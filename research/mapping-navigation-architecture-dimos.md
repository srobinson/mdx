---
title: DimOS Mapping and Navigation Architecture Deep Dive
type: research
tags: [robotics, mapping, navigation, occupancy-grids, path-planning, slam, dimos]
summary: Architecture analysis of DimOS mapping (41 files, 3956 LOC) and navigation (25 files, 4636 LOC) subsystems covering occupancy grid generation, Voronoi gradient costmaps, replanning A*, frontier exploration, and visual servoing.
status: active
source: codebase-analyst
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Executive Summary

DimOS implements a complete autonomous navigation stack for indoor robots. The mapping subsystem converts 3D point clouds into 2D occupancy grids using three distinct algorithms (general, height-cost, simple), then transforms these into gradient costmaps using a Voronoi-based approach that favors paths equidistant from obstacles. The navigation subsystem uses a replanning A* architecture with global/local planner separation, frontier-based autonomous exploration via wavefront BFS, and visual servoing for object-directed navigation. The system is reactive (RxPY subjects) and uses LCM for inter-module communication.

## Project Metadata

- **Language**: Python with C++ extension (pybind11 for A*)
- **Key dependencies**: NumPy, SciPy (ndimage), numba (GPU kernels), Open3D (point clouds), RxPY (reactive streams), pybind11
- **Communication**: LCM (Lightweight Communications and Marshalling) with custom message types
- **Architecture pattern**: Module system with typed input/output ports, reactive subscriptions

## Architecture Overview

### Mapping Subsystem (3,956 LOC across 41 files)

```
dimos/mapping/
  pointclouds/           # PointCloud2 -> OccupancyGrid conversion (935 LOC)
    occupancy.py         # Three occupancy algorithms (501 LOC)
    accumulators/        # Incremental point cloud merging
  occupancy/             # Grid post-processing pipeline (1,548 LOC)
    gradient.py          # Distance-based and Voronoi gradient generation
    inflation.py         # Binary obstacle inflation by robot radius
    operations.py        # Smoothing and overlay operations
    path_map.py          # Orchestrator: inflate -> gradient -> navigation map
    path_resampling.py   # Path smoothing with moving average filter
    extrude_occupancy.py # 2D grid -> 3D MuJoCo scene generation
    visualizations.py    # Grid visualization utilities
  osm/                   # OpenStreetMap tile fetching (446 LOC)
  google_maps/           # Google Maps API integration (435 LOC)
```

### Navigation Subsystem (4,636 LOC across 25 files)

```
dimos/navigation/
  base.py                        # NavigationInterface ABC
  rosnav.py                      # ROS bridge navigation module
  replanning_a_star/             # Primary navigation stack (2,238 LOC)
    module.py                    # ReplanningAStarPlanner (Module entry point)
    global_planner.py            # Goal handling, replanning, stuck detection
    local_planner.py             # Path following with obstacle detection
    min_cost_astar.py            # Python A* implementation
    min_cost_astar_cpp.cpp       # C++ A* via pybind11 (production default)
    navigation_map.py            # Costmap management wrapper
    controllers.py               # P and PD velocity controllers
    goal_validator.py            # BFS-based safe goal search
    path_clearance.py            # Path obstacle checking
    path_distancer.py            # Distance-to-path calculation
    position_tracker.py          # Stuck detection via position history
    replan_limiter.py            # Replan attempt budgeting
  frontier_exploration/          # Autonomous exploration (1,359 LOC)
    wavefront_frontier_goal_selector.py  # Wavefront BFS frontier detection
  visual_servoing/               # Vision-guided navigation (374 LOC)
    detection_navigation.py      # Navigate toward 3D detections
    visual_servoing_2d.py        # 2D bounding box centering
```

## Map Representations

### 1. Point Clouds (3D)

Raw sensor data arrives as `PointCloud2` messages. The `GeneralPointCloudAccumulator` maintains a running voxel-downsampled map using Open3D, splicing new frames into existing geometry with a cylinder-based replacement strategy (`_splice_cylinder` with `shrink=0.5`).

**File**: `dimos/mapping/pointclouds/accumulators/general.py`

### 2. Occupancy Grids (2D)

The core representation. `OccupancyGrid` uses an int8 numpy array where:
- `-1` = unknown
- `0` = free space
- `1-99` = cost (gradient values)
- `100` = occupied/lethal

Three algorithms convert point clouds to occupancy grids:

#### `general_occupancy` (default)
Height-band filtering: points between `min_height` and `max_height` become obstacles, points below become free space. Supports free-space dilation via `mark_free_radius`.

**File**: `dimos/mapping/pointclouds/occupancy.py:297-410`

#### `height_cost_occupancy`
Terrain slope-based costmap. Computes Sobel gradient magnitude of a smoothed height map, maps slope to cost 0-100 based on `can_climb` threshold. Handles overhangs via `can_pass_under` (if vertical gap exceeds threshold, uses ground height instead of ceiling). Uses numba kernel (`_height_map_kernel`) for fast grid population. Erodes the observed mask before computing gradients to avoid false costs at unknown-region boundaries.

**File**: `dimos/mapping/pointclouds/occupancy.py:143-284`

#### `simple_occupancy`
Minimal variant using numba kernel for grid population with height band filtering. No free-space expansion.

**File**: `dimos/mapping/pointclouds/occupancy.py:427-491`

### 3. Gradient Costmaps (2D, derived)

The costmap processing pipeline (`make_navigation_map`) transforms binary occupancy into navigation-ready costmaps:

```
binary occupancy -> smooth (optional) -> inflate by robot half-width -> overlay original obstacles -> Voronoi gradient
```

Two strategies: `"simple"` (inflate only) and `"mixed"` (smooth + inflate + overlay).

**File**: `dimos/mapping/occupancy/path_map.py:25-40`

### 4. External Map Sources

- **OSM**: Fetches raster tiles, provides `pixel_to_latlon`/`latlon_to_pixel` conversion (`dimos/mapping/osm/osm.py`)
- **Google Maps**: Geocoding, place search, location context via Google Maps API (`dimos/mapping/google_maps/google_maps.py`)

## Key Algorithms

### Voronoi Gradient (the interesting one)

Standard distance-based gradients produce high costs in the center of narrow corridors, making them navigable but expensive. The Voronoi gradient solves this by finding the Voronoi diagram of obstacle clusters (cells equidistant from multiple distinct obstacles) and assigning zero cost to Voronoi edges.

**Algorithm**:
1. Label connected obstacle regions via `ndimage.label`
2. Compute EDT (Euclidean Distance Transform) with nearest-obstacle indices
3. Map each cell to its nearest obstacle cluster label
4. Detect Voronoi edges using 3x3 min/max filters: edge exists where `local_max != local_min` of cluster labels
5. Compute distance to nearest Voronoi edge via EDT
6. Cost = `99 * d_voronoi / (d_obstacle + d_voronoi)`

Result: paths naturally flow through corridor centers and maximize clearance from all obstacles.

Falls back to standard gradient when <= 1 obstacle cluster exists.

**File**: `dimos/mapping/occupancy/gradient.py:84-202`

### Min-Cost A* (dual-objective)

The A* implementation uses a **dual-priority** search: primary key is cumulative cell cost, secondary key is path distance with Euclidean heuristic. This means the planner first minimizes traversal through high-cost areas, then among equal-cost paths picks the shortest.

Key design choices:
- Unknown cells are traversable with `cost_threshold * unknown_penalty` (default 0.8x threshold), encouraging exploration through unmapped space
- 8-connected grid with diagonal movement costs of sqrt(2)
- C++ implementation via pybind11 is the production default, with Python fallback
- C++ version pre-allocates hash maps at `width * height / 4`

**Files**: `dimos/navigation/replanning_a_star/min_cost_astar.py:122-227`, `min_cost_astar_cpp.cpp:111-241`

### Replanning Architecture

The `GlobalPlanner` runs a monitoring thread that triggers replanning on three conditions:

1. **Obstacle detected**: Local planner signals `obstacle_found`
2. **Path deviation**: Robot drifts > 0.9m from planned path
3. **Stuck detection**: Position tracker detects no progress over 8-second window

Before planning, it tries multiple robot width multipliers (`[1.1]`, formerly `[2.2, 1.7, 1.3, 1]`) to find paths with sufficient clearance. Goals in occupied space are relocated via BFS-based `find_safe_goal` with contiguous free-space search.

The `ReplanLimiter` caps retry attempts to prevent infinite replanning loops.

**File**: `dimos/navigation/replanning_a_star/global_planner.py:44-348`

### Local Planner

Follows the global path using P or PD velocity controllers (`PController`, `PdController`). Produces `cmd_vel` (Twist) commands. Monitors path clearance and signals the global planner when obstacles are found on the planned path.

**Files**: `dimos/navigation/replanning_a_star/local_planner.py`, `controllers.py`

### Wavefront Frontier Exploration

Autonomous exploration using the wavefront frontier detection algorithm (850 LOC). Key features:

- **Frontier detection**: BFS from robot position, identifying unknown cells adjacent to free space (but not adjacent to obstacles)
- **Frontier grouping**: Connected frontier cells are clustered, filtered by minimum perimeter
- **Goal scoring**: Considers distance, exploration direction momentum, and obstacle proximity (`safe_distance`)
- **Information gain tracking**: Counts known cells between exploration steps, stops after `num_no_gain_attempts` consecutive low-gain goals
- **Lookahead distance** and **max explored distance** parameters control exploration radius

The explorer publishes `goal_request` via LCM, which feeds directly into the replanning A* planner.

**File**: `dimos/navigation/frontier_exploration/wavefront_frontier_goal_selector.py:81-845`

### Visual Servoing

Two modes for vision-guided navigation:

1. **DetectionNavigation**: Computes twist commands to approach 3D object detections, using depth information for distance control
2. **VisualServoing2D**: Centers a 2D bounding box detection in the camera frame using proportional control

**Files**: `dimos/navigation/visual_servoing/detection_navigation.py`, `visual_servoing_2d.py`

## Data Flow

```
Sensor (LiDAR/Depth) -> PointCloud2
                            |
                  GeneralPointCloudAccumulator (voxel downsampling, splicing)
                            |
                  occupancy_fn (general/height_cost/simple)
                            |
                      OccupancyGrid (binary: -1/0/100)
                            |
                  make_navigation_map:
                    smooth_occupied -> simple_inflate -> overlay -> voronoi_gradient
                            |
                      OccupancyGrid (gradient: 0-100 cost)
                            |
           +----------------+----------------+
           |                                 |
    min_cost_astar                   WavefrontFrontierExplorer
           |                          (frontier detection + goal selection)
    Path (smooth_resample_path)              |
           |                          goal_request -> GlobalPlanner
    LocalPlanner                             |
           |                          (same path as left)
    cmd_vel (Twist)
```

## Module Communication Pattern

DimOS uses a typed port system. Each `Module` declares `In[T]` and `Out[T]` ports. Modules wire together via LCM subscriptions:

```python
class ReplanningAStarPlanner(Module, NavigationInterface):
    odom: In[PoseStamped]
    global_costmap: In[OccupancyGrid]
    goal_request: In[PoseStamped]

    goal_reached: Out[Bool]
    cmd_vel: Out[Twist]
    path: Out[Path]
```

Internal reactive plumbing uses RxPY `Subject` instances for event propagation between GlobalPlanner, LocalPlanner, and the monitoring thread.

## Path Smoothing

Paths from A* are jagged (grid-aligned). The `smooth_resample_path` function applies:
1. 10x upsampling via linear interpolation along arc length
2. Moving average filter (window=100 by default)
3. Resampling at desired spacing (0.1m)
4. Start/end points preserved exactly

**File**: `dimos/mapping/occupancy/path_resampling.py:143-256`

## MuJoCo Scene Generation

An occupancy grid can be extruded into a 3D MuJoCo simulation scene. `identify_convex_shapes` finds rectangular regions in the grid, then `generate_mujoco_scene` produces XML with box geoms at 0.5m height. This enables sim-to-real transfer of mapped environments.

**File**: `dimos/mapping/occupancy/extrude_occupancy.py:168-235`

## Notable Design Decisions

1. **Voronoi gradient over distance gradient**: Standard inflation layers create high-cost valleys in corridor centers. The Voronoi approach produces zero-cost paths through corridor midlines, yielding more natural robot trajectories without parameter tuning.

2. **Dual-objective A***: Cost-first, distance-second prioritization means the planner actively avoids high-cost zones even if they offer shorter paths. This interacts well with the Voronoi costmap since corridor centers have zero cost.

3. **Unknown space is traversable**: Setting `unknown_penalty=0.8` means the planner will route through unknown space rather than refusing to plan. This is essential for frontier exploration where the goal is often in unmapped territory.

4. **C++ A* with Python fallback**: The critical hot path (A* search) has a pybind11 C++ implementation while the rest of the stack stays in Python. Pragmatic performance optimization.

5. **Reactive architecture**: RxPY subjects and LCM pub/sub decouple the planner from sensor sources. The same planner module works with ROS SLAM backends or custom point cloud pipelines.

6. **Numba kernels**: Performance-critical grid population loops use numba JIT compilation rather than pure numpy, particularly for `height_cost_occupancy`.

## Relationship to Perception

The mapping subsystem receives point clouds from perception but does not directly depend on semantic understanding. The connection points are:
- `PointCloud2` messages from depth sensors (via ROS or LCM)
- `visual/query.py` uses VLM (Qwen) to find object bounding boxes in images for visual navigation
- `DetectionNavigation` consumes 3D object detections from the perception pipeline

There is no semantic mapping layer (no labeled rooms, no object-aware costmaps). Maps are purely geometric.

## What Goes Beyond Standard SLAM

DimOS does not implement SLAM itself. It consumes SLAM output (registered point clouds, odometry) from external sources (ROS SLAM backends like RTAB-Map). The novel contributions are in the costmap generation and navigation planning layers:

1. **Voronoi gradient costmaps**: While Voronoi diagrams for robot path planning exist in the literature, applying them as a costmap layer (rather than a discrete graph) that feeds into grid-based A* is a clean practical integration.

2. **Height-cost occupancy with overhangs**: The `can_pass_under` logic in `height_cost_occupancy` handles tables, shelves, and other overhangs that standard 2D projection would treat as obstacles.

3. **Occupancy-to-simulation pipeline**: `extrude_occupancy.py` bridges real-world mapping directly into MuJoCo simulation scenes, enabling rapid sim testing of navigation in real environments.

4. **Information-gain-based exploration termination**: The frontier explorer tracks the rate of new information discovery and terminates when gains plateau, rather than requiring complete map coverage.

## Test Coverage

The occupancy subsystem has thorough unit tests (8 test files covering inflation, gradient, path operations, extrusion, and visualization). The navigation subsystem has tests for the A* algorithm and goal validator, plus a substantial test suite for the wavefront frontier explorer (368 LOC of tests).

## Open Questions

1. How does the system handle dynamic obstacles? The replanning architecture detects them via path clearance checks, but there is no explicit dynamic object tracking or prediction.
2. What SLAM backends are supported beyond the ROS integration in `rosnav.py`?
3. The `_find_wide_path` method currently only tries `[1.1]` robot width (commented-out values: `[2.2, 1.7, 1.3, 1]`). Was this simplified for performance, or is the wider search still under development?
4. The `GlobalConfig` object referenced throughout is not in the mapping/navigation directories. It likely holds robot dimensions, planner strategy, and other global parameters.

## Relevance to EchoEcho

DimOS's mapping architecture provides a reference implementation for indoor occupancy grid generation and navigation costmap design. The Voronoi gradient approach and the height-cost occupancy algorithm for handling overhangs are directly relevant to any indoor mapping system. The occupancy-to-MuJoCo pipeline demonstrates how 2D maps can be extruded into 3D representations, which parallels the floor plan extrusion concepts in the EchoEcho interior mapping proposals.

---
title: DimOS Perception and Detection System Architecture
type: research
tags: [perception, computer-vision, robotics, 3d-detection, reid, vlm, segmentation, dimos]
summary: Deep analysis of DimOS perception pipeline covering 2D/3D detection, object tracking, ReID, VLM integration, spatial memory, and temporal scene understanding
status: active
source: codebase-analyst
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Executive Summary

DimOS (by Dimensional Inc.) implements a full perception stack for robotic spatial understanding. The system processes RGBD camera streams through a layered pipeline: YOLO-based 2D detection with instance segmentation, depth-based 3D lifting via Open3D, embedding-based re-identification for persistent object identity, and VLM-powered semantic querying. An experimental temporal memory subsystem uses VLMs to build persistent entity-relationship graphs from video streams. The architecture is reactive (RxPY), module-based, and designed around LCM pub/sub transport.

## Project Metadata

- **Language**: Python 3
- **Framework**: Custom module system (`dimos.core.module.Module`) with RxPY reactive streams and LCM transport
- **Key dependencies**: ultralytics (YOLO/YOLOE), Open3D, torch, torchreid, transformers, chromadb, sam2 (EdgeTAM), openai
- **Perception subsystem**: 72 files, 13,443 LOC
- **Models subsystem**: 23 files, 3,106 LOC
- **License**: Apache 2.0, Copyright Dimensional Inc.

## Architecture Overview

### Module System

Every perception component extends `Module`, which provides:
- `In[T]` / `Out[T]` typed pub/sub channels (LCM-backed)
- `@rpc` decorated methods for remote procedure calls
- `@skill` decorated methods for agent-accessible capabilities
- Reactive stream composition via RxPY observables
- Lifecycle management (`start()` / `stop()`)

### Pipeline Layers

```
Camera (RGB + Depth + CameraInfo)
    |
    v
[Detection2DModule] -- YOLO/YOLOE detector
    |  produces: ImageDetections2D (bbox, seg mask, track_id, confidence)
    v
[Detection3DModule] -- extends Detection2DModule
    |  aligns 2D detections with pointcloud stream
    |  produces: ImageDetections3DPC (pointcloud per detection)
    v
[ObjectSceneRegistrationModule] -- full pipeline
    |  YOLOE 2D -> depth lift -> Object3D -> ObjectDB
    |  produces: persistent Object entities with pointclouds
    v
[ObjectTracking] -- single-object CSRT tracker with ORB ReID
    |  produces: 2D/3D tracking for a specified bounding box
    v
[ReidModule] -- embedding-based long-term identity
    |  produces: stable person IDs across track breaks
    v
[SpatialMemory] -- ChromaDB-backed spatial scene memory
    |  produces: location-indexed image embeddings
    v
[TemporalMemory] -- experimental VLM-powered scene understanding
    |  produces: entity graph, rolling summaries, queryable memory
```

## Perception Capabilities

### 2D Detection

**File**: `dimos/perception/detection/module2D.py` (181 LOC)

`Detection2DModule` wraps any `Detector` implementation. It applies a sharpness barrier (rejecting blurry frames), runs detection, optionally filters results, and publishes to LCM topics.

**Detectors available**:

| Detector | File | LOC | Description |
|----------|------|-----|-------------|
| `Yolo2DDetector` | `detection/detectors/yolo.py` | 83 | Standard YOLO with ultralytics, supports bbox + keypoints |
| `Yoloe2DDetector` | `detection/detectors/yoloe.py` | 177 | YOLO-E with text and visual prompting, instance segmentation, built-in tracking |

`Yoloe2DDetector` is the primary detector. It supports two modes:
- **LRPC** (prompt-free): uses a pre-trained model that detects common objects without text prompts
- **PROMPT**: accepts runtime text prompts (`set_prompts(text=["cup", "mouse"])`) or visual bounding box prompts

Key configuration: `conf=0.6, iou=0.6, persist=True` (built-in tracker persistence), `max_area_ratio=0.3` filter.

YOLOE's `model.track()` provides short-term `track_id` values per detection, which serve as the initial identity link before ReID takes over.

### 3D Detection

**File**: `dimos/perception/detection/module3D.py` (235 LOC)

`Detection3DModule` extends `Detection2DModule`. It:
1. Aligns 2D detection stream with a pointcloud stream using `align_timestamped()` (tolerance 250ms, 20s buffer)
2. Looks up TF transform from camera_optical frame to pointcloud frame
3. For each 2D detection, creates a `Detection3DPC` by projecting the detection bbox onto the world pointcloud

The `Detection3DPC.from_2d()` method (336 LOC file) handles:
- Projecting 2D bbox corners through camera intrinsics
- Extracting the relevant subset of the world pointcloud
- Computing oriented bounding boxes via Open3D

### Object Scene Registration (Full Pipeline)

**File**: `dimos/perception/object_scene_registration.py` (359 LOC)

`ObjectSceneRegistrationModule` combines everything into a production pipeline:

1. Subscribes to aligned color + depth streams
2. Runs `Yoloe2DDetector.process_image()` for 2D detections with segmentation masks
3. Calls `Object.from_2d_to_list()` to create 3D objects from RGBD:
   - Masks the depth image per detection
   - Creates Open3D RGBD images
   - Projects to pointclouds via `PinholeCameraIntrinsic`
   - Applies voxel downsampling (5mm default) and statistical outlier removal
   - Optionally transforms to world frame via camera_transform
   - Computes oriented bounding boxes for center/size/pose
4. Feeds objects into `ObjectDB` for persistence and deduplication

### Segmentation

**File**: `dimos/models/segmentation/edge_tam.py` (269 LOC)

`EdgeTAMProcessor` implements SAM2-based video object segmentation:
- Uses EdgeTAM (efficient SAM2 variant) for GPU-accelerated mask tracking
- Accepts point prompts, label prompts, or bounding box prompts to initialize tracking
- Propagates masks across frames using `SAM2VideoPredictor.propagate_in_video()`
- Manages a sliding buffer (100 frames) to avoid OOM
- Produces `Detection2DSeg` objects with per-pixel masks

The segmentation masks feed into the 3D lifting pipeline. When `Detection2DSeg` masks are available, the depth masking is pixel-precise rather than bbox-approximated.

### Depth Handling

Depth processing is distributed across the pipeline rather than centralized:

- `Object.from_2d_to_list()` handles RGBD to pointcloud conversion using Open3D
- Depth scale conversion (mm to meters) happens at ingestion: `DEPTH16` format is divided by 1000
- `ObjectSceneRegistrationModule.get_full_scene_pointcloud()` generates a full scene pointcloud from the latest depth frame, with optional object exclusion for manipulation planning
- Camera intrinsics are extracted from `CameraInfo.K` matrix: `[fx, 0, cx, 0, fy, cy, 0, 0, 1]`

No standalone depth estimation model exists. The system assumes a hardware depth sensor (RGBD camera).

## Object/Entity Representation

### Type Hierarchy

```
Detection2D (abstract)
  |-- Detection2DBBox (bbox, track_id, class_id, confidence, name, image)
  |     |-- Detection2DPerson (keypoints, pose from YOLO)
  |     |-- Detection2DSeg (segmentation mask + bbox)
  |     |-- Detection2DPoint (single point detection)
  |
Detection3D(Detection2DBBox)
  |-- Detection3DPC (pointcloud, oriented bbox, pose)
  |-- Object (persistent 3D object with accumulated pointcloud, update history)
```

### The Object class (`detection/type/detection3d/object.py`, 367 LOC)

`Object` is the primary persistent entity. Key fields:

```python
@dataclass(kw_only=True)
class Object(Detection3D):
    object_id: str          # UUID hex[:8]
    center: Vector3
    size: Vector3
    pose: PoseStamped
    pointcloud: PointCloud2
    camera_transform: Transform | None
    mask: np.ndarray | None
    detections_count: int = 1
```

`update_object()` accumulates repeated observations, incrementing `detections_count` and replacing pointcloud/center with the latest observation.

### ObjectDB (`detection/objectDB.py`, 321 LOC)

Two-tier spatial memory with deduplication:

- **Pending tier**: recently detected objects with `detections_count < threshold` (default 6)
- **Permanent tier**: confirmed objects promoted after repeated detection
- **Deduplication**: first by `track_id` match (from YOLOE tracker), then by center distance within threshold (default 0.2m)
- **TTL**: pending objects expire after 5s; track_id mappings expire after 5s
- Thread-safe via `threading.RLock`

### ImageDetections2D (`detection/type/detection2d/imageDetections2D.py`, 94 LOC)

Container binding an image to its list of detections. Factory methods:
- `from_ultralytics_result()`: parses YOLO/YOLOE results into typed detections (bbox, seg, or person based on available data)
- `from_ros_detection2d_array()`: deserializes from LCM/ROS messages

## Re-Identification (ReID)

### Architecture

```
ReidModule (module.py, 114 LOC)
  |-- subscribes to aligned (image, detections) streams
  |-- delegates to IDSystem
        |-- PassthroughIDSystem: returns track_id as-is (no ReID)
        |-- EmbeddingIDSystem: embedding-based long-term identity
```

### EmbeddingIDSystem (`reid/embedding_id_system.py`, 266 LOC)

This is the core ReID engine. It maps short-term YOLO `track_id` values to stable long-term IDs using embedding similarity.

**Algorithm**:

1. For each detection, crop the image region (with optional padding)
2. Compute an embedding via the embedding model
3. Normalize the embedding for cosine similarity
4. Accumulate embeddings per `track_id` (up to `max_embeddings_per_track=500`)
5. Wait for `min_embeddings_for_matching=10` embeddings before attempting association
6. Compare against all other tracks using group similarity:
   - `top_k_mean` mode (default): mean of top-30 pairwise cosine similarities
   - Also supports `max` and `mean` modes
7. Apply negative constraints: tracks that co-occurred in the same frame cannot be the same object
8. If best similarity exceeds `similarity_threshold=0.63`, merge tracks under the same long-term ID
9. Otherwise, assign a new unique long-term ID

**Embedding models available**:

| Model | File | LOC | Backend |
|-------|------|-----|---------|
| `TorchReIDModel` | `models/embedding/treid.py` | 108 | torchreid (person re-identification) |
| `CLIPModel` | `models/embedding/clip.py` | 112 | HuggingFace CLIP (vision-language) |

`TorchReIDModel` is the default for person ReID. It uses the torchreid library, which provides models specifically trained for person re-identification (e.g., OSNet, ResNet-based).

### ObjectTracking (ORB-based ReID)

**File**: `dimos/perception/object_tracker.py` (641 LOC)

A separate, simpler tracking module for single-object tracking:
- Uses OpenCV CSRT tracker for frame-to-frame bbox tracking
- ORB feature descriptor matching for re-identification (Lowe's ratio test at 0.75)
- Runs in a dedicated thread at 30Hz
- 3-frame warmup period before ReID validation starts
- Stops tracking after `reid_fail_tolerance` consecutive failures
- Publishes TF transforms for tracked object position

This is distinct from the embedding-based `ReidModule` and appears designed for single-target following rather than multi-object scene understanding.

## VLM (Vision-Language Model) Integration

### VlModel Base Class (`models/vl/base.py`, 358 LOC)

Abstract base providing:
- `query(image, question)`: ask a question about an image
- `query_batch(images, question)`: batch inference
- `query_multi(image, queries)`: multiple questions about one image
- `query_json(image, query)`: structured JSON output with retry
- `query_detections(image, query)`: VLM-based object detection (outputs bounding boxes)
- `query_points(image, query)`: VLM-based point localization
- `caption(image)`: image captioning
- `auto_resize` config for scaling images before inference

### VLM Implementations

| Model | File | LOC | Type | Notes |
|-------|------|-----|------|-------|
| `QwenVlModel` | `vl/qwen.py` | 102 | API (OpenAI-compatible) | Uses `vllm` backend, `Qwen/Qwen2.5-VL-72B-Instruct` default |
| `OpenAIVlModel` | `vl/openai.py` | 106 | API | GPT-4o default |
| `MoondreamVlModel` | `vl/moondream.py` | 220 | Local | Custom detection and point query methods |
| `Florence2Model` | `vl/florence.py` | 170 | Local | Microsoft Florence-2, batch captioning |

`QwenVlModel` is integrated into the 3D detection pipeline via `Detection3DModule.ask_vlm()` and `nav_vlm()` skills, allowing natural language object queries that resolve to 3D positions.

The `nav_vlm` skill chain: text query -> VLM detection -> 2D bbox -> pointcloud alignment -> 3D pose. This enables commands like "red cup on the table left of the pencil" to produce navigable 3D coordinates.

### VLM-based Detection

`VlModel.query_detections()` prompts the VLM to output bounding boxes as JSON arrays (`["label", x1, y1, x2, y2]`), then converts these to `ImageDetections2D`. Coordinate rescaling handles the `auto_resize` transform. This provides open-vocabulary detection without retraining.

## Temporal Memory (Experimental)

**Directory**: `dimos/perception/experimental/temporal_memory/` (14 files, 3,536 LOC)

### Architecture

```
FrameWindowAccumulator -- collects frames at configurable FPS
    |
    v
CLIP Filter -- selects diverse keyframes from window
    |
    v
WindowAnalyzer -- VLM analyzes keyframes for entities, relations, activities
    |
    v
EntityGraphDB -- SQLite-backed entity-relationship graph
    |
    v
TemporalState -- rolling state with entity roster and summaries
```

### Key Components

**TemporalMemoryConfig** (41 LOC): Configures window-based processing at 1 FPS, 5s windows, 5s stride. VLM summary every 30s. CLIP filtering for keyframe diversity.

**FrameWindowAccumulator** (159 LOC): Collects frames into fixed-time windows, emits windows when stride elapses.

**CLIP Filter** (`clip_filter.py`, 171 LOC): `adaptive_keyframes()` selects diverse frames by computing CLIP embeddings and greedily picking frames that maximize minimum distance from already-selected frames.

**WindowAnalyzer** (166 LOC): Sends keyframes to VLM with structured prompts to extract:
- Entities with names and descriptions
- Spatial relations between entities
- Current activities
- Rolling scene summaries

**EntityGraphDB** (625 LOC): SQLite-backed persistent storage with tables for entities, relations, and distances. Supports:
- Entity upsert with last-seen timestamps
- Spatial relations (e.g., "left_of", "on_top_of")
- Distance estimation between entity pairs (VLM-estimated)
- Neighborhood queries by entity name or spatial proximity
- Time-based entity filtering

**TemporalState** (170 LOC): In-memory rolling state tracking entity roster, recent activities, and scene summaries. Thread-safe snapshots for query-time context.

**TemporalMemory** (664 LOC): Orchestrates the full pipeline as a `Module`. Processes camera stream, runs VLM analysis on windows, maintains entity graph, handles natural language queries against accumulated scene knowledge.

## Spatial Memory

**File**: `dimos/perception/spatial_perception.py` (594 LOC)

`SpatialMemory` maintains a location-indexed visual memory using ChromaDB:
- Records frames at minimum distance (0.01m) and time (1s) intervals
- Embeds images with CLIP (512-dim)
- Stores in ChromaDB with position metadata
- Supports queries by text, image, or location
- Tracks named locations and robot positions
- Persists to disk via ChromaDB PersistentClient

## Sensors Supported

Based on the input types across modules:
- **RGB camera**: `In[Image]` (BGR OpenCV format)
- **Depth camera**: `In[Image]` with `DEPTH16` (uint16 mm) or `DEPTH` (float32 meters) formats
- **Camera intrinsics**: `In[CameraInfo]` with K matrix
- **Pointcloud**: `In[PointCloud2]` (Open3D-backed)
- **TF transforms**: `TF()` lookup service for coordinate frame transforms

The system assumes an RGBD camera (like RealSense or similar) providing synchronized color, depth, and camera info streams.

## Key Patterns

### Reactive Stream Composition

All perception modules use RxPY for dataflow:
```python
aligned_frames = align_timestamped(
    self.color_image.observable(),
    self.depth_image.observable(),
    buffer_size=2.0,
    match_tolerance=0.1,
)
backpressure(aligned_frames).subscribe(self._on_aligned_frames)
```

`align_timestamped()` is the critical primitive for multi-sensor fusion. `backpressure()` prevents queue buildup when processing is slower than sensor rate.

### Two-Tier Object Persistence

ObjectDB's pending/permanent pattern prevents transient false detections from persisting. Objects must be detected `min_detections=6` times before promotion. This is a simple but effective filtering heuristic.

### Embedding-based Identity

The ReID system's group similarity comparison (storing all embeddings per track, comparing via top-k mean) is more robust than single-embedding matching. The negative constraint system (co-occurring tracks cannot merge) prevents identity collapse.

## Applicability to Indoor Mapping Without Robots

Several DimOS perception components are directly relevant to EchoEcho's indoor mapping use case:

**Directly applicable:**
- **VLM-based open-vocabulary detection** (`VlModel.query_detections()`): could identify room features, signage, doors, and landmarks from phone camera images without training custom models
- **Temporal Memory entity graph**: the entity-relationship extraction pattern (VLM + SQLite graph) could build semantic maps of indoor spaces from walkthrough video
- **CLIP-based keyframe selection**: useful for reducing redundant frames from continuous camera capture during building walkthroughs
- **Spatial Memory with ChromaDB**: location-indexed image embeddings could power "what's near this location" queries for indoor navigation

**Partially applicable (would need adaptation):**
- **Object.from_2d_to_list()**: the RGBD-to-pointcloud pipeline requires hardware depth sensors. Phone-based mapping would need monocular depth estimation (e.g., Depth Anything, MiDAS) as a substitute
- **ObjectDB deduplication**: the track_id + distance matching pattern is useful, but indoor mapping would need larger distance thresholds and possibly visual place recognition instead of track_id continuity
- **ReID system**: the embedding similarity approach could identify recurring landmarks across different visits, adapting `EmbeddingIDSystem` for place/object re-recognition rather than person tracking

**Not applicable:**
- **CSRT single-object tracker**: designed for real-time robot target following, not relevant to mapping
- **EdgeTAM segmentation**: requires CUDA GPU, designed for real-time video, too heavy for mobile

## Open Questions

1. How does the `Detection3DPC.from_2d()` method handle occlusion when projecting 2D detections onto the world pointcloud? The 336 LOC file was outlined but the full projection logic warrants deeper inspection.
2. The temporal memory's VLM prompts (in `temporal_utils/prompts.py`) were not examined. These would reveal exactly what structured information is extracted per window.
3. No monocular depth estimation model exists in the codebase. If indoor mapping without depth sensors is a goal, this is a gap that would need to be filled.
4. The `dimos/models/embedding/mobileclip.py` file was not indexed by fmm. This is likely a lightweight CLIP variant for mobile/edge deployment that could be relevant for phone-based perception.
5. The `Qwen/video_query.py` implements frame-level video querying via Qwen VLM. This is a deprecated path (`agents_deprecated` imports) but shows intent for video-level understanding.

---
title: Memory Architecture in DimOS - Spatial, Temporal, and Time-Series Systems
type: research
tags: [dimos, memory, spatial-memory, temporal-memory, graph-database, timeseries, robotics, vlm]
summary: Deep analysis of DimOS memory subsystems covering time-series storage backends, VLM-driven temporal entity graphs, and ChromaDB-backed spatial vector memory.
status: active
source: codebase-analyst
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Executive Summary

DimOS implements three distinct memory architectures. The **time-series store** (`dimos/memory/timeseries/`, 2,231 LOC) provides a generic, backend-swappable storage layer for timestamped sensor data with reactive stream integration. The **temporal memory** (`dimos/perception/experimental/temporal_memory/`, 3,536 LOC) builds an entity-relationship graph from video frames using VLM analysis, persisted in SQLite. The **spatial memory** (`dimos/perception/spatial_perception.py`, 594 LOC + `dimos/agents_deprecated/memory/spatial_vector_db.py`, 340 LOC) maps CLIP image embeddings to robot poses in a ChromaDB vector database for location-aware retrieval.

## Architecture Overview

```
dimos/memory/                          Time-Series Storage Layer
  timeseries/
    base.py         TimeSeriesStore[T]   ABC with 9 abstract methods, 22 public methods
    inmemory.py     InMemoryStore        SortedKeyList, O(log n) ops
    sqlite.py       SqliteStore          SQLite + pickle serialization
    postgres.py     PostgresStore        PostgreSQL + pickle, table-per-sensor
    pickledir.py    PickleDirStore       One pickle file per timestamp
    legacy.py       LegacyStore          Backward compat wrapper
  embedding.py      EmbeddingMemory      CLIP embedding + costmap overlay (stub)

dimos/perception/
  spatial_perception.py     SpatialMemory     ChromaDB + CLIP + odometry
  experimental/
    temporal_memory/
      temporal_memory.py    TemporalMemory    VLM window analysis orchestrator
      entity_graph_db.py    EntityGraphDB     SQLite graph: entities, relations, distances
      temporal_state.py     TemporalState     Thread-safe in-memory state container
      frame_window_accumulator.py             Bounded frame buffer with windowing
      window_analyzer.py    WindowAnalyzer    Stateless VLM interaction layer
      clip_filter.py        adaptive_keyframes  Motion-based keyframe selection
      temporal_utils/
        prompts.py          VLM prompt templates + JSON schema
        graph_utils.py      Graph context builder for query enrichment
        parsers.py          VLM response parsing
        helpers.py          Entity ID generation, text clamping
```

## 1. Time-Series Storage (`dimos/memory/timeseries/`)

### Core Abstraction

`TimeSeriesStore[T]` (`base.py:37-367`) is a generic ABC parameterized over any `Timestamped` subclass. Items are keyed by their `.ts` float attribute. The base class provides all iteration, streaming, and seek logic; backends only implement 9 primitive operations:

```python
# Abstract contract (base.py)
_save(timestamp, data)
_load(timestamp) -> T | None
_delete(timestamp) -> T | None
_iter_items(start?, end?) -> Iterator[(float, T)]
_find_closest_timestamp(timestamp, tolerance?) -> float | None
_count() -> int
_last_timestamp() -> float | None
_find_before(timestamp) -> (float, T) | None
_find_after(timestamp) -> (float, T) | None
```

### Storage Backends

| Backend | Data Structure | Serialization | Best For |
|---------|---------------|---------------|----------|
| `InMemoryStore` | `SortedKeyList` (sortedcontainers) | None (native Python) | Testing, short-lived sessions |
| `SqliteStore` | SQLite table `(timestamp REAL PK, data BLOB)` | pickle | Single-process persistent |
| `PostgresStore` | Postgres table `(timestamp DOUBLE PRECISION PK, data BYTEA)` | pickle | Multi-process, networked |
| `PickleDirStore` | One `.pkl` file per timestamp | pickle | Debug, inspection |

All persistent backends use Python `pickle` for data serialization. The `InMemoryStore` uses `sortedcontainers.SortedKeyList` with `bisect_key_left/right` for O(log n) lookups.

### Reactive Stream Integration

The base class integrates with RxPY observables:

- `pipe_save(source)` - operator for `Observable.pipe()` chains, saves items using `.ts`
- `consume_stream(observable)` - subscribes and saves all emitted items
- `stream(speed, seek, duration, loop)` - replays data as an `Observable` with scheduler-based timing using absolute time reference to prevent drift

The `stream()` method implements a sophisticated scheduler-based replay that computes target wall-clock times from the original timestamps and schedules emissions accordingly, preventing cumulative timing drift.

### Iteration Modes

- `iterate(seek, duration, from_timestamp, loop)` - lazy iteration with optional seeking, time bounding, and looping
- `iterate_realtime(speed, seek, ...)` - same but with `time.sleep()` delays matching original timing
- `slice_by_time(start, end)` - returns `[start, end)` range as list

## 2. Temporal Memory (`dimos/perception/experimental/temporal_memory/`)

### Pipeline Architecture

The temporal memory system processes a live video stream through a multi-stage VLM analysis pipeline:

```
color_image stream
    |
    v
sharpness_barrier(fps)     <- rate limit to configured FPS
    |
    v
FrameWindowAccumulator     <- bounded deque, extracts windows by time
    |
    v (every stride_s seconds)
adaptive_keyframes()       <- CLIP-based motion-aware frame selection
    |
    v
WindowAnalyzer.analyze_window()    <- VLM Call #1: entity/relation extraction
    |
    +---> EntityGraphDB.save_window_data()      persist entities + relations
    +---> EntityGraphDB.estimate_and_save_distances()  <- VLM Call #2 (background thread)
    +---> TemporalState.update_from_window()    update in-memory state
    +---> WindowAnalyzer.update_summary()       <- VLM Call #3 (periodic rolling summary)
    +---> publish EntityMarkers to Rerun         3D visualization overlay
```

### VLM Interaction Protocol

The system makes up to 3 VLM calls per window analysis cycle:

**Call #1 - Window Analysis** (`window_analyzer.py:84-115`): Sends keyframes + structured prompt to VLM. The prompt includes the current entity roster and rolling summary. VLM returns structured JSON conforming to `WINDOW_RESPONSE_SCHEMA`:

```python
# Structured output schema (prompts.py:23-78)
{
    "window": {"start_s": float, "end_s": float},
    "caption": str,                              # dense grounded description
    "entities_present": [{"id": str, "confidence": float}],
    "new_entities": [{"id": str, "type": enum, "descriptor": str}],
    "relations": [{
        "type": "speaks_to|looks_at|holds|uses|moves|gesture|scene_change|other",
        "subject": str, "object": str,
        "confidence": float, "evidence": [str], "notes": str
    }],
    "on_screen_text": [str],
    "uncertainties": [str],
    "confidence": float
}
```

Entity types: `person`, `object`, `screen`, `text`, `location`, `other`. Entity IDs are sequential (`E1`, `E2`, ...) and stable across windows via the roster mechanism.

**Call #2 - Distance Estimation** (`entity_graph_db.py:556-609`): Runs in a background thread. For each pair of entities visible in the window (up to `max_distance_pairs=5`), asks VLM to estimate pairwise distances. Results are categorized as `near`, `medium`, or `far` with optional metric estimates.

**Call #3 - Rolling Summary** (`window_analyzer.py:127-147`): Triggered every `summary_interval_s` (default 30s). Sends the latest frame plus accumulated chunk buffer to VLM to produce a compressed rolling summary.

### Entity Graph Database (`entity_graph_db.py`)

SQLite-based graph with three tables:

**entities** table:
```sql
entity_id TEXT PRIMARY KEY,
entity_type TEXT NOT NULL,
descriptor TEXT,
first_seen_ts REAL NOT NULL,
last_seen_ts REAL NOT NULL,
metadata TEXT  -- JSON: {world_x, world_y, world_z}
```

**relations** table:
```sql
relation_type TEXT NOT NULL,  -- speaks_to, looks_at, holds, uses, moves, gesture, etc.
subject_id TEXT NOT NULL,     -- FK -> entities
object_id TEXT NOT NULL,      -- FK -> entities
confidence REAL DEFAULT 1.0,
timestamp_s REAL NOT NULL,
evidence TEXT,                -- JSON array of visual cues
notes TEXT
```

**distances** table:
```sql
entity_a_id TEXT NOT NULL,    -- canonical ordering: a < b
entity_b_id TEXT NOT NULL,
distance_meters REAL,
distance_category TEXT,       -- near, medium, far
confidence REAL DEFAULT 1.0,
timestamp_s REAL NOT NULL,
method TEXT                   -- "vlm"
```

Thread safety: connection-per-thread pattern via `threading.local()`.

Key query capabilities:
- `get_nearby_entities(entity_id, max_distance, latest_only)` - spatial proximity queries with optional latest-only dedup
- `get_entity_neighborhood(entity_id, max_hops=2)` - BFS graph traversal up to N hops, collecting relations and distances
- `get_entities_by_time(time_window)` - temporal queries on first/last seen timestamps
- `get_relations_for_entity(entity_id, relation_type?, time_window?)` - filtered relation lookups

### Persistence Model

Two levels of persistence:
1. **Persistent DB** at `~/.local/state/dimos/temporal_memory/entity_graph.db` - survives across runs
2. **Persistent JSONL** at `~/.local/state/dimos/temporal_memory/temporal_memory.jsonl` - raw VLM responses + parsed output
3. **Per-run JSONL** in the run log directory - same data, scoped to one execution

The `new_memory` flag (default `False`) controls whether to wipe the persistent DB on startup.

### In-Memory State (`temporal_state.py`)

`TemporalState` is a thread-safe dataclass holding:
- `entity_roster: list[dict]` - all known entities with IDs, types, descriptors
- `rolling_summary: str` - compressed narrative of observations
- `chunk_buffer: list[dict]` - window results since last summary
- `last_present: list[dict]` - entities visible in most recent window
- `next_summary_at_s: float` - countdown for next rolling summary trigger

All mutations acquire a lock. `snapshot()` returns a deep copy for safe reads outside the lock.

### CLIP Keyframe Selection (`clip_filter.py`)

`adaptive_keyframes()` selects 3-5 frames from a window based on visual change:
1. Compute frame-to-frame pixel-level mean absolute differences
2. Sum total motion to determine target frame count (scaled by `change_threshold`)
3. Always include first and last frames
4. Add peaks in the diff signal (local maxima above 50% of threshold)
5. Fill remaining slots with uniform sampling

## 3. Spatial Memory (`dimos/perception/spatial_perception.py`)

### Architecture

`SpatialMemory` is a `Module` that subscribes to `color_image` and robot odometry streams, producing CLIP embeddings stored in ChromaDB:

```
color_image stream
    |
    v
_process_frame() (every 1s)
    |
    +-- distance gate: skip if robot moved < 0.01m
    +-- time gate: skip if < 1.0s since last record
    |
    v
ImageEmbeddingProvider.get_embedding()  <- CLIP ViT
    |
    v
SpatialVectorDB.add_image_vector()
    |
    +-- ChromaDB collection (cosine similarity, HNSW index)
    +-- VisualMemory (image storage by ID)
```

### Storage Backend

`SpatialVectorDB` (`agents_deprecated/memory/spatial_vector_db.py:33-340`) wraps ChromaDB:

- **Image collection**: `PersistentClient` at `~/.local/state/dimos/spatial_memory/chroma/`, HNSW index with cosine distance
- **Location collection**: separate collection for text-tagged named locations
- **Visual memory**: `VisualMemory` instance for raw image storage (by frame ID)

Metadata per entry:
```python
{
    "pos_x": float, "pos_y": float, "pos_z": float,
    "rot_x": float, "rot_y": float, "rot_z": float,
    "timestamp": float,
    "frame_id": str
}
```

### Query Modes

1. **By embedding** (`query_by_embedding`): Direct cosine similarity search in ChromaDB
2. **By location** (`query_by_location`): Brute-force scan of all metadata, filtering by Euclidean distance within radius. Note: the `TODO` comment acknowledges this needs an efficient spatial index.
3. **By text** (`query_by_text`): CLIP text embedding -> cosine similarity search. Enables natural language queries like "where is the kitchen."
4. **By tag** (`query_tagged_location`): Text-based lookup in the location collection

### Relationship to Mapping

Spatial memory is decoupled from the mapping system. It stores robot poses alongside image embeddings but does not integrate with occupancy grids or SLAM maps. The `EmbeddingMemory` class in `dimos/memory/embedding.py` hints at a costmap overlay approach (query spatial embeddings and overlay results on an `OccupancyGrid`) but the implementation is a stub with `_store_spatial_entry` being a no-op and `query_text` returning an empty list.

## 4. Embedding Memory (`dimos/memory/embedding.py`) - Stub

`EmbeddingMemory` (106 LOC) is a partially implemented module that would combine CLIP embeddings with costmap overlays:

```python
@dataclass
class SpatialEntry:
    image: Image
    pose: PoseStamped

@dataclass
class SpatialEmbedding(SpatialEntry):
    embedding: Embedding
```

The `start()` method sets up a reactive pipeline: `color_image -> sharpness_barrier -> create_spatial_entry -> embed -> store`, but `_store_spatial_entry` is a passthrough and `query_text` returns `[]`. The `query_costmap` method signature suggests the intent was to overlay embedding similarity heatmaps onto navigation costmaps.

## Key Patterns

### Reactive Stream Architecture
All memory modules integrate with RxPY observables. `TimeSeriesStore.pipe_save` and `consume_stream` allow plugging storage into reactive pipelines. `TemporalMemory` uses `Subject`, `interval`, and `sharpness_barrier` operators for frame ingestion and periodic analysis.

### VLM as Structured Perception
The temporal memory system uses VLM (defaulting to OpenAI) as a perception backend, not for chat. It extracts structured entity/relation data from video frames via carefully designed prompts with JSON schema constraints. The system maintains a running entity roster that provides continuity across VLM calls.

### Thread Safety Patterns
- `TemporalState`: single `threading.Lock` protecting all mutations, `snapshot()` for safe reads
- `EntityGraphDB`: connection-per-thread via `threading.local()`
- `FrameWindowAccumulator`: single lock over buffer and counters
- Distance estimation runs in daemon threads with join-on-stop cleanup

### Two Generations of Spatial Memory
The codebase contains two distinct approaches:
1. **Active**: `SpatialMemory` in `dimos/perception/` using ChromaDB + CLIP
2. **Stub**: `EmbeddingMemory` in `dimos/memory/` with costmap integration intent
3. **Deprecated**: `spatial_vector_db.py` in `agents_deprecated/` (still used by active `SpatialMemory`)

## Open Questions

1. **No vector search in temporal memory**: `EntityGraphDB` uses SQLite with relational queries only. Entity similarity or semantic retrieval would require either embedding entities or integrating with the spatial memory's ChromaDB.

2. **Spatial query_by_location is O(n)**: The `SpatialVectorDB.query_by_location` does a full scan of all metadata. For large deployments this will need an R-tree or similar spatial index.

3. **EmbeddingMemory vs SpatialMemory**: Two separate spatial memory approaches exist. `EmbeddingMemory` has the more elegant architecture (costmap overlay) but is unfinished. `SpatialMemory` is functional but lives partially in `agents_deprecated/`.

4. **No cross-system memory integration**: Time-series stores, temporal entity graphs, and spatial vector memory operate independently. A query like "what was near the robot when it saw a person 5 minutes ago" would require manually correlating across all three systems.

5. **Pickle serialization in time-series stores**: All persistent backends use pickle, which carries known security risks for untrusted data and lacks schema evolution support.

6. **Distance estimation accuracy**: VLM-based distance estimation (near/medium/far categories) provides approximate spatial relationships between entities but lacks metric precision. The system stores optional `distance_meters` but these are VLM estimates, not sensor measurements.

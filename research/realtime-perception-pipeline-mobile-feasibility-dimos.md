---
title: DimOS Real-Time Perception Pipeline - Mobile Feasibility Analysis
type: research
tags: [dimos, perception, mobile, real-time, vlm, yolo, streaming, spatial-memory]
summary: Analysis of DimOS perception pipeline latency characteristics, hardware assumptions, and feasibility for real-time mobile contexts
status: active
source: codebase-analyst
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Executive Summary

DimOS is a Python robotics framework (138k LOC, 860 files) with a sophisticated perception pipeline built around YOLOE object detection, Open3D pointcloud processing, ChromaDB spatial memory, and VLM-based scene understanding. The pipeline assumes GPU-equipped robots with depth cameras (ZED, RealSense). Several components have latency and computational profiles that are compatible with mobile adaptation, but the 2D-to-3D lifting path and the spatial memory indexing loop are tightly coupled to depth hardware that phones lack.

## Project Metadata

- **Language**: Python 3.x
- **Key dependencies**: ultralytics (YOLOE), Open3D, ChromaDB, RxPY, OpenCV, PyTorch, transformers (HuggingFace CLIP), ffmpeg-python
- **Build**: pyproject.toml + uv
- **Architecture**: Reactive streams (RxPY observables), modular component system with pub/sub transport (LCM)
- **Hardware targets**: NVIDIA Jetson, desktop GPU, RealSense/ZED depth cameras

## 1. Detection Pipeline Latency Characteristics

### YOLOE Integration

**File**: `dimos/perception/detection/detectors/yoloe.py` (177 LOC)

The detector wraps Ultralytics YOLOE with these characteristics:

- **Model**: `yoloe-11s-seg-pf.pt` (prompt-free) or `yoloe-11s-seg.pt` (text/visual prompt mode). The ObjectSceneRegistration module uses the **large** variant: `yoloe-11l-seg-pf.pt`
- **Inference**: `self.model.track()` with `conf=0.6, iou=0.6, persist=True` (tracking built into the detection call via Ultralytics)
- **Device auto-detection**: CUDA preferred, CPU fallback
- **Thread safety**: Single `threading.Lock` serializes all inference calls
- **No batching**: One frame per `process_image()` call

**Estimated latency**: YOLOE-11s on Jetson Orin: ~15-25ms. YOLOE-11l: ~40-80ms. On CPU (phone): the -s model would run at ~200-500ms, the -l model would be impractical.

**Mobile takeaway**: YOLOE-11s is feasible on modern phone NPUs via ONNX/CoreML export. The -l variant used in ObjectSceneRegistration is too heavy. The Ultralytics `track()` API includes BoT-SORT tracking, which adds ~5ms overhead per frame but is lightweight enough for mobile.

### 2D to 3D Lifting

**File**: `dimos/perception/detection/type/detection3d/object.py`, lines 144-287

The `Object.from_2d_to_list()` classmethod converts 2D detections to 3D objects through:

1. Mask extraction from segmentation (or bbox fallback)
2. Mask erosion (3px kernel) to clean depth edges
3. Open3D RGBD projection: `create_from_rgbd_image()` + `create_from_pointcloud()`
4. Voxel downsampling (5mm)
5. Statistical outlier removal (10 neighbors, 0.5 std ratio)
6. Oriented bounding box computation
7. Optional transform to world frame

**This path requires a depth image.** Without depth, DimOS falls back to `pixel_to_3d()` which assumes a fixed depth (e.g., 1.5m) and does simple pinhole unprojection. The Open3D processing chain is CPU-heavy and allocates per-detection pointclouds.

**Mobile takeaway**: This entire path is inapplicable without depth sensors. However, the fallback `pixel_to_3d()` with assumed depth is trivially portable and runs in microseconds. For a phone-based system, monocular depth estimation (e.g., DepthAnything) could substitute, but would add 30-50ms per frame.

### Object Tracking (ObjectTracking module)

**File**: `dimos/perception/object_tracker.py` (641 LOC)

Uses OpenCV `TrackerCSRT` with ORB feature extraction for re-identification. Frame-by-frame tracking runs in a dedicated thread. The re-identification uses ORB `detectAndCompute` which is lightweight (~2-5ms).

**Mobile takeaway**: CSRT + ORB is already phone-feasible. Runs at 30+ fps on mobile hardware.

## 2. VLM Query Pipeline (nav_vlm)

**File**: `dimos/perception/detection/module3D.py`, lines 126-169

End-to-end flow:
1. `nav_vlm(question: str)` receives natural language query
2. Instantiates `QwenVlModel` (cloud API via Alibaba DashScope, OpenAI-compatible client)
3. Captures single frame from `self.color_image.get_next()`
4. Calls `model.query_detections(image, question)` which:
   - Resizes image, converts to base64
   - Sends to cloud VLM with structured prompt requesting `[label, x1, y1, x2, y2]` JSON
   - Parses response into `ImageDetections2D`
5. Gets pointcloud and camera-to-world transform
6. Calls `process_frame()` to lift 2D detections to 3D via pointcloud
7. Falls back to `pixel_to_3d(center, assumed_depth=1.5)` if no 3D match

**Latency breakdown**:
- VLM API call (QwenVL via DashScope): **800-2000ms** (network + inference)
- Image base64 encoding: ~5-10ms
- Pointcloud lookup + transform: ~10-20ms
- 2D-to-3D lifting: ~20-50ms per detection

**Total: ~1-2.5 seconds per query**

**Mobile feasibility**: Entirely feasible with cloud VLM + phone camera. The pipeline is already cloud-based (QwenVL API). A phone would skip the pointcloud/3D lifting step and use `pixel_to_3d()` with assumed or estimated depth. The 1-2s latency is acceptable for on-demand queries ("find the red chair") but too slow for continuous frame-by-frame analysis.

**Alternative VLM path**: `dimos/navigation/visual/query.py` has `get_object_bbox_from_image()` which is a simpler version: VLM query returns a single bbox as JSON. Lighter prompt, same cloud API dependency.

## 3. Streaming Architecture

### Video Provider

**File**: `dimos/stream/video_provider.py` (234 LOC)

`VideoProvider` uses `cv2.VideoCapture` in a dedicated thread. Frame emission is rate-controlled via `time.sleep()` to match target FPS. Frames are shared to multiple subscribers via RxPY `ops.share()`.

**No ring buffer or frame dropping at the source level.** The provider emits every frame at the target rate. Backpressure is handled downstream.

### RTSP Provider

**File**: `dimos/stream/rtsp_video_provider.py` (379 LOC)

Uses ffmpeg subprocess (`pipe:` stdout) for RTSP stream decoding with:
- `nobuffer` flag to minimize input latency
- `low_delay` flag for reduced decode latency
- TCP transport (reliable, slightly higher latency than UDP)
- Raw BGR24 output piped to numpy arrays

**No adaptive bitrate or quality negotiation.** The provider reads at stream native FPS and emits all frames.

### Backpressure Strategy

**File**: `dimos/utils/reactive.py` (lines 36-65), `dimos/rxpy_backpressure/latest.py`

The `backpressure()` utility wraps any observable with a `LatestBackPressureStrategy`:
- If the downstream consumer is busy processing a frame, incoming frames are **cached (latest only)** and the old cached frame is discarded
- When the consumer finishes, it picks up the most recent cached frame
- This is the key real-time mechanism: slow consumers never build up a queue

The `Operators.exhaust_lock` in `video_operators.py` provides a similar pattern: skip frames while a processing inner observable is in-flight.

### Frame Alignment

**File**: `dimos/types/timestamped.py` (lines 169-287)

`align_timestamped()` synchronizes a primary stream (e.g., color images) with secondary streams (depth images) using:
- Per-stream circular buffers (configurable window, default 1.0s)
- Closest-timestamp matching within tolerance (default 100ms)
- Deferred matching: if a secondary hasn't arrived yet, the primary is buffered until secondary catches up or times out

The ObjectSceneRegistration uses `buffer_size=2.0, match_tolerance=0.1` for color/depth alignment.

**Mobile takeaway**: The RxPY reactive streaming architecture is portable. The backpressure strategy (drop-latest) is exactly what a mobile client needs. The frame alignment logic is relevant if integrating multiple sensor streams (e.g., camera + IMU). For a single-camera phone, it simplifies to direct frame emission.

### FPS Sampling

**File**: `dimos/stream/video_operators.py` (lines 32-102)

`VideoOperators.with_fps_sampling()` provides time-based frame rate reduction using either:
- `ops.sample(interval)`: take latest frame per interval
- `ops.throttle_first(interval)`: take first frame per interval

This is the primary frame-rate governor. A phone client would use this at 1-5 fps for VLM analysis while keeping camera preview at 30fps.

### Sharpness Barrier

**File**: `dimos/msgs/sensor_msgs/Image.py` (lines 607-611)

`sharpness_barrier(target_frequency)` selects the sharpest image within each time window. Uses `quality_barrier` internally. This is a lightweight Laplacian variance computation.

**Mobile takeaway**: Excellent candidate for on-device filtering. Laplacian sharpness detection costs ~1ms per frame and would prevent sending blurry frames to cloud VLMs. Already designed as a composable RxPY operator.

## 4. ObjectDB Persistence and Real-Time Queries

**File**: `dimos/perception/detection/objectDB.py` (321 LOC)

### Architecture

Two-tier in-memory database:
- **Pending**: objects with `detection_count < 6` (configurable `min_detections_for_permanent`)
- **Permanent**: promoted objects that have been seen 6+ times

### Deduplication

1. **Track ID matching**: O(1) lookup via `_track_id_map` dict. TTL: 5 seconds. Fast path for consecutive-frame tracking.
2. **Distance matching**: Linear scan through all objects, computing `Vector3.distance()`. Threshold: 0.2m. This is O(n) where n = total objects.

### Staleness

- Pending objects have a TTL of 5 seconds (`_pending_ttl_s`)
- Pruning runs on every `add_objects()` call
- Thread safety: `threading.RLock` on all operations

### Performance for Walking User

The 0.2m dedup radius assumes a relatively stationary robot perspective. A walking user at 1.5 m/s covers 0.2m every 133ms. At 5-10 fps detection rate, consecutive frames would have minimal displacement, so the dedup would work. But the 6-detection promotion threshold at 1 fps means an object needs to be visible for 6+ seconds before it is "confirmed." For a walking user who moves past objects in 2-3 seconds, most objects would expire from pending before promotion.

**Mobile adaptation needed**:
- Reduce `min_detections_for_permanent` to 2-3
- Reduce `pending_ttl_s` to 2-3s
- Increase `distance_threshold` to 0.5-1.0m to account for monocular depth estimation noise
- The O(n) distance scan becomes problematic above ~1000 objects (full building scan). Needs spatial indexing (R-tree, grid hash) for large-scale use.

## 5. CLIP Keyframe Selection

**File**: `dimos/perception/experimental/temporal_memory/clip_filter.py` (171 LOC)

### Algorithm: `adaptive_keyframes()`

Input: list of frames (3-100), output: 3-5 diverse keyframes.

1. Compute frame-to-frame pixel differences (mean absolute diff)
2. Total motion = sum of diffs
3. Target frame count = `total_motion / change_threshold`, clamped to [3, 5]
4. Always include first and last frame
5. Add peaks in the diff signal (local maxima above 50% of threshold)
6. If too many: keep highest-diff peaks. If too few: fill uniformly.

**This does NOT use CLIP at all.** Despite the file name `clip_filter.py`, `adaptive_keyframes` uses pure pixel differencing. CLIP is used elsewhere (the `CLIPModel` in `dimos/models/embedding/clip.py`) for embedding-based similarity, but the keyframe selector itself is lightweight.

**Computational cost**: One `np.abs(frame_diff).mean()` per adjacent frame pair. For a 5-frame window, this is ~4 numpy operations on full-resolution images. With 640x480 images: ~1ms total.

**Mobile feasibility**: Trivially runnable on-device. Could filter 30fps camera input down to 3-5 frames per 5-second window before sending to cloud VLM. This is the single most valuable on-device component for a mobile architecture.

### The broader temporal memory pipeline

**File**: `dimos/perception/experimental/temporal_memory/temporal_memory.py` (664 LOC)

The `TemporalMemory` module orchestrates:
1. Frame ingest at configurable FPS (default 1.0) with sharpness filtering
2. Buffer accumulation in `FrameWindowAccumulator` (bounded deque, max 100 frames)
3. Every `stride_s` seconds (default 5.0), extract a window of frames
4. Skip stale scenes (configurable threshold)
5. Select diverse keyframes via `adaptive_keyframes` (max 3 per window)
6. VLM Call #1: Window analysis (entities, relations, caption)
7. VLM Call #2: Distance estimation (background thread)
8. Periodic VLM Call #3: Rolling summary (every 30s)
9. Persist entities to graph DB

**VLM is called every 5 seconds with 3 frames.** At ~1-2s per VLM call, this means the VLM is busy ~40% of the time during active exploration.

## 6. SpatialPerception / ChromaDB Index

**File**: `dimos/perception/spatial_perception.py` (594 LOC)

### Update Loop

`SpatialMemory.process_stream()` processes a combined video+pose stream:

1. Gate on minimum distance moved (0.01m default)
2. Gate on minimum time elapsed (1.0s default)
3. Compute CLIP embedding of frame via `ImageEmbeddingProvider`
4. Store in ChromaDB with position/rotation metadata

**CLIP embedding**: `CLIPModel.embed()` runs HuggingFace CLIP (ViT-B/32) with `torch.inference_mode()`. On GPU: ~10-15ms per image. On CPU: ~100-200ms. On phone NPU: ~30-50ms via CoreML/ONNX.

**ChromaDB write**: `vector_db.add_image_vector()` inserts one embedding + metadata per frame. ChromaDB PersistentClient with local SQLite. Single insert: <5ms.

**Query**: `query_by_text()` and `query_by_image()` use ChromaDB's built-in similarity search. Sub-10ms for collections under 10k items.

### Real-Time Profile

This is designed for **continuous real-time updates** gated by distance and time. At walking speed (1.5 m/s) with 0.01m distance threshold, it would store ~150 frames per second, which is excessive. The 1.0s time gate limits it to 1 frame/second.

**Mobile adaptation**: The 1-frame/second storage rate with CLIP embeddings is feasible if CLIP runs on-device (NPU). ChromaDB is SQLite-backed and could run on mobile, though a lighter vector store (e.g., USearch, hnswlib) would be more appropriate. The distance gating would need GPS/IMU-based position rather than robot odometry.

## Architecture Summary: What Could Run Where

| Component | Current Hardware | On-Phone Feasible? | Latency | Notes |
|-----------|-----------------|-------------------|---------|-------|
| YOLOE-11s detection | CUDA GPU | Yes (NPU/CoreML) | ~25-50ms | Needs ONNX export |
| YOLOE-11l detection | CUDA GPU | No | ~200ms+ on CPU | Too heavy for mobile |
| BoT-SORT tracking | CPU | Yes | ~5ms | Already lightweight |
| CSRT + ORB tracker | CPU | Yes | ~5ms | OpenCV, well-supported |
| Keyframe selection | CPU | Yes | ~1ms | Pure numpy |
| Sharpness filter | CPU | Yes | ~1ms | Laplacian variance |
| Backpressure/streaming | CPU | Yes | ~0ms | RxPY operators |
| FPS sampling | CPU | Yes | ~0ms | Time-based gating |
| VLM query (QwenVL) | Cloud API | Yes (already cloud) | 800-2000ms | Phone as camera only |
| CLIP embedding | CUDA GPU | Marginal (NPU) | 30-50ms mobile | CoreML/ONNX possible |
| 2D-to-3D lifting | CPU + depth sensor | No (needs depth) | 20-50ms | Requires depth camera |
| Open3D pointcloud | CPU + depth sensor | No | 30-100ms | Heavy, needs depth |
| ObjectDB dedup | CPU | Yes | <1ms | In-memory dict |
| ChromaDB spatial index | CPU + disk | Marginal | <10ms | SQLite-backed, heavy deps |
| Monocular depth (not in DimOS) | N/A | Yes | 30-50ms | Would need to add |

## Proposed Mobile Architecture

Based on this analysis, a viable mobile perception pipeline would:

**On-device (phone)**:
1. Camera stream at 30fps
2. `sharpness_barrier` + `with_fps_sampling(fps=5)` to select 5 sharp frames/second
3. `adaptive_keyframes` to select 3-5 frames per 5-second window
4. Lightweight YOLOE-11s via CoreML/ONNX for basic object detection (optional)
5. Send keyframes + GPS/IMU pose to cloud

**Cloud**:
1. VLM scene analysis (QwenVL or GPT-4V) on keyframes
2. Monocular depth estimation on selected frames
3. Entity graph construction (from temporal memory)
4. Spatial memory index (ChromaDB or equivalent)

**Hybrid latency profile**:
- On-device frame selection: <5ms
- Network upload (3 frames, JPEG compressed): 100-300ms
- Cloud VLM analysis: 800-2000ms
- Total query-response: ~1-2.5s per window

This matches the temporal memory's existing 5-second stride and would provide scene understanding updates every 5-7 seconds during walking navigation.

## Key Files Referenced

- `dimos/perception/detection/detectors/yoloe.py` - YOLOE detector wrapper
- `dimos/perception/detection/objectDB.py` - Two-tier object persistence
- `dimos/perception/detection/module3D.py` - nav_vlm and 3D detection pipeline
- `dimos/perception/detection/module2D.py` - 2D detection module with tracking
- `dimos/perception/object_scene_registration.py` - Full detection/3D/ObjectDB pipeline
- `dimos/perception/spatial_perception.py` - ChromaDB spatial memory with CLIP
- `dimos/perception/experimental/temporal_memory/temporal_memory.py` - VLM-based temporal scene analysis
- `dimos/perception/experimental/temporal_memory/clip_filter.py` - Keyframe selection
- `dimos/perception/experimental/temporal_memory/frame_window_accumulator.py` - Bounded frame buffer
- `dimos/perception/experimental/temporal_memory/window_analyzer.py` - VLM window analysis
- `dimos/stream/video_provider.py` - Video capture to RxPY observable
- `dimos/stream/video_operators.py` - FPS sampling, backpressure, exhaust_lock
- `dimos/stream/rtsp_video_provider.py` - RTSP streaming via ffmpeg
- `dimos/utils/reactive.py` - Backpressure utility (LatestBackPressureStrategy)
- `dimos/types/timestamped.py` - Multi-stream temporal alignment
- `dimos/models/vl/qwen.py` - QwenVL cloud API integration
- `dimos/models/embedding/clip.py` - CLIP embedding model
- `dimos/msgs/sensor_msgs/Image.py` - Sharpness barrier operator
- `dimos/perception/object_tracker.py` - CSRT + ORB object tracking

## Open Questions

1. **YOLOE NPU export**: Has Ultralytics YOLOE been successfully exported to CoreML or ONNX for mobile inference? The standard Ultralytics YOLO export pipeline supports this, but YOLOE's prompt-free architecture may have compatibility issues.
2. **Monocular depth on mobile**: What is the actual latency of DepthAnything v2 on iPhone 15 NPU? Published benchmarks suggest 20-40ms at 384x384, but real-world performance varies.
3. **ChromaDB on iOS/Android**: ChromaDB uses SQLite + hnswlib internally. While both run on mobile, the Python dependency chain is problematic. A native vector store (e.g., sqlite-vss) would be more appropriate.
4. **IMU-based distance gating**: The spatial perception distance gate (0.01m) assumes high-accuracy odometry. Phone GPS provides ~3-5m accuracy outdoors, ~10-30m indoors. ARKit/ARCore visual-inertial odometry provides ~1-5cm accuracy but requires constant camera processing.
5. **VLM cost at scale**: At 5-second intervals, a walking navigation session generates ~720 VLM calls per hour. At $0.003/call (QwenVL pricing), this is ~$2.16/hour. Acceptable for accessibility use cases but worth monitoring.

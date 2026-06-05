---
title: Cubicell architecture and physical layout assessment
type: research
tags: [cubicell, architecture, file-layout, maintainability, typescript]
summary: Source grounded assessment of Cubicell's logical architecture, physical file layout, module boundaries, and scaling limits at fa32189.
status: active
project: cubicell
confidence: high
created: 2026-08-14
updated: 2026-08-14
---

# Cubicell architecture and physical layout assessment

## Verdict

Cubicell has real architecture. Several runtime invariants are strong. The physical tree no longer shows that architecture clearly.

The source is over partitioned at the top level and under modularized inside its largest folders. The root mixes several ways of organizing code at the same depth:

- Logical layers such as `domain`, `state`, and `evaluation`.
- Runtime subsystems such as `camera`, `transport`, `scene`, and `persistence`.
- UI categories such as `panels`, `controls`, `components`, and `design-system`.
- Delivery boundaries such as `studios`, `capabilities`, and `renderer`.
- General support folders such as `app`, `shared`, and `config`.

Each category is defensible in isolation. Their combination gives a new maintainer too many equally important entry points.

The concern is valid, with one qualification. Cubicell does not need a whole tree rewrite because it has 26 folders. The evidence supports focused restructuring around four pressure points:

1. `domain` is flat and exposes too much through one barrel.
2. `state` and `persistence` form one durability system across a misleading folder line.
3. The UI and composition folders overlap in responsibility.
4. Root documentation lacks a current authority map.

Any broad physical refactor is unsafe until the project restores a behavioral test surface.

## Current assessment

| Area | Judgment | Evidence |
| --- | --- | --- |
| Runtime invariants | Strong | Pure domain mutations, pure evaluation, one camera writer, semantic commands, bounded incremental rendering |
| Type design | Strong | Discriminated unions, typed commands, storage records, and explicit ports |
| File size discipline | Strong | Median 71 lines, p95 408, maximum 670 |
| Runtime import cycles | Strong | FMM found no runtime file cycle |
| Duplication | Strong | FMM found two structural duplicate candidates from 2,944 declarations |
| Physical navigation | Weak | 26 folders under `src`, 27 measured homes including root files, and several overlapping names |
| Feature locality | Weak for broad features | Face media spans about ten folders. Authored camera motion spans about eight |
| Module enforcement | Mixed | Seven folders have linted barrels. Nineteen do not |
| Public API shape | Weak in `domain` | `src/domain/index.ts` has 448 exports and 159 direct dependants |
| Documentation trust | Weak | `ARCHITECTURE.md` is pinned behind HEAD and still describes a deleted test tree |
| Change safety | Weak | Current `package.json` has no test command and the previous test tree is absent |

## The logical architecture

The intended direction is documented in `MODEL.v2.md:350-382`:

```text
Domain
  -> Evaluation
  -> Interaction and camera authority
  -> Adapters and application wiring
  -> Views and capture effects
```

The implementation contains several useful boundaries.

### Document model

`src/domain/` owns cube topology, scene state, grid layout, selection, content, scores, camera tracks, workbench state, project records, and pure operations. Domain files do not import React, Three, or the DOM.

The types are generally honest. `src/domain/content.ts:7-64` models content as a discriminated union. `src/domain/cube.ts:45-88` owns face state and the current fixed cube shape. `src/domain/workbench.ts` owns structures, states, media assets, and the working document.

### Authoring and commands

`src/editor/commands.ts` defines serializable intent. `src/interaction/commands/registry.ts` assigns each command a lane, target, arbitration rule, validation, and handler. `src/interaction/bus.ts` runs a synchronous document lane and a coalesced view lane.

This is a real seam. UI fields create commands. Domain operations mutate the document. The command bus keeps input devices from owning business rules.

Some workbench flows still call store actions directly. `ARCHITECTURE.md:85-93` names neighbor placement, grid rebuilds, visibility, preferences, and reset as side paths.

### Evaluation and playback

`src/evaluation/` samples document state without mutation. `scoreAt` produces a `Moment`. Camera track sampling produces a pose. `src/transport/stagedScene.ts` is the meeting point between session time and the document.

The split between authored document state and sampled playback state is sound.

### Camera

`src/pose/` owns pose math. `src/view/` owns framing policy. `src/camera/cameraAuthorityRuntime.ts` advances one pose. `src/camera/CameraDriver.tsx` writes the Three camera once per frame.

The folder names require explanation, but the single writer rule is valuable.

### Rendering

`src/scene/` owns the Three scene, GPU instances, face atlases, shaders, selection chrome, and the render scheduler. `src/renderer/` is a 138 line delivery contract and re-export layer. It does not own most rendering work.

### Durability

`src/state/projectDurability.ts` coordinates hydration, pending changes, promotion, revisions, rebase, and recovery. `src/persistence/` owns IndexedDB, memory storage, record codecs, hydration, projections, and storage ports.

The two folders form one durability system. The import graph records 44 imports from persistence to state and 19 in the reverse direction.

## What the physical tree gets right

### Files stay bounded

The tracked `src` tree contains 500 files when CSS is included. FMM indexes 475 TypeScript and TSX source files with 58,818 lines. The largest file has 670 lines. Most files remain focused.

The layout problem does not come from giant source files.

### Runtime files form a directed graph

FMM reports no runtime file cycle after excluding barrel hierarchy edges. Type only cycles exist inside domain, interaction, persistence, scene, and one capability. These local type relationships do not create runtime initialization loops.

### The code has little structural duplication

FMM found two duplicate candidate clusters at a 0.90 threshold. Both are small pairs. The architecture has not decayed through copy and paste.

### Several invariants have one owner

The command bus, the camera writer, pure evaluation, the storage port, stable instance slots, and face state mutation each have identifiable owners. These owners should survive any future reorganization.

## Why the tree feels shapeless

### The root uses several organizing axes

The root asks a maintainer to choose between 26 peers before the maintainer knows whether a change is a domain rule, a runtime subsystem, a UI feature, or a bundle boundary.

The source tree contains 11 homes with fewer than 500 measured lines. `renderer` has 138 lines. `motion` has 234. `config` has 94. At the other extreme, `domain` has 61 files with no subdirectories.

This imbalance makes every top level name appear equally important even though some names represent major bodies of knowledge and others represent delivery shims.

### Folder names overlap

The same product noun appears in several ownership systems:

| Noun | Current homes |
| --- | --- |
| Motion | `src/motion`, `src/panels/motion`, `src/capabilities/motion`, and face video clocking in `src/scene` |
| Camera | `src/camera`, `src/pose`, `src/view`, `src/domain/cameraTrack.ts`, `src/evaluation/cameraTrackSampleAt.ts`, and panel controls |
| Scene | `src/domain/scene.ts`, `src/scene`, and `src/renderer` |
| Content | `src/domain/content.ts`, `src/capabilities/media`, `src/scene/contentRaster.ts`, persistence codecs, and thumbnail code |
| Editor | `src/editor`, `src/interaction`, `src/app`, `src/panels`, and `src/studios/editor` |

These names describe responsibility after a maintainer understands the design. They do not help the maintainer discover the design.

### The `domain` barrel hides ownership

`src/domain/index.ts` has 448 exports, 159 direct dependants, and 322 transitive source dependants. It spans cube topology, content, selection, camera tracks, scores, project records, workbenches, and operations.

The barrel prevents deep imports. It also removes the originating module name from most import statements. A caller can import almost every core concept from `../domain`, so the import does not reveal which body of knowledge owns the symbol.

The documented word `curated` no longer describes this public surface.

### Folder boundaries have no global direction rule

`.oxlintrc.json:27-65` closes deep imports for seven folders. The lint rule says which path callers use. It does not say which folders may depend on which other folders.

The aggregate folder graph contains four strongly connected groups. These groups do not prove a source cycle. They identify places where the folder names cannot become independent packages without moving contracts:

- `domain` and `shared`.
- `state` and `persistence` inside a larger application group.
- `scene` and `renderer` inside the camera and transport group.
- `app`, `studios`, `capabilities`, and `panels`.

### Architecture documentation compensates for the tree

`ARCHITECTURE.md:147-211` needs 63 numbered entries to explain file ownership. The detail is useful. The length also shows how much knowledge the path names fail to carry.

The document is pinned to `5f01f74`. Current HEAD is `fa32189`. The document still says that `tests/*.test.ts` cover the system. The current repository has no test tree and no test script.

The repository root contains 23 Markdown files. `docs` contains another 45 files. `.archive` contains 69 files. `README.md` does not classify the root documents by authority or currency.

## How changes spread

Layered systems naturally spread broad features across layers. Folder count alone does not make that spread a defect.

Face media is still useful evidence. A new content kind can affect the content union, the face owner, workbench resolution, commands, panel UI, media import, rasterization, shaders, codecs, validation, and thumbnails. Those owners live in about ten folders.

Authored camera motion has a similar path through the track model, compiler, evaluator, state validation, camera authority, studio wiring, and motion panels.

These examples prove a navigation cost. They do not prove that every change is wide. A panel adjustment or codec repair can remain local.

The next product concepts matter more than the past examples. Nested grids would change the scene model. Hosted synchronization would extend the already porous durability system. Property tracks would enter several existing motion homes. Those changes will test the physical boundaries.

## Lead judgment

### Act on if Cubicell remains active

1. Restore behavioral verification before moving files. A physical refactor across hundreds of imports is not reviewable against build output alone.
2. Freeze new top level folders until the project selects one primary organizing axis.
3. Split `domain` only along real product concepts. The likely concepts are document structure, block form, authoring selection, and playback. A cosmetic folder split would add paths without reducing the barrel.
4. Resolve the `state` and `persistence` ownership line before hosted synchronization work. Either treat them as one durability module or extract shared records and guards into a small contract owned by that module.
5. Publish one document authority map. Keep the current architecture map pinned to HEAD or label it historical.

### Consider when the next product capability is chosen

- Group `scene` and the thin `renderer` delivery layer under one graphics boundary.
- Reduce the `app`, `studios`, `capabilities`, and `panels` clique after deciding whether multiple studios remain a product goal.
- Rename `src/motion` if property timeline work continues. Its current name means camera glide only.
- Replace the universal domain barrel with smaller public contracts when the domain concepts are stable.

### Do not act on from this evidence alone

- Do not reorganize the full tree because it has 26 folders.
- Do not treat aggregate folder cycles as source cycles.
- Do not move all code into feature folders. Engine rules, evaluation, rendering, and persistence need shared owners.
- Do not preserve the current folder tree as a template for a greenfield project.

## A plausible greenfield shape

This tree illustrates one organizing axis. It is not an approved design.

```text
src/
  document/
    block/
    project/
    motion/
  authoring/
    commands/
    selection/
    history/
    ui/
  playback/
    evaluation/
    transport/
  graphics/
    scene/
    camera/
    thumbnails/
  storage/
    records/
    browser/
  app/
  shared/
```

The important property is dependency direction:

1. `document` imports only `shared`.
2. `authoring`, `playback`, `graphics`, and `storage` import `document` through small contracts.
3. `app` imports and composes every outer module.
4. Outer modules do not import `app`.

This shape groups related knowledge while preserving the real invariants already present in Cubicell.

## Verification

The assessment was read only with respect to the repository.

- Repository HEAD was `fa32189908c18ef3457df0702fc030d7177a804f`.
- `git status --short --branch` reported a clean worktree, 22 commits ahead of `origin/main`.
- FMM reported 475 indexed source files and 58,818 lines.
- FMM reported no runtime dependency cycles.
- FMM duplicate clustering found two candidate pairs from 2,944 declarations at threshold 0.90.
- `/Users/alphab/.mdx/TMP/pstack/cubicell-layout-audit/analyze-layout.mjs` generated the final layout report twice with SHA-256 `8fab75a0967491d11a63aa113d483103b27c46ebd8eaa508a2ef4fe5579de319`.
- GPT and Grok produced independent layout, dependency, feature locality, explanation, and critique reports.

Regenerate the physical layout report with:

```sh
node /Users/alphab/.mdx/TMP/pstack/cubicell-layout-audit/analyze-layout.mjs \
  /Users/alphab/Dev/LLM/DEV/helioy/cubicell \
  /Users/alphab/.mdx/TMP/pstack/cubicell-layout-audit/layout-report.json
```

`throughput checkpoint: n/a, read-only investigation`

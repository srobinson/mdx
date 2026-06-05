# Cubicell theory capability audit (lens 2: theory against machine)

Source: `/Users/alphab/Dev/LLM/DEV/helioy/cubicell/THEORY.md` (spinors / SO3 / SU2 transcript).
Machine: cubicell worktree facts + domain/scene symbols. No code run this lens.
Buckets: ALREADY = executable today unused as art; KNOWN-WORK = path known; BLOCKED = model forbids.

ALREADY | flag-legible orientation of a cube | capture-state + keypad 45° views + AxisHintChrome; cube placement.rotation exists on CubeCell
ALREADY | pure rigid orientation without scale/skew (special-orthogonal feel) | MeshBasic unlit parts; createTransformMatrix Euler→Quaternion; no lighting/normals so graphic not shaded 3D
ALREADY | binary dual world (two global "charges") | set-scene-polarity black|white; theme tokens resolve face/edge colors
ALREADY | lattice exclusion: two cubes cannot share one home | OccupancyMap / placeCubesAt coord claim; one cell content per coord in flat cells[]
ALREADY | continuous morph home without cutting the object | snap-cube-home, set-cube-offset, morph numeric-lerp channels; transport plays states
ALREADY | two authored path classes that return to a pose | CameraPosePath cut|linear|orbit; TransitionMode auto|cut (cut works, inspector rarely authors it)
ALREADY | permanent graphic edge that never thins away | edgeCoverageCore min 1 CSS px; MeshBasic edge color
ALREADY | flat unlit "diagram object" not a lit solid | MeshBasicMaterial only; polarity graphic look
ALREADY | quaternion slerp under the hood for camera/part motion | cameraMotion.ts Quaternion slerp; three.js matrix path
ALREADY | assemble many identical-style cubes (boson-like share of appearance) | set-cube-color / inheritCubePartStyle; many cells same face/edge state
ALREADY | reveal buried interior by dropping faces (see through lattice) | face.visible + isFaceBuried skip in createCubeCellInstances
ALREADY | per-part color/opacity/visibility as graphic language | CubeFaceState + CubeEdgeState; set-face-state / set-edge-state
ALREADY | performable transport of geometric states | transport store + morph evaluation + captured camera per state
ALREADY | shape deformation that preserves instancing (square-root-of-bar geometry) | edgeShapeShader instanceShapeSize/Treatment; shape reads clean ~0.4; instancing preserved
ALREADY | opposite-sense congruent camera routes | cameraTrack opposite orbit helper; detents for exact views
ALREADY | selection as targeting not free mesh edit | CubeSelection cube|face|edge; confinement product language

KNOWN-WORK | face-owned silhouette that filleted edges cannot round | faces own silhouette (shared fact); face XY fillet + shape attrs on planes measured maxd~146 in shell-probe; cost: instancing preserved, segmented PlaneGeometry, wire for face shape attrs, no capacity change beyond face vertex count (8×8 segs)
KNOWN-WORK | visible corner fillet where faces meet edges | same face-shape path; edges already deform; must co-author face shape from edge treatment; instancing yes; vertices face segs; wire edge shape already v1 + face attrs
KNOWN-WORK | author cut vs morph as first-class UI dual (two homotopy classes of return) | TransitionMode cut exists without inspector control (score.ts note); panel + command only; instancing N/A; wire none if only UI
KNOWN-WORK | long 360/720 choreography as state path art | cameraTrack orbit path + multi-state sequence; need Animation studio mount / cameraTrackControls live; capacity scene-size only; wire animation score if new channels
KNOWN-WORK | assembly order as "winding" through the lattice | assemblyOrder modes + edit-score; authoring surface exists partially; no new geometry
KNOWN-WORK | edge shape as default graphic vocabulary in presets/demos | treatment/shapeSize already on CubeEdgeState; content/presets only; instancing yes; no wire bump
KNOWN-WORK | polarity-driven performance toggle as live instrument | set-scene-polarity live; bind to transport/VJ tempo; no model change
KNOWN-WORK | teach SO3 loops as camera loops that look continuous across antipodes | orbit path + projection morph; authoring education not engine; no wire

BLOCKED | spinor phase after 360° that looks identical but is not the same state | no phase/half-integer orientation in domain; placement.rotation is Euler SO3; blocking symbol: CubeCell.placement.rotation / Pose has no double-cover phase
BLOCKED | class-1 vs class-2 return as durable identity (must go twice to identity) | states compare by pose content not covering space; blocking: Pose / capture-state equality is SO3, not SU2
BLOCKED | exchange antisymmetry (swap two cubes flips a global sign) | no multiparticle wavefunction; swap is ordinary place/remove; blocking: flat cells[] + no exchange operator
BLOCKED | recursive cell-in-cell (Powers of Ten dive as nested grid content) | shared fact: no recursion; cells flat array; blocking: CellContent kind grid absent; Workbench.library structures only
BLOCKED | media / textbook content inside cells (spinor essay as interior) | shared fact: no media in domain; opaque interior unanswered; blocking: CellContent empty|cube only, assets structure+animation only
BLOCKED | true fermion exclusion of identical full quantum state beyond lattice home | occupancy is spatial only; two cells can share identical face/edge state freely; blocking: no state-hash exclusion, only coord occupancy
BLOCKED | one instanced shell replacing 6 faces + 12 edges with per-face drop | shell-probe: fatal; blocking: createCubeCellInstances face skip + InstancedMesh shared topology
BLOCKED | lit / normal-based "physical" spinor visualization | MeshBasic only; blocking: material model MeshBasicMaterial, no lights
BLOCKED | free mesh flag geometry as separate authored primitive | only cubes faces edges; blocking: domain primitive confinement (PRODUCT only-cubes)
BLOCKED | continuous spacetime field of spinors (not discrete cubes) | lattice of cubes is the confinement; blocking: product model grid+cells not continuum field

## Counts
- ALREADY: 16
- KNOWN-WORK: 8
- BLOCKED: 10

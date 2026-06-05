# Transport Matters reference and process documentation sweep

Assessed against `main` at `af52318d2950f56efce3113fbe2abd73aba72ec4`. The seven source documents were clean in the working tree. Proposed repository reduction: 1,061 of 1,347 lines, about 79 percent.

| Path | Current lines | Disposition | Approximate repository lines after | Proposed repository cut | Live inbound reference |
|---|---:|---|---:|---:|---|
| `docs/NORTHSTAR.md` | 182 | TRIM to ~115 lines | 115 | 67 | `NOW.md`, `docs/CONTROLPLANE.md` |
| `docs/DESIGN.md` | 260 | TRIM to ~50 lines | 50 | 210 | None |
| `docs/WHEEL.md` | 207 | TRIM to ~70 lines | 70 | 137 | `justfile` comment only |
| `docs/PERFORMANCE.md` | 94 | TRIM to ~45 lines | 45 | 49 | `docs/TEST.PERFORMANCE.md` only |
| `docs/TEST.PERFORMANCE.md` | 276 | MERGE into `NOW.md` | ~6 in `NOW.md` | 270 | None |
| `docs/process/WARROOM.md` | 300 | RELOCATE out of this repo | 0 | 300 | None |
| `docs/process/AGENT-PROFILES.md` | 28 | RELOCATE out of this repo | 0 | 28 | None |
| **Total** | **1,347** |  | **~286** | **1,061** |  |

### docs/NORTHSTAR.md (182 lines)
- Disposition: TRIM to ~115 lines
- Evidence: `NOW.md` and `docs/CONTROLPLANE.md` actively use this as the product lens. Its product thesis still matches the capture, controlled home, control plane, and canvas direction. Its `Stepping stones` section describes earlier work such as the www separation and launch extraction, while `NOW.md` now leads with first run and multi launch. The claim that this supersedes `~/.mdx/projects/transport-matters-north-star.md` was noted but that path was not read, as directed.
- Survives: The product paragraph; context and authority thesis; cost thesis; MoA and eval relationship; human and agent identity direction; two altitude UX; durable decision principles; ownership boundaries; the open roster decision. Keep positioning toward operators already spending heavily on agents, without exact price points.
- Cuts: The worked example tree; closed count headings such as `Three goals`; exact feature inventories; the fixed four verb catalogue; current or shipped status claims; exact prices; detailed pane anatomy; the entire `Stepping stones` progress snapshot. Rewrite surviving lists as principles where a future code change could otherwise change the count.

### docs/DESIGN.md (260 lines)
- Disposition: TRIM to ~50 lines
- Evidence: The YAML frontmatter duplicates live values in `www/packages/canvas/src/styles/tokens.css` and `www/packages/canvas/src/theme/types.ts::ACCENTS`, `CORNERS`, `BORDERS`, and `SHADOWS`. The runtime contract lives in `www/packages/canvas/src/theme/types.ts::ThemeSettings` and `www/packages/canvas/src/theme/theme.ts::applyThemeTokens`. Current component claims were checked against `CommandCenter`, `ArkExchangeViewer`, `IconToggle`, `CanvasTooltip`, `AmbientBackdrop`, and `sceneRegistry`. These sites prove that the inventory is current today and that ordinary component changes can invalidate it tomorrow.
- Survives: `Instrumented Workspace`; dense, dark, mono, compact, restrained; Canvas tokens own appearance while Ark owns interaction semantics; token first and accent rarity; legibility over atmosphere; Inspector and Canvas remain separate products; verify theme behavior at the rendered seam.
- Cuts: All YAML token data; every hex, pixel, spacing, radius, shadow, and typography value; the palette catalogue; the current Ark adoption inventory; component by component specifications; startup theme facts; repeated do and do not catalogues. Code remains the sole owner of values and current component usage.

### docs/WHEEL.md (207 lines)
- Disposition: TRIM to ~70 lines
- Evidence: The live mechanisms are owned by `justfile::verify-wheel`, `.github/workflows/ci.yml::package`, `linux-wheel-spawn`, and `standalone`, `packages/gateway/scripts/build.mjs::POSIX_PREBUILDS`, `api/scripts/assert_gateway_wheel.py`, `desktop/electron-builder.yml`, and `scripts/release.sh`. The platform reasoning remains useful. The detailed packaging track has drifted into planning: `WHEEL.md` calls embedded Postgres the next blocker and recommends pgembed, while current `NOW.md` defines the first run database choices as Docker, a supplied connection string, or managed service.
- Survives: The wheel as the inner artifact and the application as the outer artifact; why Linux runtime proof belongs in CI; why the Darwin PTY last mile needs a Mac; the cost and risk reason against permanent macOS CI today; the trigger for adding macOS or Windows runners; Windows reaping as a distinct design concern.
- Cuts: The shipped file inventory; exact prebuild matrix; job and command catalogue; build diagram details already expressed by configuration; current CI guarantees; local step by step instructions; completed DMG history; the pgembed and PGLite decision snapshot; update staging; release commands. Link to the owning recipe or workflow when an operator needs mechanics.

### docs/PERFORMANCE.md (94 lines)
- Disposition: TRIM to ~45 lines
- Evidence: The document is genuinely a future lever parking lot. There is no `@xterm/addon-webgl` dependency or terminal wheel zoom implementation at this head, and `www/packages/canvas/src/viewers/terminal/terminalSession.ts` still sets the base terminal rendering configuration. The launch latency reasoning matches the remote provider architecture. Its stated current focus is stale against `NOW.md`, and its exact WebGL cap, wheel threshold, zoom range, and slice references read as an implementation specification.
- Survives: Separate launch latency from terminal painting; profile a real launch before choosing a lever; prompt cache observability, warm process ideas, and connection reuse as unscheduled candidates; GPU rendering as a many pane smoothness option; renderer independence at the terminal byte boundary; fall back safely if GPU rendering is eventually adopted.
- Cuts: The current focus sentence; exact context caps; exact wheel deltas and zoom bounds; settled resize prescription; slice numbers; implementation shaped wording. Retain questions and reasons, not an unapproved design.

### docs/TEST.PERFORMANCE.md (276 lines)
- Disposition: MERGE into `NOW.md`
- Evidence: No local or remote `docs/test-performance` branch remains. Baseline `3ae57012` is an ancestor of `main`, and the work landed in `7807e053`, PR #313. Current owners are `justfile::test`, `justfile::test-affected`, `api/justfile::test`, and `scripts/test-affected.sh`. The document's inventory already drifted from 335 API test files to 368. `api/pyproject.toml` still has no unit, integration, and end to end marker taxonomy, so one open direction remains real.
- Survives: About six lines in `NOW.md`: local unit feedback should remain under 30 seconds; preserve slow regression coverage in the full gate; markers and dedicated unit, integration, and end to end recipes are the open mechanism if this work is still wanted.
- Cuts: The branch header; shipped checklist; command catalogue; suite inventories; counts; timings; historical diagnosis; timing model; implementation checklist; remeasurement log; appendix. Git history and PR #313 preserve the completed work, while recipes preserve current operation.

### docs/process/WARROOM.md (300 lines)
- Disposition: RELOCATE out of this repo
- Evidence: The file calls itself project agnostic. The active reusable owner already exists at `/Users/alphab/Dev/LLM/DEV/helioy/helioy-plugins/plugins/helioy-bus/skills/warroom/SKILL.md`, whose `Role`, `The Spine`, `Runtimes`, `Message Protocol`, and `Modes` sections cover the same process and drive the actual tool. The repository copy then adds volatile adoption data: exact models, seat counts, CI job counts, branch names, worktree commands, and incident history. Nothing in the live tree links to it.
- Survives: In the helioy bus warroom skill, keep the context budget rationale, scout before build, independent review, real product proof, review weight by blast radius, bounded artifacts, and concise reply protocol. Carry any missing proof principle into that owner once.
- Cuts: Delete the repository copy after relocation. Do not carry its Transport Matters roster, model calibration, exact CI surface, branch workflow, worktree recipe, or incident narratives into the generic owner. Current project gates already live in `justfile`, workflows, and repository instructions.

### docs/process/AGENT-PROFILES.md (28 lines)
- Disposition: RELOCATE out of this repo
- Evidence: The file names no Transport Matters product symbol and describes Directors and Orchestrators generally. It has zero inbound links. The helioy bus warroom skill already owns model selection in `Runtimes` and review rationale in `Why We Spend Tokens On Review`; its current runtime names already differ from this file's Grok 4.5 snapshot. Keeping both guarantees drift.
- Survives: Merge only evidence backed, cross project selection rules into the plugin owner: mix model families for consequential review, mutation check tests, and treat a green gate as insufficient evidence for a real user story.
- Cuts: Delete the repository file after the small merge. Drop the per model scorecard, unavailable model list, and claims derived from a small sample.

## Zero inbound links

Four documents have no live inbound reference anywhere in the tracked tree after excluding archives and captured test fixtures:

| Path | Fix |
|---|---|
| `docs/DESIGN.md` | Link the trimmed principles from `www/packages/canvas/CLAUDE.md`. |
| `docs/TEST.PERFORMANCE.md` | Merge the live marker into `NOW.md`, then delete the source. A new link would preserve a finished work record. |
| `docs/process/WARROOM.md` | Relocate the durable material to the helioy bus warroom skill, then delete the repository copy. |
| `docs/process/AGENT-PROFILES.md` | Merge the durable observations into the helioy bus warroom skill, then delete the repository copy. |

Two additional reachability notes matter after the sweep. `docs/WHEEL.md` has a plain `justfile` comment as its only inbound reference, so the trimmed rationale should gain one human facing link from packaging or release documentation. `docs/PERFORMANCE.md` is linked only by `docs/TEST.PERFORMANCE.md`; once that source leaves, link the trimmed parking lot from `NOW.md` if the levers remain worth keeping.

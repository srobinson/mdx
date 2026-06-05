# Scout A — docs placement and reference inventory

**Repo:** `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters` @ `main`  
**Mode:** read only (no edits, no moves, no git ops)  
**Date:** 2026-08-02  
**Topic:** `tm-docs-scout`

## Verdict on proposed layout

**Mostly sound.** The three-bucket split (living references → `docs/`, delivery plans → `docs/plans/`, process → `docs/process/`) matches how the files already cite each other, and root keep-list matches the agent-grounding stack.

**Challenges / fix-before-move:**

1. **`.gitignore` vs `PROJECT.md`.** Root rules currently ignore `PROJECT.md` globally and only un-ignore `/PROJECT.md`. After a move to `docs/PROJECT.md` (any final name still matching `PROJECT.md`), git will ignore the new path unless the un-ignore is updated (e.g. `!/docs/PROJECT.md` or drop the ignore once the file lives under `docs/`). See §2.
2. **Cross-depth relative links break** between `docs/` and `docs/plans/` (today everything is sibling `./`). Rewrite is mandatory for markdown links; bare prose docnames in code are non-load-bearing (see §1 code).
3. **`PERFORMANCE.md` → `NOW.md` and `TEST.PERFORMANCE.md` → `scripts/test-affected.sh`** become `../` paths after the move.
4. **`WARROOM.md` prose** claims it is “the owned process doc at the repo root” — content update required, not just path.
5. **`docs/superpowers/**` is gitignored** (`docs/superpowers/` in `.gitignore`). It still contains local plans/specs that cite `DESIGN.md`; update if those copies are used, but they are outside the tracked rewrite scope.
6. **Root `.archive/` orphan:** `VERIFIED-SUBMIT-PLAN.v1.md` has no live parent at root. Decide keep-at-root-archive vs delete vs attach to a future plan; do not invent a live file for it.
7. **Rename `AGENTS.PROFILES.md` → `AGENT-PROFILES.md` is free:** zero inbound references in rewrite scope. Rename reduces adjacency confusion with the `AGENTS.md` → `TLDR.md` symlink; good.
8. **`TEST.PERFORMANCE.md` name** (dot in basename) is fine under `docs/`; no tooling special-cases it. Optional rename later is unrelated to this move.

**Root keep list confirmed present and correct:** `TLDR.md`, `README.md`, `NOW.md`, `LESSONS.md`, `QUICKSTART.md`, plus symlinks `AGENTS.md` → `TLDR.md` and `CLAUDE.md` → `TLDR.md` (same inode on this case-insensitive volume for `Agents.md`/`AGENTS.md`).

**Already under `docs/` (not in move list):** `docs/ARCHITECTURE.md`, `docs/CHANNELS.md`, `docs/.archive/ARCHITECTURE.v1.md`.

---

## 1. REFERENCE MAP

Convention for “must become”:

- Target paths assume proposed layout.
- `PROJECT.md` final name pending Scout B; written here as `docs/PROJECT.md` with a pending marker.
- **Markdown links** (`[text](./FILE.md)`): must rewrite or they break navigation.
- **Backtick / prose docnames** in root docs: should rewrite for humans.
- **Code comments / docstrings** that name `FOO.md` only: **not load-bearing** (no `open()` / packaging embed). Optional hygiene to new path; listed as `optional-prose`.
- **Self path** = the moving file’s own outbound links that change depth.

Exclude from rewrite: `.archive/`, `TMP/`, `NOTES/`, `api/tests/fixtures/**` (counts in §1.2 / §2).  
`.nancy/` is gitignored (not in rewrite scope); noted under risks.

### 1.1 By moving file

#### `HARNESS-COMPATIBILITY.md` → `docs/HARNESS-COMPATIBILITY.md`

| Source | Exact text / link | Must become | Kind |
|--------|-------------------|-------------|------|
| `COMPATIBILITY-PUBLISHING.md` | `[HARNESS-COMPATIBILITY.md](./HARNESS-COMPATIBILITY.md)` | `./HARNESS-COMPATIBILITY.md` (co-move to `docs/`; unchanged) | md-link |
| `LAUNCH-CONTRACT.md` | `[HARNESS-COMPATIBILITY.md](./HARNESS-COMPATIBILITY.md)` | unchanged (co-move `docs/`) | md-link |
| `RUNTIME-SURFACING-PLAN.md` | `[HARNESS-COMPATIBILITY.md](./HARNESS-COMPATIBILITY.md)` (2×) | `../HARNESS-COMPATIBILITY.md` | md-link |
| `RUNTIME-SURFACING-S2-PLAN.md` | `[HARNESS-COMPATIBILITY.md](./HARNESS-COMPATIBILITY.md)` | `../HARNESS-COMPATIBILITY.md` | md-link |
| `RUNTIME-SURFACING-S2-PLAN.md` | prose `HARNESS-COMPATIBILITY.md` (2× amend steps) | `docs/HARNESS-COMPATIBILITY.md` or `../HARNESS-COMPATIBILITY.md` relative to plan | prose |
| `api/src/transport_matters/exceptions.py` | docstring `HARNESS-COMPATIBILITY.md` (2×) | optional `docs/HARNESS-COMPATIBILITY.md` | optional-prose |
| `api/src/transport_matters/harnesses/compatibility.py` | module doc + comment | optional path | optional-prose |
| `api/src/transport_matters/harnesses/compatibility_facts.py` | module doc | optional path | optional-prose |
| `api/src/transport_matters/harnesses/compatibility_store.py` | comment | optional path | optional-prose |
| `api/src/transport_matters/harnesses/connections.py` | module doc | optional path | optional-prose |
| `api/src/transport_matters/harnesses/probes/__init__.py` | comment | optional path | optional-prose |
| `api/src/transport_matters/index/adapters/base.py` | comment | optional path | optional-prose |
| `api/src/transport_matters/index/adapters/__init__.py` | comments (2×) | optional path | optional-prose |

**Outbound from this file (self after move):**

| Link | Today | After |
|------|-------|-------|
| `[LAUNCH-CONTRACT.md](./LAUNCH-CONTRACT.md)` | sibling | unchanged (both `docs/`) |
| `[RUNTIME-SURFACING-PLAN.md](./RUNTIME-SURFACING-PLAN.md)` | sibling | `./plans/RUNTIME-SURFACING-PLAN.md` |

Archive hits: **24**. TMP/NOTES hits: **20** (out of rewrite scope).

---

#### `COMPATIBILITY-PUBLISHING.md` → `docs/COMPATIBILITY-PUBLISHING.md`

| Source | Exact text / link | Must become | Kind |
|--------|-------------------|-------------|------|
| `RUNTIME-SURFACING-PLAN.md` | `[COMPATIBILITY-PUBLISHING.md](./COMPATIBILITY-PUBLISHING.md)` | `../COMPATIBILITY-PUBLISHING.md` | md-link |
| `RUNTIME-SURFACING-S2-PLAN.md` | `[COMPATIBILITY-PUBLISHING.md](./COMPATIBILITY-PUBLISHING.md)` | `../COMPATIBILITY-PUBLISHING.md` | md-link |
| `RUNTIME-SURFACING-S2-PLAN.md` | prose `COMPATIBILITY-PUBLISHING` (embed step) | path-qualified prose | prose |
| `api/src/transport_matters/harnesses/certification.py` | module doc `COMPATIBILITY-PUBLISHING.md` | optional path | optional-prose |

**Outbound:** `[HARNESS-COMPATIBILITY.md](./HARNESS-COMPATIBILITY.md)` → unchanged (co-move).

Archive: **11**. TMP/NOTES: **1**.

---

#### `LAUNCH-CONTRACT.md` → `docs/LAUNCH-CONTRACT.md`

| Source | Exact text / link | Must become | Kind |
|--------|-------------------|-------------|------|
| `HARNESS-COMPATIBILITY.md` | `[LAUNCH-CONTRACT.md](./LAUNCH-CONTRACT.md)` | unchanged (co-move) | md-link |
| `NOW.md` | prose `` `LAUNCH-CONTRACT.md` `` (3×: near candidate_key, #345 note, wrap authority) | `` `docs/LAUNCH-CONTRACT.md` `` | prose |
| `RUNTIME-SURFACING-PLAN.md` | `[LAUNCH-CONTRACT.md](./LAUNCH-CONTRACT.md)` (2×) | `../LAUNCH-CONTRACT.md` | md-link |
| `RUNTIME-SURFACING-S2-PLAN.md` | `[LAUNCH-CONTRACT.md](./LAUNCH-CONTRACT.md)` | `../LAUNCH-CONTRACT.md` | md-link |
| `api/src/transport_matters/harnesses/resolver.py` | module doc + docstring | optional path | optional-prose |

**Outbound:**

| Link | After |
|------|-------|
| `./HARNESS-COMPATIBILITY.md` | unchanged |
| `./RUN-IDENTITY.md` | unchanged |
| `./RUNTIME-SURFACING-PLAN.md` | `./plans/RUNTIME-SURFACING-PLAN.md` |

Archive: **21**. TMP/NOTES: **6**.

---

#### `RUN-IDENTITY.md` → `docs/RUN-IDENTITY.md`

| Source | Exact text / link | Must become | Kind |
|--------|-------------------|-------------|------|
| `CONTROLPLANE.md` | `[RUN-IDENTITY](./RUN-IDENTITY.md)` | unchanged (co-move) | md-link |
| `LAUNCH-CONTRACT.md` | `[RUN-IDENTITY.md](./RUN-IDENTITY.md)` | unchanged | md-link |
| `RUNTIME-SURFACING-PLAN.md` | `[RUN-IDENTITY](./RUN-IDENTITY.md)` (2×) | `../RUN-IDENTITY.md` | md-link |
| `RUNTIME-SURFACING-S1-PLAN.md` | `[RUN-IDENTITY.md](./RUN-IDENTITY.md)` | `../RUN-IDENTITY.md` | md-link |

**Outbound:** external NASA URL only (no local path change).

Archive: **20**. TMP/NOTES: **0**.

---

#### `CONTROLPLANE.md` → `docs/CONTROLPLANE.md`

| Source | Exact text / link | Must become | Kind |
|--------|-------------------|-------------|------|
| `CONTROLPLANE-OBSERVATION-PLAN.md` | prose `` `CONTROLPLANE.md` `` (2×) | `` `../CONTROLPLANE.md` `` or `` `docs/CONTROLPLANE.md` `` | prose |

**Outbound:**

| Link | After |
|------|-------|
| `./NORTHSTAR.md` | unchanged (co-move) |
| `./RUN-IDENTITY.md` | unchanged |
| `./CONTROLPLANE-OBSERVATION-PLAN.md` | `./plans/CONTROLPLANE-OBSERVATION-PLAN.md` |

Archive: **1** (plus dated snapshot; see §4). TMP/NOTES: **0**.

---

#### `NORTHSTAR.md` → `docs/NORTHSTAR.md`

| Source | Exact text / link | Must become | Kind |
|--------|-------------------|-------------|------|
| `NOW.md` | `[NORTHSTAR.md](./NORTHSTAR.md)` | `[NORTHSTAR.md](./docs/NORTHSTAR.md)` | md-link |
| `CONTROLPLANE.md` | `[NORTHSTAR](./NORTHSTAR.md)` | unchanged (co-move) | md-link |

**Fixtures:** 9 hits across `api/tests/fixtures/claude_messages/turn-{0,1,2}/request.ir.json` (embedded NOW.md text, Task description, absolute `file_path` to root `NORTHSTAR.md`). **Do not rewrite** (see §2 pattern).

Archive: **1**. TMP/NOTES: **0**.

---

#### `DESIGN.md` → `docs/DESIGN.md`

| Source | Exact text / link | Must become | Kind |
|--------|-------------------|-------------|------|
| `docs/superpowers/plans/2026-07-05-canvas-icon-system.md` | multiple `` `DESIGN.md` `` + git add path | `docs/DESIGN.md` if local copy maintained | **gitignored** local |
| `docs/superpowers/specs/2026-07-05-canvas-icon-system-design.md` | prose `DESIGN.md` / `` `DESIGN.md` `` | same | **gitignored** local |

**No tracked inbound markdown links.** No code opens this file. Move is reference-clean for git-tracked tree; only local superpowers copies mention it.

Archive: **0**. TMP/NOTES: **0**.

---

#### `WHEEL.md` → `docs/WHEEL.md`

| Source | Exact text / link | Must become | Kind |
|--------|-------------------|-------------|------|
| `justfile` / `Justfile` (same inode) | comment `See WHEEL.md.` | `See docs/WHEEL.md.` | prose |

No markdown link form. No packaging embed of the file itself.

Archive: **0**. TMP/NOTES: **0**.

---

#### `PERFORMANCE.md` → `docs/PERFORMANCE.md`

| Source | Exact text / link | Must become | Kind |
|--------|-------------------|-------------|------|
| `TEST.PERFORMANCE.md` | `[PERFORMANCE.md](./PERFORMANCE.md)` | unchanged (co-move) | md-link |

**Outbound:** `[NOW.md](./NOW.md)` → `[NOW.md](../NOW.md)`.

Archive: **0**. TMP/NOTES: **0**.

---

#### `TEST.PERFORMANCE.md` → `docs/TEST.PERFORMANCE.md`

No inbound references in rewrite scope.

**Outbound:**

| Link | After |
|------|-------|
| `./PERFORMANCE.md` | unchanged |
| `./scripts/test-affected.sh` | `../scripts/test-affected.sh` |

Archive: **0**. TMP/NOTES: **0**.

---

#### `RUNTIME-SURFACING-PLAN.md` → `docs/plans/RUNTIME-SURFACING-PLAN.md`

| Source | Exact text / link | Must become | Kind |
|--------|-------------------|-------------|------|
| `HARNESS-COMPATIBILITY.md` | `[RUNTIME-SURFACING-PLAN.md](./RUNTIME-SURFACING-PLAN.md)` | `./plans/RUNTIME-SURFACING-PLAN.md` | md-link |
| `LAUNCH-CONTRACT.md` | `[RUNTIME-SURFACING-PLAN.md](./RUNTIME-SURFACING-PLAN.md)` | `./plans/RUNTIME-SURFACING-PLAN.md` | md-link |
| `RUNTIME-SURFACING-S1-PLAN.md` | `[RUNTIME-SURFACING-PLAN.md](./RUNTIME-SURFACING-PLAN.md)` | unchanged (co-move plans/) | md-link |
| `RUNTIME-SURFACING-S2-PLAN.md` | `[RUNTIME-SURFACING-PLAN.md](./RUNTIME-SURFACING-PLAN.md)` | unchanged | md-link |

**Outbound (from plan after move):**

| Link | After |
|------|-------|
| `./LAUNCH-CONTRACT.md` | `../LAUNCH-CONTRACT.md` |
| `./HARNESS-COMPATIBILITY.md` | `../HARNESS-COMPATIBILITY.md` |
| `./COMPATIBILITY-PUBLISHING.md` | `../COMPATIBILITY-PUBLISHING.md` |
| `./RUN-IDENTITY.md` | `../RUN-IDENTITY.md` |
| `./CONTROLPLANE-OBSERVATION-PLAN.md` | unchanged (co-move plans/) |
| `./RUNTIME-SURFACING-S1-PLAN.md` | unchanged |
| `./RUNTIME-SURFACING-S2-PLAN.md` | unchanged |

Archive: **13**. TMP/NOTES: **8**.

---

#### `RUNTIME-SURFACING-S1-PLAN.md` → `docs/plans/RUNTIME-SURFACING-S1-PLAN.md`

| Source | Exact text / link | Must become | Kind |
|--------|-------------------|-------------|------|
| `RUNTIME-SURFACING-PLAN.md` | `[RUNTIME-SURFACING-S1-PLAN.md](./RUNTIME-SURFACING-S1-PLAN.md)` | unchanged | md-link |

**Outbound:** parent plan unchanged; `./RUN-IDENTITY.md` → `../RUN-IDENTITY.md`.

Archive: **7**. TMP/NOTES: **0**.

---

#### `RUNTIME-SURFACING-S2-PLAN.md` → `docs/plans/RUNTIME-SURFACING-S2-PLAN.md`

| Source | Exact text / link | Must become | Kind |
|--------|-------------------|-------------|------|
| `RUNTIME-SURFACING-PLAN.md` | `[RUNTIME-SURFACING-S2-PLAN.md](./RUNTIME-SURFACING-S2-PLAN.md)` | unchanged | md-link |
| `api/src/transport_matters/capture_rpc.py` | comment `RUNTIME-SURFACING-S2-PLAN.md` | optional path | optional-prose |
| `api/src/transport_matters/test_capture_rpc_drift.py` | module doc | optional path | optional-prose |
| `www/packages/canvas/src/firstrun/harnessCards.ts` | block comment `RUNTIME-SURFACING-S2-PLAN` | optional path | optional-prose |

**Outbound:** parent plan unchanged; harness/launch/compat links → `../…`.

Archive: **0** live-name hits in `.archive/` body text; versioned files exist as `RUNTIME-SURFACING-S2-PLAN.v1–v3.md` (see §4). TMP/NOTES: **13**.

---

#### `CONTROLPLANE-OBSERVATION-PLAN.md` → `docs/plans/CONTROLPLANE-OBSERVATION-PLAN.md`

| Source | Exact text / link | Must become | Kind |
|--------|-------------------|-------------|------|
| `CONTROLPLANE.md` | `[CONTROLPLANE-OBSERVATION-PLAN.md](./CONTROLPLANE-OBSERVATION-PLAN.md)` | `./plans/CONTROLPLANE-OBSERVATION-PLAN.md` | md-link |
| `RUNTIME-SURFACING-PLAN.md` | `[CONTROLPLANE-OBSERVATION-PLAN.md](./CONTROLPLANE-OBSERVATION-PLAN.md)` | unchanged (co-move plans/) | md-link |

No markdown outbound links to other repo files (prose only to `CONTROLPLANE.md`).

Archive: **7**. TMP/NOTES: **0**.

---

#### `WARROOM.md` → `docs/process/WARROOM.md`

| Source | Exact text / link | Must become | Kind |
|--------|-------------------|-------------|------|
| `WARROOM.md` (self) | prose: “This `WARROOM.md` is the owned process doc at the repo root.” | “at `docs/process/WARROOM.md`” (or equivalent) | prose |

No inbound links in rewrite scope.

Archive: **2** (versioned snapshots v1–v2). TMP/NOTES: **0**.

---

#### `AGENTS.PROFILES.md` → `docs/process/AGENT-PROFILES.md` (rename)

**Zero inbound references** in rewrite scope (only the file’s own H1 “Agent Profiles”, and an unrelated phrase “agent profiles” in `HARNESS-COMPATIBILITY.md` about product concepts, not this filename).

Rename + move is reference-clean.

Archive: **0**. TMP/NOTES: **0**.

---

#### `PROJECT.md` → `docs/<name pending Scout B>` (assumed `docs/PROJECT.md` below)

| Source | Exact text / link | Must become | Kind |
|--------|-------------------|-------------|------|
| `TLDR.md` | `[PROJECT.md](./PROJECT.md)` | `[PROJECT.md](./docs/PROJECT.md)` (or Scout B name) | md-link |
| `AGENTS.md` / `CLAUDE.md` | same link (symlinks → `TLDR.md`; one content rewrite) | same as TLDR | md-link via TLDR |
| `README.md` | `[PROJECT.md](./PROJECT.md)` | `./docs/PROJECT.md` (or Scout B name) | md-link |
| `.gitignore` | `PROJECT.md` + `!/PROJECT.md` | rewrite rules for new path (see §2) | config |

`.nancy/tasks/*/INIT_PROMPT.md` contains “Look for a docs/PROJECT.md” — **gitignored**, out of rewrite scope; already anticipates a `docs/` location.

Archive: **0**. TMP/NOTES: **6**. Fixtures: **3 files** (see §2).

---

### 1.2 Counts outside rewrite scope

| Zone | Role | Approximate hit volume |
|------|------|------------------------|
| `.archive/` | historical snapshots + cross-mentions inside them | HARNESS 24, LAUNCH 21, RUN-IDENTITY 20, RUNTIME-SURFACING-PLAN 13, COMPAT 11, CONTROLPLANE-OBS 7, S1 7, CONTROLPLANE 1, NORTHSTAR 1, WARROOM 2, others 0 body hits |
| `TMP/` + `NOTES/` | local notes | HARNESS 20, S2 plan 13, RUNTIME plan 8, LAUNCH 6, PROJECT 6, COMPAT 1, rest 0 |
| `api/tests/fixtures/claude_messages/` | captured wire payloads | NORTHSTAR 9, PROJECT 3 files × embedded TLDR text |

Do **not** bulk-rewrite `.archive/` (history). Do **not** touch fixtures (see §2).

### 1.3 Rewrite-scope summary tally

| Class | Approx count |
|-------|--------------|
| **Mandatory markdown-link / path rewrites** (unique link sites, including self-outbound that change depth) | **~40** |
| **Root/prose path updates** (`NOW.md` LAUNCH×3, `justfile` WHEEL, `WARROOM` root claim, `.gitignore`) | **~7** |
| **Optional code-comment hygiene** | **~18** |
| **Gitignored local superpowers DESIGN mentions** | **9** |
| **Zero-ref movers** (`TEST.PERFORMANCE.md` inbound, `AGENTS.PROFILES.md` inbound) | safe |

---

## 2. TWO SPECIFIC ODDITIES — `PROJECT.md`

### 2.1 `api/tests/fixtures/claude_messages/turn-{0,1,2}/request.ir.json`

**Verdict: incidental captured-payload text. Do NOT rewrite.**

Evidence:

- Each turn’s `request.ir.json` embeds a `# claudeMd` / system-reminder block that is a snapshot of agent grounding (TLDR-equivalent), ending with `See [PROJECT.md](./PROJECT.md) for more.`
- That is frozen wire/transcript IR used as regression fixtures, not live documentation.
- No non-fixture test under `api/tests` asserts on the string `PROJECT.md` or requires the file to exist at a path for those fixtures to parse.
- Same class as NORTHSTAR hits in the same fixtures (embedded NOW.md body + absolute `file_path` to then-root `NORTHSTAR.md`).

Touching them would churn large golden IR without product benefit and would misrepresent historical captures.

### 2.2 `.gitignore`

**Verdict: real configuration that MUST be updated when PROJECT moves (or is renamed).**

Current rules:

```
# Local docs
LESSONS.md
PROJECT.md
TLDR.md
# ...but the root agent-grounding stack is committed (layered-tldr-agent-grounding)
!/PROJECT.md
!/TLDR.md
```

Interpretation:

- `PROJECT.md` (unanchored) ignores **any** path segment `PROJECT.md` in the tree.
- `!/PROJECT.md` re-includes **only the repo-root** file so the committed grounding stack works.
- `LESSONS.md` stays local-only (no un-ignore) — consistent with keep-at-root but uncommitted.

After move to e.g. `docs/PROJECT.md`:

- Without a new un-ignore, **`docs/PROJECT.md` stays ignored** and will not appear in `git status` / commits (silent drop — high severity).
- Root `!/PROJECT.md` becomes a no-op once the root file is gone.

**Required rewrite (shape, not final patch):**

- Remove root-only un-ignore or replace with `!/docs/<final-name>.md`.
- Prefer anchoring ignores (`/PROJECT.md` only if anything remains at root) so a future `docs/PROJECT.md` is not blanket-ignored.
- Coordinate final filename with Scout B before landing the gitignore edit.

---

## 3. SYMLINK SAFETY

| Item | Status |
|------|--------|
| `CLAUDE.md` → `TLDR.md` | Confirm; move set does **not** include `TLDR.md`, `CLAUDE.md`, or `AGENTS.md`. Safe. |
| `AGENTS.md` → `TLDR.md` | Same. Safe. |
| Content link inside TLDR | `[PROJECT.md](./PROJECT.md)` must be rewritten when PROJECT moves (symlink readers see updated TLDR). |
| `AGENTS.PROFILES.md` beside `AGENTS.md` | Real file, not a symlink. Moving/renaming it does not disturb `AGENTS.md`. |

### `AGENTS*` tooling globs

Searched rewrite-scope tree for globs / loaders of `AGENTS*`:

| Hit | Assessment |
|-----|------------|
| `packages/CLAUDE.md` → `@./AGENTS.md` | Package-local `packages/AGENTS.md`, unrelated to root `AGENTS.PROFILES.md`. |
| `api/.../cli/run_context.py` writes/reads runtime-home `AGENTS.md` | Managed runtime home artifact, not repo root profiles doc. |
| Conversation projection prefix `"# AGENTS.md instructions for "` | Runtime content marker. |
| No `AGENTS*` glob in `justfile`, `pyproject.toml`, `.github/workflows`, packaging | **None found.** |

**Conclusion:** Renaming `AGENTS.PROFILES.md` → `AGENT-PROFILES.md` and moving under `docs/process/` does not break symlink resolution or any discovered `AGENTS*` consumer. The rename is mildly **helpful** (stops humans/tools from conflating profiles doc with the TLDR symlink).

---

## 4. ARCHIVE CONVENTION

Snapshot skill rule (from `~/.agents/skills/snapshot/SKILL.md`): archive is **`<parent-dir>/.archive/`**, sibling of the canonical file. One archive directory per parent; all docs in that parent share it. Version pattern: `<basename>.v<N>.<ext>` (or dated variants already in tree).

`docs/` **already** has `docs/.archive/ARCHITECTURE.v1.md` — the correct pattern for anything landing in `docs/`.

### Recommendation

| New parent of canonical | Archive home | Action for existing root `.archive/` snapshots |
|-------------------------|--------------|-----------------------------------------------|
| `docs/` | `docs/.archive/` | Move matching snapshots here |
| `docs/plans/` | `docs/plans/.archive/` (create) | Move plan snapshots here |
| `docs/process/` | `docs/process/.archive/` (create) | Move WARROOM snapshots here |
| Orphans / retired | keep at root `.archive/` or delete intentionally | Do not invent parents |

### Snapshot → parent map (root `.archive/` today, 26 files)

| Snapshots | Live parent (today) | After move, archive should live at |
|-----------|---------------------|-------------------------------------|
| `HARNESS-COMPATIBILITY.v1.md` … `v6.md` | `HARNESS-COMPATIBILITY.md` | `docs/.archive/` |
| `LAUNCH-CONTRACT.v1.md` … `v3.md` | `LAUNCH-CONTRACT.md` | `docs/.archive/` |
| `CONTROLPLANE.2026-07-11.md` | `CONTROLPLANE.md` (dated, not `vN`) | `docs/.archive/` |
| `RUNTIME-SURFACING-PLAN.v1.md` … `v10.md` | `RUNTIME-SURFACING-PLAN.md` | `docs/plans/.archive/` |
| `RUNTIME-SURFACING-S2-PLAN.v1.md` … `v3.md` | `RUNTIME-SURFACING-S2-PLAN.md` | `docs/plans/.archive/` |
| `WARROOM.v1.md`, `WARROOM.v2.md` | `WARROOM.md` | `docs/process/.archive/` |
| `VERIFIED-SUBMIT-PLAN.v1.md` | **no live parent** | leave in root `.archive/` or retire; do not move under `docs/plans/` without a live file |

**No root archives** for: COMPATIBILITY-PUBLISHING, RUN-IDENTITY, NORTHSTAR, DESIGN, WHEEL, PERFORMANCE, TEST.PERFORMANCE, RUNTIME-SURFACING-S1-PLAN, CONTROLPLANE-OBSERVATION-PLAN, AGENTS.PROFILES, PROJECT. Future snapshots for those should be created **in the new parent’s `.archive/`** on first snapshot after the move.

**Do not** keep versioning new edits into root `.archive/` after canons leave root — that would break the sibling convention.

---

## 5. PACKAGING CHECK

| Surface | Finding |
|---------|---------|
| `api/pyproject.toml` `[tool.hatch.build.targets.wheel]` | Packages `src/transport_matters` only. Artifacts: `www/**`, `canvas/**`, `gateway/**`, `settings.example.toml`, `channel-specs.json`, `compatibility_releases_v1.json`, `migrations/**`. **None of the moving markdown files.** |
| `force-include` | `migrations` only. |
| sdist `only-include` | `src/transport_matters`, `migrations`, `alembic.ini`, `tests`, `README.md`, `LICENSE` — api-tree `README.md`, not root design docs. |
| `project.readme` | `"README.md"` relative to `api/` packaging root. |
| Wheel-embedded JSON | `compatibility_releases_v1.json` is data implementing the publishing contract; **not** `COMPATIBILITY-PUBLISHING.md`. |
| Code `open()` / `read_text` of moving docs | **None.** All code hits are comments/docstrings naming the doc. |

**Conclusion:** Moving these markdown files **does not change what ships in the wheel or sdist.** No packaging config rewrite required for correctness. Optional comment hygiene only.

---

## 6. RISK LIST

| Risk | Severity | Notes |
|------|----------|-------|
| `.gitignore` swallows `docs/PROJECT.md` after move | **High** | See §2.2; silent non-commit. |
| Broken relative links docs ↔ plans | **High** | Every `./PLAN` from `docs/` and `./CONTRACT` from `plans/` must flip to `./plans/…` or `../…`. |
| `PERFORMANCE.md` → `NOW.md` and `TEST.PERFORMANCE.md` → `scripts/…` | **Medium** | Easy to miss; only one link each. |
| `NOW.md` prose still says bare `LAUNCH-CONTRACT.md` | **Low–Med** | Not a link but operator-facing current-focus doc. |
| `justfile` still says `WHEEL.md` | **Low** | Comment only; discoverability. |
| `WARROOM.md` “repo root” claim | **Low** | Stale process wording. |
| Fixtures / golden IR rewritten by mistake | **High if done** | Must **not** touch `api/tests/fixtures/**`. |
| Bulk-edit `.archive/` history | **Med if done** | Leave historical bodies; only **relocate files** to new sibling archives. |
| `docs/superpowers/**` stale DESIGN paths | **Low** | Gitignored; local agent plans only. |
| Case-insensitive FS (`AGENTS.md`/`Agents.md`, `justfile`/`Justfile`) | **Info** | Same inodes; no extra files to move. |
| Docs site / MkDocs / Docusaurus | **None** | No `mkdocs.yml` / docs generator config. |
| Link checkers / lychee / markdown-link-check in CI | **None found** | No automated link CI to update. |
| Pre-commit md hooks | **None found** | No `.pre-commit-config.yaml` hits for link check. |
| External `github.com/.../blob/.../*.md` URLs in repo | **None found** | No in-repo absolute blob URLs to update; external bookmarks outside repo are unknowable. |
| `.github/workflows` | **None** for these docs | CI mentions wheels, not these filenames. |
| `api/CLAUDE.md`, `packages/CLAUDE.md` | **None** for movers | packages points at local AGENTS.md. |
| Runtime `AGENTS.md` seeding | **None** | Unrelated to `AGENTS.PROFILES.md`. |
| Orphan `VERIFIED-SUBMIT-PLAN.v1.md` | **Low** | Decide archive fate; not a move blocker. |
| Scout B PROJECT final name | **Process** | Gate gitignore + TLDR/README link rewrite on final name. |
| macOS `core.ignorecase` note already in `.gitignore` | **Info** | Do not reintroduce bare `DOCS/` ignore rules. |

---

## 7. Suggested rewrite order (for the mover, not executed here)

1. Create `docs/plans/`, `docs/process/`, `docs/plans/.archive/`, `docs/process/.archive/` as needed.
2. Move archive snapshots to new sibling archives (table in §4); leave orphan VERIFIED-SUBMIT.
3. `git mv` canons into targets; rename `AGENTS.PROFILES.md` → `AGENT-PROFILES.md`.
4. Fix **cross-depth** markdown links in the moved set (largest cluster: RUNTIME-SURFACING* ↔ contracts).
5. Fix **root stay** links: `NOW.md` NORTHSTAR; `TLDR.md`/`README.md` PROJECT; `justfile` WHEEL; PERFORMANCE→NOW; TEST.PERFORMANCE→scripts.
6. Fix `.gitignore` for PROJECT (coordinate Scout B name).
7. Update WARROOM root claim prose.
8. Optionally refresh code comment paths (non-blocking).
9. Do **not** touch fixtures, `.archive/` file bodies, TMP/NOTES.

---

## 8. Inventory of root `*.md` vs proposal

| File | Proposal disposition | Scout note |
|------|----------------------|------------|
| TLDR.md | KEEP root | symlink target |
| README.md | KEEP | |
| NOW.md | KEEP | |
| LESSONS.md | KEEP (gitignored local) | |
| QUICKSTART.md | KEEP | |
| AGENTS.md, CLAUDE.md | KEEP symlinks | not in move list; correct |
| HARNESS-COMPATIBILITY … TEST.PERFORMANCE (10) | → `docs/` | OK |
| RUNTIME-SURFACING* + CONTROLPLANE-OBSERVATION-PLAN (4) | → `docs/plans/` | OK |
| WARROOM, AGENTS.PROFILES | → `docs/process/` (+ rename profiles) | OK |
| PROJECT.md | → `docs/` rename TBD | gitignore critical |

No unlisted root `*.md` left outside keep/move/symlink sets.

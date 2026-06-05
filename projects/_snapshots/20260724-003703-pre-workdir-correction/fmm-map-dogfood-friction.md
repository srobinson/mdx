---
title: fmm MAP.md dogfood — friction log
type: research
tags: [fmm, dogfood, friction, map-skill, tooling-gaps]
summary: Eight friction points found generating MAP.md for fmm's own repo via the map skill + fmm CLI; top gap is the broken stamp path (fmm status cannot supply SHA/branch/dirty).
status: active
source: codebase-analyst
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

# fmm MAP.md dogfood — friction log

**Task:** follow `MAP.SKILL.md` exactly to produce `MAP.md` for the fmm repo, using only `fmm` CLI/MCP tools as methodology. Repo at `805ae4c` (main). Binary: `fmm 0.3.6+ed3bdb7`.

**Result:** MAP.md produced and committable. Below is every point where I wanted a structural fact fmm could not give me in one call, or had to do something expensive. Each entry: **want → had to do → primitive that would solve it → severity.** Positives are listed at the end so the signal is honest, not just complaints.

The friction clusters into two themes: (A) **the stamp path is broken end-to-end**, and (B) **fmm has the metadata to answer several questions but the CLI does not expose a filtered/typed view of it** (cycles, exports, glossary, reverse-deps).

---

## 1. `fmm status` cannot supply the stamp (SHA / branch / dirty) — TOP GAP. Severity: HIGH

- **Want:** Skill Step 1 says *"`fmm status` includes a 'Git Metadata' section: SHA / Branch / Dirty"* and the orchestrator brief asserts the repo "on main includes git_sha in `fmm status`." The map header (`<!-- fmm:map sha=… branch=… dirty=… -->`) depends on it. This is the skill's **first required step**.
- **Reality:** `fmm status` prints only Configuration / Supported Languages / Workspace. No git section. `fmm status --help` documents only *"config file location, supported languages, indexed file counts"* — no git section even conceptually.
- **Two compounding causes:**
  1. **Stale binary.** Installed `fmm` is built from `ed3bdb7` (PR #153), which **predates** `805ae4c` (PR #154, *"record git sha/branch/dirty in index meta"*). So the running binary has no git-meta code at all.
  2. **Storage ≠ rendering.** PR #154's title is "record … in index **meta**." The data model exists (`fmm-core/src/store.rs` `GitMeta { sha, branch, dirty }`, `GIT_SHA_META_KEY` / `GIT_BRANCH_META_KEY` / `GIT_DIRTY_META_KEY`, written to the store meta table), but nothing renders it through `fmm status`. The skill is ahead of the implementation.
- **Had to do:** fall back to `git rev-parse --short HEAD`, `git rev-parse --abbrev-ref HEAD`, `git status --porcelain`. Pure git, zero fmm.
- **Primitive needed:** `fmm status` should read the stored `GitMeta` and render the Git Metadata section the skill expects, ideally with `fmm status --json` exposing `{git_sha, git_branch, git_dirty, files, loc}` so the stamp is one machine-readable call. Until the binary is rebuilt to ≥`805ae4c` **and** `status` renders it, Step 1 of the skill is unsatisfiable via fmm.
- **Why it's the top gap:** it breaks the very first instruction of the skill, and it's the one fact the map exists to carry (staleness detection). Everything downstream worked; the stamp did not.

## 2. `fmm cycles` reports module-hierarchy SCCs as cycles; no way to exclude `# mod-hierarchy` edges. Severity: HIGH

- **Want:** real coupling-debt cycles to "name them" (Skill Step 4 / Seams section).
- **Reality:** ~10 SCCs reported, and **every single one** is a `mod.rs` + its sibling submodules (e.g. `parser/{mod,registry}`, `cli/commands/{mod,ls,deps,…}` ×9, `manifest/*` ×11, `search/*` ×8). These are idiomatic Rust re-export facades, not architectural cycles. Crucially, `fmm deps parser/registry.rs` shows the back-edge annotated **`crates/fmm-core/src/parser/mod.rs  # mod-hierarchy`** — fmm *already classifies* the edge but `cycles` includes it anyway.
- **Had to do:** run `fmm deps` on cycle members to inspect edges and hand-judge debt-vs-idiomatic, because `cycles` prints SCC **membership only**, never the edges that close the loop.
- **Primitive needed:** (a) `fmm cycles --exclude-mod-hierarchy` (or default to runtime/import edges, opt-in mod-hierarchy), and (b) `fmm cycles --explain` / `--edges` to print the actual edge list per SCC. The classification metadata already exists; only the filter/projection is missing.
- **Impact on the map:** without this, the cycles section is dominated by false positives. I had to reframe the entire section as "all mod-hierarchy, not debt," which is the opposite of what the skill intends the section to surface.

## 3. `fmm outline` omits trait-body method signatures. Severity: MEDIUM

- **Want:** the contract of the `FmmStore` trait — `outline` is the skill's designated "shape of a component" tool (Step 2).
- **Reality:** `fmm outline crates/fmm-core/src/store.rs --include-private` shows `pub trait FmmStore / kind: trait` and **no methods**. Struct/impl methods *are* surfaced (e.g. `manifest/mod.rs` `declaration_kind_for`, `identity/mod.rs` `from_absolute_paths`), so this is specific to trait bodies.
- **Had to do:** `fmm read FmmStore` (full source) to recover `type Error`, `load_manifest`, `load_fingerprints`, `update_file_fingerprint`, batch writers.
- **Primitive needed:** `outline` should list trait method signatures (default-method bodies elided). In a ports/adapters codebase the traits **are** the most important seams; needing a full-source `read` for every trait defeats the point of outline.

## 4. `fmm exports` has no source/test filter — public-API view is polluted with test symbols. Severity: MEDIUM

- **Want:** the stable public contract per crate (Skill Step 5).
- **Reality:** `fmm exports --dir crates/fmm-store/src` lists per-file exports including `#[cfg(test)]` functions and `tests` modules (e.g. `wal_mode_is_active`, `open_db_errors_on_stale_schema_version`, `batch_write_is_atomic`, `make_parse_result`). There is no `--filter source` the way `fmm ls` has one, and no "only what the crate root re-exports" mode.
- **Had to do:** derive the real public surface from the `lib.rs` re-export facade (`fmm outline crates/<crate>/src/lib.rs`) and mentally drop test items.
- **Primitive needed:** `fmm exports --filter source` (reuse the path-based test filter `ls` already has) and/or `fmm exports --crate-public` (only `lib.rs`/`pub use` surface).

## 5. `fmm glossary <Symbol>` is substring-fuzzy, not exact-symbol — weak for single-type blast radius. Severity: MEDIUM

- **Want:** call sites / importers of the `Manifest` **struct** (Skill Step 2: "Impact / importers of a key symbol").
- **Reality:** `fmm glossary Manifest --precision call-site` returned every symbol whose **name contains** "manifest" — `build_manifest`, `candidate_manifest_paths`, `canonical_manifest_keys`, `crate_name_from_cargo_manifest`, `DependencyGraphQuery.manifest`, … The exact `Manifest` type was buried in the noise.
- **Had to do:** use `fmm ls --sort-by downstream` (file-level fan-in) + `fmm deps` for the blast-radius numbers instead; glossary did not answer the question the skill points it at.
- **Primitive needed:** `fmm glossary <Symbol> --exact`, or a symbol-level reverse-dependency query keyed on the resolved symbol rather than name substring.

## 6. No transitive reverse-dependency (true blast-radius) count for a file or symbol. Severity: MEDIUM

- **Want:** "touching `manifest/mod.rs` transitively reaches N files" for the Key Components prose.
- **Reality:** `fmm ls --sort-by downstream` gives **direct** dependents only (footer: *"↓ N = direct dependents"*). `fmm deps <file> --depth 2` gives forward transitive deps + a flat direct-downstream list, not a transitive **reverse** closure.
- **Had to do:** report direct fan-in only (↓82, ↓79, …) and avoid claiming transitive reach.
- **Primitive needed:** `fmm deps <file> --reverse --transitive` (reverse-dep closure with a count), or `fmm ls --sort-by downstream-transitive`.

## 7. No repo-wide duplication or symbol-size scan (skill pre-acknowledges). Severity: MEDIUM

- **Want:** "every near-duplicate cluster" and "every function/symbol over 150 LOC" for the Health section.
- **Reality:** `fmm similar <Symbol>` is probe-based (one symbol per call; for `ParserRegistry` it mostly returns the symbol's own fields/impl plus a few cross-type matches). `fmm ls` reports **file** LOC, not per-symbol body LOC.
- **Had to do:** skip repo-wide dupe detection entirely (did **not** brute-force read files, per skill instruction); flagged heaviest *files* only.
- **Primitive needed:** the already-planned `fmm dupes` (repo-wide near-duplicate clusters) and `fmm symbols --min-loc N` / a `body_loc` field on outline. The skill itself names these as the planned cure.

## 8. Topology rollup is single-level only. Severity: LOW

- **Want:** a full per-crate → per-module LOC tree in one call.
- **Reality:** `fmm ls --group-by subdir` collapses only the **immediate** children of the given DIR. The workspace root rollup gave just `crates/ fixtures/ npm/`.
- **Had to do:** four invocations (root + once per crate `crates/fmm-{core,cli,store}/src`) to assemble the topology tables.
- **Primitive needed:** `fmm ls --group-by subdir --depth N` (recursive rollup) or a dedicated `fmm tree` with LOC aggregation.

---

## What worked well (honest balance)

- **`fmm ls --sort-by downstream --filter source`** — the single most valuable command for the map. One call ranked the load-bearing hubs (`parser/mod.rs` ↓82, `manifest/mod.rs` ↓79, …) exactly as the Key Components section needs.
- **`fmm ls --group-by subdir <DIR>`** — clean per-module file-count + LOC; reliable topology once you accept the single-level limit (#8).
- **`fmm read <Symbol>`** — gave the full `FmmStore` trait contract *with doc comments*; the reliable fallback when outline fell short (#3).
- **`fmm deps <file>`** — accurate local_deps / downstream, and the `# mod-hierarchy` annotation is genuinely useful (it's the metadata `cycles` should reuse, #2).
- **`fmm similar`** — the score breakdown (`name / shape / kind / nbhd`) is a strong probe UX; the limit is scope (one symbol), not quality (#7).
- **`fmm validate`** / **`fmm ls` summaries** — fast, deterministic file/LOC counts (426 files · 64,443 LOC) with zero ceremony.

## Build priority implied by this log

1. **Fix the stamp path (#1)** — rebuild/release the binary to ≥`805ae4c` *and* render stored `GitMeta` via `fmm status` (+`--json`). The skill's first step is dead until then.
2. **`fmm cycles` mod-hierarchy filter + `--explain` (#2)** — biggest quality lift to the map's most-misleading section; the classification data already exists.
3. **`outline` trait methods (#3)** + **`exports --filter source` (#4)** — cheap, high-value polish to the two "shape/contract" tools.
4. **Exact-symbol glossary (#5)** and **transitive reverse-deps (#6)** — make impact/blast-radius answerable in one call.
5. **`fmm dupes` / `fmm symbols --min-loc` (#7)** — unlock the Health section's duplication + god-function checks (already on the roadmap).

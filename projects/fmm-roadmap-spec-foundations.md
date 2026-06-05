---
title: fmm Roadmap — Foundations Spec (CANONICAL)
type: spec
tags: [fmm, roadmap, foundations, git-sha, json-contract, snapshot, schema, data-contract, canonical]
summary: Authoritative foundations data-contract for the fmm roadmap, synthesized from the Claude + Codex MoE drafts. Resolves every point of divergence with rationale. Capability specs (map, diff, dupes, health, etc.) cite THIS file.
status: approved-draft
source: orchestrator-synthesis
confidence: high
repo: /Users/alphab/Dev/LLM/DEV/helioy/fmm
head: 5f8a1296d72f507a2e4bd1950001a442dc6b31fc
fmm_version: 0.3.6
created: 2026-06-17
updated: 2026-06-17
inputs:
  - ~/.mdx/projects/fmm-roadmap-spec-foundations-claude.md
  - ~/.mdx/projects/fmm-roadmap-spec-foundations-codex.md
---

# fmm Foundations Spec (canonical)

This is the authoritative foundations contract. The two source drafts (Claude, Codex) carry the full grounding and traceability tables; this file **supersedes both on every point of divergence** and is what later capability specs cite. Read the source drafts for the field→file+symbol traceability; read this for the binding decisions.

Three pieces: (1) git metadata in the index, (2) a stable versioned JSON envelope, (3) SHA-keyed structural snapshots. All anchors verified against HEAD `5f8a129`, `fmm 0.3.6`, schema v6.

---

## Convergence (both drafts agree — locked, not relitigated)

- `git_sha` / `git_branch` / `git_dirty` stored in the existing `meta` KV table (`schema.rs` → `CREATE_SCHEMA_SQL`), written at generate time.
- New `crates/fmm-cli/src/git.rs` that **shells out to `git`** (`std::process::Command`), no `git2`/`gix` dependency — matches the existing `build.rs` precedent.
- `fmm generate --sha <sha>` override for CI / detached trees.
- `Store::write_meta` signature changes to accept git metadata. **Blast radius (corrected by sign-off — the original "3 sites" undercount would break `just test`):** the trait def `fmm-core/src/store.rs::FmmStore::write_meta` + **three** impls (`fmm-store/src/sqlite_store.rs::SqliteStore`, `fmm-store/src/memory_store/mod.rs::InMemoryStore`, AND the test `NullStore` impl at `fmm-cli/src/mcp/tests/support.rs`) + **three** sidecar call sites (`fmm-cli/src/cli/sidecar.rs`, the `store.write_meta()` calls) + a test call site in `sqlite_store.rs`. All must change in lockstep or `just test` fails on `NullStore`.
- `fmm status` gains a git/index-metadata section and a new `--json` output (status has none today).
- A single JSON **envelope** wraps every report payload: version, fmm_version, git_sha, generated_at, command, params, results. Determinism is mandatory: no query wall-clock, sorted params, deterministic result ordering with stable tiebreakers.
- Snapshots keyed by git_sha, copying `content_hash` + symbol rows + dependency edges from the live index. New `write_snapshot` trait method mirroring `write_meta`.
- Snapshot retention default: **keep last 50**; pruning is explicit, never automatic during a bare `generate`.
- Snapshot requires git or `--sha`, else error. Dirty tree gated behind `--allow-dirty-snapshot`.
- `fmm diff`, `fmm snapshots list/prune`, and MCP `fmm_snapshot_status` / `fmm_structural_diff` are DEFERRED to the diff capability spec; foundations only guarantees the retained data exists. Result shapes are reserved here so the capability spec inherits them.
- MCP tools/flags are codegen'd: new tool or flag ⇒ edit `crates/fmm-cli/tools.toml`, `build.rs` regenerates schema/help/skill.

---

## Resolved divergences (orchestrator decisions)

### D1 — Snapshot storage location ⚠️ LOAD-BEARING. Decision: **separate `.fmm-snapshots.db`.**

`ensure_schema` (`schema.rs` → `drop_all_tables`) drops tables on a `SCHEMA_VERSION` mismatch because the index is regeneratable. **Sign-off refinement (Codex):** `drop_all_tables` is an *enumerated* drop list, not a blanket "drop everything", so the live code does not mechanically prove a future in-`.fmm.db` snapshot table would be dropped — it would only be dropped if a developer added it to that enumerated list. But that nuance *strengthens* the decision: keeping snapshots in `.fmm.db` would require permanently and correctly excluding every snapshot table from `drop_all_tables` — and from the reasoning of every future migration — forever. Snapshots are **historical and NOT regeneratable** (fmm has no git-history reindex path, an explicit non-goal), so that fragile coupling risks silently destroying history on a schema bump. Codex's "rebuilding a regeneratable index is acceptable" reasoning is correct for the index and wrong for snapshots.

**Decision:** snapshots live in a sibling `.fmm-snapshots.db` with an independent `snapshot_schema_version` (starts at 1) and **additive-only** migrations. It is never touched by the index's `ensure_schema`/`drop_all_tables`. This decouples the regeneratable index lifecycle from the append-only history lifecycle. The index `.fmm.db` does **not** need a schema bump for piece 1 (meta is KV) and gains no snapshot tables — so it stays at v6 unless an unrelated index change requires a bump. (This overrides Codex's "bump to v7 and add snapshot tables to CREATE_SCHEMA_SQL".)

### D2 — Snapshot table structure. Decision: **adopt Codex's fuller mirror** (in the separate DB).

Codex's `snapshots` (surrogate `snapshot_id` PK + `UNIQUE(git_sha, scope_digest)`) + `snapshot_files` (full structural columns incl. imports/deps/function_names JSON + `content_hash`) + separate `snapshot_exports` + `snapshot_methods` + `snapshot_reverse_deps` + `snapshot_workspace_packages`. Rationale: mirroring the live tables is both more faithful (richer diff) AND simpler to implement (straight row-copy, no flatten/merge) than Claude's collapsed `snapshot_symbols`. These tables move into `.fmm-snapshots.db` per D1.

### D3 — `scope_digest`. Decision: **keep it (Codex).**

`fmm generate` accepts paths, so the same SHA can be indexed at different scopes. `scope_digest` (stable digest of normalized generate paths + filter config; canonical root = `"root"`) plus `UNIQUE(git_sha, scope_digest)` prevents collisions. `fmm diff <sha>` selects canonical-root snapshots unless a scope is supplied.

### D4 — Envelope version field naming. Decision: **`contract_version` (int), plus surface `index_schema_version`.**

Use Claude's `contract_version: 1` (integer) for the envelope format — avoids overloading the word "schema_version", which collides with the DB `SCHEMA_VERSION`. Adopt Codex's idea of ALSO carrying `index_schema_version` (the DB schema the index was built under) and a `diagnostics: []` array in the envelope. Merged envelope:

```jsonc
{
  "contract_version": 1,            // envelope format version
  "fmm_version": "0.3.6",
  "index_schema_version": 6,        // DB schema the index was built under
  "git_sha": "5f8a12…" ,            // null if unstamped
  "git_branch": "main",             // null if detached / no git
  "git_dirty": false,               // null if unavailable
  "generated_at": "2026-06-04T15:51:31+00:00",  // index meta, NOT query time
  "command": "ls",
  "params": { /* key-sorted, defaults resolved */ },
  "results": { /* command payload, deterministically ordered */ },
  "diagnostics": []                  // [] normally; warnings/errors as structured items
}
```

### D5 — JSON migration strategy. Decision: **flip `--json` to the envelope directly; no staged `--json-v1`/`--legacy-json` flags.**

Codex proposed a 3-stage `--json-v1` → flip → drop-`--legacy-json` migration. Claude proposed flipping `--json` directly (pre-1.0, the old shape had no version, `contract_version` is the signal). **Decision: Claude's approach.** fmm is 0.3.6 pre-1.0; the MCP server uses its own YAML/text formatters (not CLI `--json`), and no known external consumer pins the bare-array shape. Per repo CLAUDE.md ("delete the old path completely, no parallel implementations until later unless explicitly approved"), shipping three flags and a multi-release dance is over-engineering at this stage. `--json` emits the envelope; `contract_version` signals shape. **O1 RESOLVED by sign-off:** the reviewer verified no `fmm … --json` consumer exists anywhere in the Helioy tree, and the MCP server uses in-process formatters (not the CLI `--json` path), so the direct flip is safe and the `--legacy-json` alias is unneeded. Drop the caveat.

### D6 — `generated_at` no-op stability. Decision: **adopt Codex's rule.**

A no-op `fmm generate` must NOT mutate `generated_at`; it changes only when a file row, reverse-dep row, workspace row, or metadata field actually changes. Without this, two runs over an unchanged tree produce different envelope bytes and break the byte-diff goal. Moderate implementation cost (generate must detect "nothing changed" before rewriting meta). Worth it — determinism is the whole point of the envelope. **Sign-off detail (Claude):** today `write_meta` writes `fmm_version` and `generated_at` coupled in one call (`sqlite_store.rs`, the meta INSERT). No-op stability requires decoupling them at the no-op branch in `cli/sidecar.rs` — preserve the prior `generated_at` while still letting `fmm_version` refresh — rather than skipping the whole meta write.

### D7 — Dirty-snapshot identity (Codex open question). Decision: **v1 refuses dirty snapshots by default;** `--allow-dirty-snapshot` stamps `git_dirty=1` on the same `git_sha` key. Defer the `git_sha + dirty_digest` addressing scheme until a real need appears. Keeps `git_sha` trustworthy as a snapshot key for v1.

---

## Reserved result shapes (inherited by the diff capability spec)

`fmm diff <base_sha> [<head_sha>]` returns `FmmReportEnvelope<StructuralDiffResult>` with `files {added, removed, modified[old/new content_hash]}`, `symbols {added, removed, signature_changed[before/after]}`, `dependencies {added_edges, removed_edges}` (full shape in the Codex draft). `fmm snapshots list` / `fmm_snapshot_status` return the snapshot inventory (git_sha, branch, dirty, generated_at, fmm_version, scope_digest, row counts).

---

## Build order (within foundations)

1. **Piece 1 — git metadata** (smallest, no schema bump; unblocks 2 + 3). New `git.rs`, `write_meta` signature change (full blast radius per the corrected Convergence bullet: trait `FmmStore` + 3 impls incl. the `NullStore` test impl + 3 sidecar call sites + a test call site — update `NullStore` or `just test` breaks), `--sha`/`--no-git`, `status` section + `status --json`.
2. **Piece 2 — JSON envelope** (independent of 3; delivers deterministic `--json` for map authoring). New `contract.rs`/`report.rs` envelope type + shared `print_envelope` helper (DRY seam — reject per-command envelope assembly), convert ls/outline/deps/cycles/glossary first, then lookup/exports/search/similar. Implement D6 (no-op timestamp stability).
3. **Piece 3 — snapshots** (depends on git_sha from piece 1; the separate-DB decision D1 is settled, so it is now mechanical). New `.fmm-snapshots.db` store, `write_snapshot` trait method, `generate --snapshot` (+`--allow-dirty-snapshot`, `--keep`), `snapshots list/prune` subcommand.

## Tests / gate

Per repo convention: **`just test` (nextest), never `cargo test`** (config tests need process isolation), plus `just check` (fmt + clippy). Key assertions: round-trip new meta keys; envelope determinism via **double-run byte equality**; no-op generate leaves `generated_at` unchanged; **snapshot survives an index regenerate / schema bump** (the D1 guarantee — this test is the proof D1 works); dirty-snapshot refusal; non-git snapshot with `--sha`; two-commit signature-change smoke test for the future `fmm diff`.

## Open items for the user / capability phase

- **O1 RESOLVED (sign-off):** no `fmm … --json` consumer exists in the Helioy tree; MCP uses in-process formatters. Flip `--json` directly (D5); no `--legacy-json` alias.
- **O2:** whether `fmm_status` MCP tool ships in foundations or with the `map` capability spec (both drafts lean: with map). Recommend: with map.
- **O3:** `git_dirty` scope — all changes vs only indexed-extension changes. Recommend: unscoped + a diagnostic; tighten only if noisy.
- **O4:** content_hash-based cross-snapshot dedup (store each distinct file-state once) — explicitly OUT of foundations; a later storage optimization.

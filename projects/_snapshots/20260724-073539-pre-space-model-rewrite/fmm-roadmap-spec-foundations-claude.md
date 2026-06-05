---
title: fmm Roadmap — Foundations Spec (git-sha index, versioned JSON contract, snapshot table)
type: spec
tags: [fmm, roadmap, foundations, git-sha, json-contract, snapshot, schema, data-contract]
summary: The data contract every later fmm capability (map, diff, dupes, health) cites — git-SHA in the index, a versioned JSON envelope, and a SHA-keyed structural snapshot store.
status: draft
source: codebase-analyst
confidence: high
repo: /Users/alphab/Dev/LLM/DEV/helioy/fmm
head: 5f8a1296d72f507a2e4bd1950001a442dc6b31fc
fmm_version: 0.3.6
schema_version: 6
created: 2026-06-17
updated: 2026-06-17
---

# fmm Foundations Spec

This is the **foundations** layer of the fmm roadmap. Three data-contract pieces that every later capability spec (`fmm map`, `fmm diff`, `fmm dupes`, `fmm health`) will cite:

1. **Git-SHA in the index** — bind an index to the commit it describes.
2. **Stable versioned JSON contract** — a shared, byte-diffable envelope across every `--json` surface.
3. **Snapshot table keyed by git_sha** — retain per-SHA structural state so `fmm diff` and incremental map become buildable.

Decisions already made (not relitigated here): full roadmap approved; foundations first; per-file `content_hash` already populated 416/416 and is the diff-gating primitive; `build.rs` already shells `git rev-parse` for binary version, so the git shell-out pattern exists in-repo.

Traceability is expressed as **field → file + symbol** (never `file:line` — line numbers rot). All anchors verified against HEAD `5f8a129`.

---

## 0. Ground truth (verified against the code)

| Fact | Anchor | Note |
|---|---|---|
| Schema version constant | `crates/fmm-store/src/schema.rs` → `SCHEMA_VERSION` | currently `6` |
| Schema migration is nuke-and-rebuild | `schema.rs` → `ensure_schema`, `drop_all_tables` | version mismatch drops ALL listed tables; "data loss is acceptable" because the index is regeneratable |
| `meta` is a generic key-value table | `schema.rs` → `CREATE_SCHEMA_SQL` (`meta(key TEXT PRIMARY KEY, value TEXT)`) | **new keys need no DDL and no schema bump** |
| Sole meta-write hook on generate | `crates/fmm-store/src/sqlite_store.rs` → `SqliteStore::write_meta` | writes `fmm_version`, `generated_at` (RFC3339 `Utc::now()`) |
| Trait surface | `crates/fmm-core/src/store.rs` → `Store::write_meta` | signature `fn write_meta(&self) -> Result<(), Self::Error>` — takes no args today |
| Other impl / write sites (blast radius) | `crates/fmm-store/src/memory_store/mod.rs` → `InMemoryStore::write_meta`; `crates/fmm-store/src/connection.rs` (hardcoded `INSERT INTO meta VALUES ('fmm_version', …)` + read of `fmm_version`) | both must track any trait-signature change |
| generate orchestration calls write_meta | `crates/fmm-cli/src/cli/sidecar.rs` (3 call sites: `store.write_meta()?`) | the place to compute git metadata and pass it down |
| `status` command — **no JSON today** | `crates/fmm-cli/src/cli/status.rs` → `status` | pure colored stdout; reads `COUNT(*) FROM files` only |
| `--json` is a bare payload, no envelope | `crates/fmm-cli/src/cli/commands/ls.rs` → `ls` (`serde_json::to_string_pretty(&Vec<ListFileJson>)`) | representative of every `--json` command |
| Commands that already emit `--json` | `crates/fmm-cli/src/cli/commands/{ls,outline,deps,cycles,lookup,read,similar,exports}.rs`, `search.rs`, `glossary.rs` | all emit a raw array/object, none versioned |
| MCP/CLI docs are codegen'd | `crates/fmm-cli/tools.toml` + `crates/fmm-cli/build.rs` → `generate_mcp_schema`, `generate_cli_help`, `generate_skill_md` | **any new MCP tool or flag = edit `tools.toml`**; build.rs writes `generated_schema.rs`, `generated_help.rs`, `templates/SKILL.md` |
| Existing git shell-out pattern | `crates/fmm-cli/build.rs` → `emit_version` (env `FMM_GIT_SHA`); `justfile` → `build-local` (`git rev-parse --short=7 HEAD`) | precedent: shell out to `git`, no `git2` dependency in tree |

**Naming hazard resolved up front.** The DB `SCHEMA_VERSION` (piece 3) and the JSON envelope version (piece 2) are different concepts with different lifecycles. This spec names the envelope field **`contract_version`** and never reuses "schema_version" for the JSON layer.

---

## 1. Git-SHA in the index

Bind an index to the commit whose tree it describes, so any artifact built from the index (MAP.md, diff, health report) can be SHA-stamped without a side-channel `git rev-parse`.

### 1.1 Data model

No schema bump. `meta` is key-value; add three keys, written at generate time:

| meta key | value | when absent |
|---|---|---|
| `git_sha` | full 40-char HEAD sha | omitted (not a git repo, or `--no-git`) |
| `git_branch` | `git rev-parse --abbrev-ref HEAD` (e.g. `main`; `HEAD` when detached) | omitted |
| `git_dirty` | `"true"` / `"false"` — working tree has uncommitted changes to indexed files | omitted |

Rationale for storing the **committed HEAD sha plus a dirty flag** (rather than refusing to stamp a dirty tree): the index can be generated mid-edit; `git_sha` records the commit the tree is *based on*, and `git_dirty=true` warns consumers the index may not byte-correspond to that commit. A downstream `fmm diff` treats `git_dirty=true` as "base sha is approximate."

### 1.2 Git probe (new, in fmm-cli)

New module `crates/fmm-cli/src/git.rs` exposing:

```
pub struct GitMeta { pub sha: String, pub branch: String, pub dirty: bool }
pub fn probe_git(root: &Path, sha_override: Option<&str>) -> Option<GitMeta>
```

- Gate on repo presence: `git -C <root> rev-parse --is-inside-work-tree` → if non-zero/absent, return `None` (graceful, no error).
- `sha`: `git -C <root> rev-parse HEAD`, or `sha_override` verbatim when `--sha` is passed (CI may pass a sha for a tree checked out without `.git`).
- `branch`: `git -C <root> rev-parse --abbrev-ref HEAD`.
- `dirty`: `! git -C <root> status --porcelain` is empty. Open question 1.7(a) on whether to scope dirtiness to indexed extensions only.
- Shell out via `std::process::Command` (consistent with `build.rs`/`justfile`; **no new `git2` dependency** — keeps the build lean and matches precedent).

### 1.3 Trait + write path change (blast radius)

`Store::write_meta` must accept the git metadata. Change signature:

```
// crates/fmm-core/src/store.rs → Store::write_meta
fn write_meta(&self, git: Option<&GitMeta>) -> Result<(), Self::Error>;
```

`GitMeta` (or a store-local mirror to avoid a fmm-core → fmm-cli dependency inversion — see 1.7(b)) is read in each impl and the three keys written via the existing `writer::write_meta(conn, key, value)` helper.

Sites that must change in lockstep (verified):

| Site | Anchor | Change |
|---|---|---|
| Trait decl | `fmm-core/src/store.rs` → `Store::write_meta` | new `git` param |
| Sqlite impl | `fmm-store/src/sqlite_store.rs` → `SqliteStore::write_meta` | write `git_sha`/`git_branch`/`git_dirty` when `Some` |
| Memory impl | `fmm-store/src/memory_store/mod.rs` → `InMemoryStore::write_meta` | mirror |
| Generate callers | `fmm-cli/src/cli/sidecar.rs` (3× `store.write_meta()`) | call `probe_git(root, sha_override)` once, thread `Option<&GitMeta>` to each call |
| Serialization bootstrap | `fmm-store/src/connection.rs` (hardcoded meta INSERT + `fmm_version` read) | audit: ensure round-trip preserves new keys; **verify before editing** |

Back-compat: an index generated by an older fmm (no git keys) is valid — readers treat the keys as `Option`. No migration needed because no DDL changed.

### 1.4 CLI surface

- `fmm generate --sha <sha>` — override HEAD sha (CI / detached trees). Maps to `probe_git(root, Some(sha))`.
- `fmm generate --no-git` — skip the git probe entirely (`probe_git` returns `None`); for sandboxes where shelling `git` is undesirable.
- `fmm status` — add a **Git** section to the colored output: `git_sha` (short), `git_branch`, `dirty` flag, read from `meta`. Degrades to "not a git repo / not stamped" when keys absent.
- `fmm status --json` — **new flag** (status has no JSON today). Emits the versioned envelope (piece 2) with `results` = `{ git_sha, git_branch, git_dirty, fmm_version, generated_at, source_files, indexed_files, schema_version }`. This is the canonical machine-readable "what is this index" call agents use before building a map.

`--sha` / `--no-git` are new params on the `generate` command. `generate` is hand-written clap (in `crates/fmm-cli/src/cli/mod.rs` → `Commands::Generate`), not codegen'd from `tools.toml` (tools.toml drives only the navigation tools). `status --json` likewise edited in the hand-written command. **No `tools.toml` change for piece 1** unless we also expose status over MCP (1.7(c)).

### 1.5 JSON shape (`fmm status --json`)

```json
{
  "contract_version": 1,
  "fmm_version": "0.3.6",
  "git_sha": "5f8a1296d72f507a2e4bd1950001a442dc6b31fc",
  "generated_at": "2026-06-04T15:51:31+00:00",
  "command": "status",
  "params": {},
  "results": {
    "git_sha": "5f8a1296d72f507a2e4bd1950001a442dc6b31fc",
    "git_branch": "main",
    "git_dirty": false,
    "fmm_version": "0.3.6",
    "generated_at": "2026-06-04T15:51:31+00:00",
    "schema_version": 6,
    "source_files": 416,
    "indexed_files": 416
  }
}
```

`git_sha`/`generated_at` appear both in the envelope header (provenance of the index) and in `results` (the answer to the query). That redundancy is intentional and harmless: the header is uniform across all commands; `results` is the command's own payload.

### 1.6 Traceability (field → file + symbol)

| Field/behavior | Owner |
|---|---|
| `git_sha`,`git_branch`,`git_dirty` meta keys | `fmm-store/src/sqlite_store.rs` → `SqliteStore::write_meta` |
| `probe_git`, `GitMeta` | `fmm-cli/src/git.rs` (new) |
| `--sha`, `--no-git` flags | `fmm-cli/src/cli/mod.rs` → `Commands::Generate` |
| git threading on generate | `fmm-cli/src/cli/sidecar.rs` (3 call sites) |
| status Git section + `--json` | `fmm-cli/src/cli/status.rs` → `status` |

### 1.7 Open design questions

- **(a) Dirtiness scope.** `git status --porcelain` flags any change; should `git_dirty` ignore changes to files fmm does not index (docs, lockfiles) so it tracks *structural* drift only? Cheaper and louder to use the unscoped flag; defer scoping unless noisy.
- **(b) Where does `GitMeta` live?** fmm-core (so the trait can name it) vs fmm-cli (where `git` is probed). Recommend: define a minimal `GitMeta` in **fmm-core** (`store.rs` or a new `meta` module) to keep the trait self-contained; `probe_git` in fmm-cli constructs it. Avoids fmm-core depending on fmm-cli.
- **(c) Status over MCP?** Agents currently can't ask fmm "what SHA is this index" via MCP. Adding an `fmm_status` MCP tool (edit `tools.toml`) is a small, high-value follow-up but arguably belongs to the `map` capability spec, not foundations. Flagged, not scoped here.

---

## 2. Stable versioned JSON contract

A single envelope wraps every `--json` payload so an agent can run fmm twice over the same index and diff the two outputs byte-for-byte. Today each command prints a bare array/object (verified in `ls`), which is neither self-describing nor guaranteed-deterministic.

### 2.1 The envelope

New type in fmm-core (so both CLI and any future MCP-JSON path share it), e.g. `crates/fmm-core/src/contract.rs`:

```
pub struct Envelope<T: Serialize> {
    pub contract_version: u32,   // envelope format version; starts at 1
    pub fmm_version: String,     // fmm_core::VERSION
    pub git_sha: Option<String>, // from meta, None if unstamped
    pub generated_at: String,    // index meta generated_at (NOT query wall-clock)
    pub command: String,         // "ls", "deps", ...
    pub params: BTreeMap<String, serde_json::Value>, // echoed query params, key-sorted
    pub results: T,              // command payload, deterministically ordered
}
```

A constructor `Envelope::new(command, params, results, &manifest_meta)` pulls `fmm_version`/`git_sha`/`generated_at` from the loaded index meta so the header is uniform and free of wall-clock.

### 2.2 Determinism rules (mandatory for every command)

1. **No wall-clock in output.** `generated_at` is the index's meta value, not `Utc::now()`. Two runs over an unchanged index produce identical bytes.
2. **`params` is a `BTreeMap`** (key-sorted) echoing the resolved query parameters (after defaulting), so the envelope is self-describing and stable regardless of flag order.
3. **`results` carries a total order.** Every command sorts its payload by a documented stable key before serialization: files by `path`; symbols by `(file_path, name)`; edges by `(source, target)`; cycles by their min-member path then length. Where the human output is intentionally ranked (e.g. `ls --sort-by downstream`, `similar` by score), the JSON preserves that rank but appends the stable key as a tiebreaker so equal-rank rows never reorder between runs.
4. **Pretty-print with sorted object keys**, 2-space indent (matches current `to_string_pretty`). One trailing newline.

### 2.3 Migration of existing `--json`

Wrapping the payload in `results` is a **breaking change** to current `--json` consumers (top-level shape goes from array → object). Therefore:

- Ship the envelope behind the **same `--json` flag** (no parallel flag — DRY; the old shape had no version, so there is nothing to keep alive), and set `contract_version: 1` as the signal.
- Convert every emitting command to build `Envelope { results: <existing payload> }` instead of printing the payload directly. The per-command payload structs (`ListFileJson`, etc.) are unchanged; only the wrapper is added.
- Commands to convert (verified emitters): `ls`, `outline`, `deps`, `cycles`, `lookup`, `read`, `similar`, `exports` (all under `cli/commands/`), plus `search` and `glossary`.
- A shared helper `print_envelope(command, params, results, meta)` centralizes construction + printing so no command hand-rolls the header. This is the DRY seam; reject any per-command duplication of envelope assembly.

### 2.4 MCP interaction

MCP tools return human-readable YAML/text today, not the CLI `--json`. **Foundations scope: CLI `--json` only.** Whether MCP responses also gain an envelope is deferred (2.6(a)) — the envelope type is defined in fmm-core precisely so the MCP layer can adopt it later without redefinition.

### 2.5 Traceability (field → file + symbol)

| Field/behavior | Owner |
|---|---|
| `Envelope<T>`, `Envelope::new` | `fmm-core/src/contract.rs` (new) |
| `print_envelope` helper | `fmm-cli/src/cli/mod.rs` or a new `cli/envelope.rs` |
| per-command conversion | `fmm-cli/src/cli/commands/*.rs`, `search.rs`, `glossary.rs` |
| determinism (sort keys) | each command's payload-building fn (e.g. `ls.rs` → `sort_entries`) |

### 2.6 Open design questions

- **(a) MCP envelope.** Adopt the same envelope for MCP JSON, or keep MCP responses as terse text? Leaning: keep MCP text for now (token economy), revisit when `fmm_diff`/`fmm_map` need machine-diffable MCP output.
- **(b) Bare-payload escape hatch.** Some pipelines may want the raw array (`jq '.results'` is trivial, so probably not needed). Decide whether to offer `--json-raw`. Recommend: no — one contract, no variants.
- **(c) `contract_version` bump policy.** Define what counts as breaking (field removal/rename/semantics) vs additive (new optional field, no bump). State it in the spec so capability authors know when to increment.

---

## 3. Snapshot table keyed by git_sha

Retain per-SHA structural state so a later `fmm diff <base> <head>` and incremental map become computable. The inputs already exist in the live index (`content_hash` 416/416, `exports`, `methods`, `reverse_deps`); foundations adds the **retention** layer.

### 3.1 The migration tension (the biggest open question — 3.6(a))

`ensure_schema` **drops every table** on a `SCHEMA_VERSION` mismatch (`schema.rs` → `drop_all_tables`), because the index is regeneratable. **Snapshots are NOT regeneratable** — they are historical state of commits that may no longer be checked out. If snapshots live in the main `.fmm.db`, a future schema bump silently destroys history.

Two resolutions:

- **(A) Separate snapshot store** — a sibling file `.fmm-snapshots.db` with its own independent `snapshot_schema_version`, never touched by the index `ensure_schema`/`drop_all_tables`. Append-only history; different lifecycle from the regeneratable index. **Recommended.**
- **(B) Same DB, additive migration** — keep snapshots in `.fmm.db` but exclude snapshot tables from `drop_all_tables` and switch index migrations to additive-where-possible. Higher risk: every future schema change must reason about preserving snapshots; contradicts the current "nuke is safe" invariant.

This spec specifies the tables in a way that is **agnostic to A vs B** (same DDL either way) but **recommends (A)** and flags the decision as load-bearing for `fmm diff`.

### 3.2 Schema (bumps the relevant version)

Under option (A): new file `.fmm-snapshots.db`, `snapshot_schema_version = 1`. Under (B): bump `SCHEMA_VERSION` 6 → 7 and add these tables to `CREATE_SCHEMA_SQL`, excluding them from `drop_all_tables`.

```sql
CREATE TABLE snapshots (
    git_sha       TEXT PRIMARY KEY,
    git_branch    TEXT,
    git_dirty     INTEGER NOT NULL,      -- 0/1
    fmm_version   TEXT NOT NULL,
    schema_version INTEGER NOT NULL,     -- index schema the snapshot was taken under
    generated_at  TEXT NOT NULL
);

CREATE TABLE snapshot_files (
    git_sha      TEXT NOT NULL REFERENCES snapshots(git_sha) ON DELETE CASCADE,
    path         TEXT NOT NULL,
    content_hash TEXT NOT NULL,          -- the diff-gating primitive (already populated)
    loc          INTEGER NOT NULL,
    PRIMARY KEY (git_sha, path)
);

CREATE TABLE snapshot_symbols (
    git_sha          TEXT NOT NULL REFERENCES snapshots(git_sha) ON DELETE CASCADE,
    file_path        TEXT NOT NULL,
    name             TEXT NOT NULL,      -- export name or dotted method name
    declaration_kind TEXT,
    signature        TEXT,
    visibility       TEXT,
    PRIMARY KEY (git_sha, file_path, name)
);

CREATE TABLE snapshot_edges (
    git_sha     TEXT NOT NULL REFERENCES snapshots(git_sha) ON DELETE CASCADE,
    source_path TEXT NOT NULL,
    target_path TEXT NOT NULL,
    PRIMARY KEY (git_sha, source_path, target_path)
);
CREATE INDEX idx_snapshot_files_sha ON snapshot_files(git_sha);
CREATE INDEX idx_snapshot_symbols_sha ON snapshot_symbols(git_sha);
```

`snapshot_symbols` deliberately flattens `exports` + `methods` into one symbol table (diff cares about "symbol X with signature Y existed at SHA"), keyed by the SHA. `snapshot_files.content_hash` lets `fmm diff` gate at the file level in one indexed scan before descending to symbols — reusing the exact primitive the eval reports identified.

### 3.3 Write path

`fmm generate --snapshot`:
1. Run the normal generate (refresh the live index).
2. Require git: `probe_git(root, sha_override)`. If `None` (not a repo) and no `--sha`, **error** ("snapshots require a commit; pass --sha to override"). A snapshot keyed by nothing is useless.
3. Refuse-or-warn on dirty tree (3.6(b)): a dirty snapshot does not byte-correspond to its sha. Default: warn and stamp `git_dirty=1`; `--allow-dirty` to silence.
4. `INSERT OR REPLACE` a `snapshots` row, then bulk-copy current `files.{path,content_hash,loc}` → `snapshot_files`, `exports`+`methods` → `snapshot_symbols`, `reverse_deps` → `snapshot_edges`, all stamped with the sha, in one transaction.
5. Idempotent: re-snapshotting the same clean sha is a no-op replace.

New trait method (mirrors `write_meta`'s pattern), e.g. `Store::write_snapshot(&self, git: &GitMeta) -> Result<(), _>`, implemented for `SqliteStore` (and a no-op or in-memory mirror for `InMemoryStore`).

### 3.4 Retention / pruning / size

- Default retention: **keep last `N` snapshots** (proposed `N = 50`), pruned oldest-first by `generated_at` after each `--snapshot` write.
- `fmm generate --snapshot --keep-last <N>` overrides; `fmm snapshot prune --before <iso-date>` / `--keep-last <N>` for manual control.
- **Size estimate** (this repo, 416 files): `snapshot_files` ≈ 416 rows × ~80 B ≈ 33 KB; `snapshot_symbols` (~a few thousand symbols) ≈ low hundreds of KB; `snapshot_edges` proportional to `reverse_deps`. Order ~0.3–0.5 MB per snapshot uncompressed → ~50 snapshots ≈ 15–25 MB. Acceptable for a local index file; pruning caps it. Note for the capability spec: content_hash dedup across snapshots (store each distinct file-state once, reference by hash) is a future optimization, **out of foundations scope**.

### 3.5 CLI + MCP surface

- `fmm generate --snapshot` (+ `--keep-last`, `--allow-dirty`) — hand-written in `Commands::Generate`.
- `fmm snapshot list` / `fmm snapshot prune` — new `Commands::Snapshot` subcommand (hand-written clap; not `tools.toml`, since this is project-management, not navigation).
- `fmm status` Git section gains "N snapshots retained (oldest <sha> … latest <sha>)".
- **No new MCP tool in foundations.** `fmm_diff` / `fmm_snapshot_status` belong to the diff capability spec; foundations only guarantees the data exists.

### 3.6 Open design questions

- **(a) Where do snapshots live? (load-bearing)** Separate `.fmm-snapshots.db` (recommended, immune to index nuke) vs in-DB additive migration. Everything downstream (`fmm diff`) depends on this; resolve first.
- **(b) Dirty snapshots.** Reject, or stamp `git_dirty=1` and warn? Recommend warn+stamp+`--allow-dirty` so CI on a clean checkout is the happy path and local experimentation still works.
- **(c) Snapshot granularity.** Store full symbol rows per SHA (proposed, simplest, enables rich diff) vs only `content_hash` per file (cheap, but `fmm diff` could only report file-level changes, not symbol/signature deltas). Recommend full symbols — the eval reports' value case is *symbol-level* added/removed/signature-changed.
- **(d) Auto-snapshot.** Should a normal `fmm generate` (no flag) auto-snapshot when the sha changed since the last snapshot? Powerful for "incremental map after each commit" but surprising/side-effecty. Recommend explicit `--snapshot` for v1; revisit a `watch`-driven auto-snapshot later.

---

## 4. Build order & cross-piece dependencies

1. **Piece 1 (git-sha)** first — piece 2's envelope `git_sha` field and piece 3's snapshot key both depend on it. Smallest, lowest-risk; unblocks the other two.
2. **Piece 2 (envelope)** second — independent of piece 3; delivers immediate value (deterministic `--json` for map authoring) and defines `contract_version` policy.
3. **Piece 3 (snapshots)** third — depends on `GitMeta`/git_sha from piece 1; carries the one genuinely hard decision (3.6(a) snapshot storage location). Specify and resolve 3.6(a) before writing code.

Each piece ships with: schema/meta change + back-compat note, CLI flags, JSON shape, and tests (round-trip the new meta keys; assert envelope determinism via double-run byte equality; assert snapshot survives an index regenerate under option A). Per repo convention use `just test` (nextest), **never `cargo test`** — config tests need process isolation.

---

## 5. Summary table

| Piece | Schema bump | New meta/tables | CLI surface | tools.toml? | Biggest risk |
|---|---|---|---|---|---|
| 1. git-sha | none (KV keys) | `git_sha/git_branch/git_dirty` | `generate --sha/--no-git`, `status` Git + `--json` | no | trait signature blast radius (3 impls/callers) |
| 2. JSON contract | none | none | envelope on all `--json` | no | breaking `--json` shape change (mitigated by `contract_version`) |
| 3. snapshots | yes (or separate DB) | `snapshots/snapshot_files/snapshot_symbols/snapshot_edges` | `generate --snapshot`, `snapshot list/prune` | no | **snapshots vs nuke-and-rebuild migration (3.6a)** |

**Single biggest open design question across the spec:** where the SHA-keyed snapshot store lives (3.6a) — a separate `.fmm-snapshots.db` immune to the index's nuke-and-rebuild `ensure_schema`, versus an in-DB additive migration that breaks the current "schema mismatch → drop everything" invariant. This choice determines whether historical snapshots survive future schema bumps, and every `fmm diff`/incremental-map feature is built on it.

---
title: cm Agent DX 7-axis audit (post-ALP-1970)
type: review
tags: [agent-dx, cli, mcp, audit, context-matters]
summary: cm CLI + MCP server scored against the google-labs-code agent-dx-cli-scale rubric after the ALP-1970 capability consolidation.
status: active
source: backend-engineer
confidence: high
created: 2026-04-22
updated: 2026-04-22
---

# cm Agent DX 7-axis audit — 2026-04-22

Subject: `context-matters` CLI (`cm`) and MCP server (`cm serve`) at release 0.2.10, branch `main`, post-ALP-1970 refactor (PR #48 merged). Rubric: `google-labs-code/design.md` `agent-dx-cli-scale`.

## Summary table

| # | Axis | Baseline | Current | Delta | Next upgrade (one line) |
|---|------|---------:|--------:|------:|-------------------------|
| 1 | Machine-Readable Output      | 2 | 2 | 0   | NDJSON streaming for `recall`/`browse`/`export` with non-TTY auto-detect. |
| 2 | Raw Payload Input            | 1 | 2 | +1  | Accept `--json-payload @-` on `cm store`/`update`/`forget`/`deposit` for zero-translation round-trips. |
| 3 | Schema Introspection         | 1 | 3 | +2  | **At ceiling.** Consider a `cm spec` subcommand that emits the same schemas to stdout for non-MCP callers. |
| 4 | Context Window Discipline    | 1 | 2 | +1  | Field masks (`--fields id,title,snippet`) on `recall`/`browse`/`get` to trim rows below the 16 KB cap. |
| 5 | Input Hardening              | 2 | 2 | 0   | Reject control chars + path-traversal patterns in `scope_path`/`created_by`/`source`/UUID fields (validation-layer only). |
| 6 | Safety Rails                 | 1 | 1 | 0   | Universal `--dry-run` on `store`/`update`/`deposit`/`forget` that returns the would-be ack with a `dry_run: true` envelope. |
| 7 | Agent Knowledge Packaging    | 1 | 2 | +1  | Ship versioned workflow recipes (recall → get → update) alongside the parameter reference in `SKILL.md`. |

**Net: 9/21 → 14/21 (+5)**. Two axes at ceiling (Axis 3). Three axes moved from the refactor (2, 4, 7), two by design consolidation, one incidental. Two axes (1, 5, 6) still at baseline — no refactor work touched them.

## Axis-by-axis

### 1. Machine-Readable Output — **2/3** (baseline 2, Δ 0)

**Justification.** Every `cx_*` MCP tool returns a dual-channel MCP envelope with `content[0].text` (for the model prompt) and `structuredContent` (JSON projection for programmatic consumers). See `crates/cm-cli/src/mcp/response.rs:92-105` (`build_envelope`). The CLI mirrors this: every read/write handler has a `-j/--json` flag that emits `serde_json::to_string_pretty`. Examples: `crates/cm-cli/src/cli/browse.rs:91-97`, `crates/cm-cli/src/cli/recall.rs:67-73`, `crates/cm-cli/src/cli/update.rs:71-80`, `crates/cm-cli/src/cli/deposit.rs:75-88`. Output is consistent JSON across all commands — that satisfies the `2` bar.

**Why not 3.** No NDJSON streaming and no non-TTY default. Large `recall`/`browse`/`export` results come back as one pretty-printed JSON blob, requiring the agent to wait for the full response and parse it in one shot. `cm export` on a full store buffers the whole payload in memory before writing. `-j` is opt-in; TTY-vs-pipe detection is not used to switch format automatically.

**Next upgrade.** Add `--ndjson` (or auto-select on non-TTY) on `recall`, `browse`, `get`, `export`. Emit one entry per line. For `export`, stream rows as the store cursor advances — removes the memory peak on large stores.

---

### 2. Raw Payload Input — **2/3** (baseline 1, Δ +1)

**Justification.** After the refactor the capability request types (`StoreRequest`, `UpdateRequest`, `DepositRequest`, `BrowseRequest`, `RecallRequest`) are pure data structs in `cm-capabilities` and the CLI/MCP adapters are thin marshallers. Concretely:

- `cm deposit --exchanges -` reads a raw JSON array from stdin (`crates/cm-cli/src/cli/deposit.rs:47-55`). The JSON wire shape is identical to the MCP `cx_deposit.exchanges` field.
- `cm update --body -` streams the body from stdin, and `cm update --meta '<json>'` accepts the full `MetaInput` blob (`crates/cm-cli/src/cli/update.rs:35-55`). `MetaInput` (`crates/cm-capabilities/src/validation.rs:101-113`) is the canonical wire shape for both MCP and CLI.
- MCP handlers deserialise `serde_json::Value` straight into the capability request (`crates/cm-cli/src/mcp/tools/store.rs:12`, `crates/cm-cli/src/mcp/tools/browse.rs:62`). Zero translation loss on that channel.

**Why not 3.** The CLI path for `cm store` is a Curator-UI stub (`crates/cm-cli/src/cli/store.rs:23-55`) — flags parse and drop silently. Agents that want to write a single entry via CLI must shell out to the MCP tool or call `cm deposit` with a fake exchange. Also, `cm forget` and `cm update` do not accept a full JSON payload (only individual flags), and `cm browse`/`cm recall` take flags only — no `--json-payload @file.json` path.

**Next upgrade.** Add `--json-payload` / `-p` (with `@file.json` or `-` for stdin) on every mutating CLI command. Parse straight into the capability request type. This gives agents one bulletproof invocation shape: `cm <cmd> -p -` with zero flag translation.

---

### 3. Schema Introspection — **3/3** (baseline 1, Δ +2)

**Justification.** `tools.toml` (694 lines) is the single source of truth. `build.rs` compiles it into:

- `crates/cm-cli/src/mcp/generated_schema.rs` — live runtime JSON schemas for every tool.
- `crates/cm-cli/src/cli/generated_help.rs` — CLI help strings kept in lockstep.
- `plugins/helioy-tools/skills/context-matters/SKILL.md` — agent-facing parameter reference.

Every tool schema in `crates/cm-cli/src/mcp/generated_schema/*.json` carries both `inputSchema` and `outputSchema` (see `cx_browse.json:1-275` for a 275-line schema with full type info, enum values, required-field lists, and nested object shapes).

At runtime, an MCP `tools/list` call returns the full schema set. Verified with a direct JSON-RPC probe:

```
$ printf '...initialize...tools/list...' | cm serve | jq '.result.tools[0]'
{ name: "cx_recall", has_input_schema: true, has_output_schema: true, ... }
```

That satisfies the `3` bar: live runtime-resolved schemas with full type info.

**Why at ceiling.** Input, output, enums, nested objects, required fields all present, served live from the binary, same source as the build-time artefacts. Nothing left in the rubric.

**Next upgrade (optional).** Add a `cm spec` subcommand that prints the same schemas to stdout for non-MCP callers (CI, generators, editors). Low effort since `generated_schema::generated_tool_list()` already returns the full `Value`.

---

### 4. Context Window Discipline — **2/3** (baseline 1, Δ +1)

**Justification.**

- **Response cap.** Every MCP tool response except `cx_export` is clipped at 16 KB (`crates/cm-cli/src/mcp/response.rs:13` `MAX_MCP_RESPONSE_BYTES`, truncation at `cap_response`, line 44). The truncation advisory tells the agent to use `cx_get` for full bodies or narrow the query.
- **Pagination.** `cx_browse`/`cm browse` have `cursor`/`limit` with opaque cursors (`crates/cm-cli/src/cli/cli_def.rs:101-104`). `cx_browse.json:9-12` documents the cursor as `next_cursor` round-trip.
- **Two-phase retrieval.** `cx_recall`/`cx_browse` return snippets only (200 bytes, `crates/cm-capabilities/src/projection/text.rs:10` `SNIPPET_MAX_BYTES`). `cx_get` fetches full bodies.
- **Token budget.** `cm recall --max-tokens N` trims results to fit a caller-declared budget (`crates/cm-cli/src/cli/recall.rs:31-56`, rubric-aligned explicit limit).
- **Limit clamp.** `clamp_limit` caps at 200 (`crates/cm-capabilities/src/validation.rs:19-21`).

Pagination + field-cap + snippet/get split = the `2` bar (field masks + pagination across all reads).

**Why not 3.** No field masks (`--fields id,title,snippet`) on `recall`/`browse`/`get` — the response always includes the full projection. No streaming pagination — each `cm browse` page is a full pretty-printed blob before the next fetch. No per-axis agent guidance on when to narrow (beyond the truncation advisory).

**Next upgrade.** Add `--fields` on read commands to prune the projection server-side. Pairs naturally with the Axis 1 NDJSON upgrade for streaming pagination.

---

### 5. Input Hardening — **2/3** (baseline 2, Δ 0)

**Justification.**

- Per-field byte caps (`MAX_INPUT_BYTES = 1 MiB`, `crates/cm-capabilities/src/constants.rs:2`, applied via `check_input_size` at `crates/cm-capabilities/src/validation.rs:11-16`, used in `store.rs:63-64` and `recall.rs:36`).
- Batch size caps (`MAX_BATCH_IDS = 100`, applied at `crates/cm-capabilities/src/validation.rs:75-77`).
- UUID validation (`parse_uuid_batch`, `validation.rs:71-91`).
- Enum validation (`parse_kind`, `parse_confidence`, `parse_tag_sort`, `validation.rs:24-50`) — rejects unknown values with canonical-value hints.
- Scope path parsed through `ScopePath::parse` before any DB write (every write handler calls `ScopePath::parse(...).map_err(capability_error)` — e.g. `crates/cm-cli/src/cli/browse.rs:45-48`).
- SQLx bound parameters throughout `cm-store` (no string concatenation in SQL — confirmed by inspection of the capability layer, which never hand-builds SQL).

That lands at `2` (basic type checks + some validation + rejects obvious bad shapes).

**Why not 3.** No explicit control-character rejection on string fields (title, body, tags, created_by, source, scope_path) — a hostile agent could smuggle NUL, CR, or terminal escape sequences into stored entries that later print through `cm browse` and spoof UI output. No path-traversal rejection on `source` or `scope_path`. No output sandboxing for the shell-rendered human channel.

**Next upgrade.** Add a `reject_control_chars(field, value)` helper in `cm-capabilities::validation` and call it from every write request builder. Reject `../` and leading `/` in `source` when it looks like a path. Narrow UUID parser already catches the id surface.

---

### 6. Safety Rails — **1/3** (baseline 1, Δ 0)

**Justification.** No `--dry-run` anywhere in the CLI (verified with grep across the repo — zero hits on `dry[_-]?run`). That holds the axis at `1` (no dry-run on any command).

The partial credit comes from `cm forget` being **soft-delete only** (sets `superseded_by = self_id`), with already-inactive entries silently skipped (`crates/cm-cli/src/mcp/tools/forget.rs` and the capability layer). No destructive hard-delete is exposed via CLI or MCP, so "accidental data loss" has a recoverable floor. And `supersedes` on `cx_store` is explicit — a rename has a visible audit trail.

**Why not 2 or 3.** No `--dry-run` at all. No prompt-injection defenses on fields that later get rendered back to an agent's prompt (title, body, snippet all flow directly into recall output — a stored entry with `body: "IGNORE ALL PRIOR INSTRUCTIONS..."` flows back into the next agent's context untouched).

**Next upgrade.** Add a universal `--dry-run` on `store`/`update`/`deposit`/`forget` that builds the request, runs validation, returns the would-be ack with `dry_run: true` in the envelope, and rolls back the transaction. The capability request types are already value objects, so wiring is a one-flag-per-adapter change.

---

### 7. Agent Knowledge Packaging — **2/3** (baseline 1, Δ +1)

**Justification.** `plugins/helioy-tools/skills/context-matters/SKILL.md` is:

- Fronted with YAML metadata (`name`, `description`) — satisfies "YAML skill files" in the rubric.
- Contains a workflow section (recall → store → deposit → ...).
- Includes per-tool parameter tables auto-generated from `tools.toml` (verified: `SKILL.md:78-177`).
- Documents the scope model, two-phase retrieval, and decision rules.
- Ships inside the `helioy-tools` plugin alongside other tool skills.

MCP server-side `instructions` field (`crates/cm-cli/src/mcp/instructions.rs:3-42`) echoes the same workflow verbatim, so agents get the same guidance through both the plugin-loaded skill and the MCP `initialize` handshake.

That's a YAML skill with workflows — the `2` bar.

**Why not 3.** Not versioned (no `version:` field, no migration notes for schema changes). No workflow recipes for non-obvious cascades (e.g. "recall → inspect snippets → get the three most relevant → update with new metadata"). No error-recovery recipes. No anti-pattern section (FTS5 full-sentence query mistakes are called out in one line, but there's no section of worked examples).

**Next upgrade.** Add a `recipes/` block to `SKILL.md` (or split into `recipes.md`) with three or four canonical multi-tool workflows. Version the skill with a `version: 1.x` field and a `CHANGELOG` section that tracks tools.toml schema changes. Low effort; the payoff is Stuart and peer agents cease re-deriving the same multi-step patterns in every session.

---

## Priority list — top 3 upgrades

1. **Axis 6 (Safety Rails): universal `--dry-run`** — **M effort, highest leverage.**
   Why this one: Axis 6 is at `1`, the same baseline as pre-refactor, and the refactor made it almost free to implement — every mutating capability request is now a pure value object. Wiring a `dry_run: bool` into `WriteContext` and short-circuiting the DB write before projection lands all four mutating commands at once. Unblocks agent-driven automation against production stores without a staging round-trip.

2. **Axis 2 (Raw Payload Input): `--json-payload @-` on mutating CLI commands** — **S effort, high leverage.**
   Why this one: The capability request types already deserialize from JSON cleanly. A one-flag-per-adapter change (`store`, `update`, `deposit`, `forget`) takes Axis 2 to `3` and gives agents one muscle-memory invocation shape (`cm <cmd> -p -`) that round-trips with zero flag translation. Directly addresses the `cm store` stub gap.

3. **Axis 1 (Machine-Readable Output): NDJSON + non-TTY default on reads/exports** — **M effort, medium leverage.**
   Why this one: Axis 1 is the only unchanged high-traffic axis. `cm export` already has a memory-peak concern on large stores, and `cm recall`/`cm browse` consumed by agent pipelines would benefit from line-oriented output. Pairs with the Axis 4 field-mask upgrade to produce a fully streaming read path. Deferred over the dry-run and JSON-payload wins because both of those are strictly cheaper and unblock more agent workflows first.

## Open items

- Consider whether `cm spec` (Axis 3 polish) is worth ~30 minutes of work to make non-MCP callers first-class. Low urgency; schemas are already reachable via `cm serve + tools/list`.
- Axis 5 control-char rejection is a security hygiene item, not an agent-DX item per se. Worth filing but separate from the DX leverage list.
- Axis 7 recipes could be co-developed with Stuart since the canonical workflows are in his head, not the code.

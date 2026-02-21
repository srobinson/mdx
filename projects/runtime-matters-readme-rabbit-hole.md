# README auto-gen rabbit hole — discovery (2026-05-22)

Repo: `runtime-matters` @ HEAD `e138cb5` (main, clean tree)
Pair: pane A (Claude, `runtime-matters:helioy-tools:codebase-analyst:3:2.1`) drafts, pane B (Codex, `runtime-matters:helioy-tools:codebase-analyst:3:2.2`) audits.

User intent: stop auto-generating the README and drop the tests that pin auto-gen README content. The rabbit hole continues past README into a build.rs that writes five other artifacts back into the source tree, plus type aliases and CLI help constants that are mostly dead code at runtime.

## 1. Map of generation surfaces

Surfaces A-F are produced by `crates/rtm-cli/build.rs::main()` at lines 7-18 and write into the source tree. Surface G is also produced by that build.rs but emits only an env var (no source-tree write). Surface H is produced by `crates/rtm-core/build.rs` (env-only). Surface I is documentation drift in PROJECT.md, not a generation surface. The single source of truth for A-F is `crates/rtm-core/tools.toml` (161 lines, 4 tools: `rtm_kill_by_pid`, `rtm_status`, `rtm_version`, `rtm_watchers`). The repo-root `tools.toml` is a **symlink** to that file (`tools.toml -> crates/rtm-core/tools.toml`), not a copy.

The registry is materialized by `lilo_rm_core::tool_contracts::contract_registry()` (`crates/rtm-core/src/tool_contracts.rs:66-70`) which `include_str!`s `tools.toml` and `toml::from_str`s it once into a `OnceLock<ToolRegistry>`. From that registry, two helpers do everything:

- `ToolRegistry::tool_list_value()` (`tool_contracts.rs:73-81`) → `serde_json::Value` MCP `tools/list` payload
- `ToolRegistry::admin_tools_markdown()` (`tool_contracts.rs:83-95`) → the README/SKILL.md markdown table

### Surface A: `README.md` admin tools section

- **Producer:** `crates/rtm-cli/build.rs::write_readme()` (lines 97-106). Replaces text between `<!-- rtm-admin-tools:start -->` and `<!-- rtm-admin-tools:end -->` markers in the repo-root `README.md`.
- **Consumer / why it exists:** Human-facing README. Also shipped with the cargo-dist tarball for the `rtm` binary release (`Cargo.toml::workspace.metadata.dist.include = ["LICENSE", "README.md"]`).
- **Source of truth:** `crates/rtm-core/tools.toml` via `registry.admin_tools_markdown()`.
- **Blast radius if removed:**
  - `tool_contract_snapshots.rs::admin_tools_readme_section_is_stable` (rtm-core snapshot) breaks — but it snapshots the function, not the README file, so removing the call site does not break the test; only removing `admin_tools_markdown()` does.
  - `docker_documentation.rs` does NOT care about this section (asserts unrelated hand-written narrative).
  - `surface_snapshots.rs` does not read README.
  - No runtime code depends on the README markers.

### Surface B: `crates/rtm-cli/src/generated/mod.rs`

- **Producer:** `build.rs::write_generated_sources()` lines 82-85. Hard-coded body: `"pub mod cli_help;\npub mod contracts;\npub mod mcp_tools;\n"`.
- **Consumer / why it exists:** Declares the three sibling modules so `lib.rs` can `pub mod generated;`.
- **Source of truth:** None. Static string in build.rs. Independent of tools.toml.
- **Blast radius if removed:** Module path goes away; have to wire the surviving submodules through `lib.rs` directly.

### Surface C: `crates/rtm-cli/src/generated/cli_help.rs`

- **Producer:** `build.rs::write_generated_sources()` line 86, body built by `build.rs::cli_help()` (lines 108-119).
- **Current contents:** Five `pub const *_ABOUT: &str` constants (`MCP_ABOUT`, `KILL_ABOUT`, `STATUS_ABOUT`, `VERSION_ABOUT`, `WATCHERS_ABOUT`).
- **Consumer / why it exists:**
  - Runtime use: `crates/rtm-cli/src/cli/mod.rs:50-54` uses **three** of the five — `STATUS_ABOUT`, `MCP_ABOUT`, `VERSION_ABOUT` as `#[command(about = ...)]` attribute values.
  - **`KILL_ABOUT` is unused at runtime.** `cli/mod.rs:39-40` declares a hand-written `about = "Signal a runtime session by id, or a process by pid."` for the `Kill` command. The text in `KILL_ABOUT` (`"Send an operator signal to a runtime process by pid."`) never reaches the CLI surface.
  - **`WATCHERS_ABOUT` is unused at runtime.** There is no `Watchers` CLI command. The constant exists only as MCP shim metadata in the registry, which the daemon serves from `contract_registry()`, not from this constant.
- **Source of truth:** `tools.toml` (each `[tools.<name>]` `cli_about` field) plus the literal `MCP_ABOUT` string baked into `build.rs:110`.
- **Blast radius if removed:** Three CLI command `about` attributes need a value. Easiest: inline the three live strings into `cli/mod.rs`, delete the file. Two of the five constants disappear with no replacement needed because they are dead code today.

### Surface D: `crates/rtm-cli/src/generated/contracts.rs`

- **Producer:** `build.rs::write_generated_sources()` line 87, body built by `build.rs::contracts()` (lines 121-127), with per-tool aliases produced by `build.rs::contract_aliases()` (lines 152-178).
- **Current contents:** Type aliases and zero-sized request structs for each tool: `RtmKillByPidArgs = lilo_rm_core::KillByPidRequest`, `RtmKillByPidResponse = lilo_rm_core::KillByPidResponse`, etc.
- **Consumer / why it exists:** **None.** A repo-wide grep confirms zero runtime callers. The aliases exist only because build.rs emits them. No CLI command, no MCP handler, no test imports `RtmKillByPidArgs` or any of its siblings.
- **Source of truth:** `tools.toml` (`args_type`/`response_type` fields), but the alias mapping is hard-coded in `build.rs::contract_aliases()` per tool name with a `panic!("unsupported tool contract {other}")` fallback — adding a fifth tool to `tools.toml` would break the build immediately. So the build.rs maintains a manual switch for what the alias names should point to, defeating the "single source of truth" framing for this surface.
- **Blast radius if removed:** Nothing. This is the largest pure waste in the rabbit hole.

### Surface E: `crates/rtm-cli/src/generated/mcp_tools.rs`

- **Producer:** `build.rs::write_generated_sources()` line 88, body built by `build.rs::mcp_tools()` (lines 129-143).
- **Current contents:** `pub const TOOL_LIST_JSON: &str` (177-line JSON literal) and `pub const TOOL_NAMES: &[&str]` slice.
- **Consumer / why it exists:** Only test code. There is **no runtime consumer**.
  - The daemon's MCP server serves `tools/list` from `contract_registry().tool_list_value()` directly (`crates/rtm-daemon/src/mcp_bridge.rs:36`). It never reads `TOOL_LIST_JSON`.
  - `rtm mcp` (the CLI subcommand) is a thin stdio→Unix-socket bridge (`crates/rtm-cli/src/mcp/mod.rs`) that forwards JSON-RPC lines to rtmd and does not parse the tool list either.
  - Tests: `tests/integration_pass6.rs:13-17` uses `TOOL_LIST_JSON` and `TOOL_NAMES` as the expected value for a runtime assertion against rtmd; `tests/generated_snapshots.rs:2-11` snapshots them.
- **Source of truth:** `tools.toml` via `registry.tool_list_value()`.
- **Blast radius if removed:**
  - `tests/generated_snapshots.rs::generated_mcp_tool_list_is_stable` and `::generated_mcp_tool_names_are_stable` break (acceptable — drop them).
  - `tests/integration_pass6.rs::pass6_mcp_lists_admin_tools_and_reports_status_version_watchers` (lines 11-17) breaks because it compares `tools/list` against the generated constants. The substantive assertion can be rewritten in terms of the live registry: `assert_eq!(tools["result"], contract_registry().tool_list_value());`, or relaxed to a structural check.
  - The duplicate `tool_contract_snapshots.rs::mcp_tool_list_contract_is_stable` already pins the same payload — the integration_pass6 cross-check is essentially redundant with that snapshot.

### Surface F: `crates/rtm-cli/templates/SKILL.md`

- **Producer:** `build.rs::write_skill_doc()` (lines 91-95), body built by `build.rs::skill_doc()` (lines 145-150). Prepends a frontmatter block (`name: rtm-admin`, `description: Admin MCP tools for runtime-matters rtmd.`) to `registry.admin_tools_markdown()`.
- **Consumer / why it exists:** **Test-only.** The only reference is `tests/generated_snapshots.rs:30` via `include_str!("../templates/SKILL.md")`. The file is not embedded in the rtm-cli binary, not referenced by `examples/`, not included in the cargo-dist tarball, not part of any install recipe.
- **Source of truth:** `tools.toml` for the body, hard-coded frontmatter in `build.rs:147`.
- **Blast radius if removed:** Only the snapshot test breaks. There is no skill catalog or external system that ingests this file.

### Surface G: `RTM_CLI_VERSION` env var (out of scope but adjacent)

- **Producer:** `build.rs::emit_cli_version()` (lines 20-32). Emits `cargo:rustc-env=RTM_CLI_VERSION={version}` where version is `CARGO_PKG_VERSION` optionally suffixed with the build git sha.
- **Consumer / why it exists:** Used by the binary at runtime to report its own version. `crates/rtm-cli/src/lib.rs:6` exposes it as `pub const VERSION: &str = env!("RTM_CLI_VERSION");`.
- **Source of truth:** Cargo + git.
- **Blast radius:** Out of scope for the rabbit hole. This is a normal build.rs use (writes only env, never source files) and should stay.

### Surface H: `RTM_GIT_SHA` env var (rtm-core build.rs)

- **Producer:** `crates/rtm-core/build.rs` (15 lines). Emits `cargo:rustc-env=RTM_GIT_SHA={sha}` with the 12-char HEAD sha.
- **Consumer / why it exists:** Embedded in version metadata served by `rtm_version`.
- **Source of truth:** git.
- **Blast radius:** Out of scope. Normal env-only build.rs use, stays.

### Surface I (drift, not a generation surface): `PROJECT.md` admin tools section

- **NOT a generation surface.** `PROJECT.md:202-211` has a copy of the `<!-- rtm-admin-tools:start --> ... :end -->` block but `build.rs::write_readme()` only writes to `repo_root/README.md`. If `tools.toml` changes, PROJECT.md silently drifts.
- **Consumer:** human readers of PROJECT.md.
- **Source of truth:** none — it was hand-copied at some point and is now an undocumented duplicate.
- **Blast radius if changed:** purely documentation. Worth flagging as part of the cleanup so the markers either get replaced with a plain table or get removed.

## 2. Map of asserting tests

### Tests that pin auto-generated content

| Test | File:line | Asserts | Tied to | Survives without generation? |
|---|---|---|---|---|
| `generated_mcp_tool_list_is_stable` | `crates/rtm-cli/tests/generated_snapshots.rs:1-6` | snapshot of `TOOL_LIST_JSON` parsed as JSON | Surface E | No. Redundant with `mcp_tool_list_contract_is_stable`. |
| `generated_mcp_tool_names_are_stable` | `crates/rtm-cli/tests/generated_snapshots.rs:8-11` | debug snapshot of `TOOL_NAMES` | Surface E | No. Redundant with the JSON snapshot above. |
| `generated_cli_help_is_stable` | `crates/rtm-cli/tests/generated_snapshots.rs:13-26` | snapshot of all five `*_ABOUT` constants joined with newlines | Surface C | No. Two of the five constants are dead code. |
| `generated_admin_skill_doc_is_stable` | `crates/rtm-cli/tests/generated_snapshots.rs:28-31` | snapshot of `include_str!("../templates/SKILL.md")` | Surface F | No. Drops with Surface F. |
| `mcp_tool_list_contract_is_stable` | `crates/rtm-core/tests/tool_contract_snapshots.rs:3-6` | snapshot of `contract_registry().tool_list_value()` | tools.toml → registry | Yes if tools.toml stays. Becomes the only pin on the wire shape. |
| `admin_tools_readme_section_is_stable` | `crates/rtm-core/tests/tool_contract_snapshots.rs:8-11` | snapshot of `contract_registry().admin_tools_markdown()` | `ToolRegistry::admin_tools_markdown()` (the README+SKILL.md markdown renderer) | **Only if `admin_tools_markdown()` is kept.** Item 1's plan deletes the method when Item 4 (SKILL.md) also lands, because at that point it has no caller. Item 1 deletes this test in either case because its name pins it to README ownership, which Item 1 walks away from. |
| `pass6_mcp_lists_admin_tools_and_reports_status_version_watchers` | `crates/rtm-cli/tests/integration_pass6.rs:9-42` | `assert_eq!(tools["result"], generated_TOOL_LIST_JSON)` plus `assert_eq!(names, TOOL_NAMES)` | Surface E (compares runtime to generated constant) | Partially. The substantive runtime assertion (`status`, `version`, `watchers` tool calls work end-to-end) is independent of generation. Just the `assert_eq!` against generated constants needs to be rewritten — either against `contract_registry().tool_list_value()` or relaxed. |

### Tests that look like they pin auto-gen but do not

| Test | What it actually pins |
|---|---|
| `changelog_records_docker_boundaries` (`crates/rtm-cli/tests/docker_documentation.rs:4-23`) | Hand-written CHANGELOG narrative phrases. Nothing in `build.rs` writes to `CHANGELOG.md`. Should stay; unrelated to the rabbit hole. |
| `docker_docs_do_not_expose_pattern_jargon` (`tests/docker_documentation.rs:26-31`) | Hand-written README/CHANGELOG, asserts absence of internal jargon strings. Unrelated to generation. Stays. |
| `claude_dockerfile_conforms_to_contract` (`tests/docker_documentation.rs:34-65`) | Hand-written `examples/dockerfiles/claude.Dockerfile`. Unrelated. Stays. |
| `mcp_responses_are_stable` (`crates/rtm-cli/tests/surface_snapshots.rs:97-132`) | Snapshot of the **runtime** `tools/list` JSON-RPC response. Source of value is `contract_registry().tool_list_value()` via rtmd. It pins behavior, not the generated file. Stays. |
| `mcp_tool_list_contract_is_stable` (`crates/rtm-core/tests/tool_contract_snapshots.rs:4-6`) | Function-level snapshot of `contract_registry().tool_list_value()`. Pins the registry, not the generated constant. Stays as long as tools.toml exists. Already redundant with `surface_snapshots.rs::mcp_responses_are_stable` for the wire payload, but operates at a different layer (no daemon). Worth keeping for fast feedback. |

### Tests that pin the generator itself (none exist)

Worth calling out: there is no test asserting that `build.rs::contracts()`, `build.rs::cli_help()`, or `build.rs::mcp_tools()` actually run on every build. The only signal that generation ran is that `crates/rtm-cli/src/generated/*` and `crates/rtm-cli/templates/SKILL.md` are committed and the snapshots match. If `build.rs` were silently disabled, the committed artifacts would still satisfy tests.

## 3. Cross-cutting concerns

### 3.1 build.rs writes into the source tree

`crates/rtm-cli/build.rs` writes to **six tracked files** outside `OUT_DIR`:

- `repo_root/README.md` (the workspace root README)
- `crates/rtm-cli/src/generated/mod.rs`
- `crates/rtm-cli/src/generated/cli_help.rs`
- `crates/rtm-cli/src/generated/contracts.rs`
- `crates/rtm-cli/src/generated/mcp_tools.rs`
- `crates/rtm-cli/templates/SKILL.md`

This violates the Cargo convention that build scripts write only under `OUT_DIR`. Two consequences:

1. **Dirty-tree risk on CI.** If a contributor edits `tools.toml` and pushes without running `cargo build` first, the next CI run rewrites the six files. CI does not assert clean trees (see `.github/workflows/ci.yml` — `just check`, `just build`, `just test`, `just insta-test`; none run `git diff --exit-code`). The mitigation is `build.rs::write_if_changed()` (lines 215-220) which skips writes when content is unchanged — so the dirty-tree symptom only fires when content diverges, which is exactly when reviewers most need to see it.
2. **`cargo publish` for `lilo-rm-core` is unaffected** because lilo-rm-core has no build.rs that writes to the tree (its build.rs only emits env). `rtm-cli` has `publish = false` so its build.rs is never invoked by a publish step.

The `rerun-if-changed` directives are:
- `../rtm-core/tools.toml` (the spec)
- `../../.git/HEAD`, `../../.git/packed-refs`, and the resolved ref path (for the git sha env)

So the writes happen on every tools.toml edit and on every git HEAD change. `write_if_changed` keeps the git-HEAD case quiet because the generated content does not depend on the sha.

### 3.2 What actually consumes the generated artifacts at runtime

| Surface | Runtime consumer? | Notes |
|---|---|---|
| README.md (admin tools block) | No | Read by humans and bundled in the cargo-dist tarball; not loaded by any binary. |
| `generated/mod.rs` | Yes (compile time) | Required to expose the submodules. |
| `generated/cli_help.rs` | Partial | Three of five `*_ABOUT` constants used by `cli/mod.rs`. `KILL_ABOUT` and `WATCHERS_ABOUT` are dead. |
| `generated/contracts.rs` | **No** | Zero runtime callers. Fully dead. |
| `generated/mcp_tools.rs` | **No** | Daemon uses `contract_registry().tool_list_value()` directly. CLI `rtm mcp` is a stdio bridge. Constants are test-only. |
| `templates/SKILL.md` | **No** | Only `include_str!`-ed by one snapshot test. Not embedded, not packaged, not shipped. |

### 3.3 What publishes the generated artifacts

- **crates.io for `lilo-rm-core`:** publishes `crates/rtm-core/README.md` (a separate hand-written README that does not contain `rtm-admin-tools` markers). Unaffected by the README generation.
- **crates.io for `lilo-rm-client`:** publishes `crates/rtm-client/README.md` (separate, hand-written, no markers). Unaffected.
- **crates.io for `rtm-cli`:** does not publish (`publish = false`).
- **cargo-dist tarball for the `rtm` binary release:** ships the repo-root `README.md` per `workspace.metadata.dist.include = ["LICENSE", "README.md"]`. **This is the only external consumer of the auto-generated README section.** If the admin tools table disappears from the README, users downloading the release tarball lose that table. Acceptable per the user's stated intent (they explicitly want to own README content).

### 3.4 PROJECT.md drift

`PROJECT.md:202-211` has the same `<!-- rtm-admin-tools:start --> ... :end -->` markers, but `build.rs::write_readme()` only writes to `repo_root/README.md`. PROJECT.md is currently in sync (both show the same four tools) but the moment `tools.toml` gains or changes a tool, PROJECT.md drifts silently. Worth handling as part of the cleanup: either drop the markers from PROJECT.md or drop the whole section.

### 3.5 The dead-code surface is bigger than just README

The user's stated intent ("strip out the auto gen code and the tests that support it") landing only on README leaves these wastes intact:

- 15 LOC of zero-caller type aliases in `generated/contracts.rs`
- ~80 LOC of `build.rs::contracts()` + `contract_aliases()` to emit them
- 2 of 5 `*_ABOUT` constants unused at runtime
- 177-line `TOOL_LIST_JSON` literal whose runtime equivalent is one method call
- The entire `templates/SKILL.md` file (test-only artifact)
- 1 test file (`generated_snapshots.rs`, 31 LOC) whose remaining purpose evaporates with the above
- 1 cross-check in `integration_pass6.rs` that compares runtime against a duplicated constant

If the goal is "we no longer have manual control of the content of the README," removing only the README write leaves the larger smell — a build.rs that maintains a hand-coded switch (`contract_aliases`) to mirror `tools.toml` for no runtime consumer — intact.

### 3.6 What `tools.toml` would still earn its keep for after the cleanup

Even with all generated source files deleted, `tools.toml` still earns its keep as the source for `contract_registry().tool_list_value()`, which the rtmd MCP bridge serves at runtime (`mcp_bridge.rs:36`) and which two snapshot tests pin (`tool_contract_snapshots.rs`). Deleting `tools.toml` would mean either hand-writing the JSON tools/list payload in Rust or hand-writing it as a `serde_json::json!(...)` literal and snapshotting it. That is a real design question and belongs in section 5 as an open question.

## 4. Proposed item list for moe-local-batch

Required items implement the user's stated intent. Optional items are the deeper rabbit hole — each one is justified, but the user can cut any of them.

The ordering below avoids a broken-build window: every item is independently revertable, the build still works between items, and tests stay green at each checkpoint.

### Item 1: Stop generating the README admin tools section (REQUIRED)

- Sign-off phrase suffix: `Item 1 (stop generating README admin tools section)`
- Target paths:
  - `crates/rtm-cli/build.rs` — delete `write_readme()` (lines 97-106) and `replace_or_append()` (lines 180-196); remove the call at line 17 and the `repo_root` derivation at line 12 if no longer needed.
  - `README.md` — keep the existing admin tools table content but remove the `<!-- rtm-admin-tools:start -->` / `:end -->` markers so the section becomes ordinary, hand-edited markdown.
  - `crates/rtm-core/tests/tool_contract_snapshots.rs` — delete `admin_tools_readme_section_is_stable` (lines 8-11) and the matching snapshot file `crates/rtm-core/tests/snapshots/tool_contract_snapshots__admin_tools_readme_section_is_stable.snap`.
  - `crates/rtm-core/src/tool_contracts.rs` — delete `ToolRegistry::admin_tools_markdown()` (lines 83-95) if no caller remains after the README write disappears. Confirmed: it has two callers today (`write_readme`, `skill_doc`); Item 4 covers the SKILL.md caller. If items 1+4 land together, `admin_tools_markdown` can go.
  - `PROJECT.md` — drop or rewrite the `<!-- rtm-admin-tools:start --> ... :end -->` block at lines 202-211 (drift mitigation).
- Current shape: README.md has a marker-delimited section that `build.rs` rewrites on every build that touches `tools.toml` or runs from clean.
- Desired shape: README.md contains a plain markdown admin tools table edited by hand; no markers, no build.rs side effect on README.
- Behaviour-preservation constraint:
  - `surface_snapshots.rs::mcp_responses_are_stable` must still pass (it pins runtime tools/list, not README).
  - `tool_contract_snapshots.rs::mcp_tool_list_contract_is_stable` must still pass.
  - `docker_documentation.rs` tests must still pass (they assert on README narrative unrelated to the markers; deleting the markers should not delete the surrounding human-written sections).
- Dependencies: none. This item is self-contained.
- Optional vs required: **REQUIRED (matches user's stated intent)**.

### Item 2: Drop dead aliases in `generated/contracts.rs`, the generator that emits them, and the orphan registry fields they consumed (REQUIRED-adjacent, OPTIONAL strictly)

- Sign-off phrase suffix: `Item 2 (drop contracts.rs and its generator)`
- Target paths:
  - `crates/rtm-cli/build.rs` — delete `contracts()` (lines 121-127) and `contract_aliases()` (lines 152-178); remove the call at line 87 and the `"pub mod contracts;\n"` fragment from line 84.
  - `crates/rtm-cli/src/generated/contracts.rs` — delete the file.
  - `crates/rtm-core/src/tool_contracts.rs` — delete `pub args_type: String` and `pub response_type: String` fields from `ToolContract` (lines 20-21). After `contract_aliases()` goes, these fields have no consumer (verified: `args_type` and `response_type` only appear in `contract_aliases` to source the alias names).
  - `crates/rtm-core/tools.toml` — delete the `args_type = "..."` and `response_type = "..."` lines from every tool block. Today that's four `args_type` lines (`tools.toml:9, 59, 115, 144`) and four `response_type` lines (`tools.toml:10, 60, 116, 145`).
  - **Update snapshot**: `crates/rtm-core/tests/snapshots/tool_contract_snapshots__mcp_tool_list_contract_is_stable.snap` — accept the regeneration (`cargo insta accept`) if the snapshot pinned anything that referenced `args_type` / `response_type`. Spot-check confirms `tool_list_value()` does not emit these (they are alias-only), so this is defensive; the snapshot likely does not change.
- Current shape: 15 LOC of zero-caller type aliases produced by ~30 LOC of build.rs match arms with a panic-on-new-tool fallback. Two orphan `String` fields in `ToolContract` and eight orphan TOML lines feed them.
- Desired shape: file does not exist; build.rs does not know about contracts; `ToolContract` carries only fields that have runtime consumers (cli_name, cli_about, mcp_description, response_description, params, outputs); `tools.toml` carries no orphan keys.
- Behaviour-preservation constraint: nothing depends on these aliases or the orphan fields. Verified by repo-wide grep — only references are the build.rs that emits them and the file itself. `tool_list_value()` and `admin_tools_markdown()` consume only the fields that stay.
- Dependencies: none. Independent of Items 1, 3, 4, 5.
- Optional vs required: **OPTIONAL (rabbit hole extension)**.
  - Case for: zero callers, hand-coded switch, hard-coded panic on new tools makes it the most obvious dead weight in the rabbit hole. Removing the orphan fields and TOML lines completes the cleanup; leaving them would invite future readers to wonder what they are for.
  - Case against: removing the aliases changes what "rtm-cli reflects the tools.toml contract" means; if someone adds a 5th tool later they lose the panic that signals "update the switch". This is a weak counter — the panic only existed to keep the dead code in sync.

### Item 3: Inline the live `*_ABOUT` strings and delete `generated/cli_help.rs` (OPTIONAL)

- Sign-off phrase suffix: `Item 3 (inline cli_help)`
- Target paths:
  - `crates/rtm-cli/src/cli/mod.rs` — replace `cli_help::STATUS_ABOUT`, `cli_help::MCP_ABOUT`, `cli_help::VERSION_ABOUT` (lines 50, 52, 54) with their literal strings. Drop `use crate::generated::cli_help;` at line 5.
  - `crates/rtm-cli/build.rs` — delete `cli_help()` (lines 108-119) and `const_name()` (lines 198-209); remove the call at line 86 and the `"pub mod cli_help;\n"` fragment.
  - **Do NOT delete `rust_string()` here** — `build.rs::mcp_tools()` still calls it at line 135 (`rust_string(name)` for each tool name). `rust_string()` deletion is deferred to Item 6 (after both `cli_help()` and `mcp_tools()` are gone).
  - `crates/rtm-cli/src/generated/cli_help.rs` — delete the file.
  - `crates/rtm-cli/tests/generated_snapshots.rs` — delete `generated_cli_help_is_stable` (lines 13-26) and the matching `.snap` file.
- Current shape: five const strings, three used, two dead, generated from tools.toml.
- Desired shape: three literal `about = "..."` attributes in `cli/mod.rs`. The `KILL_ABOUT` and `WATCHERS_ABOUT` dead strings disappear by removal, not by inlining.
- Behaviour-preservation constraint:
  - `cargo build` succeeds (specifically, `mcp_tools()`'s call to `rust_string` must still resolve until Item 5/6 land).
  - The `rtm --help` output for `status`, `mcp`, `version` retains its current text (verify with a one-off `rtm --help` diff before/after if doable).
- Dependencies: none for landing (`rust_string()` stays). If Item 3 ever wanted to also delete `rust_string()`, it would need Item 5 as a hard prerequisite — but the cleaner plan is to leave that cleanup for Item 6.
- Optional vs required: **OPTIONAL (rabbit hole extension)**.
  - Case for: three trivial literals are easier to read than a generated const indirection, and dropping two dead constants removes a snapshot whose only "value" is freezing text that is never displayed anywhere.
  - Case against: future tools.toml additions that need CLI help would no longer be free — someone has to type the `about` text manually in `cli/mod.rs`. Counter: there are 4 tools today and have been for a while; the cost is "type a sentence" amortized over the lifetime of the CLI.

### Item 4: Delete `templates/SKILL.md` and its generator (OPTIONAL)

- Sign-off phrase suffix: `Item 4 (delete SKILL.md)`
- Target paths:
  - `crates/rtm-cli/build.rs` — delete `write_skill_doc()` (lines 91-95) and `skill_doc()` (lines 145-150); remove the call at line 16.
  - `crates/rtm-cli/templates/SKILL.md` — delete the file. Delete the `crates/rtm-cli/templates/` directory if it becomes empty (confirmed via `ls`: it currently contains only `SKILL.md`).
  - `crates/rtm-cli/tests/generated_snapshots.rs` — delete `generated_admin_skill_doc_is_stable` (lines 28-31) and the matching `.snap` file.
- Current shape: 13-line markdown file generated from tools.toml, referenced only by a snapshot test.
- Desired shape: file does not exist.
- Behaviour-preservation constraint: no runtime behavior changes (the file has no runtime consumer). Confirm no future user-facing skill catalog plans to ingest this file (this is an open question for the orchestrator — see section 5).
- Dependencies: none.
- Optional vs required: **OPTIONAL (rabbit hole extension)**.
  - Case for: pure test-only artifact today, no shipping path, no consumer.
  - Case against: if the user plans to ship `runtime-matters` as a Claude Code skill in the future, an `rtm-admin` SKILL.md would be the natural home for that. Easier to keep one file than to regenerate it. Counter: if and when that ship date arrives, a hand-edited SKILL.md is cheaper than maintaining the generator for a hypothetical consumer.

### Item 5: Drop the redundant MCP tool list generation (OPTIONAL but tightly linked to integration_pass6)

- Sign-off phrase suffix: `Item 5 (drop generated MCP tool list)`
- Target paths:
  - `crates/rtm-cli/build.rs` — delete `mcp_tools()` (lines 129-143); remove the call at line 88 and the `"pub mod mcp_tools;\n"` fragment.
  - `crates/rtm-cli/src/generated/mcp_tools.rs` — delete the file.
  - `crates/rtm-cli/src/generated/mod.rs` — collapses to a single-module reference (or to nothing if Items 2, 3 also land; see Item 6).
  - `crates/rtm-cli/tests/generated_snapshots.rs` — delete `generated_mcp_tool_list_is_stable` and `generated_mcp_tool_names_are_stable` (lines 1-11) and matching `.snap` files. After Items 3 and 4 also delete their snapshots, the whole file becomes empty and can be removed.
  - `crates/rtm-cli/tests/integration_pass6.rs` — rewrite the first assertion at lines 11-17. Replace:
    ```rust
    let generated: Value = serde_json::from_str(rtm_cli::generated::mcp_tools::TOOL_LIST_JSON).expect("generated");
    assert_eq!(tools["result"], generated);
    assert_eq!(names, rtm_cli::generated::mcp_tools::TOOL_NAMES);
    ```
    with either a registry-based comparison:
    ```rust
    assert_eq!(tools["result"], lilo_rm_core::tool_contracts::contract_registry().tool_list_value());
    ```
    or a structural check (`names.contains(&"rtm_status")` etc.). The registry-based form keeps the spirit of the assertion (runtime contract matches the spec).
- Current shape: 177-line JSON literal duplicated from what the daemon serves at runtime, used as the expected value in two tests.
- Desired shape: file does not exist. `integration_pass6.rs` asserts against the registry directly.
- Behaviour-preservation constraint:
  - `pass6_mcp_lists_admin_tools_and_reports_status_version_watchers` still validates that the runtime MCP server lists the four admin tools, returns non-empty status, version, watchers payloads, and that kill_by_pid signals a process. Only the source of the expected value changes.
  - `tool_contract_snapshots.rs::mcp_tool_list_contract_is_stable` remains the canonical pin on the tools/list JSON shape.
- Dependencies: none on other items, but the test rewrite must land in the same commit/PR as the file deletion.
- Optional vs required: **OPTIONAL (rabbit hole extension)**.
  - Case for: TOOL_LIST_JSON is a frozen duplicate of `contract_registry().tool_list_value()`. The MCP daemon never reads it. Snapshot already pins the shape elsewhere.
  - Case against: it acts as a poor-man's cross-check that the build pipeline and runtime agree on the tool list. Counter: that cross-check happens nowhere in production code paths and the current `assert_eq!` against a generated constant is circular — the constant was generated from the same source the runtime reads at startup.

### Item 6: Collapse `crates/rtm-cli/src/generated/` to nothing and remove the generation pipeline (OPTIONAL, depends on Items 2-5)

- Sign-off phrase suffix: `Item 6 (collapse generated module and build.rs gen pipeline)`
- Target paths:
  - `crates/rtm-cli/build.rs` — delete `write_generated_sources()` (lines 79-89) entirely. After items 2, 3, 5 it has no work. Delete the call at line 15. The remaining body of `main()` is `emit_cli_version()`.
  - **`crates/rtm-cli/build.rs` — also delete `rust_string()` (lines 211-213)** here. After Items 3 and 5 both land, neither `cli_help()` nor `mcp_tools()` exists to call it. This is the natural home for that deletion (per Codex audit finding on Item 3).
  - `crates/rtm-cli/src/generated/mod.rs` — delete the file.
  - `crates/rtm-cli/src/generated/` directory — delete.
  - `crates/rtm-cli/src/lib.rs` — drop `pub mod generated;` (confirmed present at lib.rs:2).
  - `crates/rtm-cli/Cargo.toml` — drop `[build-dependencies] lilo-rm-core` and `serde_json` if `build.rs` no longer needs them. `emit_cli_version` only needs `std`, so the `[build-dependencies]` block can be deleted entirely if items 1-5 all land.
- Current shape: build.rs writes four files into `src/generated/` and `templates/`, plus README. After Items 1-5, none of that work remains.
- Desired shape: `build.rs` is the 15 lines that compute `RTM_CLI_VERSION` and emit git rerun directives. Nothing else.
- Behaviour-preservation constraint: `cargo build` and all surviving tests pass. `rtm --version` continues to work, optionally with git sha when `RTM_VERSION_INCLUDE_GIT_SHA=1`.
- Dependencies: requires Items 1, 2, 3, 4, 5 to land first. If any of them are dropped, this item changes shape (e.g. if Item 4 stays, `write_skill_doc` stays and so does the call at line 16).
- Optional vs required: **OPTIONAL (rabbit hole extension, terminal state)**.
  - Case for: this is the steady state once the rabbit hole is fully closed. Leaving build.rs with one orphan generator after closing the others is worse than closing them all together.
  - Case against: if any optional item is dropped, this item is dropped. It is a synthesis step, not an independent change.

## 5. Open questions for orchestrator

1. **PROJECT.md drift.** Do we (a) drop the `<!-- rtm-admin-tools:start --> ... :end -->` block from PROJECT.md entirely, (b) replace it with a plain inline table that mirrors README, or (c) leave it untouched? PROJECT.md is a long internal design doc; dropping the section is probably right but it does delete real content.
2. **Future SKILL.md path.** Is the runtime-matters admin MCP intended to ship as a Claude Code skill someday? If yes, an `rtm-admin/SKILL.md` is its natural home. If yes-soon, we should keep the file but treat it as hand-edited. If no, Item 4 is unambiguously a win.
3. **Should we go further and drop `tools.toml` itself?** Even with all six write sites gone, `contract_registry()` still reads `tools.toml` at runtime via `include_str!`. Reasonable alternative: replace `tools.toml` with a hand-coded `tool_list_value()` returning a `serde_json::json!(...)` literal, then `tools.toml` becomes redundant. Worth a sign-off question because it changes what "the source of truth for the admin MCP contract" is.
4. **Cargo-dist tarball README.** `workspace.metadata.dist.include = ["LICENSE", "README.md"]` ships the root README in every binary release. After Item 1, the admin tools section in that README becomes hand-edited. Is the user comfortable with the (small) risk that the shipped table drifts from the actual runtime tools/list? The two are pinned by separate tests (`tool_contract_snapshots.rs::mcp_tool_list_contract_is_stable` for the registry, eyeballs for the README) but nothing cross-checks them.
5. **Integration test rewrite shape.** For Item 5's rewrite of `pass6_mcp_lists_admin_tools_and_reports_status_version_watchers`, do we want (a) a tight `assert_eq!(tools["result"], contract_registry().tool_list_value())` cross-check or (b) a looser structural assertion that only checks tool names are present? (a) preserves intent; (b) lets the snapshot be the single source for shape pinning and the integration test focuses on "runtime really serves these tools".

---

**Status:** pane A initial draft restored after pane B clobber. Awaiting pane B audit. Pane B's clobbering draft preserved by the orchestrator at `/Users/alphab/.mdx/projects/runtime-matters-readme-rabbit-hole-paneB-clobber.md`. Sign-off phrases live in each Item N section.

**Iteration note:** The brief allows up to 3 rounds before escalation. Round 1 = this draft (round 1 redraft after clobber).

# README auto-gen rabbit hole — discovery (2026-05-22)

## 1. Map of generation surfaces

### Root README admin tools section

- **Surface name:** `README.md` Admin MCP Tools block.
- **Producer:** `crates/rtm-cli/build.rs:15-17` calls `write_readme`; `crates/rtm-cli/build.rs:97-106` reads and rewrites root `README.md`; `crates/rtm-cli/build.rs:180-196` replaces the marker bounded section or appends it if absent.
- **Consumer / why it exists:** repository documentation and the binary release package. `Cargo.toml:90` includes root `README.md` in cargo-dist artifacts.
- **Source of truth:** `crates/rtm-core/tools.toml:1-3` says it generates MCP schemas, CLI help, README text, skill docs, and typed aliases. `tools.toml` at repo root is a symlink to `crates/rtm-core/tools.toml`. Markdown comes from `ToolRegistry::admin_tools_markdown` in `crates/rtm-core/src/tool_contracts.rs:83-95`.
- **Blast radius if removed:** build no longer mutates `README.md`; manual README control returns. Runtime MCP does not depend on root README. Release archives would carry the manually committed README instead of a build rewritten one.

### Committed CLI generated Rust sources

- **Surface name:** `crates/rtm-cli/src/generated/{mod.rs,cli_help.rs,contracts.rs,mcp_tools.rs}`.
- **Producer:** `crates/rtm-cli/build.rs:79-89` creates `src/generated` and writes all four files. `cli_help` is rendered by `crates/rtm-cli/build.rs:108-119`; typed contract aliases by `crates/rtm-cli/build.rs:121-178`; MCP tool list constants by `crates/rtm-cli/build.rs:129-143`.
- **Consumer / why it exists:** `crates/rtm-cli/src/lib.rs:1-3` publicly exposes the generated module. `crates/rtm-cli/src/cli/mod.rs:5,50-55` uses generated CLI help constants. `crates/rtm-cli/tests/integration_pass6.rs:13-17` compares daemon `tools/list` output to generated `mcp_tools` constants. `crates/rtm-cli/tests/generated_snapshots.rs:1-30` snapshots the generated constants. `contracts.rs` appears unused outside the generated module.
- **Source of truth:** `crates/rtm-core/tools.toml:1-161`, parsed through `contract_registry()` in `crates/rtm-core/src/tool_contracts.rs:66-70`.
- **Blast radius if removed:** CLI help needs hand owned strings or another non build generated source. Integration and snapshot tests must stop comparing runtime output to generated constants. Removing `contracts.rs` probably only requires removing the generated module export unless downstream unpublished code imports it.

### Generated admin skill document

- **Surface name:** `crates/rtm-cli/templates/SKILL.md`.
- **Producer:** `crates/rtm-cli/build.rs:91-95` writes the file; `crates/rtm-cli/build.rs:145-150` formats frontmatter plus `ToolRegistry::admin_tools_markdown()`.
- **Consumer / why it exists:** likely used as an installable admin MCP skill template. The codebase pins it with `crates/rtm-cli/tests/generated_snapshots.rs:28-30` and `crates/rtm-cli/tests/snapshots/generated_snapshots__generated_admin_skill_doc_is_stable.snap`.
- **Source of truth:** `crates/rtm-core/tools.toml:1-161`, especially `mcp_description` fields.
- **Blast radius if removed:** skill documentation becomes manual or disappears. No runtime daemon code depends on the file.

### Runtime MCP schema and admin markdown renderer

- **Surface name:** in memory `ToolRegistry` renderers: `tool_list_value()` and `admin_tools_markdown()`.
- **Producer:** `crates/rtm-core/src/tool_contracts.rs:66-70` parses embedded `crates/rtm-core/tools.toml`; `tool_list_value()` is at `crates/rtm-core/src/tool_contracts.rs:73-81`; `admin_tools_markdown()` is at `crates/rtm-core/src/tool_contracts.rs:83-95`.
- **Consumer / why it exists:** `crates/rtm-daemon/src/mcp_bridge.rs:33-37` serves `tools/list` from `contract_registry().tool_list_value()` at runtime. `admin_tools_markdown()` feeds README and skill doc generation, plus a snapshot test.
- **Source of truth:** `crates/rtm-core/tools.toml:1-161`.
- **Blast radius if removed:** removing runtime schema rendering is much larger than README cleanup. It changes how the daemon advertises MCP tools. Removing only `admin_tools_markdown()` is safe if README and skill doc generation are also removed or rewritten.

### PROJECT.md admin tools marker block

- **Surface name:** `PROJECT.md` Admin MCP Tools block.
- **Producer:** no current writer found. `rg` only finds the marker in `README.md`, `PROJECT.md`, and `crates/rtm-cli/build.rs`. `write_readme()` only targets root `README.md` at `crates/rtm-cli/build.rs:97-106`.
- **Consumer / why it exists:** project documentation.
- **Source of truth:** looks like copied generated content from `ToolRegistry::admin_tools_markdown()`, but it is currently hand edited or stale.
- **Blast radius if removed:** documentation only. Leaving the marker risks future confusion because the marker implies generated ownership without a current producer.

### Cargo build scripts that do not write docs

- **Surface name:** version metadata emitted by build scripts.
- **Producer:** `crates/rtm-cli/build.rs:20-77` emits `RTM_CLI_VERSION`; `crates/rtm-core/build.rs:3-14` emits `RTM_GIT_SHA`.
- **Consumer / why it exists:** runtime version reporting.
- **Source of truth:** package version plus git SHA.
- **Blast radius if removed:** unrelated to README control. Keep these unless a separate versioning refactor is intended.

## 2. Map of asserting tests

### `admin_tools_readme_section_is_stable`, `crates/rtm-core/tests/tool_contract_snapshots.rs:8-10`

- **What it asserts:** snapshot of `contract_registry().admin_tools_markdown()`, the exact markdown used in generated README and skill doc content.
- **Tied surface:** root README generated section and generated skill document.
- **Still makes sense if README stops being generated:** not as named or scoped. If skill docs remain generated, replace it with a skill or renderer test that does not claim README ownership. If skill docs also become manual, delete it and its snapshot.

### `mcp_tool_list_contract_is_stable`, `crates/rtm-core/tests/tool_contract_snapshots.rs:3-6`

- **What it asserts:** JSON snapshot of `contract_registry().tool_list_value()`.
- **Tied surface:** runtime MCP `tools/list` schema, not README.
- **Still makes sense if README stops being generated:** yes. Keep it if `tools.toml` remains the daemon MCP schema source of truth.

### `generated_mcp_tool_list_is_stable`, `crates/rtm-cli/tests/generated_snapshots.rs:1-6`

- **What it asserts:** generated `rtm_cli::generated::mcp_tools::TOOL_LIST_JSON` snapshot.
- **Tied surface:** generated `crates/rtm-cli/src/generated/mcp_tools.rs`.
- **Still makes sense if README stops being generated:** only if generated MCP constants stay. If build time generation is removed, delete or replace with a runtime contract test against `contract_registry().tool_list_value()`.

### `generated_mcp_tool_names_are_stable`, `crates/rtm-cli/tests/generated_snapshots.rs:8-11`

- **What it asserts:** generated `TOOL_NAMES` debug snapshot.
- **Tied surface:** generated `crates/rtm-cli/src/generated/mcp_tools.rs`.
- **Still makes sense if README stops being generated:** only if generated MCP constants stay.

### `generated_cli_help_is_stable`, `crates/rtm-cli/tests/generated_snapshots.rs:13-26`

- **What it asserts:** generated CLI `about` strings from `crates/rtm-cli/src/generated/cli_help.rs`.
- **Tied surface:** generated CLI help constants consumed by clap in `crates/rtm-cli/src/cli/mod.rs:50-55`.
- **Still makes sense if README stops being generated:** yes if CLI help generation stays. Delete or replace with CLI help assertions if generation is removed.

### `generated_admin_skill_doc_is_stable`, `crates/rtm-cli/tests/generated_snapshots.rs:28-30`

- **What it asserts:** committed generated `crates/rtm-cli/templates/SKILL.md`.
- **Tied surface:** generated skill document.
- **Still makes sense if README stops being generated:** yes only if skill doc generation stays. It does not read README directly, but it pins the same admin table text.

### `pass6_mcp_lists_admin_tools_and_reports_status_version_watchers`, `crates/rtm-cli/tests/integration_pass6.rs:8-18`

- **What it asserts:** live MCP `tools/list` result equals generated `TOOL_LIST_JSON`, and live names equal generated `TOOL_NAMES`; then it exercises status, version, and watchers.
- **Tied surface:** runtime MCP output plus generated `mcp_tools.rs` constants.
- **Still makes sense if README stops being generated:** yes, but the generated constant comparison should be replaced if `mcp_tools.rs` goes away.

### `mcp_responses_are_stable`, `crates/rtm-cli/tests/surface_snapshots.rs:97-132`

- **What it asserts:** live MCP initialize, `tools/list`, status, version, watchers, and kill outputs as a snapshot.
- **Tied surface:** runtime MCP public surface.
- **Still makes sense if README stops being generated:** yes. This is not a generated README test.

### Docker documentation tests, `crates/rtm-cli/tests/docker_documentation.rs:3-80`

- **What they assert:** CHANGELOG contains Docker boundary strings; README and CHANGELOG do not expose pattern jargon; Dockerfile contract.
- **Tied surface:** hand documentation and Dockerfile, not the generated admin tools block.
- **Still makes sense if README stops being generated:** yes. These should stay unless the Docker docs change.

### Snapshot files to delete or update with test changes

- `crates/rtm-core/tests/snapshots/tool_contract_snapshots__admin_tools_readme_section_is_stable.snap`
- `crates/rtm-core/tests/snapshots/tool_contract_snapshots__mcp_tool_list_contract_is_stable.snap`, keep if runtime tool registry stays.
- `crates/rtm-cli/tests/snapshots/generated_snapshots__generated_mcp_tool_list_is_stable.snap`
- `crates/rtm-cli/tests/snapshots/generated_snapshots__generated_mcp_tool_names_are_stable.snap`
- `crates/rtm-cli/tests/snapshots/generated_snapshots__cli_help.snap`
- `crates/rtm-cli/tests/snapshots/generated_snapshots__generated_admin_skill_doc_is_stable.snap`

## 3. Cross-cutting concerns

### Build time side effects that touch the working tree

`crates/rtm-cli/build.rs:15-17` writes committed files during Cargo builds: generated Rust source, the skill template, and root `README.md`. `write_if_changed()` at `crates/rtm-cli/build.rs:215-220` suppresses writes only when content already matches. Cargo reruns the build script when `crates/rtm-core/tools.toml` changes because of `crates/rtm-cli/build.rs:9`.

CI runs `just check`, `just build`, `just test`, and `just insta-test` in `.github/workflows/ci.yml:23-27` and `.github/workflows/ci.yml:37-40`. `justfile:8-10`, `justfile:43-44`, and `justfile:72-76` all invoke Cargo paths that can run `rtm-cli/build.rs`. There is no CI `git diff --exit-code` check after the build. That means CI can produce a dirty checkout without failing solely because files were rewritten.

### Runtime consumers of generated artifacts

The daemon does not serve `crates/rtm-cli/src/generated/mcp_tools.rs`. Runtime `tools/list` comes from `contract_registry().tool_list_value()` in `crates/rtm-daemon/src/mcp_bridge.rs:33-37`. The generated `mcp_tools.rs` constants are test or library artifacts.

The CLI does consume generated `cli_help.rs`: `crates/rtm-cli/src/cli/mod.rs:5,50-55`. The generated `contracts.rs` aliases do not appear outside `crates/rtm-cli/src/generated/contracts.rs` and the generated module export.

### Published and packaged content

`rtm-cli` is not published to crates.io: `crates/rtm-cli/Cargo.toml:11` has `publish = false`. The public crates are `lilo-rm-core` and `lilo-rm-client`; `release-plz.toml:10-20` publishes those two. Their crates.io readmes come from `crates/rtm-core/Cargo.toml:4` and `crates/rtm-client/Cargo.toml:4`, not root `README.md`.

Root `README.md` is still packaged by cargo-dist because `Cargo.toml:90` includes it in release archives. So README generation affects GitHub and binary release artifacts, but not the `lilo-rm-core` or `lilo-rm-client` crates.io readme fields.

### fmm status

The fmm MCP server in this pane returned a schema mismatch, but the local `fmm` CLI validated the index successfully: 135 files indexed and current. I used `fmm outline` and `fmm deps` from the repo instead of the failing MCP endpoint.

## 4. Proposed item list for moe-local-batch

### Item 1: Remove root README write path

- Sign-off phrase suffix: `root README write path removed`
- Target paths: `crates/rtm-cli/build.rs`, `README.md`.
- Current shape: every `rtm-cli` Cargo build calls `write_readme()` and rewrites the marker bounded `README.md` section from `tools.toml`.
- Desired shape: Cargo builds never write root `README.md`. Remove `write_readme()` and `replace_or_append()`. Convert the README admin tools block to manually owned text or remove it. Prefer removing the `rtm-admin-tools` markers so future readers do not infer generated ownership.
- Behaviour-preservation constraint: `cargo build --workspace` must stay clean; `rtm daemon` MCP `tools/list` output must remain unchanged; root README remains valid documentation.
- Dependencies: none.
- Optional vs. required: REQUIRED (matches user's stated intent).

### Item 2: Drop README owned snapshot pinning

- Sign-off phrase suffix: `README snapshot pin removed`
- Target paths: `crates/rtm-core/tests/tool_contract_snapshots.rs`, `crates/rtm-core/tests/snapshots/tool_contract_snapshots__admin_tools_readme_section_is_stable.snap`.
- Current shape: `admin_tools_readme_section_is_stable` snapshots markdown generated by `admin_tools_markdown()`.
- Desired shape: no test asserts generated README content. Delete the test and snapshot if README generation is removed. If the renderer is retained only for skill docs, replace the test with a skill scoped name and keep it out of README ownership.
- Behaviour-preservation constraint: keep `mcp_tool_list_contract_is_stable` if the runtime MCP registry stays; `cargo insta test --all` must pass without orphan snapshots.
- Dependencies: Item 1.
- Optional vs. required: REQUIRED (matches user's stated intent).

### Item 3: Resolve the stale PROJECT.md marker block

- Sign-off phrase suffix: `PROJECT admin marker resolved`
- Target paths: `PROJECT.md`.
- Current shape: `PROJECT.md:202-211` contains the same marker bounded Admin MCP Tools table, but no current code writes `PROJECT.md`.
- Desired shape: either remove the generated markers and treat the content as manual, or replace the table with a short pointer to the runtime MCP contract. Do not leave generated markers without a producer.
- Behaviour-preservation constraint: docs only; no code behavior changes.
- Dependencies: Item 1.
- Optional vs. required: OPTIONAL (rabbit hole extension — user can drop). Case for: removes a false generated ownership signal. Case against: not directly part of README control.

### Item 4: Remove all source tree writes from `rtm-cli/build.rs`

- Sign-off phrase suffix: `build script source writes removed`
- Target paths: `crates/rtm-cli/build.rs`, `crates/rtm-cli/src/generated`, `crates/rtm-cli/templates/SKILL.md`.
- Current shape: `rtm-cli/build.rs` writes generated Rust files, skill docs, and README during ordinary Cargo builds.
- Desired shape: build script only emits version metadata and Cargo rerun directives. No build step writes committed source or docs.
- Behaviour-preservation constraint: `rtm --version` keeps the intended version and git SHA behavior; workspace build and tests pass; no dirty tree after `cargo build -p rtm-cli`.
- Dependencies: Item 1 plus choices from Items 5, 6, and 7.
- Optional vs. required: OPTIONAL (rabbit hole extension — user can drop). Case for: removes the root cause pattern behind README loss of control. Case against: larger than the README ask and requires hand ownership of existing generated artifacts.

### Item 5: Hand own CLI help strings

- Sign-off phrase suffix: `CLI help generation removed`
- Target paths: `crates/rtm-cli/src/cli/mod.rs`, `crates/rtm-cli/src/generated/cli_help.rs`, `crates/rtm-cli/tests/generated_snapshots.rs`, `crates/rtm-cli/tests/snapshots/generated_snapshots__cli_help.snap`.
- Current shape: clap `about` strings for status, MCP, version, and watchers come from generated constants.
- Desired shape: put the strings beside the clap commands or in a hand owned module. Delete the generated CLI help file and its snapshot.
- Behaviour-preservation constraint: `rtm --help`, `rtm status --help`, `rtm mcp --help`, `rtm version --help`, and `rtm watchers --help` preserve intended wording unless deliberately edited.
- Dependencies: Item 4 if all build writes are removed.
- Optional vs. required: OPTIONAL (rabbit hole extension — user can drop). Case for: eliminates another doc like generated surface. Case against: duplicates some intent currently held in `tools.toml` unless the registry contract is simplified.

### Item 6: Remove generated MCP constants and generated snapshots

- Sign-off phrase suffix: `generated MCP constants removed`
- Target paths: `crates/rtm-cli/src/generated/mcp_tools.rs`, `crates/rtm-cli/tests/generated_snapshots.rs`, `crates/rtm-cli/tests/integration_pass6.rs`, related snapshots.
- Current shape: generated constants duplicate the runtime MCP tool list. Tests compare live daemon output to those constants.
- Desired shape: tests compare live daemon output to `contract_registry().tool_list_value()` or assert the public behavior directly. Delete generated constants and generated snapshots if no longer needed.
- Behaviour-preservation constraint: `tools/list` JSON output remains stable and covered by `crates/rtm-core/tests/tool_contract_snapshots.rs:3-6` and `crates/rtm-cli/tests/surface_snapshots.rs:97-132`.
- Dependencies: Item 4 if all build writes are removed.
- Optional vs. required: OPTIONAL (rabbit hole extension — user can drop). Case for: removes a redundant generated copy. Case against: current duplicate makes integration tests assert daemon output equals the committed CLI view.

### Item 7: Delete unused generated contract aliases and simplify `tools.toml`

- Sign-off phrase suffix: `unused contract aliases removed`
- Target paths: `crates/rtm-cli/src/generated/contracts.rs`, `crates/rtm-cli/src/generated/mod.rs`, `crates/rtm-core/tools.toml`, `crates/rtm-core/src/tool_contracts.rs`, `crates/rtm-cli/build.rs`.
- Current shape: `args_type` and `response_type` fields exist so build.rs can write typed aliases. The aliases appear unused outside the generated file.
- Desired shape: remove `contracts.rs`, remove the generated module export if no generated files remain, and remove `args_type` / `response_type` from `ToolContract` and `tools.toml` if no other consumer exists.
- Behaviour-preservation constraint: MCP `tools/list` schema and tool call handling remain unchanged. Public crate semver checks should pass because these aliases live in unpublished `rtm-cli`.
- Dependencies: Item 4.
- Optional vs. required: OPTIONAL (rabbit hole extension — user can drop). Case for: removes dead generated surface and reduces registry fields. Case against: if unpublished downstream code imports `rtm_cli::generated::contracts`, this is a break.

### Item 8: Decide the admin skill doc ownership model

- Sign-off phrase suffix: `skill doc ownership decided`
- Target paths: `crates/rtm-cli/templates/SKILL.md`, `crates/rtm-cli/tests/generated_snapshots.rs`, `crates/rtm-cli/tests/snapshots/generated_snapshots__generated_admin_skill_doc_is_stable.snap`.
- Current shape: skill doc is generated from the same `admin_tools_markdown()` renderer as README.
- Desired shape: either keep skill doc generation and rename tests away from README language, or make `SKILL.md` hand owned and delete the generator plus snapshot.
- Behaviour-preservation constraint: any operator or installer that expects this template still has a valid skill doc.
- Dependencies: Item 1; Item 4 if all build writes are removed.
- Optional vs. required: OPTIONAL (rabbit hole extension — user can drop). Case for: resolves another source of generated prose. Case against: skill docs may benefit from staying synchronized with runtime MCP tools.

## 5. Open questions for orchestrator

1. Should this phase stop after README autonomy, or should it remove every `rtm-cli/build.rs` source tree write?
2. Should the root README keep a manually owned Admin MCP Tools table, or should that section be removed and replaced with a pointer to `rtm doctor` / MCP docs?
3. Should `PROJECT.md:202-211` be cleaned in the same batch even though no current generator writes it?
4. Should `tools.toml` remain the source of truth for runtime MCP schemas, or is the desired end state direct Rust definitions with no TOML registry?

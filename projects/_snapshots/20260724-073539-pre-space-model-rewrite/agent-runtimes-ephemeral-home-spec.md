---
title: Agent runtimes ephemeral home spec
summary: Transport Matters should launch Claude and Codex from pristine runtime templates through per run homes without mutating templates or losing transcript durability.
type: spec
tags: [transport-matters, agent-runtimes, runtime-home, claude, codex, auth]
status: active
created: 2026-06-15
updated: 2026-06-15
source: codebase-analyst
confidence: high
---

# Agent runtimes ephemeral home spec

Verified against `transport-matters` `main` at `16b95d7`. Code citations use file plus symbol only.

## 1. Goal and non-goals

### Goal

Launch Claude or Codex from a pristine `.agent-runtimes` template into a Transport Matters owned per run runtime home. The child process reads and writes the runtime home. The template supplies reusable content, native homes supply live credentials, transcript descriptors resolve to the runtime home, and template bytes remain unchanged.

### Non-goals

* Do not add a public user flag for runtime templates. `--agent-home-dir` keeps its current manual meaning.
* Do not build the `.agent-runtimes` registry or generator inside this slice. Transport Matters consumes a thin resolved template reference.
* Do not make Transport Matters own broad agent lifecycle policy.
* Do not persist arbitrary home filesystem state in Postgres. Only transcript visible or explicitly externalized state is durable.
* Do not route Codex CLI through `build_codex_captured_invocation` while that helper fixes `force_http_fallback=False`.

## 2. Background: current overlay machinery and Codex asymmetry

Transport Matters already has most of the runtime home machinery.

* `api/src/transport_matters/cli/launch_options.py` `AgentHomeDirOption` defines `--agent-home-dir` as the manual home override for agent config and transcripts.
* `api/src/transport_matters/cli/__init__.py` `_resolve_home_dir_option` resolves the option once and creates it for real launches.
* `api/src/transport_matters/launch_environment.py` `HOME_DIR_ENV_BY_CLIENT` maps Claude to `CLAUDE_CONFIG_DIR` and Codex to `CODEX_HOME`.
* `api/src/transport_matters/launch_environment.py` `build_managed_child_env` writes that client home into the child environment.
* `api/src/transport_matters/launch_environment.py` `build_launch_env` writes `TRANSPORT_MATTERS_AGENT_HOME_DIR` for addon side binding when a home is supplied.

The captured launch path already builds a per run runtime home.

* `api/src/transport_matters/captured_run_context.py` `build_captured_run_context` resolves a source home, creates `<run storage>/runtime-home/<client>`, calls the overlay builder, registers runtime home teardown, and passes `runtime_home_dir` into provider invocation builders.
* `api/src/transport_matters/cli/home_seed.py` `prepare_runtime_home_overlay` creates the runtime home, symlinks source entries except local names, copies local config files, then calls the client seeder against the runtime home.
* `api/src/transport_matters/captured_claude.py` `build_claude_captured_invocation` gives the Claude child `runtime_home_dir or home_dir` and writes proxy settings into the runtime `settings.json` when an overlay exists.
* `api/src/transport_matters/captured_codex.py` `build_codex_captured_invocation` forwards `runtime_home_dir` into the shared Codex invocation builder.

The Codex CLI path is asymmetric.

* `api/src/transport_matters/cli/codex_cmd.py` `run_codex` prepares the managed Codex session before any overlay, builds the invocation with no runtime home, then calls `seed_home_dir` directly against `home_dir`.
* `api/src/transport_matters/cli/codex_cmd.py` `build_codex_invocation` already accepts `runtime_home_dir` and gives the child `CODEX_HOME=runtime_home_dir or home_dir`.
* `api/src/transport_matters/captured_codex.py` `build_codex_captured_invocation` delegates to `build_codex_invocation`, but resolves Codex addons with `force_http_fallback=False`.

Result: Claude captured launches and captured pane launches can use a runtime overlay. `transport-matters codex` (the detached CLI) currently mutates the supplied home directly because it routes through `run_codex`. There is no `desktop --agent codex` path — `desktop` launches Claude; Codex canvas panes go through `RunManager` → `build_codex_captured_invocation`, which already overlays.

## 3. RuntimeHomePlan contract

Introduce an internal `RuntimeHomePlan` object. It should be built once per managed launch after storage and client resolution, before managed session preparation.

Conceptual shape:

```python
@dataclass(frozen=True, slots=True)
class RuntimeHomePlan:
    client_name: str
    content_source: Path | None
    auth_source: Path | None
    hook_trust_source: Path | None
    child_home: Path | None
    descriptor_home: Path | None
    template_provenance: RuntimeTemplateProvenance | None
    mode: Literal["native", "manual", "template", "proxy_only"]
```

Roles:

| Field | Meaning | Populated by | Default when no runtime template |
| --- | --- | --- | --- |
| `content_source` | Home whose reusable content is materialized into the runtime home. For template mode this is `.agent-runtimes/<name>` or the resolved registry path. | Runtime home planner | Current source home from `resolve_source_home_dir`. |
| `auth_source` | Native home used for account metadata and credential token links. | Runtime home planner | Same as `content_source`. |
| `hook_trust_source` | Home path that produced Codex `config.toml` hook trust keys. | Runtime home planner | Same as `content_source`. |
| `child_home` | Home passed to `build_managed_child_env`, so Claude reads `CLAUDE_CONFIG_DIR` and Codex reads `CODEX_HOME` from here. | Overlay helper | Existing home when no overlay exists, otherwise the runtime home. |
| `descriptor_home` | Home used by `prepare_managed_session`, `ClaudeLaunchProfile.prepare`, `CodexLaunchProfile.prepare`, descriptor encoding, and Codex rollout seed. | Runtime home planner | Existing behavior for non template launches unless a runtime home must be authoritative. |
| `template_provenance` | Stable record of the template id, resolved path, registry source, and version if available. It is never used as a live home. | Registry seam through RunManager | `None`. |

Population rules:

1. Proxy only or disabled client: all home fields may be `None`; no overlay is built.
2. Native mode: no `--agent-home-dir` and no runtime template. Use the native home as source if an overlay is built. Keep current operator visible behavior.
3. Manual mode: `--agent-home-dir` supplied and no runtime template. Preserve the flag semantics. The supplied home remains the manual source.
4. Template mode: `content_source` is the resolved `.agent-runtimes` template, `auth_source` is the native home, `hook_trust_source` is the template, `child_home` is the per run runtime home, `descriptor_home` is the same per run runtime home, and `template_provenance` records the template.

Ownership:

* `captured_run_context.py` should build or receive the plan for captured paths.
* `cli/codex_cmd.py` should use the same overlay block through a shared helper before `prepare_managed_session`.
* `run_manager.py` `RunManager._captured_request` is the desktop boundary that should pass the internal template reference into `CapturedRunRequest`.
* `captured_run_models.py` `CapturedRunRequest` should gain an internal optional field for the resolved template reference. This field is not a CLI flag.

## 4. Durability invariant

Invariant for template mode:

> The child transcript root, the owned source descriptor, the tailer cursor source, and the Codex rollout seed must all resolve under `RuntimeHomePlan.descriptor_home`, and `descriptor_home` must equal `child_home` for transcript producing directories.

Why this is load bearing:

* `api/src/transport_matters/captured_run_context.py` `build_captured_run_context` currently builds `runtime_home_dir`, then calls `prepare_managed_session` with `request.home_dir`.
* `api/src/transport_matters/cli/launch_profile.py` `prepare_managed_session` passes that home into the profile.
* `api/src/transport_matters/cli/launch_profile.py` `ClaudeLaunchProfile.prepare` computes the descriptor with `claude_projects_root(home_dir, env)`.
* `api/src/transport_matters/cli/launch_profile.py` `CodexLaunchProfile.prepare` seeds the rollout with `codex_sessions_root(home_dir, env)`.
* `api/src/transport_matters/cli/codex_session.py` `seed_codex_session` creates the rollout path when `write=True`.
* `api/src/transport_matters/index/tailer.py` `register_session_cursor` tails the exact owned source descriptor when present.
* `api/src/transport_matters/captured_claude.py` `build_claude_captured_invocation` and `api/src/transport_matters/cli/codex_cmd.py` `build_codex_invocation` point children at `runtime_home_dir or home_dir`.

For a pristine template, `projects/` and `sessions/` should be local runtime directories, so a source bound descriptor points at the wrong path. If Codex seeds under the template, `seed_codex_session` can create `sessions/` in the template and break the template mutation contract.

Required proof test:

1. Create a pristine Claude template with no `projects/`.
2. Launch through the planner in template mode with a fake child home under a run directory.
3. Assert `ClaudeLaunchProfile.prepare` receives `descriptor_home=child_home` and that `register_session_cursor` decodes the owned descriptor path under the runtime `projects/` directory.
4. Create a pristine Codex template with no `sessions/`.
5. Assert `CodexLaunchProfile.prepare` seeds under runtime `sessions/`, the child receives `CODEX_HOME=child_home`, and the template still has no `sessions/` after preparation.

This test should fail against current code because descriptors and Codex rollout seeds use `request.home_dir` while children use the runtime home.

## 5. Auth and credential handling

Auth splits into account metadata, credential tokens, and trust state.

### Account metadata

* Claude metadata comes through `api/src/transport_matters/cli/home_seed.py` `ClaudeSeeder.seed`, which reads `_default_claude_config_path(env)` and fills `userID` and `oauthAccount` only when absent in the runtime `.claude.json`.
* Codex auth currently comes through `api/src/transport_matters/cli/home_seed.py` `CodexSeeder.seed`, which reads `_default_codex_home(env)` and copies `auth.json` if missing.
* `api/src/transport_matters/cli/home_seed.py` `_copy_secret_file_if_missing` is delta only because it uses create exclusive behavior and returns when the target exists.

Template mode must point the seeder `seed_env` at `auth_source` for metadata. The template must be secret free, otherwise template fields shadow native auth.

### Credential tokens

Credential tokens must be symlinked from the native auth home, not copied, in template mode.

* Claude Linux token: symlink `.credentials.json` from native Claude home when it exists. macOS normally relies on Keychain as the same OS user, but the symlink rule remains safe when the file exists.
* Codex token: symlink `auth.json` from native Codex home.

Trust implication: the ephemeral runtime home shares the operator's live credential token by reference. Any process with read access to the runtime home can reach that token during the run. Rotation writes through to native and survives runtime teardown.

### Content config

Template content stays template sourced.

* Claude `settings.json` and `.claude.json` should be copied from `content_source` into the runtime home, then mutated only in the runtime home.
* Codex `config.toml` should be copied from `content_source` into the runtime home.
* `api/src/transport_matters/cli/home_seed.py` `_source_claude_config_path` currently prefers `env[CLAUDE_CONFIG_DIR]`. Template mode must pin the content `.claude.json` read to `content_source` and ignore auth env for that read.

### Trust state

* Claude project trust remains cwd keyed through `api/src/transport_matters/cli/home_seed.py` `_ensure_claude_trust`.
* Codex project trust remains cwd keyed through `api/src/transport_matters/cli/home_seed.py` `_merge_codex_project_trust`.
* Codex hook trust is path sensitive. `api/src/transport_matters/cli/home_seed.py` `_relocate_codex_hook_trust_state` must use `hook_trust_source=content_source` and `overlay_home=child_home` so template rooted hook trust keys are repointed into the runtime home.

Required auth probes:

1. Linux Claude pristine template launch with native `.credentials.json` symlinked from auth source.
2. macOS Claude pristine template launch using the same OS user and Keychain account metadata.
   **Owner-verified 2026-06-15:** Claude auths from a TM-managed overlay home on macOS because the token
   lives in the user's login Keychain (per-user, home-independent), so any launch by the authed user reads
   it regardless of which home is the content source. Template mode reuses this exact path; the only
   template-specific delta is that `oauthAccount` is *injected* (template is secret-free) rather than
   copied-along — this probe confirms that injection path; there is no Keychain risk.
3. Codex token refresh simulation proving `auth.json` writes through the native symlink.
4. Negative test proving a template that contains `oauthAccount`, `userID`, `.credentials.json`, or `auth.json` is rejected before launch.

## 6. Materialization policy

Template mode uses explicit materialization. Symlink only content expected to be read only. Keep writable state local to the runtime home. Link rotating credential tokens to native auth, never to the template.

### Local runtime set

Claude local runtime entries:

* `.claude.json`
* `settings.json`
* `projects`
* `daemon`
* `daemon.lock`
* `daemon.log`
* `daemon.status.json`
* `jobs`
* known cache or state directories found by the writer audit

Claude native token links:

* `.credentials.json`, when present in native auth home

Codex local runtime entries:

* `config.toml`
* `sessions`
* known cache or state directories found by the writer audit

Codex native token links:

* `auth.json`

Never symlink to the template:

* `.git`
* `projects`
* `sessions`
* credential token files
* any path classified writable by the audit
* unknown top level directories in template mode unless the registry marks them read only

Current code to replace or parameterize:

* `api/src/transport_matters/cli/home_seed.py` `_symlink_source_home_entries` symlinks every source top level entry except local names and `.git`.
* `api/src/transport_matters/cli/home_seed.py` `_CLAUDE_OVERLAY_LOCAL_NAMES` does not include `projects`.
* `api/src/transport_matters/cli/home_seed.py` `_CODEX_OVERLAY_LOCAL_NAMES` does not include `sessions`.
* `api/src/transport_matters/cli/home_seed.py` `_copy_overlay_local_files` copies Codex `auth.json`, which is unsafe for token rotation under ephemeral teardown.

### Checkable template never mutated property

A template mode test must snapshot the template tree before launch preparation, run overlay materialization, seeding, descriptor preparation, proxy settings application, and Codex rollout seeding, then compare the template tree after. The only allowed changes are none. If the test sees new `sessions/`, new `projects/`, modified config, modified trust state, or credential writes in the template, the launch contract fails.

## 7. Contracts

### Template secret free

A runtime template must contain reusable content only. It must not contain live credentials or account identifiers.

Reject at launch when template mode finds any of these:

* Claude `.credentials.json`
* Codex `auth.json`
* Claude `.claude.json` fields `oauthAccount` or `userID`
* Codex auth material in `config.toml`, if future Codex versions move credentials there

Rationale: current seeders are delta only. `ClaudeSeeder.seed` preserves existing `oauthAccount` and `userID`, and `_copy_secret_file_if_missing` preserves existing files. A non secret free template silently shadows native auth.

### MCP and home state durability

MCP or tool state written during a template run must be one of these:

1. Home external, such as a global store outside the runtime home.
2. Transcript derivable, such that replay can reconstruct it.
3. Explicitly captured by a future durability mechanism.

Current durable transcript paths:

* `api/src/transport_matters/addon_runtime.py` `load_capture_runtime` constructs `SessionWriter`, `TranscriptTailer`, and a transcript snapshot writer.
* `api/src/transport_matters/storage/transcript_snapshot.py` `make_transcript_snapshot_writer` appends consumed transcript bytes under Tier 1 storage.
* `api/src/transport_matters/session/writer.py` `SessionWriter.submit_blocking` durably commits event batches to Postgres.

This durability covers transcripts. It does not cover arbitrary files written under the runtime home.

## 8. Codex unification

The Codex path should reuse the overlay block, not the captured Codex helper.

Required shape:

1. Extract the overlay planning and materialization block from `api/src/transport_matters/captured_run_context.py` `build_captured_run_context` into a shared helper.
2. In `api/src/transport_matters/cli/codex_cmd.py` `run_codex`, call that helper after `prepare_launch` and addon resolution, before `prepare_managed_session`.
3. Pass `RuntimeHomePlan.descriptor_home` to `prepare_managed_session`.
4. Pass `RuntimeHomePlan.child_home` to `build_codex_invocation` as `runtime_home_dir`.
5. Delete the direct `seed_home_dir(CLIENT_NAME_CODEX, home_dir=home_dir, ...)` call from `run_codex` when a runtime home is active.
6. Keep `run_codex` on `build_codex_invocation` so `--force-http-fallback` remains preserved through `resolve_codex_addons_and_ca`.
7. Codex launches are the `transport-matters codex` CLI (`run_codex`) and Codex canvas panes (`RunManager` → `build_codex_captured_invocation`); there is no `desktop --agent codex` path, so no desktop change is needed.

Do not route CLI Codex through `api/src/transport_matters/captured_codex.py` `build_codex_captured_invocation` unless that helper first accepts and preserves the force HTTP fallback setting.

## 9. `.agent-runtimes` registry seam

The registry is external to this spec. Transport Matters expects a resolved runtime template reference, not raw registry traversal logic.

Thin interface expected by Transport Matters:

```python
@dataclass(frozen=True, slots=True)
class RuntimeTemplateRef:
    template_id: str
    client_name: Literal["claude", "codex"]
    template_home: Path
    provenance: Mapping[str, str]
```

Transport Matters requirements:

* The reference arrives through an internal `CapturedRunRequest` field, populated by desktop or RunManager.
* The reference is canonicalized before planning.
* The reference does not override `--agent-home-dir`.
* The planner derives native auth homes through existing defaults unless the registry contract later supplies an explicit auth source.
* The template path is recorded as provenance in launch facts, not as the live descriptor home.
* Template secret free validation runs inside Transport Matters even if the generator also validates.

Suggested owner boundary:

* Registry and generator: enumerate `.agent-runtimes`, create template homes, enforce generator side no secrets (templates are secret-free; the generator **never injects runtime credentials** — that is TM's launch-time job).
* Transport Matters: consume a resolved reference, build `RuntimeHomePlan`, materialize runtime home, **inject native credentials (symlink `.credentials.json` / Codex `auth.json` from the native auth home — Slice 2)**, launch child, and prove durability.

## 10. Implementation plan

### Slice 1: shared runtime home helper and descriptor binding

**Status (2026-06-15): implemented in PR #118** (`feat/runtime-home-slice1` @ `9fdd7c9`), gate green (1388 passed).
**Owner-roadtested:** `tm desktop` → spawn Codex against a pristine template → `auth.json` carried over, auth
works (no re-auth). MoE code review: Reviewer A (Claude) clean; Reviewer B (Codex) pending.

**Auth-source requirement (validated on disk 2026-06-15):** the unified Codex/Claude seed MUST source
auth from the **native home** (`~/.codex` / `~/.claude`) as the fallback, NOT from the content
`--agent-home-dir`. The current overlay seeds auth from the `--agent-home-dir`, so a pristine home yields
no `auth.json` and Codex re-auths — a **live desktop/canvas-pane bug** (proven: a desktop-launched Codex
against a pristine `skill-matters` template had `auth.json` missing, while the `codex` CLI worked because it
copies native auth in-place). Routing `run_codex` onto the overlay therefore must keep native as the auth
source: this preserves current CLI behavior AND fixes the live desktop-pane Codex auth bug. (The full
content/auth/hook-trust split + credential-token symlinks for the pristine-template case remain Slice 2.)

Deliverables:

* Extract shared overlay planning and materialization from `build_captured_run_context`.
* Add `RuntimeHomePlan` with current behavior defaults.
* Route `run_codex` through the shared helper while preserving `build_codex_invocation` and `--force-http-fallback`.
* Move the overlay build ahead of `prepare_managed_session` in Codex.
* Bind owned descriptors, tailer descriptor paths, and Codex rollout seed to the runtime home in template mode.
* Make `projects` and `sessions` local wherever descriptor binding depends on local runtime transcript roots.
* Remove the direct Codex `seed_home_dir` call for runtime home launches.
* **Build the generic launch-field carrier (shared seam, owned by this workstream).** A single generic
  "extra launch field carried through `Settings` → `_launch_run_context` → binding overlay" mechanism, set
  once where `minted`/`source_descriptor` already ride (`_register_owned_cursor` / `register_session_cursor`
  `model_copy`). `runtime_template` rides it here; **B6 continuation lineage fields (`continueFromSessionId`
  / `parentSessionId` / `forkedAtSeq`) ride the same carrier** (cross-workstream agreement 2026-06-15) so
  the seam is edited once. Keep the carrier field-agnostic; consumers add their own fields.

Tests:

* Failing first: Codex pristine template should currently create or expect template `sessions`; after the slice it seeds runtime `sessions` and leaves template unchanged.
* Failing first: Claude pristine template descriptor should currently resolve outside runtime `projects`; after the slice it resolves under runtime `projects`.
* Regression: `--force-http-fallback` still reaches `resolve_codex_addons_and_ca` from `run_codex`.
* Regression: existing manual `--agent-home-dir` tests in `api/src/transport_matters/cli/test_home_seed.py` and `api/src/transport_matters/cli/test_launch_profile.py` continue to pass.

Gate:

* `cd api && just check && just test`

### Slice 2: explicit source split and credential token links

**Owner: this (ephemeral runtime-home) workstream.** Credential-token injection — symlinking Claude
`.credentials.json` and Codex `auth.json` from the native auth home — lives in the overlay/seeder
(`cli/home_seed.py` materialization). It is NOT owned by B6 (which only drops `homeDir` from the API shape
and never touches home materialization) and NOT by the `.agent-runtimes` registry/generator (which produces
secret-free templates and must never inject runtime credentials). The `.credentials.json` symlink-from-native
is the open auth item; macOS is already owner-verified (Keychain, §5).

Deliverables:

* Split `content_source`, `auth_source`, and `hook_trust_source` in the overlay and seeder contract.
* Point seeder `seed_env` at native auth for template mode.
* Pin content config reads to `content_source`, including Claude `.claude.json` despite auth env.
* Symlink Claude `.credentials.json` from native when present.
* Symlink Codex `auth.json` from native.
* Repoint Codex hook trust from `hook_trust_source` to `child_home`.

Tests:

* Claude `.claude.json` and `settings.json` come from template content, while `oauthAccount` and `userID` come from native when absent from template runtime copy.
* Codex `config.toml` comes from template content, while `auth.json` is a symlink to native.
* Codex hook trust keys from template `config.toml` are repointed to the runtime home.
* Token rotation simulation writes through the native symlink.
* Linux and macOS auth probes are recorded. Automated Linux should be a test. macOS can be a documented manual gate until CI covers it.

Gate:

* `cd api && just check && just test`
* macOS Claude auth: **owner-verified 2026-06-15** (Keychain is user-scoped / home-independent; manually
  confirmed). The slice-2 macOS step is now a confirmation of the `oauthAccount`-injection path, not an open
  risk. Linux auth (the file-based `.credentials.json` symlink-from-native) is the open auth item and must
  pass its automated test before enabling template mode on Linux.

### Slice 3: materialization policy and writer audit

Deliverables:

* Replace catch all template symlinking with an allow list materialization policy.
* Keep writable paths local per client.
* Enforce template secret free validation at launch.
* Enumerate Transport Matters home writers and known client writable paths.
* Document MCP state contract in the operator or developer docs.
* Add template tree before and after mutation tests.

Tests:

* Template tree remains byte identical after overlay build, seeding, descriptor preparation, proxy settings application, and Codex rollout seed.
* Known writable dirs are local and not symlinks to the template.
* Unknown template top level dirs are rejected or require explicit read only classification.
* Template secrets are rejected.

Gate:

* This slice gates template mode `rmtree` teardown. Native overlay teardown may keep existing behavior. New template launches must not delete their runtime home by default until this slice passes, otherwise undiscovered home writes can be lost before the audit is complete.
* `cd api && just check && just test`

### Slice 4: registry seam and desktop request plumbing

Deliverables:

* Add internal `CapturedRunRequest.runtime_template` or equivalent.
* Add `SpawnRun` and `RunManager._captured_request` plumbing for a resolved template reference.
* Keep CLI `--agent-home-dir` unchanged.
* Record `template_provenance` in launch facts without making it a live home. **Note (Slice 1 MoE review):**
  the Slice 1 launch-field carrier rides extras **in-memory only** — `SessionBinding` lacks `extra="allow"`,
  so carrier extras drop on `model_dump`. Persisting provenance here therefore needs a **real declared field**
  on the binding/facts model, not a carrier extra.
* Add end to end desktop captured run tests for Claude and Codex template launches.

Tests:

* RunManager passes template reference through to the planner.
* Launch facts record provenance and runtime descriptor separately.
* Codex via the `transport-matters codex` CLI (`run_codex`) and via Codex canvas panes preserves proxy and CA behavior; there is no `desktop --agent codex` path to cover.
* End to end fake child writes a transcript under runtime home and the tailer registers that exact path.

Gate:

* `cd api && just check && just test`
* If frontend request schema changes, run the relevant `www` gate.

## 11. Open questions and risks

* Claude macOS Keychain behavior is **owner-verified 2026-06-15**: same-user Keychain access is
  home-independent, so an overlay/template home auths as long as the user is natively authed (which TM
  already requires). Residual macOS confirmation is only the secret-free-template `oauthAccount`-injection
  path; no Keychain risk. The open auth item is **Linux**, where the token is the `.credentials.json` file
  (not Keychain) and template mode must symlink it from native (Slice 2).
* Codex token rotation semantics should be confirmed. Symlink from native is the safe default because copied refresh tokens can become stale after teardown.
* The writer audit may discover client or MCP state that should be retained. Those paths need a product decision: home external, transcript derivable, captured separately, or intentionally ephemeral.
* Historical run descriptors may contain old absolute home paths. This spec only governs new template mode launches.
* Unknown `.agent-runtimes` template content can become writable through child tools. The registry should mark read only content, and Transport Matters should reject unknown writable ambiguity.
* Current `sessions.json` facts are legacy debt, but launch facts still carry descriptor context. Template provenance should avoid increasing reliance on duplicated disk facts.

## 12. Cross-dependency — B6 curated product API
Source: `~/.mdx/projects/tm-b6-api-proposal.md` (B6 v2, reviewed, 0 blockers). B6 and this spec are
mostly aligned — B6's `homeDir` drop explicitly cites `descriptor_home` + `rmtree`-at-teardown +
`template_provenance`. Feedback sent to the B6 orchestrator (`transport-matters:general:1:2.1`) 2026-06-15.
Four intersections:

1. **B6 continuation depends on this spec's durability invariant (§4) — the load-bearing one.** B6
   Decision 4 primes continuation context "from the Postgres transcript." That transcript only exists for
   ephemeral/template runs if the owned descriptor + tailer cursor + Codex rollout bind to the runtime home
   (§4 / Slice 1). Until Slice 1 lands, an ephemeral run's `register_session_cursor` tails the deleted
   template home and Postgres gets nothing → B6 continuation primes from an empty transcript. **B6
   build-order step 4 is downstream of this spec's Slice 1.**
2. **Shared launch plumbing.** B6 continuation and this spec's Slice 4 both thread a new field through
   `CreateRunRequest` → `SpawnRun` → `CapturedRunRequest` and `Settings` → `_launch_run_context` (B6:
   `continueFromSessionId` + lineage; here: `runtime_template`). Establish one "carry a new launch field
   through the `Settings` hop" pattern; avoid duplicate edits to `_launch_run_context` /
   `RunManager._captured_request`.
3. **`template_provenance` vocabulary.** B6 will surface structured `template_provenance` (not a raw path)
   if provenance becomes a product need. Align it with this spec's `RuntimeTemplateProvenance` /
   `RuntimeTemplateRef` so launch-facts provenance and any curated-API provenance share one structure.
4. **Slice 4 targets `/v1`.** B6 step 2 migrates the runs family to curated `/v1` `CreateRunRequest` and
   deletes `/api/runs`. Slice 4's `runtime_template` plumbing should target the post-B6 `/v1` shape;
   sequence Slice 4 after B6 step 2.

**Resolved 2026-06-15 (owner approved, B6 orchestrator agreed):** this workstream OWNS the generic
launch-field carrier (built in Slice 1); B6 lineage fields and `runtime_template` both ride it, and B6
step 4 binds to it rather than re-plumbing. Point 1's dependency is **template-mode-only** — current
non-template B6 continuation works today because the tailer tails the live home before teardown; the
descriptor-binding dependency bites only once template mode (Slice 4) can launch an ephemeral home.

Non-conflict: B6 "native resume impossible under ephemeral homes" is *cross-run* (native JSONL gone
post-teardown); the managed-mint rollout seed here is *intra-run* (the live run's own session across proxy
retries) and is consistent.

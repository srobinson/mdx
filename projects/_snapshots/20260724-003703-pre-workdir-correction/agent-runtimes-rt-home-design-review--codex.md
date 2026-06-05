---
title: Agent runtimes ephemeral home design review for Transport Matters
type: research
tags: [transport-matters, agent-runtimes, runtime-home, design-review, codex, claude, auth, transcripts]
summary: Adversarial review found the design direction sound, but pristine templates need runtime-home owned descriptors, explicit auth/content source split semantics, and a writer audit before ephemeral teardown.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Agent runtimes runtime-home design review

Scope: design review of `~/.mdx/projects/agent-runtimes-tm-homedir-recon--claude.md`, focused on `## Design: ephemeral .agent-runtimes homes` and verified against `api/src/transport_matters`.

No code was changed. Source citations use file plus symbol, without line numbers.

## Executive summary

The design direction is good: Transport Matters already has a reusable per-run home overlay, and Codex should stop mutating `--agent-home-dir` directly. The design is not implementation-ready as filed because the owned transcript descriptor, Codex rollout seed, and addon home still bind to the source or template while the child reads the runtime home. That breaks pristine templates for both live transcript tailing and Codex resume.

## Load-bearing claims

### 1. `prepare_runtime_home_overlay` `seed_env` is the auth hook

Verdict: **partly verified, but overloaded**.

Evidence:

- `api/src/transport_matters/cli/home_seed.py` `prepare_runtime_home_overlay` builds `seed_env`, sets `HOME_DIR_ENV_BY_CLIENT[client_name]` to `source_home_dir`, then calls `seed_home_dir` against `runtime_home_dir`.
- `api/src/transport_matters/cli/home_seed.py` `ClaudeSeeder.seed` reads `_default_claude_config_path(env)` and copies `userID` plus `oauthAccount` into the runtime `.claude.json`.
- `api/src/transport_matters/cli/home_seed.py` `CodexSeeder.seed` reads `_default_codex_home(env)` and copies `auth.json` into the runtime home.

The env hook can point seeders at a native auth source. The same env value also drives Codex hook trust relocation, so using it as the only split-source knob conflates auth source with content source.

### 2. `_copy_overlay_local_files` can be cleanly split between content and auth

Verdict: **refuted as a one-parameter change**.

Evidence:

- `api/src/transport_matters/cli/home_seed.py` `_copy_overlay_local_files` copies Claude `settings.json` and `.claude.json`, or Codex `auth.json` and `config.toml`, from one `source_home_dir`.
- `api/src/transport_matters/cli/home_seed.py` `_copy_secret_file_if_missing` is file-level only. It does not merge per-field content and auth.
- `api/src/transport_matters/cli/home_seed.py` `CodexSeeder.seed` uses `_default_codex_home(env)` as `source_home` for `_relocate_codex_hook_trust_state`.

For runtime templates, `settings.json` and `config.toml` are content, while `auth.json` and selected `.claude.json` fields are auth. Codex hook trust relocation must use the content template path as its source, while Codex auth must come from the native home. That requires an explicit overlay plan, not only `seed_env` redirection.

### 3. Codex rollout seed ordering breaks pristine templates

Verdict: **verified, and the same source/runtime split affects Claude descriptors**.

Evidence:

- `api/src/transport_matters/captured_run_context.py` `build_captured_run_context` creates `runtime_home_dir`, then calls `prepare_managed_session` with `home_dir=request.home_dir`.
- `api/src/transport_matters/cli/launch_profile.py` `prepare_managed_session` passes that `home_dir` into `profile.prepare`.
- `api/src/transport_matters/cli/launch_profile.py` `CodexLaunchProfile.prepare` calls `codex_sessions_root(home_dir, env)` and seeds the rollout there.
- `api/src/transport_matters/cli/codex_session.py` `seed_codex_session` writes the minimal rollout to the supplied sessions root.
- `api/src/transport_matters/cli/codex_cmd.py` `build_codex_invocation` sets the child home with `home_dir=runtime_home_dir or home_dir`.

For a pristine template, `sessions/` is absent and therefore not symlinked into the runtime overlay. The rollout seed lands under the source/template home, while the child reads `CODEX_HOME=<runtime>/sessions`.

Claude has a parallel descriptor problem:

- `api/src/transport_matters/cli/launch_profile.py` `ClaudeLaunchProfile.prepare` computes the owned source descriptor under `claude_projects_root(home_dir, env)`.
- `api/src/transport_matters/captured_claude.py` `build_claude_captured_invocation` gives the child `CLAUDE_CONFIG_DIR=runtime_home_dir or home_dir`.
- `api/src/transport_matters/index/tailer.py` `register_session_cursor` tails the exact owned `source_descriptor` when present.

With a pristine Claude template and local `projects/`, the descriptor points at the template home, while the child writes under the runtime home.

### 4. The overlay block can be extracted and reused by `run_codex`

Verdict: **mostly verified, but do not route through captured Codex blindly**.

Evidence:

- `api/src/transport_matters/cli/codex_cmd.py` `run_codex` currently calls `prepare_managed_session`, builds the Codex invocation, then directly calls `seed_home_dir` on `home_dir`.
- `api/src/transport_matters/cli/codex_cmd.py` `build_codex_invocation` already accepts `runtime_home_dir` and prefers it for child `CODEX_HOME`.
- `api/src/transport_matters/captured_run_context.py` `build_captured_run_context` contains the reusable overlay construction and teardown.
- `api/src/transport_matters/captured_codex.py` `build_codex_captured_invocation` hardcodes `force_http_fallback=False` when it resolves Codex addons and CA.
- `api/src/transport_matters/cli/__init__.py` `desktop` routes `--agent codex` through `run_codex`, preserving the user-facing `force_http_fallback` option.

Extracting a shared overlay helper is clean. Reusing the captured Codex path as-is would silently drop the CLI and desktop `force_http_fallback` surface.

### 5. Per-run runtime home plus `rmtree` is ephemeral and concurrency-safe

Verdict: **verified for the runtime home path**.

Evidence:

- `api/src/transport_matters/cli/launch_runtime.py` `resolve_storage_dir` defaults to `run_root(working_dir, run_id)`.
- `api/src/transport_matters/workspace.py` `run_root` makes the per-run path include the run UUID.
- `api/src/transport_matters/captured_run_context.py` `build_captured_run_context` uses `<resolved_storage>/runtime-home/<client>` and registers `shutil.rmtree(runtime_home_root, ignore_errors=True)` on the exit stack.

This proves path isolation. It does not prove all needed state survives teardown.

### 6. Transcript durability makes ephemeral teardown safe

Verdict: **partly verified, too broad as stated**.

Evidence:

- `api/src/transport_matters/addon_runtime.py` `load_capture_runtime` constructs a `SessionWriter`, `TranscriptTailer`, and `make_transcript_snapshot_writer`.
- `api/src/transport_matters/index/tailer.py` `TranscriptTailer.__init__` accepts both `submit_batch` and `snapshot` callbacks.
- `api/src/transport_matters/storage/transcript_snapshot.py` `make_transcript_snapshot_writer` writes tailed transcript bytes under Tier-1 storage.
- `api/src/transport_matters/session/writer.py` `SessionWriter.submit_blocking` commits normalized transcript events to Postgres.

Transcript bytes and normalized transcript events are durable. Arbitrary writes into the agent home are outside that durability path unless they appear in the transcript and are later extracted from transcript events.

## Issues

### Blocker: owned transcript descriptors and Codex rollout seeds still point at the source home

Evidence:

- `api/src/transport_matters/captured_run_context.py` `build_captured_run_context` prepares `runtime_home_dir`, then calls `prepare_managed_session` with `request.home_dir`.
- `api/src/transport_matters/cli/launch_profile.py` `ClaudeLaunchProfile.prepare` and `CodexLaunchProfile.prepare` compute descriptors under the passed `home_dir`.
- `api/src/transport_matters/cli/codex_cmd.py` `build_codex_invocation` and `api/src/transport_matters/captured_claude.py` `build_claude_captured_invocation` point the child at `runtime_home_dir or home_dir`.
- `api/src/transport_matters/index/tailer.py` `register_session_cursor` tails the owned descriptor exactly.

Impact: pristine templates lack pre-existing `projects/` or `sessions/` symlinks. The child writes under the runtime home, while tailing and Codex resume seed under the template/source home. Claude live transcript capture and Codex resume can miss their files.

One-line fix: make runtime-template mode prepare managed sessions and owned descriptors against the runtime home, while recording template provenance separately.

### Blocker: source splitting through `seed_env` breaks Codex hook trust relocation

Evidence:

- `api/src/transport_matters/cli/home_seed.py` `prepare_runtime_home_overlay` uses one `source_home_dir` for symlinks, local file copies, and the seed env.
- `api/src/transport_matters/cli/home_seed.py` `_copy_overlay_local_files` copies `config.toml` from that same source.
- `api/src/transport_matters/cli/home_seed.py` `CodexSeeder.seed` derives `source_home` from `_default_codex_home(env)` and passes it to `_relocate_codex_hook_trust_state`.
- `api/src/transport_matters/cli/home_seed.py` `_relocate_codex_hook_trust_state` only rewrites hook state keys whose path prefix matches `source_home`.

Impact: if `config.toml` comes from the template but `seed_env[CODEX_HOME]` points at native auth, hook trust keys rooted at the template path are not repointed to the runtime home. The design loses the existing hook trust behavior it is trying to preserve.

One-line fix: pass distinct `content_home`, `auth_home`, and `hook_trust_source_home` through the overlay/seeder contract.

### Major: template write-through remains possible through catch-all symlinks

Evidence:

- `api/src/transport_matters/cli/home_seed.py` `_symlink_source_home_entries` symlinks every top-level source entry except local names and `.git`.
- `api/src/transport_matters/cli/home_seed.py` `_CLAUDE_OVERLAY_LOCAL_NAMES` includes copied Claude config and daemon/job names, but not `projects` or arbitrary caches.
- `api/src/transport_matters/cli/home_seed.py` `_CODEX_OVERLAY_LOCAL_NAMES` includes only `auth.json` and `config.toml`.

Impact: a template that already has `projects/`, `sessions/`, cache directories, memory directories, MCP state, or hook state files can be mutated through runtime-home symlinks. The statement "template never mutated" only holds for a pristine source with no writable extra entries.

One-line fix: runtime-template mode should use an allow-list materialization plan and keep known writable dirs local instead of symlinking unknown top-level entries back to the template.

### Major: home writer audit is sequenced after the feature that deletes the home

Evidence:

- `api/src/transport_matters/cli/home_seed.py` `ClaudeSeeder.seed`, `CodexSeeder.seed`, `apply_claude_proxy_env_settings`, and `api/src/transport_matters/cli/codex_session.py` `seed_codex_session` are Transport Matters writers into agent homes.
- `api/src/transport_matters/cli/home_seed.py` `_symlink_source_home_entries` lets client and MCP process writes reach any symlinked source entry.
- `api/src/transport_matters/addon_runtime.py` `load_capture_runtime`, `api/src/transport_matters/storage/transcript_snapshot.py` `make_transcript_snapshot_writer`, and `api/src/transport_matters/session/writer.py` `SessionWriter` capture transcript data, not arbitrary home state.

Impact: memories, MCP server state, subprocess side effects, caches, and CLI-local state can be lost on `rmtree` if they are kept local, or mutate the template if symlinked. The proposed slice order puts the memories audit after ephemeral runtime mode, which is too late.

One-line fix: move writer enumeration and the materialization policy before enabling runtime-template teardown.

### Major: Claude auth injection is not proven by source

Evidence:

- `api/src/transport_matters/cli/home_seed.py` `ClaudeSeeder.seed` copies only `userID` and `oauthAccount` from the configured Claude config path.
- `api/src/transport_matters/cli/home_seed.py` `_copy_overlay_local_files` copies `.claude.json` and `settings.json` from one source home.
- `api/src/transport_matters/cli/home_seed.py` `_symlink_source_home_entries` would carry any native credential file only when the native home is also the content source.

Impact: a pristine content template with auth injected from native does not explicitly materialize a Claude credential file. macOS Keychain may make the same-user launch succeed, but the current source does not prove that, and non-Keychain or moved-home behavior needs a defined fallback.

One-line fix: add a live macOS auth probe plus explicit credential materialization rules for `.credentials.json` or any successor credential file when Keychain is insufficient.

### Minor: Codex overlay reuse must preserve CLI-only flags and launcher semantics

Evidence:

- `api/src/transport_matters/captured_codex.py` `build_codex_captured_invocation` calls `resolve_codex_addons_and_ca` with `force_http_fallback=False`.
- `api/src/transport_matters/cli/codex_cmd.py` `run_codex` accepts `force_http_fallback` and passes it into `resolve_codex_addons_and_ca`.
- `api/src/transport_matters/cli/__init__.py` `desktop` passes desktop `force_http_fallback` through to `run_codex` for `--agent codex`.

Impact: moving Codex CLI and desktop directly onto the captured helper can regress forced HTTP fallback. The CA handling and child `CODEX_HOME` plumbing are already reusable if the existing Codex invocation path stays in control.

One-line fix: extract only the runtime-home overlay setup first, or extend the captured Codex request and helper to carry `force_http_fallback` explicitly.

## Design holes requested by the brief

### A. Writers into the agent home

Verified Transport Matters writers:

- `api/src/transport_matters/cli/home_seed.py` `_copy_overlay_local_files`: copies Claude `settings.json`, Claude `.claude.json`, Codex `auth.json`, and Codex `config.toml`.
- `api/src/transport_matters/cli/home_seed.py` `ClaudeSeeder.seed`: writes runtime `.claude.json` trust/onboarding/auth metadata and `settings.json` dangerous prompt skip.
- `api/src/transport_matters/cli/home_seed.py` `CodexSeeder.seed`: writes runtime `auth.json` if missing, hook trust relocation, and project trust in `config.toml`.
- `api/src/transport_matters/cli/home_seed.py` `apply_claude_proxy_env_settings`: writes Claude `settings.json` `env` values in the runtime home.
- `api/src/transport_matters/cli/codex_session.py` `seed_codex_session`: writes the minimal Codex rollout under `sessions_root`.

Verified child transcript paths:

- `api/src/transport_matters/cli/home_seed.py` `claude_projects_root`: Claude transcripts are under `<home>/projects`.
- `api/src/transport_matters/cli/home_seed.py` `codex_sessions_root`: Codex rollouts are under `<home>/sessions`.

Risk surface:

- `api/src/transport_matters/cli/home_seed.py` `_symlink_source_home_entries` exposes every non-local top-level source entry to runtime writes.
- `api/src/transport_matters/addon_runtime.py` `load_capture_runtime` only wires transcript snapshot and Postgres transcript ingestion.

The source cannot enumerate all Claude, Codex, MCP, subprocess, or cache writes. That runtime audit must gate deletion of the ephemeral home.

### B. Template mutation paths

Current mutation paths are real:

- `api/src/transport_matters/cli/codex_cmd.py` `run_codex` directly calls `seed_home_dir` on `home_dir` today.
- `api/src/transport_matters/captured_run_context.py` `build_captured_run_context` seeds Codex owned sessions against `request.home_dir` today.
- `api/src/transport_matters/cli/home_seed.py` `_symlink_source_home_entries` can write through any symlinked template entry.

After Codex is routed through the overlay, symlink write-through and source-bound descriptor or seed writes still need fixes.

### C. macOS Keychain

The code does not prove full Claude auth for content template plus native auth source. It copies metadata fields from `.claude.json`; any credential file only arrives through native-home symlink behavior. The design needs an executable proof on macOS and a fallback for machines where Keychain plus metadata is insufficient.

### D. Codex overlay blast radius

The safe blast radius is to preserve `build_codex_invocation` and only add a runtime home. It already handles child `CODEX_HOME`, proxy env, CA certificate env, managed resume argv, and banner callers. A direct route through `build_codex_captured_invocation` must account for its hardcoded `force_http_fallback=False`.

### E. Slice sequencing

Recommended order:

1. Extract a shared runtime-home helper and make owned descriptors, tailer home, and Codex rollout seed use the runtime home for runtime-template mode. Delete `run_codex` direct source-home seeding while preserving `force_http_fallback`.
2. Split content/auth/trust sources explicitly in the overlay and seeder contract.
3. Define materialization rules for writable dirs and complete the home writer audit. This must happen before `rmtree` is enabled for template launches.
4. Add the `.agent-runtimes` registry/internal request seam and macOS auth probes.

## Bottom line

Design direction: sound. Filed sequencing and source model: not yet safe. The minimum safe design change is to introduce an explicit runtime-home plan object that separates content source, auth source, hook trust source, child home, tailer descriptor home, and template provenance.

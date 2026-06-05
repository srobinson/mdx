---
title: Transport Matters --agent-home-dir integration — recon for agent-runtimes pristine templates
type: research
tags: [transport-matters, agent-home-dir, agent-runtimes, home-overlay, pristine-template, auth, trust, recon]
summary: TM already launches Claude from a (potentially pristine) source home into a per-run ephemeral overlay; the Codex CLI/desktop path bypasses the overlay and mutates --agent-home-dir directly.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# TM `--agent-home-dir` recon (read-only)

Scope: `transport-matters` repo at `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`.
Source root: `api/src/transport_matters/`. Citations are file + symbol. No code was changed.

## TL;DR (the single most important finding)

TM **already has** a pristine-template → per-run ephemeral instance-home mechanism:
`home_seed.prepare_runtime_home_overlay` builds a per-run home that **copies** auth/config out
of the source home and **symlinks** everything else, leaving the source's auth/config bytes
untouched, then `shutil.rmtree`s the instance home at exit. **But it is only wired into the
Claude launch path and the desktop RunManager pane path.** The `transport-matters codex` CLI and
`desktop --agent codex` go through `codex_cmd.run_codex`, which **bypasses the overlay** and calls
`home_seed.seed_home_dir(...)` to **write auth + trust directly into `--agent-home-dir`**, with the
child's `CODEX_HOME` pointed at that same dir. So today a Codex runtime template is mutated on launch;
a Claude one is not. The Codex seam is half-built (`build_codex_invocation` already accepts
`runtime_home_dir`), so the clean fix is routing Codex through the same overlay.

---

## 1. How TM resolves `--agent-home-dir` and the child env it sets

- **Flag definition** — `cli/launch_options.py` `AgentHomeDirOption`: `--agent-home-dir`,
  `file_okay=False, dir_okay=True, resolve_path=False`, help "Directory for agent config and
  transcripts. Defaults to the agent native home." It is a parameter on the `claude`, `codex`, and
  `desktop` commands (`cli/__init__.py` `claude`, `codex`, `desktop`).
- **Normalization** — `cli/__init__.py` `_resolve_home_dir_option`: when set, `home_dir.expanduser().resolve()`
  and (unless `--print-command`) `mkdir(parents=True, exist_ok=True)`. Resolved **once before** the child
  can change cwd. There is **no hardcoded runtime root and no `~/.agent-runtimes` default** anywhere in TM.
- **Default (flag absent)** — `home_seed._default_claude_home` → `$CLAUDE_CONFIG_DIR` else `~/.claude`;
  `home_seed._default_codex_home` → `$CODEX_HOME` else `~/.codex`.
- **Child env vars** — `launch_environment.build_managed_child_env` maps the home onto the child via
  `HOME_DIR_ENV_BY_CLIENT = {"claude": "CLAUDE_CONFIG_DIR", "codex": "CODEX_HOME"}`. It also strips and
  re-imposes proxy/trust env so the child cannot bypass the proxy.
- **Addon/backend env var** — `launch_environment.build_launch_env` sets
  `TRANSPORT_MATTERS_AGENT_HOME_DIR` (`env_keys.AGENT_HOME_DIR`) to the same path, so the FastAPI addon's
  adapter binding and transcript `locate` resolve under the same managed home.

## 2. What TM writes into the home at launch (and the projects//sessions claim)

There are **two different launch shapes** with different write behavior.

### Claude (and any RunManager pane) — overlay, source not mutated
Path: `claude` CLI → `start_cmd.run_start` → `captured_run.run_captured_run_on_local_tty`
→ `captured_run_context.build_captured_run_context`; pane path → `captured_run.prepare_captured_run`
→ same builder. The overlay is built at `captured_run_context.build_captured_run_context` (the
`if write and prepared.client_path is not None` block):

```
source_home_dir = resolve_source_home_dir(client, home_dir=request.home_dir, env)   # = --agent-home-dir, else native
runtime_home_root = prepared.resolved_storage / "runtime-home"
runtime_home_dir  = runtime_home_root / client_name
prepare_runtime_home_overlay(client, source_home_dir=..., runtime_home_dir=..., working_dir=...)
stack.callback(shutil.rmtree, runtime_home_root, ignore_errors=True)                 # ephemeral, torn down at exit
```

`prepared.resolved_storage` is the **per-run** directory: `launch_runtime.resolve_storage_dir` returns
`run_root(working_dir, run_id)` (`{slug}/{hash}/{run_id}/`), so the instance home is
`<per-run dir>/runtime-home/<client>` — per-run and concurrency-safe.

Inside `home_seed.prepare_runtime_home_overlay`:
- `_symlink_source_home_entries` — symlinks the source's **existing** top-level entries into the
  runtime home, **except** the client's "local names" and `.git`. It runs unconditionally, but what it
  symlinks is purely a function of what is in the source dir, so it is a **no-op for a pristine custom
  template** (whose only entries — `.claude.json`/`settings.json` — are copied, not symlinked).
  Material symlinks therefore appear only when the source resolves to the **populated native home**:
  `--agent-home-dir` empty (→ `$CLAUDE_CONFIG_DIR`/`~/.claude`) or explicitly `~/.claude`. There is no
  explicit native-only guard — emptiness, not a check — so a custom home that *has* accrued
  `projects/`/`sessions/` (or any populated home) WOULD get those symlinked.
- `_copy_overlay_local_files` — **copies** (never symlinks) the auth/config files:
  Claude `settings.json` + `.claude.json`; Codex `auth.json` + `config.toml`.
- `_CLAUDE_OVERLAY_LOCAL_NAMES = {.claude.json, settings.json} ∪ {daemon, daemon.lock, daemon.log,
  daemon.status.json, jobs}` — daemon/jobs are kept **local** (not symlinked); `_assert_overlay_daemon_is_local`
  fails closed if any daemon entry resolves back to source.
- Then `seed_home_dir` runs against the **runtime** home (below), and `apply_claude_proxy_env_settings`
  writes `ANTHROPIC_BASE_URL`, `TRANSPORT_MATTERS_RUN_ID`, `TRANSPORT_MATTERS_AGENT_HOME_DIR`, `NO_PROXY`
  into the runtime `settings.json` `env` — **runtime only, never the source** (per its docstring/test
  `test_apply_claude_proxy_env_settings_updates_overlay_only`).

`ClaudeSeeder.seed` writes into the **runtime** `.claude.json`: merges `userID`/`oauthAccount` from
source, sets `hasCompletedOnboarding=true`, and `_ensure_claude_trust` sets
`projects[<cwd>].hasTrustDialogAccepted=true`; `_ensure_claude_skip_dangerous_prompt` sets
`skipDangerousModePermissionPrompt=true` in `settings.json`. **Claude history**: `ClaudeLaunchProfile.prepare`
states `claude --session-id` *creates* the transcript; TM only computes the descriptor under
`home_seed.claude_projects_root` (`<home>/projects`). The child writes `<runtime home>/projects/...`.

### Codex via CLI / `desktop --agent codex` — direct seed, home IS mutated
Path: `codex` CLI / desktop → `codex_cmd.run_codex`. It does **not** use the overlay. It calls:

```
if not print_command and home_dir is not None and prepared.client_path is not None:
    seed_home_dir("codex", home_dir=home_dir, working_dir=...)          # codex_cmd.run_codex line ~429
```

`CodexSeeder.seed` writes directly into `--agent-home-dir`:
- copies `auth.json` from native `~/.codex` if missing (`_copy_secret_file_if_missing`);
- `_relocate_codex_hook_trust_state` rewrites `config.toml` `[hooks.state]` keys;
- `_merge_codex_project_trust` writes `config.toml` `[projects."<cwd>"] trust_level = "trusted"`.

`build_codex_invocation` is called with `runtime_home_dir=None`, so the child's `CODEX_HOME` =
`runtime_home_dir or home_dir` = `--agent-home-dir`. **Codex session rollouts also land in the home**:
`CodexLaunchProfile.prepare` seeds a minimal rollout under `home_seed.codex_sessions_root`
(`<home>/sessions`) and the child appends there.

### Verify/refute the user's claim
> "tm only writes projects//sessions/ if NO --agent-home-dir is specified"

**Refuted.** The flag changes **where** history lands, not **whether** it lands:
- Claude transcripts are always written by the **claude child** (TM never writes them). They land
  under whatever `CLAUDE_CONFIG_DIR` resolves to — the per-run ephemeral runtime-home when launched
  via TM (which symlinks back to the source's `projects/` **only if the source already has one**),
  else native `~/.claude/projects`.
- Codex `sessions/` are **seeded by TM** *and* appended by the codex child, under `<home>/sessions`
  with the flag set, else `~/.codex/sessions`.

So with `--agent-home-dir` set, conversation history does **not** stay out of the home — it is
redirected **into** the managed home (Codex) or the per-run overlay home (Claude).

## 3. Is auth / trust keyed to the absolute home path?

- **Project trust** is keyed to the **project cwd (working_dir), not the home path**:
  Claude `_ensure_claude_trust` → `.claude.json["projects"][<cwd>]`; Codex `_merge_codex_project_trust`
  → `config.toml [projects."<cwd>"]`. Re-seeded every launch ⇒ moving the home does not invalidate it.
- **Codex hook trust IS path-sensitive.** `_relocate_codex_hook_trust_state` exists precisely because
  Codex keys `[hooks.state]` by the **absolute path of the hooks file under `CODEX_HOME`**. Copying
  `config.toml` into a different home would make the child recompute hooks as untrusted ("hooks need
  review") unless the table-header path prefixes are repointed. (This is exactly recent commit
  `5ea4edd fix(api): repoint Codex overlay hook trust state at the overlay home (#113)`.) TM repoints
  on every seed/overlay, so new launches are fine; a home **copied/moved without re-seed** loses hook trust.
- **Auth is file state inside the home, not path-keyed.** Claude `oauthAccount`/`userID` are copied into
  `<home>/.claude.json`; Codex `auth.json` is copied into `<home>`. The Claude **token** file
  `.credentials.json` is **not** in the copied/local set, so the overlay **symlinks** it from source
  (and on macOS the real token lives in Keychain, which TM does not touch).
- **Where state lives:** Claude → `<home>/.claude.json` + `<home>/settings.json`; Codex →
  `<home>/auth.json` + `<home>/config.toml`. No TM-managed global file outside the home; the native
  `~/.claude` / `~/.codex` is only read as the seed source.

## 4. Blast radius of moving `~/.agent-runtimes/<name>` → `~/.agent-runtimes/runtimes/<name>`

**Low for TM internals; the risk is stale persisted paths and external wiring.**
- No hardcoded runtime root in TM; `--agent-home-dir` is resolved fresh each launch. TM does not care
  where the home lives as long as the path passed is correct.
- Project trust (cwd-keyed) and auth (copied each launch) survive the move. Codex hook trust is
  path-sensitive but repointed on every seed ⇒ fine for new launches.
- **Stale on move:** absolute home paths persisted in **run records** — `launch_profile.persist_owned_session_facts(..., home_dir=...)`,
  `codex_session` descriptors (`home_dir=str(home_dir)`), workspace/launch manifests written via
  `run_with_workspace_manifest(..., home_dir=...)` / `launch_manifest`, and the live env
  `TRANSPORT_MATTERS_AGENT_HOME_DIR`. Historical runs point at the old path; read-side `locate` for those
  runs would miss. New runs are unaffected.
- **External (not TM):** the skill-matters generator, any aliases/launch scripts, and the requirement
  that the new template location actually contains valid seeded auth.

## 5. KEY — can TM launch from a pristine template into a separate instance home today?

- **Claude: YES, already.** The `run_start` path runs every Claude launch through
  `prepare_runtime_home_overlay` with `source_home_dir = --agent-home-dir` and a per-run ephemeral
  `runtime_home_dir = <run dir>/runtime-home/claude`. Auth/config/settings are **copied** (template
  bytes untouched), and the source's *existing* other entries are symlinked. **For a pristine template
  the symlink step is a no-op** (nothing but the copied files to link), so the Claude child creates a
  *local* `projects/` in the ephemeral home, which is `rmtree`d at exit (Tier-1 run dir keeps the owned
  transcript copy) — the template is never written. Symlinked write-back only happens when the source
  is populated (native `~/.claude`, reached when `--agent-home-dir` is empty or `=~/.claude`), or if a
  custom template has accrued a `projects/` dir.
- **Codex (CLI/desktop): NO.** `run_codex` seeds the home directly and points the child's `CODEX_HOME`
  at it, so the template is mutated (auth + trust + `sessions/` rollouts). Only the RunManager pane path
  (`prepare_captured_run` → `build_codex_captured_invocation`, which forwards `runtime_home_dir`) uses
  the overlay for Codex.

### Cleanest seam to make it pristine for both
The overlay seam is already **half-built for Codex**: `build_codex_invocation(... runtime_home_dir=None)`
already prefers `runtime_home_dir or home_dir` for the child's `CODEX_HOME`, and
`build_codex_captured_invocation` already forwards `runtime_home_dir`. The clean change is to route the
Codex CLI/desktop launch through the **same** `build_captured_run_context` overlay that Claude uses
(make `run_codex` delegate to `run_captured_run_on_local_tty`, or replicate
`prepare_runtime_home_overlay` + `runtime_home_dir` and **drop the direct `seed_home_dir(home_dir=home_dir)`**).
That unifies all four entry points (Claude CLI, Codex CLI, desktop, pane) on one overlay.

### Writable state that must be redirected for a *truly* pristine template
1. **History dirs** — keep `projects/` (Claude) and `sessions/` (Codex) **local** to the ephemeral
   runtime home instead of symlinking to source. Today they are symlinked when present in source
   (they are absent from `_CLAUDE_OVERLAY_LOCAL_NAMES` / `_CODEX_OVERLAY_LOCAL_NAMES`). Adding them to
   `home_seed._overlay_local_names` would stop history from ever writing back into the template.
   (Transcripts are still preserved: the Tier-1 per-run dir owns its own transcript copy.)
2. Auth/config/settings — already **copied**, safe.
3. Claude daemon/jobs — already forced **local** (`_assert_overlay_daemon_is_local`).
4. Codex hook trust — already **relocated** into the runtime home.
5. Proxy route settings — already written to the **runtime** `settings.json` only.

### Codex rollout-seed ordering (load-bearing for the LOE)
`build_captured_run_context` calls `prepare_managed_session` with `home_dir=request.home_dir` (the
**source**), so `CodexLaunchProfile.prepare` seeds the resume rollout at `<source>/sessions`, while the
child reads `CODEX_HOME=<runtime>/sessions`. That only resolves when `sessions/` existed in the source
**at symlink time**: true for native `~/.codex` (the path the pane exercises), but **false for a pristine
Codex template** — `sessions/` is absent, nothing is symlinked, the seed lands at `<source>/sessions`,
the child looks in `<runtime>/sessions`, and resume breaks. So routing Codex through the overlay is
correct for native/populated homes as-is, but a **pristine Codex template additionally requires seeding
the rollout into the runtime home** (thread `runtime_home_dir` into
`prepare_managed_session`/`CodexLaunchProfile.prepare`). This is the one step beyond "mirror Claude" and
the first thing to test.

## LOE — "Codex uses the same overlay as Claude"
**Small, ~half a day.** The seam is already plumbed: `build_codex_invocation` accepts `runtime_home_dir`
and prefers it for `CODEX_HOME`; the pane path already builds Codex with the overlay. Recommended path
(surgical, low blast radius): (1) extract the overlay block from `build_captured_run_context` into a
shared helper; (2) call it in `codex_cmd.run_codex` (inside its existing `ExitStack`), pass
`runtime_home_dir` into `build_codex_invocation`, and delete the direct `seed_home_dir(...)` block; (3)
tests. `desktop --agent codex` (→ `run_codex`) needs no change. Two things to validate: native `codex`
launches start running in an ephemeral `CODEX_HOME` symlinked to `~/.codex` (matches Claude), and the
rollout-seed ordering above (seed into runtime home for the pristine-template case). Full unification
(routing Codex CLI through `run_captured_run_on_local_tty`) deletes ~150 lines of duplicate lifecycle but
must de-Claude that path (`inject_system_prompt`, `--force-http-fallback` is hardcoded `False` in
`build_codex_captured_invocation`); treat as a follow-up. "Same overlay" ≠ "pristine template": the
latter is the separate Medium item above (history dirs local + rollout reseed), affecting both agents.

## Design — ephemeral `.agent-runtimes` homes (leverage + work)
**Goal.** Launch claude *or* codex from a pristine `.agent-runtimes/<name>` template into an ephemeral,
TM-owned per-run home, with **auth injected from native `~/.claude`/`~/.codex`**; template never mutated;
home `rmtree`'d at exit; durability in Postgres (+ Tier-1 raw bytes).

**Core move (one idea).** The overlay already does ~90% of this. It just collapses two roles into one
`source_home_dir`: the *content source* (skills/config that form the home body) and the *auth source*
(`oauthAccount`/`auth.json`). The design = **split those two sources**, route *both* agents through one
overlay, and drive it from an internal request mode (no user flag).

### Leverage (DRY — reuse as-is, no change)
- `build_captured_run_context` overlay block — per-run home create + `rmtree` teardown + wiring.
- `build_managed_child_env` + `HOME_DIR_ENV_BY_CLIENT` — child `CLAUDE_CONFIG_DIR`/`CODEX_HOME` = runtime home.
- Per-run rooting `<run dir>/runtime-home/<client>` via `resolve_storage_dir`→`run_root` (ephemeral, concurrency-safe).
- `ClaudeSeeder`/`CodexSeeder`, `_relocate_codex_hook_trust_state`, `_assert_overlay_daemon_is_local`,
  `apply_claude_proxy_env_settings` — already write into the runtime home and read auth from an env-pointed source.
- Tailer → `transcript_snapshot` (Tier-1) + `SessionWriter` (Postgres) — the durability that makes ephemeral safe.
- `build_codex_invocation.runtime_home_dir` + `build_codex_captured_invocation` — already plumbed.

### Work (the deltas — minimal, surgical)
- **A. Split content vs auth source.** `prepare_runtime_home_overlay` gains an explicit `auth_source_home`
  distinct from the content `source_home_dir`; default `auth_source = source` preserves current behavior.
  Auth-from-native is ~one line: point `seed_env[CLAUDE_CONFIG_DIR/CODEX_HOME]` (home_seed.py:225) at native;
  `_copy_overlay_local_files` copies secrets from `auth_source`, content from `source`.
- **B. Route Codex through the overlay.** Extract the `build_captured_run_context` overlay block into a
  shared helper; both agents call it; delete `run_codex`'s direct `seed_home_dir`. Fixes the asymmetry.
- **C. Seed the Codex resume rollout into the runtime home** (thread `runtime_home_dir` into
  `prepare_managed_session`/`CodexLaunchProfile.prepare`) so resume resolves under `CODEX_HOME=<runtime>/sessions`.
- **D. Keep writable/history dirs local** (`projects/`, `sessions/`, caches) so nothing writes back to the template.
- **E. Internal mode + registry seam.** Add `CapturedRunRequest.runtime_template` (internal, no flag),
  populated by desktop/RunManager from the `.agent-runtimes` registry; `build_captured_run_context` maps it to
  (content=template, auth=native). `--agent-home-dir` unchanged as the manual path.
- **F. Content materialization (open).** copy vs symlink+copy-secrets vs hybrid — decide in design/impl; does NOT gate the rest.

### Bake-in considerations (consider now, build later)
- **Memories:** ephemeral is safe IFF every memory-bearing mutation is transcript-visible (→ Postgres → future
  extraction). Enumerate home writers; the risk is **out-of-band** writes (subprocess, an MCP server's own
  on-disk state) no tool call reflects — those are silently lost and unrecoverable. Shapes what must be captured/local.
- **macOS Keychain:** Claude token is in Keychain (read by child as same OS user), `.claude.json` is metadata only;
  codex `auth.json` is a real file copy. Confirm an auth-injected home fully auths Claude.

### Sequencing (independent, shippable slices)
1. **Unify + fix asymmetry** (B + C + tests) — codex stops mutating `--agent-home-dir`. ~Small (½ day). Standalone value.
2. **Split sources** (A + tests) — default preserves behavior. Small.
3. **Ephemeral `.agent-runtimes` mode** (E + D + tests) — depends on the separately-built registry contract. Medium.
4. **Materialization decision + memories audit** (F + writer enumeration). Small–Medium.

## Revised design v2 (post adversarial review — supersedes the points below in v1)
MoE reviewers Claude `7:3.1` + Codex `7:3.2` independently converged. Review files:
`agent-runtimes-rt-home-design-review--claude.md` and `--codex.md`. Net: direction sound; v1 was not
implementation-ready because owned descriptors/seeds, the auth model, and materialization were
under-specified. One Blocker against the "template never mutated" guarantee.

**Central change — a `RuntimeHomePlan` object** that makes the single conflated `source_home_dir`
explicit as distinct roles:
- `content_source` — the pristine `.agent-runtimes/<name>` template (skills/config/settings)
- `auth_source` — native `~/.claude`/`~/.codex` (oauthAccount metadata + credential token)
- `hook_trust_source` — where `config.toml` came from (the template), for `_relocate_codex_hook_trust_state`
- `child_home` / `descriptor_home` — the ephemeral runtime home (child `CLAUDE_CONFIG_DIR`/`CODEX_HOME`,
  AND where owned descriptors + the Codex rollout are computed/seeded)
- `template_provenance` — recorded in session facts, never used as a live home

**Corrected mechanisms (v1 claims that were wrong):**
- **Descriptor / tailer / rollout bind to the runtime home, not source** (BLOCKER). `prepare_managed_session`
  and the owned `source_descriptor` (Claude `claude_projects_root`, Codex `codex_sessions_root`) must compute
  against `runtime_home_dir` in template mode. Today they use `request.home_dir` (source) and
  `index/tailer.py register_session_cursor` tails the exact descriptor — so a source-bound descriptor on a
  pristine template makes the tailer watch the wrong path → **Postgres never sees the records → ephemeral
  teardown loses data.** This fix is what *makes* "ephemeral is safe" true; it is not optional.
- **Auth is NOT "copy secrets from auth_source"** (v1 claim 2 was the wrong knob). `.claude.json`/`config.toml`
  mix auth with content; copying them from native drags native projects/MCP/model config into a template run.
  Correct model: (a) `oauthAccount`/`userID` via `seed_env` pointed at native (existing seeder delta-merge);
  (b) **symlink the credential *token* file from native** — `.credentials.json` (Linux) and Codex `auth.json` —
  so the token is present AND rotation writes through to native (survives teardown); (c) pin content
  `.claude.json`/`config.toml`/`settings.json` to `content_source`, ignoring `env` for that read
  (`_source_claude_config_path` currently prefers `env[CLAUDE_CONFIG_DIR]`).
- **Materialization IS the "template never mutated" guarantee** (v1 mislabeled F as non-gating). Keep
  `projects/`, `sessions/`, and any writable content dir **local** to the runtime home (add to
  `_overlay_local_names`); symlink only read-only content. Else the Codex rollout seed + child/subprocess
  writes write **through** symlinks into the template (`seed_codex_session` even `mkdir`s `<template>/sessions`).
- **Template must be secret-free** (enforced contract). Seeders are delta-only (`if not in config` /
  `_copy_secret_file_if_missing` `O_CREAT|O_EXCL`), so a template carrying `oauthAccount`/`auth.json` silently
  shadows native auth. The `.agent-runtimes` generator (skill-matters) must guarantee no secrets in the template.

**Out-of-band writes / durability (Major):** the fan-out captures transcript+wire only. Strongest loss case is
Codex `auth.json` token rotation (copied token refreshed in the ephemeral home, lost at `rmtree`; single-use
refresh tokens → next run re-copies a stale token → auth drift) → the symlink-to-native fix above covers it.
MCP state is safe ONLY because today's servers write outside the home (cm→global, helioy-bus→`~/.helioy`,
fmm→repo `.fmm.db`); bake "MCP/home state must be home-external or transcript-derivable" into the contract.

**Codex routing (Minor):** extract the overlay *block only*; keep `run_codex` on `build_codex_invocation`
(threads `--force-http-fallback`); do NOT route through `build_codex_captured_invocation` (hardcodes
`force_http_fallback=False`). Move the overlay build ahead of `prepare_managed_session`. CA cert is
home-independent (safe). `desktop --agent codex` needs no separate change.

**Revised sequencing (v1's C-in-slice-1 / D-in-slice-3 split was broken — C is inert without sessions-local):**
1. **Slice 1 — unify + bind to runtime home.** Extract the shared overlay helper; bind owned descriptors +
   tailer descriptor + Codex rollout seed to the runtime home; **make `projects/`/`sessions/` local** (the D
   piece C depends on, shipped together); route Codex through the block; delete `run_codex`'s direct
   `seed_home_dir` (preserve `force_http_fallback`).
2. **Slice 2 — explicit source split.** `RuntimeHomePlan` (content/auth/hook-trust); auth via `seed_env` +
   credential-token symlink-from-native; pin content config to the template; **validate a pristine launch on
   Linux AND macOS**.
3. **Slice 3 — materialization policy + home-writer audit (GATES teardown).** Allow-list writable dirs local;
   complete the writer enumeration; enforce template-secret-free. Must land **before** `rmtree` is enabled for
   template launches.
4. **Slice 4 — `.agent-runtimes` registry / internal-request seam + macOS+Linux auth probes.**

## Key files / symbols
- `cli/launch_options.py` `AgentHomeDirOption` — the flag.
- `cli/__init__.py` `_resolve_home_dir_option`, `claude`, `codex`, `desktop` — entry points + normalization.
- `cli/start_cmd.py` `run_start` → `captured_run.run_captured_run_on_local_tty` (Claude CLI uses overlay).
- `captured_run.py` `run_captured_run_on_local_tty` (write=not print_command), `prepare_captured_run` (write=True) — both → `build_captured_run_context`.
- `captured_run_context.py` `build_captured_run_context` — builds the overlay under `<run dir>/runtime-home/<client>`, rmtree at exit.
- `cli/home_seed.py` — `prepare_runtime_home_overlay`, `resolve_source_home_dir`, `seed_home_dir`,
  `ClaudeSeeder.seed`/`CodexSeeder.seed`, `_symlink_source_home_entries`, `_copy_overlay_local_files`,
  `apply_claude_proxy_env_settings`, `_ensure_claude_trust`, `_merge_codex_project_trust`,
  `_relocate_codex_hook_trust_state`, `_assert_overlay_daemon_is_local`, `claude_projects_root`, `codex_sessions_root`,
  `_default_claude_home`/`_default_codex_home`, name sets `_CLAUDE_OVERLAY_LOCAL_NAMES`/`_CODEX_OVERLAY_LOCAL_NAMES`.
- `cli/codex_cmd.py` `run_codex` (direct seed, no overlay), `build_codex_invocation` (accepts `runtime_home_dir`).
- `captured_codex.py` `build_codex_captured_invocation` (forwards `runtime_home_dir`).
- `launch_environment.py` `build_launch_env`, `build_managed_child_env`, `HOME_DIR_ENV_BY_CLIENT`.
- `cli/launch_runtime.py` `resolve_storage_dir` → `run_root(...)` (per-run storage), `LaunchPreparation`.
- `env_keys.py` `AGENT_HOME_DIR` (`TRANSPORT_MATTERS_AGENT_HOME_DIR`).

## Open questions
- macOS Keychain: the live Claude OAuth token is not in the home and not copied; whether a pristine
  template launch re-auths cleanly when only `.claude.json` `oauthAccount` (metadata) is present was
  not exercised here (likely relies on `.credentials.json` symlink to native, or Keychain).
- Whether the read-side `locate`/backfill can tolerate a moved home for historical runs whose facts
  embed the old absolute path (Q4 staleness) was not traced end-to-end.

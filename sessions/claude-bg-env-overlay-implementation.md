---
title: Claude bg-env propagation fix — per-run runtime overlay + settings-env route
type: sessions
tags: [backend, transport-matters, captured-run, overlay, bg-env-propagation, claude, codex, launch-path]
summary: Per-run symlink-rich runtime overlay routes the captured-run proxy into Claude settings.json env at the actual retry port so daemon background workers inherit the route, without mutating the source ~/.claude.
status: active
source: backend-engineer
confidence: high
created: 2026-06-14
updated: 2026-06-14
---

## Summary

Implements the root fix from `NOTES/claude-bg-env-propagation-fix-spec.md`. Claude
daemon-spawned background workers were losing the proxy route because it was injected
only via first-child OS env (`ANTHROPIC_BASE_URL`); the daemon rebuilt worker env from
its dispatch state and dropped it. Fix: every captured run now launches the client from
a **per-run runtime overlay home** under run storage, and the proxy route is written into
the overlay's Claude `settings.json` `env` block, which Claude re-applies to daemon
workers (validated by the 2026-06-14 live smoke recorded in the spec).

Picked up as a warroom handoff (exclusive ownership) on top of a WIP "starting block".
Made the WIP spec-correct, reconciled DRY, fixed lint/type errors, and reconciled the
launch-path contract tests to the new always-overlay behavior. Gate `cd api && just ci`
is green: 1355 passed; ruff format/check, mypy, and migration-smoke clean.

## API / behavior contract

New `home_seed.py` surface:
- `resolve_source_home_dir(client_name, *, home_dir, env)` — source home is `--agent-home-dir`
  if supplied, else `$CLAUDE_CONFIG_DIR`/`$CODEX_HOME`, else `~/.claude`/`~/.codex`.
- `prepare_runtime_home_overlay(client_name, *, source_home_dir, runtime_home_dir, working_dir, env) -> RuntimeHomeOverlay`
  — symlinks user-visible source state into the overlay; keeps Claude daemon control +
  dispatch state LOCAL (`_CLAUDE_DAEMON_LOCAL_NAMES` = `daemon`, `daemon.lock`, `daemon.log`,
  `daemon.status.json`, `jobs`); copies overlay-owned real files (`settings.json`,
  `.claude.json`; codex: `auth.json`, `config.toml`); seeds trust + skip-dangerous on the
  overlay; `_assert_overlay_daemon_is_local` fails closed if ANY daemon-local name resolves
  back to the source home (covers `jobs/`, comparison resolves both sides).
- `apply_claude_proxy_env_settings(*, runtime_home_dir, proxy_url, run_id)` — merge-only
  write of managed keys into overlay `settings.json` `env`:
  `ANTHROPIC_BASE_URL=proxy_url`, `TRANSPORT_MATTERS_RUN_ID`, `TRANSPORT_MATTERS_AGENT_HOME_DIR=<overlay>`,
  `NO_PROXY=127.0.0.1,localhost`. Raises `ValueError` on non-object root or non-object `env`.

Launch-path wiring:
- `captured_run_context.build_captured_run_context` builds the overlay when `write` and a
  client is resolved, sets `effective_request.home_dir = source_home_dir`, threads
  `runtime_home_dir` to the claude/codex invocation builders, and registers
  `rmtree(runtime_home_root)` on the resource stack (overlay is **per-run ephemeral**).
- `captured_claude.build_claude_captured_invocation` calls `apply_claude_proxy_env_settings`
  **inside `build_invocation`** (the retry-safe factory) using `proxy_url=loopback_http_url(proxy_port)`,
  so a bind-retry rewrites the route at the actual port. Child `CLAUDE_CONFIG_DIR` = overlay;
  process-env `ANTHROPIC_BASE_URL` reuses the same `proxy_url` (single source of route).
- `codex_cmd.build_codex_invocation` / `captured_codex` thread `runtime_home_dir` → child
  `CODEX_HOME` = overlay; codex routing stays in process env.

Behavior change (spec §4): the child **always** runs from a per-run overlay, so
`CLAUDE_CONFIG_DIR` is now always set to `<run_storage>/runtime-home/<client>` even with no
`--agent-home-dir`. `--agent-home-dir` is now the **source** home (overlay built from it),
not a destination seeded from native.

## Key decisions made this session

- `apply_claude_proxy_env_settings` matches the spec §1 signature `(runtime_home_dir, proxy_url, run_id)`;
  dropped the WIP's extra `agent_home_dir` param. `TRANSPORT_MATTERS_AGENT_HOME_DIR` is the
  overlay (the child's real `CLAUDE_CONFIG_DIR`), not the source. The addon's transcript-locate
  uses a separate process-env `AGENT_HOME_DIR` (= source) and is unaffected (overlay `projects/`
  is symlinked to source, so both resolve to the same dir).
- Promoted `launch_environment._LOOPBACK_NO_PROXY` → public `LOOPBACK_NO_PROXY` and consumed it
  in `home_seed` (DRY: single definition of `127.0.0.1,localhost`).

## Tests

- `home_seed` unit tests: overlay symlinks user state + keeps control files local + source
  unmutated; copies native-default account metadata; codex overlay copies auth/config +
  symlinks plugins; `apply_*` preserves unrelated top-level + env keys, replaces only managed
  keys, rewrites on retry port, writes route when no settings exist, restrictive `0600` mode,
  and raises `ValueError` on non-object root/`env`.
- Launch-path contract tests reconciled to always-overlay: child `CLAUDE_CONFIG_DIR` derived
  from `TRANSPORT_MATTERS_STORAGE_DIR`/runtime-home/<client>; overlay contents inspected
  **during spawn** via spy side-effect (overlay is rmtree'd post-run); spawn-spec consistency
  test mirrors the resolved overlay + source home into the public helper.

## Open items (later slices, not in this change)

- Spec §7 fail-closed health check (allow-listed env keys; classify `--bg-pty-host` wrapper vs
  routed `--bg-spare` worker) — not implemented here.
- Spec §5 explicit daemon stop-before-spawn for the overlay — overlays are per-run fresh
  (rmtree on lease close) so no stale daemon, but the explicit stop step is deferred.
- `--settings <file>` spike vs editing overlay `settings.json` — unproven for daemon workers.
- Overlay path manifest classification: `daemon*` + `jobs/` are now kept local (route-sensitive
  dispatch state); transcript/history symlink safety and remaining non-daemon entries still need
  a runtime smoke before a final stance (spec default = symlink for source fidelity).
- Codex overlay symlink manifest (plugin/cache/memory) needs one runtime smoke.

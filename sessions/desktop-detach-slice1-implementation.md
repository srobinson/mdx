---
title: Desktop Detach Implementation
type: sessions
tags: [backend, desktop, cli, docs, transport-matters]
summary: Implemented detached desktop launch by default with foreground compatibility, runtime PID records, channel list PID visibility, log tailing, viewer channel environment coverage, and final user docs.
status: active
source: backend-engineer
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

## Summary

Implemented slice 1 of `feat/desktop-detach` in commit `2074239`. The `transport-matters desktop` command now launches the channel backend in a detached process by default, records the backend PID and launch metadata, then starts Electron separately. The previous blocking behavior remains available through `transport-matters desktop --foreground`.

The implementation introduced a shared desktop runtime seam for channel record paths, log paths, atomic record writes, live record reads, and PID liveness checks. `transport-matters channel list` displays a live PID column, and `transport-matters tail [channel]` provides log inspection with last N lines and follow mode.

Slice 1 follow up commit `4b7b10d` added a regression guard for the detached viewer environment. The test starts with no ambient `TRANSPORT_MATTERS_CHANNEL`, lets the real channel activation path run, captures the actual detached Electron subprocess environment, and asserts the viewer receives `TRANSPORT_MATTERS_CHANNEL=preview`.

Slice 2 docs commit `279ccdc` documented the detached default. `_DESKTOP_HELP` stated that `desktop` returned immediately by default and that `--foreground` kept the backend attached. `docs/CHANNELS.md` covered running and managing detached instances, including `channel list` PID visibility, `tail` flags, `kill <PID>`, and accepted edge cases for `--storage-dir`, `TRANSPORT_MATTERS_HOME`, and PID reuse. The README included the desktop management one liner and listed `transport-matters tail` as a primary command.

Detach readiness fix commit `d1c152f` changed the detached return contract. `run_desktop_detached` now writes the runtime record, waits for the backend web port using the same readiness timeout as foreground launch, and only then opens Electron. If the backend never accepts connections, the viewer is not spawned. The error path distinguishes a still running slow backend from an early child exit and points the operator at `transport-matters tail <channel>` plus the log path.

## API Contract

No HTTP API contract changed.

### CLI contract

```typescript
// transport-matters desktop [--channel <channel>] [--foreground]
interface DesktopLaunchDefaultBehavior {
  mode: "detached";
  result: "returns_after_backend_ready_and_viewer_spawned";
  recordPath: "<channel-storage>/runtime/desktop.json";
  logPath: "<channel-storage>/runtime/desktop.log";
}

interface DesktopLaunchForegroundBehavior {
  mode: "foreground";
  result: "blocks_until_backend_exits";
}

// transport-matters channel list
interface ChannelListRow {
  channel: string;
  home: string;
  database: string;
  proxy: string;
  web: string;
  pid: string; // blank when no live detached backend record exists
  label: string;
  suffix: string;
}

// transport-matters tail [channel] [-n lines] [-f]
interface TailCommandOptions {
  channel?: string;
  lines: number;
  follow: boolean;
}
```

## Database Changes

No schema or migration changes were required. The live smoke used the preview channel database and confirmed it was already at migration `0005_session_template_provenance`.

## Security Considerations

The detached backend is started with an explicit environment from the prepared desktop launch plan. The process uses `stdin=DEVNULL`, redirects stdout and stderr to the channel log, closes inherited file descriptors, and starts a new session. Runtime records are local channel state under `~/.transport-matters*` and are not exposed through an HTTP API in this slice. PID display fails closed to a blank value for stale, malformed, missing, or inaccessible records.

The docs explicitly keep shutdown simple through `kill <PID>` and warn about accepted runtime record edges: explicit `--storage-dir` or `TRANSPORT_MATTERS_HOME` launches sit outside channel scoped `list` and `tail`; `TRANSPORT_MATTERS_HOME` collapses channels to one record path; PID reuse can briefly make a stale record appear live.

The readiness fix keeps the record write before the readiness wait so a slow but live backend remains inspectable through the log path. The command exits non zero before spawning Electron if the backend times out or exits early.

## Performance Notes

`channel list` performs a small JSON read and PID liveness check per channel. Stale records are cleaned up on read. The tail command streams by polling for appended log bytes, which is simple and sufficient for local diagnostic usage. Detached launch now waits for backend readiness before returning. The measured preview smoke returned in 2315 ms and made `/api/meta` reachable immediately at return.

## Verification

- `cd api && just check`: passed.
- `cd api && just ci`: passed with `1652 passed` in the API test suite.
- `cd desktop && just package-smoke`: passed.
- `just check`: passed at repo root. Existing style warnings about `!important` in `www/src/session-canvas/components/pane-dock.css` remained unchanged.
- `just test`: passed at repo root with desktop, web, and API suites.
- Live smoke installed the local checkout, ensured the preview database, launched `transport-matters desktop --channel preview`, observed backend PID `73686` in `transport-matters channel list`, tailed startup and shutdown logs, killed the detached backend, verified the PID column blanked, and killed the detached Electron process.
- Bus completion reply for slice 1 sent to `transport-matters:general:1:3.1` on topic `tm-detach-build` with message `a0f3f32a-b448-45fa-b4cb-fdc4fdc809f1`.
- Slice 1 fix commit `4b7b10d`: `cd api && just test src/transport_matters/cli/test_desktop.py` passed with `29 passed`.
- Slice 1 fix commit `4b7b10d`: `cd api && just check` passed.
- Slice 1 fix commit `4b7b10d`: `fmm validate` passed and `git status --porcelain=v1` was clean.
- Bus completion reply for the fix sent to `transport-matters:general:1:3.1` on topic `tm-detach-build` with message `fe97400e-681a-4d9f-8c5c-445c8568dd2a`.
- Slice 2 docs commit `279ccdc`: `just check` passed. The root check rerun completed with exit code 0.
- Slice 2 docs commit `279ccdc`: `just test` passed with desktop `33 passed`, web `989 passed`, and API `1653 passed`.
- Slice 2 docs commit `279ccdc`: `git diff --check` passed before commit, `fmm validate` passed with all 855 indexed files current, and `git status --short` was clean after commit.
- Bus completion reply for slice 2 sent to `transport-matters:general:1:3.1` on topic `tm-detach-build` with message `1703ea38-097e-4c29-bd12-5aac237db226`.
- Detach readiness repro before fix: after launching `transport-matters desktop --channel preview`, the command returned in 551 ms, immediate curl to `127.0.0.1:8798/api/meta` failed with connection refused, the 1 second retry still failed, and a later retry returned 200 while `desktop.log` showed clean startup.
- Detach readiness tests were added failing first. Red run: `cd api && just test src/transport_matters/cli/test_desktop.py::test_run_desktop_detached_waits_for_backend_before_viewer src/transport_matters/cli/test_desktop.py::test_run_desktop_detached_timeout_does_not_spawn_viewer src/transport_matters/cli/test_desktop.py::test_run_desktop_detached_timeout_reports_early_backend_exit` failed because the wait never ran and timeout never raised. Green run passed with 3 tests.
- Detach readiness fix commit `d1c152f`: `cd api && just test src/transport_matters/cli/test_desktop.py` passed with `32 passed`.
- Detach readiness fix commit `d1c152f`: `cd api && just check` passed with ruff format, ruff check, and mypy clean.
- Detach readiness fix commit `d1c152f`: `just check` passed at repo root. Existing Biome warnings about `!important` in `www/src/session-canvas/components/pane-dock.css` remained unchanged.
- Detach readiness fix commit `d1c152f`: `just test` passed at repo root with desktop `33 passed`, web `989 passed`, and API `1656 passed`.
- Detach readiness live smoke after fix: with preview port initially free, `transport-matters desktop --channel preview` returned in 2315 ms, immediate curl to `http://127.0.0.1:8798/api/meta` returned HTTP 200 at `2026-06-20T16:34:39+0700`, and `desktop.log` showed clean startup followed by the meta request.
- Bus completion reply for detach readiness fix sent to `transport-matters:general:1:3.1` on topic `tm-detach-fix` with message `32ed9c5c-b5b8-4bad-9c2a-96ff1b26d48e`.

## Open Items

- No persistent process supervisor was added in this slice. Detached runs remain local channel processes that can be inspected through the runtime record and log.
- The optional Electron hosted close affordance remains deferred by directive. The documented stop path is `kill <PID>`.

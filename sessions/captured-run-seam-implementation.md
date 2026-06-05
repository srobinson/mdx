---
title: Captured run seam implementation
type: sessions
tags: [backend, transport-matters, captured-run, cli]
summary: Implemented and hardened the reusable Claude captured run seam for pane-owned launches.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Implemented C1 for captured Claude launch extraction on branch `feat/captured-run-seam`, PR #61.

Commits:

- `0e2c71c` added the initial seam.
- `e101354` completed the C1 fix round after peer review.

Key decisions:

- Added `api/src/transport_matters/captured_run.py` as the reusable seam for pane-owned Claude launches.
- Kept `run_start()` and `run_client_with_retry()` public signatures unchanged.
- Moved the Claude invocation builder into `build_start_invocation()` and made the seam standalone importable.
- Rewired `run_start()` into `run_captured_run_on_local_tty()` so Claude CLI orchestration shares the captured-run context path.
- Kept Codex on the existing generic retry runner.
- Added seam owned-session retry: `prepare_captured_run()` mints once, retries bind conflicts inside the seam, and reuses the same run id plus owned native session id across attempts.
- Restored persist-before-manifest ordering for captured runs.
- Added `install_signal_handlers` policy to the seam for future callers. The current CLI local terminal path preserves signal behavior through the existing runner.
- Removed the redundant double teardown on failed proxy attempts.

## API Contract

Internal Python contract:

```python
@dataclass(frozen=True, slots=True)
class CapturedRunRequest:
    client_name: str
    passthrough: tuple[str, ...]
    directory: Path | None
    proxy_port: int | None
    web_port: int | None
    upstream: str
    storage_dir: Path | None
    home_dir: Path | None
    client_bin: Path | None
    client_disabled: bool
    no_system_prompt: bool
    debug: bool

@dataclass(frozen=True, slots=True)
class CapturedRunSpawnSpec:
    run_id: str
    working_dir: Path
    storage_dir: Path
    proxy_port: int
    web_port: int
    mitmdump_log: Path
    client: ManagedClient | None
    launch_env: dict[str, str]
    managed_session: ManagedSession | None

@dataclass(slots=True)
class CapturedRunLease:
    spawn_spec: CapturedRunSpawnSpec
    def close(self) -> None: ...

def prepare_captured_run(request: CapturedRunRequest, ...) -> tuple[CapturedRunSpawnSpec, CapturedRunLease]: ...
def run_captured_run_on_local_tty(request: CapturedRunRequest, ...) -> None: ...
def build_start_invocation(...) -> Callable[[int, int], tuple[list[str], dict[str, str], ManagedClient | None]]: ...
```

No HTTP or WebSocket endpoint was added in C1. The returned `CapturedRunSpawnSpec.client` is the future C2 attachment point for desktop PTY bridging.

## Database Changes

None.

The implementation preserves existing owned session fact persistence through `persist_owned_session_facts()` and does not add migrations or new session store tables.

## Security Considerations

- No new `TRANSPORT_MATTERS_*` environment string literals were introduced.
- The managed launch environment continues to flow through the existing shared builders.
- Claude child proxy configuration still uses the existing managed child environment sanitizer.
- Workspace locks and manifests remain scoped to the canonical workspace run root.
- `CapturedRunLease.close()` terminates supervised children, removes the live manifest, releases the workspace lock, and closes resource handles idempotently.
- A subprocess import guard now proves `transport_matters.captured_run` is standalone importable and not dependent on pytest import order.

## Performance Notes

- The CLI path keeps its existing retry runner and signal behavior for local terminal launches.
- The pane-owned seam starts mitmdump once per successful prepared run and returns after proxy readiness.
- Bind conflict retries are bounded to three attempts, matching the existing CLI retry budget.
- Line limits remain under the project threshold: runner is 699 lines, launch runtime is 668 lines, and the captured-run seam is 528 lines.

## Verification

- `cd api && uv run python -c "import transport_matters.captured_run"`
  - Exit code 0.
- `cd api && just test src/transport_matters/cli/test_captured_run.py -q`
  - 6 passed.
- `cd api && just test src/transport_matters/cli -q`
  - 250 passed.
- `cd api && just ci`
  - Ruff format check passed.
  - Ruff lint passed.
  - Mypy passed across 309 source files.
  - Migration smoke passed, 6 tests.
  - Full pytest passed, 1251 tests.

## Open Items

- C2 should add the WebSocket or desktop attach layer that consumes `CapturedRunSpawnSpec.client`.
- The first desktop integration should keep pane ownership explicit until a server managed run manager is designed and accepted.

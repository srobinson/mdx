## Reuse Map

- Reuse: `api/src/transport_matters/cli/net.py` `port_in_use` and `raise_port_in_use`. Keep the existing loopback listener probe and the current foreign process error path.
- Reuse: `api/src/transport_matters/cli/desktop_runtime.py` `DesktopRuntimeRecord`, `desktop_record_path`, `read_live_desktop_record`, `stop_desktop_record`, and `is_pid_alive`. This is the existing detached desktop PID record and termination model.
- Reuse: `api/src/transport_matters/cli/desktop_cmd.py` `DESKTOP_BACKEND_COMMAND` and `_build_desktop_backend_command`. The backend command already carries the ownership marker: `transport-matters _desktop-backend --work-dir ... --web-port ... --proxy-port ... --storage-dir ... --channel ...`.
- Reuse: `api/src/transport_matters/cli/desktop_cmd.py` `run_desktop_detached`, `_wait_for_detached_backend_or_exit`, `build_backend_started_event`, and `spawn_detached_electron`. These are the right seams for surfacing an already live backend instead of spawning a second one.
- Reuse: `api/src/transport_matters/api/v1/meta.py` `get_meta`, `_build_meta_response`, and `MetaResponse`. `/api/meta` already returns the backend channel and proves the FastAPI backend is responsive.
- Reuse: `api/src/transport_matters/main.py` `create_app`. `/health` is a liveness probe, but `/api/meta` is the better identity probe because it includes channel.
- Reuse: `api/src/transport_matters/cli/launch_runtime.py` `prepare_launch` and `resolve_launch_ports`, plus `api/src/transport_matters/captured_run.py` `run_captured_run_on_local_tty`. This is the `transport-matters claude` launch path that hard fails on channel default ports before starting children.
- Reuse: `api/src/transport_matters/cli/bind_failure.py` `handle_bind_failure` and `format_retry_exhaustion`. Keep this for post spawn bind races and error wording, not for preflight ownership classification.
- Existing infra: `api/src/transport_matters/run_manager.py` `RunManager` owns canvas pane runs in process memory and tears them down through `CapturedRunLease`. It does not own the detached desktop backend that conflicts on the channel web port.
- Existing infra: `api/src/transport_matters/shared_proxy/manager.py` `SharedProxyManager.by_listen_port` maps proxy listen ports to run ids inside the live API process. It is useful for live canvas runs, but it cannot classify a stale detached backend before the backend starts.
- Existing infra: `api/src/transport_matters/channel.py` `ChannelSpec` and `api/src/transport_matters/storage_roots.py` `default_storage_root`. Channel id, channel default ports, and channel home are the expected identity inputs.
- Similar checked and rejected: `api/src/transport_matters/cli/diagnose.py` `run_doctor` only calls `port_in_use` and prints a warning. It does not resolve port to PID.
- Similar checked and rejected: `api/src/transport_matters/cli/bind_failure.py` `format_retry_exhaustion` mentions `lsof` only as a human hint. It is not a reusable process lookup implementation.
- Similar checked and rejected: `api/src/transport_matters/manifest.py` `Manifest` records PID and ports for captured run manifests, but local TTY launches remove the manifest on exit and detached desktop uses `DesktopRuntimeRecord` instead.
- None found: no current `psutil` dependency, no `lsof` or `ps` wrapper, no port to PID helper, no command line reader, and no stale versus live desktop backend classifier. Searches used: fmm `psutil`, fmm `lsof`, fmm `port_in_use`, fmm `RunManager`, and `rg` for `psutil|lsof|netstat|fuser|cmdline|ppid|_desktop-backend`.

## Quality Map

- Duplication / parallel implementation: `api/src/transport_matters/cli/launch_runtime.py` `resolve_launch_ports` and `api/src/transport_matters/cli/desktop_cmd.py` `_resolve_backend_ports` both fast fail through `raise_port_in_use`. A new ownership decision must be shared, not copied into both branches.
- Boundary / design issue: `api/src/transport_matters/cli/desktop_cmd.py` is already close to the project file size limit. The classifier should not be added there. Put generic process inspection in a small new module, and put desktop ownership decisions beside `DesktopRuntimeRecord` in `desktop_runtime.py` or a narrow sibling.
- Boundary / design issue: `api/src/transport_matters/cli/desktop_runtime.py` `read_live_desktop_record` trusts PID liveness only. PID reuse could misclassify a foreign process as ours unless the new classifier also verifies command line identity.
- Boundary / design issue: PPID 1 is not a stale signal for this feature. `api/src/transport_matters/cli/desktop_cmd.py` `run_desktop_detached` starts the backend with `start_new_session=True`, then the parent CLI exits. A healthy detached backend can also have PPID 1.
- Boundary / design issue: `/api/meta` proves a backend is responsive and on the expected channel, but it does not expose storage dir, web port, proxy port, or PID. Storage and port ownership must come from the command line marker and the desktop runtime record.
- Boundary / design issue: `api/src/transport_matters/cli/diagnose.py` currently gives no process owner detail despite being the natural diagnostic surface named in the brief.
- Dead code / obsolete path: none found in this slice. The existing desktop runtime record, channel stop, bind retry, and RunManager ownership paths are active and tested.
- Grooming recommendation: refactor during the slice. Add one reusable process owner adapter and one desktop classifier, then wire both launch paths to it. Do not expand `desktop_cmd.py` with process parsing logic.

## Plan

- Decision needed: auto kill versus confirm then kill for case (a). Recommendation: auto kill only after strict `our_stale_backend` classification. Never kill `foreign`. Never kill `our_live_backend`; surface or reuse it.
- Decision needed: for `transport-matters claude` when an implicit channel default web port is held by a live owned desktop backend. Recommendation: do not kill it. Either allocate a dynamic web port for the new local TTY launch, or explicitly decide that live desktop reuse is a separate product slice. Explicit `--web-port` and `--proxy-port` should keep today’s error on live conflicts.
- Proposed new generic seam: `api/src/transport_matters/cli/process_owner.py`.
  1. Add `ListenerProcess(pid, ppid, cmdline)` and `listener_processes(port) -> tuple[ListenerProcess, ...]`.
  2. Prefer adding `psutil` as a runtime dependency because `api/pyproject.toml` has no current process inspection dependency and shelling to `lsof` plus `ps` is platform and output fragile.
  3. Use `psutil.net_connections(kind="tcp")` for `LISTEN` sockets on loopback and `psutil.Process(pid).cmdline()` plus `ppid()` for identity. Treat inaccessible, missing, or multiple disagreeing owners as `foreign` for safety.
  4. If a new runtime dependency is rejected, keep the same interface and back it with a narrow `lsof -nP -iTCP:<port> -sTCP:LISTEN -t` plus `ps` adapter. Do not let shell output parsing leak into desktop launch code.
- Proposed desktop classifier home: `api/src/transport_matters/cli/desktop_runtime.py` if small, or new sibling `api/src/transport_matters/cli/desktop_owner.py` if it would push `desktop_runtime.py` past a clean boundary.
- Proposed classification shape:

```python
DesktopBackendPortOwnerKind = Literal[
    "our_stale_backend",
    "our_live_backend",
    "foreign",
]

@dataclass(frozen=True, slots=True)
class DesktopBackendIdentity:
    channel: str
    storage_dir: Path
    proxy_port: int
    web_port: int

@dataclass(frozen=True, slots=True)
class DesktopBackendPortClassification:
    kind: DesktopBackendPortOwnerKind
    pid: int | None
    reason: str
    record: DesktopRuntimeRecord | None = None


def classify_desktop_backend_listener(
    port: int,
    *,
    expected: DesktopBackendIdentity,
    meta_timeout_s: float = 0.75,
) -> DesktopBackendPortClassification: ...
```

- Classification rules:
  1. Resolve `port -> ListenerProcess` through the process owner seam. No PID, inaccessible PID, or multiple unrelated PIDs means `foreign`.
  2. Parse the listener command line. It must contain `transport-matters`, `_desktop-backend`, `--channel <expected.channel>`, `--web-port <expected.web_port>`, `--proxy-port <expected.proxy_port>`, and `--storage-dir <expected.storage_dir>`, with paths normalized through `expanduser().resolve(strict=False)`. If any field differs, return `foreign`.
  3. Read `desktop_record_path(expected.storage_dir)` through `read_live_desktop_record`. If present, require record PID, channel, proxy port, and web port to match. Missing record does not by itself make the process foreign when the command line is exact, but a mismatched live record should return `foreign`.
  4. Probe `http://127.0.0.1:<web_port>/api/meta` with a short timeout and Host `127.0.0.1`. If it returns channel `<expected.channel>`, classify `our_live_backend`.
  5. If command line identity is exact but `/api/meta` is unreachable after a bounded retry, classify `our_stale_backend`. Use PPID only as diagnostic text in `reason`, never as the deciding predicate.
- Desktop launch wiring:
  1. Reorder `prepare_desktop_launch` so it resolves channel, cwd, storage dir, and default ports before checking port usage.
  2. Replace `_resolve_backend_ports` with a classification aware helper. On free ports, continue unchanged.
  3. On web port conflict classified as `our_live_backend`, return a launch result that skips backend spawn and calls `spawn_detached_electron` with `build_backend_started_event` for the existing port and storage dir.
  4. On web port conflict classified as `our_stale_backend`, terminate the matched backend. Prefer `stop_desktop_record` when the record matches; otherwise terminate the matched PID from the strict command line classifier. Wait until `port_in_use` returns false, then continue normal launch.
  5. On `foreign`, call `raise_port_in_use` and preserve the current `--web-port` or `--proxy-port` hint.
  6. Treat proxy port only conflicts conservatively until the shared proxy owner is modeled. If the web backend owner cannot be tied to the proxy conflict, return `foreign` and preserve today’s error.
- `transport-matters claude` launch wiring:
  1. Add an optional conflict resolver hook to `resolve_launch_ports` rather than duplicating desktop logic inside `run_start`.
  2. For an owned stale desktop backend on the channel web port, terminate it and retry the same default ports.
  3. For an owned live desktop backend on an implicit channel default, do not kill it. Prefer dynamic allocation for the local TTY launch unless the product decision is to add a true external web runtime reuse path.
  4. For explicit pinned user flags or foreign owners, keep today’s fail fast behavior.
- Doctor follow up:
  1. Extend `api/src/transport_matters/cli/diagnose.py` `run_doctor` to use the new process owner seam for port warnings.
  2. Print owner PID and a safe truncated command label only. Do not dump full env or secrets.
- Tests and gates:
  1. Unit test `process_owner` with fake adapters for no listener, one listener, inaccessible owner, and multiple listeners.
  2. Unit test the desktop classifier for all three exact cases: `our_stale_backend`, `our_live_backend`, and `foreign`.
  3. Add regressions that prove PID reuse is rejected unless the command line marker matches.
  4. Add a regression that PPID 1 plus healthy `/api/meta` is `our_live_backend`, not stale.
  5. Add desktop launch tests that stale owned backend is terminated and live owned backend opens the viewer without spawning another backend.
  6. Update the current fast fail tests: `test_desktop_channel_default_port_in_use_fails_fast` and `test_start_channel_default_port_in_use_fails_fast` should still cover the foreign case.
  7. Run repo recipes, not hand rolled equivalents: `just check` and `just test`.

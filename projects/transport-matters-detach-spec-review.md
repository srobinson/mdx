---
title: Architect review — detached desktop instances spec
type: research
tags: [transport-matters, desktop, detach, channels, review, architecture]
summary: Adversarial pass over transport-matters-detach-spec.md; 3 substantive conditional findings, 2 minor notes, KISS shape confirmed sound.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

# Detached desktop spec — architect review

Artifact reviewed: `~/.mdx/projects/transport-matters-detach-spec.md`
Baseline: `main` @ `87d6d3e`, working tree clean. All code refs verified against that tree.
Mandate: judge the MECHANISM. KISS shape (detached-by-default, `--foreground`, runtime record, `channel list` PID column, `tail`, operator kills PID, no supervisor/`stop`/`ps`) is locked and not re-opened. Findings flag creep too; none of the three substantive findings adds scope.

**Verdict: CONDITIONAL.** 3 substantive findings (all file+symbol fixes, no shape change), 2 minor notes. Recursion/double-Electron concern is provably clean.

---

## Finding 1 (substantive) — `run_desktop_detached` must call `activate_channel(channel)`

The spec's "Detached launch mechanism" describes `run_desktop_detached` calling `prepare_desktop_launch(launch_viewer=True)` directly and never mentions `activate_channel`. Both existing sibling entry points call it first: `cli/desktop_cmd.run_desktop_launch` and `cli/desktop_cmd.run_desktop_backend_server` open with `activate_channel(channel)`.

Why it matters (verified):
- `channel.activate_channel` sets `os.environ[env_keys.CHANNEL] = spec.id` and clears the settings cache.
- `cli/desktop_cmd.spawn_detached_electron` builds the viewer env from `os.environ` plus only four overrides (`DESKTOP_ROUTE_URL`, `CWD`, `STORAGE_DIR`, `WEB_PORT`). It does **not** set `CHANNEL`.
- `desktop/src/main.ts:registerDesktopLifecycleFromEnv` derives the viewer's channel identity (dock icon, app name, preview-amber badge) from the env via `resolveDesktopChannelSpec(env)` → `applyChannelIdentity`, on the hosted (route-url) branch this detached launch uses.

Consequence: a flag-only invocation `transport-matters desktop --channel preview` (no `TRANSPORT_MATTERS_CHANNEL` in env) leaves `os.environ[CHANNEL]` unset, so the detached viewer renders the **wrong channel identity** (missing preview-amber badge / wrong dock). This is masked by `justfile:channel-restart`, which exports `TRANSPORT_MATTERS_CHANNEL={{channel}}` before the command, so the live smoke would not catch it. It breaks for direct CLI use.

Fix: `cli/desktop_cmd.run_desktop_detached` calls `activate_channel(channel)` before `prepare_desktop_launch`, matching the two sibling entry points. Add a test asserting the spawned-viewer env carries the resolved `CHANNEL` when channel is supplied by flag only.

## Finding 2 (substantive) — record-path: route `list`/`tail` through the shared seam; document the `--storage-dir` edge

The writer uses `resolved_storage / "runtime" / "desktop.json"` where `resolved_storage = cli/desktop_cmd._resolve_storage_dir(...)`, which honors `--storage-dir` and otherwise returns `storage_roots.default_storage_root(channel)` (which itself honors `$TRANSPORT_MATTERS_HOME`), with `.expanduser().resolve()` applied.

The spec instructs `channel_cmd.list_channels` to re-derive `spec.home / "runtime" / "desktop.json"` inline from the raw `channel.ChannelSpec.home`. Two problems:

- **(a) DRY.** The spec defines `desktop_runtime.desktop_record_path(storage_dir)` as the shared seam, then has `list` re-inline the same path construction. `list` (and `tail`'s `desktop_log_path`) must call the shared seam, not reconstruct the path.
- **(b) Divergence.** The writer's resolved path and list's raw `spec.home` differ whenever `--storage-dir` is passed, or under `$TRANSPORT_MATTERS_HOME`, or if `spec.home` is non-canonical (symlink/relative) since `_resolve_storage_dir` applies `.resolve()` and `list` does not. The instance then writes a record `list` never reads → invisible PID column.

Fix: `list_channels` computes the path via `desktop_runtime.desktop_record_path(default_storage_root(spec.id))` (the same resolution the writer uses for the no-`--storage-dir` case); `tail` resolves its log path via `desktop_runtime.desktop_log_path(...)` the same way. Then state explicitly in the spec that `--storage-dir` instances are outside `channel list`'s channel-scoped view as an accepted KISS edge (PID-reuse caveat is already acknowledged; this one is not).

## Finding 3 (substantive) — atomic-write helper: instruction is correct in direction, but home is unnamed and the placement forces a layering inversion

The "extract a tiny public helper first" instruction is correct. Verified: `test_private_import_boundary.py` inspects only `ast.ImportFrom` nodes and flags any imported alias/module leaf beginning with a single underscore, so `from ...cli.home_io import _write_atomic_json` would **fail the lint**. `claude_home.py` only escapes today because it does `from . import home_io` then `home_io._write_atomic_json(...)` (module-attribute access, not an `ImportFrom` of a private alias). So copying or `from`-importing the private name is genuinely barred.

Two gaps the spec leaves open:

- **Home unnamed.** The spec says extract a public helper and "update both callers" but never names where the public helper lives, and "both callers" is ambiguous: the private name has three call sites in `cli/claude_home.py`, and `manifest.write` is a *second*, independent inline copy of the same temp-file + `Path.replace` convention. Name the single public helper and its callers explicitly.
- **Layering inversion.** The spec places the new module at the package root (`api/src/transport_matters/desktop_runtime.py`). All three of its consumers (`cli/desktop_cmd`, `cli/channel_cmd`, the new `tail`) live under `cli/`, and the helper lives at `cli/home_io`. The naive execution (promote `_write_atomic_json` in place, import it into a root-level module) makes a package-root module depend on the outer `cli/` package — an inversion of the documented import order. No test enforces cli layering (only the private-import lint exists), so this is an architectural smell rather than a hard gate failure, but it is avoidable.

Recommended fix (smallest, KISS): place the new module at `cli/desktop_runtime.py` (cohesive with its only consumers) and promote `cli/home_io._write_atomic_json` → public `cli/home_io.write_atomic_json`. That keeps the import cli→cli, satisfies the lint, and avoids the inversion. Consolidating `manifest.write` onto the same helper is optional and out of KISS scope; the helper's home must still be named either way.

---

## Minor notes (non-blocking)

- **`started_at` format.** `datetime.now(UTC).isoformat()` produces `...+00:00` with microseconds, but the schema example shows `2026-06-20T07:24:57Z` (no microseconds, `Z`). Pin the format deliberately and assert the produced string in the record-schema test. (Point 5 otherwise clean: UTC-at-spawn in the CLI has no sandbox constraint and relies on no forbidden call.)
- **Detached Electron spawn-failure UX.** `run_desktop_detached` writes the record from `Popen.pid` before `spawn_detached_electron`, so a viewer-launch `ElectronResolutionError` still leaves a killable recorded PID — good. Optionally catch it to avoid a raw traceback while the backend is already live.

## Positively clean

- **Point 1 — no recursion / no double-Electron (CONFIRMED).** `plan.command` = `cli/desktop_cmd._build_desktop_backend_command`, which emits `["transport-matters", DESKTOP_BACKEND_COMMAND, "--work-dir", "--web-port", "--proxy-port", "--storage-dir", "--channel", ...]`. `DESKTOP_BACKEND_COMMAND` is the hidden `_desktop-backend` child → `run_desktop_backend_server` → `prepare_desktop_launch(launch_viewer=False)` → `serve_desktop_backend(plan, None)`, which spawns no Electron. The child reuses the parent's resolved ports passed explicitly as `--proxy-port`/`--web-port`, so `prepare_desktop_launch`'s `event.routeUrl` web port matches the child's bind. The single viewer is the CLI's own `spawn_detached_electron`, which sets `DESKTOP_ROUTE_URL` → `registerDesktopLifecycleFromEnv` takes the hosted/attach branch and spawns no second backend. No recursion, no double-Electron. (The channel-identity env gap is Finding 1, orthogonal to recursion.)
- **Point 4 — tail.** `channel.resolve_channel_spec` exists; channel id defaults to `_DEFAULT_CHANNEL_ID` via `resolve_channel_id` (consistent with the spec's "then stable"). `-n`/default-100, `-f` poll, and non-zero exit with the missing-log path are sound; truncation/rotation is out of KISS scope and a naive seek-and-read loop will not crash. Fold the log-path resolution into the Finding-2 shared-seam fix.
- **Point 6 — slices + gates.** Real recipes: root `justfile` `check`/`test`/`channel-restart` (the spec adds the `*desktop_args` variadic), `api/justfile:ci`, `desktop/justfile:package-smoke`. Two slices reasonable. All traceability is field→file+symbol; **no file:line anchors** present.

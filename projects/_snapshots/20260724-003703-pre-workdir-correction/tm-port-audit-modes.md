---
title: Transport Matters — Port + Relaunch Behavior, Dev Mode vs Production (User Install)
type: research
tags: [transport-matters, ports, channels, relaunch, dev-mode, production, electron, scout]
summary: Fixed per-channel port + reclaim-on-relaunch is already coherent for both modes through one code path; they differ only in channel SET (prod = 1 default `stable`, dev = `stable`+`preview` concurrent) and in dev's rebuild-from-working-tree wrapper.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-24
updated: 2026-06-24
---

# Transport Matters: Port + Relaunch Behavior per Mode

Scout for `tm-port-audit`. Read-only. Maps DEVELOPER mode vs PRODUCTION (user install) mode and the right fixed-port + relaunch behavior for each. Every claim is cited to file + symbol and verified at source.

## TL;DR (owner's question, answered)

**Yes — "the port is fixed" + "relaunch reclaims it" is the right model for BOTH modes, and it is already implemented through one shared code path** (`run_desktop_detached` in `cli/desktop_cmd.py`). The two modes do not need different port designs. They differ only in:

1. **Channel SET.** Production runs ONE channel (`stable`, fixed proxy `8787` / web `8788`). Dev additionally runs `preview` (fixed `8797`/`8798`) concurrently. Same fixed-port-per-channel rule, different number of channels live at once.
2. **Rebuild wrapper.** Dev relaunch goes through `just channel-restart`, which rebuilds the web + desktop bundles from the working tree before launching. Production never rebuilds; it relies on the built-in idempotent reuse / auto-recover in `transport-matters desktop` plus `--force-restart`.

The only behavior gap worth the owner's attention is at the **wedged / foreign-squatter edge** (see "Where the model has a sharp edge"). For the normal "I closed it, reopen it" case, reclaim is automatic in both modes.

---

## 1. Developer mode (channels)

Source of truth: `docs/CHANNELS.md`, `api/src/transport_matters/channel-specs.json`, `channel.py`, `cli/channel_cmd.py`, root `justfile`.

**Two channels ship**, declared in `channel-specs.json` (schema 1), parsed into a frozen `ChannelSpec` by `channel.py::_build_channel_spec`:

| Boundary | `stable` | `preview` |
| --- | --- | --- |
| Home | `~/.transport-matters` | `~/.transport-matters-preview` |
| Database | `transport_matters` | `transport_matters_preview` |
| Proxy port | `8787` | `8797` |
| Web port | `8788` | `8798` |
| Electron name / app id | `Transport Matters` / `io.helioy.transport-matters` | `Transport Matters Preview` / `io.helioy.transport-matters.preview` |
| Electron user data | default | `~/.transport-matters-preview/electron-user-data` |
| Badge | none | amber `PREVIEW` |

- `stable` is the hardcoded default (`channel.py::_DEFAULT_CHANNEL_ID`); resolution honors `TRANSPORT_MATTERS_CHANNEL` then falls back to `stable` (`resolve_channel_id`).
- **Concurrent-by-design.** `docs/CHANNELS.md` states stable and preview "can run at the same time because their homes, databases, ports, Electron identity, user data, and dock identity are separate." One channel id fans out to every local state boundary. This is a deliberate dogfood affordance: run the installed daily driver (`stable`) beside the working-tree build (`preview`).
- **Dev relaunch** = `just channel-restart preview` (`justfile:74`). It runs, in order: rebuild www bundle → rebuild desktop bundle + `electron:install` → `transport-matters channel stop {channel}` → `transport-matters channel ensure-db {channel}` → `transport-matters desktop --channel {channel}`. So the rebuild-from-working-tree and the explicit `stop` are the dev-only parts; the actual launch is the same `desktop` command production uses.
- **Stop / list / tail** are first-class: `transport-matters channel stop|list|status` (`cli/channel_cmd.py`), `transport-matters tail [channel]`.

## 2. Production / user-install mode

Source of truth: `README.md`, `QUICKSTART.md`, `scripts/install.sh`, `scripts/release.sh`, `api/pyproject.toml`, `desktop/package.json`, `cli/desktop_cmd.py`.

- **Install path:** end users install from **PyPI**, not source. `scripts/install.sh` (shipped via `…/releases/latest/download/install.sh | bash`) installs `uv` if missing, then `uv tool install --force transport-matters`. Releases are cut by pushing a `vX.Y.Z` tag (`scripts/release.sh`) → CI publishes the wheel to PyPI.
- **One entry point.** `api/pyproject.toml` `[project.scripts]` defines exactly `transport-matters = "transport_matters.cli:main"`. No second console script. The Electron desktop assets are bundled INTO the Python wheel (hatch wheel artifacts ship `www/**` and `channel-specs.json`); there is **no standalone double-clickable `.app`** distributed. `desktop/package.json` is `private: true`. The `package-smoke/Transport Matters.app` under `desktop/dist/` is a CI smoke artifact, not a shipped product.
- **Launch path:** the flagship user command is `transport-matters desktop` (`QUICKSTART.md` step 4). It starts the backend **detached by default**, waits until it accepts connections, then opens the Electron canvas (`--foreground` keeps it attached). Electron is always launched **through** the CLI (`cli/desktop_cmd.py::resolve_electron_launch` → spawns the packaged/`node_modules` electron against `desktop/dist/main.js`), never handed over as a separate bundle.
- **Channels for users?** `--channel` is a real, user-visible Typer option (`cli/launch_options.py`), but only two channels exist and `stable` is the default. **A normal user effectively runs exactly one channel — `stable` — on fixed `8787`/`8788`, home `~/.transport-matters`, DB `transport_matters`.** `preview` is the dev/early-adopter second instance. So: the *channel concept* is dev-facing; the *production user* is simply "always on the default channel," which still gives them fixed ports. `install.sh` prints `localhost:8787` / `localhost:8788` as fixed next-step URLs precisely because they are pinned.
- **Restart path:** there IS a dedicated user-facing restart — `transport-matters desktop --force-restart` (wired through `cli/__init__.py::desktop` → `run_desktop_detached(force_restart=...)`). Stop without restart: `transport-matters channel stop`. So production users do NOT need `just channel-restart` (a source-checkout recipe); they get reclaim from the `desktop` command itself.

## 3. The reclaim mechanism (shared by both modes)

This is the heart of the audit. `run_desktop_detached` (`cli/desktop_cmd.py:258`, verified at source) is the single relaunch path for both modes. On every launch it first calls `discover_desktop_runtime` (`desktop_runtime.py`), which reads the `desktop.json` record, checks `is_pid_alive`, runs `probe_desktop_liveness` (3 health probes against `web_port/health`), and cross-checks the channel via `/api/meta`. It then branches on the resolved state:

| Recorded runtime state | What relaunch does | User experience |
| --- | --- | --- |
| `--force-restart` (any non-`absent`) | `force_restart_desktop_runtime_or_exit` — unconditional SIGTERM, then fresh launch | "Hard restart" |
| `live` (same channel, healthy) | `_attach_existing_desktop` — **reuses** the backend, spawns only the viewer, returns. No rebind. | "It's already running, just open the window" (idempotent) |
| `stale` (recorded pid dead) | `recover_desktop_runtime_or_exit(announce=False)` → `stop_desktop_record` → fresh launch | Silent self-heal; reclaims its own port |
| `not-serving` (pid alive, refusing) | `recover_desktop_runtime_or_exit(announce=True)` → stop → fresh launch | Self-heal with a notice |
| `wedged` / `unhealthy` (timeout, or channel mismatch) | `refuse_desktop_runtime_or_exit` — **exit 1**, tells user to run `--force-restart` or `doctor`. Does NOT auto-kill. | "Stuck — needs explicit action" |

**Port source (verified at source):** `_resolve_backend_ports` (`cli/desktop_cmd.py:470`). For the `desktop` path `allocate_port_pair_func is None`, so the ports are **strictly** `channel_spec.proxy_port` / `channel_spec.web_port` — no ephemeral / auto-increment fallback. Before binding, it probes both fixed ports with `port_in_use_func` (`cli/net.py::port_in_use`, a `connect_ex` probe) and, if occupied by something it could not recover, calls `raise_port_in_use` → `error: <label> port <N> is already in use … pick a different port with --web-port`, **exit 2**.

**Stop / reclaim primitive:** `stop_desktop_record` (`desktop_runtime.py`) reads the record, SIGTERMs the pid, polls `is_pid_alive` for `timeout_s=3.0`, escalates to SIGKILL on timeout, then unlinks `desktop.json`. It waits on the **PID**, not on the OS releasing the port. Callers: `channel stop` (`cli/channel_cmd.py`), and the recover / force-restart helpers in `cli/desktop_recovery.py`.

**Idempotency is tested.** `cli/test_desktop_idempotent.py::test_run_desktop_detached_live_runtime_attaches_without_backend` asserts a relaunch against a live record spawns exactly one viewer with the backend `popen_func` set to `pytest.fail("backend should not start")`. Companion tests cover absent→start, dead→recover (no SIGTERM), refused→recover (SIGTERM + warning), transient timeout→retry→attach, persistent timeout→refuse (exit 1, no kill), `--force-restart`→SIGTERM live pid, and foreign listener→exit 2.

> Note: the ephemeral `allocate_port_pair` (`cli/ports.py`) + EADDRINUSE retry-with-reallocation (`cli/bind_failure.py`) belong to the separate `start` / `claude` / `codex` mitmdump proxy-launch path, **not** the `desktop` path. The desktop app is always fixed-port.

## 4. Where each mode must be the SAME vs may DIFFER

**Must be the same (and already is):**
- Fixed-port-per-channel binding (`_resolve_backend_ports`, no ephemeral fallback for `desktop`).
- The discover → reuse / recover / refuse decision table (`run_desktop_detached`).
- The stop/reclaim primitive (`stop_desktop_record`).

**Legitimately differs:**
- **Channel set:** prod = 1 default channel (`stable`); dev = `stable` + `preview` concurrent. This is the *only* fundamental difference, and the fixed-port model handles it natively because ports are per-channel.
- **Rebuild step:** dev's `just channel-restart` rebuilds bundles from the working tree before launching; prod launches the wheel-bundled assets directly. This is a build concern, not a port concern.
- **Relaunch ergonomics surface:** dev uses the `channel` subcommands + justfile recipe; prod uses `transport-matters desktop` (idempotent) and `desktop --force-restart`.

## 5. REUSE: is `just channel-restart` the prod reclaim primitive?

**No — and it should not be.** `just channel-restart` is a *developer* convenience wrapper that (a) rebuilds www + desktop from the working tree and (b) force-stops before relaunch. A production user has no working tree, no `just`, no source checkout (`repo_root()` would fail). The **real** reclaim primitive that both modes already share is the `run_desktop_detached` discovery logic plus `stop_desktop_record`. Production relaunch is already covered by:
- `transport-matters desktop` → automatic reuse (live) or self-heal (stale/not-serving).
- `transport-matters desktop --force-restart` → forced reclaim.
- `transport-matters channel stop` → explicit stop.

So the model generalizes cleanly: **prod = the same reclaim primitive applied to the single default channel; dev = the same primitive applied to stable + preview, wrapped in a rebuild recipe.** No separate Electron-app lifecycle is needed.

## 6. Where the model has a sharp edge (owner's attention)

The fixed-port + reclaim story is fully coherent **except** at two states, which are the only places "relaunch reclaims it" is NOT automatic:

1. **Wedged / unhealthy same-channel backend** → relaunch **refuses (exit 1)** and tells the user to run `--force-restart` or `doctor`. For a *developer* this is fine. For a *non-technical production user* who just wants to reopen a stuck app, "exit 1, run a flag" is a UX cliff. Consider: should production `desktop` auto-escalate a wedged self-owned backend to a force-restart (with a notice), reserving the refusal only for ambiguous/foreign cases?
2. **Foreign process squatting the fixed port** → **exit 2**, "pick a different port with --web-port." Correct and safe, but a fixed-port design means a production user cannot trivially dodge a port conflict (e.g. another app on 8788) without learning the flag. This is the inherent trade-off of fixed ports; it is rare but worth a one-line doctor hint.

Everything else — the common "close and reopen" loop — already reclaims the fixed port automatically and is proven idempotent by tests.

## Open questions for the owner

- Should production `desktop` (default channel) auto-recover a *wedged* self-owned backend instead of refusing with exit 1, to spare non-technical users the `--force-restart` step?
- Should the fixed-port collision (exit 2) path surface a `doctor`-style remediation hint, given production users cannot easily change the port?
- Is `preview` ever intended to reach production users, or is it strictly a dev/dogfood channel? (Affects whether the channel concept should be documented user-facing at all.)

---
title: Transport Matters cross-platform build and UI road-test plan
type: projects
tags: [transport-matters, python-wheel, uv, postgres, mitmproxy, electron, cross-platform, windows-arm64, linux, vm, road-test, launch]
summary: How to build and manually road-test the transport-matters UI on Windows and Linux from an Apple Silicon Mac before launch. The product is a Python wheel (mitmproxy + FastAPI + embedded React UI) installed via uv, with a thin Electron shell and an EXTERNAL Postgres. Covers the real native-dependency surface (psycopg/cryptography wheels, the missing win_arm64 wheels), the POSIX-pty Windows terminal blocker, Postgres provisioning per environment, local VM and cloud x64 options, and a per-platform UI checklist.
status: active
created: 2026-06-13
updated: 2026-06-13
project: transport-matters
confidence: high
related: [transport-matters-launch, transport-matters-capture-roadtest, transport-matters-desktop-cockpit-spec, apple-containers-macos-2026]
---

# Transport Matters cross-platform build and UI road-test plan

Goal: before launch, manually operate the transport-matters UI on **Windows and Linux** from the dev machine (M2 Max, macOS 26.5.1, arm64). This doc is the build/runtime matrix, the test rig, and the click-through checklist, grounded in the app's actual architecture. Apple Containers deep dive: `apple-containers-macos-2026.md`. Editorial launch plan: `transport-matters-launch.md`. API capture runbook: `transport-matters-capture-roadtest.md`.

## The architecture that drives testing

transport-matters is not a self-contained Electron app. The distributable is a **Python wheel** plus a thin Electron shell:

- Backend: a **Python wheel** (`transport-matters`, installed via `uv tool install transport-matters`) running **mitmproxy** (`mitmdump`) with a **FastAPI** server as an addon, serving the embedded **React UI** (`api/src/transport_matters/www/`). Entry: `desktop/src/backendProcess.ts:82` spawns the `transport-matters` CLI; the FastAPI app starts inside mitmdump via `api/src/transport_matters/addon.py`.
- Database: **Postgres via `psycopg[binary,pool]` v3**, **external server required**. No SQLite, no embedded Postgres, no pglite. Config via `TRANSPORT_MATTERS_DATABASE_URL` or `settings.toml` at `~/.transport-matters/` (`api/src/transport_matters/config.py`). Dev uses a docker-compose Postgres on `localhost:55432`.
- Terminals: **Python stdlib `pty`** (`api/src/transport_matters/supervisor.py:10`), POSIX-only.
- Electron shell: thin, **prebuilt Electron binaries** (no native node modules, no electron-builder). `@electron/packager` is used for a smoke test only; Windows/Linux desktop packaging is not configured yet.

The practical consequence: "operate the UI on Windows/Linux" means running the **Python backend** on the target OS/arch, pointing it at a reachable Postgres, and opening the React UI (in a browser today, optionally the Electron cockpit later). Cross-platform risk lives in the **Python runtime and its native wheels**, not in an Electron build matrix.

## Three launch-blocking findings

### 1. Windows terminals are broken as built (top risk)

Terminals use Python's stdlib `pty`, which exists only on POSIX. `import pty` fails on Windows. As written, the terminal feature will not run on Windows at all. Resolution paths: implement a Windows PTY backend (ConPTY via `pywinpty`) behind the existing terminal bridge, or scope terminals out of the Windows launch and degrade gracefully. Validate first by running the backend on Windows and opening a terminal pane.

### 2. Postgres is external, so every test environment needs one

The app does not provision its own database. To road-test the UI on any Windows or Linux environment you must give it a reachable Postgres. Options, cheapest first:
- Run the existing **docker-compose Postgres inside the VM** (or via Apple Containers / Docker on the host and point the VM at it).
- Point `TRANSPORT_MATTERS_DATABASE_URL` at a Postgres reachable from the VM (the host Mac, or a cloud/Supabase instance).

This is also a **product launch gap to confirm**: the `uv tool install` / `curl | bash` install story does not stand up Postgres for end users. Validate the end-user Postgres provisioning plan (bundle a container, require Docker, ship an embedded option, or point at managed Postgres) before launch.

### 3. No win_arm64 wheels, so x64 is the reliable Windows path

Verified on PyPI (June 2026): neither `psycopg-binary` 3.3.4 nor `cryptography` 49.0.0 publish a `win_arm64` wheel (Windows = `win_amd64` only). A native Windows-on-ARM Python install would have no binary wheels for these and would fall back to building from source (Rust + libpq + MSVC), which fails for a casual road-test. **Install x64 Python on Windows instead** (native on cloud x64, or under Prism emulation in the local ARM VM). Linux ships full `aarch64` wheels, so arm64 Linux installs cleanly and natively.

This inverts the usual Electron advice: there is no reason to chase a native win-arm64 build here. Prebuilt Electron already handles arch for the thin shell, and the Python deps steer Windows testing to x64.

## Runtime + wheel matrix

| Target | Native-arch Python wheels? | Recommended approach |
|---|---|---|
| Windows x64 | Yes (`win_amd64`) | Primary. What most Windows users run. |
| Windows ARM64 | No win_arm64 for psycopg/cryptography | Install **x64 Python**, run under Prism emulation (local ARM VM) or native on a cloud x64 desktop. |
| Linux x64 | Yes (manylinux x86_64) | Primary. What most Linux users run. |
| Linux ARM64 | Yes (manylinux/musllinux aarch64) | Native, clean. UTM arm64 Ubuntu desktop. |
| macOS arm64 | Yes | Native dev surface. |

## Local VM options (verified, mid-2026)

| Product | Cost | Win11 ARM | Setup | Verdict |
|---|---|---|---|---|
| Parallels Desktop | $99.99/yr or $129.99 perpetual | Best, Microsoft-authorized, one-click | Low | Frictionless, paid |
| VMware Fusion | Free incl. commercial (Broadcom, Nov 2024) | Supported, source the image yourself | Medium | Free runner-up |
| UTM (QEMU + Apple Virtualization) | Free, open-source | Yes, also best for Linux guests | Medium | Best free + Linux choice |
| VirtualBox | Free | Non-production developer preview | High | Avoid on Apple Silicon |

Parallels pricing came from secondary aggregators (the buy page renders prices in JS); confirm on the live buy page before paying. Everything else is from primary vendor sources. Linux GUI: UTM with the Apple Virtualization backend running an **arm64 Ubuntu desktop** gives a real window manager at near-native speed, free, and gets native aarch64 wheels.

## Cloud x64 options (use for native x64 Windows without emulation)

Because Windows testing wants x64 here, a cloud x64 Windows desktop is more attractive for this app than it would be for a native-arm Electron build: it avoids Prism emulation entirely and gets native `win_amd64` wheels.

| Option | Use it? | Billing fit | Notes |
|---|---|---|---|
| Azure Virtual Desktop (PAYG) | Yes | Good, per-second compute | More setup (Azure tenant). 20% cut effective May 2026 (medium confidence). |
| AWS WorkSpaces AutoStop | Yes | Good, low base + hourly when used | "Best for occasional users." |
| AWS EC2 Windows on-demand | Maybe | Fair, hourly, cheapest raw | DIY RDP; Windows Server, not 11 client. |
| Windows 365 Cloud PC | No | Poor, fixed monthly per user | Wrong shape for a one-off pass. |
| Microsoft Dev Box | No | n/a | Maintenance mode, sign-ups closed Nov 1, 2025. |
| BrowserStack / LambdaTest / Sauce | No | n/a | Cannot install/drive a packaged desktop build. Web + mobile-native only. |

## Simplest road-test path

The Electron cockpit is not yet packaged for Windows/Linux, and the UI is served over HTTP by the Python backend, so the lowest-friction road-test is the **web UI in a browser**:

1. Stand up Postgres (docker-compose, or `TRANSPORT_MATTERS_DATABASE_URL` to a reachable instance).
2. Install the tool: `uv tool install transport-matters` (x64 Python on Windows; native arm64 on Linux).
3. Run `transport-matters claude --web-port 8765 <project>` (per the capture runbook).
4. Open the printed web UI URL in the VM's browser and operate it.

Add the Electron cockpit to the road-test only once Windows/Linux packaging exists.

## Per-platform UI road-test checklist

Operate the real backend, not a dev server.

**Setup (both platforms)**
- Postgres reachable; `uv tool install transport-matters` succeeds (x64 on Windows).
- `transport-matters claude` launches: mitmdump comes up, FastAPI serves, web UI URL prints.
- mitmproxy CA cert installed and trusted on the target OS (cert flow differs per OS), so the client's LLM traffic is captured.

**UI (both platforms)**
- Session canvas: open a session, add/move/resize panes; persistence survives an app restart (confirms Postgres round-trip).
- Resource drops: drag a local file and a URL onto the canvas; both resolve in the resource viewer.
- Dock drag-out / multi-window: drag a pane out and re-dock.
- Themes: switch themes (little-background-lab surface); confirm rendering under paravirtualized GPU.
- Live capture: send a message in the client, confirm wire and transcript turns land (the core thesis).
- App-data paths land in the platform-correct location.

**Windows-specific**
- Terminals: expect failure until a ConPTY backend exists (finding 1). Confirm the rest of the UI degrades gracefully without terminals.
- Compare responsiveness of x64-emulated Python in the ARM VM vs a native x64 cloud desktop on heavy canvas interactions.

**Linux-specific**
- Native arm64 install (UTM Ubuntu) runs clean; terminals work (POSIX pty).
- Wayland vs X11 behaviour if the distro defaults to Wayland.

## GPU caveat

Every Apple Silicon VM exposes only a **paravirtualized** GPU (no passthrough; architecturally blocked). Heavy canvas/WebGL/shader work (the little-background-lab theme surface) will look and perform differently in a VM than on native hardware. Weight a real x64-hardware cloud check more heavily if GPU-bound UI is in scope.

## Open items

- **Validate finding 1**: confirm terminals fail on Windows; decide ConPTY/`pywinpty` backend vs scoping terminals out of the Windows launch.
- **Validate finding 2**: confirm the end-user Postgres provisioning plan for Windows/Linux (bundle, Docker requirement, embedded option, or managed Postgres). This is a launch-readiness gap, not just a test concern.
- Decide whether Windows/Linux Electron cockpit packaging is in scope for v1 or whether the browser-served UI is the launch surface.
- Decide whether win_arm64 support is worth pursuing (requires building psycopg + cryptography from source for Windows ARM; likely not worth it given x64 emulation works).
- Confirm `mitmproxy` proxy mode and CA-cert install behave on Windows for the target LLM clients.

## Sources and related

- Apple Containers deep dive: `apple-containers-macos-2026.md`
- Editorial launch plan: `transport-matters-launch.md`
- API capture runbook: `transport-matters-capture-roadtest.md`
- Desktop cockpit spec: `transport-matters-desktop-cockpit-spec.md`
- Wheel availability checked on PyPI: `psycopg-binary` and `cryptography` JSON metadata (no win_arm64 as of June 2026).
- Electron Windows-on-ARM, electron-builder, WoA Prism emulation, VM and cloud sources as cited in the deep-research pass.

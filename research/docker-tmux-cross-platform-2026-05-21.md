---
title: Docker + Tmux Cross-Platform Patterns for Interactive Container Stdio
type: research
tags: [runtime-matters, alp-2650, docker, tmux, pty, stdio, cross-platform, sandboxing]
summary: Five canonical patterns for routing container stdio to a developer-visible tmux pane, scored on simplicity, cross-platform parity, and disconnect survival. Recommends host-pty + docker-attach (Pattern A) for v1 and a future migration to container-side reconnecting-pty (Pattern D) for parity with Coder/Codespaces.
status: active
confidence: high
created: 2026-05-21
updated: 2026-05-21
related: [alp-2643-host-docker-sandboxing-runtime-matters]
---

## Executive Summary

The container-tty problem reduces to one binding decision: **which side of the docker boundary owns the PTY master**. Every shipping tool (Dev Containers, Codespaces, Coder, agent-deck) makes one of five distinct choices, and the trade-offs (disconnect survival, cross-platform parity, runtime pid visibility, daemon-socket exposure) collapse cleanly along that axis. For rtm's constraints (host-side shim, no daemon socket in the container, host-side tmux as the developer surface, three OS targets), the clean v1 shape is **Pattern A: host-pty + `docker attach` to a detached container**, with **Pattern D (container-side reconnecting-pty over websocket)** as the explicit migration target once we want true disconnect survival across container restarts.

The seductive trap is Pattern E (tmux server inside the container). It looks elegant on macOS, breaks the host-side "respawn-pane -t target" addressability that rtm's tmux backend currently depends on, and fragments badly across the three platforms.

## Background and Constraints

rtm's current spawn path:

```
sm -> rtmd -> tmux respawn-pane -t <pane> -- rtm __shim <runtime> ...
   -> rtm-shim execs <runtime-binary> inside the pane (host)
```

ALP-2643 already pinned host-side decisions: shim stays host-side, daemon socket is not mounted into the container, isolation is policy on `SpawnRequest` rather than a new `SpawnTarget`. ALP-2650's open question is the inverse of the ALP-2643 decision: ALP-2643 rejected Docker+tmux for v1; this gate asks how to support it without violating those invariants.

The five hard constraints, restated:

1. Runtime process runs inside a Docker container.
2. Container stdio is visible in a host-side tmux pane.
3. Disconnect/reconnect survives the run.
4. macOS (Docker Desktop VM) + Linux native + Windows (WSL2 / Docker Desktop on WSL2) all work from one design.
5. Daemon socket is NOT mounted into the container.

A sixth implicit constraint from the existing rtmd contract: `Lifecycle::runtime_pid` must be populated with a host-visible PID for reconcile to work. This forces some patterns out.

## Where the PTY Lives — The Load-Bearing Decision

Every tool in this space sits on one of five PTY placements. Each has a fixed cost on disconnect survival, signal propagation, and platform parity.

| Placement | Multiplexer | Stdio binding | Disconnect survives | Daemon socket needed? |
|---|---|---|---|---|
| A. Host PTY (tmux), `docker attach` reattaches container's PID 1 stdio | host tmux | `docker run -d ... && docker attach` inside pane | container yes, pane state yes | no |
| B. Host PTY (tmux), `docker exec -it` against detached container | host tmux | `docker run -d ... && docker exec -it` inside pane | container yes, exec process dies on detach | no |
| C. Host PTY (tmux), `docker run -it` foreground | host tmux | `docker run -it` directly in pane | nothing survives detach | no |
| D. Container PTY, server in container, host client reattaches | host tmux + container pty server | ttyd / Coder agent / SSH inside container; pane runs websocat/ssh client | container yes, pty server keeps session | no (server speaks its own protocol over published port) |
| E. Container PTY, tmux server in container | container tmux | host pane runs `docker exec -it ... tmux attach` | container yes, tmux session yes | no |

This table is the spine of the rest of the report.

---

## Pattern A — Host PTY, `docker run -d` + `docker attach` inside pane

**Shape.** The shim runs inside the host tmux pane. It starts the container detached (`docker run -d --name <session-id> ...`), then `docker attach`es. The dockerd daemon owns the PTY pair: the slave is the container's controlling terminal, the master is exposed through a unix socket on the host. `docker attach` simply binds your terminal's stdin/stdout to that master fd over the daemon socket. Reference: [iximiuz on Docker attach PTY internals](https://iximiuz.com/en/posts/linux-pty-what-powers-docker-attach-functionality/).

**Stdio binding.** Pane PTY (tmux's slave) <-> shim stdin/stdout <-> docker CLI <-> dockerd <-> containerd-shim <-> container PID 1's stdio fds.

**Disconnect / reconnect.** The container keeps running because it was started with `-d`. The PTY pair lives in the daemon and persists. Reattaching is `docker attach <name>` again. Crucially, **multiple clients can attach simultaneously** to the same container — dockerd maintains a linked list of attached sockets and broadcasts master output to all of them. That means the dev can detach from tmux pane and re-attach from a new pane without losing the run.

**Cross-platform.** dockerd is the same Linux process inside Docker Desktop's VM on macOS, inside the WSL2 VM on Windows, and on the host on Linux. The PTY always lives inside that Linux execution context. The host tmux is whatever the dev runs natively (macOS terminal + tmux, Windows Terminal + WSL2's tmux, Linux native tmux). The docker CLI on each platform speaks the same wire protocol to dockerd.

**Signal handling.** PID 1 problem applies: the container should run `tini` (`--init`) or `dumb-init` so SIGINT from Ctrl+C in the pane reaches the runtime correctly. `docker attach --sig-proxy=true` (default) maps the pane's Ctrl+C to a SIGINT delivered to PID 1. Without tini, signals to PID 1 are silently dropped unless the runtime explicitly installs handlers. See [tini](https://github.com/krallin/tini), [dumb-init](https://github.com/Yelp/dumb-init).

**Runtime pid visibility.** `docker inspect --format '{{.State.Pid}}' <name>` returns the **host-visible** PID of the container init process (on macOS/Windows this PID is inside the VM, but on Linux it is the host PID). For reconcile parity, the rtm lifecycle pid is the docker PID (host process executing `docker attach`) or the container init PID retrieved post-spawn.

**Trade-offs.**

- (+) Simplest design. No new process inside the container beyond the runtime + tini.
- (+) Survives dev detach trivially. Container is detached from birth.
- (+) Cross-platform parity is perfect — dockerd does the work, OS doesn't matter.
- (+) Daemon socket stays out of the container. Only the host shim touches it.
- (-) On Linux only, `docker inspect`'s pid is the true host pid; on macOS/Windows it is a VM-internal pid. Reconcile must treat the "container init pid" as opaque to the VM and rely on `docker inspect <name>` rather than `kill(pid, 0)` for liveness. This is the **single platform asymmetry** in this pattern.
- (-) Detach key sequence is `Ctrl-P Ctrl-Q` by default, which clashes with tmux's prefix on some configs. `--detach-keys=""` or remapping is required.
- (-) When the container's main process exits, `docker attach` exits and the pane goes dead — same as the current tmux-respawn-pane host path, so semantically aligned.

**What this means for rtm.** This is the closest analogue to the current `tmux respawn-pane -- rtm __shim ... runtime` flow. Swap the inner command from `rtm __shim ... <runtime-bin>` to `rtm __shim ... docker run -d ... && docker attach ...`. The shim stays the pane's foreground process. The runtime pid in `Lifecycle::runtime_pid` becomes the docker-CLI pid on host (or, for richer telemetry, the container init pid from `docker inspect`).

---

## Pattern B — Host PTY, `docker run -d` + `docker exec -it`

**Shape.** Same outer shell as A, but instead of attaching to PID 1, the pane shells into a *new* process inside the container via `docker exec -it`. The agent runs as PID 1 in the background; the pane sees a shell (or directly execs the runtime as a non-PID-1 process).

**Stdio binding.** Pane PTY <-> docker CLI <-> dockerd <-> exec session in container (separate PTY pair from PID 1's).

**Disconnect / reconnect.** Container survives. The exec process, however, **dies when the pane disconnects** — its stdio fds are tied to the now-broken pane PTY. This is the fundamental difference from `docker attach`: each exec session has its own PTY pair, and that PTY pair is destroyed when the client disconnects.

For agent runs that are themselves the long-running PID 1, this is fine — the runtime keeps running, and the exec session was just a window into it. But if the runtime is run *as* the exec command, reconnect requires either knowing the runtime is still alive (it isn't) or having a wrapper that started the runtime inside the container with its own session manager (a la dtach/abduco/tmux *inside* the container — see Pattern E).

**Cross-platform.** Same as A. Identical mechanics.

**Trade-offs.**

- (+) Same simplicity and parity as A.
- (+) Cleaner separation: agent always runs as PID 1, never re-spawned; the human's window is a discrete exec session.
- (-) **Disconnect kills the visible run unless you split the runtime from the visible exec.** This is the killer: it forces either Pattern E (in-container multiplexer) or accepting a UX regression vs current tmux flow.

**What this means for rtm.** Only viable if the runtime is launched separately (e.g., via `docker exec -d <session-id> runtime ...` to background-start it inside the container) and the pane separately `docker exec -it`s into a `tail -f` / `tmux attach` / dtach reattach. This adds an in-container multiplexer concept that Pattern A avoids. Skip unless we explicitly want disconnect-survives-mid-run.

---

## Pattern C — Host PTY, `docker run -it` foreground in pane

**Shape.** The naive baseline. Pane runs `docker run -it --rm <image> <runtime>`. Container's lifetime is tied to the pane.

**Disconnect / reconnect.** Nothing survives. Closing the pane sends SIGHUP, the docker CLI exits, and `--rm` removes the container. Even without `--rm`, the container stops because PID 1's stdio went away (depends on PID 1 behavior, but typically yes).

**Trade-offs.**

- (+) Simplest possible mental model.
- (-) Fails constraint (c) outright. Not a serious option for v1.

**What this means for rtm.** Useful as the "ephemeral one-shot" or test mode. Not the default.

---

## Pattern D — Container-side PTY server, host pane is a thin client

**Shape.** A tiny in-container daemon (ttyd, gotty, openssh-server, or a custom one like Coder's agent) owns a PTY pair and exposes a websocket/HTTP/SSH endpoint on a published container port. The host tmux pane runs a thin client (websocat, ssh, ttyd's client) that streams the PTY master over the network. Reference: [ttyd](https://github.com/tsl0922/ttyd), [Coder reconnecting-pty pattern](https://github.com/coder/coder/pull/15201).

**Stdio binding.** Pane PTY <-> in-pane client (`ssh` / `websocat`) <-> host TCP socket on container port <-> in-container pty server <-> agent runtime.

**Disconnect / reconnect.** This is the architecture that gives **true disconnect survival**. The pty server keeps the PTY pair alive in the container even when no client is attached. The agent doesn't notice the dev came and went. Coder's "reconnecting-pty" routes a session id through to the agent, so a reconnect after WS drop re-attaches the same session. GitHub Codespaces uses this shape (SSH server inside the container + `gh cs ssh` client).

**Cross-platform.** The container port works the same way on all three platforms (Docker handles port publishing through the VM on macOS/Windows). The host pane just runs a TCP client. Zero platform-specific code on the host side.

**Signal handling.** Signals from the pane are translated by the in-container pty server. Coder's agent and ttyd both proxy SIGINT correctly. PID 1 still wants tini for orphan reaping.

**Runtime pid visibility.** `docker inspect <name>` still gives us the container init pid for liveness. The runtime process itself is a child of the pty server, addressable inside the container but not directly from the host.

**Trade-offs.**

- (+) Best disconnect/reconnect story. Survives pane death, tmux server restart, host reboot of the tmux client.
- (+) Multiple developers can attach to the same session if the server allows.
- (+) Cleanly cross-platform.
- (-) Requires a process inside the container we don't otherwise need. Either burned into the agent image (ttyd) or sidecar'd at spawn time.
- (-) Port published on host or routed via docker network — operational footprint we don't have today.
- (-) "Where is the runtime running" becomes more abstracted from `docker inspect`.

**What this means for rtm.** This is the right destination architecture once we want first-class disconnect survival. The Coder and Codespaces designs are the proof. But it adds infrastructure (in-container pty server, port management) we don't have today. Defer to v2 once Pattern A has shipped and we have real demand for survival across container restarts.

---

## Pattern E — tmux server inside the container, host pane attaches to it

**Shape.** `docker run -d` starts a container whose PID 1 (under tini) is `tmux new -s s -d`. The agent runs as a window inside the container's tmux server. The host tmux pane runs `docker exec -it <name> tmux attach -t s`.

**Stdio binding.** Host pane PTY <-> docker exec session <-> in-container tmux client <-> in-container tmux server <-> agent runtime.

**Disconnect / reconnect.** Container's tmux server keeps the session, agent keeps running. Reattach is a fresh `docker exec -it ... tmux attach`. Survival is excellent.

**Cross-platform.** All three platforms work, since tmux is fine inside the Linux container regardless of host OS.

**Trade-offs.**

- (+) Disconnect survives without inventing a custom pty server.
- (+) The agent never sees a stdio close, even between dev sessions.
- (-) **Breaks host-side tmux addressability**. rtmd's current contract is `respawn-pane -t <session:window.pane>` against the host tmux server. If the tmux that the runtime actually lives in is *inside* the container, the host's tmux loses the ability to identify, kill, or send-keys to the runtime by host-pane id. We'd need a dual-tmux model and reconcile across both.
- (-) Two tmux servers in the dev's mental model (host one for "where the pane lives", container one for "where the runtime lives") — Windows devs would have to grok this even though they don't natively run tmux at all.
- (-) Brittle in classic ways: `not a terminal` errors when the entrypoint isn't run with `-it`, tmux's $TERM expectations, "open terminal failed" when arguments don't add up. Documented widely; see [ptrj's tmux-in-docker gist](https://gist.github.com/ptrj/b54b8cdd34f632028e669a1e71bc03b8).

**What this means for rtm.** Strongly avoid as the primary design. It violates the "host tmux is the addressable surface" assumption that the rest of the daemon is built around. It is reasonable only as an *internal* in-container survival mechanism behind a Pattern D server (dtach/abduco are lighter alternatives if we go down that road).

---

## How shipping tools actually place the PTY

| Tool | Pattern | Notes |
|---|---|---|
| **VS Code Dev Containers** | A (sort of) + custom protocol | `docker exec` to a long-lived `vscode-server` inside the container. Server speaks VS Code's own RPC over docker-exec stdio; the terminal panel multiplexes named PTYs. No host tmux. Across platforms, identical, since dockerd does the heavy lifting. |
| **GitHub Codespaces** | D | sshd inside the codespace, `gh cs ssh` from host. Survives disconnect because the codespace VM (not just container) keeps running, and sshd keeps PTY state. |
| **Coder workspace agent** | D with reconnecting-pty | The agent ([coder docs](https://coder.com/docs/reference/api/agents)) exposes `/api/v2/workspaceagents/{id}/pty` over websocket. Sessions are addressed by id, so a reconnect after WS drop re-binds to the same PTY without restarting the shell. PTY lives in the workspace (which may be a container, VM, or bare metal — pattern is uniform). |
| **JetBrains Gateway** | D over SSH tunnel | Backend IDE in container/VM/host, terminal is the workspace's tty via SSH-tunneled gRPC. |
| **agent-deck** ([asheshgoplani/agent-deck](https://github.com/asheshgoplani/agent-deck)) | A with hotkey | Host tmux is the developer surface. Container is bind-mounted. `T` hotkey on a sandboxed pane drops into `docker exec -it ... sh` for a shell. Agent runs in container. Closest match to rtm's constraints I found in the wild. |
| **Anthropic Claude Code sandboxing** | Not docker | Uses macOS Seatbelt / Linux+WSL2 bubblewrap. The sandbox is process-level, so the agent's tty *is* the parent shell's tty. No container in the loop, so no PTY-placement question. Worth noting as a "the docker dimension is optional" datapoint. |
| **Tilt / Skaffold / DevSpace** | B-ish | `kubectl exec` from host into pods. Tilt explicitly punts: the UI shows pod ids and tells you to run `kubectl exec` yourself in a terminal. DevSpace integrates a terminal panel that exec's into a pod and reuses the kubernetes remotecommand protocol (now [WebSockets in 1.31+](https://kubernetes.io/blog/2024/08/20/websockets-transition/)). |

The pattern boundary is crisp: **B and C lose the run on disconnect; A survives the run but kills the visible pane; D and E both survive both**. Industry tools that prioritize survival pick D (Codespaces, Coder, JetBrains). Tools that prioritize simplicity and host-tmux integration pick A (agent-deck).

## Cross-Platform Mechanics Summary

| Platform | Where dockerd runs | Where Linux container PID 1 lives | Host tmux runs in | Pty placement implications |
|---|---|---|---|---|
| Linux native | Host process | Host kernel namespaces | Host shell | Container init PID is a real host PID. `docker inspect` returns a usable host pid. |
| macOS (Docker Desktop) | Inside LinuxKit VM | Inside the VM | Host (macOS) shell | Container init PID is **VM-internal**; host has no direct PID. Liveness has to go through `docker inspect`. The PTY is also VM-internal; `docker attach` traverses the host docker socket -> VM dockerd -> shim -> pty. |
| Windows (Docker Desktop on WSL2) | Inside WSL2 distro | Inside the distro | Either Windows Terminal -> WSL2 distro -> tmux, or directly in WSL2 distro | Same as macOS conceptually. PTY is in the WSL2 distro. The host pane is whichever distro the dev runs tmux in (most likely the same one that holds the docker CLI). |

**The cross-platform load-bearing fact**: `docker run` and `docker attach` semantics are identical across all three. dockerd hides the VM. As long as the design routes through `docker` CLI commands and treats container init pids as opaque (use `docker inspect` for liveness, not `kill -0`), the same code path works everywhere. Patterns A, B, C, D inherit this for free. Pattern E inherits it too, but adds the in-container tmux server complication on top.

The one explicit Windows wrinkle: dev's "host tmux" likely lives inside WSL2, not on Windows itself. There is no Windows-native tmux equivalent that fits our model. ConPTY exists at the Windows kernel level but isn't a multiplexer. So the Windows story is "run tmux in WSL2, use the same docker CLI you'd use on Linux". This is already the recommended posture in the docker docs and is how Claude Code's WSL2 sandbox path is documented.

## PID 1 and Signal Handling — Required in Every Pattern

Regardless of which pattern, the container needs `tini` or `dumb-init` as PID 1. Reasons documented many times ([tini README](https://github.com/krallin/tini), [Yelp dumb-init post](https://engineeringblog.yelp.com/2016/01/dumb-init-an-init-for-docker.html), [Peter Malmgren's PID 1 piece](https://petermalmgren.com/signal-handling-docker/)):

1. Without an init, PID 1 receives signals only if it explicitly handles them. The kernel does not fall back to default behavior for PID 1. Ctrl+C in the pane becomes a no-op.
2. Zombie reaping. Without an init, exited children stick around until container exit. Long-running agent processes that spawn subagents will accumulate them.
3. `docker run --init` injects `tini` automatically. Cheapest correct default for rtm's docker backend.

For Pattern A, this is mandatory because the pane sends Ctrl+C through `docker attach --sig-proxy` -> dockerd -> shim -> kill(PID 1, SIGINT). If PID 1 is the agent process with no signal handler, Ctrl+C is silently swallowed.

## Recommendation Lattice

Five design shapes, scored on the three rtm-relevant axes. Higher is better; max 3.

| Shape | Simplicity | Cross-platform parity | Disconnect survival | Total | Verdict |
|---|---|---|---|---|---|
| A: host tmux, `docker run -d` + `docker attach` | 3 | 3 | 2 | **8** | **v1 default**. Closest to current rtm tmux flow; minimal new surface; container outlives pane close. |
| B: host tmux, `docker run -d` + `docker exec -it` | 2 | 3 | 1 | 6 | Skip unless we add an in-container multiplexer. The exec session dies on disconnect, taking the visible run with it. |
| C: host tmux, `docker run -it` foreground | 3 | 3 | 0 | 6 | Useful only as ephemeral one-shot mode (`rtm spawn --isolation=docker --ephemeral`). Not the default. |
| D: container-side pty server + host thin client (ttyd / SSH / coder-rpty pattern) | 1 | 3 | 3 | 7 | **v2 target**. Right architecture for true survival across container restart. Adds in-container daemon + port management. Defer until A's limitations bite. |
| E: tmux server inside container | 1 | 2 | 3 | 6 | **Avoid as primary**. Breaks host-side tmux addressability that rtmd already depends on. Reasonable only as an internal survival mechanism *behind* Pattern D, and even then dtach is lighter. |

### Recommended path for ALP-2650

1. **Worker 1 — Pattern A as default for `--target tmux --isolation docker`.** Shim runs in host pane and execs `docker run -d --name <session-id> --init --rm=false ... <image> <runtime-cmd>` then `docker attach --detach-keys=<chosen> <session-id>`. Lifecycle pid = host docker-CLI pid; container init pid recorded as a separate `Lifecycle::container_pid` for telemetry.
2. **Worker 2 — Reject Pattern E loudly.** Add a preflight rule that fails any spawn whose image baked-in entrypoint launches its own tmux server, with a doctor pointer. Avoids the "two tmuxes" cliff.
3. **Optional Worker 3 — Pattern C as opt-in for tests.** `--isolation=docker --ephemeral` runs `docker run -it --rm` foreground in the pane. Used by integration tests where survival is not required.
4. **Future, post-v1 — Pattern D as the disconnect-survival upgrade.** Introduce an in-container `rtm-runtime-agent` that owns a reconnecting-pty over websocket on a published port. Host pane runs `rtm-attach <session-id>` as a thin TCP client. Same shim placement; same daemon; only the pane-side command changes.

### Why not Pattern D in v1

We do not yet need disconnect survival across container restart. The current host-tmux path doesn't survive tmux server restart either, so Pattern A delivers parity with the existing UX. Pattern D's payoff lands only once we promise "your agent keeps running across reboot of your laptop", which is a v2 product claim.

### Why not Pattern E ever

The K8s mental model is `kubectl exec`, not `kubectl in-pod-tmux`. The daemon owns placement; the container owns runtime; the multiplexer is the dev's host surface. Putting a multiplexer in the container double-counts the role tmux plays and fights with rtmd's tmux backend selector. The architectural cost is permanent; the only upside is survival, which Pattern D delivers more cleanly.

## Sources Consulted

### PTY and stdio internals
- [Linux PTY — How docker attach and docker exec work inside (iximiuz)](https://iximiuz.com/en/posts/linux-pty-what-powers-docker-attach-functionality/) — primary technical reference for where the PTY lives and how attach multiplexes
- [Implementing Container Runtime Shim: Interactive Containers (iximiuz)](https://iximiuz.com/en/posts/implementing-container-runtime-shim-3/) — shim-level scatter/gather pattern for stdio
- [Docker Run, Attach, and Exec — How they work under the hood (iximiuz Labs)](https://labs.iximiuz.com/tutorials/docker-run-vs-attach-vs-exec) — full chain `terminal <-> docker CLI <-> dockerd <-> containerd <-> shim <-> app`

### Tool architectures
- [Coder agent API reference](https://coder.com/docs/reference/api/agents) — `/api/v2/workspaceagents/{id}/pty` endpoint
- [coder/coder PR #15201 — close server pty connections on client disconnect](https://github.com/coder/coder/pull/15201) — pty bicopy timeout details
- [GitHub Codespaces SSH usage](https://docs.github.com/en/codespaces/developing-in-a-codespace/using-github-codespaces-with-github-cli) — sshd-in-container pattern
- [VS Code Dev Containers — Developing inside a container](https://code.visualstudio.com/docs/devcontainers/containers) — `docker exec` to in-container vscode-server
- [devcontainer CLI exec docs](https://stuartleeks.github.io/devcontainer-cli/exec.html) — confirms `devcontainer exec` is `docker exec` plus path/user resolution
- [JetBrains Gateway deep dive](https://blog.jetbrains.com/blog/2021/12/03/dive-into-jetbrains-gateway/) — SSH-tunneled backend
- [asheshgoplani/agent-deck](https://github.com/asheshgoplani/agent-deck) — closest in-wild analogue to rtm's tmux+docker target
- [trekhleb/claude-pod](https://github.com/trekhleb/claude-pod) — Claude Code in docker without tmux
- [Anthropic Claude Code sandboxing](https://code.claude.com/docs/en/sandboxing) — Seatbelt/bubblewrap path; not docker, but informs the "sandbox is process-level" alternative

### Multiplexers and pty servers
- [ttyd (tsl0922)](https://github.com/tsl0922/ttyd) — minimal websocket pty server
- [gotty (sorenisanerd)](https://github.com/sorenisanerd/gotty) — Go original of ttyd
- [abduco (martanne)](https://github.com/martanne/abduco) — lightest detach/attach multiplexer alternative
- [tmux in daemonized docker container — gist](https://gist.github.com/ptrj/b54b8cdd34f632028e669a1e71bc03b8) — Pattern E pitfalls in practice
- [Taisun-Docker/tmux entrypoint](https://github.com/Taisun-Docker/tmux/blob/master/entrypoint.sh) — in-container tmux entrypoint reference
- [moul/docker-tmux](https://github.com/moul/docker-tmux) — minimal tmux-in-container image

### PID 1 and signals
- [krallin/tini](https://github.com/krallin/tini) — `--init` flag default
- [Yelp/dumb-init](https://github.com/Yelp/dumb-init) — alternative init
- [PID 1 Signal Handling in Docker (Peter Malmgren)](https://petermalmgren.com/signal-handling-docker/) — primary writeup of the PID 1 kernel quirk
- [Orphan process handling in containerd (Peter Malmgren)](https://petermalmgren.com/orphan-children-handling-containerd/)
- [moby/moby #28872 — docker client doesn't pass signals when terminal attached](https://github.com/moby/moby/issues/28872)

### Cross-platform
- [Docker Desktop WSL2 backend](https://docs.docker.com/desktop/features/wsl/) — Windows path
- [lima-vm/lima](https://github.com/lima-vm/lima) — macOS alternative VM, same Linux-on-host model
- [Bret Fisher — getting a shell in Docker Desktop Mac VM](https://gist.github.com/BretFisher/5e1a0c7bcca4c735e716abf62afad389) — confirms PTY lives in the VM on macOS
- [Kubernetes 1.31 streaming transition SPDY → WebSockets](https://kubernetes.io/blog/2024/08/20/websockets-transition/) — protocol-level analog of pattern D

## Source Quality Assessment

- **High confidence**: PTY placement claims (iximiuz primary source), `docker attach`/`exec` semantics (Docker docs + multiple corroborating posts), tini necessity (Docker `--init`, Anthropic engineering posts, Yelp post).
- **Medium confidence**: Coder reconnecting-pty exact wire format — PR comments give the shape but I did not fetch the agent code; the design class is well-attested though. Codespaces SSH internals — only the dev-facing surface is documented.
- **Lower confidence**: How JetBrains Gateway carries terminal data inside its TLS-over-SSH channel. Treated as Pattern D for the purposes of this report; precise framing not in public docs.
- **Gap**: I did not find a public writeup of how agent-deck routes `docker exec` from its host tmux pane in code. The README places it firmly in Pattern A with a hotkey shell escape, but the spawn-side wiring (sidecar vs `docker exec` direct) is undocumented externally.

## Open Questions

1. **Container init pid handling for `Lifecycle::runtime_pid`.** Confirm during implementation whether rtmd's reconcile uses `kill(pid, 0)` style liveness checks; if so, Pattern A on macOS/Windows needs to be wired to `docker inspect <name> --format ...State.Running` instead. ALP-2643 mentions populating `Lifecycle::runtime_pid` from a host-visible Docker process or container init pid "compatible with existing reconcile" — verify which it is before this decision is final.
2. **Detach key clash.** Default `Ctrl-P Ctrl-Q` collides with tmux prefix on some configs. Need a stable per-rtm choice or `--detach-keys=""` (disables detach). For Pattern A, the dev shouldn't need to detach manually — pane close handles it.
3. **Image-baked entrypoint conflicts.** If an image's `ENTRYPOINT` is itself a shell that exec's the runtime, signal handling and PID 1 reaping need explicit verification. The Pattern E preflight rule should also catch obviously-multiplexed entrypoints.
4. **`docker attach` failure modes when stdin is not a tty.** rtm's headless target uses no PTY. Pattern A's `docker attach` requires the pane PTY. Confirm the headless-docker path (already in v1 per ALP-2643) is unaffected.
5. **Workspace mount semantics.** Not addressed here; ALP-2643 deferred. The pattern lattice is orthogonal to mount/network/secrets choices, but a final design needs to confirm the bind-mount of `cwd` doesn't interact with the PTY placement (it shouldn't).

## Actionable Takeaways

- **Decision for ALP-2650 gate**: ship Pattern A as the canonical `--isolation docker --target tmux` shape. Reject Pattern E with a preflight error and a doctor note.
- **Shim contract change**: the shim's command composition stays "host process that becomes the runtime" — but the runtime is now `docker run -d ... && docker attach`. Composer/launcher boundary doesn't need to know it's docker; the backend chooses the command.
- **Runtime pid contract**: lifecycle pid = host pid of the `docker` CLI; add `container_init_pid` (optional, from `docker inspect`) as separate telemetry. Reconcile uses `docker inspect` for liveness, not `kill -0`, on any docker-backed lifecycle.
- **Mandatory `--init`**: docker backend adds `--init` unconditionally unless the user image declares its own tini-equivalent via image label or rtmd config.
- **Documentation**: doctor should explain that on macOS/Windows the container's PID is VM-internal and that `docker inspect` is the liveness source of truth.
- **Future migration path**: when v2 needs survival-across-container-restart, fork Pattern D off Pattern A. The host shim contract barely changes — only the pane-side command flips from `docker attach` to `rtm-attach <session-id>` (TCP client to in-container agent). Backend remains the same.

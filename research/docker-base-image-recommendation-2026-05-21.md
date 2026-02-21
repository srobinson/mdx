---
title: Docker base image recommendation for rtm coding-agent containers
type: research
tags: [docker, rtm, runtime-matters, base-image, devcontainers, claude-code, codex, aider, multi-arch]
summary: rtm should ship Option A (image-agnostic) with documented BYO Dockerfile examples. Reference one canonical base (mcr.microsoft.com/devcontainers/base:ubuntu) plus a docs-only "thin" path on top of node:slim/python:slim. Publishing rtm-branded images is premature; the agent vendors (Anthropic, OpenAI/codex-universal, Aider) are already shipping their own and divergent enough that an rtm meta-image would either duplicate them or rot.
status: active
confidence: high
created: 2026-05-21
updated: 2026-05-21
related: [docker-tmux-cross-platform-2026-05-21]
---

# Docker base image recommendation for rtm coding-agent containers

Follow-up to `~/.mdx/research/docker-tmux-cross-platform-2026-05-21.md`. That research locked Pattern A (host tmux + `docker run -d` + `docker attach`). This research answers the open design call: does rtm ship reference base images, endorse one, or stay BYO?

## Executive summary

**Recommendation: Option A — rtm stays image-agnostic.** Document the contract (`--init` compatible, non-root user, executable agent binary on PATH, workspace mount path), ship example Dockerfiles for the four reference agents (Claude Code, Codex, Aider, generic), and recommend `mcr.microsoft.com/devcontainers/base:ubuntu` as the layering base when the operator does not have a strong opinion.

Why not B (ship `helioy/rtm-agent-base:*`): each agent vendor already publishes or recommends its own image. Anthropic ships `ghcr.io/anthropics/claude-code` plus a devcontainer feature. OpenAI ships `ghcr.io/openai/codex-universal`. Aider ships `paulgauthier/aider`. An rtm-published meta-image would either re-vendor those (maintenance drag, version drift, license surface) or re-implement them thinner (re-invents what Anthropic just published). The win is small and the cost is permanent.

Why not C (endorse one image family): the devcontainers/Codespaces world and the agent-vendor world have not converged. devcontainers/base is the right *starting point* for layering, but it is not what Anthropic, OpenAI, or Aider actually publish for their agents. Endorsing one would lie about the ecosystem.

A is honest about the situation in 2026: the agent vendors are still figuring out their own images, and rtm's job is the substrate, not the contents.

---

## Candidate inventory

For each candidate: registry, multi-arch, compressed size, default user, audience, signals. Sizes are sums of layer-blob bytes from the manifest at the time of writing (May 21, 2026); container-on-disk is roughly 2.5x compressed.

### 1. mcr.microsoft.com/devcontainers/base

- **Registry/tags**: `mcr.microsoft.com/devcontainers/base:{ubuntu, alpine, debian, noble, jammy, bookworm, bullseye, trixie}` plus semver tags.
- **Multi-arch**: amd64 + arm64 native, all variants. Manifest confirmed via `docker manifest inspect`.
- **Compressed size**: `base:ubuntu` 307.8 MB (amd64) / 298.1 MB (arm64). `base:alpine` 256.3 MB / 246.3 MB.
- **Default user**: `vscode` (non-root) with passwordless sudo. UID 1000.
- **Includes**: git, zsh + Oh My Zsh, curl, ca-certs, basic build tooling via buildpack-deps. **No language runtimes.**
- **Security defaults**: works fine under `--read-only` if `/tmp` and `/home/vscode` are mounted as tmpfs/volume; default permissive otherwise.
- **License**: MIT (devcontainers/images repo).
- **Maintainer**: Microsoft, very active (release cadence weekly-ish).
- **Audience**: devcontainer.json users, GitHub Codespaces, JetBrains Space, anyone who wants a clean Ubuntu/Alpine/Debian with sane non-root defaults.
- **Signals**: 2.4k stars on devcontainers/images; the de-facto default if you write `"image":` in devcontainer.json without further thought.
- **Note**: Dockerfile is intentionally minimal — `FROM buildpack-deps:${VARIANT}-curl`, then user setup. This is the right *substrate* for layering.

Source: <https://github.com/devcontainers/images>, <https://mcr.microsoft.com/en-us/product/devcontainers/base/about>, manifest inspect.

### 2. mcr.microsoft.com/devcontainers/universal (GitHub Codespaces default)

- **Tags**: `:linux`, `:2-linux`, `:5.1-linux`.
- **Multi-arch**: **amd64 ONLY**. The manifest list contains no arm64 entry. **On Apple Silicon this silently QEMU-emulates and runs like garbage.** This is a hard disqualifier for a recommended-default image.
- **Compressed size**: 3.7 GB (amd64).
- **Default user**: `codespace` (non-root) with sudo.
- **Includes**: Python (multiple), Node (multiple via nvm), Go, Ruby, Java, .NET, PHP, C/C++, Rust, jq, GitHub CLI, Docker-in-Docker, conda. Kitchen sink.
- **Audience**: GitHub Codespaces users who want zero-config "it just works" for any language. Heavy.
- **Verdict**: useful as a *fallback* for `--image` when an operator wants a kitchen-sink workspace, but unsuitable as rtm's default given the arm64 gap.

Source: <https://github.com/devcontainers/images/tree/main/src/universal>, manifest inspect.

### 3. gitpod/workspace-base and workspace-full

- **Multi-arch**: **amd64 ONLY** for both. Single-manifest images, not a manifest list. Confirmed via `docker buildx imagetools inspect`. Hard disqualifier for Apple Silicon defaults.
- **Compressed size**: workspace-base 708 MB. workspace-full 3.15 GB.
- **Default user**: `gitpod` (UID 33333). Bash configured with `.bashrc` for VS Code integration.
- **Includes (base)**: Ubuntu 22.04, sudo, git, build-essential, curl, custom prompt. (full): Docker, Nix, Go, Java, Node, C/C++, Python, Ruby, Rust, PHP, plus Homebrew, Tailscale, Nginx.
- **Audience**: Gitpod (now Ona) cloud workspaces; people who replicate the Gitpod env locally.
- **Signals**: still actively published; Gitpod the company rebranded to Ona in 2025 and pivoted toward "Secure Infrastructure for AI-Generated Code." Workspace-images repo still receives commits.
- **Verdict**: no arm64 means it cannot be a default. Useful as a reference for what "kitchen sink dev workspace" looks like, but rtm should not depend on it.

Source: <https://github.com/gitpod-io/workspace-images>, buildx imagetools inspect.

### 4. codercom/enterprise-base, codercom/code-server

- **enterprise-base multi-arch**: **amd64 ONLY** per the layer-detail URLs and Coder docs. Coder explicitly recommends building your own image; their published one is "for backward compat, codercom/example-base is recommended for new deployments." Not a strong endorsement to build on.
- **code-server**: amd64 + arm64; this is the VS Code-in-the-browser image, not a base for an agent.
- **Audience**: Coder enterprise workspace templates; ops teams who want to host VS Code remotely. Not designed for headless agent execution.
- **Stance on agents**: Coder explicitly does not endorse agent-in-workspace as a primary pattern. Their interest is the workspace as VS Code host.
- **Verdict**: not relevant to rtm's pattern (host tmux attaching to docker). Code-server is overkill; enterprise-base is amd64-only and unmaintained.

Source: <https://github.com/coder/images>, <https://coder.com/docs/install/docker>.

### 5. Daytona, DevPod, JetBrains Space

- **Daytona**: provides `daytonaio/workspace-project` for runtime, but their public messaging in 2026 is "Secure Infrastructure for Running AI-Generated Code" with a Declarative Image Builder that builds Snapshots from Dockerfiles per workspace. They do not push a recommended base image for users to layer on. Their model is "give us a Dockerfile, we'll handle the rest."
- **DevPod**: defers entirely to devcontainer.json. The `Devpodio/devpod-docker` repo is a CLI image, not a workspace base. DevPod recommends users either use `mcr.microsoft.com/devcontainers/*` images or BYO.
- **JetBrains Space**: discontinued in 2024; not a live candidate.
- **Verdict**: none publishes an image rtm should depend on. Daytona's model is closest to rtm's (per-task image), but their abstraction layer (Snapshots) is proprietary.

### 6. Anthropic Claude Code

- **Image**: `ghcr.io/anthropics/claude-code:latest` and version-pinned tags (`:1.0.20` etc.).
- **Multi-arch**: published per Anthropic's documentation; the ghcr public-pull policy is restrictive (anonymous `docker manifest inspect` returns 403 — pulls require login or a PAT). Third-party reports place size around 487 MB.
- **Default user**: `node` (non-root, UID 1000). Confirmed from Anthropic's reference Dockerfile.
- **Base image**: `node:20` (per upstream Dockerfile in `anthropics/claude-code/.devcontainer/Dockerfile`).
- **Includes**: git, zsh + powerlevel10k, gh CLI, jq, git-delta, fzf, iptables/ipset (for firewall), `@anthropic-ai/claude-code` installed globally via npm. Workspace at `/workspace`, claude config at `/home/node/.claude`.
- **Firewall**: ships `init-firewall.sh` that needs `NET_ADMIN` + `NET_RAW` capabilities. Optional.
- **Anthropic's published recommendation**: Use `mcr.microsoft.com/devcontainers/base:ubuntu` + the `ghcr.io/anthropics/devcontainer-features/claude-code:1.0` feature. That feature auto-installs Node 18 LTS if missing and pulls `@anthropic-ai/claude-code` globally.
- **Caveat**: Anthropic explicitly says the reference devcontainer is "a working example, not a maintained base image." They expect users to layer or use the feature.

Source: <https://code.claude.com/docs/en/devcontainer>, <https://github.com/anthropics/claude-code/tree/main/.devcontainer>, <https://github.com/anthropics/devcontainer-features/tree/main/src/claude-code>.

### 7. OpenAI Codex (codex-universal)

- **Image**: `ghcr.io/openai/codex-universal:latest`.
- **Multi-arch**: amd64 + arm64. **But OpenAI explicitly says "only the amd64 version is actively tested,"** and the arm64 variant omits OpenJDK 10 and Swift due to compat. So multi-arch with caveats.
- **Compressed size**: 10.4 GB (amd64), 9.9 GB (arm64). **Huge.** This is the cloud-Codex environment image — pyenv with Python 3.10-3.14, nvm with Node 18-24, rustup with 13 Rust versions, Go 1.22-1.25, multiple Javas, Ruby, PHP, Swift, Bun, Bazel, Elixir/Erlang.
- **Default user**: `root`. No alternative user configured. Notable downside.
- **Audience**: "reference implementation of the base Docker image available in OpenAI Codex" — for users who want to reproduce the cloud-Codex environment locally.
- **Verdict**: not a starting point for rtm-managed Codex CLI usage. Too big, runs as root, kitchen-sink. The right model for Codex inside rtm is a thin layer on top of `node:slim` or `mcr.microsoft.com/devcontainers/base:ubuntu` with `npm i -g @openai/codex`.

Source: <https://github.com/openai/codex-universal>, manifest inspect.

### 8. OpenAI Codex CLI (the binary itself)

- **No official image** for the CLI alone. The codex repo's docker support is unmerged (PR #1065) or community-contributed (`ungb/codex`, `ungb/codex-docker`). The official posture is "install via npm or brew on your host."
- **Implication for rtm**: rtm operators wanting Codex must build their own thin image, exactly the same pattern as Aider. Documented Dockerfile is the unblocker.

### 9. Aider (paulgauthier/aider)

- **Image**: `paulgauthier/aider` and `paulgauthier/aider-full`.
- **Multi-arch**: amd64 + arm64. Confirmed via `docker manifest inspect`.
- **Compressed size**: 1.29 GB (amd64), 1.32 GB (arm64). Sizable; the `-full` variant pulls Playwright + Chromium.
- **Default user**: `appuser` (UID 1000) per the upstream Dockerfile.
- **Base image**: `python:3.12-slim-bookworm`.
- **Includes**: aider Python package, build-essential, git, libportaudio2, pandoc. `-full` adds playwright chromium.
- **License**: Apache 2.0.
- **Aider's own Docker recommendation**: their docs say "run `docker pull paulgauthier/aider`" — they assume their image is the answer.

Source: <https://aider.chat/docs/install/docker.html>, <https://github.com/Aider-AI/aider> Dockerfile.

### 10. Continue.dev, Cursor, Cline

- **Continue.dev**: no recommended base image. They run as a VS Code/JetBrains extension on the host, expecting Ollama or cloud APIs. Their FAQ acknowledges Docker only as "if Continue talks to Ollama in Docker, use bridge IP 172.17.0.1."
- **Cursor**: same — extension model, no container story.
- **Cline**: same. Community posts suggest running Cline-the-extension inside a devcontainer for isolation (the same `mcr.microsoft.com/devcontainers/base:*` answer), but Cline does not publish or recommend a base image of its own.
- **Verdict**: the "extension agents" (Continue, Cursor, Cline) are not in rtm's primary scope — they run inside an editor, not as a process rtm spawns. If a user wants a Cline-like setup, the answer is again "layer on devcontainers/base + add Node + install whatever Cline needs," which is the standard pattern.

Source: <https://docs.continue.dev/faqs>, <https://github.com/cline/cline/issues/2095>.

### 11. Minimal baselines

- **node:slim (bookworm-slim base)**: amd64+arm64 multi-arch, 80 MB compressed. Glibc. Right answer when the agent is "node-CLI plus a workspace." Caveat: pure-image; no git, no curl, no zsh. Layering required.
- **node:alpine**: amd64+arm64 multi-arch, ~55 MB. Musl. **Footgun with Node native modules** (better-sqlite3, node-pty, sharp, etc. need recompilation or prebuilt-musl wheels that often do not exist). Avoid for general-purpose agent containers.
- **python:3.12-slim**: amd64+arm64 multi-arch, 41 MB compressed. Glibc. Right answer when the agent is a Python tool (Aider, Continue's headless mode if/when it ships).
- **python:3.12-alpine**: musl; same caveat — wheels for native deps (pandas, ujson, lxml) need musl variants. PythonSpeed has the canonical "Alpine makes Python builds 50x slower" article.
- **debian:stable-slim** (or `:bookworm-slim`): amd64+arm64 multi-arch, 28 MB compressed. The blank-slate option. For Rust-built CLIs (Codex CLI is Rust per OpenAI's repo), this is the right base — install the binary, add tini, done.

Source: <https://hub.docker.com/_/python>, <https://pythonspeed.com/articles/alpine-docker-python/>, manifest inspect.

### 12. Distroless (gcr.io/distroless/*)

- **Multi-arch**: amd64+arm64+arm/v7.
- **Compressed size**: nodejs20 ~50 MB, python3 ~20 MB.
- **Default user**: `nonroot` available via `:nonroot` tags.
- **Includes**: ONLY the language runtime + glibc + tzdata + CA certs. **No shell, no package manager, no anything else.**
- **Verdict for rtm**: **DOA for interactive agents.** rtm's pattern is host tmux attaching to a container with a PTY. Without a shell or `tini` in the image, you cannot run `bash -c "claude"` or recover sensibly from a crash. Distroless is for headless production services, not interactive coding agents.

Source: <https://github.com/GoogleContainerTools/distroless>.

### 13. Multi-arch reality check

Summary table for the candidate set, native arm64 availability (NOT QEMU emulation):

| Image | amd64 | arm64 native | If pulled on M-series |
|---|---|---|---|
| mcr.microsoft.com/devcontainers/base:* | yes | yes (ubuntu, alpine, debian) | native |
| mcr.microsoft.com/devcontainers/universal:linux | yes | **NO** | QEMU emulation, very slow |
| gitpod/workspace-base, gitpod/workspace-full | yes | **NO** | QEMU emulation |
| codercom/enterprise-base | yes | **NO** | QEMU emulation |
| ghcr.io/openai/codex-universal | yes | yes (with caveats) | native, but huge |
| ghcr.io/anthropics/claude-code | yes | yes (per docs) | native |
| paulgauthier/aider | yes | yes | native |
| node:slim, python:slim, debian:stable-slim | yes | yes | native |
| gcr.io/distroless/* | yes | yes | native |

The "amd64 only" entries are the canary: anything Apple Silicon developers will hit must be in the top group. **The single biggest argument against C (endorsing one existing family) is that the heavy "workspace" images — Codespaces universal, Gitpod, Coder — are all amd64-only. That excludes them as rtm defaults on M-series Macs.**

### 14. Alpine vs Debian for agents

- **Node native modules**: Alpine/musl is the source of half the support tickets in the better-sqlite3 / node-pty / sharp / @grpc/grpc-js trackers. rtm's agents (Claude Code is Node-based, Cursor extension if/when, anything using `node-pty` for PTYs) will hit this. Default to Debian-glibc.
- **Python wheels**: PyPI wheels are manylinux (glibc) by default. Alpine needs `musllinux` wheels that exist for top-N packages but not the long tail. Aider's choice of `python:3.12-slim-bookworm` is correct.
- **Rust prebuilts**: rustup defaults to glibc targets. Musl works but is a second-class citizen for most crates. Codex CLI (Rust) on Alpine is doable but invites trouble.
- **Verdict**: **default to glibc (Debian/Ubuntu slim) for any image rtm recommends or examples.** Reserve Alpine for ops who explicitly want it and accept the trade.

### 15. Read-only root + writable workspace

Of the candidates, which support `docker run --read-only --tmpfs /tmp -v workspace:/workspace`?

- **devcontainers/base:ubuntu**: yes, as long as you tmpfs `/tmp` and either tmpfs or mount `/home/vscode`. Confirmed pattern.
- **claude-code**: yes; `/workspace` writable, `/home/node/.claude` mounted as a volume for credential persistence.
- **codex-universal**: probably yes but `root` user complicates the "no privilege escalation" story.
- **aider**: yes; standard non-root pattern.
- **slim baselines + custom Dockerfile**: trivially yes; the operator controls the layout.
- **gitpod/workspace-full**: messy. Many setup scripts write to `/home/gitpod` at run time. Not designed for read-only root.

`--read-only` plus a writable workspace volume is the right rtm pattern. It is achievable with all of the candidate-A entries above; it is incompatible with `--privileged` patterns common in the "kitchen sink" workspace images.

### 16. Time-to-first-spawn

For a developer running `rtm spawn` for the first time, the bottleneck is image pull. Compressed sizes set the floor (cold cache on a 100 Mbps connection):

- debian:stable-slim → 28 MB → ~3 s
- python:3.12-slim → 41 MB → ~4 s
- node:slim → 80 MB → ~7 s
- devcontainers/base:alpine → 256 MB → ~22 s
- devcontainers/base:ubuntu → 308 MB → ~26 s
- claude-code (per ghcr) → ~487 MB → ~40 s
- gitpod/workspace-base → 708 MB → ~60 s
- aider → 1.3 GB → ~110 s
- devcontainers/universal:linux → 3.7 GB → ~5 min
- gitpod/workspace-full → 3.15 GB → ~4 min
- codex-universal → 10.4 GB → **~15 min**

That distribution alone makes the case: **the first-time-spawn cost of an image rtm "recommends" matters enormously.** A `helioy/rtm-agent-base` even at 100 MB still adds a layer to whatever the operator was already going to pull.

---

## Option scoring lattice

Scored 1-5; higher is better. Categories from the brief.

| Criterion | A: image-agnostic + examples | B: ship `helioy/rtm-agent-base:*` family | C: endorse devcontainers/base |
|---|---|---|---|
| Maintenance burden for rtm | **5** (zero images to maintain) | 1 (4+ images, multi-arch CI, security updates) | 4 (no image, but doc maintenance) |
| Time-to-first-spawn | 3 (depends on user choice; sane defaults pull ~300 MB) | 3 (smaller bespoke image, but extra layer to publish/pull) | 3 (308 MB pull) |
| Customization flexibility | **5** (operator picks anything) | 2 (override path exists, but ecosystem optimizes for the rtm-published image) | 4 (operators layer freely) |
| Security hardening defaults | 4 (rtm forces `--init`, `--read-only`, drops caps; image is operator's call) | 4 (rtm controls; arguably more consistent) | 4 (devcontainers/base is reasonable but `vscode` user has passwordless sudo by default) |
| Cross-platform parity (multi-arch) | **5** (operator's image; rtm validates `docker manifest` at spawn) | 3 (rtm CI must publish multi-arch every release) | **5** (devcontainers/base is arm64-native) |
| Ecosystem alignment | **5** (matches how Anthropic, OpenAI, Aider, devcontainers, DevPod, Daytona already think) | 2 (introduces a fifth competing image family) | 4 (good for the devcontainer world; orthogonal to Anthropic's own ghcr image) |
| **Total** | **27** | **15** | **24** |

A wins decisively. C is acceptable as a documented default; B is a maintenance bear trap with negligible upside in 2026.

---

## Concrete recommendation

**Adopt Option A.**

1. **Document the contract** rtm enforces:
   - Image must work with `docker run --init` (rtm always injects tini at PID 1; image's own ENTRYPOINT runs as PID 2+).
   - Image must NOT require `--privileged`. Optional `--cap-add NET_ADMIN NET_RAW` for the Claude Code firewall pattern, gated behind an explicit `rtm spawn --net-admin` flag.
   - Image must have a non-root user. rtm will refuse to spawn into UID 0 unless `--allow-root` is set.
   - Workspace mount path: standardize on `/workspace`. Document it.
   - Agent binary must be on PATH. rtm passes the command as `["<agent>", "<args>"...]`; the image's job is to make `claude`, `codex`, `aider` etc. resolve.
   - Image must publish an `arm64` manifest if it claims to support Apple Silicon developers. rtm should warn at spawn time when it detects `--platform=linux/amd64` on an arm64 host.

2. **Publish four reference Dockerfiles** in the rtm repo under `examples/dockerfiles/` (not built or published as images):
   - `claude-code.Dockerfile`: `FROM mcr.microsoft.com/devcontainers/base:ubuntu` + Anthropic's devcontainer-features approach OR `FROM ghcr.io/anthropics/claude-code:latest` for users who want Anthropic's full stack.
   - `codex.Dockerfile`: `FROM mcr.microsoft.com/devcontainers/base:ubuntu` + `RUN npm install -g @openai/codex`. Document the codex-universal alternative for kitchen-sink needs.
   - `aider.Dockerfile`: just document `paulgauthier/aider` as `--image`. No Dockerfile needed.
   - `base.Dockerfile`: `FROM mcr.microsoft.com/devcontainers/base:ubuntu` + tini + workspace setup. The "I want to BYO" starter.

3. **Recommend** `mcr.microsoft.com/devcontainers/base:ubuntu` as the canonical layering base in rtm docs. Reasons: multi-arch native, sane non-root defaults, MIT, actively maintained by Microsoft, already the implicit answer for devcontainer.json users and what Anthropic itself recommends. This is the "soft C" that lives inside A.

4. **Do not publish `helioy/rtm-agent-base:*` images in v1.** Revisit if (a) two or more sibling Helioy products end up duplicating the same Dockerfile, or (b) operators report meaningful drift between vendor images and rtm's expectations. Until then, the maintenance cost is real and the user value is small.

---

## Open questions for the warroom

1. **Workspace mount path**: rtm needs to pick `/workspace` or `/repo` (or make it configurable but with a default). What does session-matters' contract look like? If `sm` describes the mount as a logical name and rtm translates, the path is internal-only and `/workspace` is fine. If the path leaks into agent prompts or CWD assumptions, it needs to match what each agent expects (Aider opens `cwd`; Claude Code expects `/workspace` per its reference container).

2. **Should the rtm-recommended starter image preinstall git?** The vendor images all do. devcontainers/base does. A bare `node:slim` does not. If we recommend layering on `node:slim`/`python:slim` as a "small" path, the example Dockerfile must `RUN apt-get install -y git` or downstream agents break (Claude Code spawns `git` constantly).

3. **Default shell**: tmux attaches to whatever the container's PID 1 entrypoint runs. If we want `rtm exec` to drop the user into a shell inside a running container (`docker exec -it container bash`), the image needs `bash` on PATH. `node:slim` ships with `sh` (dash) but not bash. devcontainers/base ships zsh + bash. Recommend "image must provide `/bin/bash`" as part of the contract.

4. **Credential mounting**: Claude Code expects `~/.claude/` to persist across spawns. Aider reads `~/.aider.conf.yml` and `~/.env`. Codex CLI reads `~/.codex/`. rtm needs a policy for credential volumes: a per-runtime named volume (`rtm-creds-claude-code`, `rtm-creds-codex`), or pass-through `-v ~/.claude:/home/node/.claude:ro` from the host? The first is more isolated; the second matches how developers actually use these agents today.

5. **Firewall capability gating**: Anthropic's reference container ships `init-firewall.sh` that needs `NET_ADMIN` + `NET_RAW`. Should rtm offer a first-class `--firewall` flag that adds those caps and invokes the script, or punt and require operators to add `--cap-add` manually via `rtm spawn --docker-flag '--cap-add=NET_ADMIN'`? The first is more opinionated; the second keeps rtm dumber.

6. **arm64 spawn-time validation**: when rtm spawns on an arm64 host and the user's image manifest has no arm64 entry, should rtm refuse, warn loudly, or silently let Docker QEMU-emulate? Suggest: warn loudly by default, refuse under `rtm spawn --strict-arch`. This is where the "amd64-only" candidates (Codespaces universal, gitpod, coder) start mattering.

7. **Is there a need for an rtm "shim" baked into images?** Probably not. The shim lives on the host per the prior research. But if rtm ever wants to inject a sidecar process inside the container (resource accounting, syscall audit), an "rtm-instrumented" image becomes necessary. Mention as a future trigger, not v1.

---

## Sources

### Primary (Dockerfiles + manifests)

- Microsoft devcontainers images repo: <https://github.com/devcontainers/images>
- devcontainers/base:ubuntu Dockerfile: <https://github.com/devcontainers/images/blob/main/src/base-ubuntu/.devcontainer/Dockerfile>
- devcontainers/universal:linux Dockerfile: <https://github.com/devcontainers/images/blob/main/src/universal/.devcontainer/Dockerfile>
- Gitpod workspace-images: <https://github.com/gitpod-io/workspace-images>
- Coder images: <https://github.com/coder/images>
- Anthropic claude-code repo (.devcontainer): <https://github.com/anthropics/claude-code/tree/main/.devcontainer>
- Anthropic devcontainer-features (claude-code): <https://github.com/anthropics/devcontainer-features/tree/main/src/claude-code>
- OpenAI codex-universal: <https://github.com/openai/codex-universal>
- OpenAI codex CLI: <https://github.com/openai/codex>
- Aider repo + Dockerfile: <https://github.com/Aider-AI/aider>
- Manifest inspection: local `docker manifest inspect` against each image (May 21, 2026).

### Docs

- Claude Code Devcontainer docs: <https://code.claude.com/docs/en/devcontainer>
- Aider Docker docs: <https://aider.chat/docs/install/docker.html>
- mcr base image about page: <https://mcr.microsoft.com/en-us/product/devcontainers/base/about>
- Coder install with Docker: <https://coder.com/docs/install/docker>
- Continue.dev FAQs: <https://docs.continue.dev/faqs>
- DevPod prebuild workspace: <https://devpod.sh/docs/developing-in-workspaces/prebuild-a-workspace>
- Daytona Dockerfile support: <https://www.daytona.io/dotfiles/dockerfile-support>
- Python Docker base-image analysis: <https://pythonspeed.com/articles/base-image-python-docker-images/>
- Alpine Python slowness: <https://pythonspeed.com/articles/alpine-docker-python/>

### Community

- "Running Claude Code in Docker" (Software Thug): <https://www.softwarethug.com/posts/running-claude-code-in-docker-setup-that-works/>
- Morph Claude Code Docker guide: <https://www.morphllm.com/claude-code-docker-container>
- Codex Docker discussions: <https://github.com/openai/codex/discussions/915>

## Source quality assessment

- **High confidence**: multi-arch facts (verified directly via `docker manifest inspect` on May 21, 2026), Anthropic's stated recommendation (their own docs), Aider Dockerfile contents (read directly), codex-universal contents (Dockerfile read directly).
- **Medium confidence**: exact compressed sizes (manifest layer sums are accurate but on-disk sizes vary with overlay storage; numbers in the table are floor estimates). The claude-code:latest ~487 MB number comes from a third-party blog and could not be verified due to ghcr anonymous-pull restrictions.
- **Low confidence / gaps**: Microsoft, Coder, and Gitpod do not publish "official agent-in-container" recommendations. Their stance is inferred from what they publish and how active their repos are. Daytona's pivot to "Secure Infrastructure for AI-Generated Code" is real (their homepage messaging) but I did not find a corresponding base-image recommendation; their model is per-task Snapshot building.

## Actionable takeaways

1. **Adopt Option A.** Ship the contract, ship four example Dockerfiles, recommend `mcr.microsoft.com/devcontainers/base:ubuntu` as the canonical starter.
2. **Validate arm64 at spawn time.** This is the highest-value single check rtm can do for the cross-platform story — most of the "kitchen sink" images on the market fail this check.
3. **Enforce non-root by default.** All vendor images (Anthropic, Aider) get this right; codex-universal does not. rtm's `--allow-root` flag is the escape hatch.
4. **Standardize `/workspace` as the mount point.** Aligns with claude-code's reference container and what most devcontainer.json users assume. Document it as part of the contract.
5. **Revisit B in 6-12 months** if (a) the agent-vendor images diverge from rtm's contract in ways that hurt users, or (b) multiple sibling repos copy the same Dockerfile. Until then, every line of YAML rtm doesn't ship is a line rtm doesn't have to maintain.

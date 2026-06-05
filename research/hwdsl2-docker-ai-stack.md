---
title: What hwdsl2/docker-ai-stack does well (strengths capture)
type: research
tags: [docker-compose, self-hosted, ai-stack, ollama, litellm, anythingllm, hardening, hwdsl2]
summary: One-command self-hosted AI stack (Ollama/LiteLLM/AnythingLLM + STT/TTS/RAG/MCP) with secure-by-default auto-config, idempotent bootstrap, auto-wired keys, healthcheck gating, and a Caddy HTTPS overlay.
status: active
source: github-researcher
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# What hwdsl2/docker-ai-stack does well

Pure strengths capture. No comparison, no grading, no verdict. Every structural claim is cited to the cloned repo at the commit reviewed (`fa8ff64`, pushed 2026-06-14).

## Stats

84 stars, MIT licensed, created 2026-05-05 (~6 weeks old at review), last push 2026-06-14 — actively maintained with near-daily commits. Single author (Lin Song / hwdsl2, 50/50 commits), who also maintains [setup-ipsec-vpn](https://github.com/hwdsl2/setup-ipsec-vpn) (28k+ stars), so the project inherits a track record in hardened, idempotent setup scripts. Primary language Shell. Disk ~2 MB. No CI workflows and no git tags/releases; versioning is handled through a dated `CHANGELOG.md` and pinned image tags rather than repo releases. Multi-arch (`linux/amd64`, `linux/arm64`) with separate CUDA image variants. Repo is config + docs + two shell scripts: there is almost no application code, the value is in the orchestration and the operational polish around it.

## What it is

A Docker Compose configuration that stands up a complete self-hosted AI stack on one Linux server with `docker compose up -d`. It bundles Ollama (local LLM), LiteLLM (OpenAI-compatible gateway with Admin UI), AnythingLLM (chat UI), Whisper + WhisperLive (STT), Kokoro (TTS), an Embeddings service, Docling (document parsing), an MCP Gateway, and a pgvector-enabled Postgres, all pre-wired so the services discover and authenticate to each other automatically. Everything runs locally by default; LiteLLM optionally routes out to 100+ external providers.

## What it does well

### Service orchestration and inter-service wiring

The standout is that the services auto-wire with zero manual key plumbing. Ollama and the MCP Gateway each generate an API key on first start and write it to a *shared* Docker volume (`ollama-shared`, `mcp-shared`); LiteLLM mounts those read-only and reads the keys on startup (`docker-compose.yml:47-49`). LiteLLM in turn publishes its own key to `litellm-shared`, which AnythingLLM's bootstrap reads (`chat-ui-bootstrap.sh:14-33`). The result is that `docker compose up -d` produces a fully authenticated, connected mesh with no copy/paste step — a genuinely hard UX problem solved cleanly with nothing but volumes and small scripts. The README documents the mechanism explicitly (`README.md:375-387`).

Startup ordering is correct and enforced, not hoped for. LiteLLM declares `depends_on` with `condition: service_healthy` for ollama, mcp, and db (`docker-compose.yml:57-63`), so it only starts once its dependencies pass their healthchecks. AnythingLLM depends on litellm (`docker-compose.yml:142-144`). The shared key volumes are correctly distinguished from data volumes and called out as ephemeral / not-worth-backing-up (`README.md:575`), showing the author understands the lifecycle of each volume.

### One-command setup and curated lightweight stacks

The quick start is genuinely one command (`README.md:54-61`). Beyond the full stack, the `stacks/` directory ships eight pre-composed subsets (chat-ui, voice-pipeline, voice-chat, rag-pipeline, rag-pipeline-full, code-assistant, ai-tools, chat-only) each with its own compose files and README, scoped to a memory budget from ~4.5 GB to ~6.5 GB and a named use case (`README.md:149-168`). These are real tailored configs, not the full file with services commented out: `stacks/chat-only/docker-compose.yml` drops the `mcp` service entirely, removes `LITELLM_MCP_URL` from LiteLLM's env, and removes mcp from `depends_on` — so each preset is internally consistent for exactly the services it includes. This lets a low-RAM user run a coherent subset without editing YAML.

### Configuration ergonomics and sensible defaults

Defaults are chosen so the stack is useful immediately and safe to expose later. AnythingLLM is pre-pointed at the local LLM through LiteLLM (`GENERIC_OPEN_AI_BASE_PATH=http://litellm:4000/v1`, model `ollama/llama3.2:3b`, `docker-compose.yml:111-113`) and ships with telemetry disabled (`DISABLE_TELEMETRY=true`, `docker-compose.yml:134`). Heavy/optional services (Kokoro, Docling, WhisperLive) are commented out by default to keep the memory footprint small, with the matching named volumes also commented so enabling is a two-step, clearly-paired edit (`docker-compose.yml:151-208`). Every service has a commented optional `*.env` mount line in place (`docker-compose.yml:11`, `:50`, `:73`, etc.), so customization is uncomment-and-edit rather than restructure. The opt-in path to switch AnythingLLM's embedder to the stack's Embeddings + pgvector is documented inline in the compose comments *and* carries the correct data-migration warning that old vectors must be re-embedded (`docker-compose.yml:115-133`, `README.md:507`).

### GPU vs CPU handling

GPU support is a clean parallel compose file rather than a flag or template hack. `docker-compose.cuda.yml` is the CPU file plus `deploy.resources.reservations.devices` GPU blocks on the GPU-capable services (ollama, whisper) and `:cuda`-tagged images (`docker-compose.cuda.yml:18-24`, `:91-97`, `:3`, `:83`). The README gives the `COMPOSE_FILE` env trick so users do not have to append `-f docker-compose.cuda.yml` to every later command (`README.md:137-143`), and there is explicit Podman guidance because Podman ignores the Compose `deploy:` block — it tells the user to swap in a CDI `devices:` entry instead (`README.md:351-364`). That is a real-world edge case most projects miss.

### Security and hardening (the signature strength)

Secure-by-default is implemented carefully, not asserted. The AnythingLLM bootstrap (`chat-ui-bootstrap.sh`) is the centerpiece:

- It generates a 20-char admin password using Node crypto with **rejection sampling** to avoid modulo bias (`chat-ui-bootstrap.sh:43-58`), and an ambiguous-character-free alphabet (no `0/O/1/I/l`).
- It validates the generated password and JWT secret against strict regexes (`chat-ui-bootstrap.sh:35-41`) and has layered fallbacks (Node crypto → `/proc/sys/kernel/random/uuid` → `/dev/urandom`).
- It **fails closed**: if it cannot generate a valid password and JWT secret, it refuses to start AnythingLLM unauthenticated and exits (`chat-ui-bootstrap.sh:124-130`). Refusing to run rather than running insecurely is the correct safety posture.
- Fresh-install detection is principled: it keys off the absence of `anythingllm.db` (which Prisma always creates on boot), so the password seeding only ever fires on a truly new volume and never clobbers an existing install (`chat-ui-bootstrap.sh:118-120`, documented in `CHANGELOG.md:79-82`).
- Generated secrets are written `chmod 600` (`chat-ui-bootstrap.sh:115`, `:137`) and the password is printed once to logs and persisted to a known file for later retrieval (`chat-ui-bootstrap.sh:136-151`).

Port exposure is conservative: Ollama (`11434`) and MCP (`3000`) are not published to the host at all by default (commented, `docker-compose.yml:6-7`, `:89-90`); access is funneled through LiteLLM. Embeddings, Whisper, Kokoro, Docling, WhisperLive bind to `127.0.0.1` only (`docker-compose.yml:70`, `:80`, etc.), so they are reachable on the host but not on the network. Secrets never enter git: `.gitignore` excludes `.env` and `.env.*`. The README is honest about the auth model, flagging which services are optional-auth by default and instructing users to set keys before any public exposure (`README.md:19`, `:552`).

### Networking and TLS

HTTPS is an optional overlay rather than a baked-in assumption, which keeps the local quickstart trivial while making production a one-liner. `docker-compose.proxy.yml` adds a Caddy container on `80/443` (incl. `443/udp` for HTTP/3) and uses `ports: !override` to *rebind* AnythingLLM and LiteLLM to `127.0.0.1` so that in proxy mode Caddy is the only public listener (`docker-compose.proxy.yml:24-30`). The Caddyfile is minimal and correct: automatic ACME TLS keyed off `$DOMAIN`/`$ACME_EMAIL`, zstd/gzip encoding, a configurable request-body size cap, and a commented optional second hostname for exposing the LiteLLM Admin UI with a clear "keep the master key secret" warning (`caddy/Caddyfile:1-21`). The compose file uses `${DOMAIN:?...}` / `${ACME_EMAIL:?...}` so a missing required var fails fast with a helpful message (`docker-compose.proxy.yml:7-9`). The README states the minimum Compose version the `!override` needs (`2.24.4+`) and gives a host-based-proxy fallback for older setups (`README.md:517`, `:550`).

### Health checking and diagnostics

`stack-check.sh` (393 lines) is a real diagnostic tool, not a token gesture. It is engine-agnostic (auto-detects Docker vs Podman, overridable via `CONTAINER_ENGINE`, `stack-check.sh:25-42`), discovers services both by container name and by *image name* with awk that strips registry prefixes, tags, and digests so it works under Podman's `docker.io/` qualification and with custom container names (`stack-check.sh:66-99`). It self-adapts to whichever subset of services is running (every block is skipped cleanly if absent), so the same script serves the full stack and all eight lightweight stacks. Checks go beyond "is it up": it confirms Ollama has a model pulled, verifies API-key files exist, and runs a live end-to-end LLM routing test through LiteLLM and an MCP `initialize` handshake (`stack-check.sh:196-212`, `:292-303`). It degrades colors when not a TTY (`stack-check.sh:45-53`), separates pass/fail/warn, and returns a meaningful exit code. Container healthchecks themselves are tuned: `interval` raised from 5s to 15s to cut steady-state probe overhead while keeping generous `start_period` for slow starters (Ollama 60s, LiteLLM 300s) so dependents are not blocked prematurely (`docker-compose.yml:12-17`, `:51-56`; rationale in `CHANGELOG.md:61-64`).

### Documentation

Documentation is thorough and operationally minded. The README (603 lines) covers quick start, GPU, lightweight stacks, a Mermaid architecture diagram, a no-Compose `docker run` path, full Podman support, backup/restore, and update flow. It is fully localized into four languages (English, Simplified Chinese, Traditional Chinese, Russian) across README, troubleshooting, and backup-restore docs. The troubleshooting guide is structured for triage and, notably, tells users precisely *where* to file an issue — this repo for wiring/compose problems vs the individual service repos for image behavior vs upstream for app bugs (`docs/troubleshooting.md:242-259`), and what to include with secrets redacted. The `CHANGELOG.md` is dated, categorized (Added/Changed/Fixed), and explains the *why* behind operational changes (e.g. why AnythingLLM was pinned, why the healthcheck interval changed).

## Notable engineering details

- **Selective image pinning.** Third-party images the author does not control are pinned: `pgvector/pgvector:pg18-trixie`, `mintplexlabs/anythingllm:1.13`, `caddy:2`. The author's own `hwdsl2/*` images float (untagged) because he controls their release cadence. AnythingLLM was deliberately moved off `latest` to a stable tag with a documented rationale (upstream `latest` tracks master) (`CHANGELOG.md:55-60`).
- **`.env` persistence fix.** AnythingLLM's `server/.env` is symlinked into the data volume (`chat-ui-bootstrap.sh:154`) so UI-set passwords and provider keys survive `docker compose down && up` and image upgrades — a subtle data-loss bug that was found and fixed, with a migration note (`CHANGELOG.md:93-114`).
- **pgvector reuse.** The bundled Postgres carries pgvector, so RAG vector storage reuses the same DB LiteLLM already needs rather than adding a separate vector database (`README.md:423-439`).
- **`.gitattributes`** enforces LF line endings on `*.sh`/`*.yml`/`*.yaml` so scripts do not break when cloned on Windows.
- **Fail-fast required env** via `${VAR:?message}` in the proxy overlay, and idempotent, defensive shell throughout (`set -euo pipefail`, `2>/dev/null || true` on best-effort steps, bounded retry loops with `seq`).
- **Port-conflict awareness:** WhisperLive's REST API is mapped to host `8001` specifically to avoid colliding with Embeddings on `8000`, with an inline comment explaining why (`docker-compose.yml:177`).

## Caveats / rough edges

Genuinely minor, listed for completeness only:

- The `chat-ui-bootstrap.sh` and `caddy/Caddyfile` files are **copied** into each relevant `stacks/` subdirectory rather than symlinked (verified byte-identical), so a future change to the bootstrap script must be applied in three places. The same holds for the heavily-duplicated per-service compose blocks across nine compose files and eight stacks; there is no templating layer, so edits are repetitive (acceptable given Compose has no native include/inheritance and the duplication keeps each stack self-contained and `cd`-and-run).
- No CI: nothing automatically lints the compose files or runs `stack-check.sh`, so consistency across the many duplicated files rests on author discipline (which so far appears high).
- The author's own images float on `latest`, so a `docker compose pull` could in principle pull a breaking image change; mitigated by the author controlling those images and the documented backup-before-upgrade flow.

## Sources consulted

- `README.md` (full), `README-zh.md`/`README-ru.md`/`README-zh-Hant.md` (existence/localization)
- `docker-compose.yml`, `docker-compose.cuda.yml`, `docker-compose.proxy.yml`
- `caddy/Caddyfile`
- `chat-ui-bootstrap.sh`, `stack-check.sh`
- `CHANGELOG.md`, `docs/troubleshooting.md`
- `stacks/chat-only/docker-compose.yml` (consistency spot-check), `.gitignore`, `.gitattributes`
- `git log`, `git shortlog`, `gh repo view` for stats

## Open questions

- Behavior of the `hwdsl2/*` service images themselves (the `*_manage` CLIs, key generation) lives in separate repos (docker-ollama, docker-litellm, etc.) and was not inspected here; the key-sharing claim is verified at the volume/wiring level in this repo but not inside those images.
- Real-world first-boot timing and memory figures are as documented; not independently measured.

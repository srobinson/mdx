---
title: Vellum Assistant — architecture review for Helioy (channels / memory / security / hosting)
type: research
tags: [github-review, vellum-assistant, vellum-ai, typescript, bun, personal-ai, memory-graph, qdrant, drizzle, credential-isolation, sandbox, multi-channel, plugins, context-matters, agent-matters, session-matters, runtime-matters, transport-matters, knowledge-matters, littleorgans]
summary: Production-grade open-source personal-AI monorepo from Vellum; A-grade reference for an 8-type memory graph, a hard-process credential boundary (CES), a channel-discriminator event envelope, and a plugin-hook agent loop. Borrow patterns, build nothing from it.
status: active
source: github-researcher
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Vellum Assistant — review for Helioy

Repo: https://github.com/vellum-ai/vellum-assistant
Reviewed 2026-06-15 at commit `4ddebe7` (shallow clone, depth 50). Cloned to /tmp, analyzed, removed.

## 1. Stats

Public open-source mirror of Vellum AI's internal personal-AI product. 673 stars, 98 forks, MIT license, created 2026-02-07, last push 2026-06-15 (active today). Primary language TypeScript (5,921 `.ts` + 665 `.tsx`), with a 1,104-file Swift client (macOS/iOS) and ~311 MB on disk across 8,816 tracked files. Runtime is **Bun 1.3.11** (Node 22 floor). The visible git history is a single squashed initial commit (2026-06-12) plus ~50 subsequent commits, but PR numbers in the merge messages run in the **34,000s** (e.g. `#34630`, `#34808`), which tells you this is a long-lived internal monorepo open-sourced as a snapshot, not a from-scratch repo. Top committers: `siddseethepalli` (29), `devin-ai-integration[bot]` (11), plus Vellum staff (Aaron Levin, Maddie Abboud). CI is **extensive**: 38 GitHub Actions workflows (per-package `ci-main-*` / `pr-*`, evals, perf, release, Socket security autofix). Foundational docs are unusually rich: `ARCHITECTURE.md` (59 KB), `AGENTS.md` (32 KB), `CONSTITUTION.md`, `GLOSSARY.md`, per-package `ARCHITECTURE.md` + `AGENTS.md` + `CLAUDE.md`.

## 2. Grade

**A− (sits with notebooklm-py / mngr / fallow-rs, just under off-scale SurrealDB).** This is a genuinely production-grade, multi-surface agent platform with first-class architecture docs, deep CI, a real security boundary, and an 8-type memory graph that is fully implemented (not vapor). It loses the off-scale mark only because the open-source drop is a frozen squash of a closed internal repo (no real upstream history, managed-platform orchestration lives in a sibling private repo, and a couple of headline README claims are aspirational). For Helioy's purposes it is the single best multi-channel personal-agent reference reviewed to date.

## 3. What it does well

- **Architecture-doc discipline.** Every package carries `ARCHITECTURE.md` + `AGENTS.md` + `CLAUDE.md`, and the root `ARCHITECTURE.md` includes a full system-overview mermaid graph (ARCHITECTURE.md:263+) mapping macOS Swift app, Bun daemon, gateway, web (Next.js/Postgres), and storage. This is how you onboard an agent to a 8,800-file repo.
- **Hard security boundary that is real, not a README bullet.** Credentials live in a separate process (CES) reachable only by RPC; the model process never sees plaintext (ARCHITECTURE.md:38-46).
- **8-type cognitive memory, actually implemented** as a graph with decay, triggers, and hybrid retrieval (`assistant/src/memory/graph/types.ts:5-14`).
- **Per-package CI + evals + perf gates.** `ci-pr-evals.yaml`, `ci-perf-macos.yaml` mean memory/agent quality is regression-tested, not vibe-checked.
- **Plugin-hook agent loop.** The agent loop is decomposed into composable lifecycle hooks shipped as first-party plugins (`assistant/src/plugins/defaults/`), so behavior extends without forking the runtime.
- **Self-authored identity files.** `SOUL.md` (persistent, assistant-edited on correction) + `NOW.md` (volatile scratchpad), a clean split of durable relational memory from transient working state (`assistant/src/prompts/templates/SOUL.md`, `.../NOW.md`).

## 4. Channels

The channel abstraction is a **discriminated-union event envelope**, not an interface/registry. There is no `Channel` interface; channels are string literals plus per-channel adapter folders.

- **Channel taxonomy.** `gateway/src/channels/types.ts:1-11` defines `CHANNEL_IDS = telegram | phone | vellum | whatsapp | slack | email | a2a`. `INTERFACE_IDS` (same file, lines 24-35) extends that with `macos | ios | cli | web` — the distinction is "true channel" (gateway-ingested) vs "client surface".
- **Normalized inbound envelope.** Every raw provider webhook is parsed by a per-channel `normalize.ts` into `GatewayInboundEvent` (`gateway/src/channels/inbound-event.ts:72-77`), carrying `sourceChannel`, `message.conversationExternalId`, `actor.actorExternalId`, optional `source.threadId` (Slack `thread_ts`, email `In-Reply-To`), and attachments. This is the canonical seam: provider mess → one envelope.
- **Routing.** `gateway/src/routing/resolve-assistant.ts:8-46` maps `conversationId` + `actorId` → `assistantId` via a priority chain (conversation route → actor route → default policy). Routing is stateless.
- **Reply dispatch.** Runtime renders channel-specific output (`textToSlackBlocks` BlockKit at `assistant/src/runtime/channel-reply-delivery.ts:177`) and POSTs back to a `callbackUrl` registered at inbound time (`deliverRenderedReplyViaCallback`, same file:92-205; per-channel driver in `assistant/src/runtime/gateway-client.ts`).
- **Adapters on disk** (all under `gateway/src/`): `telegram/`, `slack/` (Socket Mode via `apps.connections.open`), `twilio/` (voice + relay WS), `email/`, `whatsapp/` (HMAC-SHA256-validated), `voice/`. Client surfaces: `clients/macos/`, `clients/` iOS (Swift), `apps/web/` (Next.js/React 19), `clients/chrome-extension/`.
- **Conversation key formula** (`assistant/src/memory/delivery-crud.ts:46-62`): `asst:{assistantId}:{sourceChannel}:{externalChatId}[:thread:{sourceThreadId}]`.

**Caveat — cross-channel continuity is aspirational.** The README claims "start a thought in one channel and pick it up in another" (README.md:106). The conversation key *requires* `sourceChannel`, so Slack and Telegram threads for the same human are separate conversations with separate histories. Memory is unified per-user via `scope_id` (below), but the *conversation* is not aliased across channels. Treat the README line as marketing, the per-channel key as truth.

## 5. Memory

The headline ("8 types of memory") is real and well-built. Storage topology spans three substrates.

**Substrates.**
- **SQLite (Drizzle ORM)** — the relational graph. `memory_graph_nodes` (migration `202-memory-graph-tables.ts:14-35`) is a *single* table holding all 8 types, discriminated by a `type` column. Columns: `type`, `content`, `scope_id` (isolation), `emotional_charge` (JSON: valence/intensity/decayCurve), `significance`, `stability` (default 14), `confidence`, `fidelity`, `reinforcement_count`, `created`, `event_date`, `last_accessed`. Sibling tables `memory_graph_edges` (caused-by, contradicts, supersedes, …) and `memory_graph_triggers` (temporal cron / semantic / event activations). The macOS-app-era schema also has `conversations`, `messages`, `tool_invocations`, `reminders`, `cron_jobs`, `tasks`, `work_items`, `contacts` (ARCHITECTURE.md:339-359).
- **Qdrant (vectors)** — collections `memory` (legacy) and `memory_v2_concept_pages`. Hybrid search fuses dense + 30K-vocab sparse via RRF (`assistant/src/memory/graph/graph-search.ts:88-96`), filtered by `target_type` and `scope_id`.
- **Disk (markdown)** — "memory v2" concept pages at `memory/concepts/<slug>.md` with YAML frontmatter (`edges`, `summary`, `links`); activation state spilled to SQLite.

**The 8 types** (`assistant/src/memory/graph/types.ts:5-14`): episodic, semantic, procedural, emotional, prospective, behavioral, narrative, shared. They are one table discriminated by `type`, not separate stores. What distinguishes them is *behavior*: Ebbinghaus decay on `significance` (`stability * (1 + 0.3*(reinforcement-1))`), fidelity ladder (vivid→clear→faded→gist→gone), and emotional-charge decay curves (linear/logarithmic/transformative/permanent).

**Retrieval pipeline** (`assistant/src/memory/graph/retriever.ts:46-152`): dense embed (auto-selected backend) + in-process sparse TF-IDF → Qdrant hybrid + RRF → multi-signal scoring (`scoring.ts`: semantic similarity, decayed significance, emotional intensity, temporal/recency/trigger/activation boosts) → optional LLM re-rank dedup → tiered injection (tier-1 > 0.8) as an `<memory_context>` XML block. A background `MemoryJobsWorker` polls every 1.5s to embed/extract/cleanup_stale (ARCHITECTURE.md:336).

**Scoping/isolation.** `memory_graph_nodes.scope_id` (TEXT, default `'default'`, indexed) is the per-user / per-channel partition key, filtered at every retrieval call. `'default'` = guardian; custom strings = per-channel or guest scopes. Untrusted actors get a no-op read (no injection) and no write (extract gated to guardian provenance, `assistant/src/memory/indexer.ts:62-66`).

**Structured extraction** (`assistant/src/memory/graph/extraction.ts`): LLM emits a `MemoryDiff { createNodes, updateNodes, deleteNodeIds, createEdges, createTriggers, reinforceNodeIds }` applied transactionally; each node keeps `sourceConversations: string[]` for attribution. **Dedup is the weak spot** — the v1 graph relies on an *optional* LLM re-rank pass at retrieval, not fingerprinting (the old `memory_items` fingerprint dedup was dropped in migration 189). So README "dedup" is partial.

**Embeddings** (`assistant/src/memory/embedding-backend.ts`): auto chain local ONNX (`bge-small-en-v1.5`) → OpenAI → Gemini → Ollama, 32 MB LRU cache, Qdrant circuit breaker. Local-by-default is real.

**"Memory v3" / v2 concept pages** is a parallel narrative-page retrieval path (markdown pages + EMA-based activation tiers, `assistant/src/memory/v2/`), shipped *behind a shadow plugin* (`memory-v3-shadow`) so a new memory system runs in production alongside the old one before switchover.

## 6. Security

Two genuinely strong primitives: a resolved-once trust model and a hard credential process boundary.

- **Trust tiers (guardian / trusted / unknown).** Resolved once at inbound (`assistant/src/runtime/actor-trust-resolver.ts:8-46`) by matching `actorExternalId` against a guardian binding for `(assistantId, channel)`, then enforced everywhere via a unified `TrustContext`. Guardian = full control, self-approves tools; trusted contact = can invoke tools, needs approval for sensitive ops; unknown = fail-closed, no memory read, no tool trigger, no escalation. Default is deny.
- **Credential isolation (CES).** `credential-executor/` is a top-level package in its own process/container, reachable only by RPC (stdio JSON-RPC locally; Unix socket `/run/ces-bootstrap` in Docker, ARCHITECTURE.md:38-46). The assistant calls three tools (`run_authenticated_command`, `make_authenticated_request`, `manage_secure_command_tool`); CES materializes the secret in *its* process and returns only stdout/HTTP response. **Source imports between assistant and CES are banned**; they share only typed contract packages (`packages/ces-client`, `credential-storage`, `egress-proxy`). At rest: AES-256-GCM via `@vellumai/credential-storage`, keys in `/ces-security/{keys.enc,store.key}` (Docker volume no other container mounts) or `~/.vellum/protected/` (local).
- **Egress gating.** `packages/egress-proxy` enforces a per-secure-command *manifest*: auth adapter (`env_var`/`temp_file`/`credential_process`), egress mode (`proxy_required` | `no_network`), allowed argv patterns, domain allowlists. The daemon also runs a MITM Script Proxy with a local CA for credential-template injection (ARCHITECTURE.md:385-393).
- **Sandboxing.** Tool/meet execution uses Docker; meet bots use **Docker-in-Docker** (inner `dockerd` in the assistant container, bot lifecycle coupled to parent, ARCHITECTURE.md:212-237). **Kata** is used for apt isolation (chroot rootfs at `$VELLUM_APT_DATA_ROOT`, `docker-init-apt-root.sh`), not for per-tool VM isolation. No gVisor. The docs explicitly note DinD is *not* for managed/multi-tenant K8s (ARCHITECTURE.md:238).
- **Auth.** Single-header JWT (`iss: vellum-auth`, `aud: vellum-daemon|vellum-gateway`, `sub` principal pattern, `scope_profile` bundle, `policy_epoch` for stale-token rejection). Bootstrap is loopback-only `POST /v1/guardian/init`; refresh is single-use rotation with replay detection. Every route declares required scopes + principal types via `enforcePolicy()`.
- **Signing-key bootstrap.** Gateway mints the actor-token signing key and serves it once at `GET /internal/signing-key-bootstrap`; the daemon fetches it at startup (retry 30×), then the gateway writes a lockfile so the endpoint 403s thereafter (ARCHITECTURE.md:250-261). Removes the need to pre-share a secret between same-image containers.
- **Permission gating.** Decisions `allow` / `always_allow` / `deny` / `always_deny` (persisted to `scoped_approval_grants` SQLite, fail-closed on restart) plus *temporary in-memory* overrides `allow_once` / `allow_10m` (TTL) / `allow_conversation` (`assistant/src/tools/permission-checker.ts`, `conversation-approval-overrides.ts`). Risk classifier (`classifyRisk()`) buckets tools low/medium/high; gateway-owned auto-approve threshold, fail-closed to strict if gateway unreachable.
- **Multi-tenant note:** there is **no RLS**. Isolation is per-assistant-instance: one SQLite DB per assistant process, all state keyed by `DAEMON_INTERNAL_ASSISTANT_ID`. The web tier (Postgres) owns cross-assistant tenancy (`assistants`, `assistant_channel_accounts`, `api_keys`, ARCHITECTURE.md:429-436).

## 7. Hosting

- **Model:** "same codebase, same data model" for self-host *and* managed (README.md:28). One Docker image set deploys both; `VELLUM_ENVIRONMENT` selects the namespace.
- **Runtime topology per assistant:** assistant container (Bun daemon, HTTP+SSE) + gateway container (Bun, channel webhooks, :7830) + CES container + Qdrant + (for meets) inner dockerd. The web dashboard is a separate Next.js/Postgres tier.
- **No in-repo K8s/Helm.** The gateway exposes `/healthz` + `/readyz` for k8s liveness/readiness (`gateway/src/index.ts`, ARCHITECTURE.md:422), and there's a `helm.ts` *tool command* (the assistant can run helm), but there are **no deployment manifests or charts** in the repo. Managed K8s orchestration lives in a sibling private repo (ARCHITECTURE.md:238 note). So: self-host = Docker Compose-shaped; managed = external.
- **Multi-local-instance isolation** (ARCHITECTURE.md:103-186): each named instance gets `~/.local/share/vellum/assistants/<name>/`, its own `VELLUM_WORKSPACE_DIR` / `GATEWAY_SECURITY_DIR` / `CREDENTIAL_SECURITY_DIR`, and a lockfile (`~/.vellum.lock.json`) tracking `instanceDir`, `daemonPort`, `gatewayPort`, `qdrantPort`, `pidFile`. Ports are scanned upward from per-environment base ports (`packages/environments/src/seeds.ts`).
- **Data layout** (ARCHITECTURE.md:56-90): per-assistant data under XDG dirs; `protected/` holds keys+credentials+trust; guardian/platform tokens in `$XDG_CONFIG_HOME/vellum[-<env>]/` shared across channels.
- **Config surface:** thin root `.env.example` (Sentry DSNs, `PROXY_ALLOWED_HOSTS`, docs URL); the real surface is per-package env (`GATEWAY_PORT`, `GATEWAY_INTERNAL_URL`, `IS_CONTAINERIZED`, channel secrets `TELEGRAM_*`/`TWILIO_*`/`SLACK_*`/`WHATSAPP_*`, `CES_*`, provider API keys) plus a feature-flag registry (`meta/feature-flags/feature-flag-registry.json`) resolved at runtime over a unix socket. CLI is `vellum hatch/wake/sleep/ps/terminal/upgrade`.

## 8. Novel ideas

1. **Discriminated-union inbound envelope (`GatewayInboundEvent`)** — `gateway/src/channels/inbound-event.ts:72-77`. Channels are not an interface; they are normalize functions converging on one tagged event. Why interesting: dead-simple, type-exhaustive, zero per-channel polymorphism ceremony.
2. **8-type memory graph in one table + decay/trigger machinery** — `assistant/src/memory/graph/types.ts`. Why: cognitive-science taxonomy (episodic…shared) realized as a single discriminated table with Ebbinghaus decay, fidelity ladder, and cron/semantic/event triggers, not eight microservices.
3. **CES hard process boundary with import-ban** — secrets never enter the model process, enforced *socially* (no source imports, contract packages only) and *physically* (separate container, dedicated key volume). Why: the strongest credential story reviewed; the import-ban makes the boundary lint-checkable.
4. **Signing-key bootstrap with one-shot lockfile** — gateway serves the JWT signing key exactly once at startup, then 403s. Why: same-image containers establish a shared secret with no external secret store and no pre-baking.
5. **Shadow-plugin canary for a new memory system** (`memory-v3-shadow`) — run the next memory engine in production alongside the current one, compare injections, roll back instantly. Why: memory quality gates agent quality; this makes the swap auditable and reversible.
6. **Self-authored identity split: SOUL.md (durable, edited-on-correction) vs NOW.md (volatile scratchpad)** — `assistant/src/prompts/templates/`. Why: clean separation of relational/behavioral memory from working state, both owned and mutated by the agent.
7. **Plugin-hook agent loop** — `assistant/src/plugins/defaults/` (compaction, history-repair, exploration-drift, image-recovery, max-tokens-continue, tool-error, tool-result-truncate, title-generate, memory-retrieval). Why: the agent loop's failure-recovery and housekeeping concerns are *plugins on lifecycle hooks*, composable and third-party-extensible without forking the loop.
8. **Manifest-driven egress policy** — each secure command declares its own network mode + argv allowlist + domain allowlist (`packages/egress-proxy`). Why: capability is data, not code; new authenticated tools ship a manifest, not a new trusted code path.

## 9. Primitives that transfer to Helioy

1. **`GatewayInboundEvent` discriminated envelope** — `gateway/src/channels/inbound-event.ts:72-77` → **transport-matters**. When transport-matters grows beyond the helioy-bus to ingest Slack/email/webhook surfaces, converge every substrate on one tagged inbound event with `{sourceChannel, conversationExternalId, actorExternalId, threadId}`. Matches the existing "symmetric envelope across all substrates" lesson (the half-converted-envelope anti-pattern memory).
2. **`scope_id` partition column for memory** — `assistant/src/memory/graph/types.ts` + every retriever filter → **context-matters / cm**. cm already has a scope hierarchy (global>project>repo>session); Vellum validates that a *single indexed scope column filtered at every read* is enough for per-user/per-channel isolation without RLS. Confirms cm's design choice.
3. **Multi-signal recall scoring (decay + recency + trigger + activation boosts, then tiered injection)** — `assistant/src/memory/graph/scoring.ts`, `retriever.ts:46-152` → **context-matters / cm** and **knowledge-matters**. cm's recall ranks by kind/confidence/priority; Vellum's decayed-significance + recency (ACT-R) + trigger boosts are a richer ranking model worth borrowing for cm's `cx_recall`.
4. **Hybrid dense+sparse RRF retrieval with local-ONNX-default embeddings** — `graph-search.ts:88-96`, `embedding-backend.ts` → **knowledge-matters** (and cm if it ever embeds). Local-first ONNX with cloud fallback is exactly the Helioy local-first posture.
5. **CES credential boundary (separate process, RPC-only, import-ban, dedicated key volume)** — `credential-executor/`, ARCHITECTURE.md:38-46 → **runtime-matters** + **identity-matters**. This is the reference architecture for Helioy's credential-broker (already a theme in the shockwave review). The import-ban as a lint-enforceable boundary is the steal.
6. **Resolved-once trust tiers + fail-closed permission gating with `allow_10m`/`allow_conversation` TTLs** — `actor-trust-resolver.ts:8-46`, `permission-checker.ts`, `conversation-approval-overrides.ts` → **agent-matters** + **runtime-matters**. The grant-once / 10-minute / always taxonomy with in-memory TTL overlay on persisted grants is a clean permission model for Helioy tool gating.
7. **Signing-key bootstrap (one-shot endpoint + lockfile)** — ARCHITECTURE.md:250-261 → **runtime-matters**. For Helioy's multi-process local stack (daemon + bus + tools), a one-shot key handoff between same-image processes avoids pre-baked secrets.
8. **Plugin-hook agent loop with first-party defaults** — `assistant/src/plugins/defaults/` → **agent-matters** + **orchestration-matters**. Decomposing failure-recovery/housekeeping (compaction, history-repair, max-tokens-continue, tool-result-truncate) into composable hooks is directly applicable to Helioy's agent runtime, and resonates with linear-workflows' plugin posture.
9. **Shadow-plugin canary for swapping a core subsystem in prod** — `memory-v3-shadow` → **context-matters** (cm migrations) + general Helioy methodology. When cm changes its retrieval/ranking, run old+new in shadow and diff before switchover.
10. **SOUL.md / NOW.md self-authored identity split** — `assistant/src/prompts/templates/` → **agent-matters / attention-matters**. Durable behavioral file (edited on correction) vs volatile working scratchpad mirrors Helioy's attention-matters + identity layering; the "edit synchronously on correction, don't batch-defer" rule is a good ergonomic.

## 10. Does NOT transfer

1. **Docker-in-Docker for sandboxing** — privileged inner `dockerd` (ARCHITECTURE.md:212-237) is the opposite of Helioy's K8s-shaped endgame, and the docs themselves say it's not for multi-tenant K8s. Helioy's runtime-matters should target gVisor/Kata RuntimeClass (per the gvisor review), not DinD.
2. **Swift macOS/iOS clients** (`clients/`, 1,104 Swift files) — Helioy's surface is Electron/web (littleorgans baseline); native Apple clients are out of scope.
3. **Postgres web-tenancy tier** (`apps/web` + Drizzle/Postgres, ARCHITECTURE.md:429-436) — this is Vellum's managed-SaaS control plane. Helioy is local-first; the Postgres multi-tenant model is the v2-product concern, not v1.
4. **The full channel adapter fleet** (Twilio voice relay, WhatsApp HMAC, Telegram webhooks) — concrete integrations Helioy doesn't need now; only the *envelope* abstraction transfers, not the adapters.
5. **CONSTITUTION.md relational-archetype governance** — interesting as a product-philosophy artifact, but it's Vellum brand identity, not a reusable mechanism.
6. **Bun runtime assumption** — Vellum is Bun-native (`bunfig.toml`, `bun.lock`). Helioy's tooling is mixed Rust/TS; don't inherit the Bun coupling.

## 11. Verdict

**Borrow (primitives), build nothing.** MIT and clean, so copy is legally fine, but the value is the *patterns*, not the TypeScript. The eight high-leverage borrows: the discriminated inbound envelope (transport-matters), `scope_id` + multi-signal recall scoring + hybrid-RRF retrieval (context-matters/cm/knowledge-matters), the CES credential boundary with import-ban (runtime-matters/identity-matters), the resolved-once trust + TTL permission model (agent-matters), the signing-key bootstrap (runtime-matters), the plugin-hook agent loop, and the shadow-plugin canary methodology (cm migrations). Skip the DinD sandbox (target gVisor/Kata), the Swift clients, and the Postgres SaaS tier. This is the strongest multi-channel personal-agent reference reviewed for Helioy and worth a second pass when transport-matters or the credential-broker work begins.

## Sources consulted

- `README.md`, `ARCHITECTURE.md` (esp. :30-261 system overview, :250-261 signing-key, :103-186 multi-instance, :212-237 DinD, :339-359 schema, :429-436 web tenancy), `.env.example`, 38 `.github/workflows/*`.
- Channels: `gateway/src/channels/types.ts:1-35`, `gateway/src/channels/inbound-event.ts:72-77`, `gateway/src/routing/resolve-assistant.ts:8-46`, `assistant/src/runtime/channel-reply-delivery.ts:92-205`, `assistant/src/memory/delivery-crud.ts:46-62`.
- Memory: `assistant/src/memory/graph/{types.ts:5-14, graph-search.ts:88-96, retriever.ts:46-152, scoring.ts, extraction.ts, indexer.ts:62-66}`, `assistant/src/memory/migrations/202-memory-graph-tables.ts:14-67`, `assistant/src/memory/embedding-backend.ts`, `assistant/src/memory/v2/`.
- Security: `credential-executor/`, `packages/{credential-storage,egress-proxy,ces-client}/`, `assistant/src/runtime/actor-trust-resolver.ts:8-46`, `assistant/src/tools/permission-checker.ts`, `assistant/src/runtime/conversation-approval-overrides.ts`, `assistant/src/runtime/auth/`.
- Hosting: `assistant/Dockerfile`, `assistant/docker-entrypoint.sh`, `docker-init-apt-root.sh`, `docker-kata-*.sh`, `cli/`, `setup.sh`, `packages/environments/`, `gateway/src/index.ts` (healthz/readyz).
- Novel: `assistant/src/plugins/defaults/` (index + per-plugin dirs), `assistant/src/prompts/templates/{SOUL.md,NOW.md}`, `CONSTITUTION.md`.

## Open questions

- Where exactly is the v1→v2/v3 memory cutover decided at runtime (the `memory.v2.enabled` flag resolution path) — not fully traced.
- How the managed-platform K8s orchestration (sibling private repo) maps these containers to pods — out of repo, unverifiable here.
- Whether the LLM re-rank dedup is ever promoted to a fingerprint pass, or stays the only dedup in the graph path.

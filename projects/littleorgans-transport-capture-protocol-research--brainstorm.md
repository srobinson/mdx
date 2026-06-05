---
title: littleorgans mandatory capture layer — protocol and enterprise constraints research
type: research
tags: [littleorgans, transport, capture, proxy, tls, http2, sse, enterprise, threat-model]
summary: External primary-source research on the protocol, trust, privacy, and supply-chain constraints any mandatory littleorgans capture layer must satisfy; base-URL redirection dominates TLS interception for every current agent CLI.
status: complete
confidence: high
created: 2026-07-31
updated: 2026-07-31
---

Status: COMPLETE

## Worker Status

No nested workers were spawned. All research was executed directly by
`littleorgans:helioy-tools:deep-research:5:2.4` via primary-source retrieval
(vendor documentation, RFCs, upstream repository issues and PRs).

| Worker | Scope | Final state |
|---|---|---|
| — | — | none spawned |

Scope note: this is external evidence only. No `tm` dependency is proposed, no repo was edited, and transport-matters is treated as prior experimental evidence rather than a design input. Every claim below carries a retrieval date of 2026-07-31 unless stated otherwise, and claims are split into **[STABLE]** (protocol or vendor-documented fact) and **[ASSUMPTION]** (requires a local experiment before it can be load-bearing).

---

## 1. Executive summary

Three findings dominate.

**Base-URL redirection beats TLS interception for every agent CLI that matters.** Claude Code, Codex CLI, and Gemini CLI each document a first-class base-URL override. Anthropic documents the decisive case explicitly: setting `ANTHROPIC_BASE_URL` *without* a gateway credential routes all inference through the intermediary while the developer's claude.ai subscription login stays the active credential. A mandatory capture layer therefore does not need a private CA, a trust-store install, or an MDM rollout to see full request and response bodies for the primary runtime.

**A capture layer is a protocol participant, not a passive tap.** Anthropic's gateway protocol reference states that a gateway which rewrites or redacts request bodies breaks header/body capability pairing and produces hard `400` errors, that error response bodies must be forwarded unmodified or Claude Code's automatic retry-and-degrade path breaks, and that buffering a streamed response stalls the client. Capture that mutates anything is a correctness hazard, not merely a privacy one.

**The captured artifact is a credential-bearing, source-code-bearing object from the first byte.** Every captured request carries a live bearer token or API key in `Authorization`/`x-api-key`, and the request body carries repository source, file paths, and whatever the agent read. Redaction cannot happen on the wire without breaking pass-through, so it has to happen at the storage boundary, after the bytes are already relayed.

---

## 2. Requirement matrix

Columns: requirement, source of the constraint, what satisfies it, confidence.

### 2.1 Interposition mechanism

| # | Requirement | Constraint source | Satisfied by | Class |
|---|---|---|---|---|
| R1 | Capture must see request and response bodies for Claude Code without installing a CA | `ANTHROPIC_BASE_URL` set without a credential variable routes through the intermediary and preserves the claude.ai subscription login ([llm-gateway](https://code.claude.com/docs/en/llm-gateway)) | Localhost reverse proxy at a base URL; no MITM | STABLE |
| R2 | The same for Codex CLI | `openai_base_url` in `config.toml` and the `OPENAI_BASE_URL` env var override the built-in provider; `[model_providers]` supports `base_url`, `env_key`, `wire_api` ([Codex config reference](https://developers.openai.com/codex/config-reference)) | Base-URL override; note `openai`, `ollama`, `lmstudio` provider ids are reserved | STABLE |
| R3 | The same for Gemini CLI | `GOOGLE_GEMINI_BASE_URL` / `GOOGLE_VERTEX_BASE_URL`; URL must be HTTPS unless it is `localhost`, `127.0.0.1`, or `[::1]` ([gemini-cli configuration.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md)) | Localhost base URL avoids the HTTPS requirement entirely | STABLE |
| R4 | Capture must survive a runtime whose base URL cannot be overridden | No general mechanism exists; falls back to CONNECT proxy + TLS interception (RFC 9110 §9.3.6 tunnel semantics, [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)) | Two-mode design: redirect mode (default) and intercept mode (fallback) | STABLE |
| R5 | SOCKS is not an option for Claude Code | "Claude Code does not support SOCKS proxies" ([network config](https://code.claude.com/docs/en/corporate-proxy)) | HTTP CONNECT only | STABLE |

### 2.2 Wire correctness

| # | Requirement | Constraint source | Satisfied by | Class |
|---|---|---|---|---|
| R6 | Never buffer a streamed response | "Inference responses must stream… a gateway that buffers complete responses before relaying them stalls the client" ([gateway protocol](https://code.claude.com/docs/en/llm-gateway-protocol)) | Byte-streaming relay; `X-Accel-Buffering: no` if nginx is ever in path; no response compression on SSE | STABLE |
| R7 | Forward `anthropic-beta` and `anthropic-version` byte-for-byte, as an open list | Same source: "don't allowlist individual values, because the set changes with Claude Code releases" | Opaque header passthrough | STABLE |
| R8 | Stripping `anthropic-beta` fails subscription-auth requests with `401` | Same source: the header carries an OAuth capability the upstream requires under claude.ai login | Never filter that header, even in a "minimal" mode | STABLE |
| R9 | Do not modify request bodies | Same source: "A gateway that rewrites or redacts request bodies for content inspection breaks the pairing the same way stripping does, so inspect without modifying" | Redact at rest, not on the wire | STABLE |
| R10 | Forward error response bodies unmodified | Same source: "The retry logic matches on the upstream's error wording… A gateway that wraps upstream errors in its own envelope breaks the recovery path even when it preserves the status code" | No error envelopes | STABLE |
| R11 | Forward the `system` array unchanged, attribution block first | Same source: the `api.anthropic.com` strip of the attribution block is positional; reordering or merging leaks it into the prompt and the cache key | Structural passthrough of `system` | STABLE |
| R12 | Support SSE event grammar for capture parsing | Anthropic streams `message_start`, `content_block_start`, `content_block_delta`, `content_block_stop`, `message_delta`, `message_stop`, `ping`, `error` ([messages-streaming](https://docs.anthropic.com/en/api/messages-streaming)) | Event-typed parser, tolerant of unknown event names | STABLE |
| R13 | Handle HTTP/2 on at least the upstream leg | undici `allowH2` defaults to `true` and selects by ALPN ([undici Client.md](https://github.com/nodejs/undici/blob/main/docs/docs/api/Client.md)); Rust `reqwest` negotiates h2 by ALPN by default | h2-capable client on the upstream leg; h1 is acceptable on the loopback leg | STABLE |
| R14 | Expose `/v1/messages` and optionally `/v1/messages/count_tokens` | Gateway protocol: inference posts to `/v1/messages?beta=true`, "match on the path, not the full URL"; token counting is the only optional endpoint | Path-prefix routing | STABLE |
| R15 | Tolerate best-effort startup traffic | Gateway protocol: `HEAD /` connectivity probe, and `GET /inference-profiles?type=SYSTEM_DEFINED` on Bedrock-format gateways; both rejectable | Return anything; do not 500 the session | STABLE |
| R16 | `/v1/models` discovery must not redirect and must answer inside 3s | Gateway protocol: `GET /v1/models?limit=1000`, 3s timeout, "any redirect is treated as failure so the credential can't leak to a redirect target" | Serve directly at the base URL or omit the endpoint | STABLE |

### 2.3 Coverage boundaries

| # | Requirement | Constraint source | Implication | Class |
|---|---|---|---|---|
| R17 | Base-URL capture does **not** see all Claude Code egress | Documented hosts outside the gateway path: `api.anthropic.com` (fast-mode check, WebFetch domain safety check, feature flags, telemetry), `claude.ai`, `platform.claude.com`, `mcp-proxy.anthropic.com`, `downloads.claude.ai`, `storage.googleapis.com`, `bridge.claudeusercontent.com`, `raw.githubusercontent.com`, two Datadog intake hosts, `formulae.brew.sh`, `code.claude.com` ([network config](https://code.claude.com/docs/en/corporate-proxy)) | "Mandatory capture" must be scoped to *inference* traffic, or it silently under-claims | STABLE |
| R18 | Fast mode and WebFetch preflight bypass `ANTHROPIC_BASE_URL` by design | Gateway protocol: "The fast mode availability check never appears in gateway logs… The WebFetch domain safety check also calls `api.anthropic.com` directly" | Capture completeness claims must exclude these | STABLE |
| R19 | Cloud and Slack surfaces cannot be captured at all | "Claude Code in Slack and Claude Code on the web are Anthropic-hosted products that always use Anthropic's API… Gateway variables set in a cloud session's environment configuration are not applied" | A mandatory-capture policy has to disable those surfaces, not intercept them | STABLE |
| R20 | Remote Control and voice dictation break under capture | Remote Control is disabled while `ANTHROPIC_BASE_URL` points at a non-Anthropic host (v2.1.196+); voice dictation needs a claude.ai identity | Feature-loss budget is a product decision, not an implementation detail | STABLE |

### 2.4 Configuration delivery

| # | Requirement | Constraint source | Satisfied by | Class |
|---|---|---|---|---|
| R21 | Env-var-only interposition is unreliable for background agents | "The supervisor is one process shared by every terminal. It inherits the environment of whichever shell starts it first, and an OS-installed supervisor receives no shell environment at all… reaches background agents when that shell happened to cold-start the supervisor, and silently doesn't when a different shell did" | Configuration must land in `~/.claude/settings.json` `env` or managed settings, not a shell export | STABLE |
| R22 | Variables are read once at startup | "Variables exported in your shell are read once at startup, so a running session doesn't pick up later changes" | Capture cannot be enabled mid-session; enrollment is a launch-time act | STABLE |
| R23 | A repository cannot redirect a Desktop-managed session's TLS or proxy path | In Desktop sessions where the app manages the provider connection, proxy and CA variables are read only from managed settings and `~/.claude/settings.json`, ignored in a repository's own settings files (v2.1.217+) | Repo-scoped config is not a viable enrollment channel for those sessions | STABLE |
| R24 | Cloud sessions ignore CA/mTLS/proxy vars from settings `env` blocks | Documented ignore list: `CLAUDE_CODE_CLIENT_CERT`, `CLAUDE_CODE_CLIENT_KEY`, `CLAUDE_CODE_CLIENT_KEY_PASSPHRASE`, `NODE_EXTRA_CA_CERTS`, `NODE_TLS_REJECT_UNAUTHORIZED`, `CLAUDE_CODE_OAUTH_SCOPES` | Same conclusion as R19 | STABLE |
| R25 | A corporate launcher wrapper on `PATH` does not reach background processes | "The supervisor and its workers start Claude Code from a fixed path rather than by looking up `claude` on `PATH`, so every background agent bypasses a wrapper you place earlier on `PATH`" — use the `processWrapper` setting / `CLAUDE_CODE_PROCESS_WRAPPER` | A `lilo run`-style exec wrapper is **not** sufficient for mandatory coverage of background agents | STABLE |

R25 is the sharpest constraint on any "wrap the launch and capture is automatic" design.

### 2.5 TLS interception path (fallback mode only)

| # | Requirement | Constraint source | Cost | Class |
|---|---|---|---|---|
| R26 | Interception needs a per-host CA in every relevant trust store | mitmproxy generates leaf certs signed by its own CA, valid 199 days to stay under the 398-day cap ([mitmproxy certificates](https://docs.mitmproxy.org/stable/concepts/certificates/)) | Root-equivalent key material on every developer machine | STABLE |
| R27 | macOS trust requires admin or MDM | `security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain` needs root; Apple removed forced CLI trust, so a configuration profile / MDM is the supported path | Enrollment is an IT act, not a `brew install` | STABLE |
| R28 | Runtime trust stores diverge from OS trust stores | Claude Code defaults to `bundled,system` via `CLAUDE_CODE_CERT_STORE`, but reading the OS store needs `tls.getCACertificates`, i.e. Node 22.15+ on npm installs; older Node sees only bundled + `NODE_EXTRA_CA_CERTS` | Per-runtime CA plumbing, versioned | STABLE |
| R29 | Rust runtimes are a separate trust problem | `rustls-native-certs` respects local roots, `webpki-roots` compiles in Mozilla's set and ignores enterprise CAs; `rustls-platform-verifier` still lacks `SSL_CERT_FILE` support ([reqwest #2640](https://github.com/seanmonstar/reqwest/issues/2640)) | A Rust agent built against `webpki-roots` cannot be intercepted without a rebuild | STABLE |
| R30 | Codex has its own CA precedence chain | `CODEX_CA_CERTIFICATE` > `SSL_CERT_FILE` > system roots, unified across HTTPS and websocket clients as of v0.129.0; aws-lc-rs is the process-wide rustls provider so P-521/SHA-512 enterprise chains verify | Interception must emit a chain the target provider accepts | STABLE, vendor-blog-sourced |
| R31 | Interception collides with pre-existing corporate interception | Zscaler / CrowdStrike Falcon / Palo Alto already terminate TLS in many orgs; a second intercepting hop must trust the first one's CA and re-present its own | Chained-MITM configuration is required, not optional | STABLE |
| R32 | Node's own proxy support is now first-class and must be reasoned about | `NODE_USE_ENV_PROXY` / `--use-env-proxy` make Node honour `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY`; `--use-system-ca` stable since v24.10.0; undici `EnvHttpProxyAgent` is the experimental env-driven dispatcher ([Node CLI docs](https://nodejs.org/api/cli.html)) | Behaviour differs by Node major; pin expectations per runtime | STABLE (exact "version added" for `NODE_USE_ENV_PROXY` conflicts across sources — see §5 U1) |

### 2.6 Artifact privacy and observability

| # | Requirement | Constraint source | Satisfied by | Class |
|---|---|---|---|---|
| R33 | Captured requests contain live credentials | Gateway protocol documents `Authorization` and `x-api-key` on every request; `apiKeyHelper` values are sent in **both** headers | Strip credential headers at the storage boundary; never at the relay | STABLE |
| R34 | Captured bodies are source code and prompt content | Inherent to `/v1/messages` bodies | Storage is a code-confidentiality asset with the same classification as the repo | STABLE |
| R35 | Redaction belongs at rest, and the industry agrees | LiteLLM ships secret detection/redaction as enterprise-only; Portkey offers PII redaction plus a privacy mode that suppresses log storage entirely; Kong AI PII Sanitizer covers 20 categories across 9 languages | Precedent for a "capture but do not persist content" mode | STABLE |
| R36 | An emitted-telemetry path should follow OTel GenAI semconv, with eyes open | GenAI semantic conventions were still **Development** status as of May 2026, with no committed stabilization timeline; prompt/completion content capture is an explicit opt-in | Track the spec; do not treat attribute names as stable | STABLE |
| R37 | Mandatory capture of a developer's traffic is a labour-law event in the EU | Consent in an employment relationship is generally not "freely given" under GDPR; works councils in Germany (BetrVG), the Netherlands, Austria, and Sweden hold co-determination or consent rights over monitoring systems, separate from the GDPR basis | "Mandatory" needs a lawful basis other than consent, plus works-council process where applicable | STABLE |
| R38 | Session correlation should ride existing headers, not body parsing | Claude Code sends `x-claude-code-session-id`, `x-claude-code-agent-id`, `x-claude-code-parent-agent-id`; "Use it to aggregate all requests from one session without parsing request bodies" | Free subagent/parent topology, no body inspection needed | STABLE |
| R39 | Agent IDs are not user IDs | "the ID identifies an agent, not a person or a device, so don't treat the agent ID header as a user identifier" | Attribution needs a separate identity join | STABLE |

R38 is materially useful: the parent/child agent topology that a capture layer would otherwise reconstruct by body parsing is already on the wire as headers.

### 2.7 Supply chain

| # | Requirement | Constraint source | Satisfied by | Class |
|---|---|---|---|---|
| R40 | A mandatory capture binary is a privileged, widely-deployed artifact | Notarization is required for software distributed outside the Mac App Store signed with Developer ID; hardened runtime (`--options=runtime`) is a precondition | Signed + notarized release pipeline | STABLE |
| R41 | A bare Mach-O cannot be stapled | Stapling works on `.dmg`, `.pkg`, `.app` only | Ship a `.pkg` if offline Gatekeeper verification matters | STABLE |
| R42 | The interception CA private key is the highest-value secret in the system | Inherent | If intercept mode ships, per-host key generation, non-exportable storage, and a revocation story are mandatory | ASSUMPTION on mechanism, STABLE on threat |

---

## 3. Threat boundaries

Five boundaries, ordered by how much design they constrain.

**B1 — Relay boundary (bytes in flight).** Everything crossing it must be unmodified: headers as an open list, bodies byte-for-byte, error envelopes preserved, streaming un-buffered. Sources R6–R11. Any capture feature that wants to change a byte belongs on the far side of this boundary or nowhere.

**B2 — Persistence boundary (bytes at rest).** This is the only place redaction is safe. Credential headers (R33), prompt content (R34), and the OAuth capability values inside `anthropic-beta` all cross here. The industry precedent (R35) is a three-way switch: full content, redacted content, metadata only.

**B3 — Trust boundary (who can enrol a machine).** Anthropic has already drawn a line here that a capture design must respect rather than fight: a checked-out repository cannot redirect the TLS or proxy path of a Desktop-managed session (R23), and cloud sessions ignore CA and proxy variables entirely (R24). The corollary is that repo-local config is an untrusted enrollment channel by vendor design. Trusted channels are managed settings and `~/.claude/settings.json`.

**B4 — Coverage boundary (what "mandatory" can honestly mean).** Base-URL capture covers inference. It does not cover fast-mode checks, WebFetch domain safety preflight, telemetry, plugin downloads, MCP connector traffic, or any Anthropic-hosted surface (R17–R19). A capture layer that claims completeness without enumerating this list is making a false claim. Under `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` the residue shrinks but does not vanish: WebFetch preflight is explicitly unaffected.

**B5 — Legal boundary.** Mandatory, always-on capture of developer traffic that contains their prompts is employee monitoring in the EU sense (R37). Consent is not the available basis. Works-council co-determination in DE/NL/AT/SE attaches to the *system*, not to each use of it. US state wiretap and notice law adds a second, differently-shaped constraint.

A sixth boundary exists only if intercept mode ships: **B6 — CA boundary.** Distributing a root-equivalent CA to every developer machine (R26–R28, R42) creates a single key whose compromise yields silent interception of all TLS on those machines, including traffic unrelated to agents. Redirect mode has no equivalent exposure. This asymmetry is the strongest argument for making redirect the default and intercept the explicitly-opted-into fallback.

---

## 4. Prior art worth reading before designing

- **Helicone** made the proxy-first, zero-instrumentation bet and it worked; it was acquired by Mintlify in March 2026 and is now in maintenance mode. The architecture is validated; the standalone business was not.
- **Cloudflare AI Gateway** exposes an OpenAI-compatible `/compat` endpoint and translates to upstream native APIs. Translation is a different product than capture, and it is where feature pass-through breaks (cf. R7–R10).
- **LiteLLM** is the reference open-source implementation of the base-URL swap across 100+ providers; **Portkey** went Apache 2.0 in March 2026 with the strongest guardrails story.
- **Langfuse** is the "gateway plus separate observability" half of the pattern, joined over OTel. Relevant if littleorgans wants capture and analysis to be separable.
- **mitmproxy** is the reference for intercept mode, including the 199-day leaf validity trick and the ALPN re-negotiation that keeps h2 end-to-end.

The 2026 landscape splits cleanly into gateway-as-observability and gateway-plus-observability. That split is the first architectural fork for a littleorgans capture layer, and it is orthogonal to the redirect-versus-intercept fork.

---

## 5. Unknowns and assumptions requiring experiments

**U1 — `NODE_USE_ENV_PROXY` version added.** The Node CLI documentation page renders a "v15.10.0" history entry, while release-note coverage attributes `fetch()` support to v24.0.0 and `http`/`https` client support to v24.5.0. These cannot both be right. *Experiment:* run `node -e` probes against pinned 20/22/24 builds with a loopback proxy and record which majors honour it for `fetch` versus `http.request`.

**U2 — Does redirect mode actually preserve subscription auth end to end?** The vendor statement (R1) is unambiguous, but it presumes the intermediary forwards the OAuth capability in `anthropic-beta`. *Experiment:* run a claude.ai-logged-in session through a null-transform loopback relay and confirm a `200`, then confirm a `401` when the header is stripped. This single experiment determines whether intercept mode is needed at all for the primary runtime.

**U3 — Which leg negotiates HTTP/2.** undici's `allowH2` default of `true` is ALPN-conditional; whether `api.anthropic.com` actually selects h2 for Claude Code, and whether the Anthropic-format upstream behaves identically under h1, is unverified. *Experiment:* capture ALPN on a live session for Claude Code (Node/Bun), Codex (Rust/reqwest), and Gemini CLI (undici).

**U4 — Bun's trust and proxy behaviour.** Claude Code's native installer bundles a runtime; a Windows report states the bundled Bun honours neither the Windows system trust store nor `NODE_EXTRA_CA_CERTS`. Whether that holds on macOS/Linux and on current versions is unverified, and it is a hard blocker for intercept mode on native installs.

**U5 — Streaming fidelity under relay.** R6 forbids buffering, but the failure mode is graded, not binary: a relay that coalesces SSE frames may pass tests and still degrade perceived latency. *Experiment:* measure inter-frame delta distributions direct versus relayed.

**U6 — What `anthropic-beta` values actually appear**, and whether any of them are OAuth-scoped in a way that makes the captured header itself a credential fragment. Unverified.

**U7 — Whether `x-claude-code-agent-id` is stable enough to be a join key** against the littleorgans `SessionId`. The docs say subagent IDs are freshly generated per spawn while teammate agents reuse a stable name-based ID; a capture schema that assumes one shape will be wrong for the other.

**U8 — Codex and Gemini equivalents of R25.** Whether either ships a background-supervisor process that bypasses a `PATH` wrapper the way Claude Code's does is unresearched, and it determines whether a launch-wrapper enrollment model can be uniform across runtimes.

**U9 — HTTP/3 exposure.** No current agent CLI is known to use QUIC to a model provider, but RFC 9298 CONNECT-UDP exists and the tooling (masque-go, quic-go) is mature. If a provider or SDK adopts h3, a CONNECT-based intercept mode goes blind while redirect mode is unaffected. This is a further argument for redirect-as-default. Unverified as a near-term risk.

**U10 — Legal posture.** Whether littleorgans is shipping a tool that *enables* monitoring (obligation on the deploying org) or *performs* it (obligation partly on littleorgans) has not been settled, and it determines whether §B5 is a docs problem or a product-design problem.

---

## 6. Sources

Retrieved 2026-07-31 unless noted.

**Protocol specifications**
- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) (CONNECT, §9.3.6; tunnel as blind relay)
- [RFC 9298 — Proxying UDP in HTTP](https://datatracker.ietf.org/doc/html/rfc9298)
- [Anthropic Messages streaming](https://docs.anthropic.com/en/api/messages-streaming)

**Vendor documentation (primary, highest weight)**
- [Claude Code — Enterprise network configuration](https://code.claude.com/docs/en/corporate-proxy)
- [Claude Code — Gateway protocol reference](https://code.claude.com/docs/en/llm-gateway-protocol)
- [Claude Code — Connect to an LLM gateway](https://code.claude.com/docs/en/llm-gateway-connect)
- [Claude Code — Other LLM gateways](https://code.claude.com/docs/en/llm-gateway)
- [Node.js CLI documentation](https://nodejs.org/api/cli.html) (`NODE_USE_ENV_PROXY`, `NODE_EXTRA_CA_CERTS`, `--use-system-ca`)
- [undici `Client` API](https://github.com/nodejs/undici/blob/main/docs/docs/api/Client.md) (`allowH2`)
- [undici `ProxyAgent` API](https://undici.nodejs.org/docs/docs/api/ProxyAgent.html)
- [Codex configuration reference](https://developers.openai.com/codex/config-reference)
- [gemini-cli configuration reference](https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md)
- [mitmproxy — Certificates](https://docs.mitmproxy.org/stable/concepts/certificates/)
- [mitmproxy — How mitmproxy works](https://docs.mitmproxy.org/stable/concepts/how-mitmproxy-works/)

**Implementation evidence**
- [reqwest #2640 — `SSL_CERT_FILE` vs rustls-tls](https://github.com/seanmonstar/reqwest/issues/2640)
- [rustup #3400 — webpki-roots vs native-tls and enterprise middleboxes](https://github.com/rust-lang/rustup/issues/3400)
- [Codex #14239 — extend custom CA handling across HTTPS and websocket clients](https://github.com/openai/codex/pull/14239)
- [Codex #27706 — aws-lc-rs rustls provider](https://github.com/openai/codex/pull/27706)
- [Codex #6849 — OAuth login fails behind corporate proxy with custom CA](https://github.com/openai/codex/issues/6849)
- [claude-code #41157 — Windows enterprise SSL inspection, bundled runtime trust](https://github.com/anthropics/claude-code/issues/41157)
- [claude-code #22512 / #10458 — `NODE_EXTRA_CA_CERTS` in settings.json](https://github.com/anthropics/claude-code/issues/22512)
- [claude-code #11660 — `HTTPS_PROXY` in settings.json](https://github.com/anthropics/claude-code/issues/11660)
- [gemini-cli #15543 — corporate proxies and custom LLM gateways](https://github.com/google-gemini/gemini-cli/issues/15543)
- [gemini-cli #16173 — custom API version for enterprise proxy endpoints](https://github.com/google-gemini/gemini-cli/issues/16173)

**Ecosystem and prior art**
- [LiteLLM — secret detection/redaction](https://docs.litellm.ai/docs/proxy/guardrails/secret_detection)
- [Helicone's proxy-first bet](https://www.joinnextdev.com/a/helicone/helicones-proxy-first-bet-is-now-infrastructure)
- [Top 5 AI gateways 2026](https://guptadeepak.com/tools/top-5-ai-gateways-2026/)
- [OpenTelemetry — Inside the LLM Call: GenAI Observability](https://opentelemetry.io/blog/2026/genai-observability/)
- [Greptime — OTel GenAI semantic conventions status](https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions) (Development status as of 2026-05)

**Operational and legal**
- [Configure SSE through nginx](https://oneuptime.com/blog/post/2025-12-16-server-sent-events-nginx/view) (`proxy_buffering`, `X-Accel-Buffering`)
- [Germany employee monitoring laws — BetrVG and GDPR](https://www.employee-monitoring.net/compliance/employee-monitoring-laws-germany)
- [Employee monitoring and GDPR](https://secureprivacy.ai/blog/employee-monitoring-gdpr-guide)
- [macOS code signing and notarization](https://docs.bastion.tech/devices/apple/signing-notarizing)
- [Adding root CAs to macOS trust stores](https://learnings.bolmaster2.com/posts/add-certificates-to-trust-stores)

---

## 7. Source quality assessment

Highest confidence sits with the Anthropic gateway documentation set, which is unusually specific about failure modes and is the authority on its own client's behaviour. RFCs and the Node/undici references are definitive for protocol semantics. GitHub issues and PRs in `openai/codex` and `anthropics/claude-code` are strong evidence of real-world enterprise failure modes but reflect point-in-time versions.

Weakest links: the Codex custom-CA precedence chain (R30) comes from a third-party knowledge base corroborated by the linked PRs rather than from OpenAI's own docs, and should be re-verified against `developers.openai.com` before being relied on. The Node `NODE_USE_ENV_PROXY` version history is internally inconsistent across sources (U1). The AI-gateway landscape summaries are secondary and used only for orientation, not for any load-bearing claim.

Notable gap: Reddit, HackerNews, and X returned essentially nothing on mandatory agent-traffic capture. The practitioner conversation on this problem is happening in vendor docs and GitHub issues, not in community forums. That is itself a signal about how new the problem is.

---

## 8. Actionable takeaways

1. **Make redirect mode the default and the only mode in v1.** It needs no CA, no MDM, no admin rights, preserves subscription auth, and is immune to the h3 risk. Run experiment U2 first; it is a half-day and it decides the architecture.
2. **Write the relay as a strict byte-transparent proxy.** Capture is a tee, never a transform. Encode R6–R11 as tests, because each has a documented failure mode and three of them fail loudly only on a future Claude Code release.
3. **Enumerate the coverage boundary in the product copy.** "Mandatory capture" should read "mandatory capture of model inference", with the R17 host list published. The honesty is cheap and the alternative is a broken claim.
4. **Enroll through managed settings / `~/.claude/settings.json`, not a `PATH` wrapper.** R25 means a launch-wrapper design silently misses background agents, which is exactly the traffic a mandatory layer most wants.
5. **Use `x-claude-code-session-id` and the agent-id headers as the correlation spine.** Free topology, no body parsing, and it joins cleanly to a platform `SessionId`.
6. **Treat the persistence boundary as the product's real security surface**, and ship a metadata-only mode from day one, following the Portkey privacy-mode precedent.
7. **Resolve the legal posture (U10) before writing the word "mandatory" in any user-facing document.**

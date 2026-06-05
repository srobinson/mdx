---
title: Agent CLI traffic capture — protocol, trust, and enterprise constraints (2026)
type: research
tags: [proxy, tls, mitm, http2, sse, claude-code, codex, gemini-cli, llm-gateway, observability, capture]
summary: Base-URL redirection, not TLS interception, is the viable capture mechanism for every current agent CLI; Anthropic documents that ANTHROPIC_BASE_URL without a credential preserves subscription auth while routing all inference through an intermediary.
status: active
confidence: high
created: 2026-07-31
updated: 2026-07-31
related: ["~/.mdx/projects/littleorgans-transport-capture-protocol-research--brainstorm.md"]
---

# Agent CLI traffic capture: protocol, trust, and enterprise constraints

Full requirement matrix, threat boundaries, and experiment list live in
`~/.mdx/projects/littleorgans-transport-capture-protocol-research--brainstorm.md`.
This file is the research-of-record: findings by theme, source grading, and gaps.

## Executive summary

Every current agent CLI (Claude Code, Codex, Gemini CLI) ships a first-class base-URL override, and Anthropic documents that setting `ANTHROPIC_BASE_URL` *without* a gateway credential routes all inference through the intermediary while leaving the developer's claude.ai subscription login as the active credential. That single fact removes the need for a private CA, a trust-store install, and an MDM rollout for the dominant runtime. The residual problems are not interception problems: they are byte-transparency, coverage honesty, enrollment reliability, and the legal status of monitoring developer prompts.

## Detailed findings

### 1. Redirection dominates interception

Anthropic's LLM gateway docs state that `ANTHROPIC_BASE_URL` alone does not replace the subscription: "Requests still route through the gateway, but a saved claude.ai login remains the active credential, so its usage limits and billing apply." The gateway must forward the OAuth capability carried in `anthropic-beta`, and stripping it fails those requests with `401`.

Codex exposes `openai_base_url` in `config.toml` plus the `OPENAI_BASE_URL` env var, and a `[model_providers]` block with `base_url`, `env_key`, and `wire_api` (`responses` → `/responses`, `chat` → `/chat/completions`). Provider ids `openai`, `ollama`, `lmstudio` are reserved.

Gemini CLI exposes `GOOGLE_GEMINI_BASE_URL` and `GOOGLE_VERTEX_BASE_URL`; the URL must be HTTPS unless it targets `localhost`, `127.0.0.1`, or `[::1]` — which makes a loopback capture endpoint the path of least resistance. Open issue #16173 notes the API version is hardcoded (`v1beta` / `v1beta1`), which constrains proxies that expect a different version.

### 2. A capture relay is a protocol participant

Anthropic's gateway protocol reference is unusually explicit about failure modes, and each is a design constraint:

- Streaming must not be buffered; a buffering gateway "stalls the client."
- `anthropic-beta` and `anthropic-version` must be forwarded verbatim and treated as **open lists**: "A gateway pinned to an observed list strips the next capability's header or field and breaks it on the release that introduces it."
- Capability header/body pairs travel together; splitting them yields hard `400`s. Critically: "A gateway that rewrites or redacts request bodies for content inspection breaks the pairing the same way stripping does, so inspect without modifying."
- Error bodies must pass through unmodified, because Claude Code's retry-and-degrade logic matches on the upstream's error *wording*. Wrapping errors breaks recovery even with the status code preserved.
- The system-prompt attribution block is stripped **positionally** by `api.anthropic.com`. Reordering the `system` array, prepending a block, or merging entries defeats the strip and leaks the block into the prompt and the cache key.
- `/v1/models` discovery uses a 3s timeout and treats *any* redirect as failure, deliberately, "so the credential can't leak to a redirect target."

Practical corollary: redaction is only safe at rest, never on the wire.

### 3. Coverage is narrower than "capture everything"

Claude Code's documented egress reaches far beyond `api.anthropic.com` inference: `claude.ai`, `platform.claude.com`, `mcp-proxy.anthropic.com`, `downloads.claude.ai`, `storage.googleapis.com`, `bridge.claudeusercontent.com`, `raw.githubusercontent.com`, two Datadog intake hosts, `formulae.brew.sh`, `code.claude.com`. Two calls bypass `ANTHROPIC_BASE_URL` **by design**: the fast-mode availability check and the WebFetch domain safety preflight, both of which go direct to `api.anthropic.com`. `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` shrinks the residue but explicitly does not affect the WebFetch preflight.

Anthropic-hosted surfaces cannot be captured at all: "Claude Code in Slack and Claude Code on the web… always use Anthropic's API. Gateway variables set in a cloud session's environment configuration are not applied." Remote Control is disabled outright when `ANTHROPIC_BASE_URL` points at a non-Anthropic host (v2.1.196+).

### 4. Enrollment reliability is the hidden constraint

The single most design-relevant finding for a launch-wrapper architecture: background agents run under a per-user supervisor that "start[s] Claude Code from a fixed path rather than by looking up `claude` on `PATH`, so every background agent bypasses a wrapper you place earlier on `PATH`." The supported hook is the `processWrapper` setting / `CLAUDE_CODE_PROCESS_WRAPPER`. The supervisor also inherits the environment of whichever shell cold-started it, so shell exports reach background agents nondeterministically. Configuration must land in `~/.claude/settings.json` `env` or managed settings.

Anthropic has also drawn a trust boundary that a capture design should respect rather than fight: in Desktop-managed sessions, proxy and CA variables are read only from managed settings and `~/.claude/settings.json`, and ignored in a repository's own settings files, "so a checked-out repository can't redirect the TLS or proxy path of a session whose credentials come from the app."

### 5. Interception, if it ships, is a per-runtime trust problem

Not one trust store, but several, diverging:

- Claude Code defaults to `CLAUDE_CODE_CERT_STORE=bundled,system`, but reading the OS store needs `tls.getCACertificates` — Node 22.15+ on npm installs. Older Node sees only the bundled Mozilla set plus `NODE_EXTRA_CA_CERTS`.
- Node gained `--use-system-ca` (stable v24.10.0) and `NODE_USE_ENV_PROXY` / `--use-env-proxy` for env-driven proxying; undici's `EnvHttpProxyAgent` is the experimental dispatcher equivalent, and `ProxyAgent` tunnels https via HTTP CONNECT.
- Rust splits on crate choice: `rustls-native-certs` respects local roots, `webpki-roots` compiles in Mozilla's set and ignores enterprise CAs entirely, and `rustls-platform-verifier` still lacks `SSL_CERT_FILE`. A Rust agent built against `webpki-roots` cannot be intercepted without a rebuild.
- Codex resolved this with a unified `codex-client::custom_ca` module (v0.129.0) with precedence `CODEX_CA_CERTIFICATE` > `SSL_CERT_FILE` > system roots, covering HTTPS and websocket clients, and moved to aws-lc-rs as the rustls provider so enterprise chains signed with P-521/SHA-512 verify.
- macOS trust requires root or, since Apple removed forced CLI trust, a configuration profile via MDM.
- mitmproxy remains the reference implementation: on-the-fly leaf generation signed by its own CA, 199-day validity to stay under the 398-day cap, ALPN re-negotiated so h2 stays h2 end to end.

Add the chaining problem: many orgs already run Zscaler / CrowdStrike Falcon / Palo Alto TLS termination, so a second intercepting hop must trust the first's CA and re-present its own.

### 6. Transport shape

undici's `allowH2` defaults to `true` and selects by ALPN, so the Node-based CLIs may or may not run h2 to the provider depending on negotiation; Rust `reqwest` negotiates h2 by ALPN by default. Anthropic streams SSE with a fixed event grammar (`message_start`, `content_block_start`, `content_block_delta`, `content_block_stop`, `message_delta`, `message_stop`, `ping`, `error`). Inference posts to `/v1/messages?beta=true` — match on path, not full URL. If nginx ever sits in the path, `proxy_buffering` defaults to on and will hold the entire response until `proxy_read_timeout`; `X-Accel-Buffering: no` and disabled compression are the fixes.

HTTP/3 is not yet a live risk for agent CLIs, but RFC 9298 CONNECT-UDP and mature tooling (masque-go, quic-go) mean a provider adopting h3 would blind a CONNECT-based intercept while leaving redirect capture unaffected.

### 7. The artifact is credential-bearing and legally loaded

Every captured request carries a live credential in `Authorization` and/or `x-api-key` (an `apiKeyHelper` value is sent in **both**), and the body carries repository source. The industry has converged on redaction as a gateway feature — LiteLLM ships secret detection/redaction as enterprise-only, Portkey offers PII redaction plus a privacy mode that suppresses log storage entirely, Kong's AI PII Sanitizer covers 20 categories across 9 languages — but R9 above means none of it can happen on the relay path without breaking correctness.

OTel's GenAI semantic conventions were still **Development** status as of May 2026 with no committed stabilization timeline, and prompt/completion content capture is an explicit opt-in there too.

Legally, mandatory always-on capture of developer prompts is employee monitoring in the EU sense. Consent in an employment relationship is generally not "freely given" under GDPR, and works councils in Germany (BetrVG), the Netherlands, Austria, and Sweden hold co-determination or consent rights over the monitoring *system* independent of the GDPR basis.

### 8. Free correlation metadata

Claude Code already emits `x-claude-code-session-id`, `x-claude-code-agent-id`, and `x-claude-code-parent-agent-id`, documented for aggregating a session "without parsing request bodies." Subagent IDs are fresh per spawn; teammate agents in an agent team reuse a stable name-based ID. The docs warn the agent ID "identifies an agent, not a person or a device," so attribution needs a separate identity join.

## Sources consulted

**Specs**: [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html), [RFC 9298](https://datatracker.ietf.org/doc/html/rfc9298), [Anthropic messages streaming](https://docs.anthropic.com/en/api/messages-streaming)

**Vendor docs**: [Claude Code enterprise network config](https://code.claude.com/docs/en/corporate-proxy), [gateway protocol reference](https://code.claude.com/docs/en/llm-gateway-protocol), [gateway connect](https://code.claude.com/docs/en/llm-gateway-connect), [other LLM gateways](https://code.claude.com/docs/en/llm-gateway), [Node CLI docs](https://nodejs.org/api/cli.html), [undici Client](https://github.com/nodejs/undici/blob/main/docs/docs/api/Client.md), [undici ProxyAgent](https://undici.nodejs.org/docs/docs/api/ProxyAgent.html), [Codex config reference](https://developers.openai.com/codex/config-reference), [gemini-cli configuration](https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md), [mitmproxy certificates](https://docs.mitmproxy.org/stable/concepts/certificates/)

**Issues/PRs**: [reqwest #2640](https://github.com/seanmonstar/reqwest/issues/2640), [rustup #3400](https://github.com/rust-lang/rustup/issues/3400), [codex #14239](https://github.com/openai/codex/pull/14239), [codex #27706](https://github.com/openai/codex/pull/27706), [codex #6849](https://github.com/openai/codex/issues/6849), [claude-code #41157](https://github.com/anthropics/claude-code/issues/41157), [claude-code #22512](https://github.com/anthropics/claude-code/issues/22512), [claude-code #11660](https://github.com/anthropics/claude-code/issues/11660), [gemini-cli #15543](https://github.com/google-gemini/gemini-cli/issues/15543), [gemini-cli #16173](https://github.com/google-gemini/gemini-cli/issues/16173)

**Ecosystem**: [LiteLLM secret detection](https://docs.litellm.ai/docs/proxy/guardrails/secret_detection), [Helicone proxy-first](https://www.joinnextdev.com/a/helicone/helicones-proxy-first-bet-is-now-infrastructure), [OTel GenAI observability](https://opentelemetry.io/blog/2026/genai-observability/), [OTel GenAI semconv status](https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions), [AI gateways 2026](https://guptadeepak.com/tools/top-5-ai-gateways-2026/)

**Ops/legal**: [SSE through nginx](https://oneuptime.com/blog/post/2025-12-16-server-sent-events-nginx/view), [Germany monitoring law](https://www.employee-monitoring.net/compliance/employee-monitoring-laws-germany), [GDPR employee monitoring](https://secureprivacy.ai/blog/employee-monitoring-gdpr-guide), [macOS notarization](https://docs.bastion.tech/devices/apple/signing-notarizing), [macOS trust stores](https://learnings.bolmaster2.com/posts/add-certificates-to-trust-stores)

## Source quality assessment

High confidence on everything sourced from `code.claude.com/docs` — it is the authority on its own client and is specific about failure modes. RFCs and Node/undici references are definitive. GitHub issues are strong evidence of real enterprise failure modes but are point-in-time.

Weaker: the Codex custom-CA precedence chain comes from a third-party knowledge base corroborated by the linked PRs, not from OpenAI's own docs — re-verify before relying on it. Node's `NODE_USE_ENV_PROXY` version history is internally inconsistent (docs page renders v15.10.0; release notes attribute `fetch()` support to v24.0.0 and `http`/`https` to v24.5.0).

Reddit, HackerNews, and X returned essentially nothing on mandatory agent-traffic capture. The practitioner conversation lives in vendor docs and GitHub issues.

## Open questions

1. Does a null-transform loopback relay actually preserve claude.ai subscription auth end to end? (Decides whether interception is needed at all.)
2. Which Node majors honour `NODE_USE_ENV_PROXY` for `fetch` vs `http.request`?
3. Does the bundled Bun runtime in Claude Code's native installer honour system trust / `NODE_EXTRA_CA_CERTS` on macOS and Linux, or only fail on Windows?
4. Does ALPN actually select h2 for each CLI against its provider?
5. Do Codex and Gemini CLI have background supervisors that bypass a `PATH` wrapper the way Claude Code's does?
6. Is `x-claude-code-agent-id` stable enough to serve as a join key given the fresh-per-spawn vs stable-name-based split?

## Actionable takeaways

- Default to base-URL redirection; treat TLS interception as an explicitly opted-into fallback, not a baseline. It needs no CA, no MDM, no admin rights, and is immune to a future h3 migration.
- Build the relay strictly byte-transparent and encode the documented failure modes (no buffering, verbatim `anthropic-beta`, unmodified bodies, unwrapped errors, unreordered `system`) as tests — three of them fail loudly only on a *future* client release.
- Enroll via managed settings, not a `PATH` wrapper; a wrapper silently misses every background agent.
- Publish the coverage boundary. "Capture of model inference" is defensible; "capture everything" is not.
- Put redaction at the persistence boundary and ship a metadata-only mode from day one.
- Settle the monitoring-law posture before using the word "mandatory" in user-facing copy.

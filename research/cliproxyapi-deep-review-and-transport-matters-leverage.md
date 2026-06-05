---
title: CLIProxyAPI deep review and Transport Matters leverage
type: research
tags:
  - cliproxyapi
  - transport-matters
  - protocol-translation
  - oauth
  - routing
  - capture
summary: Pinned source review of CLIProxyAPI, its value to developers, and the patterns Transport Matters should study, adapt, or avoid.
status: active
source: github-researcher
created: 2026-08-13
updated: 2026-08-13
project: transport-matters
related:
  - agent-cli-provider-vs-harness-taxonomy-2026
  - agent-cli-traffic-capture-protocol-constraints-2026
  - transport-matters-codex-http-fallback-architectural-review
  - unified-transcript-ir-transport-matters
confidence: high
---

# CLIProxyAPI deep review and Transport Matters leverage

## Executive judgment

CLIProxyAPI is a capable local protocol gateway for developers who want one OpenAI compatible endpoint over several model providers, personal subscriptions, OAuth identities, API keys, and account pools. It combines protocol translation, credential selection, retry policy, session affinity, usage normalization, model discovery, management APIs, a terminal interface, plugins, and several storage backends.

Transport Matters should use CLIProxyAPI as a source of protocol fixtures, failure cases, state machine designs, and compatibility tests. It should not become a Transport Matters runtime dependency or credential owner.

The strongest leverage is narrow and practical:

1. Harvest difficult translation fixtures for tools, reasoning, usage, streaming, and terminal errors.
2. Compare its session identity evidence ordering with Transport Matters' explicit run and exchange identity.
3. Study its credential availability and cooldown state machine for a future, separate routing context.
4. Use its model capability vocabulary as an observation source and compatibility canary.
5. Preserve Transport Matters' raw byte truth, provider adapters, runtime homes, audit trail, and ownership boundaries.

The smallest useful experiment is an offline fixture corpus. Pin the reviewed commit, select a dozen high value cases, replay them through Transport Matters adapters, and produce a round trip gap matrix. No proxy integration or real credentials are required.

## Scope and evidence

This review pins CLIProxyAPI at commit [`d757063c967426eaf78a71b1980ebdef5c2299eb`](https://github.com/router-for-me/CLIProxyAPI/tree/d757063c967426eaf78a71b1980ebdef5c2299eb), the `main` head cloned on 2026-08-13. The latest tag at review time was `v7.2.131`.

The review covered:

- repository structure and request flow
- public server, SDK, plugin, storage, and management surfaces
- authentication, account selection, retry, cooldown, and affinity
- request, response, streaming, reasoning, and tool translation
- model catalog and usage accounting
- configuration defaults and operational exposure
- test, build, vet, race, and CI evidence
- current GitHub activity and open issue themes
- comparison with live Transport Matters architecture and ownership

The local clone is at `/Users/alphab/Dev/LLM/DEV/helioy/CLIProxyAPI`.

### Repository scale at the pinned commit

| Measure | Result |
|---|---:|
| Go files | 1,123 |
| Production Go files | 633 |
| Test Go files | 490 |
| Production Go lines | 198,347 |
| Test Go lines | 171,774 |
| Commits | 3,407 |
| Commits in the preceding 30 days | 384 |
| Production Go files above 700 lines | 79 |

The repository had about 47,000 GitHub stars and 7,000 forks at review time. Those values indicate reach, not correctness. The commit and verification results are the reliable evidence boundary.

## What CLIProxyAPI is

CLIProxyAPI is a local gateway with three related jobs:

1. Present familiar client protocols, primarily OpenAI Chat Completions and Responses, Claude, Gemini, Codex, and related compatible routes.
2. Select a provider credential or account and execute the upstream request.
3. Translate request, stream, response, error, reasoning, tool, and usage semantics between protocols.

That makes it useful as a developer access layer and compatibility laboratory. Its core concern is successful execution through a selected upstream identity. Transport Matters has a different core concern: faithful capture, explanation, audit, and controlled intervention around an agent runtime.

### Main architectural areas

| Area | Responsibility | Representative source |
|---|---|---|
| Server entry | Configuration, stores, auth, plugins, watcher, server lifecycle | [`cmd/server/main.go`](https://github.com/router-for-me/CLIProxyAPI/blob/d757063c967426eaf78a71b1980ebdef5c2299eb/cmd/server/main.go) |
| API | Gin routes, protocol handlers, management endpoints | [`internal/api`](https://github.com/router-for-me/CLIProxyAPI/tree/d757063c967426eaf78a71b1980ebdef5c2299eb/internal/api) |
| Authentication | Credential records, selection, retries, cooldown, affinity | [`sdk/cliproxy/auth`](https://github.com/router-for-me/CLIProxyAPI/tree/d757063c967426eaf78a71b1980ebdef5c2299eb/sdk/cliproxy/auth) |
| Executors | Provider specific upstream execution | [`internal/runtime/executor`](https://github.com/router-for-me/CLIProxyAPI/tree/d757063c967426eaf78a71b1980ebdef5c2299eb/internal/runtime/executor) |
| Translation | Pairwise protocol request and response transforms | [`internal/translator`](https://github.com/router-for-me/CLIProxyAPI/tree/d757063c967426eaf78a71b1980ebdef5c2299eb/internal/translator) |
| Reasoning | Canonical reasoning configuration and provider application | [`internal/thinking`](https://github.com/router-for-me/CLIProxyAPI/tree/d757063c967426eaf78a71b1980ebdef5c2299eb/internal/thinking) |
| Session identity | Derivation from headers, bodies, protocol hints, and client signals | [`sdk/cliproxy/session/identity.go`](https://github.com/router-for-me/CLIProxyAPI/blob/d757063c967426eaf78a71b1980ebdef5c2299eb/sdk/cliproxy/session/identity.go) |
| Model registry | Model metadata, aliases, capabilities, remote updates | [`internal/registry`](https://github.com/router-for-me/CLIProxyAPI/tree/d757063c967426eaf78a71b1980ebdef5c2299eb/internal/registry) |
| Hot reload | Configuration and credential change watching | [`internal/watcher`](https://github.com/router-for-me/CLIProxyAPI/tree/d757063c967426eaf78a71b1980ebdef5c2299eb/internal/watcher) |
| Embedding | Service builder and SDK lifecycle | [`sdk/cliproxy`](https://github.com/router-for-me/CLIProxyAPI/tree/d757063c967426eaf78a71b1980ebdef5c2299eb/sdk/cliproxy) |
| Extension | Trusted in process plugins and host callbacks | [`internal/pluginhost`](https://github.com/router-for-me/CLIProxyAPI/tree/d757063c967426eaf78a71b1980ebdef5c2299eb/internal/pluginhost) |

### Simplified request flow

```text
client protocol request
        |
        v
route and protocol handler
        |
        v
credential selection and availability policy
        |
        v
request translation and reasoning application
        |
        v
provider executor
        |
        v
stream, response, error, and usage translation
        |
        v
client protocol response
```

The implementation has protocol specific shortcuts and branches, so the diagram is a mental model rather than a complete call graph.

## How it helps a developer in general

### One local API over several providers

A tool that already speaks OpenAI compatible APIs can target one local endpoint while CLIProxyAPI handles several upstream protocols. This can reduce bespoke client integration work for prototypes, editor extensions, local agents, and model comparison tools.

### Access through existing identities

The repository supports OAuth and API key based accounts, including account pools. This can be convenient for individual development where permitted by the upstream service and account terms. Each provider's terms and automation rules require independent review before operational use.

### Compatibility testbed

The translation matrix contains real handling for:

- messages and content parts
- tool declarations and tool calls
- reasoning controls and reasoning output
- images and live media paths
- streaming event boundaries
- usage and token data
- provider specific errors and terminal events

This makes the repository useful even when the server is never deployed. Its fixtures and edge handling form a map of where apparently compatible APIs differ.

### Account routing and resilience

The authentication manager provides round robin, weighted, and fill first selection, plus retry, cooldown, and session affinity behavior. Developers building their own gateway can study the separation between credential availability, selection policy, and executor behavior.

### Embedding and extension

The Go SDK exposes a service and builder for embedding. Custom providers and trusted plugins add extension points. The checked in SDK documentation is stale at the pinned commit, however. Several guides still reference module version `v6` and Go 1.24, while the module is `v7` and declares Go 1.26. One guide imports an internal package that an external module cannot import. A first time embedder should follow current exported source and examples, then verify every documented import.

### Local operations

The terminal interface, management routes, file watching, configurable stores, usage accounting, and model registry provide a broad operational surface for a local or team gateway. That breadth is also the main complexity cost.

## Strong engineering lessons

### Protocol compatibility is behavioral

Matching endpoint names and JSON shapes is insufficient. Tool call ordering, reasoning blocks, usage timing, stream termination, and upstream error timing affect clients. CLIProxyAPI's breadth reinforces the need for executable conformance fixtures.

### Translation needs an explicit loss model

CLIProxyAPI largely implements pairwise protocol transforms. This provides broad coverage but grows with each protocol pair and can obscure which fields were dropped, synthesized, or reordered. A system designed around auditability should record every lossy decision.

Transport Matters already has a better foundation for this purpose: raw bytes alongside provider adapters and an internal representation. CLIProxyAPI can supply adversarial cases while Transport Matters retains provenance.

### Retry has a semantic commitment boundary

An upstream retry is safe before meaningful output reaches the downstream client. Once tool calls, text, reasoning, or protocol terminal state has been emitted, retrying through a different account can duplicate effects or combine unrelated streams.

Transport Matters should make this boundary observable in captures. If a future routing context owns retry, it should persist the selected credential identity, attempt number, retry cause, and downstream commitment state.

### Credential state is a state machine

Credential selection depends on more than a list of tokens. Disabled state, cooling periods, provider availability, quota signals, model support, health, affinity, and current attempt state all contribute.

This is useful design material for a future routing product context. Credential state should remain outside the capture plane and runtime lifecycle owner.

### Session identity should expose evidence

CLIProxyAPI derives affinity identity from several protocol and client signals. This is practical for a compatibility proxy. Transport Matters already has explicit run, session, exchange, and harness context, so heuristic identity should remain secondary evidence.

An identity record should preserve:

- selected identity value
- evidence source
- precedence rule
- confidence
- collisions or ambiguity
- the raw field used, subject to redaction policy

### Hot reload needs serialized ownership

Configuration and credential watching looks simple until file writes, debounce timers, asynchronous persistence, runtime replacement, and cleanup overlap. CLIProxyAPI's implementation and race results show why reload should have one queue, one owner, and explicit completion semantics.

### Related state should publish as one snapshot

CLIProxyAPI's Home path couples its active control plane client and execution registry in one atomic dispatch bundle. Configuration application is staged before the new bundle becomes visible. This is a strong general pattern for live systems: requests should never observe new policy with old execution state.

Transport Matters can apply the same rule when a launch profile, adapter set, override snapshot, or routing policy changes. Construct and validate the complete generation, then publish one immutable reference.

### Process globals constrain embedding

The token store, model registry, translator registry, and usage manager use process global access in parts of the codebase. The public builder makes embedding possible, but multiple isolated service instances in one process need explicit proof. A developer embedding the SDK should assume one service per process until isolation tests demonstrate otherwise.

### Remote metadata is evidence, not authority

A frequently updated model catalog is useful for discovery and canary checks. It can drift, disappear, or change outside a pinned release. Transport Matters should treat remote capability data as an observed claim. Certification and trust decisions need a versioned local authority.

## Quality and maintainability assessment

### Positive evidence

- The repository has substantial protocol coverage and a large test corpus.
- `go test ./...` passed at the pinned commit.
- `go build ./cmd/server` passed and produced a runnable Darwin ARM64 binary.
- OAuth callback files, configuration paths, and plugin installation include several strong permission, validation, and atomic replacement controls. Default provider token persistence is an important exception described below.
- Recent commits show active correction of security and compatibility problems.
- The MIT license permits reuse with preservation of its notice and license terms.

### Risks and cautions

#### Change velocity

The repository had 384 commits in the preceding 30 days and ten tagged releases from `v7.2.122` through `v7.2.131` between 2026-08-07 and 2026-08-13. Any evaluation or dependency should pin an exact commit or release.

#### Large files and concentrated responsibilities

Seventy nine production Go files exceed 700 lines. Several exceed 1,800 lines. Large server composition, executor, handler, storage, and cooldown modules increase review cost and make ownership harder to see.

This is a concern for direct adoption. It does not erase the value of individual patterns and fixtures.

#### Pairwise translator growth

Pairwise translation provides direct control but creates a combinatorial maintenance surface. New protocols and feature variants multiply request, response, and streaming cases. Transport Matters should avoid importing this matrix into its capture plane.

#### Documentation drift

The SDK version and import issues described above were confirmed against the pinned source. Public source is the safer integration guide until the docs are corrected.

#### Static analysis findings

`go vet ./...` did not pass:

- `request_logger_body_source.go` defines `WriteTo(w io.Writer) error`, which conflicts with the conventional `io.WriterTo` signature expected by vet.
- two plugin host stream paths were reported as possible context cancellation leaks.

The plugin reports need maintainer adjudication because cancellation ownership appears to move into a stream registry. They are analyzer findings, not confirmed production leaks.

#### Race suite findings

Targeted race runs did not pass. Confirmed failures included:

- watcher tests reading state while asynchronous persistence or debounce callbacks write it
- OpenAI handler tests concurrently changing Gin's global mode

These are confirmed test suite races. The evidence does not establish a production data race. It does show that the race validation boundary is not clean.

#### CI verification boundary

The pull request workflow runs `go build`. The reviewed workflows did not provide a repository wide `go test`, `go vet`, race, or static analysis gate. Local passing tests therefore exceed the automated pull request proof visible in the repository.

#### Operational and trust surface

The server can hold valuable OAuth tokens and API keys, expose management APIs, install trusted plugins, update model data, and serve multiple network protocols. Some configuration and code paths also implement client cloaking or identity mutation. These capabilities need explicit security and policy decisions.

The focused security review found six source confirmed boundary defects. No exploit was run, so the claims below are bounded to code behavior at the pinned commit.

| Finding | Source evidence | Effect |
|---|---|---|
| Forwarded client IP headers are trusted without an explicit proxy allowlist | [`internal/api/server.go`](https://github.com/router-for-me/CLIProxyAPI/blob/d757063c967426eaf78a71b1980ebdef5c2299eb/internal/api/server.go) creates the Gin engine without `SetTrustedProxies`; management middleware uses `ClientIP()` | A remote caller can forge a loopback address. A valid management credential is still required, but the remote locality rule and IP keyed abuse controls weaken. |
| Several provider token writers use `os.Create` | Claude, Codex, Kimi, xAI, and Vertex token storage implementations create the final file directly | Requested mode is `0666` subject to umask, and the destination is truncated before encoding completes. Common `022` umask yields a readable `0644` token file. |
| Error logging can retain prompt and translated upstream payloads | Request logging captures error paths even when full request logging is disabled; log files use `0644` and directories use `0755` | Sensitive prompts, tool inputs, output, and provider errors may persist locally with broad account level readability. |
| Home request log forwarding clones raw headers | [`internal/logging/request_logger_home.go`](https://github.com/router-for-me/CLIProxyAPI/blob/d757063c967426eaf78a71b1980ebdef5c2299eb/internal/logging/request_logger_home.go) forwards cloned headers without the text log sanitizer | `Authorization` and related credentials can cross into the Home log payload when the feature is enabled. A checked in test asserts the raw authorization value reaches that payload. |
| HTTP header acquisition has no server deadline or size limit after protocol sniffing | The multiplexer clears its ten second sniff deadline and the `http.Server` has no `ReadHeaderTimeout` or `MaxHeaderBytes` | An exposed deployment can accumulate slow partial header connections and goroutines cheaply. |
| Session affinity has no global entry budget | [`sdk/cliproxy/auth/session_cache.go`](https://github.com/router-for-me/CLIProxyAPI/blob/d757063c967426eaf78a71b1980ebdef5c2299eb/sdk/cliproxy/auth/session_cache.go) bounds aliases per group but not total groups | Authenticated high cardinality identifiers can grow memory until TTL cleanup. |

Two supply chain paths also deserve explicit treatment:

- The management page updater has a fallback that accepts and serves downloaded HTML without digest verification. That page executes in the management origin.
- The main remote model catalog is unsigned and read without a response size bound. `--local-model` disables the remote catalog path.

Other operational concerns include wildcard CORS, an authenticated management API call facility that can act as an SSRF primitive, retry amplification across a large credential pool, and storage backends that persist application readable bearer material. Git storage is especially durable because credentials can enter repository history.

The code also has verified strengths. Management routes require a configured secret. Secret comparison and hashing paths use appropriate primitives. OAuth state has length, character, provider, and expiry validation. Callback writes use restrictive modes. Refresh paths use concurrency control. Retry waits honor cancellation. TLS verification remains enabled in ordinary proxy transport. Plugin archive extraction checks paths and content hashes.

For individual local evaluation:

1. Bind to `127.0.0.1` rather than all interfaces.
2. Replace sample API keys and use strong client authentication.
3. Keep remote management disabled. A protected local network and TLS are insufficient until trusted proxy handling is explicit.
4. Set a restrictive process umask, inspect every persisted token mode, and protect the auth directory and backups.
5. Disable request logging or use only synthetic prompts until every log sink is sanitized and permissions are tightened.
6. Disable plugins, remote control panel updates, and remote model updates unless required.
7. Place an authenticated, rate limited reverse proxy in front of any deliberate remote deployment and enforce header deadlines there.
8. Pin the exact version.
9. Review each provider's current terms before using subscription OAuth through automation.

The sample configuration's empty host can bind broadly. TLS is disabled by default. Remote management is guarded by configuration and secret handling, and sample keys trigger a protective safe mode. Those protections do not replace explicit local hardening.

The practical security verdict is conservative: keep the service on a trusted host until forwarded IP handling, token persistence, secret logging, inbound header limits, and management asset provenance are corrected.

## Comparison with Transport Matters

| Concern | CLIProxyAPI | Transport Matters | Decision |
|---|---|---|---|
| Primary purpose | Execute through a unified provider gateway | Capture, inspect, audit, and intervene around agent runs | Preserve separate purposes |
| Source of truth | Translated request and selected upstream execution | Raw wire artifacts plus parsed internal request and audit data | Preserve Transport Matters ownership |
| Credentials | Central pools, OAuth refresh, cooldown, selection | Runtime specific homes and launch context | Do not centralize in capture |
| Translation | Pairwise protocol conversion | Provider adapters parse and reconstruct observed traffic | Use fixtures, keep raw provenance |
| Session identity | Heuristics from protocol and client signals | Explicit run, session, exchange, harness, and launch identity | Study precedence only |
| Retry | Gateway policy tied to credential availability | Captured behavior today, possible future routed behavior | Model separately with commitment evidence |
| Model metadata | Dynamic registry and updater | Provider and harness evidence, certification needs | Use as a canary, not authority |
| Plugins | Trusted in process extension ABI | Deliberate product contexts and services | Defer |
| Storage | Filesystem, Git, Postgres, object stores | Postgres session data plus raw capture artifacts and product stores | Avoid transplanting stores |
| UI | Management API, web panel, terminal UI | Canvas, desktop, and product interfaces | Learn from operations, do not transplant |

### Current Transport Matters owners

- `ProviderAdapter` in `api/src/transport_matters/adapters/base.py` owns provider byte parsing and reconstruction.
- `SharedProxyManager` in `api/src/transport_matters/shared_proxy/manager.py` owns the shared mitmproxy process and per run bindings.
- `OverrideStore` remains the mutation owner for captured request changes.
- `RunManager` in `packages/runtime/src/service/RunManager.ts` owns runtime launch and lifecycle concerns.
- Raw request, curated request, audit, response, and wire artifacts provide the evidence chain.

Any adopted pattern must enter through one of these owners or a deliberately created product context. A second proxy, credential cache, clock, model authority, or retry loop would create parallel ownership.

## Adopt, adapt, study, reject

### Adopt as source material

#### Translation and conformance fixtures

Harvest cases for:

- reasoning configuration and replay
- tool schema and tool call transformation
- stream terminal events
- upstream errors before and after downstream commitment
- usage normalization
- images and multipart content
- session identity signals

Copy only the minimum fixture data or logic needed. Record the source commit and preserve the MIT notice where required.

#### Explicit credential availability vocabulary

The vocabulary around enabled, unavailable, cooling, exhausted, model incompatible, selected, retried, and affinity bound is useful for a future routing state model.

#### Model capability observation

Use catalog changes as inputs to compatibility probes. Compare claimed features with captured behavior before updating any trusted model profile.

#### Usage quality states

CLIProxyAPI distinguishes subset, independent, separate reasoning, unclassified, and other token accounting shapes. Transport Matters should adapt that vocabulary inside its existing exchange statistics owner. Keep raw provider fields, record the normalization rule, and prevent totals from being counted twice.

### Adapt to Transport Matters boundaries

#### Loss annotated translation

For each adapter transformation, emit structured facts such as:

- source path
- destination path
- preserved, normalized, synthesized, or dropped
- reason
- adapter version

CLIProxyAPI's edge cases can populate the tests. Transport Matters should retain the audit shape.

#### Commitment aware attempts

Represent an attempt with explicit phases:

```text
selected -> dispatched -> upstream accepted -> downstream committed -> terminal
```

Only a separate routing owner may create a replacement attempt. The capture plane records the attempt and commitment evidence.

#### Identity evidence chain

Adapt the precedence lessons while preferring explicit Transport Matters identifiers. Heuristic identifiers should remain labeled and reviewable.

#### Serialized reload queue

If Transport Matters needs live profile or adapter reload, use a single serialized queue with debounce, generation numbers, cancellation ownership, and tests that await completion.

### Study before any implementation

- usage normalization across streaming and nonstreaming paths
- provider cooldown interpretation
- account affinity collision behavior
- WebSocket and live media semantics
- plugin lifecycle and cancellation ownership
- failure behavior when model metadata changes during a run
- management authentication and network exposure

### Reject for current Transport Matters scope

- embedding CLIProxyAPI as a required runtime service
- moving OAuth credentials into the capture plane
- replacing provider adapters with a pairwise translator matrix
- making a remote model catalog authoritative
- copying its Git or object credential stores
- introducing its plugin ABI before a concrete extension need exists
- client cloaking, identity confusion, or silent protocol mutation
- adding a second management interface or terminal interface
- adding live media relay before the ordinary request capture loop is complete

## Recommended Transport Matters experiment

### Goal

Measure concrete Transport Matters adapter gaps using CLIProxyAPI's hardest protocol cases, without introducing a runtime dependency.

### Inputs

- CLIProxyAPI commit `d757063c967426eaf78a71b1980ebdef5c2299eb`
- 10 to 12 MIT sourced fixtures
- current Transport Matters provider adapters
- existing raw, curated, audit, response, and wire artifact formats

### Fixture selection

Select at least two cases from each group:

1. reasoning configuration and reasoning output
2. tool declarations, calls, and results
3. stream terminal and error behavior
4. usage and token normalization
5. identity or affinity signals
6. multimodal content if current adapters claim support

### Execution

1. Copy or reconstruct each fixture as ordinary JSON or text.
2. Add source commit, source path, license, protocol, and expected behavior metadata.
3. Parse each request through the current `ProviderAdapter`.
4. Serialize the internal request back to provider bytes.
5. Compare source, internal form, reconstructed output, and audit facts.
6. Repeat for response and stream fixtures where the adapter supports them.
7. Record every preserved, normalized, synthesized, reordered, and dropped field.
8. Produce a gap matrix ranked by user visible effect and implementation cost.

### Pass criteria

- every fixture has pinned provenance
- replay is offline and deterministic
- no real provider credential is required
- original bytes remain available
- every lossy transform is visible
- failures identify one current owner
- no second proxy, credential cache, or model registry is introduced

### Expected output

| Fixture | Protocol path | Result | Loss | User effect | Owner | Next action |
|---|---|---|---|---|---|---|
| Example | Responses to internal request | pass | reasoning summary normalized | low | ProviderAdapter | document |

This experiment is small enough to judge. A successful result gives Transport Matters a reusable compatibility corpus and a measured roadmap.

### Optional sandbox after the offline experiment

Run CLIProxyAPI against a synthetic local upstream and capture the exchange through Transport Matters. Use fabricated credentials and deterministic responses. This can test redirects, streaming, errors, and mutation visibility without provider policy or secret exposure.

## Decision guide

Use CLIProxyAPI directly when the problem is local unified access to several providers and the operator accepts its credential, translation, and trust model.

Use it as a reference when building protocol tests, routing state, usage normalization, or compatibility probes.

Keep it outside Transport Matters when the requirement is faithful provenance, raw traffic truth, explicit runtime identity, explainable mutation, or a single owner for credentials and scheduling.

## Verification record

Commands were run from the clean pinned clone.

| Check | Result |
|---|---|
| `git status --short --branch` | clean `main` tracking `origin/main` |
| `go test ./...` | pass |
| `go build -o <temporary-path> ./cmd/server` | pass |
| built binary inspection | Darwin ARM64 executable, about 77 MB |
| temporary binary removal | complete |
| `go vet ./...` | fail, three findings described above |
| targeted `go test -race` | fail, confirmed test races described above |
| source file and line inventory | complete |
| current pull request workflow inspection | build gate confirmed, broader gates absent |

The Transport Matters repository remained unmodified during review. The CLIProxyAPI clone remained clean after verification.

## Sources and related research

### Primary sources

- [CLIProxyAPI pinned repository](https://github.com/router-for-me/CLIProxyAPI/tree/d757063c967426eaf78a71b1980ebdef5c2299eb)
- [README](https://github.com/router-for-me/CLIProxyAPI/blob/d757063c967426eaf78a71b1980ebdef5c2299eb/README.md)
- [Configuration example](https://github.com/router-for-me/CLIProxyAPI/blob/d757063c967426eaf78a71b1980ebdef5c2299eb/config.example.yaml)
- [Go module declaration](https://github.com/router-for-me/CLIProxyAPI/blob/d757063c967426eaf78a71b1980ebdef5c2299eb/go.mod)
- [Pull request build workflow](https://github.com/router-for-me/CLIProxyAPI/blob/d757063c967426eaf78a71b1980ebdef5c2299eb/.github/workflows/pr-test-build.yml)
- [License](https://github.com/router-for-me/CLIProxyAPI/blob/d757063c967426eaf78a71b1980ebdef5c2299eb/LICENSE)

### Local Transport Matters research

- `~/.mdx/research/agent-cli-provider-vs-harness-taxonomy-2026.md`
- `~/.mdx/research/agent-cli-traffic-capture-protocol-constraints-2026.md`
- `~/.mdx/research/transport-matters-codex-http-fallback-architectural-review.md`
- `~/.mdx/research/unified-transcript-ir-transport-matters.md`

### Focused review workpapers

The supporting architecture and security and operations workpapers live under `~/.mdx/projects/cliproxyapi-*.md`. The focused Transport Matters comparison was incorporated directly into this document. This document is the standalone synthesis and decision surface.

## Final recommendation

Treat CLIProxyAPI as a rich external test corpus and reference architecture. Begin with the offline fixture experiment. Defer integration, credentials, plugins, stores, and management surfaces until a measured Transport Matters gap requires one of them and the existing owner cannot satisfy it cleanly.
| Vet and race boundary | not clean; findings remain documented in the main research body |
| Repository modification | neither repository was modified |

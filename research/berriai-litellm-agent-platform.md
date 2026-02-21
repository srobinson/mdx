---
title: BerriAI/litellm-agent-platform review for runtime-matters + session-matters + identity-matters
type: research
tags: [github-review, litellm-agent-platform, agent-sandbox, runtime-matters, session-matters, identity-matters, vault-sidecar, k8s-crd, kubernetes-sigs, mit, apache-2.0, typescript, go]
summary: Production-shaped TypeScript + k8s reference for the runtime/session/identity split Helioy is building. Vault MITM, image snapshotting, single-shot diagnose, WS PTY attach, agent-sandbox CRD consumption all transfer as shape, not code.
status: active
source: github-researcher
confidence: high
created: 2026-05-17
updated: 2026-05-17
---

## Stats

**BerriAI/litellm-agent-platform** (https://github.com/BerriAI/litellm-agent-platform). MIT, 135 stars, 10 forks, default branch `main`. Created 2026-05-07, last push 2026-05-16: ten days old at review time. Four authors in git log (Ishaan Jaff x2, ishaan-berri, Krrish Dholakia) which is the Berri founding pair plus a bot account. ~12k LOC TypeScript across `src/` (Next.js 16 App Router) + `harnesses/` (five harness images) + `vault/` (sidecar) + `cli/` (the `lap` binary). CI: two workflows on PR (typecheck, zizmor) plus a manually triggered EKS deploy. License is the bare 11-line MIT (no CLA, no patent grant, no contributor terms). Velocity is extreme: 20+ merged PRs in the last 7 days, every commit is a self-contained change with an explanatory message.

**kubernetes-sigs/agent-sandbox** (https://github.com/kubernetes-sigs/agent-sandbox). Apache-2.0, 2.2k stars, 271 forks, default branch `main`. Created 2025-08-12, last push 2026-05-16: nine months old, active. 50+ unique authors, formal Kubernetes CLA required (Copilot suggestions explicitly blocked because they break CLA attribution), SIG Apps governance, kubernetes-style OWNERS file. Go module `sigs.k8s.io/agent-sandbox`. Six GitHub workflows including KEP toc-update, release, and PyPI publish. Python SDK lives at `clients/python/agentic-sandbox-client/`. ~9k LOC of controller code (sandbox + claim + warmpool + template) under `controllers/` and `extensions/controllers/`.

## Grade

**A−** for `litellm-agent-platform`. The prediction holds and is grounded: the shape of the seven-product family is already implemented in TypeScript by people who do not know it exists. Vault MITM, image snapshot at agent-creation, single-shot diagnose, WebSocket PTY attach, warm-pool semantics, agent-sandbox CRD as the runtime substrate. Code quality is high (constant-time token compare, explicit timing budgets, named failure codes with recommended actions, header-vs-query auth duality with documented "AWS ALB strips Authorization" rationale). The deductions from a full A: stack mismatch (TS + Next.js + Prisma vs Helioy's Rust 2024 + smd/rtmd daemons), no MCP anywhere, identity-matters collapsed into the same process as session-matters, no separation between persona and runtime-image. Borrow the shapes, not the code.

**B+** for `kubernetes-sigs/agent-sandbox`. SIG-Apps quality, four-CRD family with clean separation of concerns, full Python SDK with router gateway, but the controller code itself is Go and not borrowable (invariant 9: Rust 2024). The grade is for it as a CRD contract to consume, not as a borrow target.

## Underlying primitive: kubernetes-sigs/agent-sandbox

This is the foundation `lap` builds on, and the foundation Helioy's runtime-matters should target when it gets to k8s deployment.

### CRD family

Four resources, three groups:

- **`Sandbox`** (`agents.x-k8s.io/v1alpha1`, `api/v1alpha1/sandbox_types.go:230`). The atomic unit. Carries a `PodTemplate` plus `VolumeClaimTemplates`, `Lifecycle` (shutdownTime + shutdownPolicy: Delete | Retain), `Replicas` (0 or 1 only, enforced via kubebuilder validation), optional `Service` boolean for headless service auto-creation. Status surfaces `ServiceFQDN`, `PodIPs`, and a conditions array (Ready, Suspended, Finished). Stable hostname per Sandbox is the design centrepiece. This is what `lap` writes directly. Sandbox CRD is also designed for runtimeClass swap (gVisor, Kata) without API breakage.
- **`SandboxTemplate`** (`extensions.agents.x-k8s.io/v1alpha1`, `extensions/api/v1alpha1/sandboxtemplate_types.go`). Reusable parameterised Sandbox blueprint. Adds `NetworkPolicyManagement` (Managed | Unmanaged) and `EnvVarsInjectionPolicy` controls so the template owner can restrict what a downstream Claim is allowed to override.
- **`SandboxClaim`** (`extensions/api/v1alpha1/sandboxclaim_types.go`). User-facing thin abstraction: requests a Sandbox from a Template, optionally subject to a `WarmPoolPolicy` ("none" | "default" | "<pool-name>"). Adopts an existing warm sandbox if one matches. Carries `AssignedSandboxNameLabel` once bound. This is the layer end users would normally write.
- **`SandboxWarmPool`** (`extensions/api/v1alpha1/sandboxwarmpool_types.go`). HPA-scalable pre-warmed pool keyed on a `SandboxTemplateRef`. Two update strategies: `Recreate` (delete stale pods immediately) or `OnReplenish` (replace only when claimed). The kubebuilder scale subresource is wired so HPAs can drive `replicas` directly.

### Controller pattern

Single-binary controller manager at `cmd/manager/` runs the Sandbox controller (`controllers/sandbox_controller.go`, 1150 LOC) plus the three extensions controllers (`extensions/controllers/sandbox{claim,template,warmpool}_controller.go`, ~2300 LOC of controller logic total). Standard controller-runtime: Reconcile loops watch their CRD, materialise pods + services + PVCs with `controllerRef` ownership and finalizers, surface ready/suspended/finished conditions, hash the PodTemplate for deterministic re-roll. Test coverage is heavy: `extensions/controllers/sandboxclaim_controller_test.go` alone is 3587 LOC.

### Python SDK

`clients/python/agentic-sandbox-client/k8s_agent_sandbox/`. Four connection modes (Production gateway, Tunnel via `kubectl port-forward`, In-Cluster direct pod IP, Advanced custom URL). `Sandbox` class exposes `commands` (CommandExecutor) and `files` (Filesystem) abstractions, OpenTelemetry-instrumented (`trace_manager.py`). Built around a `SandboxConnector` indirection so the four modes are pluggable. Async variant available (`async_sandbox_client.py`).

### Should runtime-matters target this CRD?

Yes. Helioy invariant 6 (K8s-as-principle) plus invariant 9 (Rust 2024) means runtime-matters should:

1. **Consume the CRD via API**, not fork it. Write Sandbox CRs from `rtmd` using the official Go-generated OpenAPI schema (Rust client via `kube-rs`). The CRD is stable enough that `lap` ships against a pinned `v0.4.5` and tracks releases.
2. **Skip the Python SDK.** The SDK is a coupling Helioy does not need; `rtmd` is the daemon shape, not a client library.
3. **Borrow the four-resource decomposition.** Sandbox = single pod runtime, Template = persona, Claim = user request, WarmPool = pre-spawn. This maps cleanly onto agent-matters (PodSpec) + identity-matters (RBAC-bound user identity) + session-matters (the Claim equivalent). The names are wrong for Helioy but the cuts are right.
4. **Pin to a release tag.** The CRD is v1alpha1; agent-sandbox is pre-1.0 and explicitly developing toward Beta/GA. Pin per Helioy release. The roadmap signals "Strict Sandbox-to-Pod Mapping" (issue 127) is still in progress — runtime-matters cannot assume strict 1:1 today.
5. **Do not import the controller code.** Go + controller-runtime. Helioy's controllers live in orchestration-matters (`om`) per the seven-product table, which is its own thing.

The mental model: agent-sandbox sits between Helioy's runtime-matters and the kubelet, just as kubelet sits between agent-sandbox and the container runtime. Runtime-matters owns "boot the agent here on this host", agent-sandbox owns "give me one stable singleton pod with persistence".

## Primitives that transfer

1. **Vault sidecar MITM credential pattern.** `vault/src/server.ts` is a 482-line HTTPS forward proxy that reads `REAL_<KEY>` env vars at boot, mints fresh `stub_xxx` strings, writes `KEY=stub_xxx` to `/lap-shared/env` for the harness to source, then MITMs every CONNECT with on-demand leaf certs (`vault/src/server.ts:220-256`), scans request headers + text-y bodies for stubs, swaps them, forwards. Leaf cert lifetime is 24h with 30-min pre-expiry refresh. Inspect endpoint gated by `HMAC(MASTER_KEY, HOSTNAME)` so a hostile pod on the cluster network cannot exfiltrate stubs. Egress allow/deny lists parsed at boot from `EGRESS_ALLOW_OUT` / `EGRESS_DENY_OUT` (CIDR + wildcard + exact). **Lands in identity-matters (`im`).** The cleanest mapping: `im` is the per-session secret broker; the sidecar is `im`'s pod-side delegate. Operational cost is real (CA cert distribution, MITM compatibility with TLS pinning libraries, gRPC payload skipped because `content-encoding` is not identity) but contained.

2. **Image snapshot at agent-creation.** `src/app/api/v1/managed_agents/agents/route.ts:158` writes `task_definition_arn: resolveHarnessImage(harness_id, env)` into the Agent row. Existing agents keep their image even after `K8S_HARNESS_IMAGE*` env vars change. **Lands in agent-matters (`agm`).** Maps directly onto the immutability principle: an agent is a snapshot of (persona + runtime image) at creation time, addressable by stable ID. The hard rule: changing `agm` config does not retroactively rewrite existing agents.

3. **Single-endpoint diagnose super-bundle.** `src/app/api/v1/managed_agents/sessions/[session_id]/diagnose/route.ts:547` fans out 9 parallel reads (session row, agent row, Pod, Sandbox CR, NodePort Service, pod logs tail 200, node, pods-on-node, prepull DaemonSet, warm-pool counts, direct harness HTTP probe via node ExternalIP) with per-call `Promise.race` timeouts of 15s, runs a deterministic 8-rule detector (`detectIssues` at line 395), returns one JSON. Detection codes (`route.ts:407-538`): `dead_node_assigned`, `stale_node_host_cache_suspect`, `pod_image_pull_backoff`, `pod_not_ready_old`, `harness_unreachable`, `node_oversubscribed`, `service_missing`, `warm_pool_empty_for_agent`. Each carries severity + recommended_action. **Lands in session-matters (`sm`).** `sm diagnose <session>` is the obvious kubectl-shaped command. Borrow the multi-stage fan-out pattern (stage 1: independent k8s reads; stage 2: reads that depend on stage 1's `nodeName`; stage 3: harness probe via the resolved ExternalIP bypassing the in-process cache). The detector pattern (named codes, severity, recommended action) is reusable as `sm`'s diagnostic taxonomy.

4. **WebSocket PTY attach with ALB header workaround.** `cli/bin/lap.mjs:509` (`attachPty`) opens a `ws://` connection, sends the token both as `?token=` query and `Authorization: Bearer` header because "AWS ALB / Classic ELB silently strip custom request headers (including Authorization) on WebSocket upgrade requests" (verified against EKS ELB ingress). Sends `{type:"resize", cols, rows}` JSON on open and on stdout resize, raw keystrokes otherwise. WS ping every 30s to defeat AWS ELB's 60s idle timeout. Ctrl-D detaches without killing the remote process. On WS close prints `code=` + `reason=` so 1006 (abnormal ALB drop), 1001 (going away), 1008 (auth) are debuggable. Harness side at `harnesses/claude-code/server.js:148-184` wraps the agent in `tmux new-session -A -s lap CMD` so the PTY persists across WS reconnects (the killed pty is the tmux *client*, not server). **Lands in session-matters (`sm`).** The `sm attach` command for long-lived sessions, plus the tmux wrapper trick for orchestration-matters warroom panes that need reconnection survival.

5. **Diagnostic ring buffer + HMAC-gated inspect endpoint.** `vault/src/server.ts:104-296` keeps the last 100 interceptions in memory (timestamp, method, host, path, swapped stub names, real-value fingerprint with last-2-chars only), exposed at `/interceptions` gated by `HMAC(MASTER_KEY, HOSTNAME)` with `timingSafeEqual` comparison. Reset endpoint at `/interceptions/reset`. **Lands in transport-matters (`tm`).** Wire-level observation is exactly `tm`'s mandate. The fingerprint design (don't leak the credential prefix, expose just enough to confirm "vault swapped the right one") is a model for `tm`'s on-the-wire visibility primitives.

6. **`SELECT ... FOR UPDATE SKIP LOCKED` warm claim.** `src/server/warmPool/index.ts:60` issues raw SQL: claim the oldest warm task for an agent inside a transaction with `FOR UPDATE SKIP LOCKED`, ensuring concurrent double-click claims cannot hand out the same task twice (loser gets null, falls through to cold path). **Lands in orchestration-matters (`om`) and session-matters (`sm`).** Helioy's controllers need this pattern wherever multiple consumers race for a pre-warmed resource. The companion `markClaimedTaskDead` / `deleteClaimedWarmTask` lifecycle is the right shape for warm-pool consumption.

7. **Per-pod auth token, derived deterministically.** `src/server/k8s.ts:57` derives the vault inspect token as `HMAC(MASTER_KEY, task_arn)` so both the platform and the vault can compute the same value without out-of-band shared state. The harness auth token (`HARNESS_AUTH_TOKEN`, `harnesses/claude-code/server.js:55-66`) gates the `/tty` upgrade with `verifyClient` so an unauthenticated client never sees the PTY. **Lands in identity-matters (`im`).** Use the HMAC-of-stable-identifier pattern wherever Helioy needs symmetric derivation without a key exchange step.

8. **Multi-stage CA bundle construction at boot.** `harnesses/_shared/entrypoint-common.sh:35-65` builds a combined CA bundle (vault CA + system CAs) because Python's `ssl` library rejects a glued bundle without a `\n` between cert blocks (`-----END CERTIFICATE----------BEGIN CERTIFICATE-----` on one line fails PEM parsing). Exports `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`, `GIT_SSL_CAINFO` at the combined path. **Lands in runtime-matters (`rtm`).** Every runtime that boots into a vault-MITM'd network needs this exact bundle composition; the comment chain in the file is the canonical reference.

9. **`agent_templates.json` + `agent-templates/` dir split.** Single JSON file at repo root describes templates (id, name, prompt, harness_id, model, tools, requirements, env_vars, skill_file, files). The `files` array references template-relative paths in `agent-templates/<id>/`, which the loader base64-encodes into `LAP_FILE_N_*` env vars at startup; the harness entrypoint writes them to `sandbox_path`. Underscore-prefixed ids are ignored (used for `_sample` docs entry). **Lands in agent-matters (`agm`).** The split between "metadata as JSON" and "binary content as directory" is the right shape for persona definitions. The base64-into-env trick is a useful escape hatch when the runtime layer cannot mount volumes.

10. **Three-tier env precedence with explicit deletion.** `src/server/k8s.ts:397` documents and enforces "passthrough → per-session env_vars → required base → explicit deletion". Concretely: `delete merged["LITELLM_API_KEY"]` after the spread because `containerEnvPassthrough` could reintroduce it via `CONTAINER_ENV_LITELLM_API_KEY`. The AGENTS.md trap is documented at `AGENTS.md:18`: "After merging containerEnvPassthrough into the harness env, explicitly `delete merged["KEY"]` for any key that must be vault-stubbed." **Lands across runtime-matters and identity-matters.** Helioy's daemons will eventually want this exact precedence model; codify it now so future contributors do not regress.

11. **Hot-path session cache with deferred writeback.** `src/server/sessionCache.ts` (referenced from `docs/k8s-backend.md`): process-local `Map<session_id, SessionCacheEntry>` on the read side, plus a `Map<session_id, Date>` for `last_seen_at` flushed every 5s in a single transaction. Removes 350ms of Neon RTT per message. Soft cap of 10k entries with oldest-first eviction. **Lands in session-matters (`sm`).** The flush-interval (5s) being 3 orders of magnitude under the idle timeout (24h) is the design principle. Helioy's `smd` will face this exact pressure when it grows beyond toy workloads.

12. **TCP-level reverse proxy for WS upgrades.** `server-proxy.mjs` (402 LOC) sits in front of the Next.js standalone server because "Next.js 16 App Router route handlers don't support WS upgrades (the connection closes after the response is generated)". Intercepts upgrades bound for `/api/v1/managed_agents/sessions/<id>/tty`, validates the `?token=` against `HARNESS_AUTH_TOKEN` or `MASTER_KEY` with `timingSafeEqual`, pipes the raw TCP connection to the sandbox pod. **Lands in transport-matters (`tm`).** This is a generalisable pattern: any framework that owns the response lifecycle (Next.js, axum's `Router`, FastAPI) will fight WS upgrades, and bypassing at TCP is the escape hatch. Helioy's `tm` should own the TCP-level upgrade routing rather than burying it in the application layer.

## Does NOT transfer

1. **TypeScript + Next.js 16 + Prisma + Neon stack.** Helioy invariant 9 is Rust 2024. The application code does not port; only the shapes do. Specifically: the `src/server/k8s.ts` 1282-line module is a TS port of an earlier Python (`litellm/proxy/managed_agents_endpoints/`); the reconcile.ts header even says "Ported from litellm/proxy/managed_agents_endpoints/lifecycle.py". This is a moving target inside Berri's own stack, which is a warning sign about reuse: if Berri itself rewrote it once, the line-by-line code is not the asset.

2. **Identity-matters collapsed into the platform process.** `lap` runs auth (`src/server/auth.ts`), session state, k8s client, vault config, all in the same Next.js process. Helioy invariant 7 separates identity-matters into its own product. Do not borrow the colocation: it is what forces the explicit-deletion env trap (primitive 10) to exist in the first place. With `im` as a separate daemon, the trap disappears because the harness env never sees `containerEnvPassthrough` from the same process tree.

3. **No MCP anywhere.** The harnesses ship `claude-code`, `codex`, `hermes`, `opencode`, `claude-agent-sdk` and none of them expose MCP. The platform's "tools" are static strings in `agent_templates.json`. Helioy invariant 5 says daemons ARE MCP servers; `lap`'s harness contract (`POST /session`, `GET /session/:id/message`, `POST /session/:id/abort`, SSE `/event`, WS `/tty`) is a custom HTTP+WS protocol that does not align. Do not port the contract.

4. **NodePort + ExternalIP host-side routing.** The platform routes traffic via per-pod NodePort Services because kind clusters do that cleanly. The 30000-30099 window caps concurrent sandboxes at 100; the production EKS path inherits the same model. This is `lap`'s scaling ceiling and `docs/k8s-backend.md` calls it out: "For higher fan-out, swap to a ClusterIP + ingress topology — out of scope for this iteration." Helioy should use the agent-sandbox `headless Service` + `ServiceFQDN` path (set `Sandbox.spec.service: true`) and route via DNS, not NodePort. agent-sandbox already exposes a stable per-Sandbox hostname; use it.

5. **Direct `Sandbox` CR writes, skipping `SandboxClaim`.** `lap` writes `Sandbox` CRs directly from `runTask` and only references the extensions CRDs for warm pools. This is fine for `lap`'s simpler model but skips the value of `SandboxClaim`'s template-bound provisioning. Helioy's `om` should write `SandboxClaim`, not `Sandbox`, so warm-pool adoption is automatic and the template owner controls env-var injection policy.

6. **In-repo CA cert (`vault/ca.crt`).** The vault ships a checked-in CA. Even with the explanation that it gets replaced by the cluster CA at deploy time, a default-trusted MITM cert in a public repo is a footgun. Helioy's `im` must mint the CA at install time per environment and never commit one.

## Verdict

**Inspiration.** Wrong stack to borrow code from, right shape to learn from. The architectural decisions (vault MITM, image snapshot, single-shot diagnose, agent-sandbox CRD as runtime substrate, warm-pool lifecycle, WS PTY attach with reconnection survival via tmux) are unusually well-aligned with the seven-product family Helioy locked yesterday. The implementations are TypeScript + Next.js and do not port. The right move is to read this codebase as a working reference whenever a Helioy product needs to decide a question this team already answered: read their answer, evaluate it, then implement the Helioy version in Rust.

## Why

Berri implemented the seven-product family without naming it. They reach for vault because credential isolation is a hard requirement when agents run with `bypass-permissions: on`; they reach for image snapshot because users get angry when their agents change behaviour under them; they reach for a single-shot diagnose because real operators get paged at 3am and need one URL. These pressures are not Berri-specific: they will hit Helioy in the same order. The asset is the prior art on what specifically broke and how the team fixed it, captured in the comments. `vault/src/server.ts:200-217` explains why PKCS#1 keys fail with an opaque error and how to remediate. `harnesses/_shared/entrypoint-common.sh:48-60` explains why concatenating PEM files without a newline breaks Python's `ssl`. `cli/bin/lap.mjs:511-520` explains why the WS auth token must travel as both header and query. These are months of operator pain compressed into comments. Helioy can skip the operator pain by reading them now.

## How to apply

Concrete next steps, named against the seven products.

- **agent-matters (`agm`).** Codify image snapshot at agent-creation time as an `agm` invariant: an agent is `(persona, runtime image, env shape, secrets shape)` snapshotted at create, addressable by stable UUIDv7. Steal the `agent_templates.json` + `agent-templates/` directory split as the persona file layout: metadata in JSON, binary content (settings files, skill markdown, etc.) on disk relative to the template directory.
- **identity-matters (`im`).** Build the vault MITM as the `im` pod-side delegate. Per-session leaf certs minted on demand. CA distributed via volume mount, never committed. HMAC-derived inspect tokens for any debug surface that reaches across a cluster network. Codify the explicit-delete env merge as a test invariant: a passthrough env var must never reintroduce a vault-stubbed key.
- **session-matters (`sm`).** Implement `sm diagnose <session>` as the kubectl-shaped equivalent of `lap`'s diagnose endpoint. Lift the multi-stage fan-out pattern: stage 1 parallel reads, stage 2 reads dependent on stage 1, stage 3 health probes via resolved addresses that bypass in-process caches. Lift the named-code detector pattern with severity + recommended_action; add Helioy-specific codes (e.g. `am_write_failed`, `cm_scope_mismatch`). Build the WS attach in `sm attach <session>`; send the token both as query and header from day one.
- **runtime-matters (`rtm`).** Target the agent-sandbox `SandboxClaim` (not `Sandbox`) so warm-pool adoption is automatic. Use the Python SDK as a reference for the connection-mode taxonomy (gateway / tunnel / in-cluster / advanced) but write the Rust client against the CRD directly using `kube-rs`. The kubelet boundary contract: `rtmd` writes `SandboxClaim`, agent-sandbox owns the pod lifecycle, `rtmd` reads `Sandbox.status` for readiness. Pin agent-sandbox to a release tag; track the strict 1:1 mapping issue (kubernetes-sigs/agent-sandbox#127) because it is on the path to GA. Build the multi-stage CA bundle composer into `rtmd`'s boot path.
- **orchestration-matters (`om`).** Steal the `SELECT ... FOR UPDATE SKIP LOCKED` warm-claim pattern. `om` controllers will face the same race whenever multiple users claim a warmed resource concurrently. Build the warm-pool lifecycle on `SandboxWarmPool` rather than reimplementing it.
- **workflow-matters (`wm`).** Out of scope for this review; `lap` does not implement workflows.
- **transport-matters (`tm`).** Build the diagnostic ring buffer + HMAC-gated inspect endpoint as a `tm` primitive. Own the TCP-level WS upgrade routing so application frameworks (axum, actix) do not have to fight it. Lift the credential-fingerprint pattern: expose enough to confirm a swap happened without leaking the prefix.

Two cross-cutting reads to schedule next:

1. **agent-sandbox controller code walkthrough.** Specifically `controllers/sandbox_controller.go` (1150 LOC) and `extensions/controllers/sandboxclaim_controller.go` (1557 LOC). Helioy's `om` controllers will reach for the same controller-runtime patterns. Skip code, study the Reconcile structure, hash-based template re-roll, condition machinery, finalizer ordering.
2. **`lap` ground truth for the v0 spec.** The `docs/k8s-backend.md` spawn-time breakdown (~115ms runTask, ~1-2s waitRunningGetUrl, ~8-11s waitHttpReady cold) is the only empirical cold-start data in scope. The 5/16 baseline spec assumes much faster numbers; reconcile against this.

## Sources Consulted

- `README.md`, `AGENTS.md`, `LICENSE`, `docs/k8s-backend.md`, `docs/lap-cli.md`
- `vault/src/server.ts` (482 LOC, entire file)
- `src/server/k8s.ts` (1282 LOC, focus on `buildContainerEnv`, `buildVaultEnv`, `runTask`)
- `src/server/reconcile.ts` (603 LOC, focus on warm orphan sweep + stuck creating watchdog)
- `src/server/warmPool/index.ts` (360 LOC)
- `src/server/harness.ts`
- `src/server/sessionCache.ts` (referenced from docs)
- `src/app/api/v1/managed_agents/sessions/[session_id]/diagnose/route.ts` (881 LOC, entire file)
- `src/app/api/v1/managed_agents/agents/route.ts` (focus on `task_definition_arn` snapshot)
- `harnesses/_shared/entrypoint-common.sh`
- `harnesses/claude-code/server.js` (WS PTY attach, tmux wrapper)
- `cli/bin/lap.mjs` (711 LOC, focus on `attachPty`)
- `server-proxy.mjs` (TCP-level WS upgrade routing)
- `agent_templates.json`, `agent-templates/README.md`
- `k8s/sandbox-warm-pool-example.yaml`
- agent-sandbox: `README.md`, `roadmap.md`, `api/v1alpha1/sandbox_types.go`, `extensions/api/v1alpha1/sandbox{template,claim,warmpool}_types.go`, `controllers/sandbox_controller.go` (skim), `clients/python/agentic-sandbox-client/README.md`, `clients/python/agentic-sandbox-client/k8s_agent_sandbox/sandbox.py`
- Git history: 50 commits on `lap`, 23 unique contributors on agent-sandbox

## Open Questions

1. **SandboxClaim vs direct Sandbox writes.** Why did `lap` choose direct? Comment trail in `src/server/k8s.ts` does not explain. Worth asking on `#agent-sandbox` Slack before Helioy commits to one path.
2. **gVisor / Kata wiring.** agent-sandbox supports `runtimeClass` swap but `lap` does not exercise it. For Helioy's "untrusted code execution" use case (agents writing arbitrary code), gVisor at minimum should be the default. Cost: kernel-level overhead, no current numbers from either project.
3. **CRD stability.** agent-sandbox is `v1alpha1` and pre-1.0. The roadmap signals upcoming changes (decouple API from runtime, multi-sandbox per pod, status updates). Helioy needs a release-pin strategy and a compatibility-shim plan.
4. **Vault sidecar with TLS-pinning clients.** The MITM works because every TLS client in the harnesses reads `SSL_CERT_FILE` or `NODE_EXTRA_CA_CERTS`. A library that pins to a public root (some Go HTTP clients, mobile SDKs) breaks silently. Test before promising the pattern in `im`.
5. **`docs.litellm-agent-platform.ai/`** is referenced from the README but was not fetched in this review. Worth a separate pass to capture the publicly documented contract vs the in-repo behaviour.
6. **The "Other" license on LiteLLM proper.** The `lap` repo is bare MIT; the parent `litellm` is "Other". Confirm `lap` is genuinely standalone before any code lift (the reconcile.ts header acknowledges porting from `litellm/proxy/managed_agents_endpoints/lifecycle.py` which is in the "Other"-licensed parent — risk that the original is not MIT-compatible).

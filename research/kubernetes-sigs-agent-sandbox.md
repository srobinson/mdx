---
title: kubernetes-sigs/agent-sandbox review for runtime-matters and orchestration-matters
type: research
tags: [github-review, kubernetes-sigs, agent-sandbox, crd, runtime-matters, k8s-endgame, apache-2.0, go, kubebuilder, v1alpha1]
summary: Foundational k8s CRD for the runtime/session split. Clean four-resource decomposition, opinionated controllers, but v1alpha1 churn is still real (v0.3.10 → v0.4.6 each shipped breaking changes). Target SandboxClaim, not Sandbox, when runtime-matters ships its k8s mode. Wait for the Beta epic (#740) to land before pinning.
status: active
source: github-researcher
confidence: high
created: 2026-05-18
updated: 2026-05-18
---

## Stats

**kubernetes-sigs/agent-sandbox** (https://github.com/kubernetes-sigs/agent-sandbox). Apache-2.0, 2,222 stars, 271 forks, default branch `main`. Created 2025-08-12, nine months old. Latest release `v0.4.6` (2026-05-14), running an automated weekly Thursday cadence since v0.4.5. Pre-1.0, two CRD API groups both at `v1alpha1`. Go 1.26 controller (`sigs.k8s.io/agent-sandbox`), Python SDK (`k8s-agent-sandbox` on PyPI), hand-written Go SDK (`clients/go/sandbox/`), generated Kubernetes-style clientset (`clients/k8s/`). 4,714 lines across the API and controller files inspected; 1,150 LOC core controller, 1,557 LOC SandboxClaim controller, 542 LOC SandboxWarmPool controller, 222 LOC SandboxTemplate controller. SIG Apps subproject under formal Kubernetes governance: CLA required, OWNERS files, KEP directory, kube-api-linter in CI. AI-assisted code review (Copilot first-pass) is explicitly opted-in and Copilot suggestions are blocked from being applied via the UI because it would break CLA attribution. Contributor pool is overwhelmingly Google (23 google.com commits since 2026-01-01 vs 16 noreply, 3 gmail, then trace amounts from nirmata, daocloud, akvelon, buenosystems, msn). The PR velocity is real: stale at 30 days, auto-close at 45.

## Grade

**B+**. The CRD decomposition is correct and clean. Four resources with sharp separation: `Sandbox` is the singleton-pod primitive, `SandboxTemplate` is the persona+policy, `SandboxClaim` is the user request, `SandboxWarmPool` is the pre-spawn. Field-level kubebuilder validation is opinionated and tight. The controller code is idiomatic controller-runtime with envtest fixtures and goleak-checked unit tests. The deductions from A−: (1) v1alpha1 is genuinely unstable — v0.3.10, v0.4.5, and v0.4.6 each shipped marked breaking changes covering the same surface area (warm pool semantics, service creation defaults, status field rename). (2) The "Sandbox CRD as workload primitive" abstraction has a known leak — issue #127 ("strict 1:1 Sandbox-to-Pod mapping") was officially closed as v0.4.5 work but PR #115 introduced the warm-pool adoption path that breaks the invariant, and the controller carries `resolvePodName(sandbox)` indirection to deal with it. (3) The roadmap is honest but long: "Decouple API from Runtime", "Multi-Sandbox per Pod", "Status Updates", and "API Support for other isolation technologies" are all listed for 2026 and none has landed. (4) Cross-vendor adoption is invisible: the "Who is using" issue (#776) has been open since April with two `/lifecycle frozen` and `/kind support` comments and zero real adopters. BerriAI/litellm-agent-platform is the only publicly identifiable production consumer, and they skip half the API (write `Sandbox` directly, use `SandboxWarmPool` from extensions but not `SandboxClaim` or `SandboxTemplate`).

The grade is for it as a CRD contract to consume, not as a Go library. Helioy runtime-matters is Rust 2024 and will not import the controller code anyway.

## Primitives that transfer

1. **Four-resource decomposition.** `Sandbox` (atomic singleton pod with stable identity), `SandboxTemplate` (parameterized blueprint with NetworkPolicy and EnvVarsInjectionPolicy controls), `SandboxClaim` (user request bound to a template, optionally with a warm-pool policy), `SandboxWarmPool` (HPA-scalable pre-warmed pool keyed on a template ref). The cut lines are right: persona is separable from request, request is separable from warm-pool plumbing, pool is separable from the singleton primitive. Helioy should adopt the same shape for the runtime-matters/session-matters/agent-matters boundary even though the names map differently. **Lands across runtime-matters, session-matters, agent-matters.** The Helioy mapping is roughly `SandboxTemplate` → `agm` persona, `SandboxClaim` → `sm` session, `Sandbox` → `rtm` runtime, `SandboxWarmPool` → `om` pool. Borrow the cuts, not the field names.

2. **Core/extensions API group split.** `agents.x-k8s.io/v1alpha1` carries only `Sandbox`; `extensions.agents.x-k8s.io/v1alpha1` carries the three higher-level resources. The split is enforced in `cmd/agent-sandbox-controller/main.go:167` where extensions registration is gated on a `-extensions` flag, and the binary can be deployed core-only or core-plus-extensions independently. This is the right pattern for Helioy: the seven-product family is going to ship at different velocities, and having API groups that mirror the product boundary makes per-product release pinning possible. **Lands in helioy-tools / the eventual Helioy CRD bundle.** When runtime-matters ships its first CRD, it should sit alone in `runtime.helioy.dev/v1alpha1` with everything compositional (warm pools, claims, dispatch) in `extensions.runtime.helioy.dev/v1alpha1`.

3. **`+kubebuilder:subresource:scale` + HPA on warm pools.** `SandboxWarmPool` exposes the `scale` subresource via `+kubebuilder:subresource:scale:specpath=.spec.replicas,statuspath=.status.replicas,selectorpath=.status.selector` so a standard HorizontalPodAutoscaler can drive the warm pool size. The same trick is used on `Sandbox` itself (`api/v1alpha1/sandbox_types.go:227`) constrained to 0 or 1 so the scale subresource works for pause/resume via `kubectl scale --replicas=0 sandbox/foo`. Helioy's eventual warm-pool primitive should expose this subresource from day one because it makes the autoscaling integration story trivial. **Lands in orchestration-matters (`om`).**

4. **`WarmPoolPolicy` as a constrained enum-plus-name string.** `extensions/api/v1alpha1/sandboxclaim_types.go:38` defines a single string field that takes `"none"`, `"default"`, or any specific pool name. The validation method `IsSpecificPool()` returns true for everything except the two reserved literals. This is a clean way to combine sentinel values with free-form names in one field without inventing a discriminated union. **Lands wherever Helioy needs `none | default | <named>` semantics.** Workflow dispatch policies have the same shape: "no workflow", "system default", or a named workflow.

5. **Hash-based template drift detection with vetted-hash cache.** `extensions/controllers/sandboxwarmpool_controller.go:435` (`isSandboxStale`) computes FNV-1a hash of the PodTemplate JSON, compares to the label on each warm sandbox, and caches the deep-equal verdict per hash so the second sandbox with the same hash is O(1). The fallback when the hash is empty is deliberate: log and treat as not stale to avoid mass deletion on marshal failure (`comparePodSpecs` line 484, "any remaining difference is a TRUE template drift"). The hash is FNV-1a not SHA: cheaper, collision-tolerant because the deep-equal is the real arbiter. **Lands in orchestration-matters (`om`).** Helioy's controllers that drive pre-warmed resources will face exactly this problem; the cache-by-hash pattern saves a deep-equal per warm replica per reconcile.

6. **`SELECT FOR UPDATE SKIP LOCKED` equivalent via in-process queue.** `extensions/controllers/queue/simple_sandbox_queue.go` is a `sync.Map<templateHash, synchronizedQueue<sandboxKey>>` where `Pop()` removes the head atomically and `Add()` deduplicates via a side `map[SandboxKey]struct{}`. `extensions/controllers/sandboxclaim_controller.go:582` (`getCandidate`) demonstrates the consumer pattern: Pop a key, fetch the Sandbox, if it's gone (ghost) loop and Pop the next, if it fails verification add to a `skipped` list and Pop the next, with a deferred re-add of skipped at exit so they're not lost. **Lands in orchestration-matters (`om`).** When multiple controllers race for a warm resource, in-process queue plus optimistic-conflict-retry is the controller-friendly equivalent of the database SKIP LOCKED pattern Berri used. Helioy should use this pattern instead of postgres SKIP LOCKED in any controller that lives inside the cluster.

7. **`computeReadyCondition` as the centralized state machine.** `controllers/sandbox_controller.go:313`. One function takes (sandbox, error, service, pod) and returns one Condition with a deterministic status and reason. The reasoning chain is layered: replica count zero implies Suspended, error implies ReconcilerError, pod missing implies "Pod does not exist", pod Pending implies still-not-ready, pod Running but not Ready implies ContainerStartup phase. The pattern keeps all condition-deriving logic in one place so the reconciler body stays a sequence of resource reconciles plus one call to `computeConditions`. **Lands in runtime-matters (`rtm`) and orchestration-matters (`om`).** Helioy's daemons will surface conditions on whatever CRDs they own; centralizing the condition derivation by output condition rather than by triggering event is the readable pattern.

8. **Adoption-vs-creation with `controllerRef` checking.** `controllers/sandbox_controller.go:71` (`checkOwnership`) returns a three-way enum: owned-by-this-sandbox, unowned, owned-by-other. Every reconciler decision branches on this. `reconcileService` line 525 implements the full matrix: owned-by-other refuses with a clear error; unowned can be adopted under explicit `service: true` but not under `nil`; owned-by-this drifts the labels/selector if needed. The pattern prevents the "delete someone else's resource" footgun while still permitting orphan adoption when intended. **Lands across all Helioy controllers.** Every controller that touches resources another component might also create needs this exact three-way switch.

9. **Default-deny NetworkPolicy with explicit metadata-server block.** `extensions/controllers/sandboxtemplate_controller.go:157` (`buildDefaultNetworkPolicySpec`) builds the "Secure Default": ingress only from `app=sandbox-router`, egress to `0.0.0.0/0` excepting `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`. The 169.254 carveout is the metadata server block (AWS IMDS, GCP metadata) and is the right default for anything running untrusted code: "intentionally blocks internal cluster DNS (CoreDNS) by default to prevent agents from probing for service discovery and leaking internal service names". Helioy's runtime-matters will face the same threat model with codex/cli sandboxes. **Lands in identity-matters (`im`) policy library.** The exact CIDR list is portable as a baseline; ship it as the default and let users opt out at the template level.

10. **`Service` opt-in defaulting via three-state pointer.** `api/v1alpha1/sandbox_types.go:165` defines `Service *bool` where `nil` means "preserve existing, do not create", `true` means create headless, `false` means delete owned. The v0.4.6 release flipped the default from "always create" to "opt-in" because at thousands of pods the kube-proxy and CoreDNS overhead dominated. The lesson is structural: when a field's default needs to change because of scale, the `*bool` triple-state lets you migrate without breaking existing resources. **Lands in any Helioy CRD that may eventually need its default flipped.** Use `*bool` from day one if there is any chance the field's semantics will shift. The accompanying comment is honest: `//nolint:nobools // Enum not used to avoid duplicating the Service API`. They chose the right tradeoff.

11. **Server-Side Apply for status updates.** `extensions/controllers/sandboxwarmpool_controller.go:386` uses `r.Status().Patch(ctx, patch, client.Apply, client.FieldOwner("warmpool-controller"), client.ForceOwnership)` instead of `Update`. This is the right pattern for status updates because it lets multiple controllers cooperatively own different status fields without trampling each other. The `//nolint:staticcheck` acknowledges the SA1019 warning (SSA requires generated apply configurations, not yet available for these types). **Lands across Helioy controllers.** Adopt SSA for status from day one and accept the generated-apply-config cost later.

12. **`predicate.LabelSelectorPredicate` to scope the controller's watch.** `controllers/sandbox_controller.go:1131`. The Sandbox controller only watches Pods and Services that carry `agents.x-k8s.io/sandbox-name-hash`, not every Pod in the cluster. At scale this is the difference between watching 50 sandboxes and watching 50,000 pods of unrelated workloads. **Lands in every Helioy controller.** Default to label-selector predicates; only widen if you have a reason.

13. **`+kubebuilder:default=Retain` for destructive defaults.** `Lifecycle.ShutdownPolicy` defaults to `Retain` not `Delete`. The reasoning is that the safe default for a user who configures a shutdownTime but does not specify a policy is "keep my CR so I can see what happened" not "delete everything silently". Helioy's pause/expire defaults should follow the same principle: never delete user-visible state by default.

14. **`EnvVarsInjectionPolicy` as a security knob owned by the template, not the claim.** `extensions/api/v1alpha1/sandboxtemplate_types.go:128`: the template author declares `Allowed | Overrides | Disallowed`, and the claim cannot override its own restriction. Defaults to `Disallowed`. This is the right way to enforce "the persona owner controls what the session can inject" without inventing an admission webhook. Berri's `lap` does not exercise this because lap is single-tenant; Helioy is single-tenant today too but will not be forever, and the pattern is cheap to adopt early.

## Does NOT transfer

1. **Go + controller-runtime + kubebuilder.** Helioy invariant 9 is Rust 2024. The controller code does not port. Helioy will write controllers against `kube-rs` and the manual equivalent of the kubebuilder marker conventions. This rules out direct lift; the CRD YAML in `k8s/crds/` is the only consumable artifact.

2. **Two-CRD-version-in-one-API-group strategy.** agent-sandbox keeps everything at `v1alpha1` and ships breaking changes inside the alpha label (v0.3.10 renamed `status.Name` to `status.name`, v0.4.6 flipped service default). Helioy should not follow this. The Helioy convention should be: when a breaking change is needed, bump the API version (`v1alpha2`) and ship a conversion webhook, even at alpha. Stuart is the sole consumer today so this is mostly aesthetic, but the pattern matters when the seven products start cross-referencing each other's types.

3. **Single binary controller manager with `-extensions` flag.** The single-binary deployment is reasonable for a SIG Apps project where one cluster admin wears all hats. Helioy's runtime-matters is per-host (kubelet-equivalent), orchestration-matters is cluster-wide (kube-controller-manager-equivalent), and they should not share a binary. The split is per-daemon. Borrow the deployment-time flag pattern (`make deploy-kind EXTENSIONS=true`) but not the single-binary architecture.

4. **In-process `observedTimeMap` for first-seen tracking.** `extensions/controllers/sandboxclaim_controller.go:91` uses a `sync.Map` keyed by namespaced name to remember "when did this controller first observe this claim", and writes the value into an annotation on first reconcile. The pattern works because k8s controllers are leader-elected and the in-process map is consistent with the only active reconciler. Helioy's controllers should resist this pattern because daemons that crash lose the map and the annotation is the only durable record. Better: write the annotation immediately on first observation and never read the in-process map.

5. **`agent_templates.json` style single-file metadata.** Not present in this project; `lap` had it, agent-sandbox does not. agent-sandbox encodes persona inline in `SandboxTemplate.spec.podTemplate`, which means the persona definition is k8s YAML, not a portable artifact. Helioy should not follow this either direction: persona should be portable across runtimes (k8s, bare metal, future Wasm) and live in its own representation, with the k8s-runtime view being a derived projection. The Helioy `agm` persona format is not `SandboxTemplate.spec`.

6. **Python SDK as the user-facing client surface.** The Python SDK at `clients/python/agentic-sandbox-client/` exists because the Python ecosystem is where AI workloads run. It is well-designed (sync/async parity, four connection strategies, OpenTelemetry instrumentation, pydantic models in `models.py:70`) but Helioy's `runtime-matters` is not a user-facing surface. The connection strategies (`SandboxDirectConnectionConfig`, `SandboxGatewayConnectionConfig`, `SandboxLocalTunnelConnectionConfig`, `SandboxInClusterConnectionConfig`) are a useful taxonomy but they live in the SDK; Helioy's `rtmd` does not need a client library because the MCP boundary is the consumer interface.

7. **`sandbox-router` as the in-cluster routing fabric.** The default NetworkPolicy assumes a pod labeled `app=sandbox-router` exists. agent-sandbox does not ship the router as core; it lives in `clients/python/agentic-sandbox-client/sandbox-router/` as a separate Python app. The router pattern (centralized gateway that proxies to per-sandbox pods, used by all four Python connection strategies in concert with the `X-Sandbox-*` header injection) is fine but Helioy's transport-matters should not depend on a router service the way agent-sandbox does. Per-sandbox direct addressing via stable hostnames (`Sandbox.status.ServiceFQDN`) is the right Helioy default; route opaquely through `tm` when needed, not through a per-cluster router daemon.

8. **Bare `Sandbox` writes from external systems.** BerriAI/litellm-agent-platform writes Sandbox CRs directly, skipping the SandboxClaim layer. They have not documented why; my read after inspecting both codebases is that lap's threading model (one platform process owns the full lifecycle including warm-pool selection) made the claim layer feel redundant. Helioy should not copy this. Writing `SandboxClaim` is structurally cleaner because the SandboxClaimReconciler owns the warm-pool adoption race (`getCandidate` + `adoptSandboxFromCandidates` lines 582-717) including the optimistic-conflict retry loop with 3 attempts. Reimplementing that in `rtmd` would be a maintenance burden.

## Verdict

**Consume the CRD, not the code.** agent-sandbox is the right substrate for Helioy's k8s endgame. The CRD design is opinionated in the right places (`*int32 Replicas` constrained to 0/1, `+kubebuilder:default=Retain` for destructive defaults, EnvVarsInjectionPolicy owned by the template author, three-state Service pointer for opt-in). The controller is well-built but not borrowable. The v1alpha1 churn is real but bounded: the breaking changes since v0.3.10 (October 2025) have all been small, well-documented, and addressable with manifest changes. The Beta graduation epic (#740) opened 2026-05-16 and lists service opt-in plus suspend/resume design as the two remaining blockers. The honest read on stability is "pin to a release, expect to update the manifest at each minor".

## Why

Three reasons hold this rating in place.

First, the API surface is genuinely small. Four resources, fewer than a dozen top-level fields each, and the field semantics are documented inline with kubebuilder markers that double as validation rules. Stuart can read `api/v1alpha1/sandbox_types.go` (257 LOC) and `extensions/api/v1alpha1/sandboxclaim_types.go` (207 LOC) in twenty minutes and have the full mental model. Compare to writing a Helioy-native equivalent from scratch: months of design, dozens of bugs the upstream team has already paid for (#754 selector unset when replicas=0, #770 label-value-convention violation, #764 stale-pod adoption race), zero ecosystem leverage.

Second, the SIG Apps governance signals stability commitment. The Beta graduation epic exists and has an owner. The Service opt-in change (v0.4.6) was shipped specifically because scale data forced a default flip; that is the behavior of a project that intends to be production-grade, not a research artifact. The Copilot-as-first-reviewer experiment shows the maintainers actively investing in review velocity even at the cost of a complicated CLA workflow.

Third, the abstraction matches the runtime-matters mandate exactly. runtime-matters (per `019e327f-111b-7382-a760-12e4e410e701`) is the per-host kubelet + container-runtime equivalent. Sandbox is the per-host singleton-pod abstraction. The boundary is precise: rtmd writes `SandboxClaim`, agent-sandbox owns the pod lifecycle, rtmd reads `Sandbox.status` for readiness. No overlap, no contention. The only Helioy-side work is the Rust client (`kube-rs`) and the per-Helioy-product CRDs that compose with agent-sandbox's primitives.

## How to apply

**Decision: Option B with explicit fallback to Option D.** Target `SandboxClaim` (the extension) as runtime-matters' k8s consumption point. Rationale: SandboxClaim's adoption-race logic is non-trivial and the upstream controller owns it correctly. Writing Sandbox directly (lap's choice) means reimplementing warm-pool adoption in rtmd, which is wasted work. SandboxClaim is also where the EnvVarsInjectionPolicy enforcement lives, which matters when Helioy goes multi-tenant.

The fallback to Option D applies only if the Beta epic (#740) stalls past 2026-Q3. In that case, ship v1 of runtime-matters as bare-metal-only and revisit the k8s path against whatever v1beta1 looks like.

Concrete next steps:

- **runtime-matters (`rtm`).** Target `SandboxClaim` for k8s mode. Use `kube-rs` to write CRs and watch `Sandbox.status.conditions` for `Ready=True`. Pin to a release tag in `Cargo.toml` (`agent-sandbox-crd = "0.4.6"` once a Rust crate exists, or vendor the YAML otherwise). The Helioy daemon-pair convention (rtmd-on-bare-metal vs rtmd-in-k8s) maps to feature flags in the same binary. Add a contract test that fails if the pinned agent-sandbox release introduces a field rename in `Sandbox.status` (parse the CRD YAML at CI time).

- **orchestration-matters (`om`).** Borrow the `SandboxWarmPool` mechanics for Helioy's eventual warm-pool primitive. The `+kubebuilder:subresource:scale` pattern, the FNV-1a hash drift check with vetted-hash cache, and the in-process `SimpleSandboxQueue` for adoption-race resolution all transfer directly. The "Recreate vs OnReplenish" update strategy enum is the right shape for any pool primitive Helioy ships.

- **agent-matters (`agm`).** Do NOT mirror `SandboxTemplate`'s inline-PodSpec persona format. Helioy personas should be runtime-agnostic; the k8s-runtime view is a derived projection. The EnvVarsInjectionPolicy three-state enum (`Allowed | Overrides | Disallowed`) is a clean security primitive worth lifting into `agm`'s persona schema.

- **identity-matters (`im`).** Lift the default-deny NetworkPolicy spec (`buildDefaultNetworkPolicySpec` in `sandboxtemplate_controller.go:157`) as the default for any Helioy session that runs untrusted code. The exact CIDR carveouts (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `fc00::/7`) plus the explicit "blocks CoreDNS by default" comment are portable as a baseline.

- **session-matters (`sm`).** Adopt the central `computeReadyCondition` pattern when `smd` surfaces session conditions. One function that takes all observed state and returns one condition. Avoid the temptation to scatter `SetStatusCondition` calls across the reconciler body.

- **helioy-tools.** When Helioy ships its own CRDs, follow the core/extensions API group split: `<product>.helioy.dev/v1alpha1` for the atomic primitive, `extensions.<product>.helioy.dev/v1alpha1` for composition. Make the controller binary support a `-extensions` flag from day one so per-product deployment cadence stays decoupled.

Two cross-cutting reads to schedule next:

1. **`controllers/sandbox_controller.go` reconcileChildResources walkthrough.** Not for code lift but for the Reconcile-loop structure: parallel reconciles of PVC + Pod + Service, status derivation deferred to `computeConditions` after all reconciles complete, expiry handled in a separate branch. Helioy's controllers will reach for this shape.

2. **The Beta graduation epic (#740) and its linked KEPs.** Specifically the suspend/resume design (KEP 119 is in the repo at `docs/keps/119-sandbox-suspended-state/`). The condition hierarchy in that KEP (Suspended + Ready as orthogonal conditions, with the Suspended.Reason field documenting Pod state) is the model Helioy should adopt for any resource with a pause primitive.

## Open Questions

1. **Why does BerriAI write Sandbox directly?** Worth asking @ishaan-berri or @krrishdholakia on Twitter/Slack before Helioy commits to SandboxClaim. The lap codebase has no comment trail explaining the choice. My hypothesis (single-process owns full lifecycle) is unverified.

2. **Will the Helioy Rust client need to fork kube-rs's CRD code generation?** kube-rs has `kube-derive` but it expects to consume `#[derive(CustomResource)]` on Rust types. For external CRDs (which agent-sandbox is, to Helioy) the standard approach is `kube::CustomResource::api_resource()` plus serde structs hand-typed against the YAML. Confirm before committing to the API.

3. **What's the v1alpha1 → v1beta1 conversion story?** The Beta epic does not include a conversion webhook. If agent-sandbox bumps the API version without a conversion webhook, Helioy will face a hard migration. Track the epic; raise the question on the SIG Apps mailing list if it's not addressed by 2026-Q3.

4. **Does the Sandbox controller's leader election scope to namespace or cluster?** `cmd/agent-sandbox-controller/main.go:73` defaults to cluster-wide leader election via `coordination.k8s.io/leases`. Confirm this is acceptable for Helioy's multi-cluster vision; the bare-metal `rtmd` is per-host and cannot leader-elect against a k8s lease. The k8s-mode `rtmd` may need to coexist with the cluster-wide agent-sandbox controller without contention.

5. **Cross-vendor adoption signal.** Beyond Berri (and the example apps Google contributes), who is actually consuming this CRD in production? The "Who is using" issue (#776) is dormant. Worth a direct ask on Slack `#agent-sandbox` before deeply coupling.

## Sources Consulted

- `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `roadmap.md`, `RELEASE.md`, `LICENSE`
- `api/v1alpha1/sandbox_types.go` (257 LOC, entire file)
- `extensions/api/v1alpha1/sandboxclaim_types.go` (207 LOC, entire file)
- `extensions/api/v1alpha1/sandboxtemplate_types.go` (168 LOC, entire file)
- `extensions/api/v1alpha1/sandboxwarmpool_types.go` (121 LOC, entire file)
- `controllers/sandbox_controller.go` (1150 LOC, full read of Reconcile + computeConditions + reconcileService + reconcilePVCs + handleSandboxExpiry + SetupWithManager)
- `extensions/controllers/sandboxclaim_controller.go` (1557 LOC, focus on Reconcile, getCandidate, adoptSandboxFromCandidates, completeAdoption)
- `extensions/controllers/sandboxtemplate_controller.go` (222 LOC, entire file)
- `extensions/controllers/sandboxwarmpool_controller.go` (542 LOC, focus on reconcilePool, isSandboxStale, comparePodSpecs, SetupWithManager)
- `extensions/controllers/queue/simple_sandbox_queue.go` (146 LOC, entire file)
- `cmd/agent-sandbox-controller/main.go` (286 LOC, entire file)
- `clients/python/agentic-sandbox-client/k8s_agent_sandbox/sandbox_client.py` (focus on create_sandbox + get_sandbox)
- `clients/python/agentic-sandbox-client/k8s_agent_sandbox/models.py` (full)
- `clients/python/agentic-sandbox-client/k8s_agent_sandbox/connector.py` (focus on connection strategies)
- `clients/go/README.md` (full), `clients/go/sandbox/` (file listing only)
- `k8s/crds/` (file listing + first 30 lines of sandbox CRD YAML)
- `docs/api.md`, `docs/keps/119-sandbox-suspended-state/README.md`
- `extensions/examples/sandboxtemplate.yaml`, `extensions/examples/sandboxwarmpool.yaml`
- `examples/hermes-agent/README.md`, `examples/kueue-agent-sandbox/README.md`, `examples/langchain/README.md`, `examples/kata-gke-sandbox/README.md`, `examples/openclaw-sandbox/README.md`
- Release notes: v0.4.6, v0.4.5, v0.4.2, v0.3.10 (full)
- GitHub issues: #127 (closed, strict 1:1 mapping), #119 (closed, status update), #740 (open, Beta graduation epic), #776 (open, adopter survey, dormant)
- Git log for `api/`, `extensions/api/`, `controllers/sandbox_controller.go` (last 30 commits)
- Author email domains for last 4 months of commits (Google-dominated: 23/49 commits)

## Draft cm body

```yaml
title: "kubernetes-sigs/agent-sandbox review for runtime-matters: B+, consume SandboxClaim from k8s mode of rtmd, pin to v0.4.6, track Beta epic #740"
scope: global/project:helioy
kind: decision
confidence: high
source: https://github.com/kubernetes-sigs/agent-sandbox
tags: [github-review, kubernetes-sigs, agent-sandbox, crd, runtime-matters, k8s-endgame, apache-2.0, go, kubebuilder, v1alpha1]
```

Body:

Foundational k8s CRD for Helioy's k8s endgame. Four resources, two API groups: `Sandbox` (core, atomic singleton pod with stable identity and PVC binding), `SandboxTemplate` + `SandboxClaim` + `SandboxWarmPool` (extensions). Apache-2.0, 2.2k stars, nine months old, SIG Apps governance, Google-dominated contributor base. Grade B+. Deductions: v1alpha1 churn is real (v0.3.10 / v0.4.5 / v0.4.6 each shipped breaking changes), abstraction leaks at the warm-pool adoption boundary (issue #127 closed but `resolvePodName` indirection remains), no cross-vendor adopters visible besides BerriAI/litellm-agent-platform. Decision: rtmd's k8s mode targets `SandboxClaim` (Option B), not bare `Sandbox` writes. Rationale: SandboxClaim's adoption-race logic with optimistic-conflict retry and ghost-pod handling is non-trivial and the upstream controller owns it correctly. Bare Sandbox writes (lap's choice) means reimplementing warm-pool adoption in rtmd, which is wasted work. Pin to v0.4.6 in Cargo.toml. Track Beta epic #740 for conversion-webhook story before v1beta1 lands. Borrow primitives: four-resource decomposition, core/extensions API group split, `+kubebuilder:subresource:scale` for HPA-on-warm-pool, FNV-1a hash drift detection with vetted-hash cache, in-process SandboxQueue as the SKIP-LOCKED equivalent, default-deny NetworkPolicy with metadata-server block. Do NOT borrow: Go controller code (invariant 9: Rust 2024), single-binary controller manager (Helioy daemons are per-product), `agent_templates.json`-style persona format (personas must be runtime-agnostic). Companion review: BerriAI/litellm-agent-platform (cm `019e34ba-881f-7971-924f-a978599015c2`) for the consumer-side shape. Artifact: `~/.mdx/research/kubernetes-sigs-agent-sandbox.md`.

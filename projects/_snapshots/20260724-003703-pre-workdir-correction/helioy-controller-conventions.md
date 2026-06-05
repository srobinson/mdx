---
title: helioy-controller-conventions — cross-cutting rules for Helioy CRDs and controllers
type: projects
tags: [helioy-tools, conventions, k8s, crd, controllers, kube-rs, kubebuilder, rust, draft]
summary: Six cross-cutting conventions for every Helioy CRD and controller. Lifted from the kubernetes-sigs/agent-sandbox review (cm 019e3784-2194-7b91-87ae-84e3b3545767). Lock these now so every controller that lands carries the same rules from day one.
status: draft
project: helioy-tools
confidence: high
created: 2026-05-18
updated: 2026-05-18
related: [kubernetes-sigs-agent-sandbox, berriai-litellm-agent-platform, runtime-matters-kubelet-draft, session-matters-foundation-draft]
---

# helioy-controller-conventions — cross-cutting rules for Helioy CRDs and controllers

## Why this doc exists

The seven-product Helioy family will ship multiple CRDs (the first one likely from orchestration-matters or runtime-matters, since rtm's k8s consumer is now locked to Option B per [[kubernetes-sigs-agent-sandbox]]). Each controller needs a consistent set of design rules from day one. These rules are not negotiable per product; they are the substrate every controller stands on. Picked from the agent-sandbox review which vetted them against a production project with a year of operational history.

The cost of getting these wrong is real: rework on every CRD that already shipped, conversion webhooks, migration code, operational debt that compounds. The cost of writing them down now is one short doc.

Stack assumption: Rust 2024 + `kube-rs` per invariant 9 of the seven-product decision (cm `019e327f-111b-7382-a760-12e4e410e701`). Where agent-sandbox uses kubebuilder Go markers, the Helioy equivalents are `kube-rs` derive macros + manual CRD YAML.

## Convention 1: Core/extensions API group split

**Rule.** Every Helioy product that ships CRDs uses two API groups: `<product>.helioy.dev/v1alpha1` for the atomic primitive, `extensions.<product>.helioy.dev/v1alpha1` for everything compositional (warm pools, claims, dispatch, templates).

**Why.** Per-product release cadence stays decoupled. The atomic primitive ships at a different velocity than the compositional extensions, and consumers can pin them independently. agent-sandbox `cmd/agent-sandbox-controller/main.go:167` gates extensions registration on a `-extensions` flag so the binary deploys core-only or core-plus-extensions.

**How to apply.**

1. Two distinct API group strings in the CRD YAML.
2. Controller binary supports a runtime flag (`--extensions=true|false`) to register extensions or skip.
3. CRD release tags are independent: a v0.5.0 release of `runtime.helioy.dev/v1alpha1` does NOT force a release of `extensions.runtime.helioy.dev/v1alpha1`.
4. Helm chart split: separate `manifest.yaml` and `extensions.yaml` outputs.

## Convention 2: Adoption-vs-creation three-way controllerRef check

**Rule.** Every controller decision that touches a child resource branches on a three-way enum: `owned-by-this`, `unowned`, `owned-by-other`. No two-way "owned vs not" check.

**Why.** Prevents the "delete someone else's resource" footgun while still permitting orphan adoption when intended. `controllers/sandbox_controller.go:71` (`checkOwnership`) shows the canonical implementation; `controllers/sandbox_controller.go:525` (`reconcileService`) implements the full matrix: owned-by-other refuses with a clear error; unowned can be adopted only under explicit opt-in (`service: true`); owned-by-this drifts labels/selector if needed.

**How to apply.** Every `kube-rs` controller writes:

```rust
enum Ownership {
    OwnedByThis,
    Unowned,
    OwnedByOther { owner: ObjectReference },
}

fn check_ownership(child: &impl Resource, parent: &impl Resource) -> Ownership { ... }
```

Decisions that touch the child must `match` on Ownership; the `OwnedByOther` arm refuses with an actionable error message naming the conflicting owner.

## Convention 3: `Option<bool>` three-state for opt-in defaults

**Rule.** Any CRD field whose default semantics might shift in a later version is `Option<bool>` (or the moral equivalent). Three states: `None` (preserve existing, do nothing), `Some(true)` (create / enable), `Some(false)` (delete / disable).

**Why.** Lets a default flip in a later release without breaking existing resources. agent-sandbox `api/v1alpha1/sandbox_types.go:165` defines `Service *bool`; v0.4.6 flipped the default from "always create" to "opt-in" because at thousands of pods kube-proxy + CoreDNS overhead dominated. Existing resources kept their explicit settings; only new resources with `nil` saw the new default.

**How to apply.** When designing any boolean-ish field on a Helioy CRD, ask: "could the default behaviour ever change because of scale, threat model, or operational learning?" If yes, `Option<bool>`. The accompanying lint suppression (`// nolint:nobools` equivalent) is acceptable; we accept the tradeoff knowingly.

## Convention 4: Server-Side Apply for status updates

**Rule.** Status updates use Server-Side Apply with an explicit field owner. Never `Update`.

**Why.** Multiple controllers (or multiple tasks of the same controller) may cooperatively own different status fields. SSA lets each own its slice without trampling the others. agent-sandbox `extensions/controllers/sandboxwarmpool_controller.go:386` uses `Patch(ctx, patch, client.Apply, client.FieldOwner("warmpool-controller"), client.ForceOwnership)`.

**How to apply.** `kube-rs` exposes SSA via `Api::patch_status` with `PatchParams::apply("<field-owner>").force()`. The field owner string is the controller's stable identifier, e.g. `runtime-matters/rtmd-status` or `orchestration-matters/warmpool-controller`. Adopt SSA for status from day one and accept the generated-apply-config cost later when v1beta1 lands.

## Convention 5: Label-selector predicate to scope watches

**Rule.** Every controller scopes its watch by label selector. The selector matches the controller-owned label that the CRD's controller writes during creation.

**Why.** At scale, watching 50 sandboxes vs 50,000 unrelated pods is the difference between a responsive controller and an OOM event. `controllers/sandbox_controller.go:1131` shows the pattern; the Sandbox controller only watches Pods and Services carrying `agents.x-k8s.io/sandbox-name-hash`.

**How to apply.** When wiring up a `kube-rs` `Controller`, configure the watch:

```rust
let watcher_config = watcher::Config::default()
    .labels("runtime.helioy.dev/owned-by");
```

Default to label-selector watches. Widen only with a measured reason.

## Convention 6: Non-destructive defaults for any user-visible state

**Rule.** Any field that could trigger user-visible data loss defaults to the non-destructive value. The safe default for a user who configures (say) `shutdownTime` without specifying a `shutdownPolicy` is "keep my resource so I can see what happened", not "delete everything silently".

**Why.** Operational safety. agent-sandbox `Lifecycle.ShutdownPolicy` defaults to `Retain` not `Delete`; pause/resume defaults follow the same pattern. The user who forgot to specify a policy is more often a confused operator than an explicit data-deletion request.

**How to apply.** When designing any CRD field that controls a destructive action (delete, evict, expire, drop, force), the default value is the non-destructive option. Document the rationale in the field's doc comment so the next reader does not "fix" it.

## How to apply (process)

1. **CRD design review checklist.** Before any new CRD lands in a Helioy product, the PR review verifies all six conventions are followed. Add this checklist to `helioy-tools/CONTRIBUTING.md` once that file exists.
2. **First-controller conformance test.** When the first Helioy controller ships (likely orchestration-matters), build a fixture suite that asserts the controller respects conventions 2-5 (ownership check, status SSA, watch scoping). The test is the executable form of this doc.
3. **Convention review cadence.** Revisit this doc when shipping a CRD that does not fit one of the conventions. The doc updates; the conventions hold or they are explicitly revised with a recorded reason.

## Provenance

Every convention here is lifted from a primitive vetted by the agent-sandbox review. Original source: `kubernetes-sigs/agent-sandbox` v0.4.6 (Apache-2.0), reviewed 2026-05-18, cm `019e3784-2194-7b91-87ae-84e3b3545767`. The conventions are 6 of the 14 primitives from that review's "Primitives that transfer" section. The product-specific primitives (#3, #5, #6 orchestration-matters; #4 workflow-matters; #7 session-matters; #9 identity-matters; #14 agent-matters) live in their respective product drafts.

## Related

- Source review: `~/.mdx/research/kubernetes-sigs-agent-sandbox.md` (cm `019e3784-2194-7b91-87ae-84e3b3545767`)
- Consumer-side review: `~/.mdx/research/berriai-litellm-agent-platform.md` (cm `019e34ba-881f-7971-924f-a978599015c2`)
- Seven-product family: cm `019e327f-111b-7382-a760-12e4e410e701`
- runtime-matters draft (uses conventions 2, 3, 4): `runtime-matters-kubelet-draft.md`
- session-matters draft (uses conventions 4, 5): `session-matters-foundation-draft.md`

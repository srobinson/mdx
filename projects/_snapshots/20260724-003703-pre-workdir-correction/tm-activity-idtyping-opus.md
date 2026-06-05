# Activity ID typing & magic strings — position (opus, second family)

Grounded in `packages/activity/src` @ 3f6b379 and the two specs.

## Q1 — ID typing: a deliberate split, not one rule

**Brand the two aggregate-identity keys; plain-string everything local; harness
is an opaque domain tag whose known set lives in the bundle.**

- **`RunId`, `WorkspaceId` → branded nominal (`string & { readonly __brand }`).**
  These are the aggregate keys (spec §6.1: "keyed by run_id, owned by
  workspace_id"), they flow through every layer, and `RunActivityContext` holds
  both as `string | null` side by side (trivially swappable). A one-file
  `ids.ts` (branded types + constructors applied once at the reader boundary) is
  a cheap, zero-runtime guard a copied template should set once.
- **Event/record ids, `toolCallId` → plain `string`.** Short-lived,
  single-boundary, compared only for equality. Branding them is ceremony without
  payoff — the over-engineering to avoid.
- **`Harness` → opaque domain tag; the enumerated set lives in the harness
  bundle, never the domain.** The domain is harness-agnostic, so it must not
  enumerate harnesses: a closed union (today's `RuntimeKind`) forces a domain
  edit per harness — the exact thing we forbid. The known set lives in the
  slice-1 TS bundle (`const HARNESSES = ["claude","codex"] as const`), mirroring
  Python `harnesses/` and `session.harness`. Adding a harness = one registry
  edit, zero domain edits.
- **Reject open-enum `"claude" | "codex" | (string & {})` in the domain.** It is
  an obscure idiom (against "obvious to maintain"), gives no real safety (any
  string passes), and re-leaks the harness set into the domain.
- **Keep `RunActivityEventStream = "lifecycle" | "record"` a closed named
  union.** Contrast with Harness: this is a domain-owned, genuinely closed set,
  so a literal union is correct — not everything should be extensible.

## Q2 — Magic strings: single-source the contracts, keep union literals bare

**Must be single-sourced:**
- **Cross-plane wire literals `tm_events`, the `run_lifecycle` payload type,
  `run_lifecycle_event` table** — the highest-value case. Python already names
  `NOTIFY_CHANNEL` in `session/listen.py`, yet `session/writer.py` (default arg)
  and `session/test_listen.py` re-inline `'tm_events'`; the slice-1 TS listener
  would be a third copy. Fix: one const per plane (reuse `NOTIFY_CHANNEL`
  everywhere in Python; a `TM_EVENTS_CHANNEL` in `@tm/activity`'s pg adapter —
  **not** `@tm/core`, which is browser-only and never sees pg NOTIFY), with the
  spec/ARCHITECTURE.md as the cross-language source of truth and a conformance
  test asserting the two planes agree.
- **Harness ids** — the bundle registry (Q1), not scattered literals.
- **The slice-1 `ActivityRecordKind` ↔ event-`type` mapping** — one exhaustive
  `Record<ActivityRecordKind, …>`, not scattered string compares.

**Bare literals are correct — do NOT extract:**
- **`RunActivityEvent` `type` discriminators** (`"record.tool_use"`, …). The
  union literal *is* the single source; TS narrows on literal types, so pulling
  them into `const`s would weaken discriminated-union exhaustiveness.
- **XState state-node keys.** `activityStatuses` already single-sources status
  for consumers; the machine's literal state keys are an XState-structural
  duplication, already guarded by the graph test's `activityStatuses.toContain`.

Principle: single-source **contracts that cross a boundary** (planes, packages,
languages); leave literals bare where the type system already makes them the one
source of truth.

---
title: "Transport Matters autopilot baseline"
description: "Architecture for issue 382 controlled A/B/A captures and observed request evidence"
artifact_type: design
project: transport-matters
repo: /Users/alphab/Dev/LLM/DEV/helioy/transport-matters
status: accepted
created: 2026-08-17
source_commit: 16dfcbd105c2196f6776aa9cfb5f447855415ff8
issues:
  - "https://github.com/littleorgans/transport-matters/issues/382"
tags:
  - autopilot
  - baseline
  - capture
  - request-schema
---

# Transport Matters autopilot baseline

## Decision

Build the first issue 382 slice as one controlled supported cell. Run prompt A, prompt B, then prompt A again. Every probe gets its own empty source home and enters through `prepare_captured_run`. The operation persists one immutable, self contained evidence bundle. The command defaults to Claude. The completed live proof uses Codex because the local Claude fleet credential is unavailable.

The CLI remains thin. Capture owns launch preparation, runtime homes, proxy lifecycle, storage, and cleanup. Request inventory owns strict native JSON decoding, duplicate key rejection, pointer escaping, string leaf hashes, and TM IR annotations. The new baseline code owns probe policy, exact exchange correlation, finite observed schema, evidence classification, and bundle persistence.

The first slice does not capture every model. It does not claim model dependence. It does not add a baseline database or a second launch path.

## Caller view

```python
report = harvest_controlled_baseline(
    cell=BaselineCell(
        harness="claude",
        provider="anthropic",
        harness_version=observed_version,
        model=model_id,
        request_shape="first-turn",
    ),
    prompts=ControlledPrompts(
        prompt_a="Reply with exactly ALPHA.",
        prompt_b="Reply with exactly BRAVO.",
    ),
    workspace=isolated_workspace,
    output=output_root,
    timeout=timeout,
    capture_dependencies=default_claude_run_dependencies(),
)
```

The caller supplies the cell and deterministic prompt content. The operation allocates probe identities and homes, launches three captured runs, selects one owned exchange per run, builds evidence, writes an immutable bundle, reads it back, and returns its reference.

## Existing owners

| Concern | Owner |
| --- | --- |
| Captured launch request and lease | `captured.models`, `prepare_captured_run` |
| Runtime child home and managed environment | existing captured run and home overlay modules |
| Captured run index and exchange bytes | `certification_run_reader` |
| Strict native request parsing and string inventory | `request_inventory` |
| Semantic normalized form | `session.wire_normalization` |
| Atomic JSON write | existing `write_atomic_json` |

No new code may duplicate these responsibilities.

## Public contracts

```python
class ProbeLabel(StrEnum):
    A1 = "a1"
    B = "b"
    A2 = "a2"


class EvidenceKind(StrEnum):
    STABLE = "stable"
    PROMPT_DERIVED = "prompt-derived"
    SESSION_GENERATED = "session-generated"
    MODEL_DEPENDENT = "model-dependent"
    STRUCTURALLY_OPTIONAL = "structurally-optional"
    UNKNOWN = "unknown"


class DriftOutcome(StrEnum):
    EXACT = "exact"
    COMPATIBLE = "compatible-drift"
    BREAKING = "breaking-drift"
    INSUFFICIENT = "insufficient-evidence"


class ControlledPrompts(BaseModel):
    model_config = ConfigDict(frozen=True)

    prompt_a: str
    prompt_b: str

    # Boundary validation requires two nonempty, distinct prompts.


class BaselineCell(BaseModel):
    model_config = ConfigDict(frozen=True)

    harness: str
    provider: str
    harness_version: str | None
    model: str
    request_shape: Literal["first-turn"]


class ProbeEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: ProbeLabel
    delivery_id: UUID
    prompt_sha256: str
    run_id: str
    exchange_id: str
    correlation_method: Literal["unique-prompt"]
    raw_request_base64: str
    raw_request_sha256: str
    inventory: RequestInventory
    normalized_request: dict[str, object]
    transcript_paths: tuple[str, ...]
    transcript_sha256: tuple[str, ...]


class JsonNodeObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    pointer: str
    kinds: tuple[Literal["null", "boolean", "number", "string", "array", "object"], ...]
    present_in: tuple[ProbeLabel, ...]


class PointerEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    pointer: str
    value_sha256_by_probe: dict[ProbeLabel, str]
    presence_by_probe: dict[ProbeLabel, bool]
    tm_ir_sections: tuple[str, ...]
    kinds: tuple[str, ...]
    classifications: tuple[EvidenceKind, ...]
    reason: str


class BaselineBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_schema_version: Literal[1]
    bundle_id: UUID
    generated_at: datetime
    source_commit: str
    cell: BaselineCell
    prompts: ControlledPrompts
    probes: tuple[ProbeEvidence, ProbeEvidence, ProbeEvidence]
    observed_schema: tuple[JsonNodeObservation, ...]
    pointer_evidence: tuple[PointerEvidence, ...]
    static_fingerprint: str
    repeat_a_outcome: DriftOutcome
    reference_bundle_id: UUID | None
    reference_outcome: DriftOutcome


def harvest_controlled_baseline(...) -> BundleRef: ...
def read_baseline_bundle(...) -> BaselineBundle: ...
def compare_baseline_bundles(...) -> BaselineComparison: ...
```

`PointerEvidence.classifications` is a tuple because structural optionality is independent of value provenance. A pointer may be structurally optional and prompt derived. A single exclusive enum would lose evidence.

## Probe execution

The plan is always `a1`, `b`, `a2`. A1 and A2 use identical prompt bytes. B uses different bytes. Every probe gets:

- a new delivery UUID
- a distinct empty manual source home
- a separate captured run and managed runtime home
- the same isolated workspace
- the same cell identity

The workspace path must be resolved before `CapturedRunRequest` validation. This handles the macOS `/var` and `/private/var` alias and prevents ancestor instruction leakage from the operator project.

`prepare_captured_run` remains the only launch preparation call. The process supervisor receives `spec.client.argv`, `spec.client.env`, and `spec.client.cwd` unchanged. A `finally` block always terminates the client and closes the lease.

## Exchange correlation

Captured exchange records do not currently persist the delivery UUID. This slice uses a strict unique prompt method within each isolated run.

One exchange qualifies only when the same exchange has:

1. readable `request.raw`
2. readable request IR
3. completed response evidence
4. the exact probe prompt in validated request evidence
5. an owned run transcript with the prompt and a later assistant turn

The resolver accepts exactly one qualifying exchange. Zero or multiple candidates produce insufficient evidence. Tool schema presence and index position are never selection predicates.

Delivery UUID persistence can strengthen this contract later. It does not belong in the first issue 382 slice.

## Raw observation and inventory

The observed schema is finite capture evidence. It does not claim to describe all provider requests.

Promote the existing strict JSON traversal into one shared native node observation function inside `request_inventory.py`. Both inventory and baseline schema use it. Preserve duplicate key rejection and RFC 6901 escaping.

Every observed pointer records all six JSON kinds and probe presence. String leaves retain the existing `RequestInventory` value hash, token count, API role, TM IR section, and provenance.

Array indices remain native JSON pointers. The classifier compares exact pointers. It does not pair array members by position across captures or invent stable identities for reordered elements.

## Classification

Classification uses direct evidence.

- Stable requires equal value and kind across A1, B, and A2.
- Prompt derived requires A1 and A2 equality, a different B value, and direct evidence that the pointer contains the probe prompt or maps to an explicitly prompt bearing semantic field.
- Session generated requires a known session identity field or a proven existing annotation. A1 versus A2 difference alone is unknown.
- Structurally optional records probe presence variation independently of value classification.
- Model dependent is always unproven in this single model slice.
- Unknown covers every unproven value or structure change.

The static fingerprint hashes sorted stable, structurally required pointer, kind, and value digest records. It excludes prompt, session, optional, model, and unknown evidence without deleting that evidence from the bundle.

## Outcomes

The bundle records two different outcomes.

`repeat_a_outcome` describes the A1 and A2 evidence inside one bundle. It can report exact repeat evidence or insufficient evidence. The A/B difference remains pointer evidence and does not turn the first bundle into a lifecycle comparison.

`reference_outcome` compares this bundle with an earlier bundle for the same cell:

- exact when schema and stable fingerprints match
- compatible drift when changes stay within previously demonstrated nonstatic evidence and retain kinds and semantic mapping
- breaking drift when stable required evidence changes, disappears, changes kind, or loses semantic mapping
- insufficient evidence when no reference exists, correlation is ambiguous, unknown evidence changes, or either artifact is incomplete

The first bundle has no reference and records insufficient evidence for `reference_outcome`.

## Persistence

Each harvest writes a new immutable bundle:

```text
<output>/bundles/<harness>/<provider>/<model>/<bundle-uuid>.json
<output>/current/<harness>/<provider>/<model>.json
```

The bundle is self contained. It embeds base64 raw bytes and digest binds the inventory, normalized form, transcript snapshot, provenance, observed schema, classifications, and comparison evidence. Raw bytes never appear in logs.

The writer performs these steps:

1. write the bundle to a temporary sibling
2. atomically replace the final bundle path
3. strictly read the bundle back
4. decode and hash every raw request
5. verify each inventory hash and probe labels
6. atomically update the small current pointer

Every harvest retains new run and exchange provenance. Remove the existing unchanged shortcut.

## Modules

| Module | Responsibility |
| --- | --- |
| `baseline_harvest.py` | CLI arguments, descriptor and one cell selection, one deep call |
| `baseline_capture.py` | probe plan, three launches, lifecycle, exact correlation |
| `baseline_evidence.py` | frozen contracts, pure schema, classification, fingerprints, bundle comparison |
| `baseline_store.py` | immutable write, strict read, atomic current pointer |
| `request_inventory.py` | shared strict native JSON observation and existing inventory |

No file may exceed 700 lines. Refactor the current 152 line `_capture_cell` before adding behavior. Refactor the existing 171 line test setup into fixtures before extending it.

## Verification

Write failing tests before production changes.

1. A/B/A order, prompt bytes, three homes, three UUIDs, same isolated workspace.
2. Resolved workspace path handles `/var` aliasing.
3. Every probe delegates to `prepare_captured_run` and passes the prepared client spec unchanged.
4. Correlation ignores startup traffic and rejects zero or multiple matching completed exchanges.
5. Selected raw request, response, prompt, and transcript proof belong to one run and exchange decision.
6. Client and lease cleanup hold on success and every failure boundary.
7. Shared JSON observation preserves all six kinds, escaped pointers, and duplicate key refusal.
8. Classification covers direct prompt evidence, known session evidence, optional presence, unknown changes, and unproven model dependence.
9. Immutable bundle round trip validates hashes and refuses unknown artifact versions.
10. A second identical harvest creates a second bundle with new provenance.
11. One real supported A/B/A run persists a readable bundle and proves three fresh homes and correlated exchanges.

## Rejected scope

- whole model matrix capture
- cross model classification
- provider specific baseline runners
- baseline database or blob store
- delivery ID persistence changes
- provider access probes
- retention or pruning policy

## Implementation sequence

1. Extract the current probe lifecycle and test setup without changing behavior.
2. Add the strict A/B/A plan and exchange correlation tests.
3. Add shared native JSON observations and pure classification tests.
4. Add immutable bundle storage and read back validation.
5. Run the focused suite, static checks, then one real Claude A/B/A smoke.

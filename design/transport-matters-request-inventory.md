---
title: Transport Matters request inventory
type: design
tags: [transport-matters, request-inventory, json-pointer, overlays]
summary: One read only inventory of exact textual JSON leaves with conservative semantic labels.
status: active
project: transport-matters
confidence: high
created: 2026-08-17
updated: 2026-08-17
---

# Transport Matters request inventory

## Problem

Captured `request.raw` is the only authority for native JSON leaf identity. `InternalRequest` can add meaning, but provider adapters normalize, preserve, or regroup wire data. The existing Codex worksheet joined five native leaves and assigned the joined text a digest that no provider field owned.

The inventory must preserve every decoded JSON string leaf. Semantic labels may add meaning to an existing leaf. They cannot remove a leaf or create a native preimage.

## Usage

```python
inventory = build_request_inventory(
    artifacts.request_raw,
    capture=RequestCaptureProvenance(
        harness="codex",
        harness_version="0.147.0",
        provider=artifacts.request_ir.provider,
        model=artifacts.request_ir.model,
        run_id=run_id,
        exchange_id=exchange_id,
    ),
    internal_request=artifacts.request_ir,
    annotations=controlled_capture_annotations,
)

leaf = inventory.require_leaf("/input/2/content/0/text")
assert leaf.sha256 == sha256(leaf.value.encode("utf-8")).hexdigest()

display = inventory.aggregate(
    [
        "/input/2/content/0/text",
        "/input/2/content/1/text",
    ]
)
assert display.members[0].pointer == "/input/2/content/0/text"
```

`RequestTextAggregate` has no `pointer` or `sha256`. A caller cannot mistake joined display text for a native field.

## Shape

```python
ProvenanceKind = Literal[
    "user-authored",
    "user-configuration-derived",
    "session-derived",
    "static-harness",
    "provider-metadata",
    "unknown",
]
TmIrSection = Literal[
    "model",
    "system",
    "tools",
    "messages",
    "sampling",
    "metadata",
    "stream",
    "provider_extras",
]

class RequestCaptureProvenance(BaseModel):
    harness: str
    harness_version: str | None
    provider: str
    model: str
    run_id: str | None
    exchange_id: str

class ProvenanceAssessment(BaseModel):
    kind: ProvenanceKind
    confidence: Literal["low", "medium", "high"]
    evidence: str

class TokenCount(BaseModel):
    value: int
    quality: Literal["authoritative", "estimate"]
    method: str

class LeafAnnotation(BaseModel):
    pointer: str
    api_role: str | None
    tm_ir_section: TmIrSection | None
    provenance: ProvenanceAssessment | None

class RequestStringLeaf(BaseModel):
    pointer: str
    value: str
    sha256: str
    character_count: int
    byte_count: int
    token_count: TokenCount
    api_role: str | None
    tm_ir_section: TmIrSection | None
    provenance: ProvenanceAssessment

class RequestLeafReference(BaseModel):
    pointer: str
    sha256: str

class RequestTextAggregate(BaseModel):
    value: str
    members: tuple[RequestLeafReference, ...]

class RequestInventory(BaseModel):
    capture: RequestCaptureProvenance
    raw_sha256: str
    leaves: tuple[RequestStringLeaf, ...]

    def require_leaf(self, pointer: str) -> RequestStringLeaf: ...
    def aggregate(self, pointers: Sequence[str], *, separator: str = "\n\n") -> RequestTextAggregate: ...

def build_request_inventory(
    request_raw: bytes,
    *,
    capture: RequestCaptureProvenance,
    internal_request: InternalRequest | None = None,
    annotations: Iterable[LeafAnnotation] = (),
    authoritative_token_counts: Iterable[AuthoritativeTokenCount] = (),
) -> RequestInventory: ...
```

All public models are frozen. The builder owns parsing, duplicate key detection, RFC 6901 escaping, hashing, counting, semantic enrichment, and validation.

## Invariants

- The decoded JSON string is the exact value. SHA256 and byte count use its UTF 8 bytes. Character count uses Unicode code points.
- The root string uses pointer `""`. Object tokens escape `~` as `~0` and `/` as `~1`. Array tokens use decimal indexes.
- Duplicate decoded object keys fail the build because RFC 6901 cannot identify both values.
- Leaves sort by pointer. Equivalent object member order produces the same inventory order.
- Raw traversal does not depend on `InternalRequest`. Parser gaps cannot hide leaves.
- Provider rules may set API role and TM IR section only when the raw shape proves them.
- Every leaf starts with provenance `unknown`, low confidence, and explicit evidence. Role and position never imply `static-harness` or `user-authored`.
- Supplied annotations must name an existing string leaf. Duplicate or conflicting annotations fail the build.
- The default token count is `ceil(character_count / 4)`. It is labelled `estimate` with its method.
- An authoritative count must bind the pointer, leaf digest, count, and source method. Mismatches fail the build.
- Aggregate display records retain constituent pointers and digests. They cannot serve as native preimages.

## Module map

`api/src/transport_matters/request_inventory.py` owns the complete public contract and private implementation. Existing storage, adapters, and overlay code remain unchanged. Future reports, controlled captures, and overlay authoring call the builder.

One module keeps the call chain flat. If the file approaches 700 lines, private mechanics can move without changing the public entry point.

## Synthesis decision

Candidate A is the base. The cross judge scored it 23/25. Candidate B scored 15/25.

The design grafts Candidate B's raw body digest and stronger authoritative token identity. It rejects Candidate B's seven file package, public stage functions, public annotator registry, synthetic group digest, warning based stale annotations, and confidence based conflict resolution.

The implementation will omit public parser stages. A caller gets one complete inventory or a boundary error.

## Tradeoffs accepted

- We reject duplicate keys to preserve unique standard pointers.
- We keep provenance unknown until evidence supports a stronger claim.
- We accept estimated leaf token counts until a provider supplies an isolated authoritative measurement.
- We compute inventories on demand. This read only slice does not persist `request.inventory.json`.

## Verification

Focused tests will prove pointer escaping, duplicate key rejection, Unicode counts, deterministic order, annotation validation, token quality, conservative provenance, Claude and Codex semantic labels, and the five leaf aggregation regression.

The final gate will run the builder against the two issue captures and independently compare every pointer, value, and digest.

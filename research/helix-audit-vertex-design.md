---
title: "Helix Audit Vertex: Native Provenance and Accountability Design"
type: research
tags: [helix, audit, provenance, architecture, context-matters, attention-matters, critic]
summary: "Architecture design for Helix's audit/provenance capabilities. Audit as cross-cutting infrastructure, not a fourth adapter. Graduated maturity levels, CRITIC accountability via am fitness alignment, and gap documentation."
status: active
source: software-architect
confidence: high
created: 2026-03-22
updated: 2026-03-22
---

## Design Thesis

Audit is not a fourth adapter. It is a property of the context substrate itself.

Helix's three adapters each transform raw context into an optimal representation: cm stores structured entries, am holds geometric identity, mdm indexes full-text documents. Audit does not transform context into a representation. Audit records what happened to context and why. Adding it as a peer adapter would violate the adapter contract, which exists to answer "what does this agent know?" Audit answers a fundamentally different question: "what changed, who caused it, and can we trust it?"

The correct architectural position: audit is cross-cutting infrastructure that every adapter participates in, coordinated at the Helix proxy level.

```
Agent  -->  helix CLI  -->  Proxy Agent  -->  Adapters (cm, am, mdm)
                                |
                           Audit Layer
                           (cross-cutting)
                                |
                           Provenance Store
```

## 1. Provenance for Context Entries

### What to Track

Every context operation through Helix produces a provenance record. The record answers five questions:

| Question | Field | Example |
|----------|-------|---------|
| What happened? | `operation` | `store`, `recall`, `update`, `forget`, `supersede`, `conflict_resolve` |
| Who initiated it? | `agent_id` | `agent:rust-engineer` |
| In what session? | `session_id` | `f1ebae7b-27ba-4935-90a7-3d51f0ac43d2` |
| Authorized how? | `authorization` | `policy:write-path-curation`, `human:stuart`, `agent:nancy` |
| Derived from what? | `derivation` | `[entry_id_1, entry_id_2]` or `source:conversation` |

### Where It Already Exists

cm-store already has a `mutations` table (migration 005) that records `action`, `source`, `timestamp`, and full before/after snapshots within the same transaction as every write. This is the foundation. It tracks what happened and where the write originated (`mcp`, `cli`, `web`, `helix`).

What it lacks:

1. **Agent identity.** `source` tells you the channel (mcp vs helix), not the agent. A `helix` source could be any agent routed through the proxy. The mutations table needs an `agent_id` field.

2. **Session binding.** No `session_id` links a mutation to the conversation that produced it. Without this, cross-session provenance requires timestamp correlation, which is fragile.

3. **Authorization chain.** No record of whether the write was quality-gated by the proxy LLM, approved by a human, or delegated by an orchestrator. The proxy's curation decision ("I routed this to cm because...") is lost.

4. **Derivation lineage.** When the proxy merges two overlapping entries or synthesizes from recall results, the relationship to source entries is not captured. Honcho's `source_ids` pattern applies here.

### Schema Extension

The mutations table should evolve to:

```sql
ALTER TABLE mutations ADD COLUMN agent_id    TEXT;     -- who initiated
ALTER TABLE mutations ADD COLUMN session_id  TEXT;     -- conversation context
ALTER TABLE mutations ADD COLUMN auth_type   TEXT;     -- 'proxy_curation' | 'human' | 'policy' | 'agent_delegation'
ALTER TABLE mutations ADD COLUMN auth_id     TEXT;     -- identity of the authorizer
ALTER TABLE mutations ADD COLUMN derived_from TEXT;    -- JSON array of source entry IDs
ALTER TABLE mutations ADD COLUMN proxy_rationale TEXT; -- proxy's curation reasoning (optional)
```

The `proxy_rationale` field deserves explanation. When the Helix proxy decides to route a write to cm rather than mdm, or merges two entries rather than creating a new one, that reasoning is the most valuable provenance for debugging context quality. It costs storage but pays for itself when CRITIC needs to understand why the context graph looks the way it does.

### Adapting for am and mdm

am and mdm do not currently have mutation tables. Two options:

**Option A: Adapter-local mutation tables.** Each adapter maintains its own mutation log following the same schema. Helix queries all three when constructing a provenance timeline.

**Option B: Centralized provenance store.** A single provenance table at the Helix level records operations across all adapters, with an `adapter` field discriminating cm/am/mdm.

Recommendation: **Option B.** The provenance timeline is inherently cross-adapter. A single recall might hit cm and mdm. A write might be routed to cm after the proxy considered am. Splitting provenance across adapters makes cross-adapter correlation harder and duplicates schema evolution effort.

The centralized store does not replace cm's existing mutations table. cm's mutations table serves cm-internal needs (before/after snapshots for rollback, cm-web dashboard). The Helix-level provenance store serves cross-adapter audit needs. They can share a write path without one depending on the other.

## 2. Context Operation Audit Trail

### Which Operations Are Auditable

Every operation that crosses the Helix proxy boundary should produce an audit record:

| Operation | Why Auditable |
|-----------|---------------|
| `recall` | Agents act on recalled context. If the recall was incomplete or misleading, the audit trail shows what was returned and what was available but filtered. |
| `save` | The write that created context. Provenance of the entry. |
| `update` | What changed and why the proxy chose update over supersede. |
| `forget` | Soft deletion. Who requested it, from what session. |
| `supersede` | Entry replacement chain. The old entry's ID links to the new. |
| `conflict_resolve` | When the proxy resolves overlapping entries. The merge strategy, the entries involved, the resulting entry. |
| `routing_decision` | When the proxy routes a write to a specific adapter. Which adapters were considered, why the chosen one won. |
| `quality_gate` | When the proxy rejects a write for quality reasons. What was rejected and why. |

### Read-Path Audit

This is the less obvious but more important half. Write-path audit tracks what went into the store. Read-path audit tracks what came out and how it was shaped.

When an agent calls `helix recall`, the proxy:
1. Queries Tantivy for candidates
2. Curates via LLM (reranks, filters, synthesizes)
3. Returns the shaped result

The audit record for a recall should capture:
- **Candidates returned by Tantivy** (entry IDs, scores)
- **What the LLM filtered out** (entry IDs excluded and brief reason)
- **What the LLM synthesized** (the final response, or its hash for storage efficiency)
- **Token budget** (requested vs used)

This is expensive to store for every recall. The graduated maturity levels (section 7) address this: at L1, only record that a recall happened and what was returned. At L2, record the candidate set. At L3, record the full curation reasoning.

## 3. Gap Documentation

### The Problem

When a context write fails, the system currently logs an error and the agent receives a failure response. The failure is not part of the context model. Future agents querying the same scope have no way to know that information was lost.

AHP's GapRecord pattern addresses this directly: when recording fails, a GapRecord is written on the next success documenting what was lost.

### Design for Helix

A context gap is a first-class entity in the provenance store:

```sql
CREATE TABLE context_gaps (
    id           TEXT PRIMARY KEY,           -- UUID v7
    timestamp    TEXT NOT NULL,
    agent_id     TEXT,
    session_id   TEXT,
    adapter      TEXT NOT NULL,              -- which adapter failed
    operation    TEXT NOT NULL,              -- what was attempted
    reason       TEXT NOT NULL,              -- structured reason code
    payload_hash TEXT,                       -- BLAKE3 hash of what was lost (if available)
    payload_hint TEXT,                       -- human-readable description of lost content
    resolved     INTEGER NOT NULL DEFAULT 0, -- 1 if the gap was later filled
    resolved_by  TEXT                        -- entry ID that filled the gap
);
```

Structured reason codes:

| Code | Meaning |
|------|---------|
| `ADAPTER_UNAVAILABLE` | The target adapter was not responding |
| `WRITE_REJECTED` | Proxy quality gate rejected the write |
| `CONFLICT_UNRESOLVED` | Overlapping entries detected, no resolution available |
| `BUDGET_EXCEEDED` | Token budget for curation exhausted |
| `SERIALIZATION_FAILURE` | Content could not be serialized for the target adapter |
| `TIMEOUT` | Write operation timed out |

The `payload_hint` field is critical. It tells future agents not just that something was lost, but approximately what. "Attempted to store a decision about retry strategy for the auth service" is far more useful than "write failed."

When an agent calls `helix recall` and the scope has unresolved gaps, the response should include a `gaps` field:

```json
{
  "results": [...],
  "gaps": [
    {
      "timestamp": "2026-03-22T14:30:00Z",
      "hint": "Decision about auth service retry strategy",
      "reason": "ADAPTER_UNAVAILABLE"
    }
  ]
}
```

The agent now knows what it does not know.

### Fail-Open Discipline

AHP's fail-open principle applies to the audit system itself. If the provenance store fails to record an audit event, that failure must not block the context operation. The audit system is the observer, not the gatekeeper. A gap record for the gap record is written on next success.

## 4. Tamper Detection

### The Question

Does Helix need cryptographic tamper evidence (hash chains, Ed25519 signing)? Or is a lighter-weight approach sufficient?

### Analysis

**Arguments for full cryptographic tamper evidence:**
- CRITIC mutations change the system genome. If someone tampers with the mutation history, CRITIC cannot verify its own evolution.
- Cross-agent accountability requires proving that Agent A's context write was not modified between write and Agent B's recall.
- If Helix is deployed in regulated environments, cryptographic audit trails may be a compliance requirement.

**Arguments against:**
- Helix is currently a single-owner, single-machine system. The threat model for tamper is low. The owner is the attacker and the victim simultaneously.
- Full hash chains add operational complexity (crash recovery, chain rotation, key management) that is not justified by the current deployment model.
- AHP exists as a protocol for this exact purpose. If cryptographic audit is needed later, Helix can emit AHP-compatible records via an interceptor without internalizing the protocol.

### Recommendation: Lightweight Now, Compatible Later

**L1 (now): Content hashing with BLAKE3.**

cm already uses BLAKE3 for content deduplication (`content_hash` on entries). Extend this to the provenance store: every audit record includes a `content_hash` of the operation payload. This enables detecting content modification (someone changed an entry's body without updating the hash) without the operational weight of hash chains.

Additionally, store a `prev_record_hash` on each provenance record within an adapter scope. This creates a lightweight chain that detects insertion or deletion of audit records, without requiring canonical serialization or cross-SDK byte parity.

```sql
ALTER TABLE provenance ADD COLUMN content_hash     TEXT;  -- BLAKE3 of operation payload
ALTER TABLE provenance ADD COLUMN prev_record_hash TEXT;  -- BLAKE3 of previous record in this scope
```

**L2 (when needed): AHP-compatible checkpoint emission.**

At defined intervals, compute a Merkle root over recent provenance records and store it. This is AHP's checkpoint pattern adapted to Helix's needs. No Ed25519 signing required unless Helix moves to a multi-operator deployment.

**L3 (if regulated): Full AHP interceptor.**

If Helix ever needs L3 tamper evidence (external witness attestation, signed chains), implement an AHP interceptor on the Helix proxy. This emits AHP records for every context operation without changing Helix's internal architecture. The AHP chain becomes an external audit artifact, not an internal dependency.

This graduated approach means Helix does not carry the operational burden of cryptographic audit until it needs it, while maintaining a clean upgrade path.

## 5. CRITIC Accountability

### The Problem

CRITIC evolves the system genome. It proposes mutations to skills, prompts, agent definitions, MCP servers, context configuration, and orchestration patterns. These mutations change how every agent in the system behaves.

Two accountability requirements:

1. **Mutation provenance.** Every genome mutation must record: what was changed, what the before/after states were, what hypothesis motivated it, what test was run, what the measured outcome was, and who approved it.

2. **Value alignment proof.** CRITIC uses am as the fitness function. Every mutation should be justified in terms of am's value landscape, not just metric improvement. The audit trail must capture this justification so the owner can verify that the system is evolving toward their vision, not just toward efficiency.

### Design

CRITIC mutations are a distinct provenance category. They do not flow through the normal context write path (they modify the genome, not the context). They need their own audit structure:

```
Mutation Record:
  id:                 UUID v7
  timestamp:          ISO 8601
  genome_unit:        "agent_definition/brand-guardian/prompt"
  mutation_type:      "prompt_refinement" | "config_tuning" | "skill_addition" | ...
  hypothesis:         "Specific tone parameters will reduce correction rate"
  before_state_hash:  BLAKE3 of genome unit before mutation
  after_state_hash:   BLAKE3 of genome unit after mutation
  before_state:       full content (or reference to versioned file)
  after_state:        full content (or reference to versioned file)
  test_id:            reference to experiment that validated this
  baseline_metric:    { "tone_corrections_per_10_tasks": 7 }
  mutated_metric:     { "tone_corrections_per_10_tasks": 2 }
  am_alignment:       "Aligns with 'direct, technically precise' voice
                       identity (am salience score 0.87 for this region)"
  approved_by:        "human:stuart" | "policy:low-risk-auto-approve"
  approval_timestamp: ISO 8601
  phase:              1 | 2 | 3 | 4  (maps to CRITIC evolution phases)
  confidence:         "low" | "medium" | "high"
  review_after:       "50 tasks"
  reverted:           false
  reverted_by:        null
  revert_reason:      null
```

### am Alignment Verification

The `am_alignment` field is where audit meets identity. When CRITIC proposes a mutation:

1. CRITIC queries am for the value landscape relevant to the genome unit being mutated.
2. CRITIC articulates how the proposed mutation aligns with (or at minimum does not contradict) the retrieved values.
3. The audit record captures both the am query result and the alignment reasoning.

If CRITIC proposes a mutation that improves a metric but the am alignment field is empty or contradicts the value landscape, that is a signal for owner review regardless of the mutation's risk tier.

This creates a verifiable chain: owner shapes am -> am provides fitness landscape -> CRITIC justifies mutations against that landscape -> audit records the justification -> owner can verify alignment.

### Genome Versioning

Each adopted mutation increments a genome version. The version history is itself an audit trail:

```
v0.8.2 -> v0.8.3 (EXP-041: adapter weight tuning)
v0.8.3 -> v0.8.4 (EXP-042: dependency query weighting)
v0.8.4 -> v0.8.3 (REVERT: EXP-042 caused side effects in architecture queries)
```

The revert case is important. When a mutation is reverted, the revert is a new mutation record, not a deletion of the original. Both the adoption and the revert are audit evidence. The system learns from failures.

## 6. Cross-Agent Context Accountability

### The Problem

Agent A stores context via `helix save`. Agent B recalls that context via `helix recall`. If Agent B acts on inaccurate context that Agent A deposited, what accountability chain exists?

### Current State

cm's mutations table records that a `helix` source performed a `create` action. But it does not record which agent wrote the entry. The Helix proxy performs quality curation on the write path, but the proxy's identity (not the originating agent's identity) is what cm sees.

### Design

The accountability chain requires three components:

**1. Write attribution.** Every context entry carries an `authored_by` field (the originating agent) and a `curated_by` field (the Helix proxy session that quality-gated it). The proxy's curation does not erase the originating agent's identity.

**2. Read receipts.** When Agent B recalls context authored by Agent A, a lightweight read receipt is recorded in the provenance store:

```
Read Receipt:
  entry_id:    the recalled entry
  reader_id:   "agent:rust-engineer"
  session_id:  Agent B's session
  timestamp:   when the recall occurred
  context:     "recalled as part of query 'auth retry strategy'"
```

Read receipts are optional (L2+ maturity). They enable answering: "Who consumed this context? If we discover the entry was wrong, which agents need to be informed?"

**3. Impact tracing.** When context is superseded or marked incorrect, the system can trace forward through read receipts to identify agents that may have acted on the now-invalid information. This is not automated remediation (too complex, too risky). It is a diagnostic capability: "Here are the sessions that consumed the corrected entry."

### The Helix Proxy as Accountability Boundary

The proxy occupies a unique position. It sees both sides of every transaction: the originating agent on one side, the adapter on the other. The proxy should maintain a request-scoped context that flows through the entire operation:

```
RequestContext:
  request_id:     UUID v7 (unique per helix call)
  agent_id:       the calling agent
  session_id:     the agent's session
  operation:      recall | save | conflicts
  timestamp:      request start
  adapter_calls:  [] (populated as the proxy routes to adapters)
```

This context is the spine of the provenance record. Every adapter call within a single helix operation shares the same `request_id`, enabling reconstruction of the full operation lifecycle.

## 7. Conformance/Maturity Levels

### Graduated Audit Levels

AHP's L1/L2/L3 progression maps well to Helix's needs. Three levels, each building on the previous:

**L1: Operation Log (Baseline)**

| Capability | What It Provides |
|-----------|------------------|
| Mutation log | cm's existing mutations table with agent_id and session_id extensions |
| Gap records | First-class context gaps with structured reason codes |
| Content hashing | BLAKE3 on entries and provenance records |
| Lightweight chain | `prev_record_hash` on provenance records within adapter scope |

Cost: Low. Adds a few columns to existing tables and a new context_gaps table. No LLM calls, no cross-adapter coordination.

**L2: Provenance Trail**

Everything in L1, plus:

| Capability | What It Provides |
|-----------|------------------|
| Centralized provenance store | Cross-adapter audit timeline |
| Read-path audit | Candidate sets and filtering decisions on recall |
| Read receipts | Who consumed which context entries |
| Proxy rationale capture | Curation reasoning for routing and quality decisions |
| CRITIC mutation records | Full mutation provenance with am alignment |
| Periodic checkpoints | Merkle root over recent provenance records |

Cost: Medium. The proxy rationale capture requires storing LLM output for audit purposes, which adds storage. Read receipts add a write per recall per entry. Checkpoints add periodic computation.

**L3: Verifiable Audit**

Everything in L2, plus:

| Capability | What It Provides |
|-----------|------------------|
| Signed checkpoints | Ed25519 signing of Merkle roots |
| AHP-compatible export | Context operations exportable as AHP records |
| OTLP telemetry | Provenance records mapped to OpenTelemetry spans |
| Impact tracing | Forward trace from corrected entries to consuming sessions |
| Cross-system correlation | W3C Trace Context headers on helioy-bus messages |

Cost: High. Key management, AHP integration, OTLP infrastructure. Justified only when Helix operates in multi-operator or regulated environments.

### Default Configuration

Single-owner deployments start at L1. The owner can enable L2 features individually (provenance store without read receipts, for example). L3 is opt-in and requires explicit infrastructure setup.

```toml
# helix.config.toml
[audit]
level = 1                    # 1, 2, or 3

[audit.l2]
read_receipts = false        # per-entry read tracking
proxy_rationale = true       # capture curation reasoning
checkpoint_interval = 100    # provenance records between checkpoints

[audit.l3]
signing_key = "~/.helix/audit.key"
ahp_export = false
otlp_endpoint = ""
```

## 8. Integration Architecture

### Not a Fourth Adapter

To restate the opening thesis with specifics: the audit layer is infrastructure that the proxy coordinates, not an adapter that the proxy routes to.

The adapter contract is:

```
recall(query, budget) -> []Entry
store(entry) -> id
update(id, patch) -> id
delete(id) -> void
capabilities() -> []string
```

Audit does not satisfy this contract. You do not `recall` audit records the same way you recall context. You do not `store` provenance the way you store a decision. The access patterns are fundamentally different: context is queried by semantic relevance, provenance is queried by timeline, by entry, by agent, or by session.

### Where Audit Lives

```
helix-audit/
  provenance.rs      -- centralized provenance store (SQLite)
  gaps.rs            -- context gap management
  critic_log.rs      -- CRITIC mutation audit records
  checkpoint.rs      -- Merkle root computation (L2+)
  export.rs          -- AHP/OTLP export (L3)

helix-proxy/
  request_context.rs -- per-request audit context
  audit_hooks.rs     -- before/after hooks on proxy operations
```

The proxy owns the request context lifecycle. Before routing to adapters, it creates a `RequestContext`. After each adapter call returns, it emits a provenance record. If an adapter call fails, it emits a gap record. The audit layer never intercepts or modifies the data flow. It observes.

### Interaction with cm's Existing Mutations Table

cm's mutations table continues to serve cm-internal needs. The Helix provenance store is a superset: it records cross-adapter operations and proxy-level decisions that cm's table cannot capture. For cm operations, both the cm mutations table and the Helix provenance store are written in the same logical operation, but they are not coupled. cm can operate without Helix audit. Helix audit can reconstruct cm history from its own records.

### Interaction with am

am is write-only for the owner, read-only for agents. Audit for am tracks:

- Owner write operations (what was fed into the manifold, when, from what source)
- Agent read operations (which agents queried am, what regions of the manifold were accessed)
- CRITIC's am queries for fitness alignment (what the CRITIC read from am when justifying mutations)

am does not need its own mutation table. The Helix provenance store handles this because am operations flow through the Helix proxy.

### Interaction with mdm

mdm is a search index, not a primary store. Audit for mdm tracks:

- Index updates (when documents are re-indexed, what changed)
- Search operations (what was queried, what was returned)

Lightweight compared to cm and am. At L1, only index update events. At L2, search operations.

## Trade-Off Summary

| Decision | What We Gain | What We Give Up |
|----------|-------------|-----------------|
| Cross-cutting infrastructure over fourth adapter | Clean separation of concerns; adapters stay focused on representation | No single "audit adapter" to query; provenance queries go through a separate surface |
| Centralized provenance store over per-adapter tables | Cross-adapter correlation; single schema evolution | Storage duplication with cm's mutations table; additional write per operation |
| BLAKE3 chains over full AHP integration | Lightweight tamper detection; no key management; no binary format complexity | Cannot prove authorship (no signing); cannot prove to third parties (no witness) |
| Gap records as first-class entities | Agents know what they don't know; system incompleteness is visible | Storage overhead for failed operations; adds a `gaps` field to recall responses |
| Proxy rationale capture | CRITIC can understand and evaluate curation decisions; debugging context quality becomes possible | Storage cost for LLM output on every curated operation; potential sensitivity of reasoning content |
| Graduated maturity levels | Deploy what you need, no more; clear upgrade path | Configuration complexity; L1 deployments lack cross-adapter provenance |

## Implementation Priority

1. **Extend cm mutations table** with `agent_id`, `session_id`, `auth_type`, `derived_from`. Low effort, immediate value. Already decided as P1 infrastructure.
2. **Context gaps table and recall integration.** Agents knowing what they don't know is a novel capability that no competitor offers.
3. **Helix proxy RequestContext.** The spine that makes everything else possible. Must exist before the centralized provenance store.
4. **Centralized provenance store (L2).** Cross-adapter audit timeline.
5. **CRITIC mutation records.** Required when CRITIC tooling begins. Can be designed now, implemented when CRITIC is built.
6. **Read receipts, checkpoints, export (L2/L3).** Later. Justified by deployment scale or regulatory requirements.

## Open Questions

1. **Provenance retention policy.** How long should provenance records be kept? Context entries have scopes and TTLs. Should provenance records inherit the entry's lifecycle, or have their own retention rules?

2. **Proxy rationale storage cost.** Storing the LLM's curation reasoning for every operation could be expensive. Should rationale be stored only for write operations (where curation decisions have lasting impact) and sampled for reads?

3. **Gap resolution workflow.** When a gap is later filled, who marks it resolved? The agent that retries the write? The proxy automatically if a subsequent write covers the same content? Manual operator action?

4. **CRITIC audit storage location.** CRITIC mutations affect the system genome, which lives in files (prompts, configs, code). Should the CRITIC audit store be alongside the genome (git-tracked) or in the provenance database?

5. **Multi-machine provenance.** If Helix ever runs distributed (multiple proxy instances), the provenance store needs conflict resolution. SQLite is single-writer. Does this push toward PostgreSQL for the provenance store, or does the single-owner model make this premature?

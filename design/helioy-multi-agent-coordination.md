---
title: "Helioy Multi-Agent Coordination Design"
type: design
tags: [helioy, multi-agent, brainstorm, attention-matters, nancy, helioy-bus]
summary: "Three interconnected designs from the 2026-03-07 brainstorm session: epoch-aware retention, brainstorm protocol, and specialized agent architecture"
status: active
created: 2026-03-07
updated: 2026-03-07
project: helioy
related: [helioy-architecture, nancyr-architecture]
confidence: high
---

# Helioy Multi-Agent Coordination Design

Produced through three consecutive brainstorms across 5 agents (attention-matters, fmm, nancyr, nancy, mdcontext, helioy-plugins). Each brainstorm refined the coordination model. The third brainstorm applied the protocol designed in the second, validating it in practice.

## 1. Epoch-Aware Retention for AM GC

### Problem

AM's garbage collector treats `activation_count` as the sole survival signal. Fresh data ingested via `am_ingest` starts at zero activation and is immediately GC-eligible before any query tests its value. The blog corpus (780K occurrences, 6,900 neighborhoods) exposed this: reference papers were being collected before they could prove useful.

### Design

Layered defense with four mechanisms:

```toml
[retention]
grace_epochs = 50           # epoch-based primary grace
retention_days = 3           # timestamp backstop for idle projects
min_neighborhoods = 100      # floor: skip GC entirely below this
recency_weight = 2.0         # linear epoch bonus in eviction scoring
```

**GC order of operations:**

1. Early return if total neighborhoods < `min_neighborhoods`
2. Exclude neighborhoods where `epoch >= max_epoch - grace_epochs`
3. Exclude neighborhoods newer than `retention_days`
4. Evict by composite score: `activation_count + (epoch/max_epoch * recency_weight)` ASC

**Key decisions:**

- **Epoch AND timestamp grace.** Epoch protects during active bursts (100 ingestions in one hour). Timestamp protects during idle periods (project untouched for a week). They solve different failure modes.
- **`NeighborhoodType::Ingested`** for bulk-imported data via `am_ingest`. Uses existing `neighborhood_type` column. No schema migration.
- **Linear recency weighting** for v1. Adaptive half-life tied to query cadence deferred until evidence shows static weight is insufficient.
- **`min_neighborhoods` not `min_episodes`** because episodes are containers. A single episode can hold hundreds of neighborhoods. Content density is what matters.

### Implementation Status

Implemented by attention-matters. 285 tests pass, clippy clean. All four retention parameters wired through. `NeighborhoodType::Ingested` applied during `am_ingest`. No schema changes. Three PRs:

1. Grace epoch filter + min_neighborhoods floor
2. retention_days backstop + composite eviction score
3. NeighborhoodType::Ingested + RetentionPolicy config

## 2. Multi-Agent Brainstorm Protocol

### Problem

The first brainstorm (epoch-aware retention) produced good outcomes but with significant waste: redundant synthesis messages (4 agents each writing "here's where we agree"), ceremonial closers (4 agents saying "thread closed"), and echo proposals. Roughly 60% of message volume was redundant agreement.

### Three-Phase Protocol

| Phase          | Who posts                        | Rule                                                                           |
| -------------- | -------------------------------- | ------------------------------------------------------------------------------ |
| **Propose**    | All agents with relevant context | Independent proposals, no reading others first. 3-5 key points, max 200 words. |
| **Synthesize** | Designated synthesizer only      | Merged design, flagged divergences, opens dissent window.                      |
| **Dissent**    | Only agents with corrections     | Silence = consent. One closer from synthesizer.                                |

**Message conventions:**

- `[topic:short-name]` on every message for filtering
- `[mode:proposals|reactions|decision]` on the opening broadcast
- `[phase:synthesis]` on the synthesis message
- Synthesizer declared in the opening broadcast

**Synthesizer selection:** The agent closest to the implementation. They understand constraints best and will bear the implementation cost. If nobody is implementing (pure design), the questioner or orchestrator synthesizes. The synthesizer should NOT also be a proposer in the same round to maintain neutrality.

**Silence-as-consent:** After the synthesizer posts, agents respond ONLY with corrections or genuinely new information. No "+1" messages. Silence within the dissent window means agreement. The synthesizer closes with "No dissent. Proceeding."

### Disagreement Resolution

| Tier | Scope                                       | Who decides                      |
| ---- | ------------------------------------------- | -------------------------------- |
| 1    | Change lives in one repo                    | Technical owner of that codebase |
| 2    | Cross-cutting (spans repos)                 | Orchestrator picks the path      |
| 3    | Requirements, priorities, product direction | Escalate to Stuart               |

Timeout: 2 rounds of unresolved back-and-forth auto-escalates to the next tier.

Cross-repo interface disagreements: both owners must agree on the boundary contract.

### Validation

The protocol was applied to its own design (brainstorm 2: agent profiles) and to brainstorm 3 (specialized agents). Results:

| Brainstorm           | Messages | Redundant | Protocol |
| -------------------- | -------- | --------- | -------- |
| Retention (freeform) | ~25      | ~10 (40%) | None     |
| Agent profiles       | ~8       | 0         | Good     |
| Specialized brains   | ~8       | 0         | Strong   |

~60% reduction in message volume with equivalent output quality.

### am_salient Trigger Checklist

Seven canonical triggers for marking conscious memory:

1. **Correction** from the user (old memory was wrong)
2. **Constraint discovery** (invisible walls revealed by failure)
3. **Decision with rejected alternatives** (the rejection reasoning is more valuable than the choice)
4. **Cross-project wiring** (how components connect across repos)
5. **Terminology anchors** (naming/definition corrections)
6. **Non-obvious root causes** (post-bugfix, only if surprising)
7. **Time-saving workflow patterns** (reusable process knowledge)

Ritual checkpoints: post-brainstorm (highest yield), post-bugfix (if non-obvious), session-end (lightweight scan for missed triggers). Agent checklist, not automation.

## 3. Specialized Agent Architecture

### Problem

Every agent session starts cold. Agents query one shared AM brain, get generic recall, and re-derive context by reading files. Domain knowledge does not compound across sessions.

### Design: Isolated Subconscious, Shared Conscious Overlay

```
Per-agent brain.db (subconscious)     Shared conscious overlay (am_salient)
+-----------------+                   +----------------------------+
| am episodes     |                   | Architecture decisions     |
| am queries      |  <-- isolated --> | User preferences           |
| am feedback     |                   | Cross-repo wiring          |
| am buffer       |                   | Brainstorm outcomes        |
+-----------------+                   +----------------------------+
  per agent, private                    global, all agents query
```

**Brain isolation rationale (from attention-matters):** IDF weights, activation counts, and drift rates are calibrated to a single manifold's statistics. Mixing two manifolds produces meaningless scores. The bus is the cross-agent query protocol. AM is the within-agent memory protocol.

**Conscious memory stays shared:** am_salient writes are global by design. Architecture decisions, user preferences, and cross-project wiring span agents. Per-agent brains handle domain-specific conversation history. The conscious layer is the institutional memory.

### Agent Roster

| Agent             | Owns                      | Brain accumulates                                                    |
| ----------------- | ------------------------- | -------------------------------------------------------------------- |
| attention-matters | am-core, am-store, am-cli | Memory engine internals, GC tuning, manifold geometry                |
| fmm               | fmm crate                 | Parser quirks, indexing edge cases, language support                 |
| nancyr            | nancyr workspace          | Orchestration architecture, coordination patterns, process knowledge |
| nancy             | nancy bash MVP            | Coordination protocols, bus patterns, skill design                   |
| mdcontext         | mdcontext crate           | Markdown indexing, search ranking, consumer-side AM patterns         |
| helioy-plugins    | plugin crate + skills     | Skill authoring, MCP tool design, trigger optimization               |

**Rejected agents:**

- **research-synthesizer** (unanimous rejection): its proposed role (cross-domain connective tissue, brainstorm outcomes) duplicates am_salient's conscious layer. A codeless agent accumulates noise without structural grounding.
- **blog agent** (unanimous rejection): blog is a task, not a domain. Any agent with the my-voice skill can generate content.

### Agent Profile Schema

Each agent declares a profile loaded from config at registration:

```toml
# .helioy/agent.toml
[profile]
owns = ["attention-matters"]
consumes = ["fmm", "helioy-plugins"]
capabilities = ["am", "fmm", "linear-server"]
domain = ["memory", "geometric"]
skills = ["brainstorm", "knowledge-base"]
```

Stored in the bus registry via extended `register_agent`. `list_agents` returns profiles. Routing uses `owns ∪ consumes` for respondent selection, `owns` only for synthesizer selection.

### Brain Seeding

One-time migration from the existing shared brain:

1. Filter existing episodes by relevance to the agent's `owns` + `consumes` fields
2. Export via `am export --filter-episodes`
3. Import into the new per-agent brain.db via `am import`
4. After seeding, brains diverge independently

Brain path convention: `~/.helioy/brains/{agent-name}.db`

### Implementation Path

1. Create `~/.helioy/brains/` directory structure
2. Each agent's `.helioy/agent.toml` sets `data_dir` pointing to its brain.db
3. Seed brains via filtered export/import
4. AM `--project` flag already scopes operations; wire agent config to set scope automatically

No AM code changes needed. The `AM_DATA_DIR` environment variable already supports multiple brain files.

### Dependencies

- Bus profile schema (from Section 2) provides `owns`/`consumes` fields for routing
- Bus topic threading and nudge throttling (helioy-bus implementing)
- Brain seeding requires the existing shared brain to have sufficient episode history

## Open Items

- helioy-bus implementing topic field, nudge throttling, and profile registry
- `list_agents(owns="X")` field-level filtering deferred to v2
- Adaptive recency half-life for GC deferred until linear weighting proves insufficient
- helioy-plugins suggested a "site" agent for helioy.com/blog/docs; low priority, revisit if content complexity grows

---
title: "cass-memory: Procedural Memory Extraction from AI Coding Agent Sessions"
type: research
tags: [procedural-memory, cross-agent, session-extraction, playbook, confidence-decay, TypeScript, Bun]
summary: "Deep code review of cass_memory_system (cm), a TypeScript/Bun CLI that extracts procedural memory from AI coding agent sessions via a three-layer cognitive architecture: episodic (cass search) -> working (diary) -> procedural (playbook with confidence-tracked rules)."
status: active
source: github-researcher
confidence: high
created: 2026-04-24
updated: 2026-04-24
---

## Executive Summary

`cass-memory` (CLI: `cm`) is a TypeScript/Bun tool by Jeffrey Emanuel (336 GitHub stars) that sits atop the CASS search engine (reviewed separately in `session-history-indexing-and-search-cass.md`). Where CASS indexes and searches raw session files, `cass-memory` extracts reusable rules from those sessions, tracks their effectiveness with a confidence decay system, and makes them available to any coding agent before each task. The system implements a three-layer cognitive architecture: episodic memory (raw sessions via CASS), working memory (structured diary entries), and procedural memory (playbook bullets with feedback scoring). Cross-agent learning is the key value proposition: a debugging pattern discovered in Cursor is automatically available to Claude Code on the next session.

## Architecture

### Three-Layer Memory Model

```
Episodic (cass binary)
  Session JSONL/JSON from 19 agent formats
  Full-text + semantic search via CASS
      |
      | cassExport() -> sanitized text
      v
Working Memory (diary entries)
  LLM extracts structured fields:
    accomplishments, decisions, challenges, preferences, keyLearnings
  Cross-agent enrichment via CASS search
  Stored as JSON files in ~/.cass-memory/diary/
      |
      | reflectOnSession() -> PlaybookDelta[]
      v
Procedural Memory (playbook)
  YAML file at ~/.cass-memory/playbook.yaml
  Bullets with: content, category, scope, maturity, feedback events
  Confidence decay (90-day half-life)
  Maturity progression: candidate -> established -> proven -> deprecated
  Anti-pattern inversion when rules prove harmful
```

### File Layout (src/, 17.7K lines total)

| File | LOC | Role |
|---|---|---|
| `utils.ts` | 3432 | Kitchen-sink utilities: keyword extraction, scoring, hashing, validation, output formatting |
| `cm.ts` | 1197 | CLI entry point (commander), 26+ subcommands |
| `cass.ts` | 1175 | CASS binary wrapper: search, export, timeline, SSH remote search |
| `llm.ts` | 1131 | LLM abstraction via Vercel AI SDK (6 providers + CLI fallback) |
| `semantic.ts` | 1023 | Embedding pipeline (Xenova/MiniLM or Ollama), cosine similarity, cache |
| `types.ts` | 921 | Zod schemas for every domain type |
| `curate.ts` | 723 | Playbook mutation: dedup, conflict detection, feedback, inversion |
| `playbook.ts` | 703 | YAML read/write, merge global+repo playbooks |
| `diary.ts` | 661 | Diary generation (LLM or fast heuristic mode) |
| `tracking.ts` | 544 | Processed session log to avoid reprocessing |
| `orchestrator.ts` | 454 | End-to-end reflection loop: discover -> export -> diary -> reflect -> validate -> curate -> save |
| `reflect.ts` | 438 | LLM prompt for extracting PlaybookDelta[] from diary |
| `trauma.ts` | 455 | "Project Hot Stove" safety guards (dangerous command patterns) |
| `scoring.ts` | 230 | Confidence decay math, maturity state machine |
| `sanitize.ts` | 244 | Secret redaction (AWS keys, tokens, passwords, SSH keys) |
| `commands/` | 26 files | Individual CLI command implementations |

### Data Flow: The Reflection Pipeline

The core value creation happens in `orchestrateReflection()` (orchestrator.ts):

1. **Discovery**: `findUnprocessedSessions()` queries CASS timeline for sessions not yet in `ProcessedLog`
2. **Export**: `cassExport(sessionPath, "text")` gets sanitized session text via the CASS binary
3. **Diary generation**: `generateDiary()` calls LLM (or fast heuristic) to extract structured fields
4. **Cross-agent enrichment**: If enabled, searches CASS for related sessions from other agents
5. **Reflection**: `reflectOnSession()` sends diary + existing playbook + CASS history to LLM, gets `PlaybookDelta[]`
6. **Validation**: Each delta validated against CASS history evidence
7. **Curation**: `curatePlaybook()` applies deltas with dedup, conflict detection, feedback tracking
8. **Persistence**: Atomic write to playbook YAML under file lock

### Key Design Decision: CASS as External Dependency

`cass-memory` does not parse session files directly. It shells out to the `cass` binary (the Rust tool reviewed in the separate research doc) for all session access: search, export, timeline. This creates a hard dependency but avoids reimplementing 19 format parsers. The system degrades gracefully when CASS is absent, operating in "playbook-only" mode with no historical context.

## Session Parsing

### What Formats Are Supported

CM does not parse session files itself. It relies on the CASS binary (19 formats: Claude Code JSONL, Codex CLI, Cursor, Aider, etc.). However, CM has fallback parsers in two places:

**`cass.ts` fallback** (`handleSessionExportFailure()`): When `cass export` fails, CM reads the raw file directly:
- `.jsonl`: Parses line-by-line, extracts `[role] content` from each JSON object
- `.json`: Looks for `messages`, `conversation`, or `turns` arrays
- `.md`: Passes through as-is

**`diary.ts` format handling** (`formatRawSession()`): Understands Codex CLI format (`type: "response_item"` with `payload.content` arrays), Claude multi-block content format, and standard `{role, content}` format.

**Agent detection** (`extractSessionMetadata()`): Infers agent from path substrings:
- `.claude` -> "claude"
- `.cursor` -> "cursor"  
- `.codex` -> "codex"
- `.aider` -> "aider"
- `.pi/agent/sessions` -> "pi_agent"

### Content Coercion

`coerceContent()` in cass.ts recursively handles nested content structures that differ across agents:
- String: pass through
- Array: map and join (Claude's multi-block `[{type: "text", text: "..."}]`)
- Object with `text`, `content`, `message`: extract text field
- Codex CLI blocks (`type: "input_text"` / `type: "output_text"`): extract `.text`

## The Procedural Memory Extraction Pipeline

### Step 1: Diary Generation (diary.ts)

Two modes:

**LLM mode** (default): Sends session content to LLM with prompt asking for:
- `status`: success/failure/mixed
- `accomplishments`: Specific completed tasks with file/function names
- `decisions`: Design choices with rationale
- `challenges`: Problems, errors, blockers
- `preferences`: User style revelations
- `keyLearnings`: Reusable insights
- `tags`, `searchAnchors`

Session content is truncated to 50K chars before LLM call.

**Fast mode** (`CASS_MEMORY_LLM=none`): No LLM call. Uses heuristics:
- `inferOutcome()`: Regex patterns for error/success keywords
- `extractFirstUserMessage()`: First user message as task description
- `extractFilePaths()`: Regex for file extensions mentioned

### Step 2: Cross-Agent Enrichment (diary.ts)

When `crossAgent.enabled && crossAgent.consentGiven` in config:
1. Extract keywords from diary `keyLearnings + challenges + accomplishments`
2. Search CASS with top 5 keywords
3. Filter hits to exclude current agent, apply allowlist
4. Attach as `relatedSessions` on diary
5. Write privacy audit log entry

### Step 3: Reflection (reflect.ts)

Iterative LLM extraction (default 3 iterations):
1. Format existing playbook bullets (grouped by category with maturity icons)
2. Format CASS history (related sessions from diary)
3. Send to LLM with reflector prompt asking for `PlaybookDelta[]`

**Delta types** (discriminated union on `type`):
- `add`: New rule with content, category, kind, scope, tags
- `helpful`: Existing bullet proved useful (by ID)
- `harmful`: Existing bullet caused problems (by ID, with reason)
- `replace`: Update existing bullet content
- `deprecate`: Mark existing bullet as outdated
- `merge`: Combine multiple bullets into one

**Strict mode schemas**: All LLM-facing Zod schemas use `.strict()` and `.nullable()` (not `.optional()`) for OpenAI structured output compatibility.

Deltas are deduplicated across iterations using content hashing.

### Step 4: Validation (validate.ts)

Each proposed delta is validated against CASS history:
- Search CASS for evidence supporting/contradicting the rule
- LLM scores confidence and verdict: ACCEPT, REJECT, REFINE, ACCEPT_WITH_CAUTION
- If REFINE, the LLM suggests refined rule text which replaces the original

### Step 5: Curation (curate.ts)

The curation engine applies deltas to the playbook with extensive safety checks:

**Deduplication** (three tiers):
1. Exact content hash match (O(1) via Map)
2. Jaccard similarity above threshold (default 0.85), using pre-tokenized sets
3. If duplicate found, reinforce with helpful feedback event instead of adding

**Conflict detection** (heuristic, not LLM):
- Negation conflict: one says "do", the other says "avoid", with high term overlap
- Opposite directives: "must" vs "avoid" on similar subjects
- Scope conflict: "always" vs "except when" on overlapping topics
- Uses pre-computed marker flags (NEGATIVE_MARKERS, POSITIVE_MARKERS, EXCEPTION_MARKERS)

**Anti-pattern inversion**: When a rule accumulates harmful feedback exceeding the threshold (default 3), and harmful > 2x helpful:
- Positive rules are inverted: `"Cache auth tokens" -> "AVOID: cache auth tokens. Marked harmful 3 times"`
- Negative rules are simply deprecated (inverting a negative would create a positive, which would be confusing)

**Maturity state machine** (scoring.ts):
```
candidate -> established -> proven -> deprecated
                                          ^
                        (auto-deprecate if score < -threshold)
```

Transitions based on decayed feedback counts:
- candidate: < 3 total feedback events
- established: >= 3 events, harmful ratio < 30%
- proven: >= 10 helpful, harmful ratio < 10%
- deprecated: harmful ratio > 30% with enough signal, or score < -pruneHarmfulThreshold

### Step 6: Scoring and Decay (scoring.ts)

```
effectiveScore = (decayedHelpful - 4 * decayedHarmful) * maturityMultiplier
```

Where `decayedValue = 0.5^(ageDays / halfLifeDays)` with configurable half-life (default 90 days).

Maturity multipliers: candidate=0.5, established=1.0, proven=1.5, deprecated=0.

This means a rule marked helpful 10 times 6 months ago with no recent validation has effective score ~2.5 (10 * 0.25 * 1.0). A new rule with 2 helpful marks scores 1.0 (2 * 1.0 * 0.5). Recent, actively validated rules dominate.

## Cross-Agent Memory Sharing

### How Agent A Learns from Agent B

The mechanism is straightforward: all agents' sessions are indexed by the same CASS instance. When CM generates context for a task, it:

1. Searches CASS with task keywords (no agent filter by default)
2. Returns `historySnippets` from any agent
3. During reflection, the LLM sees related sessions from all agents

Cross-agent enrichment is **opt-in** (`privacy enable` command) and requires explicit consent. An allowlist controls which agents participate.

### Remote Machine Support

CM supports SSH-based remote CASS queries (`remoteCass` config). Multiple machines can be searched in parallel, with results merged and scored alongside local results. Remote hits carry `origin: { kind: "remote", host: "workstation" }`.

### Privacy Controls

- Master toggle: `crossAgent.enabled` (default false)
- Explicit consent: `crossAgent.consentGiven` (separate from enabled)
- Agent allowlist: `crossAgent.agents` (empty = all allowed when enabled)
- Audit log: JSONL file tracking every cross-agent enrichment event
- Repo-level config cannot override: crossAgent, remoteCass, apiKey, baseUrl, cassPath, playbookPath

## LLM Provider Architecture (llm.ts)

### Provider Support

Uses Vercel AI SDK (`ai` package) for unified interface across 6 providers:
- OpenAI (default model: gpt-4o-mini)
- Anthropic (default: claude-sonnet-4-20250514)
- Google (Gemini 1.5 Flash)
- Ollama (llama3.2:3b)
- AWS Bedrock (Claude Sonnet via credential chain)
- CLI fallback: shells out to `claude`, `codex`, or `gemini` CLI tools, piping prompt via stdin

**Fallback chain**: If primary provider fails, automatically tries next available provider in order: anthropic -> openai -> google -> bedrock -> ollama -> cli.

**Budget tracking**: Per-call cost recording with daily ($0.10) and monthly ($2.00) limits. Calls blocked when budget exceeded.

**CLI provider**: Novel approach. When no API key is available, CM shells out to installed CLI tools (claude -p, codex, gemini), pipes the prompt via stdin, and parses JSON from stdout. Includes markdown fence stripping, retry with "fix your JSON" prompts, and 2-minute timeout.

### Structured Output

All LLM calls use `generateObject()` (structured output) with Zod schemas, not free-form text generation. This ensures type-safe extraction. Schemas are strict-mode compatible for OpenAI (every property required, nullable instead of optional, additionalProperties: false).

## Safety Systems

### Secret Sanitization (sanitize.ts)

Before any content reaches the LLM or is stored, it passes through `sanitize()`:
- AWS access keys and secret keys
- Bearer tokens
- Generic API keys and tokens (preserving JSON structure)
- Private key blocks (RSA, EC, DSA, OPENSSH)
- Passwords in common formats
- GitHub PATs (classic and fine-grained)
- Slack tokens
- Database connection strings with credentials
- User-configurable extra patterns (regex or substring)

Pattern construction uses dynamic string building to avoid tripping static secret scanners.

### Trauma Guard ("Project Hot Stove", trauma.ts)

Mechanical safety guards against catastrophic commands:
- 25+ dangerous patterns: `rm -rf /`, `DROP DATABASE`, `terraform destroy`, `git push --force`, `dd of=/dev/`, etc.
- Scans CASS history for sessions containing apology keywords combined with destructive commands
- Can install as Claude Code hook or git pre-commit hook
- Trauma entries have severity (CRITICAL/FATAL), scope (global/project), and can be healed or removed

## Playbook Storage and Format

### YAML Structure

```yaml
schema_version: 2
name: playbook
description: Auto-generated by cass-memory
metadata:
  createdAt: "2025-12-08T..."
  lastReflection: "2025-12-09T..."
  totalReflections: 5
  totalSessionsProcessed: 12
deprecatedPatterns: []
bullets:
  - id: "b-a1b2c3"
    content: "For React hooks, test effects separately with renderHook"
    category: "testing"
    scope: "global"
    kind: "stack_pattern"
    type: "rule"
    maturity: "established"
    state: "active"
    helpfulCount: 5
    harmfulCount: 0
    feedbackEvents: [...]
    sourceSessions: ["~/.claude/sessions/abc.jsonl"]
    sourceAgents: ["claude"]
    tags: ["react", "testing", "hooks"]
    embedding: [0.123, ...]  # MiniLM-L6-v2
    effectiveScore: 3.75
    createdAt: "2025-12-08T..."
    updatedAt: "2025-12-09T..."
```

### Two-Layer Playbook

Global (`~/.cass-memory/playbook.yaml`) + repo-level (`.cass/playbook.yaml`). Merged for context queries, but mutations route to the correct layer based on where the referenced bullet lives. Repo config is security-restricted (cannot override sensitive paths, API keys, or sanitization settings).

## Semantic Search (semantic.ts)

### Embedding Pipeline

Two backends:
- **Xenova** (default): ONNX Runtime with `@xenova/transformers`, model `all-MiniLM-L6-v2` (~23MB download, cached in `~/.cache/huggingface/`). Includes WASM runtime fixup for Bun standalone binaries.
- **Ollama**: HTTP calls to `/api/embed` endpoint

Embeddings are cached in `~/.cass-memory/embeddings/bullets.json` with content-hash invalidation. Batch processing (32 texts per batch) with fallback to per-text embedding on failure.

Used for: `similar` command (find related playbook bullets), dedup during curation, context relevance scoring.

## Patterns Worth Adopting for Helioy

### 1. Confidence Decay with Half-Life

The scoring system is the most transferable pattern. Rules that haven't been validated recently lose influence automatically. This prevents stale knowledge from dominating. The implementation is clean: each feedback event carries a timestamp, and `calculateDecayedValue()` applies exponential decay.

**For attention-matters**: This is directly applicable to the salience scoring layer. Geometric memory entries could carry feedback events with timestamps, and salience could decay without revalidation. The 90-day half-life and 4x harmful multiplier are reasonable starting defaults.

### 2. Anti-Pattern Inversion

When a rule proves harmful, automatically generating an inverted warning is a clever way to preserve institutional knowledge about what NOT to do. This is richer than simple deletion.

**For context-matters**: Feedback entries with kind='feedback' could carry a `was_inverted_from` pointer to track lineage.

### 3. Playbook Delta as Discriminated Union

The `PlaybookDelta` type (add/helpful/harmful/replace/deprecate/merge) with Zod discriminated union is a clean contract between the LLM extraction layer and the curation layer. The LLM produces typed deltas; curation applies them idempotently.

**For Helioy**: This pattern could apply to how any LLM-extracted knowledge flows into context-matters or attention-matters. Define the mutation vocabulary as a discriminated union, let the LLM produce typed mutations, curate before persisting.

### 4. Graceful Degradation Architecture

Every external dependency (CASS, LLM, semantic model, remote hosts) has a degradation path:
- No CASS: playbook-only mode
- No LLM: fast heuristic extraction
- No semantic model: keyword-only search
- Remote host down: local-only results

Degradation info is surfaced in the `degraded` field of every response, with `suggestedFix` arrays. This is a good UX pattern for Helioy components.

### 5. Structured LLM Output via Zod Schemas

All LLM calls use Vercel AI SDK's `generateObject()` with strict Zod schemas. No free-form text parsing. The strict-mode compliance (nullable not optional, additionalProperties false) ensures compatibility with OpenAI's structured output mode. This is worth adopting for any LLM extraction in Helioy.

### 6. Security-Conscious Config Merging

The repo-level config security model is well-designed: repos can add sanitization patterns but cannot disable sanitization, override API keys, redirect API calls, or change CLI commands. This prevents malicious repo configs from exfiltrating data.

## What Not to Adopt

1. **External binary dependency for core functionality**: Requiring a separate Rust binary (CASS) makes the system harder to install and debug. Helioy's history-matters should own its own parsing.

2. **LLM-in-the-hot-path for every reflection**: Each session reflection makes multiple LLM calls (diary + reflect + validate). At scale this is expensive and slow. Consider batch processing or cheaper extraction heuristics first, LLM only for refinement.

3. **3400-line utils.ts**: This file does everything from keyword extraction to output formatting to path resolution. Helioy should keep utilities decomposed by concern.

4. **YAML for structured data with embeddings**: Playbook YAML files grow large with embedding vectors. SQLite or binary format would be more appropriate for data with numeric arrays.

5. **Global mutable state in semantic.ts**: `embedderPromise`, `embedderModel`, `embeddingBackend` are module-level mutable variables. This makes testing brittle and prevents concurrent configurations.

## Relationship to Helioy Components

| CM Concept | Helioy Analog | Notes |
|---|---|---|
| Episodic Memory (CASS) | history-matters (planned) | CASS indexes raw sessions; history-matters would do the same for Helioy |
| Working Memory (Diary) | Not yet built | Structured session summaries could feed attention-matters |
| Procedural Memory (Playbook) | context-matters | CM playbook bullets ≈ cx_store entries with kind='lesson' |
| Cross-Agent Enrichment | helioy-bus | CM shells out to CASS for cross-agent search; Helioy has the bus for real-time inter-agent communication |
| Confidence Decay | attention-matters salience | AM's geometric memory on S3 already has salience; decay could be an explicit half-life |
| Trauma Guard | Could be a skill | Dangerous pattern blocking could be a helioy-tools skill |
| Semantic Search | attention-matters | AM already has geometric similarity; CM's MiniLM embeddings are a simpler alternative |

### Key Architectural Difference

CM is a post-hoc extraction system: sessions happen, then CM processes them offline. Helioy's attention-matters and context-matters operate in real-time during sessions. This is a fundamental difference. CM's approach requires less integration but produces delayed value. Helioy's approach provides immediate context but requires tighter agent integration.

CM's offline reflection loop (discover unprocessed sessions -> extract -> curate) could complement Helioy's real-time system. After a session ends, a scheduled task could run reflection-style extraction to distill lessons into context-matters, producing higher-quality entries than real-time buffering alone.

## Sources Consulted

- `src/cm.ts`: CLI entry point, 26+ commands
- `src/types.ts`: Full Zod schema for every domain type
- `src/cass.ts`: CASS binary integration, remote SSH search
- `src/config.ts`: Config loading with security-restricted repo overrides
- `src/orchestrator.ts`: End-to-end reflection pipeline
- `src/reflect.ts`: LLM reflector prompt and delta extraction
- `src/curate.ts`: Playbook mutation with dedup/conflict/inversion
- `src/diary.ts`: Diary generation (LLM and heuristic modes)
- `src/llm.ts`: 6-provider LLM abstraction with fallback chain
- `src/semantic.ts`: Embedding pipeline (Xenova/Ollama)
- `src/scoring.ts`: Confidence decay and maturity state machine
- `src/trauma.ts`: Project Hot Stove safety patterns
- `src/sanitize.ts`: Secret redaction patterns
- `src/commands/context.ts`: Context assembly for agent consumption
- `src/commands/onboard.ts`: Guided onboarding workflow
- `.cass/playbook.yaml`: Repo-level playbook structure
- `SKILL.md`: Agent-facing documentation
- `README.md`: Architecture overview and feature description
- `package.json`: Dependencies and build config

## Open Questions

1. **Embedding quality for code rules**: MiniLM-L6-v2 is a general-purpose sentence transformer. How well does it capture similarity between code-specific rules like "test React hooks with renderHook" vs "use testing-library's renderHook for hook tests"? No evaluation was found.

2. **Scaling characteristics**: The playbook is a single YAML file. With hundreds of rules, YAML parsing and embedding recomputation on every context query could become slow. No benchmarks were found.

3. **LLM extraction reliability**: The reflector depends on the LLM producing valid typed deltas. The strict schemas help, but there's no published accuracy evaluation of how well the LLM extracts genuinely useful rules vs. generic filler.

4. **Offline-first viability**: The fast mode (no LLM) uses crude heuristics. How much value does it provide compared to LLM extraction? This determines whether the system is useful without API costs.

5. **Cross-agent enrichment effectiveness**: The privacy-gated cross-agent feature searches CASS with keywords from the diary. The relevance of these cross-agent results is unvalidated. Are keywords from one agent's diary useful for finding relevant sessions from a different agent on a different codebase?

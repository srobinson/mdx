---
title: "Worktree Conflict Detector"
type: design
tags: [helioy, helioy-bus, fmm, multi-agent, conflict-detection, worktree, architecture]
summary: "Background daemon that detects file, region, and API surface conflicts across concurrent git worktrees and nudges agents to coordinate before merge-time failures"
status: proposed
created: 2026-03-16
updated: 2026-03-16
project: helioy
related: [helioy-multi-agent-coordination, helioy-architecture, fmm-architecture]
confidence: medium
---

# Worktree Conflict Detector

## Problem Statement

The helioy ecosystem runs multiple Claude Code agents in parallel, each in its own git worktree of the same repo. Two agents can independently modify the same file, the same function, or break each other's API assumptions. Today nothing detects these collisions until merge time or, worse, until CI reveals a runtime failure from an incompatible signature change.

The cost of late detection is high. A merge conflict discovered after an agent has made 40 minutes of dependent changes forces either manual resolution or a full rebase, both of which disrupt the agent's context window and waste tokens.

## Conflict Taxonomy

Three tiers, ordered by detection difficulty and blast radius.

### Tier 1: Region Overlap

Two worktrees modify the same function or class method in the same file. Merge conflict is guaranteed. Detection is straightforward through line-range intersection.

### Tier 2: File Overlap

Two worktrees modify different functions in the same file. Merge conflict is probable (git's 3-way merge heuristics fail on nearby edits and structural changes). Detection requires only file-level diff comparison.

### Tier 3: API Surface Break

Agent A changes an exported function's signature (parameters, return type, name). Agent B calls that export from a different file. The merge succeeds cleanly because the files do not overlap. The runtime fails because the call site no longer matches the definition. This is the critical tier that no existing tooling catches before CI.


## Component Architecture

### Placement Decision

**Option A: Standalone daemon** (recommended)
A Python process that runs alongside the bus server, polling worktrees on a fixed interval. Communicates conflicts through helioy-bus `send_message`. Lives in `helioy-bus/server/conflict_detector.py`.

**Option B: Integrated into helioy-bus**
Add detection logic directly into the bus server process, triggered by heartbeat cycles.

**Option C: Git hook (post-commit)**
Each worktree runs detection after every commit.

| Criterion | Standalone daemon | Bus integration | Git hook |
|-----------|------------------|-----------------|----------|
| Polling frequency control | Full control | Coupled to heartbeat | Only on commit |
| Catches uncommitted work | Yes (uses working tree diff) | Yes | No |
| Process isolation | Clean failure boundary | Shared failure domain | Per-worktree |
| Deployment complexity | One more process to manage | Zero additional process | Hook distribution |
| Can detect cross-worktree conflicts | Yes, central view | Yes, central view | Requires coordination |

**Decision: Standalone daemon.** It provides the central cross-worktree view needed for all three tiers, catches uncommitted work (where most agent edits live before commit), and fails independently of the bus server. The git hook option fails on the most important requirement: detecting conflicts before commit, while agents are still actively editing.

### Where It Lives

```
helioy-bus/
  server/
    bus_server.py           # existing
    proxy.py                # existing
    conflict_detector.py    # new: daemon entry point
    detection/
      __init__.py
      worktree.py           # git worktree discovery and diff extraction
      region.py             # tier 1: line-range intersection
      file.py               # tier 2: file-level overlap
      api_surface.py        # tier 3: fmm-powered signature analysis
    nudge/
      __init__.py
      formatter.py          # actionable nudge message construction
      negotiation.py        # conflict resolution protocol state
```

The detector imports from `bus_server.py` for the `send_message` function and database access. It does not modify the bus server's MCP interface.


## Data Flow

```
                                 ┌──────────────────┐
                                 │   fmm index       │
                                 │  (per-worktree)   │
                                 └────────┬─────────┘
                                          │ fmm_dependency_graph
                                          │ fmm_file_outline
                                          │ fmm_lookup_export
                                          │
┌───────────┐    git diff     ┌───────────┴───────────┐
│ Worktree A ├───────────────→│                       │
└───────────┘                 │   Conflict Detector   │
                              │      (daemon)         │
┌───────────┐    git diff     │                       │
│ Worktree B ├───────────────→│  1. Discover worktrees│
└───────────┘                 │  2. Collect diffs     │
                              │  3. Pairwise compare  │
┌───────────┐    git diff     │  4. fmm enrichment    │
│ Worktree C ├───────────────→│  5. Classify tier     │
└───────────┘                 │  6. Format nudge      │
                              └───────────┬───────────┘
                                          │
                                    send_message()
                                          │
                              ┌───────────┴───────────┐
                              │     helioy-bus         │
                              │   (inbox + nudge)      │
                              └───────────────────────┘
```

### Poll Cycle (target: every 5 seconds)

1. **Discover active worktrees.** Run `git worktree list --porcelain` from any worktree to enumerate all linked trees. Cross-reference with the bus agent registry to identify which worktrees have active agents (filtering out stale or idle trees).

2. **Collect diffs.** For each active worktree, run `git diff --name-only` (unstaged) and `git diff --cached --name-only` (staged) against the common merge base. This produces a set of touched files per worktree. Cache the result; skip worktrees whose HEAD and working tree mtime have not changed since the last poll.

3. **Pairwise file comparison.** For each pair of worktrees, compute the intersection of their touched-file sets. Any non-empty intersection triggers tier 2 (file overlap) analysis at minimum.

4. **Region analysis (tier 1).** For overlapping files, run `git diff -U0` in each worktree to extract changed line ranges. Parse the hunk headers (`@@ -a,b +c,d @@`). If any two worktrees' changed ranges overlap within the same file, classify as tier 1.

5. **API surface analysis (tier 3).** For files touched by worktree A, query fmm for exports and their signatures. For each modified export, query fmm's dependency graph to find downstream callers. If any downstream caller lives in a file touched by worktree B, flag as tier 3.

6. **Deduplicate and debounce.** Maintain a conflict state map keyed by `(worktree_pair, file, tier)`. Only send a nudge when a conflict is newly detected or has escalated in tier. Do not re-nudge for the same conflict within a configurable window (default: 120 seconds).


## Detection Algorithms

### Tier 1: Region Overlap

```
Input: file F, worktree W1, worktree W2
  hunks_w1 = parse_hunk_headers(git diff -U0 W1 -- F)
  hunks_w2 = parse_hunk_headers(git diff -U0 W2 -- F)

  for h1 in hunks_w1:
    for h2 in hunks_w2:
      if ranges_overlap(h1.new_start, h1.new_end, h2.new_start, h2.new_end):
        yield RegionConflict(file=F, w1=W1, w2=W2, range1=h1, range2=h2)
```

Enrichment: use `fmm_file_outline` to resolve which exported symbol each overlapping range belongs to. The nudge message names the symbol, not just the line numbers.

### Tier 2: File Overlap

```
Input: touched_files_w1, touched_files_w2
  overlap = touched_files_w1 & touched_files_w2

  for file in overlap:
    if not has_region_overlap(file, w1, w2):
      yield FileConflict(file=file, w1=w1, w2=w2)
```

This tier requires no fmm involvement. It is a pure set intersection.

### Tier 3: API Surface Break

This is the high-value detection that justifies the component's existence.

```
Input: worktree W1 (modifier), all other worktrees
  modified_files_w1 = get_modified_files(W1)

  for file in modified_files_w1:
    # Get the file outline from W1's working tree
    outline_before = fmm_file_outline(file, worktree=base_commit)
    outline_after  = fmm_file_outline(file, worktree=W1)

    changed_exports = diff_exports(outline_before, outline_after)
    # changed_exports: list of (export_name, change_type)
    # change_type: signature_changed | renamed | removed

    for export in changed_exports:
      # Find all files that import this export
      graph = fmm_dependency_graph(file)
      downstream_files = graph.downstream

      for other_wt in other_worktrees:
        touched_by_other = get_modified_files(other_wt)
        # Check if any downstream file is touched OR used by the other worktree
        # The dangerous case: downstream file is NOT touched (no merge conflict)
        # but the call site exists and will break
        untouched_callers = downstream_files - touched_by_other
        if untouched_callers:
          yield ApiSurfaceBreak(
            modifier=W1,
            export=export,
            callers=untouched_callers,
            affected_worktree=other_wt
          )
```

**Key insight for tier 3:** The most dangerous conflicts are the ones where the caller file is NOT modified by anyone. Both worktrees merge cleanly. The caller still references the old signature. CI catches it; nothing else does.

### fmm Integration Requirements

Tier 3 detection depends on fmm being able to answer two questions:

1. **What exports changed?** Compare `fmm_file_outline` output between the merge base and the worktree's working copy. This requires fmm to run its tree-sitter parse against arbitrary file paths, not just its indexed working directory. Today fmm indexes one root directory. To support multiple worktrees, one of these adaptations is needed:

   - **(a) Run fmm on-demand parse per worktree.** The `fmm_file_outline` tool already does on-demand tree-sitter parsing (documented as "no index rebuild needed"). If fmm can accept absolute file paths pointing into other worktrees, this works without changes.
   - **(b) Run fmm index per worktree.** Each worktree gets its own `.fmm` index directory. The detector queries each independently. Higher disk/CPU cost but provides full fmm capability per worktree.
   - **(c) Diff exports via git + tree-sitter directly.** The detector embeds its own minimal tree-sitter parser for export extraction, bypassing fmm. Avoids coupling but duplicates logic.

   **Recommendation: option (a) first, fall back to (c) if fmm's path handling proves restrictive.** Option (b) is reserved for cases where full dependency graph queries per worktree become necessary.

2. **Who calls the changed export?** `fmm_dependency_graph(file)` returns downstream dependents. `fmm_lookup_export(name)` resolves a symbol to its definition file. Together these answer "if I change `processOrder` in `orders.py`, which files call it?" This works against the primary fmm index (which tracks the canonical repo), and that is sufficient because downstream callers change infrequently relative to the export itself.


## Nudge Message Format

Nudges are sent via `helioy-bus send_message` with a structured topic and content format.

### Topic Convention

```
conflict:{repo}:{conflict_id}
```

Example: `conflict:nancyr:a3f2b1c8`

The conflict_id is a stable hash of `(worktree_pair, file, tier)` so that follow-up messages (escalation, resolution) thread together.

### Message Content

```markdown
## Conflict detected: {tier_label}

**File:** `{file_path}`
**Your change:** {description of what the recipient modified}
**Conflicting change:** {description of what the other agent modified}
**Other agent:** {agent_id}
**Risk:** {tier-specific risk description}

### Suggested action
{tier-specific recommendation}

### To acknowledge
Reply to this thread with your plan: "I will rebase", "I will coordinate with {other_agent}", or "I own this file, other agent should wait".
```

### Tier-Specific Content

**Tier 1 (region overlap):**
> Risk: Merge conflict guaranteed. You and `{other_agent}` are editing `{symbol_name}` in `{file}`.
> Suggested action: One of you should finish and merge first. Coordinate via bus to decide who goes first.

**Tier 2 (file overlap):**
> Risk: Merge conflict likely. You are editing `{your_symbols}` while `{other_agent}` is editing `{their_symbols}` in the same file.
> Suggested action: Review each other's changes after the first merge to resolve potential context conflicts.

**Tier 3 (API surface break):**
> Risk: Clean merge, runtime failure. `{other_agent}` is changing the signature of `{export_name}` in `{file}`. Your file `{caller_file}` calls this export and will break silently.
> Suggested action: Wait for `{other_agent}` to merge, then update your call site in `{caller_file}` before merging.


## Negotiation Protocol

Nudges alone are insufficient. Agents need a lightweight protocol to resolve conflicts without human intervention.

### States

```
DETECTED  -->  ACKNOWLEDGED  -->  RESOLVED
              |                    ^
              +--> DEFERRED ------+
```

- **DETECTED:** Detector sends the initial nudge. Both agents receive it.
- **ACKNOWLEDGED:** An agent replies with their plan. The reply is sent to the topic thread so the other agent sees it.
- **DEFERRED:** An agent replies "I will defer" and pauses work on the conflicting file. The other agent proceeds.
- **RESOLVED:** The conflict no longer appears in the detector's diff analysis (one agent merged, or the conflicting changes were removed).

### Protocol Messages (agent to bus)

Agents respond to conflict nudges by replying to the same topic:

```
CLAIM: I own {file}. I will merge first.
DEFER: I will wait for {other_agent} to merge {file}.
COORDINATE: Let's sync. I need {specific_thing} from your changes.
RESOLVED: My changes to {file} are merged. Proceed.
```

### Priority Resolution

When both agents send `CLAIM` for the same file, the detector breaks the tie:

1. The agent who modified the file first (earlier first-diff timestamp) gets priority.
2. If timestamps are tied, the agent with fewer total modified files gets priority (smaller changeset is easier to rebase).
3. The losing agent receives a follow-up nudge: "Priority given to {other_agent}. Please defer or coordinate."

This is advisory, not enforced. Agents can ignore it. The detector continues monitoring and will re-nudge if the conflict persists.


## Performance Budget

The detector must not interfere with agent work. Target budget per poll cycle:

| Operation | Expected cost | Mitigation |
|-----------|--------------|------------|
| `git worktree list` | <10ms | One call per cycle, not per worktree |
| `git diff --name-only` per worktree | <50ms each | Skip unchanged worktrees (mtime cache) |
| `git diff -U0` for overlapping files | <20ms per file | Only run for tier 1 candidates |
| `fmm_file_outline` for tier 3 | <100ms per file | Only run for files with modified exports |
| `fmm_dependency_graph` for tier 3 | <100ms per file | Cache; dependency graph changes slowly |
| Pairwise comparison | O(W^2 * F) | W is small (2-6 worktrees), F is small (touched files) |

**Total budget per cycle: <500ms for a typical 4-worktree setup.** The 5-second poll interval provides 10x headroom.

### Caching Strategy

- **Worktree diff cache:** Store `(worktree_path, HEAD_sha, working_tree_mtime) -> touched_files`. Invalidate when HEAD or mtime changes.
- **fmm result cache:** Store `(file_path, content_hash) -> outline/graph`. fmm's own caching may handle this; verify before adding a layer.
- **Conflict state cache:** Store `(pair, file, tier) -> last_nudge_time`. Prevents nudge storms.


## Startup and Lifecycle

### Launch

The conflict detector starts as a companion to the warroom. Two options:

- **warroom.sh integration:** `warroom.sh` spawns the detector as a background process after creating agent panes. The detector's PID is written to `~/.helioy/bus/conflict_detector.pid` for lifecycle management.
- **justfile target:** `just detect` or `just warroom-with-detection`. Preferred for explicitness.

### Shutdown

- Clean shutdown on SIGTERM/SIGINT.
- Writes final state to the conflict state cache so restarts resume without re-nudging.
- If no active worktrees remain (all agents unregistered), the detector exits on its own.

### Health

The detector registers itself on the bus as a system agent with `agent_type: "conflict-detector"`. It heartbeats like any other agent. Other agents can query `list_agents` to verify detection is active.


## Open Questions

1. **fmm path flexibility.** Can `fmm_file_outline` accept absolute paths pointing into worktrees other than its indexed root? If not, the tier 3 algorithm needs a workaround (option c: embedded tree-sitter parser). This is the single highest-risk assumption in the design.

2. **Uncommitted vs. committed changes.** The design polls working tree diffs (uncommitted changes). Agents that commit frequently will have smaller working tree diffs, potentially causing the detector to miss conflicts between committed-but-unmerged changes. The detector should also compare each worktree's branch HEAD against the merge base, not just the working tree.

3. **Cross-repo conflicts.** The current design assumes all worktrees belong to the same repository. The helioy ecosystem has multiple repos (fmm, nancyr, helioy-bus, etc.). Cross-repo API surface breaks (e.g., fmm changes an export that helioy-bus imports) are out of scope for v1 but should be considered for v2.

4. **Agent compliance.** The negotiation protocol is advisory. If an agent ignores a nudge and merges anyway, the other agent discovers the conflict through normal git operations. The detector should track "ignored nudges" as a signal for future priority resolution, but enforcement is a policy decision, not a technical one.

5. **Merge base selection.** Which branch is the "base" for diffing? If all worktrees branch from `main`, the merge base is clear. If worktrees branch from each other or from different points on main, the detector needs to compute pairwise merge bases via `git merge-base`. This adds complexity but is necessary for correctness.

6. **fmm index staleness.** The fmm index reflects the state of its indexed root directory. If worktree A modifies a file and the fmm index has not rebuilt, `fmm_dependency_graph` may return stale downstream information. The on-demand `fmm_file_outline` parse avoids this for export detection, but the dependency graph query does not. Acceptable for v1 since dependency relationships change less frequently than function bodies.

7. **Scale ceiling.** The pairwise comparison is O(W^2). For the current helioy setup (2-6 concurrent worktrees), this is negligible. At 20+ worktrees, the detector should switch to a file-indexed approach: maintain a global map of `file -> set(worktrees)` and only analyze files that appear in 2+ worktree sets.


## Tradeoffs

### Chosen: Polling over event-driven

Polling every 5 seconds is simpler and more portable than filesystem watchers (inotify/fsevents). The tradeoff is a 0-5 second detection latency. For a system where the response is a nudge message to an LLM agent (which operates on minute-scale cycles), 5 seconds of latency is irrelevant.

### Chosen: Advisory nudges over hard blocks

The detector sends information, not orders. It cannot block a merge or prevent a commit. This preserves agent autonomy and avoids the failure mode where a buggy detector stops all progress. The tradeoff is that agents can ignore nudges, but the system is designed so that ignoring a nudge has natural consequences (merge conflicts, CI failures) rather than silent corruption.

### Chosen: Central daemon over distributed hooks

A single process with a global view of all worktrees is architecturally simpler than N hooks coordinating through shared state. The tradeoff is a single point of failure. If the detector crashes, agents lose conflict detection but continue working normally. This is acceptable because detection is an optimization, not a correctness requirement.

### Chosen: fmm dependency data over custom static analysis

Reusing fmm's existing export/dependency index avoids duplicating static analysis logic. The tradeoff is a runtime dependency on fmm's index freshness and path handling. If fmm proves too rigid for multi-worktree use, the fallback (embedded tree-sitter for export extraction only) is scoped and manageable.


## ADR-001: Conflict Detector Deployment Model

### Status
Proposed

### Context
Multiple concurrent AI agents in git worktrees create conflicts that surface too late. We need a detection mechanism that integrates with the existing helioy-bus and fmm infrastructure without adding operational complexity.

### Decision
Deploy the conflict detector as a standalone Python daemon that lives in the helioy-bus repository, polls git worktrees on a fixed interval, and sends nudges through helioy-bus. It uses fmm for API surface analysis (tier 3) and raw git diffs for file/region analysis (tiers 1 and 2).

### Consequences
- Easier: adding detection without modifying the bus server; independent failure domain; clear separation of detection logic from messaging infrastructure.
- Harder: one more process to manage; requires fmm to handle paths outside its indexed root (or a fallback parser); negotiation protocol adds conversational overhead to agents.

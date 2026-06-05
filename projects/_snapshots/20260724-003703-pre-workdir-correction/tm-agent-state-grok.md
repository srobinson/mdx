# TM Agent-State: Versioned Schema Drift Pipeline + Closed-Source Extraction

**Author:** grok (warroom lean: pipeline + extractability + generalization)  
**Date:** 2026-07-10  
**Mode:** ideation only (no repo writes)  
**Pinned harness versions:** Claude Code `2.1.205`, Codex `0.144.0`  
**Topic:** `tm-agent-state-ideation`

---

## 0. Executive thesis

**Headline pipeline idea: SCHEMA-LOCK with FAIL-LOUD DRIFT GATES.**

Ship a re-runnable per-`(harness, version)` acquisition job that builds a
versioned **Harness Manifest**, diffs it against the last known good, and
**fails the build / `transport-matters doctor`** when any *state-relevant*
event, tool, control subtype, or stop_reason is unmapped. Golden fixtures pin
behavior per version. Mappers never silently ignore unknown high-signal types.

Today TM's activity parser already drops unrecognized Claude record types and
only maps `AskUserQuestion` into `needs-you`. Real corpus types like
`attachment`, `mode`, `permission-mode`, `queue-operation` exist in volume and
would currently trip (or be misclassified relative to) the known-set gate.
Local permission and plan gates often never appear as wire `stop_reason`s;
they live on the PTY plane and in control/hook side-channels.

---

## 1. Probe results: what is actually extractable

### 1.1 Claude Code 2.1.205 (CLOSED)

| Artifact | Location | Extractable schema? |
|---|---|---|
| Install form | Native **Mach-O arm64** at `~/.local/share/claude/versions/2.1.205` (~226MB, Bun-compiled) | **No `.d.ts`, no JS source tree, no published TypeScript types** |
| Version history on disk | `~/.local/share/claude/versions/{2.1.179,198,202,203,204,205}` | Free multi-version binary set for **string-set diffs** |
| Global npm `@anthropic-ai/claude-code` | Empty / unused on this machine; symlink points at native binary | N/A |
| Stale npm name `claude-code` | Thin pointer package saying "not the package you're looking for" | Zero schema |
| Public docs | [Hooks reference](https://code.claude.com/docs/en/hooks) | **Structured, version-annotated event schemas** (best first-class public surface) |
| Public source | GitHub issues request a stable transcript schema; not shipped as OSS | Infer only |
| Empirical corpus | `~/.claude/projects/**/*.jsonl` | **Highest-fidelity transcript type histogram** |

**Binary string harvest (structured signals that survive compile):**

- Wire / API: `stop_reason` values `end_turn | tool_use | max_tokens | pause_turn | refusal | model_context_window_exceeded`
- Content blocks: `tool_use`, `tool_result`, `text`, `redacted_thinking`, stream events
- Control plane: `control_request` / `control_response` with subtypes including
  `can_use_tool`, `request_user_dialog`, `plan_approval_request/response`,
  `set_permission_mode`, `session_state_changed`, `interrupt`
- Built-in tools with lifecycle weight: `AskUserQuestion`, `EnterPlanMode`,
  `ExitPlanMode`, plus Bash/Read/Edit/Write/…
- Hooks (also public): `PreToolUse`, `PermissionRequest`, `Notification`
  (`agent_needs_input`, `agent_completed`, `permission_prompt`, `idle_prompt`,
  `elicitation_dialog`, …), `Stop`, `SessionStart/End`, …
- Internal lifecycle strings: `onAwaitingUserInput`, `Agent idle`,
  `Agent stalled (stream watchdog)`, plan mode enter/exit copy

**Cross-version string diff (proof the pipeline works on closed binaries):**

Diffing `type:"…"` token sets for `2.1.204` vs `2.1.205` already yields
additions (`meta`, `read_truncation_notice`) and removals
(`agent_descriptions`, `unreachable_rules`, layout tokens). Drift is
detectable without source.

**Empirical transcript types (51 files, ~16k lines on this machine):**

| type | count | Today mapped by activity parser? |
|---|---:|---|
| `assistant` | 5284 | yes (tool_use / AskUserQuestion / end_turn) |
| `attachment` | 3283 | **NO** (dropped if not in known set) |
| `user` | 3207 | yes (turn-open / tool_result) |
| `last-prompt` | 811 | **NO** |
| `mode` | 811 | **NO** (`mode: normal` etc.) |
| `permission-mode` | 811 | **NO** (`bypassPermissions` etc.) |
| `ai-title` | 635 | **NO** |
| `system` | 562 | known-ignored |
| `file-history-snapshot` | 509 | **NO** |
| `queue-operation` | 233 | **NO** |
| `agent-setting` | 108 | **NO** |
| `pr-link` / `relocated` / `worktree-state` | smaller | **NO** |

Fixture on disk (`api/tests/fixtures/claude_transcript.jsonl`) also contains
`ai-title` and `file-history-snapshot` that the known-set does not list.

**Claude extractable schema summary:**

| Layer | Harvest quality | Role for state derivation |
|---|---|---|
| Public hooks docs | High (typed events, matchers, version min notes) | **Lifecycle side-channel** TM can inject or observe |
| Binary string inventory | Medium (noisy, incomplete, but re-runnable) | Drift detector + candidate enum discovery |
| Transcript corpus histogram | High for top-level `type` / tool names | Ground truth for mapper coverage |
| `.d.ts` / open source | **None** | Do not plan on it |
| Wire API bytes | High for model-visible blocks / stop_reason | Incomplete for *local* permission/plan gates |
| PTY scrollback | Medium (regex fragile) | Only plane that surfaces some local pause UIs |

**Bottom line for Claude:** treat as **closed binary + public hooks contract +
empirical JSONL**. Schema is *harvested*, not *imported*. No typed package
exports exist on the install path we ship against.

### 1.2 Codex 0.144.0 (OPEN + closed binary package)

| Artifact | Location | Extractable schema? |
|---|---|---|
| npm `@openai/codex` | Thin JS launcher only | No types in the published tarball |
| Native binary | `codex-darwin-arm64` vendor Mach-O (~260MB, Rust) | String harvest works; richer type names survive |
| GitHub `openai/codex` | **Apache-2.0**, `codex-rs/*` crates | **First-class source of truth** for enums/protocols |
| App-server protocol strings | Embedded JSON-schema-ish fragments + notification names | High |
| Rollout / JSONL kinds | Documented in binary strings | `session_meta`, `turn_context`, `event_msg`, `response_item`, `world_state`, `compacted` |

**State-relevant EventMsg / notifications visible in binary:**

`TurnStarted`, `TurnComplete`, `TurnAborted`, `TokenCount`,
`ExecApprovalRequest`, `ApplyPatchApprovalRequest`, `RequestPermissions`,
`ElicitationRequest`, `AgentMessage`, `AgentReasoning`, `PlanUpdate`,
`HookStarted/Completed`, `CollabWaitingBegin`, `GuardianAssessment`,
`SessionConfigured`, `StreamError`, `ThreadStatusChangedNotification`
(`Idle` / `SystemError` / …), approval modes `on-request | never | on-failure | unless-trusted`.

**Bottom line for Codex:** prefer **git pin of `openai/codex` tag matching
CLI version** → extract Rust enums / JSON-RPC method tables. Binary strings
are the fallback when source lag or private builds appear. Open source makes
Codex the **template harness** for the pipeline; Claude is the hard case.

### 1.3 What TM already owns (read-only inventory)

- **Activity machine** (`packages/activity`): statuses
  `starting | thinking | running-tools | needs-you | stalled | exited`.
  `needs-you` is flat: entered via `record.assistant_turn_ended` or
  `record.question_asked` only. **No `needs_you` subtypes** yet.
- **Claude mapper:** only `user|assistant|system|summary` known; questions =
  `AskUserQuestion`; turn end = `stop_reason === "end_turn"`.
- **Codex mapper:** `event_msg` markers
  `task_started|task_complete|turn_aborted|token_count` plus
  `response_item` function_call / message. Question =
  `function_call.name === "request_user_input"`. Approvals
  (`ExecApprovalRequest` etc.) are **not** mapped into `needs-you`.
- **Three planes already in product mental model:** wire, transcript, PTY
  scrollback ring. State derivation today is almost entirely **transcript**
  (+ run lifecycle start/exit). Permission/plan local gates are under-served.

This is the silent-misclassify surface the pipeline must make loud.

---

## 2. Canonical vocabulary (contribution, not sole owner)

Cross-cutting proposal for the shared state enum (pipeline-friendly form):

```
AgentLifecycleStatus =
  | starting
  | thinking            # model generating, no pending local gate
  | running_tools       # tool calls in flight
  | needs_you           # human gate; see subtype
  | stalled             # watchdog / transcript error / hung stream
  | exited

NeedsYouSubtype =
  | question            # AskUserQuestion / request_user_input / elicitation
  | permission          # tool permission, sandbox, exec/patch approval
  | plan_review         # ExitPlanMode / plan approval / plan mode review
  | other               # auth, rate-limit interactive, unknown gate

Plane =
  | wire
  | transcript
  | pty
  | hooks               # optional 4th plane if TM injects hooks
  | process             # pid exit / run lifecycle
```

**Per-state primary plane (default truth, with fallbacks):**

| Status / subtype | Primary plane | Secondary | Why |
|---|---|---|---|
| starting | process | transcript SessionStart / session_meta | Launch facts |
| thinking | wire (streaming) | transcript assistant deltas | Model work is on the wire |
| running_tools | transcript tool_use without result | wire tool_use blocks | Transcript is durable; wire is live |
| needs_you.question | transcript tool_use AskUser* | wire tool_use | Usually model-initiated tool |
| needs_you.permission | **pty** or **hooks PermissionRequest** | codex event_msg approval | Often **absent** from wire+transcript until resolved |
| needs_you.plan_review | transcript ExitPlanMode / plan tools + mode | control_request plan_approval_* | Mix of tool + mode records |
| stalled | process watchdog + transcript silence | pty "stalled" strings | Absence of progress is the signal |
| exited | process | SessionEnd / thread closed | Process is ground truth |

**Rule:** a state claim must cite its plane. Multi-plane merge is a
**priority lattice**, not a majority vote: process.exited wins; an armed
permission gate on PTY/hooks outranks a transcript that still looks
"running_tools"; wire `end_turn` without open tools implies needs_you only
if no local gate is open.

---

## 3. Bold options (divergent)

### Option A — SCHEMA-LOCK pipeline (recommended spine)

**What:** versioned manifests + fail-loud unmapped + golden fixtures.

**Pros:** mechanical, re-runnable, harness-agnostic process; stops silent
rot; works for closed binaries via string harvest; doctor can run offline.

**Cons:** binary strings are noisy (false positives); needs human triage
classes (`state_critical | conversational | noise`); does not by itself
observe local gates that never write JSONL.

**Tradeoff:** invest in **classifier labels** on every enum member so "new
type: meta" can be auto-classed noise while "new type: permission_request"
fails hard.

### Option B — Hooks as first-class fourth plane (Claude-heavy)

**What:** TM injects (or requires) hook handlers for
`PermissionRequest`, `Notification(agent_needs_input|permission_prompt|…)`,
`Stop`, `Elicitation`. Hooks POST into the capture plane.

**Pros:** Anthropic already documents these schemas with version floors;
`agent_needs_input` is literally the product state; PermissionRequest fires
when the dialog appears (the missing transcript signal).

**Cons:** requires controllable settings injection per run; enterprise
`allowManagedHooksOnly` / user disable can break it; Codex hooks differ;
not available for foreign sessions TM did not spawn.

**Tradeoff:** best for **captured runs TM launches**; incomplete for
attach-to-existing / backfill.

### Option C — Pure empirical corpus mining

**What:** no binary harvest; only expand known-sets from live JSONL
histograms in CI against fixture banks + user corpus samples.

**Pros:** ground-truth types only; low false positives.

**Cons:** lagging (new types appear only after users hit them); cannot
discover rare control subtypes; fails open for new versions until corpus
catches up.

**Tradeoff:** essential **validation leg**, insufficient as sole acquire step.

### Option D — Binary differential + snapshot testing only

**What:** treat harness like a black box; snapshot full string inventories;
never try to map to semantic state until humans label diffs.

**Pros:** always detects change.

**Cons:** human bottleneck; no automatic fail on unmapped *semantic* events;
does not produce mappers.

**Tradeoff:** good **smoke layer**, bad product state layer.

### Option E — Source-of-truth plugins per openness class

**What:** Codex/OpenCode (open) use git-tag enum extractors; Claude uses
hooks+binary+corpus; future open harnesses copy Codex path.

**Pros:** maximal signal per harness; generalization via **adapter interface**
not one algorithm.

**Cons:** two (or more) acquire implementations to maintain.

**Tradeoff:** this is the realistic end state; Option A is the **interface**
that Options B–E plug into.

### Option F — PTY computer-vision / TUI grammar

**What:** parse scrollback with a versioned TUI grammar (permission box,
plan panel, "Waiting for input").

**Pros:** only plane for some local gates when hooks unavailable.

**Cons:** brittle across themes, locales, width, alt-screen; high false
positive risk; expensive.

**Tradeoff:** last resort, version-pinned regex/grammar fixtures, never
primary for open harnesses with structured approvals.

### Recommended blend

**A (spine) + E (per-openness acquire) + B (Claude captured-run hooks) + C
(corpus validation) + F (PTY fallback only).** Reject pure D as product
strategy; keep D as the lowest-level acquire artifact.

---

## 4. Pipeline design: re-runnable per-(harness, version)

### 4.1 Artifact: Harness Manifest

Path sketch (concept only):

```
~/.transport-matters/schema-lock/
  claude/2.1.205/manifest.json
  claude/2.1.205/acquire.log
  claude/2.1.205/golden/{question,permission,plan-review,tool-loop,exit}.jsonl
  codex/0.144.0/manifest.json
  ...
  current.json   # {claude: "2.1.205", codex: "0.144.0"}
```

**Manifest shape (conceptual):**

```jsonc
{
  "harness": "claude",
  "version": "2.1.205",
  "acquired_at": "ISO-8601",
  "sources": [
    {"kind": "binary_strings", "path": "~/.local/share/claude/versions/2.1.205", "sha256": "..."},
    {"kind": "hooks_docs", "url": "https://code.claude.com/docs/en/hooks", "retrieved_at": "..."},
    {"kind": "corpus_histogram", "files": 51, "lines": 16379},
    {"kind": "mapper_snapshot", "module": "transcriptRecords", "git_sha": "..."}
  ],
  "enums": {
    "transcript_record_types": [
      {"name": "assistant", "class": "state_critical", "mapped_to": ["thinking","running_tools","needs_you","exited"]},
      {"name": "attachment", "class": "state_relevant", "mapped_to": null},
      {"name": "mode", "class": "state_relevant", "mapped_to": null},
      {"name": "permission-mode", "class": "state_relevant", "mapped_to": null},
      {"name": "ai-title", "class": "noise", "mapped_to": "ignore"}
    ],
    "stop_reasons": [...],
    "tools_lifecycle": [
      {"name": "AskUserQuestion", "needs_you": "question"},
      {"name": "ExitPlanMode", "needs_you": "plan_review"},
      {"name": "EnterPlanMode", "class": "mode_transition"}
    ],
    "control_subtypes": [
      {"name": "can_use_tool", "needs_you": "permission", "plane": "control"},
      {"name": "plan_approval_request", "needs_you": "plan_review", "plane": "control"}
    ],
    "hook_events": [
      {"name": "PermissionRequest", "needs_you": "permission", "plane": "hooks"},
      {"name": "Notification:agent_needs_input", "needs_you": "question", "plane": "hooks"}
    ],
    "pty_markers": [
      {"id": "permission_dialog", "needs_you": "permission", "plane": "pty", "fragile": true}
    ]
  },
  "mapper_coverage": {
    "state_critical_unmapped": [],
    "state_relevant_unmapped": ["attachment", "mode", "permission-mode", "..."],
    "noise_unmapped_ok": true
  },
  "diff_vs_previous": {
    "previous": "2.1.204",
    "added": ["meta", "read_truncation_notice"],
    "removed": ["agent_descriptions", "..."]
  }
}
```

### 4.2 Stages (re-runnable CLI conceptual)

```
tm-schema-lock acquire  --harness claude --version auto
tm-schema-lock diff     --harness claude --from 2.1.204 --to 2.1.205
tm-schema-lock check    --harness claude --version 2.1.205   # fail-loud
tm-schema-lock goldens  --harness claude --version 2.1.205   # regenerate under flag
tm-schema-lock onboard  --harness <new> --probe
```

**Stage details:**

1. **Resolve version**
   - Claude: `claude --version` + resolve symlink under `~/.local/share/claude/versions/`.
   - Codex: `codex --version` + npm package version + optional git tag `rust-v*` / release tag.

2. **Acquire (multi-source, merge)**
   - `binary_strings`: extract candidate tokens via curated regexes
     (quoted snake identifiers, `type:"…"`, control subtypes, tool names).
   - `docs`: fetch hooks/permissions pages; parse event tables (Claude).
   - `source_git` (Codex/open): checkout tag; run enum extractor over Rust
     (`EventMsg`, rollout item kinds, app-server notifications).
   - `corpus`: histogram of user + TM fixture JSONL for top-level types and
     tool names; never upload corpus; local only.
   - `mapper_snapshot`: static scan of `CLAUDE_KNOWN_*`, tool special-cases,
     codex handled event_msg set.

3. **Classify**
   - Auto rules: if name matches permission/approval/plan/ask/elicitation →
     `state_critical`; known noise lists (`ai-title`, layout tokens) → `noise`;
     else `state_relevant` requiring human or heuristic promotion.
   - New `state_critical` without `mapped_to` → **FAIL**.
   - New `state_relevant` → **FAIL** unless allowlisted in
     `pending-triage.json` with expiry.

4. **Diff**
   - Set-diff enums vs previous manifest.
   - Require changelog note for any `state_critical` add/remove.
   - Binary-only noise churn should not fail if class remains `noise`.

5. **Check (the fail-loud gate)**
   - Load mapper registration table.
   - For every manifest member with `class ∈ {state_critical, state_relevant}`:
     must be either mapped or explicitly `mapped_to: "ignore"` with rationale.
   - Run golden fixtures through mapper → activity events → machine status;
     assert expected `needs_you` subtype.
   - Optional: live doctor compares **running harness version** to latest
     checked manifest; warn if ahead of schema-lock.

6. **Goldens**
   - Minimal synthetic JSONL (and optional PTY snippets) per scenario:
     question, permission, plan-review, tool-loop, stall, exit, interrupt.
   - Prefer synthetic over recording production sessions (PII).
   - When harness versions, re-capture goldens under explicit
     `--accept-drift` after human review of the diff.

### 4.3 Fail-loud policy (precise)

| Observation | Severity | Action |
|---|---|---|
| Unknown transcript `type` with no class | error | fail check; do not map as ignore by default |
| Known `state_critical` unmapped | error | fail CI / doctor --strict |
| Known `noise` unmapped | ok | silent ignore |
| Tool name special-case list misses new Ask* / ExitPlan* | error | fail |
| Wire `stop_reason` not in enum | error | fail |
| Binary string set only grows noise tokens | info | log; no fail |
| Running harness version > last checked | warn (error in strict) | prompt re-acquire |
| Hooks plane disabled on captured run | warn | fall back to pty+transcript; mark confidence low |

**Never** "skip unknown type" without a counted telemetry event and a
manifest class. Counting alone is not enough if the count is not gated.

### 4.4 Mapping table sketch (Claude 2.1.205)

| Signal | Plane | → Status |
|---|---|---|
| process start | process | starting |
| user turn-open content | transcript | thinking (after) |
| assistant streaming / no end | wire/transcript | thinking |
| tool_use (not Ask*/ExitPlan*) | transcript/wire | running_tools |
| tool_use AskUserQuestion | transcript/wire | needs_you.question |
| tool_use ExitPlanMode / plan_approval_request | transcript/control | needs_you.plan_review |
| PermissionRequest hook / can_use_tool control | hooks/control | needs_you.permission |
| PTY permission box (fallback) | pty | needs_you.permission (low confidence) |
| stop_reason end_turn + no open tools + no local gate | wire/transcript | needs_you.question? or idle-thinking — **product decision**: prefer explicit idle vs needs_you.other |
| stop_reason tool_use with pending | wire | running_tools |
| silence past stallTimeout | process timer | stalled |
| process exit | process | exited |
| mode / permission-mode records | transcript | context annotations, not status alone |
| attachment hook_success | transcript | noise unless hookEvent is Permission* |

**Codex 0.144.0:**

| Signal | → Status |
|---|---|
| event_msg task_started | thinking / turn open |
| response_item function_call (normal) | running_tools |
| function_call request_user_input | needs_you.question |
| ExecApprovalRequest / ApplyPatchApprovalRequest / RequestPermissions | needs_you.permission |
| ElicitationRequest | needs_you.question |
| PlanUpdate + waiting for approval (if distinct) | needs_you.plan_review |
| event_msg task_complete | needs_you or idle (product) |
| turn_aborted | stalled / transcript-error |
| ThreadStatus Idle | needs_you.other or idle |
| process exit | exited |

---

## 5. Onboarding a NEW harness with minimal work

### 5.1 Harness Adapter contract (one trait, many acquires)

```
HarnessSchemaAdapter {
  name: string
  detect_version() -> Version
  locate_artifacts() -> {binary?, source_git?, docs_urls?, transcript_glob?}
  acquire(version) -> RawInventory
  classify(inventory) -> EnumMembers
  default_plane_priority() -> Plane[]
  lifecycle_tools() -> ToolRules
  golden_scenarios() -> Scenario[]
}
```

**Minimum viable onboard checklist (human, ~1 day target):**

1. Name the harness and launch path (how TM spawns / attaches).
2. Point `detect_version` + `locate_artifacts` (binary path, config dir, transcript glob).
3. Run `acquire` → first manifest (mostly unmapped).
4. Label classes for top 20 transcript types + any approval events (interactive
   triage UI or markdown checklist).
5. Implement **one** mapper function: `raw_record -> ActivityRecord[]`
   covering turn-open, tool-use/result, question, permission, plan, turn-end.
6. Add 5 golden JSONL scenarios; wire into `check`.
7. Declare plane priority (open harnesses usually transcript > wire > pty;
   closed may need hooks).
8. Land `current.json` pin; CI matrix entry.

**Everything else is shared:** diff, fail-loud gate, doctor integration,
activity machine, UI badges for `needs_you` subtypes.

### 5.2 Open vs closed playbooks

| | Open (Codex, future OSS agents) | Closed (Claude Code today) |
|---|---|---|
| Acquire primary | Git tag enum extract | Binary strings + hooks docs + corpus |
| Types | Compile-time / source enums | Harvested candidates |
| Local gates | Often structured event_msg | Hooks + PTY fallback |
| Drift | PR on upstream tag bump | Binary version dir bump / auto-update |
| Confidence | High | Medium; annotate plane confidence |

### 5.3 Version resilience process (the "keep this correct" loop)

```
harness auto-updates
    → doctor notices version ⊄ checked set
        → acquire new version (local, offline-capable for binary)
            → diff vs previous
                → state_critical delta?
                    yes → fail strict / open issue / block release
                    no  → auto-promote noise; re-run goldens
                → human triages state_relevant within SLA
                    → mapper PR + golden update
                    → check green → pin current.json
```

**Organizational rule:** schema-lock green is a **release gate** for TM, not
a best-effort linter. Harness churn is the product risk.

**CI cadence:**

- On every PR: `check` against pinned versions (fast, fixtures only).
- Nightly: `acquire` against installed harnesses on the runner; open PR on
  drift.
- On doctor: lightweight version pin compare + optional full check.

---

## 6. Closed-source extraction playbook (Claude detail)

Ordered by ROI:

1. **Public hooks + permissions docs** (stable, structured, version-min
   footnotes). Mirror event list into manifest `hook_events`.
2. **Installed binary string inventory** with curated extractors (not raw
   `strings` dumps in git). Store **hashes + sorted token sets**, not the
   binary.
3. **Multi-version local cache** (`~/.local/share/claude/versions/*`) for
   free differential without re-download.
4. **Empirical JSONL** from fixtures + opt-in local corpus histograms.
5. **SDK / `--print` / control protocol** experiments (if TM can speak
   control_request) for live state — research spike, not day-one.
6. **Do not depend on** npm package types, GitHub source, or reverse-engineered
   full ASTs. Bun single-binary will keep those empty.

**Internet sources worth tracking (not installing into runtime):**

- https://code.claude.com/docs/en/hooks (and permission-modes)
- GitHub issues requesting stable transcript schema (signal of breakage)
- Community transcript parsers (claude-code-log etc.) as **cross-checks**,
  never as sole truth

**Legal/safety:** harvest from the **user's installed binary and their own
transcripts** only; do not redistribute proprietary binary contents; manifests
contain token sets and counts, not code.

---

## 7. Gaps exposed by this probe (actionable for design, not implementation)

1. **Known-set too small for Claude** vs real corpus (attachment, mode,
   permission-mode, …).
2. **needs_you is untyped** in the activity machine; product needs subtypes.
3. **Permission / plan local gates** under-modeled; Codex approval events not
   mapped; Claude PermissionRequest not on transcript plane.
4. **No schema-lock artifacts** today; version pins exist only as informal
   "we tested on X".
5. **PTY plane** unused for lifecycle classification despite being named in
   the product brief.
6. **end_turn → needs-you** may conflate "idle, ready for next prompt" with
   "blocked on human". Consider `idle` vs `needs_you` split (vocabulary
   debate for the room).

---

## 8. Risks and anti-patterns

| Anti-pattern | Why it hurts | Instead |
|---|---|---|
| Silent ignore of unknown types | Today's failure mode | Fail-loud classes |
| One giant regex over PTY as primary | Theme/locale rot | Structured planes first |
| Assuming npm `@anthropic-ai/claude-code` has types | Install is native binary | Binary+docs+corpus |
| Assuming Codex npm tarball has schemas | Types live in git/Rust binary | Source tag extract |
| Coupling activity machine to harness enums | Explodes states | Map to harness-agnostic ActivityRecord first |
| Goldens from production sessions | PII, instability | Synthetic minimal fixtures |
| Waiting for Anthropic to publish JSON Schema | Issue open for months | Harvest pipeline now |

---

## 9. Proposed decision for the room

1. Adopt **SCHEMA-LOCK** as the process spine (Option A).
2. Implement **HarnessSchemaAdapter** with open/closed acquire plugins
   (Option E).
3. For Claude captured runs, inject **hooks plane** for PermissionRequest +
   Notification matchers (Option B), with PTY fallback (Option F).
4. Extend activity vocabulary with **`needs_you` subtypes** and optional
   explicit **`idle`**.
5. Treat mapper coverage of `state_critical` enums as a **release gate**.
6. Onboard path for harness N+1 is: detect → acquire → triage top enums →
   one mapper → five goldens → pin.

---

## 10. One-line extractability verdict

**Claude Code extractable schema = no .d.ts / no source; harvest = public hooks event schemas + binary string inventories (multi-version under `~/.local/share/claude/versions`) + empirical JSONL type/tool histograms; control_request subtypes and lifecycle tools are recoverable from the binary; local permission/plan gates need hooks or PTY, not wire alone. Codex = open `openai/codex` git enums + binary EventMsg fallback.**

---

## Appendix A — Acquire source matrix

| Source | Claude | Codex | New open harness | New closed harness |
|---|---|---|---|---|
| Binary strings | ✓ primary | ✓ fallback | if ships binary | ✓ primary |
| Public docs | ✓ hooks | partial | if any | if any |
| Git source enums | ✗ | ✓ primary | ✓ primary | ✗ |
| Corpus histogram | ✓ required | ✓ required | ✓ required | ✓ required |
| Mapper snapshot | ✓ | ✓ | ✓ | ✓ |
| Injected hooks | ✓ captured runs | if supported | optional | optional |
| PTY grammar | fallback | rare | rare | fallback |

## Appendix B — Minimal golden scenarios (all harnesses)

1. **question** — model asks user; status needs_you.question  
2. **permission** — tool blocked on approval; needs_you.permission  
3. **plan_review** — plan awaiting accept; needs_you.plan_review  
4. **tool_loop** — tool_use then tool_result; running_tools → thinking  
5. **clean_exit** — process exit; exited  
6. **stall** — silence; stalled  
7. **interrupt** — user cancels mid-tool; defined recovery  

Each golden lists expected plane contributions and final status.

## Appendix C — Probe commands used (reproducible)

```bash
# Claude binary + version chain
ls -la ~/.local/bin/claude
ls ~/.local/share/claude/versions/
claude --version   # 2.1.205

# String harvest (sketch)
strings ~/.local/share/claude/versions/2.1.205 | rg -o 'type:"[A-Za-z0-9_]+"' | sort -u

# Version drift
comm -3 <(strings v204 | rg -o 'type:"[^"]+"' | sort -u) <(strings v205 | ...)

# Corpus histogram
# python over ~/.claude/projects/**/*.jsonl counting record["type"]

# Codex
codex --version    # 0.144.0
# binary under node_modules/@openai/codex/.../bin/codex
# source: github.com/openai/codex codex-rs/
```

---

*End of grok ideation proposal.*

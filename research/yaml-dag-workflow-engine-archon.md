---
title: Archon YAML DAG workflow engine — mechanisms worth stealing for Helioy
type: research
tags: [archon, workflow-engine, orchestrator, dag, worktree, nancy, helioy-bus, helioy-plugins, claude-code]
summary: Mechanism-level teardown of Archon's DAG executor, worktree isolation, platform adapter model, smart PR review fan-out, and interactive pause/resume — with Nancy/Rust translation notes.
status: active
source: github-researcher
confidence: high
created: 2026-04-12
updated: 2026-04-12
---

# Archon teardown — ideas for Nancy, helioy-bus, helioy-plugins

Repo: https://github.com/coleam00/Archon (branch `dev`, 16.3k stars, TypeScript + Bun monorepo under `packages/`).

All file paths below are rooted at repo root.

## 1. DAG execution model

**Topological layer scheduler.** `packages/workflows/src/dag-executor.ts:665` (`buildTopologicalLayers`) runs Kahn's algorithm once at the start of a run and returns `DagNode[][]`. The executor then walks layers sequentially; inside each layer, `Promise.allSettled(layer.map(...))` runs nodes in parallel (`dag-executor.ts:2428`). Cycle detection happens at load time in `loader.ts:113` and a runtime assertion at `dag-executor.ts:697` catches any slip.

**Node state passed by reference.** A single `Map<string, NodeOutput>` (`nodeOutputs`) is created per run. Every node that settles writes its `{state, output, sessionId?, costUsd?, error?}` into it. Subsequent nodes read upstream outputs via text substitution (`$nodeId.output` and `$nodeId.output.field` — the substitution implementation is `substituteNodeOutputRefs` in the same file, around line 195). There is no typed channel system between nodes; it is string-passing with optional JSON extraction for `output_format` nodes.

**`when:` conditions are evaluated by a purpose-built mini parser**, not the LLM. `packages/workflows/src/condition-evaluator.ts` is only 173 lines. Grammar: `$nodeId.output[.field] (==|!=|<|<=|>|>=) 'value'`, combined with `&&`/`||` (AND binds tighter, no parens). `splitOutsideQuotes` respects single-quoted string regions. Fail-closed: any parse error returns `{result: false, parsed: false}` and the node is skipped with a user-facing warning (`dag-executor.ts:2507`). This is the right balance — expressive enough for branching on a classifier's structured output, simple enough to hand-audit.

**Trigger rules layer on top of `when:`.** `checkTriggerRule` (`dag-executor.ts:624`) handles Airflow-style rules: `all_success` (default), `one_success`, `none_failed_min_one_success`, `all_done`. These evaluate the upstream *state*, while `when:` evaluates upstream *output content*. The two axes compose cleanly — `when:` decides "should I run given the data" and trigger rule decides "should I run given the upstream lifecycle."

**Session threading.** A sequential chain of single-node layers threads the Claude session forward via `lastSequentialSessionId` (`dag-executor.ts:2414`). The moment a parallel layer starts, threading is cleared (parallel nodes can't share one session). A node can force a fresh session with `context: fresh` in its YAML. The trick is quiet: the AI SDK accepts `forkSession: true` so retries can safely resume from the same parent without mutating it (`dag-executor.ts:2769` comment).

### `fresh_context: true` on loops

`executeLoopNode` (`packages/workflows/src/dag-executor.ts:1700`) runs an AI prompt N times inside one node. On each iteration it computes `needsFreshSession = loop.fresh_context || i === 1` (`dag-executor.ts:1795`). If true, `resumeSessionId = undefined` and the assistant spawns a clean session. How does the next iteration know what happened? **It doesn't — by design.** The loop prompt is re-substituted every iteration against `artifactsDir`, `$nodeId.output` refs, and any files the prior iteration wrote. Continuity lives on disk, not in the AI's conversation history. This is effectively a "stateless worker, shared scratchpad" loop — same model Ralph-wiggum / Oncall-engineer loops use.

### Loop `until` — the `<promise>SIGNAL</promise>` protocol

`detectCompletionSignal` in `packages/workflows/src/executor-shared.ts:385` is the exit protocol. Two formats:

```
<promise>DONE</promise>               // case-insensitive, anywhere in output — preferred
DONE                                   // only matches at end-of-output or as its own line
```

`stripCompletionTags` removes the tag before display so the user never sees it. The plain-text fallback is deliberately restrictive ("not DONE yet" must not match). Loops can also supply a deterministic `until_bash:` — a shell predicate that, on `exit 0`, signals completion regardless of the LLM (`dag-executor.ts:2005`). Either channel can fire.

**This is the cleanest version of the exit-code problem I have seen in an LLM loop.** It is not a separate classifier call, not an exit-code convention, not tool invocation — it is an in-band marker the model naturally emits, stripped before display, with a fail-closed regex.

## 2. Worktree isolation

`packages/isolation/src/providers/worktree.ts` (1017 lines, but only ~200 load-bearing). The important bits:

**Naming** (`generateBranchName`, line 426). Deterministic and collision-free:
- `issue` → `archon/issue-42`
- `pr` (same-repo) → uses the actual branch; (fork) → `archon/pr-123-review`
- `thread` → `archon/thread-{shortHash(threadId)}` (Slack/Discord IDs are arbitrary)
- `task` → `archon/task-{slug(identifier)}`

**Path layout** supports two schemes (`getWorktreePath`, line 466):
- Project-scoped: `~/.archon/workspaces/{owner}/{repo}/worktrees/{branch}` (preferred)
- Legacy global: `~/.archon/worktrees/{owner}/{repo}/{branch}`

**Adoption before creation.** `findExisting` (line 480) checks if a worktree already exists at the expected path or on the expected branch before creating. This enables "skill-app symbiosis" — a human (or a Claude Code skill) can `git worktree add` manually, and Archon will adopt it with `metadata: { adopted: true, adoptedFrom: 'path' | 'branch' }`. Provider interface exposes `adopt?(path)` as an optional method (`types.ts:184`).

**Parallel safety.** Creation always sync-fetches base branch first (`syncWorkspaceBeforeCreate`, line 601) and will *fail hard* if the configured base branch doesn't exist — no silent fallback. The concurrent-run check is at the workflow level: `getActiveWorkflowRunByPath` queries `remote_agent_workflow_runs` for any `running` row with the same `working_path` and rejects the new run with a user-facing message (`executor.ts:324`). One worktree, one active workflow.

**Cleanup is best-effort with structured `DestroyResult`.** `destroy()` returns `{worktreeRemoved, branchDeleted, remoteBranchDeleted, directoryClean, warnings[]}`. Partial failures don't throw — they surface via warnings the orchestrator can show (`types.ts:144`). Git may leave `.archon/` artifacts under a removed worktree; the provider explicitly `rm -rf`'s whatever git left behind (`worktree.ts:164`).

**How the orchestrator knows the worktree after handoff.** Migration `019_workflow_resume_path.sql` added a `working_path` column to `remote_agent_workflow_runs`. Every run records its cwd. On re-invocation, `findResumableRun(workflowName, cwd)` (`db/workflows.ts:243`) picks up failed/paused runs on the same path. Paths are the join key between orchestrator and workflow state.

## 3. Orchestrator and platform adapters

**One interface, thin implementations.** `IPlatformAdapter` is 12 methods (`packages/core/src/types/index.ts:117`): `sendMessage`, `ensureThread`, `getStreamingMode`, `getPlatformType`, `start`, `stop`, and optional `sendStructuredEvent` / `emitRetract`. `IWebPlatformAdapter` extends it with SSE bridging hooks (`setupEventBridge`, `registerOutputCallback`). That's all. Each adapter is a self-contained ~400 line file under `packages/adapters/src/{chat,forge}/`:
- `chat/slack/adapter.ts` — 12KB Bolt-based; splits long messages at 12KB (`splitIntoParagraphChunks`)
- `chat/telegram/adapter.ts`
- `forge/github/adapter.ts` — webhook-driven

**Conversation ID is platform-native.** Slack encodes it as `"channel:thread_ts"` (`adapter.ts:61`). Telegram uses `chat_id`. GitHub uses `owner/repo#issue`. The core never parses these — it just passes them back to `sendMessage`. This is the right escape hatch: each platform's native ID format round-trips through the orchestrator as an opaque string.

**There is no "common envelope."** Archon does NOT define a unified `Message` type across platforms. The adapter internally translates incoming platform events and calls `handleMessage(userMessage, conversation, ...)` (`orchestrator-agent.ts:497`) with plain text + a `HandleMessageContext` carrying `isolationHints` and optional `issueContext`. Structured content (tool calls, JSON results) goes through the optional `sendStructuredEvent(conversationId, MessageChunk)` — `MessageChunk` is a discriminated union (`types/index.ts:196`) but only the web adapter implements it. Chat adapters fall back to formatted markdown through `sendMessage`.

**Long-running status updates** use two mechanisms in parallel:
1. `safeSendMessage` + `sendCriticalMessage` retry-with-backoff wrappers around `platform.sendMessage` (`executor.ts:72, 123`). UNKNOWN errors are tracked and abort the workflow after 3 consecutive failures.
2. `WorkflowEventEmitter` — an in-process Node `EventEmitter` singleton (`event-emitter.ts:170`). The executor fires `workflow_started`, `node_started`, `loop_iteration_started`, `tool_started`, `approval_pending`, etc. Subscribers include the web adapter (forwards to SSE) and the DB persister (writes to `remote_agent_workflow_events` table). `subscribeForConversation(conversationId, listener)` filters by `runId → conversationId` map registered at `emitter.registerRun()`. Listener errors are caught; emitter failures never propagate to the executor.

**The router is itself an LLM call.** `packages/workflows/src/router.ts:73` — `buildRouterPrompt` constructs a prompt that lists every available workflow with its description and asks the model to reply with exactly `/invoke-workflow {name}`. A separate `parseWorkflowInvocation` regex (line 153) parses the response (multiline mode to tolerate models that add chatter). `resolveWorkflowName` (line 223) has a 4-tier fallback: exact → case-insensitive → suffix match → substring match, throwing on ambiguity. Nice touch: the router prompt explicitly warns that "being on a GitHub issue does NOT mean the user wants to fix it."

## 4. Smart PR review fan-out

`.archon/workflows/defaults/archon-smart-pr-review.yaml`. The whole thing is ~140 lines of YAML and deserves its reputation.

Structure:
1. `scope` (bash/command node) — gathers PR diff
2. `sync` — syncs the PR with main, depends on `scope`
3. `classify` — a `haiku` prompt node with `allowed_tools: []` (read-only classification), depends on `scope`. Uses `output_format:` with a JSON schema:
   ```yaml
   output_format:
     type: object
     properties:
       run_code_review: {type: string, enum: ["true", "false"]}
       run_error_handling: {type: string, enum: ["true", "false"]}
       # ...
       complexity: {type: string, enum: ["trivial","small","medium","large"]}
       reasoning: {type: string}
   ```
4. Five parallel reviewer nodes (`code-review`, `error-handling`, `test-coverage`, `comment-quality`, `docs-impact`), each with `depends_on: [classify, sync]` and `when: "$classify.output.run_code_review == 'true'"`.
5. `synthesize` node — `depends_on` all five reviewers, `trigger_rule: one_success`. This is the merge step: it runs if at least one reviewer produced output, regardless of which ones the `when:` filtered out or which ones failed.
6. `implement-fixes` — auto-fixes CRITICAL/HIGH issues.
7. Optional `notify` — a bash probe followed by an MCP-backed node that sends a push notification.

**Why it works.** The classifier runs on haiku (cheap, fast), its `output_format` schema guarantees downstream `$classify.output.run_X` substitution is valid JSON (`dag-executor.ts:1059` overrides `nodeOutputText` with structured_output when present), and each reviewer is independently skippable. The synthesis node doesn't need to coordinate merging — `trigger_rule: one_success` + string concatenation of `$code-review.output` etc. in its prompt handles it. Conflicts between reviewers are resolved by the synthesis LLM reading them all together.

The pattern: **structured-output classifier gates parallel specialist agents, then one synthesis node reads all their outputs at once.** This is the DAG workflow equivalent of Anthropic's orchestrator-workers pattern, but expressed declaratively.

## 5. Interactive / human-in-the-loop nodes

Two separate mechanisms, both reaching the same DB state.

**Approval nodes** (`executeApprovalNode`, `dag-executor.ts:2191`) pause the workflow via `deps.store.pauseWorkflowRun(runId, {nodeId, type: 'approval', captureResponse, onRejectPrompt?, onRejectMaxAttempts?})`. The metadata goes into `remote_agent_workflow_runs.metadata.approval` as JSONB. The executor returns `{state: 'completed', output: ''}` to the DAG layer, and the between-layer status check at `dag-executor.ts:2880` notices `status = 'paused'` and cleanly exits without marking the whole run as failed. Very deliberate comment: "Return completed — the between-layer status check will see 'paused' and break."

**Interactive loop gates** (same approach, different node type). After each iteration where the AI did *not* emit the completion signal, if `loop.interactive && loop.gate_message` is set, the executor sends a gate message and calls `pauseWorkflowRun(runId, {type: 'interactive_loop', nodeId, iteration, sessionId})`. The session ID is preserved in metadata so the next iteration can resume the same Claude session.

**Resume protocol.** The user types `/workflow approve <runId> [feedback]` in chat. `approveWorkflow` in `packages/core/src/operations/workflow-operations.ts:131`:
1. For `interactive_loop`: writes an `approval_received` event, stores `loop_user_input: feedback` in metadata, flips status to `'failed'` (yes, failed — read on).
2. For standard approvals: writes a `node_completed` event with the captured response as `node_output`, flips to `'failed'`.

**The trick: paused runs are resumed through the `findResumableRun` path that was originally built for failed runs.** Setting status to `'failed'` after approval means the next invocation of `executeWorkflow` (triggered by any user message in the conversation) goes through the resume detection code at `executor.ts:349`, pulls `getCompletedDagNodeOutputs(runId)` to rebuild `nodeOutputs`, and restarts at the right place. One path, two use cases. The approval-node completed event makes `getCompletedDagNodeOutputs` treat the approval node as done. The interactive-loop case is cleverer: the executor inspects `metadata.approval.type === 'interactive_loop'` at `dag-executor.ts:1737` and resumes the loop at `iteration + 1` with `loopUserInput` substituted into the prompt via `$LOOP_USER_INPUT`.

**Where resume state is stored:**
- `remote_agent_workflow_runs.status` — `paused | running | failed | completed | cancelled`
- `remote_agent_workflow_runs.metadata` (JSONB) — `approval` context, `loop_user_input`, `rejection_reason`, `rejection_count`, `github_context`
- `remote_agent_workflow_events` — per-step trail; `getCompletedDagNodeOutputs` reassembles `nodeOutputs` from `node_completed` events
- `remote_agent_workflow_runs.working_path` — the worktree path, key for `findResumableRun`

## 6. Schema highlights

Migrations tell the story:

- `006_isolation_environments.sql` — `workflow_type + workflow_id` is a unique key per codebase. One row per (codebase, issue/pr/thread/task).
- `008_workflow_runs.sql` — baseline runs table. `conversation_id` FK to conversations (the chat thread), `codebase_id` FK to codebases (the repo).
- `010_immutable_sessions.sql` — sessions are append-only with `parent_session_id` linking previous session in chain + `transition_reason` ('plan-to-execute', 'isolation-changed', 'reset-requested'). Audit trail, not mutable state.
- `012_workflow_events.sql` — lean UI-relevant events. Deliberately NOT storing assistant text or tool I/O (those go to `{cwd}/.archon/logs/{runId}.jsonl` as JSONL). Events carry `event_type`, `step_name`, `data` (JSONB). This is the event stream that drives both SSE and persistence.
- `014_message_history.sql` — conversation messages with role/content/metadata. Plain.
- `015_background_dispatch.sql` — added `parent_conversation_id` to workflow_runs so a "worker conversation" for a background workflow can be linked back to the user's conversation. `conversations.hidden` hides worker convos from the sidebar.
- `019_workflow_resume_path.sql` — added `working_path` (the single most important column for resume).

**The conversation ↔ workflow_run link is two-way.** `conversations.isolation_env_id` points to the active worktree, `workflow_runs.conversation_id` points to the parent chat, and `workflow_runs.parent_conversation_id` handles background dispatch. Messages and events are separate tables so verbose AI output doesn't bloat the event stream.

## 7. Skill copy mechanism

Archon bundles its Claude Code skill *inside the compiled binary* via `packages/cli/src/bundled-skill.ts`. Each skill file is a static import with `with { type: 'text' }`:

```ts
import skillMd from '../../../.claude/skills/archon/SKILL.md' with { type: 'text' };
// ... 17 more imports
export const BUNDLED_SKILL_FILES: Record<string, string> = { 'SKILL.md': skillMd, ... };
```

Bun resolves these at compile time into the binary. `copyArchonSkill(targetPath)` (`setup.ts:1183`) iterates the record and `writeFileSync`'s each entry to `<target>/.claude/skills/archon/{relativePath}`. Always overwrites (explicit comment: "Always overwrites existing files to ensure the latest skill version is installed").

Same trick for default workflows and commands via `BUNDLED_WORKFLOWS` / `BUNDLED_COMMANDS` in `packages/workflows/src/defaults/bundled-defaults.ts`. The discovery layer (`workflow-discovery.ts:136`) loads bundled defaults first, then overrides by exact filename from `<cwd>/.archon/workflows/`. Repo-local files with the same name win.

**Comparison to helioy-plugins.** helioy-plugins ships via the Claude Code plugin marketplace — the skills live in the plugin repo itself, distributed through Claude Code's plugin system. Archon's model is different: Archon is a server/binary that *writes skills into the target repo*. This gives Archon two nice properties: (a) no runtime dependency on the Claude Code plugin marketplace, and (b) repo-local skills can be version-controlled alongside the workflows that use them.

---

## Borrow list for Helioy

### For Nancy (Rust orchestrator)

1. **`<promise>SIGNAL</promise>` in-band exit protocol for autonomous loops.** Nancy already has worker agents producing streaming output. Copy the regex and the `strip-before-display` trick verbatim. Spec section below. Ship it before we add any more "is the worker done" heuristics.
   - Rust translation: `regex::Regex::new(r"(?i)<promise>\s*DONE\s*</promise>")`. Strip with `regex::Regex::replace_all`.
   - Combine with an optional `until_bash:` escape hatch — a shell command the worker can write to declare structural completion (e.g. `grep -q '\[x\]' SPEC.md`). Non-zero = not done, zero = done.

2. **Topological layer scheduler with `Promise.allSettled`-style semantics.** Nancy currently runs one worker at a time. A Kahn's-algorithm layer scheduler (`petgraph::algo::toposort` feeds into layer assignment) would let Nancy fan out parallel specialists when a SPEC naturally decomposes. Critical property: layers run sequentially, nodes within a layer run concurrently with `tokio::try_join_all` or `futures::future::join_all`. Session threading only for single-node layers.

3. **Fail-closed condition evaluator.** Port `condition-evaluator.ts` to Rust as a ~200 line module. The grammar is small enough to hand-write with `nom` or just careful string matching. Use it to gate Nancy subtasks on classifier output, e.g. `$classify.output.needs_refactor == 'true'`. Do NOT use a general expression evaluator — the tight grammar is load-bearing for auditability.

4. **Structured-output classifier → parallel specialists → synthesis.** This is the smart-PR-review pattern. Nancy should have a built-in "dispatcher" node type that runs a haiku-tier classifier with a JSON schema, then fans out to whichever specialists the classifier approves, then synthesizes with `trigger_rule: one_success`. This is the right default topology for "review this thing" and "plan this feature."

5. **`working_path` as the join key for resume.** Nancy's current spec-driven design already assumes a worktree per task. Add a `working_path` column (or equivalent in whatever store Nancy uses) so that `nancy orchestrate` on the same worktree picks up a paused SPEC without ceremony. Store pause state as structured JSON in a metadata column — approval context, iteration number, worker session ID.

6. **Worktree adoption before creation.** `findExisting` checks path-then-branch and adopts what's there. Nancy (or helioy-bus warroom) should do the same — a human can prep a worktree with `git worktree add` and warroom/Nancy will adopt it. Flag with `adopted: true` so cleanup logic knows not to nuke uncommitted work the human staged.

7. **Structured `DestroyResult` not a boolean.** `{worktreeRemoved, branchDeleted, remoteBranchDeleted, directoryClean, warnings}` is exactly the shape a cleanup service needs to report partial failures without raising exceptions.

### For helioy-bus

8. **Fire-and-forget event emitter with per-conversation filtering.** helioy-bus already has a message bus, but the `WorkflowEventEmitter` pattern is worth stealing for workflow-internal events (not cross-agent mail): in-process, typed, fire-and-forget, singleton, with a `runId → conversationId` map so subscribers can filter. Use it to push workflow progress to warroom dashboards without cluttering the mail channel. Listener errors are caught and logged; emitter failures never propagate.

9. **Event persistence separated from log persistence.** Archon's two-table split — lean events in `workflow_events`, verbose AI output in JSONL files — is the right call. Apply it to warroom: store structured events in SQLite for replay and UI, keep the full transcripts on disk. Do not put transcripts in the bus.

10. **Minimal platform adapter interface, no common envelope.** helioy-bus uses MCP for transport; that's already platform-specific. But the 12-method `IPlatformAdapter` shape (send, ensure-thread, start, stop, streaming-mode, platform-type, optional structured-event) is a good model for adding new chat surfaces (Linear comments, GitHub PR comments, Slack). Conversation ID stays as an opaque platform-native string. Resist the urge to unify message types across platforms — plain text + an optional structured event channel is enough.

### For helioy-plugins

11. **LLM-powered router as a first-class abstraction.** helioy-plugins has a bunch of skills; deciding which to trigger on a given user message is currently implicit. Consider a router skill that reads the user request plus "Use when / NOT for" frontmatter from each registered skill and emits a `/invoke-skill {name}` command. 4-tier name resolution (exact → case-insensitive → suffix → substring) prevents typo friction and ambiguity-throws make conflicts explicit.

12. **`output_format: json_schema` on prompt nodes.** If helioy-plugins ever grows workflow-style steps, this is the interlock. The SDK returns `structured_output` separately from prose; use it as the canonical node output (override `nodeOutputText` with `JSON.stringify(structured_output)`). Downstream `$nodeId.output.field` just works. Without this, branching on classifier output is unreliable.

---

## Do NOT borrow

- **Their resume-via-status='failed' trick.** Archon flips paused runs to `failed` status because `findResumableRun` was built for failures and they didn't want a second query. This is load-bearing confusion — a staff engineer would add a `resumable` bool or a richer status enum. Nancy should have distinct `paused`, `failed`, `resumable` statuses from day one.
- **The `.archon/config.yaml` hierarchy + `~/.archon/` + bundled-defaults + repo overrides** discovery chain. It's a lot of surface area for three layers. Helioy already has `~/.mdx` + cm scopes; don't reinvent this.
- **Bun's `import with { type: 'text' }` skill bundling.** Clever for a binary distribution, but helioy-plugins ships via the Claude Code plugin marketplace — the existing model is fine. Only consider this if Nancy ever needs to distribute as a single Rust binary with embedded skills, in which case `include_str!` is the direct Rust equivalent.
- **Their fresh-loop "continuity via artifacts" model as the *only* option.** It's elegant but footguns newcomers ("why doesn't the model remember the last iteration?"). Nancy's current SPEC.md + cm + disk-artifacts approach already does this well; don't suggest Nancy add `fresh_context: true` as a knob until there's a clear reason.
- **String-based `$nodeId.output` substitution as the primary channel between nodes.** It works because YAML is the authoring surface, but in Rust you want typed channels (`tokio::sync::oneshot` or `mpsc`) for node-to-node data passing, with the string substitution reserved for prompt templating. Don't copy the architecture — copy the feel.
- **GitHub adapter complexity.** Archon's GitHub adapter is webhook-driven and handles fork PRs, issue comments, labels, and PR reviews. This is a lot. helioy-bus should stick to the warroom + mail model for now and lean on `gh` CLI for GitHub interaction inside workflows.

## Sources consulted

All paths from `https://github.com/coleam00/Archon` @ `dev`:

- `packages/workflows/src/dag-executor.ts` (3036 lines — the star of the show)
- `packages/workflows/src/executor.ts` (top-level run/resume orchestration)
- `packages/workflows/src/condition-evaluator.ts` (the mini when: parser)
- `packages/workflows/src/executor-shared.ts` (detectCompletionSignal + stripCompletionTags)
- `packages/workflows/src/router.ts` (LLM router + 4-tier name resolution)
- `packages/workflows/src/workflow-discovery.ts` (bundled vs. repo override)
- `packages/workflows/src/event-emitter.ts` (typed fire-and-forget singleton)
- `packages/workflows/src/loader.ts` (Kahn's cycle detection, Zod schema validation)
- `packages/isolation/src/providers/worktree.ts` (1017 lines, naming + adoption + cleanup)
- `packages/isolation/src/types.ts` (IsolationRequest, DestroyResult)
- `packages/core/src/orchestrator/orchestrator.ts` (isolation resolution entry)
- `packages/core/src/orchestrator/orchestrator-agent.ts` (handleMessage, router invocation)
- `packages/core/src/operations/workflow-operations.ts` (approve/reject/resume operations)
- `packages/core/src/db/workflows.ts` (findResumableRun, pauseWorkflowRun)
- `packages/core/src/types/index.ts` (IPlatformAdapter, MessageChunk)
- `packages/adapters/src/chat/slack/adapter.ts` (reference adapter implementation)
- `packages/cli/src/bundled-skill.ts` + `packages/cli/src/commands/setup.ts` (skill copy)
- `.archon/workflows/defaults/archon-smart-pr-review.yaml` (the fan-out pattern)
- `migrations/006_isolation_environments.sql`, `008_workflow_runs.sql`, `010_immutable_sessions.sql`, `012_workflow_events.sql`, `014_message_history.sql`, `015_background_dispatch.sql`, `019_workflow_resume_path.sql`

## Open questions

- How does the Codex provider return structured_output? Archon treats Codex as returning JSON inline in agent_message text and validates with `JSON.parse` — is there a cleaner SDK path?
- The `archon-ralph-dag.yaml` and `archon-piv-loop.yaml` workflows were not read — worth a follow-up specifically on how Archon shapes Ralph-wiggum-style continuous-loop patterns as DAGs vs. pure loop nodes.
- `executor-preamble.ts` — not read; likely contains the prompt prefix every workflow gets. Could influence Nancy's default system prompt.
- What does the Workflow Builder visual DAG editor compile to? (packages/web not opened.) If it round-trips YAML, Helioy could use the same YAML schema.

# JSONL Session Parsing Analysis

## 1. What is in the JSONL?

The JSONL file is a linear log of every message exchanged during a Claude Code session. Each line is a JSON object with a `type` field. For the reference session (535 lines, rust-engineer working on ALP-1403):

| Type | Count | Purpose |
|---|---|---|
| `assistant` | 319 | Claude's responses: text blocks + tool_use blocks |
| `user` | 206 | Human prompts (2-4 actual) + tool_result messages (~202) |
| `agent-setting` | 3 | Agent type identifier (e.g. `helioy-tools:rust-engineer`) |
| `queue-operation` | 2 | Prompt enqueue/dequeue timestamps |
| `progress` | 2 | Hook execution progress (SessionStart) |
| `last-prompt` | 2 | Truncated last prompt for UI display |
| `system` | 1 | Compaction boundary with token counts |

### Key data available per message type

**`assistant` messages** contain a `message.content` array of:
- `text` blocks: reasoning, status updates, plans
- `tool_use` blocks: `{name, id, input}` with full input parameters

**`user` messages** contain a `message.content` of:
- `string` or `text` blocks for actual human/orchestrator prompts (rare, 2-4 per session)
- `tool_result` blocks for tool outputs (bulk of the count)

**`agent-setting`**: includes `agentSetting` (agent type string) and `sessionId`.

**`system` with `subtype: compact_boundary`**: includes `compactMetadata.preTokens` showing token usage at compaction time.

**`progress`**: includes hook event name, hook command path, and timestamps.


## 2. Derivability Analysis: JSONL vs Session Log

### Task
**JSONL derivability: HIGH (mechanical)**

The first `user` message with actual content (not a `tool_result`) contains the task briefing. In nancy sessions, this is the orchestrator's structured prompt with issue ID, title, acceptance criteria. Extracting the first non-tool-result user message and taking its first line or `# heading` gives the task description.

Heuristic: find the first `user` entry where `message.content` is a string, or contains a `text` block (not `tool_result`). Extract the first markdown heading or first sentence.

**Quality vs agent-authored:** Comparable. The agent's session log task line is essentially a paraphrase of this same input.


### Summary
**JSONL derivability: LOW (requires LLM synthesis)**

The summary in the reference log is a coherent 3-sentence paragraph describing what was accomplished, which Linear issues were closed, and that tests pass. This requires understanding intent, completion state, and synthesizing across the full conversation.

A mechanical version could list: "Made N tool calls (M edits, K writes, J bash). Modified files: [list]. Ran tests: [pass/fail based on last cargo test output]." This is factual but not useful as a handover document.

**Quality gap: Large.** Mechanical summaries lack the "what was accomplished and why it matters" framing that makes handovers actionable.


### Agents Spawned
**JSONL derivability: HIGH (mechanical)**

Scan `assistant` messages for `tool_use` blocks where `name == "Agent"`. Extract `input.description` and `input.subagent_type`. In the reference session: zero Agent tool calls, matching the log's "None."

Implementation: trivial filter over tool_use blocks.

**Quality vs agent-authored:** Identical. This is pure structured data.


### Artifacts Produced
**JSONL derivability: HIGH (mechanical)**

Scan for `tool_use` blocks where `name` is `Write`, `Edit`, or `Bash` (for file creation via shell commands). Extract:
- `Write`: `input.file_path`
- `Edit`: `input.file_path`
- `Bash`: parse `input.command` for `git commit` messages, `mv`, `rm` operations

In the reference session, this produces 17 unique file paths from Write/Edit calls. Git commit messages from Bash tool results add context about what was created vs deleted.

**Quality gap: Small.** The agent-authored log adds annotations like "NEW", "DELETED", "Added impl LanguageDescriptor." The mechanical version would list paths without context. Enhancement: pair each path with the count of edits and the Write/Edit that created it (first occurrence = NEW, subsequent = modified). Deletion detection from `git rm` or `rm` in Bash commands.


### Key Findings
**JSONL derivability: LOW (requires LLM synthesis)**

These are lessons learned and gotchas discovered during the session. Examples from the reference: "The Edit tool resolves paths relative to the claude daemon cwd, not the worktree." This insight is embedded in the assistant's text reasoning blocks, not in structured tool calls.

A mechanical approach could extract assistant text blocks that contain warning patterns ("note:", "important:", "gotcha:", "workaround:") but this is fragile and noisy.

**Quality gap: Large.** This is the highest-value section of the handover and the hardest to automate.


### Patterns Captured
**JSONL derivability: HIGH (mechanical)**

Scan for `tool_use` where `name` matches `cx_store`, `cx_deposit`, `am_ingest`, or `am_buffer`. Extract `input.title` and `input.kind`. In the reference session: zero cx_store calls (the agent used cx_deposit through the session-logger skill instead).

Note: if patterns are captured via the `session-logger` Skill invocation (which writes the log file and calls cx_store), those are visible as Skill tool calls with args. The actual cx_store happens inside the skill execution context, which may or may not appear in the JSONL depending on whether skill internal tool calls are logged.

**Quality gap: Small** when the agent uses explicit memory tools. **Large** when insights are captured only in prose.


## 3. Quality Gap Summary

| Section | Mechanical derivability | Quality vs agent-authored |
|---|---|---|
| Task | High | Equivalent |
| Summary | Low | Large gap |
| Agents Spawned | High | Identical |
| Artifacts Produced | High | Small gap (missing annotations) |
| Key Findings | Low | Large gap |
| Patterns Captured | High (if tools used) | Small gap |


## 4. Recommended Hybrid Approach

Parse the JSONL mechanically for the structured fields. Skip the synthesis fields entirely rather than producing low-quality approximations.

### Mechanical extraction (zero agent tokens)

```python
def parse_session_jsonl(path: str) -> dict:
    """Extract structured session metadata from JSONL."""
    lines = [json.loads(l) for l in open(path)]

    result = {
        "session_id": None,
        "agent_type": None,
        "task_prompt": None,
        "tool_calls": {},       # name -> count
        "artifacts": [],        # unique file paths from Write/Edit
        "agents_spawned": [],   # from Agent tool calls
        "patterns_stored": [],  # from cx_store/cx_deposit calls
        "git_commits": [],      # from Bash tool results containing commit output
        "linear_issues": [],    # from save_issue calls
        "compaction_tokens": None,
        "start_time": None,
        "end_time": None,
    }

    for line in lines:
        t = line.get("type")

        if t == "agent-setting":
            result["agent_type"] = line.get("agentSetting")
            result["session_id"] = line.get("sessionId")

        elif t == "system" and line.get("subtype") == "compact_boundary":
            result["compaction_tokens"] = line.get("compactMetadata", {}).get("preTokens")

        elif t == "user":
            content = line.get("message", {}).get("content", [])
            # First actual human prompt (not tool_result)
            if result["task_prompt"] is None:
                if isinstance(content, str):
                    result["task_prompt"] = content[:500]
                elif isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            result["task_prompt"] = c["text"][:500]
                            break

        elif t == "assistant":
            ts = line.get("timestamp")
            if ts:
                if not result["start_time"]:
                    result["start_time"] = ts
                result["end_time"] = ts

            content = line.get("message", {}).get("content", [])
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict) or c.get("type") != "tool_use":
                    continue
                name = c.get("name", "")
                inp = c.get("input", {})
                result["tool_calls"][name] = result["tool_calls"].get(name, 0) + 1

                if name == "Write":
                    result["artifacts"].append(inp.get("file_path", ""))
                elif name == "Edit":
                    result["artifacts"].append(inp.get("file_path", ""))
                elif name == "Agent":
                    result["agents_spawned"].append({
                        "description": inp.get("description", ""),
                        "type": inp.get("subagent_type", "general"),
                    })
                elif "save_issue" in name:
                    result["linear_issues"].append({
                        "title": inp.get("title", ""),
                        "status": inp.get("status", ""),
                    })
                elif name in ("mcp__plugin_helioy-tools_cm__cx_store",
                              "mcp__plugin_helioy-tools_cm__cx_deposit"):
                    result["patterns_stored"].append(inp.get("title", inp.get("summary", "")))

    result["artifacts"] = sorted(set(filter(None, result["artifacts"])))
    return result
```

### Output template (mechanical fields only)

```markdown
---
session: {session_id}
date: {date}
agent: {agent_type}
source: jsonl-parse  # distinguishes from agent-authored
---

## Task
{first heading or first line of task_prompt}

## Tool Activity
{tool_call_count} tool calls: {top 5 tools by frequency}

## Artifacts Produced
{deduplicated Write/Edit file paths}

## Agents Spawned
{Agent tool call descriptions, or "None"}

## Git Commits
{commit messages extracted from Bash results}

## Linear Issues
{save_issue titles with status}

## Patterns Captured
{cx_store/cx_deposit titles, or "None"}
```

### What this replaces and what it does not

**Replaces:** The mechanical sections of the session-logger skill. No agent cooperation needed. Can run post-hoc on any session JSONL, including crashed/evicted sessions that never got to run session-logger.

**Does not replace:** Summary, Key Findings. These require either: (a) a cheap LLM pass over the extracted data (could use haiku with the mechanical output as input), or (b) acceptance that handover documents for evicted agents lack synthesis.

### Cost analysis

Parsing a 535-line JSONL takes <50ms in Python. Zero API tokens. The session-logger skill, by contrast, consumes agent context to introspect and summarize, typically 2-5k tokens of output in a session that may already be at the 165k eviction boundary.

### Edge cases

1. **Compacted sessions:** After compaction, early messages are lost from the context window but remain in the JSONL. The JSONL is the complete record. This is an advantage over agent self-reporting, which can only describe what it remembers post-compaction.

2. **Multi-turn sessions with orchestrator prompts:** Multiple `user` text messages may appear (e.g., mid-session directives). The parser should collect all of them, not just the first.

3. **Bash tool calls that create files:** `mkdir -p && cat > file` patterns in Bash are not captured by the Write/Edit scan. Could parse Bash commands for redirect operators, but this gets fragile fast. Recommendation: accept the gap. Most structured file creation goes through Write/Edit.

4. **Skill invocations:** The `Skill` tool call shows `{skill, args}` but the skill's internal tool calls may not be individually logged as top-level JSONL entries. Need to verify whether skill-internal Write/Edit calls appear in the JSONL or are nested.

# Claude print versus interactive wire payload

Date: 2026-08-04

## Question

Does `claude -p` send the same provider request as an interactive Claude session?

## Method

Both runs used Transport Matters `prepare_captured_run` and its packaged addon. No alternate proxy or adapter was introduced.

- Claude Code: `2.1.221`
- Working directory: `/Users/alphab/Dev/LLM/DEV`
- Model selector: `sonnet`
- Prompt: `Reply exactly TM_PRINT_COMPARE_OK.`
- Transport Matters system injection: disabled for both runs
- Print launch difference: `-p`
- Comparison source: persisted `request.ir.json` parsed as `InternalRequest`
- Raw request bytes were excluded from the comparison.

Print evidence:

- Run: `1c7b2005-d622-43df-93cb-145c2f52c47b`
- Exchange: `e4075532-e5ca-401c-9e9f-749a7b22e4c9`
- IR: `/Users/alphab/.transport-matters/workspaces/dev-llm-dev/564ab4be/1c7b2005-d622-43df-93cb-145c2f52c47b/20260804T092807Z-e4075532/request.ir.json`
- IR SHA256: `a3cb25516bad4794e2a4bf2095e9f5db196e068742d543cc90793192112c5cda`

Interactive evidence:

- Run: `d4e6d372-4d60-47a5-8d64-2fe09155c8e6`
- Exchange: `e1de0139-c2f8-48b6-8e0e-e64e0c02487f`
- IR: `/Users/alphab/.transport-matters/workspaces/dev-llm-dev/564ab4be/d4e6d372-4d60-47a5-8d64-2fe09155c8e6/20260804T092815Z-e1de0139/request.ir.json`
- IR SHA256: `e5288264f69b9a26762c4e911195693c611dfaf24fd115ea3c0df7d5d6d2e047`

## System prompt

All three normalized system parts differ.

| Part | Print | Interactive | Cache control |
|---|---|---|---|
| 0 | 74 chars: `x-anthropic-billing-header: cc_version=2.1.221.08e; cc_entrypoint=sdk-cli;` | 70 chars: `x-anthropic-billing-header: cc_version=2.1.221.08e; cc_entrypoint=cli;` | absent in both |
| 1 | 62 chars: `You are a Claude agent, built on Anthropic's Claude Agent SDK.` | 57 chars: `You are Claude Code, Anthropic's official CLI for Claude.` | ephemeral, TTL 1h in both |
| 2 | 27,515 chars, SHA256 `0b42f74c91b5949f1713de1e257408dc8b5715cdbf79eea9881e74619ec40e60` | 32,870 chars, SHA256 `fb180cc215d49257da21fabf850d21051e5eaaa8e6a589ed5e8eae175d8e4206` | ephemeral, TTL 1h in both |

The interactive third part adds interactive shell guidance, a Scratchpad Directory section, and deferred interactive tool guidance including `EndConversation` and worktree commands. Its instruction body is 5,355 characters larger.

## Tools

Print has 20 tools:

`Agent`, `Bash`, `Edit`, `Read`, `ReportFindings`, `ScheduleWakeup`, `Skill`, `ToolSearch`, `Write`, `mcp__plugin_helioy-tools_cm__cx_browse`, `mcp__plugin_helioy-tools_cm__cx_deposit`, `mcp__plugin_helioy-tools_cm__cx_export`, `mcp__plugin_helioy-tools_cm__cx_forget`, `mcp__plugin_helioy-tools_cm__cx_get`, `mcp__plugin_helioy-tools_cm__cx_recall`, `mcp__plugin_helioy-tools_cm__cx_search`, `mcp__plugin_helioy-tools_cm__cx_stats`, `mcp__plugin_helioy-tools_cm__cx_store`, `DeferredToolPlaceholder`, `mcp__plugin_helioy-tools_cm__cx_update`.

Interactive has 22 tools. It has the same 20 names plus `Artifact` and `AskUserQuestion`. Definitions for all 20 common tools are identical in normalized IR.

## Other structural differences

- Model: identical, `anthropic/claude-sonnet-5`.
- Maximum tokens: identical, `64000`.
- Sampling: identical.
- Stream: `true` in both.
- System block count: three in both.
- System cache control placement: identical. Part 0 has none; parts 1 and 2 use ephemeral TTL 1h.
- Message roles: identical, `user` then `system`.
- User message: identical. The context block is 3,981 chars and the prompt block is 34 chars.
- Session start system message: print is 21,250 chars; interactive is 21,850 chars. Both carry ephemeral TTL 1h on the single block.
- Metadata: device and account identity are identical. The launcher owned session IDs differ, including the session ID embedded in Anthropic `user_id` metadata.
- Provider extras: both use adaptive thinking, high effort, and the same context management edit. Print additionally sends `thinking.display = "omitted"`.

## Verdict

The normalized requests are not equivalent. The most significant difference is the mode specific system instruction set: print identifies itself as an Agent SDK client and sends a 27,515 character third system part, while interactive identifies itself as Claude Code and sends a 32,870 character third system part. Print also omits `Artifact` and `AskUserQuestion`.

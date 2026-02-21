---
title: Claude Code Feature Flags - Complete tengu_ Flag Inventory and Internal Mechanics
type: research
tags: [claude-code, feature-flags, tengu, growthbook, statsig, reverse-engineering, internals]
summary: Comprehensive catalog of 50+ tengu_ feature flags in Claude Code, their evaluation pipeline (GrowthBook + Statsig), bypass mechanisms, and the tengu_coral_fern memory topic file auto-loading flag
status: active
source: deep-research
confidence: high
created: 2026-03-23
updated: 2026-03-23
---

## Executive Summary

Claude Code (internal codename "Tengu") uses a dual feature flag system powered by GrowthBook (primary, replacing Statsig post-OpenAI acquisition) to gate features behind server-controlled rollouts. Flags are cached locally in `~/.claude.json` under `cachedGrowthBookFeatures` (and legacy `cachedStatsigGates`), synced on startup, and can be overridden locally (though the server may rewrite them). The `tengu_coral_fern` flag specifically controls automatic loading of topic files referenced in MEMORY.md; it is disabled by default and, when enabled, would eliminate the need for the memory selection agent to manually read topic files on demand. As of v2.1.81 (March 2026), 28 flags are tracked in the official changelog tracker, though community documentation catalogs additional flags seen in earlier versions.

---

## 1. "Tengu" as Internal Codename

"Tengu" is Anthropic's internal project codename for Claude Code. This was first publicly identified by Tibor Blaho on X (Feb 2025) and confirmed through bundle analysis by multiple researchers.

- The codename appears in all feature flag prefixes (`tengu_`), in Statsig configuration keys, and in telemetry event names.
- Deedy Das (X post) asked Claude Code to explore its own binary and identified five project codenames: **Tengu** (Claude Code), **Penguin Mode** (fast mode), **Grove** (privacy/data system), **Amber Flint** (agent teams), **Marble Anvil** (thinking edits).

Source: [Tibor Blaho on X](https://x.com/btibor91/status/1895037705853247557), [Deedy Das on X](https://x.com/deedydas/status/2020350881464742330)

---

## 2. Feature Flag Infrastructure

### 2.1 Dual System: GrowthBook + Statsig

Claude Code uses two feature flag providers:

| Aspect | GrowthBook | Statsig |
|--------|-----------|---------|
| Cache key in ~/.claude.json | `cachedGrowthBookFeatures` | `cachedStatsigGates` |
| Role | Primary feature flags | Legacy gates + experiments |
| Server endpoint | GrowthBook API | `statsig.anthropic.com` |
| Migration status | Active, replacing Statsig | Being phased out (OpenAI acquired Statsig Sep 2025) |

Anthropic began migrating from Statsig to GrowthBook after OpenAI's acquisition of Statsig (Sep 2, 2025). GitHub issue #7151 raised supply chain concerns; Anthropic never publicly responded. The migration is in progress as of March 2026.

Source: [Issue #7151](https://github.com/anthropics/claude-code/issues/7151), [Issue #28941](https://github.com/anthropics/claude-code/issues/28941)

### 2.2 Flag Evaluation Pipeline

From the gastonmorixe bypass gist, the minified evaluation chain is:

```
lK() -> rt() -> nRA() -> lO()
```

When telemetry-disabling env vars are set, `lO()` returns true, causing `rt()` to return false, which makes `lK()` skip the cache entirely and return the default value (typically `false`). This is why setting `DISABLE_TELEMETRY=1` disables all feature flags.

**Evaluation order (inferred from multiple sources):**
1. Environment variables (highest priority) -- e.g., `ENABLE_TOOL_SEARCH`, `ENABLE_CLAUDEAI_MCP_SERVERS`
2. Application-level checks (subscription status via `hasAvailableSubscription`)
3. GrowthBook cached flags in `~/.claude.json` (`cachedGrowthBookFeatures`)
4. Statsig cached gates in `~/.claude.json` (`cachedStatsigGates`)
5. Hardcoded defaults (lowest priority)

Source: [gastonmorixe bypass gist](https://gist.github.com/gastonmorixe/9c596b6de1095b6bd3b746ca3a1fd3d7)

### 2.3 Flag Sync Mechanism

1. Claude Code starts up
2. Client sends user context to GrowthBook API (user ID, subscription tier, stable ID)
3. Server evaluates flag rules and returns current values
4. Results written to `cachedGrowthBookFeatures` in `~/.claude.json`
5. Local edits to `~/.claude.json` may be overwritten on next sync

### 2.4 Environment Variables That Disable All Flags

Setting any of these causes the flag evaluation to skip the cache and return defaults:

- `DISABLE_TELEMETRY=1`
- `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`
- `CLAUDE_CODE_USE_BEDROCK=1`
- `CLAUDE_CODE_USE_VERTEX=1`

### 2.5 Local Override Methods

**Direct edit** (fragile, gets overwritten):
```json
// ~/.claude.json
{
  "cachedGrowthBookFeatures": {
    "tengu_coral_fern": true
  }
}
```

**fs.readFileSync interception** (gastonmorixe method, persistent):
```bash
NODE_OPTIONS="--import $HOME/.claude/injectors/feature-flag-bypass-pure.mjs" claude
```
This hooks `fs.readFileSync`, intercepts reads of `.claude.json` and `.config.json`, and injects flag values into `cachedGrowthBookFeatures` before the application sees them. Zero disk writes.

**tweakcc** (Piebald-AI): patches the Claude Code binary/bundle directly to bypass specific gates like `tengu_brass_pebble`.

Source: [gastonmorixe gist](https://gist.github.com/gastonmorixe/9c596b6de1095b6bd3b746ca3a1fd3d7), [OmerFarukOruc gist](https://gist.github.com/OmerFarukOruc/77e87cb178bbd39abb448cf9cb93f94a), [tweakcc](https://github.com/Piebald-AI/tweakcc)

---

## 3. Complete Feature Flag Inventory

### 3.1 Flags from komen205/claude-code-feature-flags (v2.1.25, Jan 2026)

**Memory & Sessions:**
| Flag | Default | Purpose |
|------|---------|---------|
| `tengu_session_memory` | false | Persistent memory across sessions |
| `tengu_sm_compact` | false | Smart compaction with memory extraction |
| `tengu_coral_fern` | false | Auto-load topic files referenced in MEMORY.md |

**Integrations:**
| Flag | Default | Purpose |
|------|---------|---------|
| `tengu_claudeai_mcp_connectors` | false | Pull MCP servers from claude.ai account |
| `tengu_chrome_auto_enable` | false | Auto-enable Chrome extension |

**Planning & Workflow:**
| Flag | Default | Purpose |
|------|---------|---------|
| `tengu_plan_mode_interview_phase` | false | Interview/clarification before planning |
| `tengu_scratch` | false | Scratch/draft workspace |

**File Operations:**
| Flag | Default | Purpose |
|------|---------|---------|
| `tengu_marble_kite` | false | Skip "must read before write" validation |
| `tengu_file_write_optimization` | false | Shorter write confirmations |

**API & Performance:**
| Flag | Default | Purpose |
|------|---------|---------|
| `tengu_streaming_tool_execution2` | true | Stream tool execution |
| `tengu_bash_haiku_prefetch` | true | Prefetch with Haiku for bash |
| `tengu_compact_cache_prefix` | true | Cache prefix optimization |
| `tengu_system_prompt_global_cache` | false | Global system prompt caching |

**Extended Thinking:**
| Flag | Default | Purpose |
|------|---------|---------|
| `tengu_marble_anvil` | true | Keep all thinking blocks |
| `tengu_workout` | false | Effort/thinking level controls |

**Premium:**
| Flag | Default | Purpose |
|------|---------|---------|
| `tengu_brass_pebble` | false | Agent swarms (max/team plan) |

**UI/UX:**
| Flag | Default | Purpose |
|------|---------|---------|
| `tengu_code_diff_cli` | true | Diff view in CLI |
| `tengu_pr_status_cli` | true | PR status in footer |
| `tengu_permission_explainer` | true | Explain permission requests |
| `tengu_keybinding_customization_release` | true | Custom keybindings |
| `tengu_thinkback` | false | /think-back year-in-review animation |

**Search:**
| Flag | Default | Purpose |
|------|---------|---------|
| `tengu_mcp_tool_search` | true | Search across MCP tools |

### 3.2 Flags from marckrenn/claude-code-changelog (v2.1.81, Mar 2026)

**Feature Gates (12):**
`tengu_ccr_bridge`, `tengu_ccr_bridge_multi_session`, `tengu_ccr_bundle_seed_enabled`, `tengu_chair_sermon`, `tengu_disable_bypass_permissions_mode`, `tengu_scratch`, `tengu_streaming_tool_execution2`, `tengu_thinkback`, `tengu_tool_pear`, `tengu_toolref_defer_j8m`, `tengu_vscode_onboarding`, `tengu_vscode_review_upsell`

**Dynamic Configs (16):**
`tengu_1p_event_batch_config`, `tengu_auto_mode_config`, `tengu_bad_survey_transcript_ask_config`, `tengu_bridge_initial_history_cap`, `tengu_bridge_min_version`, `tengu_bridge_poll_interval_config`, `tengu_desktop_upsell`, `tengu_feedback_survey_config`, `tengu_good_survey_transcript_ask_config`, `tengu_iron_gate_closed`, `tengu_kairos_brief`, `tengu_kairos_cron`, `tengu_kairos_cron_config`, `tengu_max_version_config`, `tengu_sm_compact_config`, `tengu_sm_config`

### 3.3 Flags from GitHub Issues (various versions)

| Flag | Source | Purpose |
|------|--------|---------|
| `tengu_amber_quartz` | #33580 | Voice mode (/voice command) |
| `tengu_ccr_bridge` | #34528, #36034 | Remote Control |
| `tengu_copper_bridge` | #27178 | Chrome extension socket mode |
| `tengu_c4w_usage_limit_notifications_enabled` | #19869 | Usage limit notifications |
| `tengu_pid_based_version_locking` | #19869 | Multi-process version locking |
| `tengu_marble_sandcastle` | #29015 | Fast mode (native binary gating) |
| `tengu_prompt_cache_1h_config` | blog | 1-hour prompt cache TTL for Max subscribers |

### 3.4 Flags from X/Twitter and Other Sources

| Flag | Source | Purpose |
|------|--------|---------|
| `tengu_system_prompt_global_cache` | @bhaidar X | Global prompt caching (v2.1.23) |
| `tengu_workout` | @bhaidar X | Effort/thinking controls (v2.1.23) |

---

## 4. tengu_coral_fern: Deep Analysis

### 4.1 What It Controls

`tengu_coral_fern` gates automatic loading of topic files referenced in MEMORY.md. Currently (disabled by default):

- MEMORY.md is loaded into the system prompt (first 200 lines)
- Topic files (e.g., `debugging.md`, `patterns.md`) exist in the memory directory but are NOT auto-loaded
- Claude must use Read tool to access topic files on-demand during a session
- A "memory selection agent" or "determine which memory files to attach" sub-agent evaluates which files are relevant

If `tengu_coral_fern` were enabled:

- Topic files linked from MEMORY.md would be automatically loaded at session start
- This would replace the on-demand reading pattern with proactive injection
- The memory selection agent's role would shift from reactive (read when needed) to proactive (pre-load at startup)

### 4.2 Source of Information

Giuseppe Gurgone's blog post at giuseppegurgone.com/claude-memory is the primary source. Key methodology: Gurgone "tasked Claude Code to research its own minified CLI bundle." The agent found:

- `U_` = "MEMORY.md" (the filename constant in the minified bundle)
- `pZ` = 200 (the line limit constant)
- The `tengu_coral_fern` flag name gating topic file auto-loading

Gurgone notes: "I asked the agent to verify the discoveries a few times but haven't verified them myself manually so some information might be inaccurate."

### 4.3 Relationship to Other Memory Flags

The three memory flags form a progression:

1. **`tengu_session_memory`** (gate): Enables session memory writing/recall. Background process extracts summaries every ~5k tokens or 3 tool calls. First extraction at ~10k tokens.
2. **`tengu_sm_compact`** (gate): Enables instant compaction using pre-written session memory summaries instead of re-analyzing the conversation.
3. **`tengu_coral_fern`** (gate): Enables auto-loading of topic files from MEMORY.md at startup.

Together, these represent Anthropic's phased rollout of persistent memory capabilities.

### 4.4 Version and Status

- First documented by komen205 in the community feature flags repo, tested on v2.1.25 (Jan 2026)
- Described by Gurgone's blog post (undated, likely Feb-Mar 2026 based on SDK version context)
- As of v2.1.81 (Mar 21, 2026): NOT listed in the marckrenn changelog tracker's 28 flags, suggesting it may have been removed, renamed, or is evaluated through a different mechanism than the tracked Statsig gates/configs
- The claudefast.com session memory guide confirms `tengu_session_memory` is a Statsig gate; the same system likely controls `tengu_coral_fern`

### 4.5 The Memory Selection Agent

The Piebald-AI system prompts repo tracks an agent prompt called "Determine which memory files to attach" (218 tokens). This agent:

- Reads the memory directory
- Evaluates which topic files are relevant to the current query
- Attaches selected files to the main agent's context

If `tengu_coral_fern` is enabled, this agent's role would likely change: instead of selecting files on-demand, topic files would be pre-loaded based on MEMORY.md references, potentially making the selection agent unnecessary for the common case.

### 4.6 How to Enable It (Theoretically)

Edit `~/.claude.json`:
```json
{
  "cachedGrowthBookFeatures": {
    "tengu_coral_fern": true
  }
}
```

Or use the gastonmorixe bypass to inject it via `fs.readFileSync` interception. Note: the server may overwrite this on next sync.

---

## 5. Bundle Analysis Details

### 5.1 The cli.mjs Bundle

Claude Code's main logic lives in `cli.mjs`, a ~20MB single file that is heavily obfuscated. Variables are renamed to non-semantic names (e.g., `U_`, `pZ`, `fR`, `i7`, `f6`, `Lu`). The bundle uses:

- `commander` for CLI parsing
- `ink` for React-based terminal UI
- `zod` for schema validation
- `ripgrep` for file traversal

### 5.2 System Prompt Construction

The system prompt is assembled dynamically via promise-based stitching:
- `fR()` returns the system prompt
- `i7()` provides tool function definitions
- `f6()` specifies the model
- `Lu()` supplies the thinking scratchpad

### 5.3 Obfuscation and Analysis Limitations

Lines are concatenated, modules clumped. Meaningful function names are gone. Analysis relies on:
- String literal search (flag names are stored as plaintext strings)
- Control flow inference from known behavior
- Having Claude Code analyze its own bundle (Gurgone's method)

---

## 6. Key Configuration Files and Paths

| Path | Purpose |
|------|---------|
| `~/.claude.json` | Primary config; contains `cachedGrowthBookFeatures`, `cachedStatsigGates`, `hasAvailableSubscription` |
| `~/.claude/settings.json` | User settings (e.g., `autoMemoryEnabled`) |
| `~/.claude/settings.local.json` | Local-only user settings |
| `~/.claude/projects/<hash>/memory/MEMORY.md` | Project memory index (200-line cap) |
| `~/.claude/projects/<hash>/<session-id>/session-memory/summary.md` | Session memory summaries |
| `~/.claude/agent-memory/<name>/MEMORY.md` | User-scope agent memory |
| `~/.claude/agent-memory-local/<name>/` | Local-scope agent memory |

### Memory Settings

Enable auto-memory: `~/.claude/settings.json` with `"autoMemoryEnabled": true`
Disable auto-memory: `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`

---

## 7. Notable Incidents with Feature Flags

### 7.1 MCP Connectors Without Consent (#28941)

`tengu_claudeai_mcp_connectors` was silently enabled server-side, injecting Gmail and Google Calendar MCP servers into Claude Code sessions without user consent. Servers connected through `mcp-proxy.anthropic.com`. Workaround: `export ENABLE_CLAUDEAI_MCP_SERVERS=false`.

### 7.2 tengu_scratch Freeze Bug (#19869)

Setting `tengu_scratch: true` caused Claude Code to freeze on launch. The flag auto-reset to `true` on each exit, requiring users to create wrapper scripts or bash aliases to force it back to `false`.

### 7.3 Remote Control Regressions (#34528, #36034)

`tengu_ccr_bridge` returned `false` for valid Max subscribers due to server-side GrowthBook rule misconfiguration. The flag could not be overridden locally because the server re-evaluated it on each sync.

---

## Sources Consulted

### Primary Sources
- [Giuseppe Gurgone - Claude Code's Experimental Memory System](https://giuseppegurgone.com/claude-memory)
- [komen205/claude-code-feature-flags](https://github.com/komen205/claude-code-feature-flags) (MIT, community documentation)
- [marckrenn/claude-code-changelog cc-flags.md](https://github.com/marckrenn/claude-code-changelog/blob/main/cc-flags.md)
- [gastonmorixe - Feature Flag Bypass Gist](https://gist.github.com/gastonmorixe/9c596b6de1095b6bd3b746ca3a1fd3d7)
- [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts)
- [Piebald-AI/tweakcc](https://github.com/Piebald-AI/tweakcc)
- [turboai.dev - Claude Code Version Tracker](https://www.turboai.dev/blog/claude-code-versions)

### GitHub Issues (anthropics/claude-code)
- [#28941 - tengu_claudeai_mcp_connectors without consent](https://github.com/anthropics/claude-code/issues/28941)
- [#19869 - tengu_scratch freeze bug](https://github.com/anthropics/claude-code/issues/19869)
- [#18397 - tengu_mcp_tool_search not working](https://github.com/anthropics/claude-code/issues/18397)
- [#33580 - tengu_amber_quartz voice mode](https://github.com/anthropics/claude-code/issues/33580)
- [#34528 - tengu_ccr_bridge regression](https://github.com/anthropics/claude-code/issues/34528)
- [#36034 - tengu_ccr_bridge unavailable](https://github.com/anthropics/claude-code/issues/36034)
- [#7151 - Statsig/OpenAI acquisition concern](https://github.com/anthropics/claude-code/issues/7151)
- [#27178 - tengu_copper_bridge Chrome extension](https://github.com/anthropics/claude-code/issues/27178)
- [#29015 - tengu_marble_sandcastle fast mode](https://github.com/anthropics/claude-code/issues/29015)

### X/Twitter
- [Tibor Blaho - Tengu codename identification](https://x.com/btibor91/status/1895037705853247557)
- [Deedy Das - All codenames from binary exploration](https://x.com/deedydas/status/2020350881464742330)
- [Bilal Haidar - v2.1.23 flag additions](https://x.com/bhaidar/status/2016761567518277674)

### Blog Posts and Guides
- [ClaudeFast - Session Memory Guide](https://claudefa.st/blog/guide/mechanics/session-memory)
- [Lee Han Chung - Poking Around Claude Code](https://leehanchung.github.io/blogs/2025/03/07/claude-code/)
- [Ian Paterson - Claude Code Memory Architecture](https://ianlpaterson.com/blog/claude-code-memory-architecture/)

### Reddit
- No relevant results found. Reddit has near-zero signal for Claude Code internals topics.

### Hacker News
- No substantive discussions found about feature flags specifically.

---

## Source Quality Assessment

**High confidence:** The feature flag names, their storage location (`cachedGrowthBookFeatures` in `~/.claude.json`), and the GrowthBook evaluation mechanism are confirmed across 5+ independent sources (GitHub issues, bypass gists, community repos, blog posts, and Piebald-AI system prompt tracking).

**Medium confidence:** The specific purpose of `tengu_coral_fern` (topic file auto-loading) comes primarily from Giuseppe Gurgone's blog post, which itself relies on Claude Code analyzing its own minified bundle. Gurgone explicitly disclaims manual verification. The komen205 feature flags repo independently lists the same flag with a different description ("Access past sessions from current conversation"). These may be two aspects of the same feature, or the descriptions may be imprecise.

**Low confidence:** The internal evaluation chain function names (`lK`, `rt`, `nRA`, `lO`) come from the gastonmorixe bypass gist's analysis of the minified bundle. These names are non-semantic and version-dependent; they will change with bundle updates.

---

## Open Questions

1. **Has tengu_coral_fern been renamed or removed?** It appears in the komen205 repo (v2.1.25) but NOT in the marckrenn changelog tracker (v2.1.81). Was it graduated to a different mechanism, merged into `tengu_sm_config`, or removed entirely?

2. **What exactly does "access past sessions from current conversation" mean?** The komen205 repo describes `tengu_coral_fern` differently than Gurgone's blog. Is this about topic file loading, session history access, or both?

3. **Statsig to GrowthBook migration completeness.** Which flags are still on Statsig vs. fully migrated to GrowthBook? The `cachedStatsigGates` key still exists in `~/.claude.json`.

4. **What do the mystery flags control?** `tengu_chair_sermon`, `tengu_tool_pear`, `tengu_toolref_defer_j8m`, `tengu_kairos_brief/cron` have no public documentation of their purpose.

5. **Can users reliably enable tengu_coral_fern locally?** Does the flag require server-side support (like `tengu_ccr_bridge`), or is it purely a client-side gate that respects local overrides?

---

## Actionable Takeaways

1. **To inspect your current flags:** `cat ~/.claude.json | python3 -m json.tool | grep tengu`

2. **To override a flag locally (fragile):** Edit `cachedGrowthBookFeatures` in `~/.claude.json`. Set `DISABLE_TELEMETRY` and `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` to prevent sync (but this disables ALL flags).

3. **To override a flag persistently:** Use the gastonmorixe `fs.readFileSync` interception method via `NODE_OPTIONS="--import"`. This survives server syncs.

4. **To track flag changes across versions:** Watch the [marckrenn/claude-code-changelog](https://github.com/marckrenn/claude-code-changelog) repo, which updates within minutes of each release.

5. **For memory topic file loading specifically:** Until `tengu_coral_fern` is widely enabled, the current workaround is to keep MEMORY.md under 200 lines as a concise index with links to topic files, and rely on the memory selection agent to read them on-demand. Alternatively, structure your MEMORY.md so the most important pointers are in the first 200 lines.

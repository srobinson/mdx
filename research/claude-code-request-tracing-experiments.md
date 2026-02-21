---
title: Claude Code Request Tracing Experiments
category: research
tags: [claude-code, debugging, tokens, proxy, mitmproxy, optimization]
created: 2026-03-17
updated: 2026-03-17
---

# Claude Code Request Tracing

Concrete instructions for intercepting and analyzing Claude Code API requests. Use this to measure token startup costs, identify bloat, and validate optimization changes.

## Prerequisites

```bash
brew install mitmproxy   # already installed
```

The capture script lives at `/tmp/capture_claude_request.py`. Copy it somewhere permanent if needed.

## Method 1: mitmproxy (structured analysis)

Best for: measuring token breakdown by section, comparing before/after changes.

### Step 1: Save the capture script

```bash
cat > ~/.claude/scripts/capture_claude_request.py << 'PYEOF'
"""mitmproxy addon: capture Claude API request body to /tmp/claude_request.json"""
import json

def request(flow):
    if flow.request.path.startswith("/v1/messages"):
        body = json.loads(flow.request.get_text())
        with open("/tmp/claude_request.json", "w") as f:
            json.dump(body, f, indent=2)

        system_parts = body.get("system", [])
        tools = body.get("tools", [])
        messages = body.get("messages", [])

        total_system_chars = sum(len(json.dumps(p)) for p in system_parts)
        total_tools_chars = sum(len(json.dumps(t)) for t in tools)

        print(f"\n{'='*60}")
        print(f"MODEL: {body.get('model', 'unknown')}")
        print(f"SYSTEM PARTS: {len(system_parts)} ({total_system_chars:,} chars / ~{total_system_chars//4:,} tokens)")
        print(f"TOOLS: {len(tools)} ({total_tools_chars:,} chars / ~{total_tools_chars//4:,} tokens)")
        print(f"MESSAGES: {len(messages)}")
        print(f"TOTAL BODY: {len(flow.request.get_text()):,} chars / ~{len(flow.request.get_text())//4:,} tokens")
        print(f"{'='*60}")

        print(f"\n--- SYSTEM PROMPT BREAKDOWN ---")
        for i, part in enumerate(system_parts):
            if isinstance(part, dict):
                text = part.get("text", "")
                ptype = part.get("type", "unknown")
                chars = len(text)
                first_line = text[:120].replace('\n', ' ').strip()
                print(f"  [{i}] {ptype}: {chars:,} chars (~{chars//4:,} tok) | {first_line}...")
            else:
                print(f"  [{i}] {type(part)}: {len(str(part)):,} chars")

        print(f"\n--- TOOLS BREAKDOWN (top 20 by size) ---")
        tool_sizes = []
        for t in tools:
            name = t.get("name", "unknown")
            chars = len(json.dumps(t))
            tool_sizes.append((name, chars))

        tool_sizes.sort(key=lambda x: -x[1])
        for name, chars in tool_sizes[:20]:
            print(f"  {name}: {chars:,} chars (~{chars//4:,} tok)")
        if len(tool_sizes) > 20:
            rest = sum(c for _, c in tool_sizes[20:])
            print(f"  ... +{len(tool_sizes)-20} more tools: {rest:,} chars (~{rest//4:,} tok)")
        print(f"{'='*60}")
PYEOF
```

### Step 2: Start proxy (Terminal 1)

```bash
mitmdump \
  --mode reverse:https://api.anthropic.com \
  --listen-port 8002 \
  -s ~/.claude/scripts/capture_claude_request.py
```

### Step 3: Run claude through proxy (Terminal 2)

```bash
# Minimal test (measures baseline startup cost)
ANTHROPIC_BASE_URL=http://localhost:8002 claude --print "Say hello"

# Interactive session (measures full interactive overhead)
ANTHROPIC_BASE_URL=http://localhost:8002 claude
```

### Step 4: Analyze

The proxy terminal prints the breakdown live. The raw JSON is saved to `/tmp/claude_request.json` for deeper analysis.

```bash
# Quick size check
wc -c /tmp/claude_request.json

# Count tools
jq '.tools | length' /tmp/claude_request.json

# List all tool names sorted by definition size
jq -r '.tools[] | "\(.name)\t\(. | tostring | length)"' /tmp/claude_request.json | sort -t$'\t' -k2 -nr | head -30

# System prompt parts count and sizes
jq '[.system[] | {type, chars: (.text // . | tostring | length)}]' /tmp/claude_request.json

# Extract just the system prompt text for reading
jq -r '.system[].text // empty' /tmp/claude_request.json > /tmp/claude_system_prompt.txt

# Check which agent descriptions are in the Agent tool
jq -r '.tools[] | select(.name == "Agent") | .description' /tmp/claude_request.json > /tmp/claude_agent_tool.txt
```

## Method 2: claude-code-logger (quick visual inspection)

Best for: seeing the conversation flow, quick sanity checks.

### Terminal 1

```bash
npx claude-code-logger start --log-body --merge-sse -v -p 8001
```

### Terminal 2

```bash
ANTHROPIC_BASE_URL=http://localhost:8001 claude
```

Everything streams to Terminal 1 in a readable format. No file output.

## Method 3: Shell alias for convenience

Add to `~/.zshrc`:

```bash
# Traced claude session (requires proxy running on 8002)
alias claude-trace='ANTHROPIC_BASE_URL=http://localhost:8002 claude'
alias claude-trace-print='ANTHROPIC_BASE_URL=http://localhost:8002 claude --print'
```

## Experiment Log

### 2026-03-17: Baseline after plugin cleanup

**Context:** Uninstalled 15 plugins (10 voltagent, typescript-lsp, rust-analyzer-lsp, skill-creator, document-skills, pr-review-toolkit). Remaining: helioy-tools, helioy-bus.

**Results:**
```
MODEL: claude-opus-4-6
SYSTEM PARTS: 3 (33,490 chars / ~8,372 tokens)
TOOLS: 185 (241,766 chars / ~60,441 tokens)
MESSAGES: 1
TOTAL BODY: 283,976 chars / ~70,994 tokens
```

**Top token consumers:**
| Component | Tokens | % of total |
|-----------|--------|------------|
| Tools (185 total) | ~60,441 | 85% |
| System prompt | ~8,372 | 12% |
| Messages | ~2,180 | 3% |

**Top tools by size:**
| Tool | Tokens |
|------|--------|
| Agent (34 agent descriptions) | ~7,656 |
| pencil:batch_design | ~3,374 |
| Bash | ~3,151 |
| TodoWrite | ~2,611 |
| AskUserQuestion | ~1,252 |
| EnterPlanMode | ~1,083 |
| pencil:spawn_agents | ~1,064 |
| pencil:batch_get | ~1,020 |
| Remaining 165 tools | ~31,632 |

### Running your own experiment

After making a change (disabling a plugin, trimming agents, etc.):

1. Start the proxy: `mitmdump --mode reverse:https://api.anthropic.com --listen-port 8002 -s ~/.claude/scripts/capture_claude_request.py`
2. Run: `ANTHROPIC_BASE_URL=http://localhost:8002 claude --print "hello"`
3. Record the output in a new section below
4. Compare against the baseline above

### Template for new entries

```
### YYYY-MM-DD: <what changed>

**Context:** <what was modified>

**Results:**
MODEL:
SYSTEM PARTS: X (Y chars / ~Z tokens)
TOOLS: X (Y chars / ~Z tokens)
TOTAL BODY: Y chars / ~Z tokens

**Delta from baseline:** <+/- tokens>
```

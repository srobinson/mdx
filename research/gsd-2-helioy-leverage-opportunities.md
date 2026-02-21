---
title: "GSD-2 Patterns Leverageable for Helioy Ecosystem"
date: 2026-03-18
category: research
tags: [gsd, helioy, patterns, leverage, architecture, extension-system, agent-loop]
summary: "Specific architectural patterns and approaches from GSD-2 that could benefit Helioy ecosystem components (am, cm, fmm, mdm, helioy-bus, helioy-plugins)."
---

# GSD-2: Leverage Opportunities for Helioy

## 1. EventStream Pattern for helioy-bus

### What GSD Does

`EventStream<T, R>` (`pi-ai/utils/event-stream.ts`) is a generic push-based async iterable with a final result promise. 87 lines, zero dependencies. It solves the problem of streaming events while also providing a terminal result.

```typescript
class EventStream<T, R> implements AsyncIterable<T> {
    constructor(isComplete: (event: T) => boolean, extractResult: (event: T) => R)
    push(event: T): void
    end(result?: R): void
    result(): Promise<R>
}
```

### Why It Matters for Helioy

helioy-bus needs to stream messages between agents while tracking completion. This pattern provides:
- Back-pressure via async iteration (consumer controls pace)
- Completion detection without separate signaling
- Works for both LLM streaming and inter-agent message passing
- Zero dependencies, trivially portable to Rust

### Specific Application

The helioy-bus message protocol could use this pattern for agent-to-agent communication streams. An agent sending a request to another agent gets an `EventStream<BusMessage, BusResult>` that delivers progress events and a final result.

---

## 2. Extension System Architecture for helioy-plugins

### What GSD Does

The extension system separates three concerns:
1. **Registration** (during load): `registerTool()`, `registerCommand()`, `on(event, handler)`
2. **Runtime binding** (post-load): `bindCore()` replaces stubs with real implementations
3. **Execution context** (per-call): `createContext()` provides fresh context for each handler invocation

Key insight: extensions register during load phase but cannot call action methods until `bindCore()` runs. Provider registrations are queued during load and flushed post-bind.

### Why It Matters for Helioy

helioy-plugins currently loads MCP servers. The GSD pattern of separating registration from binding solves the initialization ordering problem: plugins can declare what they provide before the runtime is fully initialized. The two-phase approach prevents errors from premature method calls.

### Specific Patterns to Adopt

1. **ExtensionRuntime with throwing stubs**: Initialize all action methods as stubs that throw "not initialized" errors. Replace with real implementations in `bindCore()`. This catches ordering bugs at development time.

2. **Virtual module system for distribution**: GSD uses jiti's `virtualModules` for Bun binary distribution. helioy-plugins should consider the same approach for distributing plugins that import from helioy packages.

3. **Event dispatch with early termination**: Extension event handlers run in series. Tool call handlers can return `{ block: true }` to short-circuit execution. Context handlers chain transforms. This gives extensions fine-grained control without complex priority systems.

4. **Trust on first use (TOFU)**: Project-local extensions require explicit trust before loading. helioy-plugins should adopt the same security model for project-scoped plugin discovery.

---

## 3. Agent Loop Design for helioy-bus Orchestration

### What GSD Does

The agent loop (`pi-agent-core/agent-loop.ts`) has a nested loop structure:
- Outer loop: continues when follow-up messages arrive after agent would stop
- Inner loop: processes tool calls and steering messages

The `transformContext` hook allows modifying messages before each LLM call (context pruning, injection). The `convertToLlm` hook translates agent messages to provider-specific format.

### Why It Matters for Helioy

helioy-bus orchestration (warroom) needs to manage multi-agent conversations. The GSD pattern of separating "agent message" from "LLM message" is directly applicable:

- **AgentMessage**: Any message in the conversation (custom types via declaration merging)
- **Message**: LLM-compatible subset (user/assistant/toolResult)
- **convertToLlm**: Translates at the boundary

This allows helioy-bus to carry its own message types (coordination signals, context metadata, agent handoffs) that get stripped before reaching the LLM.

### Steering Messages for Agent Coordination

The steering queue pattern maps directly to inter-agent coordination:
- Agent A sends a steering message to Agent B while B is processing
- B finishes current tool, skips remaining tools, processes steering message
- This provides non-destructive interruption without aborting in-flight work

---

## 4. Provider Abstraction Patterns for Helix

### What GSD Does

The `ApiProvider` registry allows runtime registration/unregistration of providers. Models carry their API protocol, provider, base URL, and compatibility overrides as first-class data.

The `compat` field on models is particularly pragmatic:
```typescript
interface OpenAICompletionsCompat {
    supportsStore?: boolean;
    supportsDeveloperRole?: boolean;
    supportsReasoningEffort?: boolean;
    maxTokensField?: "max_completion_tokens" | "max_tokens";
    requiresToolResultName?: boolean;
    thinkingFormat?: "openai" | "zai" | "qwen";
}
```

### Why It Matters for Helioy

Helix (the unified intelligent context API) needs to abstract across different context sources. The GSD approach of:
1. Registry pattern for providers
2. Model/source metadata as first-class data
3. Per-source compatibility overrides
4. Lazy loading of provider SDKs

...applies directly to Helix's need to abstract across cm, am, and mdm.

### Specific Application

Define a `ContextProvider` interface analogous to `ApiProvider`:
```typescript
interface ContextProvider {
    source: ContextSource;  // "am" | "cm" | "mdm" | custom
    query: (params: QueryParams) => ContextStream;
    querySimple: (params: SimpleQueryParams) => ContextStream;
}
```

Register providers at runtime. Sources carry their capabilities and quirks as metadata.

---

## 5. Session Management Patterns for context-matters

### What GSD Does

Sessions are JSONL files with typed entries. Key patterns:

1. **Append-only**: New entries are appended. No in-place modification.
2. **Blob externalization**: Image data above 1KB is stored in a separate blob store, replaced with references in the session file.
3. **Compaction**: Old messages are replaced with a summary entry. File operations from compacted messages are preserved in compaction details.
4. **Tree branching**: Sessions support forking from any entry point, with branch summaries preserving context.
5. **Atomic writes**: Uses `proper-lockfile` for concurrent access safety.

### Why It Matters for Helioy

context-matters stores structured context. The GSD patterns of blob externalization (large data out of the hot path), compaction (summarize old context while preserving key facts), and tree branching (explore alternatives) are directly applicable to cm's context lifecycle management.

### Specific Pattern: Compaction with File Operation Tracking

GSD's compaction preserves `readFiles` and `modifiedFiles` across compaction boundaries. When old messages are summarized, the tool-use history is extracted and stored in `CompactionDetails`. This ensures the agent remembers which files were touched even after context is pruned.

cm could adopt the same pattern: when context is pruned or summarized, extract and preserve key factual references (entity IDs, timestamps, relationships) in summary metadata.

---

## 6. Native Performance Bridge for fmm and mdm

### What GSD Does

Performance-critical operations are implemented in Rust and exposed via NAPI:
- **grep**: Regex search respecting gitignore
- **glob**: File pattern matching with streaming callbacks
- **text**: Unicode-aware wrapping, width calculation, truncation
- **diff**: Unified diff generation
- **ast**: Tree-sitter operations
- **json_parse**: Streaming/partial JSON parsing
- **gsd_parser**: Domain-specific file parsing (frontmatter, sections)

Cross-platform distribution via platform-specific npm optional dependencies:
```
@gsd-build/engine-darwin-arm64
@gsd-build/engine-linux-x64-gnu
...
```

### Why It Matters for Helioy

fmm already uses Rust. But the GSD distribution strategy is worth studying:

1. **Optional dependency per platform**: The main package declares them as `optionalDependencies`. Installation on a supported platform pulls the right binary automatically.
2. **Three-tier fallback**: npm package -> local release build -> local dev build. Development never blocked by distribution.
3. **TypeScript wrappers**: Each native module has a TS wrapper that handles loading and provides typed interfaces.

This is exactly the pattern fmm, am, cm, and mdm should use for npm distribution of their Rust binaries.

### Specific Module Worth Studying

`gsd_parser` in the Rust crate handles frontmatter parsing, section extraction, and batch file parsing. The `batchParseGsdFiles(directory)` function scans an entire directory of structured files in native code. fmm does similar work. The batch parsing approach (one native call for N files) is more efficient than N native calls.

---

## 7. Differential TUI Rendering for Interactive Helioy Tools

### What GSD Does

Custom TUI with:
- **Differential rendering**: Compares new output with previous, only updates changed lines
- **Synchronized output**: Wraps updates in `CSI ?2026h/l` to prevent flicker
- **Overlay compositing**: Modal components rendered on top of base content with column-level splicing
- **Component model**: Simple `render(width): string[]` interface

### Why It Matters for Helioy

If any Helioy tool needs a rich terminal interface (e.g., an interactive context browser, a memory visualization, a bus monitoring dashboard), the GSD TUI patterns provide a proven approach. The key insight is that the differential rendering algorithm is general-purpose and independent of the component model.

The overlay system is particularly useful for modal dialogs (confirm actions, select from options) overlaid on a running agent display.

---

## 8. Tool Schema Validation Pattern

### What GSD Does

Tools define parameters using TypeBox schemas:
```typescript
parameters: Type.Object({
    command: Type.String({ description: "The bash command to run" }),
    timeout: Type.Optional(Type.Number({ description: "Timeout in ms" })),
})
```

The agent loop validates arguments before execution via `validateToolArguments(tool, toolCall)`. Invalid arguments are caught before the tool runs, producing a clean error tool result.

### Why It Matters for Helioy

helioy-plugins MCP tools need runtime validation. TypeBox provides:
- Runtime validation from the same schema that generates JSON Schema for tool descriptions
- TypeScript type inference from schemas (`Static<typeof schema>`)
- No separate type definitions and validation logic

All Helioy MCP tools should use TypeBox for parameter schemas.

---

## 9. Hashline Editing Approach

### What GSD Does

Files are read with hash anchors:
```
1#a3f  function hello() {
2#b7c    console.log("world");
3#e2d  }
```

Edits reference lines by hash instead of line number:
```
anchor: "b7c"
replacement: '  console.log("hello world");'
```

This is resilient against line number shifts between read and edit operations (e.g., another tool added lines above).

### Why It Matters for Helioy

fmm's `fmm_read_symbol` returns source code by line ranges. If fmm ever provides edit capabilities, the hashline approach would prevent edit failures from stale line references. Even without edits, the hash-based line identification could improve fmm's cross-session symbol tracking.

---

## 10. File-Based State Machine for Autonomous Workflows

### What GSD Does

The GSD auto mode uses filesystem state (`.gsd/` directory) as the source of truth:
- Each agent session reads state from disk on start
- After agent_end, state is derived again from disk
- Next action is determined by file presence/content
- No in-memory state carries across sessions

This makes the system crash-recoverable by design. A crashed session can be resumed by simply starting a new one: it reads disk state and picks up where the last one left off.

### Why It Matters for Helioy

helioy-bus warroom orchestration could benefit from this pattern:
- Agent coordination state stored on filesystem (or in SQLite)
- Each agent reads shared state on start
- Progress tracked via state files rather than in-memory coordination
- Crash recovery is automatic: restart the agent, it reads current state

The GSD implementation includes crash locks, runtime records, and session forensics. These patterns are directly applicable to long-running multi-agent workflows.

---

## Summary: Priority Adoption Order

| Priority | Pattern | Target Component | Effort |
|----------|---------|-----------------|--------|
| 1 | EventStream for message streaming | helioy-bus | Low |
| 2 | Two-phase extension loading | helioy-plugins | Medium |
| 3 | Native binary npm distribution | fmm, am, cm, mdm | Medium |
| 4 | TypeBox tool schema validation | helioy-plugins | Low |
| 5 | AgentMessage/Message separation | helioy-bus | Medium |
| 6 | Steering queue for agent coordination | helioy-bus warroom | Medium |
| 7 | Provider registry with compat overrides | Helix | Medium |
| 8 | Session JSONL with compaction | context-matters | High |
| 9 | File-based state machine | helioy-bus warroom | High |
| 10 | Differential TUI rendering | Future CLI tools | Low (optional) |

---

## Key Files for Reference

| File | What to study |
|------|--------------|
| `packages/pi-ai/src/utils/event-stream.ts` | EventStream pattern (87 lines) |
| `packages/pi-agent-core/src/agent-loop.ts` | Agent loop with steering/follow-up (705 lines) |
| `packages/pi-agent-core/src/types.ts` | AgentMessage, AgentTool, AgentEvent types |
| `packages/pi-ai/src/api-registry.ts` | Provider registry pattern |
| `packages/pi-ai/src/types.ts` | Model interface with compat overrides |
| `packages/pi-coding-agent/src/core/extensions/loader.ts` | Two-phase extension loading |
| `packages/pi-coding-agent/src/core/extensions/wrapper.ts` | Tool interception pattern |
| `packages/pi-coding-agent/src/core/session-manager.ts` | JSONL session persistence |
| `packages/pi-coding-agent/src/core/compaction/compaction.ts` | Context compaction |
| `packages/native/src/native.ts` | Three-tier native addon loading |
| `native/crates/engine/Cargo.toml` | Rust dependency surface |
| `packages/pi-tui/src/tui.ts` | Differential rendering engine |
| `src/resources/extensions/gsd/auto.ts` | File-based state machine |
| `packages/pi-ai/src/providers/transform-messages.ts` | Cross-provider message normalization |

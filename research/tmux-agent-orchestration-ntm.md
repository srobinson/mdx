---
title: "NTM: Named Tmux Manager for Multi-Agent Orchestration"
type: research
tags: [tmux, multi-agent, orchestration, go, cli, dicklesworthstone, agent-coordination]
summary: "Go-based tmux orchestration system that turns tmux into a local control plane for parallel AI coding agents (Claude, Codex, Gemini), with safety policies, durable state, ensemble reasoning, and REST/WebSocket APIs."
status: active
source: github-researcher
confidence: high
created: 2026-04-24
updated: 2026-04-24
---

## Executive Summary

NTM (Named Tmux Manager) is a Go binary (~300K lines of production Go, ~460K lines of tests) that layers structured multi-agent orchestration on top of tmux. Built by Dicklesworthstone, it provides session lifecycle management, work graph triage, safety policy enforcement, durable checkpointing, Agent Mail coordination, and both CLI and REST/WebSocket API surfaces. It is the most complete open source multi-agent tmux orchestrator available, combining orchestration, safety, and observability in one binary. 259 stars, 41 forks, actively developed (v1.13.1 as of 2026-04-16).

## Architecture

### Package Structure

88 internal packages, organized into clear layers. The entry point is minimal (`cmd/ntm/main.go` calls `cli.Execute()`). Everything lives under `internal/` with no public Go API.

**Core infrastructure:**
- `cli/` (5K+ lines): Cobra command tree, the primary human interface
- `tmux/`: Low-level tmux process interaction with circuit breaker protection
- `robot/` (10K+ lines, largest file): Machine-readable JSON API via `--robot-*` flags
- `serve/` (6K lines): chi-based REST/SSE/WebSocket server on port 7337
- `state/`: SQLite-backed durable store with 14 migration files (WAL mode, embedded SQL)
- `events/`: In-process pub/sub event bus with ring buffer history
- `kernel/`: Command registry with CLI/TUI/REST surface parity enforcement
- `config/` (5.7K lines): TOML/YAML config with user-level and project-level overrides

**Agent management:**
- `agent/`: Type system for 8 agent types (Claude Code, Codex, Gemini, Ollama, Cursor, Windsurf, Aider, User), plus terminal output parser for state detection
- `agentmail/`: HTTP client for Agent Mail MCP server (reservations, messaging, identity)
- `coordinator/`: Active session coordinator tracking agent state, context usage, assignments
- `swarm/`: Auto-respawner with account rotation for rate limit recovery
- `supervisor/`: Daemon lifecycle manager for co-processes (cm, bd, am)
- `assign/`: Task assignment engine
- `scheduler/`: Task scheduling

**Safety and governance:**
- `policy/`: YAML-based destructive command protection (block/approve/allow rules)
- `approval/`: Workflow engine with SLB (two-person rule) enforcement
- `safety/`: Higher-level safety integration layer
- `redaction/`: Sensitive content scanning with modes (off/warn/redact/block)
- `privacy/`: Privacy controls
- `audit/`: Durable audit logging

**Orchestration assets:**
- `ensemble/` (45K lines): Multi-agent reasoning ensemble system with 12 mode categories (Formal, Ampliative, Causal, Strategic, etc.), synthesis, budgeting, and velocity tracking
- `pipeline/`: Workflow executor with dependency graphs, progress events, dry-run support
- `workflow/`: Workflow loader with built-in TOML templates (red-green, parallel-explore, review-pipeline, specialist-team)
- `recipe/`: Session presets
- `handoff/`: Agent handoff protocol with YAML file artifacts

**Observability:**
- `checkpoint/`: Incremental session checkpointing with scrollback capture
- `health/`: Agent health checks
- `metrics/`: Metrics collection
- `alerts/`: Alert generation
- `tracker/`: Progress tracking
- `watcher/`: File/process watching

**TUI:**
- `tui/`: Bubbletea TUI with dashboard panels, styles, layout, theme system
- `palette/`: Command palette (fuzzy search)

**Web UI:**
- `web/`: Next.js dashboard with TypeScript, Tailwind, openapi-fetch client
- Pages: sessions, agents, mail, pipelines, safety, beads, analytics, scanner, accounts

### Data Flow

```
Human/Agent CLI --> Cobra commands --> internal packages --> tmux processes
                                   --> robot JSON output
                                   --> REST/SSE/WebSocket API
                                   --> SQLite state store
                                   --> Agent Mail HTTP API
                                   --> Event bus (in-process pub/sub)
```

### Key Architectural Decisions

1. **Single binary, everything internal.** No public Go API. The binary IS the product.
2. **SQLite as the state backbone.** WAL mode, embedded migrations, runtime projections with GC.
3. **Circuit breaker on tmux client.** 5 consecutive failures triggers 10s backoff. Prevents hammering a failing tmux server.
4. **Three automation surfaces:** `--robot-*` CLI flags (local scripting), REST API (service consumers), and raw tmux (agent panes). Each has consistent JSON semantics.
5. **Kernel registry for surface parity.** Commands register with CLI, TUI, and REST bindings simultaneously to prevent surface drift.
6. **Graceful degradation.** Optional integrations (Agent Mail, bv, cass, worktrees) make NTM stronger but are not required. Missing tools produce actionable errors.
7. **Forked bubbletea.** `third_party/bubbletea` is a vendored fork of charmbracelet/bubbletea via `go.mod replace` directive.

## Key Patterns

### Terminal Output Parsing for Agent State

The `agent/parser.go` system is one of the most interesting components. It parses raw terminal output from Claude, Codex, and Gemini CLIs to detect:
- Agent type (via signature patterns)
- State flags (working, idle, rate-limited, error)
- Quantitative metrics (context %, token counts)
- Confidence scores

This is fragile by nature (screen-scraping), but NTM compensates with a hint system and canonical type normalization. File: `internal/agent/parser.go`, `internal/agent/patterns.go`.

### Ensemble Reasoning System

The `ensemble/` package (45K lines) implements a multi-perspective reasoning framework:
- 12 mode categories (Formal, Ampliative, Uncertainty, Vagueness, Change, Causal, Practical, Strategic, Dialectical, Modal, Domain, Meta)
- Tiered modes (core/advanced/experimental)
- Budget management per ensemble run
- Output caching with deduplication
- Synthesis across agent outputs
- Velocity tracking for throughput estimation
- Context window management per agent

This goes well beyond simple "ask three models and pick the best answer." It is a structured reasoning taxonomy applied to multi-agent orchestration.

### Robot Mode as First-Class Surface

The `--robot-*` flag system provides ~30 machine-readable commands with:
- Consistent JSON envelope (`success`, `timestamp`, error codes)
- Exit code semantics (0=success, 1=error, 2=unavailable)
- Agent hints in responses
- Attention feed with cursor-based pagination
- Health/incident tracking

This is designed so that AI agents themselves can operate NTM programmatically.

### Safety as Product, Not Afterthought

- YAML policy files define destructive command patterns
- Three actions: block, approve (needs human), allow
- SLB (Service Level Board) two-person approval workflow
- Durable approval records with audit trail
- Redaction engine for sensitive content in outputs

### Supervisor Pattern for Co-Processes

The `supervisor/` package manages daemons (Agent Mail, beads daemon, cass-memory) with:
- Port allocation
- Health monitoring
- Clean shutdown
- Restart counting
- Owner tracking (which session owns which daemon)

## Dependencies

| Package | Purpose |
|---------|---------|
| spf13/cobra | CLI command framework |
| charmbracelet/bubbletea (forked) | TUI framework |
| charmbracelet/lipgloss | Terminal styling |
| charmbracelet/glamour | Markdown rendering |
| go-chi/chi/v5 | HTTP router for REST API |
| gorilla/websocket | WebSocket for real-time streams |
| modernc.org/sqlite | Pure-Go SQLite (no CGO) |
| fsnotify | File system watching |
| chromedp | Chrome DevTools Protocol (for browser automation) |
| shirou/gopsutil | Process/system utilities |
| BurntSushi/toml | Config parsing |
| gopkg.in/yaml.v3 | YAML policy/pipeline parsing |

Notable: uses `modernc.org/sqlite` (pure Go, no CGO) rather than mattn/go-sqlite3.

## Integration Ecosystem

NTM is designed to compose with Dicklesworthstone's other tools:

- **Agent Mail (am):** MCP-based agent messaging and file reservation system
- **beads/br/bv:** Dependency-aware issue tracking and graph triage
- **CASS:** Cross-agent session search (the project we already reviewed)
- **cass-memory (cm):** Procedural memory extraction
- **dcg:** Another integration (referenced but not fully documented)
- **pt:** Integration mentioned in attention_feed.go

This creates a self-reinforcing tooling ecosystem where each tool makes the others more useful.

## Relevance to Helioy

**High relevance.** NTM and Helioy's nancyr solve overlapping problems with different approaches:

1. **NTM is tmux-native.** It wraps tmux sessions/panes directly. nancyr uses tmux as a substrate but adds its own bus layer.
2. **NTM's robot mode** is conceptually similar to helioy-bus's agent communication, but NTM uses structured CLI flags and REST, while helioy-bus uses MCP.
3. **The ensemble reasoning system** is interesting for Helioy's warroom pattern. NTM's 12-category taxonomy of reasoning modes could inform how warroom agents are briefed.
4. **NTM's attention feed** (cursor-based event pagination with reconstruction confidence) is a well-engineered pattern that could inform how helioy-bus handles event replay.
5. **Safety/policy system** is more mature than anything in Helioy currently. Worth studying if Helioy needs guardrails for autonomous agent actions.
6. **Agent state parsing** from terminal output is a capability helioy-bus could use to detect agent status without requiring agents to self-report.
7. **The checkpoint/timeline system** solves recoverability in a way Helioy could learn from for persistent warroom state.

Key difference: NTM is a monolithic single-binary approach (everything in one Go binary). Helioy is compositional (many small tools connected by bus/MCP). Both are valid architectures for different operational models.

## Scale Metrics

- ~300K lines production Go (581 non-test files)
- ~460K lines test Go (867 test files, 73 E2E tests)
- ~340K lines TypeScript/CSS (web UI)
- 88 internal packages
- 14 database migrations
- 37 doc files including 10K-line OpenAPI spec
- v1.13.1, actively maintained

## Sources Consulted

- README.md: project overview and command reference
- AGENTS.md: development guidelines and project structure
- go.mod: dependency graph
- internal/ package structure (all 88 packages enumerated)
- Key source files: cli/root.go, cli/spawn.go, tmux/client.go, tmux/session.go, robot/robot.go, robot/attention_feed.go, serve/server.go, state/store.go, state/schema.go, state/runtime_store.go, agent/types.go, agent/parser.go, agentmail/client.go, coordinator/coordinator.go, policy/policy.go, approval/engine.go, ensemble/types.go, pipeline/executor.go, supervisor/supervisor.go, redaction/redaction.go, handoff/writer.go, kernel/registry.go, events/bus.go, swarm/auto_respawner.go
- Recent git history (20 commits)
- GitHub releases (v1.13.0, v1.13.1)

## Open Questions

1. **How does the ensemble system actually dispatch to agents?** The 45K-line ensemble package is the most complex subsystem. Deeper analysis would reveal the exact dispatch/synthesis flow.
2. **What is the "beads" system?** Referenced heavily (.beads/ directory, bv integration) but appears to be a separate project (beads_rust / br CLI). Likely Dicklesworthstone's issue tracker.
3. **How mature is the web UI?** The Next.js dashboard exists but unclear how production-ready it is versus the CLI/robot surfaces.
4. **What is the actual adoption?** 259 stars and 41 forks, but the CONTRIBUTING.md explicitly rejects outside contributions. This is a solo project, like all of Dicklesworthstone's work.

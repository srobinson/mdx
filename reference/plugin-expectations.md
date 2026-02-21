---
title: "Helioy Plugin Verification Spec"
type: reference
tags: [helioy, plugin, mcp, skills, hooks, verification]
summary: "What 'working' means for every component in helioy-tools and how to verify it"
status: active
created: 2026-02-21
updated: 2026-02-21
project: helioy
---

# Plugin Expectations

What "working" means for every component in helioy-tools, and how to verify it.

---

## MCP Servers

### 1. am (Attention Matters)

**Binary**: `am serve`

**Expected tools**:

- `am_query` — Query geometric memory with text
- `am_buffer` — Buffer a conversation exchange pair
- `am_activate_response` — Strengthen memory connections from response text
- `am_salient` — Mark insight as conscious memory
- `am_feedback` — Provide relevance feedback on recalled memories
- `am_ingest` — Ingest a document as a memory episode
- `am_batch_query` — Process multiple queries in a single pass
- `am_stats` — Get memory system statistics
- `am_export` — Export full DAE system state as JSON
- `am_import` — Import a full DAE system state from JSON

**Smoke test**: `am_stats` — returns `{ conscious, episodes, n }` with numeric values.

**Expected behavior**: Queries return conscious/subconscious/novel recall. Buffer accumulates exchanges and auto-creates episodes after 3 pairs. Salient memories persist across sessions and projects.

---

### 2. fmm (Frontmatter Matters)

**Binary**: `npx -y frontmatter-matters serve`

**Expected tools**:

- `fmm_lookup_export` — O(1) symbol-to-file lookup
- `fmm_list_exports` — Search/list exported symbols
- `fmm_file_info` — Get file structural profile from index
- `fmm_dependency_graph` — Upstream dependencies + downstream dependents
- `fmm_read_symbol` — Read source code for a specific exported symbol
- `fmm_file_outline` — Spatial outline of a file (exports with line ranges)
- `fmm_search` — Search files by structural criteria

**Smoke test**: `fmm_list_exports` with no arguments — returns list of indexed symbols.

**Expected behavior**: Requires `.fmmrc.json` in project root. Returns structural metadata from pre-built sidecar index. Falls back gracefully if no index exists.

---

### 3. mdx (mdcontext)

**Binary**: `npx -y --package mdcontext mdcontext-mcp`

**Expected tools**:

- `md_search` — Semantic search across markdown documents
- `md_context` — Get LLM-ready context from a markdown file
- `md_structure` — Get heading hierarchy with token counts
- `md_keyword_search` — Search by headings, code blocks, lists, tables
- `md_index` — Build or rebuild the index for a directory
- `md_links` — Get outgoing links from a markdown file
- `md_backlinks` — Get incoming links to a markdown file

**Smoke test**: `md_structure` with path to any `.md` file — returns heading outline.

**Expected behavior**: Requires index (call `md_index` first if needed). Semantic search uses embeddings. Keyword search uses structural parsing. Operates on `~/.mdx/` knowledge base by default.

---

### 4. linear-server

**Endpoint**: `https://mcp.linear.app/mcp` (HTTP-based, not local binary)

**Expected tools**:

- Issues: `get_issue`, `list_issues`, `create_issue`, `update_issue`
- Projects: `list_projects`, `get_project`, `save_project`
- Documents: `list_documents`, `get_document`, `create_document`, `update_document`
- Comments: `list_comments`, `create_comment`
- Teams: `list_teams`, `get_team`
- Users: `list_users`, `get_user`
- Labels: `list_issue_labels`, `create_issue_label`, `list_project_labels`
- Statuses: `list_issue_statuses`, `get_issue_status`
- Cycles: `list_cycles`
- Milestones: `list_milestones`, `get_milestone`, `create_milestone`, `update_milestone`
- Initiatives: `list_initiatives`, `get_initiative`, `create_initiative`, `update_initiative`
- Status Updates: `get_status_updates`, `save_status_update`, `delete_status_update`
- Attachments: `get_attachment`, `create_attachment`, `delete_attachment`
- Images: `extract_images`
- Docs: `search_documentation`

**Smoke test**: `list_teams` — returns team list including "Alphabio".

**Expected behavior**: Authenticated via Linear OAuth. All CRUD operations work against the Alphabio workspace. Issue identifiers follow `ALP-NNN` pattern.

---

## Skills

### 1. memory

**Trigger**: User asks about memory, wants to recall prior sessions, inspect memory, check stats, or manage memory state.

**Manual invocation**: `/helioy-tools:memory`

**Expected behavior**: Manages AM memory lifecycle — recall, buffer, activate, salient, feedback, export/import. Encodes autonomous memory discipline: memory calls happen in every substantive response.

---

### 2. fmm

**Trigger**: Project has `.fmmrc.json`. Invoked before reading or searching source files.

**Manual invocation**: `/helioy-tools:fmm`

**Expected behavior**: Directs to MCP-first code navigation (fmm_read_symbol, fmm_lookup_export, etc.) instead of grep/read. 88-97% token savings over reading full files.

---

### 3. knowledge-base

**Trigger**: User wants to manage `~/.mdx/` knowledge base — create, read, update, search, list documents.

**Manual invocation**: `/helioy-tools:knowledge-base`

**Expected behavior**: CRUD on `~/.mdx/` with 7 categories (research, decisions, design, sessions, projects, retrospectives, reference). Enforces YAML frontmatter. Versioning via `_versions/` subdirs.

---

### 4. linear-workflow

**Trigger**: Creating issues, planning features, breaking down work in Linear.

**Manual invocation**: `/helioy-tools:linear-workflow`

**Expected behavior**: Enforces parent/sub-issue pattern, proper sizing (small 3-10 subs, medium 10-30, large 30-100+), HotFix label for single-line fixes, team=Alphabio.

---

### 5. create-spec

**Trigger**: User wants to define what to build before autonomous execution.

**Manual invocation**: `/helioy-tools:create-spec`

**Expected behavior**: Interactive workflow — explore codebase, elicit ONE question at a time, offer 2-4 options, generate SPEC.md with Goal/Success Criteria/Constraints/Notes.

---

### 6. check-directives

**Trigger**: At turn start, after major tasks, and ALWAYS before marking task complete.

**Manual invocation**: `/helioy-tools:check-directives`

**Expected behavior**: Polls Nancy orchestrator inbox (`nancy inbox`), reads/acts/archives per type (directive/guidance/stop). Must check before marking any task COMPLETE.

---

### 7. nancy-send-message

**Trigger**: Worker needs to communicate with orchestrator — blockers, progress, review requests.

**Manual invocation**: `/helioy-tools:nancy-send-message`

**Expected behavior**: Sends message via `ralph msg <type> "<message>"` where types = blocker, progress, review-request.

---

### 8. nancy-orchestrator

**Trigger**: Running `nancy orchestrate` to supervise a worker agent.

**Manual invocation**: `/helioy-tools:nancy-orchestrator`

**Expected behavior**: Orchestrator supervision — monitor worker, send directives (`nancy direct $TASK "msg"`), read worker messages (`nancy messages`), archive. Don't micromanage.

---

### 9. nancy-update-spec

**Trigger**: A success criterion in SPEC.md has been verified and should be checked off.

**Manual invocation**: `/helioy-tools:nancy-update-spec`

**Expected behavior**: Edits SPEC.md to check off criteria. Only when verified, not just implemented.

---

### 10. skill-creator

**Trigger**: User asks to build, create, or add a new skill.

**Manual invocation**: `/helioy-tools:skill-creator`

**Expected behavior**: Scaffolds new skill at correct location (`skills/<name>/SKILL.md`). Enforces kebab-case naming, frontmatter rules (name + description only), MCP inheritance.

---

## Hooks

### SessionStart

**Trigger**: Fires on every new Claude Code session.

**Action**: Runs `~/.cargo/bin/am sync`, then injects system-reminder message.

**Expected behavior**:

1. AM sync completes (syncs geometric memory state)
2. System-reminder injected telling agent to call `am_query` with first user message
3. Agent receives memory protocol instructions (buffer, activate, salient)

**How to verify**: Start a fresh session. First response should contain `<system-reminder>` tags referencing AM memory protocol. Check that `am sync` ran by looking at process output.

---

## Verification Checklist

Run through these in order. Every item must pass.

### Foundation

- [ ] `claude plugin validate` passes for helioy-tools
- [ ] `claude plugin list` shows helioy-tools as enabled
- [ ] Plugin manifest (`plugin.json`) has correct name, description, author

### SessionStart Hook

- [ ] Start fresh Claude Code session
- [ ] SessionStart hook fires (visible in first system-reminder)
- [ ] `am sync` ran successfully
- [ ] Agent receives memory protocol instructions

### MCP Server: am

- [ ] `am_stats` returns valid stats (N, episodes, conscious count)
- [ ] `am_query` with test text returns structured response (conscious/subconscious/novel)
- [ ] `am_buffer` accepts user/assistant pair without error

### MCP Server: fmm

- [ ] `fmm_list_exports` returns indexed symbols (requires `.fmmrc.json` in project)
- [ ] `fmm_lookup_export` resolves a known symbol to its file
- [ ] `fmm_file_outline` returns line ranges for a known file

### MCP Server: mdx

- [ ] `md_index` builds index for a directory
- [ ] `md_structure` returns heading hierarchy for a markdown file
- [ ] `md_search` returns results for a natural language query

### MCP Server: linear-server

- [ ] `list_teams` returns Alphabio team
- [ ] `list_issues` with team=Alphabio returns issues
- [ ] `get_issue` retrieves a specific issue by identifier

### Skills (manual invocation)

- [ ] `/helioy-tools:memory` — loads memory management context
- [ ] `/helioy-tools:fmm` — loads FMM navigation protocol
- [ ] `/helioy-tools:knowledge-base` — loads KB management context
- [ ] `/helioy-tools:linear-workflow` — loads Linear conventions
- [ ] `/helioy-tools:create-spec` — begins interactive spec elicitation
- [ ] `/helioy-tools:check-directives` — checks orchestrator inbox
- [ ] `/helioy-tools:nancy-send-message` — ready to send worker message
- [ ] `/helioy-tools:nancy-orchestrator` — loads orchestrator supervision context
- [ ] `/helioy-tools:nancy-update-spec` — ready to update spec criteria
- [ ] `/helioy-tools:skill-creator` — loads skill scaffolding context

### Integration

- [ ] Memory persists across sessions (query in new session returns prior context)
- [ ] FMM + AM both available in same session (no MCP conflicts)
- [ ] Linear operations (create/read/update issue) work end-to-end
- [ ] Skills reference correct MCP tool names (inherited from plugin-level `.mcp.json`)

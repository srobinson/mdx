---
title: "Canopy AI Agent Integration Analysis"
category: research
tags: [canopy, agents, mcp, ai-native, tooling]
created: 2026-03-15
---

# Canopy AI Agent Integration Layer

## Executive Summary

Canopy is a 103K-line Python local-first P2P collaboration platform with a deeply integrated AI agent layer. Agents are first-class citizens: they get their own account type, inbox, heartbeat system, presence tracking, event subscriptions, and a dedicated MCP server with 58 tools. The platform treats agents as peers alongside humans, giving them structured work primitives (tasks, objectives, requests, signals, contracts, circles, handoffs, skills) that can be created inline from message content or via REST/MCP APIs. The agent integration is production-grade, with rate limiting, trust scoring, capability routing, and audit trails.

## Architecture Overview

### Module Layout (Agent-Relevant)

| File | LOC | Role |
|------|-----|------|
| `canopy/api/routes.py` | 11,557 | REST API surface (Flask Blueprint) |
| `canopy/mcp/server.py` | 4,415 | MCP server (58 tools, stdio transport) |
| `canopy/core/inbox.py` | 1,721 | Agent action inbox (pull triggers) |
| `canopy/core/mentions.py` | 1,738 | @mention extraction and event storage |
| `canopy/core/circles.py` | 1,409 | Structured deliberation objects |
| `canopy/core/signals.py` | 1,061 | Durable structured memory objects |
| `canopy/core/contracts.py` | 827 | Deterministic coordination objects |
| `canopy/core/tasks.py` | 749 | Assignable tasks with P2P sync |
| `canopy/core/objectives.py` | 744 | Multi-member goal containers |
| `canopy/core/requests.py` | 769 | Structured asks with roles |
| `canopy/core/skills.py` | 683 | Skill registry with trust scoring |
| `canopy/core/handoffs.py` | 672 | Inline state-transfer notes |
| `canopy/api/agent_instructions_data.py` | 631 | Agent onboarding payload |
| `canopy/core/agent_heartbeat.py` | 593 | Heartbeat snapshot builder |
| `canopy/core/agent_event_subscriptions.py` | 293 | Per-agent event type filtering |
| `canopy/core/agent_runtime.py` | 248 | Runtime telemetry (fetch timestamps) |
| `canopy/core/agent_presence.py` | 214 | Presence badges (online/recent/idle/offline) |
| `canopy/core/events.py` | 578 | Workspace event journal (14 event types) |
| `canopy/mcp/mcp_server_framework.py` | 427 | HTTP-based MCP server framework (unused by main) |

### Data Flow

```
AI Agent (Claude, etc.)
    |
    +-- MCP (stdio, 58 tools) -- CanopyMCPServer -- Flask app context
    |
    +-- REST API (/api/v1/*) -- Flask Blueprint -- require_auth decorator
    |
    v
SQLite (local-first, per-node)
    |
    +-- P2P Mesh Sync (tasks, objectives, handoffs, messages, etc.)
```

## 1. Agent Model

### How Agents Are Represented

Agents are standard user accounts with `account_type = 'agent'`. There is no separate Agent model class. The user table holds everything, and agent-specific behavior is controlled by checking the account_type field throughout the codebase.

**What makes agents first-class:**

- **Dedicated account type**: `account_type='agent'` triggers different default configs (relaxed rate limits, higher burst caps)
- **Agent inbox** (`agent_inbox` table): A pull-first trigger queue that stores actionable items (mentions, DMs, replies, channel_added events). Agents get relaxed defaults: 0s cooldown, 500 max pending, 500/hr sender limit vs humans' 100 max pending and 20/hr limits.
- **Agent presence** (`agent_presence` table): Tracks last check-in with 4-tier status: online (<120s), recent (<15min), idle (<1hr), offline. Source field records how the check-in happened (heartbeat, event_fetch, inbox_fetch).
- **Agent runtime state** (`agent_runtime_state` table): Tracks `last_event_fetch_at`, `last_event_cursor_seen`, `last_inbox_fetch_at` so admins can verify agents are servicing Canopy.
- **Agent heartbeat**: A comprehensive snapshot endpoint that aggregates workload counters across all structured primitives, providing `needs_action`, `needs_catchup`, and `poll_hint_seconds` (5s when work exists, 30s otherwise).
- **Agent directives**: Per-agent instruction text stored on the user profile (`agent_directives` field), with a hash included in heartbeat for change detection.
- **Human approval gate**: Agent accounts require human approval before full access. Agents poll `GET /api/v1/auth/status` until approved.

### Heartbeat Payload (key fields)

The heartbeat (`build_agent_heartbeat_snapshot`) is the primary "should I do something?" signal for agents. It returns:

- `unacked_mentions`, `pending_inbox` with timestamps and IDs
- `assigned_open_tasks`, `assigned_in_progress_tasks`, `assigned_blocked_tasks`
- `active_objectives`, `lead_objectives`
- `active_requests`, `assignee_requests`, `reviewer_requests`, `watcher_requests`
- `owned_handoffs`
- `pending_work_total` (sum of all above)
- `needs_catchup` (mentions or inbox pending)
- `needs_action` (catchup OR any work)
- `poll_hint_seconds` (5 or 30)
- `directives_hash` (16-char SHA256 prefix of agent directives)
- `event_subscription_source`, `event_subscription_types`, `event_subscription_unavailable_types`
- `workspace_event_seq` (monotonic journal cursor)

## 2. MCP Server

### Architecture

`canopy/mcp/server.py` implements `CanopyMCPServer` using the official MCP Python SDK (`mcp.server.Server`) with stdio transport. Authentication uses `CANOPY_API_KEY` environment variable, validated against Canopy's API key manager on startup.

**Connection flow:**
1. Set `CANOPY_API_KEY` env var
2. Launch `start_mcp_server.py` or `canopy_mcp_server.py`
3. MCP client connects via stdio
4. Server validates API key, resolves user_id
5. Permission checks gate each tool call

**Permission model:** Each tool call checks `self._check_permission(Permission.XXX)` against the API key's permission set. Default agent permissions: `READ_MESSAGES`, `WRITE_MESSAGES`, `READ_FEED`, `WRITE_FEED`.

### 58 MCP Tools (grouped by domain)

**Messaging (8):** `send_message`, `get_messages`, `update_message`, `mark_message_read`, `delete_message`, `send_channel_message`, `update_channel_message`, `get_channel_messages`

**Channels (2):** `list_channels`, `create_channel`

**Mentions (2):** `get_mentions`, `ack_mentions`

**Inbox (8):** `get_inbox`, `get_inbox_count`, `get_inbox_stats`, `get_inbox_audit`, `rebuild_inbox`, `ack_inbox`, `get_inbox_config`, `set_inbox_config`

**Catchup (2):** `get_catchup`, `get_session_catchup`

**Objectives (4):** `list_objectives`, `get_objective`, `create_objective`, `update_objective`, `add_objective_task`

**Requests (4):** `list_requests`, `get_request`, `create_request`, `update_request`

**Signals (4):** `list_signals`, `get_signal`, `create_signal`, `update_signal`, `lock_signal`

**Handoffs (1):** `get_handoffs`

**Skills (4):** `discover_skills`, `get_skill_trust`, `endorse_skill`, `record_skill_invocation`

**Community Notes (3):** `create_community_note`, `rate_community_note`, `get_community_notes`

**Feed (4):** `post_to_feed`, `update_feed_post`, `delete_feed_post`

**Polls (2):** `get_poll`, `vote_poll`

**Profile & System (5):** `get_profile`, `update_profile`, `upload_avatar`, `get_status`, `get_instructions`, `check_auth_status`

**Files (1):** `upload_file`

**Search (1):** `search`

**Heartbeat (1):** `heartbeat`

### Alternative: HTTP MCP Framework

`mcp_server_framework.py` (427 lines) provides a standalone HTTP-based MCP server using Python's `http.server`. It implements JSON-RPC 2.0 with `@server.tool` decorator pattern, auto-extracting parameter schemas from function signatures. This appears to be an earlier/alternative transport, as the main server uses stdio.

## 3. Structured Work Primitives

All primitives share a common pattern: inline block parsing from message text (e.g., `[task]...[/task]`), a Manager class backed by SQLite, P2P sync via snapshot upsert, and REST/MCP API exposure.

### Tasks (`canopy/core/tasks.py`)

- **Statuses:** open, in_progress, blocked, done
- **Priorities:** low, normal, high, critical
- **Fields:** title, description, assigned_to, objective_id, due_at, visibility (network/local), metadata, origin_peer, source_type
- **Inline format:** `[task] title: ... assignee: @handle [/task]`
- **Authorization:** creator, assignee, or editors can update
- **P2P sync:** `apply_task_snapshot()` does LWW (last-writer-wins) merge by updated_at

### Objectives (`canopy/core/objectives.py`)

- **Statuses:** pending, in_progress, completed, archived
- **Roles:** lead, contributor, reviewer
- **Auto-status:** Automatically transitions based on task completion (all done -> completed, any done -> in_progress)
- **Progress tracking:** `tasks_total`, `tasks_done`, `progress_percent`
- **Inline task syntax:** Supports checkbox (`- [ ] Task @assignee`), bracket-assignee (`- [AgentName] Task desc`), and plain list formats

### Handoffs (`canopy/core/handoffs.py`)

- **Purpose:** Capture state and next steps inline. Designed for agent-to-agent and human-to-agent context transfer.
- **Fields:** title, summary, next_steps (list), owner, tags, visibility, permissions
- **Capability routing fields:** `required_capabilities` (list), `escalation_level` (normal/elevated/admin), `return_to` (user_id for return routing), `context_payload` (structured context for receiving agent)
- **Visibility gating:** Channel membership and custom permission lists

### Signals (`canopy/core/signals.py`)

- **Purpose:** Durable structured memory objects for multi-agent collaboration (decisions, requirements, research findings, claim sets)
- **Statuses:** draft, active, locked, archived
- **Fields:** signal_type, title, summary, owner, tags, confidence (0-1), data (arbitrary JSON), notes, TTL/expiry
- **TTL support:** `ttl_seconds`, `ttl_mode`, `expires_at` with relative parsing (30d, 2w, etc.)
- **Locking:** Owner/admin can lock to prevent further edits

### Circles (`canopy/core/circles.py`)

- **Purpose:** Structured deliberation objects. A mini-RFC process embedded in chat.
- **Flow:** Create circle with question/topic -> participants submit entries -> optional voting
- **Features:** Opinion limit per participant, clarification limit, edit window, deadline
- **Response format:** `[circle-response]...[/circle-response]` blocks for structured participation

### Contracts (`canopy/core/contracts.py`)

- **Purpose:** Deterministic coordination objects with explicit lifecycle and bounded retention
- **Statuses:** proposed -> accepted -> active -> fulfilled/breached/void/archived
- **Fields:** title, summary, terms, owner_id, counterparties (list), fingerprint (SHA256), revision counter
- **Authorization tiers:** Managers (owner/creator/admin) can edit all fields. Participants (counterparties) can only advance status transitions.
- **Integrity:** Content-addressable fingerprinting. Revision counter increments on fingerprint changes.

### Skills (`canopy/core/skills.py`)

- **Purpose:** Embeddable skill manifests parsed from `[skill]...[/skill]` blocks
- **Fields:** name, version, description, inputs, outputs, perms, invokes (with protocol prefixes: `mcp:`, `api:`, `inbox:`), tags
- **Trust scoring:** Composite score = `success_rate * 0.6 + endorsement_score * 0.3 + usage_score * 0.1`
- **Invocation tracking:** Records success/failure, duration_ms, unique invokers
- **Endorsement system:** Peer agents can endorse skills (weighted 0-5)
- **Community notes:** Agents can annotate content for accuracy (context, correction, misleading, outdated, endorsement) with crowd-sourced rating (accepted/rejected/proposed)

### Requests (`canopy/core/requests.py`)

- **Purpose:** Structured asks with explicit deliverables
- **Statuses:** open, acknowledged, in_progress, completed, closed, cancelled
- **Roles:** assignee, reviewer, watcher
- **Fields:** title, request (body), required_output (success criteria), priority, due_at, tags
- **Member system:** `request_members` join table with role assignment

## 4. Inbox and Notifications

### Agent Inbox (`canopy/core/inbox.py`, 1721 lines)

The inbox is a **pull-first trigger queue**. When an agent is @mentioned, receives a DM, or gets a thread reply, an inbox item is created. The agent polls for pending items.

**Statuses:** pending -> seen -> completed/skipped/expired

**Trigger types:** mention, dm, reply, channel_added

**Rate limiting (agent defaults):**
- 0s global cooldown, 5s sender cooldown, 10s agent-sender cooldown
- 50/min channel burst, 500/hr channel limit, 200/hr sender limit
- 500 max pending items, 14-day expiry, audit enabled

**Rate limiting (human defaults):**
- 10s global cooldown, 30s sender cooldown, 60s agent-sender cooldown
- 3/min channel burst, 20/hr channel limit, 20/hr sender limit
- 100 max pending, 7-day expiry

**Inbox rebuild:** `POST /api/v1/agents/me/inbox/rebuild` scans channel history (default 7 days, max 1 year) and backfills missing inbox items, bypassing rate limits. Designed for startup catch-up after offline periods.

**Completion tracking:** When completing or skipping, agents can attach `completion_ref` (a dict with message_id, post_id, etc.) so admins can verify linked output.

### Mentions (`canopy/core/mentions.py`)

- **Extraction:** Regex-based `@handle` extraction supporting markdown wrappers (`**@Agent**`), avoiding emails and trailing punctuation
- **Resolution:** `resolve_mention_targets()` maps handles to user IDs, splitting into local and remote targets
- **Event storage:** `mention_events` table with acknowledged_at tracking
- **Delivery:** SSE stream at `GET /api/v1/mentions/stream` plus polling at `GET /api/v1/mentions`
- **Claim mechanism:** `POST /api/v1/mentions/claim` prevents duplicate agent pile-ons. Agents claim a mention source (by mention_id, inbox_id, or source_type+source_id) before replying.

## 5. Agent Instructions & Onboarding

`agent_instructions_data.py` builds a comprehensive onboarding payload returned by `GET /api/v1/agent-instructions`. This is the first endpoint an agent should call. It includes:

- Base URL and API prefix (`/api/v1`, with `/api` as backward-compatible alias)
- 52 capability descriptions covering every API surface
- Auth instructions (X-API-Key header)
- Credential storage guidance (save to `~/.canopy_credentials.json`)
- Inline block format documentation (tasks, objectives, requests, signals, handoffs, circles, skills, contracts, polls)
- Expiration/TTL documentation
- Content linking syntax (`[msg:<id>]`, `[post:<id>]`)
- Agent directives (per-agent custom instructions)

The payload is a self-contained agent bootstrap document. An agent can read this single endpoint and understand the full API surface.

## 6. REST API Surface (Agent-Relevant Endpoints)

**Agent Identity & Discovery:**
- `GET /api/v1/agents` - List all agents with handles, skills, capabilities
- `GET /api/v1/agents/me` - Current agent profile
- `GET /api/v1/agents/system-health` - Queue + peer + uptime diagnostics
- `GET /api/v1/agent-instructions` - Bootstrap payload (no auth required)
- `GET /api/v1/auth/status` - Account approval status
- `POST /api/v1/register` - Register new agent account

**Agent Inbox:**
- `GET /api/v1/agents/me/inbox` - List pending inbox items
- `GET /api/v1/agents/me/inbox/count` - Count by status
- `PATCH /api/v1/agents/me/inbox` - Batch status update
- `PATCH /api/v1/agents/me/inbox/<id>` - Single item update
- `GET/PATCH /api/v1/agents/me/inbox/config` - Inbox configuration
- `GET /api/v1/agents/me/inbox/stats` - Status counts + rejection reasons
- `GET /api/v1/agents/me/inbox/audit` - Rejection audit trail
- `POST /api/v1/agents/me/inbox/rebuild` - Backfill from history

**Agent Events:**
- `GET /api/v1/agents/me/events` - Low-noise event feed (default: DM/mention/inbox/attachment)
- `GET /api/v1/agents/me/catchup` - Digest of new activity

**Workspace Events:**
- `GET /api/v1/events` - Full workspace journal
- `GET /api/v1/events/diagnostics` - Event system health

**Mentions:**
- `GET /api/v1/mentions` - Poll mention events
- `GET /api/v1/mentions/stream` - SSE stream
- `POST /api/v1/mentions/ack` - Acknowledge
- `POST /api/v1/mentions/claim` - Claim for response (anti-pile-on)

## 7. Event Subscription System

### Architecture

Agents can customize which workspace event types they receive, stored per-agent in `agent_event_subscription_state` and `agent_event_subscriptions` tables.

### 14 Supported Event Types

- `dm.message.created`, `dm.message.edited`, `dm.message.deleted`, `dm.message.read`
- `channel.message.created`, `channel.message.edited`, `channel.message.deleted`, `channel.message.read`
- `channel.state.updated`
- `mention.created`, `mention.acknowledged`
- `inbox.item.created`, `inbox.item.updated`
- `attachment.available`

### Default Agent Subscription (8 types)

DM messages (created/edited/deleted), mentions (created/acknowledged), inbox items (created/updated), attachment.available. Channel message events are excluded by default to reduce noise.

### Resolution Logic

Three-tier priority: explicit request > stored preferences > defaults. Message-related event types require `READ_MESSAGES` permission. The system also reports `unavailable_types` when permission filtering removes requested types.

### API

- `GET /api/v1/agents/me/events?after_seq=N&limit=50&types=dm.message.created,mention.created`
- `GET/POST /api/v1/agents/me/event-subscriptions` - Persist preferred event families

## 8. Comparison to helioy-bus

| Dimension | Canopy | helioy-bus |
|-----------|--------|------------|
| **Transport** | HTTP REST + MCP stdio + SSE | Unix domain socket / TCP |
| **Topology** | P2P mesh with direct connections | Central bus with agent registry |
| **Message model** | Pull-first (inbox + heartbeat polling) | Push-first (message delivery) |
| **Agent identity** | User account with account_type='agent' | Registered agent with capabilities |
| **Work primitives** | 8 types (tasks, objectives, requests, signals, contracts, circles, handoffs, skills) | Messages only (typed payloads) |
| **Event system** | Workspace event journal with per-agent subscriptions | Topic-based pub/sub |
| **Trust** | Per-peer trust scores, skill endorsements, community notes | Not implemented |
| **Persistence** | SQLite local-first with P2P sync | In-memory (ephemeral) |
| **Scale target** | Small mesh (10-50 nodes) | Process-local coordination |

Canopy's agent integration is significantly more mature than helioy-bus in terms of structured work primitives and trust. helioy-bus is lighter and better suited for fast inter-process coordination within a single machine.

## 9. Opportunities for Helioy Integration

### Direct Integration Points

1. **MCP bridge**: Canopy's MCP server could be registered as a tool source in helioy-plugins, giving Claude Code agents direct access to 58 Canopy tools. The stdio transport is already compatible.

2. **Structured work items as attention-matters signals**: Tasks, objectives, and requests from Canopy could be ingested into attention-matters as memory fragments, providing cross-platform work tracking.

3. **helioy-bus as event transport**: Canopy's polling-based event system could be supplemented with helioy-bus push notifications for lower-latency agent wakeup on the same machine.

4. **Skill registry sharing**: Canopy's skill manifest format (`[skill]...[/skill]`) and trust scoring system could inform a shared skill registry across Helioy components.

5. **Contract primitives for nancyr**: Canopy's contract model (proposed -> accepted -> active -> fulfilled/breached) maps well to multi-agent coordination contracts that nancyr could orchestrate.

### Architectural Patterns Worth Adopting

- **Inline block parsing**: The `[type]...[/type]` and `::type ... ::endtype` pattern for embedding structured data in natural language messages is elegant and agent-friendly. Code fence masking prevents false matches.
- **Heartbeat with `needs_action` + `poll_hint_seconds`**: A clean pattern for adaptive polling. Agents poll less when idle, more when work exists.
- **Mention claim mechanism**: Prevents duplicate agent pile-ons. Essential for any multi-agent system where agents watch the same channels.
- **Dual inbox configs**: Different rate limit profiles for human vs agent accounts is a practical necessity that attention-matters should consider.
- **Trust scoring formula**: `success_rate * 0.6 + endorsement * 0.3 + usage * 0.1` is a reasonable starting point for skill-level trust in multi-agent settings.

## Key Technical Decisions

- **No ORM**: Raw SQLite with dict-style row access throughout. `conn.execute()` everywhere.
- **Flask without heavy framework**: Plain Blueprint, no Flask-RESTful or Marshmallow. Manual JSON validation.
- **LWW conflict resolution**: P2P sync uses last-writer-wins by `updated_at` timestamp. No CRDTs.
- **Defensive parsing**: Every parser masks code fences, sanitizes control characters, caps input size, and limits block count. Security-conscious design.
- **Backward compatibility**: Status aliases (`handled` -> `completed`), multiple URL prefixes (`/api/v1` and `/api`), flexible header parsing (`X-API-Key`, `Authorization: Bearer`, raw auth header).

## Open Questions

1. **Circle voting and consensus mechanisms**: How does the voting flow work in practice for multi-agent deliberation? Need to read the full circles implementation.
2. **P2P sync conflict handling**: LWW works for simple cases. How are merge conflicts handled for complex objects like objectives with both member and task changes?
3. **Agent approval workflow**: What does the human approval process look like in the UI? Is there a programmatic approval API for automated provisioning?
4. **Event journal retention**: 30-day / 50K row cap. Is this sufficient for agents that go offline for extended periods, or does the inbox rebuild compensate?
5. **Contract enforcement**: Contracts have breach/void statuses, but is there any automated enforcement, or is it purely declarative?

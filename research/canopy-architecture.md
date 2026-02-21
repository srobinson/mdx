---
title: "Canopy Architecture Analysis"
type: research
tags: [canopy, architecture, python, p2p, flask, sqlite, local-first]
summary: "Deep architectural analysis of Canopy, a 103K-line Python local-first P2P collaboration platform built on Flask + SQLite + WebSockets"
status: active
source: codebase-analyst
confidence: high
created: 2026-03-15
updated: 2026-03-15
---

## Executive Summary

Canopy is a local-first, peer-to-peer collaboration platform (v0.4.83) designed for both humans and AI agents. It runs as a single-process Flask application backed by SQLite, with a separate asyncio thread handling WebSocket-based P2P mesh networking. The architecture follows a **service-manager pattern** where ~20 manager classes are instantiated inside a single monolithic `create_app()` factory and wired together via Flask's `app.config` dictionary. At 103K lines of Python, the codebase is feature-rich but architecturally centralized: the `core/app.py` file alone is 6,669 lines and serves as the system's nervous system, containing all callback wiring between the network layer and domain logic.

## Project Metadata

| Field | Value |
|---|---|
| Language | Python 3.10+ |
| Framework | Flask 3.0+, waitress (production WSGI) |
| Database | SQLite (WAL mode) |
| P2P Transport | WebSockets (websockets library), asyncio |
| Crypto | cryptography (ChaCha20-Poly1305, Ed25519, X25519), bcrypt |
| Discovery | Zeroconf (mDNS/DNS-SD) |
| Serialization | msgpack (P2P wire), JSON (API/DB) |
| Build | setuptools, pyproject.toml |
| Version | 0.4.83, protocol version 1 |
| Total LOC | ~103K (80K source, 23K tests) |
| Test count | 79 test files |
| fmm indexed | No (manual analysis) |

## Module Map

### Package Topology

```
canopy/                     # 80,198 LOC source
  core/          36,260 LOC  # Domain logic, app factory, all managers
  api/           11,557 LOC  # REST API (1 file: routes.py)
  ui/            15,777 LOC  # Web UI (1 file: routes.py + templates)
  network/        8,256 LOC  # P2P mesh (manager, connection, discovery, routing, identity, invite)
  security/       2,200 LOC  # Encryption, trust, API keys, file access, CSRF
  mcp/            4,868 LOC  # MCP server for AI agent integration
  main.py           154 LOC  # Entry point / WSGI bootstrap
```

### LOC Distribution (top 15 source files)

| File | LOC | Role |
|---|---|---|
| `ui/routes.py` | 15,777 | Web UI routes (HTML rendering, AJAX endpoints) |
| `api/routes.py` | 11,557 | REST API (agent + human endpoints) |
| `core/app.py` | 6,669 | App factory + all P2P callback wiring |
| `core/channels.py` | 5,255 | Channel/thread system (Slack-style) |
| `mcp/server.py` | 4,415 | MCP tool definitions for AI agents |
| `network/manager.py` | 4,060 | P2P network coordinator |
| `network/routing.py` | 2,125 | Message routing + channel encryption |
| `core/mentions.py` | 1,738 | @mention extraction and routing |
| `core/inbox.py` | 1,721 | Agent action inbox (mention-triggered) |
| `core/database.py` | 1,637 | Schema + migrations + connection pool |
| `core/identity_portability.py` | 1,565 | Distributed auth (Phase 1) |
| `core/circles.py` | 1,409 | Decision circles (governance) |
| `core/files.py` | 1,242 | File storage manager |
| `core/search.py` | 1,201 | Full-text search |
| `core/messaging.py` | 1,153 | DM system + E2E encryption |
| `core/network/connection.py` | 1,191 | WebSocket connection management |

### Dependency Flow Between Packages

```
                    main.py
                       |
                    core/app.py  (orchestrator)
                   /    |    \
                  /     |     \
           api/     ui/     network/
           routes   routes  manager
             \       |       /
              \      |      /
               core/* managers
                     |
                 database.py
                     |
                  security/*
```

**Interconnection analysis:**

- **core** is the gravitational center. Every other package imports from it.
- **api** and **ui** both import heavily from core (messaging, channels, mentions, events, profiles, etc.) and from security. They are peer consumers with significant import overlap.
- **network** imports from core.messaging and core.large_attachments but is otherwise self-contained. Its integration happens through callbacks wired in app.py.
- **security** has minimal inbound coupling. It provides services consumed by all other packages.
- **mcp** depends on core and security but is architecturally isolated (separate process entry point).

**Cleanest boundary:** `security/` - small, focused modules with clear responsibilities and minimal coupling.
**Leakiest boundary:** `core/app.py` - it reaches into every package and contains ~3000 lines of inline callback closures that bridge network events to domain logic.

## Core Abstractions

### Domain Objects

| Object | Module | Storage | Description |
|---|---|---|---|
| `Channel` | core/channels.py | `channels`, `channel_members`, `channel_messages` | Slack-style channel with types: public, private, DM, group_DM, general |
| `Message` (DM) | core/messaging.py | `messages` | Direct message with E2E encryption support |
| `Message` (Channel) | core/channels.py | `channel_messages` | Channel message with threading, reactions, attachments |
| `User` | database schema | `users`, `user_keys` | Identity with Ed25519/X25519 keypairs, account_type (human/agent) |
| `PeerIdentity` | network/identity.py | `peer_identity.json` | Device-level cryptographic identity (Ed25519 + X25519) |
| `Signal` | core/signals.py | `signals` table | Structured memory objects (decisions, requirements) with TTL |
| `Contract` | core/contracts.py | DB table | Agent agreements |
| `Handoff` | core/handoffs.py | DB table | Agent task transfers |
| `Circle` | core/circles.py | DB table | Governance/decision structures |
| `Objective` | core/objectives.py | DB table | Goal tracking linked to tasks |
| `Task` | core/tasks.py | DB table | Work items |
| `StreamRecord` | core/streams.py | `streams` table | Live media/telemetry streams (HLS, events-json) |
| `FeedPost` | core/feed.py | `feed_posts` | Social feed content with TTL retention |
| `InboxItem` | core/inbox.py | `agent_inbox` | Agent action queue items (mention-triggered) |
| `WorkspaceEvent` | core/events.py | `workspace_events` | Durable event journal for UI/agent consumers |

**Assessment:** The domain model is reasonably well-defined with dataclasses for core entities. There is a clear separation between the direct messaging system (DM) and the channel messaging system, each with its own Message dataclass and table. The agent-oriented abstractions (signals, contracts, handoffs, circles, objectives) form a structured collaboration layer on top of the messaging substrate. The domain objects are generally modeled as **anemic dataclasses** with `to_dict()` serialization, while business logic lives in the corresponding Manager classes.

### Manager Classes (Service Layer)

The system uses approximately 20 manager classes, each wrapping a specific domain concern:

- `DatabaseManager` - SQLite connection pooling, schema, migrations
- `MessageManager` - DM CRUD, E2E encryption, workspace event emission
- `ChannelManager` - Channel lifecycle, membership, channel messages, E2E channel keys
- `FileManager` - File upload/download, checksum, large attachment transfers
- `FeedManager` - Social feed CRUD with retention policies
- `InteractionManager` - Reactions, interactions on feed/channel posts
- `ProfileManager` - User profiles, avatars, agent directives
- `TaskManager` - Task lifecycle
- `SearchManager` - Full-text search across messages/channels/feed
- `MentionManager` - @mention tracking, notifications
- `InboxManager` - Agent action queue
- `SignalManager` - Signal CRUD with TTL lifecycle
- `ContractManager` - Agent contract management
- `HandoffManager` - Agent task handoff lifecycle
- `CircleManager` - Decision circle governance
- `ObjectiveManager` - Goal/objective tracking
- `StreamManager` - Live stream lifecycle
- `WorkspaceEventManager` - Durable event journal
- `IdentityPortabilityManager` - Distributed auth phase 1
- `ApiKeyManager` - API key generation, validation, permissions
- `TrustManager` - Peer trust scoring
- `P2PNetworkManager` - P2P mesh coordinator

## Data Layer

### Database Architecture

**Engine:** SQLite in WAL mode with a background checkpoint thread (5-minute interval).

**Connection management:** Thread-local connection pooling via `threading.local()`. Connections are managed through a `get_connection()` context manager with configurable `busy_timeout_ms` (default 5000ms, startup uses 30s).

**Schema approach:** Inline DDL in `_initialize_database()` using `CREATE TABLE IF NOT EXISTS`. The initial schema defines ~20 tables in a single `executescript()` call. No external migration files.

**Migration strategy:** Code-based migrations in `_run_migrations()` using `PRAGMA table_info()` to detect missing columns, then `ALTER TABLE ADD COLUMN`. A `schema_migrations` table tracks version numbers, but the actual migration logic uses column-presence detection rather than version tracking. This is pragmatic but makes it difficult to reason about what migration state a given database is in.

### Key Tables

| Table | Purpose |
|---|---|
| `users` | Identity (id, username, public_key, password_hash, account_type, agent_directives) |
| `user_keys` | Per-user Ed25519 + X25519 keypairs |
| `messages` | Direct messages (sender, recipient, encrypted content) |
| `channels` | Channel metadata |
| `channel_members` | Channel membership with roles |
| `channel_messages` | Channel message content with threading |
| `channel_keys` | Per-channel encryption keys |
| `feed_posts` | Social feed with TTL retention (expires_at) |
| `trust_scores` | Per-peer trust scores |
| `api_keys` | API key hashes + permission JSON blobs |
| `agent_inbox` | Agent action queue (mention-triggered, pull-first) |
| `workspace_events` | Durable event journal (autoincrement seq, 50K row cap, 30-day retention) |
| `signals` | Structured memory objects with TTL |
| `peers` | Discovered network peers |
| `delete_signals` | Data removal compliance tracking |
| `mesh_principals` | Distributed identity (Phase 1) |
| `mesh_bootstrap_grants` | Cross-peer auth grants |
| `content_contexts` | External content extraction (YouTube transcripts, etc.) |
| `agent_presence` | Agent check-in timestamps |

**Resilience:** WAL mode with periodic checkpoints, integrity checks on startup, retry logic for locked databases during initialization (3 attempts with 2s backoff). Database path is per-device based on a stable device_id to avoid collisions when the source tree is shared via Dropbox/cloud sync.

## Application Lifecycle

### Boot Sequence

```
main() → Config.from_env() → create_app(config) → waitress.serve(app)
```

1. **Config loading** (`Config.from_env()`): Dataclass-based configuration with env var overrides. Device-specific paths computed from a stable `device_id` per machine. Legacy data migration from `./data/canopy.db` to device-specific directory.

2. **App factory** (`create_app()`): Single monolithic function (~6400 lines) that:
   - Creates Flask app
   - Instantiates all ~20 manager classes sequentially
   - Stores each in `app.config['MANAGER_NAME']`
   - Wires P2P callbacks (~3000 lines of inline closures)
   - Registers blueprints (api, ui)
   - Installs rate limiting, error handlers, template filters
   - Starts P2P network on a background thread
   - Starts a maintenance loop (background thread for TTL enforcement, expiry cleanup)

3. **P2P startup** (`P2PNetworkManager.start()`): Spawns a daemon thread running an asyncio event loop. Within that loop:
   - Initializes `ConnectionManager` (WebSocket server on mesh_port)
   - Initializes `PeerDiscovery` (Zeroconf mDNS)
   - Initializes `MessageRouter`
   - Starts listening for incoming peer connections

4. **WSGI serving**: Waitress (8 threads) for production, Flask dev server for debug mode.

### Shutdown

Signal handlers (SIGTERM/SIGINT) call a shutdown function stored in `app.config['SHUTDOWN_FUNCTION']`. An `atexit` handler provides cleanup on normal exit. The P2P thread is daemonic, so it dies with the process.

## State Management

### The `app.config` Service Locator

All shared state flows through Flask's `app.config` dictionary. Every manager instance is stored there:

```python
app.config['DB_MANAGER'] = db_manager
app.config['MESSAGE_MANAGER'] = message_manager
app.config['CHANNEL_MANAGER'] = channel_manager
app.config['P2P_MANAGER'] = p2p_manager
# ... ~16 more
```

Route handlers retrieve them via a utility function:

```python
# canopy/core/utils.py
def get_app_components(app: Flask) -> Tuple[...]:
    return (
        app.config.get('DB_MANAGER'),
        app.config.get('API_KEY_MANAGER'),
        app.config.get('TRUST_MANAGER'),
        # ... 8 more
    )
```

This returns an 11-element tuple. Routes destructure it at the top of every handler. The pattern is verbose but consistent.

**Cross-cutting state injection:** Some managers have their `workspace_events` attribute set post-construction:

```python
message_manager.workspace_events = workspace_event_manager
channel_manager.workspace_events = workspace_event_manager
mention_manager.workspace_events = workspace_event_manager
inbox_manager.workspace_events = workspace_event_manager
```

### Thread Safety

- SQLite connections use thread-local storage (`threading.local()`)
- P2P state uses explicit locks (`threading.Lock()` for activity events, endpoint health, large attachment state)
- The P2P network runs on its own asyncio event loop in a daemon thread
- No global mutable state outside `app.config` (which is set once at startup)

## Design Patterns

### 1. Callback Injection (P2P Integration)

The P2P manager exposes ~30 optional callback attributes (`on_channel_message`, `on_peer_connected`, `on_direct_message`, etc.). The app factory assigns closures to these callbacks, creating the bridge between the network layer and domain logic. This avoids tight coupling between network and core but produces a massive wiring section in app.py.

```python
p2p_manager.on_channel_message = _on_p2p_channel_message  # line 2421
p2p_manager.on_channel_announce = _on_channel_announce      # line 2570
p2p_manager.on_member_sync = _on_member_sync                # line 2781
# ... ~25 more callback assignments
```

### 2. Workspace Event Journal (Event Sourcing Lite)

`WorkspaceEventManager` maintains a durable, append-only event log in SQLite. Events are typed (14 types like `dm.message.created`, `channel.message.edited`, `mention.created`), scoped to visibility (`user`, `channel`, `dm`), and support deduplication via `dedupe_key`. Consumers poll by `seq` cursor. This provides an event-driven substrate for both UI (SSE streaming) and agent integration without requiring a full event bus.

### 3. Manager Pattern (Service Objects)

Each domain concern has a manager class that encapsulates its SQLite queries, business rules, and event emission. Managers take `DatabaseManager` as their primary dependency and occasionally reference other managers. This is a procedural service-layer pattern, with managers serving as stateless(ish) facades over SQLite.

### 4. Blueprint Separation

API and UI are cleanly separated into Flask Blueprints. The API blueprint is registered twice (`/api/v1` and `/api` for legacy compatibility). Both blueprints consume the same core managers via `get_app_components()`.

### 5. Token-Bucket Rate Limiting

Custom in-process rate limiting with separate buckets for API, upload, registration, login, UI AJAX, and P2P endpoints. Global singleton `_RateLimiter` instances with `before_request` hooks.

### 6. Device-Isolated Storage

Each physical machine gets its own data directory under `./data/devices/<device_id>/` containing the database, keys, and files. This handles the edge case where the source tree is shared via cloud sync.

### 7. Capability Negotiation

Peers advertise capabilities during WebSocket handshake (e.g., `dm_e2e_v1`, `large_attachment_v1`). The system uses capability checks before attempting E2E encryption or large attachment transfers. Version negotiation supports mixed-version deployments.

## Architectural Strengths

1. **Self-contained deployment.** Single process, SQLite, no external services. Genuinely local-first with zero infrastructure dependencies.

2. **Comprehensive agent integration.** The agent inbox, mention system, workspace events, MCP server, and structured tools (signals, contracts, handoffs, circles) create a rich substrate for AI agent participation.

3. **Thoughtful security layering.** Per-user keypairs, per-channel encryption keys, E2E DM encryption, trust scores, API key permissions, CSRF protection, file access controls, and rate limiting. Defense in depth.

4. **Graceful degradation.** Mixed-version peer support, capability negotiation, and feature flags (e2e_private_channels, identity_portability) allow incremental rollout.

5. **Device isolation.** Per-device data directories prevent corruption from cloud sync.

6. **WAL mode SQLite with proper resilience.** Background checkpointing, retry logic for locked databases, integrity checks on startup.

## Architectural Concerns

1. **`create_app()` is 6,669 lines.** This single function contains all manager instantiation, all P2P callback wiring (~3000 lines of inline closures), and application setup. It is the most critical file in the codebase and also the hardest to reason about. Extracting the callback wiring into a dedicated module (e.g., `core/p2p_bridge.py`) would improve maintainability without changing behavior.

2. **`app.config` as service locator.** Storing 20+ manager instances in Flask's config dictionary is convenient but provides no compile-time guarantees, no lifecycle management, and makes testing harder than a proper DI container would. The `get_app_components()` utility returns an 11-tuple that must be destructured correctly at every call site.

3. **Route file sizes.** `ui/routes.py` (15,777 lines) and `api/routes.py` (11,557 lines) are monolithic. These could be split into sub-blueprints by domain (channels, messages, feed, settings, admin, etc.).

4. **Schema-in-code migrations.** Column-presence detection via `PRAGMA table_info()` is pragmatic but fragile. There is no way to know what schema version a database is at without running the migration function. Adding a proper migration framework (or using the `schema_migrations` table that already exists) would improve auditability.

5. **Duplicated datetime parsing.** The `_coerce_app_datetime()`, `_to_iso()`, `_parse_dt()`, `_parse_ts()`, and `_now_utc()` utilities are reimplemented across at least 5 modules. A single `canopy.core.datetime_utils` module would eliminate this.

6. **No dependency injection.** Managers are constructed and wired manually in `create_app()`. Cross-references between managers (e.g., `message_manager.workspace_events = workspace_event_manager`) happen via post-construction attribute assignment, which is ordering-sensitive and invisible to static analysis.

7. **P2P/domain coupling through closures.** The ~25 callback closures in `create_app()` close over local variables from the factory scope. This means the domain logic for handling P2P events is defined inside the app factory rather than in the domain modules where it belongs. Testability suffers because these closures cannot be invoked independently of the full app context.

## Dependencies

| Package | Purpose |
|---|---|
| Flask 3.0+ | Web framework |
| waitress 3.0+ | Production WSGI server |
| cryptography 41+ | ChaCha20-Poly1305, Ed25519, X25519, TLS cert generation |
| bcrypt 4.1+ | Password hashing |
| websockets 12+ | P2P WebSocket transport |
| zeroconf 0.132+ | mDNS/DNS-SD peer discovery |
| msgpack 1.0+ | Binary serialization for P2P wire protocol |
| base58 2.1+ | Peer ID encoding |
| Pillow 10.4+ | Image processing (avatars, previews) |
| openpyxl 3.1+ | Spreadsheet preview support |
| python-dateutil 2.8+ | Date parsing |

Optional: `mcp` (AI agent MCP server), `pystray` (system tray), `pyinstaller` (tray build).

## Open Questions

1. **Test coverage.** 79 test files exist but coverage metrics are unknown. The test names suggest strong coverage of edge cases and regressions (e.g., `test_fk_race_and_avatar_recovery`, `test_mention_claim_race_compat`).

2. **Channel key rotation protocol.** The channel key distribution system has retry logic and delivery state tracking, but the full key rotation protocol (when rotation triggers, how old keys are deprecated) was not fully traced.

3. **Catchup/sync protocol details.** The P2P manager has extensive catchup request/response callbacks and Merkle-assisted digest sync (disabled by default), but the sync protocol details were not examined.

4. **MCP server architecture.** The MCP server (`mcp/server.py`, 4,415 lines) runs as a separate process. Its tool surface and how it integrates with the main Canopy instance was not analyzed.

5. **UI frontend.** Template-rendered HTML with JavaScript (static files under `ui/static/`). The frontend architecture was not examined.

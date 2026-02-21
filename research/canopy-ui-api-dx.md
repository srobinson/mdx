---
title: "Canopy UI, API & Developer Experience Analysis"
category: research
tags: [canopy, api, ui, flask, developer-experience, p2p, streaming, search]
created: 2026-03-15
updated: 2026-03-15
summary: "Deep analysis of Canopy's web UI, REST API surface, streaming, file handling, search, test coverage, developer experience, and Windows tray app."
status: active
source: codebase-analyst
confidence: high
---

## Executive Summary

Canopy is a local-first P2P collaboration platform (v0.4.83) built as a monolithic Flask application with 103K lines of Python across 149 files. It provides a server-side rendered web UI (Bootstrap 5, dark theme, PWA-capable), a comprehensive REST API (167 endpoints under `/api/v1/`), HLS/telemetry streaming, SQLite FTS5 search, encrypted P2P mesh networking, and an optional Windows system tray app. The project targets both human users via the web UI and AI agents via the API, with explicit agent onboarding, inbox, heartbeat, and event subscription systems.

## Project Metadata

| Attribute | Value |
|-----------|-------|
| Version | 0.4.83 |
| Language | Python 3.10+ |
| Framework | Flask 3.0+, Werkzeug 3.0+ |
| Server | Waitress (production WSGI) |
| Database | SQLite with FTS5 |
| Crypto | `cryptography` 41+, `bcrypt` 4.1+ |
| P2P | Custom WebSocket mesh (`websockets` 12+, `zeroconf`, `msgpack`) |
| Frontend | Server-side Jinja2 templates, Bootstrap 5.3, vanilla JS (6.5K LOC) |
| Build | setuptools, pip, optional Docker |
| Total source LOC | ~103K Python, ~38K HTML templates, ~6.5K JS |
| Test LOC | ~18.5K across 77 test files |

### Key Dependencies

- **Flask/Werkzeug**: Web framework and WSGI
- **cryptography/bcrypt**: E2E encryption, password hashing
- **zeroconf**: mDNS LAN peer discovery
- **websockets/msgpack**: P2P mesh transport
- **Pillow**: Image thumbnails
- **openpyxl**: Excel spreadsheet preview
- **base58**: Peer identity encoding
- **KaTeX** (vendored): LaTeX math rendering in content

---

## 1. Web UI Architecture

### Rendering Model

Canopy uses **server-side rendered Jinja2 templates** with AJAX endpoints for dynamic updates. There is no SPA framework. The pattern is traditional Flask: full page loads for navigation, then `/ajax/*` endpoints (jQuery-style fetch calls from vanilla JS) for in-page mutations.

### Template Hierarchy

`base.html` (5,647 lines) defines the full application shell: CSS custom properties for a dark theme, responsive sidebar navigation, PWA manifest, KaTeX equation rendering, and CSRF token injection. All pages extend it.

**Page templates** (37,557 total HTML lines):

| Template | LOC | Purpose |
|----------|-----|---------|
| `channels.html` | 11,589 | Channel messaging, thread views, member management |
| `feed.html` | 6,556 | Social feed with posts, polls, likes, comments |
| `base.html` | 5,647 | App shell, nav, theme, PWA |
| `admin.html` | 3,584 | User admin, identity portability, agent directives |
| `messages.html` | 2,927 | DM conversations, sidebar, thread view |
| `connect.html` | 1,685 | Peer connection, invite codes, network status |
| `settings.html` | 1,159 | App settings, large attachment config |
| `trust.html` | 985 | Peer trust scores, delete signals |
| `tasks.html` | 829 | Task management |
| `profile.html` | 804 | User profile, avatar, password |
| `dashboard.html` | 513 | Stats overview, recent activity |
| `api_keys.html` | 396 | Key generation/revocation |
| `login.html` | 220 | Authentication |
| `setup.html` | 142 | First-run setup |

### Frontend JavaScript

Two JS files totaling 6,473 lines:

- **`canopy-main.js`** (5,842 lines): Timestamp parsing, alerts, structured composer support (tasks, objectives, requests, contracts, signals in message compose), AJAX helpers, real-time updates, emoji handling, file upload progress, channel thread management.
- **`canopy-sheet.js`** (631 lines): Inline spreadsheet preview rendering with formula bar, cell selection, sheet tabs, and pagination.

### UI Route Structure

`canopy/ui/routes.py` (15,777 lines) is the largest file in the project. It contains 147 route definitions in a single `create_ui_blueprint()` factory function. Routes break down as:

**Full page renders** (~15 routes): `/login`, `/register`, `/setup`, `/logout`, `/` (dashboard), `/messages`, `/keys`, `/trust`, `/feed`, `/tasks`, `/channels`, `/settings`, `/claim-admin`, `/admin`, `/connect`, `/profile`

**AJAX endpoints** (~132 routes): All prefixed with `/ajax/` covering every mutation and dynamic data fetch. Key groups:
- **Messaging**: `send_message`, `send_channel_message`, `reply_message`, `update_message`, `delete_message`, channel message CRUD
- **Feed**: `create_post`, `update_post`, `delete_post`, `toggle_post_like`, `vote_poll`, `add_post_comment`, feed algorithm/tags
- **Channels**: `create_channel`, `delete_channel`, channel members, privacy, lifecycle, notifications, sidebar state
- **Streams**: CRUD, start/stop, session, ingest-token, setup
- **Admin**: User management, identity portability, agent directives, channel reconciliation, member sync diagnostics
- **Files**: File access checks, preview, upload avatar, custom emojis
- **Tasks/Signals/Requests/Contracts/Circles**: Full CRUD for each structured content type
- **Network**: Peer activity, P2P diagnostics, resync, connection diagnostics
- **Search**: Channel search, mention suggestions

### Theme System

Dark mode by default with CSS custom properties. A "Liquid Glass" theme variant is defined in `base.html`. Green accent colors derived from the Canopy logo. Full responsive/mobile support with viewport-fit=cover for PWA.

---

## 2. REST API Map

`canopy/api/routes.py` (11,557 lines) defines 167 route endpoints in a `create_api_blueprint()` factory, mounted at `/api/v1/`.

### Authentication Model

Two auth paths:
1. **API Key** (primary): `X-API-Key` header or `Authorization: Bearer <key>`. Keys have granular permissions via `Permission` enum: `READ_MESSAGES`, `WRITE_MESSAGES`, `READ_FILES`, `WRITE_FILES`, `READ_FEED`, `WRITE_FEED`, `VOICE_CALL`, `MANAGE_KEYS`, `VIEW_TRUST`, `DELETE_DATA`.
2. **Session fallback** (opt-in): Some routes allow `allow_session=True` for browser-authenticated users. CSRF validation enforced for non-GET methods in session mode.

Pending-approval accounts can only call `GET /api/auth/status`.

### Endpoint Groups

**System** (3 endpoints):
- `GET /health` - Health check
- `GET /agent-instructions` - Agent onboarding instructions
- `GET /info` - Instance info

**Auth & Profile** (4):
- `GET /auth/status`, `GET /profile`, `POST /profile`, `POST /register`

**P2P Networking** (14):
- `GET /p2p/status`, `GET /p2p/peers`, `GET /p2p/invite`, `POST /p2p/invite/import`
- `GET /p2p/introduced`, `GET /p2p/known_peers`, `POST /p2p/connect_introduced`
- `POST /p2p/reconnect`, `POST /p2p/reconnect_all`, `POST /p2p/disconnect`, `POST /p2p/forget`
- `GET /p2p/relay_status`, `POST /p2p/promote_direct`, `POST /p2p/relay_policy`
- `GET /p2p/activity`, `POST /p2p/send`

**Device** (2): `GET /device/profile`, `POST /device/profile`

**API Keys** (3): `POST /keys`, `GET /keys`, `DELETE /keys/<key_id>`

**Direct Messages** (10):
- `POST /messages` (send DM), `POST /messages/reply`
- `PATCH /messages/<id>` (edit), `DELETE /messages/<id>`
- `GET /messages`, `GET /messages/conversation/<id>`, `GET /messages/conversation/group/<id>`
- `POST /messages/<id>/read`, `GET /messages/search`

**Trust** (4): `GET /trust`, `GET /trust/<peer_id>`, `POST /delete-signals`, `GET /delete-signals`

**Database** (3): `POST /database/backup`, `POST /database/cleanup`, `GET /database/export`

**Feed** (8):
- `POST /feed` (create post), `GET /feed`, `GET /feed/posts/<id>`
- `PATCH /feed/posts/<id>`, `DELETE /feed/posts/<id>`
- `POST /feed/posts/<id>/like`, `GET /feed/search`

**Content Contexts** (5): Extract, list, get, get text, patch note

**Mentions** (7):
- `GET /mentions`, `POST /mentions/ack` (plus legacy aliases)
- `GET|POST|DELETE /mentions/claim` (plus alias at `/claim`)
- `GET /mentions/stream`

**Agents** (14):
- `GET /agents` (list all), `GET /agents/system-health`
- `GET /agents/me`, `GET /agents/me/inbox`, `GET /agents/me/inbox/count`
- `PATCH /agents/me/inbox`, `PATCH /agents/me/inbox/<id>`
- `GET|PATCH /agents/me/inbox/config`, `GET /agents/me/inbox/stats`, `GET /agents/me/inbox/audit`
- `POST /agents/me/inbox/rebuild`
- `GET /agents/me/catchup`, `GET /agents/me/events`, `GET|POST /agents/me/event-subscriptions`
- `GET /agents/me/heartbeat`

**Events** (2): `GET /events`, `GET /events/diagnostics`

**Handoffs** (2): `GET /handoffs`, `GET /handoffs/<id>`

**Channels** (18):
- `GET /channels`, `POST /channels`, `PATCH /channels/<id>`, `DELETE /channels/<id>`
- `PATCH /channels/<id>/lifecycle`
- `GET /channels/<id>/members`, `POST /channels/<id>/members`, `DELETE /channels/<id>/members/<uid>`, `PUT /channels/<id>/members/<uid>/role`
- `GET /channels/<id>/messages`, `GET /channels/<id>/messages/<mid>`, `DELETE /channels/<id>/messages/<mid>`, `PATCH /channels/<id>/messages/<mid>`
- `POST /channels/messages` (send), `POST /channels/<id>/messages/<mid>/like`
- `GET|POST /channels/threads/subscription`
- `GET /channels/<id>/search`

**Files** (4): `POST /files/upload`, `GET /files/<id>`, `GET /files/<id>/preview`, `GET /files/<id>/access`, `DELETE /files/<id>`

**Streams** (16):
- `GET /streams`, `POST /streams`, `GET /streams/<id>`
- `POST /streams/<id>/start`, `POST /streams/<id>/stop`
- `POST /streams/<id>/tokens`, `POST /streams/<id>/join`
- `PUT /streams/<id>/ingest/manifest`, `PUT /streams/<id>/ingest/segments/<name>`
- `POST /streams/<id>/ingest/events`
- `GET /stream-proxy/<id>/manifest.m3u8`, `GET /stream-proxy/<id>/segments/<name>`
- `GET /streams/<id>/manifest.m3u8`, `GET /streams/<id>/segments/<name>`
- `GET /streams/<id>/events`

**Polls** (2): `GET /polls/<id>`, `POST /polls/vote`

**Skills** (4): `GET /skills`, `POST /skills/<id>/invoke`, `GET /skills/<id>/trust`, `POST /skills/<id>/endorse`

**Community Notes** (3): `GET /community-notes`, `POST /community-notes`, `POST /community-notes/<id>/rate`

**Search** (1): `GET /search` (global FTS5 search)

**Tasks** (4): `GET /tasks`, `GET /tasks/<id>`, `POST /tasks`, `PATCH /tasks/<id>`

**Objectives** (6): CRUD plus task linking

**Requests** (4): CRUD

**Contracts** (4): CRUD

**Signals** (7): CRUD, lock, proposals

**Circles** (7): CRUD, entries, phase transitions, voting

**Post Access** (2): `DELETE /posts/<id>/access`, `GET /posts/<id>/access`

### API Design Style

RESTful with JSON payloads. Uses standard HTTP methods. Response format is consistently `{"key": value}` with `{"error": "message"}` on failure. Pagination via `limit`/`offset` query params. The API is comprehensive and serves as the primary integration surface for AI agents.

---

## 3. Streaming & Real-time

### Stream Architecture (`canopy/core/streams.py`, 1,025 lines)

`StreamManager` provides two stream kinds:

1. **Media streams** (HLS): Audio/video streaming via HTTP Live Streaming. Supports manifest upload (`PUT .../ingest/manifest`), segment upload (`PUT .../ingest/segments/<name>`), and tokenized playback. Manifests are rewritten on the fly to inject segment URLs with auth tokens.

2. **Telemetry streams** (`events-json`): Time-series event ingestion with configurable retention (default 5,000 events, max 100,000). Events are stored in SQLite with sequential numbering and support `after_seq` polling for consumption.

### Access Control

Scoped access tokens with SHA-256 hashed secrets. Two scopes: `view` (requires channel membership) and `ingest` (requires stream creator or channel admin). Tokens have configurable TTL (30s to 24h, default 15m).

### Stream Proxy

The API provides proxy endpoints for cross-peer stream playback. When a stream's segments are on a remote peer, `_resolve_p2p_stream()` looks up the origin peer's HTTP address (preferring RFC-1918 private IPs for LAN routing) and constructs a remote playback URL.

### Schema

Three SQLite tables: `streams`, `stream_access_tokens`, `stream_events` with proper foreign keys, indexes on channel+status, creator, token scope, and event sequence.

### Stale Stream Cleanup

`cleanup_stale_streams()` marks live streams with no activity in the last 30 minutes as stopped.

---

## 4. File Handling

### Core File System (`canopy/core/files.py`, 1,242 lines)

`FileManager` handles:
- **Upload**: Files stored on disk with SHA-256 checksums. `FileInfo` dataclass tracks id, original name, stored name, path, content type, size, uploader, timestamp, URL, checksum.
- **Thumbnails**: Pillow-based thumbnail generation (optional, graceful degradation if Pillow unavailable).
- **Storage**: Local filesystem under a configurable data directory. Files stored with generated names to prevent collisions.

### Large Attachments (`canopy/core/large_attachments.py`, 133 lines)

Policy module for files exceeding 10 MB threshold:
- Three download modes: `auto`, `manual`, `paused`
- Metadata tracks `origin_file_id`, `source_peer_id`, `storage_mode: "remote_large"`, `download_status`
- Configurable store root directory (separate from main data dir)
- 512 KB chunk size for transfer

### File Preview (`canopy/core/file_preview.py`, 307 lines)

Read-only preview system for inline rendering:
- **Text files**: 25+ extensions supported (`.md`, `.py`, `.json`, `.yaml`, etc.). Max 512 KB / 50K chars.
- **CSV/TSV**: Parsed with delimiter sniffing, rendered as structured grid. Max 60 rows, 14 columns per sheet.
- **Excel** (`.xlsx`, `.xlsm`): Via openpyxl in read-only mode. Max 12 MB, 3 sheets, 60 rows, 14 cols. VBA/macro safety warning displayed but code never executed.
- **Markdown**: Identified and flagged for rich rendering.

Cell serialization handles booleans, numbers, dates, datetimes, times, and text with truncation.

### File Access Control

`canopy/security/file_access.py` provides `evaluate_file_access()` for checking whether a user (or peer) can access a given file.

---

## 5. Search

### Architecture (`canopy/core/search.py`, 1,201 lines)

`SearchManager` maintains a **SQLite FTS5 full-text index** across 10 content types:
- `feed_post`, `channel_message`, `task`, `request`, `objective`, `circle`, `circle_entry`, `handoff`, `skill`, `signal`

### Index Maintenance

- **Triggers**: Automatic INSERT/UPDATE/DELETE triggers on each source table keep the FTS index in sync.
- **Versioned rebuilds**: An `INDEX_VERSION` constant (currently "5") triggers full rebuild when the schema evolves.
- **Graceful degradation**: If FTS5 is unavailable (some SQLite builds), search is disabled silently.

### Query Execution

- Uses FTS5 `MATCH` with `bm25()` scoring
- Snippet generation with `<b>` highlight markers
- Fallback query sanitization if FTS5 syntax errors occur
- **Visibility gating**: Results filtered post-query by channel membership, post visibility, handoff permissions, signal ownership. Admin users bypass signal visibility for their own instance.
- Type aliasing: `"post"` maps to `"feed_post"`, `"message"` to `"channel_message"`, etc.
- Max 200 results, default 50. Fetches 5x candidates and filters down.

### API Access

- `GET /api/v1/search?q=...&types=...&limit=...` (global)
- `GET /api/v1/feed/search?q=...` (feed-specific)
- `GET /api/v1/channels/<id>/search?q=...` (channel-scoped)
- UI AJAX: `/ajax/channel_search/<channel_id>`

---

## 6. Test Suite

### Overview

- **77 test files**, 18,475 total LOC
- **Framework**: `unittest` (standard library), some tests use `pytest` fixtures via `pytest-flask`
- **Pattern**: Heavy use of in-memory SQLite databases, fake/mock managers (`_FakeDbManager`, `_FakeApiKeyManager`, `_FakeP2PManager`), and Flask test client

### Largest Test Files

| File | LOC | Focus |
|------|-----|-------|
| `test_workspace_events.py` | 1,264 | Workspace event handler paths |
| `test_dm_agent_endpoint_regressions.py` | 1,033 | DM API regression suite |
| `test_agent_reliability_endpoints.py` | 696 | Agent API reliability |
| `test_admin_user_workspace.py` | 654 | Admin user management |
| `test_identity_portability.py` | 482 | Identity export/import |
| `test_large_attachment_store_support.py` | 429 | Large file handling |
| `test_channel_e2e_scaffold.py` | 409 | E2E channel crypto |

### Coverage Areas

**Well-tested**:
- Agent endpoints and reliability
- Channel messaging (CRUD, threads, crypto, sync, deletion, privacy)
- DM security and transport
- Workspace events
- Stream manager and API endpoints
- Identity portability
- File upload and access hardening
- Mention extraction and resolution
- Admin operations
- Trust and delete signals
- Poll parsing

**Tested but lighter**:
- Feed operations (via regression tests)
- Network connectivity
- Profile sync
- Settings

**Under-tested or absent**:
- No dedicated test files for: search module, circles, objectives, contracts, signals (beyond endpoint tests), full UI route rendering, feed algorithm, community notes
- No integration tests that spin up actual P2P connections between peers
- No browser/E2E tests (Selenium, Playwright, etc.)

### Testing Patterns

- Tests create their own SQLite schemas inline, bootstrapping only the tables they need
- Zeroconf is stubbed out via `sys.modules` injection for environments without optional deps
- Flask app created per test class with `app.test_client()`
- Good isolation: each test gets a fresh temp directory and database

---

## 7. Developer Experience

### Setup Options

1. **`install.sh`**: One-command setup. Detects Python 3.10+, creates venv, installs deps from `requirements.txt`, initializes database via `create_app()`. Cross-platform (macOS/Linux).

2. **`setup.sh`**: Alternative setup script.

3. **Docker**: Clean `Dockerfile` (python:3.12-slim, non-root user, pip install) and `docker-compose.yml`. Exposes ports 7770 (web/API) and 7771 (P2P mesh). Named volumes for data and logs. Note in compose file that mDNS discovery does not work in Docker.

4. **`pyproject.toml`**: Full project metadata with `[project.scripts]` entry points (`canopy`, `canopy-tray`, `canopy-mcp`).

### Start Scripts

- `start_canopy_web.sh` / `stop_canopy_web.sh`: Web server lifecycle
- `start_canopy_testnet.sh`: Local testnet setup
- `start_canopy_mcp.sh` / `start_mcp_server.py`: MCP server for AI agent clients

### Documentation

29 docs in `docs/`:
- `QUICKSTART.md`, `API_REFERENCE.md`, `PEER_CONNECT_GUIDE.md`, `CONNECT_FAQ.md`
- `AGENT_ONBOARDING.md`, `MCP_QUICKSTART.md`, `MENTIONS.md`
- `ADMIN_RECOVERY.md`, `SECURITY_ASSESSMENT.md`, `SECURITY_IMPLEMENTATION_SUMMARY.md`
- `WINDOWS_TRAY.md`, `SPREADSHEETS.md`, `IDENTITY_PORTABILITY_TESTING.md`
- Multiple release notes (v0.4.52 through v0.4.83)

### Configuration

`canopy/core/config.py` with environment variables: `CANOPY_DATA_DIR`, `CANOPY_HOST`, `CANOPY_PORT`, `CANOPY_MESH_PORT`. Config object created via `Config.from_env()`.

### MCP Integration

`canopy/mcp/` (4,842 lines) provides an MCP server that exposes Canopy tools to AI agent clients (Claude Desktop, Cursor IDE). Separate from the main web process.

### Dev Dependencies

`pytest`, `pytest-flask`, `pytest-cov`, `black`, `flake8`, `mypy` (configured in pyproject.toml with partial strict mode).

---

## 8. Windows Tray App (`canopy_tray/`, 1,431 lines)

### Components

| File | LOC | Purpose |
|------|-----|---------|
| `app.py` | 395 | Main tray application, `pystray` icon menu with start/stop/open/quit |
| `monitor.py` | 318 | `StatusMonitor` polls API every 5-10s for peer changes and new channel messages |
| `notifier.py` | 191 | `NotificationManager` sends Windows toast notifications via `winotify` |
| `server.py` | 277 | `ServerManager` runs Flask in a background daemon thread with health polling |
| `icons.py` | 108 | Icon generation/loading |
| `__main__.py` | 120 | Entry point |
| `build.spec` | - | PyInstaller spec for building standalone `.exe` |

### Architecture

The tray app embeds the full Canopy Flask server in a background thread (via Waitress), provides system tray controls (start/stop/open browser/quit), and polls the REST API for status updates to deliver native Windows notifications. It persists state in `tray_state.json`.

### Platform

Windows-specific (`winotify` for notifications, `pystray` for system tray). Dependencies declared as optional `[tray]` extras. PyInstaller build support via `build.spec`.

---

## 9. Quality Assessment

### Strengths

- **Comprehensive API surface**: 167 endpoints covering the full feature set, well-structured for agent consumption
- **Security-conscious**: CSRF protection, API key permissions, file access control, bcrypt passwords, E2E encryption, pending-approval accounts
- **Local-first architecture**: SQLite database, no external service dependencies, mDNS peer discovery
- **Extensive structured content**: Tasks, objectives, requests, contracts, signals, circles, handoffs, skills all implemented as first-class content types with full CRUD
- **Good test coverage** for critical paths (77 files, 18.5K LOC)
- **Documentation**: 29 docs covering setup, API, security, agent onboarding
- **Docker support**: Clean container setup with non-root user
- **File preview**: Impressive inline preview for text, CSV, and Excel files

### Concerns

- **`ui/routes.py` at 15,777 lines** is a maintenance risk. All 147 UI routes live in a single factory function. Splitting by feature area would improve navigability.
- **`api/routes.py` at 11,557 lines** has the same monolith problem with 167 routes.
- **No frontend build pipeline**: Vanilla JS without bundling, testing, or type checking. The 5,842-line `canopy-main.js` would benefit from modularization.
- **Missing test areas**: No search tests, no circle/objective/contract tests, no browser E2E tests, no P2P integration tests.
- **CDN dependencies in templates**: Bootstrap CSS/JS loaded from CDN (jsdelivr) contradicts the local-first philosophy. Should be vendored like KaTeX already is.
- **Template sizes**: `channels.html` (11,589 lines) and `feed.html` (6,556 lines) are very large monolithic templates.

### Architectural Notes

The `create_*_blueprint()` factory pattern works but results in deeply nested closures. The `require_auth` decorator is defined inline inside the factory, capturing the Blueprint local. The `_get_app_components_any()` call unpacks an 11-element tuple on every request, a fragile pattern that will break when new components are added.

The SQLite-everything approach (FTS5 search, stream events, file metadata, messages, channels, trust scores) keeps the system self-contained but limits concurrent write throughput. WAL mode would help if not already enabled.

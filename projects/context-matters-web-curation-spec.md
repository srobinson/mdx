---
title: "cm-web: Context Store Monitor & Curator"
type: projects
tags: [context-matters, web, monitoring, curation, vite, react, axum, spec]
summary: "Spec for a monitoring-first web application over the context-matters store. Vite + React + TypeScript frontend, Axum JSON API backend. Separate crate in workspace."
status: draft
project: helioy
created: 2026-03-18
updated: 2026-03-19
supersedes: "original htmx server-rendered spec"
---

# cm-web: Context Store Monitor & Curator

## Vision

A monitoring-first web application that gives Stuart real-time visibility into what agents are writing to the context store, with inline curation as a natural side effect of observation. It also serves as a practical field test of the MCP surface by exercising the same store semantics through a browser-native workflow. This is the first web application in the Helioy ecosystem and establishes foundational patterns (components, hooks, API client, styling) that each future Helioy web project copies and adapts.

## Mental Model

The context store is a living system. Multiple agents write to it continuously. Entries accumulate across scopes, kinds, and tags. Without a monitoring surface, the only way to understand the store's state is through MCP tool calls or raw SQL. cm-web makes the store's health legible at a glance and makes curation frictionless.

**Primary workflow**: Monitor > Spot > Act > Move on. Never leave the scanning surface to take action.

## Current Store Profile

| Metric | Value |
|--------|-------|
| Active entries | 171 |
| Superseded entries | 5 |
| Entry creation rate | ~30/day |
| Active agents | 9 (claude-code writes 60%) |
| Scopes | 9 across 2 projects |
| Unique tags | 153 (97 used only once) |
| Database size | 632KB |
| Relations | 28 |

Key quality signals visible in the data:
- Tag sprawl: 97 singleton tags need consolidation
- Scope concentration: 36% of entries at global scope (likely over-broad)
- Kind imbalance: 60% observations, only 5% decisions and feedback
- Low supersession rate: 5/171 suggests duplicates aren't being caught

---

## Architecture

### Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | Vite + React 19 + TypeScript | Largest component ecosystem, best LLM code generation quality, Stuart's experience |
| Components | shadcn/ui + Radix UI primitives | Copy-paste ownership model. Radix is battle-tested and shadcn's default primitive layer. See component manifest below. |
| Styling | Tailwind CSS v4 | CSS-first config via `@theme` directive. shadcn's theming uses CSS variables. |
| Icons | Lucide | shadcn default. 1,500+ icons, 15.7KB for 200 icons. Best bundle efficiency at scale. |
| State | TanStack Query | Server state management with caching, background refetch. #1 React data library. |
| Routing | TanStack Router | Type-safe params + search params. URL-backed filter state benefits from compile-time route safety. |
| Markdown | react-markdown + rehype | Render entry bodies |
| Charts (deferred) | Tremor + Recharts | Tremor: Tailwind-native, copy-paste, 35+ dashboard components. Recharts for custom viz. Not in v1. |
| Backend API | Axum 0.8 + tower-http | JSON REST API, serves built frontend assets in production |
| Database | SQLite via cm-store | Same database, same `open_store()` path as MCP server |

**Initialization**: `npx shadcn create` with Radix primitives, Tailwind v4, Lucide icons.

**Research reference**: Full ecosystem analysis at `~/.mdx/research/react-component-ecosystem-2026.md`.

### shadcn Component Manifest

Components installed via `npx shadcn add <name>`. Each lives in `frontend/src/components/ui/`.

| Component | Used for |
|-----------|----------|
| `accordion` | Entry card expand/collapse in feed |
| `alert-dialog` | Forget confirmation |
| `badge` | Entry kind, quality flags, tag chips |
| `button` | Actions everywhere |
| `card` | Entry cards, dashboard stat cards |
| `collapsible` | Expandable sections within entry detail |
| `command` | Search autocomplete (uses cmdk + Radix) |
| `dropdown-menu` | Sort controls, entry actions overflow |
| `input` | Text fields (title, search) |
| `label` | Form labels |
| `popover` | Tag picker, scope picker |
| `scroll-area` | Feed scroll container |
| `select` | Kind, confidence, scope dropdowns |
| `separator` | Visual dividers |
| `sonner` | Toast notifications (via sonner lib) |
| `switch` | Dark/light toggle, show-forgotten toggle |
| `textarea` | Body editing (markdown) |
| `tooltip` | Icon labels, badge explanations |

**Not needed for v1** (add later if required):
- `dialog` / `sheet` / `drawer` (no side panels or modals)
- `tabs` (two views handled by router, not tabs)
- `table` (no table view)
- `data-table` (no table view)
- `menubar`, `navigation-menu` (simple nav, no menus)

### Theme

- All colors via CSS custom properties (shadcn's `--background`, `--foreground`, `--primary`, etc.)
- Never hardcode colors. All styling references theme variables.
- Dark/light mode toggle via class strategy (`:root.dark`)
- User preference persisted to `localStorage`
- Kind badge colors defined as theme extensions (semantic: `--kind-fact`, `--kind-decision`, etc.)

### Project Structure

```
crates/cm-web/                       # New crate in workspace
  Cargo.toml
  src/
    main.rs                          # Server startup, CLI args (clap)
    api/
      mod.rs                         # Axum router, AppState
      entries.rs                     # CRUD + search endpoints
      stats.rs                       # Aggregate stats endpoint
      export.rs                      # JSON export download
      mutations.rs                   # Mutation history endpoint
    shared.rs                        # Helpers extracted from cm-cli (or imported)
  frontend/
    package.json
    tsconfig.json
    vite.config.ts
    index.html
    src/
      main.tsx                       # App entry
      App.tsx                        # TanStack Router, layout shell
      styles/
        globals.css                  # Tailwind directives + shadcn CSS variables
      lib/
        utils.ts                     # cn() helper (shadcn generates this)
        constants.ts                 # Kind labels, scope display, defaults
        formatters.ts                # Relative time, scope breadcrumbs
      api/
        client.ts                    # Typed fetch wrappers
        types.ts                     # API types (see Types section)
      routes/
        __root.tsx                   # TanStack Router root layout
        index.tsx                    # Dashboard (default route: /)
        feed.tsx                     # Feed view (/feed)
      components/
        ui/                          # shadcn/ui generated (Radix primitives)
          accordion.tsx              # npx shadcn add accordion
          alert-dialog.tsx
          badge.tsx
          button.tsx
          card.tsx
          collapsible.tsx
          command.tsx
          dropdown-menu.tsx
          input.tsx
          label.tsx
          popover.tsx
          scroll-area.tsx
          select.tsx
          separator.tsx
          sonner.tsx
          switch.tsx
          textarea.tsx
          tooltip.tsx
        composed/                    # Reusable composed components (copy-paste to next project)
          FilterBar.tsx              # Faceted filter chips with counts
          TagInput.tsx               # Tag chip input with autocomplete
          InlineEdit.tsx             # Click-to-edit for text fields
          DiffView.tsx               # Before/after diff for pre-save confirmation
          ThemeToggle.tsx            # Dark/light mode switch
        domain/                      # cm-specific components (not reusable)
          EntryCard.tsx              # Feed item (compact + expanded states)
          EntryEditor.tsx            # Full edit form (within expanded card)
          ScopeTree.tsx              # Scope hierarchy with counts
          KindBadge.tsx              # Entry kind color badge
          QualityBadge.tsx           # Untagged, stale indicators
          MutationLog.tsx            # History of changes
          StatCard.tsx               # Dashboard summary card
          QualityAlerts.tsx          # Dashboard alerts banner
      hooks/
        useEntries.ts                # TanStack Query: useInfiniteQuery for feed
        useEntry.ts                  # TanStack Query: single entry get + mutate
        useStats.ts                  # TanStack Query: store stats
        useSearch.ts                 # TanStack Query: FTS5 search
        useFilters.ts                # URL search-param backed filter + sort state
        useMutationHistory.ts        # Mutation log queries
    components.json                  # shadcn config (paths, style, icons)
```

### Types

**Type generation (ts-rs, planned)**: Domain types in `cm-core/src/types.rs` will be generated to `frontend/src/api/generated/` via ts-rs. `#[derive(TS)]` on Rust structs produces TypeScript interfaces at test time (`cargo test --workspace`). Rust is the single source of truth. ts-rs is not yet added to cm-core; this is implementation work tracked in the scaffold sub-parent.

ts-rs setup (to implement):
- Add `ts-rs = { version = "12.0", features = ["chrono-impl", "uuid-impl", "serde-json-impl"] }` to `cm-core/Cargo.toml`
- Add `.cargo/config.toml`: `TS_RS_EXPORT_DIR = { value = "crates/cm-web/frontend/src/api/generated/", relative = true }`
- `ScopePath` needs `#[ts(as = "String")]` (custom serde `try_from`/`into`)
- `EntryMeta.extra` (flattened HashMap) needs `#[ts(type = "Record<string, unknown>")]` or `#[ts(skip)]`
- Research: `~/.mdx/research/ts-rs-rust-typescript-type-generation-2026.md`

Types generated from cm-core (consumed by frontend via import):

| Rust type | TypeScript output | Notes |
|-----------|------------------|-------|
| `Entry` | `{ id: string, scope_path: string, kind: EntryKind, ... }` | UUID and DateTime map to `string` |
| `NewEntry` | Omits id, content_hash, timestamps, superseded_by | Used by `POST /api/entries` |
| `UpdateEntry` | All fields optional | Used by `PATCH /api/entries/:id` |
| `EntryMeta` | `{ tags: string[], confidence?: Confidence, ... }` | `extra` field via `#[serde(flatten)]` |
| `EntryKind` | `'fact' \| 'decision' \| 'preference' \| ...` | 8 variants, `rename_all = "snake_case"` |
| `BrowseSort` | `'recent' \| 'oldest' \| 'title_asc' \| ...` | New enum, added as part of store-level sorted browse |
| `Confidence` | `'high' \| 'medium' \| 'low'` | |
| `ScopeKind` | `'global' \| 'project' \| 'repo' \| 'session'` | |
| `Scope` | `{ path: string, kind: ScopeKind, label: string, ... }` | |
| `RelationKind` | `'supersedes' \| 'relates_to' \| 'contradicts' \| ...` | 5 variants |
| `EntryRelation` | `{ source_id: string, target_id: string, relation: RelationKind, ... }` | |
| `StoreStats` | `{ active_entries: number, entries_by_kind: Record<string, number>, ... }` | Base stats only; dashboard extends this |
| `TagCount` | `{ tag: string, count: number }` | |
| `EntryFilter` | `{ scope_path?: string, kind?: EntryKind, sort?: BrowseSort, ... }` | Includes `Pagination` and sort field |
| `Pagination` | `{ limit: number, cursor?: string }` | Cursor is opaque string; store owns encoding |
| `PagedResult<T>` | `{ items: T[], total: number, next_cursor?: string }` | Generic |
| `MutationRecord` | `{ id: string, entry_id: string, action: MutationAction, ... }` | Snapshots are `unknown` (serde_json::Value) |
| `MutationAction` | `'create' \| 'update' \| 'forget' \| 'supersede'` | `rename_all = "lowercase"` |
| `MutationSource` | `'mcp' \| 'cli' \| 'web' \| 'helix'` | `rename_all = "lowercase"` |
| `WriteContext` | `{ source: MutationSource }` | Passed by callers on every write |

Web-only types (defined in `frontend/src/api/types.ts`, not generated):

```typescript
// Compact entry for list/feed views (no full body)
interface EntrySnippet {
  id: string
  scope_path: string
  kind: EntryKind
  title: string
  snippet: string               // Truncated body (~200 chars)
  tags: string[]
  confidence?: string
  created_by: string
  created_at: string
  updated_at: string
  superseded_by: string | null
}

// Filter state (URL-param backed)
// BrowseSort is generated from cm-core via ts-rs; FilterState maps it to URL params
interface FilterState {
  scope_path?: string
  kind?: EntryKind
  tag?: string
  created_by?: string
  sort: BrowseSort               // Maps 1:1 to cm-core BrowseSort enum
  show_forgotten: boolean        // Toggle to reveal superseded entries
}

// GET /api/stats response. Explicit web read model, not an extension of StoreStats.
// cm-web constructs this from store.stats() plus supplementary queries.
interface DashboardStats {
  active_entries: number
  superseded_entries: number
  entries_today: number          // Created in last 24h
  entries_this_week: number      // Created in last 7 days
  scope_tree: ScopeNode[]        // Hierarchical scope list with counts
  active_agents: AgentInfo[]     // Agents with activity in last 7 days
  entries_by_kind: Record<string, number>
  entries_by_scope: Record<string, number>
  entries_by_tag: TagCount[]
  db_size_bytes: number
  quality: QualitySnapshot       // Inputs for quality alerts
}

// Pre-computed quality inputs (avoids client fetching all entries to count)
interface QualitySnapshot {
  untagged_count: number         // Entries with zero tags
  under_tagged_count: number     // Entries with exactly one tag
  stale_count: number            // Entries not updated in 30+ days
  global_scope_count: number     // Entries at global scope (potentially over-broad)
  multi_tagged_count: number     // Entries with 2+ tags (quality positive)
}

// Derived from: SELECT DISTINCT created_by, COUNT(*), MAX(created_at)
// FROM entries WHERE superseded_by IS NULL GROUP BY created_by
interface AgentInfo {
  created_by: string
  entry_count: number
  last_active: string            // ISO 8601
}

// Quality indicators (computed client-side from entry data)
interface QualityFlags {
  untagged: boolean              // tags.length === 0
  under_tagged: boolean          // tags.length === 1
  stale: boolean                 // updated_at > 30 days ago
}
```

### Backend API

REST endpoints are aligned with the MCP tool surface and reuse the same underlying store semantics where possible. The goal is to field test the MCP model through a web UI, not to force strict 1:1 response shapes for every endpoint. Web-specific read models (for dashboard aggregation, sort controls, and UI composition) are allowed.

```
GET    /api/entries              # Browse-oriented list for feed UI
GET    /api/entries/search       # FTS5 search, matches cx_recall candidate selection
GET    /api/entries/:id          # Full entry + relations_from + relations_to
POST   /api/entries              # cx_store: create new entry
PATCH  /api/entries/:id          # cx_update-style partial update (scope change excluded)
DELETE /api/entries/:id          # cx_forget: soft-delete
POST   /api/entries/merge        # Supersede + create consolidated or re-scoped replacement
GET    /api/stats                # Dashboard-oriented aggregates
GET    /api/mutations            # Store-wide mutation history (filterable by source)
GET    /api/export               # cx_export: JSON download
```

Notes:
- `PATCH /api/entries/:id` does not support scope migration. Scope changes are modeled as create-a-replacement + supersede-the-original.
- `GET /api/stats` returns `DashboardStats`, an explicit web read model defined in cm-web. Constructed from `store.stats()` plus supplementary queries for today/week counts, active agents, scope tree, and quality snapshot. Not an extension of cm-core's `StoreStats`.
- `GET /api/entries/:id` returns the full entry plus `relations_from: EntryRelation[]` and `relations_to: EntryRelation[]`. Two extra store calls (`get_relations_from`, `get_relations_to`) per request. No separate relations endpoint needed at this scale.
- `GET /api/mutations` is the store-wide audit endpoint. It calls `ContextStore::list_mutations` which queries across all sources. Optional filters: `entry_id`, `action`, `source`, `since`, `until`. The UI defaults to `source=web` when showing curation history, but the endpoint itself reflects the full cm-store mutation model.

Query parameters for `GET /api/entries`:
- `scope_path` -- exact scope filter
- `kind` -- entry kind filter
- `tag` -- tag filter
- `created_by` -- agent/creator filter
- `sort` -- BrowseSort value (recent, oldest, title_asc, title_desc, scope_asc, scope_desc, kind_asc, kind_desc)
- `include_superseded` -- boolean, show forgotten entries
- `cursor` -- opaque page token (store-owned encoding, sort-aware)
- `limit` -- page size (default 50, max 200)

**Pagination**: Cursor-based for all sort modes. The store owns cursor encoding/decoding semantics per sort. The cursor is an opaque string at the API boundary; the frontend does not interpret its contents. Each sort mode encodes the last-seen ordered fields plus `id` as tiebreaker. Frontend uses TanStack Query's `useInfiniteQuery` for infinite scroll. Each response includes `next_cursor` when more results exist. This is a store-level contract: `BrowseSort` and the opaque cursor live in cm-core, cursor logic in cm-store.

**Store-level sorted browse contract** (prerequisite, implemented before cm-web):
- Add `BrowseSort` enum to cm-core: `Recent`, `Oldest`, `TitleAsc`, `TitleDesc`, `ScopeAsc`, `ScopeDesc`, `KindAsc`, `KindDesc`
- Add `sort: BrowseSort` field to `EntryFilter`
- Replace `PaginationCursor { updated_at, id }` with an opaque page token (`String`). The store encodes/decodes cursor contents per sort mode.
- Each sort defines a deterministic total order with `id` as final tiebreaker. Example: `TitleAsc` uses `ORDER BY title ASC, updated_at DESC, id DESC`.
- Text sort uses SQLite default collation for v1. Case-folding and locale behavior deferred.
- Cursor comparison logic mirrors the SQL ordering for each sort mode.

Query parameters for `GET /api/entries/search`:
- `q` -- FTS5 query string
- `scope` -- optional scope filter (when set, ancestor walk determines candidate entries)
- `kinds[]` -- kind filter (multiple)
- `tags[]` -- tag filter (multiple)
- `limit` -- result limit

**Search**: v1 search matches current `cx_recall` behavior exactly. Scoped search means "search within target scope plus ancestors" (ancestor walk determines candidate entries). Ordering is FTS5 relevance score (`ORDER BY rank`), not scope depth. This matches the current `search()` implementation in cm-store. Scope-first ranking is a potential future search mode, not a v1 feature.

### Shared Code

Helpers currently in `cm-cli/src/mcp/mod.rs` are needed by the web API handlers:
- `ensure_scope_chain`, `clamp_limit`
- `snippet`, `estimate_tokens`, `cm_err_to_string`, `check_input_size`
- `parse_confidence`, `entry_to_*_json` formatters

Cursor encoding/decoding is no longer a handler helper concern. With store-level sorted browse, the opaque cursor contract belongs in cm-core/cm-store, not `cm-cli`.

**Approach**: Extract non-cursor helpers to `cm-cli/src/shared.rs` (pub), then `cm-web` depends on `cm-cli` for shared helpers + `cm-store` for database access. Alternatively, create a thin `cm-shared` crate if the dependency feels wrong.

### Build & Serve

**Development:**
```sh
# Terminal 1: Axum API server with hot reload
cargo watch -x 'run -p cm-web -- --port 3141'

# Terminal 2: Vite dev server with HMR, proxying /api to Axum
cd crates/cm-web/frontend && npm run dev
```

Vite dev server proxies `/api/*` requests to `http://localhost:3141`.

**Production:**
```sh
cd crates/cm-web/frontend && npm run build   # Outputs to dist/
cargo build -p cm-web                        # Embeds dist/ via rust-embed or include_dir
cm-web --port 3141 --open                    # Single binary serves everything
```

### Logging

Structured logging via `tracing` with:
- Request/response logging (method, path, status, duration)
- Mutation logging (what changed, who triggered it)
- Error logging with context
- Configurable log level via `--verbose` flag and `RUST_LOG` env var

---

## Information Architecture

Two views. Each answers a distinct question.

### 1. Dashboard (Default View) -- "How healthy is the system?"

The landing page. Answers: what happened since I last looked, is anything off, what's the shape of the store.

**Layout (top to bottom):**

**Summary cards (top row):**
- Total active entries
- Entries today / this week
- Active agents: derived from `SELECT DISTINCT created_by, COUNT(*), MAX(created_at) FROM entries WHERE superseded_by IS NULL GROUP BY created_by`. Shows agent names with entry counts. "Active" = has written in last 7 days.
- Quality score: simple composite percentage. Formula: `(multi_tagged_count / active_entries * 0.5) + (non_stale_entries / active_entries * 0.5)`. This is a heuristic for v1. Computed client-side from `DashboardStats.quality` fields. `entries_at_correct_scope` is dropped from v1: the system has no objective "correct scope" signal yet.

**Quality alerts banner:**
Actionable items surfaced prominently. "12 entries need attention: 4 untagged, 5 at global scope." Each item is clickable, navigates to Feed with appropriate filter applied. Computed client-side from `DashboardStats.quality`, not from fetching the full entry corpus.

Note: "Potential duplicate" and "scope mismatch" detection are deferred. Helix will report these from the field. v1 quality badges are limited to: untagged, under-tagged, stale.

**Recent activity (left 60%):**
Last 20 entries, reverse chronological. Compact cards showing title, agent, scope, tags, timestamp. Click navigates to Feed with entry expanded.

**Scope tree (right 40%):**
Visual hierarchy of scopes with entry counts. Click a scope to navigate to Feed filtered by that scope.

Charts are deferred. Stats are text/number cards only for v1.

### 2. Feed View -- "What's in the store?"

The primary working view. All entries in a scrollable list. Supports both chronological scanning and filtered/sorted exploration.

**Sort controls (top of feed, alongside filters):**
- Recent (default): `updated_at DESC`
- Oldest: `updated_at ASC`
- Title A-Z / Z-A
- Scope A-Z / Z-A
- Kind

**Each entry card (compact state) shows:**
- Kind badge (color-coded)
- Title (primary text)
- Scope (as breadcrumb path)
- Agent name
- Relative timestamp ("2m ago", "1h ago")
- Tag chips (first 5, "+N more" overflow)
- Quality badges (untagged, under-tagged, stale)
- Content preview (first 2 lines, truncated)

**Entry card (expanded state):**
Clicking an entry card expands it inline (accordion). The expanded card shows:
- Full markdown-rendered body
- All metadata: kind, scope, confidence, created_by, created_at, updated_at, content_hash
- All tags (with inline add/remove)
- Related entries (via entry_relations)
- Edit button: transforms the expanded card into an edit form
- Forget button: with confirmation

**Edit mode (within expanded card):**
- Title: text input
- Body: markdown textarea with preview toggle
- Kind: dropdown
- Scope: dropdown/tree picker. Changing scope creates a replacement entry and supersedes the original; it is not an in-place patch.
- Tags: chip input with autocomplete from existing tags
- Confidence: dropdown (high/medium/low)
- created_by: read-only display
- Pre-save diff: before clicking "Save", show a diff of what changed. Save > diff view > confirm.
- Cancel returns to read-expanded state

**Forget behavior:**
- Forget button triggers a confirmation
- On confirm: entry card fades out (200ms opacity transition)
- Toast appears: "Forgotten [title]"
- FilterBar includes "Show forgotten" toggle. When on, forgotten entries appear grayed out as inactive entries.

**FilterBar (persistent, top of feed):**
- Scope: dropdown/chips with counts
- Kind: chips with counts
- Agent: chips with counts
- Tag: searchable dropdown
- "Show forgotten" toggle
- Active filters shown as removable chips with "Clear all"
- Filter state persisted in URL params (shareable, survives refresh)

**Create new entry:**
A "+" button in the feed header. Opens an empty expanded card in edit mode at the top of the feed. Same fields as edit mode. On save, card animates into the feed at its sorted position.

---

## Mutation History (P1 -- cm-store level) [IMPLEMENTED]

Shipped in `feat: add mutation history infrastructure to cm-store (#10)`.

Every write operation on the context store is logged at the **cm-store layer**, regardless of caller. MCP tools, CLI commands, web UI, and future Helix operations all produce mutation records. This is infrastructure, not a web feature.

**Storage**: The `mutations` table in `cm-store`'s SQLite schema (migration `005_mutations.sql`). Written by cm-store's write path, not by individual callers.

```sql
CREATE TABLE mutations (
    id               TEXT PRIMARY KEY,           -- UUID v7
    entry_id         TEXT NOT NULL,              -- Entry that was mutated (no FK, survives deletion)
    action           TEXT NOT NULL CHECK (action IN ('create', 'update', 'forget', 'supersede')),
    source           TEXT NOT NULL CHECK (source IN ('mcp', 'cli', 'web', 'helix')),
    timestamp        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    before_snapshot  TEXT,                       -- JSON: full entry state before (NULL for create)
    after_snapshot   TEXT                        -- JSON: full entry state after (all actions capture post-state)
);
CREATE INDEX idx_mutations_entry ON mutations(entry_id);
CREATE INDEX idx_mutations_timestamp ON mutations(timestamp);
CREATE INDEX idx_mutations_source ON mutations(source);
```

No foreign key on `entry_id`. Mutation records are self-contained (full JSON snapshots of entry state) and must survive even if an entry row is hard-deleted by maintenance, import/reset, or future operations. An audit trail that disappears when its subject is deleted defeats the purpose.

**cm-store integration**: Every write method on the `ContextStore` trait (`create_entry`, `update_entry`, `forget_entry`, `supersede_entry`) takes a `&WriteContext` parameter and writes a mutation record in the same transaction. `WriteContext` wraps a `MutationSource` enum (`Mcp | Cli | Web | Helix`). Callers declare their origin; cm-store handles the rest. Zero additional work for consumers.

**Snapshots**: `before_snapshot` is NULL for `create` (no prior state). `after_snapshot` is captured for all four actions, including `forget` (records the entry's final state with `superseded_by` set).

**Query methods on ContextStore**:
- `get_mutations(entry_id, limit, offset)`: per-entry history with pagination
- `list_mutations(entry_id?, action?, source?, since?, until?, limit)`: filtered queries across all entries, including timestamp range

**API**: `GET /api/mutations` with filters: entry_id, action, source, date range. Returns reverse-chronological list. The web UI can filter to `source=web` to isolate its own curation trail, or show all sources for full history.

**UI**: Accessible from the expanded entry card ("History" tab or link). Shows a timeline of all changes to that entry from any source. Each mutation shows the diff.

**Why P1**: This is foundational infrastructure for Helix. Every context source in the ecosystem benefits from a store-level audit trail. Building it into cm-store now means MCP, CLI, web, and Helix all get mutation history for free. Retrofitting it later means either missing historical data or backfilling.

---

## Visual Design Principles

Not a full design system. Principles that guide implementation.

- **Density over decoration.** Maximize information per viewport. Chrome recedes, content stays prominent.
- **System fonts.** `-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif`. Monospace for IDs, hashes, timestamps, code.
- **Color is semantic.** Kind badges and quality indicators use color. Everything else is neutral.
- **Dark mode from day one.** CSS custom properties / Tailwind dark variant. Single-user tool, likely used in dark environments.
- **Motion is functional.** Card expand/collapse, forget fade-out, toast enter/exit. No decorative animation. 150-200ms durations.
- **Responsive but opinionated.** Optimized for 13" laptop and external monitor. No mobile layout. Sidebar collapses at narrow widths.

---

## Foundational Patterns (for Helioy ecosystem reuse)

Components in `components/ui/` are designed to be copied into the next Helioy web project without modification. Domain components in `components/domain/` are cm-specific.

Reusable patterns this project establishes:
1. **API client**: Typed fetch wrappers with TanStack Query integration
2. **FilterBar**: URL-param backed faceted filtering with chips UI
3. **ExpandPanel**: Inline accordion expand with animated transitions
4. **InlineEdit**: Click-to-edit for text fields with save/cancel
5. **Toast**: Mutation feedback with undo capability
6. **Badge**: Semantic color-coded labels
7. **DiffView**: Before/after comparison for pre-save confirmation
8. **TagChip**: Tag display with inline add/remove + autocomplete
9. **Dark mode**: Tailwind dark variant pattern from the start

---

## Deferred (not in v1)

- Charts/visualizations on dashboard (text/number cards sufficient for v1)
- Command palette (Cmd+K)
- Keyboard navigation (revisit after using the app to understand real workflow)
- Bulk operations (select multiple, bulk forget/retag/scope-change)
- Duplicate detection / scope mismatch detection (Helix will report from the field)
- Agent-level views / per-agent dashboards
- Content diff on entry updates (except pre-save diff which IS in v1)
- WebSocket real-time updates (TanStack Query polling sufficient at ~30 entries/day)
- Restore / undo semantics for forgotten entries beyond the current UI flow
- Scope-first search ranking (separate search mode, not a change to default FTS ordering)
- Scope correctness signal for quality scoring (no objective "correct scope" metric yet)

## Open Questions

- Should forgotten entries become restorable via a first-class store operation, or remain non-restorable in v1 while the web UI focuses on monitoring and curation only?

---

## Constraints

- Separate `cm-web` crate in the context-matters workspace
- Single binary in production: Axum serves API + embedded frontend assets
- No authentication. Single user, localhost only.
- Database: `~/.context-matters/cm.db`. Same path as MCP server.
- Port 3141 default. `--port` flag for override. `--open` flag to launch browser.
- Frontend works without Vite dev server in production (embedded static assets).

---

## Resolved Decisions

1. **Project location**: Separate `cm-web` crate in workspace.
2. **Views**: Dashboard + Feed. No separate table view. Feed with sort controls covers comparison needs.
3. **Entry interaction**: Expanding inline panel, not side panel/drawer. Keep spatial context.
4. **Diff**: Pre-save only. Edit > diff view > confirm. No historical content diffs in v1.
5. **Search**: v1 matches cx_recall behavior exactly. Scope determines candidates (ancestor walk), ordering is FTS5 relevance. Scope-first ranking is a separate deferred search mode.
6. **Duplicate detection**: Deferred. Helix will report from the field.
7. **Standalone per project**: Each Helioy project ships its own web app. Patterns transfer via copy-paste, not shared packages.
8. **Components**: Not from scratch. Use shadcn/ui + Radix primitives. Copy-paste ownership model, Tailwind-native, dark mode, accessible.
9. **Type sharing**: ts-rs (v12.0). Rust is the single source of truth. `#[derive(TS)]` on cm-core types generates TypeScript to `frontend/src/api/generated/`. No hand-written type duplication. Research: `~/.mdx/research/ts-rs-rust-typescript-type-generation-2026.md`.
10. **Sorted browse**: Store-level contract. `BrowseSort` enum and sort-aware opaque cursor live in cm-core/cm-store. All sort modes use cursor pagination. No offset fallback.
11. **Dashboard stats**: Explicit web read model (`DashboardStats`), not an extension of cm-core's `StoreStats`. cm-web constructs it from `store.stats()` plus supplementary queries.
12. **Entry detail**: `GET /api/entries/:id` returns entry + relations inline. No separate relations endpoint.
13. **Mutations endpoint**: Store-wide audit trail with optional filters. UI defaults to `source=web` for curation view.

---

## Success Criteria

- [ ] `cm-web` starts Axum server on port 3141, serves the React app
- [ ] `--port` and `--open` flags work
- [ ] Dashboard: summary cards (total entries, today/week, active agents, quality score)
- [ ] Dashboard: quality alerts banner with clickable items
- [ ] Dashboard: recent activity list (last 20 entries)
- [ ] Dashboard: scope tree with entry counts
- [ ] Feed: scrollable entry list with compact cards
- [ ] Feed: sort controls (recent, oldest, title, scope, kind)
- [ ] Feed: FilterBar (scope, kind, agent, tag, show-forgotten toggle)
- [ ] Feed: filter state persisted in URL params
- [ ] Feed: entry expand inline (accordion) with full markdown content
- [ ] Feed: expanded entry shows all metadata + related entries
- [ ] Feed: inline editing within expanded card (title, body, kind, scope, tags, confidence)
- [ ] Feed: pre-save diff view with confirm
- [ ] Feed: create new entry via "+" button
- [ ] Feed: forget with confirmation, fade-out animation, and toast feedback
- [ ] Feed: FTS5 search (matches cx_recall: scope determines candidates, FTS5 rank orders results)
- [ ] Quality badges on entry cards (untagged, under-tagged, stale)
- [x] Mutation history: store-level audit trail in cm-store (P1), viewable per entry with source filter
- [ ] Mutation history: cm-web UI surfaces per-entry timeline with source filter
- [ ] Export: trigger JSON download from UI
- [ ] Dark mode
- [ ] Structured server logging (requests, mutations, errors)
- [ ] API semantics remain aligned with the MCP/store model while allowing web-specific read models
- [ ] Store-level sorted browse: BrowseSort enum, sort field on EntryFilter, opaque cursor contract
- [ ] ts-rs type generation: derive TS on cm-core types, .cargo/config.toml, just recipe
- [ ] Components in ui/ are reusable (copy-paste directly into another project)

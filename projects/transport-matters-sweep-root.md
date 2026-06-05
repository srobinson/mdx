# Root docs sweep — scout report

Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters` @ `main` (`af52318d`)  
Lens: docs guide, they do not promise. Code is source of truth. Fewer is better.  
Test: would a code change silently invalidate this? If yes, liability → delete, not correct.  
Cluster: `TLDR.md`, `README.md`, `QUICKSTART.md`, `NOW.md`, `docs/CHANNELS.md`.

---

## Summary

| Path | Lines | Disposition | Rationale (one line) |
| --- | ---: | --- | --- |
| `TLDR.md` | 89 | **TRIM to ~55–65** | Agent-loaded every turn via `CLAUDE.md`/`AGENTS.md`/`Agents.md` symlinks; half is changelog, route inventory, or README positioning |
| `README.md` | 275 | **TRIM** (setup) | Human product doc; install/quick-start duplicates `QUICKSTART.md`; keep operator surface and architecture sketches |
| `QUICKSTART.md` | 102 | **KEEP AS IS** | Operational bootstrap only; low rot, clear steps, points at CHANNELS for dev |
| `NOW.md` | 496 | **TRIM to ~280–320** | Explicitly not a history of shipped work, yet Phase 1 holds long SHIPPED narratives (#352/#353/#354) |
| `docs/CHANNELS.md` | 242 | **KEEP AS IS** | Reference for channel isolation; dense but operators need the tables; one-time legacy block can age out later |

---

## Independent judgment on the five TLDR claims

Earlier analysis listed five liabilities. Verdicts below are from re-reading the tree, not from accepting that list.

### 1. Retired surfaces paragraph (legacy index, block store, diff projection, raw fetch, dark wire store + `#259` + `0008_wire_store`)

**Agree: cut the changelog; keep a one-line product marker.**

- Teaching an agent what does *not* exist is expensive context. Issue numbers and migration names age and force doc edits after merges.
- Confirmed still true in code: `WireStoreObserver` writes via `SessionWriter`; no product read surface found for wire exchanges. Deferred block in `NOW.md` restates the same facts (duplicate).
- `docs/ARCHITECTURE.md` already says product mental model for “dark wire store” lives in `TLDR.md`, so a durable sentence is enough: wire is written; wire-vs-transcript diff still needs a read surface. Drop retired surface inventory and issue/migration cites.

### 2. Canvas / `RunManager` paragraph (routes, `DELETE`, scrollback, minimize vs close, `app.state`)

**Agree, and stronger: the block is already partly wrong.**

- TLDR says a server-managed `RunManager` owns the run on `app.state` with `/runs` and `WS /runs/{id}/terminal`. Code and ARCHITECTURE place `RunManager` in the product plane (`packages/runtime`, mounted by `packages/gateway`). Python `app.state` holds gateway process / capture plumbing, not that route inventory.
- ARCHITECTURE: Runtime is the Gateway’s first router; migration order still documents origin flip. Route and close/minimize semantics will keep moving under that migration.
- **Survives as markers only:** canvas can host a captured run through the same capture seam as CLI (`prepare_captured_run`); lifecycle is process-resident. Point at ARCHITECTURE for ownership. Drop route lists, scrollback ring, DELETE affordance, minimize-vs-close.

### 3. Channel axis restating `docs/CHANNELS.md`

**Agree.**

- TLDR already links CHANNELS in the same sentence. Naming the three channel ids and “each owns home/db/ports” is enough orientation; maturity copy and Electron detail belong only in CHANNELS.

### 4. “No system proxy toggle, no global certificate install, no sudo”

**Agree: README positioning, not agent mental model.**

- Same claim lives in `README.md` (and is echoed in `NOW.md` hosted-matrix prose). Agents do not need the non-invasive install pitch every turn. Drop from TLDR.

### 5. Fenced hierarchy block (`bash`, `opus-confirmed`, owner / Space / Worktree / Canvas)

**Partial disagree on substance; agree on form.**

- Earlier claim: if vocabulary is unused, delete; if used, make it prose.
- **It is used.** Domain types and stores exist: `packages/space` (`StoredContextWorktree`, `StoredContextCanvas`, `SpaceId` / `WorktreeId` / `CanvasId`), `www/packages/space-client`, Python `SpaceStore`, gateway mounts Space when DB is set. Hierarchy is load-bearing for canvas/control-center work.
- **Form fails the lens:** fenced as `bash` (not bash), “opus-confirmed” is provenance not guidance, and this is the only root-doc statement of the hierarchy. Convert to short prose under Mental Model; drop the fence and provenance.

### Extra TLDR findings (not in the prior list)

- **WWW section** mixes durable orientation (`www/packages/` vs embedded bundles vs `packages/*`) with packaging notes (`D1-b`, “after the separation”) that will age. Keep three stable roots; drop decision labels.
- **Planes** (Python capture vs TypeScript product) are the highest-value agent fact *missing* from TLDR and present in ARCHITECTURE. One short paragraph prevents wrong-plane PRs. Durable rule, not a route inventory.
- **Symlinks confirmed:** `CLAUDE.md`, `AGENTS.md`, `Agents.md` → `TLDR.md`. Token cost claim is real.

---

### TLDR.md (89 lines)

- **Disposition:** TRIM to ~55–65 lines (proposed full text below ~63 lines).
- **Survives:**
  - One-sentence product definition (proxy, pause, Postgres history).
  - Two launch paths (Claude reverse proxy, Codex HTTPS proxy).
  - Pointers: CHANNELS, NOW, ARCHITECTURE, `doctor`.
  - Mental model: orthogonal stack, workspace path identity, turn = wire + transcript never collapsed, Tier-1 path pattern, Postgres/`SessionWriter`, breakpoint, Codex incremental turns.
  - Durable product marker: wire written, wire-vs-transcript still needs a read surface (no issue/migration).
  - Canvas hosts captured runs via shared capture seam; process-resident lifecycle (no routes).
  - Space → Worktree → Canvas as prose; point at `packages/space`.
  - Two-plane rule (capture vs product).
  - Minimal tree orientation for `www/`, embedded bundles, `packages/*`, capture plane root.
- **Cuts:**
  - Non-invasive install marketing.
  - Channel maturity essay (link suffices).
  - Retired surface inventory + `#259` / `0008_wire_store`.
  - RunManager on `app.state`, `/runs`, scrollback, DELETE, minimize vs close (wrong plane + volatile).
  - Fenced hierarchy / `opus-confirmed`.
  - Packaging decision labels (`D1-b`, “after the separation”).

#### Proposed full replacement

```markdown
# TLDR

`transport-matters` is the wire-level observability and session history layer
for littleorgans coding agents. It proxies live agent traffic, persists turn
artifacts, can pause the next outbound request for inspect or edit, and records
correlated transcript history in Postgres.

Two launch paths: Claude Code through a reverse proxy in front of
`api.anthropic.com`, and Codex through an explicit HTTPS proxy for ChatGPT
authenticated websocket traffic. Proxy, backend, and UI ship as one install.
Channels isolate home, database, ports, and Electron identity
(`stable` / `preview` / `dev`). See [docs/CHANNELS.md](./docs/CHANNELS.md).

**Current focus:** [NOW.md](./NOW.md). Decisions: [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).

## Mental Model

Orthogonal to the rest of the Little Organs stack. TM sees the bytes regardless
of who spawned the agent and does not coordinate with session-matters or
runtime-matters at runtime.

A **workspace** is the unit of capture. Identity is the canonical target path,
not the visible slug, so two checkouts of the same project share history.

A **turn** is one outbound request and its response. Two streams are captured
and never collapsed: the **wire** (what hit the provider) and the **transcript**
(what the CLI recorded on disk). Their difference is the product: injected
reminders, tool schemas, and replayed context the harness hides surface as
wire-only content.

**Storage.** Tier-1 source of truth is the per-run directory under
`<channel home>/workspaces/{slug}/{hash}/{run}/` (raw request and response
bytes, owned transcript, launch facts). Correlated history is Postgres;
`SessionWriter` owns writes from the transcript tailer and backfill. The API
exposes owner-scoped session reads and live event streaming, not raw bytes.
Wire bytes are written today; wire-versus-transcript diff still needs a read
surface over that store.

A **breakpoint** holds the next outbound turn for review or edit before
release. Codex later turns carry incremental request payloads; the UI reflects
that wire reality.

A captured run can run in a **canvas** pane as well as a detached CLI: same
capture seam (`prepare_captured_run`), PTY bridged to the pane. Run lifecycle
is process-resident and does not outlive the process that owns it.

**Hierarchy.** An owner organizes **Spaces** (workdir-agnostic). A Space holds
**Worktrees** (path identity; may span repos). A **Canvas** is anchored to a
Worktree. Domain code lives under `packages/space` and `@tm/contract/space`.

**Planes.** Python is the capture plane (mitmproxy, Tier-1, frozen Inspector
API, session store). TypeScript is the product plane (Activity, Runtime, Space,
Gateway composition root). New product work extends the product plane; see
ARCHITECTURE for seams and the cli ratchet.

`transport-matters doctor` is the first command when something feels wrong.

## Tree orientation

- `www/packages/` — browser package sources (pnpm)
- `api/src/transport_matters/www/` and `.../canvas/` — embedded Inspector and Canvas bundles served at `/` and `/canvas`
- `packages/*` — product-plane node packages (`gateway`, `runtime`, `space`, …)
- `api/src/transport_matters/` — capture plane
```

---

### README.md (275 lines)

- **Disposition:** TRIM (setup surface only); keep as the human-facing product/operator doc.
- **Survives:**
  - Positioning and two launch paths.
  - Non-invasive install claims (correct home for them).
  - Command catalog, pass-through args, workflow, multi-instance behavior, “no aggregated view yet” (honest limitation marker).
  - Claude/Codex architecture sketches and Codex env/trust notes operators need.
  - Source checkout / `just dev` contributor path.
- **Cuts / merge:**
  - Install block and “New here?” path largely duplicate `QUICKSTART.md`. Keep a one-line install + hard link to QUICKSTART for Postgres and first DB prepare; do not re-teach `ensure-db` here.
  - Optional later: Codex CA merge detail is accurate today but high-churn; if it moves again, prefer “see doctor / CHANNELS” over re-specifying bundle paths in README.
- **Not MERGE into QUICKSTART:** audiences differ (marketing/operator overview vs four-step bootstrap). Duplication is the install/quick-start overlap only.

---

### QUICKSTART.md (102 lines)

- **Disposition:** KEEP AS IS.
- **Survives:** install → Postgres options → `channel ensure-db` / manual `db upgrade` → run; env table; fail-closed on unreachable Postgres; pointer to CHANNELS for `dev`.
- **Cuts:** none required under this lens. Procedure that matches CLI commands is guide material; invalidation would be a user-facing CLI rename, which deserves a doc touch.
- **Note:** install curl matches README; that is acceptable one-line duplication for a standalone bootstrap path.

---

### NOW.md (496 lines)

- **Disposition:** TRIM to ~280–320 lines. Self-stated rule: “Merged work leaves this file.” Shipped sections currently violate it.
- **Survives:**
  - North Star pointer and multi-launch destination framing.
  - Phase 1 open work: governing rule 1.1 (symlink vs broker axis), 1.3 login driver seam (gateway sibling PTY, not `POST /v1/runs`), 1.5 pre-launch credential readiness, first-frame baseline / stage 2 mechanism, “expect iterations”.
  - Phases 2–5 open items with symbols (`launch_ledger`, delivery unlink-on-claim, `launch_batch`, close filters, gateway-per-pane, shared proxy pool).
  - Deferred list with re-entry triggers (highest value: wire store read surface, hosted matrix, harness settings).
  - Parking lot / chores that still guide not-now decisions.
- **Cuts:**
  - **§1.2 SHIPPED (#352)** long write-up: replace with one line (“credential source dispatch shipped; gate uses that predicate”) or delete; details live in code + ARCHITECTURE credential isolation.
  - **§1.4 slices 1a/1b shipped (#353/#354)** narrative: same treatment. Keep the converged product rule in one sentence if still load-bearing: fail open on visibility, fail closed on action; first run is settings, not a wizard (`?firstrun=1` retired). Drop harness-card implementation archaeology.
  - Binary version pin “2.1.220” and long login transcript inside 1.1/1.3: version pins rot; keep the rule and the decided seam, not the capture diary.
  - Wire-store dark paragraph under Product direction duplicates TLDR/ARCHITECTURE; one trigger line is enough.
  - `#345` landed prose under “launch seam already exists” can shrink to a pointer at `LAUNCH-CONTRACT.md` + symbols without PR storytelling.
- **Does not DELETE the file:** it is the current-focus anchor TLDR points at; empty parking lots mislead less than missing north-star context.

---

### docs/CHANNELS.md (242 lines)

- **Disposition:** KEEP AS IS (reference). Light future trim only for proven one-time residue.
- **Survives:**
  - Channel table and purpose/reset posture.
  - Isolation boundary table (home, DB, ports, Electron id).
  - `channel list` / `stop` / `ensure-db`, `just reset` postures, what reset does not touch.
  - Dev harness isolation (strip inherited env) and explicit alternate DB recipe.
  - Pytest namespace ownership policy (safety-critical for agents running tests/resets).
- **Specification vs reference:** yes, it is detailed and code-like. That is appropriate for channel state boundaries: wrong home or wrong reset is destructive. Better one reference with tables than agents inventing paths. Code (`ChannelSpec`) remains authority; doc is the operator map.
- **Cuts later (not blocking):**
  - “One time legacy cleanup” commands for old Electron profiles once residue is gone from real machines.
  - Storage override warning section if the warning path is removed from code.
- **Not MERGE into README:** too long; README already points operators who need multi-channel detail here via contributor/dev paths. QUICKSTART already links it for `dev`.

---

## Cross-doc duplication map

| Claim | Homes today | Preferred home after sweep |
| --- | --- | --- |
| Install curl / uv tool | README, QUICKSTART | QUICKSTART; README one-liner + link |
| Postgres + ensure-db | QUICKSTART, CHANNELS (dev), README (source) | QUICKSTART + CHANNELS for channel-specific |
| Non-invasive install | TLDR, README, NOW (matrix prose) | README only |
| Channel isolation table | TLDR (prose), CHANNELS | CHANNELS; TLDR one sentence + link |
| Dark wire store / #259 | TLDR, NOW deferred | TLDR one durable sentence; NOW trigger only |
| Canvas run lifecycle / routes | TLDR (over-specified), CONTROLPLANE, ARCHITECTURE | ARCHITECTURE + CONTROLPLANE; TLDR marker |
| Space / Worktree / Canvas | TLDR fence only (root) | TLDR prose + `packages/space` |
| Multi-launch north star | NOW, NORTHSTAR | NOW pointer + NORTHSTAR full vision |

---

## Priority order if a human edits next

1. Replace `TLDR.md` with the proposed text (highest token ROI; symlinked agent context).
2. Strip SHIPPED Phase 1 narratives from `NOW.md` per self-rule.
3. Collapse README install/quick-start into a link to QUICKSTART.
4. Leave QUICKSTART and CHANNELS alone unless legacy cleanup is known done.

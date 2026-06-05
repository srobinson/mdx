---
title: Transport Matters channels — DESIGN/UX + isolation-model brainstorm
type: brainstorm
tags: [transport-matters, channels, isolation, desktop, electron, dogfood]
summary: Adopt browser-style release channels (stable/canary, +optional beta); derive every isolation dimension from one channel id, mostly free via the existing storage-root cascade.
status: active
source: codebase-analyst (independent MoE voice)
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

# Channels for side-by-side dogfooding — one voice's recommendation

**Recommendation in one line:** copy the pattern that already solved this exact
problem — **browser release channels**. Run **`stable`** (the daily driver) next
to **`canary`** (the working-tree build), with **`beta`** as an optional soak
rung. A single `--channel <id>` derives every isolation knob; the storage root
already cascades into most of them.

## (a) Channel taxonomy — and why not preview/staging

Three rungs, but only two normally resident:

| Channel | Role | Code behind it | Badge |
|---|---|---|---|
| `stable` | the app Stuart works in daily (instance A) | installed wheel from a tagged build | quiet — slate dot, no shout |
| `beta` | optional dogfood soak before blessing | a promoted canary, frozen | violet pill `BETA` |
| `canary` | the in-dev instance (instance B) | rebuilt from the working tree / current branch | amber pill `CANARY` |

Common case is `stable` + `canary`; `beta` only exists when Stuart wants a soak
period before promotion. **Loudness scales with danger:** the instance most
likely to break shouts, the one that holds real history whispers.

**Defending this over Stuart's `preview`/`staging` lean:**
- This is *literally* the Chrome/Firefox/VS Code-Insiders problem: two installs
  of one app, side by side, distinct dock icons, a promotion direction everyone
  already understands. Borrowing the vocabulary means zero learning curve and a
  ready-made color convention (canary = amber/caution).
- `staging` is the word that will bite. Everywhere else it means a *pre-prod
  environment*, not "the app I use every day." Calling the daily driver
  `staging` inverts the convention. `stable` says exactly what it is.
- `preview` is softer than reality — a preview is a read-only glance; instance B
  is a fully live, prompt-it-for-real instance. `canary` carries the "expect
  breakage, it warns you first" semantics `preview` lacks.
- If Stuart wants his words anyway: keep `release`→`stable`, rename
  `preview`→the canary role, and **drop `staging`** (the ambiguous one). The
  ladder, badges, and isolation are unchanged; only the labels move.

## (b) Title-bar badge — and how identity threads through

The window badge alone is not enough, because it vanishes on minimize/⌘-Tab. So
identity lives in **two surfaces fed by one source**:

1. **Native (dock / ⌘-Tab):** Electron `app.setName("Transport Matters Canary")`
   + a per-channel tinted dock icon. This is what disambiguates when the window
   isn't focused — today entirely missing (`app.setName`/`setPath` are never
   called; window title is the hardcoded `APP_NAME`).
2. **In-window pill (`www` WindowDragRegion):** a colored channel pill in the
   recreated title-bar strip, for the focused case.

**Threading from one knob:**
`--channel` / `TRANSPORT_MATTERS_CHANNEL` → a pure `resolve_channel(id)` →
Electron `main` calls `app.setName()` + `app.setPath('userData', …)` + dock icon
**before app-ready**, and forwards the channel in the backend env (the
`TRANSPORT_MATTERS_*` block in `desktop/src/env.ts` is the existing seam) →
backend adds `channel`/`label`/`color` to `GET /api/meta` (meta.py already serves
CWD) → WindowDragRegion reads `/api/meta` and paints the pill. `stable` gets no
loud pill; only the off-daily channels shout.

## (c) Isolation model — derive everything from `c`

The strong finding: **the storage root already cascades.** `TRANSPORT_MATTERS_HOME`
drives tier-1, the per-run dirs, *and* the shared-proxy control socket
(`_control_socket_path(runtime_dir)` in `shared_proxy/manager.py`, sha256 of the
runtime dir). Point one knob at a per-channel root and the lock/socket/run
surface isolates for free. Only three dimensions need their own derivation:

| Dimension | Today | Per-channel from `c` |
|---|---|---|
| Storage root (→ tier-1, runs, proxy socket) | `~/.transport-matters/` via `TRANSPORT_MATTERS_HOME` | `stable` keeps the canonical path; others `~/.transport-matters@<c>/` (sibling, so the daily driver stays byte-identical, zero back-compat risk) |
| Web port | 8788 via `TRANSPORT_MATTERS_WEB_PORT` | `8788 + 10·offset(c)` → stable 8788, canary 8798, beta 8808 |
| Proxy port | 8787 via `TRANSPORT_MATTERS_PROXY_PORT` | `8787 + 10·offset(c)` (paired block of 10 leaves headroom) |
| Postgres DB | one DSN via `TRANSPORT_MATTERS_DATABASE_URL` | same server/role, derived dbname `tm_<c>` |
| Electron userData | default `…/transport-matters-desktop` | `app.setPath('userData', …-<c>)` |
| App/dock identity | hardcoded "Transport Matters" | `app.setName` + tinted icon per `c` |

**DRY the derivation:** the offset/color/dbname table must live in **one**
committed file (a tiny `channels.toml` shipped in the wheel) that both `config.py`
and `env.ts` read — never re-encode the port math in two languages.

## Scripted path + promotion ladder (one command per hop)
- `tm-channel up canary` — build wheel from working tree → ensure `tm_canary` DB
  + migrations → set channel env → (re)launch desktop. Idempotent (tears down the
  prior canary first). Plus `down` / `restart`.
- `tm-channel promote canary beta`, `promote beta stable` — moves the **code
  artifact**, not the session DB. Stable's captured history is sacred and never
  promoted over; `--with-data` only if ever wanted.

## Trade-offs + the one thing that bites
- Per-channel DB on one server (recommended) keeps setup trivial and isolates a
  bad canary migration from stable's data; the shared server process is the only
  coupling (low risk single-user).
- Sibling storage dirs vs a `channels/<c>/` subtree: sibling keeps `stable`
  exactly where it is today (no migration for the daily driver) at the cost of a
  slightly busier home dir. Worth it.

**The bite:** ports and dirs derive locally for free, but the **Postgres DB is
the one dimension that must be *created and migrated* before launch.** If
`tm_canary` is missing or on an old schema, the channel face-plants on exactly
the two preflight guards from NOW.md (`preflight_session_store_or_exit`,
`RunManager._ensure_session_store_available`). So `tm-channel up` **must**
createdb + migrate as a step — and this couples directly to the no-DB / store-
picker work. Get that one step wrong and the preview instance won't boot.

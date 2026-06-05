# Transport Matters — Launcher UI: the ⌘K command center

Date: 2026-06-18
Status: DESIGN LOCKED (visual brainstorm w/ Stuart, approved). Ready to spec into slices.
Owner: Stuart (what/why), Claude (how)
Lens: `~/.mdx/projects/transport-matters-north-star.md` — this surface is **client #1 of the
control plane's Launch verb**. Everything here is the human adapter onto operations the
director also drives over MCP.
Complements: `~/.mdx/projects/tm-launcher-design.md` (the data-model: provider→model→agent,
`capabilities.json`; this doc is the frontend-design pass that one deferred) ·
`~/.mdx/projects/tm-ui-component-strategy.md` (Ark UI headless layer) · cm decisions
(`command-center`, `agent-first launcher`, `zero-chrome`, `provider-taxonomy`).

---

## Charter

Replace the "nasty" always-visible canvas command bar with a keyboard-first **⌘K command
center**. The desktop canvas goes **zero-chrome**: you watch agents work; you control the
fabric by keyboard (and, much later, by voice→director). The launcher is **agent-first and
recommendation-default**: 99% of launches are "pick an agent, hit enter," with model/effort
overrides as progressive disclosure for the eval path.

Scope is the UI adapter (`www/src/session-canvas/`). Out of scope: voice, the director,
eval mode internals, and the non-Agents scopes' deep internals (named, deferred).

## Surface

- **Zero chrome.** No persistent button row, no top strip. A faint, fading first-run ⌘K
  hint softens discoverability; nothing permanent.
- **⌘K** opens the root command center.
- **⌘A** jumps straight into the Agents scope (the launcher) — the 99% action gets one key.

## Command center

**Root (⌘K)** is organized by **domain**, where each domain is a face of the same control
plane the director drives over MCP:

| Domain | Control-plane verb | Contents | Accelerator |
|---|---|---|---|
| Agents | **Launch** | spawn & configure runs | ⌘A |
| Canvas | **Manage / Observe** | panes, layout, focus/close, navigation (e.g. Go to Lab), Reset view | — |
| Workdir | Launch placement | set where agents run | — |
| Settings | manage-agents (curation context) | homes, skills, defaults, overlays, plan | ⌘, (later) |
| Sessions | **Observe** | browse transcript history | — |

**Root behavior:** flat-searchable across all domains **and** domains are enterable scopes
(Raycast model). A power user types "research" from cold and spawns without entering a
scope; a browser enters Agents and arrows through.

**Navigation grammar (global):**
- `↵` enters a scope (from root) / triggers the highlighted item.
- `⌫` on an empty query, or `←`, pops scope → root.
- `Esc` closes the palette.
- Accelerators (⌘A, ⌘, …) jump straight into a scope from anywhere.

## The Agents scope (the launcher)

Reached by ⌘A or by entering Agents from root. **Agent-first, recommendation-default.**

**Row model.** One row per agent; the subtitle shows its recommended target, e.g.
`research · Opus 4.8 · xhigh · Claude`. Native is always present.

**Grammar inside Agents:**
- `↵` — spawn the highlighted agent with its **recommended target** (the one-action path).
- `→` — expand the highlighted row into its **override config** (the eval / non-default path).
- `←` / `⌫` — collapse / back to root.

**Override config (via `→`).** Editable fields, defaults pre-filled from the agent:
harness · vendor · model · effort. The **vendor row collapses to one option** when the
harness is single-vendor (Claude → Anthropic); opencode/pi surface a real vendor choice.
"Defaults come from the agent; touch these only for evals."

**States (the robustness contract — Native is always present and spawnable):**
- **Populated:** agents listed with recommended-target subtitles, then (in root) other domains.
- **Loading:** Native is live immediately; specialist rows fill in (skeletons) as the list resolves.
- **Empty (no fleet on disk):** Native only, a quiet "install a fleet to add specialists" line.
  Exactly today's one-click behavior.
- **Error (fleet fetch failed):** degrade to Native-only + a quiet retry chip. A list fetch
  **never** blocks a launch.

## Data dependencies

- **Reads** `recommended_model.default` (pre-select harness+vendor) and
  `recommended_model.by_vendor[vendor]` (model+effort) from each agent's `capabilities.json`.
  **Pending** the `provider-taxonomy` schema-2 bump (harness/vendor split), out to
  agent-runtimes on bus topic `tm-launcher-proposal`. Until it lands, the palette reads the
  current shape and the override fields stay minimal.
- **`GET /v1/runtime-templates`** — the list endpoint the Agents scope enumerates. Builds
  **with** its consumer (no premature endpoint); returns name + recommended target +
  capability/vendor compat for display + filter.
- **`CreateRunRequest`** (`api/.../api/v1/run_routes.py`) extends with the managed launch
  fields: harness/vendor/model/effort + placement. Absent selection → NATIVE (today's
  behavior, byte-for-byte). This is the **Launch** verb the director also calls.

## Build order (v1)

1. **RouteSwitcher → Ark `Menu`** — the de-risking pilot (tm-ui-component-strategy.md step 1):
   proves Ark + vanilla-CSS `data-part` styling + Electron portal behavior on the lowest-risk widget.
2. **Agents scope (⌘A + the launcher)** — agent-first list, recommended-target rows,
   `↵` spawn / `→` configure, the four states, Native-always invariant. Ark `combobox`/`listbox`.
   Threads selection → `CreateRunRequest` (the Launch API). This is the load-bearing slice.
3. **Root command-center shell** — ⌘K, domain list, flat-search across domains, scope nav grammar.
4. **Remaining scopes** — Canvas, Settings, Workdir, Sessions fill in (each its own slice; some
   wrap existing surfaces, e.g. Settings = the manage-agents context, Sessions = the shipped
   transcript browse).

## Deferred / out of scope (named, not dropped)

- Voice intake and the director (north-star; much later).
- Eval mode (compare agents across model/effort/vendor) — the override config is the seam it
  will grow from; not built now.
- Deep internals of Workdir/Settings/Sessions scopes beyond wiring them into the command center.

## Open items

- Confirm the v1 **domain set** (Agents/Workdir/Canvas/Settings/Sessions) and the "etc."
- Root flat-search ranking (recency, fuzzy) — tune during the build.
- Whether Settings gets ⌘, in v1 or trails.

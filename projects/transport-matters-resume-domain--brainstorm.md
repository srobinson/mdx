---
title: Transport Matters — Spaces Slice 7 (Resume) — Domain + Scope Brainstorm
type: research
tags: [transport-matters, spaces, slice7, resume, domain, scope, brainstorm]
summary: Recommend Slice 7 = narrow native-resume-on-reopen whose true spine is session-home reconstitution from the owned Tier-1 transcript, not UI. The resume launch machinery already exists (LaunchProfile mints+injects native_session_id); continuation/resume-card/MCP are a later iteration whose substrate (purpose/visibility schema, lineage columns) already quietly shipped.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-22
updated: 2026-06-22
---

# Spaces Slice 7 (Resume) — Domain + Scope Brainstorm

**Author:** `transport-matters:helioy-tools:codebase-analyst:1:4.1`
**Mode:** Warroom brainstorm — divergent. Options + a recommendation, not a single answer.
**Angle:** DOMAIN + SCOPE (the other analyst owns identity/persistence/feasibility).
**Method:** read the two seed docs, then verified every code claim against `main` (slices 1-6 merged). File::symbol evidence inline. The seed docs both predate the substrate that has since landed; the corrections below are the load-bearing part of this brainstorm.

---

## Executive summary

Slice 7 as written ("reopen a captured-run pane → resume the agent") is the **right narrow scope**, but its centre of gravity is **not the UI and not the launch flag** — both of those already exist. The launch layer already mints and injects the session id and already knows how to pass `--resume`/`resume` (`launch_profile.py`). The genuinely missing, genuinely hard piece is **making a dead run's session home replayable after a desktop quit** — reconstituting the harness's on-disk session from TM's owned Tier-1 transcript copy. Everything else in Slice 7 hangs off that.

The broader "resume/session model" from the older notes (startup screen, resume card, continuation routes, MCP tools, summary) is **mostly substrate-complete now** (the schema and lineage columns it was blocked on have shipped) but is a **separate, later epic**, not Slice 7. Folding it in would conflate *resume* (same thread) with *continue/fork* (new lineage) and balloon a PR-sized slice into an epic.

**Headline recommendation:** Slice 7 = **native-resume-on-reopen, scoped around session-home durability**, shipping the **Reattach / Resume / View** verb triad on pane reopen. **Internal continuation ("Continue/Fork") is explicitly deferred** to the next iteration, where its substrate already waits.

---

## Verified state — what changed since the seed docs (read this first)

Both seed docs are stale on the substrate. The proposal (2026-06-21) wrote the Slice 7 note *before* the launch/schema work landed; the resume notes (`tm-notes-remaining-resume.md`, 2026-06-15) predate Spaces entirely. Verified against `main`:

| Claim in a seed doc | Verified reality on `main` | Why it matters for scope |
|---|---|---|
| "`native_session_id` = the harness's own session id to pass to `--resume`" (proposal) | **TM MINTS it** (`launch_profile.py:244`, `uuid4`) and **injects** it: Claude `--session-id <id>`, Codex `resume <id>` (Codex pre-seeds its `session_meta` rollout so the id resolves). Bound back via adapter (`ingest.py:86`). | Resume needs **no post-hoc discovery** of the harness id. TM assigned it. This de-risks the whole feature and is the strongest argument that "TM can guarantee resume." |
| Harness-neutral seam is unbuilt; "do not spec the strategy now" (proposal) | **`LaunchProfile` ABC already exists** (`launch_profile.py:66-110`): class vars `harness`, `mints_session_id`; methods `prepare()`, `client_argv()`, `user_supplied_session()`; registry `HARNESSES: dict[str, LaunchProfile]`; subclasses `ClaudeLaunchProfile`/`CodexLaunchProfile`. | The seam is not greenfield. Slice 7 **extends** this ABC; it does not invent a parallel seam. The shape question (deliverable 3) is largely answered by what shipped. |
| `--resume`/`resume` plumbing planned/absent | **Functional today**: `CodexLaunchProfile.client_argv` injects `["resume", native_session_id]`; user `--resume`/`-r`/`--continue`/`-c` passthrough detected via `_CLAUDE_SESSION_FLAGS` and honored (`user_supplied_session`). | The launch *flag* is not the work. The reopen *orchestration* + *home survival* is. |
| Dependency 0: `session_purpose`/`session_visibility` ABSENT, blocks continuation (notes) | **SHIPPED** — migration `0004_session_purpose_visibility.py`; enums `SessionPurpose`/`SessionVisibility` on `SessionRow`; written (`ingest.py:91-92`); defaults `user`/`user_visible`. | The continuation type's hardest blocker is gone. Continuation is now cheap-ish — which is *more* reason to keep it as its own slice, not cram it into 7. |
| `parent_session_id`/`forked_at_seq` lineage | PRESENT and **written**; CHECK enforces both-null-or-both-set (`0001` migration). | The continuation anchor is real and exercised. Native resume does not touch it. |
| Runs survive? | **No.** `RunManager` is process-resident (dict keyed by `run_id`), **no DB persistence of run state**, scrollback ring + replay-on-attach only (`run_manager.py`). Runs die on API restart/quit. | This is the spine. A cold reopen has nothing to replay unless the session home is reconstituted. |
| captured-run pane `sessionId` | Optional, **persisted, never populated** today (`paneRecords.ts:114`, comment "populated on session-bind in Slice 7"). `worktreeId` required. `Canvas.defaultWorktreeId` present. | The viewer↔session link is the small, safe half of Slice 7. |
| `/api/v2/*`, `continuationId`, `resume-context.json` | **ABSENT.** API is `/api/v1` only. | The old notes' route shapes are obsolete naming. Anything new follows `/v1/` (locked decision). |
| `runtimeTemplate?` on captured-run pane | PRESENT (optional). | This is the wire that should carry "which profile to re-launch with" on resume. Reconcile it with `HARNESSES`. |

**Net:** the proposal's instinct ("anchors are in place, defer strategy") is right, but the anchors are further along than it knew. The real Slice-7 unknown is durability, not plumbing.

---

## Deliverable 1 — SCOPE (the key fork)

Three scoping options, minimal → full. The fork is **"reopen→re-spawn one session" vs "the whole resume/session model."**

### Option A — *Reopen-as-resume, hot-path only* (minimal)
Wire pane reopen to the **existing** resume machinery and populate the pane `sessionId`. Solve durability only for the easy case (run still alive → reattach; recently-dead → resume if the home happens to still exist). No new durability guarantee.
- **In:** session-bind populates `captured-run.sessionId` (`RunViewModel.session_id` → pane); reopen of a still-live run reattaches (already shipped); reopen of a cold pane attempts resume via `LaunchProfile`.
- **Out:** home reconstitution, continuation, resume card, startup rework.
- **Trade-off:** Ships fast but is **a lie under the headline use case** (quit the desktop, come back tomorrow → nothing to resume because the home is gone). Demos well, fails the actual "pick up where I left off" promise. **Reject as the slice; keep as the trivial first PR within B.**

### Option B — *Native-resume-on-reopen, durability-first* (RECOMMENDED)
Option A **plus** the load-bearing piece: **reconstitute the harness session home from the owned Tier-1 transcript** before re-spawn, so resume works after a quit. Ship the reopen UX that distinguishes the three live verbs (Reattach / Resume / View). **No** continuation, **no** resume card with lineage badges, **no** MCP tools, **no** startup-screen rework.
- **In:** (1) home-reconstitution capability on `LaunchProfile` (per-harness, behind the ABC); (2) `sessionId` bind on the pane; (3) reopen affordance offering Resume vs View when a run is cold, Reattach when hot; (4) the durability dependency the proposal flagged, made the spine.
- **Out:** everything continuation/lineage/discovery-UI.
- **Trade-off:** Bigger than A, but it is the **smallest slice that makes the headline true**. Stays PR-shaped if continuation is excluded. Matches the proposal's literal Slice 7 and the "iteration not v1/v2" discipline.

### Option C — *Resume + session model, one epic* (full)
Slice 7 absorbs the broad feature: continuation routes (`POST .../continuations`), resume card (`currentTurnCount`/`inheritedForkTurnCount`/`lineageBadge`), preview-only transcript mode, continuation-linked runs (`continuationId` on create), backend canvas-layout store, MCP resume tools, capture summary.
- **Trade-off:** Now that Dependency-0 schema shipped, this is **credible as a NEXT epic** and cheaper than the old notes assumed — but it is **not one slice**. It mixes two mental models (resume vs fork) and at least six PR-sized surfaces. **Reject for Slice 7; recommend as the named follow-on epic** ("Session Model / Continuation"), seeded by Slice 7's verbs.

### Recommendation
**Option B.** Slice 7 is native resume on reopen, with **session-home reconstitution from Tier-1 as the spine** and the **Reattach/Resume/View** triad as the surface. Internal continuation is the first task of the *next* iteration, not Slice 7. This keeps the slice PR-sized, makes the headline promise real, and respects that the launch flag and schema are already done.

---

## Deliverable 2 — the two resume types + reopen UX

The proposal names two types. The verified mechanics let me sharpen them and add the verb that the proposal omitted (**Reattach**), which is the most common case and the one already shipped.

### The two declared types
1. **Native resume** — re-spawn the **same** session: same `native_session_id`, same worktree cwd. The provider API is stateless, so this is a **local transcript replay** — the harness rebuilds context from its on-disk session home. Because TM *minted and injected* that id and *owns* the Tier-1 transcript, TM can reconstruct the home deterministically. This is the "same thread, picked up later" model. **Belongs in Slice 7.**
2. **Internal continuation** — spawn a **new** session with `parent_session_id = X` + `forked_at_seq`, marked `session_purpose = continuation`. A fresh agent that can *read* session X. This is **branching/lineage**, not the same process. Different mental model, different UI (lineage badges, fork-point), different write path (continuation route). **Belongs in the next iteration** (its schema already shipped).

### The verb that was missing — Reattach
There are **three** reopen outcomes, not two, because a run can still be alive:
- **Reattach** — the run is **hot** (process-resident, not killed; e.g. minimized-to-dock). The viewer rejoins; scrollback replays from the ring (`run_manager.attach`). **No resume, no new process. Already shipped.**
- **Resume** — the run is **cold** (died on quit). Re-spawn the same `native_session_id` after reconstituting the home. *This is the new Slice-7 work.*
- **View / Open transcript** — render the Tier-1 transcript read-only (`TranscriptChatPane`, `session-timeline`). No process. **Always available, safest fallback, already shipped substrate.**
- *(later)* **Continue / Fork** — new lineage child. Next iteration.

### Reopen UX (recommended)
On reopening a `captured-run` pane (or restoring a Canvas that contains one), TM **infers state, then offers intent**:

```
  reopen captured-run pane
        │
        ├─ run hot?  ──► REATTACH (silent; viewer rejoins, scrollback replays)
        │
        └─ run cold ──► show pane chrome:  [ Resume ]   [ View transcript ]   ( Continue ⟶ later )
                          │                     │
                  home reconstitutable?     always available
                    yes → Resume primary    (Tier-1 owned)
                    no  → Resume disabled +
                          "View transcript" primary,
                          tooltip names the missing home
```

- **Default safe action is View** when resume is not guaranteed; **Resume is primary** only when the home is reconstitutable. Never silently resume on restore (surprising side effects, cost, divergent context).
- The distinction must surface in **language**, not just behavior: a cold captured-run pane is visibly "cold," and Resume vs View is an explicit choice. Conflating them ("just reopen and it does something") is the failure mode to avoid.

---

## Deliverable 3 — the harness-neutral seam (SHAPE, not per-harness strategy)

The seam **already exists** as `LaunchProfile`. The recommendation is **extend it, do not build a parallel seam.** Per the proposal, the *per-harness strategy* (which flag, where the home lives, how to seed a rollout) stays **inside** each subclass and is **not specced now**. Only the *shape* of the contract is specced.

### Existing contract (verified)
```
LaunchProfile (ABC)              HARNESSES: dict[str, LaunchProfile]
  harness: str                     "claude" -> ClaudeLaunchProfile(mints_session_id=True)
  mints_session_id: bool           "codex"  -> CodexLaunchProfile(mints_session_id=False)
  prepare(...)
  client_argv(...)                 # Claude: --session-id <id> ; Codex: resume <id>
  user_supplied_session(...)       # honors user --resume/-r/--continue/-c passthrough
```

### Slice-7 additions (shape only)
1. **A resume capability predicate** — e.g. `supports_resume: bool` class var. Not every harness will. Keeps the orchestrator from assuming.
2. **Resume = spawn-with-a-fixed-prior-id.** The elegant observation: the profile *already* injects a *given* id. Resume is the same launch with `mints_session_id` semantics flipped to "reuse this id" instead of "mint a new one." So the seam may need **no new argv method** — generalize the existing id-injection path to accept a *prior* id (resume mode) rather than a fresh mint. Worst case, a thin `resume_argv(native_session_id, cwd)` that the subclass implements.
3. **A home-reconstitution capability** — e.g. `reconstitute_home(native_session_id, tier1_seed, target_home) -> bool`. Per-harness because Claude's session home layout ≠ Codex's rollout. The orchestrator calls this **before** re-spawn and stays harness-agnostic. *This is the new, genuinely per-harness work and the part the proposal said not to over-specify — correct, but the method's existence is the seam contract.*
4. **The pane's `runtimeTemplate?` resolves to a `HARNESSES` entry.** Today there are two parallel "which harness" concepts: the pane-side `runtimeTemplate?` string and the api-side `LaunchProfile`/`HARNESSES`. **Reconcile them** so reopen knows which profile to re-launch with from the persisted pane alone. This is a domain-coherence point, not a strategy.

### The orchestrator's view (harness-blind)
> "Profile for `runtimeTemplate`, ensure the home for `native_session_id` exists from its Tier-1 seed, then resume it at `worktreeId`'s cwd."

Adding a third harness = one new `LaunchProfile` subclass + a `HARNESSES` entry. No orchestrator change. That is the test the seam must pass, and the existing seam nearly already does.

---

## Deliverable 4 — Ubiquitous language + lineage anchors

### Anchors (verified locations + the correction)
| Anchor | Verified | Domain role |
|---|---|---|
| `native_session_id` | TM-**minted** `uuid4`, injected, bound back (`launch_profile.py:244`, `ingest.py:86`) | **The resume key.** *Correction:* it is TM-originated, not "the harness's own id." Resume = relaunch with this prior id. |
| `parent_session_id` / `forked_at_seq` | written; CHECK-paired (`0001`) | **The continuation anchor.** Not used by native resume. |
| captured-run pane `sessionId?` | persisted, unpopulated (`paneRecords.ts:114`) | **The viewer↔session link.** Slice 7 populates it on session-bind. |
| `worktreeId` (required on captured-run pane) | `paneRecords.ts` | **The placement anchor** — the cwd root the resumed run re-enters. |
| `session_purpose` (`user`/`continuation`/`internal_*`) + `session_visibility` | shipped (`0004`) | **Classification.** `continuation` marks the second resume type. Native resume keeps `user`. |
| `runtimeTemplate?` (pane) ↔ `harness` (`SessionRow`) ↔ `HARNESSES` | `paneRecords.ts`, `launch_profile.py` | **The harness anchor** for "which profile to re-spawn with." Three names for one concept — reconcile. |
| Tier-1 transcript copy | `~/.transport-matters/workspaces/{slug}/{hash}/{run}/` | **The restore seed** for home reconstitution. |

### Proposed product verbs (the domain contribution)
Resume is overloaded in casual speech; the product needs **four distinct verbs** so users and code never conflate same-thread, new-thread, rejoin, and read:

- **Reattach** — viewer rejoins a **live** run. (Already the dock/restore behavior. Not resume.)
- **Resume** — re-spawn the **same** session (`native_session_id`) after it died; local transcript replay. (Slice 7.)
- **Continue** — new session, `parent_session_id` set, `purpose=continuation`. Product verb for the lineage type. (Next iteration. Internal mechanism noun: *fork*, matching `forked_at_seq`.)
- **View** (or **Open transcript**) — read-only render. Always available.

Supporting nouns:
- **Cold pane / cold run** — a captured-run pane whose process has died and needs Resume-or-View. Opposite: **hot**/live.
- **Session home** — the harness's own on-disk session dir (Claude config home, Codex rollout). The thing that must survive a quit.
- **Reconstitute** — rebuild the session home from the Tier-1 restore seed so Resume has something to replay. Internal verb.

Avoid: "restart" (implies fresh, loses context), "reload" (ambiguous), and using "resume" for the continuation type (it is a *fork*, not the same thread).

---

## Overlap reconciliation with the older resume notes

`tm-notes-remaining-resume.md` (2026-06-15) audited a broad resume/session feature. Post-Spaces, here is what is **obsolete**, **superseded**, and **still relevant**:

- **Obsolete naming:** `/api/v2/*` everywhere → the API is `/api/v1` (locked). Any new route follows `/v1/`.
- **Dependency 0 (schema) — DONE:** `session_purpose`/`session_visibility` shipped (`0004`). The note's "hard blocker" is cleared; this is why continuation is now cheaper and belongs in its own slice rather than being perpetually blocked.
- **S1 startup screen — SUPERSEDED by Spaces:** "left column = recent working dirs, right = sessions for the selected dir" is now the **Space → Worktree launcher** (⌘K, slice 6). Do not rebuild a separate startup screen; the resume entry point is *reopening a captured-run pane / Canvas*, which Spaces already gives. The note's S1 is mostly absorbed.
- **S2 resume card — still relevant, but NEXT epic:** `currentTurnCount`/`inheritedForkTurnCount`/`lineageBadge` are real gaps, but they serve **Continue** (lineage display), not native Resume. Defer with continuation.
- **S3 preview-only mode — still relevant, NEXT epic:** `TranscriptChatPane` exists; preview-only interaction does not. Useful for orientation before Continue. Not needed for Resume (View suffices).
- **S4 continuation route — still relevant, NEXT epic, now unblocked.** The core of the second resume type.
- **S5 continuation-linked run / `continuationId` / `resume-context.json` — NEXT epic.** Tied to S4.
- **S6 backend canvas-layout store — orthogonal.** Canvas is still client-only (zustand/localStorage); the locked Spaces decision keeps localStorage as the cache and the server as a *sync target*, so a backend layout store is a Spaces follow-on, not resume.
- **MCP resume tools + capture summary — out of scope, parked.** Unchanged.

**One-line:** the old broad feature's *foundation* quietly shipped inside Spaces; its *surfaces* remain unbuilt and regroup cleanly into a "Session Model / Continuation" epic that **follows** Slice 7.

---

## Open questions / risks (ranked) — for whoever plans Slice 7

1. **(Spine) Session-home durability across quit.** Where does each harness keep its session home, is it ephemeral, and can it be reconstituted from the Tier-1 transcript? This is the make-or-break dependency and the bulk of the per-harness work. If a home cannot be reconstituted for a harness, Resume degrades to View for that harness (acceptable, must be explicit).
2. **Resume-vs-keep-alive fork.** An alternative to resume-from-cold is **run durability** (daemonize the run so it survives quit). That is a *different, harder* feature (orphaned PTYs, proxies, ports; `RunManager` would need DB-backed state). Recommend **explicitly rejecting it for Slice 7**: native resume is cheaper and leverages the transcript TM already owns. Worth a one-line non-goal so it is not relitigated.
3. **Codex `resume <id>` semantics on a reconstituted home.** TM pre-seeds the Codex rollout at first launch; on resume the rollout must already reflect the replayed turns. Confirm Codex `resume` against a TM-reconstituted rollout actually replays (vs starting empty). Per-harness detail, but the riskiest one.
4. **`runtimeTemplate` ↔ `LaunchProfile` ↔ `harness` reconciliation.** Three names; resume needs one resolvable path from the persisted pane to a profile. Cheap to fix, must be done before reopen can pick the right profile.
5. **Worktree gone at resume.** The pane's `worktreeId` may point at a deleted/missing worktree (Spaces allows it: `missing=true`). Resume must handle "cwd no longer exists" — block with a clear message, do not silently resume into the wrong dir.
6. **Idempotency / double-resume.** Reopening the same Canvas twice must not spawn two live runs for one `native_session_id`. Reattach-if-hot guards this, but the cold→resume path needs a single-flight check.

---

## Recommendation (one line for the orchestrator)

**Slice 7 = native-resume-on-reopen scoped around session-home reconstitution from the owned Tier-1 transcript, shipping the Reattach/Resume/View verb triad; the launch flag and lineage/classification schema already exist, so internal continuation ("Continue/Fork") and the resume-card/MCP surfaces are the next iteration, not Slice 7.**

---

*Evidence files (verified on `main`): `api/src/transport_matters/cli/launch_profile.py` (LaunchProfile/HARNESSES, native_session_id mint+inject, resume flags), `api/src/transport_matters/session/{models.py,ingest.py}` + migrations `0001`,`0004` (anchors + purpose/visibility), `api/src/transport_matters/run_manager.py` (process-resident runs, scrollback), `api/src/transport_matters/captured_run.py` (prepare_captured_run), `www/src/session-canvas/model/paneRecords.ts` (PaneContentRef, captured-run sessionId?/worktreeId, Canvas.defaultWorktreeId, runtimeTemplate?). Seed docs: `transport-matters-spaces--proposal.md` §"Native resume on reopen", `tm-notes-remaining-resume.md` (stale 2026-06-15), `transport-matters-spaces--plan.md` (Slice 7 deferral).*

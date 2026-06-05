# Transport Matters — Spaces / Canvas / Worktree (brainstorm proposal)

Date: 2026-06-21
Mode: Warroom brainstorm (Mode 4), orchestrator synthesis.
Inputs: two independent proposals, written without coordination —
- Claude `codebase-analyst` (domain / naming / UX lens): `transport-matters-spaces-domain--brainstorm.md`
- Codex `backend-engineer` (identity / persistence / feasibility lens): `transport-matters-spaces-feasibility--brainstorm.md`

The two agents reached the **same core model from opposite ends**. That convergence is the
high-confidence spine below. Where they diverge are the real decisions left for Stuart.

---

## The headline

Your brain dump fused two different things into "Canvas". Split them and the whole model
falls out cleanly:

- The **work** multiplicity under a project (main branch + a feature branch worked at once)
  is **Worktrees**.
- The **viewing** multiplicity (several saved pane arrangements over that project) is
  **Canvases**.

So "1 Space → multiple Canvas" is only half the picture. The full picture is two orthogonal
axes hanging off a Space, meeting at the Pane:

```
                 Space  (the project / area you care about; repo or plain dir)
                /     \
   capture axis/       \ view axis
              /         \
        Worktree …       Canvas …          (1 Space → many of each, independently)
        (where agents     (saved arrangement
         run; a path)      of panes)
              \           /
               \         /
                 Pane     (a viewer bound to a worktree-rooted run/session/resource)
```

Neither Worktree nor Canvas owns the other. This mirrors TM's founding instinct (wire vs
transcript are two orthogonal streams that meet at a turn).

---

## What both agents agreed on (treat as decided unless you object)

1. **Space is a brand-new aggregate ABOVE today's path-keyed workspace.** Nothing below
   gets re-keyed.
2. **`WorkspaceId` stays exactly as-is** — the internal per-path storage key. Tier-1 capture
   (`~/.transport-matters/workspaces/{slug}/{hash}/{run}/`) is byte-for-byte untouched. Zero
   capture-regression risk.
3. **Worktree = the work level below Space = today's path-derived workspace**, one per path.
   A plain (non-git) Space has exactly one Worktree (the directory itself). A git Space has
   one Worktree per `git worktree list` entry. This is the grouping layer you were missing:
   today each worktree directory is already its own `Workspace` with separate history, and
   nothing ties them together.
4. **"Canvas" is the right word — keep it.** Both kept it. It is the shipped noun
   (`CanvasModel`, `session-canvas/`), the north-star noun, and an accurate metaphor (pan/zoom
   surface of viewers). It must mean *"a saved surface of panes"* and never mean project /
   repo / path / process. (Codex's only fallback if the UI stays confusing: rename → `Surface`.
   Both advise: don't rename yet.)
5. **Repo-ness is detected from `git --git-common-dir` at startup and persisted additively.**
   The common-dir is shared by all worktrees of one repo, so it's the natural Space grouping key.
6. **Persist Space + Worktree server-side now; Canvas server store is a sync target, not owner**
   (localStorage stays the cache, matching NOW.md). Session links stay **soft** (nullable
   `space_id`/`worktree_id`, no FK) so transcript history survives a Space delete or merge.
7. **API-first parity:** new `/v1/spaces` + `/v1/spaces/{id}/worktrees`; `POST /v1/runs`
   targets a `worktreeId` instead of a raw `cwd` (CLI still resolves cwd internally). The voice
   director gets Space and Worktree as first-class launch/observe nouns, not just Run.
8. **Migration is additive, zero re-key.** New tables + nullable session columns + a one-time
   backfill that runs git detection over each existing session `cwd`. Pre-release, so direct
   migration, no compat layer.
9. **The ⌘K "Workdir" launcher stub (NOW.md) becomes the Space + Worktree scopes.** A
   single-worktree Space skips the worktree sub-step (fast path preserved); a multi-worktree
   repo inserts a branch picker.

This is unusually strong: a domain-first pass and a persistence-first pass, run blind to each
other, produced the same five nouns with the same boundaries.

---

## Decisions — LOCKED (Stuart, 2026-06-21)

### Decision 1 — Space identity: minted-stable, **uuid4**, no string prefix  ✅ LOCKED

Minted-stable id bootstrapped from a derived detection key — but matching littleorgans'
`lilo-common::id` convention (`crates/lilo-common/src/id.rs`), **not** Codex's draft
`spc_<uuidv7>`:

- **Mint with `uuid4`** (littleorgans `Uuid::new_v4()`), not uuidv7. We don't need v7's
  embedded timestamp because we already capture `created_at`/`detected_at` separately.
- **Store in native Postgres `uuid` columns** (littleorgans is `#[sqlx(transparent)]` over
  `uuid::Uuid`), not `text`. Serialize as the **bare uuid string — no `spc_`/`wkt_`/`cnv_`
  prefix.** Identity is carried by the typed field (`space_id`, `worktree_id`), not a string tag.
- **Short display = shortest-unambiguous-prefix, 7-char floor** (littleorgans
  `shortest_unambiguous_prefix`, `MIN_SHORT_PREFIX_LEN = 7`), computed on demand for CLI/voice,
  **never stored**.
- A **derived detection key** still groups linked worktrees: `repo_instance_key =
  sha256(canonical git-common-dir)` (a lookup column, not the public id). The minted `space_id`
  survives repo moves, renames, and merges; the director and Canvases anchor to it.

*Net correction to Codex's schema:* `space_id`/`worktree_id`/`canvas_id` become `uuid` PKs
(app-minted uuid4), `repo_instance_key` stays a derived `text` lookup column with the UNIQUE
constraint that does the grouping.

### Decision 2 — leaf naming: keep `Workspace` internal, `Worktree` is the product noun  ✅ LOCKED

`WorkspaceId` stays the internal per-path storage key (zero rename, zero data migration).
`Worktree` is the new product/API noun above it. The Space/Workspace homophone exists only in
code, never in the product surface.

### Decision 3 — Worktree lifecycle: detect-only first — **but keep the full-CRUD spec**  ✅ LOCKED

Ship detect/observe first (TM reads the worktrees you make with git, never mutates). Creating
worktrees from TM (`git worktree add/checkout/remove`) is the next iteration, **not dropped**:
Codex's end-to-end lifecycle design — endpoints + every failure mode (dirty tree, detached
HEAD, deleted branch, branch-checked-out-elsewhere, missing path, running-runs block remove,
git binary absent → plain Space still works) — is preserved in
`transport-matters-spaces-feasibility--brainstorm.md` §"Worktree lifecycle" and carries
forward into the spec's later iteration.

### Decision 4 — Canvas ↔ Space binding: one Space per Canvas  ✅ LOCKED

A Canvas belongs to exactly one Space. A cross-Space "scratch" Canvas is a later power-user
surface, not now.

### Naming preference applied throughout — no `v1`/`v2`

Per Stuart: there is one version; frame everything as **iteration**, not numbered milestones.
This doc drops `v1`/`v2` labels. Two follow-ups it touches: the schema's `layout_version`
integer (reconsider — prefer a forward-only `layout` shape that iterates in place) and the
existing `/v1/`-prefixed API namespace (the one place this preference collides with shipped
convention — flagged below, your call).

---

## Recommended model in one paragraph

A **Space** is the project/area you care about, identified by a minted stable **uuid4** and
grouped by git-common-dir (or canonical path for a plain dir), repo-ness detected and persisted every
startup. Under it run two independent axes: **Worktrees** (the launchable paths where agents
run and capture is rooted — today's `WorkspaceId`, untouched) and **Canvases** (saved
surfaces of **Panes**). A Pane is a viewer bound to a worktree-rooted run/session/resource —
the point where the two axes meet. `WorkspaceId` and all Tier-1 bytes stay exactly as they are;
Space/Worktree/Canvas are new server records with soft links, so the voice director and the
⌘K palette operate on the same Observe/Launch/Manage/Prompt verbs at Space, Worktree, and Run
granularity.

---

## Peer-consensus result (2026-06-21) — both CONDITIONAL sign-off; model STANDS

Fresh Claude (domain) + Codex (feasibility) panes adversarially reviewed the locked model
against `main@2323169` (clean tree) and littleorgans `id.rs`. Both signed off conditionally:
the core (Space / Worktree / Canvas / Pane, orthogonal axes, uuid4, detect-only-first,
one-Space-per-Canvas) **stands**. Codex positively confirmed uuid4 + native Postgres `uuid`
ports cleanly to the Python/Pydantic v2/psycopg3 backend. The two reviewers hit the same core
seam from opposite sides (Claude: `workspaceId` leaks on the API; Codex: the run must carry
resolved identity, not cwd alone) — high confidence it's the real fix. Reviews:
`~/.mdx/projects/transport-matters-spaces-{domain,feasibility}--review.md`.

### Corrections folded as binding spec requirements

1. **ResolvedWorktree handoff** *(Codex F1, Major)* — the Space store returns a DTO
   `{space_id, worktree_id, cwd, workspace_slug, workspace_hash, missing|archived}` threaded
   through `SpawnRun → ManagedRun → ManagedRunView → SessionWriter`. `cwd` stays internal but is
   **not** the only identity on a run, or `GET /runs`, terminal frames, idempotent-create, and
   filters would have to rediscover space/worktree from `cwd`.
2. **Drop `workspaceId` from public response DTOs** *(Claude F2 + Codex F1, Major)* — `Run` and
   `Worktree` responses surface `spaceId` + `worktreeId` only. `WorkspaceId` stays an internal
   Tier-1 storage key, emitted in no response. Removes `RunViewModel.workspace_id → workspaceId`
   from the serialized surface. This is what actually makes Decision 2 true.
3. **Pane worktree-rooting is not an invariant** *(Claude F1, Major)* — `terminal {owner,label}`
   and `resource(url|path)` refs carry no worktree (`paneRecords.ts PaneContentRef`). So:
   `worktreeId` **required** on spawnable/live-process panes (`terminal`, `captured-run`),
   optional for `resource(url)` (worktree-less by design); session/run-backed panes resolve via
   their ref; **promote `Canvas.defaultWorktreeId` into the domain model** as the explicit
   fallback. Strike the "every Pane is worktree-rooted" prose.
4. **Empty-`cwd` legacy backfill** *(Codex F2, Major)* — `session.cwd` defaults `'' NOT NULL`;
   empty-cwd rows can't be git-detected. Keep `/v1/sessions?workspaceId=` as a legacy history
   surface with an "unassigned legacy" group, and/or allow a legacy Worktree row `path=NULL,
   missing=true` keyed only by `workspace_slug/hash`. **Never** silently assign empty-cwd rows to
   a current Space.
5. **`repo_instance_key` resolves relative `--git-common-dir` against the TARGET cwd**
   *(Codex F3, Minor)* — not the API process cwd (`meta.py` notes they differ), or unrelated
   repos group. Unit test with process-cwd ≠ target-cwd.
6. **Migration** *(Codex)* — real downgrade dropping tables/indexes/columns in dependency order;
   don't claim the whole chain downgrades to base (`0001` is forward-only). Keep
   `session_id/run_id/workspace_slug/workspace_hash` as `text`. `repo_instance_key` stays a
   derived lookup column, never public identity.
7. **Doc/UX hygiene** *(Claude F3/F4)* — "rename → Surface" fallback is **struck** (foreclosed by
   shipped `CanvasSurface.tsx`). "Space" collides with the ⌘K `Canvas gesture modifier: Space`
   string (`commandModel buildSettingsRows`) — Space *scope* needs disambiguating chrome
   (launcher-slice check). State explicitly: the director can **observe/select** a Canvas but not
   **create/mutate** it (Canvas has no director write-verb in this cut).

### Small opens — resolved as defaults

- **API namespace:** new Space routes follow the shipped `/v1/` prefix (one consistent
  namespace; dropping the prefix is a separate API-wide decision, not a per-feature fork).
- **`layout_version`:** kept as a forward-only migration safety field (not a product version).

### Native resume on reopen — deferred (Slice 7)

Reopening a captured-run pane should be able to **resume** the agent, not just re-view its
transcript. There are two distinct resume types, and they share the same lineage anchors:

- **Native resume** — re-spawn the same session via the harness's own native flag
  (`--resume <native_session_id>` for Claude, `resume` for Codex). The provider API is
  stateless, so resume is a **local transcript replay**: the harness rebuilds context from its
  on-disk session. This is precisely why TM (which owns the transcript) can guarantee resume.
- **Internal continuation** — spawn a **new** agent with `parent_session_id = X` plus tooling
  to read session X. Lineage, not the same process.

**Harness-neutral requirement:** the per-harness resume strategy (which native flag, what the
session home looks like) lives on the **LaunchProfile / runtime-template capability seam**, kept
pluggable so adding a new harness is easy. Do **not** spec the strategy now.

**Anchors already in place** (so Slice 7 needs no schema/canvas migration):
- `SessionRow.native_session_id` (the harness's own session id to pass to `--resume`/`resume`),
- `parent_session_id` / `forked_at_seq` (the continuation lineage),
- the captured-run pane `sessionId` (Slice 6) — persisted now, populated on session-bind later,
- `worktreeId` on the pane (the cwd root the resumed run must re-enter).

**Dependency / risk to resolve when Slice 7 is planned:** the agent's native session (its
transcript + session home) must **survive a desktop quit**. Today runs die on quit and some
session homes are ephemeral, so a naive reopen has nothing to resume from. TM's owned Tier-1
transcript copy is the restore seed; Slice 7 must establish how the native home is reconstituted
(or pointed at the Tier-1 copy) before native resume is reliable.

## Next — writing the implementation spec

Consensus complete. Moving to a `writing-plans` spec that decomposes the model + the 7 folded
requirements into PR-sized slices. Warroom `spaces` (Claude %383 + Codex %384) held for an
optional architect pass over the spec, then recycled.

Source files: `~/.mdx/projects/transport-matters-spaces-domain--brainstorm.md`,
`~/.mdx/projects/transport-matters-spaces-feasibility--brainstorm.md`,
`~/.mdx/projects/transport-matters-spaces-{domain,feasibility}--review.md`.

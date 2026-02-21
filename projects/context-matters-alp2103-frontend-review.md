---
title: ALP-2103 frontend review (cm-web ScopeSelector + cx_search split)
type: projects
tags: [context-matters, cm-web, frontend, review, alp-2103]
summary: Review of the cm-web frontend slice of ALP-2103. Identifies seam risk between structured wire format and current `scope: string` query params, missing pagination contract on `/entries/search`, dependency cycle between ALP-2118 and ALP-2117, and a tactical recommendation to keep `WebRecallView` as the search projection until cursor support exists.
status: active
source: frontend-engineer
confidence: high
created: 2026-04-30
updated: 2026-04-30
---

# ALP-2103 frontend review

Scope: ALP-2106, 2107, 2116, 2117, 2118 (with skim of 2104, 2110, 2115).

## Summary — top risks before Nancy starts

1. **Wire format is undecided where it matters most.** ALP-2104 declares structured JSON `{kind, path|paths|cwd}` as the canonical shape, but ALP-2115 says "decode `scope` as a structured JSON value carried in the query string" while ALP-2116 says "encode the structured selector into the `scope` query parameter shape". Neither pins HTTP method (GET vs POST) or encoding (JSON-in-querystring vs flat `scope.kind` + `scope.path` keys). With current GET routes and `scope=cwd_inferred` + `cwd=...` already split across two flat params, the round-trip needs an explicit decision recorded in ALP-2104 *or* ALP-2115 before any of 2116, 2106, 2107 can land. Reviewer recommends URL-encoded JSON in `scope=` for read GETs (matches `deny_unknown_fields` posture, keeps one parser) and bans the legacy `cwd=` query key.
2. **ALP-2117 must land before ALP-2106.** ALP-2106 routes Recall's "Any scope" through `cx_search`. The frontend already calls `api.entries.search()` and gets `WebRecallView` back (search currently delegates to `recall::recall`). When the backend swaps in a new `cx_search` capability, the projection contract changes. ALP-2106 cannot ship without ALP-2117 finalised, and ALP-2117 currently leaves the choice open. Issue order in the epic body should be 2104 → 2115 → 2117 → 2116 → 2118 → 2106 → 2107.
3. **Dependency-cycle risk: ALP-2118 needs the value type from ALP-2116, ALP-2118 also pre-supplies UI for ALP-2106 and 2107.** Today both 2106 and 2107 list overlapping files (`RecallBar.tsx`, `FilterBar.tsx`, `FeedPage.tsx`). Without 2118 landing first the two branches will collide on RecallBar. Suggested split: 2118 lands the shared `<ScopeSelector mode>` and the typed value; 2107 then surfaces full mode in BrowsePane/FilterBar; 2106 wires the routing predicate. This needs to be stated in the issue bodies, not implicit.
4. **Frontend `RecallParams` and `SearchParams` carry a `cursor` field that the backend search route does not accept** (`SEARCH_QUERY_KEYS = &["query", "scope", "cwd", "kind", "tag", "limit"]`, `crates/cm-web/src/api/entries.rs:116`). ALP-2117 calls this out but no sub-issue owns the fix. Either drop `cursor` from `SearchParams` (most expedient) or add it to the backend parser plus capability. Keep one ALP-2117 acceptance check that asserts: every typed field on the frontend Param type is accepted by the backend parser.
5. **Browse, FilterBar, and BrowsePane each maintain their own scope `useState<string|undefined>`.** With the structured shape this becomes `useState<ScopeSelector|undefined>`. Three duplicates exist (`BrowsePane.tsx:21`, `FeedPage.tsx` via URL search, `RecallBar.tsx` via `useRecallControls`). ALP-2118 names extracting the *control*; it does not own extracting the *state hook*. Add a `useScopeSelectorState` hook to ALP-2118 acceptance, otherwise the three sites all mint slightly-different `ScopeSelector | undefined` values.

---

## Per-issue findings

### ALP-2116 — Frontend: model and serialize ScopeSelector requests
**Status: needs revision (blocker for 2106/2107/2118).**

Concerns:
- The wire-shape decision is delegated to ALP-2104 but the issue does not state how the structured value embeds in a GET URL. Pin one of: (a) `scope=<urlencoded JSON>`; (b) repeated `scope.kind=path&scope.path=...&scope.paths=a&scope.paths=b`; (c) move all read endpoints to POST. Option (a) is cheapest and keeps `deny_unknown_fields` workable.
- "Update `scope-contract.test.ts` and the Rust source contract test" — the Rust source contract test is not located. Either name the file or drop the requirement.
- The current `RecallParams` carries `scope?: string; cwd?: string` as two flat fields. The replacement should be a single `scope?: ScopeSelector` (the `cwd` lives inside the discriminated union for the `cwd_inferred` variant). This is a behavioural breaking change; call it out explicitly so the singular `cwd` query key is removed everywhere, including `BrowseParams`, `ExportParams`, and `api.export(scope: string)` (which today accepts a bare string).
- Add an explicit acceptance: "The legacy positional `api.export(string)` overload is removed in this issue."

Recommended issue edits:
- Replace "encode the structured selector into the `scope` query parameter shape expected by ALP-2115" with "encode the structured selector as a URL-encoded JSON object in the `scope` query parameter; remove the standalone `cwd` query key".
- Add a "Verify" bullet: "`api.export(string)` overload removed; `BrowseParams`, `SearchParams`, `RecallParams`, `ExportParams`, `AgentBrowseParams` all reference a single `ScopeSelector` type; `cwd` is no longer a top-level field on any param interface."

### ALP-2118 — Reusable scope selector control
**Status: needs revision.**

Concerns:
- The "two modes (singular vs full)" framing risks a flag-laden component. The cleaner split is two primitives sharing the typed value: `<ScopePicker>` (single path, used by RecallBar) and `<ScopeSelector>` (full vocab, used by BrowsePane and FilterBar). They both produce `ScopeSelector | undefined`, but RecallBar's primitive only ever emits `Path | CwdInferred`. Reviewer position: prefer two primitives over one component with a `mode` prop.
- Issue lists "Replace duplicated scope option builders in `RecallBar`, `FilterBar`, `BrowsePane`, and feed route consumers" — there is also `EntryEditor.tsx:330` and `NewEntryEditor.tsx:215` that build scope options for write paths. Those are *write-side scope pickers*, not read-side selectors. State that they are out of scope to prevent accidental rewrites.
- The shared backing data is `stats.scope_tree` from `useStats()` (already widely used). Issue should name this so the implementer does not invent a new endpoint.
- For Set mode, add a UX acceptance: "Set defaults to a single-element list when the user clicks the first option; when reduced to zero elements, the selector reverts to All or undefined."
- The acceptance "Any scope in Recall mode routes through the search path rather than recall when a query exists" belongs to ALP-2106, not 2118. Move it.

Recommended issue edits:
- Split the goal into two primitives, name them.
- Add `useScopeSelectorState` hook acceptance: "Single hook produces `(value, setValue)` of type `ScopeSelector | undefined` and is consumed by RecallBar, FilterBar (curate), and BrowsePane."
- Move the "routes through search" acceptance to ALP-2106.

### ALP-2106 — Route Recall "Any scope" to cx_search
**Status: good once 2117 lands.**

Concerns:
- "Any scope with an empty query does not fire a request and shows a hint" — verify this hint also gates the existing `useAgentRecall` debounce path (`FeedPage.tsx:127`). The current `useAgentRecall` is enabled by `isRecallMode` only, so the no-fire requirement needs `enabled: isRecallMode && (recallScope !== ALL || debouncedQuery)`.
- The recall mode's RecallBar copy "Matches `cx_recall`: optional query, single scope, multi kind, multi tag." (`RecallBar.tsx:74`) is wrong once All routes through search. Issue does mention this. Make the copy switch on selector mode, not on operation choice — the visible label "Any scope" is preserved, but the helper text below should switch to "Cross-scope search via `cx_search`" when selector === All.
- Routing decision lives in: useRecallControls? FeedPage? a new `useRecallOrSearch` hook? Pick one. The issue leaves it implicit. Recommend a tiny `useRecallOrSearch(selector, query)` hook that returns one of two query objects so RecallBar and RecallResults stay agnostic.
- "A singular scope calls recall. Recall must receive only Path or CwdInferred selectors." — the typed `ScopeSelector` value already encodes this. The runtime guard should live in ALP-2104 (capability). Frontend gets it for free via the type.

Recommended issue edits:
- Add a "Files" entry: a new `routes/feed/useRecallOrSearch.ts` if the routing logic ends up non-trivial.
- Move the "no-fire on empty Any" check explicitly into the `useAgentRecall` enabled clause.

### ALP-2107 — Surface Subtree and Set scope selectors
**Status: good once 2118 lands.**

Concerns:
- The issue lists `crates/cm-web/frontend/src/components/composed/FilterBar.tsx` as a touched file, but the composed FilterBar is the dumb facet/chip primitive — it does not need scope shape knowledge. Only the wrapping `components/FilterBar.tsx` and `BrowsePane.tsx` need editing. Drop the composed file from the touched list.
- "Set returns the selected union once ALP-2110 is complete" — fine, but the UI cannot ship before 2110, so add an explicit blocker on 2110 (today the issue body mentions 2110 in passing; promote it to "Blocks on").
- The chip rendering for Set ("scope:[a, b]") is not specified. Add an acceptance for chip representation of multi-select scope.

Recommended issue edits:
- Drop `components/composed/FilterBar.tsx` from the file list.
- Make ALP-2110 a hard blocker, not just a referenced sibling.
- Add a chip-rendering acceptance bullet.

### ALP-2117 — Define cx_search web response contract
**Status: blocker. Most ambiguous issue in the epic.**

See the dedicated recommendation section below. This issue must be resolved first.

Concerns:
- "Today the frontend type has a cursor field while the current backend search parser does not accept it" — explicitly: `SearchParams.cursor?: string` exists in `client.ts:151` but `SEARCH_QUERY_KEYS` rejects it. This is already broken at runtime if any caller passes a cursor. None do today (search has no cursor UI), so it's latent. Treat as a typed-contract drift that 2117 must close.
- "If it stays recall shaped, document how search fills or omits recall specific header fields such as routing, tier, scope chain, tokens, and scope hits." — currently `WebRecallHeader` carries `scope_chain: Array<string>` which is meaningless for cross-scope search (no walk). Either omit it (header field stays an empty array, projection lies) or split the projection. Reviewer position below.

---

## Cross-cutting concerns

### File-size budget projections (post-edit)

| File | Current | After ALP-2103 sub-issues | Risk |
| ---- | ------- | ------------------------ | ---- |
| `crates/cm-web/frontend/src/api/client.ts` | 342 | ~380–410 (one shared serializer + tagged ScopeSelector type + new search response type) | green |
| `crates/cm-web/frontend/src/components/RecallBar.tsx` | 203 | ~170 (selector extracted to ALP-2118 primitive) | green, drops |
| `crates/cm-web/frontend/src/components/FilterBar.tsx` | 124 | ~115 (uses shared selector) | green |
| `crates/cm-web/frontend/src/components/composed/FilterBar.tsx` | 167 | unchanged (do not touch) | green |
| `crates/cm-web/frontend/src/components/BrowsePane.tsx` | 138 | ~150 (typed selector state) | green |
| `crates/cm-web/frontend/src/routes/feed/FeedPage.tsx` | 331 | ~360 if recall/search routing inlined; ~330 if routing extracted to a hook | yellow — extract `useRecallOrSearch` to keep under 350 |
| `crates/cm-web/frontend/src/api/hooks.ts` | 174 | ~210 (add `useSearch` enabled gating, `useAgentSearch` if introduced) | green |
| `crates/cm-web/frontend/src/api/scope-contract.test.ts` | 43 | ~110 (every variant exercised) | green |
| New: `lib/scope.ts` (shared serializer + types) | n/a | ~120 | green |
| New: `components/composed/ScopeSelector.tsx` | n/a | ~180 | green |
| New: `components/composed/ScopePicker.tsx` (singular) | n/a | ~100 | green |
| New: `routes/feed/useRecallOrSearch.ts` | n/a | ~50 | green |

No file projects over 700 LOC. FeedPage is the only one to watch; the recommended `useRecallOrSearch` extraction keeps it healthy.

### Components/hooks that already exist and should be reused

- `useStats()` → `stats.scope_tree` is the single source for known-scope vocabulary. RecallBar, FilterBar, BrowsePane, ScopeTree, EntryEditor all already consume it. ALP-2118 must not invent a new endpoint.
- `components/composed/FilterBar.tsx` (the dumb primitive) — already takes `Record<string, string|boolean|undefined>`. Surfacing Subtree/Set requires a richer per-facet type than `string`. Recommended path: do **not** generalise the composed FilterBar; instead, render the new `<ScopeSelector>` adjacent to the composed FilterBar in `components/FilterBar.tsx`. Keeps the dumb primitive dumb.
- `useRecallControls` already isolates recall-only state. Mirror it as `useScopeSelectorState` for non-recall surfaces.

### Seam risks

- **URL state ↔ structured selector.** `routes/feed/search.ts:18` currently parses URL `scope` as a string (with a legacy `scope_path` fallback). With structured wire format, the URL state for Feed must either keep a compact stringy form (e.g. `scope=path:global/...` or `scope=subtree:global/...` flat encodings) and translate at the API boundary, or carry a JSON blob in the URL. ALP-2116 mentions "Keep feed URL state compact if useful" — pin this. Recommended: keep URL state as `scope` (string) + a new `scope_mode` enum in URL only (`exact|subtree|all` and a new `scope_set` repeated key for Set). The API client serializer is the only thing that emits structured JSON. URL is for humans and bookmarks, not for the API.
- **`routes/index.tsx:74` and `ScopeTree.tsx:119`** link to `/feed` with `search={{ scope: node.path }}` (string). After ALP-2107 these links must produce a URL the new Feed search validator accepts as Path-mode. The cleanest fix is an `exact` default in the URL validator when only `scope` is provided.
- **`scope-contract.test.ts` is the only typed contract.** It currently includes legacy `cwd_inferred` magic strings. After ALP-2116, those become `{kind: "cwd_inferred", cwd: "..."}` literals. The test file is the right place to lock this; expand it to assert every variant compiles and that `cwd` cannot be passed at the top level.

---

## ALP-2117 recommendation — explicit position

**Recommendation: keep `/api/entries/search` returning `WebRecallView` for the duration of this epic. Defer a dedicated `WebSearchView` projection to a follow-up.**

Rationale:
1. The `cx_search` capability does not exist yet. Until it does, `/entries/search` continues to delegate to `recall::recall` (today's behaviour, `entries.rs:75-114`). The current projection works.
2. `WebRecallView` already contains every field a search consumer needs: `header.routing`, `header.candidates`, `header.returned`, `header.tokens`, `header.kinds_histogram`, `header.tags_histogram`, plus `entries[]` of `WebRecallRow` (which carries `score`, `snippet`, `scope`, `kind`, `tags` — exactly what a search result row needs).
3. `WebRecallHeader` fields that don't apply to cross-scope search degrade cleanly: `tier` is `null`, `scope_chain` is `[]`. Document this in the projection's doc comment, not via a new type. The frontend `TracePanel` already handles `null`/empty cases.
4. The only fields that genuinely don't fit are forward-looking: `cursor` (search doesn't paginate yet) and a future `relevance_explanation`. Both are deferrable.
5. A dedicated `WebSearchView` would force a parallel `RecallResults`/`SearchResults` component pair and a parallel `TracePanel` variant for marginal value. The `kind: "recall" | "browse"` discriminator on `TracePanel` already supports adding `"search"` if/when the projection diverges.

**Concrete change to ALP-2117 body:**

Replace "Decide whether `/api/entries/search` returns a new search projection or a compatibility view shaped like the existing recall response" with:

> Decision: `/api/entries/search` returns `WebRecallView` for this epic. Document in the projection that `header.tier = null` and `header.scope_chain = []` are normal for search responses. Drop the unused `cursor` field from frontend `SearchParams` until the `cx_search` capability gains pagination. Reopen this issue when paginated search is requested.

Acceptance:
- `SearchParams.cursor` removed from `client.ts`.
- A unit test in `entries.rs` asserts that a `scope.kind=all` search returns a `WebRecallView` whose `header.scope_chain` is empty.
- Frontend `RecallResults` continues to consume `WebRecallView`. No new component.

---

## Suggested issue changes

1. **Reorder dependencies in epic body (ALP-2103).** State explicit order: 2104 → 2115 → 2117 → 2116 → 2118 → 2106 → 2107 → 2110 (browse-side, can land in parallel with 2118).
2. **Pin wire encoding in ALP-2104** (or 2115). One sentence: "The `scope` query parameter on read GET routes carries a URL-encoded JSON object matching the `ScopeSelector` `serde(tag = \"kind\")` shape. The legacy `cwd` top-level query key is removed."
3. **Move "routes through search" acceptance from ALP-2118 to ALP-2106.** It is routing logic, not control logic.
4. **Promote ALP-2110 from sibling to blocker for ALP-2107.**
5. **Split ALP-2118 deliverables explicitly** into (a) `<ScopePicker>` singular, (b) `<ScopeSelector>` full, (c) `useScopeSelectorState` hook, (d) value type re-exported from `lib/scope.ts`.
6. **Remove `composed/FilterBar.tsx` from ALP-2107 file list.**
7. **Lock ALP-2117 to the "stay on `WebRecallView`" decision** per the recommendation above.
8. **Add an ALP-2116 acceptance** that removes `api.export(scope: string)` overload and the standalone `cwd` field across all Param types.
9. **Stable references audit:** Issue bodies pin no line numbers. Good. Symbol references (`RecallBar`, `FilterBar`, `BrowsePane`, `useRecallControls`, etc.) all resolve. ALP-2104 pins `query.rs:27-31` and `recall.rs:23,81` and `migrations/001_initial_schema.sql:39` — flag these as line-number drift risk and replace with symbol-only references in the issue body.

---

## Open questions

1. Does `cx_search` (the future capability) accept `kinds: Vec<EntryKind>` and `tags: Vec<String>` like recall, or single `kind`/`tag` like the current legacy parser? ALP-2104 doesn't say; ALP-2117 doesn't say. The frontend type lists `kind?` singular today. Recall has `kinds[]`. This must be decided before ALP-2117 lands or `SearchParams` will encode a kind shape that doesn't match the capability.
2. After Set mode, does the URL serialise as `scope_set=a&scope_set=b` (repeated key) or as JSON in `scope=`? Tied to question 2 above (URL state vs API state).
3. Should `/api/agent/search` exist (parity with `/api/agent/recall`)? Today only `/entries/search` exists. If yes, add to ALP-2106 or a sibling.
4. Stuart's intent: is `cx_facet` truly out of this epic? ALP-2103 says yes. ALP-2118's "Set" UI reads close to faceted scope selection; the issue should explicitly note that the scope selector is *not* a facet and does not aggregate counts post-query.

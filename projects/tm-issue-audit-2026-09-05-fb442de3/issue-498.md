# 498: Transcript recall is unusable: indexed FTS exists but is unexposed, and channel scoping makes 'not found' indistinguishable from 'not reachable'

URL: https://github.com/littleorgans/transport-matters/issues/498
State: open
Labels: enhancement
Updated: 2026-08-27T22:03:02Z

## Summary

Transcript recall is the capability that makes a session store worth keeping, and today it does not work. I was asked to reconstruct the history of the browser-pane CDP/devtools work from transcripts alone. I could not, and the interesting part is *why*: four independent gaps, each of which alone would be enough to make a recall question return "nothing found" when the truth is "not reachable from here".

The headline: **the store already has a populated, GIN-indexed full-text column that no endpoint exposes.**

Everything below was measured on this machine, 2026-08-28.

## What a recall question costs today

The documented path is: page `/v1/sessions`, pull `/v1/sessions/{id}/events` for each, grep client-side. Measured:

| channel | sessions | events | span |
| --- | --- | --- | --- |
| stable | 152 | 1,857 | 2026-07-15 .. 08-27 |
| preview | 341 | 7,830 | 2026-07-19 .. 08-27 |
| dev | 8 | 884 | 2026-08-27 |

Dumping 7 dev sessions produced 3.4 MB. Full history extrapolates to ~40 MB pulled over HTTP, one session at a time, to answer one question. Add a second keyword later and you pay it again unless you cached.

## Gap 1: a backend serves exactly one channel, and nothing says so

`/v1/sessions` returns only the channel its backend is bound to. The backend I was attached to had **8 of 501** sessions. Nothing in the response, the skill, or the error surface indicates the other 493 exist. A recall agent asks its question, gets an empty result, and reports "no history" with total confidence.

To reach the rest I had to hand-start two extra uvicorn backends against `preview` and `stable`, unsetting six inherited `TRANSPORT_MATTERS_*` variables so they would not bind the current run's storage. That is not a search surface, it is a workaround, and it writes to those channels on startup (`run_startup_refresh`).

**Ask:** cross-channel read, or at minimum an explicit statement of scope in every list response, so "empty" is distinguishable from "elsewhere".

## Gap 2: full-text search already exists in the schema and is not exposed

`public.event` has:

```
search_text  text
content_tsv  tsvector
```

and

```
event_fts_gin  CREATE INDEX ... USING gin (content_tsv)
```

It works:

```sql
select count(*) from event
where content_tsv @@ websearch_to_tsquery('english','browser');
-- 51
```

There is no API endpoint over it. The skill tells agents "no server-side full-text search" and sends them to grep 40 MB, while an indexed tsvector sits in the same table.

Coverage is partial, which is the real work here:

| kind | rows | with `search_text` |
| --- | --- | --- |
| meta | 5,187 | 0 |
| turn | 2,643 | 2,192 |

5,641 of 7,830 rows carry an empty tsvector. So `meta` events are invisible to FTS, and 451 `turn` rows were missed. `raw::text ~* ...` catches what FTS misses today, which is exactly the signal that backfill is incomplete.

**Ask:** `GET /v1/sessions/search?q=...` over `content_tsv`, returning `session_id, seq, ts, headline`, with `ts_headline` for snippets. Backfill `search_text` for all kinds, or state deliberately which kinds are excluded and why.

## Gap 3: the list surface cannot filter on what it returns

`/v1/sessions` returns `harness`, `provider`, `status`, `createdAt`, `lastActivityAt`, `turnCount`. It accepts none of them as filters. Params are `owner, workspaceId, spaceId, worktreeId, purpose, visibility, includeInternal, limit (≤100), cursor`.

So "codex sessions from last week" means paging all 501 rows and filtering locally. On this store `purpose`/`visibility` are the only filters offered and they have exactly one value each (`user`/`user_visible`), i.e. the filters that exist discriminate nothing and the fields that discriminate are not filters.

**Ask:** `harness`, `provider`, `status`, `createdAfter`, `createdBefore`, `minTurnCount`.

## Gap 4: the good read shape is gated, run-keyed, and live-only

`/v1/controlplane/conversation/{run_id}` is the right projection — clean `{turn, role, text, total_chars}` with `older_cursor`/`newer_cursor`. Three things stop it being a history surface:

1. It needs a control plane bearer; without one: `403 forbidden: invalid or revoked control plane bearer`.
2. It is keyed by `run_id`, while the history surface is keyed by `session_id`.
3. The `conversation` MCP tool that holds the bearer is bound to the current backend and reads the live roster (13 runs, all from today).

The correlation exists but is only recoverable by string-scraping: conversation item ids are `message:<session_id>:<seq>`, and a timeline item's `source.sourcePath` embeds the run id.

Meanwhile the ungated historical path (`/events`) returns raw rows whose field names vary per harness, which is precisely why grep beats structured extraction across mixed history.

**Ask:** an ungated read-only conversation projection keyed by `session_id`, and a first-class `runId` field on `SessionSummary`. Adjacent to #496.

## Gap 5 (smaller): `source_path` points at files that are gone

`timeline` items carry `source.sourcePath` into the harness's native JSONL, which invites a filesystem grep. Runtime homes get cleaned:

```
~/.transport-matters          0 native transcript files
~/.transport-matters-preview  0
~/.transport-matters-dev      2
```

The database is the only durable copy. Worth saying so where `sourcePath` is documented.

## The test case that motivated this

Reconstructing the browser-pane CDP/devtools arc from transcripts. Result: **the work is not in the store.** Across all three channels the only matches are noise:

- `cdp` — 3 hits in stable, all `meta`, all the same skill-catalog string: `"browser-harness: Direct browser control via CDP"`.
- `browser.?pane` — 48 hits in stable, all `meta`, all `cwd` fields naming `/T/tm-browser-pane-proof-*` temp dirs from an automated proof harness on 2026-08-27.
- `WebContentsView` — 0 hits anywhere.
- `devtools` — 0 hits outside the dev channel, where the 28 hits are this investigation itself.

The commits exist. The sessions that produced them were never captured into any channel's store. **That is the most serious finding**, and it is invisible from inside the API: an agent asking this question gets an empty grep and no way to tell "never captured" from "wrong channel" from "FTS gap". Capture coverage needs its own answer, and probably its own issue once someone determines whether this is workspace scoping, channel drift, or sessions that simply ran outside TM.

## Suggested shape

1. **Expose the tsvector.** Highest value per unit work; the index is already built.
2. **Make scope explicit in every response.** Cheapest fix for the worst failure mode, which is confident wrongness.
3. **Backfill `search_text` across kinds**, or document the exclusion.
4. **Add the obvious filters.**
5. **Ungate a `session_id`-keyed conversation projection.**
6. **Investigate capture coverage** — why a month of browser-pane work left no transcript.

## Notes

`skills/transcript-search/SKILL.md` in `littleorgans/.agent-runtimes` has been corrected against the live API: it documented the wrong prefix (`/api` vs `/v1`), wrong params, wrong response shape (bare array vs `{items, nextCursor}`), offset vs cursor paging, and a nonexistent `transport-matters status` command. It now also warns that piping a response through `echo` under zsh corrupts JSON escapes and produces a misleading `Invalid string: control characters` jq error. That is documentation catching up with the API, not a substitute for the gaps above.


## Comment by srobinson at 2026-08-27T22:03:02Z (updated 2026-08-27T22:03:02Z)

https://github.com/littleorgans/transport-matters/issues/498#issuecomment-5445747524

Verified the negative result behind this issue against Postgres directly. It holds, but it had been established on the same incomplete index the issue proposes exposing, and one attribution in it is wrong. Both details sharpen Gap 2.

## The coverage gap is uniform across all three channels

The table above measures `preview`. It is the same everywhere:

| channel | meta rows | with `search_text` | turn rows | with `search_text` |
| --- | --- | --- | --- | --- |
| stable | 1,247 | 0 | 610 | 451 (73.9%) |
| preview | 5,187 | 0 | 2,643 | 2,192 (82.9%) |
| dev | 517 | 0 | 491 | 382 (77.8%) |

Every `meta` row in the store carries an empty tsvector, and roughly a fifth of `turn` rows do. Across all channels that is 6,951 meta rows and ~1,300 turn rows invisible to any query over `search_text` or `content_tsv`.

## The original negative finding was drawn on that index

The conclusion reported was that the browser-pane CDP/devtools work is absent from the transcript store. Re-running the scan against `raw::text`, which covers the rows FTS cannot see:

| term | stable | preview | dev |
| --- | --- | --- | --- |
| `devtools` | 0 | 0 | 49 rows / 3 sessions |
| `WebContentsView` | 0 | 0 | 11 rows / 2 sessions |
| `browser pane` | 0 | 0 | 27 rows / 3 sessions |
| `cdp` (word-boundary) | 3 | 1 | 73 rows / 3 sessions |

The conclusion survives: the sessions that produced #492 / #493 / #495 are genuinely not in the store, and the stable/preview `cdp` hits are the skill-catalog noise already identified.

The point is that this verification had not been run. The claim "the counts match the underlying tables exactly, so nothing is hidden from me" was true of *session counts* and not of searchable *content*. A negative answer over `search_text` today is a negative over roughly 70% of turn rows and 0% of meta rows.

## Correction: the dev-channel devtools hits span three sessions, not one

They were attributed to a single session. Actual distribution:

| session | rows |
| --- | --- |
| `89c3b50f-6744-4989-824a-944e195bf86c` | 16 |
| `5819a0bf-9749-49c1-b407-dc2db52e806a` | 14 |
| `c055d100-71a2-41fc-aa43-c0516a1f448f` | 5 |

`c055d100` is a separate earlier run whose transcript contains the pane reporting `attach: unavailable / reason: devtools_disabled`. Part of the arc **is** captured, and the scan passed over it.

That matters for the framing at the end of the issue: the capture gap is narrower than stated. Discussion of the feature is captured; only the sessions that implemented it are missing. Whoever picks that up should scope it to implementation sessions rather than the topic as a whole.

## Consequence for the Gap 2 ask

This is the argument for treating the `search_text` backfill as a blocker on the endpoint rather than follow-up work.

Shipping `GET /v1/sessions/search?q=...` over `content_tsv` at current coverage produces an endpoint that answers confidently and wrongly. A caller gets `[]` and cannot distinguish "not in the corpus" from "in a `meta` row" or "in one of the 1,300 unbackfilled turn rows". That is Gap 1's failure mode, "empty" indistinguishable from "not reachable", reappearing inside the search surface itself.

Two things worth pinning to the endpoint:

- Backfill `search_text` for every kind before exposing it, or have the endpoint report the coverage it searched so a caller can qualify an empty result.
- Whatever populates `search_text` on write is not running for `meta` at all and is skipping ~20% of `turn`. Worth finding out which, since a backfill that does not fix the writer will drift straight back.

All figures measured 2026-08-28 against `transport_matters`, `transport_matters_preview`, and `transport_matters_dev` on `localhost:55432`.


## Sub issues
[]

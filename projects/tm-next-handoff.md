# TM handoff — 2026-08-18

## Just landed

`5591db86 feat(capture): persist provider-neutral request evidence (#391)` on `main`.
Nine CI jobs green. Dual-reviewed (Sol on persistence/migration, Opus on capture/disclosure).

What it changed: method, URL and redacted headers now durable for ALL providers (was
Codex-only, gated by `derive_codex_http`); original content-encoding and content-length
retained request-side; divergence marker on disk and in Postgres via migration
`0034_wire_request_divergence`. Header snapshot moved to request time in
`addon_handlers::handle_http_request` (previously response-time, after `set_text` may have
rewritten content-length — the "original headers" claim was false for overridden requests).

Defects caught in review, all fixed: `request_raw_bytes` column meaning was silently
redefined in place (now additive — old column keeps decoded meaning, new `request_wire_bytes`
NULL on old rows as discriminator); parse-failure dropped the wire snapshot, losing the
divergence marker exactly on the drift path (now routed through `persist_unparsed_exchange`);
unknown bodies recorded 0 and `diverged=false` instead of NULL for both (a fabricated fact);
a `strict=False` fix corrupted undecodable bodies to `?` bytes (now `get_content(strict=False)`).

## Next action

Triage the 10 findings from a `/code-review` pass against merged #390 (baseline capture).
Raw agent transcript: `~/.mdx/projects/tm-390-review-findings.jsonl` (804KB, JSONL — have an
agent read it, do not ingest into orchestrator context).

Known headline findings from that pass, unverified:
- `baseline_capture::_wait_for_correlated_exchange` correlates by prompt substring, breaks on
  Claude title turns, and ignores existing `controlplane.envelope.extract_delivery_id`
- `_json_has_assistant_role` never matches Grok
- `classify_aba` fingerprints unmasked date/cwd leaves, so re-harvest reports BREAKING spuriously
- plus JSONL torn-read, verdict inconsistency, canonical-JSON, and DRY items

Caveat: that pass ran UNSCOPED over the working tree (it reviewed merged main, not a diff),
so treat finding count as inflated until triaged.

## Recommended sequencing

NOW.md names replay as the next primitive, and #391 cleared its precondition (replay needs a
URL and headers). But replay needs a trustworthy comparator to verify reproduction, and the
#390 findings say baseline capture is currently unreliable in exactly that role. So:
triage #390 → fix what's confirmed in baseline capture → then replay.

## Repo state

`main` clean and synced. Four other worktrees remain on disk, untouched, ownership unknown:
`harvest-gates` (slice/native-capture-home), `overlay-landing` (feat/overlay-slice2),
`overlay-registry` (fix/canvas-overlay-status-fullscreen), `process` (wip/canvas-overlay).
Three are overlay work, which NOW.md calls the landing spot. Ask Stuart before removing any.

## Warroom notes

`capev` killed. When respawning: pane self-reports of model are unreliable (one codex pane
said "GPT-5 high" while its footer read `gpt-5.6-sol xhigh`) — read the footer. Do NOT
pre-load `/code-review` into a pane; it forks a background subagent and reviews whatever is in
the tree, which is how the unscoped #390 pass happened. Brief with real scope instead.

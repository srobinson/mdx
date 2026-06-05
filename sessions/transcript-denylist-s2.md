---
title: Transcript denylist (S2) implementation
type: sessions
tags: [frontend, transport-matters, transcript-viewer, denylist, reveal-all]
summary: Append-only JSON-path denylist applied as a UI-side presentation filter on the reveal-all transcript view.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-24
updated: 2026-06-24
---

## Summary

Shipped S2 of the transcript reveal-all track (S1 = nativePayload reveal, PRs #125/#126). The
denylist curates the full-visibility transcript view as a UI-side presentation default:
records whose native payload matches a rule are hidden by default but revealable. Branch
`feat/transcript-denylist`, head `af842f5`. Gate (`just check` && `just test`) green:
desktop 46, www 1057, api 1749.

Key decision (orchestrator's open question) was settled by the converged spec, not guessed:
**v1 is read + apply only; appends are out-of-band** (operator edits the JSON file and
refreshes). Search, import, and replay remain deferred.

## Architecture Decisions

- **Backend reader** `api/src/transport_matters/transcript_denylist.py`: frozen Pydantic
  `TranscriptDenyRule{path, equals?}` / `TranscriptDenylist{hide}` + `read_transcript_denylist`.
  Reads `<storage-root>/transcript_denylist.json` via the existing `default_storage_root()`;
  **uncached** so an edit + refresh is picked up with no rebuild. Missing file is the expected
  default (empty), not an error; malformed JSON/schema is logged and treated as empty so a typo
  can never blank reveal-all (the read never raises).
- **Transport**: echoed on the meta endpoint (`MetaResponse.transcript_denylist`), reusing the
  established meta read path rather than a parallel config mechanism. `MetaResponse` is not in
  the ir/overrides type-mirror test, so the contract is kept in sync by the manual snake→camel
  mapping in `fetchMeta` (`transcriptDenylist`, with a `?? []` guard).
- **Filter placement**: a pure, testable `stream/transcriptDenylist.ts` (dotted-path resolve +
  `annotateDeniedMessages`) consumed by `TranscriptChatPane` via `useMeta`. Kept out of the pure
  `mapIrToChat` mapper since matching needs the meta config (a hook value). Order is preserved
  by annotating each message with a `hidden` flag rather than partitioning into two lists.
- **UX**: denied records hidden by default; a `show N filtered` toggle in the status bar reveals
  them dimmed inline (`data-hidden` + token-only CSS). Honors reveal-all: nothing is permanently
  hidden. Empty denylist → no-op → identical to the current view.

## Semantics

A rule matches when the value at its dotted `path` in the native payload is present and, when
`equals` is set, equal to it. `equals` omitted or null means presence match. Both Python and TS
treat null as presence (no literal-null matching; discriminators are string enums `type` /
`attachment.type`). A record hides if any rule matches.

## Deviations from Spec

None material. The spec described the filter as "collapse/dim with global toggle + per-card
expand"; implemented as hide-by-default + global show-hidden toggle (dimmed on reveal), with the
pre-existing per-card "view raw" serving as the per-card expand. This is the same behavior in a
slightly tighter default.

## Open Items

- Optional next slice: a UI affordance to append a path to the denylist ("hide this field")
  instead of out-of-band file edits.
- Deferred per spec: transcript search, import, replay.

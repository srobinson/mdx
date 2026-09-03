---
title: Preview Codex replay evidence audit
type: sessions
tags: [transport-matters, codex, replay, performance]
summary: Read-only captured artifact comparison against full replay
status: active
created: 2026-09-08
updated: 2026-09-08
---

Observed 2026-09-08T01:05:04.178926+00:00 at source 0c6a57559a1c6cc2487946b9c614517ebbc18fbb.

Completed exchanges passing all comparisons: 5.

- 642f2051-70cb-4e77-8bb4-7c10d09cfdef, 524dbc4b-f21d-48cc-b3db-0ae4af9bdad4: status completed; pass True; messages 7; journal commits 0; comparisons {"events": true, "turn": true, "response": true}.
- 642f2051-70cb-4e77-8bb4-7c10d09cfdef, 7e45e75b-c611-4c71-8866-dacac785bfbe: status completed; pass True; messages 2359; journal commits 0; comparisons {"events": true, "turn": true, "response": true}.
- 642f2051-70cb-4e77-8bb4-7c10d09cfdef, ad779521-eef8-4443-90c2-4ca9754e52e0: status completed; pass True; messages 7; journal commits 0; comparisons {"events": true, "turn": true, "response": true}.
- 642f2051-70cb-4e77-8bb4-7c10d09cfdef, b0f1dea6-4c08-4aaa-8a01-9cf5053fdd5f: status completed; pass True; messages 21; journal commits 0; comparisons {"events": true, "turn": true, "response": true}.
- 642f2051-70cb-4e77-8bb4-7c10d09cfdef, fc4aeac1-3a7f-4894-b23b-a8b49947abe0: status completed; pass True; messages 2989; journal commits 0; comparisons {"events": true, "turn": true, "response": true}.

A provider terminal, completed turn, and stored response establish exchange completion. A remaining manifest or open WebSocket does not establish an unfinished response. Absent terminal evidence with an open turn establishes only that the captured exchange was still open at observation.

Rerun:

```sh
/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/api/.venv/bin/python -B /Users/alphab/.mdx/sessions/tm-preview-live-performance-evidence/audit-replay.py
```

The DiskStorage read path can rewrite transport during redaction. This script uses DiskStorageLayout and ExchangeArtifacts directly, apply_stream for journal hydration, rebuild_codex_derived_artifacts for full semantic replay, and parse_codex_response_payloads for full response parsing. It does not call the storage reader or repair service.

Selection bounded to latest 16 primary exchanges and, when incomplete, first 8 completed fallback exchanges.
No latency sampling or performance improvement claim.
Replay uses captured transport, not an independent vendor transcript.
Operator facts and turn identity reuse stored metadata through the existing rebuild API.
No capture, database, process, or repository writes. Python audit hook denies network and writes outside audit-prefixed output files.
Open exchanges are point-in-time observations, not final parity proof.
File hash stability is checked across each read and replay; later producer changes remain possible.
Exact source HEAD verified; running preview process build identity is not verified.

Exact comparison hashes, input file hashes, provider event counts, terminal timestamps, and diagnostics are in audit-result.json.

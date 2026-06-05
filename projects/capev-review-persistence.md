---
title: PR 391 persistence and precedence review
type: projects
tags: [transport-matters, pr-review, capture, persistence, migration]
summary: Persistence, migration, precedence, ownership, and divergence review for PR 391 at c23691aa
status: active
created: 2026-08-17
updated: 2026-08-17
project: transport-matters
confidence: high
source: https://github.com/littleorgans/transport-matters/pull/391
---

# PR 391 persistence and precedence review

Reviewed `573a453871e4cbf84ff7165dcf50652df02b6712..c23691aadf5c3d5184b563638f49cb4a30485394`.

Counts: 0 blockers, 1 major, 0 minors.

## Major

### Parse failure drops the exact request evidence

Location: `api/src/transport_matters/addon_handlers.py:203`, `handle_http_request`

Observation: `handle_http_request` snapshots the original headers and encoded body before parsing. When `parse_request_ir` returns `None`, the branch calls `persist_unparsed_http_exchange` without either snapshot. That path writes a decoded `request.raw` and synthetic request IR, but no `TransportArtifacts`. Its dedicated unparsed sink also bypasses `WireStoreObserver`.

Failing scenario: send a gzip encoded Anthropic, Codex, or Grok request with a new shape that its adapter rejects. A focused reproduction at the reviewed SHA started with 64 encoded bytes, persisted 44 decoded bytes, and loaded an exchange with no transport artifact. The original content encoding, declared content length, encoded byte count, and positive divergence marker are gone. PostgreSQL receives no corresponding wire exchange.

Impact: protocol drift is the request class most likely to fail parsing. The capture then loses the evidence needed to explain or replay that drift, and the divergence marker silently under reports it.

Basis: the changed request hook captures the original inputs, but the parse failure branch does not forward them. [Reviewed source](https://github.com/littleorgans/transport-matters/blob/c23691aadf5c3d5184b563638f49cb4a30485394/api/src/transport_matters/addon_handlers.py#L203-L209)

Caveat: the decoded request body remains durable, and the unparsed sink was historically separate from the PostgreSQL wire store. If PR 391 explicitly excludes unparsed HTTP requests, this becomes accepted scope. The stated provider neutral and false negative free evidence contract does not make that exclusion.

Smallest correction: carry the captured request snapshot into unparsed persistence, write the same HTTP transport artifact to disk, and preserve `WireStoreObserver` as the only PostgreSQL writer if unparsed rows must enter the wire store.

## Verified without another finding

- Migration `0034_wire_request_divergence::upgrade` adds one nullable column and preserves existing rows. Historical `request_raw_bytes` values remain their prior decoded lengths with divergence unknown. Old transport artifacts load with all four new request evidence fields defaulted to `None`. Downgrade removes only the new column, then reupgrade restores it.
- `merge_http_transport_artifacts` resolves every collision checked. Request time request evidence wins, while response time response evidence and Codex messages win.
- `WireStoreObserver._submit_exchange` remains the sole production constructor feeding `SessionWriter.submit_wire_exchange`. No second PostgreSQL writer was added.
- Parsed request disk artifacts and PostgreSQL rows derive size and divergence from the same preserved request object. Replayed identical writes converge without a second notification, response completion remains monotonic, and the marker does not flip.
- A missing `raw_content` value collapses to empty evidence, but the production JSON adapters reject that empty decoded body before request evidence is constructed. No reachable false negative was retained for that case.

Verification: 28 focused tests passed after supplying the repository test database URL, including request evidence, provisional finalize, migration preservation, writer replay, and observer persistence. A direct precedence collision and legacy artifact parse passed. All PR checks were green. The PR head and base remained exact, and the worktree remained pristine.

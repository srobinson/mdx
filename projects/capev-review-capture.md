# capev review: capture path, disclosure, reuse

Target: PR#391, branch `feat/capture-request-evidence`, sha `c23691aa`, base `573a4538`. Diff only.
Angle: capture-path correctness, disclosure, reuse discipline. Migration/precedence/persistence belongs to the other reviewer.
Tree verified pristine (`git status --porcelain` empty) before and after; no writes by me or any subagent.

Local evidence run (this pane has no Postgres): `api/.venv/bin/python -m pytest -q src/transport_matters`
→ **3403 passed, 0 failed, 293 errors**, every error `MissingDatabaseConfigError` from the `test_db` fixture. The DB-backed
tests this PR adds (`session/test_wire_request_body_divergence_migration.py`, `session/test_wire_writer.py`) were **not**
executed here.

Counts: **0 Blockers, 1 Major, 4 Minors.**

> **Delta verification of sha `8f706213` is appended at the end of this document** (4 resolved, 1 partial, 0 unresolved).
> The findings below are the original pass against `c23691aa`; read the delta section for current status.

---

## 1. Disclosure — CLEAN (verified, highest-stakes item)

No path found where a request header reaches disk or Postgres unredacted. Three independent gates:

1. `http_transport.py:90 build_http_transport_artifacts` is the **only** constructor of an HTTP `TransportArtifacts`
   in the tree (`grep redact_transport_artifacts` / `build_http_transport_artifacts`), and it calls
   `transport_redaction::redact_transport_artifacts` on every build. `exchange_recorder/artifacts.py:63
   derive_http_transport` is the only caller, reached from all three persist paths
   (`exchange_recorder/__init__.py` `persist_http_exchange`, `persist_http_provisional_exchange`,
   `_finalize_http_provisional_exchange`). The in-memory `ExchangeArtifacts.transport` is therefore already redacted.
2. `storage/disk.py:544` redacts again on write; `storage/disk.py:410` redacts on read and rewrites the file if the
   stored bytes were ever pre-redaction.
3. `merge_http_transport_artifacts` only ever combines two already-redacted artifacts (`existing` comes from
   `storage.read_exchange`, `finalized` from `build_http_transport_artifacts`).

Coverage check against the three providers this PR newly exposes:
`transport_redaction::_SENSITIVE_HEADER_NAMES` covers `authorization`, `proxy-authorization`, `x-api-key`, `api-key`,
`apikey`, `cookie`, `set-cookie`; `_header_is_sensitive` additionally matches any `*-token`, `*-session`, and the
`x-openai-`, `openai-sentinel-`, `x-auth-`, `x-csrf-`, `cf-access-` prefixes. That covers Anthropic (`x-api-key`,
`authorization`), Grok/xAI (`authorization`, `cookie`) and Codex (`authorization`, `openai-sentinel-*-token`).
`test_http_request_evidence.py::test_anthropic_request_evidence_is_durable_and_redacted` proves the end-to-end
non-Codex case through real disk storage.

Also worth recording: the new fields carry **sizes only**, never the encoded body, so no second copy of a request body
lands on disk. See Minor 2 for the one uncovered surface (URL query strings).

## 2. Wire behaviour — CLEAN (additive capture only)

`addon_handlers.py:203-204` reads `flow.request.headers` via `snapshot_headers` (`items(multi=True)` → tuple, no
mutation) and `raw_http_body_bytes` (`getattr(message, "raw_content")`, a plain attribute — no stream consumption,
mitmproxy's `raw_content` is the undecoded buffer and reading it decodes nothing). `capture_http_request_artifacts`
is pure `getattr` over `method/scheme/host/path` plus two header scans. Nothing writes to `flow.request`; the only
mutation in the handler remains `addon_handlers.py:249 flow.request.set_text(...)`, unchanged and still after capture.
No new `await` sits between capture and forward. The one real cost is Minor 3.

## 3. The QM3 fix — REAL, and the unchanged Codex baselines say nothing either way

The snapshot is genuinely request-time: `addon_handlers.py:203` runs immediately after adapter selection and **before**
`run_pipeline`, `capture_request_flow_state`, and `flow.request.set_text` at :249. The overridden case is proven by
`test_http_request_evidence.py::test_http_request_snapshots_headers_before_override_rewrites_length`, which asserts
`request.headers["content-length"] != evidence.original_content_length`. The breakpoint path holds too: `pause_session.py`
rewrites the request on release, then re-persists with the same `request_state`, whose `http_request_artifacts` still
carry the pre-edit headers. `merge_http_transport_artifacts` prefers `existing.request`, so finalize cannot overwrite the
request-time record with a later one; `test_http_provisional_finalize.py::test_finalize_http_provisional_exchange_preserves_request_time_transport`
covers that. The old response-time builder `codex/transport::build_codex_http_transport_artifacts` is deleted, and
`grep` finds no remaining caller.

**On "Codex certification baselines UNCHANGED":** unchanged baselines are *not* evidence the fix is real, and *not*
evidence the old path is still live. The records in `harnesses/certification_records_v1/` contain no transport headers
at all — they hold suite outcomes, fixture digests and per-run evidence digests. Header timing is invisible to them.
Two further facts: (a) the certification digest that *does* touch transport,
`certification_evidence.py::_check_wire` → `certification_run_reader::CapturedExchange.manifest_item`
(`transport_sha256` over the exact persisted bytes), necessarily moves for all three harnesses after this PR —
Codex because `transport.json` gains four new keys, Claude and Grok because they gain a `transport.json` where
`transport_sha256` was previously `null`; (b) that is expected, since each record pins a `transport_matters_revision`
and is re-minted per revision, so it is not a finding. The baseline files simply were not re-minted in this PR.
Verified no minting regression: `drift_capture::detect_unknown_shapes` reads `artifacts.transport` only on the
`codex` branch, so the new non-Codex transports cannot trip `CertificationMintingError`, and
`certification_run_reader.py:191`'s "needs redaction repair" guard stays satisfied because the write path redacts first.

## 4. Reuse discipline — CLEAN

- Bound to `storage/base::TransportArtifacts`; the four additions are optional fields on the existing
  `TransportHttpRequestArtifacts`. No sibling artifact model, no new artifact file, no new disk path.
- Header extraction is one owner: `http_transport::snapshot_headers` is the only `items(multi=True)` in the tree;
  `codex/transport::_snapshot_headers` and `flow_state::_header_items` are both deleted, and `flow_state`,
  `codex/transport` and `addon_handlers` all call the shared one.
- Body policy is one owner per side: `http_transport::decoded_http_body_bytes` for the decoded body
  (`request_pipeline::parse_request_ir`, `artifacts::extract_response`, `persist_unparsed_http_exchange`) and
  `raw_http_body_bytes` for the wire bytes. `artifacts::request_raw_bytes` is deleted; the only surviving
  `get_text()` outside `http_transport` is `credential_refresh.py:79` on an httpx response, unrelated.
- New home `transport_matters/http_transport.py` sits at the src root, not under `codex/`, 138 lines, and imports only
  `storage.base` + `transport_redaction`. No cycle: verified that `import transport_matters.codex.transport` does not
  pull `exchange_recorder` (`sys.modules` check), and the function-local import kept in `derive_http_transport` is the
  repo's documented lightweight-package-surface convention (`codex/__init__.py` docstring), not a cycle workaround —
  correct to keep.
- No new helper duplicates an existing owner. `header_artifacts` replaces `_header_models`; dead
  `codex/transport::_message_event_type` was removed on the way past.

---

## Findings

### MAJOR — `request_raw_bytes` silently changes unit, with no discriminator for readers

`api/src/transport_matters/wire_store_observer.py:68` (`_request_body_evidence`), used at `:120` and `:152`.

The Postgres column `wire_exchange.request_raw_bytes` (added in `0008_wire_store`) has always held
`len(artifacts.request_raw)`, the **decoded** body size. This PR redefines it to
`transport.request.original_body_size_bytes`, the **on-the-wire encoded** size, for every row that has an HTTP
transport, and the test change at `test_wire_store_observer.py` swaps `assert write.request_raw_bytes ==
len(artifacts.request_raw)` for `== 987`, confirming the redefinition is deliberate. No rename, no backfill, no
column comment, and the new sibling column `request_body_decoding_diverged` cannot act as a discriminator because
`NULL` means both "row written before this PR" and "row with no transport evidence".

Failure scenario: a Codex request with `content-encoding: gzip`, 12,400 decoded bytes compressed to 2,100 wire bytes.
Before the deploy the row records 12400; after it records 2100. `SELECT avg(request_raw_bytes) FROM wire_exchange`
over a window spanning the deploy averages two different units with no way to partition them. Concretely inside this
repo, `session/test_wire_writer.py:249-252` uses this value as the denominator of the storage-reduction gate
(`stored <= 0.04 * write.request_raw_bytes`, message "stored N of M wire bytes"): for the same live gzip'd exchange the
numerator stays the compressed-JSON blob while the denominator drops ~6x, so the reduction a live-fed row reports
changes without any change to what was stored.

Fix shape: either keep `request_raw_bytes` meaning decoded size and add `request_wire_bytes` for the new fact, or
migrate the column with a backfill/`NULL`-out so old rows are distinguishable. Both are cheap next to a column whose
unit depends on the write date.

### MINOR — `decoded_http_body_bytes` fallback re-raises the ValueError it exists to absorb

`api/src/transport_matters/http_transport.py:45`.

The `get_text()` call is wrapped, but the fallback `getattr(message, "content", None)` is not: `getattr`'s default
only suppresses `AttributeError`. mitmproxy's `Message.content` is a property documented as "may raise a `ValueError`
when the HTTP content-encoding is invalid" (`mitmproxy/http.py`, `get_content(strict=True)` re-raises).

Failure scenario: a request with `content-encoding: gzip` and a truncated gzip body. `get_text()` raises, the except
swallows it, `getattr(request, "content", None)` raises `ValueError`, and it propagates out of
`exchange_recorder/__init__.py:204 persist_unparsed_http_exchange`, which has no guard — the unparsed exchange is never
recorded and the addon's error path is entered instead of the capture path. `parse_request_ir` happens to be inside a
`try`, which is why the main path survives.

This shape was inherited from the deleted `artifacts::request_raw_bytes` (whose docstring claimed "never raising on bad
bodies" — the claim was already false), but this PR makes it the single owner and widens it to the main request and
response paths, so it is the right moment to fix. mitmproxy already owns this exact policy: `get_text(strict=False)`
returns surrogate-escaped UTF-8 and never raises, collapsing all three branches to one call.

### MINOR — URL query strings are now persisted for every provider, and redaction has no URL rule

`api/src/transport_matters/http_transport.py:58` (`path=getattr(request, "path", "")`) and
`transport_redaction::redact_transport_artifacts`.

mitmproxy's `Request.path` includes the query string (the PR's own fixture uses `/v1/messages?beta=true`), and
redaction operates on header lists only. Until this PR that surface was Codex-only; it is now every provider.

Failure scenario: any provider or proxy configuration that carries a credential as a query parameter
(`?key=`, `?access_token=`) writes it verbatim into `transport.json`, and `storage/disk.py:410`'s read-side repair pass
will never clean it because the pass only rewrites headers. None of the three current providers do this, which is why
this is Minor and not a Blocker — but header-only redaction is now the sole guard over a much wider surface, and a
URL-side rule belongs next to the header rules while the surface is being widened.

### MINOR — every request now waits on an extra artifact write before being forwarded

`api/src/transport_matters/exchange_recorder/__init__.py:352` (`persist_http_provisional_exchange`).

The provisional persist gained `transport=transport`, so the pre-forward path now builds and redacts a transport
artifact and writes an additional `transport.json` per request inside the awaited request hook. mitmproxy forwards only
after the hook resolves, so this is added latency on the live wire path for every captured request, for every provider.
It is additive capture, not mutation, and the write is off-loop on the storage thread pool — but the brief asks
explicitly whether anything delays the request, and this does. Worth a deliberate decision (defer the transport write to
finalize, or accept it and note why) rather than an accident of where the field was added.

### MINOR — `_header_value` silently prefers the last duplicate header

`api/src/transport_matters/http_transport.py:133`.

`for header_name, value in reversed(headers)` returns the last occurrence, with no comment explaining why. mitmproxy's
own `Headers.get` joins duplicates instead. For a request carrying two `content-length` or two `content-encoding`
headers, the recorded "original" value is the last one, which is not necessarily the one the upstream server acted on —
so the evidence silently picks a side of an ambiguity it is supposed to be recording. Either document the choice or
record all occurrences.

---

## Explicitly checked, not findings

- `body_decoding_diverged` is honest: `decoded_body` is the same `raw` handed to the adapter and stored as
  `request_raw`, `original_body` is the pre-mutation `raw_content`, so the flag means exactly "what we stored differs
  from what crossed the wire". For `application/json` mitmproxy infers utf-8 (`net/http/headers::infer_content_encoding`),
  so a plain JSON request does not produce a false positive; a body with a UTF-8 BOM or no `content-type` (latin-1
  fallback) correctly reports divergence with `original_content_encoding` unset.
- `original_content_encoding` / `original_content_length` are read from the pre-mutation header snapshot, and
  `original_body_size_bytes` from the pre-mutation `raw_content` — none are re-derived after decoding. Item 5 of the
  brief found no post-decode impostor.
- `merge_http_transport_artifacts` is safe on truthiness (`existing.request or finalized.request`): pydantic v2
  `BaseModel` defines neither `__bool__` nor `__len__`, so an empty-but-present request model cannot be dropped.
- `build_http_transport_artifacts`'s `AssertionError` branch is unreachable (redaction returns `None` only for a `None`
  input it never receives), but it is a cheap total-function guard against the `Optional` signature. Left alone.

---

# Delta verification — sha `8f706213`

Revision `c23691aa` → `8f706213` (`git merge-base --is-ancestor` confirms the reviewed commit is still an ancestor).
Deltas only; my 5 findings, plus the cross-check on the newly-covered unparsed path. Tree pristine, no writes.

Evidence run on the new sha: `api/.venv/bin/python -m pytest -q src/transport_matters`
→ **3407 passed, 0 failed, 294 errors**, every error still `MissingDatabaseConfigError`. The error count rose by one
because the delta adds one more DB-backed test (`test_shared_capture_runtime_persists_unparsed_request_evidence`).
Delta-specific non-DB tests run green: `test_http_request_evidence.py` + `exchange_recorder/test_unparsed.py` → 11 passed.
Still not executed here (no Postgres): `session/test_wire_request_body_divergence_migration.py`,
`session/test_wire_writer.py`, and the two DB-backed observer tests.

**Verdict: 4 RESOLVED, 1 PARTIAL, 0 UNRESOLVED. Disclosure still clean, including the new unparsed route.**

## MAJOR `request_raw_bytes` unit change — RESOLVED

The fix is genuinely additive, and the code matches the summary.

- `wire_store_observer.py:69` `_request_body_evidence` now returns `len(artifacts.request_raw)` as the first element on
  **both** branches, so `request_raw_bytes` is written from exactly one expression and keeps the meaning it has always
  had. The encoded size moved to a separate return slot feeding the new `request_wire_bytes`.
- `migrations/versions/0034_wire_request_divergence.py` is a single `ALTER TABLE … ADD COLUMN request_wire_bytes integer,
  ADD COLUMN request_body_decoding_diverged boolean`. No `DEFAULT`, no `UPDATE`, no backfill, no rewrite of any existing
  row; `downgrade` drops both. Old rows keep their stored `request_raw_bytes` and get `NULL` in both new columns, so
  `request_wire_bytes IS NULL` is its own discriminator.
- `session/test_wire_request_body_divergence_migration.py` proves it end to end: a row inserted at revision 0033 with
  `request_raw_bytes = 12400` reads back after upgrade as `('ex-existing', 12400, None, None)`, alongside a
  post-upgrade row `('ex-new', 12400, 2100, True)`.
- The two columns cannot be conflated by a reader: separate fields on `session/wire_store::WireExchangeWrite`, separate
  entries in `dao_statements::_WIRE_EXCHANGE_REPLACE_COLUMNS`, separate SQL columns, and each written from one source.

Every consumer I enumerated reads the column it means. `grep` over the tree for both names shows:
`session/test_wire_writer.py:250-253`'s storage-reduction gate still divides by `request_raw_bytes`, i.e. the decoded
size it always used (`wire_writer_test_support.py`'s misleading "TRUE wire body size" comment was corrected to
"decoded Tier 1 body size" in the same commit); `storage/disk::DiskStorageBackend.read_exchange`,
`harnesses/certification_run_reader::read_captured_exchange`, `api/v1/exchanges.py` and
`www/packages/core/src/types/transport.ts` contain **no reference to either column** — they read the transport artifact
(`original_body_size_bytes`), not the wire store, so none of them can pick up the wrong one.

## MINOR `decoded_http_body_bytes` ValueError — PARTIAL

The raise is genuinely fixed. `http_transport.py:35` now calls `get_text(strict=False)` (mitmproxy's own non-raising
lossy decode) with a `TypeError` shim for test doubles, and every remaining exception path falls to
`raw_http_body_bytes`, which is a plain `raw_content` attribute read that cannot raise. The unguarded
`getattr(message, "content", None)` that re-raised `ValueError` into `persist_unparsed_http_exchange` is gone.

**What remains: the byte-exact fallback was lost.** Previously an undecodable-charset body reached `message.content`
and was persisted verbatim. Now `get_text(strict=False)` surrogate-escapes it and `.encode("utf-8", errors="replace")`
collapses each undecodable byte to `?` (0x3F — verified in the repo interpreter: `b'{"a":"\xff\xfe"}'` persists as
`b'{"a":"??"}'`). The original bytes are unrecoverable from the stored artifact.

Failure scenario: a request whose body decompresses to non-UTF-8 bytes and which the adapter then rejects. It lands on
`persist_unparsed_http_exchange` — the path whose docstring says "raw bytes preserved", and the exact path the other
reviewer's Major just made carry request evidence — and `request_raw` on disk no longer matches what crossed the wire.
`body_decoding_diverged` correctly reports that they differ, so the record is honest, but the bytes are gone.

Fix: keep `get_text(strict=True)` for the happy path and fall back to `message.get_content(strict=False)`, which
returns the exact decoded bytes (or the raw compressed bytes if the content-encoding is broken) and never raises,
before falling to `raw_http_body_bytes`. This regression follows from the `strict=False` shape I recommended, so I am
flagging it rather than treating my own finding as closed.

## MINOR URL query strings unredacted — RESOLVED

`transport_redaction::_redact_query` is applied to `transport.request.path` and `transport.upgrade.path` inside
`redact_transport_artifacts`, so the URL now inherits all three existing gates (build-time, disk write, disk read
repair) rather than a new bespoke one. Name matching reuses `_header_is_sensitive` and adds `_SENSITIVE_QUERY_NAMES`
plus `-key/-password/-secret/-signature` suffixes, normalizing percent-encoding and `_`→`-`, so `?access_token=`,
`?api_key=` and `?%6Bey=` all match. Proven by
`test_http_request_artifacts_mark_encoded_body_divergence_and_redact`, which now asserts
`/v1/messages?beta=true&access_token=[redacted]&key=[redacted]` — the non-sensitive `beta` is preserved.

No defect introduced: `_redact_query` returns `(path, False)` when there is no `?` or no sensitive field, and the
`changed` flags are OR-ed per part, so a clean artifact still short-circuits to `(transport, False)`. That matters —
it keeps `certification_run_reader.py`'s "needs redaction repair" guard and `storage/disk::read_exchange`'s rewrite
from firing on artifacts that need nothing.

## MINOR extra pre-forward write — RESOLVED

The ask was a deliberate decision rather than an accident of placement, and that is what landed:
`exchange_recorder/__init__.py:385` now carries "The request hook awaits Tier 1 persistence before forwarding.
Including transport here keeps the original boundary snapshot durable if the process exits before a response arrives."
The cost is unchanged and now stated, with a reason that outweighs it. Closed.

## MINOR `_header_value` last-duplicate — RESOLVED

`http_transport.py:135` now collects every occurrence and joins with `", "`, matching mitmproxy's own
`Headers.get` join semantics instead of silently picking a side. Proven by
`test_http_request_artifacts_fold_repeated_evidence_headers` (`"2, 3"`, `"gzip, br"`).

No defect introduced: nothing parses `original_content_length` numerically. `www/packages/core/src/types/transport.ts`
types it `string | null`, and the only numeric field any consumer reads is `original_body_size_bytes` (an int, read by
`wire_store_observer`), which is unaffected.

## Cross-check: request evidence through `persist_unparsed_exchange` — disclosure still CLEAN

The new route is `addon_handlers.py:209` → `persist_unparsed_http_exchange` →
`build_http_transport_artifacts(provider=adapter.name, request=request_artifacts)` →
`persist_unparsed_exchange(transport=…)` → `ExchangeArtifacts(transport=…)` → `persist_exchange`.

It reaches disk through the same two gates as every other path and adds no third route:
`build_http_transport_artifacts` redacts unconditionally (it remains the only HTTP `TransportArtifacts` constructor in
the tree), and `storage/disk.py:544` redacts again on write. `adapter.name` is `"anthropic"` / `"codex"` / `"grok"`, and
`TransportArtifacts.provider` is a plain `str`, so the provider stamp is correct on this path too. The Postgres leg is
new (`register_unparsed_exchange_sink` → `WireStoreObserver.on_unparsed_exchange` → `_submit_exchange`) but carries
only sizes, the divergence flag and IR — no headers and no URL. `test_parse_failure_preserves_encoded_request_evidence`
proves the artifact survives a parse failure and lands on disk with the encoded-side evidence intact.

Two observations on this path, neither a defect:

- No test asserts redaction **on the unparsed path itself**, even though its `_Request` fixture already carries
  `authorization: Bearer secret`. Redaction is proven for the constructor and for the parsed path; one extra assertion
  in `test_parse_failure_preserves_encoded_request_evidence` would close the gap directly rather than by composition.
- The body is now decoded three times per unparsed request: `parse_request_ir`, `addon_handlers.py:211`, and
  `exchange_recorder/__init__.py:212`. Each is a full gunzip of a body that just failed to parse. One value threaded
  through would do.

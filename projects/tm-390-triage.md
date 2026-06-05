# TM #390 review findings — triage against current `main`

Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`, branch `main` at `5591db86`, clean.
Source report: `/Users/alphab/.mdx/projects/tm-390-review-findings.jsonl` (final assistant message,
last line — the review's output contract was a JSON array, not a `ReportFindings` call).

## Preamble

**10 findings in the report. 10 survive as CONFIRMED. 0 STALE, 0 FALSE, 0 OUT-OF-SCOPE.**

The unscoped-pass caveat turned out not to bite. The review ran in the
`feat/capture-request-evidence` worktree (which became PR#391) and reviewed the whole merged tree,
but all ten surviving findings landed inside #390's baseline files — `baseline_capture.py`,
`baseline_evidence.py`, `baseline_store.py`, and the `observe_request_json` block #390 added to
`request_inventory.py`. PR#391 (`5591db86`) touched none of those files (`git show --stat 5591db86`:
wire/HTTP/exchange-recorder/session paths only), so nothing went stale.

Every defect below is reproduced live against current `main`. Nine were reproduced by executing
code through the repo interpreter (`uv run python`, 3.14); the tenth is a static duplication audit
verified by grep. The four baseline test modules
(`test_baseline_capture.py`, `test_baseline_evidence.py`, `test_baseline_harvest.py`,
`test_request_inventory.py`) are **26 passed** on current `main` — every confirmed defect is
untested, none is a failing test.

Where a reviewer sub-claim was imprecise inside an otherwise-correct finding, it is flagged under
**Reviewer precision** in that section.

Ordered CONFIRMED-first, then by severity.

---

## 1. `capture-title-collision`

- **id**: `capture-title-collision`
- **claim**: `baseline_capture::_wait_for_correlated_exchange` correlates the owned exchange by
  prompt substring across every completed exchange and raises on more than one match, so Claude
  Code's first-turn title/topic side request — which embeds the user prompt verbatim — makes the
  harvest fail or succeed only by race.
- **verdict**: **CONFIRMED**
- **evidence**:
  - `api/src/transport_matters/baseline_capture.py` :: `_wait_for_correlated_exchange` — the only
    discriminator is `request_contains_text(raw, prompt)`; two or more matches raise
    `BaselineCorrelationError`, one match returns.
  - `api/src/transport_matters/baseline_capture.py` :: `_capture_probe` — the prompt is delivered as
    `CapturedRunRequest(initial_prompt=prompt, delivery_id=delivery_id)`, so every exchange the
    launch produces from that prompt is a substring match.
  - Prior-art proof the repo already knew about the title turn: `git show 573a4538^:api/src/transport_matters/baseline_harvest.py`
    selected the owned exchange with `has_tool_schemas` (tool schemas present ⇒ real first turn,
    title request has none), and `git log --all -S titletra` shows the deleted fixture
    (`test_baseline_harvest.py`, exchange id `titletra-…`) that covered exactly this case. #390
    (`573a4538`) removed both.
  - The replacement fixture in `api/src/transport_matters/test_baseline_capture.py` makes the side
    exchange `{"prompt":"startup"}` — promptless — so the regression is not covered.
    `test_harvest_rejects_ambiguous_prompt_exchange_and_cleans_up` asserts the raise as intended
    behaviour.
  - The unique correlator the reviewer names is real and already wired for this exact launch:
    `api/src/transport_matters/controlplane/envelope.py` :: `extract_delivery_id` /
    `launch_delivery_fields`; `api/src/transport_matters/captured/context.py` already stamps the
    launch fields when `initial_prompt` and `delivery_id` are set; and
    `api/src/transport_matters/wire_store_observer.py` already correlates through
    `extract_delivery_id`.
- **severity**: **high** — this is the primary live path (`baseline_harvest --harness claude`) and
  it either raises or picks nondeterministically depending on side-request latency.
- **replay_road**: **YES** — a replay comparator that re-issues "the captured request" is only as
  trustworthy as the rule that decided which exchange was ours.
- **Reviewer precision**: `extract_delivery_id` matches on a whole-block `prompt_digest`, not a
  substring, which is why it discriminates the title turn (whose prompt is template-wrapped). Worth
  confirming against one live title-request capture before treating it as a drop-in.

---

## 2. `fingerprint-unmasked-volatiles`

- **id**: `fingerprint-unmasked-volatiles`
- **claim**: `classify_aba` hashes every leaf that is identical across the three same-session probes
  into `static_fingerprint`, including Claude Code's own date/cwd system-prompt text, so an
  unchanged harness re-harvested the next day reports BREAKING.
- **verdict**: **CONFIRMED** (reproduced)
- **evidence**:
  - `api/src/transport_matters/baseline_evidence.py` :: `classify_aba` — `static_records` is built
    from `probe.raw_nodes` / `probe.inventory.leaves` (raw, unmasked) for every pointer classified
    exactly `(STABLE,)`, then `canonical_digest`ed. `_classify_pointer` marks a pointer `STABLE`
    whenever ≥2 probes agree, and appends `STRUCTURALLY_OPTIONAL` only when presence varies — so
    "constant within this one A/B/A run" is sufficient.
  - `api/src/transport_matters/baseline_evidence.py` :: `compare_baseline_bundles` — any
    `static_fingerprint` inequality short-circuits to `DriftOutcome.BREAKING`.
  - The repo already owns the correct masks and the fingerprint bypasses them:
    `api/src/transport_matters/session/wire_normalization.py` :: `_CROSS_LAUNCH_MASKS` carries
    `Today's date is \d{4}-\d{2}-\d{2}` and `<cwd>…</cwd>` rules, and its own comment states the
    intent — "so two launches of the same harness and model hash equal".
    `api/src/transport_matters/baseline_capture.py` :: `_build_probe_evidence` calls
    `normalize_request(..., cross_launch=True)` and stores the result as `normalized_request`, which
    `classify_aba` never reads.
  - Live reproduction (`uv run python`): two bundles differing only in the system-prompt date leaf
    (`2026-08-17` → `2026-08-18`) →
    `compare_baseline_bundles` returns `breaking-drift`, reason `stable baseline fingerprint changed`.
  - `no_system_prompt=True` in `_capture_probe` suppresses TM's injected prompt only; Claude Code's
    own environment preamble is unaffected.
- **severity**: **high** — the drift signal is unusable for its stated purpose from day 2 onward.
- **replay_road**: **YES** — the fingerprint is the comparator's equality primitive.

---

## 3. `grok-reply-never-detected`

- **id**: `grok-reply-never-detected`
- **claim**: `_json_has_assistant_role` requires a literal `role`/`type == "assistant"` that Grok
  transcript records never carry, so `--harness grok` can never reach `transcript_complete`.
- **verdict**: **CONFIRMED** (reproduced)
- **evidence**:
  - `api/src/transport_matters/baseline_capture.py` :: `_json_has_assistant_role` — matches only
    `value.get("role") == "assistant"` or `value.get("type") == "assistant"`.
  - `api/src/transport_matters/index/adapters/grok.py` :: `GrokAdapter.normalize` — Grok's
    `updates.jsonl` records are JSON-RPC notifications (`method: "session/update"`,
    `params.update.sessionUpdate`); the assistant role is *derived* (`role = "user" if update_type
    == "user_message_chunk" else "assistant"`) and never appears literally. `grok_updates_path`
    confirms the transcript file this snapshot mirrors.
  - Grok is advertised by the CLI: `api/src/transport_matters/harnesses/__init__.py` ::
    `_GROK_DESCRIPTOR` has both `wire_provider="grok"` and a `launch` boundary, so
    `list_launch_eligible_descriptors` returns it and
    `api/src/transport_matters/baseline_harvest.py` :: `main` accepts `--harness grok`.
  - Live reproduction: `_transcript_has_reply` over a two-record Grok-shaped transcript
    (`user_message_chunk` then `agent_message_chunk`) returns `False`; the same file in Claude shape
    returns `True`.
  - The per-harness seam already exists: `TranscriptAdapter.normalize` in
    `api/src/transport_matters/index/adapters/base.py`.
- **severity**: **high** — `baseline_harvest --harness grok` burns the full 180 s timeout and then
  raises `BaselineCorrelationError` on every run.
- **replay_road**: **YES** — a provider-neutral replay comparator cannot rest on a Claude-shaped
  transcript probe.

---

## 4. `verdict-inconsistency`

- **id**: `verdict-inconsistency`
- **claim**: `compare_baseline_bundles` returns different verdicts for the same underlying harness
  change depending on probe-presence flicker, and only EXACT/BREAKING are tested.
- **verdict**: **CONFIRMED** (reproduced)
- **evidence**:
  - Live reproduction, one added constant JSON field against the same reference bundle:
    - present in all 3 probes → classified `(STABLE,)` → enters `static_records` → fingerprint
      differs → **`breaking-drift`**;
    - the *same* field present in only 2 of 3 probes → classified
      `(STABLE, STRUCTURALLY_OPTIONAL)` → excluded from `static_records` → fingerprint equal →
      falls through to the `allowed` set → **`compatible-drift`**.
  - `api/src/transport_matters/baseline_evidence.py` :: `classify_aba` (the
    `item.classifications == (EvidenceKind.STABLE,)` filter) and `_classify_pointer` (the
    `STRUCTURALLY_OPTIONAL` append) are the two lines that produce the split.
  - `compare_baseline_bundles` never reads `classifications` for the EXACT branch, so a
    `PROMPT_DERIVED` leaf degrading to `UNKNOWN` still returns EXACT: neither `static_fingerprint`
    (the leaf varies across probes, so it is in neither bundle's records) nor `observed_schema`
    (pointer/kinds/present_in only) carries the classification.
  - A pointer removed in the candidate is absent from `candidate_evidence`, so the
    `pointer in candidate_evidence` conjunct fails and the result is INSUFFICIENT even for a
    demonstrably optional pointer.
  - The `changed_pointers` set comprehension in `compare_baseline_bundles` scans
    `candidate.observed_schema` with `next(...)` per pointer — O(P²).
  - Test coverage: `api/src/transport_matters/test_baseline_evidence.py` ::
    `test_bundle_comparison_reports_exact_and_breaking_drift` is the only comparison test, and the
    only `DriftOutcome` assertions in the module are `EXACT` and `BREAKING`.
- **severity**: **high** — the verdict is the product. An operator cannot act on a signal that flips
  between "breaking" and "compatible" on probe noise.
- **replay_road**: **YES** — this function *is* the comparator the replay primitive will extend.

---

## 5. `dual-canonical-json`

- **id**: `dual-canonical-json`
- **claim**: `request_inventory::_canonical_json_bytes` is a second canonical-JSON serializer beside
  `canonicalization::canonical_json`, they disagree on number rendering, and one artifact therefore
  mixes two hashing disciplines.
- **verdict**: **CONFIRMED** (reproduced)
- **evidence**:
  - `api/src/transport_matters/request_inventory.py` :: `_canonical_json_bytes` (`json.dumps(...,
    sort_keys=True, separators=(",", ":"))`) vs
    `api/src/transport_matters/canonicalization.py` :: `canonical_json` / `_canonical_number`
    (integral floats rendered via `str(int(value))`).
  - Live reproduction: `canonical_json(1.0)` → `"1"`; `json.dumps(1.0, …)` → `"1.0"`.
    `observe_request_json(b'{"temperature":1.0}')` yields node digest `d0ff5974…` = sha256("1.0"),
    while `sha256(canonical_json(1.0))` = `6b86b273…`. Two digests for one value.
  - Both disciplines land in the same artifact: `RequestJsonNode.sha256` (via
    `request_inventory::_observe_native`) is computed with `_canonical_json_bytes`, and
    `baseline_evidence::classify_aba` then feeds those digests to `canonical_digest` for
    `static_fingerprint`.
  - `request_inventory::_json_kind` duplicates `api/src/transport_matters/json_tags.py` ::
    `json_kind` (same six-name JSON kind mapping; the inventory copy raises on unsupported input
    where the shared one stays total).
  - `git show 573a4538 -- api/src/transport_matters/request_inventory.py` confirms
    `_canonical_json_bytes`, `_json_kind`, `_observe_native`, `observe_request_json`, and
    `request_contains_text` are all #390 additions — in scope.
- **severity**: **medium** — no crash today, but every node digest in the baseline artifact is
  computed under a discipline the rest of the system does not use, and a future canonicalization fix
  must be applied twice.
- **replay_road**: **YES** — replay compares digests; two disciplines in one artifact is a
  correctness hazard the comparator inherits.

---

## 6. `transcript-read-fragility`

- **id**: `transcript-read-fragility`
- **claim**: `_transcript_has_reply` reads the transcript with `read_text` + `splitlines` and bails
  on the first bad line, so a torn multibyte read crashes the harvest and a raw U+2028 hides the
  reply; the repo already owns `iter_complete_records` as the transcript-iteration seam.
- **verdict**: **CONFIRMED** (reproduced, all three sub-claims)
- **evidence**:
  - `api/src/transport_matters/baseline_capture.py` :: `_transcript_has_reply` —
    `path.read_text(encoding="utf-8").splitlines()`, and `except json.JSONDecodeError: return False`
    aborts the whole file on one bad line.
  - `api/src/transport_matters/baseline_capture.py` :: `_wait_for_correlated_exchange` — the
    `_transcript_has_reply` call sits outside the `try`, whose only handler is
    `CertificationMintingError`, so a `UnicodeDecodeError` escapes to `main` and exits 1.
  - Live reproduction:
    - torn multibyte read (file truncated mid-UTF-8 sequence) →
      `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc3 … unexpected end of data`;
    - a raw U+2028 inside the user line → `False` (the same file without it → `True`), so the reply
      is undetectable until the 180 s timeout.
  - Existing seam: `api/src/transport_matters/index/record_ingest.py` :: `iter_complete_records` —
    takes bytes, skips malformed complete lines rather than aborting, and refuses to consume the
    half-written trailing line.
- **severity**: **medium** — both failures need a live, concurrently-appended transcript, but the
  poll loop reads exactly that, ten times a second, for up to 180 s.
- **replay_road**: **YES** — transcript completion is the gate that decides when correlation is
  allowed to run.

---

## 7. `provenance-never-annotated`

- **id**: `provenance-never-annotated`
- **claim**: `build_request_inventory` is called without `annotations` in the live path, so every
  leaf carries unknown provenance, `_session_derived` can never be True, `SESSION_GENERATED` is
  test-only, and `repeat_a_outcome` is INSUFFICIENT for every live bundle.
- **verdict**: **CONFIRMED** (reproduced)
- **evidence**:
  - `api/src/transport_matters/baseline_capture.py` :: `_build_probe_evidence` calls
    `build_request_inventory(captured.request_raw, capture=provenance,
    internal_request=captured.request_ir)` — no `annotations`.
  - `grep -rn "build_request_inventory("` over `src/transport_matters` shows the only caller that
    passes `annotations=` is `test_baseline_evidence.py`. The other non-test call site,
    `baseline_evidence::ProbeEvidence.validate_raw_evidence`, also omits them.
  - `api/src/transport_matters/request_inventory.py` :: `_make_leaf` falls back to
    `_unknown_provenance()` (kind `"unknown"`) when no annotation exists;
    `api/src/transport_matters/baseline_evidence.py` :: `_session_derived` requires
    `leaf.provenance.kind == "session-derived"`, so it is unreachable from the live path.
  - `api/src/transport_matters/baseline_evidence.py` :: `_repeat_a_outcome` allows only
    `{SESSION_GENERATED, STRUCTURALLY_OPTIONAL}`, so *any* non-container leaf differing between A1
    and A2 lands in INSUFFICIENT.
  - Live reproduction: an A/B/A set differing only in one per-launch id leaf →
    `repeat_a_outcome = insufficient-evidence`, that pointer classified `(UNKNOWN,)` with reason
    "controlled probes do not prove the value source", leaf provenance `unknown`.
  - The test name itself documents the gap:
    `test_aba_marks_only_annotated_session_values_as_session_generated`.
- **severity**: **medium** — the harvest still writes a bundle, but the A/A repeat check inside it
  carries no signal, and one classification branch is dead outside tests.
- **replay_road**: **YES** — the A/A leg is what proves a value is allowed to differ on replay.
- **Reviewer precision**: the reviewer's specific attribution ("Claude's `metadata.user_id` embeds a
  per-launch session id") is **UNVERIFIED** — no repo evidence for that field; blocked by having no
  live Claude first-turn capture on disk. The mechanism above holds regardless of which leaf varies.

---

## 8. `current-pointer-absolute-path`

- **id**: `current-pointer-absolute-path`
- **claim**: the current-baseline pointer persists `str(path)` even though the path is derivable, so
  a relocated store makes `read_current_baseline` hard-fail and permanently blocks all future
  harvests of that cell.
- **verdict**: **CONFIRMED** (reproduced)
- **evidence**:
  - `api/src/transport_matters/baseline_store.py` :: `write_baseline_bundle` writes
    `{"artifact_schema_version": 1, "bundle_id": …, "path": str(path)}`, while `_bundle_path`
    already derives the same path from `output` + cell + `bundle_id`.
  - `api/src/transport_matters/baseline_store.py` :: `read_baseline_bundle` resolves the stored path
    and raises `ValueError("baseline bundle reference is outside the bundle store")` when it is not
    under `(output / "bundles").resolve()`.
  - `api/src/transport_matters/baseline_capture.py` :: `harvest_controlled_baseline` calls
    `read_current_baseline` **before** launching anything, so the failure is not recoverable by
    re-running.
  - Live reproduction: write a bundle into `<tmp>/store-a`, `shutil.move` the store to
    `<tmp>/store-b`, then `read_current_baseline(output=store-b, …)` →
    `ValueError: baseline bundle reference is outside the bundle store`. The persisted pointer still
    names the old absolute path.
  - The same file already models the pointer as `_CurrentBundlePointer` (used on read), but the
    write hand-builds the dict.
- **severity**: **medium** — no data loss, but the cell is bricked until someone hand-deletes the
  pointer file, and the failure message does not say so.
- **replay_road**: **YES** — the replay comparator loads its reference through this same pointer.

---

## 9. `dry-duplication`

- **id**: `dry-duplication`
- **claim**: the #390 code re-implements helpers that already exist (dependency unpack, prompt
  digest, sha256 pattern, base64+digest validation, probe-order check, current-pointer model), and
  the hand-rolled dependency unpack skips the `check_session_store` preflight.
- **verdict**: **CONFIRMED** (verified by grep; one sub-claim FALSE, one imprecise — see below)
- **evidence**:
  - **Preflight gap (behavioural, the load-bearing part).**
    `api/src/transport_matters/capture_rpc.py` :: `CaptureLeaseRegistry.register_capture` runs
    `self._dependencies.check_session_store` before `_prepare_with_dependencies`.
    `api/src/transport_matters/baseline_capture.py` :: `_capture_probe` hand-unpacks the same eight
    dependency callables into `prepare_captured_run` and never calls `check_session_store`, even
    though `captured/dependencies.py :: CapturedRunDependencies` carries it and
    `baseline_harvest::main` builds the full `default_claude_run_dependencies()`. The harvest can
    launch into a session store that every other capture path refuses.
  - **Prompt digest.** `controlplane/envelope.py :: prompt_digest` is exactly
    `hashlib.sha256(text.encode("utf-8")).hexdigest()`; it is re-inlined at
    `baseline_capture.py :: _build_probe_evidence` and
    `baseline_evidence.py :: BaselineBundle.validate_probe_contract`.
  - **Digest pattern.** `request_inventory.py :: Sha256Hex` exists and `baseline_evidence.py`
    already imports from that module, yet `Field(pattern=r"^[0-9a-f]{64}$")` is re-declared four
    times in `baseline_evidence.py` (`TranscriptEvidence.sha256`, `ProbeEvidence.prompt_sha256`,
    `ProbeEvidence.raw_request_sha256`, `BaselineBundle.static_fingerprint`).
  - **Probe-order check.** `baseline_evidence.py :: _require_probe_order` and
    `baseline_evidence.py :: BaselineBundle.validate_probe_contract` perform the identical
    `labels != (A1, B, A2)` check in the same module.
  - **Base64+digest validation.** `TranscriptEvidence.validate_bytes` and
    `ProbeEvidence.validate_raw_evidence` each re-implement decode-then-compare-digest.
  - **Current pointer.** `baseline_store.py :: write_baseline_bundle` hand-builds the dict that
    `baseline_store.py :: _CurrentBundlePointer` already models.
  - Governing rules quoted by the reviewer are real: `~/.claude/CLAUDE.md` ("Never re-declare a type
    that already lives somewhere else") and the repo root `CLAUDE.md` ("DO NOT REINVENT CODE. FIND
    CODE").
- **severity**: **medium** — the preflight gap is a genuine behavioural hole; the rest is
  maintenance cost against explicit project rules.
- **replay_road**: **NO** — none of this blocks a trustworthy comparator, though the prompt-digest
  and `Sha256Hex` consolidations are cheap to fold into whatever fixes findings 1 and 5.
- **Reviewer precision**:
  - "`_json_contains_text` duplicates `request_contains_text` from the same diff" is **FALSE**.
    `request_contains_text` takes bytes and runs the strict inventory parser;
    `_json_contains_text` takes an already-decoded transcript record. Only the recursive-walk shape
    overlaps; they are not interchangeable.
  - "neither forwards `check_session_store`" is imprecise: `prepare_captured_run` has no such
    parameter at all, and `capture_rpc` invokes the preflight separately. The gap it names is real;
    the mechanism it describes is not.

---

## 10. `redundant-hashing`

- **id**: `redundant-hashing`
- **claim**: the capture path re-serializes and re-hashes the whole request many times over
  (per-node subtree hashing, validator re-parse on every model construction, write-then-read-back,
  per-poll-tick re-parse), and the bundle embeds raw request plus transcripts base64 in `indent=2`
  JSON.
- **verdict**: **CONFIRMED** (mechanisms verified; cost measured)
- **evidence**:
  - `api/src/transport_matters/request_inventory.py` :: `_observe_native` hashes
    `_canonical_json_bytes(value)` at **every** node, so the root re-serializes the whole document —
    O(bytes × depth).
  - `api/src/transport_matters/baseline_evidence.py` :: `ProbeEvidence.validate_raw_evidence`
    re-runs both `observe_request_json` and `build_request_inventory` on every construction — and
    `ProbeEvidence` is constructed on build, on write read-back, and on reference load.
  - `api/src/transport_matters/baseline_store.py` :: `write_baseline_bundle` immediately calls
    `read_baseline_bundle` and re-validates the entire bundle it just wrote.
  - `api/src/transport_matters/baseline_capture.py` :: `_wait_for_correlated_exchange` calls
    `request_contains_text` per candidate exchange per 100 ms tick, and that helper goes through
    `_observe_native` — full parse plus per-node hashing on every tick.
  - `api/src/transport_matters/baseline_evidence.py` :: `compare_baseline_bundles` — O(P²)
    `next(...)` scan (also noted in finding 4).
  - `api/src/transport_matters/atomic_io.py` :: `write_atomic_json` uses `json.dumps(value,
    indent=2)`, and `ProbeEvidence` carries `raw_request_base64` plus every transcript's
    `bytes_base64` — three probes' worth per bundle.
  - Measured on a synthetic 78 KiB Claude-shaped first-turn request (18 tool schemas, `uv run
    python`): `build_request_inventory` 11.1 ms, `observe_request_json` 6.3 ms,
    `request_contains_text` 6.2 ms — the last one being per poll tick, per candidate exchange.
- **severity**: **low** — real waste, but nothing a user observes breaking. At 10 Hz over a 180 s
  timeout the poll loop is a few percent of one core; the visible cost is bundle size.
- **replay_road**: **NO** — a slow comparator is still a correct comparator. Worth folding into the
  same pass as finding 5 (both live in `_observe_native`), not worth its own change.

---

## Reproduction artifacts

Probe scripts used for the live reproductions (scratchpad, not committed, no source files touched):

- `…/scratchpad/probe.py` — findings 3 and 6 (`_transcript_has_reply` against Grok-shaped records,
  raw U+2028, torn multibyte read).
- `…/scratchpad/probe2.py` — findings 2, 4, 7 (`classify_aba` / `compare_baseline_bundles` verdicts).
- `…/scratchpad/probe3.py` — finding 8 (store relocation).
- `…/scratchpad/probe4.py` — finding 10 (inventory cost measurement).

Scratchpad root:
`/private/tmp/claude-501/-Users-alphab-Dev-LLM-DEV-helioy-transport-matters/5f2f475f-cafc-4744-895f-e64e24e86ac0/scratchpad`

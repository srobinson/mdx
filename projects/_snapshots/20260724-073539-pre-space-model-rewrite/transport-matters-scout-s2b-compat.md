# Scout: S2b compatibility releases and channel state

Baseline: main @ 070e10e1 (S2a merged). Tree pristine, no source writes.
Governing docs: RUNTIME-SURFACING-S2-PLAN.md (section "S2b. Compatibility releases and
channel state" plus "Decisions folded into this plan"), COMPATIBILITY-PUBLISHING.md
(headings "Certification", "Publication"), HARNESS-COMPATIBILITY.md (sections "Harness
compatibility release", "Channel state", "Signed data updates", "Outcome codes").

## Reuse Map

Every S2b capability, with the existing owner or the searches that prove none exists.

| S2b capability | Existing owner | Verdict |
| --- | --- | --- |
| Release / channel-state / block models | none found. Searched `CompatibilityRelease\|ChannelState\|VersionBlock\|compatibility_release` across `api/src`, `www/packages`, `packages` (py+ts): zero code hits, docs only. Field shapes are contract-named in HARNESS-COMPATIBILITY.md (`HarnessCompatibilityRelease`, `CompatibilityChannelState`, `VersionBlock`). | new `harnesses/compatibility.py` per plan Ownership table |
| Model conventions | `harnesses/__init__.py` (`HarnessCapabilities` pydantic `ConfigDict(frozen=True)`, frozen dataclasses); api/CLAUDE.md Pydantic v2 rules | reuse conventions |
| Harness identity | `harnesses/__init__.py` `HarnessId`, `get_harness_descriptor`, `registered_harness_ids` | reuse as-is |
| Canonical JSON | `canonicalization.py` `canonical_json` (layer 1, stdlib only) | reuse as-is |
| Canonical digest helper | none found as shared symbol. One inline combo exists: `controlplane/launch_service.py` `_intent_fingerprint` (sha256 over `canonical_json`). | add one public `canonical_digest()` in `canonicalization.py`; refactor `_intent_fingerprint` to call it so there is one owner, not two inline copies |
| Signature verification | none found. Searched `ed25519\|cryptography\|nacl\|hmac\|verify_signature` in `api/src`: zero hits; every `signature` hit is a wire thinking-signature or file-stat cache signature. No crypto dependency in `api/pyproject.toml`. | new verifier interface + stub that REJECTS all cached channel updates |
| Monotonic sequence validation | none found. Searched `monotonic` in `api/src`: only `time.monotonic()` deadlines. | new, inside channel-update validation |
| Package-embedded signed data | `channel.py` `_channel_specs` is the exact pattern: `importlib.resources.files("transport_matters") / "channel-specs.json"`, `lru_cache`, schema check, duplicate-id check. Wheel inclusion via `api/pyproject.toml` `[tool.hatch.build.targets.wheel].artifacts` (explicit entry per data file — a new embedded JSON needs its own entry). | mirror pattern; new artifacts entry required |
| Channel-scoped cache home | `storage_roots.py` `default_storage_root` (honors `TRANSPORT_MATTERS_HOME`, falls back to `channel.py` `resolve_channel_spec().home`); `stable` and `preview` already exist in `channel-specs.json` | reuse as-is for the mutable cached copy location |
| Version probe (raw) | `capabilities.py` `_probe_harness_version` / `detect_harnesses` (raw first line of `--version`) | reuse as observation input |
| Version normalization + ordering | none found as shared helper, and no `packaging`/semver dependency in `api/pyproject.toml`. Partial prior art: `cli/codex_session.py` `resolve_codex_cli_version` extracts trailing semver from `codex --version` with a `0.0.0` sentinel — a codex-only fork of the same job. | new pure ordering helper in the compatibility module; do NOT add a third `--version` interpretation (see Quality Map D1). Recommend a minimal normalized-tuple compare, no new dependency; contract requires "cannot order → unknown" which `packaging.Version` does not give for free |
| Range + block matching | none found (no matching logic anywhere; outcome codes exist only in HARNESS-COMPATIBILITY.md "Outcome codes"). | new pure function per plan S2b item 4 |
| Installed adapter-revision registry | none found. Searched `revision` in `api/src` non-test: only Alembic DB revisions and `session/timeline_stream.py` projection revisions — unrelated. Release manifests reference 13 adapter revisions; "adapter revision availability" validation needs an installed-set to check against. | new: mint initial revision identifiers naming existing adapters and one registry constant |
| Embedded release evidence (claude 2.1.211, codex 0.144.4) | COMPATIBILITY-PUBLISHING.md "Certification"/"Publication" define the evidence fields; plan decision fixes baselines (claude 2.1.211, codex 0.144.4, minimum = baseline) | data content, built by hand for S2b; digests must be self-consistent (test-enforced) |
| Fixture matrix testing | `pytest.mark.parametrize` precedent throughout (`test_runtime_registry.py` et al.); shared-data contract test precedent `harnesses/test_registry.py` `test_shared_descriptor_fixture_matches_registry` | reuse patterns |
| JSON read + validate idiom | `runtime_registry.py` `read_runtime_template_capabilities` (pydantic `model_validate`, chained domain errors) — the repo-convention idiom | reuse for manifest validation |

Flagged planned-new items that could duplicate an existing owner if built carelessly:
a canonical digest helper (owner must be `canonicalization.py`, not a private copy in
`harnesses/`), a version parser (must not fork `resolve_codex_cli_version` a second
time), and an embedded-JSON loader (must mirror `channel.py`, not invent a new idiom).

## Quality Map

Scope swept: `harnesses/`, `capabilities.py` + test, `runtime_registry.py` + test,
`channel.py`, `canonicalization.py`, `cli/codex_session.py`, `api/v1/meta.py`,
`api/v1/capabilities.py`, `shared/harness_descriptors_v1.json`. Analysis only.

Sizing: green. Largest source file `runtime_registry.py` 330 LOC; largest test
`test_runtime_registry.py` 642 LOC (watch — nearing the 700 hard limit; S2b adds
nothing to it). No function near 150 LOC.

- **D1 duplication (pre-existing, S2b-adjacent):** two parallel `--version` probes.
  `capabilities.py` `_probe_harness_version` (2s timeout, raw first line, None on
  failure) vs `cli/codex_session.py` `_run_codex_cli_version` (5s timeout,
  trailing-semver extraction, `0.0.0` sentinel, mtime-keyed cache). Same
  responsibility, divergent semantics. S2b's normalization must land as the one shared
  owner; folding `codex_session` onto it is S2c/S2f territory but S2b must not create
  a third interpretation.
- **D2 idiom split (pre-existing):** `channel.py` validates embedded JSON with
  hand-rolled `_require_str/_require_mapping/_require_port` helpers while
  `runtime_registry.py` uses pydantic `model_validate`. S2b should use the pydantic
  idiom (api/CLAUDE.md convention); no need to rewrite `channel.py`.
- **D3 latent duplication:** `launch_service.py` `_intent_fingerprint` inlines
  sha256-over-`canonical_json`. Adding a second inline copy for release digests would
  create real duplication; promote one public helper to `canonicalization.py` (layer 1
  stays stdlib-only — sha256 is stdlib) and adopt it in both.
- **Dead code (minor):** `capabilities.py` `detect_harness` (singular, by-id) has zero
  production callers — only `test_capabilities.py` uses it (`detect_harnesses` and
  `detect_harness_descriptor` carry all production traffic). Candidate for deletion in
  a touching PR.
- **Boundary health: good.** `harnesses/` is a pure leaf (no I/O); `capabilities.py`
  (subprocess I/O) imports it downward; REST projections (`api/v1/meta.py`,
  `api/v1/capabilities.py`) are thin `from_*` mappers. S2b must preserve the split:
  pure models + matching in the leaf, cache I/O separated.
- **Ubiquitous-language watch:** "channel" now means the install channel
  (`channel.py` `ChannelSpec`, stable/preview homes and ports) and will also mean the
  compatibility channel (`CompatibilityChannelState.channel`). They align 1:1 and the
  cached copy lives under the channel-scoped home, so S2b must derive the channel id
  from `resolve_channel_spec`, never a second channel enum.
- **Descriptor JSON pattern note:** `shared/harness_descriptors_v1.json` is a
  contract-test fixture (Python registry is authoritative; TS and Python both assert
  against it). Compatibility releases are the opposite: data is authoritative and read
  at runtime — the right precedent is `channel-specs.json`, not the descriptor pair.

## Plan

All S2b code is backend-only, no Postgres (executor tables are S2c), no REST surface
(inventory is S2g). One new module plus data, one small shared-helper promotion.

1. **`canonicalization.py`:** add public `canonical_digest(value) -> str` (sha256 hex
   over `canonical_json`); switch `launch_service._intent_fingerprint` to it
   (mechanical, byte-identical output).
2. **`harnesses/compatibility.py`:** frozen pydantic models field-for-field from the
   contract: `HarnessCompatibilityRelease`, `HarnessRouteCompatibility`,
   `HarnessModelCompatibility`, `CompatibilityChannelState`, `VersionBlock`, plus the
   manifest envelope. Pure version normalization/ordering (unorderable → unknown,
   cannot launch). Pure `match_release(...)` range + block evaluation returning the
   contract outcome codes (`harness_update_required`, `harness_version_blocked`,
   `harness_version_unknown`, `compatibility_release_unavailable`).
3. **Installed adapter revisions:** mint initial revision identifiers for the existing
   claude/codex adapters and expose one installed-set registry constant for
   "adapter revision availability" validation.
4. **Channel-update validation:** `SignatureVerifier` interface + stub rejecting every
   mutable cached update; schema validation (pydantic idiom), digest recomputation via
   `canonical_digest`, monotonic sequence, adapter-revision availability. Only
   package-embedded data can activate; signature fields populated and round-tripped.
5. **Embedded data:** `compatibility_releases_v1.json` package data (claude 2.1.211,
   codex 0.144.4, minimum = baseline, both channel pointers `paused`, no grok release)
   loaded via the `channel.py` pattern; new `[tool.hatch.build.targets.wheel]`
   artifacts entry; a self-consistency test recomputes every embedded digest.
6. **Tests:** colocated `harnesses/test_compatibility.py` fixture matrices — below
   minimum, unknown, blocked per scope (version/route/target/release), supersession
   clears, paused/revoked/missing pointer, tampered digest, stale sequence, missing
   adapter revision, cached-update rejection, embedded activation, digest
   self-consistency. Split the file before 700 LOC if the matrices demand it.

Gates: `just check` and `just test` verbatim. (`cd api && just migration-smoke` is in
the S2 plan gates; S2b adds no migration, run it anyway as the plan lists it.)

Reuse verdict: the compatibility layer itself is genuinely greenfield (no models, no
crypto, no sequence validation anywhere), but every supporting mechanism S2b needs has
an existing owner to reuse — canonical JSON, embedded-data loading, channel homes,
version probing, validation idiom — and three careless-duplication traps are named
above.

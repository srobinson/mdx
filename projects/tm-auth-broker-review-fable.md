---
title: PR #335 credential broker core — review (fable, reuse & shape)
type: review
project: transport-matters
pr: 335
commit: 0f4e63df
reviewed_against: ~/.mdx/projects/tm-auth-broker-scout.md, ~/.mdx/projects/tm-auth-broker-probe.md
created: 2026-07-27
---

# PR #335 review — reuse and shape pass

Verdict: **approve with one important finding (small fix) and two minors.** No invariant
is violated; the important finding is a confidentiality leak vector for the fleet refresh
token, which is the asset this whole feature exists to protect, so it should land before
the seam-swap slice wires real traffic through the write path. Tree confirmed pristine
before and after review (`git status --porcelain` empty at `0f4e63df`).

## 1. Reuse map conformance — clean

- `credential_broker.CredentialBroker.mint` uses `lock.py:exclusive_file_lock`;
  `credential_broker.MintedCredential.write_to` uses `atomic_io.py:write_atomic_bytes`
  (0600 default, asserted in `test_minted_credential_never_contains_refresh_token`).
  No new lock or atomic-write primitive appeared.
- `credential_broker.SecurityOwnerCredentialStore` follows the `harnesses/probes/runner.py`
  pattern: injectable `run`, hard timeout, `stdin=DEVNULL`, and a strict redaction boundary —
  command output and exception objects never reach the raised error
  (`test_security_store_error_does_not_surface_command_output`,
  `test_security_store_discards_sensitive_spawn_exception`).
- `credential_broker.HttpxTokenExchanger` follows the `cli/runs_health.py` idiom: thin,
  injectable `post`, explicit timeout, no retry machinery.
- Wire shape matches the probe exactly: URL `platform.claude.com/v1/oauth/token` (probe's
  correction over the design's claude.ai), JSON body field set, headers, `expires_in`
  seconds→ms via the same `*1000` conversion the binary uses, rotated `refresh_token`
  required (stricter than the binary's retain-old fallback, which is what the rotation
  invariant demands and the probe endorses).

## 2. Placement and boundary — clean

src-root pure leaf; imports only `atomic_io`, `lock`, stdlib, and httpx. No import into or
from `cli/`, no session/storage/server coupling, no private cross-module imports. Ports are
`Protocol` (shape-only contracts per api/CLAUDE.md), effects behind injected callables.
Consistent with the two-plane rule; matches the `lock.py`/`manifest.py` precedent named in
the scout report.

## 3. Over-engineering — straight answer: no, with two speculative edges to cut

506 lines decompose into: ~95 lines of fail-closed field validation at the two
deserialization boundaries (keychain document, token response) — required by the
fix-at-the-entry-boundary rule and the fail-closed design; ~85 lines keychain adapter;
~70 lines HTTP adapter; ~60 lines broker; the rest docstrings/exports/errors. There are no
retry ladders, no caching beyond the stored credential, no async, one lock, one code path.
The one subtle piece of machinery — the repeated try/except/else + `_safe_cause` dance —
is load-bearing, not decoration: raising outside the `except` block is the only way to get
`__context__ is None`, and httpx exceptions carry the request object containing the
refresh token, so ordinary chaining would retain the secret in the traceback. Tests pin
`__context__ is None` explicitly.

Two things I would cut as speculation the invariants do not require:
- the NFC normalization (finding 3 below);
- the fabricated `"claude-code-user"` fallback account (finding 4 below).

The 6× repetition of the sanitize dance could be one `_call_sanitized(fn, message)` helper
(~25 lines saved, centralizes the subtlety) — cosmetic, one clause, not a round.

## 4. Return type — structural, not convention

`MintedCredential` is frozen/slots with exactly `access_token`, `expires_at_ms`, `scopes`;
no refresh field exists to carry.
`test_minted_credential_never_contains_refresh_token` pins the field list by introspection
(`dataclasses.fields`), asserts the written document contains no `refresh` substring, and
asserts repr suppression. A future field addition breaks the test. Structural: yes.

## 5. Perturbation claims — all four checked, all bind

- **return-before-persist**: `test_rotation_is_persisted_before_mint_returns` asserts the
  shared event log equals `["read", "exchange", "write"]`; removing the persist (or
  reordering) changes the log. Binds.
- **return-on-writeback-failure**: `test_write_back_failure_raises_instead_of_returning_access`
  injects a failing store write inside `pytest.raises(CredentialWriteBackError)`; a
  return-instead-of-raise fails the raises block, and the store-unchanged assertion pins
  no partial persist. Binds.
- **read-before-lock-without-reread**: `test_concurrent_caller_blocks_then_rereads_without_second_exchange`
  parks caller 1 inside the exchange (event-gated fake), submits caller 2, then asserts the
  store's second read does NOT occur within the window — a pre-lock read fires immediately
  and fails that assertion; a missing re-read double-exchanges and fails
  `exchanger.calls == [...]` (length 1) and `write_count == 1`. Binds for both buggy
  variants. Timing window (0.2s) is on the safe side: a race loss produces a false FAIL,
  not a false pass.
- **DESIGN_CLIENT_ID substitution**: `test_http_exchanger_pins_client_id_and_request_shape`
  holds an independent literal copy of the expected id, asserts equality with the module
  constant, inequality with `DESIGN_CLIENT_ID`, and that the captured request body carries
  the expected id. Binds.

## 6. client_id pin — correct and single-sourced

`credential_broker.CLAUDE_CODE_OAUTH_CLIENT_ID` is the exact production literal, defined
once in the module and referenced (not re-typed) at the one use site; the only second copy
is the test's deliberate independent pin, which is the mechanism that catches drift. No
third location.

## Findings, ranked by value

**F1 — important, security. `SecurityOwnerCredentialStore.write` passes the fleet refresh
token through process argv.** The rotated credential document is hex-encoded into the
`security add-generic-password -X <hex>` argument list. argv is visible to same-user
processes for the lifetime of the subprocess, and Transport Matters' own product is
spawning same-user agent processes that run arbitrary tool commands — a launched agent
polling `ps` during a refresh window can harvest the owner refresh token, the exact
crown-jewel asset. `security(1)`'s own usage text calls argv-passed secrets insecure. Fix
is small and stays inside the adapter: run `security -i` and feed the
`add-generic-password … -X <hex>` command line via stdin (quote the service name), which
`_run_command` already supports shape-wise (`input=` instead of `stdin=DEVNULL` for the
write path). Read path is unaffected (secret arrives on stdout, already captured).

**F2 — integration risk to carry into slice 3's brief, not a slice-1 code defect.
Keychain ACL will fail-closed the first real read.** The `~/.claude-auth` item was created
by the claude binary, so its ACL trusts that binary, not `/usr/bin/security`; the first
`find-generic-password -w` triggers a GUI consent prompt, and the adapter's 2s timeout
converts it into `CredentialBrokerError` before any human can answer. Fail-closed is the
right behavior (no hang, invariant preserved), but it means the doctor bootstrap check must
own the one-time grant flow (longer timeout or explicit user instruction to "Always
Allow"), or bootstrap re-creates the item via the CLI so the CLI is the trusted creator.
Verified read-only on the real item (`acct = "alphab"`, attribute read, no secret access):
the account default (`$USER`) is correct on this machine.

**F3 — minor. NFC normalization of the config dir before hashing is unverified
speculation.** `SecurityOwnerCredentialStore.__init__` normalizes the path with
`unicodedata.normalize("NFC", …)` before `sha256`. The probe did not establish that the
binary normalizes; if it hashes the raw `CLAUDE_CONFIG_DIR` string, a decomposed-Unicode
path yields a different service suffix than the binary's, and (worse, in slice 3) teardown
would delete a nonexistent item and leak the real one. Identity for ASCII paths, so
today's fleet home is unaffected. Cut it, or verify the binary's behavior and cite it.

**F4 — minor. The `"claude-code-user"` fallback account can split-brain the keychain
item.** If `USER` is unset/invalid (launchd contexts), `write` under a fabricated account
creates a second item for the same service while the binary's item keeps the now-consumed
refresh token — the exact fleet-revocation failure. Raise `CredentialBrokerError` when no
valid account can be resolved instead of inventing one; read already fails closed, write
must too.

**Cosmetic (one clause):** fold the six repeated sanitize dances into one
`_call_sanitized` helper.

## Builder trust verdict (requested standing assessment)

High on this slice. The build followed the scout map to the letter (both named primitives
reused, both adapter idioms followed, placement as recommended), the perturbation tests
genuinely bind rather than decorate, and the two boundary-validation layers are exactly
where the repo's lessons say they belong. The misses (argv exposure, ACL reality) are both
in the gap between "code shape" and "how macOS actually behaves at runtime" — consistent
with the known component-boundary blind spot, and exactly what the real-binary smoke in
slice 3 would have caught late. Nothing suggests shortcut-taking; test rigor is above
repo baseline.

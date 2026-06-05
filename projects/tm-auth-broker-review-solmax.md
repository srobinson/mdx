# PR #335 credential broker trust boundary review

Verdict: issue, 5 findings.

## Boundary

- Reviewed PR #335 at `0f4e63dfda28a904de0fa992684e69467a933d99` against base
  `95affedc668ab37e1fe239cb66f17271a1345362`.
- The PR contains only `api/src/transport_matters/credential_broker.py` and
  `api/src/transport_matters/test_credential_broker.py`.
- The worktree was pristine immediately before this report was written.
- Review was static. I ran no test suite, token exchange, Claude authentication command,
  keychain operation, or provider request. The brief reports CI 9/9 successful.

## Findings

### 1. Critical: the fleet refresh token enters process arguments and can enter captured traceback locals

Location: `api/src/transport_matters/credential_broker.py:SecurityOwnerCredentialStore.write`,
`api/src/transport_matters/credential_broker.py:HttpxTokenExchanger.exchange`,
`api/src/transport_matters/credential_broker.py:CredentialBroker._exchange`

`SecurityOwnerCredentialStore.write` serializes the complete rotated owner document, converts
it to hexadecimal, and passes that reversible value as the argument after `security -X`.
Hexadecimal encoding provides no secrecy. macOS exposes command arguments through process
inspection, so any process running as the owner can sample the short lived `security` process,
decode the argument, and obtain the fleet refresh token. A launched agent runs as that same
owner. It can then exchange the stolen token, invalidate the broker copy, and gain the account
authority carried by the credential.

The exception tests cover rendered messages and explicit causes only. On an HTTP failure,
`HttpxTokenExchanger.exchange` raises from a frame whose locals still include
`refresh_token` and the JSON request body. `CredentialBroker._exchange` preserves that
traceback with a bare re-raise. Any error serializer configured to capture frame locals will
write the token into its error payload. The current repository has no such serializer enabled,
so this second path is conditional. The process argument exposure is unconditional during
every rotation.

Use a keychain write primitive that never places secret bytes in argv. Before launch errors
gain a serialized surface, ensure exceptions cross the broker boundary without secret bearing
frames or locals.

### 2. Critical: a successful remote rotation can be lost before local persistence

Location: `api/src/transport_matters/credential_broker.py:CredentialBroker.mint`,
`api/src/transport_matters/credential_broker.py:HttpxTokenExchanger.exchange`

The lock orders exchange before keychain write, but it cannot make the remote commit and local
write atomic. A concrete failure sequence is:

1. The endpoint accepts refresh token R0, revokes it, and creates R1.
2. The response is lost during a read timeout, or the broker dies after receiving it and before
   `OwnerCredentialStore.write` completes.
3. The keychain still contains R0 and the process lock releases.
4. The next launch re-reads R0, sends a revoked token, and fails. Every launch remains broken
   until the owner logs in again.

`test_exchange_failure_leaves_owner_credential_untouched` models a fake exchanger failing
before it returns. It cannot distinguish that case from a response lost after the server
committed the rotation. A keychain write error has the same fleet consequence even though
`CredentialWriteBackError` correctly withholds the access token.

No client protocol can recover an unknown R1 unless the endpoint supplies idempotency or
reuse semantics. The broker still needs a durable in doubt state before the request and an
explicit recovery path, so later callers stop before retrying R0 and report the real fleet
condition.

### 3. High: the single writer boundary is optional at the public API

Location: `api/src/transport_matters/credential_broker.py:__all__`,
`api/src/transport_matters/credential_broker.py:CredentialBroker.__init__`,
`api/src/transport_matters/credential_broker.py:HttpxTokenExchanger.exchange`

`CredentialBroker` accepts an arbitrary `lock_path`. The path need not be absolute, canonical,
or derived from the owner credential identity. Two processes can target the same keychain item
with different lock paths, acquire different inodes, re-read the same R0, and exchange it
concurrently. Refresh token reuse can then revoke the fleet token and force manual login.

The module also exports the production `HttpxTokenExchanger`, whose public `exchange` method
can be called without any lock or write back. The invariant that one component owns exchange
therefore depends on every future caller following a convention.

The concurrency test creates one broker and one shared path, so it proves the happy
configuration only. A module owned production factory should derive one canonical lock from
the owner identity and keep the production exchanger private. Tests can continue to inject
ports inside that boundary.

### 4. High: `minimum_ttl` is a refresh trigger rather than a returned credential postcondition

Location: `api/src/transport_matters/credential_broker.py:CredentialBroker.mint`,
`api/src/transport_matters/credential_broker.py:OwnerCredential.rotated`

After an exchange, `mint` persists and returns the new credential without checking whether its
`expires_in` satisfies `minimum_ttl`. For example, a caller requesting nine hours will refresh
an owner credential, persist the endpoint's expected eight hour token, and return that token
as if the floor were met. A later caller repeats the unnecessary rotation. A shorter endpoint
lifetime can let the last home in a launch batch start near expiry and fail before its intended
window ends.

The production clock is wall time, so a backward clock correction also inflates the apparent
remaining lifetime of a cached token. The tests hold time constant and cover only a 120 second
exchange result against a 30 second floor.

Persist every returned rotation first, then validate the resulting access expiry against a
conservative current time. If the new token cannot satisfy the requested floor, fail the
launch after preserving R1. The configured floor also needs to include the maximum batch start
delay and intended run window.

### 5. Medium: the keychain test reports success for a runner that never persists anything

Location: `api/src/transport_matters/credential_broker.py:SecurityOwnerCredentialStore.write`,
`api/src/transport_matters/test_credential_broker.py:test_security_store_uses_expected_keychain_item_with_fake_runner`

Production treats `security` exit status zero as durable success. The fake runner returns zero
for every write but never changes the value returned by the next read. The test inspects the
outbound bytes only. It also omits the `-X` flag from the asserted command prefix. A missing or
malformed flag, or a runner that reports success without updating the item, can therefore keep
this test green. The first fails in production only after remote rotation. The second lets the
broker hand out access while the owner keychain remains on revoked R0.

The current `-X` syntax matches the local `security(1)` manual, so this finding is a proof gap
rather than evidence that the present invocation is malformed. A stateful fake should model
the exact account and service item, then prove that a post-write read returns the complete R1
document. Given the consequence of false success, production should also verify the stored
rotation before returning access.

## Confirmed properties

- With one canonical lock file, `CredentialBroker.mint` blocks concurrent callers and re-reads
  the owner credential after acquisition.
- A reported write failure raises `CredentialWriteBackError` and no access credential returns.
- `MintedCredential` structurally has no refresh token field, writes an access only document,
  uses mode `0600`, and suppresses its access token from `repr`.
- Credential dataclass representations and the tested exception strings do not reveal token
  values.
- The four PR body perturbation claims bind statically: returning before persistence, returning
  on write failure, reading before lock acquisition, and substituting the design client ID each
  contradict a named assertion in the colocated tests.

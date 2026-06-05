# PR #342 auth lifecycle review

## Review boundary

- PR: `#342`, `ml/auth-lifecycle` into `main`
- Reviewed head: `583153a3cd7cc427791f636bd02cccd5aef212b7`
- Live diff: 13 files, 463 additions, 84 deletions
- Hosted gates: 9 successful, one optional check skipped
- Method: static and read only
- No login, setup token, token exchange, captured run, database write, Keychain
  operation, channel home access, or credential value access occurred.

## Verdict

Found 1 blocker, 2 major findings, and 2 minor findings.

The success path has solid foundations. `MintedCredential` has no refresh field,
serializes only the access credential shape, writes a 0600 file into a 0700
directory, and all broker entry points share the same blocking lock. Run home
teardown removes the symbolic link without following it. The findings concern
failure paths around that success path.

## 1. Blocker: broker failure can restore a refresh bearing native credential link

### Location

- `api/src/transport_matters/cli/home_overlay.py:_link_overlay_credential_files`
- `api/src/transport_matters/cli/home_overlay.py:_mint_claude_credential`
- `api/src/transport_matters/cli/runtime_home.py:plan_runtime_home`

[Fallback after mint failure](https://github.com/littleorgans/transport-matters/blob/583153a3cd7cc427791f636bd02cccd5aef212b7/api/src/transport_matters/cli/home_overlay.py#L412-L443)

[Native auth source selection](https://github.com/littleorgans/transport-matters/blob/583153a3cd7cc427791f636bd02cccd5aef212b7/api/src/transport_matters/cli/runtime_home.py#L89-L125)

### Inputs and state

1. A managed Claude launch uses a runtime overlay.
2. The fleet broker fails. Examples include an unavailable owner credential,
   a failed exchange, or `runtime-access/.credentials.json` being a directory.
3. The native Claude home has a plaintext `.credentials.json` containing the
   normal owner OAuth shape, including `refreshToken`.

### What happens

`_mint_claude_credential` catches the failure and returns `False`.
`_link_overlay_credential_files` then follows the legacy path and links the
runtime home directly to `auth_source_home_dir/.credentials.json`.
`plan_runtime_home` selects the native Claude home as that auth source for an
overlay.

The branch test explicitly preserves this fallback:

[Fallback test](https://github.com/littleorgans/transport-matters/blob/583153a3cd7cc427791f636bd02cccd5aef212b7/api/src/transport_matters/cli/test_home_seed_credentials.py#L230-L274)

### Impact

The launched process receives the owner document through a symbolic link,
including its refresh capability. It can rotate the single use refresh token.
Concurrent fallback launches can then rotate independently and revoke the
fleet. This defeats the access only boundary the PR introduces.

### Basis and caveat

The default macOS Keychain path often leaves no native plaintext file, in which
case the fallback creates no link. Plaintext and custom source homes remain
supported states, and this branch handles them explicitly. A broker failure
should fail the Claude launch or leave it unauthenticated without linking an
unvalidated source document.

## 2. Major: a reworded genuine expiry is silent at the refresh boundary

### Location

- `api/src/transport_matters/credential_refresh.py:_is_expired_oauth_response`
- `api/src/transport_matters/credential_refresh.py:refresh_expired_claude_credential`
- `api/src/transport_matters/addon_handlers.py:handle_response`

[Exact classifier and silent false return](https://github.com/littleorgans/transport-matters/blob/583153a3cd7cc427791f636bd02cccd5aef212b7/api/src/transport_matters/credential_refresh.py#L35-L72)

[Ignored classifier result](https://github.com/littleorgans/transport-matters/blob/583153a3cd7cc427791f636bd02cccd5aef212b7/api/src/transport_matters/addon_handlers.py#L432-L465)

### Inputs and state

1. The shared access token expires.
2. The provider returns HTTP 401 and `error.authentication_error`.
3. The provider changes punctuation or wording in the expiry message.

### What happens

The exact string comparison returns `False`. The caller ignores that result.
No warning, health state, or live status event identifies an authentication
response that nearly matched the expiry classifier. Normal exchange
persistence still runs when request state exists, so forensic evidence can
exist without a refresh specific signal.

Claude Code clears its credential cache on the 401 and rereads the access only
file. The file still contains the expired access token and has no refresh
token. Recovery fails and the long running session receives the authentication
failure.

### Impact

A provider text change restores the original long run failure mode. Operators
see the downstream authentication failure but receive no Transport Matters
signal that refresh classification declined the response.

### Basis and caveat

The narrow exchange trigger is appropriate because revocation, invalid scope,
and malformed credentials must not rotate a single use refresh token. The
near miss needs a loud, sanitized signal. A managed Claude response with
HTTP 401 and `authentication_error` can report a classifier miss without
logging the body or starting an exchange.

## 3. Major: shared artifact corruption is neither diagnosed nor repaired

### Location

- `api/src/transport_matters/credential_broker.py:CredentialBroker._write_shared_credential`
- `api/src/transport_matters/cli/home_overlay.py:claude_fleet_credential_error`

[Shared artifact writer](https://github.com/littleorgans/transport-matters/blob/583153a3cd7cc427791f636bd02cccd5aef212b7/api/src/transport_matters/credential_broker.py#L395-L428)

[Doctor checks only the owner credential](https://github.com/littleorgans/transport-matters/blob/583153a3cd7cc427791f636bd02cccd5aef212b7/api/src/transport_matters/cli/home_overlay.py#L461-L476)

### Inputs and state

While one or more runs are live, the shared file is deleted, truncated to zero
bytes, replaced by a directory, or made unreachable through a dangling parent.

### What happens

The inspected Claude Code binary checks the target before main request
attempts. A missing target clears the cached credential and reloads no access
token. A zero byte document fails JSON loading. A directory cannot be read as
the credential document. In these states Claude can fail before sending a
request, so the proxy receives no expiry 401 that could invoke the broker.

A later launch or a matched 401 can recreate a missing regular file. A
directory at the destination makes the atomic replacement fail. The current
doctor path checks that the fleet home is a directory and that the owner
Keychain item can be read. It never validates the shared file, its type, its
JSON shape, its permissions, or its link consumers.

### Impact

One damaged shared artifact can stop every live run on its next credential
check while doctor still reports the owner credential as healthy. The first
visible symptom can be a login prompt inside each pane.

### Basis and caveat

Atomic replacement prevents broker initiated partial documents. This finding
concerns deletion, external corruption, hard crash residue, and unexpected
filesystem state. A safe health check can validate shape and location without
printing any value.

## 4. Minor: the protected directory can be a symbolic link

### Location

- `api/src/transport_matters/credential_broker.py:CredentialBroker._write_shared_credential`
- `api/src/transport_matters/atomic_io.py:_write_temp`

[Directory creation without containment validation](https://github.com/littleorgans/transport-matters/blob/583153a3cd7cc427791f636bd02cccd5aef212b7/api/src/transport_matters/credential_broker.py#L424-L428)

[Temporary write under the resolved parent](https://github.com/littleorgans/transport-matters/blob/583153a3cd7cc427791f636bd02cccd5aef212b7/api/src/transport_matters/atomic_io.py#L45-L58)

### Inputs and state

`~/.claude-auth/runtime-access` already exists as a symbolic link to another
directory.

### What happens

`mkdir(..., exist_ok=True)` accepts a link that resolves to a directory.
`chmod` follows it, and the atomic writer creates and replaces
`.credentials.json` below the resolved external directory. No containment or
link check rejects this state.

### Impact

The broker can change the permissions of an unrelated directory and replace an
unrelated `.credentials.json` outside the intended fleet auth subtree. The
credential remains 0600 and the resolved directory becomes 0700, which limits
cross account disclosure, but path isolation and data integrity do not hold.

### Caveat

This requires preexisting local filesystem state under the owner controlled
fleet home. The fixed child names prevent string based parent traversal.

## 5. Minor: hard termination can retain a second access token file

### Location

- `api/src/transport_matters/atomic_io.py:write_atomic_bytes`
- `api/src/transport_matters/atomic_io.py:_write_temp`

[Temporary file lifecycle](https://github.com/littleorgans/transport-matters/blob/583153a3cd7cc427791f636bd02cccd5aef212b7/api/src/transport_matters/atomic_io.py#L20-L26)

### Inputs and state

The process is killed after the 0600 temporary file is fully written and
synced, but before `replace` or the `finally` cleanup completes.

### What happens

The randomly named temporary file remains beside `.credentials.json`.
Caught exceptions clean it up, while process death cannot run that cleanup.

### Impact

The directory can contain a stale second access credential, invalidating the
claimed sole entry invariant and extending secret retention. The enclosing
0700 directory and 0600 file prevent ordinary cross account disclosure.

## Requested contract checks

### Concurrency

Holds. Launch minting and proxy 401 minting both construct
`CredentialBroker` for the same fleet home. Every `mint()` acquires
`~/.claude-auth/broker.lock`, rereads the owner under the lock, and exchanges
only below the TTL floor. Ten simultaneous expiry responses serialize. The
first exchanges and persists the rotated owner. The remaining callers reread
the fresh owner and do not exchange again.

[Locked mint path](https://github.com/littleorgans/transport-matters/blob/583153a3cd7cc427791f636bd02cccd5aef212b7/api/src/transport_matters/credential_broker.py#L395-L422)

[Single exchange concurrency proof](https://github.com/littleorgans/transport-matters/blob/583153a3cd7cc427791f636bd02cccd5aef212b7/api/src/transport_matters/test_credential_broker.py#L288-L320)

### Mtime propagation

No independent correctness finding. The broker writes a new temporary inode,
syncs it, and atomically replaces the target. A client stat before the rename
sees the old document and can send the old token. Its resulting expiry 401
forces Claude Code to clear its cache and reread after the proxy refresh. A
client stat after the rename sees the replacement. A coarse timestamp collision
can delay proactive adoption, but the forced 401 reread does not compare mtime.
That fallback depends on the classifier in finding 2.

### Teardown

Holds for an ordinary run home. `shutil.rmtree` unlinks symbolic link entries
and does not descend into their targets. Removing one runtime home therefore
leaves the shared file for every other run.

[Run home teardown registration](https://github.com/littleorgans/transport-matters/blob/583153a3cd7cc427791f636bd02cccd5aef212b7/api/src/transport_matters/captured/context.py#L270-L295)

### Success path isolation

Holds. The shared document is 0600, its immediate directory is 0700,
`MintedCredential` has no refresh field, and serialization includes only
`accessToken`, `expiresAt`, and `scopes`. Error wrappers sanitize underlying
exceptions before launch warnings or proxy logs receive them. Findings 1 and 4
are the paths that escape this success case.

## Re-verification of 8042ccdf

### Review boundary

- Prior reviewed head: `583153a3cd7cc427791f636bd02cccd5aef212b7`
- Re-verified head: `8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5`
- Delta: 20 files, 489 additions, 122 deletions
- Live PR total: 25 files, 935 additions, 189 deletions
- Hosted gates: 9 successful, one optional check skipped
- Method: static, read only, and limited to the delta
- No login, setup token, token exchange, captured run, database write, Keychain
  operation, channel home access, or credential value access occurred.

### Closure summary

| Prior finding | Status | Verified fact |
|---|---|---|
| 1. Native credential fallback | Open | Fresh homes fail closed, while an existing credential file or link in a reused home is retained and can bypass the shared access file. |
| 2. Silent 401 classifier miss | Open | A sanitized warning is written to proxy log files, with no healthy run surface reading those files. |
| 3. Shared artifact corruption | Closed | Doctor validates the artifact and broker minting repairs missing, truncated, and empty directory states or aborts on unsafe state. |
| 4. Linked protected directory | Closed | Broker minting rejects the protected directory when it is already a symbolic link. |
| 5. Hard termination residue | Open | A later mint removes residue, while hard termination still leaves the second file until that later mint. |

Result: 2 of 5 closed.

### Prior finding 1 remains open for reused homes

#### Location

- `api/src/transport_matters/cli/home_overlay.py:_mint_claude_credential`
- `api/src/transport_matters/cli/home_overlay.py:_symlink_file_if_exists`
- `api/src/transport_matters/cli/home_overlay.py:materialize_runtime_home_overlay`
- `api/src/transport_matters/captured/context.py:_prepare_home_and_grant`

[Claude mint and retained target](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/cli/home_overlay.py#L413-L481)

[Overlay reuses existing directory entries](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/cli/home_overlay.py#L155-L187)

[Cleanup registration occurs after successful preparation](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/captured/context.py#L270-L295)

#### Inputs and state

1. A runtime home is reused.
2. Its `.credentials.json` already exists as a file or symbolic link. An
   upgrade can leave the former native credential link in that location.
3. The new broker mint succeeds.

#### What happens

The broker safely writes the shared access document. `_symlink_file_if_exists`
then returns when the runtime target exists or is a symbolic link. It does not
validate or replace that target. The launch proceeds with the retained
credential path, which can still resolve to the native owner document.

When minting fails, the exception aborts every production launch caller checked.
The CLI maps it to exit 2. The capture API maps it to HTTP 503, and no spawn
spec is returned. That half cannot be bypassed by ignoring a boolean result.
However, overlay materialization creates and populates the runtime home before
minting. Cleanup is registered only after preparation returns, so a failed
mint leaves the partial home and any prior credential entry in place.

#### Impact

A reused home can still launch with a refresh bearing native document after a
successful broker mint. The access only boundary remains bypassable on the
specific reused home case requested by this re-verification.

#### Test gap

The new failure test starts with an empty runtime home and proves that fresh
case only.

[Fresh home test](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/cli/test_home_seed_credentials.py#L226-L280)

### Sanitized launch reason holds

The launch error can contain only:

- fixed bootstrap guidance and fixed artifact locations;
- field names and shape validation failures;
- HTTP status codes;
- sanitized operation categories;
- filesystem paths derived from the fleet home or run storage.

Production Keychain reads, writes, token exchange calls, JSON parsing, and
read-back validation pass through sanitized exceptions. The caught filesystem
errors operate on fixed paths that never derive from a credential value. No
branch includes response bodies, credential fields, token fragments, or
request URLs.

[Sanitized launch wrapper](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/cli/home_overlay.py#L426-L465)

[Exact shared document validation](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/credential_broker.py#L88-L125)

### Prior finding 2 remains open because nobody reads the warning

The warning text itself is sanitized. It contains a fixed classifier result and
does not include the response body.

[Sanitized classifier warning](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/credential_refresh.py#L42-L63)

The delivery path differs by launch mode:

| Launch path | Warning destination | Healthy run reader |
|---|---|---|
| Detached desktop | Channel runtime `logs/shared-mitmdump.log` | Nobody |
| Canvas pane | Channel runtime `logs/shared-mitmdump.log` | Nobody |
| Interactive CLI with Claude | Run storage `logs/mitmdump.log` | Nobody |
| Proxy only CLI | Foreground terminal | Operator |

The desktop and Canvas paths use `SharedProxyProcess`, which redirects the
shared proxy process output to `logs/shared-mitmdump.log`.

[Shared proxy log destination](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/shared_proxy/process.py#L65-L128)

`transport-matters tail` reads `runtime/desktop.log`, not the shared proxy log.

[Tail reads desktop log only](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/cli/tail_cmd.py#L25-L46)

The interactive Claude CLI starts mitmdump in the background and redirects it
to the run's `logs/mitmdump.log`. That file is inspected for startup bind
failure and named when mitmdump exits. A healthy long run has no reader or
operator notification for warnings appended there.

[CLI proxy log routing](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/cli/runner.py#L313-L345)

[Foreground applies only without a managed client](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/cli/runner.py#L430-L496)

The change converts code silence into a stored warning. It does not create an
operator facing signal for the three requested managed launch paths.

### Prior finding 3 is closed

`shared_access_credential_error` now validates:

- protected directory presence, type, 0700 mode, and sole entry;
- shared file type, 0600 mode, exact root and OAuth field sets;
- JSON validity and value shapes.

Broker minting overwrites missing or truncated regular files, removes an empty
directory at the file path, and aborts on unsafe states such as a non-empty
directory. Doctor calls this validator after reading the owner credential.

[Artifact health validation](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/credential_broker.py#L483-L528)

[Repair and fail closed paths](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/credential_broker.py#L444-L464)

### Prior finding 4 is closed

The broker checks the protected directory before and after creation, then
rejects an existing symbolic link before chmod or credential write. The new
test proves the external directory remains unchanged.

[Linked directory rejection](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/credential_broker.py#L444-L455)

### Prior finding 5 remains open with bounded recovery

`write_atomic_bytes` still creates a named, fully written temporary file before
replacement. Hard termination between those operations still leaves the file.
The new cleanup runs only when a later broker mint reaches
`remove_atomic_write_residue`.

[Named temporary file and later cleanup](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/atomic_io.py#L20-L70)

The later mint removes the residue and doctor reports the unexpected extra
entry before that. This bounds recovery and detection, while the original
hard termination retention scenario remains possible.

### New blocker: managed Claude cannot launch outside macOS

#### Location

- `api/src/transport_matters/claude_fleet_auth.py:claude_fleet_credential_broker`
- `api/src/transport_matters/cli/home_overlay.py:_link_overlay_credential_files`
- `desktop/src/standaloneSmoke.ts:STANDALONE_SMOKE_HARNESS`

[Production broker rejects every non macOS host](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/claude_fleet_auth.py#L22-L33)

[Every managed Claude overlay now requires broker minting](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/cli/home_overlay.py#L413-L440)

[Standalone smoke now exercises Codex](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/desktop/src/standaloneSmoke.ts#L1-L25)

#### Inputs and state

A user launches a managed Claude run on Linux or another non macOS host.

#### What happens

The old platform guard returned to the native credential link path outside
macOS. The delta removes that guard. Every Claude overlay now requires
`_mint_claude_credential`, while the production broker always raises on a
non macOS platform. The launch aborts before a child process starts.

The replacement non macOS test injects a fake broker. A separate test confirms
that the real factory rejects Linux. The packaged standalone smoke was changed
from Claude to Codex, so the outer packaged gate cannot detect this Claude
regression.

[Tests formalize the split](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/cli/test_home_seed_credentials.py#L69-L92)

#### Impact

All managed Claude launches fail outside macOS. This is a complete harness
availability regression unless the product has intentionally dropped
non macOS Claude support.

#### Caveat

The fleet Keychain design is intentionally macOS specific. The reviewed delta
contains no product contract or platform gate declaring managed Claude itself
macOS only, and the prior implementation explicitly preserved non macOS
launches.

### Codex remains unaffected

Codex bypasses `_mint_claude_credential` and retains the native `auth.json`
link path. The test injects a Claude broker that always raises, then proves
Codex still links the native file. The packaged standalone smoke also completes
through Codex.

[Codex branch and link helper](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/cli/home_overlay.py#L413-L423)

[Codex regression test](https://github.com/littleorgans/transport-matters/blob/8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5/api/src/transport_matters/cli/test_home_seed_credentials.py#L283-L312)

### Other delta

The final commit adds a bundled certifi CA file and sets `SSL_CERT_FILE` for
the packaged backend while preserving an explicit parent setting. This change
supports HTTPS from the standalone Python runtime and is not traceable to the
five review findings. Static inspection found no independent correctness issue
in that path.

## Final delta cb701be1

### Review boundary

- Prior reviewed head: `8042ccdfdd25bd06ff93c81969b2dde7fe5f32f5`
- Final reviewed head: `cb701be1ed7d01f4b833db76a77970c7ac0f56c5`
- Delta: 13 files, 286 additions, 16 deletions
- Hosted gates: 9 successful, one optional check skipped
- Method: static review plus five focused tests and two isolated fault probes
- No login, setup token, token exchange, captured run, database write, Keychain
  operation, channel home access, or credential value access occurred.

### Verdict

Four of the original five findings are closed. The access credential boundary
remains open because callable Claude spawn surfaces bypass it. One previously
reported blocker outside the five remains, and the delta adds one major and one
minor finding.

| Prior finding | Status | Verified fact |
|---|---|---|
| 1. Native credential fallback | Open | Supported CLI, Canvas, and desktop routes now reject a reused native credential, but exported launch surfaces can still construct and spawn Claude without the assertion. |
| 2. Silent 401 classifier miss | Closed | The response hook queues `auth_required` with `provider_event=claude_refresh_classifier_miss` as soon as the complete unmatched 401 is classified. |
| 3. Shared artifact corruption | Closed | Doctor validation and safe state repair remain. The new writer regression below creates a separate corruption window. |
| 4. Linked protected directory | Closed | The protected directory link rejection is unchanged. |
| 5. Hard termination residue | Closed | Credential writes no longer create a second named access credential file. |

Result: 4 of 5 closed.

### Blocker: the claimed Claude spawn boundary is bypassable

The current supported launch graph does converge. CLI launches call
`run_captured_run_on_local_tty`, while Canvas and desktop launches call
`prepare_captured_run`. Both build their provider invocation through
`_build_provider_invocation`.

[Supported provider routing](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/captured/context.py#L337-L420)

The asserted boundary itself has two callable bypasses:

1. `build_claude_captured_invocation` checks identity only when
   `runtime_home_dir` is present. Its public signature permits `None`, then
   constructs a Claude `ManagedClient` from `home_dir` without an assertion.
   The helper remains exported from `captured.run`.
2. `transport_matters.cli.run_children` is publicly exported. It accepts
   arbitrary Claude arguments and environment, constructs `ManagedClient`
   directly, and reaches the PTY spawn path without calling the builder.

[Optional assertion and unchecked client construction](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/captured/claude.py#L119-L152)

[Builder export](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/captured/run.py#L65-L84)

[Direct Claude construction and launch](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/cli/runner.py#L257-L310)

[Public CLI export](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/cli/__init__.py#L87-L101)

This leaves the invariant dependent on caller discipline. A future internal
caller can copy either existing surface and launch Claude with a native
credential document.

### Identity comparison

The comparison follows relative links and link chains through strict
resolution. `samefile` then compares filesystem identity, so hardlinks,
case folded aliases, and a bind mount that reports the same device and inode
match. A symbolic link at the shared path resolves to its target for the
assertion, although normal minting fails closed on that link because the writer
uses `O_NOFOLLOW`.

The comparison has a time of check to time of use window. It runs while the
client descriptor is built. The CLI then starts and waits for the proxy before
spawning the client. The captured run route can return the spawn specification
to another runtime before the client process starts. No open descriptor or
other pinned identity reaches the child. Replacing the runtime credential path
after the assertion and before spawn therefore defeats the check. This requires
concurrent local mutation, but it preserves the same refresh credential impact.

[Check before proxy start and spawn specification return](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/captured/run.py#L239-L290)

### Codex remains unaffected

Codex returns from `_mint_overlay_credential` without constructing a Claude
broker. Its overlay still links the native `auth.json`, and its invocation
builder contains no Claude identity assertion.

[Separate credential branches](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/cli/home_overlay.py#L417-L455)

[Codex client construction](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/captured/codex.py#L174-L203)

The focused Codex overlay test passed with a Claude broker that always raises.

### Mint first ordering

A Claude mint now completes before `_prepare_materialization_dirs` creates the
runtime directory. The focused failure test passed and confirmed that a failed
mint creates neither the runtime directory nor a credential entry.

[Mint before materialization](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/cli/home_overlay.py#L155-L196)

[Failed mint proof](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/cli/test_home_seed_credentials.py#L293-L347)

### Minor: later preparation exceptions still skip runtime home cleanup

Mint first fixes the mint failure case only. `prepare_runtime_home` can create
and populate the directory, then raise while seeding local state or validating
the overlay. `_prepare_home_and_grant` registers `shutil.rmtree` only after that
call returns. Its enclosing `ExitStack` therefore has no cleanup callback when
such an exception propagates.

[Post materialization seeding can raise](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/cli/home_seeders.py#L110-L181)

[Cleanup registered after successful preparation](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/captured/context.py#L270-L306)

An isolated fault probe forced the seeder to raise after materialization. The
runtime directory and its `.credentials.json` symbolic link both remained.
The process does not launch, so this is a residue and lifecycle finding rather
than another native credential exposure.

### 401 state originates in response processing

Both the per run addon and shared proxy pass `LiveStatusObserver` into
`handle_response`. For an unmatched authentication 401, the refresh classifier
invokes the callback while processing the completed response. The callback
queues the classifier specific sticky row before `persist_http_exchange`.

[Classifier callback before exchange persistence](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/addon_handlers.py#L457-L496)

[Specific live state emission](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/live_status_observer.py#L211-L230)

The database write is asynchronous and the response handler does not await its
returned future. Observable persistence therefore includes event loop and
writer latency. Its trigger is the completed 401 response hook, independent of
exchange or run finalization. The focused handler test passed and observed the
classifier specific row.

### Major: single path writes expose a partial shared credential

`MintedCredential.write_to` replaced atomic rename with an in place rewrite of
the shared document. The writer updates the live inode before `ftruncate` and
`fsync`. An I/O failure or hard termination after any partial write leaves the
sole shared path containing a partial or mixed JSON document. Concurrent
Claude processes can also read the live inode during the rewrite.

[In place credential rewrite](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/atomic_io.py#L45-L68)

[Shared broker write call](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/credential_broker.py#L444-L464)

An isolated fault probe forced the second write call to fail. The shared path
remained present and its JSON was invalid. A later mint can repair it, while
running clients can fail before that repair.

The new hard termination test patches `Path.replace`, but the new writer never
calls `Path.replace`. The injected termination hook is unreachable, the child
can complete normally, and the test ignores its return code. Its green result
does not exercise termination during the in place write.

[Unreached termination hook](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/test_credential_broker.py#L209-L234)

### Carried blocker: managed Claude still cannot launch outside macOS

The final delta does not change the prior platform blocker. The production
broker still raises on every non macOS host, and every supported managed Claude
launch still mints before materialization.

[Unchanged platform rejection](https://github.com/littleorgans/transport-matters/blob/cb701be1ed7d01f4b833db76a77970c7ac0f56c5/api/src/transport_matters/claude_fleet_auth.py#L22-L33)

### Verification

The following focused tests passed from an isolated archive of the exact final
SHA:

- reused Claude home rejection;
- failed mint cleanup;
- Codex native credential linkage;
- unmatched Claude 401 live state;
- single named credential path.

The test harness used isolated temporary homes and skipped the repository
database fixture. The two fault probes used synthetic, shape only documents.

## Final delta 6001257f

### Review boundary

- Prior reviewed head: `cb701be1ed7d01f4b833db76a77970c7ac0f56c5`
- Reviewed head: `6001257fe8e5f662de7dc0531cf9b63b8a004730`
- Delta: 10 files, 355 additions, 139 deletions
- Hosted gates: 9 successful, one optional check skipped
- Method: static launch graph review, five focused tests, and one isolated
  spawn probe
- No login, setup token, token exchange, captured run, database write, Keychain
  operation, channel home access, or credential value access occurred.

### Verdict

Two of the three requested checks are clean. Required argument provenance and
the named nullable modes hold on current production routes. The sole builder
claim remains open because an unchecked preview result has the same spawnable
type as a launched client. The legacy exported `run_children` route independently
constructs and spawns Claude without the builder.

Found one blocker and no major or minor findings.

### Blocker: preview produces an unchecked spawnable client

`build_claude_captured_invocation_preview` calls the shared implementation with
`runtime_home_dir=None` and runtime materialization disabled. When
`claude_path` is present, the shared implementation skips the credential
identity assertion, selects `invocation.home_dir`, and returns a normal
`ManagedClient`.

[Preview enters the unchecked shared implementation](https://github.com/littleorgans/transport-matters/blob/6001257fe8e5f662de7dc0531cf9b63b8a004730/api/src/transport_matters/captured/claude.py#L52-L96)

[Unchecked client construction](https://github.com/littleorgans/transport-matters/blob/6001257fe8e5f662de7dc0531cf9b63b8a004730/api/src/transport_matters/captured/claude.py#L165-L202)

`ManagedClient` is the descriptor accepted by
`run_prepared_client_on_local_tty`, which forwards its arguments and
environment to `ProcessSupervisor.spawn`. The type does not distinguish a
preview from a launchable client.

[Managed client spawn](https://github.com/littleorgans/transport-matters/blob/6001257fe8e5f662de7dc0531cf9b63b8a004730/api/src/transport_matters/cli/runner.py#L365-L382)

An isolated probe built a preview with shape only inputs, passed its returned
client to the exported local terminal runner, and observed one Claude spawn
call. No process was started because the probe used a recording supervisor.

The current `--print-command` product route is dry. It passes the preview
factory only to `print_invocation`, which prints the returned client arguments
and exits. Three focused print tests passed and confirmed that this route does
not call the client runner.

[Current print route exits after rendering](https://github.com/littleorgans/transport-matters/blob/6001257fe8e5f662de7dc0531cf9b63b8a004730/api/src/transport_matters/captured/run.py#L117-L175)

[Preview renders a full client descriptor](https://github.com/littleorgans/transport-matters/blob/6001257fe8e5f662de7dc0531cf9b63b8a004730/api/src/transport_matters/cli/launch_runtime.py#L407-L417)

The current CLI wiring remains dry. The boundary contract still fails. The new
type makes the checked builder require a runtime home while leaving an
unchecked client representable in the same spawn type.

### Corroborating path: exported runner still constructs Claude directly

`transport_matters.cli.run_children` remains publicly exported. It accepts
Claude arguments and environment, constructs `ManagedClient`, then reaches the
same PTY spawn path without calling any captured Claude builder.

[Direct constructor and runner](https://github.com/littleorgans/transport-matters/blob/6001257fe8e5f662de7dc0531cf9b63b8a004730/api/src/transport_matters/cli/runner.py#L257-L310)

[Public export](https://github.com/littleorgans/transport-matters/blob/6001257fe8e5f662de7dc0531cf9b63b8a004730/api/src/transport_matters/cli/__init__.py#L87-L101)

Current production callers no longer use this compatibility surface. Its
continued ability to construct and spawn Claude still disproves the requested
claim that no Claude client construction reaches spawn without the sole
builder.

### Required argument provenance is clean

The only production `ClaudeCapturedInvocation` construction uses the prepared
launch paths and metadata. `identity_seed` comes directly from
`_run_identity_seed`, which binds the resolved run id, working directory,
runtime home, workspace identity, and control access. No default, temporary
path, sentinel, or unrelated identity is substituted.

[Real identity derivation](https://github.com/littleorgans/transport-matters/blob/6001257fe8e5f662de7dc0531cf9b63b8a004730/api/src/transport_matters/captured/context.py#L143-L202)

[Single production invocation construction](https://github.com/littleorgans/transport-matters/blob/6001257fe8e5f662de7dc0531cf9b63b8a004730/api/src/transport_matters/captured/context.py#L368-L409)

The launch route requires `write=True`, registers cleanup before
materialization, rejects a missing prepared directory, and passes that exact
directory to the checked builder.

[Prepared launch route](https://github.com/littleorgans/transport-matters/blob/6001257fe8e5f662de7dc0531cf9b63b8a004730/api/src/transport_matters/captured/context.py#L276-L313)

The static negative type pin uses an `Any` value solely to isolate the missing
`runtime_home_dir` diagnostic. The function is never called and does not feed a
production launch.

### Nullable mode spot checks are clean

- Proxy only has `prepared.client_path=None`. Its dedicated builder rejects a
  non-null client path and the shared implementation returns `client=None`.
- User session state changes only the optional native session id and source
  descriptor. It does not select the child credential home.
- External web permits `web_port=None`. It still enters the `write=True`
  captured launch route and uses the checked runtime home.
- Native home keeps `home_dir=None` in public launch metadata while
  `plan_runtime_home` builds a run local overlay used by the child.
- No grant leaves `mcp_config_path=None`. Runtime home planning and credential
  identity verification are unchanged.

[Mode dispatch](https://github.com/littleorgans/transport-matters/blob/6001257fe8e5f662de7dc0531cf9b63b8a004730/api/src/transport_matters/captured/context.py#L368-L409)

[Runtime overlay planning](https://github.com/littleorgans/transport-matters/blob/6001257fe8e5f662de7dc0531cf9b63b8a004730/api/src/transport_matters/cli/runtime_home.py#L65-L159)

None of these valid nullable modes escapes the identity comparison on a current
launched Claude route.

### Other final delta verification

The guarded atomic writer restores atomic replacement and the cleanup callback
now precedes runtime home materialization. Focused failure and hard termination
tests passed from the exact reviewed SHA. No independent regression was found
in those changes.

## Final check 0dd0397c

### Review boundary

- Reviewed head: `0dd0397c5fe454155bbda662ad0bdd203d3ddd4a`
- Prior reviewed head: `6001257fe8e5f662de7dc0531cf9b63b8a004730`
- Delta: 11 files, 249 additions, 34 deletions
- Hosted gates: 9 successful, one optional check skipped
- Method: complete constructor and serializer inventory, static launch graph
  review, one isolated language behavior probe, and four focused tests
- No login, setup token, token exchange, captured run, database write, Keychain
  operation, channel home access, or credential value access occurred.

### Verdict

Clean. No blocker, major, or minor findings.

Every reachable production `ManagedClient` producer invokes the generated
dataclass constructor and therefore `__post_init__`. No repository path copies,
deep copies, pickles, replaces, manually allocates, or mutates a
`ManagedClient`. The environment is copied before validation, exposed through
a read only mapping, and protected from normal field reassignment by the frozen
dataclass.

[Validated frozen descriptor](https://github.com/littleorgans/transport-matters/blob/0dd0397c5fe454155bbda662ad0bdd203d3ddd4a/api/src/transport_matters/cli/runner.py#L78-L103)

### Constructor bypass inventory

`copy.copy` can create a second instance without invoking `__post_init__` in
principle. The isolated probe confirmed that its environment is the same
already validated `MappingProxyType`. No production or test source copies a
`ManagedClient`, so this cannot reach a current spawn path.

`copy.deepcopy` and `pickle` both fail with `TypeError` because
`MappingProxyType` is not serializable. `ManagedClient` defines no reduction or
state restoration hook. The captured run crosses an `asyncio.to_thread`
boundary as the same in process object. Its later HTTP payload is built by
reading the already validated fields. No process boundary or cache serializes
the descriptor itself.

[Validated descriptor converted to the capture payload](https://github.com/littleorgans/transport-matters/blob/0dd0397c5fe454155bbda662ad0bdd203d3ddd4a/api/src/transport_matters/capture_rpc.py#L435-L475)

`object.__new__(ManagedClient)` followed by manual field assignment can create
an unvalidated instance in principle. The only `object.__setattr__` that
targets this class is inside `__post_init__`, where it installs the checked
mapping. No source path performs manual allocation or field population.

`dataclasses.replace` reruns `__post_init__`. Replacing the environment while
retaining the Claude discriminator therefore revalidates and freezes the new
mapping. Changing both the discriminator and the environment can evade the
conditional Claude check in principle, as can a direct constructor with a
false discriminator. No source path applies `replace` to `ManagedClient`, and
all reachable producers use fixed harness names.

Normal reassignment of `env` raises `FrozenInstanceError`. Item assignment
through `env` fails, and later changes to the source dictionary cannot affect
the copied mapping. Deliberate `object.__setattr__` or direct `__dict__`
mutation remains possible for any frozen dataclass without slots. Neither
operation exists on a `ManagedClient` path in this repository. The mutable
`argv` list does not contain the credential path and no production path mutates
it after construction.

### Producer completeness

The complete production constructor set is:

1. Captured Claude invocation.
2. Secure workspace client wrapping.
3. Codex invocation.
4. The legacy Claude `run_children` wrapper.

[Captured Claude producer](https://github.com/littleorgans/transport-matters/blob/0dd0397c5fe454155bbda662ad0bdd203d3ddd4a/api/src/transport_matters/captured/claude.py#L56-L75)

[Secure workspace producer](https://github.com/littleorgans/transport-matters/blob/0dd0397c5fe454155bbda662ad0bdd203d3ddd4a/api/src/transport_matters/captured/run.py#L373-L413)

[Codex producer](https://github.com/littleorgans/transport-matters/blob/0dd0397c5fe454155bbda662ad0bdd203d3ddd4a/api/src/transport_matters/cli/codex_cmd.py#L174-L201)

[Legacy Claude producer](https://github.com/littleorgans/transport-matters/blob/0dd0397c5fe454155bbda662ad0bdd203d3ddd4a/api/src/transport_matters/cli/runner.py#L276-L306)

There is one additional textual constructor inside the proxy only builder
closure. Its public entry rejects a nonnull Claude path, while the shared
implementation calls the closure only for a nonnull Claude path. The
constructor is therefore unreachable.

[Proxy only guard and unreachable constructor closure](https://github.com/littleorgans/transport-matters/blob/0dd0397c5fe454155bbda662ad0bdd203d3ddd4a/api/src/transport_matters/captured/claude.py#L96-L116)

### Preview shape

`ClientCommandPreview` contains only `argv`. Its sole construction receives the
real rendered argument list. No name, environment, working directory,
sentinel, or placeholder was added. Both launch entry points wrap their
builders with an `isinstance(ManagedClient)` guard before any spawnable path,
while the print route only reads `argv`.

[Preview construction](https://github.com/littleorgans/transport-matters/blob/0dd0397c5fe454155bbda662ad0bdd203d3ddd4a/api/src/transport_matters/captured/claude.py#L78-L93)

[Spawnable type guard](https://github.com/littleorgans/transport-matters/blob/0dd0397c5fe454155bbda662ad0bdd203d3ddd4a/api/src/transport_matters/captured/run.py#L373-L387)

[Argument only print route](https://github.com/littleorgans/transport-matters/blob/0dd0397c5fe454155bbda662ad0bdd203d3ddd4a/api/src/transport_matters/cli/launch_runtime.py#L407-L420)

### Verification

Four focused tests passed from an isolated archive of the exact reviewed SHA:

- command preview cannot reach process spawn;
- a managed Claude client rejects a nonbroker credential path;
- a validated client snapshots and freezes its environment;
- the legacy Claude wrapper still reaches its simulated PTY lifecycle through
  `ManagedClient`.

The isolated language probe confirmed the copy, deep copy, pickle, replace,
frozen assignment, mapping assignment, and manual allocation behavior described
above. It used shape only paths and a recording validator.

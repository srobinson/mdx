---
title: Transport Matters ephemeral home credential broker
type: design
tags: [transport-matters, auth, oauth, ephemeral-homes, claude-config-dir, keychain, agent-runtimes]
summary: TM mints a short lived access token per launched runtime home so overlay and template launches inherit login without sharing or consuming the rotating refresh token.
status: draft
project: transport-matters
confidence: high
created: 2026-07-26
updated: 2026-07-26
---

# Transport Matters ephemeral home credential broker

## Problem

A Claude launched into an ephemeral home (`CLAUDE_CONFIG_DIR` set: TM runtime overlays,
runtime templates, `~/.agent-runtimes`) prompts for login even though the user is logged in.
Bare `claude` carries the login; every overlay and template launch does not.

This blocks unattended launch. Multi launch (`launch_batch`, the current NOW focus) makes it
worse: N simultaneous homes each hit the same wall, and any naive fix that shares one
credential across N homes is a correctness bug, not just a style problem.

## Verified mechanism

Verified against the Claude Code 2.1.219 binary on 2026-07-25, re-checked on 2026-07-26.

**Two credential stores, keychain primary, plaintext read fallback.** The selector:

```js
function _Fc(keychain, plaintext) {
  read()  { return keychain.read() ?? plaintext.read() }   // keychain wins
  update(n) {
    const prev = await keychain.readAsync();
    const r    = await keychain.update(n);                 // ALWAYS keychain first
    if (r.success) { if (prev === null) await plaintext.delete(); return }
    ...only on keychain failure: plaintext.update(n)
  }
}
```

Consequences that drive the design:

- On macOS every **write** goes to the keychain. `.credentials.json` is a read fallback only.
  On Linux there is no keychain, so that file *is* the store (why containers just mount it).
- Keychain service name is `Claude Code-credentials-` + first 8 hex of
  `sha256(CLAUDE_CONFIG_DIR)`. Confirmed: `sha256("/Users/alphab/.claude-auth")[0:8] == 919b6913`
  matches the observed item. The default home uses the unsuffixed `Claude Code-credentials`.
- **A home that writes a credential mints its own namespaced keychain item, and deleting the
  home directory does not remove it.** TM already deletes the home
  (`_prepared_home` in `captured_run_context` registers `stack.callback(shutil.rmtree, runtime_home_root, ...)`),
  so every leaked item is an unattributable orphan the moment the run ends.
- **`prev === null` deletes the seeded file.** A fresh ephemeral home has no keychain item, so
  its first credential write succeeds to the keychain and then deletes the seeded
  `.credentials.json` as migration cleanup.

**OAuth endpoint and client id**, read from the 2.1.220 binary on 2026-07-26. These are literals
in one config struct; do not substitute the adjacent design client id:

```js
TOKEN_URL:        "https://platform.claude.com/v1/oauth/token"
CLIENT_ID:        "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
DESIGN_CLIENT_ID: "59637612-477b-4836-a601-b0589eda7704"   // never this one
```

`platform.claude.com` is the only `/v1/oauth/token` host in the binary. An earlier draft of this
document said `claude.ai/v1/oauth/token`, which does not exist anywhere in it. The canonical scope
set is `[user:profile, user:inference, user:sessions:claude_code, user:mcp_servers,
user:file_upload]`, `user:profile` first.

**Writing the keychain item: `security -i`, never `-w`.** Verified against the real binary on
2026-07-26 with a throwaway item.

- `add-generic-password -X <hex>` puts the whole document, refresh token included, in **argv**,
  readable by any same-user process. That includes the agents TM itself launches, so it is
  disqualifying here.
- `-w` passed last with no value prompts for the secret on stdin, which looks like the fix and is
  a trap twice over. The prompt asks **twice** (password, then retype), so feeding the document
  once yields `passwords don't match`, stores an **empty** value, and exits **rc=0**. And the
  prompt path is capped at 128 bytes by the macOS `getpass` `_PASSWORD_LEN`, while a real
  credential document is 214+ bytes, so it silently **truncates** the refresh token, also at
  rc=0. Both failures land after the exchange has already consumed the rotation.
- The working shape is `security -i` with the full `add-generic-password -U -a <account>
  -s "<service>" -X <hex>` command supplied on **stdin**. No length cap, and argv holds only
  `security -i`. Quote the service name: it contains a space. Round trips byte exact at 666 bytes.
- Reading stays `find-generic-password -w`, where `-w` is the print-only flag and carries no
  secret in argv.
- **rc is not a sufficient guard.** Two distinct silent-corruption modes above return 0, which is
  why the read-back-and-compare is mandatory rather than defensive.

**Refresh tokens rotate on each use.** Corroborated by
[opencode-claude-auth](https://github.com/griffinmartin/opencode-claude-auth) ("Refresh tokens
rotate on each use, so write-back is enabled by default") and demonstrated the hard way:
sending the refresh token through `claude auth login` consumed it server side and broke the
default home until an interactive `/login`. Sharing one refresh token across N concurrent
homes revokes all but the first refresher.

**Access tokens live 8h against an absolute `expiresAt` set at issuance**, not a sliding
inactivity window (15 minutes of continuous API traffic left `expiresAt` unmoved). A home
seeded from an existing credential inherits the *remaining* life, not a fresh 8h.

### Machine evidence, 2026-07-26

- Keychain holds `Claude Code-credentials` plus **8** namespaced items
  (`53a55beb`, `643a6daf`, `6dbe65f1`, `83ff12ac`, `8d54e3fc`, `919b6913`, `b9030739`, `e7e9722c`).
  Only `919b6913` (`~/.claude-auth`) is attributable; none of the others hash to a surviving
  config dir. Yesterday there were 3. **The leak accumulates during normal use.**
- No plaintext credential file exists anywhere, including `~/.claude` and `~/.claude-auth`.
  There is nothing on disk to symlink today; the broker must materialize the file itself.
- `~/.codex/auth.json` is a real 0600 file, so the Codex path already works by symlink.

## Scope

In scope: harness `claude`, macOS. Out of scope: Codex (unaffected), and the Linux path, where
the plaintext file is the real store and a seeded home will happily rotate into it.

## Design

### Roles

- `~/.claude-auth` is the **sole owner** of the fleet refresh token (keychain item `...-919b6913`,
  created by `CLAUDE_CONFIG_DIR=~/.claude-auth claude auth login`). Isolating it from the user's
  interactive home means a fleet level revocation never logs the human out.
- **The broker** is the only component that ever exchanges a refresh token, and it always writes
  the rotated token back to that one item.
- **Launched homes never authenticate.** They receive a minted access token, run inside its
  validity window, and terminate. No write, so no keychain item, so no leak and no rotation race.

### Flow

1. Launch asks the broker for a run credential.
2. The broker reads the owner credential from the `~/.claude-auth` keychain item under a
   cross process lock.
3. If the cached access token has less than the safety floor remaining, it refreshes
   (`POST https://platform.claude.com/v1/oauth/token`, `grant_type=refresh_token`) and
   **persists the rotated refresh token back to the same keychain item before returning**.
   Skipping the write back self revokes the fleet. Persisting is not enough on its own: the
   write must be read back and compared under the same lock, because `security(1)` reports
   rc=0 for writes that did not land (see "Writing the keychain item" below).
4. The broker returns the access token; the launch writes it into the runtime home as a real
   0600 `.credentials.json`.
5. Teardown deletes the file with the home and, defensively, the namespaced keychain item.

Access tokens are not single use, so **one refresh fans out to many homes**. A batch of N
launches inside one window costs one rotation, which is what makes `launch_batch` safe.

### Code seam

`_link_overlay_credential_files(harness, auth_source_home_dir, runtime_home_dir)` in
`api/src/transport_matters/cli/home_overlay.py` is already the right seam: it separates the auth
source home from the content source home and is called by both
`materialize_runtime_home_overlay` and `materialize_runtime_home_template_overlay`. It no-ops
today only because `_symlink_file_if_exists` finds no source file.

Changes:

- Rename to a materialize verb. Codex keeps the symlink; Claude on macOS gets a broker minted
  file. **Never symlink Claude's credential file**: the harness deletes the plaintext path after
  a successful keychain write, and a shared target would be written by every concurrent home.
- The broker is injected, not imported ambiently, so tests can drive a fake keychain and a fake
  token endpoint.
- Teardown extends the existing `stack.callback` in `captured_run_context._prepared_home` to also
  delete `Claude Code-credentials-<sha256(child_home)[0:8]>`, idempotent and ignoring not-found.

`plan_runtime_home` in `api/src/transport_matters/cli/runtime_home.py` currently sets
`auth_source = native_home` (`~/.claude`) whenever an overlay is active. With the broker the auth
source becomes the broker owned home, defaulting to `~/.claude-auth` and configurable, so the
user's interactive credential is never touched by a launch.

Root cause of the bare vs template split, for the record: `_copy_overlay_local_files(...,
pin_claude_config_to_source=True)` makes template launches copy the template's own two key
`.claude.json` while bare launches resolve the real user config. Fixing auth does not fix that,
and it should not be conflated with it.

### Long running agents

A run that outlives its seeded window will refresh, mint its own keychain item, and orphan it.
That is the case the teardown deletion exists for. Agents that structurally cannot fit an 8h
window should get their own durable home rather than a seeded ephemeral one.

### Concurrency

Refresh is a rotating single use secret, so the exchange plus write back must hold a cross
process mutex and re-read the owner credential after acquiring it. Queue, never skip: a launch
that bypasses the lock is exactly the double refresh that revokes the fleet.

## Invariants

1. Exactly one component ever exchanges a refresh token.
2. Every rotation is persisted before the derived access token is handed out.
3. A launched home is never given a refresh token.
4. A launched home never needs to write a credential during its intended lifetime.
5. Teardown removes both the file and any namespaced keychain item, unconditionally.
6. Runtime templates never contain credentials. `validate_runtime_home_template` enforces this
   and `agent-runtimes-runtime-catalog` is a git repo.

## Ruled out, do not retry

- **`claude setup-token`** takes no options and issues `user:inference` only tokens, so bootstrap
  403s. It cannot be granted `user:profile`.
- **`CLAUDE_CODE_OAUTH_TOKEN`** is checked *before* stored credentials and returns early,
  suppressing a perfectly good keychain credential. It also makes the `/model` picker demand
  usage credits for Fable 5. The fix for a broken picker is `unset CLAUDE_CODE_OAUTH_TOKEN`;
  `claude auth login` alone does nothing because the env var wins.
- **`CLAUDE_CODE_OAUTH_REFRESH_TOKEN` + `CLAUDE_CODE_OAUTH_SCOPES`** work only with
  `claude auth login`, are inert at session start, write no credentials file into the target
  config dir, and consume the refresh token.
- **Copying `oauthAccount` / `userID` into a home's `.claude.json`** does nothing. A config dir
  containing only `.credentials.json` authenticates fine. `modelAccessCache` is a red herring:
  it is `[]` in both broken and working states, so do not seed it.

## Open questions for review

1. **Module placement.** Proposal: `api/src/transport_matters/cli/credential_broker.py`, beside
   `home_overlay`, since every consumer reaches it through the launch path. Counter argument:
   keychain access plus outbound OAuth is not a CLI concern and may belong at `src` root as a
   pure leaf.
2. ~~**`client_id` for the refresh exchange is not yet captured.**~~ **CLOSED 2026-07-26.** Endpoint,
   client id and scope set are captured above from the 2.1.220 binary. One piece of the request
   shape remains unverified: the broker posts JSON (`Content-Type: application/json`, matching the
   axios default the harness uses) and this endpoint's call site was not located to rule out
   `application/x-www-form-urlencoded`. It fails safe — a rejected request consumes no rotation —
   but it surfaces only at live smoke.
3. **Safety floor.** How much remaining life forces a refresh, and does TM mint per launch or
   reuse a cached token across a batch? Reuse is proposed; per launch minting buys nothing since
   the token is not per home attributable anyway.
4. **Failure surface.** When the fleet credential is expired or revoked, does launch fail closed
   with a structured verdict (`credential_unavailable`, sibling of `model_rejected`) or proceed
   and let the harness prompt? Fail closed is proposed: an interactive login prompt inside a
   detached pane is invisible.
5. **Bootstrap ownership.** Does `transport-matters doctor` detect a missing or logged out
   `~/.claude-auth` and instruct the user, or attempt the login itself? Detection is proposed;
   login is interactive and user owned.
6. **Existing orphans.** Add a `doctor` check that lists namespaced keychain items with no
   matching config dir, and offer cleanup. Seven such items exist today.

## Implementation slices

1. **Broker core.** Read and write the owner keychain item, refresh with write back, cross
   process lock, safety floor. Fake keychain and fake token endpoint in tests. No launch wiring.
2. **Seam swap.** Materialize verb in `home_overlay`, injected broker, real 0600 file for Claude,
   symlink retained for Codex, auth source defaulted to the broker owned home.
3. **Teardown and doctor.** Keychain item deletion at run teardown plus the orphan check and
   cleanup path.

## Verification

- Unit: rotation is persisted before the access token is returned; a second concurrent caller
  blocks and re-reads rather than double refreshing; a launched home is written a file with no
  refresh token in it.
- Integration: after a full launch and teardown, the runtime home is gone **and** no new
  `Claude Code-credentials-*` item exists. Snapshot the keychain item list before and after.
- Live smoke: a template overlay launch reaches a first turn with no login prompt. Per the probe
  fixtures lesson, this must run against a real binary, not fixtures alone.
- Gates are repo recipes: `just check` and `just test`.

## Risks

- **Consuming the fleet refresh token breaks every launch at once.** It has already happened once
  via `claude auth login`. Never route the broker's token through the CLI.
- Verifying a token by hashing the local credential bytes is worthless; server side invalidation
  leaves the bytes identical. Test whether the credential still authenticates.
- Undetected write back failure is silent until the next launch. It must raise, never warn. `security(1)`
  returns rc=0 on at least two silent-corruption paths, so the only sufficient check is reading the
  item back and comparing it to the intended document under the same lock, before the derived access
  token is handed out.
- **Testing a keychain adapter against a fake `subprocess.run` proves argv construction and nothing
  about the tool.** Both `-w` defects passed a green fake-runner suite. Any change to the write
  protocol needs one real-binary test against a throwaway item, with a payload deliberately larger
  than 128 bytes and a byte-exact comparison.

## References

- cm `019f96a5-8918-7453-bdf9-80318fc7cc69`, scope `global/project:helioy/repo:transport-matters`
- https://code.claude.com/docs/en/authentication
- https://github.com/anthropics/claude-code/issues/7100
- https://github.com/griffinmartin/opencode-claude-auth

---
title: TM auth broker review — design author
type: review
tags: [transport-matters, auth, oauth, credential-broker, review]
summary: The implementation matches the design; the bulk is adapters and validation, not extra concepts. Four cuts, one addition, and a correction to my own design doc.
project: transport-matters
reviewer: opus (design author)
pr: 335
commit: 0f4e63df
confidence: high
created: 2026-07-27
---

# TM auth broker review — design author

Reviewed `credential_broker.py` against `~/.mdx/design/transport-matters-ephemeral-home-credential-broker.md` and re-verified the mechanism against the installed **2.1.220** binary. Static reading only; no token exchange, no `claude auth login`, no keychain write.

## 1. Does it match the design, and what would I cut?

**It matches.** `CredentialBroker.mint` is exactly the minimal flow: acquire lock, read owner, floor check, exchange, persist rotation, return access-only. That is ~22 lines and it satisfies invariants 1, 2 and 3 as written. Stuart is right that the algorithm is simple, and the implementation agrees with him — the 506 lines are two adapters (~160) and input validation (~120), not extra concepts. There is no state machine, no cache layer, no retry policy. Nothing structural to remove.

Four things I would cut:

1. **`CredentialBroker.__init__:lock_path` as an injected parameter.** This is the reviewers' double-refresh finding, and the fix is a *cut*: derive the lock path from the owner config dir inside the broker so two call sites cannot disagree. Removing the knob removes the bug. Keep injection for `store` and `exchanger` — tests need those.
2. **The repeated `failure_kind` dance.** Five hand-rolled copies in `_run_command`, `HttpxTokenExchanger.exchange`, `CredentialBroker.mint`, `_read_owner`, `_exchange`. The semantics are load-bearing — raising *outside* the `except` block is what stops `__context__` retaining an `httpx` exception whose `.request` carries the refresh token — so keep the behaviour, collapse the repetition into one helper.
3. **`HttpxTokenExchanger.exchange:requested_scopes`.** `scopes or CLAUDE_AI_OAUTH_SCOPES` is a dead branch; the only caller passes `owner.scopes`, which `_required_scopes` has already validated non-empty. Cut the fallback, keep the constant.
4. **`_default_keychain_account`'s `"claude-code-user"` fallback.** A bad or missing `$USER` silently targets a nonexistent account and surfaces as "owner credential is unavailable", pointing the operator at the wrong problem. Raise instead.

Two things that look like fat and are **load-bearing — do not cut**:

- **`OwnerCredential._document` round-tripping.** `~/.claude-auth` was created by `claude auth login` and the Claude harness reads that same item. Dropping unrecognised fields on write-back would corrupt the owner home. This is why `rotated()` merges into a copied document instead of building a fresh one.
- **The validation helpers.** They look disproportionate for two trusted inputs, but a malformed parse here writes a corrupt document into the fleet keychain item, which is precisely the catastrophic case the design exists to prevent. The `isinstance(value, bool)` guards matter (`bool` is a subclass of `int`).

## 2. The crash window

**No mechanism. "Fail with a clear re-login instruction" is correct and complete.** The deep reviewer is wrong to call it a design-level gap.

Any recovery mechanism must persist the rotated refresh token somewhere *before* the keychain write completes, and the only available somewhere is a plaintext file. That trades a millisecond-wide unrecoverable window for a permanent plaintext copy of the fleet secret — inverting the design's entire purpose. The window only opens on a hard kill between two adjacent statements, and the recovery is a 30-second human action.

The type already exists: `CredentialWriteBackError` is distinct from `CredentialBrokerError`, which is the whole mechanism required. The one change needed is its message. It currently reads "rotated owner credential could not be persisted", which does not tell the operator that the fleet credential is now **dead** and that the fix is `CLAUDE_CONFIG_DIR=~/.claude-auth claude auth login`. Say that in the error.

## 3. Reviewer findings, and what the evidence says

**The argv leak is real, and the fix is smaller than the reviews assume.** `security(1)` can take the secret off argv: from its own usage text, *"Use of the -p or -w options is insecure. Specify -w as the last option to be prompted."* So `SecurityOwnerCredentialStore.write` moves from `-X <hex>` to `-w` passed last with no value, feeding the document on stdin. The blocker is that `SecurityOwnerCredentialStore._run_command` hardcodes `stdin=subprocess.DEVNULL`; that has to become the credential bytes on the write path only. Verify against a throwaway service name, never the real `-919b6913` item. Consider `ensure_ascii=True` for the keychain body, since the prompted path reads a text password rather than hex.

This one matters more here than in a normal codebase: TM launches agents **as the same user**, so "any same-user process can read argv" includes the very processes TM spawns.

**My design doc was wrong and the implementation is right about the token URL.** Do not "fix" the code back to the doc. In 2.1.220:

```
TOKEN_URL:        "https://platform.claude.com/v1/oauth/token"
CLIENT_ID:        "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
DESIGN_CLIENT_ID: "59637612-477b-4836-a601-b0589eda7704"
```

`https://platform.claude.com/v1/oauth/token` is the only `/v1/oauth/token` in the binary. `claude.ai/v1/oauth/token`, which my doc specified, does not appear at all. `CLAUDE_CODE_OAUTH_CLIENT_ID` and `CLAUDE_CODE_CUSTOM_OAUTH_URL` exist as overrides (the latter against a hardcoded allowlist); TM needs neither.

**Scopes verified exactly.** The binary's canonical set is `rrt = [user:profile, user:inference, user:sessions:claude_code, user:mcp_servers, user:file_upload]`, which matches `CLAUDE_AI_OAUTH_SCOPES` in content *and* order. Note `user:profile` is first — that is the scope whose absence caused the original Fable 5 symptom, so a rotation that silently narrowed scopes would reintroduce it.

**Unverified, flag before live smoke:** the request encoding. `HttpxTokenExchanger.exchange` posts `json=body` (`Content-Type: application/json`). I could not locate this endpoint's call site to confirm it is not `application/x-www-form-urlencoded` — the two refresh call sites I did find (the gateway IdP path and a vendored Azure identity library) both use form encoding. The `User-Agent: axios/1.15.2` header suggests a captured real request, and axios defaults an object body to JSON, so it is probably right. It fails safe either way — a rejected request consumes nothing — but it will not be caught until live smoke.

**One risk the implementation dropped, worth adding.** Design risk: *"Undetected write back failure is silent until the next launch. It must raise, never warn."* `SecurityOwnerCredentialStore.write` trusts `returncode == 0` from `add-generic-password -U`. Add a read-back-and-compare inside the same lock, after the write, before `mint` returns. Roughly five lines, and it directly discharges invariant 2. This is the only thing I would *add* to slice 1.

**The "minted token shorter than the run window" finding is real but misfiled.** It is a configuration contract, not a code defect. The design already routes it to teardown keychain deletion (slice 3) and to durable homes for agents that structurally cannot fit the window. The control is setting `minimum_ttl` at or above the longest expected run, which is a launch-wiring decision in slice 2.

## Verdict

Ship slice 1 after: the `lock_path` cut, the argv fix, the write-back read-back, and the `CredentialWriteBackError` message. Everything else here is tidying that can ride along or follow.

## References

- Design: `~/.mdx/design/transport-matters-ephemeral-home-credential-broker.md`
- cm `019f96a5-8918-7453-bdf9-80318fc7cc69`, scope `global/project:helioy/repo:transport-matters`
- Peer reviews: `~/.mdx/projects/tm-auth-broker-review-fable.md`, `~/.mdx/projects/tm-auth-broker-review-solmax.md`
- Binary evidence: `~/.local/share/claude/versions/2.1.220`

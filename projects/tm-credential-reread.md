# Claude Code 2.1.220 credential reread

## Verdict

`reread: yes`

For a `CLAUDE_CONFIG_DIR` whose Keychain item is absent, Claude Code reads
`.credentials.json` again during the process lifetime.

The shared symlink design is viable. Updating the shared target reaches a
running process on its next main API request attempt when the target mtime has
changed. An OAuth 401 also forces a reread. The binary has no dedicated
filesystem watcher, so the update is trigger driven rather than an immediate
in memory broadcast.

## Safety and scope

This was static analysis only.

- I did not execute the Claude Code binary.
- I did not run login, setup token, token exchange, or auth endpoint traffic.
- I did not read or print any credential value.
- I did not modify the repository.

## Extraction

Target:

- Path: `/Users/alphab/.local/share/claude/versions/2.1.220`
- Format: Mach O arm64
- SHA256: `8addc857f3fe64d5a0368af9ee50321b50afb4a6918ba3ef018ab84f5dbbe081`
- Embedded runtime: Bun `1.4.0`, revision
  `f6d0fcd24abd48061873c2f1a6fb2a67eee487b8`

`otool -l` identifies `__BUN.__bun` at file offset `64831488`. The section has
an eight byte length prefix followed by a Bun standalone module graph. I
decoded its trailer, `Offsets`, and fourteen 52 byte module records using the
matching Bun standalone graph layout.

The entry module record is:

- Name: `/$bunfs/root/src/entrypoints/cli.js`
- Contents pointer: offset `160608336`, length `21635672`
- Absolute executable file offset: `225439832`

The extracted source is ASCII text:

- Path used for analysis: `/tmp/tm-credential-reread.BvgLJz/cli.js`
- Size: `21635672` bytes
- SHA256: `d60e0e81efcc86861d9a7094b027b2b7b7cbd99469eebbcd6a5b707030211120`

All source citations below use extracted source byte offsets. Line numbers are
also supplied where useful, but the bundle has very long minified lines.

## Credential document loader

The concrete plaintext backend is `XJn` at `cli.js` byte `2630785`, line 271.

- `JJn()` at byte `2630563` resolves
  `join(gK(), ".credentials.json")`.
- `XJn.read()` uses `readFileSync(path, "utf8")`, then parses JSON.
- `XJn.readAsync()` uses `readFile(path, "utf8")`, then parses JSON.

The production selector is `zs()` at byte `2632495`, line 271:

```text
zs() -> bFc(Q5i, XJn)
```

`Q5i` is the macOS Keychain backend. `bFc` at byte `2626932`, line 270 reads
the primary backend first and invokes the plaintext backend when the primary
returns null. Therefore the ephemeral home described in the brief follows the
file path when no Keychain item exists for that config directory.

The OAuth layer has two accessors:

- `ms=Vr(...)` at byte `3534818`, line 474 is the synchronous memoized
  accessor. Its file capable read is `zs().read()` at byte `3535336`.
- `vB=jMe(...)` at byte `3535448`, line 474 is the asynchronous promise
  memoized accessor. Its file capable read is `zs().readAsync()` at byte
  `3535608`.

`wq()` at byte `3509965`, line 448 clears both accessor caches and the secure
storage cache.

## Call sites and classification

### Main API request path: runtime reread

`Ytp`, the main streaming query path, calls:

```text
e$o(() => Fde(...), requestAttempt, ...)
```

for each request attempt. `Fde` starts at byte `3377576`, line 427 and calls
`await O_()` at byte `3378425` before reading `ms()` and constructing the API
client.

`O_()` reaches `bJi`, which starts at byte `3514827`, line 448. `bJi` first
calls `Lxg()`, then calls `vB()`.

`Lxg` starts at byte `3510169`, line 448. It:

1. calls `stat(join(gK(), ".credentials.json"))`;
2. compares `mtimeMs` with the prior value;
3. calls `wq()` when the value changed.

The following `vB()` therefore reads the updated document. Node `stat` and
`readFile` follow a symbolic link, so a changed shared target is observed by
this path.

Classification: runtime, before every main API request attempt. The file
content is reread when mtime changed.

### OAuth 401 path: runtime forced reread

`zM` starts at byte `3510396`, line 448 and dispatches to `Nxg`.

`Nxg` starts at byte `3511308`, line 448. Its first operations are:

```text
wq()
await vB()
```

This clears the memoized OAuth and storage state and performs another backend
read. The same function also has an explicit `zs().readAsync()` disk recovery
read and the telemetry branch
`tengu_oauth_401_recovered_from_disk` at byte `3512194`.

The main request retry loop `e$o` starts at byte `12672534`, line 20364. On
401 it calls `zM(failedAccessToken)` at byte `12673113`, then calls `ms()` and
rebuilds the client when the loaded token differs. This matters for the
access only document: `Nxg` reports no refresh token, while the caller still
detects the replacement access token and continues with a rebuilt client.

Other runtime 401 callers include:

- Axios retry wrapper `xU`, byte `2444529`
- cloud request wrapper `qZc`, byte `3418308`
- side queries, byte `5200771`
- Claude.ai MCP proxy wrappers, bytes `6645673`, `6650055`, `6776835`,
  and `6781217`
- design requests, byte `9563069`
- remote settings, byte `10799677`

Classification: runtime, on OAuth 401. Cache invalidation and backend reread
are unconditional at the start of the handler.

### Explicit fresh token helper: runtime reread

`PJi` starts at byte `3513244`, line 448. It calls `wq()` and then `vB()`.

Classification: runtime, explicit fresh access token request.

### Background manager auth supervisor: runtime timers and 401

`Gcp` starts at byte `12753855`. It is the default auth controller passed to
the background manager supervisor.

Its call sites are:

- initialization: `getClaudeAIOAuthTokensAsync()`, then
  `checkAndRefreshOAuthTokenIfNeeded()`;
- proactive timer: scheduled from `expiresAt`, four minutes before expiry,
  capped at 24 hours;
- missing token poll: every 30 seconds it calls
  `clearOAuthTokenCache()` and `getClaudeAIOAuthTokensAsync()`;
- worker 401: calls `handleOAuth401Error()`, then clears and reloads even when
  the handler reports no refresh token.

Constants are at bytes `12759933` through `12759976`:

- validity margin: `300000` ms
- proactive lead: `240000` ms
- missing token poll: `30000` ms
- maximum timer delay: `86400000` ms

Classification: runtime. These paths apply to the background manager process.

### GrowthBook refresh timer: runtime conditional reread

`Vtu` schedules `$no()` every `21600000` ms. When authenticated GrowthBook
state is active, `$no()` calls `checkAndRefreshOAuthTokenIfNeeded()`. That
reaches `bJi`, `Lxg`, and `vB` as described above.

Classification: runtime, optional six hour timer.

### Cache invalidation after writes or injected token updates

OAuth save and login paths call `wq()` after persistence. Structured IO also
calls `wq()` when it applies a `CLAUDE_CODE_OAUTH_TOKEN` update. The next
`ms()` or `vB()` access reads again.

Classification: runtime, state change driven.

## Answer to the design question

The file is not startup only. The shared access only symlink design will let
running Claude Code processes adopt a broker written access token. The normal
query path checks file mtime before request attempts, and 401 recovery forces
cache invalidation and reread.

The propagation contract should be described as “on the next request or 401,”
with the background manager timers as additional triggers. There is no
dedicated file watcher.

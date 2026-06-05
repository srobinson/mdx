# Transport Matters: Codex/Claude auth symmetry scout

Scouted 2026-07-31 against `main` @ `2b1057c6`. Read-only; tree untouched.

Owner constraints binding every recommendation here:

1. The **desktop** must not depend on `transport-matters codex -- login`. Any answer
   ending in "tell the user to run a terminal command" is unacceptable for the desktop
   surface. It remains acceptable for the pure-CLI surface.
2. Do **not** blur the auth probes with the credential seam. `harnesses/probes/*` and
   `harnesses/connections.py` are diagnostic by explicit decision
   (`RUNTIME-SURFACING-S2-PLAN.md` S2g item 4: probes "never authorize or block launch").

---

## A. The seam

`cli/home_overlay.py::_link_overlay_credential_files` has two callers, both in the same
module and both the last step of materialization: `materialize_runtime_home_overlay`
(native/manual) and `materialize_runtime_home_template_overlay`. Both are reached only
through `cli/home_seeders.py::prepare_runtime_home_overlay` /
`prepare_runtime_home_template_overlay`, re-exported by `cli/home_seed.py`, dispatched by
`cli/runtime_home.py::prepare_runtime_home` on `RuntimeHomePlan.mode`.

**Claude branch.** `claude_credential_path is None` raises
`RuntimeError("Claude credential mint was not prepared")`. Otherwise symlinks
`.credentials.json` (`home_constants._CLAUDE_OVERLAY_CREDENTIAL_NAMES`).

**Codex branch** is the fallthrough with no `if` of its own: symlinks `auth.json`
(`_CODEX_OVERLAY_CREDENTIAL_NAMES`) from `auth_source_home_dir`.

`_symlink_file_if_exists` **returns immediately when the source is not a file**. That is
the entire defect.

### Claude's fail-closed half

`_mint_overlay_credential` runs *first*, before any directory is created. For Claude it
calls `_mint_claude_credential`, which guards `CLAUDE_FLEET_AUTH_HOME.is_dir()` before
minting (so the broker's `exclusive_file_lock` cannot `mkdir` an empty `~/.claude-auth` on
the way to failing), then `claude_fleet_auth.claude_fleet_credential_broker()` and
`broker.mint()`, raising `_fleet_credential_failure(reason)` → `CredentialBrokerError` with
`CLAUDE_FLEET_BOOTSTRAP_COMMAND` appended. **For Codex `_mint_overlay_credential` returns
`None` unconditionally.**

### The access-only materialization (Claude only)

`credential_broker.py::CredentialBroker.mint`, under `exclusive_file_lock`: read
`OwnerCredential` from `SecurityOwnerCredentialStore` (macOS `/usr/bin/security`, service
name suffixed with `sha256(NFC(config_dir))[:8]`); if `expires_at_ms - now >= 1h`
(`_MINTED_CREDENTIAL_MIN_TTL`) use as-is, else `HttpxTokenExchanger.exchange`, write the
rotated owner back, read back and byte-compare (`CredentialWriteBackError` on mismatch).
Then `_write_shared_credential` writes a **strictly three-field** document
`{"claudeAiOauth": {accessToken, expiresAt, scopes}}`; `MintedCredential.from_document`
rejects any other field set, so **the refresh token is structurally absent from what the
runtime home can reach**. `assert_claude_runtime_credential_identity` /
`assert_claude_client_credential_identity` re-verify at spawn via `samefile`.

### Two defects found in the seam itself

- **The Codex symlink is writable.** `target.symlink_to(source.resolve())` resolves to the
  operator's real file, so a token refresh inside a managed run **rotates the operator's
  real `~/.codex/auth.json`**. Pinned as intended behavior by
  `test_home_seed_credentials.py::test_runtime_overlay_credential_teardown_leaves_native_file`
  ("rotated sentinel" lands in the native file).
- **A second silent no-op on the same absence.** `home_seeders._seed_runtime_home_overlay`
  → `cli/codex_home.py::CodexSeeder.seed` →
  `home_io._copy_secret_file_if_missing(default_codex_home(env)/auth.json, ...)`. If only
  `_link_overlay_credential_files` asserts, the un-overlaid manual-home path stays silently
  broken. Both must move together or the asymmetry relocates.

Net state for Codex with no credential: a fully formed `CODEX_HOME` with symlinked
sessions/skills/plugins, a real `config.toml` carrying `trust_level = "trusted"`,
control-plane MCP wired with a bearer, `install_codex_run_context` written, and no
credential at all. `doctor` never looks.

---

## B. Where Codex credentials actually come from

`~/.codex/auth.json` on this machine (keys only, no values):

```
auth_mode      = "chatgpt"
OPENAI_API_KEY = null
tokens         : { id_token, access_token, refresh_token, account_id }
last_refresh   = "2026-07-23T17:47:44Z"
```

JWT claim shape only, `iss=https://auth.openai.com`, client `app_EMoamEEZ73f0CkXaXp7hrann`:
`id_token` exp **1 hour**; `access_token` `aud=https://api.openai.com/v1`, exp **~10 days**;
`refresh_token` opaque, 211 chars, **present**.

So a refresh token and a token endpoint both exist. The binary carries `/oauth/token`,
`https://auth.openai.com/api/accounts`, and a `CODEX_REFRESH_TOKEN_URL_OVERRIDE` escape
hatch. Auth modes in the binary: `chatgpt`, `apikey`, `external`,
`personal_access_token`, `agent_identity`, `bedrock_api_key`.

**Only the `codex` binary writes it.** Transport Matters never does: `_CODEX_AUTH_FILENAME`
is read (symlinked by `home_overlay`, copied by `CodexSeeder.seed`) and rejected
(`validate_runtime_home_template` refuses a template containing it;
`_validate_template_secret_free` + `_codex_config_secret_path` refuse auth-shaped keys in
`config.toml`).

**The ChatGPT websocket path in TLDR is a transport statement, not an auth statement.** The
bearer on that websocket is `tokens.access_token` from `auth.json`. That confirms
`auth_mode: chatgpt` is the mode the capture path is built for, and an API-key fallback
would not reproduce it.

**`OPENAI_API_KEY` is not part of the launch credential contract.** It appears only in
`launch/environment.py::HARNESS_CREDENTIAL_ENV_KEYS`, consumed solely by
`harnesses/probes/runner.py` to strip credential env from probes. `build_launch_env` starts
from `os.environ.copy()` and `build_managed_child_env` copies that base wholesale, popping
only proxy/trust/internal keys, so an ambient `OPENAI_API_KEY` reaches the Codex child
untouched and unaudited, bypassing the seam entirely.

**Env isolation hole.** The installed binary also honors `CODEX_API_KEY` and
`CODEX_ACCESS_TOKEN` (its own doctor string: "no Codex credentials were found — Run codex
login or provide an API key through a supported auth env var"). Neither is in
`HARNESS_CREDENTIAL_ENV_KEYS`, so probes do not strip them and can authenticate through the
parent's token, defeating the isolation that denylist exists for; and any assertion on
`auth.json` alone false-negatives whenever one is set.

---

## C. The desktop bootstrap question

`codex-cli 0.145.0`, verified against `codex login --help` and the vendored binary:

| Mechanism | Evidence | Desktop-viable? |
|---|---|---|
| Browser OAuth (`codex login`) | callback on `127.0.0.1:1455` + `/auth/callback`; `useHostedLoginSuccessPage` | only via app-server |
| Device code (`--device-auth`) | `login/src/device`, `user_code`, 15-min budget, **"device code login is not enabled for this Codex server"** | server-gated, no |
| API key (`--with-api-key`, stdin) | help text, `auth_mode: apikey` | yes, wrong auth mode |
| Access token (`--with-access-token`, stdin) | help text, `CODEX_ACCESS_TOKEN` | yes, broker landing pad |
| **app-server JSON-RPC** | `account/login/start`, `/cancel`, `/completed`, `account/logout`, `account/read`, `getAuthStatus`, `account/chatgptAuthTokens/refresh`; params union `chatgpt \| chatgptDeviceCode \| apiKey \| accessToken \| chatgptAuthTokens{accessToken,refreshToken} \| amazonBedrock`; returns `loginId` + `authUrl`; `AccountLoginCompletedNotification{status,message}` | **yes, this is the answer** |

**Reusing an existing `~/.codex/auth.json`** works today and is the only thing that does,
because `plan_runtime_home` sets `auth_source = native_home` whenever `should_overlay`
(pinned by `test_runtime_overlay_skips_missing_native_credentials_without_content_fallback`).

**The canvas is worse than the CLI.** `cli/codex_cmd.py::run_codex` passes
`use_runtime_overlay=False`, so no `CODEX_HOME` is set and a login inside
`transport-matters codex -- login` lands in the real `~/.codex`. But
`captured/context.py::_prepare_home_and_grant` passes
`use_runtime_overlay=write and prepared.client_path is not None`, so **every canvas Codex
launch overlays**, and a login typed inside a canvas pane is written into an ephemeral
directory that `stack.callback(shutil.rmtree, runtime_home_root)` deletes at run end. The
user's own attempt to fix the problem is destroyed.

### Recommendation

**Do not build a Codex token-minting broker.** Build a login driver over
`codex app-server`'s `account/login/start` against a dedicated fleet home, and have the
credential seam consume the resulting `auth.json` the way it consumes the native one today.

1. `codex_fleet_auth.py` mirroring `claude_fleet_auth.py`:
   `CODEX_FLEET_AUTH_HOME = ~/.codex-auth`, `codex_fleet_home_unavailable_reason(...)`.
   No `sys.platform` clause; this half is genuinely cross-platform.
2. A driver spawning `codex app-server --listen stdio://` with `CODEX_HOME=~/.codex-auth`,
   sending `account/login/start` (`chatgpt` variant), returning `{loginId, authUrl}` over a
   new `POST /v1/harnesses/codex/login`, streaming `account/login/completed` back. The
   desktop opens `authUrl` via Electron `shell.openExternal` with cancel wired to
   `account/login/cancel`. No terminal. Constraint 1 satisfied.
3. `_link_overlay_credential_files`'s Codex branch resolves `auth_source_home_dir` to the
   fleet home when it holds a credential, falls back to native, and **raises
   `CredentialBrokerError`** when neither does.
4. Keep `transport-matters codex -- login` as the **CLI-surface** bootstrap only. Add a
   `transport-matters codex login` targeting the fleet home as the CLI remediation string
   (the analogue of `CLAUDE_FLEET_BOOTSTRAP_COMMAND`). Never the desktop's answer.

Rationale for not brokering: the broker's value for Claude is stripping the refresh token
out of the runtime home's reach. Codex's `auth.json` cannot be stripped that way without
asserting an undocumented schema that the binary's `secret_auth_storage` feature flag is
actively threatening to move to a keyring. And the desktop's real first-run problem is *the
user has no credential at all*, which minting cannot solve.

### Where the constraints force a non-obvious design

- **Constraint 1 kills the "run this command" error string**, which is exactly what
  `CapturedRunPane.tsx` renders today for Claude (its `spawnError` banner, pinned by "shows
  the Claude fleet reason and bootstrap command when POST /v1/runs fails"). The error must
  carry a **structured, actionable code** the renderer turns into a button.
  `capture_rpc_routes.prepare_capture` needs a distinct `codex_fleet_credential_unavailable`
  code, and the pane must branch on code rather than concatenating reason + command.
- **Constraint 2 kills reusing `harnesses/probes/codex.py`'s `codex login status`** to gate
  the launch. The gate must read the credential seam's own predicate.

### Not symmetric, precisely here

The Codex side **can** be symmetric at the *seam*: fail-closed on absence, one shared error
helper, doctor and launch agreeing. It **cannot** be symmetric at the *broker*, for one
reason worth writing down rather than papering over: Claude's minted credential is provably
access-only because `MintedCredential.from_document` rejects any document whose OAuth field
set is not exactly `{accessToken, expiresAt, scopes}`. Codex has no such contract; `tokens`
is free-form and the runtime home receives `refresh_token` and `id_token` alongside
`access_token` regardless. Until Codex ships a documented access-only auth document, a Codex
"broker" is a symlink with extra steps, and the honest description of the Codex overlay is
**the runtime home holds the operator's full refresh-capable credential**.

---

## D. Blast radius if the seam asserts: 12 items

**Production paths (8).**

1. `home_overlay.materialize_runtime_home_overlay` — new raise site.
2. `home_overlay.materialize_runtime_home_template_overlay` — new raise site.
3. `home_seeders.prepare_runtime_home_overlay` / `..._template_overlay` — propagate.
4. `runtime_home.prepare_runtime_home` — propagate.
5. **`cli/codex_cmd.py::run_codex`** — wraps only `prepare_launch` in
   `except HarnessEnablementRejected`. `_prepare_codex_launch_parts` →
   `prepare_runtime_home` sits outside any handler, so `CredentialBrokerError` escapes as an
   unhandled traceback (exit 1 + stack) instead of the exit-2 `typer.secho` arm
   `cli/start_cmd.py::run_start` already has. Today `run_codex` passes
   `use_runtime_overlay=False`, so the raise only fires on a template or `--agent-home-dir`
   launch, which makes it easy to miss in review and certain to bite later.
6. **`api/v1/capture_rpc_routes.py::prepare_capture`** — its `except CredentialBrokerError`
   arm hardcodes `"claude_fleet_credential_unavailable"`. A Codex failure would reach the
   canvas under the Claude error code with a Claude bootstrap command in the detail.
7. `captured/context.py::_prepare_home_and_grant` — the canvas path where the raise
   actually fires in practice.
8. `runtime_home.seed_direct_home_if_needed` → `codex_home.CodexSeeder.seed` — the second
   silent no-op.

**Tests that newly fail (3).**

1. `cli/test_home_seed_credentials.py::test_runtime_overlay_skips_missing_native_credentials_without_content_fallback`
   — constructs a Codex overlay without a credential on purpose. Its *intent* (never fall
   back to the content source's credential) is correct and must survive; its *assertion*
   becomes "raises, and still does not link the template's secret".
2. `cli/test_home_seed.py::test_codex_overlay_repoints_hook_trust_state_to_overlay_home`.
3. `cli/test_control_plane_home.py::test_codex_control_plane_client_round_trip_preserves_source`.

**Fixture-shaped assumption (1).** `cli/test_runtime_home.py` writes
`(native/"auth.json").write_text("{}\n")` in **eight** places, none of them about
credentials. Any future codex overlay test fails by default. Argues for a shared
`_codex_auth_source(tmp_path)` helper landing with the slice, not eight more `write_text`
calls.

**Not affected:** `cli/test_runtime_home_template_validation.py` (plans only, never
materializes); the four `seed_home_dir` Codex tests in `cli/test_home_seed.py` (all write
`auth.json`); `tests/integration/`.

---

## E. Doctor

**Where.** `cli/diagnose.py::run_doctor`, immediately after the existing Claude fleet triple
(`fleet_error = claude_fleet_credential_error()` / `_ok(...)` / `typer.secho(... warn ...)`),
before `report_runs_health`. `diagnose.py` already imports
`from .home_overlay import claude_fleet_credential_error`.

**Warn, not fail.** The Claude block's own comment states the rule: "Advisory, not a
failure: a Codex-only operator never needs it." The symmetric argument holds.
`run_doctor`'s `failures` list drives `raise typer.Exit(1)`; a hard failure would break
every single-harness operator.

**Shared predicate.** `claude_fleet_credential_error(*, require_shared=True)` exists exactly
for this and says so: "Shared with `doctor` so the diagnostic and the launch path can never
disagree." Add the analogue in `home_overlay.py`:

```
codex_fleet_credential_error() -> str | None
```

`_link_overlay_credential_files` raises when it is not `None`; `run_doctor` warns on the
same call. One predicate, two consumers, structurally unable to disagree. Keep it in
`home_overlay` beside its Claude twin; splitting across modules is how they drift.

Fold in one extra check from B: report when `OPENAI_API_KEY` / `CODEX_API_KEY` /
`CODEX_ACCESS_TOKEN` is present, because that is a live credential path the `auth.json`
predicate cannot see. Codex's own doctor distinguishes "auth is provided by environment"
from "auth is configured"; mirroring that stops a green line from lying.

---

## F. The macOS-only Claude reason

`claude_fleet_auth.py::fleet_home_unavailable_reason` returns "Claude fleet credentials
require macOS" on non-darwin, ahead of the directory check. It reaches a user through three
seams, all late: `doctor` (CLI only, and only if run); `start_cmd.run_start`'s exit 2 (after
a launch attempt); and the 503 → `CapturedRunPane.tsx` banner (after the user clicked run).

**Earliest pre-launch seam: `runtime_registry.py::_catalog_summary`**, reached from
`list_runtime_templates` and rendered by the canvas launcher before any launch. It already
computes `RuntimeTemplateReadiness` per template from `detect_harnesses()`, and
`www/packages/canvas/src/launcher/templateRows.ts::readinessLabel` already renders
`needs_setup` with a per-reason string. Adding a `"credential_unavailable"` member to
`runtime_templates.py::RuntimeTemplateReadinessReason` and its mirror
`www/packages/core/src/types/runtimeTemplates.ts`, fed by `claude_fleet_credential_error()`
for anthropic-vendored templates and `codex_fleet_credential_error()` for openai-vendored
ones, puts the reason in front of the user at template-list render time on a row that is
already disabled-capable.

This respects constraint 2 by construction: the input is the credential seam's predicate.
The tempting alternative, `api/v1/harness_launch_view.py::_project_harness` (whose
`_authentication_status` / `_unavailable_reason` already produce a `launchable: false` +
`reason` shape the desktop consumes), is precisely the seam that **must not** be used: it is
fed entirely from `item.connections` (probe observations) and `item.compatibility`. Routing
a credential fact through it would make probe output authorize a launch, which S2g item 4
forbids. If the launch view carries credential readiness at all it needs a **separate field
with separate provenance**, never folded into `auth` or `exclusion_reasons`.

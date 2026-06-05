---
title: TM ephemeral home credential broker — scout report
type: scout
project: transport-matters
tags: [transport-matters, auth, credential-broker, reuse-map]
created: 2026-07-26
verified_against: 95affedc (ml/next = origin/main, clean tree)
design: ~/.mdx/design/transport-matters-ephemeral-home-credential-broker.md
---

# TM auth broker — scout report (reuse map, quality map, plan)

Verdict up front: **the design's seams hold at 95affedc with one stale symbol name and
one wrong verdict-family claim.** The materialization seam, the auth-source plan, the
template validation, and the teardown hook are all real and shaped as asserted. The
`credential_unavailable`-as-sibling-of-`model_rejected` proposal targets the wrong
vocabulary; the repo already owns a launch failure contract and a live `auth_required`
condition that together cover both halves. One new risk the design does not address:
managed launches deliberately inherit `CLAUDE_CODE_OAUTH_TOKEN`, which would override the
broker's minted file.

Method note: this worktree has no fmm index (`fmm generate` would write to the tree,
forbidden by the brief), so verification was rg + direct reads.

## 1. Corrections to the design's asserted symbols

| Design assertion | Status at 95affedc |
| --- | --- |
| `cli/home_overlay.py:_link_overlay_credential_files` is the seam, called by both materialize functions, no-ops only because `_symlink_file_if_exists` finds no source | **Confirmed exactly.** Called by `home_overlay.py:materialize_runtime_home_overlay` and `home_overlay.py:materialize_runtime_home_template_overlay`. Credential names come from `home_constants._OVERLAY_CREDENTIAL_NAMES_BY_HARNESS` (`.credentials.json` / `auth.json`). The general symlink pass skips credentials because they sit in `_CLAUDE_OVERLAY_LOCAL_NAMES` — that exclusion is an invariant the swap must preserve. |
| `cli/runtime_home.py:plan_runtime_home` sets `auth_source = native_home` whenever an overlay is active | **Confirmed, but incomplete.** The actual rule is `auth_source = native_home if should_overlay or manual_home is not None else content_source`. Manual (non-overlay) homes also get `native_home` as auth source, and PROXY_ONLY mode gets the manual home. The broker default must replace `native_home` in that expression, which touches the manual-home branch too, not only overlays. |
| `captured_run_context._prepared_home` registers the rmtree callback | **Stale symbol.** No `_prepared_home` exists. The dataclass is `captured_run_context._PreparedHome`; the `stack.callback(shutil.rmtree, runtime_home_root, ignore_errors=True)` lives in `captured_run_context._prepare_home_and_grant`. That is the function slice 3 extends. Note the callback removes `runtime_home_root` (parent of the per-harness child home), and an equivalent duplicate exists in `cli/codex_cmd.py:_prepare_codex_launch_parts` (Codex path, out of broker scope but relevant to the dupe note below). |
| `validate_runtime_home_template` enforces credential-free templates | **Confirmed.** `cli/home_overlay.py:validate_runtime_home_template` rejects entries in `policy.credential_names` and `_validate_template_secret_free` additionally rejects Claude `oauthAccount`/`userID` and Codex secret-shaped TOML keys. Re-exported through `cli/home_seed.py` and `cli/home_seeders.py`; also called at plan time by `runtime_home.py:_validated_template`. |
| Doctor surface for bootstrap/orphan checks | **Confirmed, with a shape constraint.** `cli/diagnose.py:run_doctor` (wired at `cli/__init__.py`) is a linear inline checklist, no registry. It is already ~200 lines against the ~150 guideline; the existing convention for a non-trivial check is a separate helper (`diagnose.py:report_runs_health`). New checks must follow that helper pattern. |
| `credential_unavailable` as a sibling of `model_rejected` | **Wrong family — see Q4/failure surface below.** |
| Root-cause note: `_copy_overlay_local_files(..., pin_claude_config_to_source=True)` explains the bare vs template config split | **Confirmed** at `home_overlay.py:_copy_overlay_local_files`. |

One additional seam the design does not name: `cli/home_seeders.py:_seed_runtime_home_overlay`.
After materialization it re-seeds through `ClaudeSeeder.seed` with the harness home env var
pointed at the **auth source** (when explicit), which is where `userID`/`oauthAccount`
metadata gets merged into the child `.claude.json`. Under the broker, that metadata will come
from `~/.claude-auth`'s config. Harmless for auth (design already established these fields do
nothing), but it means the fleet home's `.claude.json`, not the user's, becomes the metadata
source for launched homes. The builder should know this is expected, not a bug.

## 2. Reuse map

Format: capability → owning symbol, who writes/reads, or "none found" with searches.

**Cross-process locking — EXISTS, do not invent.**
`lock.py:exclusive_file_lock` (src root) is a blocking exclusive `flock` context manager,
kernel-held, explicitly built as "serialize rather than error" — exactly the design's
queue-never-skip requirement. Sibling `lock.py:WorkspaceLock` is the non-blocking fail-fast
variant (wrong semantics here). Each call opens its own fd, so it serializes concurrent
tasks within one process as well as across processes. The broker needs only a lock-file
path (proposal: inside the owner home, e.g. `~/.claude-auth/broker.lock`; the file is not
the credential and holds no data). Postgres advisory locks exist
(`session/migrate.py`, `session/wire_store.py`) but the broker must not depend on the DB.

**Keychain read/write — none found; `security(1)` shell-out is the only path.**
Searches: `rg -ni "keychain|keyring|generic-password|/usr/bin/security" api` → zero
non-test hits; `rg -ni "security find-generic"` → zero. No wrapper exists. The pattern to
copy is `harnesses/probes/runner.py`: blocking `subprocess.run` with hard timeout,
adapter-parsed output, redaction boundary (raw capture stays function-local, failures never
surface command output). Per the probe-fixtures lesson, the keychain adapter's fixtures must
come from a real `security` capture (stdout+stderr+exit), and note `security
find-generic-password -w` writes the secret to **stdout** but errors to **stderr** with
nonzero exit — capture all three.

**Outbound HTTP with retry/timeout — thin httpx, no shared retry helper; none needed.**
Owner pattern: `cli/runs_health.py` ("pure functions + thin httpx client"), sync
`httpx.get(..., timeout=...)` with explicit status handling. Searches: httpx census
(`rg -n "httpx|aiohttp" api/src`) shows per-module clients only; `rg -ni retry` hits are
bind-retry, session-write, and compatibility logic, not an HTTP retry primitive. The
broker's exchange is one POST that must fail closed and raise on ambiguity — retry
machinery would be over-engineering here; a single attempt with explicit timeout matches
both the repo idiom and the "undetected write-back failure must raise" risk line.

**0600 file materialization — EXISTS.**
`atomic_io.py:write_atomic_bytes` (src root, public, `mode=0o600` default, fsync + rename)
is the one to use from a src-root broker. `cli/home_io.py:_write_atomic_secret` and
`_copy_secret_file_if_missing` are private to the cli layer (module-privacy rule: non-test
code must not import another module's privates), so the credential write inside
`home_overlay` can keep using `home_io`, while the broker itself uses `atomic_io`.

**Structured launch verdicts — the family is NOT live_status; three disjoint vocabularies.**
- Launch failure codes: LAUNCH-CONTRACT.md "Failure contract" table owns the closed set;
  in code the closed unions are `harnesses/resolver_contracts.py:ResolutionRejectionCode`
  and `exceptions.py:RunRequestRejectionCode` (enablement ∪ resolution). The contract
  already reserves `materialization_failed` ("operational runtime home could not be
  prepared") and codes like `spawn_failed` that are spec-ahead-of-code today.
- Wire-observed provider conditions: `provider_conditions.py:PROVIDER_CONDITIONS` already
  contains **`auth_required`** — an Anthropic 401 mid-run classifies live via
  `classify_provider_response_status` into the sticky live-status row
  (`live_status.py:LiveStatusKind`, `session/live_status_contracts.py:RUN_LIVE_STATUS_STICKY_KINDS`).
- Harness contract evidence: `controlplane/prompt_models.py:HARNESS_REJECTION_PROMPT_REASONS`
  = `{"model_rejected"}`, minted by `live_status_observer.py` from certified native
  evidence. The module docstrings state these three sets are deliberately disjoint so an
  expired login never mints drift evidence.
- Cost of adding a live-status sibling of `model_rejected` (what the design proposed):
  `live_status.py` kinds + `session/live_status_contracts.py` + SQL in
  `session/controlplane_statements.py` + `controlplane/activity.py` +
  `controlplane/roster_projection.py` + `controlplane/delivery_proof.py` +
  `prompt_models.py`, then the TS plane: `packages/contract/src/activity/wire.ts`,
  `packages/activity/src/ports.ts`, `runActivityEvent.ts`, `runActivityMachine.ts`
  (per-state transition tables), `runActivityTransitions.ts`, `contracts/pg-contracts.json`,
  plus conformance fixtures. That fan-out is the price of the WRONG design; the right
  design (below) costs one failure code or one details field.

**Doctor check registration — none found (no registry).**
`cli/diagnose.py:run_doctor` is inline; convention is one helper per non-trivial check
(`report_runs_health` precedent). Bootstrap check has a strong reuse path: the existing
**authentication probe** — `harnesses/probes/claude.py:_parse` under
`harnesses/probes/runner.py:probe_environment`, which already strips
`HARNESS_CREDENTIAL_ENV_KEYS` so an env token cannot fake a logged-in fleet home — run with
the home env pointed at `~/.claude-auth`. It is nonconsuming (`claude auth status`-shaped,
JSON `loggedIn` authoritative) and already certified (`claude-auth-probe-r1`). Do not build
a second login detector.

**Injection/test-fake patterns in this repo.**
- Callable injection at the composition boundary: `captured_run_context.build_captured_run_context`
  (`which`, `port_in_use`, `allocate_port_pair`, ...) — the broker should enter the launch
  path the same way, as an injected object/callable, threaded
  `captured_run_context._prepare_home_and_grant` → `runtime_home.prepare_runtime_home` →
  `home_seeders.prepare_runtime_home_*` → `home_overlay` (three pass-through signatures).
- Protocol for shape-only contracts: `cli/home_seeders.py:HarnessSeeder` (api/CLAUDE.md:
  Protocol for shape-only, ABC for runtime dispatch). Broker ports (credential store,
  token exchanger) fit Protocol.
- Existing tests to extend: `cli/test_home_seed_credentials.py` already pins the seam's
  three behaviors (links from auth source, skips missing without content fallback,
  teardown leaves the native file).

**Launch-time credential env interaction — new finding, design gap.**
`launch_environment.py:HARNESS_CREDENTIAL_ENV_KEYS` documents that **managed launches
deliberately inherit** `CLAUDE_CODE_OAUTH_TOKEN` (and API-key envs);
`build_launch_env` starts from `os.environ.copy()`. The design's own "ruled out" section
establishes the env var is checked before stored credentials and suppresses them. So a
user shell exporting `CLAUDE_CODE_OAUTH_TOKEN` silently defeats the broker on every
launch. Decision needed (flag to owner, not builder-decided): strip it for broker-backed
Claude launches, or have doctor warn. Stripping changes documented inheritance semantics;
warning is weaker but non-invasive.

## 3. Answers to the four questions

### Q1 — Module placement: src root pure leaf. `api/src/transport_matters/credential_broker.py`.

Consumer list: `cli/home_overlay.py` / `cli/home_seeders.py` (materialization),
`captured_run_context.py` (src root; teardown keychain deletion),
`cli/diagnose.py` (doctor), and plausibly `controlplane/launch_service.py` once
`launch_batch` wants a preflight credential check. That is cli + root orchestration +
(future) controlplane — three consumers across layers, none of which owns keychain/OAuth.
The heaviest consumer (cli) is a false ownership signal, and the design's own counter
argument stands: keychain plus outbound OAuth is not a CLI concern. Precedent is decisive:
`lock.py`, `atomic_io.py`, `manifest.py`, `launch_environment.py` are exactly this kind of
src-root leaf, and `lock.py` + `atomic_io.py` are the broker's two main dependencies.
Placement in `cli/` would also force the src-root `captured_run_context` to import from
`cli` for teardown. One module, well under 700 lines, effects behind Protocols.

### Q2 — Slice 1 is genuinely independent of the probe. Build in parallel.

The unknown is the refresh **request** shape (`client_id`, exact form encoding). Keep
request construction behind a `TokenExchanger` Protocol (input: refresh token; output:
rotated credential) and the core never sees the wire shape. The core's data model does not
depend on the probe either: the credential document schema (`claudeAiOauth` with
`accessToken`/`refreshToken`/`expiresAt`/`scopes`) is already verified against the binary
in the design, and that is what the store port reads/writes and the floor policy consumes.
Everything slice 1 must prove — rotation persisted before the access token is returned,
second caller queues and re-reads, floor policy, fan-out reuse across a batch window —
is exercisable against a fake store and fake exchanger. Only the real exchanger adapter
(one function) waits on the capture. Condition: the brief to the builder must state the
port boundary explicitly, or the shape will leak into the core (gpt-sol's seam blind spot).

### Q3 — Concurrency: nothing serializes this today, and the race becomes reachable the moment the broker exists.

Today there is no race only because there is nothing to race on: for Claude,
`_link_overlay_credential_files` no-ops (no plaintext file exists) and `ClaudeSeeder.seed`
copies inert metadata. The existing serialization is `lock.py:WorkspaceLock` — per
workspace, non-blocking, and it protects instance liveness, not credentials. Two
concurrent launches in different workspaces, or N canvas runs spawned by one API process
(`RunManager` → same captured-run path), share zero mutexes on the credential path.
`launch_batch` makes N-way concurrency the headline feature. So the broker must bring its
own cross-process mutex; `exclusive_file_lock` provides queue-not-skip semantics
(blocking flock, fresh fd per acquisition, so it also serializes intra-process async
callers running in threads). The exchange-plus-write-back critical section and the
re-read-after-acquire both live inside the broker; no launch-path caller may bypass it
because the broker is the only component holding the refresh token (invariant 1).

### Q4 — Blast radius: every Claude overlay/template launch on the machine, plus the user's fleet login.

Consumers of the seam: `captured_run_context._prepare_home_and_grant` (all captured Claude
launches: CLI `transport-matters claude`, canvas `POST /v1/runs` spawns, future
`launch_batch` items) via `runtime_home.prepare_runtime_home` →
`home_seeders.prepare_runtime_home_overlay` / `_template_overlay` → `home_overlay`.
Codex (`cli/codex_cmd.py:_prepare_codex_launch_parts`) flows through the same
`_link_overlay_credential_files` but keeps the symlink path — a broker bug that touches
the shared function shape can break Codex launches too, so slice 2's tests must pin the
Codex symlink behavior unchanged. Failure modes: broker consumes/loses the rotation →
every launch on the machine fails at once and `~/.claude-auth` needs an interactive
re-login (already happened once); broker writes a bad file → launched homes prompt for
login invisibly in detached panes (the current bug, re-created); teardown missed →
keychain orphan accumulation (8 unattributable items exist today). Mid-run expiry is
already surfaced by the existing `auth_required` provider condition — no new machinery.

### Failure surface (design open question 4) — corrected proposal

Fail closed, but in the **launch failure contract**, not live status:
a broker failure before spawn is "operational runtime home could not be prepared", which
LAUNCH-CONTRACT.md already names `materialization_failed`. Recommendation: raise a typed
broker error, let the materialization path surface `materialization_failed` with
`details.reason = "credential_unavailable"`; only mint a distinct top-level code if the
owner wants it addressable in `roster()` filters. Post-launch expiry is already
`auth_required` (wire-classified, sticky, roster-visible). Nothing touches the
`model_rejected` family, and the three-vocabulary disjointness in
`provider_conditions.py` / `prompt_models.py` is preserved.

## 4. Quality map (groom before/with the build)

- **Stale-symbol hygiene:** the design doc should be corrected (`_prepared_home` →
  `_prepare_home_and_grant`, verdict family) before the build brief quotes it.
- **Duplicated home-prep + teardown block:** `captured_run_context._prepare_home_and_grant`
  and `codex_cmd._prepare_codex_launch_parts` repeat plan → prepare → rmtree-callback.
  Slice 3 adds keychain deletion to the Claude side only; do not copy it into codex_cmd.
  A shared prepare-teardown helper is a candidate refactor, but only if slice 3 touches
  both sites anyway — otherwise note and leave (aim rigor at the roadmap).
- **`run_doctor` length:** already ~200 lines; both new checks must be extracted helpers
  (`report_runs_health` pattern), not inline appends.
- **`cli/runtime_home.py` test-only re-export** of `RuntimeTemplateProvenance`/`RuntimeTemplateRef`
  is a NOW.md-acknowledged loose end adjacent to slice 2's files; drop it if slice 2 edits
  the file's imports anyway.
- **`home_overlay.py` at 532 LOC:** headroom exists but slice 2 should keep the broker call
  thin here (one materialize function change), with all broker logic in the new leaf.
- **Env inheritance gap:** `CLAUDE_CODE_OAUTH_TOKEN` inheritance (see reuse map) — owner
  decision required; record it as design open question 7.
- **Injection chain depth:** the broker parameter threads through three signatures
  (`prepare_runtime_home` → `prepare_runtime_home_*_overlay` → materialize). Acceptable;
  do not shortcut with a module-level singleton (that would defeat the fake-driven tests
  and create ambient import coupling).

## 5. Plan (slices bound to the reuse map)

**Slice 1 — broker core.** New `credential_broker.py` at src root. Protocols:
`OwnerCredentialStore` (read/write the owner credential; real impl = `security(1)`
subprocess adapter copied from the `probes/runner.py` pattern, fixtures from a REAL
capture) and `TokenExchanger` (real impl = thin sync httpx POST with timeout, shape
filled in when the wire capture lands). Core: `exclusive_file_lock`-guarded
read → floor check → exchange → **persist rotation via store before returning** → return
access credential; re-read after acquire; raise typed errors (never warn) on write-back
failure. Tests (colocated `test_credential_broker.py`, fakes only): rotation persisted
before return; second concurrent caller blocks then re-reads and does not double-refresh;
floor boundary; exchanger failure raises and leaves the stored credential untouched.
No launch wiring. Gate: `just check` + `just test-affected` (grok runs full `just check`
+ `just test` pre-merge).

**Slice 2 — seam swap.** Rename `_link_overlay_credential_files` to a materialize verb;
Claude on macOS gets a broker-minted real 0600 `.credentials.json` (via the cli-local
`home_io` secret writer or `atomic_io.write_atomic_bytes`), Codex keeps
`_symlink_file_if_exists`; broker injected through the three-signature chain from
`_prepare_home_and_grant`; `plan_runtime_home` auth source becomes the broker-owned home
(default `~/.claude-auth`, configurable through `config.get_settings` like other
`TRANSPORT_MATTERS_*` knobs) — note the manual-home branch of the auth-source expression.
Broker failure surfaces as typed error → `materialization_failed` +
`details.reason="credential_unavailable"` at the contract boundary. Tests: extend
`cli/test_home_seed_credentials.py` (minted file present, 0600, contains no refresh
token; Codex symlink unchanged; template mode identical); a test pinning that
`.credentials.json` is never symlinked for Claude. Gate: same as slice 1.

**Slice 3 — teardown and doctor.** Extend the `stack.callback` in
`_prepare_home_and_grant` to also delete `Claude Code-credentials-<sha256(child_home)[:8]>`
via the slice-1 keychain adapter, idempotent, not-found tolerated. Doctor: two extracted
helpers in `diagnose.py` — bootstrap check reusing the existing authentication probe
(`probes/claude.py` under `probe_environment` with the home env at the broker home;
detection only, login stays user-owned) and the orphan check (enumerate
`Claude Code-credentials-*` items, subtract items whose hash matches a surviving config
dir, offer cleanup behind an explicit flag like `--reap-orphans`). Tests: teardown
deletes file + item and tolerates absence; orphan classifier on fixture inventories.
Integration (live, per design): keychain item snapshot before/after a full launch +
teardown; template overlay launch reaches first turn with no login prompt against the
real binary. Gate: same, plus the live smoke is mandatory before merge (probe-fixtures
lesson).

Parallelization: slice 1 starts now (Q2); the exchanger adapter lands when the wire
capture arrives; slices 2 and 3 depend on slice 1's ports but not on the capture (slice 2
can merge behind a fake-exchanger-driven integration test only if the owner accepts a
dark seam — otherwise hold slice 2's merge until the adapter is real).

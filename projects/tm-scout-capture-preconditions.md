# Scout: complete precondition map for an unattended captured run

Read-only scout on `slice/native-capture-home` at `92ba19ab` (includes today's
`1ce1e1ea` native-home harvest and `92ba19ab` trusted-workdir preflight).
Evidence sources in the order the brief demands: the harness CLIs on this
machine (`claude 2.1.221` native install, `codex-cli 0.146.0`), the native
config files (read only), then our source. Builds on
`tm-scout-native-home.md` (overlay-era seeding map) and does not repeat it.

Launch shape being assessed (`baseline_harvest.py:_capture_cell`): per model
cell, `prepare_captured_run` spawns mitmdump + addon, then the harness child on
a detached PTY (fixed 32x120, `supervisor/pty_process.py:DETACHED_PTY_WINSIZE`),
argv from `cli/launch_profile.py`:

- claude: `claude --model <m> --dangerously-skip-permissions --session-id <uuid> "<prompt>"` — **interactive** mode (prompt as positional arg, not `-p`).
- codex: `codex -c shell_environment_policy.exclude=[...] --model <m> -c model_reasoning_effort=<e> --yolo resume <uuid> "<prompt>"` — interactive resume of a pre-seeded rollout. (Flags-before-subcommand parse verified: `codex --model x --yolo resume --help` exits 0.)

Settle criteria (`_capture_cell`): an exchange with tool schemas whose
`response_ir` exists, the prompt round-trip complete, AND an owned transcript
snapshot containing the prompt plus an assistant row under the run's
`transcripts/` dir. The snapshot writer is the transcript tailer inside
`addon_runtime.py:_start_session_capture`, which requires a live Postgres pool
(`create_async_pool`); since `1ce1e1ea` its failure is a **warning** and the
run continues without transcript capture.

## Claude preconditions

| # | Precondition | Enforced by | Normal-user satisfaction | Unattended harvest today | Evidence |
|---|---|---|---|---|---|
| C1 | Global onboarding complete (theme etc.) | claude gate at TUI startup | Answered once, persisted | **Yes** (native home) | `~/.claude.json` `hasCompletedOnboarding: true`, `lastOnboardingVersion: 2.1.49`; overlay-era counterpart `claude_home.py:ClaudeSeeder.seed` set the same key |
| C2 | Per-project trust of the cwd | claude gate, interactive mode only (`-p` help text: "workspace trust dialog is skipped … non-interactive") | Answer "yes" once per directory | **NO** for the default cwd | Observed screen text today (`Quick safety check: …`); `~/.claude.json` `projects` has NO entry for the old temp dir, `hasTrustDialogAccepted: false` for the repo root, no worktree entries; only 22 of 102 project entries are `true`. Harvest now preflights this (`baseline_harvest.py:main` → `claude_home.py:native_claude_workdir_is_trusted`) and exits 1 |
| C3 | Bypass-permissions acceptance for `--dangerously-skip-permissions` | claude gate, first bypass use | Accept once, or settings skip | **Yes** | `~/.claude/settings.json` `skipDangerousModePermissionPrompt: true` (the exact key `ClaudeSeeder` wrote for this purpose). Global `bypassPermissionsModeAccepted` is unset — whether settings-skip fully covers the interactive dialog is *unknown from evidence*; experiment E3 |
| C4 | Auth present and fresh | claude (keychain OAuth on macOS) | Logged in; auto-refresh | **Yes** on this machine | `installMethod: native`; keychain source accepted since `1ce1e1ea` (`credential_source.py:assert_claude_client_credential_identity` returns early for `KeychainCredentialSource` with no configured home; `runtime_home.py:prepare_runtime_home` skips the credential preflight for keychain). CI/SSH with a locked keychain: *unknown from evidence*; experiment E5 |
| C5 | Route to the proxy | our code | n/a | **Yes** | `captured/claude.py:_build_claude_captured_invocation` sets `ANTHROPIC_BASE_URL` via `build_managed_child_env` `extra_env`; reverse-mode mitm forwards every path (claude's own connectivity check to the base URL, the `/api/hello`-style HEAD, passes through because `addon_handlers.py:handle_http_request` returns untouched for non-`/v1/messages` paths). Caveat carried from the prior scout: claude's daemon env-rebuild route loss — native mode no longer writes `settings.json` `env` (`apply_claude_proxy_env_settings` gated on a runtime home), so daemon-spawned side requests may bypass the proxy; does not block first-frame settle |
| C6 | No hostile env leakage into the child | our code | n/a | **Yes** | `launch/environment.py:build_managed_child_env` strips all proxy env keys, pops `CLAUDE_CONFIG_DIR`/`CODEX_HOME` (native), sets `NO_PROXY=127.0.0.1,localhost`; native `settings.json` `env` block is benign (4 feature flags, no routing keys — read today) |
| C7 | A real TTY with sane geometry | claude TUI | terminal | **Yes** | `pty="detached"` (`c735e25c`), fixed 32x120 winsize (`pty_process.py:DETACHED_PTY_WINSIZE`). `TERM` is inherited, not set; absent-`TERM` contexts (cron/CI): *unknown from evidence*; experiment E4 |
| C8 | Workdir contained in workspace root through symlinks | our code (`secure_workdir` exec wrapper) | n/a | **Yes** | `ffb59739` resolves both sides (`captured/run.py:_secure_workspace_client`), pinned by `test_secure_workspace_client_contains_workdir_across_symlinked_roots` |
| C9 | Proxy up before child spawn; port conflicts retried | our code | n/a | **Yes** | `prepare_captured_run` readiness/bind retry loop (`start_prepared_proxy`, `_BIND_RETRY_ATTEMPTS`) |
| C10 | Transcript settle: channel Postgres reachable by the addon | our settle criteria, not the harness | backend running | **CONDITIONAL** | `_start_session_capture` needs `create_async_pool`; on failure `1ce1e1ea` downgrades to a warning and the run proceeds **without** the snapshot writer, so `transcript_complete` never becomes true and the cell dies as `TimeoutError("first frame or owned transcript did not settle")` — a masked cause. Harvest never calls `check_session_store` (`capture_rpc.py` does; `baseline_harvest.py` does not) |
| C11 | Transcript discovery points at the native home | our code | n/a | **Yes** | `ClaudeLaunchProfile.prepare` computes the descriptor with `claude_projects_root(home_dir=None)` → `~/.claude/projects`, matching where a native child writes; child home env popped so claude uses the same native home |
| C12 | Model actually available to this account | provider | n/a | **Yes** by construction | matrix comes from the account's own `claude -p /model` output (`harnesses/probes/claude.py:MODEL_ENUMERATION_PROBE`); per-cell failures are counted, not fatal |
| C13 | Enumeration probe itself runs unattended | claude `-p` (non-interactive: trust dialog skipped per help text) | n/a | **Yes** | probe commands `("-p", "/model")`, `("-p", "/effort")`; needs auth (C4) and network only |

## Codex preconditions

| # | Precondition | Enforced by | Normal-user satisfaction | Unattended harvest today | Evidence |
|---|---|---|---|---|---|
| X1 | Auth tokens present | codex (`auth.json`) | login once; auto-refresh | **Yes** | `~/.codex/auth.json` carries `tokens` (access/refresh/id), `last_refresh: 2026-08-02` |
| X2 | Per-project trust of the cwd | codex gate at interactive startup | answer once per dir | **Yes at the repo root, unchecked elsewhere** | `~/.codex/config.toml` has 67 `[projects."…"] trust_level = "trusted"` entries including the repo root; the harvest preflight (`92ba19ab`) checks **claude trust only**. Whether `--yolo` (accepted alias for `--dangerously-bypass-approvals-and-sandbox`) suppresses the trust screen: *unknown from evidence*; experiment E2 |
| X3 | Trust of the mitm CA | codex TLS | n/a | **Yes** here, NO on a fresh machine | `cli/trust.py:_build_codex_ca_bundle` raises `MitmproxyCAMissingError` unless `~/.mitmproxy/mitmproxy-ca-cert.pem` already exists (generated by a prior mitmdump run); bundle delivered as `CODEX_CA_CERTIFICATE` env (`build_managed_child_env`) |
| X4 | Explicit proxy route | our code | n/a | **Yes** | `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`/`WS_PROXY` set by `build_managed_child_env(proxy_url=…)`, mitm regular mode; product-plane evidence: attended codex capture ships |
| X5 | Seeded rollout resumable from the native sessions root | codex `resume <uuid>` | n/a | **Yes** (with a hazard) | `CodexLaunchProfile.prepare` → `seed_codex_session(sessions_root=codex_sessions_root(None, env))` → **writes into the real** `~/.codex/sessions`; child's `CODEX_HOME` popped so codex reads the same root. Real-home write on the "native, read-only" philosophy is a design hazard, not a blocker |
| X6 | TTY, geometry, env hygiene, containment, proxy-readiness, Postgres settle | as C6–C10 | — | same status as claude rows | same symbols; the transcript settle (C10) applies identically to codex cells |
| X7 | Enumeration probe unattended | codex CLI | n/a | **Yes** | `codex debug models --bundled` — local, no auth, no TUI |
| X8 | Onboarding / release gates | codex | done | **Yes** (native state) | long-lived `~/.codex` with `config.toml`, `installation_id`, `version.json`; no first-run state remaining |

## Unsatisfied today, ordered by how early it blocks

1. **Claude per-project trust of the harvest cwd** (C2). Blocks at the new
   preflight before any cell — `native_claude_workdir_is_trusted` requires
   `hasTrustDialogAccepted is True` and the repo root is `false`, worktrees
   absent. One attended `claude` visit per intended harvest directory clears
   it on this machine; every new machine and every new directory pays it again.
2. **Channel Postgres reachable by the addon** (C10, both harnesses). Blocks at
   settle, after the POST already succeeded, and since `1ce1e1ea` it fails
   *silently* into the generic timeout. If the backend/DB is running it passes;
   unattended CI or a machine without the channel DB cannot pass. The harvest
   should preflight this the way `capture_rpc.py` does (`check_session_store`)
   instead of discovering it as a timeout.
3. **Latent, codex-only: cwd trust is unchecked for codex** (X2). Satisfied at
   the repo root today; any other `--directory` that codex has not trusted
   fails inside the codex TUI with no preflight (and possibly despite `--yolo`
   — see E2).

Count of remaining layers on this machine, run from the repo root: **2 firm
(C2, C10-if-DB-down), 1 latent (X2)**. Not zero, so the two sessions of
experience remain consistent with the evidence.

## Unknown from evidence — the experiments that settle them

- E1: does claude's trust dialog fire when the project entry exists with
  `hasTrustDialogAccepted: false` (vs absent)? Run `claude` in the repo root on
  a detached PTY, capture first screen.
- E2: does codex's trust screen fire on an untrusted dir under `--yolo resume`?
  Run one codex cell with `--directory` set to a fresh temp dir.
- E3: does `settings.json` `skipDangerousModePermissionPrompt: true` fully
  suppress the interactive `--dangerously-skip-permissions` acceptance dialog
  when `bypassPermissionsModeAccepted` is unset? One detached-PTY launch.
- E4: do the TUIs start with `TERM` absent from the env (cron/CI shape)? Spawn
  one cell with `TERM` stripped.
- E5: does claude fall back or fail when the login keychain is locked (SSH /
  CI shape)? `security lock-keychain` then one probe run. (Do not run this
  unattended on Stuart's machine without asking.)

Unknowns: **5**.

## Cheapest unattended smoke test

- Cheapest proof a POST reaches the proxy and is recorded:
  `api/tests/integration/test_captured_proxy_post.py` (added today) — real
  `prepare_captured_run`, `client_disabled=True`, fake loopback upstream, one
  `urllib` POST through the live mitmdump, asserts `request.raw` on disk.
- CI without credentials: **yes** — no harness CLI, no auth, no Postgres, no
  keychain; it exercises exactly the proxy/capture seam and none of the
  harness gates above. What it cannot prove is any C/X row owned by the
  harness CLIs; those need one credentialed machine with the trust rows
  pre-accepted (C2/X2) and the channel DB up (C10).

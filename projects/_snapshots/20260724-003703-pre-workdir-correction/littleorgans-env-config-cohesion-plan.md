---
title: littleorgans env-var + config cohesion plan
type: plan
status: locked-signed-off (Claude 5:2.1 + Codex 5:2.2, 2026-06-03)
repo: littleorgans/littleorgans
created: 2026-06-03
governing_record: littleorgans-monorepo-migration--synthesis.md
workflow: ~/.mdx/workflows/moe-local-batch.md
moe_warroom: moe-lilo-envcfg (codebase-analyst on Claude 5:2.1 + Codex 5:2.2)
---

# littleorgans env-var + config cohesion plan

## MoE consensus record

Validated by a mixture-of-experts peer-consensus pass (same `codebase-analyst` on Claude
and Codex). Both panes signed off **conditional on a 10-item change set**, now applied below.
Two blockers overturned the original draft:

- **B1 — Item 8 premise was false.** `LILO_LOG_JSON` / `LILO_LOG_FORMAT` are not live format
  knobs. They appear only inside the `#[cfg(test)]` test `lilo_log_json_env_var_has_no_format_effect`
  (`crates/lilo-common/src/logging.rs:102-124`), which asserts they have *no* effect. Production
  format comes from `--output json` + tty (`select_format`, `logging.rs:34-56`). They are two
  **dead** vars. Item 8 is now a deletion; OPEN-Q4 is void.
- **B2 — detector was const-read-blind.** `scripts/check-env.sh` matches `env::var("LITERAL")`,
  not `env::var(CONST)`, so const-indirected reads show as declare-only. Four owned vars are read
  live through consts (`LILO_LOG` @ logging.rs:26, `LILO_GIT_SHA` @ lilo-build-support/src/lib.rs:85,
  `LILO_VERSION_INCLUDE_GIT_SHA` @ lib.rs:72, `LILO_TMUX_SERVER_LABEL` @ runtime/daemon/src/server/config.rs:92).
  A naive "zero reads = dead" sweep would have killed all four. The detector docstring overclaimed.

Also surfaced: inline `#[cfg(test)]` in prod files is mis-tagged PRODUCTION (path-based
`is_test_path`); non-`.rs` legacy is invisible to the gate (`justfile`, `tests/fixtures/v0_5/*`);
and bare `RTM` (no underscore) escapes the `RTM_` prefix match.

## Problem

Two coupled defects, surfaced by `scripts/check-env.sh` (added this session):

1. **Legacy naming.** Three env-var generations coexist: `LILO_*` (ours), `RTM_*`/`SM_*`
   (pre-monorepo legacy), and `HELIOY_*` (broader-brand leakage, now purged — the agent contract
   becomes `LILO_AGENT_*`). Directive: **no legacy or `HELIOY_` referenced or otherwise.** Gate
   fails on `RTM_/SM_/AGM_/HELIOY_` tokens.
2. **No cohesive config layer.** No single `Config` type, no config-file layer beyond per-agent
   TOML. Config is N independent `from_env()` readers with name consts scattered across crates.

Model seams: `lilo-paths` (owns `LILO_HOME`/`LILO_SOCKET_PATH`, derives the tree, rejects legacy)
and `lilo-build-support` (shared build-time version/SHA, standardized on `LILO_GIT_SHA`).

## Ownership rule (the convention being enforced)

One owned prefix `LILO_`, sub-namespaced by audience (Item 15): bare `LILO_` = operator,
`LILO_AGENT_*` = agent contract (injected into spawned agents), `LILO_*` version/sha = build,
`LILO_TEST_*`/`LILO_DEV_*` = internal. There is **no `HELIOY_` namespace**.

- Every var **lilo defines** is `LILO_*` (audience in the sub-prefix).
- Foreign vars we only read (`HOME`, `SHELL`, `PATH`, `CLAUDE_*`, `ANTHROPIC_*`, `CARGO_*`,
  `GITHUB_*`) keep upstream names; not ours to prefix.

`scripts/check-env.sh --check` encodes this: fail on any `RTM_/SM_/AGM_/HELIOY_` (prefixed, or bare
`RTM/SM/AGM`).

## Testing principle (governs Items 7 + 8)

Deletion is proven once — by the diff and a green suite. Do NOT add a standing test that
asserts a removed thing stays gone ("`ENV_X` has no effect", "old path still absent"). Such a
guard is negative-value coverage, often a tautology, and it keeps the dead name alive in the
tree — defeating the deletion and the no-legacy rule. Tests assert what the system does now.
Different in kind, and allowed: live `must-not` invariants (e.g. input must not override a
verified token) and the **namespace lint** (`check-env.sh` is one rule over all names, not a
per-name memorial). So Items 7 and 8 delete their guard tests with **no negative replacement**;
the standing guard against legacy names is the gate (Item 10).

---

## Phase 0 — batch item list (post-consensus)

Branch: `chore/lilo-env-namespace`. One branch, N commits, one PR. Behaviour preserved except
the deliberate contract removal in Item 5. `warroom?` per moe-local-batch scoping rule.

### Item 1 — CLI version env unify (`*_CLI_VERSION` → `LILO_CLI_VERSION`) · warroom NO
- **Target:** `internal/runtime/app/build.rs:8` + `src/lib.rs:13` (`RTM_CLI_VERSION`),
  `internal/session/app/build.rs:38` + `src/lib.rs:18` (`SM_CLI_VERSION`). `crates/lilo/build.rs:2`
  already `LILO_CLI_VERSION`.
- **Desired:** all three emit + read `LILO_CLI_VERSION` (rustc-env is per-crate, no collision).
- **Constraint:** `--version` byte-identical. **Suffix:** "CLI version unify".

### Item 2 — Git SHA unify + de-dup · warroom YES
- **Target:** `crates/lilo-rm-core/build.rs`, `crates/lilo-rm-core/src/version.rs:45`,
  `crates/lilo-build-support/src/lib.rs`.
- **Current:** lilo-rm-core has a bespoke git-sha build.rs emitting `RTM_GIT_SHA` (`--short=12`,
  "unknown" fallback), consumed by `version.rs:45`.
- **Desired:** add `lilo-build-support` pub fn **`emit_git_sha_env(name)`** that emits the *bare*
  SHA as rustc-env with the `unknown`/`None` fallback preserved (published tarball has no `.git`).
  Do NOT reuse `emit_cli_version` (`lib.rs:10-18` emits the package *version* string, not the bare
  `VersionInfo.git_sha` field `version.rs:45` wants). Wire lilo-rm-core to that path; delete the
  bespoke build.rs git logic. Standardize **7-char** (Q1: build-support already `--short=7` @
  `lib.rs:97`, truncates explicit SHAs @ `lib.rs:105-109`; `git_sha` is diagnostic, not the compat
  gate — that's protocol_version + capabilities).
- **Suffix:** "git-sha de-dup".

### Item 3 — Docker preflight knobs (`RTM_DOCKER_*` → `LILO_DOCKER_*`) · warroom NO
- **Target:** `internal/runtime/daemon/src/docker_preflight.rs:9-11`; test harness
  `internal/runtime/app/tests/common/harness.rs:50`; **+ user-facing prose in
  `internal/runtime/daemon/src/error.rs:110`** (`DockerImageNotConfigured` writes
  "...pass --image or set RTM_DOCKER_IMAGE..." — detector-invisible, must flip with the const).
- **Desired:** `LILO_DOCKER_IMAGE`, `LILO_DOCKER_ALLOW_ROOT_IMAGE_USER`,
  `LILO_DOCKER_ALLOW_ARM64_MANIFEST_ESCAPE`; error message updated.
- **Docker session label** (`docker_argv.rs:10`): the const NAME `RTM_DOCKER_SESSION_LABEL` is an
  `RTM_` token the raw-token gate catches → rename to `LILO_DOCKER_SESSION_LABEL`. Per owner the
  label VALUE `io.helioy.runtime-matters.session` → `com.littleorgans.runtime.session` (drops the
  former brand AND legacy `runtime-matters`). Regenerate the `docker_argv` snapshot (`...emits_declared_mounts_in_order.snap:13`).
- **Suffix:** "docker knobs".

### Item 4 — Reconcile timing knobs (`RTM_*_MS` → `LILO_*_MS`) · warroom NO
- **Target:** `internal/runtime/daemon/src/reconcile.rs:27,29,33`; harness `common/harness.rs:56-66`.
- **Desired:** `LILO_PROBE_SWEEP_INTERVAL_MS`, `LILO_RESUME_POLL_INTERVAL_MS`,
  `LILO_RESUME_GAP_THRESHOLD_MS`; same parsing + defaults. **Suffix:** "reconcile knobs".

### Item 5 — Drop spawned-agent RTM_ aliases (CONTRACT CHANGE) · warroom YES
- **Target:** `internal/runtime/launchers/src/lib.rs:108,112` (inject),
  `crates/lilo-rm-core/src/spawn_context.rs:17-18` (denylist),
  `crates/lilo-rm-core/tests/wire_compat.rs:264-271` (env-list assertion),
  **+ fixtures `crates/lilo-rm-core/tests/fixtures/v0_5/shim_launch.json:1` and
  `CAPTURE.md:17-22`** (carry RTM_HOME/RTM_SESSION_ID/RTM_RUNTIME_KIND etc.).
- **Confirmed write-only:** no in-repo `env::var` reader; no helioy-plugins consumer.
- **Desired:** inject only `HELIOY_*`; remove the two RTM_ denylist entries; clean fixtures.
  **Q2: drop, no deprecation note** (pre-release, zero external users). **Suffix:** "drop RTM aliases".

### Item 6 — Test sentinels + bare `RTM` + print-cwd · warroom NO
- **Target / scope:**
  (a) bare `RTM` at `crates/lilo-rm-core/tests/wire_compat.rs:266` + `tests/support/mod.rs:42`;
  (b) `RTM_TEST_PRINT_ENV` (inject `internal/runtime/app/tests/spawn_target.rs:170,286`; read by
  fake-runtime script `tests/common/harness.rs:352`) → `LILO_TEST_*` + matching setter;
  (c) delete the **dead** `RTM_TEST_PRINT_CWD` env branch (`harness.rs:352`) — note the print-cwd
  *feature* stays live via the `.rtm-print-cwd` FILE marker (`integration_pass5.rs:95`,
  `spawn_target.rs:140`); only the `${RTM_TEST_PRINT_CWD:-}` env branch is dead;
  (d) other RTM_ sentinels (`shim.rs:282,288`, `backend.rs:215`, `docker_argv.rs:282`,
  `RTM_E2E_DOCKER`, `RTM_TEST_*`, `RTM_TEST_BAD_BYTES`) → `LILO_`/neutral (rename, inject+read
  in own test, so not deletions);
  (e) **optional hygiene:** rename the `.rtm-print-cwd` marker → `.lilo-print-cwd`
  (`integration_pass5.rs:95`, `spawn_target.rs:140`, `harness.rs:352`);
  (f) **`SHELL_RESUME_SENTINEL`** (`LaunchEnv::new("SHELL_RESUME_SENTINEL", "present")`,
  `shim.rs:316,328`) — a lilo-defined UNPREFIXED var, MoE-verified TEST-only (`shim.rs:312-334`
  fixture). Fold into the sentinel rename → `LILO_*`; the `LILO_` rule admits no exceptions,
  including test sentinels.
- **Suffix:** "test sentinel + bare-RTM sweep".

### Item 7 — Delete lilo-paths legacy-ignored tests · warroom NO
- **Target:** `crates/lilo-paths/src/lilo.rs:291-299` (the `legacy_env_ignored_test!` block within
  176-312).
- **Q3: delete.** The literals keep RTM_/SM_/AGM_ alive against the absolute directive; the central
  gate is the stronger guard, and positive `LILO_HOME`/`LILO_SOCKET_PATH` tests (`lilo.rs:185-228`)
  already cover the live contract. (Also retires B1's negative-guard test.) **Suffix:** "legacy-ignored tests".

### Item 8 — Introduce LILO_LOG_FORMAT, drop LILO_LOG_JSON (OWNER OVERRIDE) · warroom YES
- **Owner override (post-lock):** Stuart directed that `LILO_LOG_FORMAT` become a real, supported
  knob — it is useful and it decouples *log* rendering from `--output` (which renders *command
  results*). Supersedes the earlier MoE Q4=void / "delete both". `LILO_LOG_JSON` (boolean) is still
  removed as redundant with `LILO_LOG_FORMAT=json`.
- **Target:** `crates/lilo-common/src/logging.rs` — add `LogFormat::Compact`; make `select_format`
  READ `LILO_LOG_FORMAT` (today it takes bools and never reads env, `logging.rs:34-56`); wire
  `.compact()` in the subscriber (`logging.rs:58-71`); delete the tautological
  `lilo_log_json_env_var_has_no_format_effect` test (`logging.rs:102-124`).
- **Desired:** `LILO_LOG_FORMAT` ∈ `auto|pretty|json|compact`, default `auto`. Precedence: explicit
  `LILO_LOG_FORMAT` > `--output json` (implies json logs when format unset) > tty heuristic. Delete
  `LILO_LOG_JSON`. Cover the NEW live behaviour with positive tests (the dead test still goes, with
  no negative replacement — Testing principle holds). **Suffix:** "introduce LILO_LOG_FORMAT".

### Item 9 — Documentation sync · warroom NO
- **Target:** `littleorgans/CLAUDE.md` "Data and environment" + README env section.
- **Desired:** document the owned set after renames — `LILO_DOCKER_*`, `LILO_*_MS`,
  `LILO_TMUX_SERVER_LABEL`, `LILO_FAULT_NAMESPACE_BINDING_CLEAR`, `LILO_VERSION_INCLUDE_GIT_SHA`,
  `LILO_GIT_SHA`, `LILO_CLI_VERSION`, **`LILO_LOCAL_BIN`** (justfile-only owned var, `justfile:3`),
  **`LILO_LOG_FORMAT`** (new knob), and the ownership rule. **Suffix:** "env docs".

### Item 10 — Harden + wire the gate · warroom NO (only because spelled out here)
- **Target:** `scripts/check-env.sh`, `justfile`, `moon.yml`/`.moon`.
- **Current gate is UNSOUND (MoE-verified) — fix before it is trusted.** The site-regexes
  (`check-env.sh:40-46`) only match `env::var`/`.env(`/`LaunchEnv::new`/const-decl, so legacy read
  through other shapes ESCAPES: `RTM_{PROBE_SWEEP,RESUME_POLL,RESUME_GAP}_*_MS` via
  `duration_env("…")` (`reconcile.rs:27,29,33`), `RTM_TEST_PRINT_ENV` via `.arg("…=1")`
  (`spawn_target.rs:170,286`), `RTM_TEST_BAD_BYTES` via `OsString::from` (`spawn_context.rs:182`),
  and bare `RTM` (prefix-only `classify`). `--check` passing today does NOT prove the migration done.
- **Detector hardening (required):**
  - **Legacy gate = a RAW token scan** for `RTM_`/`SM_`/`AGM_`/`HELIOY_` and exact bare
    `RTM`/`SM`/`AGM` across ALL files incl. non-`.rs`, INDEPENDENT of the inventory site-regexes.
    Exhaustiveness must not depend on enumerating call shapes.
  - **Self-exclusion:** `scripts/check-env.sh` is the ONE authoritative home for the forbidden
    literals (its scan patterns), so it excludes itself from the scan (cf. `check-seam.sh`'s
    `crates/lilo-sys` prune). Every other repo file — incl. `docs/reference/env-vars.md` — carries
    ZERO forbidden literals and refers to legacy descriptively; the old→new rename mapping lives in
    this plan + release notes, not the repo. This resolves the self-reference contradiction (a
    forbidden-token doc would otherwise fail its own gate).
  - **DELETE the dead `HELIOY_` contract bucket** entirely (not relocate): the header framing
    (`check-env.sh:5-8`), `CONTRACT_PREFIX = "HELIOY_"` (`:50-52`), the `RUNTIME CONTRACT` GROUPS
    entry, and its `classify()` branch all go. After Item 14 the agent contract is `LILO_AGENT_*`,
    which classifies as `OWNED` `LILO_` — no new bucket needed.
  - **Sequencing:** the `HELIOY_`-forbidden gate change lands in the SAME commit as, or strictly
    after, Item 14's rename — never before, or `just check` goes red mid-migration.
  - Trace const-indirected reads for the INVENTORY (`const NAME = "VAR"` → `env::var(NAME)`); fix
    the misleading docstring (B2).
  - Real `#[cfg(test)]` masking (reuse `scripts/check-seam.sh`'s `mask_rust`) for accurate
    test/prod tagging (F3).
  - Scan beyond `.rs`: `justfile`, `tests/fixtures/**`, `docs/**`, `examples/**`, install scripts.
    Prune `.git`, `target`, `.moon/cache`, `.nancy`.
  - Keep the `.sh` extension + `python3` shebang (matches `scripts/changed-crates.sh`); invoke
    directly (`scripts/check-env.sh`), never via `bash`. No `.py` rename — repo convention.
- **Q5: gate ALL authored references**, not prod-only (the directive is absolute and the prod/test
  split is unreliable until F3 is fixed).
- **Wire:** `check-env.sh --check` in `just check` and `moon ci`. **Suffix:** "env gate".

### Item 11 — Central env-var const registry · warroom YES
- **Target:** new module in `lilo-paths` (lowest-dependency published crate, already owns
  `LILO_HOME`/`LILO_SOCKET_PATH`).
- **Q6:** a **minimal const registry** exporting every owned `LILO_*` name once, so no module
  re-declares a literal. **`check-env.sh` MUST consume that authored list as its source of truth**
  (else two lists = ceremony). **NOT** a composed `Config` type (synthesis: no v2 creep).
  **Suffix:** "env const registry".

### Item 12 — Dead + redundant sweep (METHOD FIXED) · warroom NO
- **Method:** liveness MUST trace const-indirected reads (`env::var(CONST)`), not just literals
  (B2). Pair every declare/inject site with a read site.
- **Locked kill list (dead):** `LILO_LOG_JSON` (Item 8 — `LILO_LOG_FORMAT` is NOT dead, it is
  promoted to a real knob); write-only `RTM_SESSION_ID`, `RTM_RUNTIME_KIND` (Item 5); the dead
  `RTM_TEST_PRINT_CWD` env branch (Item 6c).
- **Cleared (real readers, incl. const-reads):** `LILO_BENCH_BIN` (mod.rs:183),
  `LILO_BENCH_SAMPLES` (mod.rs:49), `LILO_TEST_BIN` (mod.rs:295),
  `LILO_FAULT_NAMESPACE_BINDING_CLEAR` (delete.rs:108), `LILO_LOG`, `LILO_GIT_SHA`,
  `LILO_VERSION_INCLUDE_GIT_SHA`, `LILO_TMUX_SERVER_LABEL`. **No redundant live pair exists.**
  **Suffix:** "dead env sweep".

### Item 13 — Complete the HELIOY_SESSION_* caller-env denylist (DEFECT) · warroom YES
- **Found by spec validation.** `CALLER_ENV_DENYLIST` (`crates/lilo-rm-core/src/spawn_context.rs:10-19`)
  strips `HELIOY_SESSION_ID` + `HELIOY_RUNTIME` (+ RTM aliases) but NOT `HELIOY_SESSION_ROLE` /
  `HELIOY_SESSION_WORKSPACE`. The session-daemon spawn path drops all `HELIOY_SESSION_*` before
  upsert (`session/daemon/handler/spawn.rs:392-403`), but the raw runtime host-spawn path
  (`runtime/app/cli/spawn.rs:84-93` → `launchers/lib.rs:96-115`, upserts only ID+RUNTIME) does not —
  so a parent's `HELIOY_SESSION_ROLE`/`HELIOY_SESSION_WORKSPACE` can leak into the child (identity
  bleed).
- **Desired:** strip all `HELIOY_SESSION_*` in the shared caller-env path before child identity is
  injected. **NOTE:** folded into Item 14 — after the `LILO_AGENT_*` rename the denylist becomes a
  single `starts_with("LILO_AGENT_")` rule, which strips ID/RUNTIME/ROLE/WORKSPACE and closes the
  leak. **Suffix:** "denylist leak (via Item 14)".

### Item 14 — Purge HELIOY_ → LILO_AGENT_* (OWNER DECISION) · warroom YES
- **Owner decision:** zero `HELIOY_*` in the repo (brand purity, decision #12); moving away from
  helioy-bus removes the cross-repo consumer, so the rename is free.
- **Agent contract (rename 1:1):** `HELIOY_SESSION_ID`→`LILO_AGENT_SESSION_ID`,
  `HELIOY_RUNTIME`→`LILO_AGENT_RUNTIME`, `HELIOY_SESSION_ROLE`→`LILO_AGENT_ROLE`,
  `HELIOY_SESSION_WORKSPACE`→`LILO_AGENT_WORKSPACE`. Sites: inject `launchers/lib.rs:100,104`,
  `spawn.rs:395,399,403`; read `mcp/server.rs:19`, `cli/mail.rs:261` (const `HELIOY_SESSION_ID_ENV`);
  denylist `spawn_context.rs:15-16` → single `starts_with("LILO_AGENT_")` (subsumes Item 13);
  strip `spawn.rs:392`; tests `wire_compat.rs:267-268`, `conformance.rs`, `cli_mail_direct_test.rs`,
  `common/mod.rs:68`, `spawn/tests.rs:422`; fixture `v0_5/shim_launch.json`.
- **Secret:** `HELIOY_PAT` (test-example only, no prod reader) → `LILO_GITHUB_PAT` (real Actions
  secret, already set). Sites: `spawn_context.rs:155,159`, `tmux.rs:354`.
- **Test example:** `HELIOY_AGENT_NAME` (arbitrary user-env sample in agent-config `[env]` tests,
  not a lilo var) → neutral `EXAMPLE_AGENT_NAME`. Sites: `agent_config.rs` + the `cli_get_test` /
  `mcp_protocol_test` / `handler/agent_config` fixtures.
- **Acceptance:** `git grep -nE 'HELIOY_' -- . ':(exclude)scripts/check-env.sh'` returns nothing
  (the gate script is the sole authoritative home for the forbidden literal; everything else is
  zero). The lowercase `Helioy` brand in prose / Cargo keywords / the
  `io.helioy.runtime-matters.session` docker label is a SEPARATE brand-purge concern (decision #12),
  NOT this env item — pending owner go-ahead. **Suffix:** "purge HELIOY → LILO_AGENT".

### Item 15 — Sub-namespace by audience (OWNER DECISION) · warroom NO
- **Owner decision (option b):** one owned prefix `LILO_`, sub-namespaced by audience: bare `LILO_`
  = operator; `LILO_AGENT_*` = agent (Item 14); `LILO_*` version/sha = build; `LILO_TEST_*`/
  `LILO_DEV_*` = internal.
- **Retarget the internal renames:** `LILO_LOCAL_BIN`→`LILO_DEV_BIN`; `LILO_BENCH_BIN`/`_SAMPLES`→
  `LILO_TEST_BENCH_*`; `LILO_FAULT_NAMESPACE_BINDING_CLEAR`→`LILO_TEST_FAULT_NAMESPACE_BINDING_CLEAR`;
  `RTM_TEST_PRINT_ENV`→`LILO_TEST_PRINT_ENV`; all `RTM_*` sentinels + `SHELL_RESUME_SENTINEL` →
  `LILO_TEST_*` (supersedes Item 6's `LILO_/neutral` target). Operator + build vars unchanged.
- **Suffix:** "sub-namespace by audience".

---

## Open questions — adjudicated

- **Q1 — SHA length:** **7 chars.** build-support is the surviving path and already 7; `git_sha`
  is diagnostic, not the compat gate.
- **Q2 — external RTM_ alias reader:** **drop, no deprecation note.** No in-repo or helioy-plugins
  reader; pre-release, zero external users.
- **Q3 — lilo-paths legacy-ignored tests:** **delete** (Item 7).
- **Q4 — logging format knob:** **owner override → introduce.** B1 was right that no knob exists
  today; Stuart directed building `LILO_LOG_FORMAT` (`auto|pretty|json|compact`) as a real knob and
  dropping the redundant `LILO_LOG_JSON` (Item 8).
- **Q5 — gate scope:** **all authored references**, scanner extended past `.rs`, exact-match bare
  legacy tokens (Item 10).
- **Q6 — registry vs Config:** **minimal const registry in `lilo-paths`, consumed by check-env.sh**;
  no Config type (Item 11).
- **Q7 — completeness:** clean for `.cargo/config.toml`, `moon.yml` (only `CARGO_TERM_COLOR`),
  `toolchains.yml`, `.github/workflows/pr.yml` (no env). Gaps folded into Items 6/9/10.
- **Q8 — dead/redundant:** kill list locked in Item 12.

## Final warroom scoping

- **warroom YES:** Items 2, 5, 8, 11, 14 (genuine design surface: new build-support API, contract
  drop, log-format feature, public-const placement + gate-consumption wiring, HELIOY→LILO_AGENT
  contract rename). Item 13 is folded into Item 14.
- **warroom NO (land directly, gated by `just check && just build && just test`):** Items
  1, 3, 4, 6, 7, 9, 10, 12, 15.

## Execution phases (warroom — one fresh pair per phase)

Driver = `scripts/check-env.sh --check` (hardened, committed `8925218`). Branch
`chore/lilo-env-namespace`. Engineer on Codex implements + commits; reviewer on Claude reviews the
diff + signs off; orchestrator briefs, kills, respawns per phase. Each phase confirms ITS tokens
drop to zero in the gate (other phases' tokens still show — expected) + `cargo` green, then commits.

- **P1 — lilo-paths deletions (Item 7).** Delete the `legacy_env_ignored_test!` macro + invocations
  + `assert_legacy_env_is_ignored` in `crates/lilo-paths/src/lilo.rs`; keep positive tests. Clears
  `RTM_HOME`/`RTM_SOCKET_PATH`/`RTM_DB_PATH`/`SM_HOME`/`SM_SOCKET_PATH`/`SM_DB_PATH`/`SM_NAMESPACE`/
  `AGM_HOME`/`LILO_DB_PATH` (the `lilo.rs` test copies). Verify `cargo test -p lilo-paths`.
- **P2 — operator knobs (Items 3,4).** runtime/daemon: `RTM_DOCKER_*`→`LILO_DOCKER_*` (incl. the
  newly-found `RTM_DOCKER_CONTAINER_PREFIX`; `RTM_DOCKER_SESSION_LABEL`→`LILO_DOCKER_SESSION_LABEL`,
  value→`com.littleorgans.runtime.session`), `error.rs:110` prose, `RTM_*_MS`→`LILO_*_MS`; regen
  snapshots. Verify daemon crate tests.
- **P3 — build/version (Items 1,2).** `RTM_/SM_CLI_VERSION`→`LILO_CLI_VERSION`; add
  `emit_git_sha_env` in build-support, wire lilo-rm-core, `RTM_GIT_SHA`→`LILO_GIT_SHA`, delete the
  bespoke git build.rs. Verify `cargo build --workspace` + `--version` unchanged.
- **P4 — agent contract + alias drop + v0_5 fixtures (Items 14,5).** `HELIOY_*`→`LILO_AGENT_*`
  (inject + readers `mail.rs`/`server.rs` + const + denylist→`starts_with("LILO_AGENT_")` + strip);
  drop `RTM_SESSION_ID`/`RTM_RUNTIME_KIND`; `HELIOY_PAT`→`LILO_GITHUB_PAT`; `HELIOY_AGENT_NAME`→
  `EXAMPLE_AGENT_NAME`; clean v0_5 fixtures (`RTM_CAPTURE_OUT`/`RTM_SHIM_PATH`/bare `RTM` etc.).
- **P5 — test sentinels + internal sub-namespace (Items 6,15).** `RTM_*` sentinels→`LILO_TEST_*`
  (delete dead `RTM_TEST_PRINT_CWD` env branch); bare `SM`; `.rtm-print-cwd`→`.lilo-print-cwd`;
  `SHELL_RESUME_SENTINEL`/`LILO_LOCAL_BIN`→`LILO_DEV_BIN`/`LILO_BENCH_*`→`LILO_TEST_BENCH_*`/
  `LILO_FAULT_*`→`LILO_TEST_FAULT_*`.
- **P6 — LILO_LOG_FORMAT feature (Item 8).** `LogFormat::Compact` + `.compact()` arm; `select_format`
  reads `LILO_LOG_FORMAT`; 3-tier precedence; drop `LILO_LOG_JSON` + its dead test; positive tests.
- **P7 — registry + docs + gate wiring + sweep (Items 11,9,10b,12).** const registry in lilo-paths,
  check-env consumes it; doc sync; **wire `check-env.sh --check` into `just check` + `moon ci`**
  (gate now 0); final dead/redundant sweep. Exit criteria: gate exits 0 + `just check && just build
  && just test` green → open one PR.

## Deferred follow-up (tracked) — Item 16: full LILO_ literal consolidation

P5's Item 11 makes the `lilo-paths` registry authoritative for the owned NAME SET (the gate's
owned allowlist is built from it + flags unregistered owned names) and migrates the ~6 production
env-read consts to reference it. The broader DRY sweep — forbid raw owned `"LILO_..."` string
literals across ALL prod `src/**.rs` (with an allowlist for test dirs, `build.rs`, and `cli.rs`
--help copy) and migrate the remaining ~14 files to the registry consts — is **deferred to Item 16**
(118 raw `LILO_` literals across 39 files; too large for P5). Orchestrator-signed-off descope.

## Parked for a future round — brand purge (NOT env vars)

Owner scoped this round to **env vars only**. The broader brand/legacy-name purge (direction
decision #12) is large — user-facing CLI display names, error messages, MCP instructions + their
GENERATED snapshots, ~40 test image refs — so it parks:

- `runtime-matters` — CLI `display_name`/`about` (`runtime/app/cli.rs:31-32`), error prose
  (`session/daemon/polish.rs`), MCP instructions + snapshots, test images (`*-agent:latest`,
  `runtime-matters-claude:*`).
- `session-matters` — CLI `display_name`/`about` (`session/app/cli/cli_def.rs:13-19`), MCP
  instructions (`generated_instructions.rs`, `tool_docs.rs`, `mcp_bridge.rs:80`) + snapshots.
- lowercase **`Helioy`** in prose — "controls local Helioy sessions" (`generated_instructions.rs`,
  `tool_docs.rs:128`, `mcp_bridge.rs:80`), READMEs (`apps/helix/infrastructure/packages/products/python`),
  `CLAUDE.md`, `docs/architecture/*`.
- Cargo `keywords = ["helioy"]` — `lilo-rm-client/Cargo.toml:12`, `lilo-rm-core/Cargo.toml:12`.
- Docker container-name prefix VALUE `"rtm"` (`docker_argv.rs:9`, builds `rtm-<uuid>` container
  names) — lowercase, gate-safe; the const NAME is renamed to `LILO_DOCKER_CONTAINER_PREFIX` in P2
  but the value stays `"rtm"`. Flip to `"lilo"` (→ `lilo-<uuid>`) in the brand round for consistency.

**Gate-scope note:** the raw-token gate (Item 10) catches `RTM_/SM_/AGM_/HELIOY_` tokens including
CONST NAMES and identifiers (e.g. `RTM_DOCKER_SESSION_LABEL`), not just env-var strings — those are
in THIS round. But `runtime-matters`/`session-matters`/lowercase-`helioy` contain no
underscore-prefixed token, so they do NOT trip the env gate; parking them keeps this round green.

## Acceptance

- `scripts/check-env.sh --check` exits 0 (all-reference scope, bare-legacy matches, non-`.rs`).
- `just check && just build && just test` green.
- `--version` output unchanged (Items 1-2).
- No `RTM_`/`SM_`/`AGM_` literal (prefixed or bare) anywhere the gate scope covers, incl. fixtures,
  justfile, docs, and user-facing error prose.

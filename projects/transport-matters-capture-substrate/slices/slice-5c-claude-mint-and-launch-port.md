# Slice 5c — claude managed-mint + a unified, DRY managed-launch port

**Goal (two parts, both required):**
1. **Realize the original Phase A design for claude:** `transport-matters claude` mints a uuid and
   launches `claude --session-id <uuid>`, so TM **owns** the correlation id by construction instead
   of adopting whatever claude picks. `minted=True`.
2. **Generalize the launch side into ONE clean DRY path** so claude, codex, and any *future*
   mint-capable CLI share a single managed-launch abstraction. No per-provider copy-paste in the CLI.
   Adding a new mint-capable CLI must be "implement one small profile," not "fork the launch flow."

**Keep native-adopt** as the **external-adoption fallback** (a claude session TM did NOT launch, or
any case with no owned id/descriptor). It stops being the *primary* path; it stays as the read path
for un-owned sessions. Symmetric to how 5b left codex's glob as external-only.

**Depends on:** 5b merged (#26, `abe1895`) — its env-var pipeline, `source_descriptor` decode, the
descriptor branch in `register_session_cursor`, and session-row stamping are REUSED wholesale.
**Branch:** off current `main`.

## Why (context — do not re-litigate)

The Phase A spec always specced claude as MINT (own the uuid). Slice 2 deferred it as a "proxy
`--session-id` mint" (mischaracterized as proxy-side work), slice 4a's HARD GATE then made
native-adopt look "good enough," and the deferral shipped. native-adopt is the weaker design for a
capture tool: its correctness depends on an external invariant TM doesn't control (`wire
metadata.session_id == transcript sessionId == filename stem`, guarded by "if equality ever fails →
STOP"). Owning the id makes correlation true by construction and deletes that fragility. Stuart's
call: do it right, generalize it cleanly.

## VERIFIED (real claude 2.1.165, two runs) — do not redo unless you want to re-confirm

- `claude --session-id <uuid>` **CREATES** a session (no pre-existing file; unlike `codex resume`
  which needs a seed). EXIT=0, model answered.
- claude adopts the injected uuid as its own `session_id` on two surfaces that must agree: the
  headless `system/init` event (`session_id == injected`) and the transcript first record
  (`sessionId == injected`).
- Transcript lands at the deterministic path `~/.claude/projects/<cwd-slug>/<uuid>.jsonl`.
- Implication: **claude needs NO seed file** — just the flag + the (already deterministic) descriptor.

## The DRY design ask (the heart of this slice)

Today the launch side is provider-special-cased: `cli/start_cmd.py` (claude) vs `cli/codex_cmd.py`
(codex), and 5b's env vars are codex-named (`*_CODEX_NATIVE_SESSION_ID`, `*_CODEX_SOURCE_DESCRIPTOR`).
That is the duplication to kill. Design a **single managed-launch path** driven by a per-provider
**launch profile** — the launch-side counterpart to the read-side `TranscriptAdapter`
(bind/locate/normalize). A profile answers, for its CLI:
- **mint-capable?** does the CLI accept a caller-specified session id?
- **inject** — how to put the owned id into argv (claude: `--session-id <uuid>`; codex: `resume <uuid>`).
- **prepare** — does launching require pre-seeding the transcript, and how to produce the
  `source_descriptor` up front (claude: compute the deterministic path, no seed; codex: seed the
  minimal `session_meta` rollout, then the path).
- **session_id / minted derivation** (claude: id used directly, `minted=True`; codex: current synth).

Then both `transport-matters claude` and `transport-matters codex` flow through the SAME managed
launch, and a future mint-capable CLI = one new profile, zero launch-flow duplication.

> The exact shape (port/ABC vs strategy vs dataclass registry) is the **author's design call** —
> justify it; reviewer checks it for DRY, cohesion, and that adding a profile touches nothing else.
> Do NOT bolt `--session-id` onto claude as a one-off; that defeats the slice.

Generalize the 5b env vars to **provider-neutral** names (DRY); claude reuses them, no `*_CLAUDE_*`
duplicates. Touches codex env emission → the panel must prove codex does not regress.

## Locked decisions (don't re-debate)

- claude: mint via `claude --session-id <uuid>`, `session_id = native_session_id = <owned uuid>`,
  `minted=True`, `source_descriptor` (file_tail, claude_jsonl, the deterministic path) persisted at
  launch → claude rides the SAME descriptor branch codex uses; **no seed**.
- native-adopt retained for external adoption (no owned id/descriptor → fall back to `locate`).
- codex stays functionally unchanged (resume + seed + synth `session_id` + `minted=False`), just
  refactored onto the shared launch path.
- Honor user passthrough: if the user already passed `--session-id`/`--resume`/`--continue`, DO NOT
  inject (their flag wins); document the precedence.

## Panel-decides (flag a recommendation, don't silently expand scope)

- Now that managed codex owns a unique uuid4 native id, is its `uuid5` `session_id` synth still
  warranted, or could codex also use the native id directly (unifying derivation, dropping
  `minted=False`/`True` split)? **Default: leave codex's correlation key as-is** (it's the idempotency
  PK + partial-unique index; churn = regression risk). Only unify if it is clean AND you prove zero
  correlation regression. Otherwise document why codex keeps synth.

## Invariants (must not break)

- `locate` STAYS (external adoption) but is OFF the hot path for managed launches (descriptor branch
  resolves first). Managed claude must NOT depend on `locate`.
- #17 privacy boundary (AST-enforced); DAG (adapters import `ir`/siblings only; launch path uses the
  injected sink, no `storage → index`); ONE iterate path (`iter_complete_records`).
- claude's existing wire correlation must keep working: with the owned id, wire `metadata.session_id`
  == the owned uuid (verify on a real run).
- LOC ≤ 700/file, functions ≤ ~150.

## Files (RE-CONFIRM current line numbers against main)

`cli/start_cmd.py` (claude argv build, was :106 `[claude_path, *passthrough]`); `cli/codex_cmd.py` +
`cli/codex_session.py` + `cli/home_seed.py` (codex managed launch — refactor onto the shared path);
`cli/launch_runtime.py` (`build_launch_env`, codex env emission was :453-470); the centralized
env-keys module (generalize names); `index/ingest.py` (`build_run_facts`/`bind_exchange`, codex
managed-mint at :55/:111/:130 — add the claude owned-id path); `index/adapters/claude.py` (bind
:46-61 → `minted=True` when owned, keep native-adopt fallback; `locate` :64 retained for adoption);
`index/adapters/base.py` (`SessionBinding.minted` :38, `locate` default :150); `index/tailer.py`
(`register_session_cursor` :185, descriptor branch :229-236 — claude now uses it).

## Regression (ALL required)

- **(a) claude managed-mint deterministic:** launcher mints + injects `--session-id`, binding has
  `minted=True` + `source_descriptor`; cursor registers from the descriptor; appended record → one
  transcript job from the exact owned path.
- **(b) descriptor branch, not locate:** assert managed claude resolves its source via
  `source_descriptor` (decode), and that `locate` is NOT called on the managed path.
- **(c) external-adoption fallback intact:** a claude session with no owned id/descriptor still
  resolves via `locate` (native-adopt), `minted=False`.
- **(d) codex non-regression:** the 5b codex managed-mint tests stay green through the refactor.
- **(e) DRY proof:** a test (or a second/fake profile) demonstrates that adding a mint-capable CLI
  plugs into the shared path without touching the launch flow. At minimum, claude and codex are shown
  to share one managed-launch entry point.
- **(f) REAL-RUN PROOF (the gate):** a real `transport-matters claude` session through the proxy →
  wire `metadata.session_id` == the owned uuid == transcript filename stem; session row `cli='claude'`,
  `minted=1`, non-empty `source_descriptor`; live `transcript_turn` event; the DIFF/pivot resolve.
  State the evidence. (This is a green path we're changing — unit tests are not sufficient, per the
  recurring "green in tests, broken on a real run" lesson.)

## Acceptance

`just ci` green + the real-run proof. Dual MoE sign-off → orchestrator gates + PR + squash-merge.

## Spec / docs fast-follow (post-merge)

§5.1 claude: "deferred MINT" → realized managed-mint (`minted=True`, owned id), native-adopt noted as
external-adoption fallback. §5.5 row. §4.2 if the launch port lands there. LEDGER + README (5c) +
roadtest (claude now minted; what the session row should show).

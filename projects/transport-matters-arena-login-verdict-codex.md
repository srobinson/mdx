# In app harness login driver verdict

Baseline: `main` at `83f3decfc39b5eba1bba42b3ee61e3b286987f9f`.
Scores use 5 as strongest.

| Candidate | Fixed constraints | Reuse map | Red flags | Interface depth | Idempotency and state | Outcome and reread | Citations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 4. Correct sibling PTY; director input vague | 4. Strong seam use | 3. Wire types leak through common | 4. Small harness resource | 3. Detach works; restart omitted | 3. No reread failure state | 4. One imprecise locator |
| B | 5. Meets every fixed boundary | 4. Reuses PTY and query seams; repeats home key | 4. PTY exit type crosses API | 4. Rich behavior behind four operations | 5. Token retry, harness exclusion, detached watcher | 5. Best typed result taxonomy | 4. Two undefined usage helpers |
| C | 4. Correct spawn and input paths | 4. Best use of `probe_environment` | 2. Caller coordinates process and verdict | 3. Five operations expose stages | 3. Harness adoption works; restart means respawn | 2. Exit view omits credential result | 4. Baseline names exist |
| D | 5. Strong director and UI paths | 4. Correct owners; incomplete spawn env | 3. Home and gateway process types leak | 4. Good attempt resource | 4. Home exclusion is sound; restart claim is weak | 4. Predicate leads, but reread failure is untyped | 5. Best correction of scout symbol |

## Red flags found

- A, `transport-matters-arena-login-claude.md`, Shape, `packages/common/src/loginContract.ts`: information leakage. Raw gateway request and exit wire types become shared public types. Usage also ties readiness invalidation to an attached socket, so pane detachment can leave the launcher stale.
- B, `transport-matters-arena-login-codex.md`, Gateway session model: information leakage. Public `LoginResult` embeds runtime `PtyExitEvent`. The control plane needs stable process evidence rather than an adapter type.
- C, `transport-matters-arena-login-grok.md`, Usage and Shape: shallow module plus temporal decomposition. A caller must read `login_status`, detect exit, then call launch readiness to obtain the actual result. `LoginSpec.display` is also stored while the design says it is derived.
- D, `transport-matters-arena-login-opus.md`, Python API shape: information leakage. `LoginAttempt.home` exposes an internal credential path unused by the caller. `login_outcome` also accepts a gateway transport type rather than private domain process evidence.

## Citation defects

- A claims `FirstRunScreen.tsx::HarnessSection.retry`. `HarnessSection` exists, while `retry` is a local closure rather than an addressable member.
- B calls `loginSessionId(...)` and `applyEnvironmentPatch(...)` in Usage. Neither exists on `main`, and neither receives a signature in Shape. The branded type alone does not provide runtime validation.
- B says the login terminal reuses snapshot replay through `useTerminalSession`. On `main`, replay behavior is selected only for `endpoint.kind === "captured-run"`; the module map omits the required hook change.
- D supplies only the home variable to `browserPtyEnvironment`. `NodePtyAdapter.processEnvironment` treats a supplied env as complete, so the sketch can discard `PATH` and fail to resolve Homebrew installed harnesses.
- C has no missing cited baseline symbol. Its proposed call `resolve_login_spec("claude")` conflicts with its own required `native_home` parameter.

## Base

Use B. Its app scoped coordinator continues watching after a pane detaches, its client token makes network retries deterministic, and its gateway state machine cleanly separates process exit, credential evaluation, cancellation, spawn failure, and readiness failure. The prepare and evaluate port keeps credential policy in Python while the gateway owns the PTY. The substantive defect is restart recovery: process local records vanish, a waiting director receives a missing session, and retry can start a second attempt without a typed `session_lost` outcome. The design must resolve that before implementation. It should also replace public `PtyExitEvent` with control plane process evidence and derive home keys through `HOME_DIR_ENV_BY_HARNESS`.

## Grafts

1. Take A's bounded raw PTY tail and late attach replay because directors and reopened panes need the fallback URL without a vendor text parser.
2. Take D's bounded `wait_ms` control plane read and `login_input` tool because a director should finish paste code flows without implementing WebSocket terminal transport.
3. Take D's home keyed live exclusion because the credential home is the shared write target. Keep the home key private to the gateway.
4. Take A's pure `login_verdict` function because one tested function should combine typed process evidence with the fresh credential check and B's full failure taxonomy.

## Reject

1. Reject A's and C's state strings paired with nullable fields. They admit invalid combinations and weaken failure handling.
2. Reject C's separate process status and readiness verdict. It pushes lifecycle coordination into every caller.
3. Reject D's first `https://` match as the canonical fallback URL. A help link can precede the login link; bounded raw output remains truthful.
4. Reject public home paths, argv, env, and runtime PTY types. These are private spawn and adapter decisions.
5. Reject socket close as the only readiness refresh trigger. An app scoped watcher must finish after pane detachment.
6. Reject silent record loss on gateway restart. Return a typed lost outcome or persist the minimal idempotency tombstone.

## Open questions

- Must a finished or interrupted attempt remain queryable after a gateway restart? If yes, which existing store owns the minimal tombstone?
- Should a second browser receive the active session id and attach, or only learn that the harness home is busy?
- Is bounded raw output sufficient for director fallback URLs, or should each verified harness provide a typed URL extractor with conformance tests?
- Should Grok's unverified command show an enabled action with a warning, or remain unavailable until an observed binary proves command and home behavior?
- Does cancellation require process group termination to cover callback servers and child browser launchers?

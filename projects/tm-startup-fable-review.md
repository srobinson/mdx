# Review: PR #357 `feat/startup-gate` @ 4ab2612b

Precursor: `.warroomagents/fable5.md`. Architecture: `docs/ARCHITECTURE.md`.
Tree: detached worktree at 4ab2612b (pristine). Shared checkout not used.

## Ownership map (built during review)

| State | Writer | Readers | Precedence |
| --- | --- | --- | --- |
| `LaunchReadiness.ready` | `captured.readiness.launch_readiness` | canvas gate, launcher rows | single writer |
| `LaunchReadinessCheck` rows | `captured.readiness` check builders | API, canvas, ⌘K | single writer |
| Infra remediation strings (mitmdump/node/gateway/enablement) | `infrastructure_guidance.*` attached in readiness | doctor (partial), canvas | leaf intended |
| Session-store remediation | **split** (see finding) | doctor vs readiness | **none** |
| Product name constants | `product_identity` | `cli.identity` re-export, guidance | single writer |
| Gate UI decision | client derives from server `ready` | `SessionCanvasRoute` | server owns bit |

## First check: second writer without precedence?

No second writer on `ready` or on the gate bit itself. Frontend infrastructure catalog is gone; canvas renders `check.remediation` from the payload.

**Residual dual writer on session-store remediation content** (see finding). Doctor and readiness attach different guidance for the same failure class without a shared function.

## Answers

1. **Architecture.** Source-root leaves match the cli ratchet placement rule for multi-consumer pure data. `product_identity` is a genuine pure leaf; `cli.identity` is a thin re-export adapter. `infrastructure_guidance` is correctly placed for multi-consumer guidance, but is not pure: it imports `session_store_preflight.session_store_setup_help` (settings/migrations graph). No new displaced code landed in `cli/`; doctor only gained leaf imports. Capture-rpc/main adjacency not worsened by this slice.

2. **Re-entrancy.** No persisted "seen" / first-run flag. Gate is `SessionCanvasRoute` reading `useLaunchReadiness` each mount. `useLaunchReadiness` uses React Query with `staleTime: Infinity` and `refetchOnMount: false`, so recheck is cold-start or explicit Retry, not continuous. Process/app restart re-enters. Mid-session store loss without reload stays sticky until Retry.

3. **Spawn not weakened.** `templateRows.launchBlockedReason` still blocks on infrastructure failures (`harness_id === null`) **or** that harness's own failed checks. Overall `ready` is infrastructure-only and is not treated as "harness launchable." Opening workbench with zero harnesses is allowed; launching a specific harness still needs its checks green.

4. **Remediation home.** Mitmdump / node / gateway doctor paths render from `infrastructure_guidance`. Session store doctor paths still compose local strings via `cli.diagnose._session_store_failure` + `config.database_url_guidance`, not `infrastructure_guidance.session_store_unavailable_remediation`. Addon reinstall string remains local in doctor. Partial move, not full single home.

5. **Forward checks.** Canvas maps failures generically (`check.label`, `check.detail`, `check.remediation`). Test pins unknown check id `future_infra_probe` still renders server remediation. A new server check with populated `remediation` appears without frontend change; null remediation shows detail only (no invented catalog).

## Finding

### medium — dual session-store remediation writers

- **owned state:** operator remediation text for session store unavailability
- **writers:** `infrastructure_guidance.session_store_unavailable_remediation` (readiness/canvas) and `cli.diagnose.run_doctor` session-store failure branches (`_session_store_failure` + `database_url_guidance`)
- **precedence:** none; same failure class yields different guidance depending on surface
- **why in scope:** slice claimed one leaf for doctor and readiness; doctor session-store path was left on a parallel composition

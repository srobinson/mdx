# littleorgans Transport Capture Study

Status: COMPLETE

Updated: 2026-07-31

## Governing frame

- Transport capture is a mandatory first class littleorgans product capability.
- `tm` and transport-matters are experimental research only.
- littleorgans will not invoke, package, version against, or depend on `tm`.
- The study extracts validated requirements, invariants, failure lessons, and test patterns.
- No product implementation is authorized in this study.

## Baselines

- littleorgans: `98d8928941b5b5db670ed73ed06af57f61dcfa0a`
- transport-matters: `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55`

## Phase 1

Independent reports in progress: none.

Completed and status-verified:

- `littleorgans-transport-capture-boundary-map--brainstorm.md`
- `littleorgans-transport-capture-capability-taxonomy--brainstorm.md`
- `littleorgans-transport-capture-data-authority--brainstorm.md`
- `littleorgans-transport-capture-mechanics--study.md`
- `littleorgans-transport-capture-product-boundary--study.md`
- `littleorgans-transport-capture-product-contract--brainstorm.md`
- `littleorgans-transport-capture-protocol-research--brainstorm.md`
- `littleorgans-transport-capture-reject-map--brainstorm.md`
- `littleorgans-transport-capture-research-program--brainstorm.md`
- `littleorgans-transport-capture-security-durability--study.md`
- `littleorgans-transport-capture-test-evidence--brainstorm.md`
- `littleorgans-transport-capture-topology-options--brainstorm.md`
- `littleorgans-transport-capture-user-value--brainstorm.md`

## Phase 2

Synthesis inputs in progress: none.

Synthesis inputs completed and status-verified:

- `littleorgans-transport-capture-current-code-reuse--synthesis-input.md`
- `littleorgans-transport-capture-enterprise-gates--synthesis-input.md`

Definitive synthesis completed and status-verified:

- `littleorgans-transport-capture--synthesis.md`

## Adjudicated corrections

- The phase-one claim that the pinned Transport Matters credential sources
  fail to parse is retracted. The exact `a252df24` blobs for
  `cli/credential_source.py` and `credential_refresh.py` both parse under the
  project interpreter, Python 3.14.5. The earlier failures used an older
  ambient interpreter.

## Phase 3

Independent peer reviews in progress: none.

Independent peer reviews completed and status-verified:

- `littleorgans-transport-capture-peer-review-claude.md`
- `littleorgans-transport-capture-peer-review-codex-architecture.md`
- `littleorgans-transport-capture-peer-review-codex-evidence.md`

Peer consensus completed and status-verified:

- `littleorgans-transport-capture-peer-consensus.md`

Single bounded correction round completed with sign-off closure:

- `littleorgans-transport-capture-synthesis-correction-round--status.md`

Delta sign-offs in progress: none.

Delta sign-offs completed and status-verified:

- `littleorgans-transport-capture-peer-signoff-codex-architecture.md`: PASS
- `littleorgans-transport-capture-peer-signoff-claude.md`: FAIL
- `littleorgans-transport-capture-peer-signoff-codex-evidence.md`: FAIL
- `littleorgans-transport-capture-peer-consensus-signoff.md`: FAIL

Sign-off blockers closed and final-verified:

- B-1: synthetic capture faults must carry machine-readable `lilo` origin.
- B-2: power-loss durability must be scoped per artifact class.

Final delta sign-offs in progress: none.

Final delta sign-offs completed and status-verified:

- `littleorgans-transport-capture-peer-final-signoff-claude.md`: PASS
- `littleorgans-transport-capture-peer-final-signoff-codex-architecture.md`: PASS
- `littleorgans-transport-capture-peer-final-signoff-codex-evidence.md`: PASS
- `littleorgans-transport-capture-peer-final-consensus.md`: PASS

## Final outcome

- Canonical study:
  `littleorgans-transport-capture--synthesis.md`
- Canonical SHA-256:
  `9a8c03f7ca7016cc5c2d0c3a0089b8308293fd6890896863d818fda3fafc9a22`
- Canonical line count: 552
- Final consensus: PASS from all three independent reviewers.
- Remaining P0/P1 review findings: none.
- Product code changed: none.
- Repository learning recorded: `LESSONS.md`.
- Archived reviewed states:
  `.archive/littleorgans-transport-capture--synthesis.v1.md` and
  `.archive/littleorgans-transport-capture--synthesis.v2.md`.

## Remaining phases

None. The study is published under `~/.mdx/projects/`.

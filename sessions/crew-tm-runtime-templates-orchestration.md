---
title: TM runtime-template browse read-side orchestration (PR #143)
type: sessions
tags: [helioy-warroom, orchestration, transport-matters, capabilities-json, runtime-templates, harness-vendor]
summary: Orchestrated a warroom that delivered the TM browse read-side for runtime-template capabilities; dual-clean, gate-green PR #143 awaiting Stuart's merge.
status: active
source: orchestrator
confidence: high
created: 2026-06-18
updated: 2026-06-18
---

# TM runtime-template browse read-side — orchestration record

## Task

Handed off via helioy-bus by `transport-matters:general:1:1.1`: own end-to-end the TM
**browse read-side** for runtime-template capabilities. Four pieces: (1) capabilities.json
reader, (2) TM-owned harness→vendor compat map, (3) `list_runtime_templates`,
(4) `GET /v1/runtime-templates`. Browse read-side ONLY — launch-time flag injection,
`CreateRunRequest` extension, and the eval/override path are the explicitly-deferred next layer.

## Grounding decisions

- **Authoritative schema** = `~/.agent-runtimes/bin/generate.py` (`derive_capabilities` /
  `_recommended_model`), not a doc summary (Stuart redirected here). Validated against REAL
  fleet artifacts: imagegen (openai-only), research (dual-vendor, model+effort), codebase-mapper
  (by_vendor effort-only, no model).
- **No "v2" anywhere in TM code** (Stuart). The reader is just THE reader; old paths replaced,
  not paralleled. Branch `feat/runtime-templates-read-side` (not `...-v2`).
- **Harness support** (Stuart): claude/codex are live; opencode/pi forward-compat only. Reader
  still parses all four because `generate.py _HARNESSES` permits them. pi vendor set provisional.
- **flat vs tree-walk**: tree-walk, because `_validated_template_name` already permits nested
  names (test `test_resolve_runtime_template_allows_nested_relative_names`); flatness is
  data-shape, not contract.

## Warroom

`tm-runtime-templates`, cwd = worktree `transport-matters-worktrees/runtime-templates-read-side`
off main (1481a82, #142). Mode 5 slice-build-loop, mixed-runtime MoE:

| Pane | Runtime | Role |
|------|---------|------|
| %281 | Codex | backend-engineer (build) |
| %282 | Claude | engineering-code-reviewer (primed `/code-review` + `/code-hygiene`, context-first) |

## Loop

1. Engineer → PR #143 @ 0de83ed. Orchestrator verified: gate green (1568 passed), no v2, scope held, pi flagged.
2. Reviewer (adversarial) → 4/5 confirm clean + 2 refuted false positives; **1 LOW**: `GET /v1/runtime-templates`
   could 500 on a bare `ValueError` from a degenerate discovered name ("." root-level artifact). + nit (redundant sort).
3. Fix round → make discovery TOTAL (skip degenerate names via try/except), + 2 tests, + pi comment to forward-compat
   wording; nit left (conditional on dedup determinism). @ c118b68.
4. Orchestrator re-gate: 1570 passed, check clean. Reviewer delta-verify → `review: clean`.
5. Verify-don't-trust: PR head == c118b68 (local==remote, pushed), all 6 CI checks pass.

## Outcome

Dual-clean, gate-green PR #143 surfaced to Stuart (human holds merge). Completion reported upstream
to `transport-matters:general:1:1.1`. Decisions persisted to cm.

## Patterns that worked

- Verify every bus `done`/`clean` claim from disk/gh/git before acting; the reviewer's evidence and
  my own gate run agreed at each step.
- Prime reviewer context-first via send-keys (standby line → `/code-review` → `/code-hygiene`),
  verifying each submitted via `capture-pane`; full brief over the bus once primed.
- Bundle review findings + a small clarification (pi comment) + an optional nit into ONE fix round.
- In-slice fix round needs no pane compaction (build context is an asset for the same files).

# Littleorgans Transport Capture Synthesis Correction Round

Status: COMPLETE

Worker Status: COMPLETE

## Scope

Apply consensus corrections CS-1 through CS-16 once to the canonical synthesis.
Preserve the archived v1 as immutable evidence and keep the edit bounded.

## Allowed writes

- `~/.mdx/projects/littleorgans-transport-capture--synthesis.md`
- `~/.mdx/projects/littleorgans-transport-capture-synthesis-correction-round--status.md`

## Progress

- Consensus and canonical synthesis review: COMPLETE
- Corrections CS-1 through CS-16: COMPLETE
- Self-audit and bounded-delta proof: COMPLETE
- Sign-off closure B-1, B-2(b), F-2, and F-3: COMPLETE

## Changed sections

- First-screen framing and sections 1 through 4: managed inference scope,
  honest launch truth, spawn coverage matrix, and coordinator boundary.
- Sections 5 through 7: reuse corrections, delete-path repair, artifact
  vocabulary, and redirect-mode feature regression.
- Sections 8 through 10: split authority, recovery precedence, digest domain,
  same-UID threat model, daemon reads, lease readiness, durability primitives,
  availability budgets, resource bounds, and harness fault response.
- Sections 11 through 14: exhaustion order, terminate-then-erase, lineage
  closure, typed read contract, fidelity suites, enterprise integrity, legal
  gate, compatibility, and migration gates.
- Sections 15 through 17: gate exits, corrected ledger, and the CS-1 through
  CS-16 self-audit map.

## Stuart-owned unresolved decisions preserved

- U1 mid-run capture loss.
- Gate 3 dispositions for Codex, Docker, `RuntimeKind::Other`, and raw spawn.
- U9 enterprise legal posture.
- U11 retention age, global size, warning, reserve, and per-session values.
- U13 body redaction versus encrypted verbatim storage.
- U14 future hold capability.
- U15 Remote Control tradeoff under redirect capture.
- U16 separate termination-without-erasure verb.

## Bounded delta

- Archived v1 SHA-256:
  `d3200b2eb0f4e81c106a8b5bc02ba82289cdd2da724a61493d79ab89c583bdf4`
- Archive size remains 60,506 bytes.
- Canonical is 543 lines, below the 700-line limit.
- Diff is 216 insertions and 107 deletions. It retains 327 of 434 original
  lines, approximately 75 percent, while applying the sixteen specified
  corrections.

## Verification commands

- `git diff --no-index --check <v1 archive> <canonical>`
- `git diff --no-index --numstat <v1 archive> <canonical>`
- `wc -l <canonical>`
- `rg` checks for CS-1 through CS-16 anchors and both source pins
- `rg` negative checks for em dashes, `immutable`, `by construction`,
  passthrough-perfect fidelity, and direct-read v1 claims
- `shasum -a 256 <v1 archive> <canonical>`

No repository file was edited during this correction round. The existing
`LESSONS.md` worktree change remained untouched.

## Sign-off closure proof

- Baseline: archived v2 SHA-256
  `47403b80dc7c626a989146db030089805619958bc9e20fc8cb5f50203fd22b31`.
- B-1: 422/413 use a lilo-namespaced machine origin; capture records and
  CAPTURE state mark local generation; X1 proves zero retry; persisted evidence
  cannot attribute the local fault to the provider.
- B-2 option (b): request artifacts, transform manifests, and synchronized
  response prefixes have strict durability; at most 1 MiB of an unsynchronized
  response suffix may be lost and recovers as Interrupted.
- F-2: the APFS directory-entry limitation is explicit; Gate 2 and X6 prove
  the pre-created, synchronized exchange-directory layout.
- F-3: stale root `CLAUDE.md` Transport verbs are a section 5 rewrite target
  and a Gate 0 exit condition.
- Final completed delta against archived v2: 22 insertions, 13 deletions,
  552 lines. No other synthesis correction was introduced.
- Verification: v2-only `git diff --no-index --check`, `--numstat`, line-count,
  em-dash, whitespace, blocker-anchor, source-pin, provider-schema-negative,
  and zero-`tm` checks passed.

---
title: Warroom SKILL — Orchestrator-Discipline Sharpening (proposal)
type: proposal
status: awaiting-signoff
target: plugins/helioy-bus/skills/warroom/SKILL.md
author: helioy-plugins:helioy-tools:codebase-analyst
created: 2026-06-23
updated: 2026-06-23
---

# Warroom SKILL: orchestrator-context-is-the-budget sharpening

Proposed edits only. The live `SKILL.md` is **not** touched. Every BEFORE block is
an exact, un-ellipsized substring of the current working copy (re-confirmed verbatim;
file unchanged), so each is a clean find/replace.

## Principle being encoded

Once `/warroom` is invoked the agent is a **pure orchestrator/director**. Its own
context is the warroom's scarce, non-refillable resource, spent **only** on
direction and judgment. Deferral extends past implementation to **direct
questions** and **quality control**: spin up an agent to answer a question or run
QC, never research/read/verify by ingesting the artifact yourself.

The orchestrator still **owns every verdict and gate** — only the *means* of
verification changes: (a) cheap bounded signals it can afford (a `gh pr checks`
line, a `git log -1` sha, a CI exit code) and (b) a **commissioned** independent
verification/QC agent returning a bounded verdict. "Don't trust the bus" stands;
its replacement is a commissioned independent check, **not** self-ingestion of a
full diff, log, file, or report.

Constraints honored: frontmatter (`name: warroom`) preserved; cross-refs use
section-name symbols, never line numbers; **no new modes** (the one new top-level
section is a *principle* section, like "The Spine" / "Why We Spend Tokens On
Review", not a mode). Leanness: see the net-delta note at the end.

---

## Edit 1 — `## Role`

**BEFORE**

```
## Role

A warroom is a set of specialist agents running in tmux panes, connected through helioy-bus, working toward one shared goal. You are the orchestrator: choose the mode, phase the work, brief agents, monitor progress, synthesize results, apply authoritative changes, and verify gates.

Agents research, scout, review, draft, and implement. You own scope, reuse, evidence, context hygiene, and final judgment.
```

**AFTER**

```
## Role

A warroom is a set of specialist agents running in tmux panes, connected through helioy-bus, working toward one shared goal. Once /warroom is invoked you are a pure orchestrator: choose the mode, phase the work, brief agents, monitor progress, synthesize results, apply authoritative changes, and verify gates.

Agents research, scout, review, draft, and implement. You own scope, reuse, evidence, context hygiene, and final judgment. Your context is the warroom's scarce resource; spend it on direction, not doing (Orchestrator Context Is The Budget).
```

---

## Edit 2 — NEW section `## Orchestrator Context Is The Budget`

Insert immediately **after `## Role`**, before `## The Spine: Scout → Build →
Review`. Single home for the principle; other edits point here so they stay
one-liners (the SKILL's "single home" pattern, as with Priming & Compaction).

**AFTER (new text)**

```
## Orchestrator Context Is The Budget

Your context is the one resource a warroom cannot refill; spend it on direction and judgment, never on doing.

- **Defer your own questions.** To learn a fact about the code, spec, or a failure, commission an agent to find it and reply one line — do not read the source, diff, or log yourself.
- **Commission QC; never self-ingest it.** You own every verdict and gate, but verify through cheap bounded signals you can afford (a `gh pr checks` line, a `git log -1` sha, a CI exit code) plus an independent agent's bounded verdict — never by pulling a full diff, log, file, or report into your own context.
```

*(Trimmed from the prior draft: dropped a third bullet and a closing sentence that
restated the two bullets — leanness.)*

---

## Edit 3 — `## Non-Negotiables`: reconcile the verify bullet

The means of verification changes; bus-distrust stays. (The prior draft's separate
standalone hard-rule bullet is **dropped** as redundant with this bullet, the new
section, and the Anti-Patterns rows — leanness.)

**BEFORE**

```
- Bus pings wake you; they are not truth. Confirm `done`, `green`, `merged`, and `clean` from disk, `gh`, git, Linear, logs, or test output. Re-read live state before each verdict; memory-only consensus is false consensus.
```

**AFTER**

```
- Bus pings wake you; they are not truth. Confirm `done`, `green`, `merged`, and `clean` before each verdict — through cheap signals you can afford (a `gh pr checks` line, a `git log -1` sha, a CI exit code) or a commissioned verification agent, never by reading the full diff, log, or artifact yourself (Orchestrator Context Is The Budget). Memory-only consensus is false consensus.
```

---

## Edit 4 — `## Modes` shared-loop preamble (governs all six modes)

**BEFORE**

```
Each mode instantiates one shared loop: **brief independently → agents re-read live state and reply one line to the orchestrator → orchestrator verifies from disk / `gh` / git → one focused correction round → re-verify deltas only → close (recycle or compact)**. Each mode below states only its deltas from this loop.
```

**AFTER**

```
Each mode instantiates one shared loop: **brief independently → agents re-read live state and reply one line to the orchestrator → orchestrator verifies via cheap signals or a commissioned check → one focused correction round → re-verify deltas only → close (recycle or compact)**. Each mode below states only its deltas from this loop.
```

---

## Edit 5 — `## Message Protocol` (NEW — was missed; QC issue 1a)

The orchestrator **names** the output file; a commissioned agent reads it (or a
cheap signal summarizes). Replace the first sentence of the "Large artifacts…"
line; the rest of that line ("The bus is the signal, not the artifact. For
no-reply notices…") is unchanged.

**BEFORE**

```
Large artifacts go to files you name and read.
```

**AFTER**

```
Large artifacts go to files you name; a commissioned agent reads them or a cheap signal summarizes — you never ingest the artifact yourself.
```

---

## Edit 6 — `### Mode 3: Slice Build Loop` (two verify lines)

### 6a — Review-weight paragraph: drop "the orchestrator's own diff read"

**BEFORE**

```
Review weight scales with blast radius. A small mechanical PR (a few files, clear gate, no contract change) gets the orchestrator's own diff read plus the gate, not a queued adversarial pass — the reviewer pane existing is not a reason to use it. Reserve the full loop for slices that change contracts, persistence, identity, deletion, or cross-surface seams.
```

**AFTER**

```
Review weight scales with blast radius. A small mechanical PR (a few files, clear gate, no contract change) clears on cheap signals — the gate plus a `gh pr checks` line — not a queued adversarial pass; the reviewer pane existing is not a reason to use it. Reserve the full loop, and any diff read, for slices that change contracts, persistence, identity, deletion, or cross-surface seams.
```

### 6b — Step 3: confirm via cheap signals, not a self diff read

**BEFORE**

```
3. On `done:`, verify the PR yourself with `gh pr view N`; never trust the bus line alone.
```

**AFTER**

```
3. On `done:`, confirm the PR through cheap signals (`gh pr checks N`, a `git log -1` sha), not a self diff read; the adversarial read is the reviewer's job (step 4). Never trust the bus line alone.
```

---

## Edit 7 — `### Mode 4: Code Review` — NO CHANGE (rationale recorded)

Already delegation-shaped: reviewers read diffs; the orchestrator only dispatches
and **synthesizes bounded verdicts** (step 7). Step 1's "Run the baseline gate
first (`cargo test`… `just ci`)" is an **allowed cheap signal** (a gate's pass/fail
exit code), not artifact ingestion. No edit needed.

---

## Edit 8 — `### Mode 5: Peer Consensus` (minor)

Peer Consensus already models the principle — **agents** re-read live state and
sign off; the orchestrator judges bounded sign-off strings and applies writes (its
Role-granted job). One clarifying touch:

**BEFORE**

```
Brief both agents independently — do not ask them to debate; the orchestrator synthesizes.
```

**AFTER**

```
Brief both agents independently — do not ask them to debate; the orchestrator synthesizes their bounded verdicts.
```

---

## Edit 9 — `## Why We Spend Tokens On Review` (NEW — was missed; QC issue 1b)

Reconcile to match the Slice Build Loop edit: even the lightest verification is a
cheap bounded signal or a commissioned check, not the orchestrator's own diff read.

**BEFORE**

```
- **Weight scales with stakes.** Review weight scales with blast radius (Slice Build Loop): a one-line mechanical change earns the orchestrator's own diff read, while a contract change earns the full adversarial loop.
```

**AFTER**

```
- **Weight scales with stakes.** Review weight scales with blast radius (Slice Build Loop): a one-line mechanical change clears on a cheap signal or a commissioned check, while a contract change earns the full adversarial loop.
```

---

## Edit 10 — `## Shared Practices`: the "bus is not the artifact" line

Tightened: the duplicated "bus is not the artifact" phrasing (also in Message
Protocol) is dropped; this bullet now carries only the act-on-replies rule and the
write-a-review-file rule.

**BEFORE**

```
- The bus is not the artifact: read artifact files after completion. Write a review file ONLY when you will read it to drive fixes; a clean or short verdict rides the bus.
```

**AFTER**

```
- Act on bounded replies and cheap signals, not artifacts you ingest yourself; commission a reader when a fix needs the detail. Write a review file ONLY when an agent will read it to drive fixes; a clean or short verdict rides the bus.
```

---

## Edit 11 — `## Priming & Compaction`: resolve the "budget" terminology collision

"Compaction is hygiene, **not your budget**" sits beside a section titled
"…Is **The Budget**". They are orthogonal; one clarifying clause:

**BEFORE**

```
**Compaction is hygiene, not your budget.** Compact between phases and slices regardless of how much orchestrator context you have left.
```

**AFTER**

```
**Compaction is hygiene, not your budget.** Protecting your own context (Orchestrator Context Is The Budget) is the separate, converse discipline — compact between phases and slices regardless of how much orchestrator context you have left.
```

*(Remainder of the paragraph unchanged.)*

---

## Edit 12 — `## Anti-Patterns`: reconcile one row, add three

### 12a — Reconcile the bus-trust row

**BEFORE**

```
| Trust a `done`, `green`, `clean`, or `merged` bus line | Verify from disk, `gh`, git, Linear, logs, or tests. |
```

**AFTER**

```
| Trust a `done`, `green`, `clean`, or `merged` bus line | Verify via cheap signals (`gh pr checks`, a `git log -1` sha, a CI exit code) or a commissioned check — never by reading the diff, log, or artifact yourself. |
```

### 12b — Add three rows (the director's exact examples), inserted after 12a

```
| Answer a direct question by reading the source, spec, or log yourself | Spin up an agent to find it and reply one line. |
| Run QC or verification by ingesting the diff, log, or report | Commission a verification agent; you judge its bounded verdict. |
| Spend orchestrator context on artifact reads | Act on cheap signals plus delegated reads. |
```

---

## Contradictions found (every other place that clashes, with proposed fix)

Three further "verify it yourself" phrasings clash with the principle; each is a
small surgical reconciliation (BEFORE blocks verbatim from the live SKILL).

### C1 — `## Phase & Churn Control`, phase-contract "Gate" bullet

**BEFORE**

```
- **Gate**: how you will verify the phase yourself.
```

**AFTER**

```
- **Gate**: how you will verify the phase — cheap signals or a commissioned check, not a self artifact read.
```

### C2 — `### Mode 2: Spec Writing`, step 5 (re-quoted VERBATIM; QC issue 2 — no ellipsis)

**BEFORE**

```
5. One focused fix round per engineer; architect verifies deltas only. Cap spec review at one architect pass plus one correction round, then orchestrator spot-checks — never a third full round over citation mechanics.
```

**AFTER**

```
5. One focused fix round per engineer; architect verifies deltas only. Cap spec review at one architect pass plus one correction round, then the orchestrator confirms via a bounded spot-check (a cheap signal or a commissioned read) — never a third full round over citation mechanics.
```

### C3 — `### Mode 6: Brainstorm`, step 3

**BEFORE**

```
3. Read the files, compare independent convergence, identify contradictions, present the synthesis.
```

**AFTER**

```
3. Read the bounded artifacts (or commission a synthesis pass if they are large), compare independent convergence, identify contradictions, present the synthesis.
```

### Consistent, clarified — NO change (verified, not clashes)

- `## First Decision` "Your own verification gate is sufficient evidence." — a gate
  run is a cheap signal; this governs whether to spawn a warroom at all.
- Scout report (Mode 1), spec files (Mode 2), brainstorm docs (Mode 6) the
  orchestrator reads to **decide**: bounded *decision* artifacts the orchestrator
  must judge (Role), i.e. direction, not the prohibited self-QC of a diff/log.
  (Mode 6 is softened in C3 only for the large-file case.)
- `tmux capture-pane … | tail -5` progress checks and gate runs (`just ci`,
  `cargo test`) are the cheap bounded signals the principle explicitly endorses.
- Mode 5 "apply the agreed change" is the orchestrator applying authoritative
  writes (Role), not verification by ingestion.

---

## Net-delta note (QC issue 3)

Applied to `SKILL.md`, the edits now total **≈ +10 lines / ≈ +265 words**, down
from **+14 / +492**. Word growth cut ~46%. Cuts that bought the reduction:

- Dropped the standalone Non-Negotiables hard-rule bullet (redundant with Edit 2 +
  the reconciled verify bullet + Anti-Pattern rows).
- Dropped the new section's third bullet and closing sentence (restated the rest).
- Removed the duplicated "bus is not the artifact" phrasing from Shared Practices
  (consolidated into Message Protocol).
- Trimmed cross-ref pointers to navigationally-useful spots only.

The residual **+10 lines is structural and near-floor**: 7 lines are the new
single-home section the director requested, and 3 are the director's three
mandated Anti-Pattern rows. Every other edit is an **in-place rewrite that adds
zero file lines** (SKILL.md keeps one sentence/bullet per physical line). Going
lower means either removing the single-home section or dropping mandated rows.

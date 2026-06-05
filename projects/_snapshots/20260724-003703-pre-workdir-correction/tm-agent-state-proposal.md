# Initial Proposal — Harness-agnostic Agent State Derivation

Synthesis of the tm-agent-state ideation warroom (claude/Fable + codex + grok, 2026-07-10).
Backing docs: `tm-agent-state-{claude,codex,grok}.md`. This proposal goes to the execution warroom for critique.

## Problem

The Control Center must show each agent's TRUE lifecycle state — above all **`needs_you`** ("this agent is blocked on me right now") — derived from a source of truth, for Claude Code + Codex + future harnesses, and kept correct as harnesses version constantly. Today's mapping is inverted: an idle/finished run screams "needs you", and a run actually blocked on a permission prompt reads as "Thinking" (Claude writes the `tool_use` to the transcript *before* the gate renders, so the current machine sees "running-tools" while it's blocked).

## Canonical state model (the ubiquitous language)

Harness-agnostic vocabulary every adapter maps INTO, in four tiers:

**Active** (agent is working; wire-distinguishable in both harnesses):
- `reasoning` — extended thinking / reasoning tokens (Claude `thinking` blocks; Codex reasoning events) → the legitimate "Thinking"
- `generating` — producing response text (`text` blocks / agent-message) → "Responding"
- `running_tool` — a `tool_use`/exec in flight → "Running &lt;tool&gt;"

**Needs you** (blocked on the user — the star):
- `gated{ permission | plan_review | auth }` — awaiting approval; carries a **structured, ideally remotely-answerable payload**
- `asked{ question }` — an explicit AskUserQuestion

**Resting:** `idle` — turn complete, waiting (NOT needs_you).
**Terminal:** `done` / `error`.

**`needs_you` = `gated` ∪ `asked`.** The active tier is genuine (free from the wire) but is the *decoration* — `needs_you` accuracy is the one that must be bulletproof. Note: the original "Thinking-while-blocked" bug was a mislabel — a gate reads as `running_tool` on the wire (tool_use written before the gate), so splitting the active tier + detecting the gate via PTY is what makes "Thinking" mean thinking.

## Scope (decided, Stuart 2026-07-10): CANVAS RUNS ONLY

We only care about in-canvas panes, not detached CLI runs. Consequence: **every run has all planes, including the `ScrollbackRing`** — the PTY plane is always available, so "detached coverage" is a non-problem and does not force hooks.

## Four signal planes (all available for canvas runs)

| Plane | What it carries |
|---|---|
| **Wire** (API bytes) | turn boundaries, `tool_use`, AskUserQuestion (`asked`), stop_reason, usage/tokens, harness version |
| **Transcript** (JSONL) | journaled tool_use/result/turn events — NOT local gates |
| **PTY / ScrollbackRing** | the rendered TUI — the ONLY place CC permission/plan gates appear; always present for canvas runs |
| **Hooks** (optional) | structured local-gate signals — a cleaner upgrade over PTY-scraping, not required for coverage |

Fable confirmed the `ScrollbackRing` (2MiB/run in `TerminalFanout`/`RunManager`) is in-process with Activity in the one gateway, so a quiescence-triggered tail snapshot → headless-xterm render → versioned gate-signature match is buildable now.

## The harness asymmetry (the load-bearing insight)

- **Codex — open + structured.** Emits `ExecApprovalRequest` / `ApplyPatchApprovalRequest`; app-server status `waitingOnApproval` / `waitingOnUserInput`. `needs_you` is a first-class signal, no scraping. **Acquisition:** generate + pin JSON-Schema/TS from the installed `rust-v<version>`; map events → canonical states. Low effort, clean, high fidelity.
- **Claude Code — closed (native Bun Mach-O, no `.d.ts`).** Permission/plan gates are absent from wire and only partial in the transcript. `needs_you` gate signal must come from **hooks** (structured, universal) and/or **PTY** (canvas-only, brittle TUI parsing). Wire still yields `asked` + tokens + version; transcript yields the tool journal. **Acquisition:** hooks contract + versioned gate-signature packs + empirical JSONL/binary-string histograms per version.

## Maintenance process (grok's SCHEMA-LOCK)

A re-runnable per-`(harness, version)` pipeline: **acquire** schema (codex: from source tag; CC: hook contract + gate-signature packs + JSONL/string histograms) → **diff** vs last known version → **FAIL LOUD** on any unmapped event (never silently misclassify — that failure is exactly today's bug) → **golden fixtures** (real transcripts + PTY snapshots per version). Onboarding a new harness = run the same pipeline against its source-or-corpus.

## Architecture (extends TM's existing adapter pattern)

- **Canonical state model** = core domain vocabulary.
- **Per-harness adapter** (anti-corruption layer) consumes that harness's available planes and emits canonical state; extends the existing `index/adapters/{claude,codex}`.
- **Harness-schema registry**, versioned per release, maintained by the SCHEMA-LOCK pipeline.
- The **projection** surfaces canonical state on the activity wire → Control Center strip (replacing the crude inference).

## Decisions

1. **Scope — RESOLVED: canvas runs only** (Stuart). Detached CLI runs are out. Every run has all four planes, so the PTY plane is always available.
2. **Hooks vs PTY for Claude Code gates (open, now a fidelity choice not a coverage one).** Since PTY is always present for canvas runs, PTY gate-signature packs are a viable *primary* path — buildable today via the ScrollbackRing. Hooks remain an optional *quality* upgrade (structured payload, no TUI parsing) if TM can register them into the CC launch. Recommend: start with PTY, evaluate hooks as a robustness follow-up.
3. **Sequencing.** Recommend **ship Codex first** — its structured events make it the clean reference implementation of the canonical model + adapter + pipeline + projection→strip. Claude Code (PTY gate-signatures, the harder acquisition) follows on the proven skeleton.

## Recommended first slice

Codex structured-state adapter → canonical model → SCHEMA-LOCK pipeline (codex generator) → projection surfaces real `needs_you`/`gated`/`working`/`idle` → Control Center strip reflects it. Proves the whole spine end-to-end on the easy harness before taking on Claude Code's hooks-vs-PTY problem.

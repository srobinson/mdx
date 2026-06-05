# Harness Support Standard

Status: chartered 2026-07-03 (Stuart + Fable brainstorm). Companion to
`tm-activity-spec.md`; outlives it. Source of truth moves into
`docs/ARCHITECTURE.md` when slice 0 of Activity lands; this document is the
full statement, the ARCHITECTURE.md entry may summarize and link.

## Purpose

Transport Matters must be the absolute expert on every schema a supported
harness exposes. Expertise is not tribal knowledge; it is a checked-in,
versioned, executable asset. Currently supported: Claude Code, Codex.

## The three schema families

Every harness exposes three schemas. A harness is supported when all three
are handled through the bundle convention below.

| Family | Direction | Example (Claude / Codex) | IR |
|---|---|---|---|
| Wire | observed | Anthropic API bytes / ChatGPT websocket | wire IR (`request.ir.json`, `response.ir.json`) |
| Transcript | observed | CLI session JSONL / rollout files | transcript IR (normalized records, `TranscriptAdapter` vocabulary) |
| Settings | bidirectional | `settings.json`, CLAUDE.md, plugins / `config.toml`, AGENTS.md | settings IR (new) |

Wire and transcript IRs are deliberately separate (never collapse; wire is
byte truth for Inspector, transcript is semantic truth for Activity).
Settings is different in kind: TM both reads it (capture what configuration a
run actually had) and writes it (seeding ephemeral agent homes). The settings
adapter is therefore two-way: parse to IR, and render IR to a concrete home.

Settings capture: a snapshot of effective settings belongs in the run
directory beside the launch facts, so every run carries provenance of the
configuration it ran under. This is also the seam where settings become
experiment variables for the future eval story, and the policy surface for
the enterprise story.

## The harness bundle convention

Convention over configuration: one bundle per harness with a fixed shape.
Adding a harness means filling in the convention and passing the conformance
kit; nothing downstream changes because downstream consumes only IR.

```
harness bundle (per harness):
  wire adapter          # bytes -> wire IR
  transcript adapter    # records -> transcript IR
  settings adapter      # files <-> settings IR (parse and render)
  mapping tables        # declared per supported version range
  capability flags      # what this harness actually provides
  fixtures/             # real captures, per harness version
```

Existing seeds to reconcile before inventing anything:
`api/src/transport_matters/harnesses/` (`HarnessDescriptor`,
`HarnessCapabilities`) and `api/src/transport_matters/adapters/` exist on
the Python capture plane; transcript adapters sit misplaced under
`index/adapters/`. Under the two-plane rule (2026-07-03: Python = capture
plane, TypeScript = product plane, disk is the contract), product-plane
consumers get TS adapters and the v1 fixture corpus lives with the
`@tm/activity` package; consolidating one bundle home across planes is the
chartered follow-on.

### Conformance kit

A generic test suite, parameterized by fixtures, that every bundle must pass:
parse every fixture with zero unknown records, round-trip settings, produce
declared capabilities, map to the current IR versions. The kit is what makes
"adding a harness is trivial" true, and it leaves the door open to
out-of-tree community bundles later without designing for that now.

### Capability flags

Harnesses do not record uniformly. Bundles declare what they provide
(usage payloads, question-ask marker, settings render, ...) so consumers
degrade honestly. An "unknown" status beats a wrong "needs-you".

## The fixture corpus

Real transcripts, wire captures, and settings files, checked in per harness
per version, with a documented capture procedure. The corpus is the
executable form of expertise: adapters are tested against it, drift is
diffed against it, and a new harness version is supported by extending it.

## Drift defense in depth

1. **Runtime sensors (strongest).** TM parses every record of every session
   in production. Unknown record types and unexpected fields are counted
   live and surfaced in `transport-matters doctor` and the UI. Every user
   session is a drift sensor; users run new CLI versions before any CI does.
2. **CI canary.** A scheduled job installs the latest CLI, runs a scripted
   session, captures all three schema families, and diffs against the
   corpus. Early warning before users hit it.
3. **Corpus diffing.** When drift is confirmed, the new version's fixtures
   enter the corpus, mappings are extended for the new version range, and
   downstream is untouched because it keys off IR.

## Version awareness

TM launches the CLI, so it captures the harness version into the launch
facts. Mapping tables declare the version ranges they understand. An unknown
version degrades to explicit best-effort, never silent misparsing.

## IR evolution discipline

Absorbing upstream churn must not break downstream. Each IR is
schema-versioned with additive-first rules: adding a type or field is minor;
changing semantics is major and carries migration notes. Same discipline as
the Activity fact contract.

## Relationship to current work

- Activity v1 slice 1 seeds the convention: transcript fixtures per runtime,
  mapping tables with version ranges, unknown-record counters.
- The CI canary is its own small follow-on track.
- Settings IR and run-time settings snapshot are their own track (very
  related to schema capture, unrelated to Activity); the ephemeral-home
  seeding code is the natural starting seam.
- Scout round 2 additionally maps `harnesses/` and `adapters/` against the
  bundle shape.

## Open questions (deliberately unresolved)

- Whether wire IR and transcript IR share low-level value types (usage
  payload shape) or stay fully disjoint.
- Where bundles live once the convention is real: inside the repo per
  context standard, or a dedicated top-level home.
- Settings IR scope: full fidelity vs the policy-relevant subset first.

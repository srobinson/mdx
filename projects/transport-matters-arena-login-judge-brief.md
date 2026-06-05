# Judge brief: in-app harness login driver arena

You are one of two independent judges (different model families). Do not coordinate. The orchestrator synthesizes.

## Inputs

- Task and constraints: `~/.mdx/projects/transport-matters-arena-login-brief.md`
- Grounding (Reuse Map, Quality Map, Plan): `~/.mdx/projects/transport-matters-scout-login-driver.md`
- Red flags rubric: `~/Dev/LLM/DEV/helioy/helioy-plugins/plugins/helioy-pstack/skills/architect/references/design-red-flags.md`
- Rationale template: `~/Dev/LLM/DEV/helioy/helioy-plugins/plugins/helioy-pstack/skills/architect/references/rationale-template.md`
- Candidates (four, one per model family):
  - A `~/.mdx/projects/transport-matters-arena-login-claude.md`
  - B `~/.mdx/projects/transport-matters-arena-login-codex.md`
  - C `~/.mdx/projects/transport-matters-arena-login-grok.md`
  - D `~/.mdx/projects/transport-matters-arena-login-opus.md`
- Baseline ref for any code claim: `main` in the transport-matters repo (verify a candidate's citation with `git show main:<path>` or grep; a candidate that cites a symbol that does not exist is a defect).

## Rubric

Score each candidate on:

1. Honours the fixed constraints in the arena brief (sibling on the gateway via ptyPort, not RunManager/POST /v1/runs/cli; exit is completion; API-first for the director; home read-only; no 700-line file growth).
2. Binds to the Reuse Map (PlainTerminalSessions / plainTerminalConnection, run_proxy bridge, useTerminalSession / TerminalPane, launchReadinessKey, credential_source profiles, HOME_DIR_ENV_BY_HARNESS). New helper/type/route for a capability already named = defect unless recorded as a deviation with a reason.
3. Red flags: shallow module, information leakage, temporal decomposition, pass-through method.
4. Interface depth: how much complexity hides behind how small a public surface. Caller's usage written first and the types derived from it.
5. Idempotency and shared state: started twice, pane closed mid-flow, gateway restart, two browsers.
6. Failure taxonomy and readiness re-read: how the launcher learns the outcome, without matching "Login successful." text.
7. Citation accuracy against `main`.

## Output

Write `~/.mdx/projects/transport-matters-arena-login-verdict-<your runtime>.md`, under 120 lines:

- A table: candidate x rubric axis, one short cell each.
- Red flags found per candidate (file + section).
- Citation defects (symbol claimed, what exists).
- **Base**: which candidate should be the base and why (one paragraph).
- **Grafts**: numbered list, each "take <specific element> from <candidate> because <reason>".
- **Reject**: numbered list of elements to reject with reason.
- **Open questions** the human must weigh in on.

Find at least one substantive issue in the base you pick, or positively justify that none exists.

No writes to the repo. Reply to the orchestrator only, in one sentence: `done: <path> base=<A|B|C|D> grafts=<n>` or `blocked: <cause>`. Do not message other agents.

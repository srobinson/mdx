# Arena brief: in-app harness login driver (NOW.md 1.3)

You are one candidate runner in an architect arena. Read these in full before writing anything:

1. The architect skill: `~/Dev/LLM/DEV/helioy/helioy-plugins/plugins/helioy-pstack/skills/architect/SKILL.md`
2. The runner prompt (your discipline): `~/Dev/LLM/DEV/helioy/helioy-plugins/plugins/helioy-pstack/skills/architect/references/runner-prompt.md`
3. The rationale template (your output shape): `~/Dev/LLM/DEV/helioy/helioy-plugins/plugins/helioy-pstack/skills/architect/references/rationale-template.md`
4. The red flags (screen your own design): `~/Dev/LLM/DEV/helioy/helioy-plugins/plugins/helioy-pstack/skills/architect/references/design-red-flags.md`
5. The Phase A grounding: `~/.mdx/projects/transport-matters-scout-login-driver.md` (Reuse Map, Quality Map, Plan). A design that adds a helper, type, runner, or command for a capability the Reuse Map already names is a defect unless you record it as a deliberate deviation with a reason.
6. The product intent: `NOW.md` sections "Phase 1 — first run", "1.1", "1.3" in the transport-matters repo. Also `docs/NORTHSTAR.md` (API-first, UI is one client of two; the director agent must be able to do it programmatically).

## Task

Design the login driver: TM runs the harness's own login flow, in the app, against the right home, so a `credential_unavailable` launch-readiness check carries an action that fixes it with no terminal.

Fixed constraints (from NOW.md, not up for redesign):

- Reuse each harness's own login command. Claude: `CLAUDE_CONFIG_DIR=~/.claude-auth claude auth login` on macOS, native home elsewhere. Codex: `codex login` (browser plus callback on 127.0.0.1:1455). Grok: its own command. Command and home already travel on `credential_source.login_command`.
- Sibling composition on the gateway: spawn through `ptyPort` with argv and env, own id, `PtySession.onExit` as completion, then re-read the credential predicate / launch readiness. Never through `POST /v1/runs`, `RunManager`, or `cli/`. Never match on `Login successful.` text.
- UI needs: the fallback URL when the browser does not open; a stdin path for paste-code prompts; completion from process exit.
- API-first: the director agent must be able to start a login and learn its outcome through the control plane, not only through the palette.
- TM's harness home is read-only to TM; TM never writes trust state on the user's behalf.
- `transport-matters codex -- login` stays CLI-surface remediation, never the desktop route.
- No file over 700 lines; no function over ~150.

Open for you to decide (and to justify): where the driver's state lives (gateway vs Python backend), the identity of a login session and its idempotency (what happens when login is started twice, or the pane closes mid-flow), how the frontend hosts the PTY (existing terminal component vs modal), how readiness is re-read and pushed to the launcher, how the fallback URL surfaces (PTY output is enough vs parsed), and the failure taxonomy.

## Output

Write ONE file: the path given in your bus brief. Shape per the rationale template: Problem, Usage (caller's view, written FIRST: the director's control-plane call, the palette's call, the gateway's spawn), Shape (types, signatures, module map with `not implemented` bodies; TypeScript for gateway/frontend, Python for backend), Tradeoffs accepted, Alternatives considered, Open questions and risks, Next implementation step. Leave "Synthesis decision" empty. Under 300 lines. Cite existing code as path + symbol, never line numbers.

Do not hedge toward a safe middle. Produce the design your model believes in; differences between runners are the signal.

No writes to the repo. Reply to the orchestrator only, in one sentence: `done: <output path> <line count>` or `blocked: <cause>`.

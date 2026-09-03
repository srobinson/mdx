# 459: Research: portable exec kernel as a standard builtin surface (just-bash / Vercel Sandbox)

URL: https://github.com/littleorgans/transport-matters/issues/459
State: open
Labels: 
Updated: 2026-08-25T11:57:15Z

Parent: #455. **Back pocket — not scheduled.** Recorded so the option is not re-derived. Gated on evals and on #457/#458 shipping first.

## The question

Can one standard builtin tool surface work across claude, codex and grok, replacing each harness's native tools, validated by evals?

Codex is the existence proof that a small surface works: 3 top-level tools versus claude's 30, and 4.8× fewer tool bytes (30,359 vs 145,491) for comparable work.

## What the codex runtime reported first-hand

- It is **not** three tools. `exec` carries a **26,383-char description** documenting a nested API (`apply_patch`, `exec_command`, `write_stdin`, `update_plan`, `view_image`, `web__run`, MCP resources, goals). Definitions moved from structured schema into prose; the saving is still real.
- `exec` is a fresh V8 isolate per call, no filesystem or network API, state only via explicit `store`/`load`.
- Costs: three quoting layers (JS → JSON → shell) driving retries, no typed intent separating inspection from destruction, token spend parsing human-oriented stdout, portability tied to shell/OS/PATH/binaries, broad output flooding and truncating past the decisive error.
- **A structured edit primitive is load-bearing** — its own prompt forbids `sed -i` and requires `apply_patch`.
- Transplant requires the **execution environment and result protocol**, not the schema: sandbox and approval policy, known cwd plus explicit `workdir`, shell/PATH/binary guarantees, process lifecycle (session id, polling, stdin, PTY, cancellation), output shaping (token limits, truncation markers, chunking), safety teaching *with enforcement below the model*, verification guidance.
- Suggested boundary: **a small kernel, not pure exec** — exec + structured patch + async process control + explicit user interaction + typed media/web where shell cannot preserve semantics.

## Candidate: just-bash

[`just-bash`](https://github.com/vercel-labs/just-bash) (Vercel Labs, beta) is a virtual bash environment with an in-memory filesystem, written in TypeScript for agents. It **dissolves the OS from the contract** instead of teaching it: commands are implemented in TS, so `sed`, `grep`, `jq`, `awk` behave identically everywhere and GNU vs BSD, missing binaries, PATH and locale stop mattering. Filesystem classes are the policy boundary (`InMemoryFs`, `OverlayFs` reads real disk / writes to memory, `ReadWriteFs`, `MountableFs`); network is off by default behind URL and method allow-lists; `defineCommand` would let us add a structured `apply_patch` in TS. Core shell runs in the browser, so Canvas could preview kernel behaviour client-side.

It answers five of six items on the codex checklist. It is also TypeScript, which matches the plane rule.

### Benchmark, 2026-08-25

OverlayFs over this repo's `api/` tree (~850 Python files), output identical to native in every case:

| operation | just-bash | native | ratio |
| --- | --- | --- | --- |
| read file slice (`sed -n`) | 6ms | 7ms | 0.8× |
| list files (`find` + `wc`) | 248ms | 199ms | 1.2× |
| **grep** (`grep -rn`) | 142ms | 87ms | 1.8× |
| count lines (`xargs wc`) | 49ms | 21ms | 2.3× |
| **rg** (`rg -n`) | 3,700ms | 40ms | **93×** |

Performance is a non-issue except `rg`, which is ~26× slower than `grep` doing the identical job *within just-bash itself* — an implementation quirk, not a limit of the approach. Since we would own the kernel's prose contract, the mitigation is to not document `rg`. Reproduction script: benchmark against `OverlayFs({root})`, comparing `bash.exec(cmd)` wall time to `execSync(cmd)`.

### Gaps

- **No process lifecycle**: exec-and-return only. No session id, no `write_stdin`, no PTY. Dev servers, test watchers and streaming work have no equivalent — the one codex requirement it does not meet.
- **No VM isolation** (their words). Hardened against prototype pollution, but a policy boundary rather than a hard one against a hostile agent. [Vercel Sandbox](https://vercel.com/docs/vercel-sandbox) is the companion for a full VM with arbitrary binary execution, and the natural answer where real binaries or hard isolation are required.
- Real edits need `ReadWriteFs`, spending much of the sandbox benefit. `OverlayFs` is the interesting middle for exploration and planning.
- Beta software.

## How it would compose

Consistent with the mechanism boundary in #455 — an overlay subtracts and rewrites but cannot add executable capability:

- **MCP adds**: TM's MCP server exposes one `bash` tool backed by the kernel; the harness routes the call to us and we execute.
- **Overlay subtracts and rewrites**: strip the harness's builtin tools, rewrite the system prompt to teach the kernel.
- **agent-runtimes declares**: which capabilities, and which filesystem mode — a per-runtime trust level as configuration.

## Open work before this is more than a note

- End-to-end token comparison: kernel versus native tools on the same real task, counting **retries and response tokens**, not tool-definition bytes. Needs #457 (to strip tools) or a standalone agent loop. Request-byte savings alone would be misleading; the codex runtime was explicit about this.
- Eval suite along its suggested axes: quoting adversaries, hostile paths, wrong cwd, missing binary, denied network, truncation hiding the decisive error, long-running PTY work, dirty worktree preservation, exact edit plus mutation check, notebook integrity, secret redaction.
- Whether a provider accepts a `tool_use` for an undeclared tool (see #455) — decides whether schema deferral is transplantable.

## Comment by srobinson at 2026-08-25T11:57:15Z (updated 2026-08-25T11:57:15Z)

https://github.com/littleorgans/transport-matters/issues/459#issuecomment-5410025524

See #460: the `just-agent` A/B experiment (all builtins off, our system prompt, one just-bash tool). Unblocked on claude today via native flags — measured floor 5,717 bytes vs 114,619 default, zero provider spend. Only missing piece is the just-bash MCP server.

## Sub issues
[]

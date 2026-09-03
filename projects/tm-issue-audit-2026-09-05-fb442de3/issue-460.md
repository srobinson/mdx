# 460: Experiment: just-agent — one bash tool, our system prompt, A/B against an untouched agent

URL: https://github.com/littleorgans/transport-matters/issues/460
State: open
Labels: 
Updated: 2026-08-25T12:56:24Z

Parent: #455. Related: #459 (kernel research), #457 (tool control), #456 (viewer).

## The experiment

Build one agent-runtime, `just-agent`, with:

- all builtin tools disabled
- the harness system prompt replaced with our own
- exactly one tool: `bash`, backed by [just-bash](https://github.com/vercel-labs/just-bash) over an MCP server

Give the same task to `just-agent` and to an untouched agent. Measure.

This tests the entire Canvas Overlay thesis end to end: can a small, portable, self-owned tool surface do the work that a harness's native surface does, and at what token and behavioural cost.

## It is unblocked today on claude

Confirmed by capturing real request bytes against a local sink (zero provider spend, see #455 comment). No overlay machinery required:

```
claude -p "<task>" \
  --tools "" \
  --strict-mcp-config --mcp-config just-bash.json \
  --system-prompt "<our prompt>"
```

Measured floor: **5,717 bytes total, 0 tools, 203 bytes of system prompt** — against 114,619 bytes for the default configuration. A 20× smaller request before the task even starts.

The only missing component is the MCP server exposing `bash`.

## Build

**1. just-bash MCP server** (TypeScript, per the plane rule)

One `bash` tool over `Bash` + a filesystem mode chosen per runtime: `OverlayFs` (reads the real repo, writes to memory) for exploration arms, `ReadWriteFs` where the agent must actually ship changes. `defineCommand` supplies a structured `apply_patch`, which the codex runtime identified as load-bearing — general shell editing is too easy to misquote and too hard to audit.

Benchmarked at 0.8–2.3× native for `sed`, `find`, `grep`, `wc` over this repo, with identical output. **Do not document `rg` in the tool contract**: it is ~93× native and ~26× slower than `grep` doing the identical job inside just-bash.

**2. The system prompt**

Our own, teaching the one tool. It must carry what the codex runtime said an exec-shaped surface cannot work without: sandbox and approval policy, known cwd plus explicit working directory, shell and binary guarantees, output shaping and truncation behaviour, the structured edit primitive, and verification guidance. just-bash makes most of these *statable as facts* rather than per-machine guesses, because the command set is implemented in TypeScript and behaves identically everywhere.

**3. Harness coverage**

claude works via flags today. codex has no equivalent flags and grok has only `--disallowed-tools`, so extending the experiment to them depends on #457.

## Measurement design

Getting this wrong is the main risk.

- **Both arms identical** except tools and prompt: same model, same effort, same repo state, same task text, same non-interactive mode.
- **Multiple runs per arm.** Agents are stochastic; N=1 measures noise. Start at N=5.
- **Record per run**: total input tokens, output tokens, turns, wall clock, and task success judged against a fixed rubric written before the runs.
- **Classify every failure** using the taxonomy the codex runtime supplied from experience: quoting errors, hostile paths, wrong cwd, missing binary, denied network, truncation hiding the decisive error, long-running process needs, dirty worktree damage, incorrect edit, secret exposure.
- **Report request bytes and end-to-end tokens separately.** Request-byte savings are easy and misleading; the codex runtime was explicit that cost moves into the system prompt, command construction, stdout and retries.

## Task selection

Tasks must be ones a shell can plausibly do, chosen before any runs and not adjusted after seeing results. just-bash has **no process lifecycle** — no PTY, no `write_stdin`, no long-running sessions — so dev servers, watch modes and streaming test runners are out of scope until a companion mechanism exists.

Codex flagged shell-hostile domains that would unfairly penalise the kernel arm: browser and authenticated app state, images, PDFs, web results needing citations, notebooks. Excluding them is legitimate; silently excluding anything the kernel merely happens to lose is not.

## Fairness caveat, stated up front

The untouched arm has a tool surface tuned over years. `just-agent` will have a prompt written in a day. An early loss is evidence about our prompt, not about the thesis. The prompt should be iterated against the failure taxonomy before any result is treated as a verdict, and the iteration count should be reported alongside the outcome.

## Acceptance

- Both arms run the same task set unattended and produce a comparison table: request bytes, total tokens, turns, wall clock, success rate, failures by category.
- The result is reported honestly whichever way it falls, including the prompt iteration count.
- Findings feed #459 (whether a portable kernel is worth building on) and #457 (which granular controls are actually needed).

## Comment by srobinson at 2026-08-25T12:56:24Z (updated 2026-08-25T12:56:24Z)

https://github.com/littleorgans/transport-matters/issues/460#issuecomment-5410692592

## Correction to the fairness caveat: the baseline is already aggressively cut, but only on prompts

The issue body says the untouched arm has "a tool surface tuned over years". That is wrong, and the correction sharpens the experiment.

Anthropic removed ~80% of Claude Code's system prompt for frontier models (Opus 5 / Fable 5) with no measurable loss on coding evals, stating they had been over-constraining the model. The reduction is **frontier-only** — Sonnet 5 and Haiku 4.5 keep the full prompt. The headline 80% is the memory-disabled figure; with memory on it is closer to 70%.

Measured independently from our own certified captures (claude 2.1.241, first probe per cell), which reproduce exactly that split:

| alias | wire model | system prompt | tools | tool bytes |
| --- | --- | --- | --- | --- |
| sonnet | claude-sonnet-5 | 29,764 | 30 | 145,522 |
| haiku | claude-haiku-4-5 | 29,878 | 33 | 149,344 |
| fable | claude-fable-5 | **12,959** | 30 | 127,079 |
| opus | claude-opus-5 | **11,819** | 30 | 126,767 |

Opus 5's prompt is 60% smaller than Sonnet 5's in characters, consistent with the ~70% word-count figure once measurement bases are reconciled.

### The consequence that matters

**They cut the prompt. They did not cut the tools.** Opus gets 126,767 bytes of tool schemas against 11,819 bytes of system prompt — the tool surface is **10.7× the prompt** and only 13% smaller than Sonnet's. Against an Opus baseline, tools are **91% of the addressable mass**.

So the vendor has already proven the principle this experiment tests, on the region they chose to address, and left the larger region untouched. That is the strongest available argument for #457 leading delivery.

### What this changes for the experiment

- **Run the A/B on Opus 5 or Fable 5**, not Sonnet. Against Sonnet, prompt replacement would flatter us with a win the vendor already banks on frontier models.
- **The prompt-replacement win is smaller than the Sonnet numbers implied.** Our 203-byte prompt replaces 11,819 bytes on Opus, not 29,764.
- **The tool win is undiminished** and is where the result will be decided.
- The revised fairness caveat: the untouched arm is the product of deliberate, evaluated reduction, which makes it a *harder* prompt baseline than assumed — and an *unoptimized* tool baseline.

Anthropic's stated principle, which is also this experiment's hypothesis: the smarter the model, the fewer instructions it needs.

Sources: [Thariq (Anthropic) on X](https://x.com/trq212/status/2080710971228918066), [independent per-model prompt capture](https://x.com/PawelHuryn/status/2079700261581271487?lang=en), [AI Weekly summary](https://aiweekly.co/alerts/anthropic-deletes-80-of-claude-codes-system-prompt-for-claude-5)

## Sub issues
[]

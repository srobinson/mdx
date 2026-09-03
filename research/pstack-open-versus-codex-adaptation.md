---
title: Open Pstack versus Aqua-123 Codex adaptations
type: research
tags: [pstack, claude, codex, agent-runtimes, comparison]
summary: Source comparison, offline verification, and packaging probes of two community pstack ports.
status: active
created: 2026-09-11
updated: 2026-09-11
project: agent-runtimes
confidence: high
related: [pstack-claude-codex-support]
---

# Comparison

Open Pstack is the better starting point for a shared Claude Code and Codex
distribution. Aqua-123 has the clearer central contract for Codex authority,
capability fallbacks, and explicit activation. For Helioy, use Open's newer shared
workflow content as the candidate source, adapt the runtime contract using Aqua's
separation of concerns, and retain Transport Matters as the launch owner. This is
a proposed integration direction. Neither port was installed or imported.

## Examined revisions

| Project | Exact HEAD | Version | Upstream content |
| --- | --- | --- | --- |
| Open Pstack | `de67e6b40511814171e5e4c8ad7af3b79f07c9ee` | 1.4.1 | pstack 0.15.1 |
| Aqua-123 | `03ffe520e21c840c967edb039f631888d0c1862c` | 0.1.0 | pstack 0.14.3 |

Sources were cloned under `/tmp/pstack-support.IAbN83`. The comparison uses these
fixed revisions, not a claim about later updates.

## Design differences

| Concern | Open Pstack | Aqua-123 |
| --- | --- | --- |
| Host model | Shared skill prose, Claude tool vocabulary, a Codex mapping, and provider dispatch | Codex skill prose referring to one central runtime contract |
| Inventory | 54 skills | 45 skills |
| Review diversity | Executable routes across Claude, Codex, and Grok | Available Codex profiles and inherited models; no bundled cross-provider runner |
| Model evidence | Requested descriptor plus parsed provider report where available; Codex may use pinned argv evidence | Validates requested pairs against an externally supplied observable model list; otherwise inherits and labels unverified |
| Activation | Claude startup hook; explicit invocation in Codex | Every skill has explicit Codex policy; opt-in session state through bundled hooks |
| Permission guidance | Allows reversible external actions including team chat and ticket updates without asking | Parent request bounds external writes, destinations, credentials, and lifecycle creation |
| Parallel writers | Dedicated worktree or output directory, direct launcher per external lane | Exclusive paths, worktrees, or separate outputs; serialize if isolation is unavailable |
| Missing capability | Named provider dropout; no silent model substitution | Explicit sequential, generic-agent, partial-result, or fail-closed fallback |
| History | Includes Claude transcript assumptions and instructions to adapt paths | Uses available supported task history; falls back to git, issues, and handoff evidence |
| Automation | Excludes upstream Benny and make-bot-ui | Includes a dormant adapted Benny polling pack |

Open has ten skills absent from Aqua: `babysit`, `deslop`, `fix-ci`,
`fix-merge-conflicts`, `get-pr-comments`, `make-pr-easy-to-review`,
`principle-attack-the-premise`, `principle-test-behavior-not-implementation`,
`thermo-nuclear-code-quality-review`, and `what-did-i-get-done`.
Aqua alone has `setup-benny`. The count difference combines newer upstream content
and bundled companion skills; it is not a quality score.

## What is executable

### Open's provider runner

The [runner](https://github.com/ericlitman/open-pstack/blob/de67e6b40511814171e5e4c8ad7af3b79f07c9ee/plugins/pstack/skills/poteto-mode/scripts/runner/run.ts)
performs provider preflight, reserves outputs exclusively, launches CLI processes,
handles timeouts and cancellation, parses output, and emits structured receipts.
Its [command builder](https://github.com/ericlitman/open-pstack/blob/de67e6b40511814171e5e4c8ad7af3b79f07c9ee/plugins/pstack/skills/poteto-mode/scripts/runner/commands.ts)
has separate commands and access settings for Claude, Codex, and Grok.

This is substantial execution machinery. It is also a second launch owner for
Helioy. It directly executes provider CLIs and copies the parent environment,
removing a short list of cross-runtime identity markers. It neither creates a
Transport Matters overlay nor applies this repo's catalog validation. The copied
environment still contains runtime home variables and any other inherited values.

Its model evidence is correctly distinguished in code. A Codex result may be
complete with `modelVerified: false`, `reportedModel: null`, and
`modelEvidence: pinned-argv`. That establishes the requested launch argument,
not the concrete model that served the request. The documentation's occasional
four-provider wording should be read as four models across three providers.

### Aqua's executable boundaries

The [central contract](https://github.com/Aqua-123/pstack-for-codex/blob/03ffe520e21c840c967edb039f631888d0c1862c/skills/poteto-mode/references/codex-agent-runtime.md)
defines authority, delegation, isolation, history, and fallback rules in prose.
These still depend on the agent following them and the host enforcing permissions.

Concrete code backs two important parts:

- [Profile management](https://github.com/Aqua-123/pstack-for-codex/blob/03ffe520e21c840c967edb039f631888d0c1862c/skills/setup-pstack/scripts/manage-agents.mjs)
  scans for name collisions, checks ownership hashes, validates model and effort
  against supplied model records, and preserves changed files during uninstall.
- [Mode state](https://github.com/Aqua-123/pstack-for-codex/blob/03ffe520e21c840c967edb039f631888d0c1862c/hooks/scripts/poteto-mode-state.mjs)
  parses exact activation and disable phrases, persists session state with a
  project fingerprint, writes receipts atomically, and applies a 30 day TTL.

The model helper validates supplied records. It does not itself discover account
entitlement or the served model. Similarly, a locally generated hook receipt is
not independent proof that a particular Codex host trusted and fired the hook.

## Agent-runtimes fit

Neither package is ready for direct selection in this generator without adaptation.

1. The generator flattens and namespaces skills. References such as
   `../poteto-mode/references/...` must follow the generated names.
2. Open's shared prose still names Claude tools, built-in skills, registered
   agents, global model sheets, and plugin-level resources. The Codex mapping is
   useful but remains another lookup the model must perform.
3. Aqua's metadata explicitly restricts products to Codex. Its workflow contract
   cannot become a shared Claude and Grok body unchanged.
4. Aqua's optional setup depends on `templates/codex-agents/` outside `skills/`.
   Its mode persistence depends on plugin-level `hooks/` and `PLUGIN_DATA`.
   Benny setup expects `automations/benny/`. The generator currently distributes
   selected skill trees, not all these plugin components.
5. Open's global model sheets and provider launcher would overlap the repository's
   model catalog, recommended-model settings, and Transport Matters launch path.

In an isolated probe, copying only Aqua's `skills/` into a runtime-style home and
running profile setup failed with ENOENT for
`templates/codex-agents/pstack-poteto-agent.toml`. The helper failed before writing
the supplied project or user directories. This is a packaging dependency to handle,
not a failure of the complete plugin layout.

## Additional reproduced Aqua issue

On this macOS filesystem, invoking `manage-agents.mjs scan` through its `/tmp/`
path returns status 0 with no output. Invoking the same file through its resolved
`/private/tmp/` path produces the expected JSON scan report. The entrypoint guard
compares `path.resolve(process.argv[1])` with `fileURLToPath(import.meta.url)`;
the module URL resolves the symlink but the argv comparison does not.

The probe used empty temporary project and user directories. It performed no
installation. This demonstrates a CLI path portability gap despite passing unit
tests.

## Verification and limits

- Open: 158 Bun tests pass, strict typechecks pass, static plugin and workflow
  invariants pass.
- Aqua: 95 Node offline tests and 54 Bun tests pass; strict typechecks and the
  generated compatibility-map check pass.
- Tests ran using temporary Bun 1.4.0 through npm exec because installed Bun 1.0.0
  cannot consume Open's frozen lockfile. The installed Bun was not changed.
- Open's runner tests use fake provider executables to exercise process handling,
  receipts, parsing, cancellation, and timeouts. They do not establish live model
  task quality or today's provider CLI compatibility.
- Aqua's runtime-reference tests inspect text and fixture fields. Its installed
  smoke test directly calls hook handlers, which does not prove hook delivery by
  live Codex. That installed test was inspected, not executed in this comparison.
- Both inspected source checkouts remain clean. The agent-runtimes worktree retains
  exactly the pre-existing Matt Pocock import changes.

Logs: `/tmp/pstack-support.IAbN83/open-tests.log`, `aqua-offline-tests.log`, and
`aqua-bun-tests.log` in the same directory. No paid model runs, provider launches,
plugin installation, or production configuration changes were performed.

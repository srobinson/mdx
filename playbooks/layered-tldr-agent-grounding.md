---
title: Layered TLDR agent grounding
type: playbooks
tags: [claude, agents, tldr, grounding, symlinks, monorepo, helioy]
summary: Four-layer TLDR.md stack with CLAUDE.md and AGENTS.md as symlinks so agents land in any repo already grounded
status: active
project: helioy
related: []
confidence: high
---

# Layered TLDR agent grounding

Use this when adding a new repo under an existing monorepo umbrella, or when establishing the grounding stack on a fresh umbrella. The pattern gives an agent walking the filesystem a layered "what is this" answer at every level, without duplicating content and without leaking operator detail into the agent context.

The mechanism is Claude Code's recursive `CLAUDE.md` walk: every ancestor `CLAUDE.md` is concatenated into the agent's system prompt. By making `CLAUDE.md` (and `AGENTS.md` for Codex and similar) a symlink to `TLDR.md`, one canonical file does double duty: human readable repo identity and machine loaded agent grounding.

## The Stack

```
~/.claude/CLAUDE.md                          how to act (global)
/<umbrella>/TLDR.md                          what the umbrella is (1-2 lines)
/<umbrella>/<monorepo>/TLDR.md               substrate map (product + sibling table + dep direction)
/<umbrella>/<monorepo>/<repo>/TLDR.md        repo identity (why this repo exists + mental model)
```

At every layer below the global one, `CLAUDE.md` and `AGENTS.md` are parallel symlinks to the sibling `TLDR.md`. Parallel, not chained, so editing or removing one symlink can never break the other.

## Per Repo Doc Set

Each repo carries three primary docs plus two symlinks:

| File | Purpose | Audience |
| --- | --- | --- |
| `TLDR.md` | Grounding. Why this repo exists + mental model. | Agents and new teammates. |
| `README.md` | Product brochure. Product fit + install + quickstart + host support. | Operators and new users. |
| `PROJECT.md` | Depth. Architecture, contracts, repo boundaries. | Implementers and reviewers. |
| `CLAUDE.md` | Parallel symlink → `TLDR.md`. | Claude Code. |
| `AGENTS.md` | Parallel symlink → `TLDR.md`. | Codex and similar. |

`TLDR.md` and `README.md` both end with `See [PROJECT.md](./PROJECT.md) for more.` as the single signpost to depth.

## File Contracts

Three files, three audiences, three questions:

- **TLDR.md = agent orientation.** What is this repo, in one minute, so an agent can act.
- **README.md = product.** What is this thing, why reach for it, how to install.
- **PROJECT.md = tech.** Architecture, contracts, depth.

Keep the answers separate. Drift between them is the recurring failure mode.

### TLDR.md (grounding)

Each `TLDR.md` carries "why" content only. No install instructions. No common command lists. No operator examples. Those belong in `README.md`. A single diagnostic-pointer command framed as mental model is acceptable (e.g. `\`rtm doctor\` is the first command to run when something feels wrong`), because the TLDR is grounding for agents starting a new session, and a single signpost is part of the mental model.

| Layer | TLDR.md content | Token budget |
| --- | --- | --- |
| Umbrella | One paragraph: the product family, codename, scope | ~50 |
| Monorepo | Product statement, sibling repo table with links, dependency direction, mental model, cross-repo contracts | ~300 |
| Repo | Opening paragraph (the question this repo answers), Mental Model section, trailing pointer to `PROJECT.md` | ~150 |

The repo `TLDR.md` should be readable cold in under a minute. A new teammate landing in the repo should know what it does and how to think about it without reading any code.

### README.md (product)

Each repo `README.md` is the product brochure. It answers "what is this and should I reach for it?". The headline material is product fit: what the thing does, who reaches for it, why it exists. Everything below is enough to let a reader install and try the product.

Canonical shape:

- Title + product fit paragraphs (the centerpiece, treat as a poster campaign).
- Install: one or two commands. Optional host support matrix.
- Quickstart: the canonical first commands.
- Trailing line: `See [PROJECT.md](./PROJECT.md) for more.`

The mental split is README = product, PROJECT = tech. Anything technical belongs in PROJECT.md.

Does NOT belong in README:

- Development workflow / quality gate commands (`just check`, lint, test). When contributors arrive these live in `CONTRIBUTING.md`.
- Admin or operator reference tables. Auto-generated tables live next to the code they document, or in PROJECT.md if they describe stable contracts.
- Architecture, protocol contracts, isolation policy, release distribution depth, endpoint and path policy. All PROJECT.md.

**The 80% rule.** Product fit content (title + product story) should occupy roughly 80% of the file. If install + quickstart together are bigger than the product story, the README is broken.

If a section grows past a screen, the depth almost always belongs in `PROJECT.md`, not the README.

### PROJECT.md (depth)

Architecture, crate boundaries, contracts, isolation policy, events protocol, release conventions, engineering standards. PROJECT.md is the file an implementer reads when they need the full picture. No size limit beyond the global 700 line cap on any single file.

PROJECT.md has no trailing pointer. It is the depth file the others reference.

## What Belongs Where

| Content | Home |
| --- | --- |
| Why the repo exists | `TLDR.md` |
| Mental model, vocabulary | `TLDR.md` |
| Sibling repo map (monorepo TLDR) | `TLDR.md` |
| Install instructions, common commands, operator examples | `README.md` |
| Host or platform support matrix | `README.md` |
| Architecture depth, crate boundaries, contracts | `PROJECT.md` |
| Release model, cargo-dist, crates.io publishing surface | `PROJECT.md` |
| Protocol contracts (events, RPC, wire types) | `PROJECT.md` |
| Isolation / sandboxing / image contracts | `PROJECT.md` |
| Endpoint and path policy | `PROJECT.md` |
| Admin or MCP tool reference tables (often auto-generated) | `PROJECT.md` (point the generator at PROJECT.md, not README.md) |
| Development workflow / quality gate commands | `CONTRIBUTING.md` when contributors arrive; absent until then |
| Agent invariants (file size caps, validation rules, quality gate) | `~/.claude/CLAUDE.md` |
| Repo-specific agent invariants | `PROJECT.md` Engineering Standards section |

If `TLDR.md` grows past ~300 tokens, audit it. Operator material drift is the usual failure mode.

## Adding A New Repo

For a new repo joining an existing monorepo umbrella:

1. Create the per repo doc set:
   - `TLDR.md` with opening paragraph + Mental Model + trailing `See [PROJECT.md](./PROJECT.md) for more.`
   - `README.md` with product statement, install, quickstart, dev gate, trailing `See [PROJECT.md](./PROJECT.md) for more.`
   - `PROJECT.md` with architecture depth. If the repo is too new to have shape yet, create a minimal `PROJECT.md` (a stub Repository Boundaries section) and grow it as boundaries clarify; the trailing pointers from TLDR and README should always resolve.
2. Update the monorepo `TLDR.md` sibling table to list the new repo and link to its `TLDR.md`.
3. Symlink the agent files:
   ```bash
   cd /<umbrella>/<monorepo>/<new-repo>
   ln -s TLDR.md CLAUDE.md
   ln -s TLDR.md AGENTS.md
   ```
4. Commit the symlinks. Git stores them as symlinks by default; verify with `git ls-files -s CLAUDE.md` and confirm the mode is `120000`.
5. Verify the walk works:
   ```bash
   cat -L CLAUDE.md     # confirms symlink resolves to TLDR.md
   cat -L AGENTS.md
   readlink CLAUDE.md   # prints TLDR.md
   readlink AGENTS.md
   ```

## Bootstrapping A Fresh Umbrella

For a new monorepo umbrella with no TLDR stack yet:

1. Create `/<umbrella>/TLDR.md` with one to two lines naming the product family and the v1 substrate.
2. Create `/<umbrella>/<monorepo>/TLDR.md` with the product statement, sibling table, dependency direction, and mental model.
3. Symlink `CLAUDE.md` and `AGENTS.md` to `TLDR.md` at the monorepo layer.
4. For each repo, follow the steps in **Adding A New Repo**.

Do not bother symlinking at the umbrella layer if its `TLDR.md` is only one line. The monorepo layer is where the symlink starts paying.

## Migrating An Existing Repo Into The Stack

For a repo that already has any combination of `CLAUDE.md`, `README.md`, or `PROJECT.md`:

1. Audit `CLAUDE.md`. Compare each rule against `~/.claude/CLAUDE.md`.
   - Globally covered → delete.
   - Repo-specific architectural invariant (e.g. CLI shape rule) → lift into `PROJECT.md` Engineering Standards.
   - Operator facing → lift into `README.md`.
   - Repo identity paragraph → seed `TLDR.md`.
2. Audit `README.md`. The README that remains must be product focused: title, product statement, install, quickstart, dev gate, optional auto-generated tables, trailing PROJECT.md pointer. Lift everything else:
   - Architecture / system model / repo boundaries → `PROJECT.md`.
   - Protocol contracts (events, RPC, wire types) → `PROJECT.md`.
   - Isolation / sandboxing / image contracts → `PROJECT.md`.
   - Release model / crates.io contract / distribution → `PROJECT.md`.
   - Endpoint and path policy → `PROJECT.md`.
3. Audit `PROJECT.md` if it exists. Most legacy `PROJECT.md` files in early repos were tracer-bullet stubs holding operator content. Replace stub content with real architecture depth. If `PROJECT.md` is genuinely empty of architecture today, draft a Repository Boundaries section as the seed and grow from there.
4. Write or trim `TLDR.md` to the playbook's TLDR.md contract. Add the trailing PROJECT.md pointer.
5. Add the trailing PROJECT.md pointer to `README.md`.
6. Run the steps in **Adding A New Repo** from step 3 to install the symlinks.

## Verification

After setup, an agent invoked from any repo should see in its system prompt:

- `~/.claude/CLAUDE.md` content (global rules)
- The umbrella `TLDR.md` content (one paragraph) if present
- The monorepo `TLDR.md` content (product + sibling map)
- The repo `TLDR.md` content (why this repo)

Run `claude` (or the equivalent agent CLI) from the repo and inspect the loaded context. If any layer is missing, check that the `CLAUDE.md` symlink resolves with `cat -L`. On macOS and Linux, `readlink CLAUDE.md` should print `TLDR.md`.

## Anti-Patterns

- **Install instructions in TLDR.md.** They are wrong-audience noise that ships in every agent context. Move to `README.md`.
- **Common command lists in TLDR.md.** Same reason. Move to `README.md`.
- **Duplicating global invariants in repo TLDR.md.** `~/.claude/CLAUDE.md` already governs. Per-repo invariants belong in `PROJECT.md`.
- **Chained symlinks** (`AGENTS.md` → `CLAUDE.md` → `TLDR.md`). Parallel symlinks are robust to either link being touched. Always symlink directly to `TLDR.md`.
- **TLDR.md growth past ~300 tokens.** Audit and trim. Operator material is the usual culprit.
- **Version pins or moment-in-time snapshots in TLDR.md or PROJECT.md.** Things like `v0.4 starts with...`, `today that is...`, `Pass 1 implements the tracer slice`, or named milestones make these files churn on every release. Describe the shape, not the current version. Version-stamped content belongs in `CHANGELOG.md`, release notes, or migration docs. `TLDR.md` and `PROJECT.md` should still read correctly after the next ten releases.
- **Stability labels phrased as state.** `remains experimental`, `is still in alpha`, `now in beta`, `preview` carry the same drift cost as version pins. The status changes; the docs do not. Use direct descriptors (`alternate backend`, `experimental backend` once, not "remains experimental") or relocate stability commentary to release notes and the changelog.
- **"Out Of Scope" / "Coming Soon" blocks.** These are roadmap content, not architecture. Roadmap belongs in issues, milestones, or a separate roadmap doc. Architecture docs describe what is, not what might be.
- **Deferred work or roadmap phrasing in prose.** Sentences like "X is deferred", "X is not in scope", "X is out of scope", "Y is deferred" are the prose variant of an Out Of Scope block. Same drift cost, different surface. State what is supported, drop the negative statement.

## Cost Model

Three layers in the typical stack adds roughly 500 tokens to every agent's system prompt for the session. Anthropic prompt cache amortizes this for long sessions. Short-lived subagents pay the full cost on each spawn; the trade is worth it when the alternative is an agent landing in a repo with no idea what it does.

If token cost matters more than grounding for a specific repo (e.g., a high-frequency CI helper), skip the symlink for that repo and brief subagents explicitly in their prompts.

## Reference Example

The `runtime-matters` repo in the littleorgans monorepo is the canonical example of this pattern:

| Aspect | File |
| --- | --- |
| Grounding shape | `runtime-matters/TLDR.md` |
| Lean product shape | `runtime-matters/README.md` |
| Depth shape (architecture, isolation contract, events contract, release) | `runtime-matters/PROJECT.md` |
| Symlinks | `runtime-matters/CLAUDE.md` and `runtime-matters/AGENTS.md`, both parallel to `TLDR.md` |

When in doubt about whether a piece of content belongs in `TLDR.md`, `README.md`, or `PROJECT.md`, check how `runtime-matters` handled it.

`runtime-matters/README.md` uses a structural-section pattern (`The substrate` / `The boundary` / `The composition`) that builds the product story in load-bearing layers. It is one effective shape for infrastructure-flavored repos. Adopt it where it fits the repo's narrative; use a different section structure when it doesn't.

### Audit Checklist

Testable properties to keep a doc set canonical:

- **TLDR.md.** No install commands. No operator command lists. A single diagnostic-pointer command framed as mental model is acceptable. Ends with `See [PROJECT.md](./PROJECT.md) for more.`
- **README.md.** Leads with product fit (what it does, who reaches for it, why) and that material occupies roughly 80% of the file. Supporting scaffolding follows: install, quickstart, host support matrix. No development workflow, no admin or MCP tool reference tables, no architecture, no protocol contracts, no isolation policy, no release distribution depth. Ends with `See [PROJECT.md](./PROJECT.md) for more.`
- **PROJECT.md.** No trailing pointer (it is the depth file the others reference). No roadmap content (no "Out Of Scope" blocks, no "X is deferred" prose). No version pins or stability-as-state labels.

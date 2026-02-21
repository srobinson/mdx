# agent-matters Product Spec

Status: draft  
Date: 2026-04-23

## Purpose

`agent-matters` is a local runtime manager for AI coding agents.

It gives Codex, Claude, and future agent runtimes a reproducible way to assemble
focused runtime homes from curated profiles, capabilities, source skills,
instructions, hooks, settings, and launch material.

The user should not need to learn a large command tree. The normal product
experience is:

```text
install agent-matters
initialize selected runtimes
open the agent
ask the agent to set up the repo
review the plan
let the agent apply deterministic changes
```

The CLI exists to bootstrap, validate, synchronize, and provide deterministic
operations. The agent owns interpretation, planning, source discovery, profile
authoring, and explanation.

## Product Thesis

Agent runtime configuration should be authored, inspectable, reproducible, and
agent operated.

Current agent homes such as `.codex` and `.claude` accumulate valuable local
practice, but they are hard to compose, audit, share, trim, and regenerate.
`agent-matters` turns that practice into catalog material and generated runtime
homes.

Generated runtime homes are operational outputs. They remain inspectable and
debuggable, but durable changes belong in the source material that generated
them.

## First Run

A new user starts with:

```bash
npx agent-matters init
```

The first run flow should:

1. Detect supported runtimes on the machine.
2. Ask which runtimes the user wants to manage.
3. Create `~/.agent-matters`.
4. Install the `agent-matters` skill into selected runtimes.
5. Clone or update curated `agent-matters` plugin repositories.
6. Import existing runtime material into `~/.agent-matters`.
7. Run `doctor`.
8. Print the next prompt for the user to use inside the selected agent.

The setup should avoid mutating existing `.codex` or `.claude` homes during
initial import. Existing homes are source material to preserve and normalize,
not directories to overwrite during bootstrap.

Example final output:

```text
agent-matters is ready.

Managed root:
  /Users/stuart/.agent-matters

Runtimes:
  Codex   configured
  Claude  configured

Imported existing material:
  Codex   12 skills, 3 MCP servers, 2 instruction files
  Claude   8 skills, 2 MCP servers, 1 CLAUDE.md

Health:
  doctor passed

Next:
  Open Codex or Claude in a repo and say:
  "Use agent-matters to set up this repo."
```

## Runtime Setup

Runtime setup means making the selected agent able to operate
`agent-matters`.

For the initial product, that means:

- Install an `agent-matters` skill into the runtime.
- Ensure the runtime can run the `agent-matters` CLI.
- Give the runtime instructions for planning before writes.
- Give the runtime instructions for synchronizing existing local material.
- Give the runtime instructions for using curated source skills.

MCP is not required for the first product. It can be reconsidered when shell
output becomes too loose, when operations need stricter typed boundaries, or
when a UI needs direct structured access.

## Managed State

`~/.agent-matters` is the durable local home for managed material.

Expected shape:

```text
~/.agent-matters/
  catalog/
    profiles/
    skills/
    instructions/
    hooks/
    mcp/
    runtime-settings/

  imports/
    runtime-homes/
    sources/

  plugins/
    official/
    forks/

  builds/
    codex/
    claude/

  indexes/
  logs/
```

The exact layout can evolve, but the boundary matters:

- Existing runtime homes are imported into managed state.
- Curated plugins live under managed state.
- Generated builds live under managed state.
- Arbitrary project directories should not receive `catalog/` or `vendor/`
  folders unless the user explicitly chooses a project local catalog.

## Sync

`sync` imports and reconciles runtime material into `~/.agent-matters`.

Initial sync runs during `init`. The user or agent can run it again when local
runtime homes change.

Sync should:

- Read selected runtime homes.
- Detect skills, MCP servers, instructions, hooks, settings, and launch files.
- Normalize material into the catalog where possible.
- Preserve original material as import records where normalization is partial.
- Record provenance as imported from runtime home.
- Report drift without overwriting source material silently.

Direction matters:

```text
sync pulls existing runtime material into agent-matters
compile writes generated runtime homes from agent-matters material
```

## Curated Plugin Repositories

The curated plugin repository is a core product asset.

It should contain:

- The `agent-matters` runtime skill.
- Curated profiles.
- Curated runtime capabilities.
- Curated source skills.
- Fixtures and tests for source skills.
- Documentation for contribution.

First run should clone or update the curated plugin repository. If the user has
GitHub authentication available, setup may also prepare a user fork. If not,
the official repository can be used read only until the user contributes.

When the user discovers a new source, the agent should:

1. Update local plugin repositories.
2. Check whether a source skill already exists.
3. Load the source skill if present.
4. Create a source skill if missing.
5. Test search, inspect, fetch, and normalization behavior.
6. Register the source locally.
7. Request a PR back to the curated plugin repository.

This creates the product loop:

```text
one user discovers a source
the agent packages it as a source skill
the user contributes it upstream
future users receive it as curated material
```

## Source Model

Named external sources must not be hardcoded in the core.

`skills.sh`, `mcp.sh`, GitHub capability repos, local catalogs, and future
sources are source skills. They live in plugin repositories and teach the agent
how to search, inspect, fetch, and normalize material from that source.

The core only owns the durable boundary:

- Validate normalized bundles.
- Write catalog material.
- Preserve source material.
- Record provenance.
- Update indexes.
- Detect drift.
- Run doctor checks.

A source skill owns source specific behavior:

- How to search the source.
- How to inspect an entry.
- How to fetch source material.
- How to map metadata.
- How to emit a normalized bundle.
- How to test the connector.

This keeps the system extensible. Adding `mcp.sh` should mean adding a source
skill in the curated plugin repository, not adding a Rust match arm.

## Profile Authoring

Profile execution already exists as a concept. Profile authoring is a product
gap.

The user need is:

```text
I need an agent runtime for this kind of work.
Help me create the profile that represents that intent.
```

The agent should be able to:

- Inspect the repository.
- Inspect existing profiles and capabilities.
- Search curated source skills when material is missing.
- Propose a new profile plan.
- Show required imports before writing.
- Create durable profile material after approval.
- Compile and activate the profile.
- Explain what was created and why.

The profile plan should include:

- Profile id.
- Summary.
- Target runtime or runtimes.
- Selected capabilities.
- Selected instructions.
- Required source imports.
- Runtime settings.
- Hooks.
- MCP servers.
- Environment requirements.
- Files that will be written.
- Warnings and blockers.

The manifest remains the storage format. The product workflow should be intent,
plan, review, write, compile, activate, explain.

## Agent Workflow

Once `init` has completed, the normal user instruction is:

```text
Use agent-matters to set up this repo.
```

The agent should:

1. Run `doctor`.
2. Run or inspect sync state.
3. Inspect the repository.
4. Inspect available profiles and capabilities.
5. Check curated source skills for missing material.
6. Propose a profile and runtime plan.
7. Ask before mutating managed state or runtime homes.
8. Apply approved writes through deterministic commands.
9. Compile the runtime home.
10. Activate the selected runtime.
11. Explain what changed.

The agent should treat writes into arbitrary project directories as suspicious
unless the user explicitly requested a project local catalog.

## CLI Surface

The human facing CLI should stay small.

Initial surface:

```bash
npx agent-matters init
agent-matters doctor
agent-matters sync
agent-matters --version
agent-matters --help
```

Additional expert commands may exist, but they should not define the product
experience. The product experience is agent mediated.

Commands that mutate state should support plan first behavior. A successful
result should show write roots, written files, provenance, warnings, and
blockers.

## Product Principles

No hardcoded named sources.

Sources are skills. Curated sources live in plugin repositories. New sources
are added by agents and contributed back through PRs.

Preserve existing runtime homes.

The user's current `.codex` and `.claude` homes may contain real accumulated
practice. Initial setup should import and preserve that material before
generating anything new.

Keep the core deterministic.

The core validates, writes, compiles, indexes, and explains. The agent reasons,
discovers, selects, authors, and communicates.

Plan before writes.

The agent should know the write roots and provenance before applying changes.

Make generated homes explainable.

Every generated runtime file should trace back to profile material, capability
material, source imports, runtime settings, or adapter behavior.

## MVP Scope

MVP should include:

- Interactive `init`.
- Runtime detection for Codex and Claude.
- `~/.agent-matters` creation.
- Agent skill installation for selected runtimes.
- Curated plugin repository checkout.
- Initial sync from existing runtime homes.
- `doctor`.
- Minimal profile planning workflow through the agent skill.
- No hardcoded `skills.sh` behavior in core.
- Source skills loaded from curated plugin material.
- Import provenance.
- Compile and activate generated runtime homes.

MVP should defer:

- MCP server integration.
- GUI editing.
- Long lived background daemon.
- Remote account system.
- Fully general plugin marketplace.
- Automatic upstream PR creation without user review.

## Related References

[`gstack`](https://github.com/garrytan/gstack) is a useful precedent for
productizing agent workflow as skills. The local research note is
[`agent-workflow-skills-system-gstack.md`](../research/agent-workflow-skills-system-gstack.md).

Relevant patterns:

- Curated skills as the product surface, not just documentation.
- A host adapter model that maps one skill system across multiple agent
  runtimes.
- Generated skill docs with freshness checks against source of truth code.
- Shared skill preambles that establish runtime context before work starts.
- Team adoption mechanics through setup, update, and contribution flows.

## Open Questions

- What is the exact package boundary between core, runtime skill, and curated
  plugin repository?
- Should `init` always run `sync`, or ask first with auto import as the default?
- How should local forks be created when GitHub authentication is unavailable?
- What normalized bundle format should source skills emit?
- How much of profile planning should be command based versus skill prose in
  the first implementation?
- What is the safest activation model for existing `.codex` and `.claude`
  homes after import?

## Success Criteria

A new user can install `agent-matters`, initialize Codex or Claude, preserve
their existing runtime material, and ask the agent to set up a repository
without learning the internal command tree.

A new external source can be added as a source skill in a plugin repository
without changing Rust core code.

An agent can create a durable profile plan, show the user what will be written,
apply approved changes, compile a runtime home, activate it, and explain every
material change.

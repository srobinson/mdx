---
title: Grounding synthesis for skill hierarchy in agent-runtimes
type: research
tags: [agent-runtimes, skills, hierarchy, identity, synthesis]
summary: Verified current-state model and architectural constraints for introducing owner/domain/skill hierarchy; four identity planes reconciled against live code, installed harnesses, and official vendor contracts. No design proposed.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

# Grounding synthesis: skill hierarchy in agent-runtimes

Synthesis of three prior reports (`agent-runtimes-skill-hierarchy-schema-compiler.md`, `agent-runtimes-skill-hierarchy-materialization-harness.md`, `agent-runtimes-skill-hierarchy-reference-conventions.md`) reconciled against live state on 2026-09-03: `/Users/alphab/.agent-runtimes` at HEAD `71e3871ebbb8813fb213827f70e38fc4d83feafa` (dirty: `runtimes/generalist/runtime.toml`, `runtimes/tm-stu/runtime.toml`, `skills/tm-orchestrate/SKILL.md`, untouched), installed Claude Code 2.1.259, Codex CLI 0.153.0, Grok 1.0.13, and the official vendor docs (OpenAI build-skills, Claude Code skills reference, xAI skills-plugins-marketplaces, all fetched today). Read only; no repository or generated home was modified. This document states the model and constraints. It proposes no design.

## Overview

agent-runtimes generates per-runtime config homes from `runtime.toml` manifests. Skills are committed bodies under `skills/<name>/`, copied whole into `<home>/skills/<name>/` for whichever of Claude, Codex, and Grok a runtime targets. The question on the table is introducing owner/domain/skill hierarchy into that catalog.

The central finding, stable across all three reports and confirmed by live checks, is that "the skill's name" is four distinct things that today happen to coincide (with one live exception), and that the three harnesses disagree about which of them drives discovery and invocation. Any hierarchy design is really a decision about which plane carries the hierarchy and how the planes map to each other. The generated destination layout is a harness contract with hard evidence behind it: only a flat `<home>/skills/<segment>/SKILL.md` shape is portable across all three harnesses. Hierarchy is therefore free on the authored side and constrained on the generated side.

## Key concepts: the four identity planes

Keep these separate. Conflating any two of them is how the current gaps arose.

1. **Authored catalog identity.** The key a `runtime.toml` uses in `[skills].required` / `[skills].optional`, and the key `skills.catalog()` produces. Today this is the basename of an immediate child of `skills/` (`skills.catalog` in `bin/agent_runtime_compiler/skills.py`: one-level `iterdir()`, key = `entry.name`, membership = presence of `SKILL_MARKER`). It is not authored anywhere; it is a location. Confirmed live: the function is unchanged from the reports' reads.

2. **Frontmatter `name`.** A YAML field in `SKILL.md`. The generator never reads it; `_skill_frontmatter` (`bin/agent_runtime_compiler/capabilities.py`) extracts only `requires_capability`. Harness semantics differ per vendor (see the contract table below).

3. **Generated directory name.** The path segment under `<home>/skills/`. Today it equals the catalog key because `skills.materialize` computes `dest = skills_dir / name`. This is the plane the harnesses actually see.

4. **User invocation name.** What a person types. Derived differently per harness, from plane 2 or plane 3 depending on vendor.

### The official per-harness contract (fetched 2026-09-03)

| Harness | Discovery under the home's skill root | Invocation name source | Duplicate handling |
| --- | --- | --- | --- |
| Claude Code | One level: docs table lists `~/.claude/skills/<skill-name>/SKILL.md` and `.claude/skills/<skill-name>/SKILL.md`. For a generated home the root is `CLAUDE_CONFIG_DIR/skills`. | **Directory name.** Official docs, "How a skill gets its command name": for a personal or project skill, "`name` sets only the display label shown in skill listings, and the command still comes from the directory name." Frontmatter `name` sets the command segment only for plugin skills, namespaced `plugin-name:skill-name`. | Source precedence (more specific wins); plugin skills namespaced so they cannot conflict. Nested `.claude/skills/` **stores** below the cwd get directory-qualified names (`apps/web:deploy`), but that is a cwd-relative project-store mechanism, not nesting inside one skill root, so it offers no lever for generated homes. |
| Codex | Recursive. Proven by offline probe (`codex debug prompt-input` rendered `skills/group/alpha/SKILL.md` from a temp `CODEX_HOME`); OpenAI docs list ambient roots and say symlinked folders are followed. | **Frontmatter `name`**, a required field per OpenAI docs; explicit form `$skillname`. | "If two skills share the same `name`, Codex doesn't merge them; both can appear in skill selectors" (official). Visible, ambiguous, no namespacing. |
| Grok | Recursive. Proven by `grok inspect` probe against a temp `GROK_HOME`; xAI docs describe skill paths walked recursively. | **Frontmatter `name`**: "Identifier. Directory name if omitted" (official). User-invocable skills appear as `/<skill-name>`. | Duplicate resolution unspecified in docs; probe showed both listed with separate source paths. |

Consequences worth stating plainly:

- The live `codebase-map` body (directory `skills/codebase-map/`, frontmatter `name: map`, confirmed by read today) invokes as `/codebase-map` in Claude but `$map` in Codex and `/map` in Grok. The reference-conventions report's open question "directory name or frontmatter name?" is now **resolved by official docs, per harness, with different answers**. The divergence is not hypothetical; it ships today in `runtimes/codebase-mapper/`.
- A nested generated layout (`<home>/skills/team/alpha/SKILL.md`) is discovered by Codex and Grok and, on all current evidence, not by Claude (docs one-level table; `claude plugin validate --strict` ignored a nested marker in the probe; loader diagnostics describe `.claude/skills/*`). Nested output therefore produces harness-divergent skill sets from identical bytes.
- Claude's prompt inclusion for nested markers remains formally unproven (no offline renderer; probes ran on 2.1.258, installed binary is now 2.1.259), but docs, validator, and loader text all point the same way. Treat "Claude is one-level" as the working assumption, marked as evidence-supported rather than proven.

## The full flow: authored manifest to audited home

Confirmed against live code today (`skills.catalog`, `_AGENT_ID_COMPONENT` / `_AGENT_ID_PATTERN` in `manifest.py`, `requires_capability` parsing in `capabilities.py` all present as reported). Test count is **96 passing** (`python3 -m pytest tests -q` run today); schema-compiler.md's count of 87 is stale, materialization-harness.md's 96 is current.

1. **Author.** A skill body at `skills/<name>/` with `SKILL.md`; a manifest at `runtimes/<dir>/runtime.toml` declaring `id` (hierarchical, `owner/name`, validated by `_AGENT_ID_PATTERN`), `[skills].required` / `[skills].optional` (opaque strings), harness targets, settings deviations.
2. **Discover.** `generate.all_runtime_dirs` finds manifests by `rglob("runtime.toml")`, so runtime directories nest freely; `skills.catalog` finds bodies by one-level `iterdir()`, so skill directories cannot. `catalogs.discover` is the only `$HOME` read (MCP definitions only).
3. **Validate identities.** `manifest.validate_catalog_identities` enforces catalog-wide uniqueness of authored agent ids and fixed names, failing before any write. Skills have no equivalent: manifest skill names are validated only by dict membership, frontmatter `name` is never read, never checked against the directory, never checked for cross-body uniqueness (the 36 current bodies happen to have unique frontmatter names; nothing preserves that).
4. **Plan.** `compiler.plan` is pure: resolves skills, builds the catalog, derives the vendor constraint from **required** skills' `requires_capability` frontmatter intersected through `capabilities.toml` (`capabilities.vendor_constraint`), narrows declared harnesses, validates harness tables, compiles redactions, resolves MCP, validates the recommended model against `harness_models_v1.json`, drops missing optionals, and freezes a `RuntimePlan`. The `generated_from` digest hashes manifest bytes plus each required skill's **name and frontmatter**, so any rekeying of skill identity moves every home's digest.
5. **Materialize.** `writers.materialize` writes the shared skill tree once for all targeted harnesses (`skills.materialize`: prune unwanted immediate children, digest-compare wanted ones via `tree_digest`, whole-tree `copytree` replacement, never merge), then instructions (one body, two names), per-harness configs composed from committed baselines, prune of untargeted harness files, `capabilities.json`.
6. **Audit and gate.** `audit.audit_runtime` compares immediate `skills/` children against owned bodies by content digest; a stale copy is `resync` residue and `generate.regenerate` refuses the whole set without `--force`, because it cannot distinguish a body edit from a harness writing into a template. `audit_orphans` catches runtime directories whose manifest is gone. `--clean` removes exact findings.
7. **Launch (out of scope for this repo).** transport-matters clones the template into a per-run overlay, points `CLAUDE_CONFIG_DIR` / `CODEX_HOME` / `GROK_HOME` at it, swaps `config.grok.toml` into place for Grok. Everything after the clone (frontmatter parsing, prompt inclusion, invocation resolution) is harness-owned.

### Where the flat assumption is load-bearing

The schema-compiler report inventories fourteen sites; the ones that actually break under hierarchy, deduplicated across reports and confirmed by the materialization report's live probes:

- `skills.catalog` (one-level walk, basename key) — the single definition point; downstream membership checks (`vendor_constraint`, `_drop_missing_optional`, `materialize`) follow whatever it returns.
- `skills.materialize` destination (`dest = skills_dir / name`, no parent creation) and its one-level prune loop.
- `audit.audit_runtime`'s one-level skills walk and its verbatim-asserted reason strings.
- `generate.clean_residue`'s literal `parent.name == "skills"` test.
- The `generated_from` digest keying (`f"\n{name}\0"` per required skill).
- Probe-proven: handing the current copier a slashed key (`team/alpha`) writes nested output that the audit then reports as unowned and the next run's prune deletes, so every run oscillates. A partial move at `catalog()` alone is not viable.

Depth-neutral already: `tree_digest` (rglob-based), `remove_path`, `RuntimePlan`'s tuples/dicts, `writers.materialize` pass-through, `tests/generate_support.write_skill` (already `mkdir(parents=True)`), TOML rendering of non-bare keys (`render.table_header` quotes).

### Source-side hierarchy failure modes today (probe-proven)

- `skills/team/alpha/SKILL.md` with no marker on `team/`: invisible; catalog returns `{}`; a required reference fails as `unknown skill`.
- `skills/team/SKILL.md` **plus** `skills/team/alpha/SKILL.md`: catalog sees only `team`; the copier ships the whole subtree; Codex and Grok discover `alpha` as a real extra skill in the generated home, Claude does not, and `alpha`'s `requires_capability` (if any) never reaches the vendor constraint. This is the worst shape: undeclared, capability-unconstrained, harness-divergent skill delivery from a committed body.

## File map

```
skills/<name>/SKILL.md                         owned bodies (the only place to edit)
bin/generate.py                                CLI: --catalog --audit --clean --force --all
bin/agent_runtime_compiler/skills.py           catalog, tree_digest, materialize (copy/prune)
bin/agent_runtime_compiler/manifest.py         agent identity (_AGENT_ID_PATTERN), resolve_skills,
                                               validate_catalog_identities, resolve_harnesses
bin/agent_runtime_compiler/capabilities.py     _skill_frontmatter, vendor_constraint, derive_capabilities
bin/agent_runtime_compiler/compiler.py         plan() -> frozen RuntimePlan, _drop_missing_optional
bin/agent_runtime_compiler/configuration.py    baseline composition, MANAGED_KEYS
bin/agent_runtime_compiler/writers.py          materialize: skills, instructions, configs, prune
bin/agent_runtime_compiler/audit.py            residue model, skills content audit, audit_orphans
bin/agent_runtime_compiler/redaction.py        intent -> mechanism, both launch digests
capabilities.toml                              capability -> vendor registry
baselines/{settings.json,config.toml,config.grok.toml}   fleet defaults per harness
harness_models_v1.json                         vendored model catalog (recommended-model validation)
runtimes/<dir>/runtime.toml                    authored manifests (10 today; 36 owned bodies)
runtimes/<dir>/skills/<name>/                  generated copies (gitignored; audited by digest)
tests/test_skills.py, tests/generate_support.py  copy/prune/audit fixtures; write_skill is nesting-tolerant
docs/specs/2026-06-17-launcher-home-spec.md    frontmatter declared additive; reserves future keys
```

## Gotchas

1. **Same string, different plane.** `codebase-map` is a catalog key, a directory, and a Claude command; `map` is a display label in Claude and the actual invocation name in Codex and Grok. Any migration or validation keyed on one plane silently lies about the others.
2. **Frontmatter is a shared namespace with vendor-divergent semantics.** Codex requires `name`; Grok defaults it to the directory; Claude treats it as display-only outside plugins. Overloading `name` to also carry this repo's hierarchy would change invocation names on two of three harnesses as a side effect.
3. **The one-level claim in-repo is half-stale.** `skills/skill-matters/SKILL.md` and the `generate.py` docstring state both harnesses read `<home>/skills/<name>/SKILL.md`. As a statement of the portable contract it is correct; as a statement of harness discovery it is wrong for Codex and Grok (recursive, proven). The `skills.py` comment still says "both harnesses" in a three-harness fleet (confirmed live today).
4. **Optional skills never constrain vendors.** Only required skills feed `vendor_constraint`. An optional capability-requiring skill can land on a home whose harness cannot serve it (live example: `helioy-imagegen-primatives` optional on `tm/imagegen`, and the launcher spec is stale in claiming it requires the capability).
5. **`generated_from` is a published contract.** It hashes required-skill names; a rekeying moves every digest and transport-matters pins it. Additive `capabilities.json` keys need no `schema_version` bump, but digest movement is consumer-visible regardless.
6. **Grok isolation is incomplete by documented measurement.** Plugins inherit from `$HOME/.claude` regardless of `GROK_HOME`; `[skills] ignore` matches resolved paths so symlinked skills walk through it. A generated tree and Grok's effective skill set differ under a real operator HOME. Comparator captures with an emptied HOME sidestep this; reachability captures do not.
7. **The resync gate is the safety mechanism, not friction.** The dirty `skills/tm-orchestrate/SKILL.md` in the working tree means regeneration will demand `--force`; that is the designed behavior distinguishing body edits from harness writes into templates.
8. **Skill-to-skill and doc references use invocation names.** Renames or namespacing that change what a user types have blast radius inside skill bodies and operator habit, not just in the generator.
9. **`skill-creator`'s frontmatter allowlist is Anthropic's packaging schema, not this fleet's.** It would reject `requires_capability`. The Claude Code loader itself ignores unknown keys, and the launcher-home spec declares frontmatter additive, so custom keys are safe for home-delivered skills but not for claude.ai upload paths.
10. **Probes age.** Codex 0.153.0 and Grok 1.0.13 findings are current-install proofs; Claude probes ran on 2.1.258 and the installed binary is 2.1.259. Discovery behavior claims should be re-probed at design-verification time, cheaply (`codex debug prompt-input`, `grok inspect`, `claude plugin validate`).

## Architectural constraints

These bind any hierarchy design. Each is marked proven (P: code read, live probe, or official doc) or working assumption (W: strong evidence, no direct proof).

1. **(P) The generated destination must remain one flat level of `<home>/skills/<segment>/SKILL.md`.** Codex and Grok tolerate more; Claude on all evidence does not, and a marked grouping directory leaks undeclared, capability-unconstrained skills to two harnesses. Flat output is the only shape all three provably serve. (W on the narrow point of Claude nested prompt inclusion, P on everything else.)
2. **(P) Hierarchy can therefore live only in authored planes:** the source tree under `skills/`, the catalog key, the manifest reference. The mapping from authored ID to flat destination segment is a new, explicit function that does not exist today because the planes coincide.
3. **(P) Flattening creates two collision classes that do not exist today** and must fail before any write, mirroring `validate_catalog_identities`: two authored paths flattening to one destination segment, and two bodies sharing a frontmatter `name` (ambiguous in Codex/Grok selectors; official Codex docs confirm duplicates are kept visible, which is not a usable contract).
4. **(P) The invocation plane cannot be unified by this repo.** Claude keys commands on the destination directory name; Codex and Grok key on frontmatter `name`. The generator controls both inputs (segment and frontmatter bytes) but a single skill still surfaces under harness-specific names unless directory segment and frontmatter `name` are forced equal, which is a validation choice, not a mechanism the harnesses provide. The live `codebase-map`/`map` divergence must be either migrated or explicitly encoded as an alias.
5. **(P) A skill registry entry is at minimum a triple** (stable manifest key, source body path, harness-visible segment/name), replacing the current `dict[str, Path]` that collapses them. The materialization report's probes show partial moves thrash the audit/prune cycle.
6. **(P) The audit, prune, clean, and resync machinery must change in the same wave as the catalog key.** `--clean` deletes at the finding path; a grouping parent as a finding deletes siblings. `clean_residue`'s `parent.name == "skills"` test and the audit's one-level walk are coupled to the destination shape.
7. **(P) Digest churn is a coordinated event.** Rekeying moves `generated_from` for every home; transport-matters consumes it. `launch_requirements_digest` is unaffected.
8. **(P) The ID grammar should reuse `_AGENT_ID_COMPONENT`.** Agent ids already define the component shape and the owner-namespace semantics (`tm/`, `user/`); the repo's own lesson is to match the established shape rather than invent a second grammar in the same catalog.
9. **(P) Generation must not read `$HOME` for content**, unchanged. Hierarchy adds no exception.
10. **(W) Required-vs-optional and capability semantics carry over untouched.** Nothing about hierarchy changes `vendor_constraint`; but the flat inventory means any new nesting must guarantee every discovered leaf is a catalog citizen, or the leak in gotcha-style shape 2 recurs.

## Critique verdicts

Verdicts on the critiques and options raised across the three reports, reconciled against the official contracts.

### Act on

- **Flat generated output, hierarchical authored catalog.** Every line of evidence converges: Claude's one-level discovery, the grouping-leak failure mode, the probe-proven prune/audit thrash of nested output, and the smallest-change-area argument. This is the one structural decision the evidence effectively makes for the designer.
- **Pre-write collision validation for the skill registry** (duplicate flattened segments, duplicate frontmatter names, duplicate manifest keys), modeled on `validate_catalog_identities`: fail with both paths, before any home is touched.
- **Registry entries as explicit triples** (manifest key, body path, destination segment) threaded through `RuntimePlan`, replacing implicit key-equals-path.
- **Close or encode the `codebase-map`/`map` divergence** as part of the same change: either validate frontmatter `name` against the destination segment or record the alias deliberately. Leaving it unvalidated while adding a second identity axis compounds the ambiguity.
- **Coordinate the `generated_from` digest move with transport-matters** before landing.

### Consider

- **Where the authored ID lives**: frontmatter (an `id:` or similar key, additive per the launcher-home spec, mirroring how agents carry `id` in `runtime.toml`) versus the relative source path as the key (mirroring how `rglob("runtime.toml")` freed runtime directories). Both fit the evidence; the agent precedent favors authored-in-file identity with location free to move, while path-as-key needs no new frontmatter and keeps the generator's no-frontmatter-identity stance. This is the owner's contract choice; the reports deliberately leave it open and so does this synthesis.
- **Recursive source discovery via `skill_root.rglob("SKILL.md")`** with a rule for markers under markers (forbid, or treat as body content only), transplanting the runtime-discovery pattern.
- **Forcing frontmatter `name` equal to the destination segment fleet-wide**, which would collapse planes 2-4 into one user-visible name across all three harnesses at the cost of renaming `map`. Cheap to enforce, but it forecloses deliberate display-name divergence; weigh against the alias option above.
- **A validation pass for cross-body frontmatter-name uniqueness even before hierarchy lands.** The property currently holds by luck across 36 bodies and nothing preserves it.

### Noted

- Claude probes predate the installed 2.1.259 by one patch release; re-probe at verification time. Grok `[disabled]`/prompt-inclusion semantics remain unproven (no offline render); moot while output stays flat.
- Grok's `[skills] ignore` resolved-path matching would complicate any nested layout; also moot under flat output.
- The stale in-repo prose ("both harnesses", the one-level claim as a discovery statement, the launcher spec's imagegen capability claim) deserves a docs pass alongside the change, not before it.
- `tracked_names`' two-component projection misattributes tracked auxiliary files inside nested runtimes; adjacent, not blocking.
- Codex/Grok keep duplicate names visible rather than merging; this is why collision handling belongs in this repo's validator rather than being delegated to harness behavior.
- schema-compiler.md's test count (87) and line-number citations are stale against the live tree (96 tests pass today); its symbol-level claims all verified.

### Dismissed

- **Nested generated destinations** (`<home>/skills/tm/code-review/`). Against Claude evidence, leaks undeclared skills to Codex/Grok, probe-proven to fight the prune/audit cycle, and buys nothing the authored-side hierarchy does not.
- **Changing only `skills.catalog` to slashed keys** as an incremental first step. Probe-proven oscillation: every run reports a removal and an addition, and `--clean` deletes grouping parents wholesale.
- **Frontmatter `name` as the sole identity.** Claude officially ignores it for command naming outside plugins, so it cannot be the invocation identity fleet-wide; it is also a required Codex field with its own vendor semantics, so overloading it as the catalog key couples this repo's identity to harness-facing behavior. It remains one plane to validate, not the anchor.
- **Relying on Claude's nested-store qualified names (`apps/web:deploy`) as a namespacing mechanism for homes.** That mechanism is cwd-relative project-store discovery, not config-home skill-root discovery; it does not apply to `CLAUDE_CONFIG_DIR/skills`.

## Proven vs unproven (summary)

**Proven today:** repo HEAD and dirty set; 96 tests passing; flat catalog code, agent ID grammar, frontmatter parsing surface, `codebase-map`/`map` mismatch (all by direct read); Codex and Grok recursive discovery and duplicate visibility (installed-binary probes, corroborated by official docs); Claude command-name-from-directory and plugin-only frontmatter naming (official docs); Codex `name` required and duplicates unmerged (official docs); Grok `name` defaulting to directory (official docs); nested-key thrash and grouping-leak shapes (code probes).

**Working assumptions, evidence-backed but unproven:** Claude one-level discovery as prompt-inclusion behavior (docs + validator + loader text, no offline render; probed on 2.1.258, installed 2.1.259); Grok `[disabled]` meaning absent-from-prompt; whether `CLAUDE_CONFIG_DIR`/`CODEX_HOME` homes fully hide operator skill stores at launch (stated as verified in `skill-matters`, not re-launched in any of these passes).

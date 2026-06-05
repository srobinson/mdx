---
title: Skill discovery and materialization in agent-runtimes
type: research
tags: [agent-runtimes, skills, generator, claude, codex, grok]
summary: The generator owns a flat skill catalog and copied runtime tree, while harness loaders differ on nested discovery and duplicate names.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

# Skill discovery and materialization in agent-runtimes

## Executive Summary

Agent Runtimes compiles committed skill bodies and runtime manifests into self contained homes for Claude, Codex, and Grok. The current generator depends on a flat source catalog and flat generated output. Codex 0.153.0 and Grok 1.0.13 discover nested skills, while Claude 2.1.258 diagnostics point to immediate children. Preserving a source hierarchy in generated homes would also break current prune, audit, and clean logic.

## Project Metadata

| Field | Value |
| --- | --- |
| Project | `agent-runtimes` |
| Language | Python 3 |
| Build style | Repository local generator, no package metadata |
| Entry point | `bin/generate.py` |
| Test framework | pytest |
| Current snapshot | `71e3871ebbb8813fb213827f70e38fc4d83feafa` plus preexisting working tree changes |
| FMM | No `.fmm.db`; direct read only inspection used |
| Owned skills | 36 top level bodies, 180 files, about 1.9 MB |
| Runtime manifests | 10 |
| Verified harnesses | Claude Code 2.1.258, Codex CLI 0.153.0, Grok 1.0.13 |

## Architecture

### Module layout

* `bin/generate.py:144-365` owns CLI routing, runtime discovery, full catalog identity validation, audit, clean, and generation.
* `bin/agent_runtime_compiler/manifest.py:216-295` parses and deduplicates required and optional skill declarations.
* `bin/agent_runtime_compiler/skills.py:37-121` discovers owned bodies, hashes their trees, removes paths, and copies selected bodies.
* `bin/agent_runtime_compiler/capabilities.py:64-213` reads required skill capability metadata and narrows allowed vendors.
* `bin/agent_runtime_compiler/compiler.py:55-197` constructs the immutable desired state in `RuntimePlan`.
* `bin/agent_runtime_compiler/writers.py:35-145` writes the desired state into a runtime template.
* `bin/agent_runtime_compiler/audit.py:47-168` finds foreign paths, changed skill copies, and orphan runtime directories.

### Data flow

```text
runtime.toml
    |
    +--> manifest.resolve_skills
    +--> skills.catalog(skills/)
    +--> capabilities.vendor_constraint
    |
    v
compiler.plan -> RuntimePlan
    |
    v
writers.materialize
    |
    +--> runtime/skills/<catalog-key>/
    +--> AGENTS.md and CLAUDE.md
    +--> harness config files
    +--> capabilities.json
    |
    v
Transport Matters run overlay
    |
    +--> Claude skill loader
    +--> Codex skill loader
    +--> Grok skill loader
```

`skills.catalog()` returns `{entry.name: entry}` for immediate root children containing `SKILL.md`. `compiler.plan()` resolves declarations against that dictionary and reads capabilities from required entries. `writers.materialize()` writes one shared skill tree before the harness specific files. Transport Matters then clones the template, prepares auth and config, and assigns the home to a harness.

## Key Patterns

### Pure plan before filesystem writes

The repository separates decision logic from materialization. `compiler.plan()` returns a frozen `RuntimePlan`; `writers.materialize()` applies it. The intended boundary is explicit at `AGENTS.md:82-85`.

### Full copy replacement

A runtime contains real skill directories, never links back to the owned body. Matching copies stay untouched. Changed or partial destinations are removed before `shutil.copytree` writes the body. This keeps templates portable and prevents removed source files from surviving. See `bin/agent_runtime_compiler/skills.py:81-121`.

### Content based skill drift

`tree_digest()` hashes relative paths, directory entries, executable bits, and file bytes. A harness cache file inside a copied skill changes the digest. See `bin/agent_runtime_compiler/skills.py:53-70`.

### Whole target prewrite gate

`regenerate()` audits every requested runtime before writing any one of them. Changed owned copies require `--force` because the generator cannot infer whether the body changed or a harness wrote into the template. See `bin/generate.py:260-296`.

### Required skills own compatibility

Only required skills contribute `requires_capability`. Optional skills copy into the same home but do not narrow vendors. Missing required entries fail; missing optional entries log and disappear. See `bin/agent_runtime_compiler/compiler.py:71-115` and `bin/agent_runtime_compiler/compiler.py:164-216`.

## Detailed Findings

### Current source and output contract

The source catalog is one level deep. Every current marker is at `skills/<directory>/SKILL.md`. The generated tree uses the catalog key as the destination name:

```text
skills/<catalog-key>/... -> runtimes/<runtime>/skills/<catalog-key>/...
```

The manifest key and loader name can differ. `runtimes/codebase-mapper/runtime.toml:7-8` selects `codebase-map`, while `skills/codebase-map/SKILL.md:1-4` declares `name: map`. The generator parses `requires_capability` but does not validate or compare the frontmatter name.

No production check rejects duplicate frontmatter names. `manifest.dedupe()` removes repeated identical declaration strings only. Runtime identities receive a separate fail before write collision check in `validate_catalog_identities()`; skills have no equivalent.

### Audit and clean

`audit_runtime()` allows generated names and Git tracked top level names. It then inspects each immediate child of `runtime/skills`:

* no matching owned body means foreign skill residue;
* a link or non directory means invalid materialization;
* a digest mismatch means an owned copy needs resynchronization.

The audit compares content for skill bodies only. It does not rebuild a plan and compare generated config or instruction bytes.

Ordinary generation prunes unwanted immediate skill children, including `.system`. Foreign top level files outside `skills/` survive until `--clean`. `clean_residue()` removes each audit finding. If a manifest disappears, `audit_orphans()` reports the entire former runtime directory. See `bin/generate.py:209-234` and `bin/agent_runtime_compiler/audit.py:100-168`.

### Harness discovery matrix

| Harness | Current evidence | Confidence |
| --- | --- | --- |
| Claude Code 2.1.258 | Debug startup resolves the user root to `CLAUDE_CONFIG_DIR/skills`. Installed loader text describes `.claude/skills/*`. Strict validation checks an immediate child and ignores a malformed nested child. | High for root and validator behavior. Nested prompt inclusion and duplicate invocation remain unproven. |
| Codex CLI 0.153.0 | `codex debug prompt-input` loaded an immediate skill and `skills/group/alpha/SKILL.md`. It rendered two same name nested skills as separate entries with separate paths. | High. This is an offline model input render. |
| Grok 1.0.13 | `grok inspect --json` discovered immediate and nested skills. It listed two same name nested skills with separate paths. The bundled guide says configured skill directories are walked recursively. | High for discovery. Prompt inclusion and duplicate invocation choice remain unproven. |

OpenAI's current [Build skills documentation](https://learn.chatgpt.com/docs/build-skills) confirms that Codex does not merge same name skills and can show both in selectors.

Grok has another boundary. Its baseline disables or ignores several ambient sources, but it cannot fully stop plugin inheritance from `$HOME/.claude`. The generated tree may therefore be smaller than Grok's effective discovered set under an operator home. See `AGENTS.md:176-247` and `baselines/config.grok.toml:1-37`.

### Effects of nested source directories

#### Markerless group

```text
skills/team/alpha/SKILL.md
```

The current catalog returns no entry. A required declaration fails as unknown. An optional declaration is skipped.

#### Marked group

```text
skills/team/SKILL.md
skills/team/alpha/SKILL.md
```

The catalog returns only `team`. The copier includes `alpha` inside the parent body. Capability derivation reads only the parent frontmatter. Codex and Grok then discover `alpha` recursively, while Claude evidence points to the parent only. This produces cross harness divergence and an undeclared capability path.

#### Recursive path keys

A focused temporary probe passed `{"team/alpha": body}` into the current copier. The first run wrote `skills/team/alpha`, but the audit marked `skills/team` unowned. The second run removed `skills/team` during immediate child pruning and copied `alpha` again. Clean would remove the group directory as one finding.

Changing `catalog()` to recurse is therefore insufficient. Preserved hierarchy also requires new prune, audit, clean, collision, and test semantics.

#### Flat generated output

Source grouping can remain invisible to harnesses if recursive source discovery resolves each leaf into one immediate generated child. This keeps the current Claude compatible layout and preserves most of the copier and audit.

The registry then needs distinct fields for:

* stable manifest key;
* source body path;
* harness visible name and flat destination.

It must reject duplicate manifest keys, duplicate destinations, and duplicate frontmatter names before any write. The current `dict[str, Path]` cannot represent these distinctions.

### Reuse map

| Existing code | Reuse |
| --- | --- |
| `skills.tree_digest()` | Reuse unchanged per leaf body. |
| `skills.remove_path()` | Reuse for flat leaf replacement and clean. |
| Full replace branch in `skills.materialize()` | Reuse after destinations come from resolved entries. |
| `manifest.resolve_skills()` | Reuse required, optional, order, and declaration deduplication. |
| `capabilities.vendor_constraint()` | Reuse capability intersection after resolving an entry body. |
| `compiler.RuntimePlan` | Keep the immutable desired state boundary; represent resolved skill entries explicitly. |
| `writers.materialize()` | Keep one shared skill write before harness config writes. |
| `audit.Residue` and regenerate prewrite gate | Reuse the finding model and whole target gate. |
| `validate_catalog_identities()` pattern | Apply the same fail before write approach to skill identity collisions. |
| `tests/test_skills.py` | Extend its temporary roots for nested discovery, collisions, flat output, audit, clean, and capabilities. |

### Verification

`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests -q` passed all 96 tests in 0.66 seconds.

`PYTHONDONTWRITEBYTECODE=1 python3 bin/generate.py --audit` reported no residue. Repository status after verification matched the initial three modified files.

Temporary probes confirmed:

* markerless nested source bodies are absent from the current catalog;
* path preserving recursive keys conflict with prune and audit;
* Codex recursively renders nested skills and both duplicate names;
* Grok recursively discovers nested skills and both duplicate names;
* Claude resolves the configured skill root, while current validation ignores nested children.

No harness probe targeted a repository template.

## Dependencies

The generator uses only the Python standard library for this path:

* `pathlib` for source and destination paths;
* `shutil.copytree` and `shutil.rmtree` for convergence;
* `hashlib.sha256` for tree and capability digests;
* `tomllib` and `json` for manifests and generated config;
* `subprocess` for Git tracked name discovery;
* pytest for behavioral tests.

Transport Matters is the downstream consumer. It owns runtime overlays, auth seeding, launcher environment, and the Grok config swap.

## Relevance to Helioy

The flat generated layout is a compatibility boundary across three independently evolving harnesses. Source organization can change without widening that boundary. A structured skill registry with early collision validation would let Helioy group owned skills while preserving deterministic homes, current audit strength, and a single cross harness output shape.

This work also reinforces a fleet rule already used for runtime identities: validate the whole catalog before materializing any member.

## Open Questions

1. Does Claude Code 2.1.258 include nested `CLAUDE_CONFIG_DIR/skills` entries in a live prompt? Its current validator and loader text point against it, but no offline renderer can close the claim.
2. How does Grok choose an explicit invocation when two discovered skills share one name?
3. Which identity should manifests use after source grouping: source relative path, loader name, or a separate stable ID?
4. Is the current `codebase-map` to `map` mapping intentional? New validation must encode or migrate that alias.
5. `tracked_names()` uses the first two path components. A nested runtime's tracked auxiliary file may be attributed to the group directory rather than the leaf runtime. The current nested runtime test covers orphan detection only.

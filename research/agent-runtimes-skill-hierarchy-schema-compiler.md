---
title: Skill identity, selection, and compiler flow in agent-runtimes
type: research
tags: [agent-runtimes, skills, compiler, schema, hierarchy]
summary: Skill identity today is the flat directory basename under skills/; agent identity is already hierarchical (owner/name). Inventory of every flat-basename assumption and a reuse map for hierarchical skill IDs.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

# Skill identity, selection, capability filtering, validation, and runtime planning in /Users/alphab/.agent-runtimes

Read-only trace, 2026-09-03. All paths relative to `/Users/alphab/.agent-runtimes` unless absolute. No fmm index exists for this repo (`no .fmm.db`); findings come from full reads of `bin/generate.py` (369 LOC) and the 12 modules of `bin/agent_runtime_compiler/` (2,545 LOC total, including full `redaction.py`), `capabilities.toml`, four representative `runtimes/*/runtime.toml`, a generated `runtimes/generalist/capabilities.json`, `docs/specs/2026-06-17-launcher-home-spec.md`, `skills/skill-matters/SKILL.md`, all 36 skill bodies' frontmatter, `baselines/`, and the full test suite (87 tests: 30 `test_skills.py`, 27 `test_generate.py`, 17 `test_redaction.py`, 9 `test_configuration.py`, 4 `test_generate_identity.py`).

## 1. Executive summary

The repo has **two identity systems with different maturity**. Agent (runtime) identity is authored, hierarchical, and validated: `id = "tm/generalist"` in `runtime.toml`, two slash-separated components matched by `_AGENT_ID_PATTERN` (`manifest.py:36-37`), owner namespace enforced per kind, cross-catalog uniqueness enforced by `validate_catalog_identities` (`manifest.py:161`). Skill identity is **not authored anywhere**: a skill *is* its directory basename under `skills/`. `skills.catalog()` (`skills.py:42-50`) maps `entry.name -> entry` over a single-level `root.iterdir()`, and that basename is simultaneously the manifest reference key, the capability-lookup key, the audit key, and the literal destination path segment `<home>/skills/<name>`. The generator never reads the SKILL.md frontmatter `name:` field; the only frontmatter key it parses is `requires_capability` (`capabilities.py:122`, `_skill_frontmatter`). The two identity planes already diverge once in the live catalog: `skills/codebase-map/` carries frontmatter `name: map` (see §3, §5).

## 2. Pipeline (compiler flow)

Documented in AGENTS.md and confirmed in code:

```
catalogs.discover()            catalogs.py:73   the ONLY $HOME read (MCP defs)
configuration.load_baselines() configuration.py three committed baselines
manifest.load_manifest()       manifest.py:76   tomllib parse of runtime.toml
    -> compiler.plan()         compiler.py:71   pure; frozen RuntimePlan
    -> writers.materialize()   writers.py:42    only filesystem writer
```

Inside `compiler.plan` (order matters):

1. `agent_identity(manifest)` — schema_version gate (must equal 3, `manifest.py:34`), id/name/description/kind validation, `[launch].fixed_name` canonicalization.
2. `resolve_skills(manifest.get("skills", {}))` (`manifest.py:286`) — accepts a bare array (deprecated; all treated as required, logs `SKILLS_ARRAY_DEPRECATION_NOTICE`) or a `[skills]` table with `required` / `optional` string lists; dedupes; returns `(materialized, required, logs)`.
3. `skill_catalog(skill_root)` — flat name -> body dir map (see §3).
4. `resolve_harnesses(manifest)` (`manifest.py:246`) — declared targets, default all of `("claude","codex","grok")`.
5. `vendor_constraint(runtime_dir, required_skills, skill_bodies)` (`capabilities.py:176`) — for each **required** skill, parse SKILL.md frontmatter, resolve each `requires_capability` entry against `capabilities.toml` (`load_capability_registry`, `capabilities.py:41`), intersect vendor sets. Also feeds a SHA-256 `digest` from manifest bytes + each required skill's name + frontmatter, published as `generated_from`.
6. `constraint.harnesses(declared)` (`capabilities.py:163`) — drops harnesses whose vendor (via `HARNESS_VENDOR`, `manifest.py:27`) is not in the allowed set. Empty result is fatal ("required skills allow no declared harness").
7. `validate_harness_tables(settings, mcp, declared)` — validated against DECLARED, not derived, targets (a table for a later-dropped harness is a derivation, not an author error).
8. Redactions (`parse_redactions` / `compile_redactions`, `redaction.py`) — intent to per-harness mechanism; emitted keys become MANAGED keys via `configuration.MANAGED_KEYS`, derived from `redaction._MECHANISM`.
9. `resolve_mcp` (`manifest.py:376`) — shared bool keys resolved against both machine catalogs; grok resolves against codex's catalog with a lossy `grok_projection()` (`catalogs.py:60`).
10. `recommended_model(manifest)` (`manifest.py:296`) — vendor-keyed; `models.validate_model` requires exact equality with a `harness_models_v1.json` row's `native_model_id` or `canonical_model_id` and `support_tier == "observed"`; effort passes `validate_effort` (ban list `max`/`ultracode`) then `validate_model_effort` narrowing.
11. `derive_capabilities` (`capabilities.py:216`) — projects `capabilities.json`: schema_version 3, identity projection, derived `harnesses[]`/`vendors[]`, `required_capabilities`, recommended model, redaction projection, `generated_from` digest.
12. `_drop_missing_optional` (`compiler.py:200`) — optional skills absent from the catalog are skipped with a log; missing required skills already failed in `vendor_constraint` (and would again in `skills.materialize`).

`writers.materialize` (`writers.py:42`) then converges the home: `materialize_skills`, `materialize_instructions` (one body, two names AGENTS.md + CLAUDE.md), per-harness config surfaces, `_prune_untargeted` (per `HARNESS_FILES`, `writers.py:35`), `capabilities.json`.

## 3. Skill identity today: what a "skill name" is

Authoritative definition, `skills.py:42-50`:

```python
def catalog(root: Path) -> dict[str, Path]:
    return {
        entry.name: entry
        for entry in sorted(root.iterdir())
        if (entry / SKILL_MARKER).is_file()
    }
```

- Identity = `entry.name`, the **basename** of a **direct child** of `skills/`. `SKILL_MARKER = "SKILL.md"` (`skills.py:39`) is both the "is a skill" predicate and the harness contract.
- One-level `iterdir()`: `skills/tm/code-review/SKILL.md` would be invisible (the intermediate `tm/` has no SKILL.md and is never descended into).
- The SKILL.md frontmatter `name:` field exists in bodies (tests write it, `tests/generate_support.py:40-47`) but the **generator never reads it**; `_skill_frontmatter` (`capabilities.py:122`) extracts only `requires_capability`. There is no check that frontmatter name matches the basename.
- **The two planes already diverge in the live catalog.** A frontmatter scan of all 36 skill bodies finds exactly one mismatch: `skills/codebase-map/SKILL.md:2` declares `name: map` while the directory (and the manifest reference, `runtimes/codebase-mapper/runtime.toml:8` `required = ["codebase-map"]`) is `codebase-map`. So the repo/manifest/audit identity plane (basename) and the harness invocation-name plane (frontmatter `name:`) are distinct today, unvalidated against each other, and provably divergent. Any hierarchical-ID design must decide which plane the new ID lives on.
- The spec anticipates frontmatter growth: `docs/specs/2026-06-17-launcher-home-spec.md` §4 declares the SKILL.md frontmatter schema **additive** ("skill loaders and generate.py's catalog ignore unknown keys"), and reserves a future `harness` pin key. An authored `id:` (or hierarchical `name:`) key can therefore be added to frontmatter without breaking any current loader.
- Manifest references are opaque strings validated only by dict membership: `resolve_skills` -> `string_list` -> later `name in owned` (`skills.py:92`, `capabilities.py:186`). Nothing forbids a `/` in a manifest skill name today; it would fail downstream as `unknown skill` because the catalog can never produce a slashed key.

## 4. Inventory: every place that assumes a flat basename

Skill-identity sites, ordered by pipeline position:

| # | Symbol | Location | Flat assumption |
|---|--------|----------|-----------------|
| 1 | `skills.catalog` | `skills.py:42-50` | single-level `root.iterdir()`; key = basename |
| 2 | `manifest.resolve_skills` + `string_list` + `dedupe` | `manifest.py:286, 205, 213` | names are opaque strings; no shape validation (permissive, not blocking) |
| 3 | `capabilities.vendor_constraint` | `capabilities.py:176-214` | `name not in catalog` membership; error text `unknown skill: ...` lists flat names; digest keyed `f"\n{name}\0"` (a hierarchy change moves every `generated_from` digest) |
| 4 | `compiler._drop_missing_optional` | `compiler.py:200-218` | `name in bodies` membership only |
| 5 | `skills.materialize` — destination | `skills.py:81-121` | `dest = skills_dir / name`: the name IS the destination path segment. A slashed name would nest via `Path` semantics but `copytree` would fail on a missing parent, and nothing creates intermediates |
| 6 | `skills.materialize` — prune loop | `skills.py:106-109` | `for entry in sorted(skills_dir.iterdir()): if entry.name in wanted` — one-level prune; nested copies would be pruned as a unit or not seen |
| 7 | `skills.materialize` — resync detection | `skills.py:112-118` | `existed = dest.is_dir()`, digest compare per top-level name |
| 8 | `audit.audit_runtime` skills section | `audit.py:115-129` | `skills_dir.iterdir()` one level; `owned.get(entry.name)` flat lookup; reason string interpolates `skills/{entry.name}` |
| 9 | `audit.GENERATED_NAMES` | `audit.py:49-62` | `"skills"` whitelisted as a single top-level entry; the internal walk is the flat one above |
| 10 | `generate.print_catalog` | `generate.py:186-191` | `for name in sorted(skills)` flat listing |
| 11 | `generate.regenerate` gate | `generate.py:257-289` | consumes `Residue.resync` from #8; inherits its flatness |
| 12 | `generate.clean_residue` | `generate.py:230` | `item.path.parent.name == "skills"` to decide "a skill copy was removed, regenerate" — literally tests the immediate parent basename; a nested skill's parent would not be `skills` |
| 13 | Env root override | `generate.py:135` | `AGENT_RUNTIMES_SKILLS` points at one flat root; not itself a blocker |
| 14 | Tests | `tests/generate_support.py:40` `write_skill(root, name)` -> `root / name` with `mkdir(parents=True)` (already hierarchy-tolerant); `tests/test_skills.py` asserts paths like `runtime_dir / "skills" / "image-skill" / "SKILL.md"` throughout |

Depth-neutral pieces (no change needed): `skills.tree_digest` (`skills.py:53-71`, rglob + relative posix paths, works at any depth), `skills.remove_path` (`skills.py:73`), `writers.materialize` (passes `plan.skills` + `plan.skill_bodies` through untouched), `RuntimePlan.skills`/`skill_bodies` (plain tuple/dict of strings/paths), grok baseline `[skills]` config cells (`baselines/config.grok.toml`; those govern the harness's *external* skill discovery, not this repo's catalog).

Non-sites worth ruling out explicitly (each confirmed by full read): `configuration.py` never touches skill names (its `MANAGED_KEYS` derive from `redaction._MECHANISM` via `self_applied_names`, `redaction.py:283`, all model/env/config keys); `redaction.py` never touches skill names — its two digests (`generated_from` from manifest bytes + required-skill frontmatter in `vendor_constraint`, and `launch_requirements_digest` from the compiled mechanism set in `requirements_digest`) are the only content-addressed identities beside the skill tree digest; `catalogs.py` is MCP-only; `render.py` already quotes non-bare table segments (`table_header`, `render.py:47-52`), so a slashed name inside a TOML table key would render correctly if one ever appeared there (none does today).

Test-suite coverage of the flat model: `test_skills.py` exercises copy-not-link, prune, resync gate, digest, executable bit, audit reasons, capability derivation — every fixture writes one-level skills (`write_skill`, `tests/generate_support.py:40`, already `mkdir(parents=True)` and thus hierarchy-tolerant), and **no test exercises a nested skill directory**; the only nesting test in the suite is for runtimes (`test_a_directory_of_nested_runtimes_is_not_an_orphan`, `test_skills.py:641`). Audit-reason strings asserted verbatim in tests (`"not a skill this repo owns"`, `"out of sync with the owned body skills/owned"`, `test_skills.py:200-207, 328-352`) would move with a rekeying.

## 5. Authored identity vs generated destination path

The repo already demonstrates the separation for **agents** and conflates it for **skills**:

- **Agents**: authored identity is `id = "tm/stu"` inside `runtime.toml` (`agent_identity`, `manifest.py:85-135`); the directory is `runtimes/tm-stu/` — a location, not an identity. Discovery is by `rglob("runtime.toml")` (`generate.py:147`, `all_runtime_dirs` `generate.py:291`), so runtime directories may nest arbitrarily (`audit_orphans` explicitly accounts for nested runtimes, `audit.py:150-168`; test `test_a_directory_of_nested_runtimes_is_not_an_orphan`). Uniqueness is enforced on the authored id and on `fixed_name`, never on the directory name (`validate_catalog_identities`, `manifest.py:161`).
- **Skills**: authored identity does not exist. Basename = catalog key = manifest reference = capability lookup key = audit key = destination segment `<home>/skills/<basename>`. The unread frontmatter `name:` is the natural authored-identity slot but currently is decoration.

The destination side has a hard external constraint: the three harnesses discover skills as `<home>/skills/<dir>/SKILL.md`. The one-level shape is the **documented contract**, not just an implementation accident: `skills/skill-matters/SKILL.md:24-25` states "Everything is namespaced apart except `skills/`, which both read as `<home>/skills/<name>/SKILL.md`", and it is the single shared surface in the otherwise-disjoint claude/codex namespace table there (`SKILL.md:16-22`; same claim in `generate.py:9-11`). Whatever a hierarchical ID looks like, the **generated** destination layout is a harness contract. So an authored ID like `tm/code-review` must map to a destination the harnesses accept — either a nested `skills/tm/code-review/` if the harness walks recursively (unproven; documentation says one level; a live probe via `codex debug prompt-input` / `grok inspect` is required per the repo's prove-it rule) or a flattened segment (`tm--code-review` style), keeping ID and path formally distinct. Note grok adds a further wrinkle: its `[skills] ignore` matching in `baselines/config.grok.toml` matches resolved paths (AGENTS.md, grok gap notes), so a nested layout would need re-measuring against `grok inspect`.

## 6. Reuse map for adding hierarchical skill IDs

Existing machinery to reuse rather than rebuild:

| Need | Reuse | Where |
|------|-------|-------|
| ID grammar | `_AGENT_ID_COMPONENT` / `_AGENT_ID_PATTERN` (lowercase, digit, hyphen components, slash-separated) | `manifest.py:36-37` — lift to a shared pattern; agent ids and skill ids would share component grammar |
| Namespace/owner semantics | `agent_identity`'s owner extraction + kind/namespace rules (`tm/` platform, `user/` user) | `manifest.py:96-107` |
| Catalog-wide uniqueness | `validate_catalog_identities` shape (id -> path dict, duplicate = SystemExit with both paths) | `manifest.py:161-183` |
| Recursive discovery by marker | the runtime pattern `root.rglob("runtime.toml")` transplanted as `skill_root.rglob("SKILL.md")` with key = `parent.relative_to(root).as_posix()` | `generate.py:147`, `audit.py:150` |
| Authored-vs-location split | frontmatter `name:`/`id:` as authored identity with a basename fallback, mirroring how `runtimes/tm-stu` carries `id = "tm/stu"` | `_skill_frontmatter` already parses frontmatter and is the single extension point (`capabilities.py:122`); tests already write `name:` |
| Content integrity at any depth | `tree_digest` unchanged | `skills.py:53` |
| Env-scoped test roots | `AGENT_RUNTIMES_SKILLS` + `install_skill_root` / `write_skill` (already `mkdir(parents=True)`) | `generate.py:135`, `tests/generate_support.py:40,78` |

Edits required (the flat sites from §4 that actually break):

1. `skills.catalog` — recursive walk; decide the key (relative posix path vs authored frontmatter id) once, here; every downstream membership check (`vendor_constraint`, `_drop_missing_optional`, `materialize`) follows for free because they are dict lookups on whatever `catalog` returns.
2. `skills.materialize` — create parent dirs for nested dests; rewrite the prune to walk materialized SKILL.md dirs (rglob) and prune by relative path, plus remove empty intermediate dirs.
3. `audit.audit_runtime` — mirror the same rglob walk; keep the `resync` distinction; intermediate dirs must not be flagged as residue.
4. `generate.clean_residue` — replace `item.path.parent.name == "skills"` with an is-under-skills test (`"skills" in item.path.relative_to(runtime_dir).parts` or equivalent).
5. `vendor_constraint` digest — keys change, so every home's `generated_from` moves; transport-matters pins that digest (`capabilities.json` is a published contract, AGENTS.md), so the bump is a consumer-visible event even though `schema_version` need not change for additive keys.
6. Decide destination mapping (nested vs flattened) against measured harness discovery behavior before committing to either; nothing in this repo proves harnesses walk `skills/` recursively.

## 7. Validation surfaces (for completeness)

- Manifest: `schema_version == 3` fatal; id pattern; kind in `("platform","specialist","user")`; namespace rules; one-line name/description; `[launch]` key whitelist; `canonical_run_name` (2-32 ASCII, not UUID-shaped, not a control word, `manifest.py:138-159`).
- Harness targeting: `resolve_harnesses` unknown-name fatal; `validate_harness_tables` rejects `[settings.<h>]`/`[mcp.<h>]` aimed at an undeclared harness (`manifest.py:218-244`).
- Config layering: `configuration.compose` merges `baseline -> computed -> [settings.<h>] -> compiled (model/effort/redactions) -> mcp`; `MANAGED_KEYS` rejection (`configuration.py:52-66, 141`); arrays of tables fatal with path.
- Models: exact-row + observed-tier validation (`models.py:71-113`); effort ban list then per-row narrowing.
- Capabilities: registry vendors must be among `VENDORS`; unknown capability per skill fatal; mutually exclusive vendor demand fatal (`capabilities.py:196-208`).
- Post-generation: `--audit` (residue), the `--force` resync gate in `regenerate` (`generate.py:257`), and the suite `python3 bin/generate.py --all && --audit && python3 -m pytest tests -q`.

## 8. Open questions

- Do claude/codex/grok discover `skills/**/SKILL.md` recursively, or only one level under `skills/`? The repo's own docs state one level (`skills/skill-matters/SKILL.md:24-25`); decisive for the destination mapping; needs `codex debug prompt-input` and `grok inspect` against a hand-nested home (out of scope for this read-only pass).
- Should the frontmatter `name:` become authoritative (and validated against location), or should the relative path be the ID with frontmatter unread as today? The agent-identity precedent argues for authored-in-file identity with location free to move — and the live `codebase-map` dir / `name: map` divergence shows the question is not hypothetical. The spec's additive-frontmatter rule (`docs/specs/2026-06-17-launcher-home-spec.md` §4) makes an authored `id:` key backward-compatible.
- Which plane do harnesses key skill *invocation* on — directory name or frontmatter `name:`? The `map` mismatch means these can disagree in a live home today; a hierarchical scheme should either close the gap with validation or explicitly own both planes.
- `generated_from` digest churn on rekeying: coordinate with transport-matters before landing, since it pins the digest (published in `capabilities.json`, e.g. `runtimes/generalist/capabilities.json` `generated_from`). The separate `launch_requirements_digest` is unaffected (it hashes only compiled mechanism, `redaction.py:requirements_digest`).
- Repo shape lesson to respect (`LESSONS.md`, "Match the established shape before optimizing for DRY"): a skill ID grammar should mirror the agent ID grammar (`_AGENT_ID_COMPONENT`) rather than inventing a second component shape in the same catalog.

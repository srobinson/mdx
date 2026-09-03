---
title: Skill hierarchy design (candidate Grok)
type: design
tags: [agent-runtimes, skills, hierarchy, identity, path-derived]
summary: Path-derived owner/domain/name identities, flat generated homes, first-class publisher and domain selectors. Authored catalog key is the relative body path; destination segment is the leaf; frontmatter name is checked against the leaf and is never an identity plane.
status: active
source: grok-bakeoff
chosen_shape: path-derived owner/domain/name identities
head: 71e3871ebbb8813fb213827f70e38fc4d83feafa
status: active
created: 2026-09-03
updated: 2026-09-03
---

# Skill hierarchy for agent-runtimes

Chosen shape: **path-derived `owner/domain/name` identities**.

The generated home stays one flat level of `<home>/skills/<leaf>/SKILL.md`. Hierarchy lives only in the authored catalog. A skill's identity is its path under `skills/`. Publisher and domain selectors query that catalog; they do not invent a second membership list.

## Proven facts

These are readings, probes, and vendor docs from the grounding pack, rechecked against live files at HEAD `71e3871ebbb8813fb213827f70e38fc4d83feafa`. They are constraints, not choices.

1. `skills.catalog()` is a one-level `iterdir()` keyed by basename. A nested `SKILL.md` is invisible. Confirmed in `bin/agent_runtime_compiler/skills.py`.
2. Runtime discovery already uses `rglob("runtime.toml")`. Nested runtime directories work; nested skill directories do not.
3. Agent identity is authored (`id = "tm/frontend"`), two `_AGENT_ID_COMPONENT`s, unique across the catalog via `validate_catalog_identities`. The runtime directory is a location.
4. Skill identity is not authored. Basename is simultaneously the manifest key, the digest key, the audit key, and the destination segment.
5. The generator reads only `requires_capability` from frontmatter. It never reads `name`.
6. Live divergence: directory `skills/codebase-map/`, manifest `required = ["codebase-map"]`, frontmatter `name: map`. The other 35 bodies have matching directory and frontmatter `name`. Nothing enforces that.
7. Generated destination must stay one flat level for a portable home. Codex 0.153.0 and Grok 1.0.13 discover nested markers; Claude Code docs, validator, and loader text describe one-level `<home>/skills/<name>/SKILL.md`. Nested output therefore splits the skill set by harness from identical bytes.
8. A marked grouping directory copied whole leaks undeclared nested markers to Codex and Grok, unconstrained by `vendor_constraint`. A slashed catalog key passed to today's copier writes nested output, the audit flags the grouping parent as unowned, and the next prune deletes it. Partial moves thrash.
9. Flattening creates two collision classes the current code never sees: two paths sharing a destination segment, and two bodies sharing a frontmatter `name`. Codex keeps duplicate names visible and unmerged.
10. `generated_from` hashes manifest bytes plus each required skill's name and frontmatter. Rekeying moves every home digest. `launch_requirements_digest` is untouched. `capabilities.json` is additive for new keys; a `schema_version` bump means a consumer must change.
11. Only required skills feed `vendor_constraint`. Optional skills never drop a harness.
12. Audit walks immediate `skills/` children, compares `tree_digest` to the owned body, and treats a mismatch as `resync`. `clean_residue` tests `item.path.parent.name == "skills"`. `tree_digest` and `remove_path` are already depth-neutral. `tests/generate_support.write_skill` already does `mkdir(parents=True)`.
13. Generation must not read `$HOME` for skill content.
14. Manifest `schema_version` is currently 3 and must equal 3. `[skills]` accepts `required` and `optional` lists of opaque strings; unknown keys in that table are ignored.
15. 36 owned bodies, 10 manifests, 96 tests passing at the grounding snapshot. Working tree is dirty on `runtimes/generalist/runtime.toml`, `runtimes/tm-stu/runtime.toml`, `skills/tm-orchestrate/SKILL.md`. Regeneration of a dirty copy demands `--force`.

Working assumptions, evidence-backed, unproven: Claude nested prompt inclusion (docs and validator, no offline renderer; probed on 2.1.258, installed 2.1.259); Grok `[disabled]` meaning absent from the prompt.

## Design choices

1. Identity is the relative posix path of the directory that contains `SKILL.md`. Always three components: `owner/domain/name`. Same component grammar as agent ids.
2. Generated destination segment is the third component. Claude's command, the directory the copier writes, and the frontmatter `name` are that leaf. The generator checks the frontmatter field; it does not take identity from it.
3. Bulk curation is first-class `[skills.publishers]` and `[skills.domains]` tables. Exact ids stay in `[skills].required` / `[skills].optional`. A 1-component or 2-component string in those lists is an error, not a glob.
4. Optional exact ids demote a skill that a publisher or domain marked required. That is how a large domain stays mostly required while a few leaves stay optional.
5. Registry entries are `Skill` values (id, body). Destination segment is derived (`id.name`). `RuntimePlan` stops carrying a parallel name list and body map.
6. Manifest `schema_version` becomes 4. Flat skill names fail closed. `capabilities.json` `schema_version` stays 3. No new key is added to that document in this wave, because an `extra=forbid` consumer has already outaged on additive keys. Digest *values* move; the field set does not.
7. `codebase-map` keeps its leaf. Frontmatter `name` becomes `codebase-map`. Codex and Grok invocation follow the leaf; Claude is unchanged.
8. Marker-under-marker is a catalog error. Every discovered `SKILL.md` is a catalog citizen or the generate fails before writes.

# Usage (caller's view)

## Proposed skills tree

Grouping directories have no `SKILL.md`. Each leaf directory is one body. Identity is the path shown.

```
skills/
  tm/
    platform/
      skill-matters/SKILL.md
      tm-orchestrate/SKILL.md
    transcript/
      transcript-search/SKILL.md
  helioy/
    design/
      frontend-design/  impeccable/  critique/  audit/
      web-design-guidelines/  polish/  extract/  normalize/
      confident-ai-design/  clarify/  onboard/
    verb/
      adapt/  animate/  bolder/  colorize/  delight/  distill/
      harden/  optimize/  quieter/  teach-impeccable/
    content/
      blog-architect/  copywriting/  my-voice/
    visual/
      excalidraw-diagram/  helioy-imagegen/  helioy-imagegen-primatives/
    review/
      code-review/  pull-request/
    nav/
      codebase-map/          # frontmatter name becomes codebase-map
    catalog/
      find-skills/  snapshot/
  anthropic/
    authoring/
      skill-creator/SKILL.md
```

36 leaves. Domain names are catalog organization; they can move, and a move is a rekey. The invariant is the three-component path, not this particular grouping.

`helioy/design` is the always-on frontend suite. `helioy/verb` is the situational transform set the frontend manifest already comments as optional. That split is what lets one runtime select twenty-one related bodies without listing them.

## One skill

Today:

```toml
schema_version = 3
id = "tm/codebase-mapper"

[skills]
required = ["codebase-map"]
```

After:

```toml
schema_version = 4
id = "tm/codebase-mapper"

[skills]
required = ["helioy/nav/codebase-map"]
```

Resulting home (unchanged shape, new audit identity):

```
runtimes/codebase-mapper/
  runtime.toml
  skills/
    codebase-map/SKILL.md     # dest segment = leaf
  AGENTS.md
  CLAUDE.md
  settings.json
  config.toml
  config.grok.toml
  capabilities.json           # generated_from moved; key set unchanged
```

Claude command `/codebase-map`. Codex `$codebase-map`. Grok `/codebase-map`. The live `/map` (Codex, Grok) and `/codebase-map` (Claude) split is closed by correcting frontmatter, not by a dest alias table.

## A domain set, with one exact add and a demotion pattern

Today `tm/frontend` lists twelve required names and ten optional names.

After:

```toml
schema_version = 4
id = "tm/frontend"
name = "Frontend specialist"
description = "Frontend design and UX runtime: the impeccable design suite."
kind = "specialist"

[skills]
required = ["helioy/content/copywriting"]

[skills.domains]
required = ["helioy/design"]
optional = ["helioy/verb"]

[mcp]
cm = true
fmm = true
```

Expansion at plan time, against the catalog, sorted by id inside each selector, then exact ids in author order:

**Required (12):** eleven `helioy/design/*` leaves plus `helioy/content/copywriting`.

**Optional (10):** every `helioy/verb/*` leaf. None of those ids sit in required, so no demotion fires.

Generated home, still flat:

```
runtimes/frontend/skills/
  audit/  clarify/  confident-ai-design/  copywriting/  critique/
  extract/  frontend-design/  impeccable/  normalize/  onboard/
  polish/  web-design-guidelines/
  adapt/  animate/  bolder/  colorize/  delight/  distill/
  harden/  optimize/  quieter/  teach-impeccable/
```

Twenty-two immediate children. Same portable contract as today. Adding `helioy/design/typeset` later is a catalog edit: the next generate of `tm/frontend` copies it, and `generated_from` moves because the resolved required set changed. That is the bulk contract. It is not a glob in the skill list.

## A publisher set

A kitchen-sink home that wants every anthropic-owned body, plus one tm skill:

```toml
schema_version = 4
id = "tm/skill-matters"

[skills]
required = ["tm/platform/skill-matters"]
optional = ["helioy/catalog/find-skills"]

[skills.publishers]
required = ["anthropic"]
```

Resolves required to `anthropic/authoring/skill-creator` and `tm/platform/skill-matters`. The publisher selector cannot appear in `[skills].required`; a string `"anthropic"` there fails as "skill id must be owner/domain/name".

## Demotion

A domain is required, one leaf of it should stay optional:

```toml
[skills]
optional = ["helioy/design/polish"]

[skills.domains]
required = ["helioy/design"]
```

`polish` is removed from the required set and kept optional. Exact optional ids win overlap. There is no separate exclude list.

## What the author never writes

- `required = ["helioy/design"]` in `[skills]` (wrong arity; use `[skills.domains]`).
- `required = ["helioy/design/*"]` (no glob syntax).
- `id:` in SKILL.md frontmatter (path is the id).
- A dest alias (`map` vs `codebase-map`) in a side table.
- A `bundle.toml` that restates the directory listing.

## Generate output the author sees

```
SKILLS (36) owned under /Users/alphab/.agent-runtimes/skills:
  anthropic/authoring/skill-creator
  helioy/catalog/find-skills
  helioy/catalog/snapshot
  helioy/content/blog-architect
  ...
  tm/transcript/transcript-search
```

```
runtime 'Frontend specialist' (tm/frontend) @ runtimes/frontend
  22 skills | claude mcp 2 | codex mcp 2 | grok mcp 2
  + skill helioy/design/impeccable
  ~ skill helioy/nav/codebase-map: resynced
```

Log lines use the catalog id. The path on disk under the home uses the leaf.

# Shape

## Core data structures

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Literal

from agent_runtime_compiler.identity import (
    parse_domain_id,
    parse_publisher_id,
    parse_skill_id,
)

SKILL_MARKER = "SKILL.md"

SelectorKind = Literal["skill", "domain", "publisher"]


@dataclass(frozen=True, slots=True)
class SkillId:
    """Canonical catalog identity. Three components, one spelling."""

    owner: str
    domain: str
    name: str

    def __str__(self) -> str:
        return f"{self.owner}/{self.domain}/{self.name}"

    @property
    def domain_id(self) -> str:
        return f"{self.owner}/{self.domain}"


@dataclass(frozen=True, slots=True)
class Skill:
    """One owned body. Destination segment is derived, never stored."""

    id: SkillId
    body: Path

    @property
    def segment(self) -> str:
        return self.id.name

    @property
    def marker(self) -> Path:
        return self.body / SKILL_MARKER


@dataclass(frozen=True, slots=True)
class Selector:
    """One authored bulk or exact reference, before expansion."""

    kind: SelectorKind
    value: str  # publisher | owner/domain | owner/domain/name


@dataclass(frozen=True, slots=True)
class SkillSelection:
    """What the manifest asked for. Unresolved. Order is author order."""

    required: tuple[Selector, ...]
    optional: tuple[Selector, ...]


@dataclass(frozen=True, slots=True)
class ResolvedSkills:
    """What the home will carry. Required is a subset of selected."""

    selected: tuple[Skill, ...]
    required: tuple[Skill, ...]


@dataclass(frozen=True, slots=True)
class SkillMeta:
    """Parsed SKILL.md frontmatter. requires_capability is the only generator input."""

    name: str | None
    requires_capability: tuple[str, ...]
    text: str


@dataclass(frozen=True, slots=True)
class SkillCatalog:
    """Validated owned set. Built once per generate invocation."""

    skills: tuple[Skill, ...]

    def __iter__(self) -> Iterator[Skill]:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError

    def get(self, skill_id: str) -> Skill:
        """Exact id lookup. Raises SystemExit listing available ids on miss."""
        raise NotImplementedError

    def by_segment(self, segment: str) -> Skill | None:
        """Destination-segment lookup for audit and prune."""
        raise NotImplementedError

    def under_publisher(self, owner: str) -> tuple[Skill, ...]:
        raise NotImplementedError

    def under_domain(self, domain_id: str) -> tuple[Skill, ...]:
        raise NotImplementedError

    def select(self, selection: SkillSelection) -> ResolvedSkills:
        """Expand selectors, demote overlaps, fail required misses before any write."""
        raise NotImplementedError
```

Invariants encoded in types:

- `SkillId` has three fields. A two-component string cannot construct one.
- `Skill.segment` is a property of `id.name`. Writers cannot pick a different dest.
- `SkillCatalog` is frozen and already validated. Downstream membership is lookup, not re-walk.
- `SkillSelection` holds selectors, `ResolvedSkills` holds bodies. The plan never stores both a name and a path for the same skill.

Deliberately absent:

- A dest field on `Skill`.
- An `id` key in frontmatter.
- A bundle manifest type.
- Glob selectors.
- A per-home dest-collision type. Collisions are catalog-wide, so a home cannot even name two skills that would clash on disk.

## Identity grammar

```python
"""Canonical id grammar for agents and skills.

Agent ids stay two components (owner/name). Skill ids are three
(owner/domain/name). Both reuse COMPONENT. Domain and publisher strings are
the prefixes of a skill id, never a second alphabet.
"""

from __future__ import annotations

import re

COMPONENT = r"[a-z](?:[a-z0-9-]{0,62}[a-z0-9])?"
_COMPONENT = re.compile(rf"^{COMPONENT}$")
_AGENT = re.compile(rf"^{COMPONENT}/{COMPONENT}$")
_DOMAIN = re.compile(rf"^{COMPONENT}/{COMPONENT}$")
_SKILL = re.compile(rf"^{COMPONENT}/{COMPONENT}/{COMPONENT}$")


def parse_publisher_id(value: str, context: str) -> str:
    raise NotImplementedError


def parse_domain_id(value: str, context: str) -> str:
    raise NotImplementedError


def parse_skill_id(value: str, context: str) -> SkillId:
    raise NotImplementedError


def parse_agent_id(value: str, context: str) -> tuple[str, str]:
    """Returns (owner, name). Replaces the inline check in agent_identity."""
    raise NotImplementedError
```

Error text distinguishes arity, so a missing key is obvious:

- 1 component in `[skills].required` → "skill id must be owner/domain/name; put publishers in [skills.publishers]"
- 2 components in `[skills].required` → "skill id must be owner/domain/name; put domains in [skills.domains]"
- 4+ components → "skill id must be owner/domain/name"
- Invalid component characters → the same message agent ids already use, with `context`

`manifest.agent_identity` calls `parse_agent_id`. It does not keep a second regex.

## Frontmatter

```python
def parse_skill_md(body: Path) -> SkillMeta:
    """Single SKILL.md parser.

    Reads `name` for the leaf check and `requires_capability` for vendor
    constraint. Unknown keys stay ignored, per the launcher-home additive rule.
    """
    raise NotImplementedError
```

This function moves out of `capabilities.py` (`_skill_frontmatter` deleted in the same wave). `vendor_constraint` and `catalog` both call it. Two parsers of the same file is the leak this closes.

Catalog rule: `meta.name == skill.id.name`. Missing `name` fails (Codex requires the field; all 36 bodies have it). Mismatch fails with both spellings and the body path.

## Catalog

```python
def catalog(root: Path) -> SkillCatalog:
    """Discover and validate every owned body under ``root``.

    Walk ``root.rglob(SKILL_MARKER)``. Each parent relative path must parse as
    a SkillId (exactly three components). A SKILL.md at any other depth fails
    with that path. Two leaves with the same SkillId.name fail with both ids.
    Two markers that would share a path cannot occur; the path is the id.

    Does not read ``$HOME``.
    """
    raise NotImplementedError
```

Walk rules, all fatal, all before any `RuntimePlan` is built:

| Finding | Error |
| --- | --- |
| `SKILL.md` at 1 or 2 components (`skills/helioy/SKILL.md`) | grouping directory is not a skill; path cited |
| `SKILL.md` at 4+ components | skill bodies cannot nest; path cited |
| relative path fails `COMPONENT` | same grammar error as agent ids |
| two leaves, one `name` | `duplicate destination segment {name!r}: {id_a} and {id_b}` |
| frontmatter `name` missing or ≠ leaf | `frontmatter name {got!r} must equal destination segment {leaf!r} ({id} at {path})` |
| `root` missing | empty catalog, `{}` equivalent; required refs fail later |

Empty grouping directories are fine. A README beside a grouping directory is fine. `tree_digest` continues to hash the leaf body only, never a grouping parent.

## Selection

```python
def parse_skill_selection(value: Any) -> tuple[SkillSelection, list[str]]:
    """Manifest [skills] table -> selectors.

    Allowed keys: required, optional, domains, publishers.
    domains and publishers are tables of required/optional string lists.
    Unknown keys fail. The deprecated bare array still means required exact
    ids and still logs SKILLS_ARRAY_DEPRECATION_NOTICE.
    """
    raise NotImplementedError


def _expand(catalog: SkillCatalog, selector: Selector) -> tuple[Skill, ...]:
    raise NotImplementedError
```

`SkillCatalog.select` algorithm:

1. Expand `selection.required` in author order. Publisher and domain expansions emit catalog citizens sorted by `str(id)`. Exact ids append in author order. First occurrence wins inside the required list.
2. Unknown required exact id: `unknown skill`. Required publisher or domain matching zero citizens: `required {kind} {value!r} matches no skill`.
3. Expand `selection.optional` the same way. Unknown optional exact id: skip and log (today's `_drop_missing_optional`). Optional publisher or domain matching zero: skip and log.
4. Demote: any skill sitting in both sets leaves required and stays optional.
5. Return `ResolvedSkills(selected=required_then_optional, required=required)`.

`compiler._drop_missing_optional` is deleted. Optional misses are resolved here, next to required misses.

## Materialize, audit, clean

```python
def materialize(runtime_dir: Path, selected: tuple[Skill, ...]) -> list[str]:
    """Copy each selected body to ``skills/<segment>/``; prune other immediate children.

    ``wanted`` is the set of segments, not ids. dest = skills_dir / skill.segment.
    Digest compare, whole-tree replace, and the add vs resync log line stay.
    Log lines name ``skill.id``. Bare homes with no selected skills still skip
    creating an empty ``skills/``.
    """
    raise NotImplementedError
```

```python
def audit_runtime(
    runtime_dir: Path, tracked: set[str], owned: SkillCatalog
) -> list[Residue]:
    """Unchanged residue model. Skills walk stays one-level on the home.

    ``owned.by_segment(entry.name)`` replaces ``owned.get(entry.name)``.
    Reason for drift names the catalog id:
    ``out of sync with the owned body skills/{id}``.
    A dest that is not a known segment stays ``not a skill this repo owns``.
    Extra copies of owned segments this home did not select stay invisible to
    audit (materialize prunes them); that is today's behaviour.
    """
    raise NotImplementedError
```

`clean_residue`'s `item.path.parent.name == "skills"` test remains correct because dest is still an immediate child of `skills/`. Do not walk into grouping parents on the generated side; there are none.

`--force` resync gate is unchanged: any `Residue.resync` across the requested set aborts the whole set.

## Plan and capabilities

```python
@dataclass(frozen=True, slots=True)
class RuntimePlan:
    runtime_dir: Path
    identity: AgentIdentity
    harnesses: tuple[str, ...]
    skills: tuple[Skill, ...]          # selected, required then optional
    required_skills: tuple[Skill, ...]
    instructions: bool
    claude: ClaudeSurface | None
    codex: CodexSurface | None
    grok: GrokSurface | None
    capabilities: dict[str, Any]
    mcp_names: dict[str, tuple[str, ...]]
    logs: tuple[str, ...]
    # skill_bodies deleted
```

```python
def vendor_constraint(
    runtime_dir: Path, required: tuple[Skill, ...]
) -> VendorConstraint:
    """Same intersection. Digest keys ``str(skill.id)`` in required order.

    Missing names cannot reach here; select() already failed them.
    """
    raise NotImplementedError
```

```python
def plan(...) -> RuntimePlan:
    identity = agent_identity(manifest)
    selection, skill_logs = parse_skill_selection(manifest.get("skills", {}))
    owned = catalog(skill_root)
    resolved = owned.select(selection)
    constraint = vendor_constraint(runtime_dir, resolved.required)
    ...
```

`writers.materialize` calls `materialize_skills(home, plan.skills)` and does not mention segments.

`generated_from` input, in order: manifest bytes; for each required `Skill`, `f"\n{skill.id}\0"` plus that body's frontmatter text. Optional skills still do not enter the digest. A new leaf under a required domain moves the digest because it joins `resolved.required`.

## Module ownership

| Module | Owns | Does not own |
| --- | --- | --- |
| `identity.py` (new) | Component grammar; parse of publisher, domain, skill, and agent ids | Catalog walk, TOML, dest mapping |
| `skills.py` | Discovery, collision, frontmatter parse, selection expansion, copy, prune, digest | Manifest schema, vendor registry, residue types |
| `manifest.py` | `runtime.toml` shape, `[skills]` key allowlist, `SkillSelection` parse, agent identity | Expansion against the catalog |
| `compiler.py` | Ordering: identity → selection → catalog → resolve → vendor constraint → freeze | Skill policy |
| `capabilities.py` | Capability registry, vendor intersection, `capabilities.json` projection | SKILL.md parsing |
| `audit.py` | Residue model, one-level home walk, orphans | Catalog construction (calls `catalog()`) |
| `writers.py` | Home convergence | Any dest rule |
| `generate.py` | CLI, `--force` gate, `--catalog` listing of `str(id)` | Skill grammar |

Screen:

- **Shallow module.** `identity.py` hides the arity rules and the error text behind four parse functions. `SkillCatalog.select` hides expansion, demotion, and miss handling behind one call. Callers do not orchestrate those steps.
- **Information leakage.** Dest segment is not restated on the plan, in the manifest, or in frontmatter-as-identity. Frontmatter `name` is a checked projection of `id.name`. `capabilities.py` no longer has its own YAML walk.
- **Temporal decomposition.** Catalog build validates. There is no `validate.py` that re-walks the same tree. Select is catalog policy, not a compiler stage object.
- **Pass-through.** `writers.materialize` does not adapt names to skills; the plan already holds `Skill` values. `compiler.plan` does not wrap `select` in a same-shaped helper.

## Compilation flow

```
runtime.toml
    |
    v
manifest.agent_identity          # schema_version == 4; agent id unchanged
manifest.parse_skill_selection   # exact / domain / publisher selectors
    |
    +--> skills.catalog(skills/) --> SkillCatalog
    |         rglob SKILL.md
    |         arity, leaf uniqueness, frontmatter name == leaf
    |
    +--> catalog.select(selection) --> ResolvedSkills
    |
    +--> capabilities.vendor_constraint(required Skills)
    |         digest: manifest bytes + str(id) + frontmatter
    |
    v
compiler.plan -> RuntimePlan.skills: tuple[Skill, ...]
    |
    v
writers.materialize
    |
    +--> skills.materialize -> <home>/skills/<leaf>/   (flat, shared)
    +--> instructions, configs, prune untargeted, capabilities.json
    |
    v
audit / --force / --clean
    one-level home walk keyed by segment, reasons keyed by id
```

`catalogs.discover` remains the only `$HOME` read.

## Collision rules

All of these fail with both paths (or both ids), before any home is touched, same shape as `validate_catalog_identities`.

| Class | When | Why |
| --- | --- | --- |
| Duplicate destination segment | Two leaves share `SkillId.name` | Claude commands, Codex/Grok selectors, and dest paths would collide. Catalog-wide because Grok isolation is incomplete on a real HOME; unique leaves are the fleet-wide namespace. |
| Frontmatter `name` ≠ leaf | Any body | Closes the `codebase-map`/`map` class. Frontmatter is the Codex/Grok invocation plane; dest is the Claude command plane; they are forced equal. |
| Marker under marker | `SKILL.md` not at exactly three components | Prevents the grouping-leak shape (marked parent copies an undeclared child). |
| Duplicate manifest exact id | `dedupe` already drops repeats; harmless | First occurrence wins, same as today. |
| Exact id unknown (required) | Select time | `unknown skill`, available list is catalog ids. |
| Domain/publisher required, zero matches | Select time | Fail, do not silently ship an empty set. |
| Wrong arity in `[skills].required` | Parse time | Directs the author to the bulk table. Forbids prefix-as-skill. |
| Unknown `[skills]` key | Parse time | Today unknown keys are ignored; that would hide a misspelled `domain`. |
| Duplicate agent id / fixed_name | Unchanged | `validate_catalog_identities`. |

Two collision classes the design refuses to grow:

- Path vs frontmatter `id:` (no such field).
- Bundle list vs directory listing (no bundle file).

Per-home dest clashes cannot occur once catalog-wide leaf uniqueness holds.

## Migration

One wave. The old flat path is gone when the wave lands. No dual-read of `skills/impeccable` and `skills/helioy/design/impeccable`.

### Manifest schema 4

Every `runtime.toml` sets `schema_version = 4`. A leftover 3 fails at `agent_identity` with the existing "must be N" error. That is the closed door on opaque skill strings: even if a v4 parser were lenient, v3 never reaches it.

### Body moves

`git mv` each of the 36 directories onto the tree in Usage. No content edits except:

- `skills/helioy/nav/codebase-map/SKILL.md`: `name: map` → `name: codebase-map`.
- Grep of owned bodies and `instructions/AGENTS.md` / `skills/skill-matters/SKILL.md` / `bin/generate.py` docstring for leftover flat discovery claims ("both harnesses", "`<home>/skills/<name>/SKILL.md`" as a discovery statement rather than a portable-output statement).

### Manifest rewrites

| Runtime | After |
| --- | --- |
| `tm/codebase-mapper` | `required = ["helioy/nav/codebase-map"]` |
| `tm/frontend` | exact `helioy/content/copywriting`; domain required `helioy/design`; domain optional `helioy/verb` |
| `tm/imagegen` | `required = ["helioy/visual/helioy-imagegen"]`, `optional = ["helioy/visual/helioy-imagegen-primatives"]` (not the whole visual domain: that would pull `excalidraw-diagram`) |
| `tm/generalist` | `helioy/review/code-review`, `helioy/review/pull-request`; optional `helioy/catalog/snapshot`, `tm/platform/tm-orchestrate` |
| `tm/orchestrator` | `tm/platform/tm-orchestrate` |
| `tm/research` | exact ids under content, verb, visual, catalog |
| `tm/skill-matters` | `tm/platform/skill-matters`, `anthropic/authoring/skill-creator`; optional `helioy/catalog/find-skills` |
| `tm/transcript-matters` | `tm/transcript/transcript-search`; optional `helioy/verb/distill` |
| `tm/capture`, `tm/stu` | empty `[skills]` unchanged |

### Test fixtures

`write_skill(root, name, ...)` takes a three-component `name`. Frontmatter `name:` defaults to `Path(name).name` (the leaf), not the full id. `write_manifest` emits `schema_version = 4`. Every `write_skill(..., "image-skill")` becomes `write_skill(..., "tm/test/image-skill")` or a local equivalent. Audit reason assertions that interpolate `skills/owned` become `skills/tm/test/owned`.

### Digests and transport-matters

Every home's `generated_from` changes. Land only after transport-matters is ready to accept a fleet-wide digest move. `launch_requirements_digest` stays. `capabilities.json` key set stays. Do not add a resolved-skill array in this wave.

### Operator cost

Regenerate with `--force` because every copy's path (and one body, `codebase-map` frontmatter) changed. The dirty `skills/tm-orchestrate/SKILL.md` in the current working tree is independent; it still needs an explicit `--force` for the usual reason.

After this wave, `skills/<flat>/` does not exist. `audit` of a leftover flat dest reports `not a skill this repo owns`. `--clean` deletes it. The next generate copies the new dest. That is deletion of the old path, not a compatibility shim.

# Tests

Complete verification gate. Claims about harness behaviour that this repo cannot prove stay out of the suite and are listed as probes at the end.

## Catalog

- Markerless `skills/helioy/design/` with no leaf → empty catalog.
- `skills/helioy/design/alpha/SKILL.md` → id `helioy/design/alpha`, segment `alpha`.
- `skills/team/alpha/SKILL.md` (two components) → SystemExit, path in the message.
- `skills/a/b/c/d/SKILL.md` (four) → SystemExit, bodies cannot nest.
- `skills/helioy/SKILL.md` plus `skills/helioy/design/alpha/SKILL.md` → SystemExit on the grouping marker.
- Two leaves `helioy/design/alpha` and `tm/other/alpha` → duplicate destination segment, both ids.
- Frontmatter `name: map` at leaf `codebase-map` → SystemExit, both spellings.
- Frontmatter omitted → SystemExit.
- Frontmatter `name` equals leaf, `requires_capability` still parsed.
- `AGENT_RUNTIMES_SKILLS` override still relocates the root; still no `$HOME` read (`test_generation_reads_no_skill_store_under_home` remains).

## Selection

- Exact required id materializes; missing required id fails with available ids.
- Missing optional exact id logs and skips.
- `[skills.domains] required = ["helioy/design"]` expands to every current design leaf, sorted.
- New leaf under that domain appears on the next `select` (the bulk contract).
- Required domain matching nothing fails.
- Optional domain matching nothing logs and skips.
- `"helioy/design"` in `[skills].required` fails with the domains-table hint.
- `"helioy/design/*"` fails grammar.
- Publisher required `anthropic` expands to `anthropic/authoring/skill-creator`.
- Optional exact id demotes a domain-required skill; dest still written; `vendor_constraint` does not see it.
- Unknown `[skills]` key fails.
- Deprecated bare array of three-component ids still works and still logs.
- `schema_version = 3` fails before skill parse.

## Materialize / audit / clean

- Dest is `home/skills/<leaf>/`, never `home/skills/helioy/design/<leaf>/`.
- Two selected skills copy two immediate children; grouping parents are not created.
- Digest match leaves mtime; digest mismatch resyncs; log uses the id.
- Unwanted immediate child pruned; log uses the dest name (what was on disk).
- Audit `resync` reason contains `skills/{id}`.
- Audit unknown dest (`skills/.system`) unchanged.
- `--force` gate still aborts the whole set on any resync.
- `clean_residue` after deleting a dest child still prints "a skill copy was removed".
- Nested *runtime* directories remain non-orphans (existing test).
- Passing a slashed id into materialize does not nest: there is no string path join on the id.

## Capabilities

- Required `helioy/visual/helioy-imagegen` with `requires_capability` still drops claude.
- Optional capability-requiring skill still does not drop claude.
- Nested marker cannot contribute capabilities because it cannot enter the catalog.
- `generated_from` changes when a required id is rekeyed; `launch_requirements_digest` does not.
- `generated_from` changes when a new leaf appears under a required domain.
- `capabilities.json` key set is unchanged (schema_version 3, no new keys).

## Fixtures and CLI

- `write_skill(root, "helioy/design/alpha")` writes frontmatter `name: alpha`.
- `python3 bin/generate.py --catalog` prints three-component ids.
- `--all && --audit` after the move is clean, given `--force` for the path change.
- `python3 -m pytest tests -q` is the unit gate.

## Probes at design-verification time (not unit tests)

Re-run cheaply against installed binaries, as the grounding pack did:

- `codex debug prompt-input` on a generated home: only immediate `skills/<leaf>/SKILL.md` entries, no nested path.
- `grok inspect` on a generated home: same.
- `claude plugin validate --strict` on the home `skills/` tree: immediate children accepted.

These prove the portable dest. They do not prove Claude nested prompt inclusion, which this design does not rely on.

# Rationale

## Problem

The fleet wants owner/domain/skill structure in the authored catalog so a runtime can name a set instead of twenty leaves, and so two owners can publish the same leaf name without silently sharing a directory. The three harnesses do not share a discovery rule: Codex and Grok recurse, Claude on all current evidence does not. Today's generator collapses identity, dest, and invocation into one basename, and the live `codebase-map`/`map` split shows those planes are already distinct. A hierarchy that writes nested homes, or that copies identity into a second document, fights the copier, the audit, and rubric 3.

## Usage (caller's view)

An author lays bodies out at `skills/<owner>/<domain>/<name>/`, lists three-component ids for one-off skills, and lists publishers or domains when the set is the point. The home they get is the home they get today: flat `skills/<name>/`. See the examples above; the types below exist to make those examples the only legal ones.

## Shape

Path-derived identity, three components, dest = leaf, frontmatter `name` checked equal to the leaf, bulk as first-class selector tables expanded against the catalog. The public surface is small: path grammar plus two optional tables. Complexity sits in `SkillCatalog` (walk, collide, expand, demote).

Interface depth: the author learns one id spelling and where to put a prefix (exact list vs domain table vs publisher table). They do not learn dest mapping, digest keying, or prune rules. A richer selector language (globs, exclude lists, bundle files) would expose more of the catalog's internals in `runtime.toml`.

## Synthesis decision

Compared three whole shapes.

**Path-derived ids (chosen).** Identity is a location, which is how skills already work, extended from one component to three. Discovery transplants the runtime `rglob` pattern. No new frontmatter identity key, so the generator keeps its "frontmatter is a harness contract plus `requires_capability`" stance. No membership file to drift from the tree. Dest mapping is a total function (`name`). Bulk is a query.

**Explicit per-skill metadata (`id:` in SKILL.md).** Mirrors agent identity: the file carries the id, the directory is free to move. Loses on rubric 3 as soon as authors also nest by owner/domain, because they will keep path and `id:` in sync by hand. If they do not nest, rubric 1's owner/domain/skill is invisible in the tree git shows. Frontmatter `name` is already a vendor field with divergent semantics; adding `id:` next to it grows a third plane the generator must validate against the other two. Location-free moves are a real benefit for agents because `runtime.toml` exists to hold identity. Skills have no such file; SKILL.md is the harness document.

**Publisher bundle manifests (`skills/helioy/design/bundle.toml` or a plugin.json-style allowlist).** Directly copies REFS's promoted-set mechanism. Membership then lives in two places: the file list and the tree. REFS needs that because it ships a subset of a larger library (promoted vs in-progress vs deprecated). This repo owns every body and already subsets per home via `[skills]`. A bundle file would restates the directory, fight rubric 3, and still need a per-skill identity rule for the leaves it lists. Bulk curation is the one thing it does well; first-class domain selectors do that as a query over the catalog, which is a single source.

Rejected hybrids: dest = frontmatter `name` allowing `map` vs `codebase-map` (second source for dest); nested generated homes (rubric 2, probe-proven prune thrash); changing only `catalog()` to slashed keys (same thrash); globs in `[skills].required` (rubric 5).

## Tradeoffs accepted

- We accept rekeying on `git mv` in exchange for a single identity plane. Moving `helioy/design/polish` to `helioy/verb/polish` is a breaking catalog change, same as renaming a Python package.
- We accept catalog-wide unique leaves in exchange for a dest function with no per-home collision pass. `user/design/impeccable` cannot land next to `helioy/design/impeccable` until one leaf is renamed. Grok's leaky HOME makes that uniqueness load-bearing, not premature.
- We accept a Codex/Grok invocation change on one skill (`map` → `codebase-map`) in exchange for deleting the alias class.
- We accept `schema_version = 4` on every manifest in exchange for fail-closed migration, rather than reading both flat and hierarchical names.
- We accept that adding a leaf under a selected domain grows homes on the next generate, in exchange for manifests that name sets. The change is visible: catalog listing, generate logs, digest movement. We refuse glob syntax that would hide the same behaviour inside a string.
- We accept not publishing resolved skill ids in `capabilities.json` this wave, in exchange for not depending on consumers ignoring unknown keys. Inspectability is `--catalog`, generate logs, and the home tree.
- We accept a design/verb domain split fitted to `tm/frontend`'s required vs optional cut, in exchange for a two-line bulk manifest. Other runtimes keep exact ids. Domain names are not a locked ontology.

## Alternatives considered

- **Two-component skill ids (`helioy/impeccable`).** Smaller grammar, matches agents. Loses a structured prefix for bulk design-suite selection; `helioy` as publisher dumps visual, review, and content onto frontend. Rejected: rubric 1 asks for owner/domain/skill, and the motivating manifest needs the middle axis.
- **Dest = flattened id (`helioy-design-impeccable`).** Collision-free dest without unique leaves. Changes every Claude command and every Codex/Grok invocation. Rejected: the portable dest already has a working namespace (unique leaves today); uniqueness remains the cheaper invariant.
- **Per-home dest uniqueness only.** Deeper flexibility (two impeccables in the catalog, never in one home). Exposes dest policy to `select` and to every runtime. Rejected: worse interface depth; Grok leak makes catalog-wide uniqueness the safer fleet rule.
- **Exclude lists beside domain selectors.** Would let frontend keep one design domain and carve out optionals without a verb domain. Copies names that already sit in `[skills].optional`. Demotion by optional exact id is the same power with no new key.

## Open questions and risks

- Is the design/verb split the taxonomy we want, or should `tm/frontend` keep listing optional verbs as exact ids under a single `helioy/design` domain? The types do not care; only the migration table does.
- When should transport-matters take the fleet digest move? This wave should not land ahead of that.
- Should a later additive `capabilities.json` key list resolved ids once TM's parser is known to ignore unknowns? Out of this wave.
- Re-probe Claude 2.1.259 nested discovery before implementation sign-off. This design does not depend on the answer staying "one-level", but a reversal would be news.

## Next implementation step

Add `identity.py` and change `skills.catalog` to return a validated `SkillCatalog` from an `rglob` walk, with tests for arity, duplicate leaves, and frontmatter mismatch, before any manifest or writer changes.

# Red-flag screen (summary)

| Flag | How this shape avoids it |
| --- | --- |
| Shallow module | `SkillCatalog.select` and `catalog()` concentrate policy; `runtime.toml` stays three lists and two optional tables |
| Information leakage | Dest is `id.name`; frontmatter `name` is checked, not sourced; one SKILL.md parser |
| Temporal decomposition | Validation lives in the catalog walk, not a later stage with a copied tree model |
| Pass-through method | Plan holds `Skill` values; writers do not translate names to paths |

# Completeness checklist

- Caller usage with tree, one-skill manifest, domain/publisher manifests, resulting flat home
- Core types and signatures with not-implemented bodies
- Module ownership
- Compilation flow
- Collision rules
- Migration that deletes the flat path in one wave, with a named verification gate
- Tests covering catalog, select, materialize, audit, clean, capabilities, digest, CLI
- Proven facts separated from design choices
- Comparison of path-derived ids, per-skill metadata, and publisher bundles
- Rubric: (1) `owner/domain/name` path identity (2) flat dest, collisions fail pre-write (3) path is the only membership source (4) vendor_constraint, digest, audit, clean, resync updated in the same wave (5) exact vs domain vs publisher keys, no globs (6) schema 4 + git mv + `--force` regenerate + pytest + `--audit`

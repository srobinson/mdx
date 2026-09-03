---
title: Path owned skill catalog with explicit publisher bundles
type: design
tags: [agent-runtimes, skills, hierarchy, compiler]
summary: Derive canonical skill IDs from owner/domain/skill paths, flatten generated homes by validated frontmatter name, and use explicit publisher bundles for bulk selection.
status: active
source: backend-engineer
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

# Path owned skill catalog with explicit publisher bundles

## Caller usage

### Authored tree

The committed tree carries the hierarchy. A skill ID is its directory relative to `skills/`.

```text
skills/
  helioy/
    bundles.toml
    engineering/
      code-review/
        SKILL.md
        references/
    codebase/
      codebase-map/
        SKILL.md        # frontmatter name: map
    frontend/
      adapt/
        SKILL.md        # frontmatter name: adapt
      polish/
        SKILL.md        # frontmatter name: polish
```

These paths produce the canonical IDs `helioy/engineering/code-review`, `helioy/codebase/codebase-map`, `helioy/frontend/adapt`, and `helioy/frontend/polish`.

`SKILL.md` frontmatter keeps its harness role:

```yaml
---
name: map
description: Generate or refresh a MAP.md for a codebase.
---
```

The compiler uses `name` as the flat destination segment. The example above is copied to `<home>/skills/map/`. Claude, Codex, and Grok therefore agree on the human name even though the canonical catalog ID remains `helioy/codebase/codebase-map`.

### Select one skill

Runtime manifest schema 4 accepts canonical skill IDs only.

```toml
schema_version = 4
[skills]
required = ["helioy/engineering/code-review"]
```

Omitted selection keys mean empty lists.

### Select a domain or publisher set

Bulk selection uses named bundles. A bundle is an explicit list. Directory prefixes never expand implicitly.

```toml
# skills/helioy/bundles.toml
schema_version = 1
[bundles.frontend]
members = [
  "frontend/adapt",
  "frontend/polish",
]
[bundles.all]
members = [
  "engineering/code-review",
  "codebase/codebase-map",
  "frontend/adapt",
  "frontend/polish",
]
```

The file location supplies the publisher. `bundles.frontend` has ID `helioy/frontend`; `bundles.all` has ID `helioy/all`. Member IDs are relative to that publisher, so the file does not repeat `helioy` on every line.

```toml
schema_version = 4
[skills]
required_bundles = ["helioy/frontend"]
```

Adding `skills/helioy/frontend/animate/SKILL.md` does not alter the bundle. The runtime gains that skill only after `frontend/animate` is added to `bundles.frontend`.

### Resulting generated home

The exact skill example produces:

```text
runtimes/generalist/
  runtime.toml
  capabilities.json
  skills/
    code-review/
      SKILL.md
      references/
```

The bundle example produces:

```text
runtimes/frontend/
  runtime.toml
  capabilities.json
  skills/
    adapt/
      SKILL.md
    polish/
      SKILL.md
```

No owner or domain directory reaches a generated home. All three harnesses receive the same flat tree.

## Contract

The design assigns one source to each concept.

| Concept | Source of truth | Example |
| --- | --- | --- |
| Canonical skill identity | Relative body path | `helioy/codebase/codebase-map` |
| Publisher | First ID component | `helioy` |
| Domain | Second ID component | `codebase` |
| Skill slug | Third ID component | `codebase-map` |
| Harness name | `SKILL.md` frontmatter `name` | `map` |
| Generated destination | Harness name | `<home>/skills/map` |
| Bundle identity | Publisher path plus bundle table name | `helioy/frontend` |
| Bundle membership | `skills/<publisher>/bundles.toml` | `frontend/adapt` |
| Runtime selection | `runtime.toml` | `required_bundles = ["helioy/frontend"]` |

The path defines identity. Frontmatter defines invocation. A publisher bundle defines membership only. No file repeats the canonical skill ID as metadata.

## Core data structures and signatures

The snippets show ownership and interfaces. Bodies remain unimplemented.

### `bin/agent_runtime_compiler/identity.py`

This is the only new module. It owns the component grammar and the arity of agent, skill, and bundle IDs. `manifest.py` stops owning a private copy of the component regular expression.

```python
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Self
ID_COMPONENT_PATTERN = r"[a-z](?:[a-z0-9-]{0,62}[a-z0-9])?"
@dataclass(frozen=True, order=True, slots=True)
class SkillId:
    owner: str
    domain: str
    skill: str
    @classmethod
    def parse(cls, value: str, *, context: str) -> Self:
        raise NotImplementedError
    @classmethod
    def from_body(cls, root: Path, body: Path) -> Self:
        raise NotImplementedError
    def __str__(self) -> str:
        raise NotImplementedError
@dataclass(frozen=True, order=True, slots=True)
class BundleId:
    owner: str
    bundle: str
    @classmethod
    def parse(cls, value: str, *, context: str) -> Self:
        raise NotImplementedError
    def __str__(self) -> str:
        raise NotImplementedError
def validate_agent_id(value: str, *, context: str = "id") -> tuple[str, str]:
    raise NotImplementedError
```

`SkillId.parse` requires exactly three canonical components. `BundleId.parse` requires exactly two. `validate_agent_id` reuses the same component grammar and keeps the current two component agent contract.

### `bin/agent_runtime_compiler/manifest.py`

`manifest.py` owns only the authored runtime selection syntax.

```python
from dataclasses import dataclass
from agent_runtime_compiler.identity import BundleId, SkillId
RUNTIME_MANIFEST_SCHEMA_VERSION = 4
@dataclass(frozen=True, slots=True)
class SkillSelection:
    required: tuple[SkillId, ...]
    optional: tuple[SkillId, ...]
    required_bundles: tuple[BundleId, ...]
    optional_bundles: tuple[BundleId, ...]
def resolve_skill_selection(value: object) -> SkillSelection:
    raise NotImplementedError
```

Schema 4 accepts the four keys shown above. It rejects the old bare array, flat names, unknown keys, duplicate values within one list, and IDs with the wrong component count. This repository has no external users, so a compatibility parser would only create a second contract.

### `bin/agent_runtime_compiler/skills.py`

`skills.py` becomes the deep catalog module. It discovers bodies, parses the three fields the compiler needs, loads bundle membership, resolves selections, calculates the generation recipe digest, and copies resolved bodies. There is no separate bundle service or registry adapter.

```python
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence
from agent_runtime_compiler.identity import BundleId, SkillId
from agent_runtime_compiler.manifest import SkillSelection
@dataclass(frozen=True, slots=True)
class SkillFrontmatter:
    name: str
    description: str
    required_capabilities: tuple[str, ...]
    raw: str
@dataclass(frozen=True, slots=True)
class SkillDefinition:
    skill_id: SkillId
    body: Path
    frontmatter: SkillFrontmatter
    @property
    def destination(self) -> str:
        raise NotImplementedError
@dataclass(frozen=True, slots=True)
class SkillBundle:
    bundle_id: BundleId
    members: tuple[SkillId, ...]
    source: Path
@dataclass(frozen=True, slots=True)
class SelectedSkill:
    definition: SkillDefinition
    requirement: Literal["required", "optional"]
@dataclass(frozen=True, slots=True)
class ResolvedSkills:
    skills: tuple[SelectedSkill, ...]
    generated_from: str
    logs: tuple[str, ...]
@dataclass(frozen=True, slots=True)
class SkillCatalog:
    root: Path
    by_id: Mapping[SkillId, SkillDefinition]
    by_destination: Mapping[str, SkillDefinition]
    bundles: Mapping[BundleId, SkillBundle]
    @classmethod
    def load(cls, root: Path) -> "SkillCatalog":
        raise NotImplementedError
    def resolve(
        self,
        selection: SkillSelection,
        *,
        manifest_bytes: bytes,
    ) -> ResolvedSkills:
        raise NotImplementedError
def parse_skill_frontmatter(body: Path) -> SkillFrontmatter:
    raise NotImplementedError
def materialize(runtime_dir: Path, skills: Sequence[SelectedSkill]) -> list[str]:
    raise NotImplementedError
def tree_digest(path: Path) -> str:
    raise NotImplementedError
def remove_path(path: Path) -> None:
    raise NotImplementedError
```

`SkillDefinition.destination` returns `frontmatter.name`. The value is not stored twice.

`SkillCatalog.load` performs all catalog validation in one pass. It returns only after every ID, body, destination, frontmatter name, and bundle is valid. `SkillCatalog.resolve` performs bundle expansion, required versus optional precedence, missing optional logging, and digest calculation. Callers do not implement those rules.

### `bin/agent_runtime_compiler/capabilities.py`

Capability code consumes resolved definitions. It no longer parses frontmatter or looks up names in a catalog.

```python
from collections.abc import Sequence
from agent_runtime_compiler.skills import SelectedSkill
CAPABILITIES_SCHEMA_VERSION = 3
def vendor_constraint(skills: Sequence[SelectedSkill]) -> VendorConstraint:
    raise NotImplementedError
def derive_capabilities(
    constraint: VendorConstraint,
    recommended_model: dict[str, object],
    identity: AgentIdentity,
    harnesses: tuple[str, ...],
    redaction: dict[str, object],
    *,
    generated_from: str,
) -> dict[str, object]:
    raise NotImplementedError
```

`vendor_constraint` reads `required_capabilities` only from entries marked `required`. Optional entries preserve today's nonbinding behavior.

### `bin/agent_runtime_compiler/compiler.py`

The plan carries resolved selected skills. It does not expose the complete catalog to the writer.

```python
from dataclasses import dataclass
from agent_runtime_compiler.skills import SelectedSkill, SkillCatalog
@dataclass(frozen=True, slots=True)
class RuntimePlan:
    runtime_dir: Path
    identity: AgentIdentity
    harnesses: tuple[str, ...]
    skills: tuple[SelectedSkill, ...]
    instructions: bool
    claude: ClaudeSurface | None
    codex: CodexSurface | None
    grok: GrokSurface | None
    capabilities: dict[str, object]
    mcp_names: dict[str, tuple[str, ...]]
    logs: tuple[str, ...]
def plan(
    runtime_dir: Path,
    manifest: dict[str, object],
    *,
    manifest_bytes: bytes,
    skill_catalog: SkillCatalog,
    baselines: configuration.Baselines,
    catalogs: Catalogs,
) -> RuntimePlan:
    raise NotImplementedError
```

The old `skills: tuple[str, ...]` plus `skill_bodies: dict[str, Path]` pair disappears. That pair let downstream code infer identity, source, and destination from matching strings.

### `bin/agent_runtime_compiler/audit.py` and `bin/generate.py`

```python
def audit_runtime(
    runtime_dir: Path,
    tracked: set[str],
    catalog: SkillCatalog,
) -> list[Residue]:
    raise NotImplementedError
def compile_plans(
    runtime_entries: list[tuple[Path, dict[str, object], bytes]],
    *,
    skill_catalog: SkillCatalog,
    baselines: configuration.Baselines,
    catalogs: Catalogs,
) -> tuple[RuntimePlan, ...]:
    raise NotImplementedError
```

`audit_runtime` looks up each immediate generated child through `catalog.by_destination`. It compares the child with that definition's body using `tree_digest`.

`compile_plans` builds every requested plan before `writers.materialize` receives the first one. `--all` can no longer write several valid homes and then stop on a late manifest or selection error.

`Residue` should expose whether cleaning an item leaves an owned skill absent. `clean_residue` must consume that field instead of inferring skill ownership from `item.path.parent.name == "skills"`.

## Catalog rules

### Identity and source shape

1. A skill marker must be exactly `skills/<owner>/<domain>/<skill>/SKILL.md`.
2. Each component uses the existing agent ID component grammar. Components are ASCII, lower case, at most 64 characters, and contain no empty or consecutive hyphen groups.
3. The body directory must resolve inside the configured skill root. A symlinked body directory is rejected.
4. A `SKILL.md` below another skill body is rejected. Recursive Codex and Grok discovery would otherwise expose an undeclared skill from copied support files.
5. A marker at any other depth is an error. The loader never silently ignores a malformed owned tree.

The canonical ID is path derived. Moving a skill between publishers or domains changes its ID. Such a move changes its ownership or meaning, so the rename is useful signal.

### Frontmatter and destination

The catalog requires `name` and `description` because the generated copy must satisfy every target harness. It preserves unknown frontmatter fields and all body bytes.

`name` must satisfy the common portable rule already documented by the vendored validator: 1 through 64 characters, lower case ASCII letters, digits, and single hyphens. This rule also makes path traversal and hidden destinations impossible.

The frontmatter name is the generated directory segment. This closes the live `codebase-map` versus `map` split without adding alias metadata:

```text
catalog ID       helioy/codebase/codebase-map
source body      skills/helioy/codebase/codebase-map
frontmatter name map
destination      <home>/skills/map
Claude           /map
Codex            $map
Grok             /map
```

Two skill definitions may not share a destination or frontmatter name anywhere in the catalog. The diagnostic names both canonical IDs and both body paths. Global uniqueness keeps `--catalog`, generated homes, and operator vocabulary unambiguous.

### Bundles

1. `skills/<publisher>/bundles.toml` is optional.
2. The containing directory defines the publisher. The file has no `publisher` or `id` field.
3. A bundle name is one canonical component. Its public ID is `<publisher>/<bundle>`.
4. Members are explicit `<domain>/<skill>` references within that publisher.
5. Bundle members may not name other bundles. This removes cycle handling and keeps one list sufficient to review the full expansion.
6. Empty bundles, duplicate members, unknown members, and unknown tables fail catalog loading.
7. A skill may belong to several bundles. Membership is the only information bundles own.

An unknown required bundle is fatal. An unknown optional bundle logs and disappears, matching current optional skill behavior. Every known bundle is validated even when no runtime selects it.

### Selection order and overlap

Resolution processes required exact skills, required bundles, optional exact skills, then optional bundles. Each source list keeps authored order. A skill that arrives through several selectors materializes once. Required wins over optional.

Duplicate strings within one runtime list are errors. Overlap through a bundle and an exact reference is valid because bundles would otherwise be difficult to extend or specialize.

No selection operation scans a path prefix. A new file cannot enter an existing runtime through location alone.

## Compilation flow

```text
load SkillCatalog once
    discover exact owner/domain/skill markers
    parse required frontmatter fields
    load publisher bundles
    validate IDs, destinations, names, and membership
            |
            v
load every requested runtime.toml
    validate schema 4 and agent identities
    parse exact skill and bundle references
            |
            v
compile every RuntimePlan
    expand bundle membership
    resolve required and optional skills
    calculate generated_from
    derive required capability intersection
    narrow harnesses
    compose config documents
            |
            v
audit every target and enforce the resync gate
            |
            v
materialize plans
    copy each selected body to skills/<frontmatter name>
    prune other immediate children
    write instructions, configs, and capabilities.json
```

Every operation before the last box is read only. A bad skill anywhere in the catalog, a bundle collision, or a bad runtime selection fails before the first template changes.

## `generated_from`

Rekeying every skill makes a fleet wide digest change unavoidable. The new digest should also cover bundle expansion and optional destinations, which the current required only calculation cannot represent.

Use a versioned, length delimited recipe:

```text
"agent-runtimes:generated-from:v2\0"
runtime.toml raw bytes
for each resolved skill, sorted by canonical ID:
    requirement marker
    canonical ID
    destination
    exact frontmatter bytes
```

The manifest bytes already contain selected bundle IDs. The resolved entries capture the exact bundle expansion. Two bundle definitions with the same resolved result produce the same digest. That is desirable because their generated skill inventory and capability result are equal.

Full body bytes stay out of `generated_from`. `tree_digest` and the template audit already own full body drift. This keeps the two digests focused and avoids hashing 1.9 MB during every plan.

`capabilities.json` keeps schema version 3 and the same `generated_from` string field. Runtime manifests move to schema 4. Separate constants prevent an authored manifest change from implying a published capabilities parser change.

Transport Matters must accept the coordinated digest refresh before this change lands. Its template identities must be regenerated from the new homes in the same delivery wave.

## Materialization, audit, clean, and drift

The generated layout stays flat, so the proven copy model remains useful:

* `materialize` receives selected definitions and copies each full body to `skills/<destination>`.
* A matching `tree_digest` leaves a copy alone.
* A stale owned copy remains a `resync` finding and keeps the `--force` gate.
* Pruning compares immediate generated child names with the resolved destination set.
* Audit maps each immediate child through `SkillCatalog.by_destination`, then compares it with the owned body.
* Clean removes the exact finding. Its result metadata says whether regeneration must restore an owned skill.
* Orphan runtime detection does not change.

Source hierarchy never reaches audit path traversal. A grouping directory cannot become a clean target that deletes sibling skills.

The writer still copies one shared skill tree for every targeted harness. No harness specific selection path is introduced.

## Collision and failure rules

| Condition | Result |
| --- | --- |
| Wrong skill path depth | Catalog load fails with the marker path |
| Invalid owner, domain, or skill component | Catalog load fails with component and path |
| Missing or malformed `name` or `description` | Catalog load fails with body path |
| Destination outside portable name grammar | Catalog load fails |
| Duplicate canonical ID | Catalog load fails with both paths |
| Duplicate destination or frontmatter name | Catalog load fails with both IDs and paths |
| Nested `SKILL.md` inside a body | Catalog load fails with ancestor and nested marker |
| Unknown bundle member | Catalog load fails even if bundle is unused |
| Unknown required skill or bundle | Plan fails |
| Unknown optional skill or bundle | Plan logs and skips it |
| Required and optional overlap | One required selected skill |
| Required capability has no common vendor | Plan fails before writes |
| Any requested plan is invalid | No requested home is written |

Error output must use canonical IDs. Destination errors include the harness name so a caller can connect the catalog error to the generated home.

## Options considered

### Path derived IDs

The relative `owner/domain/skill` path supplies identity with no new field. The tree and manifest references cannot disagree. A move changes identity, which is correct for ownership and domain changes.

The cost is a coordinated reference update when taxonomy changes. This repository already treats such changes as breaking and requires old paths to disappear in the same wave.

### Explicit per skill metadata

An `id: owner/domain/skill` frontmatter key would keep identity stable across moves. It would also duplicate a hierarchical source path or make the path decorative. The custom key reaches all three harnesses, conflicts with the vendored skill validator, and creates another field that can disagree with location.

A sidecar `skill.toml` avoids harness exposure but adds one file and one parser to every body. It still duplicates either the path or frontmatter name. The stable move benefit is weak because moving between owner or domain is a semantic rename.

### Publisher manifests as the skill catalog

A `skills/<publisher>/catalog.toml` could list every skill ID and body path. That supports stable IDs and centralized curation, but each new body requires a second registration edit. The manifest would repeat paths, grow with the whole publisher, and become an index that can drift from marker discovery.

Publisher manifests are valuable for explicit bulk membership. Restricting them to bundles gives them one job and one source of truth.

### Decision

Use path derived skill IDs, frontmatter names for flat harness destinations, and publisher bundle manifests for explicit sets. This combines automatic leaf discovery with reviewed bulk curation. Identity, invocation, and membership remain separate and each has one owner.

## Migration

This is one breaking wave. There is no legacy resolver, alias table, or parallel flat catalog.

1. Add the identity types and the new catalog tests.
2. Assign each of the 36 current bodies one owner and one domain. Record the proposed moves in a temporary migration table reviewed by the owner. The table is tooling input, not committed product metadata.
3. Move every body with `git mv skills/<old> skills/<owner>/<domain>/<skill>`.
4. Preserve current frontmatter names. The existing 36 names are unique. `codebase-map` therefore moves to a canonical hierarchical path while its generated destination changes to `skills/map`, unifying invocation across the three harnesses.
5. Add publisher `bundles.toml` files only where a runtime benefits from bulk curation. The frontend runtime is the clear first use. Keep small or cross domain runtimes on exact IDs.
6. Bump every `runtime.toml` to schema 4. Replace all flat required and optional names with canonical IDs or explicit bundle IDs.
7. Delete the deprecated bare skills array parser and every flat name fallback.
8. Replace `RuntimePlan.skill_bodies` with resolved selected definitions. Move frontmatter parsing out of `capabilities.py`.
9. Update materialization, audit, clean, catalog display, generated digest calculation, and tests in the same commit series before regeneration.
10. Coordinate the `generated_from` refresh with Transport Matters, then regenerate every home once with `--force` because the owned source paths and one destination changed.
11. Delete every old flat source path. Search skill bodies and docs for old invocation references, with special attention to `/codebase-map`, `$codebase-map`, `/map`, and `$map`.

The temporary migration table must cover every current body exactly once. A migration test compares its source set with the catalog at the fixed starting commit, so omission and duplication fail before any move script runs.

## Tests

### Unit tests

* Parse valid agent, skill, and bundle IDs through the shared component grammar.
* Reject wrong arity, upper case, traversal components, empty components, consecutive hyphens, and overlong components.
* Discover only exact `owner/domain/skill/SKILL.md` bodies.
* Reject a marker above or below that depth, including a marker nested inside a valid body.
* Parse required `name` and `description` plus `requires_capability` from the existing supported list forms.
* Reject duplicate canonical IDs, destinations, and frontmatter names with both source paths in the message.
* Load publisher bundles with relative members. Reject unknown tables, empty bundles, duplicate members, bundle nesting, and unknown skills.
* Prove that adding a body under a domain does not change a bundle expansion.
* Resolve exact skills and bundles in deterministic order. Prove required wins over optional overlap.
* Preserve missing optional logs and missing required failures for skill and bundle references.
* Derive vendor constraints only from resolved required entries, including entries introduced by a required bundle.
* Prove an optional capability skill does not narrow harnesses.
* Keep `generated_from` stable across catalog scan order. Change it when a manifest, selected canonical ID, destination, frontmatter, requirement, or bundle expansion changes.
* Keep `generated_from` stable when only a supporting body file changes. Prove `tree_digest` catches that change.

### Materialization and audit tests

* Materialize a hierarchical source body at one flat frontmatter destination.
* Materialize `helioy/codebase/codebase-map` to `skills/map` and audit it as owned.
* Preserve executable bits and supporting directories.
* Leave an unchanged copy untouched and fully replace a stale copy.
* Prune a destination removed by a bundle edit.
* Report a foreign destination, a symlinked owned destination, and a body with changed bytes.
* Make clean request regeneration through residue metadata, without inspecting path parents.
* Prove `--all` compiles every plan before a writer spy receives one plan.
* Prove catalog collisions abort a one runtime generation and `--all` before any home changes.
* Keep orphan runtime detection and the full resync gate behavior.

### Harness contract tests

Build one temporary home with immediate `map`, `adapt`, and `code-review` directories. Assert every directory has a valid `SKILL.md` and no nested skill marker.

Then run:

* `codex debug prompt-input` and assert the three names and paths appear once.
* `grok inspect --json` and assert the three names and paths appear once.
* A Claude 2.1.259 launch through a Transport Matters overlay and assert the three command names. Claude has no equivalent offline prompt renderer, so validator output alone is insufficient for this final claim.

## Complete verification gate

The implementation is complete only when this sequence passes on the same commit:

```bash
# Structural migration checks
test "$(find skills -name SKILL.md | wc -l | tr -d ' ')" = "36"
test -z "$(find skills -mindepth 2 -maxdepth 2 -name SKILL.md -print)"
git grep -n 'required = \["codebase-map"\]' -- 'runtimes/**/runtime.toml' && exit 1 || true
# First redistribution, then idempotence
python3 bin/generate.py --all --force
python3 bin/generate.py --all
python3 bin/generate.py --audit
python3 -m pytest tests -q
# Consumer and harness proofs
python3 bin/generate.py --catalog
# Run the Codex, Grok, and Claude contract probes described above.
# Run Transport Matters template identity and launch integration tests.
git status --short
```

The second generation must report no skill add, removal, or resync. Audit must report clean. Tests must include the prewrite failure assertions. `git status` must show only the reviewed source moves, manifest changes, generator code, tests, and docs. Generated homes remain disposable output.

The Transport Matters check must prove that every refreshed template identity matches the exact regenerated bytes and that `generated_from` is accepted for all ten runtimes.

## Proven facts and design choices

### Proven at the assigned snapshot

* Repository HEAD is `71e3871ebbb8813fb213827f70e38fc4d83feafa`.
* The working tree already has three unrelated modifications. This work did not touch them.
* The owned catalog contains 36 flat skill bodies and ten runtime manifests.
* Current source discovery, materialization, audit, and clean logic use immediate child basenames.
* The generator parses only `requires_capability`; it does not validate frontmatter names.
* `codebase-map` has frontmatter name `map`.
* Current materialization copies whole bodies, preserves executable bits, prunes unwanted immediate children, and gates stale owned copies.
* Codex 0.153.0 and Grok 1.0.13 discover nested skills. Their duplicate name probes keep both paths visible.
* Official Claude documentation keys personal and project command names on the directory. Official Codex and Grok behavior keys invocation on frontmatter name.
* Claude nested prompt inclusion remains a working assumption. Current documentation, loader text, and validator behavior support one level, but no offline prompt render proves it.
* The reconciled grounding run reported 96 tests passing and a clean audit before this design task.

### Design choices

* Canonical IDs have exactly three path derived components.
* Generated destinations remain flat.
* Frontmatter `name` becomes the destination segment, so all harnesses use the same human name.
* Frontmatter names are globally unique across the owned catalog.
* Bundles are explicit publisher scoped lists with no nesting or prefix expansion.
* Runtime manifests use schema 4 and receive no compatibility parser.
* Every requested plan compiles before any requested home is written.
* The new recipe digest covers selected optional skills and bundle expansion.
* The published capabilities document keeps schema version 3.

## Design quality screen

**Shallow modules.** Only `identity.py` is new. It owns the grammar, arity, parsing, and rendering of skill and bundle IDs plus agent ID validation. Bundle loading stays in `skills.py`; a separate bundle service would add calls without hiding complexity.

**Information leakage.** Runtime manifests know IDs and bundle IDs. Capability code sees resolved required definitions. Writers see selected definitions and destinations. No caller reconstructs paths, expands bundles, or matches parallel name maps.

**Temporal decomposition.** Discovery returns an immutable validated catalog. Resolution returns an immutable selected set. Planning for the full request finishes before writing. No phase leaves a partially valid global registry for the next phase to repair.

**Pass through methods.** `SkillCatalog.resolve` owns expansion, precedence, missing optional behavior, collision safety, and digest calculation. `materialize` owns convergence. The design adds no wrapper whose only action is forwarding parameters.

## Rationale

The generated home is the strictest boundary. One flat directory per skill works for all three harnesses and keeps audit deletion exact. The authored tree can carry richer ownership without exporting that hierarchy.

Path identity avoids a new metadata field and makes ownership visible during review. Frontmatter already has to name the harness command, so using that value for the destination makes Claude agree with Codex and Grok. Explicit bundles solve bulk curation without granting future files automatic membership.

The result has three public references with distinct jobs: `owner/domain/skill` selects one body, `owner/bundle` selects a reviewed set, and the frontmatter name is what a person invokes. The compiler validates all mappings once and passes resolved objects downstream.

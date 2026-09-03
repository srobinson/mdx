---
title: Skill hierarchy design for agent-runtimes, candidate Claude
type: design
tags: [agent-runtimes, skills, hierarchy, identity, bakeoff]
summary: Path-derived canonical skill ids (owner[/domain]/leaf) with flat leaf-named generated output; one catalog object owning discovery, validation, and selection; single-wave migration.
status: active
source: backend-engineer
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

# Skill hierarchy: candidate Claude

Design against HEAD `71e3871ebbb8813fb213827f70e38fc4d83feafa`. Grounded in
the [grounding synthesis](../research/agent-runtimes-skill-hierarchy-grounding-synthesis.md) and its three source reports, all read in full, plus
direct reads of `skills.py`, `manifest.py`, `capabilities.py`, `compiler.py`,
`audit.py`, `writers.py`, `generate.py`, all 10 manifests, and a frontmatter
scan of all 36 bodies (re-verified today: exactly one `name` mismatch,
`codebase-map`/`map`; exactly one `requires_capability`; zero nested
`SKILL.md`; zero bare-array manifests).

**Chosen shape: path-derived canonical ids.** The relative source path under
`skills/` is the skill's identity: `owner/leaf` or `owner/domain/leaf`, 2 or 3
components, each matching the existing agent-id component grammar. The leaf is
the single harness-visible name: it is the flat destination segment in every
generated home and the frontmatter `name` must equal it. Generated output stays
one flat level. Rationale and the comparison against explicit per-skill
metadata and publisher bundle manifests are in §10.

---

## 1. Caller usage

### 1.1 Proposed skills tree

Every body moves under an owner, optionally a domain. Leaves keep their exact
current spelling, so no Claude command, manifest habit, or skill-to-skill
reference changes meaning. Assignment (36 bodies; the owner adjusts placement,
the mechanics do not care):

```
skills/
  tm/
    design/        frontend-design impeccable critique audit web-design-guidelines
                   polish extract normalize confident-ai-design clarify onboard
                   copywriting                                          (12)
    transform/     adapt animate bolder colorize delight harden optimize quieter (8)
    education/     teach-impeccable                                     (1)
    review/        code-review                                          (1)
    delivery/      pull-request snapshot                                (2)
    content/       distill my-voice blog-architect excalidraw-diagram   (4)
    analysis/      codebase-map transcript-search                       (2)
    orchestration/ tm-orchestrate                                       (1)
    meta/          skill-matters find-skills                            (2)
  anthropic/
    skill-creator/                                                      (1)
  helioy/
    media/         helioy-imagegen helioy-imagegen-primatives           (2)
```

`anthropic/skill-creator` shows the 2-component form: a vendored body with an
owner and no domain. Domains are curation units, chosen so that set selectors
align with how homes actually curate (the 12 skills `tm/frontend` requires are
exactly `tm/design/`).

### 1.2 Manifest selection

`[skills].required` / `[skills].optional` stay string lists. An entry is either
a canonical id or a set selector, which is a 1- or 2-component prefix followed
by a literal `/*`. Nothing else expands: a bare prefix is never a set, there is
no `**`, no mid-path glob, no suffix match.

One skill (`tm/generalist`, rewritten):

```toml
schema_version = 4
id = "tm/generalist"
# ...
[skills]
required = [
  "tm/review/code-review",
  "tm/delivery/pull-request",
]
optional = [
  "tm/delivery/snapshot",
  "tm/orchestration/tm-orchestrate",
]
```

A domain set and a mixed form (`tm/frontend`, rewritten):

```toml
[skills]
required = ["tm/design/*"]                # the 12 design skills, exactly
optional = [
  "tm/transform/*",                       # the 8 transform verbs
  "tm/education/teach-impeccable",
]
```

A publisher set (`tm/imagegen`, rewritten — `helioy/*` selects every skill
under owner `helioy` at any depth):

```toml
[skills]
required = ["helioy/media/helioy-imagegen"]
optional = ["helioy/*"]                   # overlaps required; dedupe keeps required
```

Set semantics: a selector expands to every catalog id strictly under the
prefix, sorted by id, spliced in place of the selector; then the combined
required+optional list is deduped by id, first occurrence winning, so a skill
matched by both lists is required. A required selector (id or set) that
resolves to nothing is fatal before any write; an optional one logs
`~ skill <selector>: optional, matched nothing, skipped` and is dropped —
the existing `_drop_missing_optional` contract, extended to sets. Every
expanded required entry contributes `requires_capability` to the vendor
constraint, unchanged.

### 1.3 Resulting generated home

Unchanged in shape. `tm/frontend` after regeneration:

```
runtimes/frontend/
  skills/
    adapt/SKILL.md            animate/    audit/       bolder/     clarify/
    colorize/                 confident-ai-design/     copywriting/ critique/
    delight/                  extract/    frontend-design/  harden/  impeccable/
    normalize/                onboard/    optimize/    polish/     quieter/
    teach-impeccable/         web-design-guidelines/
  AGENTS.md  CLAUDE.md  .claude.json  settings.json  config.toml
  config.grok.toml  capabilities.json  runtime.toml
```

Destination segment = leaf. Because leaves keep their current spelling and
`tree_digest` is relative-path based, an unmoved body's existing copy digests
equal and is left untouched: the migration regeneration rewrites configs and
`capabilities.json` but resyncs only the one body whose bytes change
(`codebase-map`, §8). Claude discovers `/code-review` from the directory name,
Codex and Grok invoke by frontmatter `name`, and the name==leaf rule (§5)
makes all three agree, per harness contract constraint (P) from the synthesis.

---

## 2. Identity model

The synthesis names four planes. This design collapses them to two, with one
explicit mapping:

| Plane | Carrier | Rule |
| --- | --- | --- |
| Canonical id (catalog key, manifest reference, digest key, log name) | relative source path, posix | `owner[/domain]/leaf`, components match agent grammar |
| Harness-visible name (destination segment, Claude command, Codex/Grok invocation) | `leaf` = last id component | frontmatter `name` MUST equal it; unique catalog-wide |

The mapping id -> leaf is `skill_id.rpartition("/")[2]`: derived, never stored
twice. Frontmatter `name` is the one deliberate copy — Codex requires the
field, so it must exist in the shipped bytes — and the equality validator makes
drift impossible, turning gotcha 1 ("same string, different plane") into a
checked invariant. The `codebase-map`/`map` divergence is closed by migration,
not aliased (§8).

Owner/domain get no kind/namespace semantics (agents need them because
transport-matters addresses agents by id and enforces authority; no external
consumer addresses a skill by catalog id, so a registry of skill owners would
be speculative structure).

---

## 3. Core data structures and signatures

All new code lives where the concern already lives; no new module. Bodies are
`raise NotImplementedError` per the brief; behavior is specified in the
docstrings and §4-§6.

### 3.1 `bin/agent_runtime_compiler/manifest.py` (edited)

```python
# Exported so skills.py reuses the one component grammar (synthesis constraint 8).
ID_COMPONENT = r"[a-z](?:[a-z0-9-]{0,62}[a-z0-9])?"   # was _AGENT_ID_COMPONENT
_AGENT_ID_PATTERN = re.compile(rf"^{ID_COMPONENT}/{ID_COMPONENT}$")  # unchanged

MANIFEST_SCHEMA_VERSION = 4   # v4: hierarchical skill selectors; array form removed

def resolve_skills(value: Any) -> tuple[list[str], list[str]]:
    """Return (required_selectors, optional_selectors) from the [skills] table.

    Selectors are opaque strings here; grammar and expansion belong to
    skills.SkillCatalog.select, the module that owns skill identity. The
    deprecated bare-array form is deleted in the migration wave (no manifest
    uses it at HEAD); a list is now a hard error naming the v4 table form.
    """
    raise NotImplementedError
```

`SKILLS_ARRAY_DEPRECATION_NOTICE` is deleted. Everything else in `manifest.py`
is untouched: agent identity, `validate_catalog_identities`, harness tables,
models.

### 3.2 `bin/agent_runtime_compiler/skills.py` (rewritten core)

```python
from agent_runtime_compiler.manifest import ID_COMPONENT   # models <- manifest <- skills: acyclic

SKILL_MARKER = "SKILL.md"
_COMPONENT = re.compile(rf"^{ID_COMPONENT}$")
MIN_DEPTH, MAX_DEPTH = 2, 3          # owner/leaf .. owner/domain/leaf


@dataclass(frozen=True, slots=True)
class SkillFrontmatter:
    """Everything the generator reads from one SKILL.md frontmatter."""
    name: str | None                  # None when the key is absent (fatal at catalog build)
    requires_capability: tuple[str, ...]
    text: str                         # raw frontmatter bytes as text, for generated_from


@dataclass(frozen=True, slots=True)
class SkillEntry:
    """One owned body: canonical id, its location, and its parsed frontmatter.

    Replaces the dict[str, Path] that collapsed manifest key, body path, and
    destination segment into one string (synthesis constraint 5). owner,
    domain, and leaf are projections of skill_id, never stored twice.
    """
    skill_id: str                     # "tm/review/code-review" | "anthropic/skill-creator"
    body: Path
    frontmatter: SkillFrontmatter

    @property
    def leaf(self) -> str:            # destination segment == harness name
        raise NotImplementedError

    @property
    def owner(self) -> str:
        raise NotImplementedError

    @property
    def domain(self) -> str | None:   # None for 2-component ids
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class SkillCatalog:
    """Every owned body, validated as a set. Construction is the collision gate.

    entries is keyed by canonical id; by_leaf is the derived index the flat
    destination plane needs (materialize prune, audit lookup). by_leaf is
    total and unambiguous because catalog() enforces leaf uniqueness.
    """
    entries: dict[str, SkillEntry]
    by_leaf: dict[str, SkillEntry]

    def select(
        self, selectors: list[str], *, missing: Literal["fatal", "skip"]
    ) -> tuple[list[SkillEntry], list[str]]:
        """Resolve manifest selectors to entries, in manifest order.

        An exact id resolves to its entry. "<prefix>/*" (prefix of 1 or 2
        valid components) expands to every id strictly under prefix, sorted.
        Malformed selectors (bad component, depth, non-trailing or bare "*")
        are fatal regardless of `missing`, with the selector and the rule in
        the message. An id absent from the catalog, or a set matching nothing:
        fatal when missing="fatal" (required), logged and dropped when
        missing="skip" (optional). Result is deduped by id, first occurrence.
        Returns (entries, logs).
        """
        raise NotImplementedError


def catalog(root: Path) -> SkillCatalog:
    """Discover and validate every owned body under root. The one collision gate.

    Walk: root.rglob(SKILL_MARKER); each marker's parent directory is a body,
    its id the parent's posix path relative to root. Missing root -> empty
    catalog (existing contract).

    Fails (SystemExit, naming every offender and its path) before anything is
    written, on: a marker at depth 1 (the retired flat shape) or > MAX_DEPTH;
    an id component failing ID_COMPONENT; a marker whose parent lies under
    another marker's parent (grouping-with-marker and body-embedded markers:
    both are the probe-proven leak shape, since a nested SKILL.md inside a
    shipped copy is a phantom skill to Codex and Grok); a frontmatter without
    `name`; frontmatter name != leaf; two ids sharing a leaf. Leaf uniqueness
    is one check that closes both flattening-collision classes at once,
    because name == leaf makes frontmatter-name collisions the same collision.
    """
    raise NotImplementedError


def parse_frontmatter(body: Path) -> SkillFrontmatter:
    """Single frontmatter reader, moved from capabilities._skill_frontmatter
    and extended to extract `name`. capabilities.py imports it from here."""
    raise NotImplementedError


def tree_digest(path: Path) -> str: ...      # unchanged
def remove_path(path: Path) -> None: ...     # unchanged


def materialize(runtime_dir: Path, selected: Sequence[SkillEntry]) -> list[str]:
    """Copy each selected body to skills/<entry.leaf>; prune leaves not selected.

    Same convergence contract as today: digest-equal copy untouched, anything
    else replaced whole, resync reported distinctly. The unknown-name check is
    gone — select() already resolved entries, so an unknown skill cannot reach
    here (fail-before-write moved earlier, not duplicated). Logs name the
    canonical id on add/resync ("+ skill tm/review/code-review"); prune logs
    name the leaf, which is all a foreign directory has.
    """
    raise NotImplementedError
```

### 3.3 `bin/agent_runtime_compiler/capabilities.py` (edited)

```python
def vendor_constraint(
    runtime_dir: Path, required: Sequence[SkillEntry]
) -> VendorConstraint:
    """As today, over resolved entries instead of names+catalog.

    No membership check (select owns it) and no file reads (SkillEntry carries
    parsed frontmatter): the function becomes pure over its arguments plus the
    registry and manifest bytes. Digest = manifest bytes, then per required
    entry f"\n{entry.skill_id}\0" + entry.frontmatter.text. Keying by id means
    moving a body between domains moves generated_from — correct, since the
    manifest reference moved with it (§7).
    """
    raise NotImplementedError
```

`_skill_frontmatter` and its helpers move to `skills.parse_frontmatter`;
`VendorConstraint`, `derive_capabilities`, and the registry are untouched.
`capabilities.json` gains no keys and loses none.

### 3.4 `bin/agent_runtime_compiler/compiler.py` (edited)

```python
@dataclass(frozen=True, slots=True)
class RuntimePlan:
    ...
    skills: tuple[SkillEntry, ...]    # replaces skills: tuple[str,...] + skill_bodies: dict[str, Path]
    ...

def plan(runtime_dir, manifest, *, skill_root, baselines, catalogs) -> RuntimePlan:
    """Flow change only (§4): resolve_skills -> catalog -> select(required,
    fatal) + select(optional, skip) -> dedupe -> vendor_constraint(required
    entries) -> unchanged tail. _drop_missing_optional is deleted; its
    semantics live in select(missing="skip")."""
    raise NotImplementedError
```

### 3.5 `bin/agent_runtime_compiler/audit.py` (edited)

```python
def audit_runtime(
    runtime_dir: Path, tracked: set[str], owned: SkillCatalog
) -> list[Residue]:
    """Identical walk (destination is still flat, one level). Lookup becomes
    owned.by_leaf.get(entry.name); the out-of-sync reason names the body by
    canonical id ("out of sync with the owned body skills/tm/review/code-review")
    so the finding points at the file to edit."""
    raise NotImplementedError
```

`GENERATED_NAMES`, `tracked_names`, `audit_orphans`, `audit_root` (signature
now carries the catalog it already builds): unchanged. `generate.clean_residue`
needs zero changes — findings still sit at `skills/<leaf>`, so
`item.path.parent.name == "skills"` remains true.

### 3.6 `bin/writers.py`, `bin/generate.py` (edited)

`writers.materialize`: `materialize_skills(home, plan.skills)`. `generate.py`:
`regenerate`/`apply` thread the `SkillCatalog`; `print_catalog` renders the
tree grouped owner/domain/leaf instead of a flat sorted list. No CLI flag
changes; `AGENT_RUNTIMES_SKILLS` unchanged.

---

## 4. Compilation flow

```
catalogs.discover                  unchanged ($HOME for MCP only — constraint 9 holds)
configuration.load_baselines       unchanged
manifest.load_manifest             unchanged
compiler.plan
  agent_identity                   unchanged (schema_version now 4)
  resolve_skills                   -> (required_selectors, optional_selectors)
  skills.catalog(skill_root)       -> SkillCatalog        [collision gate: §5]
  resolve_harnesses                unchanged
  catalog.select(required, fatal)  -> required entries    [unknown/empty-set fatal]
  catalog.select(optional, skip)   -> optional entries + skip logs
  dedupe by id, required first     -> plan.skills
  vendor_constraint(required)      -> VendorConstraint + generated_from  [id-keyed]
  ... redactions, mcp, models, derive_capabilities: unchanged ...
writers.materialize
  skills.materialize(home, plan.skills)   dest = skills/<leaf>, flat
  instructions / configs / prune / capabilities.json: unchanged
audit / clean / resync gate        leaf-keyed lookup, otherwise unchanged
```

Everything that decides content still runs before the frozen plan; everything
that touches the filesystem still runs after it. Identity validation happens
once, at catalog construction, not re-checked downstream (no temporal
decomposition: discovery, parsing, and validation are one step because they
are one concern — what the catalog *is*).

---

## 5. Collision and validation rules (all fail before any write)

At `skills.catalog()` — properties of the owned tree, independent of any
manifest, so they hold for `--catalog`, `--audit`, `--clean`, and every
generation path:

| # | Rule | Failure message names |
| --- | --- | --- |
| C1 | marker depth in {2,3}; depth 1 is the retired flat shape | the marker path and the required shape |
| C2 | every id component matches `ID_COMPONENT` | id and offending component |
| C3 | no marker's parent lies under another marker's parent | both marker paths |
| C4 | frontmatter `name` present (Codex requires the field) | body path |
| C5 | frontmatter `name` == leaf | body path, both values |
| C6 | leaf unique catalog-wide | both ids |

C3 is the leak killer: with it, a shipped copy can never contain a nested
`SKILL.md`, so recursive Codex/Grok discovery of a generated home finds
exactly the selected set — the synthesis's worst shape (undeclared,
capability-unconstrained, harness-divergent delivery) is unrepresentable. It
also makes "id X" and "group X/" structurally exclusive, so `tm/design` can
never be both a skill and a set prefix. C5+C6 together close both flattening
collision classes from constraint 3 with one index, and close gotcha 1 by
construction. Catalog-wide (not per-home) leaf uniqueness is chosen so any
subset of the catalog is co-selectable and the error surfaces when a body is
authored, not when some later manifest first combines two skills — the same
stance `validate_catalog_identities` takes for agents.

At `SkillCatalog.select()` — properties of one manifest against the catalog:

| # | Rule |
| --- | --- |
| S1 | selector grammar: exact id (2-3 components) or `prefix/*` (1-2 components, trailing only) |
| S2 | required id unknown, or required set empty: fatal (the empty required set is the "implicit wildcard surprise"; it never silently generates a thinner home) |
| S3 | optional id unknown / optional set empty: logged, dropped |
| S4 | expansion deterministic: sorted by id, spliced in place, dedupe first-occurrence, required before optional |

Unchanged validation surfaces: agent identity and uniqueness, harness tables,
capability registry, model rows, `MANAGED_KEYS`, the resync `--force` gate.

---

## 6. Module ownership

| Concern | Owner | Note |
| --- | --- | --- |
| Skill identity: grammar use, discovery, frontmatter parsing, catalog validation, selection, copy/prune | `skills.py` | one deep module; its interface is `catalog() -> SkillCatalog`, `select`, `materialize` |
| Component grammar (the regex) | `manifest.py` exports `ID_COMPONENT` | one grammar for agent and skill ids (constraint 8), one definition |
| Manifest shape (`[skills]` table, required/optional lists as strings) | `manifest.py` | knows nothing of selector semantics |
| Capability registry, vendor constraint, `generated_from`, capabilities.json | `capabilities.py` | consumes `SkillEntry`, reads no skill files |
| Orchestration into a frozen plan | `compiler.py` | wiring only; `_drop_missing_optional` deleted, not wrapped |
| Filesystem | `writers.py` / `skills.materialize` | unchanged split |
| Independent expectations | `audit.py` | keeps stating its own flat-destination expectation rather than importing writer constants — the documented existing choice |

Import DAG (acyclic, one new edge skills->manifest):
`models <- manifest <- skills <- {capabilities, audit} <- compiler <- writers <- generate`.

Ousterhout screen: **shallow modules** — no new module; `SkillCatalog` deepens
`skills.py` (small surface, all discovery/validation/selection complexity
behind it). **Information leakage** — frontmatter parsing had leaked into
`capabilities.py`; it moves to the skill-body module and `capabilities`
becomes file-blind; the flat-destination fact lives in `skills.py` plus the
audit's deliberate restatement. **Temporal decomposition** — validation is not
smeared across pipeline stages; the catalog is valid or it does not exist.
**Pass-through** — `resolve_skills` no longer pre-combines a list the compiler
re-derives; `select` is not wrapped; no adapter layers added.

---

## 7. Published contracts and digests

- `generated_from` is keyed by canonical id and moves for **every** home in
  the migration wave — unavoidable under any keying, because every manifest's
  bytes are rewritten (references + `schema_version = 4`) and manifest bytes
  are already hashed. One coordinated, announced event with transport-matters
  (constraint 7), not a per-design cost. After migration, moving a body across
  domains moves its ids, its manifests, and therefore the digest: correct and
  visible.
- `launch_requirements_digest`: unaffected (hashes compiled mechanism only).
- `capabilities.json`: no key changes, no `schema_version` bump.
- Harness-visible names: unchanged for all 36 leaves; the one frontmatter fix
  moves Codex `$map` -> `$codebase-map` and Grok `/map` ->
  `/codebase-map` (§8). Claude commands are unchanged everywhere.
- Home file layout: byte-stable except `capabilities.json`, configs, and the
  `codebase-map` copy; skill copies survive by digest equality.

---

## 8. Migration: one wave

No staged path, no compatibility shim, no depth-1 fallback. After the wave,
C1 makes the flat shape a hard error, so it cannot creep back.

1. **Move bodies.** `git mv skills/<name> skills/<owner>/[<domain>/]<name>` for
   all 36 per the §1.1 table. Leaves unchanged.
2. **Close the name divergence.** Edit `skills/tm/analysis/codebase-map/SKILL.md`
   frontmatter to `name: codebase-map`. Direction chosen deliberately: the
   directory (and Claude command, the fleet's majority harness at six claude
   runtimes) stays put; Codex/Grok invocation moves. No alias mechanism — an
   alias is a permanent second identity axis for one skill, which is the
   ambiguity this design exists to remove.
3. **Rewrite all 10 manifests.** Canonical ids / set selectors per §1.2;
   `schema_version = 4`. Empty-skill homes (`tm/capture`, `tm/stu`) change
   only the version line.
4. **Land the code** (§3) and the test suite (§9) in the same change set;
   delete `_drop_missing_optional`, the array form, and
   `SKILLS_ARRAY_DEPRECATION_NOTICE` in the same wave
   (migrate-callers-then-delete).
5. **Docs pass, same wave:** `skills.py` docstring ("both harnesses"),
   `generate.py` header, `skills/tm/meta/skill-matters/SKILL.md` path claims,
   `AGENTS.md` file map (`skills/<name>/` -> `skills/<owner>/[<domain>/]<name>/`),
   and the launcher spec's stale imagegen-capability sentence.
6. **Regenerate and notify.** `python3 bin/generate.py --all --force` (force
   answers for the pre-existing dirty `tm-orchestrate` body and the
   `codebase-map` edit). Send transport-matters the per-home `generated_from`
   before/after list.

**Verification gate (complete, in order):**

```
a. python3 bin/generate.py --all --force        exits 0
b. python3 bin/generate.py --audit              clean, exit 0
c. python3 -m pytest tests -q                   full suite green (96 existing + §9)
d. git status                                   only intended moves/edits; no depth-1
                                                remnant under skills/ (CI-enforced by C1
                                                from now on: a flat body fails generation)
e. Expected-churn check: regeneration log shows resync for codebase-map only;
   every other skill line absent (digest-equal copies untouched)
f. Harness probes against a TEMP CLONE of one regenerated home (never the
   template — probes write): CODEX_HOME=<clone> codex debug prompt-input
   renders exactly the selected leaves; GROK_HOME=<clone> grok inspect lists
   exactly the selected leaves; claude plugin validate --strict over the
   clone's skills/ passes. Re-run on the installed claude 2.1.259 per the
   synthesis's probe-aging note.
g. Codex/Grok name delta is exactly {$map -> $codebase-map}; Claude command
   set unchanged.
h. transport-matters acknowledges the digest move before the change merges.
```

---

## 9. Tests

Extend `tests/generate_support.py`: `write_skill(root, "tm/review/foo")`
already creates parents; it now derives frontmatter `name` from the last path
component. New/updated cases (existing 96 stay green modulo reworded audit
strings and hierarchical fixture ids):

Catalog (C-rules): depth-1 marker fatal; depth-4 fatal; bad component fatal;
marker-under-marker fatal both orders (group-with-marker, body-embedded);
missing frontmatter name fatal; name != leaf fatal; duplicate leaf across
owners fatal naming both ids; empty/missing root -> empty catalog.

Selection (S-rules): exact id resolves; `owner/*` and `owner/domain/*` expand
sorted; bare prefix without `/*` fails naming the `/*` form; non-trailing `*`
fails; required unknown id fatal; required empty set fatal; optional unknown
and optional empty set log-and-drop; overlap of set and exact id dedupes;
skill in both lists resolves required; expansion order is manifest order with
in-place splice.

Materialize/audit/clean: nested body materializes to flat leaf; prune removes
a stale leaf; digest-equal copy untouched after a pure `git mv` of its body
(the migration-churn property, asserted directly); resync gate still trips on
a copy edit and `--force` clears it; audit names an unowned leaf and an
out-of-sync copy by canonical id; `clean_residue` still reports
regenerate-needed for a removed skill copy; no-`$HOME`-read test unchanged.

Digest: `generated_from` changes when a body's domain changes; stable when
only an unrelated body moves.

Compiler/manifest: array `skills` form is a hard error; `schema_version` 3
rejected, 4 accepted; `RuntimePlan.skills` carries entries in selection order.

---

## 10. Rationale: the three shapes compared

**A. Path-derived ids (chosen).** Identity = location under `skills/`.
One source of truth with zero copied metadata: the tree *is* the catalog, and
the only duplicate anywhere (frontmatter `name` vs leaf) is harness-mandated
and validator-pinned. Discovery mirrors the runtime pattern
(`rglob(marker)`); grammar reuses the agent component; the generated plane
needs no mapping table because leaf extraction is a projection. Cost: moving a
body renames its public id, so a reorganization is a breaking rename of
manifest references. That cost is real and accepted: every consumer of a
skill id lives in this repo (manifests, logs, digests — `capabilities.json`
carries no skill list), so a move is a `git mv` plus a mechanical manifest
rewrite, atomically in one commit, and S2 makes a missed reference loud.

**B. Explicit per-skill metadata (frontmatter `id:`).** The agent precedent:
authored-in-file identity, location free to move. Rejected because the
precedent's premise does not transfer. An agent id is an externally addressed,
published identity (transport-matters launches by it; `capabilities.json`
carries it), so it must survive relocation independent of consumers this repo
does not control. A skill's catalog id has no external consumer; paying for
relocation-independence buys nothing here. What it costs: a new frontmatter
key in all 36 bodies whose value restates the path's owner/domain (copied
metadata — when the tree and the id disagree, the hierarchy this change
exists to express is ambiguous again, and "which one is real" needs yet
another validator); repo-internal identity shipped in harness-facing bytes
(the launcher spec calls frontmatter additive, but `skill-creator`'s
packaging validator and claude.ai upload paths reject unknown keys — gotcha
9); and the same C4-C6/S-rules are still all required, so B is a strict
superset of A's machinery plus one more invariant to police.

**C. Publisher bundle manifests (`bundle.toml` per owner/domain listing its
skills).** Rejected on direct evidence: membership acquires two sources of
truth (the tree and the list), which is the exact drift the reference report
documents in REFS — `plugin.json` needs a sync script and still disagreed
with the tree (22 vs 24 vs 25 over time). Every rubric-3 violation in this
problem space is some form of C. Bulk curation, its one genuine benefit, is
delivered by `prefix/*` selectors resolved against the tree — explicit at the
call site, no second file, and set membership can never disagree with the
catalog because it is computed from it.

**Sub-choices within A, also weighed:**
- *Nested generated output*: dismissed with the synthesis (Claude one-level
  evidence, probe-proven prune/audit thrash, phantom-skill leak to
  Codex/Grok, Grok resolved-path ignore complications). Flat output also
  keeps `audit`, `clean_residue`, and the prune loop nearly untouched —
  the smallest change area, probe-confirmed by the materialization report.
- *Separator-flattened segments* (`tm--review--code-review`): renames every
  Claude command and every Codex/Grok invocation, breaking operator habit and
  in-body skill references (gotcha 8) to buy duplicate-leaf tolerance, which
  C6 provides for free. Rejected.
- *Alias table for `map`*: a second identity axis for one skill, permanent;
  rejected in favor of a one-time consumer-visible rename (§8.2).
- *Variable unlimited depth*: rejected; `owner[/domain]/leaf` is the ask, and
  bounded depth keeps selectors, ids, and the tree readable. Depth 2 exists so
  a single vendored body does not need an invented domain.

**Rubric mapping:** (1) id is literally `owner[/domain]/skill` — §2. (2) flat
leaf output serves all three harnesses; C1-C6+S2 fail before any write — §5.
(3) tree is the sole membership source; leaf/owner/domain are projections; the
one mandated copy is validator-pinned — §2, §10. (4) capability filtering
untouched (required-entry intersection); digest keyed by id with a single
coordinated move; audit/clean/drift keep their exact semantics with a
leaf-keyed lookup — §3.3-3.5, §7. (5) manifests list ids or explicit `/*`
sets; empty required sets are fatal, optional ones logged; no bare-prefix
expansion — §1.2, §5. (6) one wave, flat shape deleted and then structurally
rejected, eight-step gate — §8.

---

## 11. Proven facts vs design choices

**Proven (code read, live probe, or official doc — inherited from the
synthesis and re-verified where cheap):** HEAD and dirty set; 96 tests pass;
flat one-level `catalog()`; `dest = skills_dir / name`; one-level audit walk
and `parent.name == "skills"` clean test; digest keyed `f"\n{name}\0"`;
agent grammar and `validate_catalog_identities`; Codex/Grok recursive home
discovery and duplicate-name visibility; Claude command-from-directory-name,
frontmatter `name` display-only outside plugins; Codex `name` required; Grok
`name` defaults to directory; nested-key thrash and grouping-leak shapes;
exactly one name mismatch (`codebase-map`/`map`), one `requires_capability`
(`helioy-imagegen`), zero nested markers, zero bare-array manifests (all
re-verified today at HEAD).

**Working assumptions (evidence-backed, unproven):** Claude one-level
discovery as prompt-inclusion behavior (docs + validator + loader text; probed
on 2.1.258, installed 2.1.259 — gate step f re-probes); Grok `[disabled]`
prompt semantics (moot under flat output).

**Design choices (mine, arguable):** path as identity rather than frontmatter
id (§10.B is the argument); depth bounded at 2-3 with owner mandatory;
catalog-wide rather than per-home leaf uniqueness; `name` == leaf enforced
with the `codebase-map` rename resolved toward the directory; trailing-`/*`
as the only set syntax with fatal-empty-required; `schema_version` 4 in the
same wave; the specific owner/domain assignment table (a proposal for the
owner to adjust; the mechanics are placement-agnostic).

**Residual risks:** the digest move requires transport-matters coordination
(gate step h makes it blocking); Codex/Grok users of `$map` see a one-time
rename; if Claude 2.1.259 changed discovery depth (no evidence it did), flat
output remains safe regardless — the constraint only tightens if Claude went
recursive AND a body embedded a marker, which C3 forbids.

---
title: Skill hierarchy and runtime materialization
type: research
tags: [agent-runtimes, skills, hierarchy, materialization, harnesses]
summary: Trace of skill discovery, copying, audit behavior, and harness visibility across Claude, Codex, and Grok.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

# Skill hierarchy and runtime materialization

## Scope and snapshot

This report traces how `/Users/alphab/.agent-runtimes` discovers committed skill bodies, resolves manifest declarations, copies skills into runtime templates, detects drift, and exposes the resulting tree to Claude, Codex, and Grok.

The checkout was at `71e3871ebbb8813fb213827f70e38fc4d83feafa`. It already contained modifications to `runtimes/generalist/runtime.toml`, `runtimes/tm-stu/runtime.toml`, and `skills/tm-orchestrate/SKILL.md`. This investigation did not change the repository or generated homes.

FMM has no index for this repository. `fmm_list_files` reported that `.fmm.db` is absent. I used read only file listings, Python AST inspection, targeted source reads, temporary directory probes, and the existing tests.

## Components found

| Component | Location | Responsibility |
| --- | --- | --- |
| CLI entry point | `bin/generate.py:144-365` | Resolves runtime paths, loads the runtime catalog, audits targets, compiles plans, materializes homes, and implements `--catalog`, `--audit`, `--clean`, and `--all`. |
| Skill catalog | `bin/agent_runtime_compiler/skills.py:37-50` | Treats an immediate child of the configured skill root as an owned skill only when that child contains `SKILL.md`. The dictionary key is the child directory name. |
| Skill tree digest | `bin/agent_runtime_compiler/skills.py:53-70` | Hashes every relative path, directory entry, executable bit, and file byte in one skill body. |
| Skill copier | `bin/agent_runtime_compiler/skills.py:73-121` | Prunes unwanted immediate children from a runtime's `skills/` directory and replaces each selected skill with a full `shutil.copytree` copy. |
| Manifest skill resolver | `bin/agent_runtime_compiler/manifest.py:216-295` | Validates lists of strings, preserves first occurrence order, and returns the combined and required skill lists. |
| Capability resolver | `bin/agent_runtime_compiler/capabilities.py:64-213` | Reads `requires_capability` from required skill frontmatter, intersects allowed vendors, and narrows the declared harness set. |
| Pure plan | `bin/agent_runtime_compiler/compiler.py:55-197` | Builds a frozen `RuntimePlan` containing selected skill names, all owned body paths, targeted harnesses, config documents, capability data, and logs. |
| Filesystem writer | `bin/agent_runtime_compiler/writers.py:35-61` | Writes the shared skill tree first, then instructions and harness config files, removes files for untargeted harnesses, and writes `capabilities.json`. |
| Template audit | `bin/agent_runtime_compiler/audit.py:47-168` | Allows generated names and Git tracked names, compares immediate materialized skill children with owned bodies, reports foreign paths, and reports runtime directories whose manifest disappeared. |
| Shared instruction writer | `bin/agent_runtime_compiler/writers.py:64-89` | Copies one committed instruction body into `AGENTS.md` and `CLAUDE.md`, unless the manifest redacts home instructions. |
| Launcher boundary | `AGENTS.md:45-52`, `README.md:61-77` | Transport Matters clones templates into run homes, sets each harness home variable, seeds auth, and swaps `config.grok.toml` into the `config.toml` slot for Grok. |

The repository currently owns 36 top level skill bodies containing 180 files and about 1.9 MB. It has ten runtime manifests. The generated runtime skill sets range from zero to 22 immediate skill directories.

## Flow

1. `main()` selects one CLI action. Generation enters `regenerate()` for one runtime or every directory returned by `all_runtime_dirs()`. Runtime discovery uses `rglob("runtime.toml")`, so nested runtime groups are supported independently of skill discovery. See `bin/generate.py:320-365` and `bin/generate.py:299-300`.

2. `regenerate()` builds the current owned skill catalog and audits every target before writing any target. It collects only `Residue.resync` findings. These are owned skill copies whose digest differs from the current body. Without `--force`, any such finding aborts the whole requested set. See `bin/generate.py:260-296`.

3. `apply()` validates all runtime catalog identities when the target sits under the configured runtime root. Duplicate runtime agent IDs and fixed names fail before materialization. Skill loader names receive no equivalent validation. See `bin/generate.py:149-180`, `bin/agent_runtime_compiler/manifest.py:161-183`, and `tests/test_generate_identity.py:101-137`.

4. `compiler.plan()` parses required and optional skill names, calls `skills.catalog()`, derives capability constraints from required skill frontmatter, and narrows the default Claude, Codex, and Grok targets. A missing required skill fails. A missing optional skill is removed with a log entry. Optional skills never constrain vendors. See `bin/agent_runtime_compiler/compiler.py:71-115` and `bin/agent_runtime_compiler/compiler.py:164-216`.

5. `writers.materialize()` calls `skills.materialize()` once for the home. All targeted harnesses therefore receive the same physical `<home>/skills` tree. The generator does not build separate skill sets for Claude, Codex, and Grok. See `bin/agent_runtime_compiler/writers.py:42-61`.

6. `skills.materialize()` validates selected catalog keys, creates `skills/` when needed, removes every immediate child whose name is absent from the desired set, and copies each selected body to `skills/<catalog-key>`. A matching digest preserves the existing copy and its modification time. Any other existing destination is removed before a full copy. See `bin/agent_runtime_compiler/skills.py:81-121`.

7. Each harness discovers and parses skills after Transport Matters launches the run home. The generator controls bytes and paths up to that point. Loader precedence, frontmatter validity, prompt inclusion, and invocation resolution belong to each harness.

```text
runtime.toml
    |
    v
manifest.resolve_skills
    |
    +--> skills.catalog(skills/) --> {directory key: body path}
    |
    +--> capabilities.vendor_constraint(required bodies)
    |
    v
compiler.plan -> RuntimePlan
    |
    v
writers.materialize
    |
    +--> skills.materialize -> runtimes/<runtime>/skills/<directory key>/
    +--> instruction and config writers
    +--> capabilities.json
    |
    v
Transport Matters run overlay
    |
    +--> Claude loader
    +--> Codex loader
    +--> Grok loader
```

## Current invariants

### Source discovery is flat

`skills.catalog()` calls `root.iterdir()`, then checks `entry/SKILL.md`. It never recurses. A grouping directory without its own marker is invisible, including every marked descendant. A grouping directory with its own marker becomes one skill body. Any nested `SKILL.md` under that body is copied and hashed as an ordinary file inside the parent body.

The current tree conforms to this rule. All 36 markers sit at `skills/<directory>/SKILL.md`; there are no nested skill markers.

### Catalog identity and loader identity can differ

The manifest and copier use the top level directory name. The generator only parses `requires_capability` from frontmatter. It does not validate the frontmatter `name`, compare it with the directory, or enforce uniqueness.

The existing `codebase-map` body proves the distinction. `runtimes/codebase-mapper/runtime.toml:7-8` selects `codebase-map`; the copied directory is `skills/codebase-map`; its frontmatter name is `map` at `skills/codebase-map/SKILL.md:1-4`. Codex and Grok present loader names from frontmatter, so the runtime manifest key and invocation name can differ.

`manifest.dedupe()` removes repeated identical manifest strings. It cannot detect two different catalog keys whose frontmatter names collide. The current 36 bodies have no duplicate frontmatter names, but no test or production check preserves that fact.

### Materialization is copy based and convergent

The destination is a real directory. `shutil.copytree` copies all supporting files and preserves executable bits. A copy is never merged with its source or prior destination. Full replacement prevents deleted source files from surviving in a generated home.

A runtime with no selected skills does not gain an empty `skills/` directory when none exists. If an empty directory already exists, the copier leaves it in place.

### Drift detection is content based for skills only

`tree_digest()` includes the relative tree shape, file bytes, and executable bits. Ordering cannot change the digest. A new cache directory, a changed reference file, or a changed executable bit makes a materialized owned skill stale.

The audit checks generated and tracked top level names by shape. It does not compare generated config or instruction bytes against a fresh plan. Its strong content comparison applies to owned skill copies.

A stale owned copy sets `Residue.resync=True`. Regeneration refuses to overwrite it until the operator supplies `--force`, because the generator cannot distinguish a source edit from a harness write into the template. A top level foreign skill such as `skills/.system` has no owned body, so `--audit` reports it and ordinary materialization prunes it as an unwanted immediate child. Foreign paths outside `skills/` survive ordinary generation and require `--clean`.

### Clean follows audit findings

`clean_residue()` calls the same root audit, removes each exact finding with `remove_path()`, and reports when a skill copy needs regeneration. It preserves generated config and Git tracked auxiliary files. Orphan runtime directories are findings at the runtime root and `--clean` removes the full orphan. See `bin/generate.py:209-234` and `bin/agent_runtime_compiler/audit.py:150-168`.

### Capability derivation observes required catalog entries only

`vendor_constraint()` reads the frontmatter of required entries returned by the flat catalog. Optional skill metadata does not narrow harnesses. A nested `SKILL.md` hidden inside a parent body cannot contribute capabilities unless the parent itself declares them. See `bin/agent_runtime_compiler/capabilities.py:176-213`.

## Harness visible layout

| Owner | Proven behavior | Limit |
| --- | --- | --- |
| Generator | Writes one shared `<home>/skills/<catalog-key>/...` tree for every targeted harness. `SKILL.md` is the only marker used for catalog membership. | It does not prove that a harness accepts the frontmatter or invokes the intended skill. |
| Claude Code 2.1.258 | A no login debug start reported the user skill root as `CLAUDE_CONFIG_DIR/skills`. The installed binary describes auto loaded entries as `.claude/skills/*`. `claude plugin validate --strict <skills>` validated an immediate child and ignored a malformed `skills/group/child/SKILL.md`. | These are loader diagnostics and validator behavior. No offline prompt renderer exists in the tested CLI, so actual nested prompt inclusion was not rendered. The evidence points to immediate child discovery and against preserved nested output. Duplicate frontmatter name behavior remains unproven. |
| Codex CLI 0.153.0 | `CODEX_HOME=<temp-home> codex debug prompt-input` rendered both `skills/beta/SKILL.md` and `skills/group/alpha/SKILL.md`. A second probe with two nested skills sharing one frontmatter name rendered both entries and both paths. OpenAI's current Build skills documentation also says same name skills are not merged and both can appear in selectors. | Duplicate selection is inherently ambiguous to a human and model even though both entries remain visible. |
| Grok 1.0.13 | `GROK_HOME=<temp-home> grok inspect --json` discovered an immediate skill and a nested `skills/group/alpha/SKILL.md`. A duplicate name probe listed both nested skills with their separate source paths. Grok's bundled user guide says configured skill paths are walked recursively. | `grok inspect` proves discovery, not prompt inclusion or invocation choice. Duplicate invocation resolution was not tested. The known plugin inheritance gap also means the generated tree may not be Grok's full effective skill set under an operator HOME. See `AGENTS.md:176-247`. |

The probes ran only against temporary directories. They confirmed the existing audit warning that Codex creates `.system`, `installation_id`, and `tmp/`, while Grok creates session and user guide files. No probe pointed a harness at a repository template.

## Likely effects of nested source directories

### A markerless grouping directory disappears

For this source shape:

```text
skills/team/alpha/SKILL.md
```

the current catalog returns no entry. A manifest requiring `alpha` or `team/alpha` fails as unknown. An optional declaration logs that the skill is absent and skips it.

A temporary probe against the current `catalog()` returned `{}` for this exact shape.

### A marked grouping directory can leak undeclared children

For this shape:

```text
skills/team/SKILL.md
skills/team/alpha/SKILL.md
```

the current catalog contains only `team`. The copier reproduces the full subtree. Capability derivation reads only `team/SKILL.md`.

Codex and Grok recursively discover the nested `alpha` marker in the generated home. Claude's current diagnostics point to immediate child discovery. The same generated bytes can therefore yield extra Codex and Grok skills, no matching Claude skill, and no capability constraint from `alpha`. Audit still treats the whole subtree as the `team` body and can detect byte drift, but it cannot express `alpha` as a separately selected skill.

### Recursive catalog keys cannot be passed through unchanged

Changing only `catalog()` to return `{"team/alpha": body}` does not make the rest of the pipeline hierarchy safe.

A temporary probe passed that mapping to the current copier. The first run wrote `skills/team/alpha`, then the audit reported `skills/team` as an unowned skill. The second run removed `skills/team` during immediate child pruning and copied `alpha` again. Every run therefore reports a removal and addition. `--clean` would remove the full `team` directory because the audit finding sits at that immediate child.

Path preserving output requires coordinated changes to copy, prune, audit, clean, collision rules, and tests.

### Flattened output has the smallest change area

Source grouping can stay invisible to harnesses if discovery walks source directories and materialization still writes one validated skill per immediate `<home>/skills/<loader-name>` child. This preserves the current Claude compatible shape and lets the existing copy and digest logic continue to work.

Flattening adds a required decision that the current code avoids. Two source paths can share a leaf directory name, and two different directories can declare the same frontmatter name. Either collision must fail before any runtime write. Codex and Grok currently keep duplicate names visible; that behavior does not provide a portable or clear invocation contract. Claude's behavior is unproven.

The safest registry shape would distinguish:

* a stable manifest key, potentially the source relative path;
* the source body path;
* the harness visible name and flat destination.

The current `dict[str, Path]` collapses these concepts. The `codebase-map` versus `map` example shows they are already distinct.

## Reuse map

| Existing unit | Reuse | Needed adjustment for grouped sources |
| --- | --- | --- |
| `skills.tree_digest()` | Reuse unchanged for each leaf body. It already handles nested support files and executable bits. | Call it on each discovered skill leaf, never on a grouping directory that contains other skills. |
| `skills.remove_path()` | Reuse unchanged for leaf replacement and clean. | Do not hand it a shared grouping parent when one child is the finding. Flat output avoids this risk. |
| Copy and full replacement in `skills.materialize()` | Reuse for flat output. | Accept resolved entries rather than assuming manifest key equals destination directory. |
| `manifest.resolve_skills()` and `dedupe()` | Reuse required versus optional semantics and declaration order. | Resolve stable manifest keys to registry entries before writing. Dedupe does not replace collision validation. |
| `capabilities.vendor_constraint()` | Reuse its required only capability intersection. | Read frontmatter through the resolved entry body. A catalog validation pass should reject invalid or duplicate loader names before this stage. |
| `compiler.RuntimePlan` | Keep the pure desired state boundary. | Replace parallel raw names and body mappings with immutable resolved skill entries, or add an explicit manifest key to destination mapping. |
| `writers.materialize()` | Reuse its ordering and single shared skill write. | No harness specific skill writer is needed if output stays flat and portable. |
| `audit.Residue`, `audit_root()`, and regenerate's whole set gate | Reuse the finding model and prewrite gate. | Audit the expected flat destinations from the same validated catalog. Preserve independent expectations instead of importing writer constants. |
| `validate_catalog_identities()` pattern | Reuse the fail before write pattern. | Add skill registry validation for duplicate manifest keys, duplicate flat destinations, and duplicate frontmatter names. |
| `tests/test_skills.py` and `tests/generate_support.write_skill()` | Reuse the existing temporary root test design. `write_skill(root, "group/alpha")` already creates parents. | Add explicit cases for markerless groups, nested leaf discovery, duplicate leaf basenames, duplicate frontmatter names, flat output, capability derivation, audit, clean, and unchanged regeneration. |

## Boundaries

### Generator controlled

* Which committed bodies qualify for the catalog.
* Which manifest declarations are required or optional.
* Which required capabilities narrow harnesses.
* The exact copied bytes, paths, and executable bits in a runtime template.
* Pruning, drift reporting, force gated resynchronization, and clean behavior.
* The shared instruction copies and harness config files.

### Transport Matters controlled

* Cloning the template into a per run overlay.
* Keeping harness writes away from the template.
* Seeding credentials and trust.
* Setting `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, or `GROK_HOME`.
* Moving the Grok config into the filename Grok reads.
* Applying caller constraints published in `capabilities.json`.

### Harness controlled

* Skill root scanning depth and precedence.
* Frontmatter parsing and accepted metadata.
* Name collision display and invocation behavior.
* Progressive disclosure and final prompt inclusion.
* Built in, plugin, user, repository, and compatibility skill sources.

The generator's flat, copied tree is the only common contract presently supported by evidence across all three harnesses. Codex and Grok can scan deeper, but preserving hierarchy in generated homes would rely on behavior Claude does not appear to share.

## Non-obvious things

* `SKILL.md` has two roles. It marks a body for this generator and carries loader metadata for harnesses. The generator validates only one custom field, so marker acceptance does not imply loader validity.
* A nested runtime directory and a nested source skill directory behave differently. Runtime discovery uses `rglob`; skill discovery uses `iterdir`. `tests/test_skills.py:641-649` covers nested runtime grouping only.
* `.gitignore` hides generated `runtimes/*/skills/` because the copies total about 1.9 MB. `--audit` supplies the content check Git status cannot provide. See `.gitignore:1-18`.
* `generated_from` hashes the manifest bytes and required skill frontmatter, not full skill bodies. Full body drift is the audit's job; Transport Matters separately digests template bytes when it needs output identity. See `bin/agent_runtime_compiler/capabilities.py:176-213` and `README.md:257-263`.
* Grok's baseline reduces ambient skill discovery but does not close plugin inheritance from `$HOME/.claude`. `baselines/config.grok.toml:1-37` documents the partial isolation. A generated skill tree and Grok's effective skill set can still differ under a real operator HOME.
* The comment at `bin/agent_runtime_compiler/skills.py:37-39` says "both harnesses" even though the runtime now targets three. Its marker claim remains functionally true, but its count is stale.
* `tracked_names()` projects Git tracked names using the first two path components. A nested runtime can pass the orphan test, but a tracked auxiliary file inside a nested runtime would not be attributed to the leaf runtime by the current mapping. The existing nested runtime test does not cover that case.

## Files read

* `AGENTS.md`
* `README.md`
* `.gitignore`
* `baselines/settings.json`
* `baselines/config.toml`
* `baselines/config.grok.toml`
* `bin/generate.py`
* `bin/agent_runtime_compiler/skills.py`
* `bin/agent_runtime_compiler/writers.py`
* `bin/agent_runtime_compiler/audit.py`
* `bin/agent_runtime_compiler/compiler.py`
* `bin/agent_runtime_compiler/manifest.py`
* `bin/agent_runtime_compiler/capabilities.py`
* `tests/generate_support.py`
* `tests/test_skills.py`
* relevant sections of `tests/test_generate.py` and `tests/test_generate_identity.py`
* `skills/skill-matters/SKILL.md`
* `skills/codebase-map/SKILL.md`
* representative runtime manifests and generated homes for `generalist`, `frontend`, `imagegen`, and `codebase-mapper`
* OpenAI Build skills documentation at <https://learn.chatgpt.com/docs/build-skills>
* installed Claude Code 2.1.258 loader diagnostics and validator
* installed Codex CLI 0.153.0 offline prompt renderer
* installed Grok 1.0.13 inspector and bundled user guide

## Verification

* `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests -q`: **96 passed in 0.66 seconds**.
* `PYTHONDONTWRITEBYTECODE=1 python3 bin/generate.py --audit`: **clean**, no residue under `runtimes/`.
* Repository status after tests matched the initial three modified files.
* A current code probe confirmed that a markerless nested source returns an empty catalog.
* A current code probe confirmed that path preserving `team/alpha` output conflicts with immediate child pruning and audit ownership.
* Codex offline prompt probes confirmed recursive discovery and duplicate name visibility.
* Grok inspector probes confirmed recursive discovery and duplicate name visibility.
* Claude loader diagnostics confirmed the configured user skill root. Its validator and installed loader text point to immediate child discovery. Nested prompt inclusion remains unproven.

## Open questions

1. Claude Code has no offline prompt input renderer comparable to Codex. A live capture would be needed to close nested skill inclusion and duplicate name behavior for Claude 2.1.258.
2. Grok inspector output does not prove that every discovered enabled skill reaches the model prompt or how an explicit invocation chooses between duplicate names.
3. The desired public identity for grouped sources is unspecified. A source relative manifest key and a flat frontmatter based loader name fit the evidence, but the owner must choose the stable contract.
4. The current `codebase-map` versus `map` mismatch may be intentional compatibility. Any new validation must either encode aliases explicitly or migrate the manifest key.

---
title: Skill organization and installation conventions
type: research
tags: [agent-runtimes, skills, hierarchy, references, installation]
summary: Comparison of skill organization, identity, installation, and collision handling in agent-runtimes and mattpocock/skills.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

# Skill organization and installation conventions

Comparison of two local trees. Read-only. No harness was launched for this report.

**Trees and HEADs (verified 2026-09-03)**

| Tree | HEAD | Working tree |
| --- | --- | --- |
| `/Users/alphab/Dev/LLM/DEV/helioy/REFS/skills` | `6654f6b60cd9d5be8b54c6fafe44346dabeb3b76` (`6654f6b feat: add 'Information access' category to retrospective skill for improved agent insights`) | clean, `main...origin/main` |
| `/Users/alphab/.agent-runtimes` | `71e3871ebbb8813fb213827f70e38fc4d83feafa` (`71e3871 feat: compose harness configs from committed baselines`) | dirty: `runtimes/generalist/runtime.toml`, `runtimes/tm-stu/runtime.toml`, `skills/tm-orchestrate/SKILL.md` |

Requested REFS HEAD matches. agent-runtimes skill-body evidence below is the working tree for `skills/tm-orchestrate` and committed bodies for everything else.

## Overview

Both trees ship Agent Skills as directories that contain a `SKILL.md`. They disagree about almost every surrounding convention: how skills are grouped, who is allowed to see which ones, how they reach a harness, what identity is (directory name versus frontmatter `name`), and how collisions are handled.

`REFS/skills` is a public skill library (`package.json` name `mattpocock-skills`). It organizes skills into promotion buckets, ships a curated subset as a Claude Code plugin, and installs the rest by flattening directory basenames into the operator's global skill stores (`~/.claude/skills`, `~/.agents/skills`) or by copying files into a project via the external `npx skills` installer.

`.agent-runtimes` is a runtime generator. It owns a flat catalog of skill bodies under `skills/<name>/`, copies named subsets into isolated config homes under `runtimes/<name>/skills/`, and treats those homes as dual-target templates for Claude (`CLAUDE_CONFIG_DIR`), Codex (`CODEX_HOME`), and Grok (`GROK_HOME`). Isolation is the product. Generation must not read `$HOME` for skill content.

The reusable idea in both is the same unit: one directory, one `SKILL.md`, hyphen-case basename, optional bundled files. The rest is repository-specific: buckets and a plugin manifest versus a generator catalog and per-home copies.

## Key Concepts

**Skill body.** A directory whose identity for discovery is the presence of `SKILL.md`. REFS `scripts/link-skills.sh` and `scripts/list-skills.sh` find that file recursively. agent-runtimes `skills.catalog()` (`bin/agent_runtime_compiler/skills.py`) only accepts an immediate child of `skills/` that carries `SKILL.md`. Nested `SKILL.md` files do not exist in either tree today.

**Frontmatter identity.** Every `SKILL.md` in both trees starts with YAML `name` and `description`. REFS directory basename equals frontmatter `name` for all 37 skills. agent-runtimes has one mismatch: directory `skills/codebase-map/` with frontmatter `name: map`. The generator keys on the directory name, never the frontmatter `name`.

**Buckets (REFS only).** `skills/engineering/`, `skills/productivity/`, `skills/misc/`, `skills/in-progress/`, `skills/deprecated/`. Engineering and productivity are **promoted**: they must appear in the top-level `README.md` and in `.claude-plugin/plugin.json`'s `skills` array. The other three must not. `personal/` existed and was deleted (`CHANGELOG.md` 1.2.0); the ADR at `.agents/adr/0002-ship-as-a-claude-code-plugin.md` still names it.

**User-invoked versus model-invoked (REFS only).** Encoded twice, kept in sync by `.agents/invocation.md`: Claude frontmatter `disable-model-invocation: true`, Codex `agents/openai.yaml` `policy.allow_implicit_invocation: false`. 22 of 37 REFS skills are user-invoked; 15 are model-invoked. agent-runtimes owned bodies set neither flag.

**Runtime home (agent-runtimes only).** One directory serving three harness config surfaces. Skills are the only shared namespace: both Claude and Codex read `<home>/skills/<name>/SKILL.md` (`skills/skill-matters/SKILL.md` table). Codex and Grok cannot share one `config.toml`; Grok's file is `config.grok.toml`.

**Required versus optional (agent-runtimes only).** `runtime.toml` `[skills].required` missing from the catalog is fatal (`unknown skill`). `[skills].optional` missing is skipped with a log line (`compiler._drop_missing_optional`). Only required skills contribute `requires_capability` to vendor constraint.

**Capability (agent-runtimes only).** `helioy-imagegen/SKILL.md` declares `requires_capability: ["image-generation"]`. `capabilities.toml` maps that string to vendors `openai` and `xai`. `capabilities.vendor_constraint()` intersects those vendors and drops harnesses whose vendor is absent. That is why `tm/imagegen` does not serve Claude.

## How It Works

### 1. How REFS lays out a skill

A skill lives at `skills/<bucket>/<name>/` with `SKILL.md` plus, in this tree, `agents/openai.yaml` beside every skill (37 of 37). Extra files are skill-owned reference (`tdd/tests.md`, `domain-modeling/ADR-FORMAT.md`), scripts (`diagnosing-bugs/scripts/hitl-loop.template.sh`), or templates (`setup-matt-pocock-skills/*.md`).

Counts at HEAD `6654f6b`:

| Bucket | Skill directories with `SKILL.md` | Shipped in plugin | Docs page |
| --- | --- | --- | --- |
| `engineering/` | 18 | yes | `docs/engineering/<name>.md` |
| `productivity/` | 7 | yes | `docs/productivity/<name>.md` |
| `in-progress/` | 8 | no | none |
| `misc/` | 4 | no | none |
| `deprecated/` | 0 (README only) | no | none |

`.claude-plugin/plugin.json` lists 25 explicit paths, equal to the 25 promoted directories. Example entries: `"./skills/engineering/ask-matt"`, `"./skills/productivity/grill-me"`. The plugin `name` is `mattpocock-skills`, `version` `1.2.3`, kept in sync with `package.json` by `scripts/sync-plugin-version.mjs`.

`.claude-plugin/marketplace.json` names a single-plugin marketplace `mattpocock`. `.agents/install-block.md` says this is a fallback for installing an unreleased commit or a fork, not the documented user route. The documented Claude route is the official marketplace listing.

Human-facing docs are a parallel tree, not a second skill store. `.agents/writing-docs.md` says the published URL is always `https://aihero.dev/skills-<skill-name>` regardless of bucket, so the docs path is repo organisation only. Pages carry no install commands; the site widget owns those.

`ask-matt` is a hand-maintained router over the promoted set (`skills/engineering/ask-matt/SKILL.md`). `CLAUDE.md` requires it to be updated when a user-reachable skill is added, renamed, removed, or rerouted. It does not scan the filesystem.

Repo-root `AGENTS.md` is a symlink to `CLAUDE.md` (`CHANGELOG.md` 1.2.0: so Codex reads the same repo instructions). agent-runtimes homes do the opposite: they copy one body to both names because a template must be self-contained (`AGENTS.md` in agent-runtimes: "an import is claude-only syntax").

`CONTEXT.md` in REFS is a domain glossary for this skill set (Issue tracker, Issue, Decision ticket, Triage role), not a skill catalog.

### 2. How REFS installs

Three documented routes, plus one maintainer script. README and `.agents/install-block.md` say pick one of the two user routes: installing both leaves every skill twice.

**Claude plugin (promoted set only).** `claude plugins install mattpocock-skills` or in-session `/plugin install mattpocock-skills`. ADR 0002 records a 2026-08-05 measurement on Claude Code 2.1.222: CLI install resolved as `mattpocock-skills@claude-plugins-official` with no marketplace added first. The listing's git SHA is pinned, so a release reaches installed users when that pin moves. In-session `/plugin install` was not exercised in that write-up (`/plugin` unavailable in `claude -p`). **Not re-run for this report.**

**skills.sh (universal, project-local copies).** `npx skills@latest add mattpocock/skills`, optional `--skill=<name>`. This installer is not in the REFS repo. It is an external package. `find-skills` in agent-runtimes documents the same CLI (`npx skills find`, `npx skills add`, `-g` for global). How that installer discovers nested `SKILL.md` files, which buckets it offers, and where it writes per harness is **unproven in these two trees**. REFS `skills/in-progress/README.md` says a beta skill is installable with `--skill=<name>` and that "the plugin won't give you these." CHANGELOG 1.2.0 says skills.sh "serves every skill in the repo," which is why deleting non-plugin skills still removes them from that listing.

**Maintainer link script.** `scripts/link-skills.sh` is labelled "dev-only" and "not a supported installer." It:

1. `find`s every `SKILL.md` under `$REPO/skills` except `node_modules` and `deprecated`.
2. Takes `basename` of the skill directory, discarding the bucket.
3. Symlinks that basename into `$HOME/.claude/skills` and `$HOME/.agents/skills`.
4. Uses `ln -sfn`, so an existing symlink is replaced.
5. If `$DEST/$name` exists and is **not** a symlink, `rm -rf` then links. A real directory at that name is destroyed.
6. Bails if `$DEST` itself is a symlink into the repo, to avoid writing links back into `skills/`.

`scripts/list-skills.sh` is a thinner finder: every `SKILL.md` except `node_modules`, **including** `deprecated/`. The two scripts disagree about deprecated.

Because install flattens to basename, bucket is invisible to the harness. Two skills in different buckets with the same directory name would overwrite each other in `~/.claude/skills`. At this HEAD every frontmatter `name` is unique, so that collision is latent.

Codex native plugin is deferred. ADR 0002 states the blocker: `.codex-plugin/plugin.json` accepts `skills` only as a **single path string** (arrays rejected with `missing or invalid plugin.json`), and Codex discovers `SKILL.md` recursively under it. Pointing at `./skills/` would ship `deprecated/`, `in-progress/`, and `misc/`. A flat directory of **symlinks** "does not survive install: Codex copies the plugin tree into its cache and **drops symlinks**, so the skills arrive empty." That is a documented measurement in the ADR, **not re-run here**.

### 3. How agent-runtimes lays out a skill

Owned bodies live at `skills/<name>/SKILL.md`. `skills.catalog()` maps `entry.name -> entry` for immediate children that contain `SKILL.md`. A REFS-style `skills/engineering/tdd/SKILL.md` would be invisible to this catalog: `engineering/` has no `SKILL.md` of its own.

36 owned bodies. Every one is named by at least one `runtime.toml` (`required` or `optional`). Empty homes `tm/capture` and `tm/stu` declare no skills.

Frontmatter actually used by owned bodies:

| Key | Who uses it | Who reads it |
| --- | --- | --- |
| `name` | all 36 | harnesses (claimed); generator ignores it |
| `description` | all 36 | harnesses (claimed); generator ignores it |
| `requires_capability` | `helioy-imagegen` only | `capabilities._skill_frontmatter()` |
| `license` | `skill-creator` | unused by generator |
| `disable-model-invocation` | none | n/a |
| `agents/openai.yaml` | `impeccable`, `helioy-imagegen`, `helioy-imagegen-primatives` | unused by generator; copied through as tree content |

`helioy-imagegen-primatives` does **not** declare `requires_capability`. `docs/specs/2026-06-17-launcher-home-spec.md` still says both imagegen skills require `image-generation`. The live binding is `helioy-imagegen` required, primatives optional (`runtimes/imagegen/runtime.toml`). The spec is stale on that point.

`skill-creator/scripts/quick_validate.py` allows only `{name, description, license, allowed-tools, metadata}`. It would reject REFS `disable-model-invocation` and agent-runtimes `requires_capability`. The validator is a vendored Anthropic helper shipped as a skill; the generator does not run it.

`skill-creator/SKILL.md` further tells authors "Do not include any other fields in YAML frontmatter" and "These are the only fields that Claude reads to determine when the skill gets used." That claim about Claude is **unproven in this repo**. REFS treats `disable-model-invocation` as a Claude-read field. agent-runtimes treats `requires_capability` as a generator-read field.

Name mismatch: `codebase-map` is the catalog key and the home path `runtimes/codebase-mapper/skills/codebase-map/`. Frontmatter `name: map` is what a harness that keys on frontmatter would expose as the slash command. **Whether Claude or Codex uses directory name or frontmatter `name` is unproven here.**

### 4. How agent-runtimes installs (generates)

There is no user installer and no symlink farm. Flow:

1. Author `runtimes/<name>/runtime.toml` with `[skills].required` / `[skills].optional`.
2. `compiler.plan()` calls `manifest.resolve_skills()`, `skills.catalog(skill_root)`, `capabilities.vendor_constraint()` on required skills, then `_drop_missing_optional()`.
3. `writers.materialize()` calls `skills.materialize(home, names, owned)`.

`skills.materialize()` (`skills.py`):

- Unknown names: `SystemExit("unknown skill: ...")`.
- No names and no `skills/` directory: leave the home bare (this is `tm/capture`).
- Prune entries under `skills/` that are not in the wanted set (`- skill <name>`).
- For each wanted name: if dest is a real directory whose `tree_digest` matches the body, leave it. Otherwise delete (file, symlink, or tree) and `shutil.copytree`. Log `+ skill` on add, `~ skill <name>: resynced` on replace.

`tree_digest` hashes relative path, directory/file, executable bit, and bytes. Nothing is excluded. A `__pycache__` or a harness-written `.system` inside a copy makes the digest differ (`tests/test_skills.py::test_audit_names_a_skill_a_harness_wrote_into`).

Regenerate (`generate.regenerate`) audits all targets first. A copy that does not match its body is `resync=True` residue. Without `--force`, generation stops:

```
N skill copy(ies) in M template(s) do not match their owned body.
If you edited the body, rerun with --force to redistribute it.
If you did not, a harness wrote into a template: find out how before
overwriting the evidence.
```

`--audit` names residue the generator did not write: harness files (`installation_id`), instance dirs (`projects/`, `sessions/`), unknown skill dirs (`skills/.system`), out-of-sync copies, and orphan homes whose `runtime.toml` is gone (`audit.audit_orphans`). `codex debug prompt-input` against a template is documented to leave `installation_id`, `.sandbox_migration`, `tmp/`, and `skills/.system`. One measured overlay bug: a **symlinked** `skills/` directory let 86 paths write back into a template (`audit.py` module docstring). The intended overlay shape is real directories with leaf-file symlinks. That overlay is owned by transport-matters, **not re-measured here**.

`python3 bin/generate.py --catalog` prints owned directory names, not frontmatter names. MCP discovery is the documented `$HOME` exception (`catalogs.py`); skills are not.

Homes that ship skills, from current `runtime.toml` files:

| Runtime id | Required | Optional |
| --- | --- | --- |
| `tm/codebase-mapper` | `codebase-map` | |
| `tm/frontend` | 12 design skills | 9 transform verbs + `teach-impeccable` |
| `tm/generalist` | `code-review`, `pull-request` | `snapshot`, `tm-orchestrate` |
| `tm/imagegen` | `helioy-imagegen` | `helioy-imagegen-primatives` |
| `tm/orchestrator` | `tm-orchestrate` | |
| `tm/research` | `distill`, `excalidraw-diagram`, `my-voice`, `blog-architect` | `find-skills`, `snapshot` |
| `tm/skill-matters` | `skill-matters`, `skill-creator` | `find-skills` |
| `tm/capture` | (none) | (none) |
| `tm/stu` | (none) | (none) |
| `tm/transcript-matters` | `transcript-search` | `distill` |

`tm/stu` additionally sets Claude `disableBundledSkills = true` and several `CLAUDE_CODE_DISABLE_*` env vars. Comments cite claude 2.1.237 request-payload measurements (2026-08-20) showing bundled skills and explore/plan agents in the system prompt. **Those numbers are documented measurements, not re-run here.**

### 5. Collision handling

**Inside REFS.** Uniqueness is a convention, not an encoder. `link-skills.sh` last-writer-wins on basename. Plugin install namespaces under `mattpocock-skills:` according to `docs/engineering/code-review.md` (user-reported). A plain skills install shadows Claude's built-in `/code-review`. The docs page says this is unfixed: marketplace prefix hides the built-in; file install hides the built-in the other way. Fork-and-rename is the durable workaround because `npx skills update` overwrites frontmatter and directory renames. **Winner-takes-unqualified-name is documented from user reports, not proven by code in this tree.**

**Inside agent-runtimes.** Catalog keys are directory names; two bodies cannot share a directory. Two homes may copy the same body independently (`distill` is required in `tm/research` and optional in `tm/frontend` and `tm/transcript-matters`). A home that accumulates an extra dir under `skills/` is residue (`not a skill this repo owns`). A harness write into a copy is residue (`out of sync`). Replacement is whole-tree, never merge, so a file the body no longer has cannot survive.

**Across the two trees.** The only shared directory name is `code-review`. The bodies are different:

- REFS `skills/engineering/code-review/SKILL.md`: two-axis Standards/Spec review of `git diff <fixed-point>...HEAD`, model-invoked, calls the Skill tool, depends on `docs/agents/issue-tracker.md`.
- agent-runtimes `skills/code-review/SKILL.md`: GitHub PR candidate-finding fan-out, read-only, `gh pr view`, no `disable-model-invocation`.

If an operator still runs REFS `link-skills.sh` into `~/.claude/skills` / `~/.agents/skills` and also launches an agent-runtimes home, the two `code-review` skills occupy different stores **unless** the harness also scans the global store. Claude/Codex against `CLAUDE_CONFIG_DIR`/`CODEX_HOME` are claimed not to leak personal skills (`skill-matters` "Verified contract"). Grok is documented to still scan `~/.agents/skills` (see Gotchas). Cross-store collision for Grok is therefore live on this machine if REFS is linked globally. **Whether REFS is currently linked into those dirs was not inspected** (out of scope: would be a `$HOME` read for content).

**Claude built-in versus authored.** REFS documents `/code-review` clash. agent-runtimes `tm/stu` tries to drop bundled skills via `disableBundledSkills` and `CLAUDE_CODE_DISABLE_CLAUDE_CODE_SKILL`. Other homes do not.

### 6. What each tree assumes about harness discovery

**Shared, encoded as comments rather than tests.** `skills.py`: "Both harnesses require [`SKILL.md`], so it doubles as the marker." `skill-matters`: both Claude and Codex read `<home>/skills/<name>/SKILL.md`. Progressive disclosure (name+description always loaded, body on trigger, bundled files on demand) is stated in `skill-creator/SKILL.md`. **Prompt-render proof is absent in both trees.**

**REFS assumptions.**

- Claude plugin `plugin.json` `skills` array of directories is how Claude Code selects a subset. ADR 0002: `claude plugin validate . --strict` passed.
- Codex plugin cannot select a subset from a bucketed tree (single path, recursive discovery, symlinks dropped on copy).
- `disable-model-invocation` removes the skill from the model-visible list. `docs/engineering/ask-matt.md`: agents then treat that list as exhaustive and report user-invoked skills "missing." Thirteen of the plugin's skills carried the flag at the time of that write-up; current count of user-invoked among the 25 promoted is 14 (`ask-matt`, `grill-with-docs`, `implement`, `improve-codebase-architecture`, `setup-matt-pocock-skills`, `to-spec`, `to-tickets`, `triage`, `wayfinder`, `grill-me`, `handoff`, `teach`, `to-questionnaire`, `wait-what`). **The "missing skills" behaviour is user-reported, unfixed, not re-run.**
- Codex `policy.allow_implicit_invocation: false` is "the Codex analog." CHANGELOG 1.2.2: leaving it on `writing-for-agents` filtered the skill out of Codex's model-visible list so only `$writing-for-agents` worked. They dropped the policy to make it model-invokable again. **Documented Codex behaviour, not re-run.**
- `agents/openai.yaml` `interface.display_name` / `short_description` are "Codex UI metadata." **Whether Codex reads them from a project `skills/` copy versus a plugin cache is unproven here.**
- Claude slash command is `/<name>`; Codex explicit form is `$<name>` (CHANGELOG). Skill-to-skill calls in REFS use `Call the Skill tool with "grilling"` rather than `/grilling`, to stay harness-neutral (`.agents/invocation.md`).
- Plugin-aliased names use a `mattpocock-skills:` prefix (`docs/engineering/code-review.md`). **Unproven here.**

**agent-runtimes assumptions.**

- Pointing `CLAUDE_CONFIG_DIR` / `CODEX_HOME` at a generated home loads `<home>/skills/` and not `~/.claude/skills` or `~/.agents/skills`. Stated as "Verified contract" in `skills/skill-matters/SKILL.md`. The generator test `test_generation_reads_no_skill_store_under_home` only proves **generation** does not read those stores. It does not launch a harness.
- Grok still inherits plugins from `~/.claude` regardless of `GROK_HOME`. `AGENTS.md` records `grok inspect` 1.0.5 against a real home:

```
                        skills  mcp  hooks  plugins
empty config            99      7    2      3
+ [compat.claude] false 99      7    2      3
+ [skills] ignore       69      7    2      3
+ [plugins] disabled    10      0    2      3
```

  Fleet baseline `baselines/config.grok.toml` emits `[skills] ignore = ["~/.agents/skills"]`, `bundled_skill_dirs = []`, and `[compat.claude]` / `[compat.cursor]` all false. It does **not** emit `[plugins] disabled`, because that needs plugin names read from `$HOME`. The ignore "matches a resolved path: it removes the thirty real directories and none of the nine symlinks" (those nine point into `helioy-plugins`). **Documented measurement, not re-run. Whether `[disabled]` drops a skill from the prompt, versus listing it as disabled, is explicitly untested** (`AGENTS.md`: "grok exposes no offline prompt render").
- `grok inspect` lists both `AGENTS.md` and `CLAUDE.md` from the home root and counts tokens for each (~1.6k twice). Symlinking `CLAUDE.md` to `AGENTS.md` drops it to one entry. That reverse of the self-contained-template choice was not taken. **Discovery, not a prompt render.**
- Claude `settings.json` `disableBundledSkills` and `CLAUDE_CODE_DISABLE_*` are treated as prompt-section gates, with function names (`zX()`, `EUn()`, `gkm()`) cited from claude 2.1.235/237. **Documented from captured payloads in `tm-stu` comments.**
- Codex `config.toml` has a commented `[settings.codex.skills] include_instructions = false` in `tm-stu` only. Meaning **unproven.**
- `skill-creator` claims Claude loads three levels (metadata, body, bundled resources) and that `name`+`description` are the only frontmatter fields Claude uses for triggering. **Unproven here.**

## Where Things Live

**REFS/skills**

```
.claude-plugin/plugin.json          promoted skill path list (Claude plugin)
.claude-plugin/marketplace.json     fallback single-plugin marketplace
.agents/invocation.md               user vs model invocation contract
.agents/install-block.md            canonical install wording
.agents/adr/0002-*.md               why Claude plugin exists and Codex does not
.agents/writing-docs.md             docs/ tree, not the skill store
CLAUDE.md / AGENTS.md -> CLAUDE.md  authoring rules for this repo
scripts/link-skills.sh              flatten-and-symlink into $HOME
scripts/list-skills.sh              find SKILL.md
scripts/sync-plugin-version.mjs     package.json version -> plugin.json
skills/<bucket>/<name>/SKILL.md     the bodies
skills/<bucket>/<name>/agents/openai.yaml
docs/<bucket>/<name>.md             human docs for promoted skills only
```

**agent-runtimes**

```
skills/<name>/SKILL.md                         owned bodies (edit these)
bin/agent_runtime_compiler/skills.py           catalog, digest, copy, prune
bin/agent_runtime_compiler/capabilities.py     requires_capability parser
bin/agent_runtime_compiler/manifest.py         resolve_skills
bin/agent_runtime_compiler/compiler.py         plan + optional drop
bin/agent_runtime_compiler/writers.py          materialize
bin/agent_runtime_compiler/audit.py            residue including skill copies
bin/generate.py                                --catalog / --audit / --force
capabilities.toml                              image-generation -> openai, xai
baselines/config.grok.toml                     grok skill isolation cells
runtimes/<name>/runtime.toml                   which skills a home ships
runtimes/<name>/skills/<name>/                 generated copies
tests/test_skills.py                           copy, prune, audit, no $HOME
skills/skill-matters/SKILL.md                  composition spec
skills/skill-creator/                          Anthropic authoring helper
skills/find-skills/                            npx skills discovery helper
```

## Reusable organizational ideas versus repository-specific choices

**Reusable (either tree could adopt without taking the other's product).**

- One skill = one directory + `SKILL.md`. Marker file, not a central index.
- Hyphen-case names. REFS matches directory to frontmatter everywhere; agent-runtimes almost does.
- Progressive disclosure: short always-loaded pointer (`description`), body on trigger, extra files behind in-body pointers. REFS `writing-for-agents` and agent-runtimes `skill-creator` both teach this, with different vocabularies ("context pointer" / "leading word" versus "three-level loading").
- Dual-harness metadata when targeting both Claude and Codex: REFS encodes it as `disable-model-invocation` plus `agents/openai.yaml`. agent-runtimes mostly omits it and copies `openai.yaml` only when the vendored body already had one.
- Promotion subset: some skills are daily and shipped, others are beta or personal. REFS uses buckets + plugin allowlist. agent-runtimes uses per-home `[skills]` lists.
- Collision on a popular name (`code-review`) is a real harness problem. Prefix (plugin) or isolation (config home) are the two available answers. Neither tree renames to avoid Claude's built-in.

**Repository-specific (do not copy blindly).**

- REFS buckets exist so a human can browse and so a plugin can ship a subset. They fight Codex's single-path plugin schema. Flattening at install time is the cost of keeping buckets.
- REFS `link-skills.sh` last-writer-wins into `$HOME`. That is a maintainer convenience and the opposite of agent-runtimes' "generation must not read `$HOME` for content."
- REFS plugin versus skills.sh exclusivity ("pick one") is a distribution problem for a public library. A runtime generator has no analog.
- REFS user-invoked skills plus a router (`ask-matt`) is a cognitive-load design. agent-runtimes curation is the router: the home simply does not contain the other skills.
- agent-runtimes copies, digests, and `--force` exist because templates must be shippable and because harnesses write into homes. REFS wants the opposite for plugin users (managed, read-only, auto-update) and the opposite again for skills.sh users (editable copies you own).
- `requires_capability` is an agent-runtimes/transport-matters contract. REFS has no vendor capability model.
- agent-runtimes `skill-creator` allowed-frontmatter list is Anthropic's packaging schema, not this fleet's. Applying it to REFS or to `helioy-imagegen` would fail.
- Empty capture homes (`tm/capture`, `tm/stu`) are measurement instruments, not a skill-library idea.
- Docs pages (`docs/`) and `CONTEXT.md` as a product glossary are REFS publishing. agent-runtimes docs are operator/spec (`README.md`, `AGENTS.md`, `docs/specs/`).

## Gotchas

1. **Same string, different skill.** `code-review` in REFS is not `code-review` in agent-runtimes. A comparison that keys on name only will lie.

2. **Directory versus frontmatter.** agent-runtimes will generate `skills/codebase-map/` even though the skill calls itself `map`. If a harness indexes frontmatter `name`, slash-command `/map` and catalog id `codebase-map` diverge.

3. **Bucket flattening.** REFS install identity is basename. Bucket is authoring metadata. `link-skills.sh` will `rm -rf` a non-symlink occupant of `~/.claude/skills/<name>`.

4. **Deprecated is a policy split.** `link-skills.sh` skips `deprecated/`; `list-skills.sh` does not. The bucket is empty, so the split is currently idle.

5. **Optional capability does not bind.** `helioy-imagegen-primatives` can sit on a Claude-capable home as optional. Only required `helioy-imagegen` drops Claude. The launcher spec still claims both require the capability.

6. **skill-creator will not validate this fleet's bodies.** `requires_capability` and `disable-model-invocation` are unexpected keys.

7. **Grok isolation is incomplete by documented measurement.** Baseline ignore of `~/.agents/skills` leaves symlinked skills and plugin-sourced MCP. `[plugins] disabled` is the lever that zeros MCP (7 to 0) and cuts skills 69 to 10, and it cannot be emitted without reading `$HOME`. Floor with a hardcoded denylist: ten skills, no servers, two hooks. The ten are nine symlinks plus one Claude skill. Comparator captures that replace `HOME` with an empty directory sidestep this; reachability captures against the operator HOME do not.

8. **`skill-matters` "Verified contract"** ("personal skills and installed plugins do not leak in") is true as a design intent for Claude/Codex config-home launch, and false as a Grok statement on this machine. The same skill file states both the contract and, via `AGENTS.md`, the Grok gap.

9. **Double instruction load on Grok.** Two names, one body, tokens counted twice unless the names resolve to one file.

10. **Working tree.** agent-runtimes `skills/tm-orchestrate/SKILL.md` is modified relative to `71e3871`. Generated `runtimes/generalist/skills/tm-orchestrate/` will not match the owned body until regenerate `--force`. That is exactly the gate `generate.regenerate` encodes.

11. **Absolute paths inside skill bodies.** `helioy-imagegen/SKILL.md` still points at `/Users/alphab/.codex/skills/helioy-imagegen/icon-512x512.png`. Vendoring the tree into a home does not rewrite that. A copy in `runtimes/imagegen/skills/helioy-imagegen/` can tell the agent to read a path outside the home.

12. **`find-skills` installs globally.** `npx skills add ... -g` writes into the operator skill store, which is the surface agent-runtimes exists to avoid. Shipping `find-skills` in `tm/research` and `tm/skill-matters` is a product choice that can undo isolation if the agent follows the skill.

## Unproven harness behaviour (explicit)

Claims not proven by launching Claude, Codex, or Grok in this investigation:

- Claude loads only `name` and `description` from frontmatter to decide invocation (`skill-creator`).
- Claude `disable-model-invocation: true` omits the skill from the injected skill list, and the model treats that list as exhaustive (`docs/engineering/ask-matt.md`).
- Plugin install aliases skills as `mattpocock-skills:<name>` and that form wins over the unqualified built-in (`docs/engineering/code-review.md`).
- A non-plugin install shadows Claude's built-in `/code-review` (`docs/engineering/code-review.md`).
- Codex drops symlinks when copying a plugin tree (ADR 0002).
- Codex `.codex-plugin/plugin.json` rejects a `skills` array (ADR 0002).
- Codex reads `agents/openai.yaml` `interface.*` and `policy.allow_implicit_invocation` from a copied project skill.
- `npx skills add mattpocock/skills` discovery rules (which buckets, dest paths per agent, overwrite policy).
- Whether `<home>/skills/<name>` is discovered because of directory name, frontmatter `name`, or both.
- Whether Grok `[skills] ignore` / `[compat.claude] skills = false` / `[disabled]` removes skills from the prompt or only marks them in `grok inspect`.
- Whether Claude `CLAUDE_CONFIG_DIR` plus a generated home actually hides `~/.claude/skills` and plugins (stated as verified in `skill-matters`; no launch in this pass).
- Whether Codex `CODEX_HOME` hides `~/.agents/skills` and `~/.codex/skills`.
- Official marketplace pin SHA versus current `plugin.json` 25-skill list (ADR 0002 measured 22 vs 24 on 2026-08-05; plugin now has 25).
- `tm/stu` token tables against claude 2.1.237 (comments in `runtimes/tm-stu/runtime.toml`).
- Overlay write-back of 86 paths through a symlinked `skills/` directory (`audit.py` docstring).

Proven in-repo without a harness: catalog shape, copy/prune/digest, required versus optional, capability intersection, audit residue kinds, plugin path list equals promoted buckets, REFS name uniqueness, the `codebase-map`/`map` mismatch, and both HEADs.
)

---
title: Vibe-Skills — primitive harvest for runtime-matters and runtime-catalog
type: research
tags: [github-review, runtime-matters, runtime-catalog, skills, harness, installer, profiles]
summary: Vibe-Skills is a 2k-star Python/PowerShell skills harness with strong installer ledger and host-adapter contracts, but most of the policy-JSON ecosystem is governance theater that does not transfer.
status: active
source: github-researcher
confidence: medium
created: 2026-05-15
updated: 2026-05-15
---

# Vibe-Skills (foryourhealth111-pixel/Vibe-Skills)

## 1. Stats

Public repo at `https://github.com/foryourhealth111-pixel/Vibe-Skills`, created 2026-02-22, last push 2026-05-08, 2,094 stars, 19 MB on disk, Apache-2.0. Five active contributors with two effective humans (`foryourhealth111-pixel` 138 commits, `QingFeng Li` 103). Primary language Python with a heavy PowerShell layer (`check.ps1`/`install.ps1` are ~1k lines each). CI present as `.github/workflows/vco-gates.yml`: pytest on Ubuntu plus nine PowerShell verify gates on Windows. Bundled corpus is 258 skills under `bundled/skills/` cataloged in `config/skills-lock.json` with dir-level SHA-256 hashes. README is 852 lines of marketing prose; SKILL.md is the actual contract.

## 2. Grade

**B−.** Real engineering inside `packages/contracts`, `packages/installer-core`, and `packages/skill-catalog` (ledger-based install/uninstall, host-adapter contracts, freshness gates with file-by-file parity, managed-block merge in shared markdown files). Buried under 153 JSON policy files in `config/` and 172 PowerShell verify scripts that look like governance LARPing rather than load-bearing infrastructure. Voice is "governance capsule, lineage receipt, freeze, capsule." Same calibration band as claudex and metaharness: one or two real primitives worth lifting, rest is noise.

## 3. Primitives that transfer

1. **Host-adapter descriptor split (registry / profile / platform / closure / settings-map)** — `adapters/index.json:1-44` is the registry; per-host `adapters/<host>/host-profile.json`, `adapters/<host>/platform-macos.json`, `adapters/<host>/closure.json`, `adapters/<host>/settings-map.json` are five distinct documents per host (codex, claude-code, cursor, windsurf, openclaw, opencode, generic). Each platform file carries `status`, `install_surface`, `degrade_cases`, `promotion_target`, `proof_bundle` (`adapters/claude-code/platform-macos.json:1-37`). **Lands in `runtime-matters`** as the contract between a runner and a runtime-home install surface. Profile kinds (`persona`/`task`/`launcher`) can borrow the same split.

2. **Install ledger with typed roots** — `packages/contracts/src/vgo_contracts/install_ledger.py:62-77` defines `InstallLedger` with `managed_skill_names`, `runtime_roots`, `compatibility_roots`, `sidecar_roots`, `config_rollbacks`, `legacy_cleanup_candidates`, all with relative-path validation. Materialization tracks this live in `packages/installer-core/src/vgo_installer/ledger_service.py:14-29` via `MaterializationLedgerState`. **Lands in `runtime-matters`**: the fingerprinted build at `~/.runtime-matters/builds/<runner>/<profile>/<hash>/home/` needs exactly this ledger so the launcher knows what to remove on uninstall and what to roll back inside shared JSON files.

3. **Managed-block merge inside foreign markdown (`CLAUDE.md`, etc.)** — `packages/installer-core/src/vgo_installer/global_instruction_merge.py:8-72` brackets bootstrap content between `<!-- VIBESKILLS:BEGIN managed-block host=X block=Y version=N hash=H -->` and `<!-- VIBESKILLS:END managed-block -->`, with SHA-256 content hash, host id, and version embedded. Lets the installer edit user-owned files without clobbering. **Lands in `runtime-matters`** as the safe edit primitive for any "global instruction surface" the runner wants to touch.

4. **Catalog descriptor + profile manifest separation** — `packages/skill-catalog/catalog/profiles/index.json:1-14` lists profile manifests; `packages/skill-catalog/catalog/profiles/minimal.json:1-20` uses `selection_mode: "allowlist"`; `packages/skill-catalog/catalog/profiles/full.json:1-9` uses `selection_mode: "all_official_except_excluded"`. `CatalogDescriptor` dataclass at `packages/contracts/src/vgo_contracts/catalog_descriptor.py:1-12` carries `catalog_root`, `skill_source_root`, `profiles_manifest`, `groups_manifest`, `metadata_manifest`. **Lands in `runtime-catalog`** as the descriptor shape and the two selection modes for profile bundles.

5. **Freshness gate with file-by-file parity** — `packages/verification-core/src/vgo_verify/runtime_freshness_runtime.py:18-90` walks `packaging.mirror.files` and `packaging.mirror.directories`, hashes both sides, surfaces `only_main`, `only_installed`, `diff_files`. Emits a `runtime-freshness-receipt.json` (`references/proof-bundles/.../runtime-freshness-receipt.json:1-10`) the runtime can check at launch. **Lands in `runtime-matters`** as the launch-time check that the built home matches its source hash without re-extracting.

6. **`InstalledRuntime` contract with required markers** — `packages/contracts/src/vgo_contracts/installed_runtime_contract.py:6-37` declares required markers (`SKILL.md`, `config/version-governance.json`, etc.) that an installed runtime must carry. Two profiles: `FRESHNESS_REQUIRED_RUNTIME_MARKERS_DEFAULT` and `COHERENCE_REQUIRED_RUNTIME_MARKERS_DEFAULT`. **Lands in `runtime-matters`** as the "this build is a valid runtime home" predicate. Replace the hard-coded `SKILL.md` with whatever marker file the runtime uses.

7. **`resolve_target_root_text` (env > absolute > home-relative)** — `packages/contracts/src/vgo_contracts/target_root_contract.py:34-56` resolves a host's install destination by precedence: env var (`CODEX_HOME`, `CLAUDE_HOME`), absolute path, else `home + relative`. Cross-platform path joining handled inline. **Lands in `runtime-matters`** as the home-resolver for runtime homes on disk, with the same env-var-first pattern.

8. **Discoverable entry surface contract** — `config/vibe-entry-surfaces.json:1-50` declares which entries are public (`publicly_exposed: true`), each with `requested_stage_stop`, `progressive_stage_stops`, `allow_grade_flags`. The contract dataclass is `packages/contracts/src/vgo_contracts/discoverable_entry_surface.py:11-26`. The installer "projects" public entries as host-visible launchers (`projection_mode: "generated_wrapper_entries"`). **Lands in `runtime-catalog`** as the model for which profiles get a stable runtime launch pointer and which stay internal.

9. **Bundled-skill three-line frontmatter as the universal contract** — every one of the 258 bundled skills is a folder with `SKILL.md` carrying `name` + `description` only (`bundled/skills/tdd-guide/SKILL.md:1-4`, `bundled/skills/algorithmic-art/SKILL.md:1-5`). Optional `references/` and `scripts/` subfolders for the few that need them (`bundled/skills/code-reviewer/`). No JSON manifest required at the skill level. **Lands in `runtime-catalog`** as the authoring contract for `persona` / `task` profile kinds: keep the per-skill schema tiny, push richness into folder structure rather than YAML/JSON.

10. **CI matrix split: Python pytest on Linux, integration gates on Windows** — `.github/workflows/vco-gates.yml:13-63` runs pure-Python contract tests on ubuntu-latest and the heavier verify gates on windows-latest. `config/python-validation-targets.txt` is the allowlist of pytest targets. **Lands in either target**: the pattern of "contract tests are platform-neutral and run everywhere, integration gates only run where the runner actually lives" is exactly the shape `runtime-matters` will need across codex / claude-code / cursor.

## 4. Does NOT transfer

1. **The 153-file `config/` policy directory.** Most files are aspirational governance (`config/dialectic-team-policy.json`, `config/closure-overlay.json`, `config/cuda-kernel-overlay.json`, `config/document-failure-taxonomy.json`). Helioy already has cm/am for state and Linear for workflows; we do not need a `daily-dialectic-guard.json`.

2. **The 1,871-line PowerShell router** (`scripts/router/resolve-pack-route.ps1`) plus 49 numbered `scripts/router/modules/*.ps1` overlays. The actual routing logic is a 30-line keyword classifier (`packages/runtime-core/src/vgo_runtime/router.py:55-186`). The PowerShell layer is theater; the Python one classifies tasks into `review/debug/research/coding/planning` with a string-marker count. Borrow the small Python version if anything.

3. **The six-stage governed runtime state machine** (`skeleton_check`, `deep_interview`, `requirement_doc`, `xl_plan`, `plan_execute`, `phase_cleanup` in `packages/runtime-core/src/vgo_runtime/stage_machine.py:5-12`). Helioy already has `linear-workflows` and SPEC/plan gates. Adding a second governed pipeline would be parallel infrastructure.

4. **"Governance capsule" / "lineage receipt" / "proof bundle" vocabulary.** Cleanup receipts (`references/fixtures/runtime/vibe-sessions/.../cleanup-receipt.json`) are JSON sidecars that exist to be validated by other gates that exist to be validated by other gates. Helioy's "verification before completion" is a behavioral rule, not a file format.

5. **172 PowerShell verify gates** in `scripts/verify/`. Tooling-as-narrative. Most check that the policy JSON files agree with each other.

6. **The README at 852 lines and bilingual sibling at 40 KB.** Marketing surface area that crowds out the actual contract (SKILL.md at 234 lines is the real entry document).

7. **`upstream-lock.json`'s "shipped-local-adaptation" frame for vendored skills.** Re-implements npm's resolved-vendoring discipline with extra ceremony. Helioy's submodule / git-subtree / publish model already covers this.

## 5. Verdict (split per target)

- **`runtime-matters`: borrow.** Lift the install ledger (`InstallLedger` dataclass + materialization state), the managed-block merge primitive, the host-adapter five-file split, the freshness gate's parity walk, and the env > absolute > home target-root resolver. These are five concrete primitives that each save real work.

- **`runtime-catalog`: inspiration.** The catalog descriptor + profile manifest separation is right-shaped, and the bundled-skill three-line frontmatter is the right authoring contract. But the implementation is shallow: an `exporter.py` that copies trees with `shutil.copytree`. Borrow the schema; write the catalog itself.

## 6. Why

Both projects answer the same question: "where does a skill / profile / runtime live on disk, and how does an installer put it there safely without destroying user state?" Vibe-Skills got the file-system contracts right (ledger, managed-block, host-adapter descriptors, target-root resolution) because those are forced by reality: real users running real `install.sh` against real `~/.claude/settings.json`. Where they failed is exactly where Helioy must succeed: the runtime logic itself. Vibe-Skills wraps a keyword classifier in a six-stage governed state machine, 153 policy JSONs, and 172 verify gates. The wrap is governance theater. The classifier is 30 lines. `runtime-matters` and `runtime-catalog` should treat Vibe-Skills as a *file-system contract library*, not a runtime template.

## 7. How to apply

- In `runtime-matters`, port `vgo_contracts.install_ledger.InstallLedger` to whatever language the runner is written in. Persist it at `~/.runtime-matters/builds/<runner>/<profile>/<hash>/install-ledger.json`. Use it for uninstall and rollback.
- In `runtime-matters`, port the managed-block merge primitive (`global_instruction_merge.py`) into a small library. Any time the installer edits `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md`, or `~/.cursor/rules.md`, gate the edit through `<!-- RUNTIME-MATTERS:BEGIN ... -->` markers with content hash. Avoid the existing Helioy hand-rolled edit code.
- In `runtime-matters`, adopt the five-file host-adapter split per supported runner. Replace `host-profile.json` field set with Helioy's runner-capability vocabulary; keep the per-platform `proof_bundle` slot so claims of "supported on macOS" are backed by a stored receipt path.
- In `runtime-matters`, define the freshness predicate as one function: given canonical source root and installed home root, return `{ok, only_canonical, only_installed, diff_files}`. Land it next to the build-cache logic.
- In `runtime-catalog`, adopt `CatalogDescriptor` shape with the four sibling manifests (`profiles/index.json`, `groups/index.json`, `metadata/index.json`, plus per-profile manifests with `allowlist` / `all_except_excluded` selection modes).
- In `runtime-catalog`, keep the per-profile manifest under 25 lines like `minimal.json`. Resist adding fields. The Vibe-Skills 153-file `config/` directory is the cautionary tale.
- Do not port the six-stage state machine, the verify-gate vocabulary, or the policy-JSON ecosystem.

## 8. Artifact

`/Users/alphab/.mdx/research/foryourhealth111-pixel-vibe-skills.md`

---
title: SWE-bench/SWE-bench review for fmm road-test corpus — borrow (dataset + harness fixtures)
type: research
tags: [github-review, swe-bench, fmm, benchmark, python, multilingual, code-navigation, road-test, retrieval]
summary: SWE-bench is the right shape and scale to road-test fmm. The dataset is 2,294 instances (Lite 534, Verified 500, Multimodal 600, Multilingual 300) of pinned-commit + gold-patch GitHub issues across 20 mature Python repos plus ~45 multilingual repos. We borrow the dataset + the clone/checkout fixture; we ignore the Docker eval harness.
status: active
source: github-researcher
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

# SWE-bench/SWE-bench review for fmm road-test

URL: https://github.com/SWE-bench/SWE-bench

## Stats

- **Stars**: 5,015 (5k+); **Forks**: 870; **License**: MIT (Princeton).
- **Created**: 2023-10-04; **Last commit**: 2026-03-18 (`f7bbbb2`, fix for git-checkout reset on new-file test patches, PR #539). Active maintenance.
- **Contributors**: 54 (top: John Yang, Carlos Jimenez, Kilian Lieret, Ofir Press, Manoj — Princeton + collaborators).
- **CI**: GitHub Actions; pre-commit configured; PyPI distribution (`swebench`, ~v4.0.5).
- **Citations**: ICLR 2024 Oral (original) + ICLR 2025 (Multimodal). De facto standard for LLM-on-real-code evaluation.

## Grade

**B+ as a borrow target.** Anchored near `superpowers` on the calibration scale. The dataset itself is A-tier prior art (most-cited benchmark for code-on-real-repos); the *codebase* is a B / B+ research artifact with strong harness engineering (containerized eval, multi-language constants, gold-patch validation) but bolted-on inference modules and a Docker hard-dependency that we will route around. Not A− because the code organization is research-grade — long constants files (python.py 1452 LOC), repeated TEST_PYTEST definitions, inline string scripts for env setup — and not C because the dataset shape, harness fixtures, and BM25 retrieval baseline are genuinely useful primitives for an fmm benchmark.

## Corpus shape — the numbers that decide the verdict

Sourced from `docs/guides/datasets.md` and `swebench/harness/constants/python.py`.

| Variant | Instances | Use |
|---|---|---|
| SWE-bench (full) | **2,294** | full Python benchmark |
| SWE-bench Lite | **534** | quick dev iterations |
| SWE-bench Verified | **500** | human-verified solvable |
| SWE-bench Multimodal | **100 dev / 500 test** | UI / visual repos (JS-heavy) |
| SWE-bench Multilingual | **300** | 9 languages, 42 repos |

**Python repo set (20 repos registered in `MAP_REPO_VERSION_TO_SPECS_PY`):**

astropy, dbt-core, django, marshmallow, matplotlib, mwaskom/seaborn, pallets/flask, psf/requests, pvlib/pvlib-python, pydata/xarray, pydicom, pylint-dev/astroid, pylint-dev/pylint, pytest-dev/pytest, pyvista, scikit-learn, sphinx-doc/sphinx, sqlfluff, swe-bench/humaneval, sympy/sympy.

**Per-repo instance counts (from `swebench/resources/swebench-og/` cached env stubs — original SWE-bench split):** django 231, sympy 75, sphinx 44, matplotlib 34, scikit-learn 32, pydata/xarray 22, astropy 22, pytest 19, pylint 10, requests 8, seaborn 2, flask 1. Heavy tail on django/sympy; the dataset's diversity is real but not uniform.

**Multilingual repos (from `constants/{c,go,java,javascript,php,ruby,rust}.py`):** apache/druid, apache/lucene, astral-sh/ruff, axios, babel, briannesbitt/carbon, burntsushi/ripgrep, caddy, chartjs, diegomura/react-pdf, docusaurus, faker-ruby, fastlane, fluentd, fmtlib/fmt, gin, gson, hugo, hashicorp/terraform, immutable-js, javaparser, jekyll, jordansissel/fpm, jqlang/jq, laravel, markedjs, micropython, nlohmann/json, nushell, php-cs-fixer, phpoffice/phpspreadsheet, preact, processing/p5, projectlombok, prometheus, reactivex/rxjava, redis, rubocop, sharkdp/bat, tokio-rs/axum, tokio-rs/tokio, uutils/coreutils, valkey-io/valkey, vuejs/core, three.js, mrdoob/three.js.

**Verdict on shape:** The corpus is large enough (2,294 full + 300 multilingual), varied enough (20 mature Python repos + ~45 multilingual), and pinned enough (every instance fixes `base_commit`) to be an excellent fmm road-test fleet. Verified (500) is the right starter — sized for one-day fmm-index runs across the whole set; Lite (534) is a fine alternate.

## Instance schema (the contract for fmm)

`SWEbenchInstance` TypedDict, `swebench/harness/constants/__init__.py:24-36`:

```python
class SWEbenchInstance(TypedDict):
    repo: str                       # e.g. "django/django"
    instance_id: str                # e.g. "django__django-13089"
    base_commit: str                # ← THIS is what fmm indexes
    patch: str                      # gold fix patch
    test_patch: str                 # test patch
    problem_statement: str          # issue body
    hints_text: str                 # PR comments
    created_at: str
    version: str                    # repo package version
    FAIL_TO_PASS: str               # tests gold patch turns from F → P
    PASS_TO_PASS: str               # regression tests still passing
    environment_setup_commit: str
```

Verified adds `difficulty`; Multimodal adds `image_assets`. **Every field fmm needs is present**: `repo` + `base_commit` is the cloneable, fmm-indexable code state; `patch` + `test_patch` give file-level and patch-line-level ground truth.

## Primitives that transfer

1. **Per-instance clone + commit-pin recipe** — `swebench/harness/test_spec/python.py:264-317` (`make_repo_script_list_py`). Exact bash for clone + `git reset --hard {base_commit}` + tag-pruning to suppress post-base history. **Landing target: fmm road-test runner.** Copy as a fixture so `fmm index` runs against the same commit SWE-bench evaluates against. Drop the conda+install steps; fmm only needs source files at the pinned commit.

2. **File-level ground truth extraction** — `swebench/harness/utils.py:339-362` (`get_modified_files`, `get_new_files`). Uses `unidiff.PatchSet` to split a patch into modified vs newly-added paths. **Landing target: fmm benchmark evaluator.** Direct fit for `recall@gold-files`: ask fmm "what files relate to this problem statement / failing test?" → intersect with `PatchSet(instance.patch)`. This is the headline metric.

3. **Symbol-level ground truth via jedi static analysis** — `swebench/inference/make_datasets/bm25_retrieval.py:104-143` (`file_name_and_docs_jedi`). SWE-bench's own BM25 baseline already uses jedi to extract module + symbol names + docstrings as the BM25 document encoding. **Landing target: fmm benchmark comparator.** Two implications: (a) we can borrow the same `jedi.Script(...).get_names(all_scopes=True, definitions=True)` pattern to extract gold-touched symbols from each patch hunk, giving symbol-level (not just file-level) ground truth; (b) BM25-with-jedi-encoding is the natural baseline for fmm's `lookup_export` / `glossary` retrieval — we can compare recall head-to-head.

4. **Recall metric harness** — `swebench/inference/make_datasets/eval_retrieval.py:1-67`. Computes `avg_recall`, `all_recall`, `any_recall` of retrieved-files vs gold-files per instance. **Landing target: fmm benchmark scorer.** 67 LOC, trivially adaptable. Use as-is for fmm's first benchmark report card.

5. **Per-repo version specs as install fixtures** — `swebench/harness/constants/python.py` (1452 LOC of `SPECS_DJANGO`, `SPECS_SKLEARN`, ...). Each `repo@version` carries `python`, `packages`, `install`, `pip_packages`, `test_cmd`. **Landing target: fmm index "extras" pipeline if we ever index symbols that require imports to resolve.** For static fmm indexing we likely do not need this, but if fmm grows a Python-imports-aware mode (resolving `from x import y` to actual files), these specs become the per-instance setup contract. Keep on hand.

6. **Multi-language coverage as the long horizon** — `constants/{go,java,javascript,php,ruby,rust,c}.py`. fmm's current sweet spot is Python-and-friends; the multilingual SWE-bench (~45 repos / 9 languages) is the natural stretch target once fmm gets language adapters beyond Python+TypeScript. **Landing target: future fmm language adapters.** Use the multilingual repo list as a prioritization signal (which languages to add next, weighted by SWE-bench instance count per language).

7. **Cached environment.yml stubs as a free repo manifest** — `swebench/resources/swebench-og/<repo>/<num>/environment.yml`, ~500 directories. **Landing target: fmm test fixtures.** These are tiny YAML stubs that let us assert "this instance maps to this conda env" without running pip. Useful for offline fmm benchmark setup.

8. **HuggingFace-or-local dataset loader pattern** — `swebench/harness/utils.py:133-182` (`load_swebench_dataset`). Handles HF dataset names, local `.json`/`.jsonl`/`.parquet`, with subset filtering by `instance_ids`. **Landing target: fmm-bench CLI input plumbing.** ~50 LOC pattern worth copying verbatim so fmm-bench accepts the same input shapes SWE-bench users already know.

9. **Patch correction utilities** — `swebench/harness/utils.py:186-271` (`PATCH_PATTERN`, `extract_minimal_patch`, `PATCH_HUNK_PATTERN`). Regex-based patch normalization. **Landing target: fmm-bench ground-truth preprocessing.** Use to canonicalize the gold patches before computing symbol-level diffs.

10. **The `instance_id` naming convention** — `{repo_owner}__{repo_name}-{pr_number}`. Stable, human-readable, used everywhere as the primary key. **Landing target: fmm-bench instance schema.** Adopt verbatim; it is the lingua franca for cross-referencing with leaderboards.

## Does NOT transfer

1. **Docker eval harness** — `swebench/harness/run_evaluation.py` (677 LOC) + `docker_build.py` (532) + `docker_utils.py` (311). Builds three-layer images (base / env / instance), applies patches, runs tests, parses logs. fmm road-test does not need to *run* anything; we index source. Skip the entire `docker_*` and `modal_eval/*` modules.

2. **Patch generation / inference modules** — `swebench/inference/*` (`run_api.py`, `run_llama.py`, `run_live.py`, ~1300 LOC). LLM-calls-the-API plumbing for generating fix patches. Out of scope: we are evaluating code navigation, not patch generation.

3. **Conda environment setup machinery** — `make_env_script_list_py` and friends (~200 LOC in `test_spec/python.py`). Heavy `requests.get(...)` calls to fetch historical `environment.yml` and `requirements.txt` from GitHub raw. fmm indexes from a checkout; we do not need the env materialized.

4. **Log parsers per language** — `swebench/harness/log_parsers/{python,java,...}.py`. Parse pytest / mocha / tox output into PASS/FAIL/SKIPPED. Useful for the eval scoring loop, irrelevant for an indexing benchmark.

5. **`get_top_pypi.py`, collection pipeline, `make_lite/criteria.py`** — `swebench/collect/*` (~8 files). The pipeline used to *build* SWE-bench from PRs. We consume the dataset; we do not build new instances. Skip.

6. **Modal/cloud eval** — `swebench/harness/modal_eval/*` (4 files). Cloud orchestration for running the eval at scale. Replace with whatever fmm uses for parallel indexing (likely just GNU parallel or a thread pool).

7. **Versioning extraction** — `swebench/versioning/*`. Maps PRs to release versions, used during dataset construction. Not needed downstream.

8. **swebench-og resource trees beyond env.yml stubs** — the per-instance directories only hold `environment.yml`. No code there; no patches; no problem statements. Everything live ships through HuggingFace Datasets.

## Verdict

**Borrow** — the dataset is the right corpus and the harness has 5–10 small reusable pieces (clone-script, modified-files extractor, recall scorer, jedi-encoder pattern). Build a thin `fmm-bench` runner that pulls Verified (500) from HF, clones-and-pins per instance, runs `fmm index`, then computes file-level and symbol-level recall against the gold patches. Skip Docker entirely.

## Why

fmm needs adversarial breadth — it has to survive monkey-patched Django ORMs, sympy's metaclasses, sphinx's directive system, matplotlib's `pyplot`-vs-OO duality, and scikit-learn's `_BaseEstimator` mixins. SWE-bench's whole point is that *these* repos break LLMs in real, reported, human-confirmed ways. Anything that breaks LLM agents on these repos will also break fmm's "what calls this", "what changed", "where is this defined" answers. Picking SWE-bench Verified specifically (500 human-vetted instances) gives us a fixed, reproducible, leaderboard-adjacent target that other people will recognize. The BM25-with-jedi baseline at `bm25_retrieval.py:104` is the killer detail: SWE-bench *already* has a code-nav-adjacent baseline in their own retrieval pipeline. fmm's gravity sits on showing it can beat or match that recall using structural (not lexical) navigation.

## How to apply — concrete next steps for fmm

1. **Stand up `fmm-bench` as a small package** in the fmm repo (or a sibling `fmm-bench` repo). One CLI entry: `fmm-bench run --dataset verified --out reports/`. ~500 LOC budget.

2. **Vendor the four files we want** (not the whole repo):
   - `swebench/harness/utils.py:339-362` (`get_modified_files`, `get_new_files`) → `fmm_bench/patch_utils.py`.
   - `swebench/inference/make_datasets/eval_retrieval.py:1-67` → `fmm_bench/scoring.py`.
   - `swebench/harness/test_spec/python.py:271-293` (the clone + reset block, minus the conda lines) → `fmm_bench/checkout.py`.
   - `swebench/inference/make_datasets/bm25_retrieval.py:104-143` (`file_name_and_docs_jedi`) → `fmm_bench/baselines/bm25_jedi.py` for head-to-head comparison.

3. **Use `datasets.load_dataset('SWE-bench/SWE-bench_Verified', split='test')` directly** — do not vendor instances, do not fork the dataset; just depend on the HF dataset.

4. **Define three fmm metrics to compute per-instance:**
   - `recall@gold-files` — for each instance, ask fmm "given the problem_statement as a query, return the top-k files" and intersect with `get_modified_files(patch)`. Compare to BM25-jedi baseline.
   - `recall@gold-symbols` — extract symbol names from each `@@` hunk in the gold patch (use `jedi.Script(...).get_names()` scoped to the file + hunk line range), then ask fmm `fmm_lookup_export` or `fmm_glossary` for each and check coverage.
   - `blast-radius accuracy` — for each modified symbol, ask fmm "what uses this?" and check whether the test files in `test_patch` are in the result set. This is the fmm-specific question that BM25 cannot answer at all.

5. **Run Verified (500) end-to-end first, report numbers, then expand.** Lite (534) and full (2294) are stretch. Multilingual (300) is the v2 stretch once fmm has Go/Rust/Java adapters.

6. **Pin a leaderboard-style report card** at `~/.mdx/research/fmm-bench-report-card.md` after the first run. Include per-repo breakdown so we see if fmm degrades on django (long files, deep inheritance) vs requests (tiny, flat). Compare against `bm25_jedi` as the published baseline.

7. **Treat instance breakage as a fmm lesson channel.** Any instance where fmm returns 0 gold files and bm25_jedi returns >0 is a structural-index bug. File as a fmm task with the failing instance_id in the title.

## Sources consulted

- `README.md` (top-level), `CHANGELOG.md`.
- `docs/guides/datasets.md`, `docs/guides/evaluation.md`.
- `swebench/harness/constants/__init__.py` (instance schema, repo-version map).
- `swebench/harness/constants/python.py` (1452 LOC; 20 Python repos + per-version SPECS).
- `swebench/harness/constants/{c,go,java,javascript,php,ruby,rust}.py` (multilingual repos).
- `swebench/harness/test_spec/test_spec.py` (TestSpec dataclass, image-key hashing).
- `swebench/harness/test_spec/python.py` (clone + env + eval script generators).
- `swebench/harness/utils.py` (dataset loader, `get_modified_files`, `get_new_files`, patch correction).
- `swebench/inference/make_datasets/bm25_retrieval.py` (jedi-based document encoding).
- `swebench/inference/make_datasets/eval_retrieval.py` (recall scoring).
- `swebench/resources/swebench-og/` (per-instance env.yml cache; per-repo counts).
- `gh repo view` metadata.

## Open questions

1. **Are gold patches stable across HF dataset versions?** SWE-bench has revised its dataset multiple times (the `og` resource tree suggests one revision). We should pin a HF revision hash in `fmm-bench`.
2. **What is the SWE-bench Multilingual instance count per language?** Docs say 300 total / 9 languages / 42 repos but per-language splits not stated. Worth checking when we add language adapters.
3. **How does the BM25-jedi baseline perform numerically?** The retrieval datasets (`SWE-bench_bm25_13K`, `_27K`, `_40K`, `_50K`) are published on HF; we should load `eval_retrieval.py` and get the numbers before committing to "beat this".
4. **`PASS_TO_PASS` is stored as a JSON string, not a list** (see `_from_json_or_obj` at `test_spec.py:195`). Worth verifying that field types match the TypedDict before writing schema validators.
5. **Patches occasionally touch tests in `tests/` directories** — should fmm-bench filter to non-test files for `recall@gold-files`, or count both? Decision needed before first run.

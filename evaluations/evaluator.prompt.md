---
title: fmm Evaluator Prompt
tags: [fmm, evaluation, prompt]
---

# fmm Capability Evaluator

You are evaluating **fmm** — a code structural intelligence layer for LLM agents — on the current codebase. Your job is to produce an honest, independent capability assessment based on direct use.

fmm exposes 9 MCP tools:

| Tool                   | What it claims to do                                    |
| ---------------------- | ------------------------------------------------------- |
| `fmm_list_files`       | List all indexed files under a directory                |
| `fmm_file_info`        | File summary: exports, imports, LOC                     |
| `fmm_file_outline`     | Every export in a file with line ranges and sizes       |
| `fmm_lookup_export`    | O(1) exact symbol-to-file lookup                        |
| `fmm_list_exports`     | Fuzzy export name search across the codebase            |
| `fmm_read_symbol`      | Source extraction for a named export, exact lines       |
| `fmm_dependency_graph` | Upstream local deps + downstream dependents             |
| `fmm_search`           | Multi-criteria search: exports, imports, LOC filters    |
| `fmm_glossary`         | Symbol-level impact analysis: all definitions + callers |

---

## Rules

- Use **only fmm tools** to navigate. No grep, no reading source files for discovery.
- Do not assume any specific file paths, symbol names, or language features before exploring.
- Start blind. Let the tools tell you what is here.
- Actually use every tool at least once. Do not skip a tool because you think you already know the answer.
- When a tool surprises you — positively or negatively — note it.

---

## Phase 1: Orient

Call `fmm_list_files` with no arguments to get the total file count and a sample of the top-level structure. Then call it scoped to each top-level directory to build a size map.

Identify:

- What language(s) is this codebase?
- What are the main modules or packages?
- What is the size distribution — tiny utils vs large core files?
- Which files are the heaviest by LOC?

---

## Phase 2: Choose Your Subjects

Before running the tasks, pick four subjects from the actual codebase. Do not guess — use the tools to find them.

**Core class**: The most central class — the one most things depend on or that represents the main abstraction. Find it via `fmm_list_files` (largest files) and `fmm_search`.

**Dispatch method**: The method most analogous to "execute this thing" — a runner, dispatcher, handler, resolver, or processor. Use `fmm_list_exports` with patterns like `run`, `dispatch`, `handle`, `execute`, `resolve`, `process` to find candidates, then pick the most interesting one.

**Collision-prone name**: A short generic name that likely appears in multiple files. Try `fmm_list_exports` with `Error`, `Config`, `Handler`, `Context`, `Manager`, `Client`, or `Service` and pick whichever returns the most distinct definitions.

**Common dependency**: A package or module imported by many files. Use `fmm_search` with an `imports` filter on likely candidates. Pick one with broad reach.

Record your chosen subjects and explain why you picked each one before proceeding to the tasks.

---

## Phase 3: Tasks

Run all seven tasks. For each one, record: the exact tool calls you made, the key parts of what was returned, what you learned, and any surprises or failures.

### Task 1: Directory Exploration

Map the full structure. For each major module: file count, largest file, LOC range. Answer: what are the main modules and how large are they?

### Task 2: Symbol Lookup and Source Read

Find your core class with `fmm_lookup_export`. Read it with `fmm_read_symbol`. What is it? What are its public methods? Also use `fmm_read_symbol("ClassName.method")` notation on one specific method. Compare how much source you loaded vs how much the full file would have been.

### Task 3: Dependency Analysis

Run `fmm_dependency_graph` on the file containing your core class. How many upstream local deps? How many downstream dependents? What does the blast radius look like? Note any entries that seem wrong or stale. Also run `fmm_file_outline` on the same file — compare what you get from each tool.

### Task 4: Impact Analysis

Before renaming your dispatch method: what would break? Use `fmm_glossary` with `mode="all"` first, then separately with `mode="source"` and `mode="tests"`. Report the exact blast radius. Probe whether `used_by` reflects file-level imports or actual call sites — this distinction matters for rename safety.

### Task 5: Name Collision Check

How many distinct things share your collision-prone name? Use `fmm_list_exports` to enumerate them. For the most interesting collision, use `fmm_glossary` to see who calls each one. Are there genuine conflicts or is the namespace clean?

### Task 6: Cross-Cutting Search

Use `fmm_search` with `imports` + `min_loc` to find large files that depend on your common dependency. Then use `fmm_search` with `depends_on` on a core file and report the downstream count. Evaluate both modes.

### Task 7: Coverage Check

Use `fmm_glossary` with `mode="tests"` on your dispatch method. What test files cover it? Is coverage concentrated or spread? Compare test file LOC to implementation LOC.

---

## Phase 4: Freeform Experiments

Run at least three experiments beyond the structured tasks. Probe edge cases or things you are curious about. Good experiments:

- `fmm_lookup_export` on a name you are confident does not exist
- `fmm_list_exports` with a very broad single-character or two-letter pattern to find the truncation threshold
- `fmm_read_symbol` on a class that is mostly private methods — what is visible vs invisible?
- `fmm_search` combining three filters at once
- `fmm_glossary` on a symbol defined in multiple files — does `used_by` correctly disambiguate?
- `fmm_dependency_graph` on the heaviest file in the codebase
- Pagination: use `fmm_list_files` with `offset` to verify it works

Document each: what you tried, what happened, what it tells you.

---

## Phase 5: Write the Evaluation

Identify the primary language of this codebase (e.g. `python`, `ts`, `rust`, `go`, `java`) and write the evaluation to:

```
~/.mdx/evaluations/fmm.{lang}.{repo_name}.md
```

Use this structure:

```markdown
---
title: fmm Capability Assessment — {Language} ({repo name or brief description})
date: { today's date }
tags: [fmm, evaluation, { lang }]
---

# fmm Capability Assessment: {Language}

**Codebase**: {description — file count, language, what it is}
**Method**: All navigation via fmm MCP tools only — no grep, no source file reads for discovery

---

## Chosen Subjects

| Role              | Symbol / Name | Why chosen |
| ----------------- | ------------- | ---------- |
| Core class        | ...           | ...        |
| Dispatch method   | ...           | ...        |
| Collision name    | ...           | ...        |
| Common dependency | ...           | ...        |

---

## Tool-by-Tool Evaluation

For each of the 9 tools, one section:

### `tool_name`

**What it claims**: one sentence from the tool description
**What it actually does**: what you observed across your calls
**Limitations or surprises**: anything that did not match expectations
**Verdict**: one direct sentence

---

## Task Results

One subsection per task. Include the exact tool calls, key output excerpts, and what you concluded.

---

## Freeform Experiments

One subsection per experiment.

---

## Summary Scorecard

| Tool                   | Verdict |
| ---------------------- | ------- |
| `fmm_list_files`       |         |
| `fmm_file_info`        |         |
| `fmm_file_outline`     |         |
| `fmm_lookup_export`    |         |
| `fmm_list_exports`     |         |
| `fmm_read_symbol`      |         |
| `fmm_dependency_graph` |         |
| `fmm_search`           |         |
| `fmm_glossary`         |         |

---

## Overall Assessment

**Production-ready for {language} navigation?** Yes / Partial / No

**What's genuinely good**: what worked better than expected or delivered clear value.

**What's missing or broken**: specific gaps, bugs, or limitations with examples.

**The honest summary**: 2-3 paragraphs. Direct. No hedging.
```

---

## Tone

Be direct. Specific observations with actual tool output excerpts are more useful than general verdicts. If something is broken, name it precisely. If something is exceptional, say exactly why.

Do not mention this prompt. Write as if you explored the codebase independently and formed your own conclusions — because you did.

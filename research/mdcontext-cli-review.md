# mdcontext CLI Review

**Date:** 2026-03-13
**Codebase:** `/Users/alphab/Dev/LLM/DEV/helioy/mdcontext`
**Reviewer:** cli-developer agent (claude-sonnet-4-6)

---

## Executive Summary

The mdcontext CLI is a well-engineered tool with thoughtful design choices. The Effect-based architecture provides strong typed error handling. The custom help system is genuinely good. Several structural issues, however, undercut the experience: a dual schema system that diverges silently, missing commands in the help registry, no shell completions, and some exit code misuse. None are blockers, but they create maintenance debt and user confusion.

---

## 1. CLI Framework

**Framework:** `@effect/cli` v0.73.1

This is an unusual and opinionated choice. Effect CLI is not a mainstream framework (Commander.js, yargs, or oclif would be more conventional), but it is coherent with the rest of the codebase which uses Effect pervasively. The tradeoffs are real:

- Pro: unified typed error channel, consistent with domain model
- Con: verbose option definitions, required argv preprocessing workaround (see below), non-standard help output that required a complete custom help override
- Con: the `showBuiltIns: false` config at `main.ts:87` hides Effect CLI's built-in `--version` and `--help` flags, then reimplements them manually in `help.ts`. This is fighting the framework.

The argv preprocessor (`argv-preprocessor.ts`) exists entirely because Effect CLI requires flags before positional arguments. This is a significant UX regression that required ~200 lines of workaround code. A conventional parser like yargs or Commander would handle this natively.

---

## 2. Command Structure and Organization

**Commands registered in `main.ts`:** index, search, context, tree, links, backlinks, duplicates, stats, config, embeddings

**Commands in help content (`help.ts`):** index, search, context, tree, links, backlinks, stats, config, embeddings

**Gap:** `duplicates` has no entry in `helpContent` (`help.ts:24`). Running `mdcontext duplicates --help` will hit `checkSubcommandHelp` at `help.ts:540-546`, fail the `helpContent[command]` lookup, print "Unknown command: duplicates", and exit with code 1. This is a regression: a working command actively errors on `--help`.

The main help (`showMainHelp` at `help.ts:467`) also omits `duplicates` from the COMMANDS listing. Users cannot discover it exists.

**Command hierarchy is otherwise logical:**
- Core workflow: index → search → context
- Navigation: tree
- Graph analysis: links, backlinks
- Maintenance: stats, embeddings, config, duplicates

The grouping in the main help uses informal comments (CORE COMMANDS, LINK ANALYSIS, INSPECTION) in `main.ts:7-18` but these categories do not appear in the rendered help output. The `showMainHelp` function emits a flat list without those groupings.

---

## 3. Dual Schema Problem

There are two parallel flag registries that must stay in sync manually:

1. **Effect CLI option definitions** — inside each `Command.make()` call in the individual command files
2. **`flag-schemas.ts`** — a handwritten duplicate used by the argv preprocessor for flag validation and typo suggestions

The search command is the most complex case. `flag-schemas.ts:135-206` defines the `searchSchema` but it is already missing the following flags that are defined in `search.ts`:
- `--rerank` / `-r`
- `--quality` / `-q`
- `--hyde`
- `--rerank-init`
- `--timeout`
- `--summarize` / `-s`
- `--yes` / `-y`
- `--stream`
- `--auto-index-threshold`

A user running `mdcontext search "auth" --rerank` will trigger the unknown flag error in the preprocessor before Effect CLI ever sees the argument. The search command is only partially usable.

Similarly, the `config` and `embeddings` commands have no schemas in the registry at `flag-schemas.ts:269-277`, so they bypass validation entirely. That is acceptable by design, but it means users get no typo suggestions for those commands.

---

## 4. Argument Parsing Quality

**Positional arguments:** Well-defined with appropriate defaults. `Args.withDefault('.')` for path arguments is the correct convention.

**Option types:** Correctly typed. Integer options use `Options.integer`, floats use `Options.float`, choices use `Options.choice`. No raw string-then-parse patterns.

**Validation:**
- The `--config` flag is handled in `main.ts:124-177` with manual parsing before the Effect CLI pipeline. The `--config=` with empty value check at line 137-142 is correct.
- Type coercion is handled by Effect CLI's built-in validators. Invalid types (e.g., `--limit foo`) produce Effect CLI validation errors that get caught by `isEffectCliValidationError` in `main.ts:367`.
- The `--mode` error enhancement at `error-handler.ts:625-633` is a nice touch: "Did you mean '--mode semantic'?" on a Levenshtein match.

**Help text quality:** Description strings are terse but accurate. The `Options.withDescription` text for `--hnsw-m` and `--hnsw-ef-construction` is exemplary — it gives recommended values and tradeoffs inline.

**Missing validation:**
- `--threshold` accepts any float including negative values and values above 1.0. There is no bounds check. A user passing `--threshold 50` gets silent bad behavior.
- `--fuzzy-distance` has no minimum check. Zero or negative values would be accepted.
- `--tokens` in the context command has no upper bound. Passing `--tokens 0` would produce degenerate output.

---

## 5. Error Messages and Exit Codes

**Exit code strategy** (`error-handler.ts:51-56`):
```
0: Success
1: User error (invalid arguments, missing config, etc.)
2: System error (file system, network)
3: API error (authentication, rate limits)
```

This is a thoughtful and documented strategy. Machines consuming the CLI can reliably distinguish API auth failures (3) from missing files (2) from bad arguments (1).

**Actual exit code usage:** The main error catch at `main.ts:374` uses `process.exit(2)` for unexpected errors. That is correct. The Effect CLI validation catch at `main.ts:370` uses `process.exit(1)`. Correct.

**Issue:** `showSubcommandHelp` in `help.ts:424-430` calls `process.exit(1)` when the command is not found in `helpContent`. For the `duplicates` command this means `mdcontext duplicates --help` exits 1 with "Unknown command: duplicates". The correct exit code for a help request on an unknown command is debatable, but the message is actively wrong — the command exists and works.

**Error message quality is generally high.** The provider-specific error handling in `error-handler.ts:214-315` is particularly good. When Ollama is not running, the error suggests "Start the Ollama daemon: ollama serve" with the download URL. When LM Studio is not connected, it suggests the specific menu location. These are actionable, specific messages.

**One gap:** `stats.ts:53-59` handles missing index by printing `{ error: 'No index found' }` in JSON mode. This is fine for humans but the JSON output lacks any error code or structured error shape, making programmatic handling inconsistent with the typed error objects from other commands.

---

## 6. User Experience and Naming

**Command names:** Excellent. Short, verb-form names where appropriate (index, search), noun-form for introspection (stats, tree). `backlinks` and `links` are clear and expected. `duplicates` is slightly verbose (vs `dupes`) but unambiguous.

**Flag naming conventions:**
- Boolean flags: `--embed`, `--watch`, `--force`, `--json`, `--pretty` — correct
- Negation: `--no-embed`, `--no-gitignore` — correct convention
- Multi-word flags: kebab-case throughout — correct
- Aliases: single-character, lowercase, occasionally uppercase (`-H` for `--heading-only`) — acceptable

**One naming inconsistency:** The `context` command uses `-x` as the alias for `--exclude` (sections). The `index` command also uses `-x` for `--exclude` (file patterns). Consistent alias reuse is fine here since they apply to different domains. But `--context` as a flag name in the `search` command conflicts conceptually with the `context` command name. A user who types `mdcontext search "auth" --context 3` is using `--context` to mean "lines of context" — the word is overloaded at the product level.

**The `-C/-B/-A` grep-style context flags** (`search.ts:193-206`) are excellent. Users familiar with grep will transfer their mental model immediately.

**`--summarize` / `-s`** is a heavy feature buried as a flag of `search`. Given its complexity (cost estimation, streaming, provider selection), it could be a standalone subcommand or at minimum needs better discoverability. The help text at `help.ts:182-186` does list it, but it is easy to miss.

---

## 7. Progress Indicators and Feedback

**Indexing progress:** `index-cmd.ts:182-188` uses raw ANSI escape codes (`\x1b[2K\r`) to overwrite the current line. This works on capable terminals but is not guarded by a TTY check. In CI or pipe contexts, the escape codes would appear as literal characters in stdout. The JSON mode skips this (`if (!json)`), but `--no-color` / non-TTY contexts are not handled separately.

**Embedding progress:** Same pattern at `index-cmd.ts:311-320`. The `\r${' '.repeat(120)}\r` clear at line 326 is a brittle hardcoded width assumption.

**Watch mode:** `index-cmd.ts:145-174` handles `SIGINT` correctly and prints "Stopped watching." before exit.

**Rerank download progress:** `search.ts:339-345` uses `process.stdout.write` with `\r` for in-place progress. Again, no TTY guard.

**No spinner library is used** for operations with indeterminate duration. The tool has `@clack/prompts` as a dependency (used in `embeddings.ts` for the interactive namespace picker), but it is not used for progress spinners elsewhere. Operations like "Checking embeddings..." (`index-cmd.ts:272`) show static text then block silently until complete. For operations that take 30+ seconds, this appears hung.

---

## 8. Configuration Integration

**Precedence chain:** CLI flags > environment variables > config file > defaults. This is documented in `config-layer.ts:73-76` and confirmed by the `createConfigProvider` pattern.

**Config file discovery:** Automatic, based on `findConfigFile` walking upward from cwd.

**`--config` / `-c` flag:** Extracted before Effect CLI parsing at `main.ts:124-181`. Supports both `--config=path` and `--config path` syntax. JSON files use synchronous loading; JS/TS/MJS files use dynamic import. The async path wraps in an IIFE at `main.ts:394-430`.

**Config validation:** `validateConfigObject` at `main.ts:225-251` checks that at least one recognized key exists if the object is non-empty. The recognized keys are `['index', 'search', 'embeddings', 'summarization', 'output', 'paths']`. If a user creates a config with only typo'd keys (e.g., `{ embedings: {} }`), the validation fires with a helpful "Found keys: embedings, Expected at least one of: index, search, ..." message.

**What is not wired:** The `output.color` and `output.verbose` config values (`config-layer.ts:131-140`) are defined in the config schema and extractable via `getOutputConfig`, but they are never read by any command. The TTY escape codes in progress output do not consult `output.color`. This means setting `color: false` in config has no effect.

---

## 9. stdin/stdout/stderr Separation

**stdout:** All primary output (`Console.log`) goes to stdout. JSON output uses `Console.log`. Correct.

**stderr:** Error messages use `console.error` in `main.ts` (lines 138, 148, etc.) and `Console.error` inside Effect effects in `error-handler.ts:428-447`. Correct.

**Mixed case:** `context.ts:199-206` uses `Console.error` for "No sections found matching..." which is appropriate since it is a non-fatal condition that still allows other files to be processed.

**Subtle issue:** The prompts in `index-cmd.ts` (the embedding cost prompt) write to stdout via `Console.log`, then read from stdin via `readline`. If stdout is piped (`mdcontext index | tee log.txt`), the prompt text goes to the pipe rather than the terminal. The `promptUser` function at `index-cmd.ts:30-41` should write the prompt to stderr or check `process.stdout.isTTY` before prompting. The `--no-embed` flag is the documented escape, but the issue still exists.

---

## 10. Interactive vs Non-Interactive Mode

**Detection:** `embeddings.ts:32-33` defines `isInteractiveTTY` correctly:
```typescript
const isInteractiveTTY = (): boolean =>
  process.stdout.isTTY && process.stdin.isTTY
```

This function is used in the embeddings command to decide whether to show the interactive namespace picker. Good.

**Not consistently applied:** The `promptUser` function in `index-cmd.ts:30-41` and `search.ts:144-155` does not check TTY. In a non-interactive context (CI, scripts), the prompt will block indefinitely waiting for stdin that will never provide input. The `--no-embed` flag mitigates this for index, but search has an auto-index prompt path (at `search.ts` after the auto-index threshold check) with the same vulnerability.

**JSON mode suppresses interactive prompts** in some but not all paths. The cost estimate prompt in `index-cmd.ts:352` is guarded by `!json`, which is correct. The auto-index prompt in the search command should also check `json` before prompting, but this needs verification in the full search command body.

---

## 11. Command Help Text: Completeness and Accuracy

The custom help system at `help.ts` is high quality. Usage strings, examples, and notes are accurate for the commands that have entries.

**Issues:**

1. `duplicates` has no help entry (covered in section 2).

2. The `help.ts` search examples include `--refine` in some implicit forms but the `--refine` flag does not appear in the search OPTIONS table at `help.ts:117-192`. The flag is implemented (`search.ts:293-298`) and in `flag-schemas.ts:197-202`, but absent from the rendered help.

3. The search help notes at `help.ts:201-223` mention `--threshold`, `--rerank`, quality modes, and HyDE in depth. These notes are accurate and useful. But users who read `--help` first would not know these features exist from the OPTIONS table alone — the notes section requires reading to the bottom.

4. The `context` command help at `help.ts:247` says the default token budget is "2000" which matches the implementation at `context.ts:43`. Consistent.

5. `links` and `backlinks` commands (`help.ts:306-339`) have no NOTES section despite requiring an index to exist. The backlinks entry notes this at line 339, but links does not, even though it reads from the same index.

6. The main help at `help.ts:514-519` lists `--config <file>` as a global option with alias `-c`. This is accurate. But `--version` is listed (`-v`) while the actual implementation uses Effect CLI's built-in version flag, which was hidden via `showBuiltIns: false`. The help text at `shouldShowMainHelp` (`help.ts:579-588`) shows main help when no args are given or when `--help` or `-h` are present. However, `--version` is not intercepted in `shouldShowMainHelp` — Effect CLI handles version, which may or may not render correctly after `showBuiltIns: false` is set.

---

## 12. Missing Commands

Given the tool's purpose (markdown indexing and search for LLM consumption), the following would be expected:

**Missing:**
- `mdcontext watch [path]` as a top-level command. Watch mode is buried as `mdcontext index --watch`. For a common workflow, this should be discoverable as a first-class command.
- `mdcontext version` or reliable `--version` behavior. The version flag handling depends on Effect CLI internals after the custom help override.
- `mdcontext clean [path]` to remove the `.mdcontext` index directory. Users currently must `rm -rf .mdcontext` manually. This is a common need (corrupted index, disk space, fresh start).
- `mdcontext validate [path]` to check that indexed files are still present and the index is not stale. Partial functionality exists in `stats`, but there is no explicit validation command.

**Not missing but poorly discoverable:**
- `duplicates` is not in main help or help registry (covered above).
- `embeddings` subcommands (`list`, `current`, `switch`, `remove`) are documented in help.ts but the embeddings command itself is listed at the bottom of the main help, after `backlinks` and `stats`.

---

## 13. Shell Completion Support

**None exists.** There are no completion scripts for bash, zsh, fish, or PowerShell. The `@effect/cli` framework does include a `--completions` built-in, but it was hidden along with other built-ins via `showBuiltIns: false` at `main.ts:87-89`.

This is a significant gap for a developer tool. Without completions:
- Flag names must be memorized or looked up
- File path completion does not work for `--config`, `--path`, file arguments
- Subcommand names are not tab-completed

The `@effect/cli` completions could be re-enabled selectively, or custom completion scripts could be generated and distributed. The package.json has no `postinstall` completion installation (only `rebuild-hnswlib.js`).

---

## 14. Structural Issues Summary Table

| Issue | File | Severity |
|---|---|---|
| `duplicates` missing from helpContent | `help.ts` | High — `--help` errors on a valid command |
| `duplicates` missing from main help listing | `help.ts:471-480` | High — command is undiscoverable |
| Search schema missing 9 flags | `flag-schemas.ts:135-206` | High — blocks `--rerank`, `--summarize`, etc. |
| No TTY check before interactive prompts | `index-cmd.ts:393`, `search.ts` | Medium — hangs in CI/scripts |
| No shell completions | project-wide | Medium — developer UX gap |
| Progress output not guarded by TTY | `index-cmd.ts:185`, `search.ts:344` | Medium — ANSI noise in pipes |
| `output.color` config value never read | all commands | Low — config option silently ignored |
| `--threshold` has no bounds validation | `search.ts:189-192` | Low — silent bad behavior |
| `--refine` missing from search help OPTIONS | `help.ts:117-192` | Low — implemented but undocumented in help |
| Hardcoded 120-char line clear | `index-cmd.ts:326` | Low — breaks on narrow terminals |
| Duplicate Levenshtein implementation | `error-handler.ts:589`, `typo-suggester.ts:12` | Low — maintenance debt |

---

## 15. Positive Observations

These are done well and worth preserving:

1. **Typed error taxonomy** (`error-handler.ts`) with documented exit codes. The Match.exhaustive guarantee means adding a new error type forces updating the handler.

2. **Provider-specific error messages** for Ollama, LM Studio, OpenAI, Voyage. Context-aware suggestions ("ollama pull nomic-embed-text") rather than generic "check your configuration".

3. **The argv preprocessor** solves a real problem cleanly. The schema-driven flag-takes-value detection at `argv-preprocessor.ts:174` prevents misclassifying flag arguments as positionals.

4. **Typo suggestions via Levenshtein** (`typo-suggester.ts`). The prefix-match preference at lines 97-112 means `--js` correctly suggests `--json` over a pure edit-distance result.

5. **`--no-embed` escape hatch** for CI environments. Documented, functional, correctly named.

6. **Consistent `--json` / `--pretty` across all commands.** Machine-readable output is a first-class concern, not an afterthought.

7. **Config file validation** with key enumeration. "Found keys: foo, Expected at least one of: index, search..." is far better than a silent no-op or a stack trace.

8. **HNSW parameter documentation inline** in flag descriptions. Users do not need to read separate docs to understand the tradeoffs of `--hnsw-m 24` vs `--hnsw-m 12`.

---

## File References

- Entry point: `src/cli/main.ts`
- Command index: `src/cli/commands/index.ts`
- Help system: `src/cli/help.ts`
- Error handling: `src/cli/error-handler.ts`
- Argv preprocessing: `src/cli/argv-preprocessor.ts`
- Flag schemas: `src/cli/flag-schemas.ts`
- Typo suggestions: `src/cli/typo-suggester.ts`
- Shared options: `src/cli/options.ts`
- Config layer: `src/cli/config-layer.ts`
- Shared error utilities: `src/cli/shared-error-handling.ts`
- CLI utilities: `src/cli/utils.ts`
- Commands: `src/cli/commands/{index-cmd,search,context,tree,links,backlinks,stats,duplicates,embeddings,config-cmd}.ts`

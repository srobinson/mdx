---
title: Fabric internals — Jina scrape, sessions/contexts/strategies, pattern authoring
type: research
tags: [fabric, danielmiessler, go, cli, llm, prompt-engineering, templates]
summary: Internals of three fabric subsystems — the Jina r.jina.ai/s.jina.ai scrape path, the session/context/strategy storage and prompt-assembly model, and the system.md pattern-authoring format with its sentinel-protected variable engine.
status: active
source: github-researcher
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

# Fabric internals deep-dive

Pinned to local clone HEAD **`29b32f9`** (`29b32f9ff2ced48ff3425cd61c6e5083047f88d3`), tag **v1.4.454**, read from `/Users/alphab/Dev/LLM/DEV/helioy/REFS/fabric`. All `file:line` citations are relative to that repo root. This is a functionality/internals explainer, not a comparison.

Config root throughout is `~/.config/fabric` (`internal/cli/initialization.go:23` calls `fsdb.NewDb(filepath.Join(homedir, ".config/fabric"))`).

---

## A. The Jina scrape path (`-u`/`--scrape_url`, `-q`/`--scrape_question`)

### Flags and dispatch
Both flags are declared on the `Flags` struct:
- `internal/cli/flags.go:68` — `ScrapeURL  string  short:"u" long:"scrape_url"  description:"Scrape website URL to markdown using Jina AI"`
- `internal/cli/flags.go:69` — `ScrapeQuestion  string  short:"q" long:"scrape_question"  description:"Search question using Jina AI"`

Dispatch happens in `handleToolProcessing` (`internal/cli/tools.go:61-89`). When either flag is non-empty:
1. `registry.Jina.IsConfigured()` is checked (`tools.go:62`); if false it errors with `scraping_not_configured`. **But Jina is effectively always configured** — see "Key is optional" below.
2. `ScrapeURL != ""` → `registry.Jina.ScrapeURL(currentFlags.ScrapeURL)` (`tools.go:69`), result appended via `AppendMessage` (`tools.go:72`).
3. `ScrapeQuestion != ""` → `registry.Jina.ScrapeQuestion(...)` (`tools.go:78`), appended (`tools.go:82`).
4. If this is **not** a chat request (no pattern/message), the scraped text is just written to output and returned (`tools.go:85-88`).

### The Jina client (whole file is 72 lines: `internal/tools/jina/jina.go`)
```go
// jina.go:37-39
func (jc *Client) ScrapeURL(url string) (ret string, err error) {
    return jc.request(fmt.Sprintf("https://r.jina.ai/%s", url))
}
// jina.go:41-43
func (jc *Client) ScrapeQuestion(question string) (ret string, err error) {
    return jc.request(fmt.Sprintf("https://s.jina.ai/%s", question))
}
```

- **`scrape_url` hits the Reader endpoint** `https://r.jina.ai/<url>` (`jina.go:38`). Jina Reader returns the page rendered as clean, LLM-friendly **markdown** (readability extraction). The target URL is concatenated raw into the path with no escaping; you pass the full `https://...` and it becomes `https://r.jina.ai/https://example.com/page`.
- **`scrape_question` hits the Search endpoint** `https://s.jina.ai/<question>` (`jina.go:42`). Jina Search runs a web search for the question and returns the **top results already read into markdown**. The question string is concatenated raw (spaces and all) into the path.

### HTTP behavior (`request`, `internal/tools/jina/jina.go:45-72`)
- Method is a plain **`GET`** (`jina.go:47`).
- **Auth header is optional and only set if a key exists**: `if jc.ApiKey.Value != "" { req.Header.Set("Authorization", "Bearer "+jc.ApiKey.Value) }` (`jina.go:53-55`).
- Uses a bare `&http.Client{}` (`jina.go:57`) with **no timeout configured** — i.e. it relies on Go's default (no client-side deadline). There is no retry logic.
- The entire response body is read with `io.ReadAll` and returned **verbatim as a string** (`jina.go:65-70`). No status-code check, no content-type check.

### Key is optional (`JINA_AI_API_KEY` not required)
The API key setup question is registered with `required=false`:
```go
// jina.go:31
ret.ApiKey = ret.AddSetupQuestion("API Key", false)
```
`IsConfigured()` walks settings and calls `IsValid()`, which returns `o.IsDefined() || !o.Required` (`internal/plugins/plugin.go:163`). Because `Required=false`, an undefined key still validates, so `registry.Jina.IsConfigured()` is **true even with no key**. Anonymous (keyless) Jina requests therefore work; the key only raises rate limits.

**Env var name** is derived, not hardcoded. Label is `"Jina AI"` (`jina.go:21`); `BuildEnvVariablePrefix("Jina AI")` → `JINA_AI_` (`plugin.go:336-350`, upper-case + spaces→`_`). Setting name `"API Key"` → `API_KEY`. Concatenated: **`JINA_AI_API_KEY`** (`plugin.go:57`). It is read from env at `Setting.Configure()` (`plugin.go:284-290`), also loadable from `~/.config/fabric/.env`.

### How scraped text reaches the model
`messageTools` accumulates with `AppendMessage(message, newMessage)` which joins with `\n` (`internal/cli/flags.go:566-573`). In a chat request, `handleChatProcessing` prepends it onto the user message: `currentFlags.AppendMessage(messageTools)` → `o.Message = AppendMessage(o.Message, message)` (`internal/cli/chat.go:22-24`, `flags.go:549-551`). So the scraped markdown becomes part of the **user input** the pattern operates on.

### Failure modes
- **No key**: works (keyless requests allowed; `jina.go:53` simply skips the header).
- **Non-200 / rate-limit (429)**: not detected. The error body (HTML/JSON from Jina) is returned as the "scraped content" string and fed to the model (`jina.go:65-70`). Only transport-level errors (`client.Do` failure, `jina.go:59`) surface as Go errors.
- **Empty content**: returns an empty string, appended as an empty message.
- **Request-construction error**: wrapped via i18n `jina_error_creating_request` (`jina.go:48`).

### Example commands
```bash
# Scrape a page to clean markdown and summarize it (keyless works)
fabric -u https://example.com/article -p summarize

# Raise limits with a key (any of these)
export JINA_AI_API_KEY=jina_xxx
fabric -u https://example.com/article -p extract_wisdom

# Search the web for a question, feed top results into a pattern
fabric -q "what is the CAP theorem" -p extract_wisdom

# No pattern -> just dump the scraped markdown to a file
fabric -u https://example.com -o page.md
```

---

## B. Sessions, Contexts, Strategies

Three distinct concepts, three distinct on-disk homes. All live under `~/.config/fabric` and are wired in `fsdb.NewDb` (`internal/plugins/db/fsdb/db.go:14-34`).

### Definitions
- **Session** = a persisted, append-only **conversation transcript** (system/user/assistant turns) that accumulates across CLI invocations. Struct: `Session{ Name string; Messages []*chat.ChatCompletionMessage }` (`internal/plugins/db/fsdb/sessions.go:40-45`).
- **Context** = a static reusable **system-prompt prefix** (a named blob of text injected ahead of the pattern). Struct: `Context{ Name string; Content string }` (`internal/plugins/db/fsdb/contexts.go:29-32`).
- **Strategy** = a named **reasoning-instruction preamble** (e.g. Chain-of-Thought) prepended to the *whole* system prompt. Struct: `Strategy{ Name, Description, Prompt string }` (`internal/plugins/strategy/strategy.go:56-60`).

### Storage on disk
| Concept | Directory | Format | Where set |
|---|---|---|---|
| Sessions | `~/.config/fabric/sessions/` | one **`.json`** file per session (marshalled `[]*ChatCompletionMessage`) | `db.go:27-28` (`FileExtension: ".json"`) |
| Contexts | `~/.config/fabric/contexts/` | plain text file, **no extension** | `db.go:30-31` |
| Strategies | `~/.config/fabric/strategies/` | one **`.json`** file per strategy | `strategy.go:132`, `strategy.go:180` |

Session JSON is written by `SaveSession` → `SaveAsJson(session.Name, session.Messages)` → `json.Marshal` then `os.WriteFile(..., 0644)` (`sessions.go:36-38`, `storage.go:137-146`, `storage.go:90-95`). Contexts are read raw via `Load` (`contexts.go:10-18`). Strategy JSON shape:
```json
// data/strategies/cot.json
{ "description": "Chain-of-Thought (CoT) Prompting",
  "prompt": "Think step by step to answer the question. Return the final answer in the required format." }
```
Strategies are bootstrapped by `fabric --setup` / `Setup()`, which git-clones `data/strategies` from the fabric repo into `~/.config/fabric/strategies` (`strategy.go:114-165`, `DefaultStrategiesGitRepoUrl`/`DefaultStrategiesGitRepoFolder` at `strategy.go:18-19`). `LoadStrategy` validates against path traversal (`strategy.go:206-211`).

### `--session`: how history accumulates
Flag: `internal/cli/flags.go:32` (`--session`, no short flag). Maps into `ChatRequest.SessionName` (`flags.go:485`).

Read/write cycle inside the chatter:
1. **Read on entry**: `BuildSession` calls `o.db.Sessions.Get(request.SessionName)` (`internal/core/chatter.go:219-225`), which loads the existing `.json` into `session.Messages` (`sessions.go:15-24`); a missing file just prints "creating new" and starts empty.
2. New turns are **appended** to the in-memory session during assembly (system + user) and then the **assistant reply is appended** after the model responds: `session.Append(&chat.ChatCompletionMessage{Role: Assistant, Content: message})` (`chatter.go:210`).
3. **Write on exit**: `if session.Name != "" { o.db.Sessions.SaveSession(session) }` (`chatter.go:212-214`). Only **named** sessions persist; an unnamed session is ephemeral.

So each `fabric --session foo ...` call rehydrates the full prior transcript, sends it to the model as history, then writes the growing transcript back. `GetVendorMessages()` strips internal `Meta`-role messages before sending to the LLM (`sessions.go:62-76`).

### `--context`/`-C`: how a context is injected
Flag: `internal/cli/flags.go:31` (`-C`/`--context`). Maps to `ChatRequest.ContextName` (`flags.go:484`). In `BuildSession`, if set, the context file is loaded and its `Content` becomes `contextContent` (`chatter.go:236-243`), which is then placed at the **front of the system message** (see assembly order below).

### `--strategy`: reasoning preamble
Flag: `internal/cli/flags.go:88` (`--strategy`). Maps to `ChatRequest.StrategyName` (`flags.go:487`). In `BuildSession`, `strategy.LoadStrategy(name)` is loaded and, if its `Prompt` is non-empty, it is prepended to the **very front** of the whole system message (`chatter.go:282-290`).

### Exact prompt-assembly order (`BuildSession`, `internal/core/chatter.go:218-353`)
This is the real precedence:
1. Load session (existing transcript) if `SessionName` set (`chatter.go:219-228`).
2. Append a `Meta` message if `request.Meta != ""` (the raw CLI args string; stripped before the LLM sees it) (`chatter.go:230-232`).
3. Resolve `contextContent` from the context file (`chatter.go:236-243`).
4. Apply template vars to the **user input** if `InputHasVars` (`chatter.go:256-261`).
5. Resolve `patternContent` (loads `system.md`, substitutes `{{input}}` + variables) (`chatter.go:263-278`).
6. **`systemMessage = joinPromptSections(contextContent, patternContent)`** — context FIRST, then pattern (`chatter.go:280`).
7. If strategy set: **`systemMessage = joinPromptSections(strategy.Prompt, systemMessage)`** — strategy prepended to the FRONT (`chatter.go:282-290`).
8. If non-English language: wrap the whole thing with a translate-after-execution instruction (`chatter.go:293-296`).
9. Append the assembled `systemMessage` as a **system-role** message, then append the user message (`chatter.go:337-346`). `joinPromptSections` trims and drops empties, joining with `\n` (`chatter.go:46-57`).

**Final effective order:** `strategy.Prompt → context.Content → pattern system.md → (existing session history, prepended as prior messages) → current user input`. Existing session history precedes the new turn because it was loaded into `session.Messages` in step 1; the new system+user messages are appended after it. (In `raw` mode, the system text is folded into the user message instead — `chatter.go:298-336`.)

### Managing sessions and contexts
| Action | Flag | Dispatch |
|---|---|---|
| List sessions | `-X`/`--listsessions` | `listing.go:87-88` |
| List contexts | `-x`/`--listcontexts` | `listing.go:82-83` |
| List strategies | `--liststrategies` | `listing.go:92-93` |
| Print a session | `--printsession <name>` | `management.go:20-21` |
| Print a context | `--printcontext <name>` | `management.go:25-26` |
| Delete a session | `-W`/`--wipesession <name>` | `management.go:15-16` |
| Delete a context | `-w`/`--wipecontext <name>` | `management.go:10-11` |

Flag defs: `flags.go:44-45`, `flags.go:71-74`, `flags.go:89`.
**Create** is implicit: a session is created the first time you use `--session newname`; a context is created by dropping a text file into `~/.config/fabric/contexts/`.

### Example: multi-turn session + context + strategy
```bash
# Create a context (just a text file, no extension)
mkdir -p ~/.config/fabric/contexts
printf 'You are advising a Go backend team. Prefer stdlib.\n' > ~/.config/fabric/contexts/goteam

# Turn 1 (creates the session file ~/.config/fabric/sessions/proj.json)
echo "How should I structure a CLI?" | fabric --session proj -C goteam -p ai

# Turn 2 - history from turn 1 is reloaded and extended
echo "Now add config loading." | fabric --session proj -C goteam -p ai

# Add Chain-of-Thought reasoning preamble to the front of the system prompt
echo "Tricky logic puzzle..." | fabric --session proj --strategy cot

# Inspect / clean up
fabric --listsessions
fabric --printsession proj
fabric --wipesession proj
```

---

## C. The pattern-authoring format (`system.md`)

### Anatomy of a `system.md`
A pattern is a directory `patterns/<name>/system.md`. Read `data/patterns/extract_wisdom/system.md` for the canonical shape. Conventional H1 sections:
- **`# IDENTITY and PURPOSE`** — role framing ("You extract surprising, insightful... information from text content...").
- **`# STEPS`** — the bulleted procedure ("Extract a summary of the content in 25 words... into a section called SUMMARY", etc.).
- **`# OUTPUT INSTRUCTIONS`** — format constraints ("Only output Markdown", "Write the IDEAS bullets as exactly 16 words").
- **`# INPUT`** — usually ends with the `{{input}}` placeholder where user text is spliced in.

These headers are a **convention only**; the loader treats the file as opaque text and does not parse sections.

### `user.md`
47 patterns ship a `user.md` alongside `system.md` (`find data/patterns -name user.md` → 47 hits, e.g. `data/patterns/analyze_claims/user.md`). **The CLI/library path never reads `user.md`** — grep for `user\.md` across `*.go` returns zero consumers; `SystemPatternFile` is hardcoded to `"system.md"` (`db.go:22`) and that is the only file `getFromDB` opens (`patterns.go:124`, `patterns.go:135`). `user.md` is a convention for the web chat UI (separate user-turn template) and is inert for `fabric -p <name>` on the CLI. You'd add one only when authoring for the web surface.

### Variable substitution and the sentinel
Two placeholders matter: `{{input}}` (the piped/typed user text) and arbitrary `{{custom}}` variables supplied via `-v`. Flag: `-v`/`--variable`, a `map[string]string` (`flags.go:30`), parsed by go-flags with `:` as the key/value separator. Example from the flag help: `-v=#role:expert -v=#points:30` → keys `#role`, `#points`. The pattern references the key **exactly as given** (e.g. `{{#role}}`, or `{{lang_code}}` matched by key `lang_code` per `docs/rest-api.md:187`).

Resolution order (`internal/plugins/db/fsdb/patterns.go:98-118`, `applyVariables`):
1. `ensureInput` guarantees the pattern contains `{{input}}`, appending it if absent (`patterns.go:84-91`).
2. **`{{input}}` is swapped for a sentinel** `__FABRIC_INPUT_SENTINEL_TOKEN__` *before* variable expansion (`patterns.go:105`, sentinel const at `internal/plugins/template/constants.go:5`). This protects untrusted user input: it is held out of the recursive template pass so that any `{{...}}` *inside* the user's text is not interpreted as a template directive.
3. `template.ApplyTemplate(withSentinel, variables, input)` resolves everything else (`patterns.go:110`).
4. **Sentinel is replaced back with the real input** as the final step (`patterns.go:116`).

`ApplyTemplate` (`internal/plugins/template/template.go:56-153`) loops over `{{...}}` tokens until none remain:
- `{{ext:...}}` → external extension call (`template.go:76-91`).
- `{{plugin:ns:op:val}}` → built-in plugins `text|datetime|file|fetch|sys` (`template.go:94-129`).
- `{{input}}` or the sentinel literal → replaced with `input` (`template.go:132-134`).
- any other `{{name}}` → looked up in the `-v` variables map; **a missing variable is a hard error** (`template_missing_required_variable`, `template.go:136-143`). A no-progress pass aborts with `template_processing_stuck` (`template.go:146-148`).

`GetWithoutVariables` (used when `--no-variable-replacement` is set) skips all of this and only substitutes `{{input}}` (`patterns.go:43-51`, `applyInput` at `patterns.go:93-96`).

### Custom-dir-overrides-bundled precedence
`getFromDB` checks the **custom patterns directory first**, then falls back to the main dir (`internal/plugins/db/fsdb/patterns.go:121-157`):
```go
// patterns.go:122-132
if o.CustomPatternsDir != "" {
    customPatternPath := filepath.Join(o.CustomPatternsDir, name, o.SystemPatternFile)
    if pattern, customErr := os.ReadFile(customPatternPath); customErr == nil {
        return &Pattern{Name: name, Pattern: string(pattern)}, nil
    }
}
// fallback:
patternPath := filepath.Join(o.Dir, name, o.SystemPatternFile) // ~/.config/fabric/patterns/<name>/system.md
```
`CustomPatternsDir` comes from the `CUSTOM_PATTERNS_DIRECTORY` env var, with `~/` expansion (`db.go:55-65`). The default "main" dir is `~/.config/fabric/patterns` (populated by `fabric --setup`/`--update` from the repo's `data/patterns`). So a same-named pattern in your custom dir **shadows** the bundled one. `GetNames` merges both dirs into a deduped, sorted set with custom winning (`patterns.go:212-254`).

### `--listpatterns` enumeration
Flag `-l`/`--listpatterns` (`flags.go:41`). Dispatch at `internal/cli/listing.go:37-62`: it calls `fabricDb.Patterns.GetNames()` (merged custom+main dirs), and if empty prints setup guidance; otherwise `ListNames` prints one pattern name per line (`patterns.go:257-274`). **It lists names only** — there is no bundled `pattern_descriptions.json`/tags file consumed by the CLI loader; the only metadata file referenced is `unique_patterns.txt` for `--latest` (`db.go:23`, `patterns.go:170-185`). Pattern descriptions/tags live in the web app, not the CLI path.

### Authoring a brand-new pattern end-to-end
Create the directory and one file; it is immediately invocable as `-p <name>`:
```bash
mkdir -p ~/.config/fabric/patterns/tldr_bullets
cat > ~/.config/fabric/patterns/tldr_bullets/system.md <<'EOF'
# IDENTITY and PURPOSE

You are a ruthless summarizer. You turn any input into a tight bullet list.

# STEPS

- Read the entire input.
- Identify the 5 most important points.

# OUTPUT INSTRUCTIONS

- Output only Markdown.
- Output exactly 5 bullets, each at most 12 words.
- Do not add a preamble or a conclusion.

# INPUT

INPUT:

{{input}}
EOF

# Invoke it
echo "long text here..." | fabric -p tldr_bullets
pbpaste | fabric -p tldr_bullets

# With a custom variable (key matches the {{token}} exactly)
# system.md references {{#tone}}, supply it with:
echo "..." | fabric -p some_pattern -v=#tone:sarcastic
```
If you omit the `{{input}}` line, `ensureInput` appends it automatically (`patterns.go:84-91`), so the user text is always spliced in.

---

## Sources consulted
- `internal/tools/jina/jina.go` (entire client)
- `internal/cli/tools.go`, `internal/cli/chat.go`, `internal/cli/flags.go`, `internal/cli/listing.go`, `internal/cli/management.go`, `internal/cli/initialization.go`
- `internal/plugins/plugin.go` (SetupQuestion / IsConfigured / env-var derivation)
- `internal/core/chatter.go` (`Send`, `BuildSession`, prompt assembly)
- `internal/plugins/db/fsdb/{db,sessions,contexts,storage,patterns}.go`
- `internal/plugins/strategy/strategy.go`
- `internal/plugins/template/{template,constants}.go`
- `data/patterns/extract_wisdom/system.md`, `data/strategies/cot.json`, `docs/rest-api.md`

## Open questions
- Exact Jina rate-limit/timeout behavior is environment-dependent; the client sets no explicit timeout (`jina.go:57`), so it inherits Go defaults and any upstream Jina-side limits.
- The web server path (`internal/server/`) may consume `user.md` and pattern descriptions; this doc covers the CLI/library path only.

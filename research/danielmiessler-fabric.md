---
title: "Fabric (danielmiessler/fabric) — What It Does and How You Use It"
type: research
tags: [fabric, cli, patterns, prompt-library, youtube, llm-tooling, go-cli, user-guide]
summary: "Fabric is a Go CLI that turns 254 crowdsourced markdown system-prompts (Patterns) into composable one-shot commands over 19 LLM vendors, with first-class ingestion of YouTube, URLs, stdin, PDFs, and files, plus a REST server and SvelteKit web GUI."
status: active
source: github-researcher
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

# Fabric — What It Does and How You Use It

Analyzed at HEAD **v1.4.454** (commit `29b32f9`, release dated 2026-06-02). All `file:line` citations are from that checkout. This is a functionality-focused user guide, not a comparison.

---

## 1. Core mental model

Fabric is a single Go binary that applies a **named, reusable system prompt** (a "Pattern") to whatever text you feed it, and prints the model's answer. You pipe content in, name a Pattern with `-p`, optionally name a model with `-m`, and you get a structured result. That is the whole loop: `<some input> | fabric -p <pattern>`.

The problem it solves: good prompts are the hard part of using LLMs, and most people rewrite the same "summarize this," "extract the key claims," "rate this essay" prompts over and over. Fabric makes those prompts **first-class, versioned, shareable artifacts**. The project ships **254 Patterns** (`data/patterns/*/`) contributed by the community, and you can add your own.

A **Pattern from a user's POV** is just a directory named for the task (e.g. `extract_wisdom/`) containing a `system.md` file: a plain-markdown system prompt with `IDENTITY`, `STEPS`, `OUTPUT INSTRUCTIONS`, and `INPUT` sections. Some patterns also carry a `user.md` (a user-turn template). Because they are markdown, you can read, fork, and tune any of them. The directory name *is* the invocation key you pass to `-p`.

On top of one-shot prompting, Fabric adds input adapters (YouTube, web pages, PDFs, audio transcription), output adapters (clipboard, files, PDF), persistent **sessions** and **contexts**, reasoning **strategies** (CoT/ToT/etc.), a **REST API server**, and a **SvelteKit web GUI**.

---

## 2. The canonical example, line by line

```bash
fabric -y "https://youtube.com/watch?v=uXs-zPc63kM" --stream --pattern extract_wisdom
```

This appears verbatim in the README (README.md:848). What each piece does:

- **`-y "<url>"`** (`--youtube`, flags.go:56). Takes a YouTube video or playlist URL. By default it grabs the **transcript** and feeds it as the input message. The dispatch lives in `processYoutubeVideo` (cli.go:117-177): the default branch (`!comments && !metadata && !visual`) calls `registry.YouTube.GrabTranscriptWithArgs(videoId, language, ...)` (cli.go:135). Transcript extraction shells out to **`yt-dlp`**, which must be installed separately (`youtube.go:4`, `exec.LookPath("yt-dlp")` at youtube.go:223). The transcript text becomes the message that the Pattern operates on. No YouTube API key is required for transcripts; `yt-dlp` does the work. (Comments/metadata use the YouTube Data API and do want an API key.)
- **`--stream`** (`-s`, flags.go:37). Streams tokens to your terminal as the model generates, instead of waiting for the full response. Internally, when `o.Stream` is true, `Chatter.Send` opens a `responseChan` and prints `StreamTypeContent` updates as they arrive (chatter.go:102-153).
- **`--pattern extract_wisdom`** (`-p`, flags.go:29). Loads `data/patterns/extract_wisdom/system.md` as the system prompt. That prompt instructs the model to pull SUMMARY, IDEAS, INSIGHTS, QUOTES, HABITS, FACTS, REFERENCES, ONE-SENTENCE TAKEAWAY, and RECOMMENDATIONS out of the transcript, with strict formatting (16-word bullets, markdown only).

**End-to-end flow:** parse flags → `yt-dlp` fetches the transcript for `uXs-zPc63kM` → transcript becomes the user message → `extract_wisdom/system.md` becomes the system message → the request goes to your default model/vendor → tokens stream to stdout as structured markdown. Add `-o out.md` to also write the result to a file.

---

## 3. Input modalities — everything you can feed it

**YouTube** (`-y` / `--youtube`, flags.go:56). Transcript is the default. Modifier flags select what to grab:
- Transcript (default), or explicitly: `--transcript` (flags.go:58); with timestamps: `--transcript-with-timestamps` (flags.go:59).
- Comments: `--comments` (flags.go:63, `GrabComments`).
- Metadata as JSON: `--metadata` (flags.go:64, `GrabMetadata`).
- Playlist: `--playlist` prefers the playlist over a single video when both IDs are in the URL (flags.go:57).
- Extra `yt-dlp` flags: `--yt-dlp-args '--cookies-from-browser brave'` (flags.go:65), useful for age-gated/region-locked videos.
```bash
fabric -y "https://youtube.com/watch?v=ID" --comments --pattern analyze_claims
fabric -y "https://youtube.com/playlist?list=ID" --playlist --metadata
```

**URLs / web scraping** (`-u` / `--scrape_url`, flags.go:68). Scrapes a page to clean LLM-friendly markdown via **Jina AI** (`https://r.jina.ai/<url>`, jina.go:38). Companion `-q` / `--scrape_question` (flags.go:69) runs a Jina web search (`https://s.jina.ai/`). Requires a Jina key configured in setup (`registry.Jina.IsConfigured()`, tools.go:62).
```bash
fabric -u "https://example.com/article" --pattern extract_article_wisdom
```

**stdin / pipes** (no flag — the default). Anything on stdin becomes the input.
```bash
pbpaste | fabric --pattern summarize
cat notes.md | fabric --pattern extract_main_idea
echo "ai security primer" | fabric --pattern write_essay
```

**Local files, PDFs, images** (`-a` / `--attachment`, flags.go:33). Attach a path or URL; used for multimodal input (e.g. OpenAI image recognition). Pair with the `to_pdf` helper to render LaTeX output back to PDF (see helpers).
```bash
fabric -a ./paper.pdf --pattern analyze_paper
fabric -a ./diagram.png --pattern "explain this image"
```

**Audio/video transcription** (`--transcribe-file`, flags.go:103). Transcribes media (separate `--transcribe-model`, optional `--split-media-file` for >25MB via ffmpeg) and feeds the text to the Pattern.

**Clipboard / copy output** (`-c` / `--copy`, flags.go:48). Copies the model's output to the system clipboard. Combine with `pbpaste` on the input side for a full clipboard round-trip.
```bash
pbpaste | fabric --pattern improve_writing --copy
```

---

## 4. The flag surface

All from `internal/cli/flags.go`. Grouped by use.

**Pattern & prompt**
- `-p, --pattern <name>` — choose a Pattern (flags.go:29).
- `-v, --variable #k:v` — fill Pattern variables, repeatable (flags.go:30).
- `--strategy <name>` — prepend a reasoning strategy, CoT/ToT/etc. (flags.go:88).
- `-C, --context <name>` — prepend a saved context block to every query (flags.go:31).
- `--session <name>` — keep a persistent multi-turn conversation (flags.go:32).
- `--readpattern <name>` — print a Pattern's raw text (flags.go:42).
- `--no-variable-replacement`, `--input-has-vars` — control variable templating (flags.go:76-77).

**Model & generation**
- `-m, --model <name>` (flags.go:49); `-V, --vendor <name>` to disambiguate (flags.go:50).
- `-t, --temperature` (flags.go:35); `-T, --topp` (flags.go:36); `-P, --presencepenalty`; `-F, --frequencypenalty`; `-e, --seed` (flags.go:70).
- `-r, --raw` — send no chat options, use model defaults; OpenAI-compatible only (flags.go:39).
- `--thinking off|low|medium|high` (flags.go:111); `--suppress-think` (flags.go:99); `--search` web-search tool (flags.go:92).

**Input adapters**
- `-y, --youtube`; `--playlist`; `--transcript[-with-timestamps]`; `--comments`; `--metadata`; `--yt-dlp-args` (flags.go:56-65).
- `-u, --scrape_url`; `-q, --scrape_question` (Jina, flags.go:68-69).
- `-a, --attachment` (flags.go:33); `--transcribe-file` (flags.go:103); `--readability` clean HTML (flags.go:75).

**Output**
- `-s, --stream` (flags.go:37); `-o, --output <file>` (flags.go:52); `-c, --copy` (flags.go:48); `--output-session` (flags.go:53); `--image-file` / `--image-size` / `--image-quality` (flags.go:94-96).

**Discovery / lists**
- `-l, --listpatterns` (flags.go:41); `-L, --listmodels` (flags.go:43); `--listvendors` (flags.go:90); `--liststrategies` (flags.go:89); `-x, --listcontexts`; `-X, --listsessions` (flags.go:44-45).

**Setup & maintenance**
- `-S, --setup` (flags.go:34); `-U, --updatepatterns` (flags.go:46); `-d, --changeDefaultModel` (flags.go:55); `--config <file.yaml>` (flags.go:83); `--version` (flags.go:84); `--dry-run` show what would be sent (flags.go:78).

**Server**
- `--serve` REST API (flags.go:79); `--serveOllama` Ollama-compatible endpoints (flags.go:80); `--address :8080` (flags.go:81); `--api-key` (flags.go:82).

**Extensions**
- `--listextensions`, `--addextension <config>`, `--rmextension <name>` (flags.go:85-87).

---

## 5. The Pattern catalog

**Count: 254 patterns** (`ls -1d data/patterns/*/ | wc -l`). Standouts:

| Pattern | What it does |
|---|---|
| `extract_wisdom` | Pull ideas, insights, quotes, habits, facts, references, recommendations from long content. The flagship. |
| `summarize` | Expert content summarizer; markdown summary in a fixed format. |
| `create_summary` | One-paragraph + bulleted main-points summary. |
| `create_5_sentence_summary` | Compress anything to 5 sentences (and 4/3/2/1-word levels). |
| `analyze_claims` | Centrist, objective analysis of truth claims and arguments with ratings. |
| `analyze_paper` / `summarize_paper` | Structured breakdown of an academic paper (findings, rigor, quality). |
| `rate_content` | Label content and assign a quality tier (A/B/C). |
| `label_and_rate` | Tag content with single-word labels, then rate it. |
| `extract_article_wisdom` | extract_wisdom tuned for web articles. |
| `improve_writing` | Fix grammar/style/clarity while preserving voice. |
| `analyze_prose` | Score prose on novelty, clarity, and prose quality. |
| `write_essay` / `write_micro_essay` | Draft an essay (PG style) from a topic. |
| `create_keynote` | Produce a TED-style keynote outline with slides and speaker notes. |
| `extract_main_idea` | Single main idea plus the key recommendation. |
| `find_logical_fallacies` | Identify fallacies and invalid reasoning in an argument. |
| `create_quiz` | Generate review questions from learning material. |
| `clean_text` | Fix broken line breaks/formatting in messy pasted text or transcripts. |
| `extract_recommendations` | Pull just the actionable recommendations. |
| `analyze_threat_report` | Security: extract trends, TTPs, and advice from a threat report. |
| `create_visualization` | Produce an ASCII-art diagram of a concept. |

**Anatomy of a pattern** (`data/patterns/extract_wisdom/system.md`):

```markdown
# IDENTITY and PURPOSE
You extract surprising, insightful, and interesting information from text content...

# STEPS
- Extract a summary of the content in 25 words... into a section called SUMMARY.
- Extract 20 to 50 of the most surprising... ideas... into a section called IDEAS:.
- Extract 10 to 20 of the best insights... into a section called INSIGHTS.
  ... (QUOTES, HABITS, FACTS, REFERENCES, ONE-SENTENCE TAKEAWAY, RECOMMENDATIONS)

# OUTPUT INSTRUCTIONS
- Only output Markdown.
- Write the IDEAS bullets as exactly 16 words.
- Do not give warnings or notes; only output the requested sections.

# INPUT
INPUT:
```

The four sections are the convention: **IDENTITY** (who the model is), **STEPS** (the procedure and named output sections), **OUTPUT INSTRUCTIONS** (formatting rules), **INPUT** (the sentinel where your piped text lands).

---

## 6. Helper binaries

Built from `cmd/` and installable individually with `go install github.com/danielmiessler/fabric/cmd/<name>@latest`.

- **`yt`** — not a separate binary; a shell **alias** that `fabric --setup` writes to your `.zshrc`/`.bashrc` (and a PowerShell function, README.md:482-516). `yt <url>` expands to `fabric -y <url> --transcript`; `yt -t <url>` adds timestamps. Quick transcript grab.
- **`to_pdf`** (`cmd/to_pdf`) — converts LaTeX to PDF via `pdflatex`. Reads stdin or a `.tex` file. Designed to terminate a pipe: `echo "ai security primer" | fabric --pattern write_latex | to_pdf` (README.md:981). Requires a LaTeX distribution on PATH.
- **`code2context`** (`cmd/code2context`) — walks a codebase (flags: `-depth`, `-ignore`, `-out`) and serializes it to JSON for the `create_coding_feature` pattern. Pipe a file list in: `find . -name '*.go' | code2context "instructions"`. (This is the current HEAD's successor to the older `code_helper`.)
- **`generate_changelog`** (`cmd/generate_changelog`) — builds a markdown changelog from git history and GitHub PRs. `generate_changelog --help`. Used by the project's own release automation.

---

## 7. Modes of operation

- **One-shot CLI** — the default: `<input> | fabric -p <pattern>`. Stateless, fastest path.
- **Streaming** — add `-s`/`--stream` for token-by-token output. Use for long generations where you want to read as it writes.
- **REST API server** — `fabric --serve` (binds `:8080`, secure with `--api-key`). Exposes chat completions (streaming), pattern CRUD, context/session management, model/vendor lists, YouTube extraction. See `docs/rest-api.md`. Use to drive Fabric from other apps or the web GUI.
- **Ollama-compatible server** — `fabric --serve --serveOllama` makes Fabric a drop-in Ollama replacement for tools that speak the Ollama API.
- **Web GUI (SvelteKit)** — a browser front-end over the REST API (`web/`, README.md:1053). Use when you want a GUI to browse patterns and chat. Run the server, then the web app.
- **Chat / session + context** — `--session <name>` persists conversation turns across invocations; `--context <name>` injects a saved background block into every query. Use for ongoing, stateful work where prior turns or fixed background matter.
- **Raw mode** — `-r`/`--raw` strips chat options and uses the model's defaults (OpenAI-compatible providers only). Use when a model misbehaves with temperature/top-p, or for reproducibility.

---

## 8. Setup & config

- **`fabric --setup`** (`-S`, flags.go:34) walks you through configuring vendors and API keys, downloads the Patterns to disk, installs Strategies, and writes shell aliases (including `yt`). Run it first (README.md:339).
- **Config location:** `~/.config/fabric/`. API keys and settings live in the env file there; Patterns in `~/.config/fabric/patterns/`, contexts in `contexts/`, strategies in `~/.config/fabric/strategies/` (README.md:399, 851, 915). Add your own pattern by dropping `~/.config/fabric/patterns/<name>/system.md`.
- **Updating patterns:** `fabric -U` / `--updatepatterns` (flags.go:46) re-syncs the bundled patterns onto disk.
- **Vendors supported (19, `internal/plugins/ai/`):** Anthropic, OpenAI, Azure (+ Entra, AI Gateway), Bedrock, Gemini/Vertex AI, Ollama, LM Studio, GitHub Copilot, Codex, Perplexity, Exolab, DigitalOcean, plus a generic `openai_compatible` adapter and `dryrun`. List them live with `fabric --listvendors`; list models with `fabric -L`.

---

## 9. Canonical real-world workflows

```bash
# 1. Summarize a YouTube talk (transcript via yt-dlp), streamed
fabric -y "https://youtube.com/watch?v=uXs-zPc63kM" --stream --pattern extract_wisdom

# 2. Extract wisdom from an article URL (Jina scrape), save to file
fabric -u "https://example.com/long-essay" --pattern extract_article_wisdom -o wisdom.md

# 3. Analyze a PDF paper
fabric -a ./paper.pdf --pattern analyze_paper

# 4. Clean a messy transcript, then copy the result to the clipboard
pbpaste | fabric --pattern clean_text --copy

# 5. Pipe a codebase into an analysis pattern
find . -name '*.go' | code2context "review for security issues" | fabric --pattern analyze_threat_report

# 6. Quick essay to PDF
echo "the future of personal AI" | fabric --pattern write_essay | fabric --pattern write_latex | to_pdf essay
```

---

## Sources consulted

- `README.md` (canonical example L848; examples L829-848; helpers L968-1026; setup/config L339-928; serve/GUI L775-1053).
- `internal/cli/flags.go` — full flag struct (the authoritative flag surface).
- `internal/cli/cli.go` — `processYoutubeVideo` dispatch (L117-177), chat pipeline (L17-115).
- `internal/cli/tools.go` — Jina scrape gating (L61-78).
- `internal/tools/youtube/youtube.go` — yt-dlp dependency and transcript/comments/metadata grabbers.
- `internal/tools/jina/jina.go` — `r.jina.ai` scrape, `s.jina.ai` search.
- `internal/core/chatter.go` — streaming path (L102-153), session build.
- `data/patterns/extract_wisdom/system.md` and siblings — pattern anatomy and catalog.
- `cmd/{to_pdf,code2context,generate_changelog}/` — helper binaries.

## Open questions

- Exact YouTube-comments/metadata API-key requirement vs transcript (transcript is keyless via yt-dlp; comments/metadata hit the Data API) was inferred from code paths, not a setup walkthrough.
- The SvelteKit web GUI was confirmed to exist (`web/`) but its feature set was not exercised live.

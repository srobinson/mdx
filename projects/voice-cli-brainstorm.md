---
title: "Voice: CLI/DX Design Brainstorm"
category: projects
tags: [voice, cli, dx, brainstorm]
created: 2026-03-17
agent: voltagent-dev-exp:cli-developer
---

# Voice: CLI & Developer Experience Design

## 1. CLI Interface Design

### Command Hierarchy

```
voice
  lint          Detect slop in text (read-only analysis)
  apply         Transform text using a voice profile
  profile       Manage voice profiles
    create      Generate a profile from writing samples
    list        List available profiles
    show        Display profile details and rules
    edit        Open profile in $EDITOR
    import      Import a profile from file or URL
    export      Export a profile to shareable format
    delete      Remove a profile
  train         Refine a profile with additional samples or corrections
  diff          Show before/after comparison without writing output
  init          Initialize Voice config in current directory
  completions   Generate shell completions (bash/zsh/fish/pwsh)
```

### Design Principles

**Progressive disclosure.** The two commands a new user needs are `voice lint` and `voice apply`. Everything else reveals itself through `--help` and natural exploration. A first run with no config should still work using the built-in slop detector.

**Positional arguments for the common case.** Files are positional. Profiles are flags.

```bash
voice lint README.md
voice apply draft.md --profile stuart
voice apply draft.md -p stuart -o clean.md
```

**Stdin/stdout by default when no file argument.** This is critical for pipeline composability.

```bash
echo "This is a really great solution" | voice lint
cat draft.md | voice apply -p stuart > final.md
```

**Sensible exit codes.**

| Code | Meaning |
|------|---------|
| 0    | Clean / success |
| 1    | Slop detected (lint) or transformation applied (apply) |
| 2    | Configuration error |
| 3    | Profile not found |
| 127  | Unknown command |

Exit code 1 on lint detection (like `grep` returning 1 for no match, or `eslint` returning 1 for findings) enables CI gating.

### Flag Conventions

```
-p, --profile <name>    Voice profile to use
-o, --output <path>     Write to file instead of stdout
-f, --format <fmt>      Output format: text (default), json, diff, annotated
-q, --quiet             Suppress non-essential output
-v, --verbose           Show detailed processing info
    --fix               In-place modification (lint mode)
    --severity <level>  Filter: error, warning, info
    --config <path>     Override config file location
    --no-config         Ignore all config files
    --color <when>      auto, always, never
```

## 2. Pipeline Integration

### Unix Philosophy: Filters Compose

Voice should behave as a well-mannered Unix filter. Text in, text out. Everything else goes to stderr.

```bash
# Chain with other tools
pandoc report.docx -t markdown | voice apply -p technical | pandoc -o report-clean.docx

# Git pre-commit hook
voice lint --severity error $(git diff --cached --name-only --diff-filter=d '*.md')

# CI/CD check
voice lint --format json docs/ | jq '.findings | length'

# Editor pipe (vim: :%!voice apply -p stuart)
```

### Git Hook Integration

```bash
voice init --hook pre-commit    # Install git hook
voice init --hook commit-msg    # Lint commit messages too
```

The pre-commit hook should be fast. Lint only staged files. Lint only changed lines if possible (use git diff ranges). Fail with clear output showing what triggered and where.

### Editor Integration Points

Voice should expose a Language Server Protocol (LSP) mode for editor integration:

```bash
voice lsp    # Start LSP server
```

This gives VS Code, Neovim, Zed, and every other LSP-capable editor diagnostics, code actions ("Remove slop"), and formatting support without building separate plugins for each.

### MCP Server Mode

```bash
voice serve    # Start as MCP server
```

Exposes `voice_lint`, `voice_apply`, `voice_profiles` as MCP tools. This lets Claude Code and other AI tools consume Voice directly.

## 3. Configuration

### File Hierarchy (Cascading)

```
~/.config/voice/config.toml          Global defaults
~/.config/voice/profiles/             Global profiles directory
./.voice/config.toml                  Project-level overrides
./.voice/profiles/                    Project-level profiles
```

TOML for config. It reads cleanly, supports comments, and avoids the YAML foot-guns.

### Config Shape

```toml
# .voice/config.toml
default_profile = "stuart"
severity = "warning"

[lint]
ignore = ["docs/vendor/**"]
rules.em_dash = "error"
rules.hedging = "warning"
rules.hollow_superlatives = "error"

[apply]
confirm = false          # true = interactive approval
backup = true            # create .bak before in-place edits

[profiles]
search_paths = ["~/.config/voice/profiles", "./.voice/profiles"]
```

### Team Sharing

Profiles are plain files (TOML or a dedicated `.voice-profile` format). They live in version control.

```
repo/
  .voice/
    config.toml
    profiles/
      team-docs.toml
      marketing.toml
```

Teams commit profiles alongside code. CI enforces them. No SaaS dependency.

## 4. Library / Runtime API

### Rust Core

Rust is the correct choice. Single binary distribution. No runtime dependencies. Fast enough for real-time editor integration.

Crate structure:

```
voice-core        Detection engine, transformation pipeline, profile parsing
voice-cli         Binary crate, argument parsing, I/O
voice-lsp         LSP server implementation
voice-mcp         MCP server implementation
```

### Public API Surface (voice-core)

```rust
use voice_core::{Profile, Linter, Transformer, Finding, Severity};

// Lint
let linter = Linter::new(&profile);
let findings: Vec<Finding> = linter.lint(text);

// Transform
let transformer = Transformer::new(&profile);
let result: TransformResult = transformer.apply(text);
println!("{}", result.text);
println!("{:?}", result.changes);  // What was changed and why

// Profile
let profile = Profile::load("stuart")?;
let profile = Profile::from_samples(&["sample1.md", "sample2.md"])?;
```

### Bindings Strategy

The Rust core compiles to a C ABI shared library. From there:

- **Node.js**: napi-rs bindings. Publish as `@voice/core` on npm.
- **Python**: PyO3 bindings. Publish as `voice-core` on PyPI.
- **Wasm**: For browser-based tooling and playgrounds.

Do not build bindings at v0. Ship the CLI and Rust crate first. Bindings come when there is demand, not before.

## 5. Profile Management

### Profile Creation

```bash
# From writing samples
voice profile create stuart --from ~/writing/blog-posts/
voice profile create stuart --from ~/writing/ --glob "*.md"

# Interactive refinement
voice train stuart --interactive
# Shows pairs: "AI version" vs "your version"
# Learns preferences from corrections

# From an existing profile as base
voice profile create stuart-formal --base stuart --from ~/writing/formal/
```

### Profile Format

```toml
# ~/.config/voice/profiles/stuart.toml
[meta]
name = "stuart"
description = "Stuart's direct, technical voice"
version = "1.2.0"
created = "2026-03-17"

[style]
# Quantified preferences (0.0 = never, 1.0 = always)
sentence_length_target = 12       # words
paragraph_length_target = 3       # sentences
contraction_preference = 0.8      # use contractions often
active_voice_preference = 0.9

[vocabulary]
preferred = ["ship", "build", "straightforward"]
avoided = ["utilize", "leverage", "synergy", "robust"]

[patterns]
# Regex-based detection with replacements
[[patterns.rules]]
name = "em_dash_elimination"
detect = '—'
severity = "error"
suggestion = "Use periods, commas, or semicolons"

[[patterns.rules]]
name = "hollow_superlative"
detect = '\b(really|very|extremely|incredibly)\s+(great|good|important|powerful)\b'
severity = "warning"
suggestion = "Be specific. What makes it good?"

[[patterns.rules]]
name = "hedging"
detect = '\b(I think|it seems like|sort of|kind of|arguably)\b'
severity = "info"
suggestion = "State it directly or remove"
```

### Sharing and Distribution

```bash
voice profile export stuart > stuart.voice-profile
voice profile import ./stuart.voice-profile
voice profile import https://example.com/profiles/technical.voice-profile
```

No package registry at launch. Profiles are files. Share them via git, gists, URLs. A registry is a v2+ consideration, and only if organic sharing patterns show friction.

## 6. Output Modes

### Default: Clean Text to Stdout

```bash
voice apply draft.md -p stuart
# Outputs transformed text to stdout
```

### Diff View

```bash
voice diff draft.md -p stuart
# or
voice apply draft.md -p stuart -f diff
```

```diff
- This is an incredibly powerful and robust solution that leverages
- cutting-edge technology to deliver transformative results.
+ This solution uses current technology effectively.
```

### Report Mode (Lint)

```bash
voice lint draft.md -f json
```

```json
{
  "file": "draft.md",
  "findings": [
    {
      "line": 3,
      "column": 15,
      "rule": "em_dash_elimination",
      "severity": "error",
      "message": "Em dash detected. Use periods, commas, or semicolons.",
      "context": "the project — which started",
      "suggestion": "the project, which started"
    }
  ],
  "summary": {
    "errors": 2,
    "warnings": 5,
    "info": 3
  }
}
```

### Interactive Mode

```bash
voice apply draft.md -p stuart --confirm
```

Walks through each proposed change. Shows context. Accepts `y/n/e(dit)/a(ll)/q(uit)`. Similar UX to `git add -p`.

### Annotated Mode

```bash
voice apply draft.md -p stuart -f annotated
```

Outputs the text with inline annotations explaining each change. Useful for learning why something was flagged.

## 7. Language and Build

### Rust Core: Non-Negotiable

- **Startup time**: Rust CLI starts in single-digit milliseconds. A tool that runs in git hooks and editor save actions cannot afford interpreter startup.
- **Single binary**: `curl -sSf https://voice.dev/install.sh | sh` drops one file. No node_modules, no virtualenv, no runtime.
- **Cross-platform**: One codebase compiles to Linux, macOS (ARM + Intel), Windows. Cross-compilation via `cross` is mature.
- **Memory**: A linting pass over a 100KB document should use < 10MB RSS.

### Recommended Crate Dependencies

| Crate | Purpose |
|-------|---------|
| `clap` (derive) | Argument parsing with shell completions |
| `tokio` | Async runtime (LSP, MCP server modes) |
| `tower-lsp` | LSP implementation |
| `serde` + `toml` | Config and profile parsing |
| `similar` | Diff generation |
| `regex` | Pattern matching engine |
| `indicatif` | Progress bars and spinners |
| `dialoguer` | Interactive prompts |
| `owo-colors` | Terminal colors (respects NO_COLOR) |
| `miette` | Rich error diagnostics |

### Distribution

Phase 1: GitHub releases with prebuilt binaries (via `cargo-dist` or `release-plz`). Homebrew tap. Install script.

Phase 2: Homebrew core. AUR. Cargo install. Scoop.

Phase 3: npm/PyPI wrappers that download the correct binary (like `@biomejs/biome`).

## 8. Performance Budget

| Operation | Target |
|-----------|--------|
| `voice lint` cold start | < 5ms |
| Lint 10KB document | < 20ms |
| Lint 100KB document | < 100ms |
| `voice apply` 10KB document | < 50ms |
| Profile load | < 2ms |
| LSP initialization | < 50ms |
| Memory (lint 100KB) | < 10MB |

These targets make Voice viable for real-time editor integration and git hooks without any perceivable delay.

## 9. Extension Points

### Custom Rules

Users define rules in profiles. The regex engine handles most detection patterns. For complex rules that need AST-level text analysis (sentence boundaries, paragraph structure, readability scores), the core engine provides built-in analyzers that profiles can reference:

```toml
[[patterns.rules]]
name = "long_sentences"
analyzer = "sentence_length"
threshold = 25
severity = "warning"
```

### Plugin System (v2+)

Wasm-based plugins for custom analyzers. A plugin compiles to `.wasm`, gets loaded at runtime, and implements a trait:

```rust
trait VoicePlugin {
    fn analyze(&self, text: &str) -> Vec<Finding>;
    fn transform(&self, text: &str, findings: &[Finding]) -> String;
}
```

Wasm provides sandboxing. No arbitrary code execution from community plugins.

## 10. Things to Get Right from Day One

1. **Respect `NO_COLOR` and `TERM`**. Never force colors.
2. **Structured output (`--format json`) on every command.** Machines need to consume this.
3. **Offline by default.** Voice should never phone home. Profile training that requires an LLM should be explicit and opt-in.
4. **Fast failure.** Bad config? Say exactly what line is wrong and what the valid values are. Use `miette` for rich diagnostics.
5. **Shell completions generated from clap derive.** Ship them. Install them via `voice completions bash > ~/.local/share/bash-completion/completions/voice`.
6. **Man pages.** Generate from clap via `clap_mangle`. Searchable, offline documentation.
7. **Idempotency.** Running `voice apply` twice on the same text produces the same output. No drift.

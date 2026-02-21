---
title: "nancy-brain Context Sources — Adding mdcontext and git log"
type: design
tags: [nancyr, nancy-brain, prompt-compiler, mdcontext, git, context-injection]
summary: "PromptCompiler has 3 context slots (AM, FMM, journal) but is missing mdcontext knowledge base and git history — two high-value sources"
status: active
created: 2026-02-21
updated: 2026-02-21
project: nancyr
confidence: high
related: [session-lifecycle, nancyr-objectives]
---

# nancy-brain Context Sources

## Current State

`PromptCompiler` in `nancy-brain/src/prompt.rs` assembles context for `claude -p` prompts. It has three slots:

```rust
pub struct PromptCompiler {
    memory_context: Option<String>,     // AM geometric memory
    codebase_map: Option<String>,       // FMM sidecar scan
    session_context: Option<String>,    // Journal continuity
}
```

Compilation order: working_dir → codebase_map → memory → sessions → token_budget → task.

## The Gap

Two high-value context sources are missing:

### 1. mdcontext (~/.mdx knowledge base)

42 documents covering architecture decisions, design docs, research, objectives, references. When nancyr spawns a worker, that worker has zero access to:

- Architecture decisions (`~/.mdx/decisions/`)
- Design docs (`~/.mdx/design/helioy-architecture.md`, `session-lifecycle.md`)
- Project objectives (`~/.mdx/projects/nancyr-objectives.md`)
- Reference material (`~/.mdx/reference/plugin-expectations.md`)

This means a nancyr-spawned agent doesn't know about the session lifecycle design, the token thesis, config isolation strategy, or any other authored knowledge. It only knows what AM recalls from conversations — not the curated, structured truth.

### 2. Git log (recent commit history)

```bash
git log -n 10 --pretty=format:"Commit: %h%nDate: %ad%nMessage: %B%n--End--" --date=short
```

This tells the agent:

- What was worked on recently (last 10 commits)
- Who did what (Co-Authored-By reveals agent vs human)
- Current branch and trajectory
- Pace of changes

~500 tokens for 10 commits. Extremely high information density per token.

## Proposed Design

Add two new context slots to PromptCompiler:

```rust
pub struct PromptCompiler {
    memory_context: Option<String>,      // AM geometric memory
    codebase_map: Option<String>,        // FMM sidecar scan
    session_context: Option<String>,     // Journal continuity
    knowledge_context: Option<String>,   // mdcontext knowledge base  [NEW]
    git_context: Option<String>,         // Recent git history         [NEW]
}
```

### Compilation order (updated)

```
1. Working directory
2. Git history (recent commits — what just happened)
3. Codebase map (FMM — what's in the code)
4. Knowledge context (mdcontext — what's been decided/designed)
5. Memory context (AM — what's been discussed)
6. Session context (journal — what happened in prior runs)
7. Token budget
8. Task prompt
```

Rationale for order: concrete → abstract → task. Git and FMM are facts about the codebase. Knowledge and memory are interpreted context. Task comes last so it's closest to where the model starts generating.

### Builder methods

```rust
pub fn with_knowledge_context(mut self, ctx: impl Into<String>) -> Self {
    self.knowledge_context = Some(ctx.into());
    self
}

pub fn with_git_context(mut self, ctx: impl Into<String>) -> Self {
    self.git_context = Some(ctx.into());
    self
}
```

## Implementation: Git Context

Simple — shell out from `main.rs`:

```rust
fn git_context(working_dir: &Path) -> Option<String> {
    let output = Command::new("git")
        .args(["log", "-n", "10",
               "--pretty=format:Commit: %h\nDate: %ad\nMessage: %B\n--End--",
               "--date=short"])
        .current_dir(working_dir)
        .output()
        .ok()?;

    if output.status.success() {
        let log = String::from_utf8_lossy(&output.stdout);
        Some(format!("Recent git history:\n{log}"))
    } else {
        None // Not a git repo, or git not available
    }
}
```

New file: `nancy-brain/src/git.rs` or inline in `nancy-cli/src/main.rs`.

CLI flag: `--no-git` to disable (matching `--no-fmm`, `--no-journal`, `--no-memory`).

## Implementation: mdcontext Knowledge Context

Shell out to mdcontext CLI — consistent with nancyr's CLI-wrapping pattern:

```rust
fn knowledge_context(task_prompt: &str, working_dir: &Path) -> Option<String> {
    // Search ~/.mdx for task-relevant documents
    let output = Command::new("npx")
        .args(["-y", "mdcontext", "search", task_prompt, "--path", "~/.mdx",
               "--limit", "5", "--format", "context"])
        .output()
        .ok()?;

    if output.status.success() {
        let context = String::from_utf8_lossy(&output.stdout);
        if context.trim().is_empty() {
            None
        } else {
            Some(format!("Knowledge base context:\n{context}"))
        }
    } else {
        None
    }
}
```

Alternatively, use `mdcontext context <file> --level summary` for specific docs if we know which ones are relevant.

CLI flag: `--no-knowledge` to disable.

### Query strategy

The task prompt itself is the search query — `mdcontext search "{task_prompt}" ~/.mdx --limit 5` returns the most relevant knowledge base sections. This means:

- "Fix the auth middleware" → might surface `nancyr-architecture.md` sections about hooks
- "Add a new skill" → surfaces `plugin-expectations.md` and `claude-plugin-architecture.md`
- "Update Linear issues" → surfaces `mdcontext-linear-status.md`

The search is semantic (embeddings) so it finds relevant content even without exact keyword matches.

### Token budget consideration

With 5 context sources, token budget matters:

| Source    | Typical size   | Priority                           |
| --------- | -------------- | ---------------------------------- |
| Git log   | ~500 tokens    | High (always include)              |
| FMM map   | ~2-10k tokens  | High (code tasks)                  |
| mdcontext | ~1-5k tokens   | Medium (task-dependent)            |
| AM memory | ~1-3k tokens   | Medium (if relevant recall exists) |
| Journal   | ~500-1k tokens | Low (last 5 sessions summary)      |

When budget is tight, priority order: task > git > fmm > knowledge > memory > journal.

## Open Questions

1. Should mdcontext query use the task prompt verbatim, or should we extract key terms first?
2. Should we cache mdcontext results for the session (query once, reuse)?
3. Should git context include `git diff --stat` for uncommitted changes in addition to log?
4. Should we add `git branch -vv` for branch tracking info?

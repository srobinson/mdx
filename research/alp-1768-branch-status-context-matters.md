---
title: ALP 1768 branch status for context matters
type: research
tags: [context-matters, git, branch-status, alp-1768]
summary: Branch nancy/ALP-1768 is clean and synced with its remote, with content already landed on main as squash commit 0c09fb6.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-26
updated: 2026-04-26
---

## Executive Summary

The worktree `/Users/alphab/Dev/LLM/DEV/helioy/context-matters-worktrees/nancy-ALP-1768` is on `nancy/ALP-1768`, clean, and exactly synced with `origin/nancy/ALP-1768`. Local history shows the branch content already exists on `origin/main` as squash commit `0c09fb6`, `feat(cli): world-class CLI parity with MCP via cm-capabilities (#41)`, with an identical tree to branch head `14d1cd4`.

## Project Metadata

- Project: `context-matters`
- Worktree: `/Users/alphab/Dev/LLM/DEV/helioy/context-matters-worktrees/nancy-ALP-1768`
- Repository root: same as worktree path
- Language and build: Rust workspace, per repo instructions using `just check`, `just build`, `just test`, `just fmt`
- fmm availability: available and indexed. `fmm_list_files(group_by: "subdir")` returned 217 files and 35,766 LOC, mostly under `crates/`.

## Branch Snapshot

- Current branch: `nancy/ALP-1768`
- Upstream: `origin/nancy/ALP-1768`
- Ahead or behind upstream: `0 0`
- HEAD: `14d1cd4163d24e5621db1b44edc7197044d8ac00`
- HEAD subject: `nancy[ALP-1768]: chore(cli): preserve smart browse parity before landing`
- HEAD date: `2026-04-21 00:15:46 +0700`
- Remote: `origin git@github.com:srobinson/context-matters.git`
- Base comparison target: `origin/main`
- Merge base with `origin/main`: `5d0d202c3809914922d0ba2345fc04caf4b84bc2`
- Divergence from `origin/main`: 12 commits on main side, 17 commits on branch side
- Important local finding: `git diff --quiet 0c09fb6..HEAD` returned exit code 0. `0c09fb6` and `14d1cd4` share tree `f8373fdd25e5729ba78bd9394e053aa156097267`.

## Working Tree State

`git status --short --branch --untracked-files=all` returned only:

```text
## nancy/ALP-1768...origin/nancy/ALP-1768
```

No staged files, unstaged files, or untracked files were present:

- `git diff --cached --name-status`: empty
- `git diff --name-status`: empty
- `git ls-files --others --exclude-standard`: empty

## Change Summary

Against the original merge base with `origin/main`, the branch contains 17 commits from `ALP-1769` through `ALP-1784`, ending with `ALP-1768`:

- terminal dependencies and CLI color handling
- CLI error printing and hints
- full subcommand surface for read, write, and admin groups
- hidden markdown help and man page generation flags
- scope helper for scope resolution advisories
- recall, browse, get, stats, forget, update, deposit, export handlers wired through `cm-capabilities`
- store stub pointing to `cm serve --web`
- CLI flag and integration test coverage
- final smart browse CLI parity preservation before landing

Triple dot diff against `origin/main` from the merge base showed 36 changed files, 3,059 insertions, and 420 deletions. Key files included:

- `crates/cm-cli/src/main.rs`: `main` lines 12 to 17, `run` lines 20 to 186
- `crates/cm-cli/src/cli/cli_def.rs`: `Cli` lines 32 to 54, `Commands` lines 59 to 225
- `crates/cm-cli/src/cli/mod.rs`: CLI module exports lines 3 to 20
- `crates/cm-capabilities/src/deposit.rs`: `DepositRequest`, `DepositResult`, and `deposit` lines 112 to 217
- `crates/cm-capabilities/src/export.rs`: `ExportRequest`, `ExportView`, and `export` lines 77 to 112
- `crates/cm-capabilities/src/forget.rs`: `ForgetRequest`, `ForgetResult`, and `forget` lines 72 to 122
- `crates/cm-cli/tests/cli_flags.rs`
- `crates/cm-cli/tests/cli_integration.rs`

The same 36 file, 3,059 insertion, 420 deletion stat appears in `origin/main` commit `0c09fb6`, `feat(cli): world-class CLI parity with MCP via cm-capabilities (#41)`. This indicates the branch was squash merged or otherwise landed as that commit.

## Risk Notes

- The branch is stale relative to current `origin/main`. Main has 12 commits after the branch content, including release, adapter cleanup, MCP hardening, type splitting, npm fixes, and local git SHA versioning.
- Continuing work on this worktree risks building on an obsolete tree. Endpoint diff `origin/main..HEAD` spans 181 files because the branch lacks later main changes.
- The branch remote still exists and is synced. Cleanup should wait until Stuart confirms no tests or branch retention workflows depend on it.
- I did not run `just check`, `just test`, or `fmm validate` because the task was read only and those commands can write build or cache artifacts. The HEAD commit message itself claims prior verification with those commands.

## Suggested Next Move

Treat `nancy/ALP-1768` as landed and superseded by `origin/main` commit `0c09fb6`. For current development, use `main` or create a new branch from current `origin/main`. If branch retention is no longer needed, clean up the remote branch and worktree only after confirmation.

## Exact Commands and Tools Used

Structural context:

```text
fmm_list_files(group_by: "subdir", limit: 200, filter: "all")
fmm_file_outline(file: "crates/cm-cli/src/main.rs", include_private: true)
fmm_file_outline(file: "crates/cm-cli/src/cli/cli_def.rs", include_private: true)
fmm_file_outline(file: "crates/cm-cli/src/cli/mod.rs", include_private: true)
fmm_file_outline(file: "crates/cm-capabilities/src/deposit.rs", include_private: true)
fmm_file_outline(file: "crates/cm-capabilities/src/export.rs", include_private: true)
fmm_file_outline(file: "crates/cm-capabilities/src/forget.rs", include_private: true)
```

Git inspection:

```sh
pwd
git rev-parse --show-toplevel
git branch --show-current
git status --short --branch --untracked-files=all
git branch -vv --no-abbrev
git remote -v
git worktree list --porcelain
git rev-parse --abbrev-ref --symbolic-full-name @{u}
git rev-list --left-right --count HEAD...@{u}
git show-ref --verify --quiet refs/remotes/origin/main && git rev-parse --short refs/remotes/origin/main
git show-ref --verify --quiet refs/heads/main && git rev-parse --short refs/heads/main
git show -s --format='%H%n%h %D%n%ci%n%s' HEAD
git diff --cached --name-status
git diff --name-status
git ls-files --others --exclude-standard
git merge-base HEAD origin/main
git rev-list --left-right --count origin/main...HEAD
git log --oneline --decorate --graph --left-right --cherry-pick origin/main...HEAD
git log --oneline --decorate --graph $(git merge-base HEAD origin/main)..HEAD
git diff --name-status origin/main...HEAD
git diff --stat origin/main...HEAD
git diff --shortstat origin/main...HEAD
git diff --name-status origin/main..HEAD
git diff --stat origin/main..HEAD
git diff --shortstat origin/main..HEAD
git show --stat --oneline HEAD
git show --name-status --format=medium HEAD
git log --oneline origin/main --grep='ALP-1768\|ALP-1769\|ALP-177\|ALP-178\|CLI parity\|cm-capabilities' --regexp-ignore-case
git show --stat --oneline 0c09fb6 --max-count=1
git diff --quiet 0c09fb6..HEAD; echo $?
git diff --shortstat 0c09fb6..HEAD
git show -s --format='%h %T %s' 0c09fb6 HEAD
```

## Open Questions

- Whether the remote branch and local worktree should be deleted now, or retained for Stuart's multi agent tests.
- Whether any external issue tracker state for `ALP-1768` still needs manual closure. No external issue details were inferred.

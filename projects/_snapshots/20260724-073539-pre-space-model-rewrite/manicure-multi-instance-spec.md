---
title: Manicure multi-instance support — build spec
date: 2026-04-15
status: approved
scope: api/src/manicure (CLI + storage + addon), no frontend changes
branch-base: feat/own-claude-process
---

# Multi-instance manicure support

## Problem

`manicure start` today assumes a single live instance per machine: fixed default ports (8787/8788), a single shared storage root (`~/.manicure/`), and no coordination between concurrent runs. Users who open two terminals in different projects today get a port collision on the second `manicure start`. And any scheme that lets two instances coexist must also avoid data corruption in the shared storage layer.

## Scope — decided, do not revisit

1. **Constraint: at most one instance per CWD.** Two terminals in the *same* directory must collide fast. Different CWDs must coexist cleanly.
2. **Workspace identity** derives from `realpath(cwd)` plus a short stable hash.
3. **Storage layout**: per-workspace, at `~/.manicure/workspaces/{cwd-slug}/{hash}/`. CWD slug is human-readable (see below). Hash disambiguates collisions.
4. **Dynamic port allocation**: no default 8787/8788 anymore. Discover free ports at startup, pass through existing env plumbing, surface in banner.
5. **Pass discovered URLs to Claude via `--system-prompt`** so the agent inside Claude Code knows its own proxy/UI URLs.
6. **`doctor` and `paths` do NOT take the lock** — they're read-only and must work even with a live instance in the same CWD.
7. **Lock mechanism**: `fcntl.flock` (POSIX advisory lock), not a PID file. Auto-releases on process death. No staleness handling needed.
8. **Manifest file** is separate from the lock. Contains `{cwd, pid, proxy_port, web_port, storage_dir, started_at}`. Advisory only; truth is the lock.
9. **No users today** → breaking changes to storage layout are acceptable. No migration needed.
10. **`manicure list`** is in scope for Phase 1 as a freebie (reads manifests, prints live instances).

## Ground-truth references

Claims verified against the working tree on branch `feat/own-claude-process` at commit `6ff778b`.

| Concern | File | Line | Note |
|---|---|---|---|
| Port defaults | `api/src/manicure/config.py` | 28-29 | `proxy_port: int = 8787`, `web_port: int = 8788` |
| Storage default | `api/src/manicure/config.py` | 30 | `storage_dir: Path = Path.home() / ".manicure"` |
| `get_settings` is cached | `api/src/manicure/config.py` | 42-44 | `@lru_cache` — any call before env mutation locks in defaults |
| CLI port defaults | `api/src/manicure/cli/__init__.py` | ~129 | `proxy_port: Annotated[int, typer.Option(...)] = 8787` |
| Env plumbing for ports | `api/src/manicure/cli/__init__.py` | step 6 (`child_env`) | Already writes `MANICURE_{PROXY,WEB}_PORT` into child env |
| `ANTHROPIC_BASE_URL` wired | `api/src/manicure/cli/__init__.py` | step 10 (`_run_children` call) | Already uses `f"http://localhost:{proxy_port}"` |
| Banner | `api/src/manicure/cli/banner.py` | `_print_banner` | Already prints proxy + web URLs |
| Addon web-bind | `api/src/manicure/addon.py` | 408 | `port=settings.web_port` — reads from `get_settings()` |
| Storage singleton | `api/src/manicure/storage/__init__.py` | 17, 40 | Process-local; lazy-init from `settings.storage_dir` |
| `append_index` | `api/src/manicure/storage/disk.py` | 152-156 | `aiofiles.open(path, mode="a")` — atomic appends under PIPE_BUF |
| `rewrite_index` | `api/src/manicure/storage/disk.py` | 139-150 | **Atomic rewrite from in-memory cache. Two processes = last-writer-wins drops entries. Real motivation for storage isolation.** |
| Module globals | `api/src/manicure/breakpoint.py` | 45-51 | Process-local; no cross-process collision |

## Conventions (from `api/CLAUDE.md`)

- Builtins-only types: `list[str]`, `dict[str, Any]`, `X | None`.
- Annotate all return types.
- No cycles in the import DAG: `ir → adapters → rules → pipeline → storage → breakpoint → server`.
- Unit tests colocated: `src/manicure/foo/test_bar.py` next to `bar.py`.
- **Hard cap: 700 lines per file.** Over 700 → refactor first.
- Errors: domain exceptions in `exceptions.py`, chain with `raise X from original`.
- Async boundary: I/O async, pure computation sync.

## Workspace identity spec

```python
# New module: api/src/manicure/workspace.py

def workspace_id(cwd: Path) -> WorkspaceId:
    """Stable identity for a working directory.

    Returns (slug, hash). Path layout: ~/.manicure/workspaces/{slug}/{hash}/.
    """
    canonical = cwd.resolve(strict=False)  # follow symlinks
    slug = _slugify(canonical)              # human-readable; see below
    hash_ = _hash(canonical)                # 8-char blake2b, hex
    return WorkspaceId(slug=slug, hash=hash_, root=canonical)
```

- **Canonicalization**: `Path.resolve(strict=False)` (follows symlinks, doesn't require existence).
- **Slug**: last **3** path segments, lowercased, non-`[a-z0-9-_]` → `-`, collapse runs of `-`, trim. Example: `/Users/alphab/Dev/LLM/DEV/helioy/manicure/api` → `helioy-manicure-api`. Empty slug (e.g. `/`) → `root`. Cap at 40 chars. (Rationale: 2 segments hides the parent project name in monorepos — `manicure-api` vs `helioy-manicure-api`.)
- **Hash**: `blake2b(canonical.as_posix().encode(), digest_size=4).hex()` → 8 hex chars. Stable across runs on the same machine.
- **Path**: `~/.manicure/workspaces/{slug}/{hash}/`. Slug collisions resolved by hash directory. `paths.resolve()` etc. must never mix two workspaces.

## Phase 1 — Workspace identity + lock + manifest + list

### Deliverables

1. `api/src/manicure/workspace.py` — `workspace_id()`, `WorkspaceId` dataclass, `workspace_root(cwd) -> Path` helper. Pure functions, no I/O side effects beyond `Path.resolve`.
2. `api/src/manicure/lock.py` — `WorkspaceLock` context manager using `fcntl.flock(LOCK_EX | LOCK_NB)`. Raises `WorkspaceLocked` (new domain exception in `exceptions.py`, or a local exception if `exceptions.py` doesn't exist — verify) on contention. Exposes `.manifest_path` property for writing the sidecar.
3. `api/src/manicure/manifest.py` — `Manifest` dataclass (`cwd: str, pid: int, proxy_port: int, web_port: int, storage_dir: str, started_at: str, manicure_version: str, slug: str, hash: str`), `write(path, manifest)`, `read(path) -> Manifest | None`, `read_all(root) -> list[Manifest]`. JSON on disk. `read_all` scans `~/.manicure/workspaces/*/*/manifest.json`. (`slug` and `hash` stored so `list` can display them without re-deriving from the path.)
4. CLI integration in `cli/__init__.py`:
   - `start` acquires the lock before any child spawn. On `WorkspaceLocked`, print an error pointing at the live manifest's PID + ports and exit 2.
   - **Lock placement**: wrap the `_run_children` call in `start()` with `with WorkspaceLock(root):`. This keeps `runner.py` focused on child lifecycle; `_run_children` does not see workspace identity.
   - Manifest written immediately after lock acquisition, deleted on exit (best-effort; `read` must tolerate stale manifest by checking the lock).
5. New `manicure list` subcommand:
   - Reads all manifests.
   - For each, tries `fcntl.flock(LOCK_EX | LOCK_NB)` on the lock file; if it fails, the instance is live; if it succeeds, the manifest is stale (release immediately).
   - Prints a table: `WORKSPACE  PID  PROXY  WEB  STORAGE  STARTED`.
   - `--json` flag for machine output.
   - Help epilog follows the same plain-text convention as `paths`/`doctor`.
6. `doctor` and `paths`: no changes — they do not touch the lock.
7. Tests colocated:
   - `test_workspace.py` — slug/hash stability, canonical-path behavior, edge cases (`/`, non-existent paths).
   - `test_lock.py` — acquire, second acquire fails, release on context exit, release on process death (use subprocess).
   - `test_manifest.py` — round-trip, missing file, malformed file.
   - Extend `test_cli.py` — second `start` in same CWD fails fast with the expected error and exit code.

### Acceptance criteria

- [ ] `manicure start` in CWD A holds the lock; a concurrent `manicure start` in CWD A prints an error mentioning the live PID + ports and exits 2.
- [ ] `manicure start` in CWD A and `manicure start` in CWD B coexist without conflict.
- [ ] `manicure doctor` and `manicure paths` work with a live instance in the same CWD.
- [ ] `manicure list` shows live instances; stale manifests are reaped transparently.
- [ ] All existing tests still pass.
- [ ] New tests green.
- [ ] Every new file under 700 lines.

### Out of scope for Phase 1

- Dynamic port allocation (still use fixed 8787/8788). Phase 2.
- Per-workspace storage root (still use `~/.manicure/`). Phase 3.
- `--system-prompt` passthrough to Claude. Phase 2.

## Phase 2 — Dynamic port allocation + system-prompt passthrough

### Deliverables

1. `api/src/manicure/cli/ports.py` (or extend `cli/net.py`) — `allocate_port_pair() -> tuple[int, int]`. Uses `socket.bind(("127.0.0.1", 0))` twice, reads the assigned ports, closes, returns. Retry with a small loop if the TOCTOU race bites on spawn.
2. CLI:
   - Drop the `proxy_port=8787` / `web_port=8788` defaults in `start`. If the user passes `--proxy-port` / `--web-port` explicitly, honor that; otherwise allocate.
   - Update help text in `cli/help.py` to document the new behavior.
   - Banner already prints discovered ports; verify it surfaces them clearly.
3. `--system-prompt` passthrough:
   - After port resolution, build a system-prompt string like:
     ```
     You are running inside manicure. Proxy URL: http://localhost:{proxy}. Inspector UI: http://localhost:{web}.
     ```
   - Prepend `--append-system-prompt {msg}` to the existing `claude_passthrough` args before spawn (preserves user-supplied `--` args).
   - If the user already passed `--system-prompt` or `--append-system-prompt` in pass-through, leave theirs alone and don't inject (detect by prefix match).
   - Flag to disable injection: `--no-system-prompt` on `manicure start`. Documented in help.
4. Tests:
   - `test_ports.py` — `allocate_port_pair` returns two different free ports; retries on collision; raises after N attempts.
   - `test_cli.py` — `start --print-command` with dynamic ports shows allocated numbers; user-supplied `--proxy-port` overrides; system-prompt is injected unless `--no-system-prompt`; user's own `--system-prompt` wins.

### Acceptance criteria

- [ ] Bare `manicure start` in two different CWDs both come up with non-colliding ports.
- [ ] `manicure start --proxy-port 9000` still works.
- [ ] `manicure start --print-command` shows the allocated ports and the injected system prompt.
- [ ] Tests green.

### Risks

- **TOCTOU race**: free port at bind time may be taken before mitmdump rebinds. Mitigation: small retry loop (3 attempts). If all fail, print actionable error with the chosen ports and suggest `--proxy-port` / `--web-port`.
- **Allocation fairness**: two concurrent `start`s might both see "free port 12345" then race. Accept the race; second one retries. Do not add inter-process coordination for port allocation.

## Phase 3 — Per-workspace storage

### Deliverables

1. `api/src/manicure/workspace.py` — add `workspace_storage(cwd) -> Path` returning `~/.manicure/workspaces/{slug}/{hash}/` and creating it if absent. Skips `@lru_cache`'d `get_settings()`.
2. CLI `start`:
   - Replace the current `resolved_storage = ... get_settings().storage_dir ...` fallback with `resolved_storage = storage_dir or workspace_storage(working_dir)`.
   - `--storage-dir` flag still overrides.
3. CLI `paths`:
   - When in a directory with a live workspace, show that workspace's storage path. When not, show the workspace the CWD would resolve to (even if empty). Add a `--workspace` flag to target a specific workspace by slug or CWD.
4. CLI `list`:
   - Already surfaces per-workspace storage from the manifest. No change beyond Phase 1.
5. Tests:
   - `test_workspace.py` — `workspace_storage` creates the directory, is idempotent, is distinct for distinct CWDs.
   - `test_cli.py` — `start --print-command` (or effective config) uses workspace storage when no `--storage-dir`; explicit flag overrides.

### Acceptance criteria

- [ ] Two concurrent `start`s in different CWDs write to different storage roots.
- [ ] `manicure paths` resolves to the workspace storage for the CWD.
- [ ] `--storage-dir` still overrides.
- [ ] No regression in the existing addon / storage code.
- [ ] Tests green.

## Review gates

- **End of each phase**: engineering-code-reviewer reviews the diff before merge. Focus: correctness, test coverage, convention adherence (700 lines, types, import DAG), race conditions in the lock/port code.
- **After all 3 phases**: full `pytest` green, `manicure start` smoke test in two terminals, `manicure list` works.

## Commit strategy

- One commit per phase: `feat(cli): workspace lock + manifest + list (phase 1)` etc.
- Small fix-up commits welcome. No squash-merge within a phase.
- Branch: continue on `feat/own-claude-process` or cut a new branch `feat/multi-instance` — engineer's call, but state it in the Phase 1 kickoff message.

## Not in scope (explicitly)

- Linear issue tracking (no users yet; keep velocity).
- Frontend changes (the UI is relative-path already; no work needed).
- Migrating existing `~/.manicure/` data (no users).
- `manicure attach` / `manicure stop` (future work; manifest gives us the hooks).
- Cross-workspace exchange search (future; per-workspace roots are fine for now).

# Token Watcher Reliability Review

## 1. Race Condition at SessionStart: JSONL File Existence

### The problem

When the SessionStart hook fires, it is unclear whether the current session's JSONL file already exists on disk. The code has two paths:

**Path A (explicit session ID):** Lines 35-36. If `HELIOY_SESSION_ID` or `CLAUDE_SESSION_ID` is set, the JSONL path is computed deterministically. But the file may not exist yet. `tail -F` (follow by name) handles this correctly: it retries opening the file until it appears. This path is safe.

**Path B (mtime fallback):** Lines 38-49. If no session ID is available, `ls -t "$JSONL_DIR"/*.jsonl | head -1` picks the most recently modified JSONL. At SessionStart time, the current session's JSONL has either not been created yet or was just created with zero content. Two failure modes:

1. **File not created yet:** `ls -t` returns the previous session's JSONL. The watcher attaches to the wrong file and tracks stale data. The `sleep 2` retry at line 43 partially mitigates this, but 2 seconds is not a guaranteed window. If Claude Code creates the file at 2.5 seconds, the retry still picks the wrong file.

2. **File created but not yet written to:** `ls -t` may pick it up (mtime is set at creation), but the race is tight. If two JSONL files have the same second-resolution mtime, `ls -t` ordering is nondeterministic.

### Severity: HIGH for Path B

Path B is the fallback when no session ID env var is set. In warroom spawns where `HELIOY_SESSION_ID` is set by the wrapper script, Path A is taken and the race does not apply. The risk is for ad-hoc sessions where the env var is absent.

### Recommendation

Eliminate Path B entirely. The `bus-register.sh` hook (lines 41-49) has the same mtime fallback pattern and the same risk. Both hooks should require an explicit session ID. If `HELIOY_SESSION_ID` and `CLAUDE_SESSION_ID` are both empty, the watcher should log a warning and exit cleanly rather than guessing.

If the fallback must be preserved, replace `ls -t | head -1` with a polling loop that waits for a new file to appear:

```bash
# Wait for a JSONL file newer than hook start time
HOOK_START=$(date +%s)
for i in {1..10}; do
    JSONL_FILE=$(find "$JSONL_DIR" -name '*.jsonl' -newer /proc/$$/fd/0 -printf '%T@\t%p\n' 2>/dev/null \
        | sort -rn | head -1 | cut -f2)
    [[ -n "$JSONL_FILE" ]] && break
    sleep 1
done
```

This is still fragile. The explicit session ID path is the correct solution.


## 2. Backgrounded Subshell PID Capture

### The problem

Line 105: `(...) &>/dev/null &`
Line 107: `echo $! > "$WATCHER_PID_FILE"`

`$!` captures the PID of the most recently backgrounded process. The backgrounded process is the subshell `(...)` itself, not the `tail | while` pipeline inside it.

Inside the subshell, `tail -F ... | while ...` creates a pipeline. The shell (bash) runs this as two processes: `tail` and `while read`. The subshell process itself is the pipeline's parent.

### What PID gets captured?

`$!` captures the subshell PID. This is correct for cleanup purposes because:
- `kill $PID` sends SIGTERM to the subshell.
- The subshell's `tail | while` pipeline receives SIGPIPE when the subshell dies.
- `tail -F` exits when the read end of its stdout pipe closes.

### What about the stop hook's `kill -- -"$WATCHER_PID"`?

Line 30 in `token-watcher-stop.sh`: `kill -- -"$WATCHER_PID"` sends the signal to the process group. This is the correct approach for killing the entire pipeline (subshell + tail + while). However, a backgrounded subshell `(...) &` does not always create a new process group. In bash, `set -m` (monitor mode) controls whether backgrounded jobs get their own process group. In a non-interactive script (which this is, since hooks run non-interactively), monitor mode is off by default. The backgrounded subshell inherits the parent's process group.

### Severity: MEDIUM

`kill -- -"$WATCHER_PID"` will fail with "No such process" because the subshell PID is not a process group leader. The fallback `|| kill "$WATCHER_PID"` on line 30 handles this correctly for the subshell itself, but `tail` may survive as an orphan.

### Recommendation

Two options:

**Option A:** Force a new process group for the subshell by using `setsid`:

```bash
setsid bash -c '
    TOTAL_OUTPUT=0
    tail -n 0 -F "$JSONL_FILE" 2>/dev/null | while IFS= read -r line; do
        ...
    done
' &>/dev/null &
```

Then `kill -- -"$WATCHER_PID"` correctly kills the entire group.

**Option B:** Track both PIDs. After the subshell starts, write both the subshell PID and the tail PID to the PID file. The subshell can report its child PIDs:

```bash
(
    ...
    tail -n 0 -F "$JSONL_FILE" 2>/dev/null &
    TAIL_PID=$!
    echo "$TAIL_PID" >> "$WATCHER_PID_FILE.children"
    wait "$TAIL_PID"
) &>/dev/null &
```

Option A is simpler and more robust.


## 3. Orphan Detection: `$PPID` in Backgrounded Subshell

### The problem

Line 72: `HOOK_PPID=$PPID` is set inside the subshell `(...)`.

In bash, `$PPID` is set once at shell startup and is read-only. Inside a subshell created by `(...)`, `$PPID` retains the value from the parent shell. The parent shell is the hook script itself (token-watcher.sh). The hook script's `$PPID` is the process that invoked it.

### What is PPID actually?

The hook is invoked by Claude Code's hook runner. The chain is:

```
Claude Code (node) → hook runner → bash (token-watcher.sh) → subshell (...)
```

`$PPID` in `token-watcher.sh` is the hook runner's PID, or Claude Code's PID, depending on how hooks are spawned. It is not necessarily the long-lived Claude Code process.

If the hook runner is a short-lived subprocess that invokes the hook and exits, `$PPID` becomes 1 (init/launchd) almost immediately after the hook completes. The orphan check `kill -0 "$HOOK_PPID"` would then fail on the very first iteration, killing the watcher prematurely.

### Severity: HIGH (conditional)

If Claude Code spawns hooks via a persistent process (the node runtime itself), `$PPID` is the node PID and the orphan check works. If hooks are spawned via a transient subprocess (e.g., `/bin/bash -c 'token-watcher.sh'`), the parent exits immediately and the orphan check fires erroneously.

### Recommendation

Do not use `$PPID` for orphan detection. Instead, monitor the Claude Code process directly:

```bash
# In the hook script (before backgrounding), capture the Claude PID
CLAUDE_PID="${HELIOY_BUS_CLAUDE_PID:-$(ps -o ppid= -p $PPID 2>/dev/null | tr -d ' ')}"
```

Or better: use the PID file written by `bus-register.sh`. The bus registration writes `$PPID` to `$PIDS_DIR/$PPID`, and the agent_id to the file. But what we actually need is the Claude Code process PID. `bus-register.sh` line 55 writes to `$PIDS_DIR/$PPID`, where `$PPID` is the Claude Code PID from the hook script's perspective.

The token watcher should read the Claude PID from the same source:

```bash
# Inside the backgrounded subshell
CLAUDE_PID=$(ls -t "$PIDS_DIR" | grep -E '^[0-9]+$' | while read pid; do
    if [[ "$(cat "$PIDS_DIR/$pid")" == "$AGENT_ID" ]]; then
        echo "$pid"
        break
    fi
done)
```

Or simply: pass the PID as an explicit variable before backgrounding:

```bash
CLAUDE_PID="$PPID"  # In the hook script, before the subshell
(
    # Use CLAUDE_PID for orphan detection
    if ! kill -0 "$CLAUDE_PID" 2>/dev/null; then ...
) &>/dev/null &
```

This captures `$PPID` in the hook script's own scope (where it is the hook runner's parent, which should be Claude Code) and passes it to the subshell via variable inheritance. Whether this is correct depends on the hook invocation chain. Logging the actual value of `$PPID` and the process tree would validate the assumption.


## 4. SQLite Concurrency from Background Processes

### The problem

Line 94-103: The backgrounded watcher runs `sqlite3 "$DB_PATH" "UPDATE ..."` on every assistant turn. In a warroom with 8 agents, 8 background watchers write to the same `registry.db` concurrently.

### Is WAL mode sufficient?

WAL mode allows concurrent readers and a single writer. Multiple writers are serialized by SQLite's internal locking. With `PRAGMA busy_timeout` set appropriately, writers will retry on lock contention rather than failing immediately.

However, the `sqlite3` CLI tool invoked here does not set a busy timeout by default. If two watchers try to write simultaneously, one gets `SQLITE_BUSY` and the statement fails. The `2>/dev/null || true` on line 103 swallows this error silently.

### Severity: MEDIUM

Token updates are high-water-mark writes (the next successful write will capture the correct value). A single lost update is self-correcting on the next assistant turn. The data is eventually consistent.

The real concern is sustained contention: if 8 watchers all fire within milliseconds (e.g., when the orchestrator sends a briefing and all agents respond nearly simultaneously), multiple updates may fail in sequence. The token data becomes stale until contention subsides.

### Recommendation

Add a busy timeout to the sqlite3 invocation:

```bash
sqlite3 "$DB_PATH" ".timeout 3000" "UPDATE agents SET ..."
```

The `.timeout 3000` pragma tells sqlite3 to retry for up to 3 seconds before returning SQLITE_BUSY. This serializes concurrent writes without data loss.

Alternatively, add random jitter to the write timing:

```bash
# Before the sqlite3 call
sleep "0.$(( RANDOM % 500 ))"
```

This spreads writes across a 500ms window, reducing contention probability.


## 5. Error Swallowing

### The problem

Line 103: `2>/dev/null || true`

All sqlite3 errors are silently discarded. This includes:
- `SQLITE_BUSY` (concurrent write contention) -- self-correcting, acceptable to swallow
- Malformed SQL syntax -- permanent, never self-corrects, invisible failure
- Database corruption -- critical, should be surfaced immediately
- Schema mismatch (e.g., `token_usage` column missing) -- permanent until schema migration

### Severity: MEDIUM

The SQL on lines 94-102 uses `json_object()` and `json_extract()`, which require SQLite 3.38+ (the JSON1 extension). If the system sqlite3 binary is older, every single write fails silently. The watcher appears to run but produces no data.

The `token_usage` column is referenced in the UPDATE but never appears in the CREATE TABLE in `bus-register.sh` (lines 83-92) or `bus_server.py:_init_db`. If no migration has added this column, every write fails silently.

### Recommendation

1. **Add the `token_usage` column migration** to both `bus-register.sh` and `bus_server.py:_init_db`:

```sql
ALTER TABLE agents ADD COLUMN token_usage TEXT DEFAULT '{}';
```

2. **Log errors to a file** instead of `/dev/null`:

```bash
WATCHER_LOG="$BUS_DIR/logs/token-watcher-${AGENT_ID}.log"
mkdir -p "$(dirname "$WATCHER_LOG")"

# In the sqlite3 call:
sqlite3 "$DB_PATH" "..." 2>>"$WATCHER_LOG" || true
```

3. **Validate sqlite3 capabilities at startup** before spawning the watcher:

```bash
if ! sqlite3 :memory: "SELECT json_object('test', 1)" &>/dev/null; then
    echo '{"error": "sqlite3 too old for JSON functions"}' >&2
    exit 0
fi
```


## Summary of Findings

| Issue | Severity | Self-correcting? | Fix complexity |
|---|---|---|---|
| JSONL mtime fallback picks wrong session | HIGH | No | Low (require explicit session ID) |
| `$PPID` in backgrounded subshell may be transient | HIGH | No | Medium (validate PID chain) |
| Process group kill fails in non-interactive mode | MEDIUM | Partial (fallback exists) | Low (use setsid) |
| SQLite writes fail without busy timeout | MEDIUM | Yes (eventual consistency) | Low (add .timeout) |
| All sqlite3 errors swallowed | MEDIUM | No (permanent for schema/syntax) | Low (log to file) |
| `token_usage` column may not exist | MEDIUM | No | Low (add migration) |

---
title: Cloudflare Computer — Durable Object VFS with pluggable agent execution backends
type: research
tags: [github-review, cloudflare, computer, computerd, durable-objects, workers, capnweb, fuse, sandboxing, agent-execution, worker-loader, mit, typescript, preview]
summary: Substantive single-author Cloudflare preview (611 commits, 35k LOC src / 31k LOC tests, 6k lines of design spec) that puts an agent's filesystem in Durable Object SQLite and projects it into three execution backends. Platform-locked to Cloudflare, so skip as a dependency. Borrow the rev-cursor sync protocol, the exec handle/reattach contract, the deny-by-default egress model, and the AGENTS.md environment-traps pattern.
status: active
source: github-researcher
confidence: high
created: 2026-08-08
updated: 2026-08-08
---

## Verdict

**Skip as a dependency. Borrow five patterns. Watch one bet.**

It is real engineering, not a demo, and it is completely unusable outside Cloudflare. `Workspace` requires `ctx.storage` from a Durable Object, the fast backends require `env.LOADER` (Worker Loader dynamic isolates), and the container backend requires Cloudflare Containers. There is no local mode, no self-host path, and no runtime other than workerd. For a Rust, macOS-host, tmux-pane orchestration stack it offers zero liftable code.

The design work is worth reading anyway, because it solves the same problems Helioy's `runtime-matters` is solving and arrives at several of the same answers independently.

Two scoping notes. Despite the name, there is no computer-use, browser rendering, screenshots, or VNC anywhere in the repo; the only Puppeteer strings are in generated `worker-configuration.d.ts` binding types in examples. "Computer" here means filesystem plus shell. And there is **no MCP** — no server, client, or transport in any package, doc, or example. The agent integration point is a Vercel AI SDK `ToolSet`, nothing else. An external contributor has an open PR proposing an MCP example; it is unmerged and the repo does not accept unsolicited PRs.

## What it actually is

An agent's working directory, stored authoritatively as SQLite rows inside a Durable Object, with a pluggable execution surface over it.

```
Workspace {
  fs       — Node-fs/promises-shaped API over DO SQLite (durable)
  runtime  — exec(source, { backend }) router over N registered backends
  git      — isomorphic-git driven against the same SQLite VFS
  assets / artifacts — publish files out to R2 / Cloudflare Artifacts
}
```

Three backends ship, and the backend ID decides how `source` is interpreted:

| Backend | Source language | Isolation | Sync cost |
|---|---|---|---|
| `container-shell` | shell | Cloudflare Container, full Linux userland, real binaries | FUSE mirror, push/pull bracket around every exec |
| `worker-shell` | just-bash | Dynamic Worker isolate, `globalOutbound: null` | none — reaches host SQLite over Workers RPC |
| `worker-javascript` | ECMAScript module | Dynamic Worker isolate, capability-scoped | none — host capability calls |

The container backend is the interesting one architecturally. The Durable Object holds truth in SQLite; a daemon called `computerd` runs inside the container, mounts that state as a **real FUSE filesystem**, and syncs deltas back over a capnweb WebSocket. Ordinary Linux tools (`npm`, `git`, `pandoc`) run against `/workspace` and their writes land in a Durable Object.

Critically, **FUSE operations never block on the network**. `computerd` keeps its own in-process SQLite mirror; every FUSE callback resolves against that local store synchronously, and a background loop syncs to the Durable Object every 250 ms (`packages/computerd/src/fuse/vfs.ts:83`, `SYNC_TICK_MS`). The WebSocket is on the sync path, not the read path. That decoupling is the whole reason the performance numbers are survivable.

The two Worker backends skip the container entirely and reach the same SQLite over Workers RPC, so there is one store and no sync round trip. That is the part that is genuinely new.

### Storage model

`packages/dofs` is a real filesystem, not a key-value shim. Schema version 5, four migrations, three tables for the inode graph and three for content:

- `vfs_nodes` — inode, type (`file|dir|symlink`), mode, mtime, `rev`, `size`, `manifest_hash`, `link_target`
- `vfs_dirents(parent_inode, name) → child_inode`, `WITHOUT ROWID` — so rename is one dirent UPDATE and hardlinks are two dirents onto one node
- `vfs_chunks(inode, idx) → hash`, `vfs_blobs(hash)`, `vfs_blob_bytes(hash)` — content-addressed, SHA-256, fixed 512 KiB windows (`CHUNK_SIZE`, `packages/dofs/src/fs/writeFile.ts:25`)
- `vfs_manifests` — `sha256` over the ordered chunk list, stamped onto the node, giving an O(1) "this file is already exactly what you are sending me" test

The provider implements enough of Node's `fs` to satisfy `@platformatic/vfs`, including symlinks, hardlinks, fd-based positional reads and writes, and a `watch` that polls the global `rev` counter. `appendFile`, `copyFile`, `watchFile`, and `unwatchFile` throw `ENOSYS`. `chown` and `utimens` never reach storage at all; the FUSE driver holds them in an in-memory sidecar map.

The FUSE tuning is unusually deliberate: `max_read`/`max_write` are pinned to 512 KiB **to match `CHUNK_SIZE` exactly**, so one FUSE read is one chunk fetch rather than four (`packages/computerd/src/fuse/options.ts:10-34`). `attr_timeout`/`entry_timeout` sit at 1 s so `find` and `git status` skip round-trips, while `negative_timeout=0` keeps a just-written file immediately visible.

## Maturity

**Real code, preview status, bus factor one.**

- 611 commits since 2026-05-22. **577 of them by a single engineer** (Aron Carroll, Cloudflare). Next contributors are 10, 8, and 5 commits. This is one person's project with light Cloudflare support.
- ~35,000 LOC source across four packages against **~31,000 LOC of tests in 115 test files**. That ratio is the strongest maturity signal in the repo.
- 19 numbered design docs totalling 6,065 lines, plus per-package READMEs, `AGENTS.md`, `CONTRIBUTING.md`, `COLLABORATORS.md`, and six in-repo agent skills.
- Per-package CI matrix (one job per workspace so a computerd test failure cannot mask a dofs typecheck failure), changesets release flow, biome lint gate.
- MIT, clean, no riders. Cloudflare, Inc. 2026.

Timeline tells the story: first commit 2026-05-22, GitHub repo created 2026-06-05, package renamed from `@cloudflare/workspace`/`wsd` to `@cloudflare/computer`/`computerd` on 2026-07-30, first npm publish 2026-07-29, `0.1.1` on 2026-08-03, issues start arriving 2026-08-05. The 6,103 stars are a launch spike from the last two weeks, not sustained accumulation.

Development has been bursty: 106 commits in W22, 210 in W23, then near-zero through W26–W30, then 61 and 55 in W31–W32. The recent burst is agent-facing file tools and removing `@cloudflare/think` coupling. Eight open PRs, all authored by the same engineer.

**Not production-ready, and the repo says so loudly.** The README, the docs index, and every package README carry a PREVIEW ONLY banner. The docs are explicitly labelled forward-looking — `docs/06_mount_interface.md` describes an R2/GitHub mount system marked **(not yet implemented)**.

Admitted gaps, from the docs and open issues:

- **No Durable Object hibernation.** `docs/11_lifecycle.md` states the code uses `server.accept()` rather than `ctx.acceptWebSocket()`, so a workspace with a live container pins an isolate.
- **capnweb session death is unhandled.** Quoting the lifecycle doc: "The death case today is **not handled** — the `Workspace` keeps its `#handle` reference pointing at the dead session, and the next RPC call throws. The caller is expected to reconstruct the workspace."
- **`gc()` is unreachable**, so orphaned blobs and manifests are never reclaimed (issue #68).
- **`vfs_changes` tombstones grow without bound** (issue #67).
- **The workerd test project segfaults and has never run in CI** (issue #71).
- Symlink handling has at least three open correctness bugs (#54, #55, #65).
- ~10 GB ceiling shared with Durable Object storage, and the container-side mirror is held in memory, so "agent-scale workspaces, not full monorepos".

**The sharpest edge, and the one that matters most for multi-agent work:** concurrent writers are not merged and not detected. From `docs/02_sync_protocol.md`, whichever container's push arrives last wins, and "There is no merge, no error, and no indication to either caller that a conflict occurred... the same semantics as a shared NFS mount without locking, or an S3 bucket without conditional PUTs." The doc names read-modify-write cycles and a shared `PLAN.md` or `state.json` as data-loss patterns by example. Structural conflicts (a path that is a file on one side and a directory on the other) resolve by deleting the local subtree without tombstones, discarding local-only children silently.

Two agents sharing one workspace lose writes. Anyone reaching for this as shared multi-agent scratch space needs to read that document first.

The wire has matching gaps, documented in `docs/08_capnweb_interface.md`: no version negotiation ("the durable object and computerd are deployed as a matched pair... request and response shape changes are hard wire breaks and require lockstep rollout"), an unauthenticated handshake that "currently trusts anything that can reach the port", and no bound on frame size, in-flight RPC count, or batch size, so "a pathological caller can ask for 100k hashes in one call and pin both sides on a single oversized frame".

Governance is closed by design. `CONTRIBUTING.md` refuses unsolicited pull requests and a `close-unrequested-prs.yml` workflow auto-closes them with a redirect to issues or discussions, gated on `author_association` plus an `allow-pr` label escape hatch.

## Novel vs repackaged

**Genuinely novel:**

1. **A filesystem whose source of truth is a database at the edge, projected into a container over FUSE.** Content-addressed 512 KiB chunks with per-chunk hashing means the sync layer ships only changed chunks and deduplicates identical content. Nobody else is shipping "your agent's disk lives in SQLite in a Durable Object and the container is a cache".
2. **Dynamic Worker isolates as the per-execution sandbox.** `env.LOADER.get(id, codeCallback).getEntrypoint(...)` mints a V8 isolate per workspace, boots effectively instantly, costs nothing per session, and dies without touching neighbours. This is the real bet, and it is a structurally different answer to agent code execution than Firecracker-per-agent (E2B) or container-per-agent.
3. **Honest, self-damaging benchmarks.** `docs/19_performance.md` publishes that computerd is **40x slower than disk on 64 MiB sequential copy** and 2x slower on a full `npm install` of 854 packages, alongside the eight metadata-heavy scenarios where it beats real disk (`stat`, `rm`, `mkdir tree`, `find tree`, `git init`, `git clone`, `npm init`). Publishing your 40x loss is a maturity signal.

**Repackaged:**

- **capnweb** is Cloudflare's own existing object-capability RPC library (3.9k stars, separate repo).
- **just-bash** is Vercel Labs' bash-for-agents interpreter (4.1k stars).
- **isomorphic-git** does all the actual git work; `packages/computer/src/git/cli.ts` is a 2,370-line argv parser over it covering 30 subcommands.
- **Cloudflare Containers** and Durable Objects are shipping products.
- **`@cloudflare/computer/tools`** is a re-implementation of the Claude Code toolset (`read`, `write`, `edit`, `ls`, `exec`, `publish`) as AI SDK tools.

**Relationship to `cloudflare/sandbox-sdk`:** they coexist rather than supersede. sandbox-sdk (1,094 stars, created 2025-06) is "run code in a container on the edge". Computer is the persistent-filesystem-plus-routing layer, and it benchmarks *against* sandbox-sdk's own `npm install` as a workload. Computer's in-repo skill index tells agents to load the `sandbox-sdk` skill when working on the container boundary. Expect convergence pressure.

## Patterns worth stealing

### 1. Backend selection is routing, not authorization

`docs/16_code_execution.md` is blunt: "There is no general `workspace.scope()` abstraction. Backend construction fixes maximum authority and module availability... The backend argument is never itself authorization." Different authority levels mean separate backend instances:

```ts
new WorkerJavaScriptBackend({ id: "worker-javascript-readonly", access: "read" });
new WorkerJavaScriptBackend({ id: "worker-javascript",          access: "read-write" });
```

This is the same conclusion the ALP-2643 design reached independently — model sandboxing as **policy on the request**, not as a new runtime kind or a new target, and fix authority at construction. Independent convergence on that cut line is worth something.

### 2. The execution handle contract

```ts
interface WorkspaceRuntime {
  exec(source: string, options?): Promise<WorkspaceRuntimeExecHandle>;
  getExec(id: string, options?): Promise<WorkspaceRuntimeExecHandle>;   // reattach
  killExec(id: string, options?): Promise<void>;
  disposeExec(id: string, options?): Promise<void>;                     // release retention
}

interface WorkspaceRuntimeExecHandle extends ReadableStream<WorkspaceRuntimeEvent> {
  readonly id: string;
  readonly backend: string;          // records resolved backend for later reattach
  result(): Promise<WorkspaceRuntimeResult>;
  kill(signal?: KillSignal): Promise<void>;
  [Symbol.dispose](): void;
}
```

Four things here are directly applicable to spawn/attach in `runtime-matters`:

- **The handle *is* the event stream.** `extends ReadableStream` rather than carrying one. Single-consumer: call `result()` or drain the stream, never both.
- **`backend` is recorded on the handle** so reattach knows where to look. Reattach needs the routing decision, not just the ID.
- **Events carry a monotonic `seq` per exec ID**, so reattach is `getExec({ id, after: seq })`. Cheap, correct, no replay-from-zero.
- **Explicit `disposeExec`** separate from `kill`. Killing stops the work; disposing releases the retained record. Conflating them loses the post-mortem.

The four-state result (`completed | failed | cancelled` with a separate `sync` sub-status that can be `pending`) is also right: the command can succeed while the post-command sync fails, and those are different facts that a caller needs separately.

Two further details from the implementation:

- **The reattach journal is two SQLite tables in the host**, `workspace_runtime_executions` and `workspace_runtime_events`. This is what makes `getExec` replay survive a host restart, and `disposeExec` deletes from both in one transaction.
- **Orphan reconciliation runs at construction.** Any row still marked `running` when the runtime comes up is finalized as failed with an explicit message ("Execution was interrupted when its Workspace runtime restarted"). A live isolate capability cannot be serialized into SQLite, so a run that spanned a restart is definitionally lost — and the design says so rather than leaving a row in limbo. Any `runtime-matters` lifecycle store needs the same startup sweep, and the same honesty about what a `running` row means after a crash.

Under the hood there are actually **two backend protocols**, not one: `WorkspaceBackend` (command backends, speaking a `ShellRPC` stub, bracketed by push/pull) and `WorkspaceModuleBackend` (`protocol: "module"`, executing in-process against host capabilities, no sync). The router hides the split by wrapping command backends in an adapter that presents the module-backend shape, so `runtime.exec` has exactly one execution path. That is the right way to add a second execution protocol without forking the caller-facing API.

### 3. Rev-cursor sync with idempotent receivers

The reason the sync protocol survives torn connections, stated plainly in `docs/11_lifecycle.md`:

> "This is why the sync protocol survives transport failures: every operation has a persistent cursor, and every receiver is idempotent. capnweb itself is fragile, but the protocol layered on top isn't."

Concretely: `pushRev` is written only after the push cursor is asserted applied, so a torn push replays the same batch and `applyChanges` drops duplicates via an `alreadyApplied` check. The pull cursor advances per committed batch to the last streamed `(rev, path)`. Watermark rows are written **in the same SQLite transaction as the data they describe**, so cursor and data cannot drift.

Three implementation details make it work, all portable:

- **Idempotency is a content hash, not a flag.** `alreadyApplied()` (`packages/dofs/src/sync/apply.ts:459`) compares the incoming file's manifest hash against the stored one, directory mode against mode, symlink target against target. A no-op entry is dropped before it bumps `rev`, which is also how loopback echo is suppressed. No dirty bits to get out of sync.
- **Dirty tracking is a monotonic counter, not a dirty set.** One `vfs_meta.rev` row bumps on every mutation and is stamped into each node. "What changed since you last saw me" is an indexed range scan on `rev > lower`, coalesced per path so five rewrites ship as one entry, sorted by `(rev, path)` so the receiver can checkpoint mid-stream.
- **Divergence is detected and recovered exactly once.** If the remote's echoed cursor is behind what we believe we pushed (a `computerd` restart under a surviving socket), the driver resets the divergent cursor and retries once. A second divergence throws rather than looping, on the reasoning that a same-rev partial cursor means the receiver lost state *inside* a rev it claimed to have, which replay cannot mend (`packages/rpc/src/sync-driver.ts:123-128`).

The cursor-and-data point is the one to internalize for `helioy-bus` reconnect semantics: a cursor persisted in a separate write from the data it describes is a bug waiting for a crash. Note the deliberate exception — the pull path advances its cursor *outside* the apply transaction and accepts re-fetching a batch, precisely because `alreadyApplied` makes replay free. Idempotency buys you the right to be sloppy about atomicity in one direction.

### 4. Deny-by-default egress with a single loopback

Every Dynamic Worker is minted with `globalOutbound: null` (`worker-shell.ts:254`, `worker-javascript.ts:208`), which blocks `fetch()` and `connect()` outright. The only path out of the isolate is back through the host Durable Object over `env.HOST`. Consequences that fall out for free:

- The shell isolate **never receives the R2 bucket binding or signing secrets**. `assets publish` inside the shell is a custom command that forwards over the loopback to a host-side capability.
- `process.env` is a snapshot of exactly what the caller passed for that execution. The host environment is never merged in, so module code cannot read host bindings through it.

Same threat model, and effectively the same answer, as the default-deny NetworkPolicy plus metadata-server block in `kubernetes-sigs/agent-sandbox`. Two independent projects converging on "the sandbox gets no network; capabilities are handed in explicitly by the host" is a strong signal for how `runtime-matters` should default.

### 5. Stubs are capabilities, and capabilities leak

From the in-repo capnweb skill: "A stub is a **capability**: holding it is the right to call the remote object. Stubs are not garbage-collected across the network — the local GC has no visibility into the remote object graph." The repo ships a leak-hunting harness for this: `CAPNWEB_TRACK_STUBS=1` plus `stubSnapshot()`, and a `GET /__computerd/stubs` endpoint on the daemon. Two soak scripts (`computerd-stub-soak.mjs`, `computerd-soak.mjs`) exist specifically to catch disposal drift over long sessions.

Any long-lived agent RPC surface needs this. A leak that only manifests after hours of a warroom session will not be caught by unit tests, and "add an endpoint that dumps the live capability table" is a cheap way to make it observable.

### 6. Bounded LLM file tools with continuation offsets

`createReadTool` defaults to 2,000 lines / 256 KiB per call, streams through `readChunks` and **stops as soon as a cap is hit** rather than reading then truncating, and returns `nextOffset` when truncated so the model can continue. `createEditTool` matches every edit against the *original* file content (not incrementally), rejects overlapping or nested edits, normalizes line endings for matching but restores the original style on write, and preserves file mode so executable scripts keep their bit.

The accompanying guidance is the useful part: "Pair the `edit` tool with a system prompt that says edits apply against the original file. Models that incrementally update their mental model of the file will produce overlapping edits and get a rejection error." And: "Treat `exec` output as untrusted text when feeding it back into the model."

### 7. `AGENTS.md` as an environment-traps document

This is the pattern most directly transferable to harness work, and it inverts the usual instinct. The repo's `AGENTS.md` spends most of its length not on conventions but on **the specific ways a fresh environment will waste an agent's time**, prefaced with: "A fresh container does not have everything the tests need. The traps below cost real time if you discover them one failure at a time."

The traps are concrete and non-obvious: `fuse-native` needs `build-essential libfuse-dev` and a failed build aborts the *entire* `npm install`, not just that package; on arm64 the bundled libfuse is x64-only and needs a manual `cp` plus `node-gyp rebuild`; test scripts do not build sibling packages so a clean checkout must run `npm run build` first; and the real-FUSE test guard is a bare `/dev/fuse` existence check, so a `mknod`'d device in an unprivileged container turns a clean skip into a hard `EPERM` failure.

That is a different genre of document from a conventions file. It is a record of every failure that cost someone an hour, written so it costs the next agent zero. Worth a pass over the Helioy harness overlays.

Also notable in the same file: the commit convention forbids "references to chat history, agent sessions, sibling commit SHAs, or task identifiers" — stand-alone artifacts only. And `.agents/skills/prose/SKILL.md` is a compact style guide whose rules are close to the Helioy writing rules already in force (no marketing voice, no decorative characters, active voice, prefer simple verbs, avoid "easy"/"simply"/"just", sentence-case headings).

### 8. Record the design you rejected, and the optimization you removed

Two habits in this codebase are worth copying outright.

**Rejected alternatives live next to the thing that won.** `docs/02_sync_protocol.md` records that a dedicated rename opcode was considered and rejected, with the reason: a rename is an *operation* in an otherwise state-based protocol, and it is meaningless to a cold-start peer that never held the source path. Directory rename stays O(subtree) as a consequence, and the doc says so. The next person who notices the O(subtree) cost finds the answer instead of re-deriving it.

**Removed optimizations are documented in place.** `packages/dofs/src/sync/apply.ts:300-314` is a comment describing an optimization that was deleted: advancing the local `pushRev` after an upstream apply moved the cursor past entries the remote did not know we had, which tripped the cross-side invariant on the next pull and **silently hid every subsequent container-side write**. The code now pays one extra push per apply. Nothing about the current code hints that the faster version is unsound, so the comment is the only thing standing between a future reader and reintroducing the bug.

This is the cheap version of institutional memory, and it survives the maintainer leaving.

### 9. Benchmark on deterministic counters, not wall-clock

`packages/dofs/src/bench/fs-ops.bench.ts` reports nanoseconds per op **and** SQL statement and row counts, via a `CountingStorage` wrapper. The statement counts are treated as the primary signal because they are deterministic and wall-clock is not. The harness also deliberately runs against a real Durable Object `SqlStorage` rather than the Node test fixture, because the fixture caches prepared statements and would understate exactly the per-statement cost the benchmark exists to measure.

For any Helioy perf work where the real cost is "how many round trips" or "how many syscalls", asserting a counter in CI is a regression test. Asserting a duration is a flaky test.

## Does not transfer

- **The entire runtime.** Durable Objects, Workers RPC, Worker Loader, and Cloudflare Containers have no local equivalent. `Workspace` cannot be constructed without `ctx.storage`.
- **TypeScript in workerd.** Helioy is Rust 2024. Nothing here is a library to import.
- **The FUSE-over-SQLite filesystem.** Helioy agents work on a real local disk in a real git worktree. Paying a 40x sequential-I/O penalty (the cost of hashing every 512 KiB chunk into a content-addressed store on release) buys chunk-level sync and dedup that Helioy already gets from the filesystem and git.
- **The concurrency model.** One Durable Object, one container, one writer. Helioy runs many panes against one tree; last-write-wins with no conflict signal is the wrong primitive for that and the docs say as much.
- **The 1:1 Durable Object to container pairing.** Load-bearing for their hibernation story, irrelevant to a tmux-pane model where one host runs many panes.
- **Single-maintainer, preview-status, closed-contribution.** Not a project to build a dependency on. If Aron Carroll changes teams, it stalls.

## Relevance to Helioy

`runtime-matters` and Cloudflare Computer are solving the same problem from opposite ends: Computer starts from durable state and adds execution; `runtime-matters` starts from execution and adds isolation policy. The overlap is the exec contract and the isolation defaults, and on both Computer independently confirms decisions already made.

The concrete borrows, ranked:

1. **The exec handle contract plus the orphan sweep** (§2) — `getExec(id, { after: seq })` reattach, `backend` recorded on the handle, `kill` separate from `dispose`, and a startup pass that reconciles `running` rows to failed. Directly shapes spawn/attach and the lifecycle store.
2. **Content-hash idempotency and cursor-with-data** (§3) — correctness rules for `helioy-bus` reconnect, not nice-to-haves. Idempotent receivers are what let you relax atomicity elsewhere.
3. **Deny-by-default egress, capabilities handed in by the host** (§4) — the default for sandboxed spawn, corroborated by `agent-sandbox`.
4. **A capability-table dump endpoint** (§5) — cheap observability for long-lived warroom sessions.
5. **`AGENTS.md` as environment traps, plus rejected-design comments** (§7, §8) — a harness overlay pass, and a documentation habit that survives the author.
6. **Counter-based benchmarks** (§9) — assert statement or round-trip counts in CI, not durations.

The one thing to carry as a warning rather than a pattern: Computer's shared-workspace concurrency is last-write-wins with no conflict signal. A tool that looks like shared multi-agent scratch space and silently drops writes is a failure mode worth naming explicitly in any Helioy equivalent.

Nothing here changes a roadmap decision. It is corroboration plus six tactical patterns and one anti-pattern.

## Sources consulted

Cloned at commit `8f0d33a`-era `main` (HEAD 2026-08-07, "dofs: Guard the staged-chunk link path"), full history, 611 commits.

- `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `COLLABORATORS.md`, `LICENSE`
- `docs/README.md`, `01_vfs.md`, `02_sync_protocol.md`, `03_filesystem_schema.md`, `05_runtime_interface.md`, `08_capnweb_interface.md`, `09_tool_interface.md`, `11_lifecycle.md`, `12_worker_backend.md`, `13_git_interface.md`, `16_code_execution.md`, `17_isolate_javascript.md`, `19_performance.md`
- `.agents/skills/{prose,capnweb,cloudflare}/SKILL.md`
- `.github/workflows/{ci.yml,close-unrequested-prs.yml}`
- `packages/*/package.json`, source file inventory, `packages/computer/README.md`
- `packages/computer/src/` — `index.ts`, `workspace.ts`, `backend.ts`, `runtime/{runtime,types,bridge,capability}.ts`, `stub.ts`, `tools/`, `backends/{container,worker-shell,worker-javascript}/`
- `packages/dofs/src/` — `schema/{core,sync,migrations,index}.ts`, `fs/{writeFile,readFile,blobCache,resolveCache,writeBuffer,gc}.ts`, `sync/{changes,apply,coalesce,manifests,watermarks}.ts`, `provider.ts`, `bench/`
- `packages/rpc/src/` — `interface.ts`, `server.ts`, `client.ts`, `sync-driver.ts`, `debug.ts`
- `packages/computerd/src/` — `fuse/{driver,options,backend,vfs,tracer}.ts`, `cli/computerd.ts`, `shim/shim.ts`
- GitHub API: 25 issues, 57 PRs, 2 discussions, contributor and commit statistics
- npm registry publish timeline for `@cloudflare/computer`
- Comparison: `cloudflare/sandbox-sdk`, `cloudflare/capnweb`, `vercel-labs/just-bash`

Related prior research: `~/.mdx/research/kubernetes-sigs-agent-sandbox.md`, `~/.mdx/research/alp-2643-host-docker-sandboxing-runtime-matters.md`.

## Open questions

- **Is Worker Loader generally available?** The whole `worker-javascript` value proposition rests on minting Dynamic Worker isolates on demand. If that binding is gated or expensive at scale, two of the three backends are unavailable to most users and Computer collapses back to a container product.
- **Does Computer absorb `sandbox-sdk` or compete with it?** Both were pushed on the same day. Two overlapping Cloudflare sandbox products with different star counts and different maintainers is not a stable equilibrium.
- **What happens at hibernation?** Until `ctx.acceptWebSocket()` lands, every workspace with a live container pins a Durable Object isolate. That is the difference between a demo economics story and a product one, and it is unresolved.
- **Bus factor.** 577 of 611 commits from one engineer, on a preview package, in a repo that refuses external pull requests. There is no second maintainer visible in the history.

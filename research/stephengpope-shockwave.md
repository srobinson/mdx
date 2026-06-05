---
title: "stephengpope/shockwave review for littleorgans + agm/im/sm/rtm: borrow-primitives"
repo: https://github.com/stephengpope/shockwave
reviewed: 2026-06-01
grade: B
verdict: borrow-primitives
tags: [github-review, shockwave, stephengpope, typescript, electron, mit-license, littleorgans, agent-matters, identity-matters, session-matters, runtime-matters]
---

# stephengpope/shockwave

## 1. Stats

Shockwave is an Obsidian-style markdown editor with an embedded coding agent and free GitHub-repo sync, built as an Electron + Vite + React 19 desktop app (macOS/Windows/Linux). Created 2026-05-21, so roughly two weeks old at review. Single contributor (stephengpope, of "AI Architects"/No-Code Architects). 50 commits on `main` (shallow clone window), last push 2026-05-31, latest release v1.0.1 (2026-05-31). CI present: one GitHub Actions workflow (`.github/workflows/release.yml`) doing a three-OS matrix build that publishes electron-builder installers to a draft Release on `v*` tags. License: **MIT** — code is borrowable, not just ideas, so littleorgans could lift implementations directly with attribution. Languages: TypeScript dominant (~467KB), JavaScript (~96KB, mostly the link parser + correlator kept as `.js`), CSS (~60KB). ~10MB disk (dominated by a 513KB `package-lock.json`). Stack: CodeMirror 6 editor, chokidar watcher, `force-graph`, and the `@earendil-works/pi-coding-agent` / `pi-ai` SDK (v0.75.4) as the embedded agent engine — notably NOT Claude Code.

## 2. Grade

**B.** Above graphify (B) on engineering discipline and below superpowers (B+) on transferable depth. The CLAUDE.md invariant catalogue (10 numbered file/link invariants, mtime self-echo guard, parser-parity test) is staff-grade rigor for a two-week-old solo app, and several subsystems (rename correlator, credential broker, embedded-agent session keying, git-as-sync) are clean, single-purpose, and directly relevant to littleorgans. It does not reach B+ because the agent layer is a thin wrapper over a third-party SDK rather than original architecture, conflict handling is explicitly deferred, and there is no daemon/control-plane sophistication — it is a single-process desktop app.

This contradicts the NCA-Toolkit suspicion. Shockwave is **not** media/automation tooling. It is a local-first knowledge editor (a "second brain") with a baked-in agent — i.e. squarely in littleorgans territory, which makes it more relevant to Helioy than the suspected target would have been.

## 3. Primitives that transfer

1. **Credential broker as agent tools, secrets never leaving the trusted process** — `src/main/agentTokensExtension.ts:39-85`. Two tools (`list_agent_secrets` returns names+descriptions only; `get_agent_secret` returns one value by exact name) plus a `promptGuidelines` instruction to never echo a token. The agent can discover-then-fetch credentials without the renderer ever seeing them. Landing target: **identity-matters (im)** — this is exactly the IAM "what an agent may touch" surface, expressed as MCP-shaped tools rather than a config blob.
2. **Process-global bridge to keep decrypted secrets off disk** — `src/main/agentTokensExtension.ts:32-37,97-99`. The materialized extension is plain JS with zero imports; it reaches back to `global.__SHOCKWAVE_AGENT_TOKENS.getSecrets()` installed by main, deliberately avoiding writing decrypted secrets to disk or doing a module-resolution dance. Landing target: **identity-matters (im)** + **session-matters (sm)** — the daemons-are-MCP-servers invariant means smd/rtmd can broker credentials to in-isolate tools the same way instead of via env/files.
3. **OS-keychain secret encryption with prefix-tagged migration** — `src/main/main.ts:134-163`. `safeStorage` (Keychain/DPAPI/libsecret) with an `enc:v1:` prefix; idempotent encrypt (already-prefixed passes through, so merged plaintext+ciphertext objects do not double-encrypt) and transparent legacy-plaintext auto-migration. Landing target: **littleorgans** secret storage and **im** at-rest credential handling.
4. **Short-lived token mint, long-lived key stays server-side** — `src/main/main.ts:850-869`. The renderer never gets the AssemblyAI API key; main mints a 60s streaming token on demand. Landing target: **session-matters (sm)** — the smd control plane should hand out scoped, short-TTL session credentials rather than the durable secret, for any streaming/transport leg.
5. **Embedded-agent session keyed by (workspace, provider, model, apiKey, systemPrompt) with teardown-on-change** — `src/main/codingAgent.ts:25-93`. One live session at a time; any key field changing aborts and rebuilds, because the system prompt and auth are baked at session boot. Landing target: **runtime-matters (rtm)** — this is a kubelet-style "desired vs running" identity check on an agent process; the makeKey/teardown pattern is the seed of rtm's session liveness + restart-on-spec-change.
6. **Effective-skill resolution with global + per-workspace override, written to a settings file the agent reads at boot** — `src/main/skillLibrary.ts:123-160` and `src/main/codingAgent.ts:50-60`. `computeEffectivePaths` resolves `enabled|disabled|inherit` (workspace override wins, inherit falls back to global) and `writePiSettings` merges `skills`/`extensions` into the agent's `settings.json`. Landing target: **agent-matters (agm)** — this is the PodSpec analogue: an agent's skills/extensions definition assembled from layered config, materialized for the runtime.
7. **Filesystem SKILL.md library: one folder per skill, frontmatter `name`+`description`, drag-to-import with validation** — `src/main/skillLibrary.ts:30-110`. Identical SKILL.md contract to Helioy's own skills (YAML frontmatter, ≤64-char kebab name matching folder, description as the load signal). Import validates a root SKILL.md exists and rejects name collisions. Landing target: **agent-matters (agm)** — confirms a portable on-disk skill format and a clean import/validate path littleorgans can reuse.
8. **Inode-primary, content-hash-fallback rename correlator** — `src/main/renameCorrelator.js:28-148`. Pairs chokidar's `unlink(old)+add(new)` into a single `rename` event using inode first, content hash second (for FAT/SMB where ino is unreliable), with an 800ms grace window before committing a delete. Landing target: **transport-matters (tm)** / **runtime-matters (rtm)** — a reusable event-correlation primitive for any watcher that observes split lifecycle events and must reassemble identity.
9. **mtime self-echo guard for write/watch loops** — CLAUDE.md invariant #6 + `src/main/main.ts` fs write handlers. Store the file's real `stat.mtimeMs` (sub-ms float) on write; the watcher's later stat returns the identical value, so `evt.mtime > stored` is false on the self-echo and the editor does not reload mid-typing. Using `Date.now()` (integer ms) instead breaks it. Landing target: **runtime-matters (rtm)** / **transport-matters (tm)** — the canonical fix for any "my own write triggers my own watcher" feedback loop.
10. **Serial-tick git-as-sync engine with explicit status state machine** — `src/main/syncEngine.ts:41-246`. A never-overlapping tick (flush dirty buffers → commit → fetch → rebase if remote ahead → push if local ahead) driving a frozen 5-state machine (`disabled/idle/syncing/paused/error`), with a request/response "flush dirty editor tabs" bridge (token + 1s timeout) and graceful drain-before-quit. Landing target: **session-matters (sm)** sqlite-backed state + **transport-matters (tm)** — the status state machine and the serial-tick-with-flush-barrier pattern transfer; git itself is the wrong substrate for Helioy.

## 4. Does NOT transfer

1. **The `@earendil-works/pi-coding-agent` SDK dependency** (`package.json:44-45`, `codingAgent.ts:13-14`). Helioy's agents are Claude Code / Codex processes orchestrated by rtm/sm; adopting a third-party agent-loop SDK would duplicate the runtime Helioy already owns. Take the session-keying *shape*, not the engine.
2. **Git/GitHub as the sync and persistence substrate** (`syncEngine.ts`, `sync.ts`). Helioy state lives in sqlite + unix sockets across sm/rtm; commit-on-interval to a personal GitHub repo is the wrong durability and conflict model. Conflict handling is itself deferred here (`syncEngine.ts:17-19` — rebase pauses, no resume path), which underlines it is not a finished pattern.
3. **CodeMirror/Obsidian editor surface** — wiki-link index, backlinks panel, force-graph, live-preview decorations, daily notes, the basename-uniqueness simplification (`CLAUDE.md` Terminology + Invariants, `src/renderer/**`). This is an editor product; littleorgans is an agent console. Knowledge-graph linking belongs to a different Helioy axis (knowledge-matters / cm), not the platform family.
4. **Permissive-TS migration posture** (`tsconfig.json` no strict mode, `noImplicitAny:false`, `.js`→`.ts` extensionAlias, pervasive `any`). Explicitly a migration baseline, not a target; Helioy's Rust 2024 stack makes this irrelevant.
5. **Single-process desktop architecture.** No daemon, no control plane, no RBAC, no multi-agent orchestration. The 7-product family's whole point (smd/rtmd daemons-are-MCP-servers, controllers, choreography) has no analogue here.

## 5. Verdict

**borrow-primitives.** A handful of clean, MIT-licensed credential-broker, session-keying, and event-correlation primitives map directly onto im/agm/rtm/sm; the editor and git-sync bulk does not. Lift the patterns (and, where MIT attribution suffices, the small files), not the architecture.

## 6. Why

Shockwave is the closest external analogue yet to what littleorgans wants to be: a local-first knowledge surface with an agent living inside the trusted process, bring-your-own-key, skills-as-folders, secrets-as-tools. Its real value to Helioy is that a solo builder, in two weeks, converged on several of the same boundaries Helioy is formalizing into a 7-product platform — agent definition (agm/skills), agent identity and credential access (im/secret tools), agent runtime liveness (rtm/session keying), and a control-plane status machine (sm/sync engine). Seeing those boundaries drawn independently is design pressure: it validates the decomposition and donates concrete, tested implementations of the gnarly edges (the mtime self-echo guard and the rename correlator are the kind of bugs Helioy will hit and is better off borrowing a solved answer for).

## 7. How to apply

- **im credential model:** adopt the `list_*`/`get_*`-by-exact-name two-tool credential broker (`agentTokensExtension.ts:39-85`) as the shape for how Helioy agents request credentials through smd/rtmd's MCP surface; pair it with the never-echo `promptGuidelines` line. Keep the "names+descriptions discoverable, value fetched separately" split.
- **im/littleorgans at-rest secrets:** reuse the `enc:v1:`-prefixed, idempotent, auto-migrating `safeStorage` pattern (`main.ts:134-163`) wherever littleorgans stores user keys; the prefix-tag-for-migration trick is the reusable idea.
- **rtm session liveness:** model rtm's agent-process identity check on the `makeKey`/`teardown` pattern (`codingAgent.ts:25-93`) — define the spec fields that force a restart, rebuild on drift.
- **rtm/tm watcher correctness:** lift `renameCorrelator.js` near-verbatim (MIT) into any Helioy watcher that sees split lifecycle events, and adopt invariant #6's real-mtime self-echo guard as a documented rule.
- **agm skill resolution:** reuse `computeEffectivePaths` layered-override logic (`skillLibrary.ts:123-137`) for how an agent's effective skill set is assembled from global + scoped config.
- **sm control plane:** borrow the frozen 5-state status enum + serial-tick + flush-barrier shape (`syncEngine.ts:41-246`) for sm's sqlite-backed reconcile loop status, swapping git for the real substrate.

## 8. Artifact

This file is the artifact: `~/.mdx/research/stephengpope-shockwave.md`. Repo: https://github.com/stephengpope/shockwave (reviewed at v1.0.1, commit window of a depth-50 clone on 2026-06-01).

---
title: cmux (manaflow-ai) GitHub review — Ghostty-based macOS agent terminal
type: research
tags: [github-review, cmux, manaflow, runtime-matters, littleorgans, macos, swift, ghostty, agent-hooks, session-restore]
summary: Native Swift/AppKit macOS terminal wrapping libghostty with the most complete agent-hook installer surface I have seen. Strong primitives for runtime-matters; littleorgans drop-in is plausible but expensive.
status: active
source: github-researcher
confidence: medium
created: 2026-05-15
updated: 2026-05-15
---

## Stats

17.0k stars, created 2026-01-28, ~3.5 months old, very active (last push 2026-05-15). Primary language Swift; subprojects in Go (`daemon/remote/`), Zig (vendored ghostty + cmuxd), TypeScript (Next.js `web/` for cmux.com + cloud VM API). Single primary contributor visible at HEAD; project is run by Manaflow Inc. (founders Lawrence Chen, Austin Wang). License is GPL-3.0-or-later with paid commercial license (dual licensing); previously AGPL, relicensed in PR #2364. Packaging is **not Electron** — it is a native Xcode/AppKit app, signed and notarized via GitHub Actions, distributed as `.dmg` + Homebrew cask + Sparkle auto-update with a separate `nightly` channel. macOS-only, minimum macOS 14 (Sonoma). CI is multi-workflow: build-ghosttykit, ci, perf-activation, test-e2e (depot.dev), nightly. Vendors `manaflow-ai/ghostty` as a submodule (a fork of mitchellh/ghostty) plus `vendor/bonsplit` for split-pane primitives.

## Grade

**B+.** Anchors: B = graphify; B+ = superpowers; A− = notebooklm-py / mngr. cmux earns B+ because the agent-hook installer + env-allowlist + cross-tool config writer is the single most complete reference implementation of "wire AI coding agents into a host" I have read this year. Held back from A− by extreme file gigantism (TerminalController.swift 17.8k LOC, Workspace.swift 14.5k LOC, cmux.swift 24.3k LOC, GhosttyTerminalView.swift 13.8k LOC, CmuxConfig.swift 3.3k LOC), GPL-3.0 contamination risk for any code reuse, and macOS-only / Ghostty-locked surface. Quality of the bits that matter is high. Quality of the surfaces around them is workmanlike but not exemplary.

## Primitives that transfer

1. **`AgentHookDef` declarative installer matrix** (`CLI/CMUXCLI+AgentHookDefinitions.swift:7-322`). One Swift struct enumerates every coding agent (codex, opencode, pi, amp, cursor, gemini, rovodev, hermes-agent, copilot, codebuddy, claude, factory, qoder) with: config dir, config file, env-var override for that dir, binary name, hook file format (flat / nested-with-timeout / yaml variants), event-to-cmux-subcommand mapping, disable env var, hook marker string, and post-install side effects (e.g. `codexConfigToml` writes `codex_hooks = true`). Target: **runtime-matters**. This is exactly the shape `runtime-matters` needs for its catalog/adapter layer when registering Claude Code, Codex, OpenCode, Gemini, etc. as managed agents.

2. **`AgentLaunchEnvironmentPolicy.safeEnvironmentKeys` explicit allowlist** (`Packages/CMUXAgentLaunch/Sources/CMUXAgentLaunch/AgentLaunchEnvironmentPolicy.swift:26-`). A hard-coded whitelist of which env vars survive into resumed agent sessions, with inline comments calling out the keys that are secrets and intentionally excluded (e.g. `AMP_API_KEY`). Target: **runtime-matters**. Exactly the policy boundary needed when `runtime-matters` synthesizes per-agent runtime homes; do not inherit ambient env, gate by allowlist.

3. **`AgentLaunchSanitizer` per-agent argv normalizer** (`Packages/CMUXAgentLaunch/Sources/CMUXAgentLaunch/AgentLaunchSanitizer.swift:3-`). Per-agent `Policy` struct with `valueOptions`, `droppedOptions`, `nonRestorableCommands`, `resumeSubcommand`, etc., plus `preservedArguments(kind:args:)` that strips e.g. `amp threads continue <id>` to avoid double-resume. Target: **runtime-matters**. Direct fit for `runtime-matters` adapters that capture an agent invocation and want to replay it cleanly later.

4. **Generic hook session-store contract: `~/.cmuxterm/<agent>-hook-sessions.json`** (referenced via `sessionStoreSuffix` field in `AgentHookDef`, persistence in `Sources/RestorableAgentTypes.swift:100-`). Every supported agent maps its native session-id concept into one flat JSON store keyed by cmux session id. Target: **runtime-matters / transport-matters**. transport-matters can borrow the "stable our-id → vendor-id" mapping shape; runtime-matters can borrow the on-disk location convention.

5. **`cmux.json` user-extension schema with three action kinds** (`Sources/CmuxConfig.swift:10-866`). `actions` (palette entries with shortcuts), `commands` (workspace + shell), `surfaceTabBarButtons`, `notifications`, `vault`. Action types: `builtin`, `command`, `agent`, `workspaceCommand`, `actionReference`. Heavy validation, duplicate-alias detection, trust prompts via `CmuxActionTrust`. Target: **littleorgans**. This is exactly the surface a littleorgans chassis needs for power-user extension; the trust/confirm/icon plumbing is the polish-grade work I would otherwise have to write.

6. **`CmuxEventBus` + `CmuxEventStream` socket-fed subscription bus** (`Sources/CmuxEventBus.swift:1-470`, `Sources/CmuxEventStream.swift:1-119`). NSLock-guarded queue with `maxPendingEvents` overflow → close subscription policy, `accepts(_:)` filter by name/category, `next(timeout:)` blocking pop. Target: **transport-matters**. Pure-Swift, no Combine, no async/await dependency. Fits a "payload truth" lens — the bus is the transport, the events are the payloads. Borrow the overflow-closes-subscription semantics.

7. **Unix-domain-socket control plane on `TerminalController`** (`Sources/TerminalController.swift:1061-1143` and `Sources/CmuxSocketEventMapper.swift`). App listens on `~/.cmux-debug-<tag>.sock` (debug) / production socket; CLI relays commands. Telemetry path is required off-main (see CLAUDE.md `Socket command threading policy`). Target: **littleorgans**. If littleorgans hosts a long-running daemon, this is the canonical macOS pattern — UDS + per-command async dispatch + explicit focus-intent allowlist.

8. **`SessionPersistencePolicy` + `SessionTabManagerSnapshot` versioned snapshot** (`Sources/SessionPersistence.swift:9-513`, `Sources/TabManager.swift:7453-7530`). Restorable workspaces are filtered by `isRestorableInSessionSnapshot`, truncated to `maxWorkspacesPerWindow`, scrollback truncated to `maxScrollbackLinesPerTerminal` and `maxScrollbackCharactersPerTerminal`. Restore replaces workspace graph atomically to avoid empty-`@Published`-emission frozen states (#399). Target: **littleorgans**. The policy enum + filter-then-truncate pattern is the right shape for any future cross-session state snapshot.

9. **`CMUXWorkstream` package — agent-facing work item abstraction** (`Packages/CMUXWorkstream/Sources/CMUXWorkstream/{WorkstreamItem,WorkstreamStore,WorkstreamEvent,WorkstreamAction,WorkstreamPayload,WorkstreamTransport}.swift`). A typed item store separated from the main app, with its own event bus and persistence. Target: **transport-matters**. The shape — `Item`, `Source`, `Kind`, `Payload`, `Action`, `Event`, `Transport`, `Persistence`, `Context`, `Store` — is a clean payload-truth/transport-insight decomposition and worth studying before finalizing the transport-matters object model.

10. **Per-tag isolated debug build** (`scripts/reload.sh --tag <slug>`, `CLAUDE.md:13-126`). One source tree produces N independently-runnable Debug apps with isolated bundle ID, socket path, derived-data path, debug log. Target: **runtime-matters / littleorgans dev loop**. This is the right primitive for a desktop dev loop where multiple branches need to coexist with multiple sockets. Helioy worktree work could borrow this.

11. **Localized-strings hard rule + xcstrings catalog** (`CLAUDE.md:234`, `Resources/Localizable.xcstrings`). Every user-facing string goes through `String(localized: "key", defaultValue: "English")`. Target: **littleorgans**. If littleorgans ever ships a product UI, copy this rule wholesale; the discipline pays back.

12. **Snapshot-boundary list-view rule** (`CLAUDE.md:236`). In any SwiftUI body containing `LazyVStack` / `LazyHStack` / `List` / `ForEach`, no view below the boundary may hold an `ObservableObject` / `@Observable` reference; rows take immutable value snapshots + closure action bundles. Documented after a real 100% CPU spin loop (#2586). Target: **littleorgans**. Hard-won SwiftUI doctrine that any SwiftUI-based littleorgans surface needs from day one.

## Does NOT transfer

1. **GPL-3.0 / formerly AGPL.** Copying source verbatim into any Helioy component carrying a more permissive license would force the whole product to GPL. Reading-for-shape is fine; copy-paste is not. This is the single biggest constraint on "borrow primitives directly."

2. **17k-LOC monolithic files.** TerminalController.swift, Workspace.swift, GhosttyTerminalView.swift, cmux.swift sit at 13–24k lines each. Helioy's hard refactor threshold is 700. Any direct adoption would require breaking these up first; the cost of refactoring someone else's monolith almost always exceeds writing it fresh.

3. **libghostty lock-in.** Terminal rendering, scrollback truncation, OSC notification dispatch all live inside the Ghostty submodule (manaflow-ai/ghostty fork). Inheriting the rendering layer means inheriting a Zig submodule and a forked terminal emulator. Heavyweight dependency for a project not yet sure it needs a terminal at all.

4. **Bonsplit + AppKit-portal hit-testing.** The split-pane system is its own vendored package with a documented typing-latency contract (`TerminalWindowPortal.swift`, `TerminalSurface.forceRefresh()`). Beautiful engineering, but it is the wrong fit unless littleorgans is fundamentally a tiling terminal.

5. **macOS-only, Sonoma+ floor.** Swift 6, macOS 14 minimum. No Linux, no Windows. If littleorgans is meant to be cross-platform — even eventually — this rules out adoption as the chassis.

6. **Vendored Stack Auth + Sparkle + AppKit menu bar.** The shell is heavily integrated with macOS-native concerns (Sparkle auto-update, status bar item, AppleScript support, dock tile plugin, services, Cmd-click file URLs). These bind the chassis tightly to macOS conventions.

7. **Cloud VM control plane in `web/`.** The Next.js + Drizzle + AWS Aurora + Stack Auth + Vercel route handlers + Effect-typed services is a real product backend, not a chassis primitive. Useful pattern reference for `web/services/**` Effect modelling but unrelated to runtime-matters scope.

8. **24k-line `cmux.swift` CLI.** The CLI dispatch is one of the most extreme monoliths in the repo. Useful as a worked example of "every agent integration in one place," but not a borrowable structure.

## Verdict

- **runtime-matters: borrow-primitives.** Read `AgentHookDef`, `AgentLaunchEnvironmentPolicy.safeEnvironmentKeys`, `AgentLaunchSanitizer`, `~/.cmuxterm/<agent>-hook-sessions.json` shape. Reimplement clean in the runtime-matters catalog/adapter layer. Do not import code — GPL-3.0 + Swift + 17k-LOC files all argue against direct reuse.

- **littleorgans (drop-in chassis): inspiration.** Not build-on-top. Reasons: GPL, Ghostty submodule lock-in, macOS-only floor, monolithic Swift files. Littleorgans should be built on a thinner base. Borrow the `cmux.json` schema doctrine, the trust-prompts pattern, the snapshot-boundary SwiftUI rule, the per-tag isolated dev build idea, and the localized-strings discipline. Read the source for shape, write fresh.

## Why

cmux solves a different problem than littleorgans. cmux is a terminal-first orchestrator for AI coding agents where the terminal pane is the unit of agency. littleorgans is a chassis for cognitive organs where the unit of agency is a typed runtime (context-matters, transport-matters, runtime-matters). The overlap is the wiring layer: how the host installs hooks into Claude Code / Codex / etc., what env vars survive a resume, how a captured launch is sanitized and replayed. cmux is unusually thorough at this wiring layer because it has to support a dozen agents across three hook formats with consistent UX. That thoroughness is exactly what runtime-matters needs to encode. Outside that wiring layer, the surface area mismatch is large: cmux is a Ghostty fork wrapped in AppKit; littleorgans is whatever it needs to be. Borrowing the chassis would mean owning the chassis's whole worldview, and the chassis's whole worldview includes 60k+ LOC of split-pane management and macOS-specific notification rings. Not worth it.

## How to apply

1. **runtime-matters catalog work.** When you next sit down to define the schema for runtime-matters' agent catalog entries (the YAML/JSON that registers Claude Code, Codex, OpenCode, etc.), open `CLI/CMUXCLI+AgentHookDefinitions.swift` side by side. Copy the field set into a Helioy-native typed struct: `name`, `display_name`, `config_dir`, `config_dir_env_override`, `config_file`, `binary_name`, `hook_format` (enum), `events` (list of `{agent_event, helioy_subcommand}`), `disable_env_var`, `feed_hook_events`, `post_install_action`. Translate the constants exactly. Files-to-touch: helioy-tools `runtime-matters` package, the catalog source of truth.

2. **runtime-matters env policy.** Before writing the resume / env-inheritance code for runtime-matters adapters, copy `AgentLaunchEnvironmentPolicy.safeEnvironmentKeys` into a Helioy-native allowlist with the same inline-comment doctrine ("intentionally excluded because secret"). Files-to-touch: runtime-matters adapter for each agent, plus the shared `env_policy.rs`/`.ts`/`.py` equivalent.

3. **cmux.json schema doctrine.** When littleorgans gains a user-extension config surface, model it on `cmux.json`: typed actions, named commands, palette opt-in, shortcut bindings, trust prompts on first use of a command, icon support, `actionReference` indirection. Files-to-touch: future `~/.config/littleorgans/littleorgans.json` schema doc + validator.

4. **SwiftUI doctrine for future UI.** If littleorgans ever ships a SwiftUI surface, paste the `CLAUDE.md:236` snapshot-boundary rule into the project AGENTS.md verbatim. It is hard-won from a real CPU spin incident, and getting it right costs nothing if you know it from day one.

5. **Avoid the monolith trap.** Read `cmux.swift` (24k LOC) and `TerminalController.swift` (17k LOC) once for shape, then never again. They are object lessons in what happens when a project grows fast without a refactor threshold. Helioy's 700-line rule is the right inoculation.

## Artifact

`~/.mdx/research/manaflow-ai-cmux.md`

---
title: "imbue-ai/mngr: senior-engineering review through the Helioy lens"
type: research
tags: [orchestrator, agents, plugins, pluggy, tmux, ssh, modal, helioy, nancyr, helioy-bus]
summary: "imbue-ai/mngr is a Unix-style multi-agent CLI built on tmux+SSH+git, with a strong pluggy plugin model, JSONL discovery events, and CEL filtering. Grade A-. Three primitives transfer cleanly to nancyr/helioy-bus."
status: active
source: github-researcher
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

# imbue-ai/mngr review

## 1. Snapshot

| Signal | Value |
|---|---|
| Stars | 331 |
| Forks | 35 |
| Created | 2026-01-19 (3 months old) |
| Last push | 2026-04-27 (today) |
| Default branch | main |
| Disk usage | 39.5 MB packed, 33 MB checkout |
| License | MIT (LICENSE on disk; GitHub reports "Other") |
| Contributors | 15 total; top two own 90% of commits: joshalbrecht 4712, evgunter 4458, qi-imbue 707, claude 199, hynek-urban 95 |
| Total commits | 10,360 |
| Languages (bytes) | Python 9.11M, Shell 218K, TypeScript 114K, JS 119K, HTML 52K, CSS 32K, HCL 1.7K |
| Python files | 855 |
| Test files | 442 (52% of .py) |
| Tracked test durations | 7,929 entries in `.test_durations` |
| Coverage floors | per-package, e.g. `imbue_common` 90%, `concurrency_group` 90%, `mngr` core 80%, `mngr_recursive` 85%, `mngr_claude` 30%, `mngr_schedule` 75% |
| CI | GitHub Actions: `ci.yml`, `vet.yml`, `publish.yml`, `publish-tombstones.yml`. Tests fan out across Modal sandboxes via the external `offload` Rust tool. |
| Pre-commit | `.pre-commit-config.yaml` |
| PyPI | `imbue-mngr` published; install script `scripts/install.sh` |
| Top-level layout | `libs/` (26 packages), `apps/` (4 incl. `minds` desktop), `scripts/` (47 ops scripts), `specs/` (24 design specs), `style_guide.md` (75K), `CLAUDE.md` (15.6K), `justfile` (12K) |

The project is mid-stage and well-funded in engineering hours: 10K commits in 3 months, two dominant authors plus a Claude bot committer (199 commits), tight CI with per-package coverage gates and a dedicated test-fanout tool.

## 2. What it does

`mngr` is a CLI that creates, lists, messages, snapshots, clones and destroys long-running coding agents (Claude Code, Codex, OpenCode, Pi, custom commands) across local, Docker, SSH, and Modal hosts. The wire format is dead simple: an "agent" is any Unix process running in window 0 of a tmux session named `mngr-<agent-id>`, with a state directory under `$MNGR_HOST_DIR/agents/<id>/` containing `data.json`, `events/*.jsonl`, and `activity/*` files. Everything else (lifecycle, discovery, idle detection, snapshots, message delivery, web terminals) is layered on top of those filesystem conventions.

Pitch: it is `git` for agents, with pluggy as the plugin spine and tmux+SSH+JSONL as the on-wire protocol.

## 3. Architecture

Load-bearing modules under `libs/mngr/imbue/mngr/`:

- `interfaces/` (3,717 LOC across `agent.py`, `host.py`, `provider_instance.py`, `data_types.py`, `volume.py`, `provider_backend.py`). Pure abstract layer. `AgentInterface` (`interfaces/agent.py:39`) is generic over `AgentConfigT`; `HostInterface` and `OnlineHostInterface` (`interfaces/host.py:65`, `:888 LOC total`) define every remote primitive (`execute_command`, `read_file`, `copy_directory`, `discover_agents`). All other code talks through these interfaces.
- `plugins/hookspecs.py` (532 LOC). 23+ pluggy hookspecs: `register_provider_backend`, `register_agent_type`, `register_cli_options`, `register_cli_commands`, plus lifecycle hooks (`on_before_host_create`, `on_agent_created`, `on_before_provisioning`, `override_command_options`, `on_load_config`, `on_error`, `on_shutdown`).
- `plugin_catalog.py` (251 LOC). Static catalog with `SignalCheck` subclasses (`ClaudeSignalCheck` runs `claude --version`, `ModalSignalCheck` checks `~/.modal.toml`) that the install wizard uses to auto-recommend plugins.
- `api/` (40+ files). Each top-level command has a thin module: `create.py`, `list.py`, `connect.py`, `message.py`, `exec.py`, `clone.py`, `gc.py`, `pull.py`, `push.py`, `events.py`, `discovery_events.py`, `find.py`, `agent_addr.py`. The CLI in `cli/` is mostly click wiring; the API modules contain the logic and are independently importable.
- `api/discovery_events.py` (753 LOC). JSONL-backed event log under `<host_dir>/events/mngr/discovery/events.jsonl` with a strongly typed envelope hierarchy: `AgentDiscoveryEvent`, `HostDiscoveryEvent`, `AgentDestroyedEvent`, `HostDestroyedEvent`, `FullDiscoverySnapshotEvent`, `HostSSHInfoEvent`, all extending `EventEnvelope` from `imbue_common`.
- `api/events.py` (1,230 LOC). Streams events from one or many JSONL sources via `pygtail`-based tail, deduplicates by event id, scans for new rotated files, multiplexes across an `EventsTarget`. Used by `mngr events`.
- `api/find.py` (626 LOC) and `api/agent_addr.py`. The `AgentAddress` parser (`api/agent_addr.py:25`) turns `"foo@myhost.modal"` into `(agent_name, host_name, provider_name)`; `find.py` resolves to live `AgentInterface`/`OnlineHostInterface` instances and ensures the host/agent is started when needed.
- `utils/cel_utils.py` (158 LOC). Compiles CEL expressions via `celpy` for `--include-filter`/`--exclude-filter` flags. Used uniformly in `list`, `message`, `exec`, `events` to filter agents by labels, host metadata, lifecycle state.
- `agents/base_agent.py` (862 LOC) and `agents/base_headless_agent.py` (157 LOC). The default agent body. `base_agent.py` does tmux paste-buffer messaging with paste-indicator detection (`_check_paste_content` at `agents/base_agent.py:60`), readiness polling, lifecycle classification.
- `hosts/host.py` (3,207 LOC). Concrete `Host` and `OnlineHost` implementations using `pyinfra` connectors and `paramiko` for SSH; tenacity for retries; `pyinfra` for both local and SSH transport so the same code path runs everywhere.
- `concurrency_group/` (sibling lib, 661 LOC core). A context-manager that owns child threads and processes, propagates shutdowns, and raises if any tracked strand has failed. Used pervasively (e.g. `api/message.py:90` fan-out across hosts via `ConcurrencyGroupExecutor`).

Plugins live as separate libs that ship as PyPI packages (`mngr_claude`, `mngr_modal`, `mngr_kanpan` TUI, `mngr_recursive`, `mngr_schedule`, `mngr_notifications`, `mngr_pi_coding`, `mngr_opencode`, `mngr_tutor`, `mngr_vps_docker`, `mngr_vultr`, `mngr_pair`, `mngr_tmr`, `mngr_wait`, `mngr_lima`, `mngr_ttyd`, `mngr_file`). Provider backends and agent types are registered through pluggy entry points; CLI options are registered per-command via `register_cli_options`.

## 4. Engineering signals

- Type discipline. Heavy use of pydantic `FrozenModel`/`MutableModel`. New-type wrappers for ids/names (`AgentId`, `HostId`, `AgentName`, `HostName`, `ProviderInstanceName`) defined in `primitives.py:1-463`. CLAUDE.md line 50 forbids `TYPE_CHECKING` without explicit permission.
- Test discipline. Three named test tiers: unit (`*_test.py`), integration (`test_*.py`), acceptance (`@pytest.mark.acceptance`), release (`@pytest.mark.release`). Test fanout via Modal sandboxes through the external `offload` tool (`cargo install offload@0.6.2`). Per-package coverage gates committed in `pyproject.toml`.
- Ratchets. `test_meta_ratchets.py` (15K, root) and `test_ratchets.py` per package enforce monotonically decreasing counts of anti-patterns (e.g. raising built-in exceptions, monkeypatch.setattr). CLAUDE.md lines 82-93 explicitly forbid evading them by regex tweak. This is a maturity signal.
- Style guide. `style_guide.md` is 75K bytes. That is unusual depth for a 3-month-old repo; suggests imbue is rolling existing internal practice into mngr.
- Hot spots. `libs/mngr_claude/imbue/mngr_claude/plugin_test.py` (3,834 lines) and `plugin.py` (2,588 lines) are by far the largest files. The Claude plugin carries Claude-specific config sync, settings.json mutation, hook injection, onboarding-dialog dismissal, and credential management; this is the integration surface that pays for the abstraction.
- Abstraction tax. `interfaces/host.py` is 888 lines and `OnlineHostInterface` exposes ~50 abstract methods. The result is that local/Docker/SSH/Modal share a single code path, but the cost is steep: any new provider must implement the full contract. The mock provider (`providers/mock_provider_test.py`) exists partly to keep this honest.
- Dead code / over-build risk. `future_specs/` has 24 spec docs marked `[future]`. The repo is honest about what is shipped versus designed; very little speculative code in the tree.
- Single-author vs team. Two clear leads (joshalbrecht, evgunter) plus a Claude bot account committing 199 times. This is a small team, not a single author. CLAUDE.md mentions internal slash commands `/autofix`, `/verify-conversation`, `/writing-ratchet-tests` that suggest tight agent-assisted dev loop.
- Docs. `libs/mngr/docs/concepts/` has 13 concept docs covering `agents`, `hosts`, `plugins`, `provisioning`, `idle_detection`, `permissions`, `snapshot`, `providers`, `provider_backends`, `agent_types`, `api`, `modal_usage`, `environment_variables`. Plus per-command docs (`docs/commands/{primary,secondary,generic,aliases}/`) and per-plugin docs (`docs/core_plugins/{agents,providers}/`). README is 400 lines with mermaid diagrams.
- Release cadence. `pushedAt` 2026-04-27T05:53:09Z; the most recent commit at clone time was a port-forwarding fix and a latchkey shim. Active daily.

## 5. What transfers to Helioy

Three concrete primitives. Each is small enough to lift without dragging the whole framework.

### Lift 1: per-agent JSONL discovery-event log with typed envelopes

Source: `libs/mngr/imbue/mngr/api/discovery_events.py:43-95` defines `DiscoveryEventType` and the six event subclasses; `:97-110` defines the on-disk path `<host_dir>/events/mngr/discovery/events.jsonl`. Streaming consumer at `libs/mngr/imbue/mngr/api/events.py:1-150` uses `pygtail` to tail the JSONL with deduplication by `event_id` and source-rotation tracking (`_AllEventsStreamState` at `api/events.py:96-115`).

Why it transfers. helioy-bus already has an inbox-as-files design (`server/services/message.py`) and registry (`server/services/agent_registry.py`); what is missing is a typed, append-only event stream that other agents and the bus itself can subscribe to without polling SQLite. Mngr's pattern, JSONL with rotation plus pygtail, gives near-realtime fanout on top of the filesystem you already use.

Land: helioy-bus, new module `server/services/events.py`. Concrete plan:
1. Define `EventEnvelope` (id, ts, source, type, payload) using pydantic.
2. Append events to `~/.helioy/bus/events/<source>/events.jsonl` on every register/send/heartbeat.
3. Expose an `events_stream` MCP tool that tails one or many sources and dedups by id.
4. nancyr's `nancy-monitor` crate becomes a consumer of this stream rather than re-implementing tail logic.

Cost estimate: ~250 LOC Python, plus a Rust tail adapter in `nancy-monitor`.

### Lift 2: CEL filter expressions for agent selection

Source: `libs/mngr/imbue/mngr/utils/cel_utils.py:13-43` (`compile_cel_filters`) and `:60-79` (`build_cel_context`, `apply_cel_filters_to_context`). Used uniformly by `mngr message --include "labels.project == 'mngr'"`, `mngr list --include "host.provider == 'modal'"`, `mngr exec` and `mngr events`. Fanout call sites: `api/message.py:50` and `api/exec.py`.

Why it transfers. helioy-bus addressing today is direct (`to="agent-id"`), role-based (`to="role:backend-engineer"`), or broadcast (`to="*"`). Adding CEL closes the gap to "send to every agent on this project where status == waiting" without inventing a new query language. `celpy` is well maintained and the integration is ~20 lines.

Land: helioy-bus, `server/services/agent_registry.py`. Concrete plan:
1. Extend `send_message` to accept an optional `selector` field that is a CEL expression.
2. Build CEL context from each registered agent's metadata (id, role, project, cwd, lifecycle).
3. Compile once per send, evaluate per agent, fan out via existing nudge path.

Cost estimate: ~80 LOC plus a `celpy` dependency.

### Lift 3: pluggy-based plugin protocol with signal-check auto-recommendation

Source: `libs/mngr/imbue/mngr/plugins/hookspecs.py:1-532` (every hook is a `@hookspec`), `libs/mngr/imbue/mngr/plugin_catalog.py:32-100` (`SignalCheck` and `ClaudeSignalCheck`/`ModalSignalCheck`/`PiSignalCheck`/`OpenCodeSignalCheck`), and `libs/mngr/imbue/mngr/agents/agent_registry.py:39-58` (`load_agents_from_plugins`). The plugin model handles four extension surfaces in one framework: agent types, provider backends, CLI commands, CLI options.

Why it transfers. nancyr is a Rust binary today, but the plugin discoverability problem still applies: which Claude-Code plugins are installed, which are usable, what should the install wizard recommend. helioy-plugins as a Claude Code plugin can borrow the catalog idea directly. helioy-bus's `runtimes/` (currently `claude.py`, `codex.py`) reads exactly like mngr's agent-type plugins and would benefit from a formal hookspec rather than ad-hoc subclassing.

Land: helioy-bus `server/runtimes/`, helioy-plugins. Concrete plan:
1. Introduce a small pluggy-style hookspec for runtimes (`register_runtime() -> (name, RuntimeClass, ConfigClass)`) inside helioy-bus. Replace the hardcoded `claude.py`/`codex.py` import with entry-point discovery.
2. Add a `SignalCheck`-style catalog so `helioy install` can detect what is on the system (claude CLI, codex CLI, opencode CLI, modal credentials) and only suggest the relevant runtimes/plugins.
3. nancyr-side: keep Rust, but adopt the same `entry-point + signal` JSON contract so a single catalog file drives both ecosystems.

Cost estimate: ~150 LOC across helioy-bus and helioy-plugins; mostly mechanical.

### Honourable mentions

- `concurrency_group/concurrency_group.py:84-661` is a context-manager that tracks every thread/process spawned inside it and raises if any sibling has failed. Cleaner than ad-hoc `threading.Thread` lists and useful for nancyr's supervisor loop, though Rust has `tokio::task::JoinSet` already.
- `interfaces/host.py:65-180` shows the right shape for a portable host abstraction (local, docker, ssh, modal all behind one API). If nancyr ever supports remote claude execution, copy this taxonomy.
- The `test_ratchets.py` pattern (monotonically decreasing anti-pattern counts) is worth adopting in nancyr's CI; it is a low-ceremony way to retire bad patterns without big-bang refactors.

## 6. What does NOT transfer

- The 26-package monorepo split. mngr ships `mngr_kanpan` (TUI), `mngr_tmr`, `mngr_vultr`, `mngr_lima`, `mngr_ttyd`, etc. as separate libs because imbue runs a real Modal-based fleet for paying users. Helioy is single-user; do not copy this fan-out.
- The `minds/` Electron desktop app. 350+ KB of TS/CSS/HTML for a tabbed workspace UI. Off-mission for nancyr (terminal-native) and helioy-bus (CLI MCP).
- Cloud-provider primitives (Modal sandbox lifecycle, Vultr provisioning, Lima image baking, packer scripts, terraform via HCL). Helioy runs locally and on the user's own machines; the SSH transport in `hosts/host.py` is over-engineered for that case.
- Snapshot/clone semantics. Mngr's "fork an agent's container" depends on Docker/Modal snapshot APIs. Helioy's analogue is "fork a worktree", which is `git worktree add` and does not need this machinery.
- The `agents/base_agent.py` tmux paste-buffer messaging logic (paste-indicator detection, normalized fuzzy-match on pane content). helioy-bus already has a working tmux nudge path; do not graft a second one.
- pyinfra. `hosts/host.py` uses pyinfra connectors to abstract local vs SSH. Adds a heavy transitive dep tree; the native helioy-bus filesystem-as-bus approach is simpler for the local-first use case.
- The 75K-byte `style_guide.md`. Useful as a reference for "what a hardcore style guide looks like", but not as something to import wholesale.

## 7. Calibrated grade

**Grade: A-.** This is the highest-signal repo I have reviewed this month, narrowly behind notebooklm-py only because notebooklm-py was a tighter scope match; mngr is broader and gives more transferable primitives at the architectural level. Justification: 10,360 commits in 3 months by a real team, per-package coverage gates committed in pyproject.toml (`mngr` 80%, `imbue_common` 90%, `concurrency_group` 90%), 442 test files against 855 source files, ratchet-based anti-pattern enforcement, a 532-line typed pluggy hookspec, a CEL-based filter that is one Python file (158 lines), and a JSONL discovery-event log that solves the same problem helioy-bus is approaching from the SQLite side. The architecture choices are conservative-to-orthodox (pluggy, pydantic, click, pyinfra, paramiko, tenacity, celpy, pygtail, loguru) which is exactly what a senior reviewer wants to see; nothing is bespoke that did not need to be. The grade is held off A by two factors: (1) imbue's monorepo and Electron desktop app are off-mission for Helioy, so the surface that transfers is narrower than the LOC count suggests; (2) the host abstraction is heavyweight (888 lines, ~50 abstract methods on `OnlineHostInterface`) and importing that taxonomy wholesale would be a bigger commitment than nancyr currently warrants.

## Sources Consulted

- `README.md`, `CLAUDE.md`, `style_guide.md` (root)
- `libs/mngr/docs/concepts/{agents,plugins,snapshot,idle_detection}.md`
- `libs/mngr/imbue/mngr/{primitives,plugin_catalog}.py`
- `libs/mngr/imbue/mngr/interfaces/{agent,host,data_types}.py`
- `libs/mngr/imbue/mngr/plugins/hookspecs.py`
- `libs/mngr/imbue/mngr/api/{discovery_events,events,message,exec,find,agent_addr,connect,data_types}.py`
- `libs/mngr/imbue/mngr/utils/cel_utils.py`
- `libs/mngr/imbue/mngr/agents/{base_agent,agent_registry}.py`
- `libs/mngr/imbue/mngr/hosts/{host,common,tmux}.py`
- `libs/concurrency_group/imbue/concurrency_group/concurrency_group.py`
- `libs/mngr_claude/imbue/mngr_claude/plugin.py` (head only, file is 2,588 lines)
- `.github/workflows/ci.yml`, root `pyproject.toml`, all `libs/*/pyproject.toml` coverage entries
- gh API: stargazers, contributors, commit count, languages, licenseInfo

## Open Questions

- How does mngr handle event-log retention across rotation when an agent is offline for days? `events.py:_AllEventsStreamState` tracks rotated files, but the gc policy was not examined.
- The `mngr clone` flow snapshots a remote agent and creates a new one from the snapshot. Worth a deeper look if Helioy ever wants "fork this agent's session" beyond `git worktree`.
- `libs/mngr_recursive` (recursive agent spawning). Not examined here; relevant if nancyr grows hierarchical sub-agent support.
- The `offload` Rust crate (`cargo install offload@0.6.2`) used for the test fanout. May be reusable as a generic test-distribution primitive for nancyr.

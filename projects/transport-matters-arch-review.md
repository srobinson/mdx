# Transport Matters — Architecture Review (3 questions)

Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
Date: 2026-05-28
Status: orchestrator's draft conclusions — to be stress-tested by the warroom, then turned into an execution plan.

These are conclusions from a first-pass investigation. **Do not trust them. Verify every claim against the live code** (cite file:line), find at least one substantive issue per claim or positively justify "confirmed, no issues," and flag anything missing, wrong, or risky.

---

## Layer model (shared context)

Three orthogonal layers, all decoupled:

- **Harness** (`api/src/transport_matters/harnesses/__init__.py`) — static `HarnessDescriptor` dataclasses describing how to *launch + proxy* a CLI client (claude, codex). Fields: `proxy_mode` (REVERSE|EXPLICIT), `trust_requirement`, `shell_environment_policy`, `pass_through_policy`, `HarnessCapabilities` flags.
- **Adapter** (`api/src/transport_matters/adapters/`) — `ProviderAdapter` ABC (`base.py`); registry list in `__init__.py` selected first-match-wins by `matches(flow)` on request path/host. Translates a provider *wire format* <-> canonical IR. Anthropic = one 507-LOC file; Codex wire/transport sprawls across `codex/` (~11.6k LOC).
- **Lock / workspace** (`lock.py`) — `WorkspaceLock` (fcntl.flock) enforces one live instance per workspace, workspace = hash of resolved CWD.

Harness (launch) and adapter (wire-format detection) are fully decoupled: `get_adapter(flow)` has zero knowledge of which harness launched.

---

## Q1 — One agent per CWD: why, and multi-in-dir cost

**Conclusion:** the only hard gate is the single `fcntl.flock` in `lock.py:83`. It exists to stop two instances clobbering shared per-workspace state keyed by `{slug}/{hash}` of the resolved CWD (`workspace.py:62-75`):
- shared `manifest.json` — one PID/ports record (`manifest.py:32-63`)
- shared `index.jsonl` + flat exchange dirs (`disk_layout.py:54-83`)

Ports are NOT a real blocker: `allocate_port_pair` (`ports.py:41-69`) gives kernel-assigned free pairs; only explicitly pinned ports collide.

`run_id` already threads end to end (set at `launch_runtime.py:270`, on the manifest `manifest.py:45`, filtered in `read_index(run_id=...)` `disk.py:261`, surfaced on `/api/v1/meta` and `/exchanges`). The data model is already instance-aware. Still singleton: the lock, the manifest filename, the storage root — none have a `run_id` path level.

Prior art: `feat/multi-instance`, `feat/multi-instance-phase2`, `feat/run-id-boundary` are already merged into main; they built the lock + run_id primitives and deliberately stopped at one-live-per-dir.

**Proposed keystone:** extend the shipped `run_id` boundary down to manifest + storage paths (`{hash}/{run_id}/`), make the manifest a list (`read_all` already globs), decide web UI per-instance vs aggregated. Extension, not rewrite.

**Verify:** Is the flock truly the only gate? Are there other singletons (a fixed socket, a pidfile, a singleton in the web/addon process, `get_settings()` process-global state) that would break two same-dir instances even after the run_id split? Is per-instance vs aggregated UI a real fork in the road? What is the actual blast radius of the run_id-down-to-storage change?

---

## Q2 — Forward-compat with provider API/version changes

**Conclusion (split verdict):**

- **Responses: forward-compatible by accident.** Never mutated, only recorded (`addon_handlers.py:286-303`). Client always gets upstream bytes. New fields / SSE events can't break a response; lossy parse only degrades our recorded copy.
- **Requests: the exposure.** Always reserialized from IR even when nothing was edited (`addon_handlers.py:135` HTTP, `:242` Codex WS). New *top-level* request key survives via `provider_extras` (`anthropic.py:71-73`). New field *nested inside* a modeled struct is silently DROPPED, because `Message`, `ToolUseBlock`, `SamplingParams`, `ImageBlock` have no overflow dict (system/tools/thinking do).

Patterns present: `UnknownBlock` passthrough (both providers), top-level `provider_extras`, Codex structural overlay `input_item_raw` (`request_parser.py:63-64`, `preserved_raw.py:130-161`) — the most forward-compat mechanism in the repo. Missing: raw-body passthrough when unmodified, `extra="allow"` on IR (all models default `extra="ignore"`), per-struct overflow on the four unprotected models, version/beta header gating (headers currently pass through untouched — which is fine).

**Proposed keystones (low effort, high payoff):**
1. Raw-body passthrough when no override fired (if curated IR == captured IR, forward original request bytes). Biggest single win; makes unmodified traffic byte-faithful regardless of wire changes.
2. Add `provider_data` overflow to `Message`, `ToolUseBlock`, `SamplingParams`, `ImageBlock`; populate + restore in both adapters.
3. Lift Codex's structural-overlay (`input_item_raw`) into the Anthropic adapter for the edited path.

**Verify:** Is the "always reserialize" claim true for BOTH transports? Is there really no unmodified-passthrough today? Does `curated_ir == ir` equality even hold for frozen pydantic models (so the passthrough guard is implementable cheaply)? Any correctness traps in passthrough (e.g. content-length, gzip, token-counting redaction at `counting.py:35`)? Is overflow-everywhere better than a blanket raw-overlay approach?

---

## Q3 — Onboarding Gemini CLI + OpenCode CLI, and layout

**Conclusion:** cost today is 4-5 central hand-edited files per CLI plus 1-2 new files. Merge-conflict surface: `cli/__init__.py`, `cli/help.py`, `adapters/__init__.py`, `harnesses/__init__.py`; a WebSocket provider also drags in `addon.py` + `addon_handlers.py`.

Critical finding: **the `HarnessDescriptor` layer is decorative.** Its data (`proxy_mode`, `trust_requirement`, `shell_environment_policy`) is read only by the read-only meta API (`meta.py:109-111`). The launch path (`cli/`, `start_cmd.py`, `codex_cmd.py`) re-hardcodes proxy mode, CA bootstrap, and shell-env excludes with Codex-named constants. Adding a descriptor auto-creates nothing.

Healthy: Codex's 11.6k LOC is essential (WebSocket turn reconstruction over a persistent socket); its adapter is only 45 LOC. Harness/adapter fully decoupled.

Reuse story: OpenCode speaking `/v1/messages` reuses `AnthropicAdapter` as-is (harness + CLI command only). Gemini needs a new HTTP adapter (`matches()` on `:generateContent`, ~Anthropic-sized, no WebSocket).

**Proposed keystone:** make descriptors load-bearing. Adopt `providers/<name>/` co-locating descriptor + launch + adapter (+ transport for WS), one registry auto-discovering descriptors AND adapters, a generic `launch()` parameterized by `proxy_mode`/`trust_requirement`/`shell_environment_policy` (collapses `start_cmd.py`+`codex_cmd.py`). Then reuse-only CLI = 1-file add; new-protocol CLI = 1 new directory, zero shared edits. Est. 1-2 days, launch consolidation being the real work.

Note: ALP-2434 (Electron UX v2 planning gate) explicitly scoped Gemini/OpenCode harnesses OUT, so this is net-new initiative territory. The descriptor refactor is the natural prerequisite to onboarding either CLI.

**Verify:** Is the descriptor really decorative, or is some launch behavior already descriptor-driven? Is the proposed `providers/<name>/` layout sound given the import DAG rule in `api/CLAUDE.md` (ir -> adapters -> rules -> pipeline -> storage -> breakpoint -> server, no cycles)? Would co-locating launch (CLI-layer) with adapter (IR-layer) violate that DAG? What is the real migration cost and risk to the released Codex path?

---

## Cross-cutting

Three keystones are independent and don't block each other:
1. run_id -> storage (Q1)
2. raw-body passthrough (Q2)
3. load-bearing descriptors (Q3)

Sequencing claim to test: doing (3) and (2) before onboarding Gemini means onboarding onto the clean shape instead of retrofitting. Is that the right order, or is there a dependency/risk that reorders them?

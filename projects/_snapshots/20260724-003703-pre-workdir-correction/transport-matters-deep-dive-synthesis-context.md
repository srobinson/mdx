---
task: transport-matters horizontal and vertical surface synthesis
session: ad-hoc-codex-2026-05-15
date: 2026-05-15T04:44:26Z
head_sha: 6ce13bfa481620bf730b0dc5733a450f1703e8c6
---

## Where my head was

The task is to synthesize a code deep dive into a durable `.mdx` product and
architecture document. The target lens is horizontal versus vertical surface:

- Horizontal surface: shared Transport Matters machinery that should stay
  provider agnostic.
- Vertical surface: provider or client specific paths for Claude Code, Codex,
  and future clients such as Gemini.

The product framing to preserve:

- Runtime Matters is out of scope for this Transport Matters redesign.
- Transport Matters should focus on payload truth, overlays, exchange detail,
  replay, fork, and provider capture.
- The staged UX now has five screens:
  1. Screen 0: env vars and capture-impact settings.
  2. Screen 1: disposable Claude Code probe.
  3. Screen 2: overlay editor with Ask Agent.
  4. Screen 3: fresh working session under overlay.
  5. Screen 4: exchange detail with replay, fork, and future overlay tools.
- Forks are a real product capability. Historical exchanges are evidence; user
  changes to historical turns should create replay, fork, or future overlay
  rules rather than mutating history.

Important mental model from the code so far:

- The backend already has a provider adapter seam, but it is mostly wire format
  oriented. `ProviderAdapter` only handles `matches`, inbound request parse,
  outbound request serialize, and inbound response parse. It does not yet model
  launch, probe, overlay capability, replay, fork, or Screen 0 env vars.
- The CLI already has separate `claude` and `codex` subcommands. That supports
  the emerging recommendation: one product and one release, provider/client
  subcommands, and a driver/capability layer behind them.
- The storage surface already persists raw request, parsed request IR, curated
  request, audit, response, transport artifacts, Codex events, and Codex turns.
  It does not yet have fork lineage as a first class concept.
- The existing overlay model is frontend local state over current override
  objects. It is useful proof of concept, but not enough for durable staged
  overlays or cross-session fork/replay lineage.
- The current Electron package is a host around the web UI and backend process.
  It is not yet the staged desktop product, but it gives a concrete lifecycle
  place to grow from.

## Agents currently running

Four read-only explorer agents were launched and had not returned when this
handover was written:

- `019e29f1-6e0f-7a62-9a83-a56eb71326b3` / Popper:
  backend and provider surface.
- `019e29f1-6e6c-7243-95bb-cf518eee3598` / Nietzsche:
  frontend and UI surface.
- `019e29f1-6ead-7871-9924-6f0ab8aaf68f` / Pauli:
  storage, overlay, replay, fork surface.
- `019e29f1-6f0a-7460-8f9d-785ef6a043e0` / Dirac:
  CLI, launch, desktop, distribution surface.

Next worker should wait for these agents before writing the final synthesis
document if they are still available.

## Evidence gathered locally

Repo topology through fmm:

- `api/`: 203 files, 41,527 LOC.
- `www/`: 133 files, 20,077 LOC.
- `desktop/`: 14 files, 1,560 LOC.
- `api/src/transport_matters/codex/`: 47 files, 11,604 LOC.
- `api/src/transport_matters/cli/`: 37 files, 6,872 LOC.
- `api/src/transport_matters/storage/`: 18 files, 3,382 LOC.
- `api/src/transport_matters/adapters/`: 6 files, 1,655 LOC.
- `www/src/components/`: 74 files, 14,020 LOC.

Backend seams checked:

- `api/src/transport_matters/adapters/base.py:17` defines `ProviderAdapter`.
  It is a wire format adapter, not a full provider driver.
- `api/src/transport_matters/adapters/__init__.py:22` selects an adapter by
  matching mitmproxy flow.
- `api/src/transport_matters/cli/start_cmd.py:141` owns the Claude launch
  lifecycle.
- `api/src/transport_matters/cli/codex_cmd.py:294` owns the Codex launch
  lifecycle.
- `api/src/transport_matters/cli/launch_runtime.py:222` builds the managed
  child environment and strips proxy/trust variables before applying managed
  proxy settings.

Storage seams checked:

- `api/src/transport_matters/storage/base.py:151` defines `ExchangeArtifacts`.
  It captures raw request, request IR, curated raw/IR, audit, response, transport,
  events, and turn.
- `api/src/transport_matters/storage/base.py:275` defines `StorageBackend`.
  It supports persist/read/delete/update pipeline tokens, but not fork lineage.
- `api/src/transport_matters/storage/disk_layout.py:61` defines artifact paths
  for exchange directories. There is no fork artifact path yet.
- `api/src/transport_matters/api/v1/exchanges.py:114` defines the exchange
  detail response.
- `api/src/transport_matters/api/v1/exchanges.py:151` reads exchange artifacts
  and returns transport diagnostics.

Frontend seams checked:

- `www/src/stores/overlaysStore.ts:29` defines a frontend `Overlay`.
  It stores a name, scope, overrides, created time, and draft flag.
- `www/src/stores/overlaysStore.ts:68` stores overlays in frontend persisted
  state.
- `www/src/types.ts:270` defines override kinds.
- `www/src/types.ts:511` defines `PausedFlow`, which still reflects the old
  breakpoint/ARM model.
- `www/src/types.ts:90` defines `ExchangeDetail` and mirrors the backend detail
  response shape.

Desktop seams checked:

- `desktop/package.json` has build, dev, package smoke, test, and typecheck
  scripts.
- `desktop/src/main.ts` starts backend and creates the hosted window.
- `desktop/src/backendProcess.ts` builds and launches the backend child process.
- `desktop/src/window.ts` hosts the renderer URL and constrains navigation.

## What I was about to do next

I was about to wait for the four explorer agents, then write:

`/Users/alphab/.mdx/projects/transport-matters-provider-surface-deep-dive.md`

The document should synthesize:

- Horizontal core surfaces.
- Vertical Claude Code surface.
- Vertical Codex surface.
- Future Gemini/client driver shape.
- How the five screen staged UX maps to today’s code.
- What needs to be added for provider drivers, durable overlays, forks, and
  exchange detail tools.

## Approaches I ruled out

- Do not frame this as Runtime Matters. Transport Matters can have provider
  launch subcommands and Screen 0 env vars, but reusable runtime profile
  composition is out of scope.
- Do not make separate release binaries per provider unless dependency or
  licensing pressure forces it later. The current CLI shape supports one
  product with provider subcommands.
- Do not mutate historical exchanges. The product rule should remain:
  inspect past, shape future, fork when rewriting history.

## Gotchas I learned

- `ProviderAdapter` is too narrow for the product driver concept. It is an IR
  translation seam, not a lifecycle or capability abstraction.
- The current overlay store lives in the frontend and persists override arrays.
  It is not a durable backend overlay system.
- `PausedFlow` and breakpoint components encode the old ARM mental model. They
  are useful raw material for Screen 2, but the new staged UX should not inherit
  the user journey unchanged.
- The Codex surface is much deeper than the generic adapter surface. There is an
  entire `api/src/transport_matters/codex/` vertical with derivation, transport,
  repair, timeline, event, and HTTP fallback logic.

## Warnings for next iteration

- Wait for explorer agents before finalizing the deep dive. They were dispatched
  specifically to avoid reading too many large files locally.
- The visual companion server was running at `http://localhost:59986` with
  content under `.superpowers/brainstorm/78530-1778817599/`, but the synthesis
  itself should be an `.mdx` artifact.
- There are local edits to `LESSONS.md` from user corrections and untracked
  `.superpowers/` visual companion files. Do not revert them.


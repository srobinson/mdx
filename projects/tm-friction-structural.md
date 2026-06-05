# Structural friction in transport-matters

Scout diagnosis. Repo `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters` at main `84d2c66d`. Read only. Evidence from feature PRs #354, #353, #352, #345, #341, #337, #336 and their near-term follow-ups.

Owner claim treated as ground truth: features are expensive to land and maintain; progress has stalled. This document explains the mechanism.

---

## Method

Per PR: file count, distinct package/area count, Python/TypeScript boundary crossing, rough line mix (feature vs test/scaffold vs plumbing), and fix/refactor PRs that hit the same area within five days.

Line mix is path-heuristic (test files and conftest vs production vs shared vocabulary / re-export style paths). It is directionally right, not an audit of every hunk.

---

## PR measurements

| PR | Title | Files | Areas | Cross-plane | +/− | Feature / test / plumb lines | 5-day area follow-ups |
|----|-------|------:|------:|:-----------:|-----|------------------------------|------------------------|
| #354 | canvas launch readiness + harness settings | 86 | 13 | yes | +2222/−556 | 46% / 49% / 5% | none yet (merged 2026-08-02) |
| #353 | first-run harness evidence cards | 25 | 4 | yes | +2040/−23 | 54% / 44% / 2% | continued as #354 |
| #352 | dispatch credentials by source | 42 | 13 | yes | +1138/−450 | 52% / 48% / 0% | auth lineage below |
| #345 | scope launch identity by candidate | 4 | 1 | no | +143/−13 | 27% / 73% / 0% | #346 test pin |
| #341 | dev channel + spec-driven reset policy | 19 | 14 | no (py+tooling) | +1209/−472 | 37% / 61% / 2% | #344 fix bootstrap |
| #337 | preview bind, per-channel storage, reset | 23 | 18 | yes (token TS) | +666/−145 | 58% / 40% / 1% | #344 fix bootstrap |
| #336 | seed Claude homes with minted credential | 4 | 1 | no | +315/−1 | 35% / 65% / 0% | **#342 fix** (+1747/−300, 39 files), #346, #348 |

### What "areas" means

Top-level packages or clusters: `py:cli`, `py:captured`, `py:harnesses`, `py:controlplane`, `py:launch`, `www:canvas`, `www:core`, `desktop`, `shared`, `scripts`, etc. A single small product idea routinely fans into a dozen of these.

### Window-level compensating work (2026-07-28 → 2026-08-02)

Same calendar window as the feature set:

| Kind | PRs | Net lines (add/del) |
|------|----:|---------------------|
| feat | 7 | +7733 / −1660 |
| fix | 6 | +4535 / −686 |
| refactor | 2 | +429 / −404 |
| test | 1 | +31 / −10 |
| docs | 4 | +1174 / −4335 |

Rough ratio of feature PRs to compensating PRs in that window: **7 feat : 9 fix/refactor/test**.

Worse than PR count: **#336 was four files (+315). Its primary fix #342 was 39 files (+1747/−300)** and crossed `cli/`, `captured/`, addon, capture RPC, and TypeScript. The feature was small; the failure surface was not.

#337+#341 (channels) produced **#344** (+570/−172, 23 files) the same day family: channel resolution still had a bootstrap hole after two "complete" channel features.

#348 explicitly paid for parallel-slice duplication from the same day (`webSocketCodes`, channel exit helpers, probe helpers, fleet-home reason, etc.). Parallel isolation without a shared home multiplies rework.

---

## 1. Typical blast radius of a "small" feature

There are two populations, not one.

### A. Single-plane domain tweak (rare in this set)

#345 and #336 look small: 4 files, one package. Reality:

- Test lines dominate (65–73%).
- The real cost lands later as a large fix (#342 after #336) or as related pins (#346).
- The module graph they sit on is already wide; the PR only shows the delta, not the dependency surface.

### B. User-visible product feature (the common case)

#353, #352, #354: **25–86 files, 4–13 areas, almost always cross-plane**, roughly **half the diff is tests**.

Median-ish product feature in this set:

- ~25–40 files if scoped tightly (#353, #352)
- ~80+ files when it also relocates ownership (#354 moved credential/exec resolution and rewired first-run)
- **must touch both languages** whenever UI reads a new fact the capture plane owns

### Forced seams (paths and symbols)

A canvas launch/readiness style change is forced through this stack:

```
www/packages/canvas  (FirstRunScreen, useLaunchReadiness, spawn, CommandCenter)
        ↓ HTTP types
www/packages/core    (transport.ts, types/launchReadiness.ts, types/harnessInventory.ts)
        ↓
shared/*.json        (harness_inventory_vocabulary_v1.json)   [when vocabulary moves]
        ↓
api .../api/v1/*     (launch_readiness routes, capture_rpc_routes)
        ↓
api .../captured/*   (readiness.launch_readiness, prepare_captured_run, context)
        ↓ still imports
api .../cli/*        (launch_runtime.prepare_launch, runner.*, runtime_home.*, home_overlay.*)
        ↓
api .../credential_source.py, launch/binaries.py, harnesses/inventory.py
```

Spawn path concretely:

| Step | Symbol / path |
|------|----------------|
| Browser spawn | `www/packages/canvas` model/spawn and captured-run binding |
| Product runtime | `@tm/runtime` / Gateway capture client → `POST /v1/capture/prepare` |
| Route | `api/v1/capture_rpc_routes.prepare_capture` |
| Registry | `capture_rpc.CaptureLeaseRegistry.prepare_capture` |
| Domain prepare | `captured.run.prepare_captured_run` |
| Context | `captured.context.build_captured_run_context` |
| Displaced launch | `cli.launch_runtime.prepare_launch`, `cli.runtime_home.plan_runtime_home` / `prepare_runtime_home` |
| Proxy start | `cli.runner.start_prepared_proxy` and related outcomes |
| Homes / creds | `cli.home_overlay`, `cli.home_seeders`, `credential_source.resolve_credential_path` |

ARCHITECTURE already states the rule: `cli/` is adapter only; measured 2026-08-01, most of it is displaced domain. The code still forces product features through that package.

Channel features add a second fan-out:

| Seam | Paths / symbols |
|------|-----------------|
| Spec | `channel-specs.json`, `channel.ChannelSpec`, `resolve_channel_spec`, `activate_channel` |
| Env keys | `env_keys` |
| Storage | `storage_roots`, `temporary_paths`, `session` testing helpers |
| Scripts | `scripts/reset-channel-store.sh`, `scripts/local-desktop-dev-mode.sh`, `justfile` |
| Integration tests | `api/tests/integration/test_reset_channel_store.py`, `test_local_desktop_dev_mode.py` |
| Docs | `docs/CHANNELS.md` |

Changing one channel property is not a one-module edit; it is a configuration surface with many readers and a destructive integration suite.

---

## 2. Where friction concentrates (three worst places)

### Worst: launch/runtime-home domain trapped in `cli/`

Evidence:

- `cli/` production ~8.5k LOC, tests ~12.6k LOC (largest pure cluster after harnesses+api tests).
- Non-cli importers of `transport_matters.cli.*` include `captured/run.py`, `captured/context.py`, `captured/claude.py`, `captured/codex.py`, `captured/dependencies.py`, `captured/models.py`, `controlplane/provisioning.py`, `env_keys.py`.
- Hottest displaced modules: `cli.runner`, `cli.launch_profile`, `cli.launch_runtime`, `cli.runtime_home`, `cli.home_seed` / `home_overlay`.
- `launch/` exists as a leaf (`binaries`, `environment`, `manifest`, ~400 production LOC) but orchestration and types remain in `cli/`.
- #354's "move credential and executable resolution out of CLI ownership" is itself proof: product work still pays to extract leaves one PR at a time while the body stays put.
- #336 seeded credentials in `cli/home_overlay.py`. #342 had to rework `cli/` **and** `captured/*`, addon, and capture RPC: the domain had no single home, so the fix could not stay local.

Why it costs features: every launch, auth, doctor, or canvas-spawn change enters an adapter package that other planes already depend on. The ratchet forbids adding more displacement, so each slice either violates the rule, does a partial extract, or threads more parameters through `prepare_captured_run`'s long dependency list. All three are expensive.

### Second: cross-plane dual contracts (not a single schema source)

Evidence:

- `test_type_mirrors.py` pins Python ↔ TypeScript by parsing both sources: `ir.py` ↔ `www/packages/core/src/types/ir.ts`, `controlplane/activity.py` ↔ `packages/contract/src/activity/wire.ts`, overrides, runtime delivery constants.
- Shared JSON fixtures (`shared/harness_inventory_vocabulary_v1.json`, descriptors, override targets, char accounting) are loaded from both planes and re-tested on both sides.
- #353 added vocabulary + Python test + `www/core` types + canvas UI in one PR. #354 expanded the same chain and added `launchReadiness` types.
- Product plane cannot invent a readiness fact without a Python producer, a route, a TS type, often a shared vocabulary change, and mirror/tests on both ends.

Why it costs features: a one-line product fact is a multi-repo-local contract ceremony. Failure mode is silent drift until `test_type_mirrors` or a dual inventory test fails late. There is no generate-once boundary; there is duplicate declaration plus a ratchet test.

### Third: channel / home / env configuration fan-out

Evidence:

- #337 and #341 together rewrote storage root semantics, specs, reset scripts, doctor-adjacent paths, and large integration tests.
- Immediate fix #344: bootstrap channel configuration during resolution (23 files again).
- Readers of channel/env concepts span `config.py`, `storage_roots.py`, `runtime_registry.py`, `session_store_preflight.py`, CLI commands, desktop scripts, and tests that each re-seed channel state.
- Auth homes are a related fan-out: `claude_home` / `codex_home` / `home_overlay` / `runtime_home` / fleet auth / credential broker, each with its own test file family.

Why it costs features: identity of "where does this run live and with whose credentials" is spread across specs, env keys, storage roots, overlay seeders, and scripts. A feature that only wants "dev channel" or "minted credential" must prove every reader still agrees, usually with integration tests that are themselves large surface area.

### Candidates tested and ranked lower as *the* center

| Candidate | Finding |
|-----------|---------|
| Python capture ↔ TS product seam | Real tax (second place), but intended architecture. Cost multiplies because contracts are dual-written and because launch domain is still on the capture side behind capture RPC. |
| `cli/` displaced code | **Center of gravity.** Architecture names it; PRs confirm every launch/auth feature still pays it. |
| Per-channel / runtime-home config | Third place; explodes specific feature classes (channels, auth homes). |
| Launch path | Same as cli displacement plus capture RPC dual entry (CLI helper and `POST /v1/capture/prepare`). |
| Test/fixture apparatus | Systemic multiplier (~40–65% of feature PR lines), not the root topology. It amplifies whatever graph you touch. |

---

## 3. Duplicated or parallel machinery (pairs)

| Pair | Paths / symbols | Why one change hits both |
|------|-----------------|--------------------------|
| CLI prepare vs capture prepare | `cli._helpers._prepare_captured_run` and `cli` codex/start paths vs `captured.run.prepare_captured_run` / `capture_rpc` | Two entry points into the same domain; behavior must stay aligned for detached CLI and canvas/RPC. |
| Captured context vs cli launch stack | `captured.context` imports `cli.launch_runtime.prepare_launch`, `cli.runtime_home.*`, `cli.launch_profile.*` | Domain lives in adapter; consumer is non-cli. Any signature change is multi-package. |
| Claude home vs Codex home | `cli/claude_home.py` ↔ `cli/codex_home.py` (+ overlay/seeders) | Parallel harness home policies; credential dispatch (#352) had to thread `CredentialSource` through both. |
| IR / activity type mirrors | `ir.py` ↔ `www/packages/core/src/types/ir.ts`; `controlplane/activity.py` ↔ `packages/contract/.../wire.ts` | Dual declaration; `test_type_mirrors.py` is the glue, not a generator. |
| Harness inventory vocabulary | `shared/harness_inventory_vocabulary_v1.json` ↔ `harnesses/inventory.py` ↔ `www/packages/core/src/types/harnessInventory.ts` (+ canvas cards) | #353/#354 paid all three (+ UI). |
| Channel default / activate helpers | Pre-#348: restated in `channel_cmd`, `tail_cmd`, `cli/__init__`; partial consolidate to `cli/channel_options` | Parallel slices re-derived the same exit/error story. |
| WebSocket close codes | Pre-#348: runtime server modules + canvas `terminalSocket.ts` | Same constant set in two languages/packages until `@tm/common/webSocketCodes`. |
| Credential ownership transition | `cli/credential_source.py` (introduced #352) → root `credential_source.py` (renamed/moved #354) | Mid-migration dual placement; follow-on features edit while the home is still moving. |

#348 is direct evidence that parallel feature work without a shared domain home produces named duplicates that need a cleanup PR the same day.

---

## 4. Feature work vs compensating work

### Inside the seven feature PRs

Across the set, **test/scaffold is typically 40–65% of lines**. Feature implementation is often the minority of the diff even before follow-up fixes.

Heuristic totals (add+del lines classified by path):

| | Feature-ish | Test/scaffold | Plumbing |
|--|------------:|--------------:|---------:|
| Sum over 7 PRs | ~4600 | ~5100 | ~200 |
| Share | ~46% | ~52% | ~2% |

So **inside feature PRs alone**, compensating apparatus already exceeds pure feature code.

### Outside those PRs, same week

- Fix/refactor/test PR count ≈ feature PR count (9 vs 7).
- #342 alone is larger than #336+#345 combined in file count and much larger in lines.
- #344 is a same-week structural fix for channel resolution after two channel features.
- #348 is pure compensating refactor for parallel-slice duplication.

**Effective ratio for this set:** about **1 unit of intended feature work to ~1–1.5 units of tests/plumbing/follow-up**, and for auth/launch specifically the follow-up can be **5× the original feature** (#336 → #342).

That matches "cannot make progress": the calendar fills with correct, careful diffs that do not advance the product surface proportionally.

---

## 5. The single structural cost to reduce next

**Move launch, runtime-home, and credential orchestration out of `cli/` into a real non-adapter domain package that both the CLI adapter and `prepare_captured_run` / capture RPC call.**

Why this one:

1. It is the seam every stalled class of work crosses: canvas spawn, readiness, auth seeding, doctor honesty, channel-aware homes, control-plane provisioning.
2. Architecture already forbids new displacement there, so every feature either fights the ratchet, does a partial extract (#354 style), or leaves the graph worse. Paying the full extract once stops the per-feature tax.
3. It collapses dual entry (CLI vs `POST /v1/capture/prepare`) onto one domain API instead of two call stacks that import the same adapter modules.
4. Follow-up explosions like #342 stay inside one package boundary instead of spraying `cli/` + `captured/` + addon + routes + TS.
5. Cross-plane and test taxes remain, but they stop multiplying by "also refactor ownership while shipping the feature."

What this is not: rewriting the Python/TS plane split, deleting tests, or a big-bang "clean architecture" pass. It is the specific gravitational wrong home for the domain that product features keep needing.

Willingness to be wrong: if most near-term work is pure Space/Activity read models with no spawn or auth, the dual-contract tax might dominate first. The measured PR set says otherwise: five of seven features were launch, auth, channel-home, or canvas launch surfaces, and the largest follow-up sat on that same graph.

---

## Appendix: per-PR area sketches

### #354 launch readiness (86 files, 13 areas)

Python: `captured/readiness.py`, `api/v1/launch_readiness.py`, `launch/binaries.py`, `credential_source` move, large `cli/*` touch for doctor/homes, `harnesses/inventory`.  
TS: `www/canvas` first-run + launcher + workbench tests, `www/core` transport + `launchReadiness` type, shell fixtures.  
Shared vocabulary.  
Half the lines tests. Cross-plane yes.

### #353 evidence cards (25 files)

Mostly `www/canvas` + `www/core` + shared vocabulary + one Python inventory test. Cross-plane thin but mandatory for the vocabulary pin.

### #352 credentials by source (42 files)

Center of mass `cli/` (24 files) introducing source-typed credentials; broker, capture routes, desktop smoke, canvas binding. Cross-plane yes. Sets up #354's extract.

### #345 launch identity scope (4 files)

`controlplane/launch_ledger.py`, `launch_service.py`, heavy tests. True single-plane; low product visibility; does not exercise the cli trap.

### #341 / #337 channels

Spec + storage_roots + scripts + huge integration tests + docs. Package count high because every environment reader must stay consistent. #344 proves incompleteness was structural, not carelessness.

### #336 seed minted credential (4 files)

All `cli/`. Looks cheap. #342 is the receipt: minting at overlay without a closed domain boundary forced a multi-plane auth reliability fix immediately after.

---

## Bottom line

Progress is slow because a typical feature is not a local edit. It is a walk across a **displaced launch domain in `cli/`**, a **dual-written cross-plane contract**, and often a **channel/home configuration fan-out**, with **tests consuming half the diff** and **follow-up fixes that can dwarf the feature**. The single highest-leverage structural repair is to give launch/runtime-home/credentials a true domain home outside `cli/` and make both entry paths thin adapters over it.

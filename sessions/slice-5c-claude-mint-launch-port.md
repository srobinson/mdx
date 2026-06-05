---
title: Capture-substrate slice 5c — claude managed-mint + DRY launch-profile port
type: sessions
tags: [backend, transport-matters, capture-substrate, slice-5c, claude, managed-mint, launch-profile, moe]
summary: claude now mints its own session id (`claude --session-id <uuid>`, minted=True, owned descriptor) via a shared per-provider LaunchProfile port that claude+codex both flow through; provider-neutral env vars; real-run proof passed.
status: active
source: backend-engineer
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

## Summary

Realized the Phase A design for claude: `transport-matters claude` mints `uuid4` and launches
`claude --session-id <uuid>`, so TM **owns** the correlation id by construction (`minted=True`,
owned `source_descriptor` at launch, **no seed** — `claude --session-id` CREATES). Generalized the
launch side into ONE DRY managed-launch path driven by a per-provider `LaunchProfile` (launch-side
twin of the read-side `TranscriptAdapter`); claude + codex converge on `prepare_managed_session`.
native-adopt (`locate`) stays as the external-adoption fallback. codex is functionally unchanged,
refactored onto the shared path.

Branch `feat/capture-slice-5c-claude-mint-and-launch-port` @ `c9b7400` (off main `abe1895`).
MoE: author backend-engineer:3.1 (claude), reviewer 3.2 (codex). In review at time of writing.

## API / launch contract

- New port `cli/launch_profile.py`: `LaunchProfile` ABC (`prepare` / `client_argv` /
  `user_supplied_session`), `ClaudeLaunchProfile`, `CodexLaunchProfile`, `ManagedSession`,
  `PROFILES` registry, and the shared `prepare_managed_session(profile, *, client_path, passthrough,
  working_dir, home_dir, env, now, write) -> ManagedSession | None`.
- Env contract generalized to provider-neutral: `TRANSPORT_MATTERS_OWNED_NATIVE_SESSION_ID` /
  `OWNED_SOURCE_DESCRIPTOR` (was `*_CODEX_*`); `build_launch_env` / `build_run_facts` / `RunFacts` /
  `Settings` params renamed `owned_*`. claude reuses them — no `*_CLAUDE_*` duplicates.
- claude argv: `[claude, *passthrough, --session-id <uuid>]`. codex argv: `[codex, -c <policy>,
  resume <uuid>, *passthrough]` (policy-args fn moved into the codex profile). User passthrough wins:
  `--session-id`/`--resume`/`-r`/`--continue`/`-c` (claude) or `resume` (codex) → skip mint.

## Database / index changes

- `bind_exchange`: provider-neutral owned-id gate — carries `owned_source_descriptor` when wire id ==
  `owned_native_session_id`; `minted = is_owned and not readback` (claude managed → True; codex keeps
  synth session_id + minted=False, the §3.4 idempotency PK, left as-is per panel-decide).
- `register_session_cursor`: carries the wire side's authoritative `minted` + owned descriptor across
  the adapter re-bind. **Bug fixed:** `upsert_session` is `minted = excluded.minted` (last-writer-wins)
  and `ClaudeAdapter.bind` returns `minted=False`, so without the carry a managed claude's `minted=1`
  clobbered to 0 once a transcript turn landed.
- `claude_transcript_source` (adapters/claude.py): shared by launch `prepare` + read-back `locate`.
  Slug = `re.sub(r"[^a-zA-Z0-9]", "-", cwd)`.

## Security considerations

No new external surface. The owned uuid is a `uuid4` minted per launch; flows only through the
managed child env + argv (already-trusted child). No secrets added. Honoring user passthrough means a
user-pinned session is never overridden.

## Performance notes

claude `prepare` writes nothing (no seed); it only computes a path + encodes a descriptor. Mint is
once-per-launch (before the retry loop), retry-safe. No new queries; the index changes are pure
derivation in the existing wire/transcript paths.

## Real-run proof (regression f — the gate)

Real `transport-matters claude` (dotted workdir `/private/tmp/tm-5c-rt2.1aQU`, headless `-p "pong"`):
session `71b07917-f112-4d45-8fd6-3186833c7ace` — `cli=claude`, `minted=1`,
`native_session_id == session_id == owned uuid`; `source_descriptor` path **exists on disk**, stem ==
owned uuid; wire `metadata.session_id` == owned uuid (1 row); **2 `transcript_turn`** (user + assistant
pong); wire == transcript == filename stem (DIFF/pivot converge). The slug fix was caught here, not by
unit tests (clean-path fixtures missed the dot → `transcript_turn=0`).

`just check` green (ruff + mypy); 1148 api tests pass.

## Open items

- Awaiting dual MoE sign-off (reviewer codex 3.2). Orchestrator gates `just ci` + opens PR;
  Stuart road-tests before merge.
- Spec/docs fast-follow (post-merge): §5.1 claude deferred-MINT → realized; §5.5 row; §4.2 if the
  port lands there; LEDGER + README (5c) + roadtest (claude now minted).
- The pre-slug-fix real run left a polluted session (`d819…`, transcript_turn=0) in the global
  `~/.transport-matters/index.db` — harmless, separate session.

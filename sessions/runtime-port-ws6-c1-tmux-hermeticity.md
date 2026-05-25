---
title: Runtime port WS6 C1 tmux hermeticity
type: sessions
tags: [backend, runtime, tmux, testing, ALP-2607]
summary: Implemented explicit tmux server-label injection for hermetic runtime tmux tests and verified WS6 C1 gates.
status: active
source: backend-engineer
confidence: high
created: 2026-05-29
updated: 2026-05-29
---

## Summary

Implemented the WS6 Card C1 rework for ALP-2607 on `feat/runtime-port-conformance`.

Commit: `b5c91901ec0e67211d41aa5aa2c54e81f0ebec34`

Key decisions:

- Removed production tmux probe machinery. The codebase no longer defines `tmux_server_for_pane`, `tmux_output_owned_for_pane`, `tmux_output_owned_with_server`, or `TmuxServer`.
- Kept tmux server selection explicit. `DaemonConfig` owns `tmux_server_label: Option<String>`, sourced from `LILO_TMUX_SERVER_LABEL`; `None` uses the default tmux server.
- Threaded `config.tmux_server_label.as_deref()` through runtime tmux call sites for nudge, respawn, liveness, capture, status, and shim respawn classification.
- Added `TmuxSession::server_label()` and `RtmHarness::start_with_tmux_server_label(...)` so tmux integration tests target their isolated per-test tmux server.
- Reverted `crates/lilo/tests/generated_surface_guard.rs` to the main-branch `cargo_bin("xtask")` form.

## API Contract

No API endpoints or wire schemas changed. Public tmux target strings remain `session:window.pane`.

Internal runtime contract adjustment:

```rust
struct DaemonConfig {
    tmux_server_label: Option<String>,
}
```

`LILO_TMUX_SERVER_LABEL` is an internal daemon environment variable used by tests and any operator that deliberately needs a non-default tmux server. It does not change the request or response shape.

## Database Changes

None.

## Security Considerations

No auth, permission, or secret handling changed. The rework avoids production auto-discovery of alternate tmux servers, which keeps server selection explicit and auditable through daemon configuration.

## Performance Notes

No additional production probing was introduced. Tmux operations use the configured server label directly, or the default server when unset.

## Verification

- `cargo build -p lilo -p lilo-runtime-app --bins`: PASS.
- `cargo test -p lilo-runtime-app --test integration_pass5 capture_tmux_pane_returns_snapshot_json -- --nocapture`: PASS.
- `cargo nextest run -p lilo-runtime-app --test integration_pass5 tmux` repeated 3 times: PASS, 8/8 each run.
- `cargo fmt --all && just check && just build && just test`: PASS. `just test` reported `414 tests run: 414 passed, 0 skipped`.
- `fmm generate && fmm validate`: PASS, 364 files indexed and current.
- `git diff --check`: PASS before amend.
- `git grep` confirmed removed probe symbols are absent from `HEAD`.
- `git status --short --branch`: clean after amend.

## Open Items

- WS6 C2 and C3 remain pending and should be handled only after C1 review or handoff.

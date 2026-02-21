---
title: Runtime Matters Docker Arm64 Preflight Fix
type: sessions
tags: [backend, runtime-matters, docker, preflight, alp-2784]
summary: Implemented local Docker architecture first preflight to avoid remote manifest latency for local arm64 images.
status: active
source: backend-engineer
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Summary

Implemented and committed `7775b0605cd139f6be8d360cd5b3b268473e3dcd` on branch `nancy/ALP-2784`. The fix scopes Phase B to the measured slow path only: Docker arm64 preflight now checks local image architecture before remote manifest inspection.

Key decision: no changes to tmux Docker argv, daemon accept handling, public protocol, docs, or host isolation because those symptoms were not proven by logs or reproduction.

## API Contract

No API contract changes.

Affected runtime behavior:

```text
Docker preflight on arm64 host:
1. docker image inspect image architecture
2. If local architecture is arm64, pass without registry manifest inspection
3. If local architecture is not arm64, fail through existing typed metadata error
4. If local image is unavailable, fall back to manifest inspection
5. If local architecture metadata is invalid, return that local metadata error directly
```

## Database Changes

No database schema or migration changes.

## Security Considerations

The change does not broaden Docker execution privileges or mount behavior. It avoids unnecessary remote registry metadata calls for trusted local images and preserves existing typed failures for unavailable images and invalid local metadata.

## Performance Notes

Before the fix, `docker manifest inspect runtime-matters-claude:local` measured about 4.7 seconds and returned registry authentication errors before local architecture fallback.

After the fix, built daemon manual verification showed:

```text
bad env rejection: real 0.12, expected fast short circuit before metadata
successful mounted spawn: real 0.42
```

Verification run:

```bash
cargo test -p rtm-daemon arm64 --quiet
cargo test -p rtm-daemon --quiet
cargo nextest run -p rtm-cli docker_spawn_env_flag_reaches_container_and_runtime docker_spawn_image_flag_overrides_daemon_default docker_tmux_pattern_a_container_survives_pane_close
just check && just build && just test
fmm validate
```

Results: daemon targeted tests passed, three previously failing CLI Docker integration tests passed after fake Docker was updated to report local architecture, the full repo gate passed with 274 nextest tests, and fmm validation was green.

## Open Items

Phase B signoff from the engineering reviewer is pending.

Deferred items require separate evidence before implementation:

1. rtmd crash investigation needs daemon logs or process exit evidence.
2. tmux Docker attach refactor needs a reproducible first frame loss with a successfully started container.
3. Manual cleanup verification used the measured container name because unrelated pre existing rtm labelled containers were already present in Docker.

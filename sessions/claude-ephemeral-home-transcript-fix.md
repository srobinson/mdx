---
title: Claude Ephemeral Home Transcript Fix
type: sessions
tags: [backend, transport-matters, claude, runtime-home, transcript]
summary: Fixed Claude captured runs so transcript descriptors tail the same runtime home used by CLAUDE_CONFIG_DIR.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented PR #131 on branch `fix/claude-ephemeral-home-transcript` at commit `8e44561`.

Claude captured runs launched from a manual runtime home now use one home for both the child process and the owned transcript descriptor. `plan_runtime_home()` sets manual overlay `descriptor_home` to the launched `child_home`, matching the existing template overlay and Codex behavior.

Root cause: manual runtime-home planning kept `descriptor_home` on the source `--agent-home-dir`, while `build_captured_run_context()` launched Claude with the per-run runtime overlay as `CLAUDE_CONFIG_DIR`. The tailer watched `<source>/projects`, but Claude wrote under the launched overlay home.

## API Contract

No public API shape changed.

Internal launch metadata alignment changed:

```typescript
interface OwnedClaudeLaunchDescriptor {
  TRANSPORT_MATTERS_AGENT_HOME_DIR: string; // launched CLAUDE_CONFIG_DIR home
  TRANSPORT_MATTERS_OWNED_SOURCE_DESCRIPTOR: string; // file_tail under the same home/projects root
}
```

## Database Changes

None. No migrations or schema changes.

## Security Considerations

The fix preserves runtime home isolation. The transcript tail path now follows the launched per-run overlay rather than the operator supplied source home, preventing a stale or unrelated directory from being tailed.

No secrets are logged. The regression only asserts path relationships and descriptor metadata.

## Performance Notes

No additional runtime work was added. The change is a planning decision before launch.

Validation performed:

- `cd api && ./.venv/bin/python -m pytest src/transport_matters/test_captured_run_web_separation.py::test_prepare_captured_run_claude_manual_home_descriptor_matches_launch_home -q`
- `cd api && ./.venv/bin/python -m pytest src/transport_matters/test_captured_run_web_separation.py src/transport_matters/cli/test_runtime_home.py::test_manual_plan_preserves_descriptor_home_and_no_overlay src/transport_matters/cli/test_runtime_home.py::test_claude_template_descriptor_resolves_under_runtime_projects src/transport_matters/cli/test_captured_run.py::test_prepare_captured_run_spawn_spec_matches_public_invocation_helper -q`
- `cd api && just check`
- `cd api && just test`, 1455 passed

## Open Items

Monitor PR review for any desired distinction between operator supplied source home and launched overlay home in UI copy or run metadata. Current behavior intentionally reports the launched home as the descriptor and manifest home for manual overlay launches.

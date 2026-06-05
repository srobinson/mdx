---
title: Runtime home slice 1 implementation
type: sessions
tags: [backend, runtime-home, codex, claude]
summary: Shared runtime home planning now drives captured and Codex launch seams with template descriptor binding.
status: active
source: backend-engineer
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Summary

Implemented runtime home slice 1 in `transport-matters` PR #118 on branch `feat/runtime-home-slice1`.

Key decisions:

- Added `transport_matters.cli.runtime_home` as the shared planner for native, manual, template, and proxy only runtime home modes.
- Routed captured run setup and the Codex CLI path through `RuntimeHomePlan`.
- Bound template mode descriptors, owned cursor fields, and launch metadata to the prepared runtime home.
- Preserved current public request shape and deferred RunManager template input plumbing to a later slice.
- Addressed review findings in commit `30ccde2`: `run_codex` is now 130 lines, stale launch field env values are stripped, proxy only launches preserve explicit homes, and `Any` launch field usage is documented.
- Fixed the road-tested desktop Codex regression in commit `d1ee43b`: captured Codex with manual `--agent-home-dir` now seeds its owned resume rollout in the runtime `CODEX_HOME`, not the manual source home. Claude manual home descriptor behavior remains unchanged.

## API Contract

No public API shape changed in this slice.

Internal launch metadata now accepts a generic launch field carrier:

```typescript
interface LaunchFields {
  [key: string]: unknown;
}

interface RuntimeTemplateLaunchField {
  template_id: string;
  template_home: string;
  [provenanceKey: string]: string;
}
```

`runtime_template` is carried internally for captured run requests, but no client facing endpoint accepts it yet.

## Database Changes

None.

Session cursor binding now preserves dynamic launch fields across owned cursor rebinding. No schema migration was required.

## Security Considerations

- Template content remains separate from native credential material.
- Codex template mode copies native `auth.json` as a fallback only when the template lacks auth.
- Claude template mode keeps `projects/` local to the runtime home.
- Codex template mode keeps `sessions/` local to the runtime home.
- Captured Codex manual homes seed owned resume rollouts into the runtime home, keeping source templates and manual homes from receiving transient owned session files.
- `TRANSPORT_MATTERS_LAUNCH_FIELDS` is controlled per launch and stripped from managed child environments to prevent stale internal metadata inheritance.
- Full credential token split remains out of scope for slice 1.

## Performance Notes

The planner adds only path selection and metadata construction during launch preparation. Runtime capture paths remain unchanged after process start.

Verification:

- Fail first: `uv run pytest src/transport_matters/cli/test_runtime_home.py -q` failed on proxy only home preservation and stale launch field env inheritance before the review fix.
- Review fix focused after: `uv run pytest src/transport_matters/cli/test_runtime_home.py src/transport_matters/cli/test_home_seed.py src/transport_matters/cli/test_launch_profile.py src/transport_matters/cli/test_codex.py src/transport_matters/cli/test_captured_run.py src/transport_matters/test_addon_runtime.py -q`, 92 passed.
- Road-test fail first: `uv run pytest src/transport_matters/test_captured_run_web_separation.py::test_prepare_captured_run_codex_manual_home_seeds_runtime_home -q` failed because the runtime `CODEX_HOME` had zero seeded rollouts.
- Road-test focused after: `uv run pytest src/transport_matters/test_captured_run_web_separation.py src/transport_matters/cli/test_runtime_home.py src/transport_matters/cli/test_captured_run.py src/transport_matters/cli/test_codex.py -q`, 42 passed.
- Gate: `cd api && just check && just test`, 1391 passed in 29.44s.

## Open Items

- Add public template input plumbing through RunManager in the planned later slice.
- Complete the credential token split design.
- Extend teardown behavior only when the owning slice reaches runtime lifecycle management.
- Wire user visible template selection once API shape changes are approved.

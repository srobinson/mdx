---
title: Desktop Relaunch Workdir Switch
type: sessions
tags: [backend, desktop, relaunch, workdir]
summary: Made desktop relaunch workdir aware so same workdir reuses and different workdir reclaim switches.
status: active
source: backend-engineer
confidence: high
created: 2026-06-24
updated: 2026-06-24
---

## Summary

Implemented `fix/desktop-relaunch-workdir-switch` at commit `87f5aafa4d2aeda7ba952b6d73b185d2f485a5a4`.

The desktop launch path now distinguishes healthy runtime reuse by both channel and requested workdir. A healthy runtime on the same channel and same workdir is reused. A healthy runtime on the same channel with a different workdir is reclaimed through the existing reclaim primitive, then relaunched for the requested cwd.

Python CLI launch paths and the direct Electron startup path share the same behavior. The direct Electron status contract now carries runtime `cwd`, which lets startup avoid attaching to a live backend serving the wrong workspace.

## API Contract

No public HTTP API changed.

Internal runtime status contract now includes the served cwd:

```typescript
interface DesktopRuntimeStatus {
  state: "absent" | "live" | "stale" | "non_tm";
  channel: string | null;
  pid: number | null;
  ports: {
    api: number | null;
    proxy: number | null;
  };
  cwd: string | null;
}
```

CLI launch behavior now follows this decision table:

| Existing runtime | Requested runtime | Action |
| --- | --- | --- |
| Same channel, same workdir, healthy | Same channel | Reuse and attach |
| Same channel, different workdir, healthy | Same channel | Reclaim, then launch requested cwd |
| Stale or wedged | Same channel | Existing auto reclaim behavior |
| Non Transport Matters runtime | Same ports | Existing refusal behavior |
| Force restart | Any | Existing forced reclaim behavior |

## Database Changes

None.

## Security Considerations

The change preserves the existing port ownership and safety boundaries. Non Transport Matters runtimes are still refused. Process termination still flows through the record scoped desktop reclaim primitive rather than a new kill path. No secrets or authentication material changed.

## Performance Notes

Same workdir relaunch remains an attach path and avoids unnecessary backend churn. Different workdir relaunch performs one existing reclaim operation before starting the requested backend. The existing debounce behavior for transient runtime startup remains covered.

## Verification

Passed:

- `cd api && uv run python -m pytest src/transport_matters/cli/test_desktop_idempotent.py src/transport_matters/cli/test_desktop_runtime.py src/transport_matters/test_launch_seam_imports.py`, 45 passed.
- `cd desktop && pnpm vitest run src/desktopRuntime.test.ts src/main.reclaim.test.ts src/main.test.ts`, 3 files passed, 26 tests passed.
- `cd api && just check`.
- `cd desktop && just check`, 10 test files passed, 49 tests passed.
- `git diff --check`.
- `just check`, including desktop, www, and api checks. Existing www lint warnings remained unrelated.
- `just test`, including desktop 49 tests, www 1057 tests, and api 1760 tests.
- `cd api && just ci`, including formatting, lint, mypy, migration smoke, and api pytest.

Root `just ci` is not defined in this repo, so API CI was run with the existing `cd api && just ci` recipe.

## Open Items

None known.

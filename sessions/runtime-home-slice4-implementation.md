---
title: Runtime Home Slice 4 Implementation
type: sessions
tags: [backend, runtime-home, runs, api, session-store]
summary: Wired external .agent-runtimes templates into run creation and persisted template provenance.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented Runtime Home Slice 4 on branch `feat/runtime-home-slice4` at commit `d2bc81d`, opened PR #128.

Key decisions:

- `CreateRunRequest.runtimeTemplate` resolves to a `RuntimeTemplateRef` before spawning the run.
- `SpawnRun.runtime_template` carries the resolved reference to `RunManager._captured_request()`.
- `CapturedRunRequest.runtime_template` remains the runtime home planning input.
- API `launch_fields` do not carry `runtime_template`; runtime home planning owns declared `template_provenance`.
- Runtime template value objects live in shared core modules so API code does not import CLI internals.
- Registry tests live beside the real `transport_matters.runtime_registry` module.
- `RuntimeHomePlan.template_provenance_field` is the single owner for the flat provenance dict shape.
- Codex captured run preparation tests stub CA resolution through one shared helper so clean HOME CI runners do not require `~/.mitmproxy/mitmproxy-ca-cert.pem`.

Fix round changes:

- Removed dead `api/src/transport_matters/cli/runtime_registry.py` shim.
- Moved `api/src/transport_matters/cli/test_runtime_registry.py` to `api/src/transport_matters/test_runtime_registry.py` and imported the real module.
- Routed `codex_cmd.py`, `captured_run_context.py`, and `RuntimeHomePlan.launch_fields` through `RuntimeHomePlan.template_provenance_field`.
- Updated PR body with deferred follow-up to drop test-only `RuntimeTemplateRef` and provenance re-exports from `cli/runtime_home.py` after remaining imports move to `runtime_templates`.

Fix round 2 changes:

- Reproduced the CI failure with clean HOME before the fix: `test_codex_captured_run_template_launch_records_provenance_and_runtime_descriptor` failed with `MitmproxyCAMissingError` and `typer.Exit(2)`.
- Extracted `_stub_codex_addons_and_ca()` in `cli/test_runtime_home.py`.
- Added `monkeypatch` to the runtime template captured run test and routed it through the shared stub.
- Reused the same helper in `test_run_codex_force_http_fallback_still_resolves_addons` to avoid duplicate fake implementations.
- Updated PR body with the hermetic clean HOME verification.

Verification:

- Failing before: `cd api && HOME=$(mktemp -d) .venv/bin/python -m pytest src/transport_matters/cli/test_runtime_home.py::test_codex_captured_run_template_launch_records_provenance_and_runtime_descriptor -q` failed before the stub with missing mitmproxy CA.
- Passing after: same clean HOME single test passed.
- `cd api && just check && just test`, 1444 passed.
- `rg "cli\\.runtime_registry|from transport_matters\\.cli\\.runtime_registry" api/src/transport_matters` returned no matches.
- Modified file length check, all touched files under 700 lines.
- `git diff --check`.

## API Contract

```typescript
// POST /api/v1/runs
interface CreateRunRequest {
  cli?: "claude" | "codex";
  cwd: string;
  prompt?: string | null;
  runtimeTemplate?: string | null; // name under ~/.agent-runtimes/runtimes/
  terminal?: {
    cols?: number;
    rows?: number;
  };
  oscColorReplies?: boolean;
  continueFromSessionId?: string | null;
  idempotencyKey?: string | null;
}

interface RunViewModel {
  id: string;
  status: string;
  runId: string;
}

interface ApiError {
  error: string;
  message: string;
  details?: unknown;
}
```

Runtime template validation failures return HTTP 400 with machine readable code `invalid_runtime_template`.

Internal contracts:

```python
@dataclass(frozen=True, slots=True)
class RuntimeTemplateRef:
    template_id: str
    client_name: str
    template_home: Path
    provenance: Mapping[str, str]

@dataclass(frozen=True, slots=True)
class SpawnRun:
    runtime_template: RuntimeTemplateRef | None = None

@dataclass(frozen=True, slots=True)
class RuntimeHomePlan:
    @property
    def template_provenance_field(self) -> dict[str, str] | None: ...
```

## Database Changes

Added migration `0005_session_template_provenance`:

- `upgrade`: add `session.template_provenance jsonb`
- `downgrade`: drop `session.template_provenance`

Persistence paths updated:

- `SessionBinding.template_provenance`
- `SessionRow.template_provenance`
- session DAO insert, upsert, and row mapping
- transcript tailer rebind preservation
- session ingest
- backfill from owned session facts

Upsert keeps the first non null provenance value with `COALESCE(session.template_provenance, EXCLUDED.template_provenance)`.

## Security Considerations

- Template names are validated as relative POSIX paths.
- Empty, absolute, current directory, parent directory, and traversal names are rejected.
- Resolved template directories must stay under `~/.agent-runtimes/runtimes`.
- Missing templates and non directory paths are rejected before run spawn.
- Existing runtime home template validation still rejects credential files and secret bearing config.
- `.git` and `runtime.toml` remain excluded from template overlay symlinks by the existing materialization policy.
- Tests no longer depend on user level mitmproxy CA material.

## Performance Notes

- Template resolution performs bounded filesystem checks on a single registry path.
- No additional database queries are introduced for run creation.
- Session writes add one JSONB column in the existing session upsert path.
- No N+1 behavior is introduced.

## Open Items

- PR #128 needs review and merge.
- UI consumers can expose `runtimeTemplate` selection once the `.agent-runtimes` registry UX exists.
- Registry metadata from `runtime.toml` remains external to Transport Matters for this slice.
- Follow-up: drop `RuntimeTemplateRef` and provenance re-exports from `cli/runtime_home.py` after remaining test imports move to `runtime_templates`.

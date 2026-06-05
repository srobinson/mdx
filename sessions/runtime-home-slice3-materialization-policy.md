---
title: Runtime Home Slice 3 Materialization Policy
type: sessions
tags: [backend, runtime-home, template-home, security]
summary: Implemented and hardened template mode materialization, unknown content inclusion, secret free validation, writer audit docs, and mutation tests.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented Slice 3 on branch `feat/runtime-home-slice3`, PR #121.

Commits:

- Initial implementation: `35f17af7af85c7eac0daf400144516ede9283ce4`.
- Fix round: `ce0946e13ee3ef4a2c61a55093158f7d7237a0b3`.
- Explicit manual template precedence regression: `f59d7e54f4831de87de88cb847070e2d8de092b9`.
- Owner policy reshape for unknown content inclusion: `307a16ba88044612aa3bf30155bbf668436fa13c`.

Key decisions:

- Template mode uses explicit per client materialization policy for known local writable, copied, credential, and ignored entries.
- Unknown top level template entries default to content and are symlinked into the runtime home.
- `.git` and `runtime.toml` are never materialized into runtime homes.
- Native and manual overlays keep the prior catch all source symlink behavior except for the shared never symlink names.
- Proxy only launches still do no materialization.
- Template runtime home teardown remains deferred. This slice supplies the evidence gate.
- Manual launches ignore `runtime_template` validation because manual home precedence means the template is unused.

## API Contract

No public HTTP API contract changed.

Launch seam contract:

- `RuntimeHomeMode.TEMPLATE` branches in `prepare_runtime_home()` to `prepare_runtime_home_template_overlay()`.
- `RuntimeHomeMode.NATIVE` and `RuntimeHomeMode.MANUAL` continue through `prepare_runtime_home_overlay()`.
- `RuntimeHomeMode.PROXY_ONLY` returns no runtime overlay.
- Template validation runs during `plan_runtime_home()` only when the selected mode is `TEMPLATE`.
- A manual home takes precedence over any `runtime_template`, even if that template path is invalid.
- Unknown template entries are included as symlinks unless classified as local writable, copied config, credential, or never materialized.

Template known content lists:

- Claude: `CLAUDE.md`, `agents`, `commands`, `hooks`, `output-styles`, `plugins`, `skills`, `statusline-command.sh`.
- Codex: `AGENTS.md`, `developer_instructions`, `hooks`, `hooks.json`, `plugins`, `skills`, `vendor_imports`.

Never materialized entries:

- `.git`.
- `runtime.toml`.

## Database Changes

None.

## Security Considerations

Launch validation rejects template secrets before materialization:

- Claude `.credentials.json`.
- Codex `auth.json`.
- Claude `.claude.json` fields `oauthAccount` and `userID`.
- Codex auth shaped material in `config.toml`, including exact, suffix, and delimiter segment secret key indicators such as `OPENAI_API_KEY`.
- Missing template roots when template mode is selected.

Codex benign auth adjacent keys such as `author` and `account_name` are allowed. Rotating credential files are linked only from native auth homes. Template config files are copied into the runtime home before mutation. Writable client state is local to the runtime home, never symlinked to the template.

## Performance Notes

The policy adds only top level template validation and small file parsing for Claude JSON or Codex TOML during launch planning. No database or request path latency impact.

Verification:

- Initial Slice 3 fail first focused validation run observed 6 expected failures before implementation.
- Fix round fail first focused run observed 3 expected failures and 8 passes before fixes.
- Fix round focused after run passed 11 tests.
- Manual precedence regression focused run passed 2 tests.
- Owner policy reshape fail first focused run passed 0 tests and failed 4 tests before implementation.
- Owner policy reshape focused after run passed 4 tests.
- `cd api && just check` passed with ruff format, ruff check, and mypy clean after the policy reshape.
- `cd api && just test` passed with 1414 tests after the policy reshape.

## Open Items

- Template mode `rmtree` teardown remains deferred until the orchestrator accepts this evidence gate.
- Slice 4 can replace hard coded known content names with a registry driven extension point.
- Future client versions may add new writable paths that need explicit classification before template launches should rely on them.

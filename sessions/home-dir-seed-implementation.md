---
title: Home Dir Seed Implementation
type: sessions
tags: [backend, cli, auth, home-dir, transport-matters]
summary: Implemented non-destructive Claude and Codex managed home seeding for --home-dir launches.
status: active
source: backend-engineer
confidence: high
created: 2026-06-01
updated: 2026-06-01
---

## Summary

Implemented local commit `bde8fed` on `feat/home-dir`.

The launch path now seeds managed Claude and Codex homes when `--home-dir` is set, the managed client will launch, and `--print-command` is false. The implementation uses a `HarnessSeeder` protocol and registry keyed by client name, so adding another harness means adding one seeder and registering it.

## API Contract

No HTTP API changed.

CLI behavior changed for:

```text
transport-matters claude <cwd> --home-dir <home>
transport-matters codex <cwd> --home-dir <home>
```

Seed contract:

```typescript
interface HomeSeedRequest {
  clientName: "claude" | "codex";
  homeDir: string;
  workingDir: string;
}

interface HomeSeedResult {
  seededHomeDir: string;
  authCopiedIfMissing: boolean;
  cwdTrusted: true;
  onboardingBypassed?: true;
}
```

Side effect rules:

- Runs only for real launch, not `--print-command`.
- Runs only when a managed client is present, not proxy only mode.
- Never clobbers existing auth.
- Trust merges into the existing home.

## Database Changes

None.

## Security Considerations

- Claude reads the default source from `CLAUDE_CONFIG_DIR/.claude.json` when set, otherwise `~/.claude.json`.
- Claude target `<home>/.claude.json` copies `userID` and `oauthAccount` only when missing, then always sets onboarding complete and cwd trust.
- Codex reads the default source from `CODEX_HOME` when set, otherwise `~/.codex`.
- Codex target `auth.json` is copied only when missing using `O_EXCL` and mode `0600`.
- `.claude.json` and `config.toml` are written via temp file plus replace, with mode `0600`.
- Tests and the real default home probe avoid printing secret values.

## Performance Notes

The seed path does bounded local file IO before launch. The Codex config merge parses the TOML before and after mutation to prevent corrupt writes. No network or database work is added.

## Open Items

- Reviewer signoff `S|B` is pending after `C|bde8fed`.
- There is no per-home lock, so concurrent launches can still have a residual lost-update race. Writes are atomic, but last writer wins.
- Claude Code token reuse is validated for the macOS credential-store model. Other platform credential layouts may still require manual login.

## Verification

- `cd api && just check && just test`
  - ruff format clean
  - ruff check clean
  - mypy clean
  - `963 passed in 6.19s`
- Targeted test subset passed: home seed tests plus existing home-dir print and launch tests.
- Real default home temp probe passed without printing secret values:
  - Claude `.claude.json` exists, mode `0600`, onboarding true, `userID` present, `oauthAccount` present, cwd trusted.
  - Codex `auth.json` exists, mode `0600`, `config.toml` exists, mode `0600`, cwd trusted.

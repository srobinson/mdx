---
title: Launcher Model Agnostic Generation
type: sessions
tags: [backend, agent-runtimes, launcher, generation, capabilities]
summary: generate.py now strips launch-time models and emits fail-closed provider capability metadata for runtime templates.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary

Implemented Slice A on branch `feat/launcher-model-agnostic`, commit `b4b6b9d`. `bin/generate.py` removes `model` from `[settings.claude]` and `[settings.codex]` before writing generated runtime artifacts. It also removes stale `model` keys already present in existing `settings.json` files during regeneration.

Implemented Slice B on the same branch, commit `672df8c`. The generator now loads the root `capabilities.toml`, supports required and optional skills, folds legacy model settings into non-binding recommended model hints, parses required skill frontmatter with stdlib code, and emits `<runtime>/capabilities.json`.

Provider derivation starts from both providers and narrows only through explicit skill `provider` frontmatter or required capability registry provider sets. Skill source store location is packaging metadata and does not constrain provider selection.

Fixed the Slice B parser in commit `4713056`. YAML-natural unquoted inline lists such as `requires_capability: [image-generation]` now parse correctly and malformed non-empty inline forms fail closed with `SystemExit` naming the skill.

## API Contract

No HTTP or GraphQL API changed. The generator contract changed as follows:

```typescript
interface RuntimeSettings {
  claude?: Record<string, unknown>; // model is ignored
  codex?: Record<string, unknown>;  // model is ignored
}

interface RuntimeSkills {
  required?: string[]; // constrains capabilities and provider
  optional?: string[]; // materialized but does not constrain
}

interface SkillFrontmatter {
  requires_capability?: string[];
  provider?: "claude" | "codex";
}

interface CapabilitiesJson {
  schema_version: 1;
  provider: "both" | "claude" | "codex";
  required_capabilities: string[];
  recommended_model: { claude?: string; codex?: string } | null;
  generated_from: string;
}
```

Generated outputs must not contain binding model keys in `settings.json` or `config.toml`. `capabilities.json` carries non-binding model hints through `recommended_model`.

## Database Changes

No database schema or migration changes.

## Security Considerations

The change preserves existing secret file mode handling. Removing generated model pins lowers launch risk by preventing copied template config from fighting the launcher supplied model. Capability metadata is generated from checked-in manifests and skill frontmatter, with no secret material.

The frontmatter parser now fails closed for malformed non-empty inline `requires_capability` declarations so a declared capability cannot be silently dropped into a broader provider surface.

## Performance Notes

No material performance impact. Work is bounded by the configured skill list for a runtime plus small TOML and frontmatter files. Hashing uses `runtime.toml` and required skill frontmatter only.

## Verification

- `python3 -m pytest tests/test_generate.py -q` passed with `9 passed in 0.07s` after commit `4713056`.
- Regression coverage includes quoted inline, unquoted inline, block list, and malformed inline `requires_capability` declarations.
- Regenerated `research`, `frontend`, `skill-matters`, `frontend-test-1`, and `transcript-matters` with `python3 bin/generate.py <runtime>`.
- All five generated `capabilities.json` files exist and have `provider = "both"`, `required_capabilities = []`, and `recommended_model = {"claude":"claude-opus-4-8","codex":"gpt-5.5"}`.
- `grep -rn '^model' runtimes/*/config.toml; grep -rn '"model"' runtimes/*/settings.json` returned empty output after regeneration.
- `git diff --check` passed before commit.

## Open Items

The five runtime manifests still use the legacy bare `skills = [...]` array and legacy `[settings.*].model` fields by design. Migrating manifests to `[skills]` and `[recommended_model]` is a later human curation step.

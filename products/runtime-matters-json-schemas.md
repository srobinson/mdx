# runtime-matters JSON Schemas

Status: draft  
Date: 2026-04-23

## Purpose

`runtime-matters` uses JSON files validated by JSON Schema for its durable
contracts.

Users interact with runtime material through agents and CLI commands. The file
formats are optimized for validation, agent edits, git diffs, generated docs,
sync safety, and runtime compilation.

## Home Layout

```text
RUNTIME_MATTERS_HOME/
  runtime-matters.json

  profiles/
    <profile-id>/
      profile.json

  skills/
    <skill-id>/
      skill.json
      SKILL.md

  mcp/
    <mcp-id>/
      mcp.json

  instructions/
    <instruction-id>/
      instruction.json
      *.md

  hooks/
    <hook-id>/
      hook.json

  runtime-settings/
    <runtime-setting-id>/
      runtime-setting.json

  sources/
    <source-id>/
      source.json
      imports/
        <kind>/
          <local-id>.json
      drift/
        <timestamp>/
          drift.json

  generated/
    indexes/
      catalog.json
    runtime-homes/
      <runtime-id>/
        <profile-id>/
          <build-hash>/
            runtime-manifest.json

  cache/
  logs/
  locks/
```

`profiles/`, `skills/`, `mcp/`, `instructions/`, `hooks/`,
`runtime-settings/`, and `sources/` are versionable. `generated/`, `cache/`,
`logs/`, and `locks/` are ignored by default.

## Schema Files

Suggested schema package layout:

```text
schemas/
  runtime-matters.common.schema.json
  runtime-matters.home.schema.json
  runtime-matters.source.schema.json
  runtime-matters.import.schema.json
  runtime-matters.skill.schema.json
  runtime-matters.mcp.schema.json
  runtime-matters.profile.schema.json
  runtime-matters.instruction.schema.json
  runtime-matters.hook.schema.json
  runtime-matters.runtime-setting.schema.json
  runtime-matters.runtime.schema.json
  runtime-matters.generated-runtime.schema.json
  runtime-matters.drift.schema.json
```

Each schema should set `additionalProperties: false` unless a field explicitly
allows runtime adapter specific data.

## Common Definitions

Common fields should be shared through `$defs`, not copied into every schema.

Draft shape:

```json
{
  "$id": "https://schemas.runtime-matters.dev/runtime-matters.common.schema.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$defs": {
    "id": {
      "type": "string",
      "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$"
    },
    "runtimeId": {
      "type": "string",
      "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "fileRef": {
      "type": "object",
      "required": ["path"],
      "additionalProperties": false,
      "properties": {
        "path": { "type": "string" },
        "role": { "type": "string" },
        "sha256": { "type": "string" }
      }
    },
    "requirement": {
      "type": "object",
      "required": ["kind", "name"],
      "additionalProperties": false,
      "properties": {
        "kind": {
          "type": "string",
          "enum": ["env", "binary", "runtime", "network", "credential"]
        },
        "name": { "type": "string" },
        "description": { "type": "string" },
        "required": { "type": "boolean", "default": true }
      }
    },
    "origin": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "sourceId": { "$ref": "#/$defs/id" },
        "sourceKind": { "type": "string" },
        "sourceLocator": { "type": "string" },
        "sourceRevision": { "type": "string" },
        "sourcePath": { "type": "string" },
        "sourceObjectId": { "type": "string" },
        "importedAt": { "$ref": "#/$defs/timestamp" }
      }
    }
  }
}
```

## Home Config

Path:

```text
runtime-matters.json
```

Purpose:

Defines the local home version, selected runtimes, registered defaults, and git
policy.

Draft fields:

```json
{
  "schemaVersion": "0.1.0",
  "homeId": "stuart-default",
  "defaultRuntime": "claude",
  "managedRuntimes": ["codex", "claude"],
  "git": {
    "required": true,
    "agentCommitsRequired": true
  },
  "createdAt": "2026-04-23T00:00:00Z",
  "updatedAt": "2026-04-23T00:00:00Z"
}
```

Required:

```text
schemaVersion
managedRuntimes
git
```

## Source

Path:

```text
sources/<source-id>/source.json
```

Purpose:

Records a source identity, locator, connector behavior, trust policy, native
tooling, and sync metadata.

Kinds:

```text
git-repository
web-catalog
local-runtime-home
local-directory
npm-package
runtime-plugin-package
```

Draft fields:

```json
{
  "id": "github-anthropics-skills",
  "kind": "git-repository",
  "locator": "https://github.com/anthropics/skills",
  "connector": {
    "kind": "source-skill",
    "id": "git-repository"
  },
  "trust": {
    "importAllowed": true,
    "syncAllowed": true
  },
  "nativeTools": [],
  "lastSeenRevision": "abc123",
  "createdAt": "2026-04-23T00:00:00Z",
  "lastSyncedAt": "2026-04-23T00:00:00Z"
}
```

For `skills.sh`:

```json
{
  "id": "web-skills-sh",
  "kind": "web-catalog",
  "locator": "https://skills.sh/",
  "connector": {
    "kind": "source-skill",
    "id": "skills-sh"
  },
  "nativeTools": [
    {
      "name": "skills",
      "runner": "npx",
      "package": "skills",
      "commands": ["find", "add", "list", "update"],
      "jsonOutput": ["list --json"]
    }
  ],
  "trust": {
    "importAllowed": true,
    "syncAllowed": true
  }
}
```

## Import Record

Path:

```text
sources/<source-id>/imports/<kind>/<local-id>.json
```

Purpose:

Tracks the relationship between a local imported entity and its source
baseline. Sync uses this to detect local dirtiness, upstream drift, and force
update behavior.

Draft fields:

```json
{
  "sourceId": "github-anthropics-skills",
  "localKind": "skill",
  "localId": "github-anthropics-skills-frontend-design",
  "localPath": "skills/github-anthropics-skills-frontend-design",
  "sourceObjectId": "frontend-design",
  "sourcePath": "skills/frontend-design",
  "sourceRevision": "abc123",
  "status": "clean",
  "baseline": {
    "revision": "abc123",
    "files": [
      {
        "path": "SKILL.md",
        "sha256": "sha256:..."
      },
      {
        "path": "skill.json",
        "sha256": "sha256:..."
      }
    ]
  },
  "importedAt": "2026-04-23T00:00:00Z",
  "lastCheckedAt": "2026-04-23T00:00:00Z"
}
```

Status enum:

```text
clean
locally_modified
upstream_changed
conflict
missing_local
missing_upstream
```

## Skill

Path:

```text
skills/<skill-id>/skill.json
```

Purpose:

Defines a skill available for runtime compilation.

Draft fields:

```json
{
  "id": "github-anthropics-skills-frontend-design",
  "kind": "skill",
  "name": "Frontend Design",
  "summary": "Frontend design guidance imported from anthropics/skills.",
  "runtimes": ["claude", "codex"],
  "files": [
    {
      "path": "SKILL.md",
      "role": "skill-instructions"
    }
  ],
  "triggers": [
    "frontend design",
    "build UI",
    "improve interface"
  ],
  "requirements": [],
  "origin": {
    "sourceId": "github-anthropics-skills",
    "sourceKind": "git-repository",
    "sourceLocator": "https://github.com/anthropics/skills",
    "sourceRevision": "abc123",
    "sourcePath": "skills/frontend-design",
    "sourceObjectId": "frontend-design"
  },
  "tags": ["frontend", "design"]
}
```

## MCP Server

Path:

```text
mcp/<mcp-id>/mcp.json
```

Purpose:

Defines an MCP server that can be rendered into supported runtimes.

Draft fields:

```json
{
  "id": "web-mcp-sh-vercel",
  "kind": "mcp",
  "name": "Vercel MCP",
  "summary": "MCP server for Vercel projects and deployments.",
  "runtimes": ["claude", "codex"],
  "transport": {
    "kind": "stdio",
    "command": "npx",
    "args": ["-y", "@vercel/mcp"]
  },
  "env": [
    {
      "name": "VERCEL_TOKEN",
      "required": true,
      "description": "Vercel API token."
    }
  ],
  "origin": {
    "sourceId": "web-mcp-sh",
    "sourceKind": "web-catalog",
    "sourceLocator": "https://mcp.sh/",
    "sourceObjectId": "vercel"
  },
  "tags": ["vercel", "deployments"]
}
```

## Instruction

Path:

```text
instructions/<instruction-id>/instruction.json
```

Purpose:

Defines reusable instruction material that profiles can include.

Draft fields:

```json
{
  "id": "strict-typescript",
  "kind": "instruction",
  "name": "Strict TypeScript",
  "summary": "Coding standards for strict TypeScript work.",
  "runtimes": ["claude", "codex"],
  "files": [
    {
      "path": "strict-typescript.md",
      "role": "instructions"
    }
  ],
  "scope": {
    "languages": ["typescript", "tsx"]
  },
  "tags": ["typescript", "standards"]
}
```

## Hook

Path:

```text
hooks/<hook-id>/hook.json
```

Purpose:

Defines a runtime hook that can be rendered where supported.

Draft fields:

```json
{
  "id": "session-log",
  "kind": "hook",
  "name": "Session Log",
  "summary": "Persist a short work log before ending a session.",
  "runtimes": ["claude", "codex"],
  "events": ["session-end"],
  "command": {
    "program": "runtime-matters",
    "args": ["log-session"]
  },
  "requirements": []
}
```

## Runtime Setting

Path:

```text
runtime-settings/<runtime-setting-id>/runtime-setting.json
```

Purpose:

Defines runtime specific configuration fragments.

Draft fields:

```json
{
  "id": "codex-safe-defaults",
  "kind": "runtime-setting",
  "name": "Codex Safe Defaults",
  "summary": "Default Codex settings for safe local work.",
  "runtime": "codex",
  "settings": {
    "approvalPolicy": "never",
    "sandboxMode": "danger-full-access"
  }
}
```

`settings` is runtime adapter specific and may allow additional properties.

## Profile

Path:

```text
profiles/<profile-id>/profile.json
```

Purpose:

A profile is the durable recipe for a configured runtime. A user can ask an
agent to create a runtime; `runtime-matters` stores that intent as a profile
and compiles it into a generated runtime home.

Draft fields:

```json
{
  "id": "platform-agent",
  "kind": "profile",
  "name": "Platform Agent",
  "summary": "Claude runtime for Linear, Supabase, orchestration, and strict Python and TypeScript work.",
  "runtimes": ["claude"],
  "skills": [
    "runtime-plugins-setup-repo",
    "runtime-plugins-sync-sources"
  ],
  "mcp": [
    "linear",
    "supabase"
  ],
  "instructions": [
    "strict-python",
    "strict-typescript"
  ],
  "hooks": [],
  "runtimeSettings": [],
  "requirements": [
    {
      "kind": "env",
      "name": "LINEAR_API_KEY",
      "required": true
    },
    {
      "kind": "env",
      "name": "SUPABASE_ACCESS_TOKEN",
      "required": true
    }
  ],
  "createdBy": "agent",
  "createdAt": "2026-04-23T00:00:00Z",
  "updatedAt": "2026-04-23T00:00:00Z"
}
```

## Runtime Target

Path:

```text
runtimes/<runtime-id>/runtime.json
runtimes/<runtime-id>/detect.json
runtimes/<runtime-id>/plugin.json
runtimes/<runtime-id>/launch.json
runtimes/<runtime-id>/mappings.json
```

Purpose:

Defines how `runtime-matters` detects a runtime, installs `runtime-plugins`,
renders generated runtime homes, and prints launch instructions.

Draft `runtime.json`:

```json
{
  "id": "claude",
  "displayName": "Claude Code",
  "status": "supported",
  "pluginInstall": "plugin.json",
  "detect": "detect.json",
  "launch": "launch.json",
  "mappings": "mappings.json"
}
```

Draft `plugin.json`:

```json
{
  "runtime": "claude",
  "install": {
    "command": "claude",
    "args": ["plugin", "install", "runtime-plugins"]
  },
  "verify": {
    "command": "claude",
    "args": ["plugin", "list"]
  }
}
```

## Generated Runtime Manifest

Path:

```text
generated/runtime-homes/<runtime-id>/<profile-id>/<build-hash>/runtime-manifest.json
```

Purpose:

Records the exact inputs and rendered files for a generated runtime home.

Draft fields:

```json
{
  "profileId": "platform-agent",
  "runtime": "claude",
  "buildHash": "abc1234",
  "inputs": {
    "profile": "profiles/platform-agent/profile.json",
    "skills": ["skills/runtime-plugins-setup-repo/skill.json"],
    "mcp": ["mcp/linear/mcp.json", "mcp/supabase/mcp.json"],
    "instructions": ["instructions/strict-python/instruction.json"]
  },
  "renderedFiles": [
    {
      "path": "CLAUDE.md",
      "sha256": "sha256:..."
    }
  ],
  "createdAt": "2026-04-23T00:00:00Z"
}
```

## Drift Record

Path:

```text
sources/<source-id>/drift/<timestamp>/drift.json
```

Purpose:

Records a sync review event when local dirtiness or upstream drift is detected.

Draft fields:

```json
{
  "sourceId": "github-anthropics-skills",
  "localKind": "skill",
  "localId": "github-anthropics-skills-frontend-design",
  "status": "conflict",
  "baselineRevision": "abc123",
  "upstreamRevision": "def456",
  "paths": {
    "baseline": "baseline/skills/frontend-design",
    "local": "local/skills/github-anthropics-skills-frontend-design",
    "upstream": "upstream/skills/frontend-design"
  },
  "recommendedActions": ["show-diff", "force-sync", "manual-edit"],
  "createdAt": "2026-04-23T00:00:00Z"
}
```

## Inventory Commands

Typed inventory commands are primary:

```bash
runtime-matters sources list
runtime-matters sources show <source-id>
runtime-matters skills list
runtime-matters skills show <skill-id>
runtime-matters mcp list
runtime-matters mcp show <mcp-id>
runtime-matters profiles list
runtime-matters profiles show <profile-id>
runtime-matters runtimes list
runtime-matters runtimes show <runtime-id>
```

`capabilities list` is a discovery and help surface, not the primary inventory
path:

```text
Capabilities are typed runtime material.

Try:
  runtime-matters skills list
  runtime-matters mcp list
  runtime-matters profiles list
  runtime-matters sources list
```

## Open Questions

- Should profile composition reference entity ids only, or allow inline
  constraints per reference?
- Should `requirements` be normalized into reusable top level entities?
- Should runtime adapter specs live in `runtime-catalog`, core, or both?
- Should `generated/indexes/catalog.json` be committed or ignored?
- What JSON Patch or edit protocol should agents use when changing manifests
  through CLI commands rather than direct file edits?

---
title: Knowledge Base Schema
type: reference
tags: [meta, schema, conventions]
summary: Frontmatter contract and conventions for ~/.mdx documents
status: active
created: 2026-02-20
updated: 2026-02-20
---

# ~/.mdx Knowledge Base Schema

## Directory Structure

```
~/.mdx/
├── research/          # Research findings, literature reviews, experiments
├── decisions/         # Architecture Decision Records (ADRs)
├── design/            # Design documents, RFCs, architecture docs
├── sessions/          # Session summaries, meeting notes
├── projects/          # Per-project status, context, onboarding
├── retrospectives/    # Post-mortems, retrospectives, lessons learned
├── reference/         # Stable reference material, guides, specs
└── _schema.md         # This file
```

Each category has a `_versions/` subdirectory for historical versions.

## Frontmatter Contract

### Required (author provides)

| Field     | Type     | Description                                    |
|-----------|----------|------------------------------------------------|
| `title`   | string   | Human-readable document title                  |
| `type`    | string   | Must match directory name. One of: research, decisions, design, sessions, projects, retrospectives, reference |
| `tags`    | string[] | Freeform tags for cross-cutting concerns        |
| `summary` | string   | One-line summary of the document               |
| `status`  | string   | One of: draft, active, superseded, archived    |

### Auto-managed (by skill)

| Field     | Type   | Description                                      |
|-----------|--------|--------------------------------------------------|
| `created` | string | ISO date, set from filesystem on first write     |
| `updated` | string | ISO date, set from filesystem on each write      |

### Optional

| Field        | Type     | Description                                    |
|--------------|----------|------------------------------------------------|
| `project`    | string   | Associated Helioy project (am, fmm, nancyr, etc.) |
| `related`    | string[] | Slugs of related documents                     |
| `confidence` | string   | One of: high, medium, low, speculative         |
| `supersedes` | string   | Slug of the document this replaces             |

## Filename Conventions

- **Kebab-case slugs**: `helioy-architecture.md`, `cli-wrapping-default.md`
- **No dates** in filenames (dates live in frontmatter)
- **No spaces** or special characters
- **No numeric prefixes** (ordering is by filesystem metadata)

## Versioning

- Current version = undecorated filename in its category directory
- Old versions live in `<category>/_versions/<slug>.v<N>.md`
- Typos and minor edits: edit in place (no version bump)
- Substantive revisions: copy current to `_versions/`, rewrite current
- Version numbers are sequential integers starting at 1

## Search

Documents are indexed by mdcontext for hybrid search (BM25 + semantic).
The `_versions/` directories are excluded from search indexing via `.mdcontextignore`.
Path-based filtering by category (e.g., `decisions/**`) works out of the box.
Frontmatter filtering (tags, status, project) requires the Helioy adapter layer.

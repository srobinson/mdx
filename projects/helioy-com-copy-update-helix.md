---
title: "helioy.com Landing Page: Updated Copy for Helix Architecture"
category: projects
tags: [helioy, identity, copy, helix, landing-page]
created: 2026-03-16
author: brand-guardian
status: draft-copy
---

# helioy.com: Updated Copy for Helix Architecture

The ecosystem has restructured. Helix is the agent-facing context API. Three context backends sit behind it. fmm, helioy-bus, and nancy remain as peer infrastructure tools. This document provides production-ready copy for the landing page.

---

## Updated Ecosystem Section

### Section Label
```
Ecosystem
```

### Section Title
```
One API for context.
Three tools for coordination.
```

### Section Description
```
Agents call helix. Helix routes to the right backend, curates the response,
and stays within the token budget. Code intelligence and agent coordination
run alongside as independent MCP servers.
```

### Ecosystem Diagram (ASCII, for what-diagram)

```html
<div class="what-diagram form-in">
  <span class="node">helix</span> <span class="edge">------------</span> <span class="label">unified context API</span><br>
  <span class="edge">&nbsp;&nbsp;|</span><br>
  <span class="edge">&nbsp;&nbsp;├──</span> <span class="node">context-matters</span> <span class="edge">-</span> <span class="label">structured memory</span><br>
  <span class="edge">&nbsp;&nbsp;├──</span> <span class="node">attention-matters</span> <span class="label">attention management</span><br>
  <span class="edge">&nbsp;&nbsp;└──</span> <span class="node">markdown-matters</span> <span class="label">document search</span><br>
  <br>
  <span class="node">fmm</span> <span class="edge">--------------</span> <span class="label">code topology</span><br>
  <span class="node">helioy-bus</span> <span class="edge">-------</span> <span class="label">agent coordination</span><br>
  <span class="node">nancy</span> <span class="edge">------------</span> <span class="label">task orchestration</span>
</div>
```

### Ecosystem Body Text

```html
<div class="what-text form-in">
  <p>
    AI agents burn tokens rediscovering what they already knew. They read files
    to understand structure. They rebuild context every session. They cannot
    share what they learn.
  </p>
  <p>
    <strong>Helix is the fix.</strong> A single context API that agents call
    with three commands: recall, save, conflicts. Behind it, three specialized
    backends handle structured memory, attention management, and document search.
    Tantivy retrieves candidates in sub-millisecond time. An LLM curates every
    read and every write. No noise accumulates.
  </p>
  <p>
    Code intelligence, agent coordination, and task orchestration run alongside
    as independent MCP servers. Install what you need. They reinforce each
    other: memory informs structure, structure guides coordination,
    coordination deposits better memory.
  </p>
</div>
```

---

## Updated Product Cards

### Card 1: helix (NEW)

```html
<div class="product-card form-in">
  <div class="product-card__name">helix</div>
  <div class="product-card__role">Context API</div>
  <div class="product-card__desc">
    Unified context interface for AI agents. Three commands: recall, save,
    conflicts. Tantivy retrieves candidates fast. An LLM curates every
    response: reranks, synthesizes, shapes to token budget. Agents never
    reference backend names. Context quality is measured, not assumed.
  </div>
  <div class="product-card__question">What context does the agent need right now?</div>
</div>
```

### Card 2: context-matters (updated description)

```html
<div class="product-card form-in">
  <div class="product-card__name">context-matters</div>
  <div class="product-card__role">Structured Memory</div>
  <div class="product-card__desc">
    Persistent structured memory. Stores facts, decisions, patterns, and
    lessons with metadata, tags, scopes, and confidence levels. Retrieval
    by geometric similarity, not keyword matching. A helix adapter.
  </div>
  <div class="product-card__question">What does the agent already know?</div>
</div>
```

### Card 3: attention-matters (NEW, replaces auto-memory concept)

```html
<div class="product-card form-in">
  <div class="product-card__name">attention-matters</div>
  <div class="product-card__role">Attention Management</div>
  <div class="product-card__desc">
    Attention and memory management for agent sessions. Tracks what matters
    now versus what mattered before. A helix adapter.
  </div>
  <div class="product-card__question">What should the agent focus on?</div>
</div>
```

### Card 4: markdown-matters (unchanged role, updated framing)

```html
<div class="product-card form-in">
  <div class="product-card__name">markdown-matters</div>
  <div class="product-card__role">Document Search</div>
  <div class="product-card__desc">
    Document indexing and semantic search across markdown collections.
    Returns meaning within a token budget, not raw text dumps. A helix adapter.
  </div>
  <div class="product-card__question">What do the docs say about this?</div>
</div>
```

### Card 5: fmm (unchanged)

```html
<div class="product-card form-in">
  <div class="product-card__name">fmm</div>
  <div class="product-card__role">Code Intelligence</div>
  <div class="product-card__desc">
    Structural code intelligence. Compiles codebases into precomputed
    topology so agents answer structural questions in O(1) without reading
    files. 5 fmm calls replace 30+ file reads.
  </div>
  <div class="product-card__question">What does the codebase structurally contain?</div>
</div>
```

### Card 6: helioy-bus (unchanged)

```html
<div class="product-card form-in">
  <div class="product-card__name">helioy-bus</div>
  <div class="product-card__role">Coordination</div>
  <div class="product-card__desc">
    Inter-agent message passing. Agents send messages, share context, and
    coordinate without a central scheduler. Choreography over orchestration.
  </div>
  <div class="product-card__question">How do agents talk to each other?</div>
</div>
```

### Card 7: nancy (unchanged)

```html
<div class="product-card form-in">
  <div class="product-card__name">nancy</div>
  <div class="product-card__role">Orchestration</div>
  <div class="product-card__desc">
    Multi-agent task orchestration. Distributes work across agents based on
    accumulated context. Agents coordinate action from shared memory, not
    rigid pipelines.
  </div>
  <div class="product-card__question">How does context become coordinated action?</div>
</div>
```

---

## Products Section Title Update

```
The stack
```

No change needed. "The stack" still works with seven cards.

---

## Brand Compliance Notes

- All copy follows the five voice principles: say less, show the mechanism, respect time, be specific, warm authority
- "helix" follows the naming convention: lowercase, descriptive, human
- "A helix adapter" on the three backend cards establishes hierarchy without marketing language
- "Three commands: recall, save, conflicts" is specific and measurable
- "Context quality is measured, not assumed" shows the mechanism (comparison mode)
- No prohibited language, no anthropomorphization, no exclamation marks
- The attention-matters card is deliberately sparse pending fuller product definition

---

*Brand Guardian. 2026-03-16.*

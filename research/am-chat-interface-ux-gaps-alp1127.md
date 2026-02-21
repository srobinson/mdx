---
title: AM Standalone Chat Interface -- UX Gaps (ALP-1127)
type: research
tags: [ux-research, am, chat-interface, geometric-memory, alp-1127]
summary: Eight UX gaps identified in the ALP-1127 issue tree that engineering specs did not address, spanning empty states, onboarding, mental model, accessibility, and feedback controls.
status: active
source: ux-researcher
confidence: high
created: 2026-03-11
updated: 2026-03-11
---

## Executive Summary

The ALP-1127 issue tree (AM Standalone Chat Interface) defines a technically complete architecture -- HTTP/SSE backend, Next.js frontend, Memory Explorer sidebar -- but leaves eight user-facing scenarios undefined. The highest-severity gaps are: (1) no empty state design for first-launch with an empty `brain.db`, (2) no first-run onboarding flow for API key configuration, and (3) no user-facing mental model for the Memory Explorer's geometric memory concepts. These gaps will produce a broken first impression for every new user if left unaddressed.

---

## Detailed Findings

### Issue Scope Reviewed

| Issue | Title | State |
|-------|-------|-------|
| ALP-1127 | AM Standalone Chat Interface | Todo |
| ALP-1128 | AM HTTP/SSE API Layer [backend-engineer] | Todo |
| ALP-1129 | Chat Interface [frontend-engineer] | Todo |
| ALP-1130 | Memory Explorer [frontend-engineer] | Todo |

---

### Finding 1: Empty State Undefined (HIGH)

**Issues affected:** ALP-1127, ALP-1129, ALP-1130

No sub-issue defines what the interface shows on first launch with an empty `brain.db`. Affected surfaces:
- Episode list sidebar (ALP-1130): empty list with no copy
- Memory stats header: zeros with no explanation
- Per-message recall panel (ALP-1129): no context to display

The original `dae_v072.html` reference implementation had the same gap. The empty state is the first experience for every new user and the moment they decide whether the product is broken or simply unfilled.

**Inference (medium confidence):** Users who encounter blank panels with no copy will assume misconfiguration, not "I need to add content first."

---

### Finding 2: Onboarding Flow Absent (HIGH)

**Issues affected:** ALP-1127, ALP-1129

ALP-1129 scopes "Settings: LLM provider, API key, model selection" as a single line item. No first-run flow is defined. A user who opens the chat with no API key configured cannot send a message. The current spec produces a blank composer with no explanation of what to do.

The friction is not optional -- the OpenRouter/Claude/GPT/Gemini key is required before any functionality works.

---

### Finding 3: Memory Explorer Mental Model Undefined (HIGH)

**Issues affected:** ALP-1130

The Memory Explorer exposes AM's internal data model using technical vocabulary: "neighborhoods," "epochs," "supersession," "activation counts," "IDF weights." These terms are accurate but opaque to non-AM-expert users.

**Recommended user-facing vocabulary mapping:**
| AM term | User-facing label |
|---------|-------------------|
| Episode | Memory |
| Neighborhood | Idea cluster |
| Salient | Conscious memory |
| Activation count | How often recalled |
| Superseded | Replaced |
| IDF weight | (hide entirely) |

This vocabulary should be consistent across the Memory Explorer and the Chat Interface memory panel.

---

### Finding 4: Feedback Controls Assume Expert Knowledge (HIGH)

**Issues affected:** ALP-1130

Boost/demote controls on recalled neighborhoods have no user education layer. Demoting a neighborhood permanently decreases its recall probability via Kuramoto coupling. This is a persistent, non-obvious consequence of a UI action with no affordance explaining it.

**Recommendation:** Tooltips on each control with plain-language effect description. Confirmation step for demote. Post-action confirmation state.

---

### Finding 5: Conversation History Not Scoped (MEDIUM)

**Issues affected:** ALP-1127, ALP-1129

AM stores distilled memory (episodes) from conversations, not raw chat transcripts. A user who refreshes the page loses the visible conversation thread even though AM recalls the semantic content. The distinction between "AM remembers" and "the chat thread is gone" is non-obvious and will produce confusion.

**Options:**
- (a) Persist chat transcript in localStorage/IndexedDB -- higher scope
- (b) Ephemeral sessions with visible indicator ("New session -- AM remembers context from previous conversations") -- lower scope, more honest

---

### Finding 6: Streaming Error States Undefined (HIGH)

**Issues affected:** ALP-1129

SSE streaming is scoped but error states are not. Undefined scenarios:
- LLM provider rate-limit error mid-stream
- `am serve` crash during streaming
- Network drop during SSE delivery

Partially rendered messages with no resolution state leave users uncertain whether to wait, retry, or assume failure.

---

### Finding 7: Document Upload UX Underspecified (MEDIUM)

**Issues affected:** ALP-1129

"Document upload triggering am_ingest" is one line in the scope. Missing definitions: supported file formats, file size limits, ingestion progress feedback (am_ingest is not instantaneous for large documents), success confirmation with episode count, failure handling (unsupported format, parse error, duplicate content).

---

### Finding 8: Accessibility -- Dark Theme + Gold Highlights (MEDIUM)

**Issues affected:** ALP-1129, ALP-1130

Dark-only theme with gold salient highlights carries two accessibility risks:
1. **Contrast ratio:** Gold on dark backgrounds may fail WCAG AA (4.5:1) depending on exact shades. The `dae_v072.html` reference was not audited.
2. **Color-only encoding:** Gold highlights encode "salient." No alternative encoding (icon, underline, bold) is defined. Approximately 8% of males have color vision deficiency that may prevent distinguishing gold from standard text.

---

## Recommendations (Prioritized)

| Priority | Recommendation | Tag | Issue |
|----------|---------------|-----|-------|
| HIGH | Define empty state copy and CTA for all three empty surfaces | design, content | ALP-1127 |
| HIGH | Define first-run flow: API key prompt before composer activates | design, engineering | ALP-1129 |
| HIGH | Define user-facing vocabulary mapping for Memory Explorer | design, content | ALP-1130 |
| HIGH | Add tooltips + confirmation to boost/demote controls | design | ALP-1130 |
| HIGH | Define streaming error states with retry affordance | engineering, design | ALP-1129 |
| MEDIUM | Decide and document conversation history persistence strategy | engineering | ALP-1129 |
| MEDIUM | Define document upload UX: formats, progress, success/error | design, engineering | ALP-1129 |
| MEDIUM | Audit gold/dark contrast ratio; add secondary salient encoding | design | ALP-1129, ALP-1130 |

---

## Sources Consulted

- Linear issue tree: ALP-1127, ALP-1128, ALP-1129, ALP-1130 (fetched 2026-03-11)
- Reference implementation: `dae_v072.html` (described in ALP-1127 description)
- Prior research: `~/.mdx/research/ai-chat-ui-kits-react-2025.md`
- AM architecture: CLAUDE.md (am-core module map)

---

## Open Questions

1. Is the target user exclusively Stuart (personal tool) or a broader developer audience? The answer changes the severity of onboarding friction significantly.
2. Is dark-only theme a hard constraint or a preference? If preference, a light mode or system-preference-aware theme resolves the accessibility concern more cleanly than contrast auditing.
3. What is the intended retention policy for the chat transcript? This determines whether option (a) or (b) for conversation history is more appropriate.
4. Does `am serve` handle LLM API key storage server-side or does the frontend forward user-entered keys per-request? The answer has security and UX implications.

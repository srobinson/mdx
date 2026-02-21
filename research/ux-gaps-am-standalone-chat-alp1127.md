---
title: UX Gaps - AM Standalone Chat Interface (ALP-1127)
type: research
tags: [ux-research, attention-matters, chat-interface, onboarding, empty-state, accessibility]
summary: Six UX gaps identified in ALP-1127 issue tree that engineering specs did not address, two high severity.
status: active
source: ux-researcher
confidence: high
created: 2026-03-11
updated: 2026-03-11
---

## Executive Summary

Reviewed the full ALP-1127 issue tree (master + ALP-1128 backend, ALP-1129 chat frontend, ALP-1130 memory explorer) for UX gaps. Engineering specs are technically sound but omit six user-facing concerns. The two highest-severity gaps - conversation history persistence and API key onboarding - will each produce failure or confusion on first use if unaddressed before implementation.

---

## Detailed Findings

### GAP-1: Conversation history not scoped or explicitly deferred [HIGH]

**Source**: ALP-1127, ALP-1129 - absence of any persistence spec for chat thread

No sub-issue, no acceptance criterion, and no mention in the architecture diagram addresses whether chat conversation history persists across browser sessions. The current architecture routes chat through the AM backend and streams responses, but the thread itself lives only in client-side React state.

The product premise is "interact with your memory system." A system that forgets its own conversations creates a jarring contradiction. Users who invest effort in a long research session and return the next day to an empty thread will interpret this as data loss, not a scoping decision.

**Recommendation (high impact, low effort):** Explicit decision record required. Options:
- Store conversation history in brain.db as a special episode type (uses existing infrastructure)
- Store in localStorage (simple, no backend change, persists per-browser)
- Explicitly defer with a visible UI notice: "This session will not be saved"

The choice matters less than making it intentionally. Silence here ships a defect.

---

### GAP-2: First-launch onboarding with no API key [HIGH]

**Source**: ALP-1129 scope item "Settings: LLM provider, API key, model selection"

The settings feature is scoped but no first-launch flow is defined. A user who installs and opens the chat app for the first time has no API key configured. The LLM proxy endpoint (ALP-1128) will fail or error. The chat interface will appear functional but produce nothing.

There is no specified:
- Detection of missing key on mount
- Setup state to render instead of the chat thread
- Explanatory copy about OpenRouter (what it is, why it is required, where to get a key)
- Key validation before dismissing setup

**Recommendation:**
Minimum viable first-launch spec:
1. On mount, check for stored provider + API key
2. If absent: render APIKeySetup component instead of ChatThread
3. Copy: "Connect a model to start chatting with your memory. AM works with Claude, GPT-4, and Gemini via OpenRouter."
4. Fields: provider dropdown, API key input, "Validate & Connect" button
5. On validate: one test call to OpenRouter before saving
6. On success: transition to empty chat state with starter prompts

This is a 1-2 day frontend task that prevents the most common first-use failure.

---

### GAP-3: Empty state undefined for Chat and Memory Explorer [MEDIUM]

**Source**: ALP-1129 and ALP-1130 - no empty state component or copy specified

Two empty states are unaddressed:

**Chat (ALP-1129):** After completing API key setup, the Thread component renders with no messages. The user has no indication of what to type, what AM can answer, or what distinguishes this from a generic chatbot.

Define: starter prompt suggestions demonstrating AM's recall capability ("What have I been working on this week?", "Summarize what I know about X"), a brief welcome message, and a distinct sub-state for when brain.db is empty (fresh install) that surfaces the document upload action as the logical first step.

**Memory Explorer (ALP-1130):** Episode list sidebar, stats header, and neighborhood views all render zero content. Zero is not designed - it defaults to whatever the component library renders for empty arrays.

Define: "Your memory is empty" state with an ingest prompt, placeholder stats ("0 episodes - start a conversation or upload a document to build your memory"), and disabled/grayed feedback controls rather than absent ones.

---

### GAP-4: Memory Explorer vocabulary is implementation-level [MEDIUM]

**Source**: ALP-1130 scope - "neighborhoods," "epochs," "supersession," "activation counts," "feedback signals"

The Memory Explorer spec exposes AM's internal data model vocabulary directly in the UI. These terms are precise and meaningful to the system author but opaque to any other user.

| Implementation term | User-facing candidate | Notes |
|---|---|---|
| neighborhood | topic cluster | Groups related memories around a concept |
| epoch | generation / version | Changes when memories are superseded |
| activation count | times recalled | How often this memory has surfaced |
| supersession | updated / replaced | A newer memory has replaced this one |
| feedback signal | your rating | Boost/demote as expressed by user action |
| am_query_index result score | relevance score | Already intuitive, keep as-is |

**Recommendation:** Define a user-facing terminology layer before ALP-1130 implementation begins. This is a content decision, not a component decision - 1 hour of copy work prevents 3 days of component refactoring later.

---

### GAP-5: Boost/demote feedback controls assume engineering mental model [MEDIUM]

**Source**: ALP-1129 ("memory operations (salient marking, feedback)"), ALP-1130 ("Feedback controls: boost/demote recalled neighborhoods")

"Boost" and "demote" appear in both frontend specs. Neither issue defines:
- What label/copy to render on the button
- What tooltip or help text explains the action
- What visual confirmation follows a click
- Whether the action is reversible and how

**Problems with "boost/demote":**
- "Boost" carries social media connotations (paid reach amplification)
- "Demote" implies a management hierarchy
- Neither indicates what changes for the user in future sessions
- No confirmation means users cannot tell whether the action registered

**Recommended copy approach:**
- Button labels: "Helpful" / "Not relevant" (or thumb up/down icons with these labels)
- Tooltip: "Tell AM this memory was useful - it will surface more often in future sessions"
- After click: brief inline confirmation ("Got it - will prioritize this memory") that fades after 2s

---

### GAP-6: No accessibility specification [LOW-MEDIUM]

**Source**: ALP-1129 and ALP-1130 - dark theme, gold highlights, collapsible panels all unspecified for accessibility

Three specific concerns:

**Contrast (ALP-1129, ALP-1130):** Gold salient highlights on a dark background must meet WCAG AA (4.5:1 for normal text, 3:1 for large text). Gold (#FFD700 or similar) on dark gray (#1a1a1a) can pass or fail depending on exact values. Validate with a contrast checker before finalizing the color token. Do not assume gold-on-dark is safe.

**Keyboard navigation (ALP-1129):** Collapsible memory context panels must support:
- `aria-expanded` state reflecting open/closed
- `aria-controls` linking trigger to panel
- Enter/Space to toggle from keyboard
- Focus must not become trapped inside collapsed panels

**Screen reader (ALP-1129):** Streamed LLM responses delivered character-by-character must use `aria-live="polite"` on the output container so screen readers announce completed sentences rather than every character.

**Dark-only theme:** Not inherently inaccessible, but the decision to ship without light mode support must be documented. Some users with photosensitivity or specific visual impairments require light backgrounds. Document as a known limitation with a future roadmap item.

---

## Recommendations

| Priority | Gap | Effort | Owner |
|---|---|---|---|
| High | Conversation history: make an explicit decision | Low | Product (Stuart) |
| High | First-launch onboarding flow | Low-Medium | ALP-1129 |
| Medium | Empty states: chat + memory explorer | Low | ALP-1129, ALP-1130 |
| Medium | Terminology mapping: user-facing vocabulary | Low | ALP-1130 |
| Medium | Feedback controls: copy + confirmation | Low | ALP-1129, ALP-1130 |
| Low-Medium | Accessibility baseline | Low | ALP-1129, ALP-1130 |

---

## Sources Consulted

- ALP-1127 (master issue + architecture)
- ALP-1128 (HTTP/SSE API Layer spec)
- ALP-1129 (Chat Interface spec)
- ALP-1130 (Memory Explorer spec)
- AM memory context: boost/demote mechanics, feedback loop architecture, brain.db episode model
- WCAG 2.1 AA contrast requirements (4.5:1 normal text, 3:1 large text)

## Open Questions

1. Who is the user population beyond Stuart? Single-user tool or intended for broader distribution? Shapes how much onboarding investment is warranted.
2. Does brain.db already have a mechanism for storing chat history (special episode type), or would that require a schema change?
3. Is OpenRouter the only API key flow, or will direct provider keys (Anthropic, OpenAI) also be supported? Affects onboarding copy substantially.
4. What is the reversibility model for boost/demote? Can a user un-boost a memory? The backend behavior should drive the UI copy.

---
title: "UX Feedback Coverage Analysis - ALP-1127 Issue Tree"
type: research
tags: [ux-research, attention-matters, gap-analysis, alp-1127, alp-1153, coverage]
summary: "Cross-referencing all UX researcher and UX designer feedback from Linear comments against the two research documents (ux-gaps-am-standalone-chat-alp1127.md and alp-1153-warroom-review-report.md). 28 discrete UX feedback items identified across sources. 14 fully captured, 6 partially captured, 8 missing from research docs entirely."
status: active
created: 2026-03-11
---

# UX Feedback Coverage Analysis

## 1. Methodology

Three source categories were cross-referenced:

1. **Research Document A** - `ux-gaps-am-standalone-chat-alp1127.md` (6 gaps identified, pre-implementation UX review)
2. **Research Document B** - `alp-1153-warroom-review-report.md` (warroom review with 4 critical bugs, 3 contract mismatches, 3 implementation gaps, 9 minor items)
3. **Linear Comments** - All comments on ALP-1127, ALP-1128, ALP-1129, ALP-1130, and ALP-1153 containing UX researcher or UX designer feedback

Linear comment sources with UX content:
- ALP-1127: 4 UX review comments (layout architecture, top-level gaps, gap review, parent review)
- ALP-1129: 2 UX review comments (chat interface gaps, chat UX gaps)
- ALP-1130: 2 UX review comments (memory explorer gaps, explorer UX gaps)
- ALP-1153: 1 UX designer pass-2 review, 1 frontend/backend contract sync with UX implications

---

## 2. Already Captured

These items appear in one or both research documents with sufficient specificity to act on.

| # | UX Feedback Item | Source(s) in Linear | Captured In |
|---|---|---|---|
| 1 | Conversation history persistence gap | ALP-1127 (3 comments) | Doc A (GAP-1) |
| 2 | First-launch API key onboarding flow | ALP-1127 (2 comments), ALP-1129 (2 comments) | Doc A (GAP-2) |
| 3 | Empty state for Chat (fresh brain.db) | ALP-1127 (2 comments), ALP-1129 (1 comment) | Doc A (GAP-3) |
| 4 | Empty state for Memory Explorer | ALP-1127 (1 comment), ALP-1130 (2 comments) | Doc A (GAP-3) |
| 5 | Memory Explorer vocabulary is implementation-level | ALP-1127 (2 comments), ALP-1130 (2 comments) | Doc A (GAP-4) |
| 6 | Boost/demote feedback copy and confirmation | ALP-1127 (2 comments), ALP-1129, ALP-1130 | Doc A (GAP-5) |
| 7 | Accessibility: contrast ratios (gold on dark) | ALP-1127, ALP-1129, ALP-1130 | Doc A (GAP-6) |
| 8 | Accessibility: keyboard navigation for collapsible panels | ALP-1129 | Doc A (GAP-6) |
| 9 | Accessibility: aria-live for streamed responses | ALP-1129 | Doc A (GAP-6) |
| 10 | SalientText component not wired into message renderer | ALP-1153 (frontend, UX designer) | Doc B (CRIT-1) |
| 11 | FeedbackButton bypasses shared component | ALP-1153 (frontend, UX designer) | Doc B (CRIT-2) |
| 12 | OpenRouter request not canceled on client disconnect | ALP-1153 (backend) | Doc B (CRIT-3) |
| 13 | Episode type missing is_conscious field | ALP-1153 (all reviewers) | Doc B (CM-1) |
| 14 | Episode neighborhood retrieval architecturally wrong | ALP-1153 (frontend, backend, contract) | Doc B (CM-3) |

---

## 3. Partially Captured

These items are mentioned in research docs but with insufficient specificity, or the Linear comments contain detail that the research docs omit.

| # | UX Feedback Item | What Linear Says | What Research Docs Say | Gap |
|---|---|---|---|---|
| 15 | **Dark-only theme as explicit decision** | ALP-1127 parent review and ALP-1130 review both flag this. ALP-1130 UX researcher adds that color-only encoding of salient content excludes ~8% of males with color vision deficiency. Recommends secondary encoding (icon, underline). | Doc A (GAP-6) mentions documenting dark-only as a known limitation. | Doc A does not mention **color-only encoding** as a distinct accessibility problem. The secondary encoding recommendation (star icon or underline for salient highlights) is absent from both docs. This is a separate concern from contrast ratios. |
| 16 | **Feedback controls: scope ambiguity in Explorer** | ALP-1130 comment specifies that in the Explorer context, the action target is ambiguous: does feedback apply to a single neighborhood, all neighborhoods in an episode, or the episode itself? Recommends showing before/after activation count. | Doc A (GAP-5) covers copy and confirmation but treats Chat and Explorer feedback as the same problem. | The Explorer-specific scope ambiguity (what exactly is being boosted/demoted) is not addressed. The before/after activation count update recommendation is absent. |
| 17 | **Score thresholds and display** | ALP-1153 UX designer flags as critical bug: code uses integer thresholds (7/4) vs spec (0.7/0.4). ALP-1130 UX researcher recommends hiding raw scores entirely, using visual ranking or plain-language labels instead. ALP-1153 contract sync reveals scores are unbounded positive f64 (not 0-1). | Doc B (M-8, M-9) captures the calibration need and relative rank recommendation. | The UX researcher's recommendation to hide raw scores entirely is not captured. The fundamental question of whether to show numerical scores at all is unaddressed. |
| 18 | **Design tokens: single source** | ALP-1127 parent review provides a complete 13-token CSS spec for `tokens.css` with exact hex values. | Doc B confirms tokens.css passes in the ALP-1153 UX designer review. | The token spec itself was acted on (tokens.css exists and passes), but neither research doc preserves the original token recommendation as a reference. Not a gap per se, but the design decision is undocumented outside the Linear comment. |
| 19 | **Responsive behavior** | ALP-1127 layout review defines three breakpoints (>=1024, <1024, <768) with specific collapse behaviors. ALP-1153 UX designer flags the breakpoint bug (sm: 640px vs md: 768px). | Doc B (M-1) captures the breakpoint mismatch but not the full responsive spec. | The three-tier responsive behavior spec from the ALP-1127 layout review is not preserved in either research doc. Only the narrow breakpoint bug is noted. |
| 20 | **API key storage security expectations** | ALP-1127 top-level gaps comment (ux-researcher) flags that key storage location is unspecified. Users expect secure handling. Recommends disclosing storage location in UI ("Keys stored locally in your browser, never sent externally") and disclosing if keys are forwarded to am serve backend. | Doc A (GAP-2) covers the onboarding flow but not the security disclosure. | The security transparency requirement is absent from both docs. Where keys are stored and whether they transit through the backend are unaddressed product decisions. |

---

## 4. Missing

These UX feedback items exist in Linear comments but are not reflected in either research document.

| # | UX Feedback Item | Source | Severity | Detail |
|---|---|---|---|---|
| 21 | **Streaming error states undefined** | ALP-1129 UX researcher | HIGH | Three failure scenarios with no defined UI: rate-limit error mid-stream, am serve crash during streaming, network drop during SSE. Partially rendered messages with no resolution state leave users uncertain. Recommendation: visible error indicator on the message, retry action, explanation of failure type. |
| 22 | **Document upload UX severely underspecified** | ALP-1129 UX researcher | MEDIUM | Scoped as a single line item. Missing: supported file formats, file size limits, ingestion progress feedback, success confirmation with episode count, failure handling (unsupported format, parse error, duplicate). |
| 23 | **Salient tag mental model gap** | ALP-1129 UX researcher | MEDIUM | Users will not understand why certain phrases are highlighted gold. Recommends a tooltip or info affordance on the first salient highlight: "AM marked this phrase as important - it will influence future memory recall." A teachable moment, not a tutorial. |
| 24 | **LLM provider switching mid-session** | ALP-1129 UX researcher | LOW | Behavior when switching provider/model during an active conversation is undefined. Does context carry over? Recommend: disable settings during active conversation, or show "Takes effect on next session" label. |
| 25 | **Sidebar navigation between Episodes and Search** | ALP-1127 parent UX review | MEDIUM | How users switch between the two sidebar views (Episodes list and Memory Search) was unresolved at spec time. Recommended: two tabs pinned to sidebar top with state persisting via localStorage. ALP-1153 pass-2 confirms this was implemented and passes, but the original gap and design rationale are not documented in either research doc. |
| 26 | **Chat-first vs sidebar-first default** | ALP-1127 parent UX review | MEDIUM | Product paradigm question: should sidebar default open or closed? UX review recommended closed with a narrow icon rail (32px), two icons (Episodes, Search), keyboard shortcut Cmd+\\. ALP-1153 confirms implemented and passing. Neither research doc captures the design rationale. |
| 27 | **Memory panel vs sidebar spatial conflict** | ALP-1127 layout review | MEDIUM | Two memory surfaces exist: per-message memory context panel (ALP-1138) and sidebar episode memory (ALP-1142). Both show AM memory in different formats. Visual hierarchy and user mental model for distinguishing them is undefined. |
| 28 | **Mode switch system message missing** | ALP-1153 UX designer pass-2 | LOW-MEDIUM | Switching between Explorer and Assistant modes emits no signal in the chat thread. Users cannot tell why assistant behavior changed. Flagged as a fail in pass-2 but absent from the warroom review report's action items. |

---

## 5. Actionable Items Needing New Linear Issues

Items from the "Missing" and "Partially Captured" categories that are not tracked in any existing Linear issue and require new work.

### High Priority

**A. Streaming error states (item 21)**
Define error state presentation for three SSE failure scenarios: provider rate-limit, server crash, network drop. Minimum: error indicator on partially rendered message, retry button, failure type explanation. This is a frontend spec + implementation task for ALP-1129 scope.

**B. API key storage security disclosure (item 20)**
Product decision required: where are API keys stored? Are they forwarded to the am serve backend for LLM proxying? UI must disclose storage location. One-line copy addition to settings, but requires a product decision first.

### Medium Priority

**C. Document upload UX spec (item 22)**
Define: accepted file formats (filter in file picker), file size limits, ingestion progress indicator, success state with episode/token count, failure handling for unsupported formats and parse errors.

**D. Salient highlight teachable moment (item 23)**
Add tooltip or info affordance on first salient highlight encounter. Copy: "AM marked this phrase as important - it will influence future memory recall." Small frontend task, large comprehension impact.

**E. Color-only encoding for salient content (item 15)**
Add secondary visual encoding to salient highlights (subtle icon, underline, or bold) so gold color is not the sole signal. Accessibility requirement distinct from contrast ratios.

**F. Memory panel vs sidebar mental model (item 27)**
Define the visual hierarchy and user mental model for distinguishing per-message memory context (inline panel) from sidebar episode memory (explorer). Content/copy task.

**G. Feedback scope clarity in Explorer (item 16)**
Specify whether boost/demote in the Explorer applies to a single neighborhood, all neighborhoods in an episode, or the episode. Show activation count change after feedback action.

### Low Priority

**H. LLM provider switching mid-session (item 24)**
Define behavior or add "Takes effect on next session" label.

**I. Mode switch system message (item 28)**
Inject a system message into the chat thread when switching between Explorer and Assistant modes.

---

## 6. Summary

| Category | Count | Coverage |
|---|---|---|
| Already captured | 14 | Both research docs combined cover the critical and contractual issues well |
| Partially captured | 6 | Details present in Linear but insufficiently reflected in research docs |
| Missing entirely | 8 | UX feedback exists in Linear comments with no reflection in research docs |
| **Total discrete UX items** | **28** | |

The two research documents together provide strong coverage of the structural and contractual gaps (type mismatches, wiring bugs, contract alignment). Where coverage falls short is on **interaction design details** that UX researchers raised: streaming failure states, document upload UX, salient highlight comprehension, security transparency, and the spatial relationship between the two memory surfaces. These are not engineering bugs but product design decisions that remain unresolved.

The highest-impact uncaptured item is **streaming error states** (item 21). A user whose LLM request fails mid-stream sees a partially rendered message with no explanation, no retry path, and no resolution. This will occur in production usage with rate-limited API keys and is a first-impression failure.

---

## Sources

- `~/.mdx/research/ux-gaps-am-standalone-chat-alp1127.md` (Research Doc A)
- `~/.mdx/research/alp-1153-warroom-review-report.md` (Research Doc B)
- ALP-1127 Linear comments (4 UX reviews, 6 orchestrator messages)
- ALP-1128 Linear comments (2 backend reviews, no UX content)
- ALP-1129 Linear comments (2 UX reviews, 1 frontend review)
- ALP-1130 Linear comments (2 UX reviews, 1 frontend review)
- ALP-1153 Linear comments (1 UX designer pass-2 review, 1 backend review, 1 frontend review, 1 contract sync)

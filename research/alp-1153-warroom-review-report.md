---
title: "ALP-1127 AM Standalone Chat Interface - Warroom Review Report"
type: research
tags: [attention-matters, warroom, review, alp-1127, frontend, backend, contract]
summary: "Second-pass validation of ALP-1127 (AM Standalone Chat Interface). 8 of 15 issues pass. 7 fail with 4 critical bugs, 3 contract mismatches, and 12 minor polish items."
status: active
source: warroom-review
confidence: high
created: 2026-03-11
---

# ALP-1127 Warroom Review Report

## 1. Executive Summary

The AM Standalone Chat Interface is structurally sound but not merge-ready. Of 15 reviewed issues across frontend and backend, **8 pass and 7 fail**. The failures cluster around three areas: frontend/backend type contract mismatches (Episode type missing fields, error field naming, missing endpoint), incomplete feature wiring (SalientText built but unused, FeedbackButton bypassing shared component), and a backend resource leak (OpenRouter requests not canceled on client disconnect). Four items are critical blockers. The remaining gaps are UX polish that can ship in a fast-follow.

**Verdict: HOLD - fix 4 critical bugs and 3 contract mismatches before merge.**

### Scorecard

| Issue    | Area              | Verdict | Blocker? |
|----------|-------------------|---------|----------|
| ALP-1131 | Backend config    | PASS    |          |
| ALP-1132 | Backend episodes  | FAIL    | Yes      |
| ALP-1133 | Backend SSE       | FAIL    | Yes      |
| ALP-1134 | Backend errors    | PASS*   | Pending  |
| ALP-1135 | FE scaffolding    | PASS    |          |
| ALP-1136 | FE SSE client     | PASS    |          |
| ALP-1137 | FE salient text   | FAIL    | Yes      |
| ALP-1138 | FE chat feedback  | FAIL    | Yes      |
| ALP-1139 | FE settings       | PASS    |          |
| ALP-1140 | FE import/export  | PASS    |          |
| ALP-1141 | FE system health  | PASS    |          |
| ALP-1142 | FE episode list   | FAIL    | Yes      |
| ALP-1143 | FE episode detail | FAIL    | Yes      |
| ALP-1144 | FE search         | PASS    |          |
| ALP-1145 | FE feedback comp  | PASS    |          |

*ALP-1134 passes structurally but has an error field name mismatch requiring a one-line backend fix.

---

## 2. Critical Bugs

### CRIT-1: SalientText component wired but never imported (ALP-1137)

`SalientText` was built as a standalone component but is never imported or used in `message.tsx`. Raw `<salient>` tags render as literal text in the chat output. This is the core differentiator of the AM chat experience. Users see broken markup instead of highlighted memory-linked text.

**Owner:** Frontend
**Fix:** Import `SalientText` in `message.tsx` and wire it into the markdown/content renderer to intercept `<salient>` tags.

### CRIT-2: Chat FeedbackButton bypasses shared component (ALP-1138)

The inline `FeedbackButton` in the chat view is a separate implementation that does not use the shared `FeedbackButtons` component from ALP-1145. Three behaviors are missing: demote confirmation dialog, "Memory updated" confirmation toast, and user-visible error state on failure.

**Owner:** Frontend
**Fix:** Replace the inline `FeedbackButton` with the shared `FeedbackButtons` component from ALP-1145, or extract the missing behaviors (confirmation, error handling) into the inline variant.

### CRIT-3: OpenRouter request not canceled on client disconnect (ALP-1133)

When a client disconnects mid-stream, the backend continues reading from OpenRouter for up to 120 seconds. This wastes API credits on responses nobody will receive.

**Owner:** Backend
**Fix:** Wrap the SSE relay loop in `tokio::select!` between the OpenRouter read and a client disconnect signal. On disconnect, abort the upstream request.

### CRIT-4: Context event JSON schema undefined (ALP-1133)

The `event: context` SSE payload shape is not formally defined in the ALP-1133 spec. The backend engineer provided the expected shape (metrics, recalled_ids, token_estimate, index), but without a spec-level contract the frontend parser may diverge.

**Owner:** Backend
**Fix:** Add the exact JSON schema for `event: context` to ALP-1133. The shape is:
```json
{
  "metrics": { "conscious": N, "subconscious": N, "novel": N },
  "recalled_ids": { "conscious": [...], "subconscious": [...], "novel": [...] },
  "token_estimate": { "conscious": N, "subconscious": N, "novel": N, "total": N },
  "index": [{ "id": "uuid", "category": "str", "score": F, "summary": "str", "token_estimate": N, "epoch": N, "type": "str" }]
}
```

---

## 3. Contract Mismatches

### CM-1: Episode type missing `is_conscious` and `is_pinned` fields (ALP-1132 + ALP-1142)

The Rust `Episode` struct includes `is_conscious: bool`. The frontend `Episode` interface in `types.ts` omits both `is_conscious` and `is_pinned`. This blocks the gold border rendering for conscious episodes and pinned episode badges.

**Owner:** Both
**Backend fix:** Ensure `is_conscious` is serialized in the Episode JSON response. Add `#[serde(rename = "created")]` on the `timestamp` field.
**Frontend fix:** Add `is_conscious: boolean` and `is_pinned?: boolean` to the `Episode` interface. Update `EpisodeItem` to render gold border when `is_conscious === true`.

### CM-2: Error response field name (ALP-1134)

Backend emits `{ "error": "..." }`. Frontend reads `parsed.message`. One side must change.

**Owner:** Both (coordinated)
**Backend fix:** Rename field from `error` to `message` in the error response type.
**Frontend fix:** Defensively read `parsed.error ?? parsed.message` during transition.

### CM-3: Episode neighborhood retrieval is architecturally wrong (ALP-1132 + ALP-1143)

`EpisodeDetail` calls `amQueryIndex({ text: episodeName })` to find neighborhoods for an episode. This performs semantic search on the episode name, returning neighborhoods similar to the name string rather than neighborhoods that belong to the episode. Confirmed incorrect by backend review.

**Owner:** Both
**Backend fix:** Add `GET /api/am/episodes/:id/neighborhoods` endpoint to ALP-1132.
**Frontend fix:** Add `amEpisodeNeighborhoods(id: string)` to `am-client.ts`. Update `EpisodeDetail` to call the new endpoint.

---

## 4. Implementation Gaps

### IG-1: Session-recall highlight not implemented (ALP-1143)

The spec calls for highlighting neighborhoods that were recalled in the current chat session. The `SessionRecallContext` (a React context exposing recalled neighborhood IDs from the runtime adapter) does not exist. This is a cross-component data flow dependency.

**Owner:** Frontend
**Dependency:** The runtime adapter must expose `recalled_ids` from the `event: context` SSE payload. A React context provider must propagate these IDs to the explorer panel.

### IG-2: `replaced_by` field missing from `RetrieveEntry` type (ALP-1143)

Episode detail should show a "replaced" indicator when a neighborhood has been superseded. The `RetrieveEntry` type does not include the `replaced_by` field that the backend provides.

**Owner:** Frontend (type addition) + Backend (confirm field is serialized)

### IG-3: Feedback states missing in memory panel (ALP-1138 / ALP-1140)

`memory-panel.tsx` fires feedback requests as fire-and-forget. No loading spinner, no confirmation toast, no error state. Users get no indication their feedback was received.

**Owner:** Frontend

---

## 5. Minor Issues

These are polish items. None block the merge but all should be tracked for fast-follow.

| # | Item | Source | Owner |
|---|------|--------|-------|
| M-1 | Responsive breakpoint uses Tailwind `sm:` (640px) instead of `md:` (768px) per spec | UX review | Frontend |
| M-2 | No pre-first-token thinking indicator (animated dots) | UX review | Frontend |
| M-3 | Panel expand/collapse is instant toggle, missing 150ms ease-out animation | UX review | Frontend |
| M-4 | Mode description subtitle missing beneath the mode toggle | UX review | Frontend |
| M-5 | Connection indicator is static green dot, no grey/yellow/red states | UX review | Frontend |
| M-6 | No system message injected into chat thread on mode switch | UX review | Frontend |
| M-7 | Episode detail missing sort controls, error state, and empty neighborhood state | UX review | Frontend |
| M-8 | Score thresholds (7/4) are provisional, need calibration against real query data | Contract sync | Both |
| M-9 | Backend recommends relative rank scoring (score/max) instead of absolute thresholds | Contract sync | Both |

---

## 6. Action Items

Ordered by severity. Items 1-7 are merge blockers. Items 8-13 are fast-follow.

| # | Action | Owner | Issue | Priority |
|---|--------|-------|-------|----------|
| 1 | Import and wire `SalientText` into `message.tsx` content renderer | Frontend | ALP-1137 | Critical |
| 2 | Replace inline `FeedbackButton` with shared `FeedbackButtons` or add confirmation/error states | Frontend | ALP-1138 | Critical |
| 3 | Add `tokio::select!` to cancel upstream OpenRouter request on client disconnect | Backend | ALP-1133 | Critical |
| 4 | Define `event: context` JSON schema in ALP-1133 spec | Backend | ALP-1133 | Critical |
| 5 | Add `is_conscious: boolean` to `Episode` type, render gold border in `EpisodeItem` | Frontend | ALP-1142 | Blocker |
| 6 | Add `#[serde(rename = "created")]` on Episode `timestamp` field, serialize `is_conscious` | Backend | ALP-1132 | Blocker |
| 7 | Add `GET /api/am/episodes/:id/neighborhoods` endpoint | Backend | ALP-1132 | Blocker |
| 8 | Add `amEpisodeNeighborhoods(id)` to `am-client.ts`, replace semantic search workaround | Frontend | ALP-1143 | Blocker |
| 9 | Rename error response field from `error` to `message` | Backend | ALP-1134 | Blocker |
| 10 | Add defensive `parsed.error ?? parsed.message` read in `am-client.ts` | Frontend | ALP-1134 | Blocker |
| 11 | Implement `SessionRecallContext` and wire recalled IDs from SSE context events | Frontend | ALP-1143 | Post-merge |
| 12 | Add `replaced_by` to `RetrieveEntry` type, render replaced indicator | Frontend | ALP-1143 | Post-merge |
| 13 | Add loading/confirmed/error states to `memory-panel.tsx` feedback | Frontend | ALP-1138 | Post-merge |
| 14 | Fix responsive breakpoint from `sm:` to `md:` | Frontend | ALP-1139 | Post-merge |
| 15 | Add pre-first-token thinking indicator | Frontend | ALP-1136 | Post-merge |
| 16 | Add panel expand animation (150ms ease-out) | Frontend | UX | Post-merge |
| 17 | Calibrate score thresholds against real AM query data | Both | ALP-1144 | Post-merge |

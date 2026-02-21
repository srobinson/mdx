---
title: ALP-1127 Iter 9 Review - Chat Interface Polish
type: sessions
tags: [review, am-chat, frontend, streaming, salient]
summary: Reviewed 5 commits (ALP-1156/1157/1159/1160 + prior review fix). Removed dead SalientText component, fixed stale comment. Clean pass.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-11
updated: 2026-03-11
---

## Summary

Iteration 9 covered frontend polish for the AM chat interface: salient text teachable moment tooltip (ALP-1160), upload modal file size limits (ALP-1159), streaming error classification and display (ALP-1157), and a warroom batch fixing salient rendering, feedback buttons, episode detail, and error parsing (ALP-1156). A prior review commit fixed axum 0.8 path syntax and removed dead cancellation code from llm_proxy.rs.

Overall quality is solid. Error classification in am-runtime.ts is well structured with proper fallback chains. The feedback button refactor correctly consolidates duplicate code into the shared FeedbackButtons component. The MutationObserver pattern in salient-teachable.tsx is clean with proper cleanup.

## Issues Found and Fixed

1. **Dead code: salient-text.tsx** (removed, 71 lines)
   ALP-1156 switched salient rendering to native `<salient>` tags via `allowedTags` on `StreamdownTextPrimitive` + CSS. The old manual parser component (`SalientText`, `stripSalientTags`) had zero imports remaining.

2. **Stale comment: episode-detail.tsx line 35**
   Comment referenced `GET /api/am/episodes/:id/neighborhoods` using colon syntax. The actual axum 0.8 route uses brace syntax `{id}`. Fixed to match.

## Patterns Observed

- Error handling follows a consistent pattern: classify at the boundary, attach structured info, render with fallback for unrecognized shapes. Good defense in depth.
- The `classifyError` function uses string matching on error messages for classification. Brittle if message formats change, but acceptable for a frontend display concern where the fallback is always safe.
- CSS custom properties used consistently for theming. No hardcoded colors except the red error border (`#ef4444` variants), which is reasonable for a semantic error state.

## Open Items

None. All quality gates pass.

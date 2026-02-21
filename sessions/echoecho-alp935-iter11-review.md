---
title: EchoEcho ALP-935 Iteration 11 Code Review
type: sessions
tags: [review, echoecho, edge-functions, security, supabase]
summary: Two bugs fixed in Edge Functions — GoTrue ban param semantics and auth-webhook fail-open
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Reviewed iteration 11 output for ALP-935. The commit covered activity_log table + RLS, updated profiles_read policy for om_specialist campus scoping, and four Deno Edge Functions: invite-user, deactivate-user, update-user-role, auth-webhook.

Migration 006 SQL was clean. invite-user and update-user-role had no defects. Two bugs found and fixed in the Edge Functions.

## Issues Found and Fixed

### 1. deactivate-user: `ban_duration: 'none'` unbans rather than bans

**File:** `supabase/functions/deactivate-user/index.ts`

**Bug:** `{ ban_duration: 'none' }` is the GoTrue API call to *remove* a ban. The comment in the file even referenced the old `{ banned: true }` API format that was since deprecated, but the actual call used the wrong `none` value. Step 1 of the two-step deactivation flow was silently a no-op — no Auth-level ban was ever applied. Only the `is_active = false` profile update provided protection.

**Fix:** Changed to `{ ban_duration: '876600h' }` (100 years — GoTrue's practical permanent ban).

### 2. auth-webhook: fails open when AUTH_WEBHOOK_SECRET not set

**File:** `supabase/functions/auth-webhook/index.ts`

**Bug:** `if (webhookSecret && authHeader !== ...)` — when `AUTH_WEBHOOK_SECRET` env var is absent, `webhookSecret` is the empty string (falsy), and the entire signature check is skipped. Any unauthenticated caller could POST to this endpoint and write rows to `activity_log`.

**Fix:** Changed condition to `if (!webhookSecret || authHeader !== ...)` — rejects all requests if the secret is not configured, and rejects if the header doesn't match. Fail closed.

## Patterns Observed

- GoTrue `ban_duration: 'none'` is a common footgun. The name suggests "no duration limit = forever" but the actual semantics are "remove the ban duration = unban". Always use a long duration string for permanent bans.
- The fail-open webhook auth pattern (`if (secret && header !== secret)`) is a recurring mistake. The correct pattern is always `if (!secret || header !== secret)`.

## Open Items

None. All issues resolved.

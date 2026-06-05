# Grok zero-capture runs: mechanism and verdict

Scout pass, warroom `grok-capture`, 2026-08-19. Investigation only; no code changed.

**Verdict: benign.** Cause (a): the zero-capture runs never sent a provider inference
request. The proxy was up, trusted and recording other traffic from those same runs.
No owning symbol.

## Correction to the starting evidence

The brief listed eight Grok runs in
`~/.transport-matters-preview/workspaces/dev-helioy-transport-matters-grok-386/7f44ee47/`.
That directory holds eight runs, but only **six are Grok**. Two are Codex:

```
python3 -c "
import json,glob
for f in sorted(glob.glob('$HOME/.transport-matters-preview/workspaces/dev-helioy-transport-matters-grok-386/7f44ee47/*/compatibility.json')):
    d=json.load(open(f)); print(f.split('/')[-2][:8], d['harness_id'], d['observed_version'])"
```

`30523917` and `a8a9020e` are `harness_id: codex` at 0.147.0, and both captured
(2 and 1 exchanges). The two 1.0.5 runs named in the brief are not in this workspace
at all:

- `8747def1` -> `~/.transport-matters-preview/workspaces/dev-helioy-cubicell/8ffc80ec/`
- `f734dee2` -> `~/.transport-matters-preview/workspaces/dev-helioy-transport-matters/ecd9b0df/`

## The discriminator

Captured exchange count equals the number of **completed** `POST
https://cli-chat-proxy.grok.com/v1/responses` flows the proxy saw. Nothing else
about the run separates the two groups.

Reproduce over every Grok run (per-run mitmdump log vs `index.jsonl`):

```
for f in ~/.transport-matters-preview/workspaces/*/*/*/logs/mitmdump.log; do
  d=$(dirname $(dirname "$f"))
  printf '%-10s resp=%-3s vis=%-2s ctok=%-3s idx=%s\n' "$(basename $d | cut -c1-8)" \
    "$(grep -c 'POST https://cli-chat-proxy.grok.com/v1/responses' "$f")" \
    "$(grep -c '/v1/repo/visibility' "$f")" \
    "$(grep -c 'api.anthropic.com/v1/messages/count_tokens' "$f")" \
    "$([ -f "$d/index.jsonl" ] && tr -cd '\n' < "$d/index.jsonl" | wc -c | tr -d ' ' || echo 0)"
done
```

The sweep covers every workspace, so it also prints Claude and Codex runs. The
`resp` column counts a Grok-only endpoint, so a Claude or Codex row reads
`resp=0` with a non-zero `idx`. Read the table below, which is Grok and the two
same-workspace Codex runs only. Filter with `compatibility.json` -> `harness_id`
before comparing rows.

| run | harness | ver | `/v1/responses` | `/v1/repo/visibility` | `count_tokens` | index lines | proxy uptime |
|---|---|---|---|---|---|---|---|
| `3d65a99d` | grok | 1.0.4 | 0 | 0 | 0 | 0 | 3804s |
| `501eaf0e` | grok | 1.0.4 | 0 | 0 | 0 | 0 | 11s |
| `70479518` | grok | 1.0.4 | 7 | 1 | 7 | 7 | 487s |
| `8c7c503f` | grok | 1.0.4 | 6 | 1 | 6 | 6 | 4982s |
| `af565dca` | grok | 1.0.4 | 10 | 1 | 10 | 10 | 108s |
| `baaab7c1` | grok | 1.0.4 | 13 | 1 | 12 | 12 | 1465s |
| `8747def1` | grok | 1.0.5 | 0 | 0 | 0 | 0 | 600s |
| `f734dee2` | grok | 1.0.5 | 0 | 0 | 0 | 0 | 7s |

`/v1/repo/visibility` and `api.anthropic.com/v1/messages/count_tokens` are
first-turn markers: the Grok CLI emits them when a turn is composed, before the
inference POST. Both are absent from every zero-capture run and present in every
capturing run. The zero-capture runs never reached turn composition.

`baaab7c1` is the only row where the counts differ (13 vs 12). The extra flow is
at `logs/mitmdump.log` line 339: `<< HTTP/2.0 200 OK (content missing)` followed by
`<< stream reset by client (CANCEL)`. The Grok CLI cancelled the stream, no
response body ever arrived, so no exchange was written. The mapping is exact once
cancelled flows are excluded.

## What the zero-capture runs did do

They are not dead runs. From `3d65a99d/logs/mitmdump.log`, all through the TM proxy:

```
 63 POST https://cli-chat-proxy.grok.com/v1/traces
 39 POST https://cli-chat-proxy.grok.com/v1/sessions/f623603e-10…
 27 GET  https://cli-chat-proxy.grok.com/v1/settings
 20 POST https://grok.com/_data/v1/events
 20 POST https://api.mixpanel.com/track
  1 GET  https://cli-chat-proxy.grok.com/v1/models
  1 GET  https://cli-chat-proxy.grok.com/v1/mcp/tools/list
  1 GET  https://cli-chat-proxy.grok.com/v1/feedback/config
```

Authenticated, model list fetched, MCP tools listed, session state synced, TLS
interception working, every request 200. No 401, 403, 429 or 5xx in any
zero-capture log. `f734dee2` shut down cleanly seven seconds after start.

This rules out (b) and (c):

- Not (b) bypass. Grok traffic reached the proxy in the same runs, decrypted, over
  the same `grok-trust/codex-ca-bundle.pem` those runs installed.
- Not (c) reached-but-unrecorded. `POST /v1/responses` appears zero times in the
  proxy's own log for those runs. TM cannot drop what never arrived.

## Why nothing was recorded, in source

Recording is gated on one predicate, `grok/transport.py:is_grok_responses_flow`:
`POST`, host `cli-chat-proxy.grok.com`, path `/v1/responses` (query string allowed).
Callers:

- `addon_handlers.py:handle_http_request` returns early unless the flow is
  `/v1/messages` or matches the Grok/Codex responses predicate.
- `addon_handlers.py:_should_stream_response` uses the same predicate to decide
  whether to buffer the body.
- `grok/adapter.py:GrokAdapter.matches` delegates to it.

Traces, sessions, settings, storage, billing and telemetry are deliberately not
exchanges. A run with zero `/v1/responses` recording zero exchanges is the gate
behaving as designed.

## Grok's harness descriptor

`harnesses/__init__.py` gives Grok `HarnessProxyMode.EXPLICIT`,
`HarnessTrustRequirement.TLS_CA_BUNDLE`,
`HarnessShellEnvironmentPolicy.SANITIZED_PROXY_WITH_SHELL_EXCLUDES`. Identical to
Codex on all three; Claude differs (`REVERSE` / `NONE` / `SANITIZED_BASE_URL`).
Grok is not the odd one out, and the descriptor is not implicated. Corroborated on
disk: `grok-trust/codex-ca-bundle.pem` is present in all six Grok runs, including
both zero-capture runs, and their traffic was decrypted.

## Question 4: is 1.0.5 implicated?

**No, and the evidence separates them.** `501eaf0e` (1.0.4, 11s, zero capture) has
the identical shape to both 1.0.5 runs. The split tracks turn submission, not
version. Version is confounded with run length in this sample: both 1.0.5 runs are
startup-only.

Caveat worth stating: no 1.0.5 run has ever reached turn composition, so 1.0.5
capture is **untested**, not proven working. Proving it needs one 1.0.5 run with a
submitted turn. That is a gap in coverage, not a defect.

## Owning symbol

None. No TM code is at fault.

If the desired behaviour changes so that a run producing zero exchanges should be
distinguishable from a run that failed to capture, the place to add that signal is
`addon_handlers.py:handle_http_request` (the early return) or the run's
`compatibility.json` writer, not the Grok adapter. Naming only; no fix proposed.

---

## Independent review

Reviewer pass (1:3.2, Opus 5), warroom `grok-capture`, 2026-08-19. Investigation
only; no code changed. Artifacts and source re-derived independently; the scout's
section was read but not relied on.

**Cause (a) holds.** It is now proven from the harness side, which the scout's
evidence never did. Two supporting claims in the scout's section do not survive,
and its headline on version overclaims its own caveat.

### 1. Does the evidence separate (a) from (b) and (c)?

**(c) is excluded, and the reason is stronger than the one given.** The per-run
`logs/mitmdump.log` is the mitmdump child's own stdout: `cli/runner.py:start_prepared_proxy`
spawns it with `log_path=mitmdump_log` from `cli/runner.py:mitmdump_log_path`. It is
mitmproxy's flow dump, produced upstream of TM's recording gate, which is why it
carries `traces`, `settings` and mixpanel flows that TM never records.

The positive control is already in the artifacts and the scout's file does not use it
as one: `baaab7c1` prints **13** `/v1/responses` flows and indexes **12**. The extra
flow prints as `<< HTTP/2.0 200 OK (content missing)` then `<< stream reset by client
(CANCEL)`. The log therefore records an arrival TM chose not to record. Absence from
the log means nothing arrived. `(c)` is excluded.

**One of the two "first-turn markers" is TM's own telemetry.**
`api.anthropic.com/v1/messages/count_tokens` is not Grok CLI traffic:

- it appears only as an httpx `INFO HTTP Request:` line, never as a proxied
  `127.0.0.1:<port>: POST ... HTTP/2.0` flow line;
- it appears in Claude runs at the same 1:1 ratio to index lines (`1f09eb7a`,
  3 index lines / 3 `count_tokens`);
- it returns `401` in the grok-386 workspace and `403` in provider-access-385,
  every time.

It is TM's own post-capture token counting. Correlating it with capture is circular:
it is a consequence of a capture, so it is present exactly when captures exist. It
carries no information about what the harness sent. `/v1/repo/visibility` is genuine
Grok CLI traffic, but it fires once per session (1 per capturing run against 6-13
inference posts), so it is a session marker, not a turn marker.

**(a) versus (b) was assumed by the scout.** Proxy-side absence cannot distinguish
"no request composed" from "request composed and sent off-proxy".

**The evidence that does establish (a)** is harness side and was not used. Every Grok
run's native session record, `~/.grok/sessions/<cwd-key>/<native_session_id>/summary.json`:

| run | ver | `num_messages` | `num_chat_messages` | `updates.jsonl` | index lines |
|---|---|---|---|---|---|
| `3d65a99d` | 1.0.4 | 0 | 2 | absent | 0 |
| `501eaf0e` | 1.0.4 | 0 | 2 | absent | 0 |
| `8747def1` | 1.0.5 | 0 | 2 | absent | 0 |
| `f734dee2` | 1.0.5 | 0 | 2 | absent | 0 |
| `8c7c503f` | 1.0.4 | 9 | 12 | present | 6 |
| `af565dca` | 1.0.4 | 41 | 32 | present | 10 |
| `70479518` | 1.0.4 | 53 | 31 | present | 7 |
| `baaab7c1` | 1.0.4 | 69 | 38 | present | 12 |

8/8 separation. In every zero-capture run the two chat messages are the system prompt
and one synthetic user message (`synthetic_reason: system_reminder`, the skills list),
and `updated_at` is within 350 ms of `created_at`. The CLI's own record says no turn
was ever composed. That is positive evidence for (a), independent of the proxy.

**separates_a_from_c = yes**, on evidence the scout's file does not contain.

### 2. Is "never sent a request" benign for the product?

What the four runs did, from `events.jsonl` in each native session and the proxy logs:

- `3d65a99d` (1.0.4, 63 min): full startup, `mcp_init_completed` at 30.004 s
  (7/8 servers, `supabase` timed out), agent `grok-build-plan`, `reasoning_effort: xhigh`.
  Idle for an hour. Clean shutdown.
- `8747def1` (1.0.5, 600 s): full startup, init 30.011 s (`supabase` and `cubicell`
  failed), session state synced 6 times, no turn. Clean shutdown.
- `501eaf0e` (1.0.4, 11 s) and `f734dee2` (1.0.5, 7 s): **`mcp_init_completed` never
  fired**. Both died inside the startup window. MCP init takes ~30 s in every Grok run
  measured, capturing ones included (`70479518` 30.002 s, `af565dca` 30.006 s), so
  neither run reached the point where the CLI can accept input.

No 4xx or 5xx in any of the four proxy logs. All four shut down cleanly. No crash, no
failed launch, no error path. **The capture path is not defective: product_defect = no.**

Two things the "benign" label flattens, ranked:

1. **A zero-turn run leaves nothing on disk.** `f734dee2`'s entire storage dir is
   `sessions.json`, `compatibility.json`, `lock`, `logs/mitmdump.log`, `grok-trust/`.
   No `index.jsonl` (not even empty), no `transcripts/`, no recorded outcome. "The user
   never typed" and "capture broke" are byte-identical on disk, and the only way to tell
   them apart is hand-reading a proxy log, which is what this warroom just spent a day
   doing. The scout names the right fix location (`addon_handlers.py:handle_http_request`
   or the `compatibility.json` writer) but files it under "if the desired behaviour
   changes". This is the finding, not the footnote: the investigation is the evidence
   that the signal is missing.
2. **Two of eight launches died inside a ~30 s window in which the harness cannot take
   input.** The 30 s is the user's own MCP config (`supabase` timing out at its 30 s
   ceiling, plus `cubicell` in one run), not TM. TM does not own the cause. It does hand
   the user a harness that is unusable for half a minute with no signal, and two launches
   did not survive it.

### 3. Does version separate them?

**Unsupported at this sample size.** 1.0.5: 2 runs, both zero. 1.0.4: 6 runs, 2 zero.
Fisher exact, one tailed: `C(4,2) / C(8,2) = 6/28 = 0.21`. Independence cannot be
rejected, and neither can implication.

What is established: turn submission explains every row in both versions, so version is
not *needed* to explain the split. What is not established, and what the scout's heading
claims, is that the evidence *separates* them. No 1.0.5 run has ever composed a turn
(both 1.0.5 sessions: `num_messages: 0`), so the 1.0.5 capture path is untested, not
proven working. The scout's own closing caveat says exactly this and contradicts its
heading. The caveat is the finding.

The 1.0.5 startup surface is also not identical to 1.0.4: the 1.0.5 runs fetch
`/v1/billing` and `/v1/bundle`, absent from 1.0.4 startup. "Same shape" should not be
assumed for the request path either. One 1.0.5 run with a submitted turn closes this;
nothing short of it does.

### Corrections to the scout's section

- "Nothing else about the run separates the two groups" was asserted, not tested. It
  survives one axis I checked: home isolation recorded in `sessions.json` does not track
  the split (isolated: 3 zero, 2 capturing; shared: 1 zero, 2 capturing).
- The `count_tokens` column is TM's own traffic, not a Grok CLI first-turn marker
  (above). The table's `ctok` column should be struck.
- The correction about 8 runs / 6 Grok and the two relocated 1.0.5 runs reproduces
  independently and is right.
- `grok/transport.py:is_grok_responses_flow` and its callers
  (`addon_handlers.py:handle_http_request`, `addon_handlers.py:_should_stream_response`,
  `grok/adapter.py:GrokAdapter.matches`) verified as described.

### Incidental, outside the brief

- TM's `api.anthropic.com/v1/messages/count_tokens` call fails on every attempt in every
  run examined: 401 in the grok-386 workspace, 403 in provider-access-385. Token counting
  has never succeeded in these runs.
- Every Grok run, including the five TM recorded with an isolated `home_dir`, has a native
  session directory under the shared `~/.grok/sessions/`. Whether an isolated copy also
  existed cannot be checked: `runtime-home` is pruned after the run, and only `af565dca`
  retains one.

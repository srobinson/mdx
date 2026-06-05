# Codex HTTP-fallback fixture (real capture, 2026-07-10)

Three consecutive real Codex `/responses` HTTP-fallback exchanges, captured
via `transport-matters codex --force-http-fallback` (run
`0dc1667e-aabc-4c7f-93db-6301b49d2d31`, workspace `dev-helioy-docs/7fc662e5`,
model `codex/gpt-5.6-sol`, codex-cli 0.144.0). Verbatim
`request.ir.json`/`response.ir.json` per turn; `turn-0/transport.json` proves
the transport: `protocol: http`, POST `chatgpt.com/backend-api/codex/responses`,
status 200, no Upgrade header, `x-codex-turn-metadata` + `session-id` headers
present.

**Intended repo destination:** `api/tests/fixtures/codex_http_fallback/`
(integration-test fixtures live under `api/tests/`; the wire-normalization
unit tests in `session/` load them from there for the PR-2 dedup-yield and
round-trip acceptance).

## Measured facts this fixture locks

- **Fallback requests are CUMULATIVE** (like Claude, unlike the WS
  incremental turns): messages 6 → 12 → 15, each turn replaying the full
  prior history; `system` (6 parts, 61,376 bytes incl. instructions) and
  `tools` (`[]` on this model) byte-identical across turns.
- **Normalization contract yield:** stripping the `tm_wire_index`
  provider_data stamp makes the replayed prefix hash-identical:
  turns 0→1 share 6/12 messages, 1→2 share 12/15 (100% of the prefix,
  prefix-positional and anywhere-reuse agree). New-message bytes per turn:
  3,153 then 2,364 of ~200 KB request IR → **~1.2–1.6% stored, 98%+
  reduction** (beats the Claude-measured ~96%).
- **turn_index populated:** 0, 1, 2 via header continuity
  (`x-codex-turn-metadata`), confirming the fallback fills
  `wire_exchange.turn_index`.
- **`input_item_raw` is ~96–98 KB per turn** (nearly the whole request
  duplicated into `provider_extras` — most real fallback input items carry
  extra fields, so the parser preserves them raw). The spec's strip clause is
  load-bearing; also strip the sibling `input_item_raw_stamped` bool (it is
  meaningless without the raw).
- **Response blocks:** `thinking` / `text` / `tool_use(name="exec")`;
  usage populated incl. `cache_read_input_tokens` (cache_creation 0, as
  modeled). `request_user_input` does not appear in this session (no
  question was triggered); `tool_use.input` may be
  `{"__raw_arguments__": "..."}` when arguments are not a JSON object —
  stored verbatim in `wire_response_block.body`, no schema impact.

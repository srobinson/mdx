---
title: Live BTC Verification Implementation
type: sessions
tags: [backend, bitcoin, evidence, shell]
summary: Implemented a repeatable public API BTC address verification script and plain language command packet.
status: active
source: backend-engineer
confidence: high
created: 2026-05-25
updated: 2026-05-25
---

## Summary

Implemented a safe, read only BTC verification packet for William's live BTC lead.

Created:

1. `/Users/alphab/.mdx/research/william-friend-packet/live-btc-check.sh`
2. `/Users/alphab/.mdx/research/william-friend-packet/live-btc-verification-commands.md`

The script checks Blockstream and mempool.space for address stats, UTXOs, and mempool transactions for `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`. It saves timestamped JSON responses under `/Users/alphab/.mdx/research/data/william-live-recheck-2026-05-25/` and prints a human readable summary.

Verified run at `20260525T142251Z` saved six JSON responses. Both providers reported `649,998,534` funded sats, `0` spent sats, `649,998,534` computed balance sats, two UTXOs, and zero mempool transactions. Cross check passed.

## API Contract

No server endpoint was added.

CLI contract:

```typescript
interface LiveBtcCheckInput {
  BTC_ADDRESS?: string; // defaults to the live BTC lead
  DATA_DIR?: string; // defaults to /Users/alphab/.mdx/research/data/william-live-recheck-2026-05-25
}

interface ProviderSummary {
  provider: "Blockstream" | "mempool.space";
  fundedSats: number;
  spentSats: number;
  computedBalanceSats: number;
  computedBalanceBtc: string;
  utxoCount: number;
  utxoValueSumSats: number;
  mempoolTxCount: number;
}

interface LiveBtcCheckOutput {
  timestampUtc: string;
  address: string;
  dataDir: string;
  providers: ProviderSummary[];
  mempoolStatus: "none" | "activity_detected";
  crossCheck: "PASS" | "FAIL";
}
```

Public API reads:

1. `GET https://blockstream.info/api/address/<address>`
2. `GET https://blockstream.info/api/address/<address>/utxo`
3. `GET https://blockstream.info/api/address/<address>/txs/mempool`
4. `GET https://mempool.space/api/address/<address>`
5. `GET https://mempool.space/api/address/<address>/utxo`
6. `GET https://mempool.space/api/address/<address>/txs/mempool`

Exit behavior:

1. `0` when all network calls, JSON validation, and cross provider checks pass.
2. Nonzero when a required local tool is missing, a network call fails, JSON parsing fails, response shape is unexpected, or key provider totals disagree.

## Database Changes

None.

## Security Considerations

1. The script uses public HTTPS GET requests only.
2. No API keys, credentials, wallet connections, signatures, account creation, or fund movement are used.
3. `curl` uses timeouts, retries, and `Accept: application/json`.
4. Responses are validated as JSON before being moved into the evidence directory.
5. New files are written with restrictive permissions through `umask 077`.
6. The plain language markdown warns William not to paste seed phrases, private keys, passwords, or two factor codes while checking the address.

## Performance Notes

The script performs six external HTTP GET requests. Each request uses a 10 second connect timeout, a 30 second max time, and two retries. The verified run completed in a few seconds. Local parsing uses Python standard library JSON only.

## Open Items

1. Add a cron or launchd wrapper if continuous monitoring is desired.
2. Treat nonzero mempool activity as urgent and preserve the timestamped JSON immediately.
3. If providers disagree, rerun once and inspect the raw browser URLs before drawing conclusions.
4. Attribution remains conservative. The live BTC lead is a repeatable monitoring lead, not final ownership attribution.

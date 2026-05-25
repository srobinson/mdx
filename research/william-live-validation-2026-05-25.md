---
title: William Crypto Case Live Validation, 2026-05-25
type: research
tags: [crypto-tracing, bitcoin, thorchain, osint, william-case]
summary: Current public chain checks show no new spend or mempool activity on the live BTC address, with related leads unchanged from the dossier.
status: active
confidence: high
created: 2026-05-25
updated: 2026-05-25
---

## Executive Summary

Current checks run on 2026-05-25 between 13:35:14Z and 13:37:02Z found no new spend, no unconfirmed transaction, and no mempool activity on the live BTC address `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`. The Wasabi deposit address, low confidence demix candidate, probable Binance branch, and two key THORChain swap records remain consistent with the existing dossier.

The actionable posture is unchanged. Keep monitoring the live BTC address, preserve the low confidence trail language, and treat the probable Binance branch as a preservation lead only if paid analytics or law enforcement validates the Wasabi demix path.

## Check Window and Raw Evidence

- BTC address checks: 2026-05-25T13:35:14Z to 2026-05-25T13:35:33Z.
- BTC transaction and outspend checks: 2026-05-25T13:35:34Z to 2026-05-25T13:35:44Z.
- THORChain Midgard checks: 2026-05-25T13:35:45Z to 2026-05-25T13:35:46Z.
- THORNode feasibility checks: 2026-05-25T13:36:59Z to 2026-05-25T13:37:02Z.
- Primary raw manifest: `/Users/alphab/.mdx/research/data/william-live-check-2026-05-25/20260525T133513Z-fetch-manifest.tsv`.
- Extra THORNode feasibility manifest: `/Users/alphab/.mdx/research/data/william-live-check-2026-05-25/20260525T133658Z-extra-fetch-manifest.tsv`.

## Detailed Findings

### 1. Live BTC Address Remains Unspent

Address: `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`

Current balance remains `649,998,534` sats, or `6.49998534 BTC`.

Triangulated status:

| Source | Result |
|---|---:|
| Blockstream address API | funded `649,998,534` sats, spent `0`, tx count `2`, mempool tx count `0` |
| mempool.space address API | same chain stats and mempool stats as Blockstream |
| blockchain.info raw address API | final balance `649,998,534`, total sent `0`, unredeemed outputs `2`, tx count `2` |
| BlockCypher balance API | final balance `649,998,534`, unconfirmed balance `0`, unconfirmed tx count `0`, final tx count `2` |

Current UTXOs:

| UTXO | Value | Block height | Block time UTC | Status |
|---|---:|---:|---|---|
| `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187:0` | `649,998,240` sats | `812907` | 2023-10-19T11:22:51Z | unspent on Blockstream and mempool.space outspend APIs |
| `4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5:0` | `294` sats | `940313` | 2026-03-11T22:02:44Z | unspent on Blockstream and mempool.space outspend APIs |

Mempool status:

- Blockstream `/address/<addr>/txs/mempool` returned an empty array.
- mempool.space `/address/<addr>/txs/mempool` returned an empty array.
- Blockstream and mempool.space address summaries both returned mempool `tx_count: 0`.
- BlockCypher returned `unconfirmed_n_tx: 0` and `unconfirmed_balance: 0`.

Conclusion: no new spend and no mempool activity on the live BTC address as of the check window.

### 2. Wasabi Deposit Address Remains Fully Spent

Address: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`

Current status across Blockstream, mempool.space, blockchain.info, and BlockCypher:

| Metric | Current value |
|---|---:|
| Funded | `4,070,902,128` sats |
| Spent | `4,070,902,128` sats |
| Balance | `0` sats |
| Transaction count | `13` |
| Current UTXOs | `0` |
| Mempool tx count | `0` |

Conclusion: unchanged. The address remains a historical Wasabi deposit destination with no live balance and no current mempool activity.

### 3. Low Confidence Demix Candidate Remains Fully Spent

Address: `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`

Current status across Blockstream, mempool.space, blockchain.info, and BlockCypher:

| Metric | Current value |
|---|---:|
| Funded | `4,763,611,646` sats |
| Spent | `4,763,611,646` sats |
| Balance | `0` sats |
| Transaction count | `10` |
| Current UTXOs | `0` |
| Mempool tx count | `0` |

The current data does not improve attribution confidence. Keep the dossier language: this is a low confidence investigative lead until a paid analytics operator or law enforcement validates the Wasabi demix path.

### 4. Probable Binance Branch Has No Current Balance or Mempool Activity

Address: `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva`

Current status:

| Source | Current value |
|---|---:|
| Blockstream address API | funded `993,353,285,374` sats, spent `993,353,285,374` sats, balance `0`, tx count `148,959`, mempool tx count `0` |
| mempool.space address API | same address summary as Blockstream |
| mempool.space UTXO API | `0` UTXOs |
| blockchain.info raw address API | final balance `0`, total sent `993,353,285,374` sats, unredeemed outputs `0`, tx count `148,959` |
| BlockCypher balance API | final balance `0`, unconfirmed balance `0`, unconfirmed tx count `0`, final tx count `148,959` |

The specific branch transaction `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287` remains spent by `1829670be43913276482832ef00ee2d7eebd6cd03a2ca2aa7f2d00fbe5d99f79`, confirmed at block `849063`, on both Blockstream and mempool.space outspend APIs.

Conclusion: no current public freeze opportunity appears at this exact address. The existing probable Binance attribution remains a cluster lead, not official Binance confirmation.

### 5. Key Path Transaction Outspends Match Existing Dossier

| Transaction | Current outspend status |
|---|---|
| `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187` | output remains unspent on Blockstream and mempool.space |
| `4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5` | output remains unspent on Blockstream and mempool.space |
| `1962037495cfc6f39cd0c525b78fdcffddb98de34babdcf785b12208152e9bb2` | spent by `4d23a22853686456ae2d8345d0402182ac301bf5aa4010a1f04df90581c2bd8f`, confirmed at block `849048` |
| `4d23a22853686456ae2d8345d0402182ac301bf5aa4010a1f04df90581c2bd8f` | mempool.space confirms both outputs spent, one by `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287` and one by `07183f4dbc9f9ad6015e829ff68dc21d49085dbb88168d723cdc21e1890f3a17` |
| `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287` | spent by `1829670be43913276482832ef00ee2d7eebd6cd03a2ca2aa7f2d00fbe5d99f79`, confirmed at block `849063` |

One Blockstream outspend fetch for `4d23a228...` reset the connection during this run. The mempool.space outspend response succeeded, and prior local Blockstream evidence for the same tx remains available in `mempool-outspends-4d23a22853686456ae2d8345d0402182ac301bf5aa4010a1f04df90581c2bd8f.json` and `blockstream-tx-4d23a22853686456ae2d8345d0402182ac301bf5aa4010a1f04df90581c2bd8f.json`.

### 6. THORChain Midgard Still Confirms Both Swap Actions

Liquify Midgard returned `count: "1"` and `status: success` for both key txids.

| Inbound txid | In asset and amount | Out BTC address | Out amount | Action time UTC |
|---|---:|---|---:|---|
| `655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204` | `125.44715147 ETH` | `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` | `7.29622713 BTC` | 2023-07-21T14:17:43Z |
| `40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C` | `727.29568000 ETH` | `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` | `31.37643194 BTC` | 2023-07-21T15:34:17Z |

The old Nine Realms Midgard and THORNode hosts did not resolve during this run. THORChain developer docs state that `*.ninerealms.com` endpoints were retired after April 20, 2025, and list Liquify gateway URLs as current public mainnet endpoints. Liquify THORNode `tx` and `tx/details` calls returned HTTP 400 for these external inbound txids, while Liquify Midgard action queries returned the expected swap records. For this evidence packet, Midgard is the useful public THORChain source for these external transaction IDs.

## What Changed Since the Existing Dossier

No material chain status changed.

| Lead | Prior dossier status | Current validation |
|---|---|---|
| Live BTC address | `6.49998534 BTC`, `0 BTC` spent | unchanged, no mempool activity |
| Wasabi deposit address | fully spent | unchanged |
| Low confidence demix candidate | fully spent | unchanged |
| Probable Binance branch | spent branch, probable cluster attribution | unchanged at exact address, still no official Binance confirmation |
| THORChain txids | successful swaps to Wasabi deposit address | unchanged via Liquify Midgard |

The March 2026 dust UTXO of `294` sats remains present and unspent. It was already reflected in the dossier, so this is not a new event from the current validation pass.

## Sources Consulted

### Existing Case Files

- `/Users/alphab/.mdx/research/william-crypto-case-dossier.md`
- `/Users/alphab/.mdx/research/william-monitoring-tooling-codex.md`
- Existing raw snapshots under `/Users/alphab/.mdx/research/data/william-live-check-2026-05-25/`

### Bitcoin Address and Transaction APIs

Target addresses:

- `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`
- `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`
- `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`
- `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva`

Source URL patterns used:

- `https://blockstream.info/api/address/<address>`
- `https://blockstream.info/api/address/<address>/utxo`
- `https://blockstream.info/api/address/<address>/txs/mempool`
- `https://blockstream.info/api/tx/<txid>`
- `https://blockstream.info/api/tx/<txid>/outspends`
- `https://mempool.space/api/address/<address>`
- `https://mempool.space/api/address/<address>/utxo`
- `https://mempool.space/api/address/<address>/txs/mempool`
- `https://mempool.space/api/tx/<txid>`
- `https://mempool.space/api/tx/<txid>/outspends`
- `https://blockchain.info/rawaddr/<address>?limit=0`
- `https://api.blockcypher.com/v1/btc/main/addrs/<address>/balance`

Example live address URLs:

- https://blockstream.info/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
- https://mempool.space/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
- https://blockchain.info/rawaddr/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g?limit=0
- https://api.blockcypher.com/v1/btc/main/addrs/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g/balance

### THORChain Sources

- THORChain developer endpoint guide: https://dev.thorchain.org/concepts/connecting-to-thorchain.html
- THORChain Midgard overview: https://docs.thorchain.org/technical-documentation/technology/midgard
- Liquify Midgard OpenAPI docs: https://gateway.liquify.com/chain/thorchain_midgard/v2/doc
- Liquify Midgard action lookup: `https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=<TXID>`

## Source Quality Assessment

Confidence is high for current public Bitcoin status because four independent public APIs agree on the live address balance, spend status, and absence of unconfirmed activity. Blockstream and mempool.space also agree at the individual outspend layer for the two live UTXOs.

Confidence remains low to medium for the Wasabi demix path. Public address status can show whether funds moved, but public APIs do not validate probabilistic CoinJoin attribution. Paid analytics or lawful exchange process remains necessary for stronger attribution.

The probable Binance branch remains medium high as a preservation lead, not final attribution. The current validation confirms the exact address has no live balance or mempool activity, but it does not prove Binance account ownership.

Known gaps:

- Blockchair returned HTTP 430 in an earlier partial fetch and was not used for conclusions.
- Blockstream returned HTTP 400 for the probable Binance branch UTXO endpoint because of too many history entries. mempool.space, blockchain.info, and BlockCypher supplied enough current balance evidence for that address.
- One Blockstream outspend fetch for `4d23a228...` reset the connection. mempool.space succeeded for the same current outspend check.
- Liquify THORNode returned HTTP 400 for external inbound txids; Liquify Midgard was the successful current public THORChain source for these swap actions.

## Open Questions

1. Can paid analytics validate or reject the path from the Wasabi coinjoin outputs to `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`?
2. Does a paid analytics vendor independently label `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` or its cluster as Binance, Binance.US, or another VASP?
3. If the live BTC address moves, does the first hop touch a service with a preservation process?
4. Can the full transaction inventory be completed from the original CSV and raw chain data to make a law enforcement packet self contained?

## Actionable Takeaways

1. Keep monitoring `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` for both confirmed spends and mempool activity.
2. Treat the two live UTXOs as the alert targets: `164f311d...:0` and `4fadadf2...:0`.
3. Preserve raw API responses from every future movement check under `/Users/alphab/.mdx/research/data/william-live-check-2026-05-25/` or a new dated sibling folder.
4. Keep external reporting language conservative: the demix candidate is low confidence, and the Binance branch is a preservation lead, not final attribution.
5. Use Liquify Midgard for current THORChain action lookups. Do not depend on retired Nine Realms endpoints.

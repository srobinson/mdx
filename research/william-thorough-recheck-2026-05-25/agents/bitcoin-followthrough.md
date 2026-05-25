---
title: William Bitcoin Followthrough Recheck
type: research
tags: [crypto-tracing, bitcoin, william-case, osint, warroom]
summary: Public data confirms the spreadsheet connects to the Wasabi deposit address, while the later demix candidate and live BTC lead remain follow-through leads outside the sheet.
status: active
confidence: medium
created: 2026-05-25
updated: 2026-05-25
---

## Executive Summary

[confirmed] The visible spreadsheet evidence connects William's July 21, 2023 ETH loss records to the BTC address `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` through THORChain and two public BTC output transactions totaling `38.67265907 BTC`. [confirmed] That address has lifetime received `40.70902128 BTC`, lifetime spent `40.70902128 BTC`, current balance `0 BTC`, and no mempool activity as of the 2026-05-25T15:06Z recheck.

[confirmed] The follow-through address `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` still holds `6.49998534 BTC`, with no spend and no pending mempool transaction. [unresolved] Public Bitcoin data does not prove that the Wasabi coinjoin spend path leads to `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`; that segment remains a low confidence investigative lead.

## Scope Handled

Task slug: `bitcoin-followthrough`.

Checked addresses:

- Wasabi deposit address: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`
- Low confidence post Wasabi candidate: `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`
- Live BTC lead: `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`

Checked whether the BTC trail is supported by the Google Sheet evidence or should be separated from it.

## Evidence Sources Read

### Local source files

- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/WARROOM-BRIEF.md`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/summary-visible-rows.csv`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/gid-1211660592.csv`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/01-Summary.csv`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/manifest.md`
- Prior context read for comparison only: `/Users/alphab/.mdx/research/william-friend-packet/live-btc-finding-repeatable.md`

### New raw data saved

Raw responses and derived summary are saved under:

```text
/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/bitcoin-followthrough/
```

Key files:

- `manifest.json`
- `derived-summary.json`
- `20260525T150603Z-blockstream-address-wasabi-deposit.json`
- `20260525T150608Z-mempool-address-wasabi-deposit.json`
- `20260525T150610Z-blockchain-info-rawaddr-wasabi-deposit.json`
- `20260525T150611Z-blockcypher-balance-wasabi-deposit.json`
- `20260525T150743Z-blockstream-address-demix-candidate-retry.json`
- `20260525T150616Z-mempool-address-demix-candidate.json`
- `20260525T150619Z-blockchain-info-rawaddr-demix-candidate.json`
- `20260525T150620Z-blockstream-address-live-lead.json`
- `20260525T150625Z-mempool-address-live-lead.json`
- `20260525T150627Z-blockchain-info-rawaddr-live-lead.json`
- `20260525T150628Z-blockcypher-balance-live-lead.json`
- `20260525T150641Z-midgard-action-655a.json`
- `20260525T150642Z-midgard-action-40a3.json`
- Ethereum JSON RPC raw files for txs `0x655a...`, `0x662e...`, `0x2ed7...`, and `0x40a3...`

## Detailed Findings

### 1. Spreadsheet to Wasabi deposit address

[confirmed] The Summary sheet names the Wasabi deposit address directly. It appears in the exported sheet at:

- `gid-1211660592.csv`, lines 53 and 55
- `extracted-tabs/01-Summary.csv`, lines 49 and 51

[confirmed] The sheet also has a direct THORChain router row for `0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204` from wallet `0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0`.

Public chain checks:

| Evidence | Result |
|---|---|
| Spreadsheet row | `summary-visible-rows.csv` source row 5 |
| ETH tx | `0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204` |
| Public ETH block time | 2023-07-21T14:00:59Z |
| ETH from | `0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0` |
| ETH to | THORChain router `0xd37bbe5744d730a1d98d8dc97c42f0ca46ad7146` |
| ETH value | `125.44715147736405 ETH`, matching the sheet's rounded `125.4472 ETH` |
| Midgard action time | 2023-07-21T14:17:43.813588Z |
| Midgard BTC out tx | `CA88B4956964E3D8BFDAE2800B48F4CB15F8CC52A8554B4BFA301A400805E053` |
| BTC block time | 2023-07-21T16:24:48Z |
| BTC output | `7.29622713 BTC` to `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` |

[confirmed] The sheet also supports an indirect staging path through `0xeEC35fd50B5E7344b3E1A7F4384b3Cb9365e204A`.

| Evidence | Result |
|---|---|
| Spreadsheet rows | `summary-visible-rows.csv` source rows 7 and 8 |
| Funding txs | `0x662e469715056d9501da5184ec4a2a466b05b3fa656c73d0fb067598b88013c2`, `0x2ed79b067f3afa2e636ae82f8c0c6cbd59d504aa7f25f146a4d22ef2186fc157` |
| Public ETH times | 2023-07-21T13:47:23Z and 2023-07-21T13:56:11Z |
| ETH from | `0x1c0b5b8d36587d0516839df7ebfb49ad8f3c543c` |
| ETH to | `0xeec35fd50b5e7344b3e1a7f4384b3cb9365e204a` |
| Funding values | `623 ETH` and `104.3 ETH`, total `727.3 ETH` |
| Follow-on THORChain tx | `0x40a3d546f349f9cf8e907b6676e6187ad01f24c76ad9d0b9d2958e8c9e059e2c` |
| Follow-on ETH time | 2023-07-21T13:56:59Z |
| Follow-on ETH value | `727.29568 ETH` to THORChain router |
| Midgard action time | 2023-07-21T15:34:17.711942Z |
| Midgard BTC out tx | `D40F9B8C207CFE8BDFF9D054A7C2BADF838DE47CB1CB65E0EDBA63200A677A89` |
| BTC block time | 2023-07-21T16:57:27Z |
| BTC output | `31.37643194 BTC` to `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` |

[confirmed] The two spreadsheet supported THORChain outputs to the Wasabi address total `38.67265907 BTC`.

[possible] The Wasabi address received `40.70902128 BTC` total. The additional `2.03636221 BTC` came from five smaller BTC outputs in the same address history. Those smaller outputs were not tied to specific visible spreadsheet rows in this pass.

### 2. Wasabi deposit address current status

[confirmed] Blockstream, mempool.space, blockchain.info, and BlockCypher agree that the Wasabi deposit address is fully spent and has no current balance.

Address: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`

| Source | Funded | Spent | Balance | Tx count | Mempool |
|---|---:|---:|---:|---:|---:|
| Blockstream | `40.70902128 BTC` | `40.70902128 BTC` | `0 BTC` | `13` | `0` tx |
| mempool.space | `40.70902128 BTC` | `40.70902128 BTC` | `0 BTC` | `13` | `0` tx |
| blockchain.info | `40.70902128 BTC` | `40.70902128 BTC` | `0 BTC` | `13` | not shown in rawaddr limit 0 |
| BlockCypher | `40.70902128 BTC` | `40.70902128 BTC` | `0 BTC` | `13` | `0` unconfirmed tx |

[confirmed] Blockstream transaction history shows seven deposits to the address and seven spends from that address. The two THORChain related deposits are the large outputs listed above.

### 3. Demix candidate current status and limits

[confirmed] The candidate address is fully spent and has no mempool activity.

Address: `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`

| Source | Funded | Spent | Balance | Tx count | Mempool |
|---|---:|---:|---:|---:|---:|
| Blockstream | `47.63611646 BTC` | `47.63611646 BTC` | `0 BTC` | `10` | `0` tx |
| mempool.space | `47.63611646 BTC` | `47.63611646 BTC` | `0 BTC` | `10` | `0` tx |
| blockchain.info | `47.63611646 BTC` | `47.63611646 BTC` | `0 BTC` | `10` | not shown in rawaddr limit 0 |
| BlockCypher | `43.02054073 BTC` | `43.02054073 BTC` | `0 BTC` | `10` | `0` unconfirmed tx |

[confirmed] BlockCypher undercounts this candidate's lifetime amount by `4.61557573 BTC` compared with Blockstream, mempool.space, and blockchain.info. It still agrees on current balance `0 BTC`. I would not use BlockCypher for the candidate lifetime total.

[confirmed] Public Bitcoin data shows the candidate sent `6.49998240 BTC` to the live lead:

| Field | Value |
|---|---|
| Tx | `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187` |
| Block time | 2023-10-19T11:22:51Z |
| Input | `6.50000000 BTC` from `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` |
| Output 0 | `6.49998240 BTC` to `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` |
| Outspend status | output 0 is unspent on Blockstream and mempool.space |

[unresolved] The Google Sheet does not contain `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`. A direct grep of `summary-visible-rows.csv`, `gid-1211660592.csv`, and `extracted-tabs/01-Summary.csv` returned zero matches.

[unresolved] Public BTC data does not prove that this candidate came from William's Wasabi coinjoin outputs. That step remains a low confidence demix hypothesis.

### 4. Live BTC lead current status

[confirmed] The live lead remains unspent as of the 2026-05-25T15:06Z recheck.

Address: `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`

| Source | Funded | Spent | Balance | Tx count | Mempool |
|---|---:|---:|---:|---:|---:|
| Blockstream | `6.49998534 BTC` | `0 BTC` | `6.49998534 BTC` | `2` | `0` tx |
| mempool.space | `6.49998534 BTC` | `0 BTC` | `6.49998534 BTC` | `2` | `0` tx |
| blockchain.info | `6.49998534 BTC` | `0 BTC` | `6.49998534 BTC` | `2` | not shown in rawaddr limit 0 |
| BlockCypher | `6.49998534 BTC` | `0 BTC` | `6.49998534 BTC` | `2` | `0` unconfirmed tx |

[confirmed] Current UTXOs:

| UTXO | Value | Block time UTC | Status |
|---|---:|---|---|
| `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187:0` | `6.49998240 BTC` | 2023-10-19T11:22:51Z | unspent |
| `4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5:0` | `0.00000294 BTC` | 2026-03-11T22:02:44Z | unspent |

[confirmed] The `294` sat March 2026 output is dust. It should not be treated as ownership attribution.

[unresolved] The Google Sheet does not contain `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`. A direct grep of the visible source files returned zero matches.

### 5. Connection and separation from spreadsheet evidence

[confirmed] Spreadsheet supported chain:

```text
Summary row 5
0xaadd5f... -> THORChain router in ETH tx 0x655a...
THORChain Midgard action 655A...
BTC tx ca88... output 0
7.29622713 BTC to bc1qwxwl...
```

[confirmed] Spreadsheet supported indirect chain:

```text
Summary rows 7 and 8
0x1c0b5... -> 0xeec35... in ETH txs 0x662e... and 0x2ed7...
0xeec35... -> THORChain router in ETH tx 0x40a3...
THORChain Midgard action 40A3...
BTC tx d40f... output 0
31.37643194 BTC to bc1qwxwl...
```

[unresolved] Follow-through lead outside the sheet:

```text
bc1qwxwl... Wasabi/CoinJoin spend path
public deterministic link stops here
low confidence candidate: bc1q9vl045...
BTC tx 164f... output 0
6.49998240 BTC to live lead bc1qyt274...
```

[confirmed] The sheet supports the BTC root address. It does not itself prove the demix candidate or live BTC lead.

## Contradictions or Unresolved Gaps

1. [confirmed] The sheet title says July 2021, but the visible rows and public chain data checked here are July 21 to July 22, 2023.
2. [confirmed] Summary row 5's displayed time `2023/07/21 10:00:59` lines up with public chain time `2023-07-21T14:00:59Z` if interpreted as UTC minus 4 hours.
3. [confirmed] Summary rows 7 and 8 appear time swapped by tx hash. `0x662e...` displays `09:56:11`, but public chain time is `13:47:23Z`. `0x2ed7...` displays `09:47:23`, but public chain time is `13:56:11Z`. The amounts and destination still support the staging path.
4. [unresolved] The Wasabi address lifetime total is `40.70902128 BTC`, while the two public THORChain links checked here total `38.67265907 BTC`. The remaining `2.03636221 BTC` is not tied to visible spreadsheet rows by this BTC follow-through pass.
5. [unresolved] The post Wasabi candidate is not in the sheet. Public data confirms its later payment to the live lead, not its origin from William's Wasabi outputs.
6. [confirmed] BlockCypher is inconsistent for the demix candidate lifetime total. Use Blockstream, mempool.space, and blockchain.info for that total.

## Repeatable Commands and URLs

### Address status checks

```bash
WASABI='bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s'
CANDIDATE='bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl'
LIVE='bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g'

for ADDR in "$WASABI" "$CANDIDATE" "$LIVE"; do
  curl -fsS "https://blockstream.info/api/address/$ADDR" | jq '{chain_stats, mempool_stats}'
  curl -fsS "https://mempool.space/api/address/$ADDR" | jq '{chain_stats, mempool_stats}'
  curl -fsS "https://blockchain.info/rawaddr/$ADDR?limit=0" | jq '{n_tx,total_received,total_sent,final_balance}'
  curl -fsS "https://api.blockcypher.com/v1/btc/main/addrs/$ADDR/balance" | jq '{n_tx,total_received,total_sent,balance,unconfirmed_n_tx,final_balance}'
done
```

### Key BTC transaction checks

```bash
curl -fsS 'https://blockstream.info/api/tx/ca88b4956964e3d8bfdae2800b48f4cb15f8cc52a8554b4bfa301a400805e053' | jq '{txid,status,vout}'
curl -fsS 'https://blockstream.info/api/tx/d40f9b8c207cfe8bdff9d054a7c2badf838de47cb1cb65e0edba63200a677a89' | jq '{txid,status,vout}'
curl -fsS 'https://blockstream.info/api/tx/164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187' | jq '{txid,status,vin,vout}'
curl -fsS 'https://blockstream.info/api/tx/164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187/outspends' | jq .
```

### THORChain checks

```bash
curl -fsS 'https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204' | jq '.actions[0] | {date,type,status,in,out}'
curl -fsS 'https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C' | jq '.actions[0] | {date,type,status,in,out}'
```

### Public browser links

- https://blockstream.info/address/bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s
- https://blockstream.info/address/bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl
- https://blockstream.info/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
- https://mempool.space/address/bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s
- https://mempool.space/address/bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl
- https://mempool.space/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g

## Sources Consulted

### Google Sheet exports

- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/gid-1211660592.csv`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/01-Summary.csv`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/summary-visible-rows.csv`

### Bitcoin APIs

- https://blockstream.info/api/address/bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s
- https://blockstream.info/api/address/bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl
- https://blockstream.info/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
- https://mempool.space/api/address/bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s
- https://mempool.space/api/address/bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl
- https://mempool.space/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
- https://blockchain.info/rawaddr/bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s?limit=0
- https://blockchain.info/rawaddr/bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl?limit=0
- https://blockchain.info/rawaddr/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g?limit=0
- https://api.blockcypher.com/v1/btc/main/addrs/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g/balance

### THORChain and Ethereum public data

- https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204
- https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C
- Ethereum public JSON RPC at `https://ethereum.publicnode.com`, methods `eth_getTransactionByHash` and `eth_getBlockByHash`

## Source Quality Assessment

Confidence is high for balances, spend status, transaction times, and the THORChain to BTC output links. Multiple public sources agree for the Wasabi and live lead balances. Midgard, Ethereum JSON RPC, and BTC transaction data agree on the two THORChain output paths.

Confidence is medium for the overall BTC follow-through because the Wasabi to candidate step is probabilistic. Public Bitcoin APIs show transactions and current status. They do not validate a CoinJoin demix attribution.

The largest source caveat is BlockCypher's undercount on the candidate address lifetime total. That does not affect the conclusion that the candidate balance is zero or that the live lead remains unspent.

## Open Questions

1. Can the five smaller deposits to `bc1qwxwl...` be tied to specific sheet rows or other source records?
2. What evidence originally selected `bc1q9vl045...` as the post Wasabi candidate, and can that method be repeated from public data?
3. If the live lead moves, does the first hop touch a custodial service, bridge, mixer, or fresh self custody branch?
4. Can William provide the source for the sheet note that labels `bc1qwxwl...` as stolen funds after THORChain?

## Actionable Takeaways

1. Keep `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` on active watch. The large UTXO is still live.
2. In any external summary, say the sheet supports the THORChain to Wasabi root, while the candidate and live lead are follow-through leads outside the sheet.
3. Do not overstate `bc1q9vl045...`. Public evidence confirms its payment to the live lead, not its origin from William's Wasabi outputs.
4. Ask William for any missing notes or screenshots that explain the extra `2.03636221 BTC` in smaller deposits to `bc1qwxwl...`.
5. If the live address moves, immediately preserve Blockstream and mempool.space raw JSON, screenshots, mempool state, and the first output set.

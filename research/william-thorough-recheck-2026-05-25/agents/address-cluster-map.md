---
title: William spreadsheet address cluster map
type: research
tags: [crypto, osint, william, address-cluster, spreadsheet]
summary: Public chain checks show a coordinated July 2023 drain from 10 listed EVM wallets into THORChain, FixedFloat, and a SimpleSwap Binance deposit path.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-25
updated: 2026-05-25
---

## Executive Summary

The spreadsheet shows 14 visible outbound transactions from 10 listed source wallets, with chain confirmed timestamps on July 21 to July 22, 2023. Public chain evidence supports one coordinated drain cluster, but the spreadsheet and public data do not prove one real world attacker identity.

Most ETH routes to two exits: THORChain receives about 852.742831 ETH, including one direct deposit and one aggregated deposit carrying the same BTC memo address, and FixedFloat receives about 32.056094 ETH through one and two hop intermediates. The BNB row routes 8.6 BNB through one intermediate to a BscScan labeled `SimpleSwap: Binance Deposit` address.

## Scope handled

Task slug: `address-cluster-map`.

Scope covered:

- Source addresses in the spreadsheet.
- First hop recipient addresses.
- Repeated destinations.
- Likely service or contract labels from public chain sources.
- Whether the spreadsheet supports one actor or account cluster.

## Evidence sources read

Spreadsheet evidence:

- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/WARROOM-BRIEF.md`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/summary-visible-rows.csv`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/01-Summary.csv`
- Per wallet detail tabs under `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/04-*.csv` through `13-*.csv`

Raw public lookup evidence saved under:

- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/address-cluster-map/`

Key derived files:

- `normalized-transaction-table.json`: chain confirmed first hop transaction table.
- `first-hop-history-summary.json`: first hop recipient onward movement summaries.
- `eth-832801-second-hop.json`: repeated destination `0xB791...` second hop to FixedFloat.
- `bsc-08178-second-hop.json`: BSC first hop onward movement to `SimpleSwap: Binance Deposit`.
- `analysis-data.md`: readable table generated from raw lookups.

Public URLs used:

- `https://eth.blockscout.com/api/v2/transactions/<tx_hash>`
- `https://eth.blockscout.com/api/v2/addresses/<address>`
- `https://eth.blockscout.com/api/v2/addresses/<address>/transactions`
- `https://bsc-dataseed.binance.org/` JSON RPC
- `https://bscscan.com/tx/<tx_hash>`
- `https://bscscan.com/address/<address>`

## Findings

### 1. Spreadsheet source addresses

Confirmed from `01-Summary.csv` rows 23 to 33 and the visible summary extraction: the sheet lists 10 wallets under `All My wallets`.

| Source wallet | Summary source rows | Detail tab refs | Chain rows confirmed |
|---|---:|---|---:|
| `0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0` | 5 | `04-0xaadd5f.csv:5` | 1 |
| `0x1c0b5b8d36587d0516839df7ebfb49ad8f3c543c` | 6, 7, 8 | `05-0x1c0b5b8.csv:4-6` | 3 |
| `0x055e6b081f175db1170350ba4f23e3a8e0895492` | 9 | `06-0x055e6b08.csv:4` | 1 |
| `0xd20a9ed00e37fdaef0a064bc32feb10845053f09` | 10 | `07-0xd20a9.csv:4` | 1 |
| `0xa30e54cb3593c6afca653621c4d3ee2105f015aa` | 11 | `08-0xa30e54c.csv:4` | 1 |
| `0xdFb05c98320D126Bcc74F6EB7960E99669dcd49a` | 12 | `09-0xdFb05.csv:4` | 1 |
| `0x9Dc08Da4cBF74F81CFfb54CECbD8fDf6554E1D34` | 13, 14 | `10-0x9Dc08.csv:4-5` | 2 |
| `0x2656269bb878ca0c4250a0df4c15a9cfca0c21ac` | 15, 16 | `11-0x265626.csv:4-5` | 2 |
| `0xFA5F6eD82Ae1EAC484B91cCDE42fe7d64cb68D03` | 17 | `12-0xFA5F6e.csv:4` | 1 |
| `0xf40c09C782C74e932b81473ae68B078F31a358f6` | 18 | `13-0xf40c0.csv:4` | 1 |

Confidence: confirmed that these are the spreadsheet source wallets and that the listed transactions were sent from them on chain. Ownership of those source wallets remains self reported by the sheet; public chain data confirms movement but cannot verify ownership.

### 2. Repeated first hop destinations

Confirmed repeated destinations from summary source rows 5 to 18 and chain lookups:

| Destination | Count | Rows | Type and label | Finding |
|---|---:|---|---|---|
| `0xB7917eE3520C4AA56ADd5d55f6026EdeEBE99d02` | 6 | 10, 12, 14, 16, 17, 18 | EOA, unlabeled | Aggregates 18.475 ETH from six source wallets, then sends 18.46 ETH to `0x8328018C...`, which sends 18.459223 ETH to FixedFloat. Confidence: confirmed. |
| `0xeEC35fd50B5E7344b3E1A7F4384b3Cb9365e204A` | 2 | 7, 8 | EOA, unlabeled | Receives 623 ETH and 104.3 ETH from `0x1c0b...`, then sends 727.29568 ETH to THORChain Router with BTC memo `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`. Confidence: confirmed. |
| `0xD37BbE5744D730a1d98d8DC97c42F0Ca46aD7146` | 1 direct, plus one indirect | 5 direct, rows 7 to 8 indirect | Verified contract, `THORChain_Router`; Blockscout label `THORChain: THORChain Router v4.1.1` | Receives direct row 5 and indirect aggregate from `0xeEC35...`. Confidence: confirmed. |
| `0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F` | 5 downstream deposits | rows 6, 9, 10, 11, 12, 14, 15, 16, 17, 18 via intermediates | EOA with Blockscout tags `FixedFloat 1`, `HOT WALLET`, `Exchange`, `FIXEDFLOAT` | Receives downstream ETH from `0x6a7E...`, `0x4EC...`, `0xbdC...`, `0x09066...`, and `0x832801...`. Confidence: confirmed. |
| `0x08178b429CA29853fa33014F635D12bD7f706297` | 1 | 13 | BNB Smart Chain EOA | Receives 8.6 BNB, then six seconds later sends 8.6 BNB to BscScan labeled `SimpleSwap: Binance Deposit`. Confidence: confirmed. |

### 3. THORChain route

Confirmed THORChain route:

| Evidence row | Transaction | Chain UTC | Route | Amount | Notes |
|---:|---|---|---|---:|---|
| 5 | `0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204` | 2023-07-21 14:00:59 UTC | `0xaadd5f...` to THORChain Router | 125.447151477 ETH | `depositWithExpiry`; memo `=:BTC.BTC:bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s:704635983:t:30`. |
| 7 | `0x662e469715056d9501da5184ec4a2a466b05b3fa656c73d0fb067598b88013c2` | 2023-07-21 13:47:23 UTC | `0x1c0b...` to `0xeEC35...` | 623 ETH | First aggregate leg. |
| 8 | `0x2ed79b067f3afa2e636ae82f8c0c6cbd59d504aa7f25f146a4d22ef2186fc157` | 2023-07-21 13:56:11 UTC | `0x1c0b...` to `0xeEC35...` | 104.3 ETH | Second aggregate leg. |
| Derived | `0x40a3d546f349f9cf8e907b6676e6187ad01f24c76ad9d0b9d2958e8c9e059e2c` | 2023-07-21 13:56:59 UTC | `0xeEC35...` to THORChain Router | 727.29568 ETH | `depositWithExpiry`; memo `=:BTC.BTC:bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s:3000764182:t:30`. |

The THORChain route carries about 852.742831 ETH by confirmed downstream deposits. The two THORChain deposits share the same BTC destination in the decoded memo: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`.

Confidence: confirmed for transaction routing, amount, timestamp, contract label, and memo. Likely that these two THORChain deposits belong to the same drain path because they share the BTC memo destination and occur within minutes.

### 4. FixedFloat route

Confirmed FixedFloat route:

| Summary row or derived hop | Transaction | Chain UTC | Route | Amount | Service evidence |
|---:|---|---|---|---:|---|
| 6 | `0xb5e309a09f479a87f71b1258380d8b8e62c84163364b3b06762927c476c4d655` | 2023-07-22 09:52:11 UTC | `0x1c0b...` to `0x6a7E...` | 0.82 ETH | First hop. |
| Derived | `0x5bccf74958688d3edd15f9dcbe63fe19b998d2cabca8225ad0cd27b905402957` | 2023-07-22 10:27:59 UTC | `0x6a7E...` to `0x4E5B...` | 0.819622 ETH | `0x4E5B...` labeled `FixedFloat 1`. |
| 9 | `0x91a3d5976df4c7fb6d000a081855b4fc217d61d6e1b71f5c99205e7dc7c2f63f` | 2023-07-21 14:06:23 UTC | `0x055e...` to `0x4EC...` | 2.84 ETH | First hop. |
| Derived | `0xaa49f832a539cabee457ca3fc2e3e47e70ca7e364ba48161aae8c4e788d07b33` | 2023-07-21 14:34:11 UTC | `0x4EC...` to `0x4E5B...` | 2.839265 ETH | `0x4E5B...` labeled `FixedFloat 1`. |
| 11 | `0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3` | 2023-07-21 14:09:11 UTC | `0xa30E...` to `0xbdC4...` | 6.05 ETH | First hop. |
| Derived | `0x77b52669183c077392ae81111f16efd50ef2c69a87b1e04d618d5a951cbb87e6` | 2023-07-21 14:28:35 UTC | `0xbdC4...` to `0x4E5B...` | 6.049265 ETH | `0x4E5B...` labeled `FixedFloat 1`. |
| 15 | `0x72d855932534ca55ae820f5ed17de8ac729b1f05b093352b5bca19dcf868f26f` | 2023-07-21 18:55:47 UTC | `0x2656...` to `0x09066...` | 3.89 ETH | First hop. |
| Derived | `0xa3b002cda3abbe5317b8e2c68c53f5439ebc3c07c625dc576d191e79d095f7fd` | 2023-07-21 19:15:47 UTC | `0x09066...` to `0x4E5B...` | 3.888719 ETH | `0x4E5B...` labeled `FixedFloat 1`. |
| 10, 12, 14, 16, 17, 18 | six listed hashes | 2023-07-21 14:11:59 to 14:13:59 UTC | six sources to `0xB791...` | 18.475 ETH total | Aggregation cluster. |
| Derived | `0x5fa29671feaf777f437b706cdb95122e9e08896bc13fb3313cc0c4eae93e50db` | 2023-07-21 14:15:23 UTC | `0xB791...` to `0x832801...` | 18.46 ETH | Second hop. |
| Derived | `0xc16a810661e5c099bbe802c841751a4afdfff447caa3c609378170d1f59de793` | 2023-07-21 14:44:59 UTC | `0x832801...` to `0x4E5B...` | 18.459223 ETH | `0x4E5B...` labeled `FixedFloat 1`. |

The FixedFloat route accounts for about 32.056094 ETH by confirmed downstream receipts to `0x4E5B...`. Small deltas from the first hop amounts are consistent with gas and residual dust.

Confidence: confirmed that these ETH paths reach a Blockscout labeled FixedFloat hot wallet. The intermediate EOAs are unlabeled and should be treated as transit wallets, not service wallets.

### 5. BNB Smart Chain route

Confirmed BNB Smart Chain route:

| Summary row or derived hop | Transaction | Chain UTC | Route | Amount | Service evidence |
|---:|---|---|---|---:|---|
| 13 | `0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1` | 2023-07-21 18:36:20 UTC | `0x9Dc08...` to `0x08178...` | 8.6 BNB | BscScan transaction page confirms transfer and success. |
| Derived | `0xd68a6dccbb3aaed884ad5181dfcc2246e2efad690b838343202ec37ca157bb77` | 2023-07-21 18:36:26 UTC | `0x08178...` to `0xeE7f2D...` | 8.6 BNB | BscScan labels destination `SimpleSwap: Binance Deposit`. |

Confidence: confirmed for BSC transfer, amount, and second hop label from BscScan page metadata and raw HTML. The public page supports a service deposit path, but not the end user account behind that deposit.

### 6. Cluster conclusion

The spreadsheet supports one coordinated drain cluster with high confidence. Evidence:

- The sheet lists exactly 10 source wallets under `All My wallets`, and summary rows 5 to 18 contain 14 transactions from those wallets.
- Chain data confirms the source, destination, amount, status, and UTC timestamp for all 14 visible summary transactions.
- Six separate source wallets send to the same first hop address `0xB791...` inside a two minute window, then the aggregate moves onward to FixedFloat.
- `0x1c0b...` uses `0xeEC35...` as an aggregator, then that aggregator deposits to THORChain with the same BTC destination used by the direct THORChain row 5 deposit.
- Four smaller ETH paths and the `0xB791...` path converge on the same Blockscout labeled FixedFloat hot wallet `0x4E5B...`.
- The same EVM source address `0x9Dc08...` appears on Ethereum row 14 and BNB Smart Chain row 13, tying the BNB route to the same source wallet set.

The spreadsheet does not prove one real world attacker identity. It proves a coherent transaction cluster and strongly supports one drain campaign. Attribution to one person, exchange account, or service customer account would require service records from THORChain related infrastructure, FixedFloat, SimpleSwap, Binance, or law enforcement process.

Confidence: likely for one coordinated actor or operator cluster; confirmed for the transaction graph; unresolved for legal identity attribution.

## Contradictions and unresolved gaps

- The lower copied detail rows in `summary-visible-rows.csv` rows 42 to 45 are useful as hints but should not be trusted for timestamps without chain verification. Example: row 42 pairs `0x931e...` with `21 Jul, 2023 19:15:47 UTC`, while chain data places `0x931e...` at 2023-07-21 14:09:11 UTC. The 19:15:47 timestamp belongs to the downstream `0x09066...` to FixedFloat transaction; row 42 therefore mixes transaction references.
- The sheet proves listed transactions and a self reported wallet set. It does not independently prove William controlled all 10 source wallets.
- `0xB791...`, `0x832801...`, `0xeEC35...`, `0x6a7E...`, `0x4EC...`, `0xbdC4...`, `0x09066...`, and `0x08178...` are transit EOAs in the observed flow. Public data here does not identify who controlled them.
- Public data cannot identify the customer account at FixedFloat, SimpleSwap, Binance, or any THORChain interface provider.

## Repeatable commands

Run the local parser and lookup script:

```bash
python3 /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/address-cluster-map/fetch_and_analyze.py
```

Inspect normalized transactions:

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path('/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/address-cluster-map/normalized-transaction-table.json')
for t in json.loads(p.read_text()):
    print(t['summary_row'], t['chain'], t['chain_from'], '->', t['chain_to'], t['chain_amount_native'], t['token'], t['timestamp_utc'], t.get('method'))
PY
```

Verify one Ethereum transaction directly:

```bash
curl -sS 'https://eth.blockscout.com/api/v2/transactions/0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204' | python3 -m json.tool
```

Verify the repeated destination path:

```bash
curl -sS 'https://eth.blockscout.com/api/v2/addresses/0xB7917eE3520C4AA56ADd5d55f6026EdeEBE99d02/transactions' | python3 -m json.tool
curl -sS 'https://eth.blockscout.com/api/v2/addresses/0x8328018C863346937816833E8Eac958D85B23990/transactions' | python3 -m json.tool
```

Verify the BSC second hop:

```bash
curl -sSL -A 'Mozilla/5.0' 'https://bscscan.com/tx/0xd68a6dccbb3aaed884ad5181dfcc2246e2efad690b838343202ec37ca157bb77' | grep -E 'Description|SimpleSwap: Binance Deposit'
```

## Recommended next action for William

William should send exchanges and services a concise package with the exact transaction hashes above, grouped by route:

1. THORChain route: row 5 direct deposit and `0xeEC35...` aggregate deposit, both with BTC memo `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`.
2. FixedFloat route: downstream deposits to `0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F` from `0x6a7E...`, `0x4EC...`, `0xbdC4...`, `0x09066...`, and `0x832801...`.
3. SimpleSwap and Binance route: BSC row 13 first hop and the six second hop to `SimpleSwap: Binance Deposit`.

Do not provide seed phrases, private keys, passwords, 2FA codes, or exchange login access to anyone. The right request is transaction investigation and account freeze assistance using public transaction hashes and proof of wallet ownership that William chooses to provide directly.

## Open questions

- Can William independently prove control of each of the 10 source wallets, for example by historical exchange withdrawal records, wallet screenshots, or signed messages from non compromised addresses?
- Did the same event include any non EVM chains or off sheet transactions?
- Are there service support ticket numbers, police report numbers, or exchange case IDs that should be attached to the FixedFloat, SimpleSwap, Binance, or THORChain related requests?
- If William believes a separate October event occurred, which addresses and transaction hashes belong to that event? The visible spreadsheet rows analyzed here are July 2023 rows.

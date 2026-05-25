---
title: William spreadsheet independent contradiction audit
type: research
tags: [william-case, crypto-tracing, spreadsheet-audit, ethereum, bitcoin, thorchain, fixedfloat]
summary: Chain data confirms the main visible EVM rows are July 2023, but the sheet has row timestamp swaps, duplicate FixedFloat rows, one wrong FixedFloat amount and time, and unresolved gaps around the claimed 2021 and October events.
status: active
source: quick-research
confidence: high
created: 2026-05-25
updated: 2026-05-25
---

## Scope handled

Independent contradiction audit for task slug `independent-contradiction-audit`. I inspected the Google Sheet exports, visible transaction list, prior packet, and public chain data for the visible EVM rows and key BTC leads.

## Evidence sources read

Local source files:

- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/WARROOM-BRIEF.md`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/summary-visible-rows.csv`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/gid-1211660592.csv`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/william-source-spreadsheet.xlsx`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/manifest.md`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/*.csv`
- `/Users/alphab/.mdx/research/transaction-inventory.csv`
- `/Users/alphab/.mdx/research/william-crypto-case-dossier.md`
- `/Users/alphab/.mdx/research/william-friend-packet/START-HERE-WILLIAM.md`
- `/Users/alphab/.mdx/research/william-friend-packet/live-btc-finding-repeatable.md`
- `/Users/alphab/.mdx/research/william-friend-packet/copy-paste-messages.md`

Raw evidence saved under:

- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/independent-contradiction-audit/`

Key generated summaries:

- `evm-chain-summary.csv`
- `visible-vs-chain-comparison.csv`
- `btc-current-summary.json`
- `thorchain-midgard-summary.json`
- `wasabi-deposit-address-flow-summary.json`
- `fixedfloat-source-tx-aa49-summary.json`

## Findings

### 1. The visible Summary tab evidence is July 2023, not July 2021

**Confirmed.** The downloaded Google Sheet CSV and the file in Downloads have identical SHA256:

```text
251d96652640e7d1d41d2ae0210647ffcc6aa2a80e3ddeec0e193830ccfcc064
```

**Confirmed.** The workbook contains 13 tabs. `Fixed Float Deposit` and `Sheet5` are blank. The `Summary` tab has 14 primary outgoing rows from 10 EVM wallets, plus lower notes and copied FixedFloat rows.

**Confirmed.** Public chain data places the primary visible outgoing rows on July 21 and July 22, 2023 UTC. The source file name says `Stolen Crypto July 2021 - Summary.csv`, but the visible chain evidence does not support July 2021 for these rows.

**Likely.** The upper Summary tab date display is local time without a timezone, probably UTC minus four hours for July 2023. When interpreted that way, 12 of the 14 primary rows match chain timestamps exactly. Chain timestamps should be used in reports.

### 2. Two large row timestamps are swapped in the source sheet

**Confirmed.** The two `0x1c0b5b8...` THORChain staging transfers have source displayed times swapped relative to public chain data:

| Visible row | Tx | Sheet display | Sheet display as UTC minus four | Chain UTC | Result |
|---:|---|---|---|---|---|
| 7 | `0x662e469715056d9501da5184ec4a2a466b05b3fa656c73d0fb067598b88013c2` | `2023/07/21 9:56:11` | `2023-07-21T13:56:11Z` | `2023-07-21T13:47:23Z` | Sheet time is 8m48s late |
| 8 | `0x2ed79b067f3afa2e636ae82f8c0c6cbd59d504aa7f25f146a4d22ef2186fc157` | `2023/07/21 9:47:23` | `2023-07-21T13:47:23Z` | `2023-07-21T13:56:11Z` | Sheet time is 8m48s early |

**Confirmed.** Amounts and destination are correct for both rows, but the timestamps are reversed. Any external packet should use chain UTC:

- `0x662e...`: `2023-07-21T13:47:23Z`, `623 ETH`
- `0x2ed7...`: `2023-07-21T13:56:11Z`, `104.3 ETH`

### 3. The primary EVM totals reconcile to chain amounts, with only rounding on the THORChain router row

**Confirmed.** Chain sums for the 14 primary visible rows are:

```text
ETH: 884.822151477364040918
BNB: 8.6
```

The sheet reports:

```text
ETH: 884.8222
BNB: 8.6
```

**Confirmed.** The ETH difference is `0.000048522635959082 ETH`, caused by row 5 rounding `125.447151477364040918 ETH` to `125.4472 ETH`. This is not a material contradiction.

**Confirmed.** The Google CSV visible export formats row 16 amount as `-$3.89` for tx `0x72d855...`, but the XLSX extracted raw value and chain value are `3.89 ETH`. Treat `-$3.89` as a display or parser artifact, not a USD amount.

### 4. The lower FixedFloat table duplicates upper rows and contains one serious wrong amount and time

**Confirmed.** The lower FixedFloat table duplicates these upper transaction hashes:

- `0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3`
- `0x91a3d5976df4c7fb6d000a081855b4fc217d61d6e1b71f5c99205e7dc7c2f63f`
- `0x72d855932534ca55ae820f5ed17de8ac729b1f05b093352b5bca19dcf868f26f`
- `0xb5e309a09f479a87f71b1258380d8b8e62c84163364b3b06762927c476c4d655`

**Confirmed.** Do not add the lower FixedFloat total `11.43 ETH` to the loss total. It is a duplicate note section, not new loss.

**Confirmed.** The lower FixedFloat row for `0x931ebd...` is wrong in two ways:

| Field | Lower FixedFloat table | Chain data |
|---|---:|---:|
| Time | `2023-07-21T19:15:47Z` | `2023-07-21T14:09:11Z` |
| Amount | `3.88 ETH` | `6.05 ETH` |

This also makes the lower table total wrong if the listed tx hash is intended. Using the listed tx hashes, the four duplicated FixedFloat rows total `13.60 ETH`, not `11.43 ETH`.

**Confirmed.** The lower row for `0xb5e309...` lists the FixedFloat wallet as the same as the victim wallet `0x1c0b5b8...`. Chain data shows the tx recipient is `0x6a7e9ed15ea2c1c7787e68f2ca2df68379ed437e`. The lower table destination is not reliable for that row.

### 5. The separate FixedFloat source tx `0xaa49...` is real, but it is a child flow, not an extra direct loss row

**Confirmed.** The source CSV has a standalone FixedFloat section tx:

```text
0xaa49f832a539cabee457ca3fc2e3e47e70ca7e364ba48161aae8c4e788d07b33
```

Chain data shows:

```text
Time UTC: 2023-07-21T14:34:11Z
From: 0x4ec986035b635d09474fc390acdf5c107dda4c70
To:   0x4e5b2e1dc63f6b91cb6cd759936495434c7e972f
Value: 2.839265 ETH
```

**Likely.** This supports an indirect path from victim row 9 destination `0x4ec986...` toward the listed FixedFloat wallet `0x4E5B2e...`. It does not prove FixedFloat customer identity or service confirmation by itself.

### 6. The THORChain to BTC path is partially confirmed, but not all BTC entering the Wasabi deposit address is explained by the two Midgard actions

**Confirmed.** Liquify Midgard returned successful THORChain actions for both key inbound txids:

| Inbound txid | In asset | BTC output | BTC address |
|---|---:|---:|---|
| `655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204` | `125.44715147 ETH.ETH` | `7.29622713 BTC` | `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` |
| `40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C` | `727.29568 ETH.ETH` | `31.37643194 BTC` | `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` |

**Confirmed.** Those two outputs total `38.67265907 BTC`.

**Confirmed.** Blockstream shows the Wasabi deposit address was funded with `40.70902128 BTC` across 7 incoming transactions. Five smaller incoming transactions total `2.03636221 BTC`.

**Unresolved.** If external materials state or imply all `40.70902128 BTC` came from the two THORChain actions, that would be wrong. The two Midgard actions explain most of the balance, not all of it. William should identify whether the five smaller BTC deposits also came from his wallets, another swap, or unrelated funds.

### 7. The live BTC lead remains live, but ownership and demix linkage remain low confidence

**Confirmed.** A fresh Blockstream recheck at `2026-05-25T15:08:23Z` shows:

```text
Address: bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
Funded: 649,998,534 sats
Spent: 0 sats
Balance: 6.49998534 BTC
UTXOs: 2
Mempool txs: 0
```

**Confirmed.** The large funding tx is:

```text
164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187
2023-10-19T11:22:51Z
6.49998240 BTC
```

**Confirmed.** The second UTXO is the `294` sat March 2026 dust output:

```text
4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5
2026-03-11T22:02:44Z
294 sats
```

**Confirmed.** Prior packet language correctly calls the Wasabi demix path low confidence. Public chain data proves current balance and spend status, not ownership or final attribution.

### 8. Prior packet has a wrong Binance branch timestamp

**Confirmed.** `william-crypto-case-dossier.md` says tx `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287` happened at `2024-06-22 15:44:45 UTC`.

**Confirmed.** Fresh Blockstream data gives `2024-06-22T14:51:25Z` for that tx.

**Required correction.** Any William packet should use `2024-06-22T14:51:25Z` unless another authoritative chain source proves otherwise.

### 9. The spreadsheet does not prove two hacks

**Confirmed.** The visible spreadsheet supports one July 2023 cluster of EVM wallet outflows, plus copied notes and downstream BTC references.

**Unresolved.** The file name says July 2021. The chain evidence for the visible rows says July 2023. The current files do not prove a July 2021 event.

**Unresolved.** The brief says William reports a second hack “last October.” The current packet contains October 2023 downstream BTC activity on a low confidence post Wasabi branch, but I did not find spreadsheet evidence of a separate October hack event. William needs to clarify the exact October year, affected wallets, source transactions, and whether this was a separate compromise or later movement from the July 2023 trail.

## Recommended next action for William

1. **Confirm dates.** William should state the exact incident dates and timezone. The visible chain data says July 21 to July 22, 2023 UTC for the main EVM outflows. It does not support July 2021 by itself.
2. **Separate source losses from downstream leads.** Count the 14 primary visible EVM rows once. Do not add lower FixedFloat duplicate rows as new losses.
3. **Correct the packet before sending.** Fix the row 7 and row 8 swapped timestamps, the lower FixedFloat `0x931ebd...` amount and time, the lower `0xb5e309...` destination, and the Binance branch timestamp.
4. **Fill the BTC gap.** If claiming the whole `40.70902128 BTC` Wasabi deposit balance as stolen, identify evidence for the five smaller deposits totaling `2.03636221 BTC`.
5. **Keep the caveat.** The live BTC balance is confirmed. The Wasabi demix path and ownership attribution remain investigative leads only.

## Repeatable commands and URLs

Run the chain fetcher:

```bash
python3 /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/independent-contradiction-audit/fetch_chain_evidence.py
```

Inspect summaries:

```bash
cat /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/independent-contradiction-audit/evm-chain-summary.csv
cat /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/independent-contradiction-audit/visible-vs-chain-comparison.csv
cat /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/independent-contradiction-audit/btc-current-summary.json
cat /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/independent-contradiction-audit/wasabi-deposit-address-flow-summary.json
```

Browser checks:

- https://etherscan.io/tx/0x662e469715056d9501da5184ec4a2a466b05b3fa656c73d0fb067598b88013c2
- https://etherscan.io/tx/0x2ed79b067f3afa2e636ae82f8c0c6cbd59d504aa7f25f146a4d22ef2186fc157
- https://etherscan.io/tx/0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3
- https://etherscan.io/tx/0xaa49f832a539cabee457ca3fc2e3e47e70ca7e364ba48161aae8c4e788d07b33
- https://blockstream.info/address/bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s
- https://blockstream.info/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
- https://blockstream.info/tx/29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287

## Open questions

- What exact year did William mean by “last October”?
- Does William have source evidence for the five smaller BTC deposits into `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`?
- Is the lower FixedFloat `3.88 ETH` entry meant to refer to a different transaction than `0x931ebd...`?
- Does William have FixedFloat order IDs, payout addresses, or ticket numbers that can validate service attribution?

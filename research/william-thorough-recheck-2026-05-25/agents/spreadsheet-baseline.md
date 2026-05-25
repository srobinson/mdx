---
title: William spreadsheet baseline audit
type: research
tags: [william, crypto, spreadsheet, chain-audit]
summary: Audits William's XLSX and CSV exports, normalizes visible rows, and reconciles spreadsheet dates with public chain timestamps.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-25
updated: 2026-05-25
---

## Executive Summary

The local Google Sheet evidence contains one dated cluster of visible transactions: July 21 to July 22, 2023. Confidence: confirmed. I found 14 unique summary transactions across 10 wallets, with 13 Ethereum transactions and one BSC transaction, plus a lower Fixed Float table that repeats four of those transaction hashes. Confidence: confirmed. The sheet does not prove a 2021 event or an October event from the spreadsheet rows inspected. Confidence: confirmed.

## Scope Handled

Audit of the local XLSX, the primary Google Sheet CSV export, extracted tab CSVs, visible row extraction, blank tabs, Excel serial date conversion, duplicate lower copied rows, and date contradictions. Confidence: confirmed.

## Evidence Sources Read

1. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/WARROOM-BRIEF.md`. Confidence: confirmed.
2. `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/william-source-spreadsheet.xlsx`. Confidence: confirmed.
3. `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/gid-1211660592.csv`. Confidence: confirmed.
4. `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/manifest.md`. Confidence: confirmed.
5. `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/*.csv`. Confidence: confirmed.
6. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/summary-visible-rows.csv`. Confidence: confirmed.
7. Public JSON RPC queries against `https://ethereum.publicnode.com` and `https://bsc-dataseed.binance.org`, saved under `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/spreadsheet-baseline/rpc/`. Confidence: confirmed.

## Generated Evidence

1. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/spreadsheet-baseline/audit_spreadsheet.py`. Confidence: confirmed.
2. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/spreadsheet-baseline/workbook-structure.json`. Confidence: confirmed.
3. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/spreadsheet-baseline/csv-profiles.json`. Confidence: confirmed.
4. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/spreadsheet-baseline/normalized-spreadsheet-rows.csv`. Confidence: confirmed.
5. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/spreadsheet-baseline/chain-times.csv`. Confidence: confirmed.
6. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/spreadsheet-baseline/date-comparisons.csv`. Confidence: confirmed.
7. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/spreadsheet-baseline/chain-transactions-native.csv`. Confidence: confirmed.

## Findings

### Workbook and tab structure

The XLSX contains 13 visible sheets. Confidence: confirmed. `Fixed Float Deposit` and `Sheet5` are blank, visible tabs with zero XML rows and zero nonempty cells. Confidence: confirmed.

| Sheet | Rows or XML rows | Nonempty rows or cells | Notes |
|---|---:|---:|---|
| Summary | 52 XML rows, max cell row 57 | 194 cells, 50 visible nonempty rows | Main table, wallet list, Fixed Float notes, ThorChain and Wasabi notes. Confidence: confirmed. |
| Fixed Float Deposit | 0 | 0 | Blank tab. Confidence: confirmed. |
| Sheet5 | 0 | 0 | Blank tab. Confidence: confirmed. |
| 10 per wallet tabs | 4 to 8 CSV rows each | 14 total transaction rows | Detail tabs repeat the 14 upper summary transaction hashes. Confidence: confirmed. |

The Google Sheet CSV export has 57 rows and 10 columns. Confidence: confirmed. The extracted Summary CSV has 52 rows and 10 maximum columns because completely blank trailing rows are not emitted the same way. Confidence: confirmed.

### Visible transaction inventory

Rows 5 to 18 of `gid-1211660592.csv` contain 14 upper summary transaction rows. Confidence: confirmed. They cover 10 wallet addresses, 13 Ethereum transfers, and one BSC transfer. Confidence: confirmed.

The sheet totals match the normalized rows: `-884.8222 ETH`, `-8.6 BNB`, and `$1,675,929.20` displayed value. Confidence: confirmed.

All 14 upper summary transaction hashes also appear in the per wallet detail tabs. Confidence: confirmed. The detail tabs do not add a second dated event; they repeat the same July 2023 transaction set. Confidence: confirmed.

### Excel serial date conversion

The XLSX stores upper table dates as Excel serial values. Confidence: confirmed. Example: serial `45128.41735` converts with the standard 1899 12 30 Excel or Google Sheets epoch to `2023-07-21 10:00:59` as a wall clock value. Confidence: confirmed.

Public chain timestamps show that the upper summary wall clock is usually four hours behind UTC. Confidence: confirmed. Example: transaction `0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204` is on chain at `2023-07-21T14:00:59Z`, while the sheet shows `2023/07/21 10:00:59`. Confidence: confirmed. The likely interpretation is that the upper summary table is displayed in UTC minus 4, probably EDT, without a timezone label. Confidence: likely.

### Date contradictions

Most upper summary rows match public chain time if interpreted as UTC minus 4. Confidence: confirmed. Two adjacent rows for wallet `0x1c0b5b8d36587d0516839df7ebfb49ad8f3c543c` appear swapped:

| Summary row | Tx hash | Sheet time | Chain UTC | Finding |
|---:|---|---|---|---|
| 7 | `0x662e469715056d9501da5184ec4a2a466b05b3fa656c73d0fb067598b88013c2` | `2023/07/21 9:56:11` | `2023-07-21T13:47:23Z` | Does not match UTC minus 4. Confidence: confirmed. |
| 8 | `0x2ed79b067f3afa2e636ae82f8c0c6cbd59d504aa7f25f146a4d22ef2186fc157` | `2023/07/21 9:47:23` | `2023-07-21T13:56:11Z` | Does not match UTC minus 4. Confidence: confirmed. |

If the two sheet times are exchanged and treated as UTC minus 4, both rows match the public chain timestamps exactly. Confidence: likely. This looks like a copied or sorted date error in the spreadsheet, not a second event. Confidence: likely.

### Lower Fixed Float copied rows

Rows 42 to 45 of `gid-1211660592.csv` are a separate lower table headed `Deposit to Fixed Float`. Confidence: confirmed. The row shape is `My Wallet`, `Time`, `Amount (ETH)`, `TX`, `Fixed Float Wallet`, not the upper summary shape. Confidence: confirmed. `summary-visible-rows.csv` records these rows as shifted columns, so I normalized them separately in `normalized-spreadsheet-rows.csv`. Confidence: confirmed.

The lower table repeats four transaction hashes from the upper summary table. Confidence: confirmed.

| Lower row | Tx hash | Lower time | Chain UTC | Amount issue | Finding |
|---:|---|---|---|---|---|
| 42 | `0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3` | `21 Jul, 2023 19:15:47 UTC` | `2023-07-21T14:09:11Z` | Lower says `3.88 ETH`; native tx value is `6.05 ETH`. | Contradiction. This row cannot be treated as the timestamp or amount of the linked transaction without another source. Confidence: confirmed. |
| 43 | `0x91a3d5976df4c7fb6d000a081855b4fc217d61d6e1b71f5c99205e7dc7c2f63f` | `21 Jul, 2023 14:06 UTC` | `2023-07-21T14:06:23Z` | Lower says `2.84 ETH`; native tx value is `2.84 ETH`. | Matches to minute precision. Confidence: likely. |
| 44 | `0x72d855932534ca55ae820f5ed17de8ac729b1f05b093352b5bca19dcf868f26f` | `21 Jul, 2023 18:55:47 UTC` | `2023-07-21T18:55:47Z` | Lower says `3.89 ETH`; native tx value is `3.89 ETH`. | Matches exactly. Confidence: confirmed. |
| 45 | `0xb5e309a09f479a87f71b1258380d8b8e62c84163364b3b06762927c476c4d655` | `22 Jul, 2023 09:52:11 UTC` | `2023-07-22T09:52:11Z` | Lower says `0.82 ETH`; native tx value is `0.82 ETH`. | Matches exactly. Confidence: confirmed. |

### What the spreadsheet proves

The spreadsheet proves a July 21 to July 22, 2023 cluster involving the listed hot wallets and the listed public transactions. Confidence: confirmed. It does not, by itself, prove a 2021 compromise, an October compromise, or two separate incidents. Confidence: confirmed. The narrative line `On xx my 10 hot wallets were exploited` leaves the incident date blank. Confidence: confirmed.

## Repeatable Commands and URLs

Run the audit and rebuild the normalized files:

```bash
python3 /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/spreadsheet-baseline/audit_spreadsheet.py
```

Inspect the key outputs:

```bash
cat /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/spreadsheet-baseline/workbook-structure.json
column -s, -t /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/spreadsheet-baseline/date-comparisons.csv | less -S
column -s, -t /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/spreadsheet-baseline/chain-times.csv | less -S
```

Public chain URLs used by the rows are embedded in `normalized-spreadsheet-rows.csv`. Confidence: confirmed. The JSON RPC endpoints used were `https://ethereum.publicnode.com` and `https://bsc-dataseed.binance.org`. Confidence: confirmed.

## Recommended Next Action for William

Ask William for the missing source behind lower Fixed Float row 42, specifically why the row says `19:15:47 UTC` and `3.88 ETH` while the linked transaction hash is on chain at `14:09:11 UTC` with a native value of `6.05 ETH`. Confidence: confirmed. Also ask William to identify which evidence file, exchange record, wallet export, or investigator note supports any 2021 or October incident, because this spreadsheet only supports the July 2023 cluster. Confidence: confirmed.

## Open Questions

1. What source generated the lower Fixed Float row 42 timestamp and amount? Confidence: unresolved.
2. Are the row 7 and row 8 times manual copy errors, or did the source export swap the displayed timestamps? Confidence: unresolved.
3. Where is the evidence for the claimed 2021 event or the claimed October event? Confidence: unresolved.

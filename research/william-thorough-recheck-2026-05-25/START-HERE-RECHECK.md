# William Crypto Recheck: Start Here

Created: 2026-05-25

## Bottom Line

The actual Google Sheet does not support the statement "July 2021" as the date of the visible theft transactions.

The visible spreadsheet transactions that we can verify on public chains occurred from:

`2023-07-21 13:47:23 UTC` through `2023-07-22 09:52:11 UTC`

That is one confirmed July 2023 on chain loss cluster, not proof of a 2021 hack and not proof of a separate "last October" hack.

The October 2023 Bitcoin movement is still important. It is a downstream lead from the Wasabi tracing work, and the live BTC lead still appears unspent. It should be described as a lead unless William can provide separate records showing it was a second hack.

## What Changed From The Earlier Packet

1. The spreadsheet title or file name is misleading. It says July 2021, but the visible chain transactions are July 2023.
2. The spreadsheet stores upper table dates as Excel serial values and displays them as wall clock times, usually UTC minus four hours. Public chain UTC should control.
3. Rows 7 and 8 have swapped or mismatched displayed times.
4. Lower FixedFloat row 42 conflicts with the chain timestamp and native amount for the transaction hash shown in that row.
5. The sheet directly supports the BTC root address `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` through THORChain.
6. The two confirmed THORChain actions explain `38.67265907 BTC` of the Wasabi address funding, not the full `40.70902128 BTC`. Five smaller BTC deposits totaling `2.03636221 BTC` still need source evidence before claiming the whole Wasabi amount as spreadsheet supported.
7. The demix candidate and live BTC lead remain investigative leads outside the spreadsheet, not spreadsheet proved facts.
8. The earlier packet had a wrong timestamp for Bitcoin tx `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287`. Use `2024-06-22T14:51:25Z`, not `2024-06-22T15:44:45Z`, unless another authoritative chain source proves otherwise.
9. Address mapping supports one likely coordinated July 2023 drain cluster, but it does not prove the real world identity of the attacker.

## Source Provenance

Google Sheet:

`https://docs.google.com/spreadsheets/d/1gxpxBDgzdLDm_MA2bA5U0szlEE01a-mJ2TlQ4-JV8dY/edit?gid=1211660592#gid=1211660592`

Local frozen copies:

- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/gid-1211660592.csv`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/william-source-spreadsheet.xlsx`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/`

The Google Sheet CSV export and the previous Downloads CSV are identical:

`251d96652640e7d1d41d2ae0210647ffcc6aa2a80e3ddeec0e193830ccfcc064`

The XLSX contains 13 visible tabs. Two are blank: `Fixed Float Deposit` and `Sheet5`.

## Confirmed Visible Transaction Set

The Summary tab has 14 unique upper table transactions:

- 13 Ethereum mainnet transactions.
- 1 BNB Smart Chain native BNB transfer.
- 10 listed source wallets.
- Spreadsheet displayed totals of `$1,675,929.20`, `884.8222 ETH`, and `8.6 BNB`.

Public chain verification totals:

- `884.822151477364040918 ETH`
- `8.6 BNB`

The public chain total rounds to the spreadsheet total of `884.8222 ETH`.

## Canonical Chain Timeline

Use these UTC chain timestamps as the source of truth.

| UTC time | Chain | Source row | From | To | Amount | Transaction |
|---|---|---:|---|---|---:|---|
| 2023-07-21T13:47:23Z | Ethereum | 7 | `0x1c0b5b8d36587d0516839df7ebfb49ad8f3c543c` | `0xeec35fd50b5e7344b3e1a7f4384b3cb9365e204a` | 623 ETH | `0x662e469715056d9501da5184ec4a2a466b05b3fa656c73d0fb067598b88013c2` |
| 2023-07-21T13:56:11Z | Ethereum | 8 | `0x1c0b5b8d36587d0516839df7ebfb49ad8f3c543c` | `0xeec35fd50b5e7344b3e1a7f4384b3cb9365e204a` | 104.3 ETH | `0x2ed79b067f3afa2e636ae82f8c0c6cbd59d504aa7f25f146a4d22ef2186fc157` |
| 2023-07-21T14:00:59Z | Ethereum | 5 | `0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0` | THORChain router `0xd37bbe5744d730a1d98d8dc97c42f0ca46ad7146` | 125.44715147736405 ETH | `0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204` |
| 2023-07-21T14:06:23Z | Ethereum | 9 | `0x055e6b081f175db1170350ba4f23e3a8e0895492` | `0x4ec986035b635d09474fc390acdf5c107dda4c70` | 2.84 ETH | `0x91a3d5976df4c7fb6d000a081855b4fc217d61d6e1b71f5c99205e7dc7c2f63f` |
| 2023-07-21T14:09:11Z | Ethereum | 11 | `0xa30e54cb3593c6afca653621c4d3ee2105f015aa` | `0xbdc4b2d85d9dcc42c3799b4569bd1d7d25d29c03` | 6.05 ETH | `0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3` |
| 2023-07-21T14:11:59Z | Ethereum | 17 | `0xfa5f6ed82ae1eac484b91ccde42fe7d64cb68d03` | `0xb7917ee3520c4aa56add5d55f6026edeebe99d02` | 5.02 ETH | `0x3f58b9738767a04a8d4701052cbfa378f7cdf9d8a0cfac34b43b0d62f766a7e8` |
| 2023-07-21T14:12:35Z | Ethereum | 10 | `0xd20a9ed00e37fdaef0a064bc32feb10845053f09` | `0xb7917ee3520c4aa56add5d55f6026edeebe99d02` | 6.451 ETH | `0xc2235fdf93d6ed97f17ea248d40fbc6c910cb502a63c75f0bb131bbb0fb465a8` |
| 2023-07-21T14:12:47Z | Ethereum | 12 | `0xdfb05c98320d126bcc74f6eb7960e99669dcd49a` | `0xb7917ee3520c4aa56add5d55f6026edeebe99d02` | 1.872 ETH | `0x0fa037ee4e0a99004dd98ca4827a9aaa9e45e56acd2b74334f09b16ad57050c3` |
| 2023-07-21T14:13:11Z | Ethereum | 18 | `0xf40c09c782c74e932b81473ae68b078f31a358f6` | `0xb7917ee3520c4aa56add5d55f6026edeebe99d02` | 2.814 ETH | `0x85955c171d41591fb52b85f3e4135704f2afb4305ea9ceee1de1ba503703e7f1` |
| 2023-07-21T14:13:35Z | Ethereum | 14 | `0x9dc08da4cbf74f81cffb54cecbd8fdf6554e1d34` | `0xb7917ee3520c4aa56add5d55f6026edeebe99d02` | 1.571 ETH | `0xa2dc0cff0e555bf26d8044e39e92071e69587e62bfe4128f827b0eb9bdfc8681` |
| 2023-07-21T14:13:59Z | Ethereum | 16 | `0x2656269bb878ca0c4250a0df4c15a9cfca0c21ac` | `0xb7917ee3520c4aa56add5d55f6026edeebe99d02` | 0.747 ETH | `0xd5a730adbe95e809d765372997260dd7057e959399e9b41d415816218de3686d` |
| 2023-07-21T18:36:20Z | BSC | 13 | `0x9dc08da4cbf74f81cffb54cecbd8fdf6554e1d34` | `0x08178b429ca29853fa33014f635d12bd7f706297` | 8.6 BNB | `0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1` |
| 2023-07-21T18:55:47Z | Ethereum | 15 | `0x2656269bb878ca0c4250a0df4c15a9cfca0c21ac` | `0x09066e7857d3a9a53c9142f8a7effcbc7989f1b5` | 3.89 ETH | `0x72d855932534ca55ae820f5ed17de8ac729b1f05b093352b5bca19dcf868f26f` |
| 2023-07-22T09:52:11Z | Ethereum | 6 | `0x1c0b5b8d36587d0516839df7ebfb49ad8f3c543c` | `0x6a7e9ed15ea2c1c7787e68f2ca2df68379ed437e` | 0.82 ETH | `0xb5e309a09f479a87f71b1258380d8b8e62c84163364b3b06762927c476c4d655` |

Machine readable version:

`/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/orchestrator-chain-check-fast/verified-chain-timestamps.csv`

## Source Wallets In The Spreadsheet

The spreadsheet lists these 10 source wallets in the visible July 2023 cluster:

1. `0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0`
2. `0x1c0b5b8d36587d0516839df7ebfb49ad8f3c543c`
3. `0x055e6b081f175db1170350ba4f23e3a8e0895492`
4. `0xd20a9ed00e37fdaef0a064bc32feb10845053f09`
5. `0xa30e54cb3593c6afca653621c4d3ee2105f015aa`
6. `0xdfb05c98320d126bcc74f6eb7960e99669dcd49a`
7. `0x9dc08da4cbf74f81cffb54cecbd8fdf6554e1d34`
8. `0x2656269bb878ca0c4250a0df4c15a9cfca0c21ac`
9. `0xfa5f6ed82ae1eac484b91ccde42fe7d64cb68d03`
10. `0xf40c09c782c74e932b81473ae68b078f31a358f6`

William should confirm these were wallets he controlled. He should not send seed phrases, private keys, wallet files, passwords, recovery phrases, 2FA codes, or remote access.

## Route Map

Public chain data supports three major routes from the visible July 2023 rows.

### THORChain Route

Confirmed.

- Spreadsheet row 5 sent `125.44715147736405 ETH` from `0xaadd5f...` to THORChain Router.
- Spreadsheet rows 7 and 8 sent `623 ETH` and `104.3 ETH` from `0x1c0b...` to `0xeec35...`.
- `0xeec35...` then sent `727.29568 ETH` to THORChain Router.
- Both THORChain swaps used the same BTC memo destination: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`.

### FixedFloat Route

Confirmed as a route to a publicly labeled FixedFloat hot wallet. Public chain data does not identify the customer account behind it.

- `0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F` is labeled by Blockscout as `FixedFloat 1`, `HOT WALLET`, `Exchange`, `FIXEDFLOAT`.
- Multiple source rows move through transit wallets into `0x4E5B...`.
- The repeated destination `0xB7917eE3520C4AA56ADd5d55f6026EdeEBE99d02` aggregates six source wallet payments totaling `18.475 ETH`, then sends `18.46 ETH` to `0x832801...`, which sends `18.459223 ETH` onward to the FixedFloat labeled wallet.
- Other downstream deposits to the FixedFloat labeled wallet come through `0x6a7E...`, `0x4EC...`, `0xbdC4...`, and `0x09066...`.

### BSC SimpleSwap And Binance Route

Confirmed as a route to a BscScan labeled SimpleSwap Binance deposit address. Public data does not identify the end user account.

- Spreadsheet row 13 sent `8.6 BNB` from `0x9Dc08...` to `0x08178...`.
- Six seconds later, `0x08178...` sent `8.6 BNB` to `0xeE7f2D...`.
- BscScan labels that destination as `SimpleSwap: Binance Deposit`.

## Spreadsheet Date Problems

These should be explained clearly before any official report is updated.

1. File name or title says July 2021, but public chain data says the visible transactions are July 2023.
2. Most upper table times are four hours behind chain UTC, consistent with EDT wall clock display.
3. Rows 7 and 8 appear to have swapped displayed times. The transaction hashes and amounts are still valid, but the displayed times do not match their chain timestamps.
4. Lower FixedFloat row 42 conflicts with public chain data. It lists `21 Jul, 2023 19:15:47 UTC` and `3.88 ETH` for transaction `0x931e...`, but the chain transaction is `2023-07-21 14:09:11 UTC` and `6.05 ETH`.
5. Lower rows 43, 44, and 45 mostly match chain timestamps, but row 43 omits seconds.

## THORChain To BTC Evidence

The spreadsheet supports a direct bridge from the July 2023 ETH loss into this BTC address:

`bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`

Confirmed path 1:

```text
Spreadsheet row 5
0xaadd5f... -> THORChain router
Ethereum tx 0x655a...
THORChain Midgard swap to BTC
BTC tx ca88...
7.29622713 BTC to bc1qwxwl...
BTC tx ca88... includes an OP_RETURN reference to the Ethereum inbound tx hash.
```

Confirmed path 2:

```text
Spreadsheet rows 7 and 8
0x1c0b5... -> 0xeec35...
Ethereum txs 0x662e... and 0x2ed7...
0xeec35... -> THORChain router
Ethereum tx 0x40a3...
THORChain Midgard swap to BTC
BTC tx d40f...
31.37643194 BTC to bc1qwxwl...
```

Those two THORChain outputs total:

`38.67265907 BTC`

The Wasabi deposit address lifetime received amount is:

`40.70902128 BTC`

The remaining `2.03636221 BTC` was not tied to a specific visible spreadsheet row in this recheck.

This is an important boundary. The spreadsheet and THORChain evidence strongly support most of the BTC entering `bc1qwxwl...`, but not the full lifetime amount. William should provide the source for the five smaller BTC deposits before any packet says the entire `40.70902128 BTC` was proven from the visible spreadsheet rows.

## Bitcoin Followthrough

Wasabi deposit address:

`bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`

Confirmed status:

- Funded: `40.70902128 BTC`
- Spent: `40.70902128 BTC`
- Current balance: `0 BTC`
- Mempool transactions: `0`

Low confidence post Wasabi candidate:

`bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`

Confirmed status:

- Funded and fully spent.
- Not present in the spreadsheet.
- Public data confirms it later sent `6.49998240 BTC` to the live lead.
- Public data does not prove the Wasabi coinjoin path from William's deposit to this candidate. It remains a low confidence demix lead.
- WalletExplorer placed the Wasabi deposit address, candidate address, and live BTC lead in three different public wallet IDs. That does not disprove the lead, but it means public co spend clustering does not prove it.

Live BTC lead:

`bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`

Confirmed status as of the recheck:

- Balance: `6.49998534 BTC`
- Spent: `0 BTC`
- Mempool transactions: `0`
- Main funding transaction: `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187`
- Main funding time: `2023-10-19 11:22:51 UTC`

This is the most actionable lead, but it should be framed carefully:

> The live BTC address is a downstream investigative lead from the low confidence Wasabi demix candidate. It is not independently proven by the spreadsheet.

## How To Describe The Incident Right Now

Use this conservative wording:

```text
The evidence currently reviewed supports one confirmed July 21 to July 22, 2023 on chain loss cluster involving 10 listed EVM wallets, 13 Ethereum transactions, and one BSC transaction. The spreadsheet shows approximately 884.8222 ETH and 8.6 BNB.

The spreadsheet file name or title references July 2021, but the visible public chain transactions in that spreadsheet occurred in July 2023. I need to provide separate source evidence before describing any 2021 event as confirmed.

There is also a downstream Bitcoin lead funded on October 19, 2023 that appears to remain unspent. That October Bitcoin movement is an investigative lead, not proof by itself of a separate October hack.

The visible July 2023 transaction graph routes funds through THORChain, FixedFloat related wallets, and a BSC path to a SimpleSwap labeled Binance deposit. Public chain data supports the routing, but service records would be needed to identify accounts or persons behind those destinations.
```

## Exact Questions For William

William should answer these before any official report is updated:

1. Did you have one incident or two separate incidents?
2. When you say "last October", which year do you mean: October 2023, October 2024, or October 2025?
3. What exact date, time, and time zone did you first see unauthorized activity for each incident?
4. Were the 10 source wallets above wallets you controlled?
5. If there was a 2021 hack, what transaction hashes, wallet addresses, screenshots, exchange emails, support tickets, police reports, or IC3 receipts prove the 2021 event?
6. If there was an October hack, what transaction hashes, wallet addresses, screenshots, exchange emails, support tickets, police reports, or IC3 receipts prove the October event?
7. Were the October 2023 Bitcoin movements something you saw as a new theft, or later movement of funds from the July 2023 trail?
8. What is the source for lower FixedFloat row 42, which conflicts with the chain timestamp and amount?
9. What is the source for the five smaller BTC deposits into `bc1qwxwl...` that total `2.03636221 BTC`?
10. Do you have original exports for Debank, Etherscan, BscScan, Arkham, THORChain, FixedFloat, Binance, THORSwap, wallet apps, or exchange support tickets?
11. What reports have already been filed, and what report numbers exist?

## Copy Paste Message To William

```text
William, I rechecked the actual spreadsheet against public chain data.

Important correction: the spreadsheet file name or title says July 2021, but the visible transactions in the spreadsheet verify on chain as July 21 to July 22, 2023 UTC.

The reviewed spreadsheet supports one confirmed July 2023 on chain loss cluster:

- 13 Ethereum transactions
- 1 BNB Smart Chain transaction
- 10 listed source wallets
- About 884.8222 ETH and 8.6 BNB

It does not, by itself, prove a 2021 hack. It also does not prove a separate "last October" hack.

There is a Bitcoin lead that was funded on October 19, 2023 and appears to remain unspent, but that is currently a downstream tracing lead from the Wasabi analysis. It should not be described as a separate hack unless you have separate evidence for that event.

Can you please answer these before we update any reports:

1. Did you have one incident or two separate incidents?
2. When you say "last October", what year do you mean?
3. What exact date, time, and time zone belongs to each incident?
4. Were these 10 wallets yours before the incident?
5. If there was a 2021 hack, please send the transaction hashes, wallet addresses, screenshots, emails, support tickets, report numbers, or original exports that prove the 2021 event.
6. If there was an October hack, please send the transaction hashes, wallet addresses, screenshots, emails, support tickets, report numbers, or original exports that prove the October event.
7. If you are claiming the full 40.70902128 BTC Wasabi deposit amount, please send the source evidence for the five smaller BTC deposits that are not explained by the two confirmed THORChain swaps.
8. Please do not send seed phrases, private keys, passwords, 2FA codes, recovery files, or anything that can sign transactions.

For now, the safest wording is: "confirmed July 2023 on chain loss cluster, plus a later Bitcoin tracing lead."
```

## Repeatable Verification

Run the EVM timestamp checker:

```bash
python3 /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/scripts/evm_tx_timestamp_check.py
```

Read the canonical EVM CSV:

```bash
cat /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/orchestrator-chain-check-fast/verified-chain-timestamps.csv
```

Run the spreadsheet baseline audit:

```bash
python3 /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/spreadsheet-baseline/audit_spreadsheet.py
```

Check the live BTC lead:

```bash
ADDR='bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g'
curl -fsS "https://blockstream.info/api/address/$ADDR" | jq '{chain_stats, mempool_stats}'
curl -fsS "https://mempool.space/api/address/$ADDR" | jq '{chain_stats, mempool_stats}'
curl -fsS "https://blockstream.info/api/address/$ADDR/utxo" | jq .
```

Check the THORChain actions:

```bash
curl -fsS 'https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204' | jq '.actions[0] | {date,type,status,in,out}'
curl -fsS 'https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C' | jq '.actions[0] | {date,type,status,in,out}'
```

Run the next public demix audit step:

```bash
# Example for one Wasabi shaped spend.
TX=447484229542bdf306892f60fdd328bdfe7c670e42013af4247302e6d3bf0be8
curl -fsS "https://blockstream.info/api/tx/$TX" > "$TX.json"
curl -fsS "https://blockstream.info/api/tx/$TX/outspends" > "$TX-outspends.json"
jq -r '.vout[] | [.scriptpubkey_address, .value, .scriptpubkey_type] | @csv' "$TX.json"
jq -r '.[] | [.spent, .txid, .vin] | @csv' "$TX-outspends.json"
```

## Supporting Agent Reports

- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/agents/spreadsheet-baseline.md`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/agents/eth-tx-verification.md`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/agents/bsc-crosschain.md`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/agents/bitcoin-followthrough.md`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/agents/event-gap-audit.md`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/agents/friend-packet-update.md`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/agents/independent-contradiction-audit.md`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/agents/thorchain-bridge.md`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/agents/public-tools-demix.md`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/agents/address-cluster-map.md`

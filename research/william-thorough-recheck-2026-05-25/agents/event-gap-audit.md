# Event Gap Audit

Created: 2026-05-25

## 1. Scope handled

Reconciled William's statement that there were two hacks, one in 2021 and one last October, against the local spreadsheet extract, the prior packet, the transaction inventory, and fresh public chain checks.

This note does not treat Stuart as William's representative. It is a practical evidence gap list for William to review and answer himself.

## 2. Evidence sources read

1. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/WARROOM-BRIEF.md`
2. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/summary-visible-rows.csv`
3. `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/manifest.md`
4. `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/01-Summary.csv`
5. `/Users/alphab/.mdx/research/transaction-inventory.csv`
6. `/Users/alphab/.mdx/research/william-crypto-case-dossier.md`
7. `/Users/alphab/.mdx/research/william-friend-packet/START-HERE-WILLIAM.md`
8. `/Users/alphab/.mdx/research/william-friend-packet/copy-paste-messages.md`
9. Fresh public chain responses saved under `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/event-gap-audit/`

## 3. Findings

### Finding A: the spreadsheet supports a July 2023 on chain event, not a 2021 event

Confidence: confirmed.

The visible Summary rows and public chain data show Ethereum and BSC transactions from July 21 to July 22, 2023 UTC. The spreadsheet file name references `Stolen Crypto July 2021`, but I found no 2021 on chain transaction in the spreadsheet extract, visible Summary rows, or prior packet files searched.

Confirmed chain time range from fresh public RPC checks:

1. Earliest visible EVM transaction: `0x662e469715056d9501da5184ec4a2a466b05b3fa656c73d0fb067598b88013c2`, Ethereum, `2023-07-21T13:47:23Z`.
2. Latest visible EVM transaction: `0xb5e309a09f479a87f71b1258380d8b8e62c84163364b3b06762927c476c4d655`, Ethereum, `2023-07-22T09:52:11Z`.
3. BSC row: `0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1`, BSC, `2023-07-21T18:36:20Z`.
4. Source only FixedFloat related row 38: `0xaa49f832a539cabee457ca3fc2e3e47e70ca7e364ba48161aae8c4e788d07b33`, Ethereum, `2023-07-21T14:34:11Z`.

The 2021 claim is therefore unresolved. The file name alone is not enough evidence of a 2021 hack.

### Finding B: the spreadsheet currently looks like one clustered July 2023 incident

Confidence: likely.

The upper Summary table shows multiple EVM source addresses losing funds over a tight July 21 to July 22, 2023 window. The listed summary totals are `$1,675,929.20`, `884.8222 ETH`, and `8.6 BNB`.

Accounts and destinations present in the July 2023 spreadsheet evidence:

1. Source accounts shown in visible Summary rows: `0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0`, `0x1c0b5b8d36587d0516839df7ebfb49ad8f3c543c`, `0x055e6b081f175db1170350ba4f23e3a8e0895492`, `0xd20a9ed00e37fdaef0a064bc32feb10845053f09`, `0xa30e54cb3593c6afca653621c4d3ee2105f015aa`, `0xdfb05c98320d126bcc74f6eb7960e99669dcd49a`, `0x9dc08da4cbf74f81cffb54cecbd8fdf6554e1d34`, `0x2656269bb878ca0c4250a0df4c15a9cfca0c21ac`, `0xfa5f6ed82ae1eac484b91ccde42fe7d64cb68d03`, and `0xf40c09c782c74e932b81473ae68b078f31a358f6`.
2. THORChain destination evidence: `0xD37BbE5744D730a1d98d8DC97c42F0Ca46aD7146`, with memo output to BTC address `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` in prior packet evidence.
3. FixedFloat related or common staging destinations in the source material: `0x6a7E9ed15eA2C1C7787E68F2CA2dF68379ed437e`, `0x4EC986035B635D09474fC390AcDF5c107DDa4c70`, `0xbdC4b2D85d9DCC42C3799b4569bd1D7D25D29C03`, `0x09066E7857D3a9a53c9142f8a7eFFcBc7989F1B5`, and `0xB7917eE3520C4AA56ADd5d55f6026EdeEBE99d02`.
4. BSC destination: `0x08178b429CA29853fa33014F635D12bD7f706297`.

This is enough to describe a July 2023 multi wallet incident. It is not enough to prove two separate hacks.

### Finding C: the prior packet has October 2023 Bitcoin movement, but not a second hack

Confidence: confirmed for dates. Confidence: low to medium for relation to the theft, matching the prior packet caveat.

Fresh Blockstream checks confirm the prior packet's October Bitcoin dates:

1. `1962037495cfc6f39cd0c525b78fdcffddb98de34babdcf785b12208152e9bb2`: `2023-10-06T11:12:03Z`.
2. `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187`: `2023-10-19T11:22:51Z`.
3. Live watchlist address `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`: chain funded total `649998534` sats, spent total `0` sats, mempool transaction count `0` in the fresh Blockstream address response.

The prior packet says the post Wasabi path is low confidence. These October 2023 movements are downstream investigative leads. I found no evidence that they are a separate wallet compromise in October 2023, October 2024, or October 2025.

Because the current date is 2026-05-25, William saying `last October` would normally mean October 2025. No October 2025 hack evidence is present in the files reviewed.

### Finding D: there are spreadsheet date conflicts that William should not paper over

Confidence: confirmed.

Important conflicts:

1. The file name says July 2021. Chain data says July 21 to July 22, 2023 for the visible loss rows.
2. Most upper Summary dates appear to be local times that match chain UTC after adding four hours.
3. Rows 7 and 8 appear swapped relative to their transaction hashes:
   1. Row 7 shows `2023/07/21 9:56:11` for `0x662e4697...`, but chain time is `2023-07-21T13:47:23Z`.
   2. Row 8 shows `2023/07/21 9:47:23` for `0x2ed79b06...`, but chain time is `2023-07-21T13:56:11Z`.
4. Lower copied row 42 says `21 Jul, 2023 19:15:47 UTC` for `0x931ebd96...`, but public chain data says `2023-07-21T14:09:11Z`.
5. Lower copied row 43 says `21 Jul, 2023 14:06 UTC` for `0x91a3d597...`, while chain data says `2023-07-21T14:06:23Z`. This looks like seconds were omitted.
6. Lower copied rows 44 and 45 match chain timestamps for `0x72d85593...` and `0xb5e309a0...`.

William should answer the incident date question from original evidence and explorer links, not from the spreadsheet title.

## 4. Contradictions or unresolved gaps

1. Unresolved: there is no source proof for a 2021 hack beyond the spreadsheet title. William needs to provide the 2021 transaction hashes, wallet addresses, screenshots, exchange messages, police reports, IC3 receipts, or a dated original file if a 2021 event happened.
2. Unresolved: there is no source proof for a `last October` hack. William needs to state the exact year and provide the specific transactions or records.
3. Unresolved: if William means October 2023, the reviewed evidence currently supports downstream Bitcoin movement from a low confidence post Wasabi branch, not a second hack.
4. Unresolved: if William means October 2025, no October 2025 evidence was present in the files reviewed.
5. Confirmed contradiction: the spreadsheet has internal date and row alignment issues, especially the July 2021 title and the row 7, row 8, and row 42 timestamp conflicts.

## 5. Repeatable commands and URLs

Raw evidence saved in this run:

1. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/event-gap-audit/chain-timestamp-summary.json`
2. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/event-gap-audit/ethereum-batch-transactions.json`
3. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/event-gap-audit/bsc-0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1-transaction.json`
4. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/event-gap-audit/bsc-0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1-block.json`
5. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/event-gap-audit/ethereum-0xaa49f832a539cabee457ca3fc2e3e47e70ca7e364ba48161aae8c4e788d07b33-transaction.json`
6. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/event-gap-audit/source-row-38-aa49f-summary.json`
7. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/event-gap-audit/bitcoin-tx-164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187.json`
8. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/event-gap-audit/bitcoin-tx-1962037495cfc6f39cd0c525b78fdcffddb98de34babdcf785b12208152e9bb2.json`
9. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/event-gap-audit/bitcoin-address-bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g.json`

Repeat one Ethereum timestamp check:

```bash
curl -fsS -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_getTransactionByHash","params":["0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204"]}' \
  https://ethereum.publicnode.com | python3 -m json.tool
```

Repeat the BSC timestamp check:

```bash
curl -fsS -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_getTransactionByHash","params":["0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1"]}' \
  https://bsc-dataseed.binance.org | python3 -m json.tool
```

Repeat the October Bitcoin checks:

```bash
curl -fsS 'https://blockstream.info/api/tx/164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187' | python3 -m json.tool
curl -fsS 'https://blockstream.info/api/tx/1962037495cfc6f39cd0c525b78fdcffddb98de34babdcf785b12208152e9bb2' | python3 -m json.tool
curl -fsS 'https://blockstream.info/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g' | python3 -m json.tool
```

## 6. Plain information request for William

William, please answer these before any official report is updated:

1. Did you have one incident or two separate incidents?
2. For each incident, what exact date, time, and time zone did you first see unauthorized activity?
3. When you say `last October`, which year do you mean: October 2023, October 2024, or October 2025?
4. If there was a 2021 hack, please send the transaction hashes, wallet addresses, screenshots, exchange notices, emails, chats, police reports, IC3 receipts, or any original dated export that proves the 2021 event. The current file name alone does not prove 2021.
5. If there was an October hack, please send the transaction hashes, wallet addresses, screenshots, exchange notices, emails, chats, report numbers, and the wallet or account names involved.
6. Were the July 21 to July 22, 2023 Ethereum and BSC transactions from wallets you controlled? If yes, list the wallet names or platforms. Do not send seed phrases, private keys, passwords, 2FA codes, wallet files, or remote access.
7. Were the October 2023 Bitcoin transactions something you personally saw as a new theft, or are they just later movement of funds from the July 2023 trail?
8. Please send any report numbers already filed with IC3, local police, FBI, Chainabuse, FixedFloat, Binance, an insurer, counsel, or analytics vendors.
9. Please send the original source files exactly as exported, plus screenshots of the wallet transaction history where possible. Do not edit originals.
10. If any account was compromised through an exchange, email, phone SIM, browser extension, hardware wallet, or cloud backup, please name the account type and approximate discovery time.

## 7. Recommended next action

Confidence: confirmed.

Do not describe this as two hacks yet. Describe the reviewed evidence as one confirmed July 2023 on chain loss cluster plus later low confidence Bitcoin tracing leads in October 2023. Ask William for source proof before adding any 2021 or October second incident to official reports.

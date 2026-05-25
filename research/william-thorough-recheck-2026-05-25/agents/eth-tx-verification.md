# Ethereum Transaction Verification

## Scope handled

[confirmed] This note covers Ethereum mainnet transactions present in `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/summary-visible-rows.csv` with `etherscan.io/tx/` URLs.

[confirmed] The check found 13 unique Ethereum mainnet transaction hashes. Four lower copied detail rows duplicate hashes already present in the upper summary rows.

[confirmed] The BscScan BNB row in source row 13 is outside this Ethereum mainnet scope and was excluded from the RPC output.

## Evidence sources read

[confirmed] Warroom brief: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/WARROOM-BRIEF.md`.

[confirmed] Input CSV: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/summary-visible-rows.csv`.

[confirmed] Public JSON RPC endpoints configured in the repeatable script:

1. `https://ethereum-rpc.publicnode.com`
2. `https://eth.llamarpc.com`
3. `https://rpc.flashbots.net`

[confirmed] Raw JSON RPC evidence was saved to `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/eth-tx-verification/raw-rpc-responses.jsonl`.

[confirmed] Repeatable script: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/eth-tx-verification/eth_tx_rpc_check.py`.

[confirmed] Machine readable manifest: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/eth-tx-verification/manifest.json`.

[confirmed] Output CSV: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/eth-tx-verification/eth-tx-verification.csv`.

## Findings

[confirmed] Every Ethereum mainnet transaction found in the visible summary rows has a mined block, a chain timestamp, from and to addresses, a native ETH value, and receipt status `success`.

[confirmed] The 13 Ethereum transactions are concentrated on July 21, 2023 UTC, with one transaction on July 22, 2023 UTC.

[confirmed] The chain facts are:

|tx_hash|chain_timestamp_utc|block|from|to|native_value_eth|receipt_status|
|---|---|---|---|---|---|---|
|0x0fa037ee4e0a99004dd98ca4827a9aaa9e45e56acd2b74334f09b16ad57050c3|2023-07-21 14:12:47 UTC|17742033|0xdfb05c98320d126bcc74f6eb7960e99669dcd49a|0xb7917ee3520c4aa56add5d55f6026edeebe99d02|1.872|success|
|0x2ed79b067f3afa2e636ae82f8c0c6cbd59d504aa7f25f146a4d22ef2186fc157|2023-07-21 13:56:11 UTC|17741950|0x1c0b5b8d36587d0516839df7ebfb49ad8f3c543c|0xeec35fd50b5e7344b3e1a7f4384b3cb9365e204a|104.3|success|
|0x3f58b9738767a04a8d4701052cbfa378f7cdf9d8a0cfac34b43b0d62f766a7e8|2023-07-21 14:11:59 UTC|17742029|0xfa5f6ed82ae1eac484b91ccde42fe7d64cb68d03|0xb7917ee3520c4aa56add5d55f6026edeebe99d02|5.02|success|
|0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204|2023-07-21 14:00:59 UTC|17741974|0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0|0xd37bbe5744d730a1d98d8dc97c42f0ca46ad7146|125.447151477364040918|success|
|0x662e469715056d9501da5184ec4a2a466b05b3fa656c73d0fb067598b88013c2|2023-07-21 13:47:23 UTC|17741906|0x1c0b5b8d36587d0516839df7ebfb49ad8f3c543c|0xeec35fd50b5e7344b3e1a7f4384b3cb9365e204a|623|success|
|0x72d855932534ca55ae820f5ed17de8ac729b1f05b093352b5bca19dcf868f26f|2023-07-21 18:55:47 UTC|17743441|0x2656269bb878ca0c4250a0df4c15a9cfca0c21ac|0x09066e7857d3a9a53c9142f8a7effcbc7989f1b5|3.89|success|
|0x85955c171d41591fb52b85f3e4135704f2afb4305ea9ceee1de1ba503703e7f1|2023-07-21 14:13:11 UTC|17742035|0xf40c09c782c74e932b81473ae68b078f31a358f6|0xb7917ee3520c4aa56add5d55f6026edeebe99d02|2.814|success|
|0x91a3d5976df4c7fb6d000a081855b4fc217d61d6e1b71f5c99205e7dc7c2f63f|2023-07-21 14:06:23 UTC|17742001|0x055e6b081f175db1170350ba4f23e3a8e0895492|0x4ec986035b635d09474fc390acdf5c107dda4c70|2.84|success|
|0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3|2023-07-21 14:09:11 UTC|17742015|0xa30e54cb3593c6afca653621c4d3ee2105f015aa|0xbdc4b2d85d9dcc42c3799b4569bd1d7d25d29c03|6.05|success|
|0xa2dc0cff0e555bf26d8044e39e92071e69587e62bfe4128f827b0eb9bdfc8681|2023-07-21 14:13:35 UTC|17742037|0x9dc08da4cbf74f81cffb54cecbd8fdf6554e1d34|0xb7917ee3520c4aa56add5d55f6026edeebe99d02|1.571|success|
|0xb5e309a09f479a87f71b1258380d8b8e62c84163364b3b06762927c476c4d655|2023-07-22 09:52:11 UTC|17747894|0x1c0b5b8d36587d0516839df7ebfb49ad8f3c543c|0x6a7e9ed15ea2c1c7787e68f2ca2df68379ed437e|0.82|success|
|0xc2235fdf93d6ed97f17ea248d40fbc6c910cb502a63c75f0bb131bbb0fb465a8|2023-07-21 14:12:35 UTC|17742032|0xd20a9ed00e37fdaef0a064bc32feb10845053f09|0xb7917ee3520c4aa56add5d55f6026edeebe99d02|6.451|success|
|0xd5a730adbe95e809d765372997260dd7057e959399e9b41d415816218de3686d|2023-07-21 14:13:59 UTC|17742039|0x2656269bb878ca0c4250a0df4c15a9cfca0c21ac|0xb7917ee3520c4aa56add5d55f6026edeebe99d02|0.747|success|

[confirmed] For 11 of 13 upper summary rows, the spreadsheet timestamp matches chain time if the spreadsheet value is treated as UTC minus four hours.

[confirmed] Source rows 7 and 8 have their upper summary times crossed. Transaction `0x662e469715056d9501da5184ec4a2a466b05b3fa656c73d0fb067598b88013c2` has chain time `2023-07-21 13:47:23 UTC`, while the sheet displays `2023/07/21 9:56:11`. Transaction `0x2ed79b067f3afa2e636ae82f8c0c6cbd59d504aa7f25f146a4d22ef2186fc157` has chain time `2023-07-21 13:56:11 UTC`, while the sheet displays `2023/07/21 9:47:23`.

[confirmed] Lower copied detail rows 43, 44, and 45 match the chain timestamp, with row 43 matching to the minute because the sheet omits seconds.

[confirmed] Lower copied detail row 42 conflicts with chain data. It links transaction `0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3` and displays `21 Jul, 2023 19:15:47 UTC`, while the chain timestamp is `2023-07-21 14:09:11 UTC`.

[confirmed] This Ethereum subset supports a July 2023 Ethereum event in the visible summary rows. This scope does not prove or disprove separate 2021, October, Bitcoin, or BNB events.

## Contradictions or unresolved gaps

[confirmed] The spreadsheet contains at least three timestamp problems in the visible Ethereum rows: crossed upper summary times for source rows 7 and 8, and an incorrect lower copied UTC timestamp for source row 42.

[confirmed] The output CSV should be treated as the canonical Ethereum transaction timestamp source for these 13 hashes because it uses block timestamps from public Ethereum JSON RPC.

[unresolved] The spreadsheet does not explain why source row 42 carries `19:15:47 UTC` for transaction `0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3`.

[unresolved] This Ethereum check does not cover the BNB row, Bitcoin rows, exchange records, wallet ownership proof, or the claimed 2021 and October events.

## Repeatable commands

Run the full Ethereum mainnet verification:

```bash
python3 /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/eth-tx-verification/eth_tx_rpc_check.py
```

Verify output shape:

```bash
python3 - <<'PY'
import csv, pathlib
base = pathlib.Path('/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25')
rows = list(csv.DictReader((base / 'data/eth-tx-verification/eth-tx-verification.csv').open()))
print('csv rows', len(rows))
print('statuses', sorted(set(r['receipt_status'] for r in rows)))
print('raw jsonl lines', sum(1 for _ in (base / 'data/eth-tx-verification/raw-rpc-responses.jsonl').open()))
print('all have required fields', all(all(r[c] for c in ['tx_hash','chain_timestamp_utc','block','from','to','native_value_eth','receipt_status']) for r in rows))
PY
```

Observed verification output:

```text
csv rows 13
statuses ['success']
raw jsonl lines 39
all have required fields True
```

## Recommended next action for William

[confirmed] Use the generated CSV as the Ethereum chain fact table for the 13 visible Ethereum transactions.

[likely] William should clarify the source and meaning of lower copied detail row 42 because its UTC timestamp conflicts with the chain.

[likely] William should keep the Ethereum July 2023 evidence separate from the BNB, Bitcoin, 2021, and October claims until those are independently verified from public chain data or exchange records he controls.

---
title: BSC row confirms 8.6 BNB transfer from same EVM address as Ethereum row
type: research
tags: [william, crypto, bsc, ethereum, crosschain]
summary: The BSC row is a confirmed July 21, 2023 native 8.6 BNB transfer from 0x9Dc08... to 0x08178..., and it likely belongs to the same July 2023 incident because the same EVM address also sent ETH that day.
status: active
source: quick-research
confidence: high
created: 2026-05-25
updated: 2026-05-25
---

# Summary

Confirmed: Summary row 13 is a real BNB Smart Chain transaction, not an Ethereum transaction and not a token transfer.

- Transaction: `0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1`
- Chain: BNB Smart Chain, chain ID `0x38`
- Block: `30163946`
- Chain timestamp: `2023-07-21T18:36:20Z`
- From: `0x9dc08da4cbf74f81cffb54cecbd8fdf6554e1d34`
- To: `0x08178b429ca29853fa33014f635d12bd7f706297`
- Value: `8.6 BNB`, exactly `8600000000000000000` wei
- Receipt status: `0x1`, successful
- Input: `0x`
- Logs: none

Likely: this belongs with the July 2023 event, not a separate 2021 or October event. The same EVM address also appears in Summary row 14 on Ethereum, where the chain confirms a same day outgoing `1.571 ETH` transfer at `2023-07-21T14:13:35Z`.

Unresolved: the BSC transaction does not prove bridging by itself. It proves the same address was used on BSC and Ethereum on July 21, 2023. A bridge or exchange path would require additional transactions before or after this transfer.

# Details

## Scope handled

Verified the BSC or BNB row in the visible Summary extract and checked the cross chain implication around address `0x9Dc08Da4cBF74F81CFfb54CECbD8fDf6554E1D34`.

## Evidence sources read

Sheet and extracted rows:

- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/WARROOM-BRIEF.md`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/summary-visible-rows.csv`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/gid-1211660592.csv`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/01-Summary.csv`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/10-0x9Dc08.csv`

Raw public chain responses saved here:

- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/bsc-crosschain/bsc-0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1-transaction.json`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/bsc-crosschain/bsc-0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1-receipt.json`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/bsc-crosschain/bsc-block-0x1cc43ea.json`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/bsc-crosschain/ethereum-0xa2dc0cff0e555bf26d8044e39e92071e69587e62bfe4128f827b0eb9bdfc8681-transaction.json`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/bsc-crosschain/ethereum-0xa2dc0cff0e555bf26d8044e39e92071e69587e62bfe4128f827b0eb9bdfc8681-receipt.json`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/bsc-crosschain/ethereum-block-0x10eb8d5.json`

Public URLs:

- `https://bscscan.com/tx/0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1`
- `https://etherscan.io/tx/0xa2dc0cff0e555bf26d8044e39e92071e69587e62bfe4128f827b0eb9bdfc8681`

## Findings

1. Confirmed: the source spreadsheet row exists in the Google Sheet export and the extracted workbook tabs.
   - `gid-1211660592.csv` row 14 shows the BSCScan transaction URL, sent to `0x08178b429CA29853fa33014F635D12bD7f706297`, amount `-8.6`, token `BNB`, and unit price `$243.80`.
   - `extracted-tabs/10-0x9Dc08.csv` repeats the same transaction under the address specific tab.

2. Confirmed: the chain timestamp is `2023-07-21T18:36:20Z`.
   - The sheet display says `2023/07/21 14:36:20`.
   - The four hour difference matches US Eastern daylight offset for July 2023. Treat the sheet display as local wall time without timezone, not UTC.

3. Confirmed: the value and parties match the row.
   - Chain from address: `0x9dc08da4cbf74f81cffb54cecbd8fdf6554e1d34`
   - Sheet address: `0x9Dc08Da4cBF74F81CFfb54CECbD8fDf6554E1D34`
   - Chain to address: `0x08178b429ca29853fa33014f635d12bd7f706297`
   - Sheet sent to: `0x08178b429CA29853fa33014F635D12bD7f706297`
   - Chain value: `8.6 BNB`
   - Sheet amount: `-8.6 BNB`

4. Confirmed: this was a plain native BNB transfer.
   - `input` is `0x`.
   - The receipt has zero logs.
   - Gas used is `0x5208`, which is `21000` gas.
   - This means the row is not a BEP20 token transfer and not a contract call.

5. Likely: the BSC row belongs to the same July 2023 incident cluster.
   - The same EVM address appears in Summary row 14 on Ethereum.
   - Ethereum row 14 is confirmed on chain at `2023-07-21T14:13:35Z` for `1.571 ETH` from `0x9dc08da4cbf74f81cffb54cecbd8fdf6554e1d34` to `0xb7917ee3520c4aa56add5d55f6026edeebe99d02`.
   - The BSC transfer happened `4h 22m 45s` after that Ethereum transfer.
   - Both are same day, same EVM source address, different chains.

6. Unresolved: no direct bridge path was proven.
   - Same address across Ethereum and BSC means the same private key controls that address on both chains.
   - This supports a multi chain compromise or multi chain sweep theory.
   - It does not show that the BNB was bridged from Ethereum, nor that the Ethereum recipient and BSC recipient are controlled by the same actor.

## Contradictions or unresolved gaps

- The visible sheet time for the BSC row is four hours behind chain UTC. This is consistent with a local timezone display, but the sheet should label its timezone explicitly.
- The destination `0x08178b429ca29853fa33014f635d12bd7f706297` appears in the provided sheet exports only as the destination for this BSC transaction. I did not find another visible row linking it to Ethereum or another transaction.
- Event attribution remains likely, not fully confirmed, until William confirms that `0x9Dc08Da4cBF74F81CFfb54CECbD8fDf6554E1D34` was one of his controlled accounts before the incident.

## Repeatable commands

```bash
ROOT=/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25
OUT="$ROOT/data/bsc-crosschain"
TX=0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1
RPC=https://bsc-dataseed.binance.org/
mkdir -p "$OUT"

curl -fsS -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_getTransactionByHash","params":["'"$TX"'"]}' \
  "$RPC" > "$OUT/bsc-transaction.raw.json"

BLOCK=$(python3 - <<'PY'
import json
obj=json.load(open('/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/bsc-crosschain/bsc-transaction.raw.json'))
print(obj['result']['blockNumber'])
PY
)

curl -fsS -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","id":2,"method":"eth_getTransactionReceipt","params":["'"$TX"'"]}' \
  "$RPC" > "$OUT/bsc-receipt.raw.json"

curl -fsS -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","id":3,"method":"eth_getBlockByNumber","params":["'"$BLOCK"'",false]}' \
  "$RPC" > "$OUT/bsc-block.raw.json"

python3 - <<'PY'
import json, datetime, decimal
out='/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/bsc-crosschain'
tx=json.load(open(f'{out}/bsc-transaction.raw.json'))['result']
receipt=json.load(open(f'{out}/bsc-receipt.raw.json'))['result']
block=json.load(open(f'{out}/bsc-block.raw.json'))['result']
print('timestamp_utc', datetime.datetime.fromtimestamp(int(block['timestamp'],16), datetime.timezone.utc).isoformat())
print('from', tx['from'])
print('to', tx['to'])
print('value_bnb', decimal.Decimal(int(tx['value'],16)) / decimal.Decimal(10) ** 18)
print('status', receipt['status'])
print('logs', len(receipt['logs']))
PY
```

## Recommended next action for William

William should label the sheet timezone and confirm whether `0x9Dc08Da4cBF74F81CFfb54CECbD8fDf6554E1D34` was his address. If yes, this row should be grouped into the July 21, 2023 multi chain incident packet as a BNB Smart Chain native transfer, with a note that no bridge path is proven from this transaction alone.

# Sources

- Local Google Sheet export: `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/gid-1211660592.csv`
- Local visible row extract: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/summary-visible-rows.csv`
- BSC JSON RPC endpoint used: `https://bsc-dataseed.binance.org/`
- Ethereum JSON RPC endpoint used: `https://ethereum.publicnode.com`
- BSCScan transaction page: `https://bscscan.com/tx/0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1`
- Etherscan transaction page: `https://etherscan.io/tx/0xa2dc0cff0e555bf26d8044e39e92071e69587e62bfe4128f827b0eb9bdfc8681`

# Open Questions

- Does William confirm `0x9Dc08Da4cBF74F81CFfb54CECbD8fDf6554E1D34` was his account on both Ethereum and BSC?
- Are there BSC transactions before this one that explain how the 8.6 BNB arrived at the source address?
- Does the destination `0x08178b429ca29853fa33014f635d12bd7f706297` connect to an exchange, bridge, mixer, or later consolidation address?

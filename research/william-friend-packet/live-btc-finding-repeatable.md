---
title: William Live BTC Finding, Repeatable Verification Packet
type: research
tags: [crypto-tracing, bitcoin, osint, william-case, evidence-packet]
summary: Public Bitcoin APIs still show 6.49998534 BTC unspent at the live watchlist address, with no mempool activity as of 2026-05-25T14:19Z.
status: active
confidence: medium
created: 2026-05-25
updated: 2026-05-25
---

## Executive Summary

The headline finding is still live: `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` holds `6.49998534 BTC` as of the recheck ending 2026-05-25T14:19:12Z. Blockstream, mempool.space, blockchain.info, and BlockCypher all show `0 BTC` spent, two unspent outputs, and no unconfirmed activity.

The caveat is just as important. This address is tied to William's prior trail through a low confidence Wasabi demix candidate. Public APIs can prove the address balance and spend status, but they cannot prove final ownership or validate the CoinJoin demix path. A paid analytics operator or law enforcement still needs to validate that part.

## Detailed Findings

### 1. Current status of the live BTC address

Address:

```text
bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
```

Current public status, rechecked 2026-05-25T14:18:55Z to 2026-05-25T14:19:12Z:

| Check | Result |
|---|---:|
| Funded total | `649,998,534` sats |
| Spent total | `0` sats |
| Current balance | `649,998,534` sats, or `6.49998534 BTC` |
| Confirmed transaction count | `2` |
| Current UTXO count | `2` |
| Mempool transaction count | `0` |
| Unconfirmed balance | `0` sats |

Blockstream and mempool.space returned the same address summary: funded `649,998,534` sats, spent `0` sats, two confirmed transactions, and zero mempool transactions. blockchain.info and BlockCypher also returned final balance `649,998,534` sats, total sent `0`, and no unconfirmed activity.

### 2. Exact unspent outputs

Two outputs are still unspent:

| UTXO | Value | Block height | Block time UTC | Status |
|---|---:|---:|---|---|
| `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187:0` | `649,998,240` sats | `812907` | 2023-10-19T11:22:51Z | Unspent on Blockstream and mempool.space |
| `4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5:0` | `294` sats | `940313` | 2026-03-11T22:02:44Z | Unspent on Blockstream and mempool.space |

The large output is the meaningful lead. The `294` sat output is March 2026 dust. Do not treat it as ownership attribution.

### 3. Mempool activity and spend status

There is no visible pending spend.

- Blockstream `/address/<address>/txs/mempool` returned an empty array.
- mempool.space `/address/<address>/txs/mempool` returned an empty array.
- Blockstream and mempool.space address summaries both show mempool `tx_count: 0`.
- BlockCypher shows `unconfirmed_n_tx: 0` and `unconfirmed_balance: 0`.
- Blockstream and mempool.space outspend APIs both show `spent: false` for the large UTXO and for the dust UTXO.

Plain answer William can use:

```text
As of 2026-05-25T14:19Z, the address bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g still has 6.49998534 BTC. Public APIs show two unspent outputs, no spent amount, and no pending mempool transaction.
```

### 4. How this address connects to the prior trail

The path is:

1. Source records identify Ethereum transfers that hit THORChain swap flow.
2. Liquify Midgard confirms two THORChain swap actions from the relevant inbound txids.
3. Both THORChain actions paid BTC to the Wasabi deposit address `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`.
4. Prior research identified `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` as a low confidence post Wasabi demix candidate.
5. Bitcoin tx `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187` paid `6.49998240 BTC` from that candidate branch to the live address `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` on 2023-10-19T11:22:51Z.
6. A separate 2026 dust transaction added `294` sats to the same live address. Treat that as noise.

Copyable caveat for any report:

```text
The current balance and unspent status are directly verifiable on public Bitcoin explorers. The link from the Wasabi coinjoin output to the current watchlist lead is a low confidence investigative lead. I am asking for preservation and lawful tracing support, not claiming final attribution.
```

### 5. Browser verification William can repeat

Open these pages in a browser:

1. Blockstream address page:
   - https://blockstream.info/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
2. mempool.space address page:
   - https://mempool.space/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
3. Large funding transaction:
   - https://blockstream.info/tx/164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187
   - https://mempool.space/tx/164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187
4. Dust transaction:
   - https://blockstream.info/tx/4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5
   - https://mempool.space/tx/4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5

What to look for:

- Confirm the address balance is `6.49998534 BTC`.
- Confirm there are two unspent outputs.
- Confirm the large output from `164f311d...` is not spent.
- Confirm there is no pending transaction for the address.
- Save a screenshot of both Blockstream and mempool.space if anything changes.

### 6. Curl verification William can repeat

Run these commands from Terminal. They do not require an account or API key.

```bash
ADDR='bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g'
FUNDING_TX='164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187'
DUST_TX='4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5'

curl -fsS "https://blockstream.info/api/address/$ADDR"
curl -fsS "https://mempool.space/api/address/$ADDR"

curl -fsS "https://blockstream.info/api/address/$ADDR/utxo"
curl -fsS "https://mempool.space/api/address/$ADDR/utxo"

curl -fsS "https://blockstream.info/api/address/$ADDR/txs/mempool"
curl -fsS "https://mempool.space/api/address/$ADDR/txs/mempool"

curl -fsS "https://blockstream.info/api/tx/$FUNDING_TX/outspends"
curl -fsS "https://mempool.space/api/tx/$FUNDING_TX/outspends"

curl -fsS "https://blockstream.info/api/tx/$DUST_TX/outspends"
curl -fsS "https://mempool.space/api/tx/$DUST_TX/outspends"
```

If `jq` is installed, this summarizes the address checks:

```bash
curl -fsS "https://blockstream.info/api/address/$ADDR" \
  | jq '{funded: .chain_stats.funded_txo_sum, spent: .chain_stats.spent_txo_sum, tx_count: .chain_stats.tx_count, mempool_tx_count: .mempool_stats.tx_count}'

curl -fsS "https://mempool.space/api/address/$ADDR" \
  | jq '{funded: .chain_stats.funded_txo_sum, spent: .chain_stats.spent_txo_sum, tx_count: .chain_stats.tx_count, mempool_tx_count: .mempool_stats.tx_count}'
```

Expected output should include:

```json
{
  "funded": 649998534,
  "spent": 0,
  "tx_count": 2,
  "mempool_tx_count": 0
}
```

A spend would change one or more of these values: `spent`, `mempool_tx_count`, the UTXO list, or the outspend response.

### 7. Raw evidence saved from this recheck

Raw responses were saved here:

```text
/Users/alphab/.mdx/research/data/william-live-recheck-2026-05-25/
```

Key files:

- `manifest-latest.json`
- `summary-latest.json`
- `20260525T141855Z-blockstream-live-address.json`
- `20260525T141856Z-blockstream-live-utxo.json`
- `20260525T141857Z-blockstream-live-mempool.json`
- `20260525T141859Z-blockstream-funding-outspends.json`
- `20260525T141905Z-mempool-live-address.json`
- `20260525T141906Z-mempool-live-utxo.json`
- `20260525T141906Z-mempool-live-mempool.json`
- `20260525T141907Z-mempool-funding-outspends.json`
- `20260525T141909Z-blockchain-info-live-address.json`
- `20260525T141909Z-blockcypher-live-balance.json`
- `20260525T141910Z-liquify-midgard-thorchain-actions.json`
- `20260525T141911Z-liquify-midgard-thorchain-actions.json`

## Sources Consulted

### Existing case files

- `/Users/alphab/.mdx/research/william-live-validation-2026-05-25.md`
- `/Users/alphab/.mdx/research/transaction-inventory.csv`
- `/Users/alphab/.mdx/research/william-crypto-case-dossier.md`

### Live BTC status APIs

- https://blockstream.info/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
- https://mempool.space/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
- https://blockstream.info/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g/utxo
- https://mempool.space/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g/utxo
- https://blockstream.info/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g/txs/mempool
- https://mempool.space/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g/txs/mempool
- https://blockchain.info/rawaddr/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g?limit=0
- https://api.blockcypher.com/v1/btc/main/addrs/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g/balance

### Transaction and outspend APIs

- https://blockstream.info/api/tx/164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187
- https://mempool.space/api/tx/164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187
- https://blockstream.info/api/tx/164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187/outspends
- https://mempool.space/api/tx/164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187/outspends
- https://blockstream.info/api/tx/4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5
- https://mempool.space/api/tx/4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5
- https://blockstream.info/api/tx/4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5/outspends
- https://mempool.space/api/tx/4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5/outspends

### THORChain trail check

- https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204
- https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C

## Source Quality Assessment

Confidence is high for current balance, UTXO status, and lack of mempool activity. Two primary Bitcoin APIs, Blockstream and mempool.space, agree at both the address level and outspend level. blockchain.info and BlockCypher independently agree on final balance and no unconfirmed activity.

Confidence is lower for the path through Wasabi. Public explorers prove transactions, balances, and spends. They do not validate a probabilistic CoinJoin demix. Treat the Wasabi to demix candidate segment as low confidence until a paid analytics tool or law enforcement validates it.

The THORChain portion is stronger than the Wasabi portion because Liquify Midgard returns action records for the two inbound txids and shows the BTC output address. This confirms the swap output to the Wasabi deposit address, not ownership after the coinjoin.

## Open Questions

1. Can a paid analytics operator validate or reject `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` as a post Wasabi candidate?
2. If the live BTC moves, does the first hop go to an exchange, mixer, bridge, or fresh self custody address?
3. Can law enforcement or a paid tool label the live address or its spending branch when it moves?
4. Should William set automated alerts through both a free service and a self hosted watcher?

## Actionable Takeaways

1. Keep `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` on active watch.
2. Track the large UTXO first: `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187:0`.
3. Treat the `294` sat UTXO as dust noise.
4. Do not contact, dust, or otherwise interact with the address.
5. If the address moves, immediately save both Blockstream and mempool.space transaction JSON, the mempool page, screenshots, and the first output set.
6. If any output appears to touch a custodial service, William should update IC3 and contact the active law enforcement contact with the raw evidence and screenshots.
7. Keep all outside reporting conservative: live balance is public fact, the Wasabi demix branch is an investigative lead.

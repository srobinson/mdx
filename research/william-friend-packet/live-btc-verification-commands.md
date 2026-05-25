# Live BTC Verification Commands

Stuart prepared this for William to review and run without creating accounts, sharing wallet information, signing anything, or sending funds.

## What this checks

The live BTC lead is:

```text
bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
```

Prior checks on May 25, 2026 found `649,998,534` sats, equal to `6.49998534 BTC`, with two unspent outputs and no mempool transactions. The script below repeats that check from public Bitcoin APIs and saves the raw JSON evidence.

## Run the full check

```bash
/Users/alphab/.mdx/research/william-friend-packet/live-btc-check.sh
```

What this command does:

1. Calls Blockstream address stats for the live BTC address.
2. Calls Blockstream UTXO stats for the same address.
3. Calls Blockstream mempool transactions for the same address.
4. Calls mempool.space address stats for the same address.
5. Calls mempool.space UTXO stats for the same address.
6. Calls mempool.space mempool transactions for the same address.
7. Saves every raw JSON response into:

```text
/Users/alphab/.mdx/research/data/william-live-recheck-2026-05-25/
```

8. Prints a plain summary with funded sats, spent sats, computed balance, UTXO count, and mempool transaction count.
9. Compares Blockstream against mempool.space and exits with a failure if the saved responses disagree on the key totals.

## Individual public API commands

These are the exact read only network checks used by the script.

Set the address once:

```bash
addr="bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g"
case_dir="/Users/alphab/.mdx/research/data/william-live-recheck-2026-05-25"
mkdir -p "$case_dir"
```

This stores the address and creates the evidence folder.

Check Blockstream address stats:

```bash
curl -fsS "https://blockstream.info/api/address/$addr" \
  > "$case_dir/blockstream-address-$addr.json"
```

This captures funded totals, spent totals, confirmed transaction count, and mempool summary from Blockstream.

Check Blockstream UTXOs:

```bash
curl -fsS "https://blockstream.info/api/address/$addr/utxo" \
  > "$case_dir/blockstream-utxo-$addr.json"
```

This captures the currently unspent outputs for the address according to Blockstream.

Check Blockstream mempool transactions:

```bash
curl -fsS "https://blockstream.info/api/address/$addr/txs/mempool" \
  > "$case_dir/blockstream-mempool-$addr.json"
```

This captures pending transactions touching the address according to Blockstream. An empty array means Blockstream sees no pending transaction for this address.

Check mempool.space address stats:

```bash
curl -fsS "https://mempool.space/api/address/$addr" \
  > "$case_dir/mempool-space-address-$addr.json"
```

This captures the same address level totals from mempool.space as an independent public source.

Check mempool.space UTXOs:

```bash
curl -fsS "https://mempool.space/api/address/$addr/utxo" \
  > "$case_dir/mempool-space-utxo-$addr.json"
```

This captures the currently unspent outputs for the address according to mempool.space.

Check mempool.space mempool transactions:

```bash
curl -fsS "https://mempool.space/api/address/$addr/txs/mempool" \
  > "$case_dir/mempool-space-mempool-$addr.json"
```

This captures pending transactions touching the address according to mempool.space. An empty array means mempool.space sees no pending transaction for this address.

## Browser URLs William can click

Address pages:

1. https://blockstream.info/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
2. https://mempool.space/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g

Raw public API pages:

1. https://blockstream.info/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
2. https://blockstream.info/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g/utxo
3. https://blockstream.info/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g/txs/mempool
4. https://mempool.space/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
5. https://mempool.space/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g/utxo
6. https://mempool.space/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g/txs/mempool

## How to read the output

`funded sats` is how many sats have been sent to the address.

`spent sats` is how many sats have been spent out of the address.

`computed balance` is funded sats minus spent sats, including any mempool delta reported by the address API.

`UTXO count` is how many unspent outputs remain at the address.

`mempool tx count` is how many pending transactions the provider currently sees for the address.

`Cross check: PASS` means Blockstream and mempool.space agreed on the key totals at the time of the run.

`Cross check: FAIL` means the raw JSON was saved, but the providers disagreed or a response shape was unexpected. Treat that as a reason to rerun and manually inspect the browser URLs.

`URGENT: mempool activity detected` means one provider saw a pending transaction for the live BTC address. Preserve the saved JSON files immediately.

## Safety notes

1. The script uses public HTTPS GET requests only.
2. The script does not use API keys.
3. The script does not submit data, create accounts, connect to wallets, sign transactions, or move funds.
4. Do not paste seed phrases, private keys, exchange passwords, or two factor codes into any site while checking this address.

## Verified run on May 25, 2026

The script was syntax checked and run successfully at `20260525T142251Z`.

Result:

```text
Blockstream funded sats: 649998534
Blockstream spent sats: 0
Blockstream computed balance: 649998534 sats, 6.49998534 BTC
Blockstream UTXO count: 2
Blockstream mempool tx count: 0
mempool.space funded sats: 649998534
mempool.space spent sats: 0
mempool.space computed balance: 649998534 sats, 6.49998534 BTC
mempool.space UTXO count: 2
mempool.space mempool tx count: 0
Mempool status: no pending transactions found by either provider
Cross check: PASS
```

Evidence files from that run use the `20260525T142251Z` filename prefix in:

```text
/Users/alphab/.mdx/research/data/william-live-recheck-2026-05-25/
```

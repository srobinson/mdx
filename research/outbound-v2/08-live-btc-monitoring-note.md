# Live BTC Monitoring Note

This is a draft for you to review.

This is the current time sensitive lead:

`bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`

## Status From The 2026-05-25 Recheck

- Balance: `6.49998534 BTC`
- Spent: `0 BTC`
- Mempool activity seen in the recheck: none
- Main funding transaction: `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187`
- Main funding time: `2023-10-19T11:22:51Z`
- Main funding output: `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187:0`
- Dust output: `4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5:0`

## Confidence Boundary

This address is connected to a low confidence post Wasabi candidate:

`bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`

Public data does not prove the Wasabi demix path. The address is still important because it holds unsold BTC and could create a service exposure if it moves to an exchange or hosted service.

## Manual Check Links

- Blockstream address page: https://blockstream.info/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
- Mempool address page: https://mempool.space/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
- Main funding transaction: https://blockstream.info/tx/164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187

## What To Do If It Moves

1. Save the new transaction hash immediately.
2. Save screenshots from Blockstream and Mempool showing the spend.
3. Save the raw transaction JSON if possible:
   - `https://blockstream.info/api/tx/[new_txid]`
   - `https://mempool.space/api/tx/[new_txid]`
4. Update the IC3 complaint with the new transaction hash.
5. Send the update to the local police contact and FBI field office contact.
6. If the outputs go to a labeled exchange or service, send the exact transaction hash, output address, amount, and timestamp to that service support route and ask for preservation guidance.

## Watch Criteria

The important event is a spend from:

`164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187:0`

The dust output is likely noise. Preserve it in the evidence file, but do not treat it as useful attribution.


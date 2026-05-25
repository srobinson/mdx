# Public Demix Research Plan

Date: 2026-05-25

## Decision

Do public research first. Do not make paid analytics the default next step.

The current post Wasabi candidate is:

```text
bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl
```

Prior work labels it low confidence. The correct next move is to run a repeatable public demix audit that explains why this address is or is not stronger than the rest of the candidate set. A paid vendor becomes useful only if public work reaches a hard confidence ceiling and William wants a law enforcement ready outside exhibit.

## What Public Research Can Do

1. Reconstruct the six Wasabi coinjoin entry transactions from the known deposit address.
2. Enumerate downstream coinjoin rounds and exit transactions.
3. Build a candidate set of post mix withdrawals by amount, timing, consolidation behavior, and later service exposure.
4. Score `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` against alternative candidates.
5. Verify whether the live BTC lead at `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` is downstream of the candidate.
6. Document every heuristic so William, law enforcement, or an analyst can repeat the work.
7. Monitor the live BTC lead for movement.

## What Public Research Cannot Reliably Do

Public chain data alone usually cannot prove a unique input to output mapping through a well executed Wasabi CoinJoin trail. Wasabi and WabiSabi are designed to break that link. Public research can raise or lower confidence, but a single definitive attribution usually needs one of:

- post mix address reuse,
- consolidation with known non mixed coins,
- deposit to a labeled service cluster,
- timing or amount behavior strong enough to exclude most alternatives,
- exchange or service records,
- wallet logs or endpoint evidence,
- a paid vendor dataset with historical entity attribution,
- law enforcement process.

## Public Tool Stack

Use these before paying anyone:

1. Blockstream Esplora API for address, tx, UTXO, and mempool data.
2. mempool.space API as a second public source.
3. DuckDB for local candidate scoring tables.
4. GraphSense or GraphSense API for open source forensics and tags where accessible.
5. WalletExplorer and public tag packs as weak labels only, never final proof.
6. OXT style graph methods if available, especially graphing CoinJoin paths and candidate exits.
7. BlockSci research methods if we need deeper CoinJoin detection and subset analysis.
8. Manual browser checks for explorer links William can repeat.

## Candidate Scoring Dimensions

Score each post mix candidate on:

- proximity to the six initial coinjoins,
- total amount relative to 40.70902128 BTC,
- exit timing after July 21 to 23, 2023,
- number of hops from initial coinjoins,
- whether funds reconsolidate,
- whether funds hit known services,
- whether later behavior resembles the depositor side,
- whether there are address reuse or common input ownership leaks,
- whether a live UTXO remains,
- whether alternative candidates have equal or better explanations.

## Vendor Use Threshold

Only ask paid analytics vendors after the public audit produces a concise question set:

1. Validate or reject the candidate `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`.
2. Validate or reject linkage to the live BTC address `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`.
3. Identify any known exchange or VASP exposure after the candidate.
4. State confidence and competing alternatives.
5. Provide a law enforcement ready exhibit if they can.

Do not pay for a vague "trace my stolen crypto" report.

## Plain Answer For William

We can research this ourselves first. The mixer does not make the trail magically impossible, but it does put a ceiling on what public data can prove. The practical question is whether the suspect made mistakes after mixing: consolidating funds, reusing addresses, hitting a service, or leaving a live UTXO. The unsold BTC address is worth focusing on because it is live and repeatably verifiable. The weak point is the Wasabi demix link into that path. That is what the public audit should test.

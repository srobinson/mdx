---
title: William Crypto Address Attribution Round 2
type: research
tags: [crypto-theft, bitcoin, wasabi, address-attribution, osint, binance, dusting]
summary: Public OSINT points the 17Stn service branch toward a probable Binance cluster, while the live 6.49998534 BTC address remains unlabeled and the 2026 dust is likely forensic noise.
status: active
confidence: medium
created: 2026-05-25
updated: 2026-05-25
related:
  - stolen-crypto-case-seed-2026-05-25
  - william-crypto-round1-synthesis
  - william-crypto-tools-and-leads-round1
---

# Executive Summary

Round 2 found one material public attribution lead: the high volume address `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` sits in WalletExplorer cluster `0000001bce8b8aa0`, and independent public label sources identify other addresses in that same cluster as Binance. Treat this as probable Binance attribution, not an official Binance confirmation.

The live watchlist address `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` remains unlabeled in public sources and still holds `6.49998534 BTC`. The March 11, 2026 dust came from a high volume micro dust dispatcher cluster, WalletExplorer `703a37cbb4f61eae`, with no reliable service attribution.

# Detailed Findings

## 1. Attribution matrix

| Target | Public label found | Evidence | Confidence |
|---|---|---|---|
| `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` | Probable Binance cluster | WalletExplorer places it in `0000001bce8b8aa0`; Coingrab labels `1LiZt9zi1y55yFCZTJ4yXR8P1iHWngvHBF` in that same WalletExplorer cluster as Binance; a 2025 legal filing labels `1ACH93S7ZFBMXPDfUyoNqMpu514oBvfEoZ`, also in the same WalletExplorer cluster, as Binance. | Medium high for Binance cluster, high for cluster membership |
| WalletExplorer cluster `0000001bce8b8aa0` | Probable Binance | Same as above. WalletExplorer itself does not name the cluster. | Medium high |
| `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` | None | WalletExplorer cluster `44582d2a68baaaee`; Blockstream and mempool.space show `6.49998534 BTC` unspent; BitcoinWhosWho has no scam report; exact web, Reddit, X, HN, and GitHub searches found no public label. | High for no public label found, high for chain state |
| WalletExplorer cluster `44582d2a68baaaee` | None | Two inbound transactions only: `164f311d...` from the demix candidate and `4fadadf...` dust from `703a37cbb4f61eae`. | High |
| `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` | None | WalletExplorer cluster `e2410ffea713c632`; BitcoinWhosWho has no scam report; exact web, Reddit, X, HN, and GitHub searches found no label. | High for no public label found |
| Dust source `bc1q7x6kj7lg9ls2g6s3wm644s5tuqkkg89dp5t532` | Unlabeled high volume dust dispatcher | WalletExplorer cluster `703a37cbb4f61eae`; 18,449 transactions; repetitive 330 sat and 294 sat outputs. | Medium |
| Dust intermediate `bc1pfe5nker9kukv02cgec70f9n4shh6c4kj83jrmpkdjuteelz2ya7qcwqdtq` | Unlabeled micro UTXO staging address | WalletExplorer cluster `f3e4b1ec5911d1c5`; 3,614 transactions; used for repeated 471 sat to 330 sat hops. | Medium |

## 2. The service like branch now points to probable Binance

### Facts

The branch transaction of interest is:

```text
29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287
```

Public chain data shows:

```text
2024-06-22 15:44:45 UTC
Input:  bc1qjx7l6l4kq5gzv8r38lrvt9hu68x9ted3y54dv4, 0.10000000 BTC
Output: 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva, 0.09998037 BTC
```

`17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` chain state, cross checked via mempool.space and Blockstream APIs on May 25, 2026:

```text
Funded UTXOs: 133,570
Funded sum:   9,933.53285374 BTC
Spent UTXOs:  133,570
Spent sum:    9,933.53285374 BTC
Balance:      0 BTC
```

WalletExplorer places that address in cluster `0000001bce8b8aa0` with `148,959` address transactions for the single address. The broader cluster is far larger: the WalletExplorer wallet page for `0000001bce8b8aa0` showed `24,495,644` total transactions and a cluster balance of `461.84973512 BTC` at block `950854`.

WalletExplorer API checks on May 25, 2026 put the following addresses in the same cluster:

```text
17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva  -> 0000001bce8b8aa0
1LiZt9zi1y55yFCZTJ4yXR8P1iHWngvHBF  -> 0000001bce8b8aa0
1ACH93S7ZFBMXPDfUyoNqMpu514oBvfEoZ  -> 0000001bce8b8aa0
1Kk6f6L6L7j2CeFNWMCDvhDkspBvVkwrs3  -> 0000001bce8b8aa0
14R8NuJvWc5gFPTYh7HpuNvQUPEfDk9urf  -> 0000001bce8b8aa0
bc1qm3epuf4a7ryd4qtdp05nmfswvhx97y9uqkqc79 -> 0000001bce8b8aa0
```

Two independent public sources label other addresses in that same cluster as Binance:

1. Coingrab labels `1LiZt9zi1y55yFCZTJ4yXR8P1iHWngvHBF` as Binance in BTC transfer rows dated December 2, 2025. URL: `https://www.coingrab.net/tx2/?cur=&pp=209&ww=2025-12-07`.
2. A 2025 legal filing hosted at `cryptolegalclaim.com` labels multiple transfers into `1ACH93S7ZFBMXPDfUyoNqMpu514oBvfEoZ` as `Binance (1ACH93)`. URL: `https://www.cryptolegalclaim.com/docs/Lawsuit-Rispba-Cause-No-5-CV-0357.pdf`, page 56 in the extracted text.

BitcoinWhosWho has one report for `17Stn...`, marked sextortion and dated October 17, 2024. That is weak evidence. On a 133,570 funded UTXO address inside a huge cluster, a single scam report is more consistent with a service deposit address that received illicit funds than with a standalone scammer wallet.

### Inference

`17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` is probably a Binance controlled deposit or hot wallet address, because it clusters with several addresses that public label feeds and a legal filing call Binance.

This is not official confirmation. WalletExplorer cluster membership is a heuristic and can over cluster in some CoinJoin contexts. Still, the Binance inference is materially stronger than the Round 1 conclusion of simply service like and unlabeled.

### Operational value

If the low confidence demix branch is accepted by law enforcement or a paid analytics firm, transaction `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287` becomes a concrete exchange preservation lead. The request should ask Binance to preserve account, KYC, login IP, device, deposit address assignment, and internal transfer records for the `0.09998037 BTC` received by `17Stn...` on June 22, 2024.

## 3. The live address remains unlabeled and unspent

The live watchlist address is:

```text
bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
```

Verified state on May 25, 2026:

```text
WalletExplorer wallet_id: 44582d2a68baaaee
Mempool and Blockstream funded sum: 6.49998534 BTC
Mempool and Blockstream spent sum:  0 BTC
Balance:                           6.49998534 BTC
Mempool pending transactions:       0
```

Its two inbound transactions are:

```text
164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187
2023-10-19 11:22:51 UTC
Input:  bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl, 6.50000000 BTC
Output: bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g, 6.49998240 BTC

4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5
2026-03-11 22:02:44 UTC
Input:  bc1q7x6kj7lg9ls2g6s3wm644s5tuqkkg89dp5t532, 0.00000330 BTC
Output: bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g, 0.00000294 BTC
```

No public source found an entity label for the live address or WalletExplorer cluster `44582d2a68baaaee`. BitcoinWhosWho says Scam Alert: None for the address. Chainabuse address pages are client rendered and did not expose report data to curl. Arkham was blocked by Cloudflare managed challenge. GraphSense and Iknaio API calls returned 401 Unauthorized without a key.

## 4. Dust source: high volume dust dispatcher, not attribution

The March 11, 2026 dust transaction was:

```text
4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5
```

Specific funding path visible in public APIs:

```text
94d27a552afda88fb686f8bcfcc339220e3b464bfff43750a17ab61a24a2d750
2026-03-09 20:30:10 UTC
bc1q7x6... -> 100 outputs of 0.00000471 BTC to bc1pfe5..., plus change back to bc1q7x6...

acf2ceabe3c6192adec94eec7bd105b8e401898f690ec896099c251d3995e83f
2026-03-10 17:42:09 UTC
bc1q7x6... -> 100 outputs of 0.00000471 BTC to bc1pfe5..., plus change back to bc1q7x6...

3de3560c6cec7643d982274194eb093751b356ae0db59f05be874f4ef21664c5
2026-03-10 18:34:34 UTC
bc1pfe5... -> bc1q7x6..., 0.00000330 BTC

4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5
2026-03-11 22:02:44 UTC
bc1q7x6... -> live address, 0.00000294 BTC
```

WalletExplorer clusters:

```text
bc1q7x6kj7lg9ls2g6s3wm644s5tuqkkg89dp5t532 -> 703a37cbb4f61eae
bc1pfe5nker9kukv02cgec70f9n4shh6c4kj83jrmpkdjuteelz2ya7qcwqdtq -> f3e4b1ec5911d1c5
```

`bc1q7x6...` has `18,449` transactions in both WalletExplorer and public chain APIs. Blockstream shows `21.72261460 BTC` funded and `21.72137487 BTC` spent, with `0.00123973 BTC` left. WalletExplorer rows show repeated `0.00000330 BTC` outgoing transfers and some recipients labelled `CoinJoinMess`.

Inference: this is an automated micro dust dispatcher. It may be a tracker, spammer, ordinals related campaign, or clustering probe. It should not be used as evidence that the live address owner touched a known service. It only proves that someone else noticed or swept the address into a dust campaign in March 2026.

## 5. Effect on the low confidence demix candidate

Public evidence does not independently prove that `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` belongs to the original thief. The candidate remains low confidence unless a paid tool can reproduce the demix path from the July 2023 Wasabi deposits.

Public evidence does strengthen the downstream lead quality if the candidate is accepted:

- The live `6.49998534 BTC` address is directly funded from `bc1q9vl...` by one input and one output in `164f311d...`.
- The service branch sends `0.09998037 BTC` to `17Stn...`, now probably a Binance cluster.
- The candidate behaves like a post mix collector: it received multiple BTC chunks from August 17 to October 15, 2023, then spent `35.97041890 BTC` on October 6, 2023 and `6.49998240 BTC` on October 19, 2023.

Public evidence also leaves major caveats:

- The source transactions funding `bc1q9vl...` are mostly multi input or one output consolidations, not direct public labels tying them to the July 21 to 23, 2023 Wasabi coinjoins.
- No public label was found for the candidate, the live address, or WalletExplorer cluster `e2410ffea713c632`.
- The dust into the live address is unrelated noise unless a paid tool identifies the duster as a known investigator or counterparty.

Bottom line: Round 2 increases confidence that one downstream branch reached Binance, but it does not increase confidence in the original Wasabi demix by itself.

## 6. Exact next query set for a paid tool operator

Give the paid operator the case context, then ask for these exact checks.

### A. Wasabi demix validation

```text
Input set:
- Wasabi deposit: bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s
- THORChain to BTC timeframe: 2023-07-21 through 2023-07-23 UTC
- Candidate: bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl
- Candidate WalletExplorer cluster: e2410ffea713c632

Questions:
1. Does your tool reproduce bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl as a post mix candidate from the seven deposits to bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s?
2. What confidence score, candidate set size, and competing candidates do you return?
3. Which heuristic drives the match: amount linkability, timing, pre mix clustering, post mix clustering, common input ownership, or off chain label?
4. Are any candidate funding transactions direct Wasabi coinjoin withdrawals or later consolidations from multiple withdrawals?
```

### B. Live UTXO preservation and spend alert

```text
Address:
- bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g

Transactions:
- 164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187
- 4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5

Questions:
1. Confirm current UTXO set and whether any mempool spend exists.
2. Set alert for any spend from this address.
3. On spend, classify the first hop immediately: CEX, bridge, mixer, wallet, peel chain, or unknown.
4. If the first hop hits a service, provide legal process endpoint and preservation language.
```

### C. Binance branch validation

```text
Branch path:
- bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl
- 1962037495cfc6f39cd0c525b78fdcffddb98de34babdcf785b12208152e9bb2
- bc1qtvj76tqmhazw8dl5yx9ep9hs32xxlcletrf6p8
- 4d23a22853686456ae2d8345d0402182ac301bf5aa4010a1f04df90581c2bd8f
- bc1qjx7l6l4kq5gzv8r38lrvt9hu68x9ted3y54dv4
- 29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287
- 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva
- WalletExplorer cluster 0000001bce8b8aa0

Questions:
1. Does your tool label 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva or cluster 0000001bce8b8aa0 as Binance?
2. Is 17Stn a deposit address, hot wallet, consolidation address, or false cluster member?
3. Can the 0.09998037 BTC received on 2024-06-22 15:44:45 UTC be mapped to a Binance user account or deposit memo by legal process?
4. Provide the exact Binance legal entity and law enforcement portal for preservation.
5. Return all same account inflows and outflows within 72 hours of this deposit if visible.
```

### D. Dust campaign classification

```text
Dust tx:
- 4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5

Dust source and intermediate:
- bc1q7x6kj7lg9ls2g6s3wm644s5tuqkkg89dp5t532
- WalletExplorer cluster 703a37cbb4f61eae
- bc1pfe5nker9kukv02cgec70f9n4shh6c4kj83jrmpkdjuteelz2ya7qcwqdtq
- WalletExplorer cluster f3e4b1ec5911d1c5
- 94d27a552afda88fb686f8bcfcc339220e3b464bfff43750a17ab61a24a2d750
- acf2ceabe3c6192adec94eec7bd105b8e401898f690ec896099c251d3995e83f
- 3de3560c6cec7643d982274194eb093751b356ae0db59f05be874f4ef21664c5

Questions:
1. Is cluster 703a37cbb4f61eae a known dusting, tracing, spam, ordinals, or exchange wallet?
2. Which other high value stale UTXOs were dusted by the same campaign around March 10 to 11, 2026?
3. Does the dust source have any known relationship to Chainalysis, TRM, Elliptic, MistTrack, Arkham, law enforcement, or a public explorer?
4. If unlabeled, ignore it as attribution and mark as forensic noise.
```

### E. Label database checks

```text
Run exact address and cluster lookup in Arkham, MistTrack, Caudena, Chainalysis Reactor, TRM Forensics, Elliptic Investigator, and Crystal:
- 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva
- 0000001bce8b8aa0
- bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
- 44582d2a68baaaee
- bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl
- e2410ffea713c632
- bc1q7x6kj7lg9ls2g6s3wm644s5tuqkkg89dp5t532
- 703a37cbb4f61eae
- bc1pfe5nker9kukv02cgec70f9n4shh6c4kj83jrmpkdjuteelz2ya7qcwqdtq
- f3e4b1ec5911d1c5
```

# Sources Consulted

## Case inputs

- `/Users/alphab/.mdx/research/stolen-crypto-case-seed-2026-05-25.md`
- `/Users/alphab/.mdx/research/william-crypto-round1-synthesis.md`
- `/Users/alphab/.mdx/research/william-crypto-tools-and-leads-round1.md`

## Chain state and clustering

- WalletExplorer address API, queried May 25, 2026: `https://www.walletexplorer.com/api/1/address?address={address}&from=0&count=5&caller=william-round2`
- WalletExplorer wallet page: `https://www.walletexplorer.com/wallet/0000001bce8b8aa0`
- WalletExplorer wallet page: `https://www.walletexplorer.com/wallet/44582d2a68baaaee`
- WalletExplorer wallet page: `https://www.walletexplorer.com/wallet/e2410ffea713c632`
- WalletExplorer wallet page: `https://www.walletexplorer.com/wallet/703a37cbb4f61eae`
- WalletExplorer wallet page: `https://www.walletexplorer.com/wallet/f3e4b1ec5911d1c5`
- mempool.space API, queried May 25, 2026: `https://mempool.space/api/address/{address}` and `https://mempool.space/api/tx/{txid}`
- Blockstream API, queried May 25, 2026: `https://blockstream.info/api/address/{address}`
- Blockchair address page for `17Stn...`: `https://blockchair.com/bitcoin/address/17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva`

## Public labels and abuse reports

- Coingrab BTC transfer page: `https://www.coingrab.net/tx2/?cur=&pp=209&ww=2025-12-07`
- Legal filing with Binance labeled BTC rows: `https://www.cryptolegalclaim.com/docs/Lawsuit-Rispba-Cause-No-5-CV-0357.pdf`
- BitcoinWhosWho address page for `17Stn...`: `https://www.bitcoinwhoswho.com/address/17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva`
- BitcoinWhosWho address page for `bc1qyt...`: `https://www.bitcoinwhoswho.com/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`
- BitcoinWhosWho address page for `bc1q9vl...`: `https://www.bitcoinwhoswho.com/address/bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`
- Chainabuse address pages attempted: `https://www.chainabuse.com/address/{address}?chain=BTC`

## Gated or unavailable checks

- Arkham address pages attempted: `https://intel.arkm.com/explorer/address/bitcoin/{address}`. Requests hit Cloudflare managed challenge.
- GraphSense and Iknaio API attempted: `https://api.iknaio.com/btc/addresses/{address}?include_actors=true`. Requests returned 401 Unauthorized without an API key.
- Blockchair API attempted: `https://api.blockchair.com/bitcoin/dashboards/address/{address}?limit=0`. Requests returned temporary IP blacklist error code 430.

## Social and code search

- Exact address searches across general web, Reddit, X or Twitter, Hacker News, and GitHub for `17Stn...`, `bc1qyt...`, `bc1q9vl...`, `4fadadf...`, `703a37cbb4f61eae`, and `f3e4b1ec5911d1c5`. No useful label hits beyond the sources above.

# Source Quality Assessment

- Chain state facts are high confidence because mempool.space and Blockstream agreed on balances, UTXO counts, and transaction details.
- WalletExplorer cluster membership is useful but not definitive ownership proof. Its clustering can over merge in CoinJoin contexts. The Binance inference for `0000001bce8b8aa0` is stronger because two independent public label sources identify other addresses inside the same WalletExplorer cluster as Binance.
- Coingrab is a public label feed, not an official exchange source. Treat it as corroborating evidence only.
- The legal filing is a public document that labels `1ACH93...` as Binance, but the filing does not prove Binance itself confirmed the label. Treat it as corroborating evidence only.
- BitcoinWhosWho is low signal for high volume service addresses. A single sextortion report against `17Stn...` should not be treated as entity attribution.
- Arkham, GraphSense, Blockchair API labels, Chainabuse full report data, and paid analytics labels remain unverified in this round due access limits.

# Open Questions

1. Does Arkham, MistTrack, Caudena, Chainalysis, TRM, Elliptic, or Crystal directly label `17Stn...` or cluster `0000001bce8b8aa0` as Binance?
2. Can Binance confirm whether `17Stn...` was a user deposit address on June 22, 2024 and preserve account records for the `0.09998037 BTC` receipt?
3. Can a paid demix tool reproduce `bc1q9vl...` from the July 2023 Wasabi deposit set with a confidence score and alternative candidate set?
4. Who operates the `703a37cbb4f61eae` dust dispatcher, and did it target other known stolen fund addresses?
5. If the live `6.49998534 BTC` UTXO moves, will the first hop go to an exchange, another peel chain, a mixer, or a bridge?

# Actionable Takeaways

1. Escalate the `17Stn...` branch as a probable Binance preservation lead, with clear caveat that attribution is indirect from cluster evidence.
2. Keep the live `bc1qyt...` alert active. It remains the best current recovery lead because funds are unspent.
3. Do not treat the March 2026 dust as owner activity or service attribution. Mark it as forensic noise unless a paid tool identifies the duster.
4. Ask any paid analytics operator to reproduce the demix candidate before spending effort on downstream legal process.
5. If paid tools validate the demix, prioritize Binance preservation for tx `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287` and live UTXO monitoring for `bc1qyt...`.

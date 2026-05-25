---
title: William Stolen Crypto — Round 1 Tools and Leads
type: research
tags: [crypto-theft, bitcoin, wasabi, thorchain, osint, tracing-tools, watchlist, william-case]
summary: Round 1 sweep of tracing tools, address labels, Wasabi demixing state of the art, watchlist alert workflows, and actionable next steps for the July 2023 theft case.
status: active
confidence: medium
created: 2026-05-25
updated: 2026-05-25
---

# Executive Summary

The Bitcoin tracing landscape in May 2026 has consolidated around a small set of free or low-cost tools (MetaSleuth, Arkham, Breadcrumbs, WalletExplorer, mempool.space) plus paid analytics suites (Chainalysis, TRM Labs, Elliptic, MistTrack Premium). OXT shut down on April 25, 2024 alongside the Samourai Wallet indictment, so legacy literature pointing to OXT is no longer actionable. Wasabi 2.x coinjoins remain effectively undemixable at scale per peer-reviewed work; targeted reduction of anonymity sets is possible only via pre and post mixing clustering errors. The strongest immediate workstreams for William this week are: (1) file or update an IC3 complaint with the consolidated address list, (2) submit a Chainabuse report tied to the Wasabi deposit and the candidate downstream addresses, (3) set up a free watchlist on `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` so any future spend triggers an immediate alert.

# Detailed Findings

## 1. Tracing Tools Inventory Beyond Blockstream and Etherscan

Each tool below has been verified for current operational status as of May 25, 2026. Tools are grouped by access tier.

### Free or Freemium Public Tools

**MetaSleuth (BlockSec).** Browser based graph tracing across BTC, ETH, and many other chains, with built in exchange and mixer labels, monitoring up to 10 addresses with 10 notifications per day on the free tier. Useful workflow: paste any victim tx hash, expand outgoing edges, follow until funds land at a labeled CEX deposit address, then export the visual graph as evidence for law enforcement. URL: <https://metasleuth.io/>. Source: MetaSleuth product page and Coinmonks walkthrough, accessed May 25, 2026.

**Arkham Intel (intel.arkm.com).** Entity attribution layer over Bitcoin and EVM chains. As of 2026 Arkham claims more than 350,000 labeled entities and more than one billion labeled addresses. Free tier supports per address lookups; the Intel Exchange marketplace gates fresh attribution for 90 days then releases it free. Useful for cross referencing wallet clusters to known custodians. URL: <https://intel.arkm.com/>. Note that WebFetch returned 403 on direct lookups for the specific BTC addresses in this case, which is consistent with anti scraping rather than absence of labels; William should sign in and search manually. Source: DEX Tools, CoinMarketCap, and Arkham documentation, accessed May 25, 2026.

**WalletExplorer.com.** Bitcoin only, but uses common input ownership heuristic clustering and provides downloadable CSV per cluster as of July 2025. Address renaming and faster server were added in 2025. Use the JSON API to script lookups: `https://www.walletexplorer.com/api/1/address?address={addr}&from=0&count=100&caller=research`. The `wallet_id` field gives the cluster handle. Service labels exist only for older clusters, so the absence of a service label on the case addresses is informative but not conclusive. URLs: <https://www.walletexplorer.com/>, API docs at <https://www.walletexplorer.com/info>. Source: WalletExplorer changelog and JSON responses, accessed May 25, 2026.

**Chainabuse.** Public reporting and lookup platform run by TRM Labs. Anyone can submit a scam report with addresses, tx hashes, URLs, IP, and loss amount; reports can be public or private. Private reports are shared with law enforcement and exchange partners. URL: <https://www.chainabuse.com/>. Address pages live at `https://www.chainabuse.com/address/{addr}?chain=BTC`. The site is JavaScript heavy, so curl and WebFetch return no rendered data; browse manually. Source: Cointelegraph guide and chainabuse.com, accessed May 25, 2026.

**MistTrack Light (SlowMist AML).** Free community tracing platform plus the MistTrack Toolkit with free risk assessments per address and the USDT banned list. The SlowMist AML team also runs a free intake for victims of crypto theft; in Q2 2025 they handled 429 reports and helped 11 victims freeze or recover approximately $11.95 million. Submission and contact via <https://misttrack.io/> and the SlowMist AML page at <https://aml.slowmist.com/>. Source: MistTrack home page and SlowMist Medium quarterly reports, accessed May 25, 2026.

**Breadcrumbs (Merkle Science).** Graph visualization plus Pathfinder for automatic discovery of related addresses. Free tier exists but is limited in graph size and history; full investigation work needs a paid plan. URL: <https://www.breadcrumbs.app/>. Source: Breadcrumbs pricing page and 2026 Startup Stash listing, accessed May 25, 2026.

**mempool.space.** Free open source Bitcoin explorer with a public WebSocket API that supports `{"track-address": "<addr>"}` and `{"track-addresses": [...]}` subscription messages, emitting `address-transactions` events in mempool and `block-transactions` events on confirmation. This is the canonical primitive for free watchlist alerting. URL: <https://mempool.space/docs/api/websocket>. Source: mempool.space docs, accessed May 25, 2026.

**Blockchair.com.** Multi chain explorer with the strongest cross chain search and free CSV export. Useful for confirming Blockstream readings against a second source. URL: <https://blockchair.com/>.

**BitcoinWhosWho.** Free public reports database. Records community submitted scam tags; for example the volume hub address `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` has one sextortion report dated October 17, 2024. URL: <https://www.bitcoinwhoswho.com/>. Source: BitcoinWhosWho page, accessed May 25, 2026.

**GraphSense (TU Wien / Iknaio).** Open source crypto asset analytics platform with Spark backend. Iknaio runs a hosted SaaS for non technical users. Free instance: <https://hosted.graphsense.iknaio.at/>. Useful for entity clustering on Bitcoin and Ethereum with a Python API for batch analysis. Source: GraphSense docs and Iknaio site.

### Tools That Are Defunct or Closed

**OXT (oxt.me).** Shut down on April 25, 2024 alongside the US indictment of the Samourai Wallet founders. Servers were seized. Do not rely on OXT in any current workflow. Some research blog posts remain archived. Source: news.bitcoin.com article on the OXT closure dated April 25, 2024, accessed May 25, 2026.

**Samourai Wallet, Whirlpool.** Servers seized April 24, 2024 by US authorities. Founders Keonne Rodriguez and William Lonergan Hill charged with money laundering. Source: Bitcoin Magazine FreeSamourai coverage.

**CipherTrace as standalone.** Acquired by Mastercard in 2021 and folded into Mastercard's crypto risk products. The product no longer has an independent victim intake. Use TRM Labs or Chainalysis Reactor instead. Source: industry references confirmed during this sweep.

### Paid Tools and Their Practical Reach

**Chainalysis Reactor and Kryptos.** Industry standard for law enforcement, not directly available to victims. Useful indirectly: most US exchanges screen against Chainalysis tags, and major case work cited in court records relies on Reactor outputs. Source: Chainalysis product page.

**TRM Labs Forensics.** Used by law enforcement and most large exchanges. Operates Chainabuse as a public face. TRM has published several long form case studies on THORChain enabled laundering, which is directly relevant to this case. Source: <https://www.trmlabs.com/resources/blog/>.

**Elliptic Investigator.** Comparable to TRM in scope. Elliptic stated publicly that they can demix Wasabi only in some circumstances. Source: news.bitcoin.com 2022 article on demixing claims.

**Crystal Intelligence.** Bitfury spin out. Used in some EU investigations. Less common in US victim workflows.

**MistTrack Premium.** Paid version of MistTrack with a fuller investigation UI, watchlists, and direct exchange liaison. SlowMist's stolen funds intake is free, the dashboard is paid. Source: misttrack.io.

**AMLBot.** Compliance grade risk scoring as a service. Useful to obtain a quick risk score per address with attribution snippets. URL: <https://amlbot.com/>. Source: search results during this sweep.

**Cielo Finance.** Wallet feed and alerting service oriented to DeFi traders, not stolen funds investigations. Marginal relevance.

**ChainPatrol and ScamSniffer.** Aimed at preventing phishing rather than tracing post theft. Useful as forward looking defensive tools only.

### What Each Tool Adds Versus Blockstream and Etherscan

| Capability | Blockstream + Etherscan | Add via free tools | Add via paid tools |
|---|---|---|---|
| Cluster ownership grouping | partial via Etherscan name tags | WalletExplorer, Arkham labels, GraphSense | Chainalysis, TRM, Elliptic |
| Cross chain bridge tracing | manual | MetaSleuth graph, Arkham | TRM, Chainalysis |
| Exchange deposit attribution | sometimes via Etherscan tags | MistTrack, Chainabuse, Arkham | All paid |
| Mixer detection | manual heuristic | MetaSleuth mixer tags, Arkham | All paid |
| Live spend alerts | no | mempool.space WebSocket, Bitwatch, cryptocurrencyalerting.com free tier | Chainalysis Sentinel |
| Public abuse history | no | Chainabuse, BitcoinWhosWho, MistTrack risk score | All paid |

## 2. Labels for the Specific Addresses

WalletExplorer JSON API was queried directly on May 25, 2026 via `https://www.walletexplorer.com/api/1/address?address={addr}&from=0&count=10&caller=research`. Results below.

### bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s (Wasabi deposit)

- WalletExplorer wallet id: `6ba31fe6a6a703ec`
- Tx count: 13
- WalletExplorer service label: none
- Notes: matches the seed's Blockstream verification of 40.70902128 BTC funded and zero balance.

### bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl (low confidence demix candidate)

- WalletExplorer wallet id: `e2410ffea713c632`
- Tx count: 10
- WalletExplorer service label: none
- Notes: six inputs feed the spending tx `1962037495cfc6f39cd0c525b78fdcffddb98de34babdcf785b12208152e9bb2` on October 6, 2023, sending 35.97041890 BTC to `bc1qtvj76tqmhazw8dl5yx9ep9hs32xxlcletrf6p8`. Mempool.space tx vouts confirmed via API.

### bc1qtvj76tqmhazw8dl5yx9ep9hs32xxlcletrf6p8 (first hop after candidate)

- WalletExplorer wallet id: `5934c9888d7aa61c`
- Tx count: 2
- Spent 35.9704189 BTC on June 22, 2024 in tx `4d23a22853686456ae2d8345d0402182ac301bf5aa4010a1f04df90581c2bd8f`, splitting to:
  - `bc1qwgudmgsqwm2g0c76rsazmvj6fh704x9kmujt43` 35.87040480 BTC, spent again ~58 minutes later in tx `07183f4dbc9f9ad6015e829ff68dc21d49085dbb88168d723cdc21e1890f3a17`
  - `bc1qjx7l6l4kq5gzv8r38lrvt9hu68x9ted3y54dv4` 0.10000000 BTC, spent quickly in tx `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287`
- Notes: this is a peeling chain. The ~0.1 BTC peel followed by a near full forward of the remainder is a classic obfuscation pattern, though it also occurs in normal exchange consolidations.

### bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g (the live watchlist target)

- WalletExplorer wallet id: `44582d2a68baaaee`
- Tx count: 2 (both inbound, never spent)
- Balance: 6.49998534 BTC unspent. Confirmed against mempool.space.
- Two inbound transactions:
  1. October 19, 2023 at block 812907, 6.4999824 BTC, txid `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187`. Same tx where 6.5 BTC left `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`.
  2. March 11, 2026 at block 940313, 0.00000294 BTC dust, txid `4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5`. The dust is consistent with a dusting attack used by tracers to flag the address; this should be noted but treated as forensic noise, not an attribution signal.
- This is the most actionable BTC lead in the case because the funds are still on chain.

### 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva (service like high volume aggregator)

- WalletExplorer wallet id: `0000001bce8b8aa0`
- Tx count: 148,959 as of WalletExplorer block 950854
- WalletExplorer service label: none, although the wallet id prefix `0000001bce` indicates this is one of WalletExplorer's earliest tracked clusters, almost certainly a custodial service that predates 2017.
- BitcoinWhosWho: 1 sextortion report dated October 17, 2024. Inference: a single report against a 148k tx wallet is consistent with either a custodial exchange or a high volume gambling site that occasionally appears in scam payment chains, not with the address being a scammer's wallet itself.
- Inference rather than fact: this address looks like a deposit or hot wallet for a high volume service. The very low 0.09998037 BTC inbound from the case chain is consistent with a small forwarded service deposit. Arkham search may resolve the entity but the public lookup is gated behind sign in.

### Cluster summary table

| Address | WalletExplorer wallet id | Tx count | Current balance | Public label | Lead class |
|---|---|---|---|---|---|
| `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` | `6ba31fe6a6a703ec` | 13 | 0 | none | confirmed Wasabi deposit per case context |
| `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` | `e2410ffea713c632` | 10 | 0 | none | low confidence demix candidate |
| `bc1qtvj76tqmhazw8dl5yx9ep9hs32xxlcletrf6p8` | `5934c9888d7aa61c` | 2 | 0 | none | first peel hop, June 2024 |
| `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` | `44582d2a68baaaee` | 2 | 6.49998534 | none | live unspent target |
| `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` | `0000001bce8b8aa0` | 148959 | 0 | sextortion mention only | likely service deposit |

## 3. Wasabi Demixing — What Is and Is Not Possible Right Now

### Established Facts

**Wasabi 2.x is computationally hard to demix at the protocol level.** Per Wasabi developers and corroborated by the 2024 emergentmind summary, finding all sub transactions of a Wasabi 2.0 coinjoin is a combinatorial complexity explosion described as "probably impossible for decades to come." Source: Wasabi Wallet blog post on privacy guarantees of WW2, also coinjoins.org review.

**Wasabi 1.x and partial Wasabi 2.x linkability are achievable when users make mistakes.** The 2022 arXiv measurement study `2109.10229` by Wahrstätter et al. detected 30,251 Wasabi and 223,597 Samourai coinjoins between July 2018 and February 2022, traced approximately 4.74 billion USD in mixed coins, and showed approximately 322 million USD landed directly at exchanges and approximately 1.16 billion USD landed at exchanges within two hops. The deanonymization vector is pre mixing and post mixing clustering rather than the mix itself. Source: <https://arxiv.org/abs/2109.10229>, last revised September 14, 2022.

**Chainalysis claims case specific demix capability.** Documented in journalist Laura Shin's 2022 investigation of the 2016 DAO hack: Chainalysis reportedly de mixed a 50 BTC Wasabi spend tied to that case using a non public forensics tool. Elliptic publicly said they can demix Wasabi only in some circumstances. Source: news.bitcoin.com article dated February 23, 2022.

**ACM 2022 paper on Wasabi detection.** "The Unique Dressing of Transactions: Wasabi CoinJoin Transaction Detection" (Stütz, Stütz, et al., 2022) describes detection patterns including the star and collector patterns. The paper is the foundation for current commercial detection but does not claim universal demix. Source: <https://dl.acm.org/doi/fullHtml/10.1145/3528580.3528585>. WebFetch returned 403; metadata visible in search snippets.

**2025 SoK survey.** "SoK: A Survey of Mixing Techniques and Mixers for Cryptocurrencies" (arXiv 2504.20296) confirms that for Wasabi specifically, weak peeling chains and address re use remain the only practical deanonymization levers. Tornado Cash and zk based mixers raise the bar substantially. Source: <https://arxiv.org/html/2504.20296v1>.

### Inferences

The prior reviewer's low confidence Wasabi candidate `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` was probably surfaced via a non protocol heuristic such as input or output amount linkability across the seven deposits, timing correlation across the six coinjoins on July 21 to 23, 2023, or a pre mix cluster overlap heuristic. None of these on their own constitutes attribution, hence the low confidence rating.

A strengthen or refute test that William can request from a paid analytics firm:

1. Run the seven deposit transactions through Chainalysis Reactor or TRM Forensics with the case timeframe.
2. Ask explicitly for the post mix candidate set with their confidence scores.
3. Compare the firm's candidates against the prior reviewer's single candidate to see if `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` appears.
4. If it does, the firm should provide their reasoning and similar candidate pool size; if it does not, treat the prior candidate as discardable.

### Firms That Perform Wasabi Demix as Part of Paid Work

- Chainalysis Reactor and the team's "Crypto Investigators" service.
- TRM Labs Forensics.
- Elliptic Investigator.
- SlowMist MistTrack (their Medium case study II is explicitly a Wasabi coinjoin withdrawal analysis).
- Merkle Science Tracker.

A victim can engage these via law enforcement liaison or, in MistTrack's case, via the free SlowMist AML intake. Source: SlowMist Medium "MistTrack Case 02: Wasabi Coinjoin Withdrawal Analysis," dated 2023.

### Gaps in 2024 to 2026 Literature

No academic paper published in 2024 or 2025 demonstrates Wasabi 2.x demix beyond what was already known from the 2022 measurement work. Industry case studies show targeted linkability via OPSEC failures, not protocol breaks. Round 2 should ask whether any non public DOJ filings name an analytics vendor that achieved Wasabi 2.x demix for a 2023 era case.

## 4. Watchlist Alert Workflows for the Unspent BTC

The live watchlist target is `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` holding 6.49998534 BTC, unspent as of May 25, 2026. The objective is to detect any spend the moment it hits mempool so William can immediately notify the FBI, IC3, and any downstream exchange compliance team if the spend goes to a CEX.

### Option A — Free WebSocket on Public Mempool.space

Minimal Python listener:

```python
import asyncio, json, websockets

ADDR = "bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g"

async def watch():
    async with websockets.connect("wss://mempool.space/api/v1/ws") as ws:
        await ws.send(json.dumps({"track-address": ADDR}))
        async for msg in ws:
            data = json.loads(msg)
            if "address-transactions" in data or "block-transactions" in data:
                # Trigger Telegram, email, or webhook here.
                print("ALERT", data)

asyncio.run(watch())
```

Pros: free, runs anywhere, no account. Cons: needs uptime, public node may rate limit; pair with a systemd or pm2 supervisor.

### Option B — Bitwatch by zapomatic

Open source Docker image that wraps mempool.space WebSocket and ships Telegram notifications. Minimal run:

```bash
mkdir -p ~/.bitwatch
docker run -d --name bitwatch --restart unless-stopped -p 3117:3117 \
  -v ~/.bitwatch:/app/server/data \
  ghcr.io/zapomatic/bitwatch:latest
# Then open http://localhost:3117 and add the address plus Telegram bot token.
```

Source: <https://github.com/zapomatic/bitwatch>.

### Option C — Cryptocurrency Alerting

Free Hobby tier emails on balance changes. Paid Trader at $47.88 per year unlocks SMS, Telegram, Discord. Pro at $239.88 per year and Business at $588 per year unlock webhooks and higher quotas. URL: <https://cryptocurrencyalerting.com/bitcoin-address-monitoring.html>. Use this if William wants a hosted no maintenance option.

### Option D — MetaSleuth Address Monitoring

Free tier allows monitoring 10 addresses with 10 notifications per day, enough for the case set. UI driven so no scripting required. URL: <https://metasleuth.io/wallet-tracking-crypto>.

### Recommended Setup

Run two layers in parallel so a single failure does not miss the spend:

1. Bitwatch in Docker on a stable home machine with Telegram alerts going to William.
2. MetaSleuth UI monitor as a UI fallback that also covers the EVM destination wallets in the same dashboard.

Optionally add Cryptocurrency Alerting free tier as a third email tripwire.

### Beyond the Watchlist

Once an alert fires, William's first action should be to capture the spending transaction id and the receiving address, then immediately:

- File an updated IC3 complaint or, if possible, contact the FBI field office case agent directly with the spend tx.
- Submit the spend tx to Chainabuse as an update to existing reports.
- If the recipient is a CEX deposit, contact that CEX's law enforcement portal directly. The most responsive exchanges for victim or law enforcement freezes in 2024 to 2026 have been Binance, Coinbase, Kraken, OKX, and Bitstamp; all run formal legal request portals.

## 5. Actionable Versus Interesting Leads

### Actionable This Week

1. **File or update IC3 complaint with the consolidated address set.** Include all victim EVM wallets, all THORChain related tx hashes, the Wasabi deposit `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`, the low confidence candidate `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`, the first hop `bc1qtvj76tqmhazw8dl5yx9ep9hs32xxlcletrf6p8`, and the unspent live target `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`. URL: <https://www.ic3.gov/>. If a complaint already exists, file an addendum with the new tracing data so the case is paired with the address set.
2. **Set up the watchlist alert on `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`.** Use the Bitwatch plus MetaSleuth recommendation in section 4. This is the highest signal lead because the funds are still on chain.
3. **Submit Chainabuse reports tied to the case.** One report per case relevant address with private submission so partners and law enforcement see the linkage but the victim's identity remains confidential. URL: <https://www.chainabuse.com/report>.
4. **Engage the SlowMist MistTrack free victim intake.** Use the MistTrack home page contact path. SlowMist has direct lines to exchange compliance teams in Asia and has produced multiple Wasabi specific case studies. URL: <https://misttrack.io/>.
5. **Contact FixedFloat compliance.** Email `compliance@fixedfloat.com` with the FixedFloat related tx hashes and victim address list. FixedFloat will require evidence of source of funds and is known to freeze swaps when given a clear law enforcement or partner referral. URL: <https://ff.io/blog/news/ff-terms-of-use-update>.
6. **File a tip with ZachXBT via <https://zachxbt.info/>.** ZachXBT and his team have a track record of unblocking otherwise stuck case work, including coordination with exchanges. Tips are pseudonymous; no fees by default.

### Interesting but Lower Priority

1. **Run an Arkham Intel search session manually.** Sign in and look up `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva`, `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`, and the WalletExplorer cluster wallet ids. Even one labeled entity match would meaningfully reduce the search space.
2. **Engage Merkle Science or Crystal as a paid second opinion.** Useful only if the case is being staffed with budget for paid analytics; otherwise the free path is sufficient.
3. **Watch THORChain laundering trend coverage from TRM Labs and Merkle Science.** This case sits inside the broader pattern of THORChain being used as a chain hop laundering router; new public case studies may surface attribution clues for the same coinjoin batch.
4. **Pursue formal Wasabi demix via a paid firm.** As described in section 3, request a candidate set with confidence scores rather than a single low confidence candidate. Useful if the budget allows.
5. **Monitor the high volume aggregator `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva`.** Inferring the underlying service through pattern of outputs would be useful but is speculative until Arkham or a paid tool returns a label.
6. **OpenSanctions and other AML sanctions lists.** Worth a check across the case set; low probability but high value if a match exists. URL: <https://www.opensanctions.org/>.

### Caveats and Risk Discipline

- The candidate `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` remains low confidence. All downstream paths described here should be treated as investigative leads, not attribution.
- Do not contact suspects directly. Routing through IC3, Chainabuse, exchange legal portals, and ZachXBT keeps the chain of custody clean.
- Do not promise the victim a recovery outcome. Public data only supports identifying movement and surface attribution; freezing and seizure require law enforcement action.
- A dust UTXO landed on the live target in March 2026; this is consistent with a dusting attack by another tracer. Do not interpret it as a signal about the underlying wallet operator.

# Sources Consulted

### Articles and case studies

- <https://news.bitcoin.com/de-mixing-wasabi-coinjoin-transactions-a-deep-dive-into-chainalysis-deanonymizing-claims/>, dated February 23, 2022.
- <https://news.bitcoin.com/crypto-community-loses-oxt-analysis-tool-amid-legal-troubles-for-samourai-wallet/>, dated April 25, 2024.
- <https://slowmist.medium.com/misttrack-case-study-ii-wasabi-coinjoin-withdrawal-analysis-a3879a59cf4>.
- <https://slowmist.medium.com/slowmist-2025-q2-misttrack-stolen-funds-analysis-747ba3343297>.
- <https://slowmist.medium.com/slowmist-2025-q3-misttrack-stolen-funds-analysis-639cbcefdf6f>.
- <https://slowmist.medium.com/slowmist-2025-q4-misttrack-stolen-funds-analysis-d75e8b0e4536>.
- <https://www.crowdfundinsider.com/2026/01/257111-regtech-slowmist-releases-misttrack-analysis-on-stolen-crypto-funds/>.
- <https://www.trmlabs.com/resources/blog/zachxbt-uncovers-crypto-theft-network-linked-to-us-government-seizure-funds>.
- <https://www.trmlabs.com/resources/blog/thorchain-exploit-drains-usd-11m-across-at-least-nine-chains-what-trm-knows-now>.
- <https://unchainedcrypto.com/kelp-dao-exploiter-moves-175-million-in-stolen-eth-into-new-wallets-routing-funds-through-thorchain/>.

### Academic and standards

- arXiv 2109.10229, Wahrstätter et al., "Adoption and Actual Privacy of Decentralized CoinJoin Implementations in Bitcoin", last revised September 14, 2022. <https://arxiv.org/abs/2109.10229>.
- arXiv 2504.20296, "SoK: A Survey of Mixing Techniques and Mixers for Cryptocurrencies", 2025. <https://arxiv.org/html/2504.20296v1>.
- ACM 2022, "The Unique Dressing of Transactions: Wasabi CoinJoin Transaction Detection." <https://dl.acm.org/doi/fullHtml/10.1145/3528580.3528585>.
- IET Blockchain 2025 review on mixing services. <https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/blc2.70021>.

### Tools and platforms

- <https://metasleuth.io/>
- <https://intel.arkm.com/>
- <https://www.walletexplorer.com/>
- <https://www.chainabuse.com/>
- <https://misttrack.io/>
- <https://www.breadcrumbs.app/>
- <https://mempool.space/docs/api/websocket>
- <https://github.com/zapomatic/bitwatch>
- <https://cryptocurrencyalerting.com/bitcoin-address-monitoring.html>
- <https://www.bitcoinwhoswho.com/>
- <https://hosted.graphsense.iknaio.at/>
- <https://amlbot.com/>

### Reporting and government

- <https://www.ic3.gov/CrimeInfo/Cryptocurrency>
- <https://www.fbi.gov/how-we-can-help-you/victim-services/national-crimes-and-victim-resources/operation-level-up>
- <https://www.fbi.gov/news/stories/operation-level-up-how-the-fbi-is-saving-victims-from-cryptocurrency-investment-fraud>
- <https://zachxbt.info/>
- <https://ff.io/blog/news/ff-terms-of-use-update>

### Live API verification

- mempool.space tx and address endpoints, executed via curl on May 25, 2026 against `4d23a22853686456ae2d8345d0402182ac301bf5aa4010a1f04df90581c2bd8f`, `1962037495cfc6f39cd0c525b78fdcffddb98de34babdcf785b12208152e9bb2`, and the destination addresses.
- WalletExplorer JSON API queries on May 25, 2026 for each address in the seed file.

# Source Quality Assessment

- WalletExplorer API responses are high confidence on cluster ids; service labels are absent for all case addresses, which is itself a data point (none of the case addresses match a known exchange cluster as of May 2026 in WalletExplorer's labels).
- mempool.space API responses are authoritative on chain state; verified against the seed's Blockstream snapshot.
- BitcoinWhosWho's sextortion report on the volume hub is a single low quality data point and should not be used as primary attribution.
- The Wasabi demixing literature is well established up to 2022 and underrepresented in 2024 to 2026; this is a real gap, not a search artifact.
- Arkham labels were not retrieved because the public page returns 403 without an authenticated session; conclusions about Arkham coverage are pending a manual check.

# Open Questions for Round 2

1. Does an authenticated Arkham Intel search return any label for `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva`, `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`, or any WalletExplorer cluster id from this case?
2. Are any of the EVM wallets in the case CSV labeled on Etherscan, Arkham, MetaSleuth, or in known sanctions lists?
3. Has any 2024 or 2025 DOJ or SDNY filing referenced Wasabi demix work tied to a 2023 era case in a way that may overlap with this batch?
4. Does Merkle Science Tracker or Crystal Intelligence have public visibility into the THORChain Asgard vault routing patterns from July 21 to 23, 2023 that match the case?
5. Are any of the WalletExplorer cluster wallet ids tied to OFAC sanctioned addresses in OpenSanctions or US Treasury Recent Actions feeds?
6. Did the dust UTXO sent to `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` in March 2026 originate from a known tracer wallet, and can the dust funder be identified to surface other parties already watching this address?

# Actionable Takeaways

1. Set the watchlist on `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` today using the Bitwatch plus MetaSleuth combination so William never misses the spend.
2. File or update the IC3 complaint with the consolidated address set this week.
3. Submit Chainabuse reports privately for the Wasabi deposit, the demix candidate, the first hop, and the live target.
4. Open a SlowMist MistTrack victim intake to engage their free assistance and exchange liaison.
5. Email `compliance@fixedfloat.com` with the FixedFloat related tx hashes; ask for any record of source of funds challenges that fired.
6. Submit the case to ZachXBT via the tip form for an experienced second eye.
7. Defer the Arkham and paid demix workstreams until round 2 unless budget and time permit them in parallel.

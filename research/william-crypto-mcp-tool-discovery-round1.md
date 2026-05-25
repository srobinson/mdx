---
title: MCP Tool Discovery for William's Stolen Crypto Investigation (Round 1)
type: research
tags: [crypto-theft, mcp, blockchain-forensics, wasabi, thorchain, osint, law-enforcement, sanctions, attribution]
summary: Ranked catalog of MCP servers and adjacent tools relevant to tracing William's 2023 ETH-to-THORChain-to-Wasabi theft, plus FixedFloat side branch. Shortlist of five to install today, plus support tools for evidence, alerting, and report packaging.
status: active
confidence: medium
created: 2026-05-25
updated: 2026-05-25
---

# Executive Summary

The MCP ecosystem now has direct, high-signal coverage for this exact case profile. Three crypto-forensics platforms publish first-party MCP servers that overlap William's surface: **MistTrack (SlowMist)**, **AnChain AML**, and **Caudena Prism**. All three publicly demonstrate Wasabi coinjoin tracing and cross-chain attribution; AnChain's Prince Group case study even involved CoinJoin upstream of a sanctioned wallet cluster, which is structurally similar to William's THORChain-to-Wasabi flow.

Surrounding those, the raw blockchain-data layer is well covered (Etherscan official MCP for the ETH side, Tatum or mempool.space MCP for BTC, THORChain Midgard MCP for the swap router itself). Evidence packaging is solid through Neo4j MCP (graph), DuckDB MCP (CSV-first analytics for the source file), and Excalidraw MCP (court-ready fund-flow diagrams). Watchlist/alerting is best done with QuickNode webhooks or cryptocurrencyalerting.com.

Recommended immediate stack: MistTrack MCP, Etherscan official MCP, mempool.space MCP, THORChain Midgard MCP, DuckDB MCP. AnChain AML MCP is the highest-leverage adjacent install if the Tier-1 trio comes back inconclusive on the low-confidence demix candidate.

What MCPs cannot do: they will not write a credible law-enforcement exchange-request packet, will not get FixedFloat to freeze funds, and will not strengthen the prior demix candidate beyond what an analyst can manually verify. Treat them as evidence-collection multipliers, not recovery agents.

---

# Detailed Findings

## Tier 1 — Direct Crypto-Forensics MCPs (install first)

These three platforms publish purpose-built MCP wrappers around investigation-grade datasets that overlap William's surface.

### 1. MistTrack MCP (SlowMist) — STRONGEST DIRECT MATCH

- **Repo**: https://github.com/slowmist/MistTrackMCP
- **Vendor docs**: https://misttrack.io/ , https://aml.slowmist.com/en/index.html
- **Mirror listings**: https://mcp.so/server/misttrackmcp/slowmist , https://slowmist.medium.com/misttrack-mcp-goes-live-ushering-in-a-new-ai-paradigm-for-on-chain-tracing-and-risk-analysis-d7e95cd07477
- **Why it matches William's case**: SlowMist has publicly published a Wasabi-Coinjoin "withdrawal analysis" workflow where they reported successful tracing of stolen funds mingled through Wasabi (search snippet: "MistTrack team performed a withdrawal analysis of the stolen funds mingled within the Wasabi Coinjoin, successfully tracing and recapturing the flow of funds"). The MCP exposes the same APIs that powered that work.
- **Capabilities exposed via MCP**: address profile, risk score, label lookup against 400M+ labeled addresses, multi-layer recursive transaction tracing, fund-flow visualization, supports 19+ chains including BTC and ETH.
- **Auth and friction**: API key from MistTrack; SlowMist's pricing page lists paid tiers. Install is `git clone` + Python entry per the README; standard `npx`/`uvx` MCP wiring against Claude Desktop and Cursor.
- **Useful for**: validating the prior demix candidate `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`, getting independent labels on `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` (high-volume service), and screening the dormant `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` for risk flags.
- **Caveats**: MistTrack scoring is not court-evidence on its own; treat outputs as investigative leads. Multi-layer recursion can be expensive in API calls; constrain depth first.

### 2. AnChain.AI AML MCP — STRONGEST FOR COURT-GRADE NARRATIVE

- **Repo**: https://github.com/anchainai/aml-mcp
- **Vendor docs**: https://www.anchain.ai/blog/sanction , https://www.anchain.ai/casestudy/data-mcp , https://aml.anchainai.com/
- **Mirror**: https://lobehub.com/mcp/anchainai-aml-mcp
- **Why it matches**: The published Prince Group case study (US Treasury TCO designation, $15B Bitcoin seizure, largest forfeiture in DOJ history) explicitly traced funding upstream through CoinJoin to a sanctioned wallet cluster. That is the same archetype as William's THORChain-to-Wasabi flow: a mixer between a known source and a downstream cluster.
- **Capabilities exposed via MCP**: address risk screening with sanctions matches and compliance flags, entity sanctions lookup with list provenance, IP country/sanctions check, Auto Trace, Auto Report. Outputs are designed for an audit trail and "reproducible audit trail suitable for regulatory review".
- **Auth and friction**: Commercial AML API key required. Standard MCP install patterns. Heavier setup than MistTrack.
- **Useful for**: producing the human-readable narrative and screening packet that would accompany an IC3 / FBI complaint or an exchange legal request.
- **Caveats**: Pricing is sales-led. Don't confuse Auto Report output with formal forensic testimony; an analyst must own the chain of custody.

### 3. Caudena Prism MCP — STRONGEST FOR WASABI DEMIX PATH CONFIRMATION

- **Vendor docs**: https://caudena.com/prism-mcp-the-first-ai-native-blockchain-intelligence-protocol/ , https://caudena.com/
- **Why it matches**: Caudena's training curriculum explicitly covers Wasabi 1.0 and 2.0 demixing, and the Prism MCP exposes a "UTXO Path" tool described as "a straightforward way to confirm or reject demixing findings in coinjoin mixers with verifiable, court-admissible UTXO paths." That is precisely what William's case needs: independent confirmation or rejection of the prior reviewer's low-confidence candidate.
- **Capabilities exposed via MCP**: address analytics, cluster intelligence, transaction tracing across Bitcoin, Ethereum, Tron, more. Single-URL HTTP connection model.
- **Auth and friction**: Caudena API key (commercial). HTTP MCP, single URL, no local install.
- **Useful for**: a second independent take on the Wasabi demix candidate, and for cross-chain pivot when the ETH side links to BTC via THORChain.
- **Caveats**: Demix claims are probabilistic; Chainalysis-style demix capabilities have been publicly debated (the Cryptonews and TheBlock pieces on the topic are worth reading before relying on any vendor's confidence score).

## Tier 2 — Raw Blockchain Data MCPs (install for primary-source queries)

These are not investigation-specific but are the cheapest, fastest way to validate every fact in the seed file against primary sources.

### 4. Etherscan Official MCP — CRITICAL for the ETH side

- **Endpoint**: `https://mcp.etherscan.io/mcp` (Streamable HTTP)
- **Docs**: https://docs.etherscan.io/mcp-docs/introduction , https://docs.etherscan.io/mcp
- **Install for Claude Code**: `claude mcp add --transport http etherscan https://mcp.etherscan.io/mcp --header "Authorization: Bearer YOUR_ETHERSCAN_API_KEY"`
- **Coverage**: 60+ EVM chains via Etherscan V2.
- **Useful for**: pulling tx detail, contract internals, ENS, ERC20 movement for the 10 victim wallets and 13 high-value transactions; resolving FixedFloat `0x4E5B…972F` activity.
- **Free**: Etherscan API key tier is free with rate limits sufficient for case-scale work.

### 5. Tatum Blockchain MCP — multi-chain catch-all

- **Repo**: https://github.com/tatumio/blockchain-mcp
- **Vendor**: https://tatum.io/mcp
- **Install**: `npx @tatumio/blockchain-mcp` with `TATUM_API_KEY` env var.
- **Coverage**: 130+ networks including BTC, ETH, BNB Chain, Litecoin, Dogecoin, Tron, Solana.
- **Useful for**: spanning the BNB side (8.6 BNB in the loss surface), Bitcoin queries that are easier through one key than juggling Mempool plus Etherscan plus Blockstream.
- **Bonus**: Tatum also publishes a public OFAC Sanctioned Wallet List tracker at https://apps.tatum.io/ofac-wallet-tracker — not an MCP but a free reference dataset.

### 6. Mempool.space MCP — free, no-key Bitcoin

- **Repo**: https://github.com/alexandresanlim/mempool-mcp-server (mempool focus), https://github.com/JamesANZ/bitcoin-mcp (general bitcoin)
- **Auth**: None. Hits public mempool.space APIs (a Blockstream Esplora fork).
- **Useful for**: independently re-verifying the seed file's Blockstream observations (UTXO counts, funded sums), walking outputs from `bc1qtvj76tqmhazw8dl5yx9ep9hs32xxlcletrf6p8` peeling chain, polling the dormant `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`.
- **Strength**: Zero install friction and no key. Best for cheap exploratory passes before paying for MistTrack credits.

### 7. THORChain Midgard MCP — directly queries the swap router used in this theft

- **Listing**: https://glama.ai/mcp/servers/@MissionSquad/mcp-thorchain
- **Backing API**: Midgard at `midgard.ninerealms.com`, fallback to `midgard.thorchain.liquify.com`.
- **Useful for**: programmatically reproducing the two Midgard examples in the seed file (`0x655A…` and `40A3…` swaps), pulling complete swap history for the THORChain inbound router observed in the case, validating ETH→BTC pairing per transaction.
- **Auth**: None for public Midgard.

### 8. Bitquery Coinpath MCP — money-flow tracing across 40+ chains

- **Endpoint and install docs**: https://mcp.bitquery.io/ , https://docs.bitquery.io/docs/usecases/MCP/
- **Auth**: OAuth 2.1 (recommended) or API token; ~30-day token caching.
- **Coinpath product**: https://bitquery.io/products/coinpath — sophisticated graph algorithm explicitly built for "follow the money" investigations across cross-chain bridges, DEXs, mixers.
- **Useful for**: a second independent tracing engine to confirm or challenge MistTrack/Prism findings; particularly good for cross-chain (THORChain bridge → BTC) inference.

### 9. Chainstack EVM MCP — fast trace_transaction style queries

- **Endpoint**: `https://mcp.chainstack.com/mcp`
- **Docs**: https://docs.chainstack.com/docs/evm-mcp-server
- **Useful for**: EVM transaction tracing (function calls, state changes, gas, internal txs) on the 13 victim transactions; cleaner than scraping Etherscan when the goal is execution-path detail.
- **Auth**: Chainstack account (free tier covers exploratory work).

### 10. Alchemy / Moralis / QuickNode MCPs — overlap, pick one

- Alchemy: `npm i @alchemy/mcp-server` (https://github.com/alchemyplatform/alchemy-mcp-server)
- Moralis: https://github.com/moralisweb3/moralis-mcp-server
- QuickNode: `@quicknode/mcp` on npm; also publishes webhook product for address monitoring (https://www.quicknode.com/webhooks).
- **Useful for**: redundancy when Etherscan rate-limits, plus QuickNode's webhooks are the cleanest path to set up a Bitcoin movement alert on the dormant `bc1qyt2747…` address.

### 11. Glassnode MCP — context, not investigation

- **Endpoint**: `https://mcp.glassnode.com` ; install via `claude mcp add --transport http glassnode https://mcp.glassnode.com --header "X-Api-Key:KEY"`
- **Useful for**: market context for the July 2023 incident period (ETH price at theft, exchange flow context). Not directly useful for tracing. Free beta tier currently available.

## Tier 3 — OSINT and Web Search MCPs (for label discovery and Chainabuse-style sources)

### 12. mcp-omnisearch — unified Tavily/Brave/Kagi/Exa/Perplexity/Firecrawl

- **Repo**: https://github.com/spences10/mcp-omnisearch
- **Auth**: Per-provider API keys.
- **Useful for**: querying community sources (Reddit threads, BitcoinTalk, Twitter/X) for prior reports on any of the candidate addresses; pulling cached article snippets for the Wasabi demix debate so the analyst is using current vendor claims.

### 13. Playwright MCP (Microsoft official)

- **Docs**: https://github.com/microsoft/playwright-mcp (Microsoft official)
- **Useful for**: scraping pages that don't ship public APIs (Chainabuse search UI, walletexplorer.com which is rate-limited at ~2 req/s, vendor sales pages, court PACER if needed). Accessibility-tree driven, deterministic, no vision model required.

### 14. Bright Data MCP

- **Listed in**: https://github.com/soxoj/awesome-osint-mcp-servers
- **Useful for**: anti-bot bypass when Chainabuse / Etherscan UI blocks Playwright. Paid.

### 15. Maigret MCP (`BurtTheCoder/mcp-maigret`)

- **Useful for**: cross-platform username search if any handles surface (e.g., from a future leak tying a wallet to a forum identity). Not directly relevant in round 1 unless an identity lead emerges.

### 16. Threat Intel MCP (`aplaceforallmystuff/mcp-threatintel`)

- **Repo**: https://github.com/aplaceforallmystuff/mcp-threatintel
- **Bundled sources**: AlienVault OTX, AbuseIPDB, GreyNoise, abuse.ch.
- **Useful for**: only if William has IP addresses tied to the theft (initial breach vector). Not directly useful for the on-chain side of round 1.

## Tier 4 — Evidence Packaging MCPs (graph, analytics, diagrams)

### 17. Neo4j MCP suite (`neo4j-contrib/mcp-neo4j`)

- **Repo**: https://github.com/neo4j-contrib/mcp-neo4j
- **Official**: https://github.com/neo4j/mcp
- **Components**: `mcp-neo4j-cypher` (query exec + schema), `mcp-neo4j-gds` (graph algorithms — PageRank, community detection, shortest paths), `mcp-neo4j-memory` (entity-with-observations storage).
- **Useful for**: building the canonical fund-flow graph from CSV + Midgard + Blockstream outputs, running clustering and PageRank to surface candidate consolidation addresses, persistent agent memory of attributions across investigation sessions.
- **Auth**: local Neo4j instance, or Neo4j AuraDB free tier.

### 18. DuckDB MCP

- **Repo options**: https://github.com/ktanaka101/mcp-server-duckdb , MotherDuck official, Mustafa Hasan Khan's variant.
- **Useful for**: directly opening `/Users/alphab/Downloads/Stolen Crypto July 2021 - Summary.csv` without ETL, running JOINs against scraped Midgard data and Etherscan tx dumps in one query session. DuckDB also has a sqlite scan extension if other case data is in SQLite.

### 19. Excalidraw MCP

- **Repo options**: `yctimlin/mcp_excalidraw` (most full-featured, includes export_to_image, export_scene, get_canvas_screenshot), `excalidraw/excalidraw-mcp` (official, hand-drawn streaming), `cmd8/excalidraw-mcp` (markdown export).
- **Useful for**: court-ready fund-flow diagrams in the IC3 attachment or any law-enforcement packet. The hand-drawn style is unintentionally great for non-technical reviewers; the structured markdown export is great for the agent to reason over what it has drawn.

## Tier 5 — Sanctions / OFAC Screening

### 20. `@easysolutions906/mcp-ofac`

- **Mentioned in**: https://dev.to/easysolutions906/ofac-sanctions-screening-for-crypto-and-defi-a-developers-guide-3fj1
- **Capability**: embedded full SDN list with fuzzy matching; offline.
- **Useful for**: a free, local first-pass check of every address in the case file against current OFAC designations. Should be done before any other engagement — establishes whether any wallets are already known to Treasury.

### 21. AnChain AML MCP — see Tier 1, #2 — covers sanctions screening with provenance.

### 22. Tatum OFAC Sanctioned Wallet Tracker

- **URL**: https://apps.tatum.io/ofac-wallet-tracker
- **Not an MCP**; free reference dataset. Useful for sanity-check cross-reference.

## Tier 6 — Watchlist / Alerting (for the dormant 6.49 BTC lead)

### 23. QuickNode Webhooks

- **Docs**: https://www.quicknode.com/webhooks
- **Useful for**: notification when `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` spends a UTXO. This is the single strongest live lead in the case per the seed file.

### 24. cryptocurrencyalerting.com

- **URL**: https://cryptocurrencyalerting.com/wallet-watch.html
- **Free tier and webhook reference**: https://cryptocurrencyalerting.com/webhook-reference.html
- **Useful for**: lower-friction alternative to running QuickNode; built specifically for wallet-watch use cases including Segwit and legacy.

### 25. Mempool.space MCP polling

- Cheapest path: have an MCP-driven scheduled task poll the address every N hours and notify on UTXO count change. Slower than webhooks but zero infra.

---

## Adjacent High-Value Tools (Not MCPs, but worth direct API access)

| Tool | URL | Why |
|---|---|---|
| Chainabuse Public API v1.2 | https://docs.chainabuse.com/docs/welcome-to-chainabuse-api | Largest community-curated multi-chain scam DB. Build a 50-line MCP wrapper or call REST directly to check every address in case file. |
| WalletExplorer JSON API | https://www.walletexplorer.com/api | No key; rate limited ~2 req/s. Has historical clustering and old exchange tags; complements MistTrack labels. |
| Blockchair address page | https://blockchair.com/bitcoin/address/17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva | Public confirmation surface for the high-volume service address; consider Blockchair's API directly. |
| IC3 filing portal | https://www.ic3.gov/CrimeInfo/Cryptocurrency | Required filing channel; FBI press release confirms cryptocurrency complaints were the single largest 2024 IC3 loss category (181,565 complaints, $11B+). |
| Chainalysis 2026 Crypto Crime Report | https://www.chainalysis.com/reports/crypto-crime-2026/ | Context for narrative framing; cite for case background paragraphs. |
| FBI Operation Level Up | https://www.fbi.gov/how-we-can-help-you/victim-services/national-crimes-and-victim-resources/operation-level-up | Victim resource for crypto theft. |

---

## Shortlist — Install Today

For the William case, install these five MCP servers first. Estimated total wiring time under 90 minutes.

1. **MistTrack MCP** — best direct match for Wasabi/THORChain demix; SlowMist's own case work is on point.
2. **Etherscan Official MCP** (HTTP, single URL, free Etherscan API key) — covers all 10 victim ETH wallets, 13 known transactions, FixedFloat destinations.
3. **mempool.space MCP** (no key) — re-verify every Blockstream observation, walk peeling chains cheaply.
4. **THORChain Midgard MCP** — independent confirmation of the ETH→BTC swap pairings already noted in the seed.
5. **DuckDB MCP** — open the CSV file directly, run SQL across CSV + scraped tx data without ETL.

If credits or pricing block #1, fall back to **Caudena Prism MCP** trial for the Wasabi UTXO-path piece, or **Bitquery Coinpath MCP** (OAuth, generous free tier) as the primary tracing engine.

After the Tier 1 stack confirms a finding, install:

- **AnChain AML MCP** for sanctions packet preparation.
- **Neo4j MCP** to materialize the evidence graph.
- **Excalidraw MCP** for the court-packet diagrams.
- **QuickNode webhook** on `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`.

## Tools to Reject or Deprioritize

- **Chainalysis Reactor / TRM Forensics / Elliptic Navigator / Crystal**: no public MCP wrappers. Sales-led contracts only. Worth a quote if William is willing to pay enterprise-tier; otherwise skip.
- **CipherTrace**: acquired by Mastercard; no MCP; partially superseded by Mastercard Crypto Secure compliance product (not investigation).
- **Arkham Intelligence direct API**: gold-standard entity tagging but commercial; only surfaced inside the Crypto Pro APIs MCP bundle (multi-key juggle). If Arkham access is acquired, use the dedicated wrapper rather than the bundle.
- **OXT.me**: defunct as of 2026 per crypto graveyard listing. Do not rely on it.
- **BitcoinAbuse.com**: superseded by Chainabuse.
- **Bitcoin Wallet MCP servers (e.g., marcopesani's)**: meant for AI agents to *send* Bitcoin, not for investigation. Wrong category.
- **General "Crypto Pro APIs" MCP bundles**: bundle DefiLlama + CoinGecko + Arkham mostly for trading; for investigation, install the Arkham slice (if licensed) standalone.
- **Any service advertising "crypto recovery" with up-front fees**: standard advance-fee scam pattern. Common in this domain; do not engage.

## Exact Next Commands (where credible)

```bash
# 1. Etherscan official MCP (free key from etherscan.io)
claude mcp add --transport http etherscan https://mcp.etherscan.io/mcp \
  --header "Authorization: Bearer YOUR_ETHERSCAN_API_KEY"

# 2. Chainstack EVM MCP (free Chainstack account)
claude mcp add --transport http chainstack https://mcp.chainstack.com/mcp

# 3. Glassnode MCP (free beta)
claude mcp add --transport http glassnode https://mcp.glassnode.com \
  --header "X-Api-Key: YOUR_GLASSNODE_API_KEY"

# 4. Tatum MCP (free tier, single key for BTC+ETH+BNB)
claude mcp add-json tatum '{"command":"npx","args":["-y","@tatumio/blockchain-mcp"],"env":{"TATUM_API_KEY":"<key>"}}'

# 5. QuickNode MCP (for webhook setup against bc1qyt2747...)
claude mcp add-json quicknode '{"command":"npx","args":["-y","@quicknode/mcp"],"env":{"QUICKNODE_API_KEY":"<key>"}}'

# 6. mempool.space MCP (no key)
claude mcp add-json mempool '{"command":"npx","args":["-y","@alexandresanlim/mempool-mcp-server"]}'
# (verify exact package name in the README; the repo is alexandresanlim/mempool-mcp-server)

# 7. DuckDB MCP (for the CSV file)
claude mcp add-json duckdb '{"command":"uvx","args":["mcp-server-duckdb","--db-path","/tmp/william-case.duckdb"]}'

# 8. Neo4j MCP (assumes local Neo4j or AuraDB)
claude mcp add-json neo4j-cypher '{"command":"uvx","args":["mcp-neo4j-cypher"],"env":{"NEO4J_URL":"bolt://localhost:7687","NEO4J_USERNAME":"neo4j","NEO4J_PASSWORD":"<pw>"}}'
```

The `tatumio/blockchain-mcp` and `mcp-neo4j-cypher` packages should be verified at install time against the latest READMEs; package names occasionally rename.

For MistTrack, AnChain, Prism, and Bitquery, follow the vendor docs because each has its own auth flow.

---

# Sources Consulted

### Direct vendor / repo (primary)
- MistTrack MCP repo and writeup: https://github.com/slowmist/MistTrackMCP , https://slowmist.medium.com/misttrack-mcp-goes-live-ushering-in-a-new-ai-paradigm-for-on-chain-tracing-and-risk-analysis-d7e95cd07477
- AnChain AML MCP repo: https://github.com/anchainai/aml-mcp
- AnChain Prince Group case study: https://www.anchain.ai/casestudy/data-mcp , https://www.anchain.ai/blog/sanction
- Caudena Prism MCP: https://caudena.com/prism-mcp-the-first-ai-native-blockchain-intelligence-protocol/
- Etherscan MCP docs: https://docs.etherscan.io/mcp-docs/introduction , https://docs.etherscan.io/mcp
- Tatum MCP: https://github.com/tatumio/blockchain-mcp , https://tatum.io/mcp
- Mempool.space MCP: https://github.com/alexandresanlim/mempool-mcp-server , https://github.com/JamesANZ/bitcoin-mcp
- THORChain Midgard MCP: https://glama.ai/mcp/servers/@MissionSquad/mcp-thorchain
- Chainstack EVM MCP: https://docs.chainstack.com/docs/evm-mcp-server , https://chainstack.com/mcp/
- Bitquery MCP: https://mcp.bitquery.io/ , https://bitquery.io/products/coinpath , https://docs.bitquery.io/
- Alchemy MCP: https://github.com/alchemyplatform/alchemy-mcp-server
- Moralis MCP: https://github.com/moralisweb3/moralis-mcp-server
- QuickNode MCP: https://www.npmjs.com/package/@quicknode/mcp , https://www.quicknode.com/webhooks
- Glassnode MCP: https://docs.glassnode.com/guides-and-tutorials/glassnode-mcp-server
- Neo4j MCP: https://github.com/neo4j/mcp , https://github.com/neo4j-contrib/mcp-neo4j , https://neo4j.com/docs/mcp/current/
- DuckDB MCP: https://github.com/ktanaka101/mcp-server-duckdb , https://motherduck.com/blog/faster-data-pipelines-with-mcp-duckdb-ai/
- Excalidraw MCPs: https://github.com/yctimlin/mcp_excalidraw , https://github.com/excalidraw/excalidraw-mcp , https://github.com/cmd8/excalidraw-mcp
- Iknaio / GraphSense: https://iknaio.com/ , https://graphsense.org/ , https://www.iknaio.com/about-us
- mcp-omnisearch: https://github.com/spences10/mcp-omnisearch
- mcp-threatintel: https://github.com/aplaceforallmystuff/mcp-threatintel
- awesome-osint-mcp-servers: https://github.com/soxoj/awesome-osint-mcp-servers
- awesome-blockchain-mcps: https://github.com/royyannick/awesome-blockchain-mcps
- aaarghhh/awesome_osint_blockchain_analysis: https://github.com/aaarghhh/awesome_osint_blockchain_analysis
- WalletExplorer API: https://www.walletexplorer.com/api
- Chainabuse Public API: https://docs.chainabuse.com/docs/welcome-to-chainabuse-api
- Tatum OFAC tracker: https://apps.tatum.io/ofac-wallet-tracker

### Vendor product / comparison (secondary)
- Crypto Pro APIs MCP (DefiLlama / CoinGecko / Arkham): https://www.pulsemcp.com/servers/rei-network-crypto-apis
- Arkham tagging system: https://info.arkm.com/research/a-guide-to-arkham-intels-industry-leading-tagging-system
- Chainalysis vs Elliptic vs TRM comparisons: https://cryptotracelabs.com/blog/chainalysis-vs-elliptic-vs-trm-labs-which-platform-should-investigators-choose/ , https://finconduit.com/resources/blockchain-analytics-providers-compared
- FixedFloat AML/KYC policy: https://www.fixedfloat.investments/aml-kyc-policy , https://ff.io/terms-of-service
- Wasabi demix debate: https://cryptonews.net/news/security/3194447/ , https://www.theblock.co/post/135148/a-look-at-chainalysis-claim-to-track-bitcoin-through-mixing-service-coinjoin
- Chainalysis 2026 Crypto Crime Report: https://www.chainalysis.com/reports/crypto-crime-2026/
- IC3 cryptocurrency portal: https://www.ic3.gov/CrimeInfo/Cryptocurrency
- FBI crypto fraud release: https://www.fbi.gov/news/press-releases/cryptocurrency-and-ai-scams-bilk-americans-of-billions

### Directory aggregators (tertiary, for discovery cross-check)
- PulseMCP: https://www.pulsemcp.com
- mcp.so: https://mcp.so
- Glama: https://glama.ai/mcp
- Smithery: https://smithery.ai
- Playbooks: https://playbooks.com/mcp

---

# Source Quality Assessment

- **High confidence**: vendor-published MCP repos and docs (MistTrack, AnChain, Etherscan, Tatum, Chainstack, Bitquery, Neo4j). All have first-party documentation and active GitHub repos.
- **High confidence**: SlowMist's published Wasabi withdrawal-analysis writeup matches William's case archetype directly.
- **High confidence**: AnChain Prince Group case study is corroborated by US DOJ press release (https://www.justice.gov/opa/pr/chairman-prince-group-indicted-operating-cambodian-forced-labor-scam-compounds-engaged), so the MCP claim is anchored in a real, documented investigation.
- **Medium confidence**: Caudena Prism's "court-admissible UTXO paths" claim — vendor language; needs an analyst's independent verification before relying on it for case work.
- **Medium confidence**: WalletExplorer API still functional at time of search but the project has not been actively updated for years; treat labels as historical, not current.
- **Lower confidence**: PulseMCP / Glama / mcp.so directory listings sometimes lag the vendor's actual install instructions; always cross-check at install time against the repo README.

# Open Questions

1. Is `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` an exchange consolidation address, a payment processor, or a service like CashApp/HiveDC? No public attribution surfaced in this round; MistTrack and Caudena are the next places to look. The address has more than 133,000 funded UTXOs, which is consistent with an exchange hot wallet but not diagnostic.
2. Does MistTrack's actual Wasabi tracing performance hold up on the seven specific deposits in William's case? The published case study is generic; verification on these specific UTXOs is needed before treating outputs as anything more than a lead.
3. Is Caudena Prism's Bitcoin coverage as deep as MistTrack's, or is it more Ethereum/Tron oriented? The vendor page lists "Bitcoin, Ethereum, Tron, and more" but the marketing emphasis is on EVM. An evaluation account is the only way to know.
4. Does FixedFloat retain transaction records that long? The seed mentions FixedFloat-tagged transactions from July 2023; FixedFloat's terms reserve the right to share data with authorities but the retention period for unverified flows is undocumented. A law-enforcement preservation letter is the path.
5. Are there community-known labels for any of the candidate addresses on Reddit, Twitter/X, or BitcoinTalk that aren't surfaced by vendor APIs? An OSINT pass with mcp-omnisearch + Playwright MCP should be a follow-up round.
6. Is there any MCP that wraps Crystal Intelligence's free Lite tier? Not surfaced in this round. Worth a focused search.

# Actionable Takeaways

1. **Install the Shortlist Five tonight**: Etherscan + Tatum + mempool.space + THORChain Midgard + DuckDB. Cost: zero (Etherscan/Tatum free tiers, mempool no key, Midgard no key, DuckDB no key).
2. **Run MistTrack and Caudena trials in parallel**: each on the prior demix candidate `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` to triangulate the low-confidence reviewer finding.
3. **Stand up a QuickNode webhook on `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`** as the single highest-leverage live lead. The address has been dormant since March 2026; movement is the trigger.
4. **Open the case CSV in DuckDB MCP** and join it against Etherscan tx pulls to build the canonical transaction-level evidence table. This becomes the source of truth that everything else writes back to.
5. **Build the Neo4j evidence graph** as a side-effect of the above, so attribution and labels accumulate across sessions instead of being re-derived.
6. **Use Excalidraw MCP to produce a one-page fund-flow diagram** for the IC3 attachment and any future exchange-legal request. Visual evidence carries disproportionate weight with non-technical reviewers.
7. **Run the OFAC MCP first-pass** (`@easysolutions906/mcp-ofac`) on every address in the file. Five minutes of work that establishes the floor; if anything matches, the entire case strategy shifts.
8. **Do not engage any service promising recovery for a fee**. Advance-fee fraud is rampant in this domain; the legitimate recovery path is law enforcement plus exchange legal cooperation, and neither charges victims.
9. **Round 2 should focus on**: legal/exchange legal-request preparation (Wasabi operator successor, exchanges with FixedFloat onramps, US exchange endpoints that touched the candidate addresses), and any community-known label for `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva`.

---
title: William Crypto Recovery Precedents and Enforcement Paths, Round 1
type: research
tags: [crypto-theft, bitcoin, thorchain, wasabi, fixedfloat, law-enforcement, recovery-precedents, osint, ic3, fbi, chainalysis, chainabuse]
summary: Recovery precedents, reporting playbook, evidence packet template, and ranked action list for a 2023 theft of ~$1.67M laundered through THORChain into Wasabi CoinJoin with a low confidence demix candidate and one currently unspent BTC address.
status: active
confidence: medium
created: 2026-05-25
updated: 2026-05-25
related:
  - stolen-crypto-case-seed-2026-05-25
---

# Executive Summary

Recovery from mixer routed crypto theft is rare but possible. The dominant success pattern is freezing at downstream CEX endpoints after low confidence on chain leads age into post mixer attribution mistakes by the launderer, with the FBI Recovery Asset Team, IRS Criminal Investigation, and exchange compliance teams acting on a documented evidence packet. For William's case the highest leverage actions this week are filing or refreshing IC3 and a direct FBI field office introduction with the full evidence packet, registering watchlists on the unspent BTC address through a free tracing platform, filing Chainabuse reports keyed to every relevant address, and submitting a coordinated suspicious activity request to FixedFloat using the THORChain Midgard verified transactions.

# Detailed Findings

## 1. Recovery is possible years after theft, but only when off chain mistakes accumulate

The strongest precedent for delayed recovery is the 2016 Bitfinex hack of 119,756 BTC. The DOJ recovered ~94,631 BTC worth $3.6B at the time in February 2022, roughly 5.5 years after the theft, by decrypting a private key file in Ilya Lichtenstein's cloud storage that contained launderer controlled addresses. The launderers had used AlphaBay as a mixer, then mistakes in account funding and KYC let federal investigators stitch the chain back together [TRM Labs, Wikipedia]. Lichtenstein and Heather Morgan pleaded guilty in August 2023, sentenced November 2024. Lichtenstein was released early under the First Step Act in January 2026 [CyberScoop, CoinDesk].

The 2012 Silk Road 50,000 BTC theft by Jimmy Zhong was solved roughly a decade later when Zhong made a critical off chain mistake. IRS-CI led that investigation [CNBC].

The pattern: mixer obfuscation does not protect against eventual attribution if the launderer touches identified surfaces later. The watchlist and dormant evidence package thesis is well supported.

## 2. Wasabi specific demixing and post mixer attribution

Europol's internal EC3 report on Wasabi, leaked 2020, said realistically in most cases Wasabi CoinJoin transactions cannot be demixed [CoinGeek, The Block]. Chainalysis has publicly claimed limited demix capability, especially where users make mistakes such as later consolidating mixed outputs or sending to known KYC accounts. Elliptic co-founder Tom Robinson said the same: demix is feasible when there is user error, not routinely [Bitcoinist].

Wasabi 2.0 launched the WabiSabi protocol with non uniform outputs starting 2022 and improved privacy over Wasabi 1.0. William's mixing happened July 2023, so it is Wasabi 2.0 era. The June 2024 zkSNACKs coordinator shutdown and the prior April 2024 US user blocking [Wasabi Blog] mean there is no live coordinator that can be subpoenaed for future mix activity. Pre shutdown coordinator records may still be reachable in theory through Gibraltar based legal process to zkSNACKs Ltd, but no public reporting confirms any such subpoena succeeded.

The prior demix candidate for William's case was explicitly low confidence. Treat it as an investigative lead requiring independent strengthening. The fact that the candidate's downstream chain reached one currently unspent BTC address with 6.49998534 BTC is meaningful only if attribution improves.

## 3. Concrete recent recovery cases relevant to William's case shape

### Ripple co-founder Chris Larsen, January 2024 LastPass linked theft, $150M XRP

ZachXBT detected the theft live. A March 2025 forfeiture complaint disclosed that law enforcement traced $23,604,815.09 of the stolen XRP across seven downstream services between June 2024 and February 2025: OKX, Kraken, WhiteBIT, AscendEX, FixedFloat, SwapSpace, CoinRabbit. WhiteBIT intercepted, froze, and on August 14, 2024 returned funds to the FBI pursuant to court order [Bitcoin.com News, ProtoS, BleepingComputer]. Notable for William: FixedFloat is named as one of the seven services that received traceable stolen assets in a federal investigation, confirming it is a reachable jurisdiction for legal process.

### Bybit hack, February 2025, $1.4B ETH

Lazarus Group laundered roughly 944 BTC through Wasabi Wallet alongside Tornado Cash, Railgun, CryptoMixer, plus cross chain swaps via THORChain, eXch, Lombard, LiFi, Stargate, SunSwap. As of April 2025, 68.57% remained traceable, 27.59% had "gone dark," and 3.84% was frozen, mostly through Binance and OKX banning Lazarus linked wallets ($43.7M). Bybit's Lazarus Bounty Program offered $140M in rewards and paid $2.2M to 11 hunters who deciphered mixer patterns [BanklessTimes, Coinpedia, Coingape]. The structural lesson: even with strong attribution, the freeze rate against an APT class launderer is low single digits. The freeze rate against an ordinary thief is higher because they hit identified CEXes more readily.

### Ronin bridge, March 2022, $625M

Law enforcement and industry partners seized roughly $30M, about 10% of the theft. Binance recovered $6M after the attackers spread funds across 86 accounts [Chainalysis, TechCrunch]. Same lesson: even with strong on chain forensics and active LE engagement, percentage recovery against a sophisticated launderer is small but nonzero.

### Edmonds Marshall McMahon UK case, June 2024

UK High Court default judgment for delivery up of stolen digital assets traced to Binance. Binance complied. Specialized civil recovery counsel using "intelligence first" approach to identify cooperative exchanges and the right civil or criminal lever [Edmonds Marshall McMahon].

### Operation Atlantic, March 2026

US Secret Service, UK NCA, Ontario Provincial Police, and OSC joint operation against approval phishing scams. Identified more than 20,000 victims, froze more than $12M, identified $45M in stolen crypto across schemes. Chainalysis was the on chain partner. Beacon Network feeds real time intelligence to 70+ financial institutions covering 75% of global crypto volume across 21+ countries [Chainalysis, TheBlock, CoinDesk].

### Operation Shamrock, ongoing

Public private coalition focused on pig butchering. TRM Labs hosts Chainabuse as the largest user reported illicit activity database. Coalition includes 2,400+ law enforcement and private partners. One reported victim ("Mez") whose $240K was stolen was tied to a $70M federal seizure because the Chainabuse report linked the small case to the larger investigation [TRM Labs, Operation Shamrock].

## 4. Reporting channels: what actually works

### IC3 (FBI Internet Crime Complaint Center) — required baseline

- File at ic3.gov regardless of dollar amount.
- Include cryptocurrency addresses, amounts, types, transaction hashes, dates and times, scammer contact methods, web domains, phone numbers.
- IC3 generates a complaint number that becomes the reference for all future contact.
- The IC3 Recovery Asset Team (RAT) achieved 74% success in FY2021, 66% in 2024, 58% in 2025 on its Financial Fraud Kill Chain process. FFKC is wire fraud focused, typically triggered within 72 hours of the wire and at $50K+. Crypto theft three years after the fact is not an FFKC use case, but IC3 remains the canonical intake and the way to be added to multi victim investigations [IC3 Annual Reports 2024, 2025, TRM Labs].

### FBI field office direct contact

For high dollar losses, IC3 alone is insufficient. Call or email the local FBI field office directly with a one page case summary and the evidence packet. Operation Level Up notified 3,780 victims in 2025 and prevented an estimated $225.9M in additional losses by direct outreach, which shows the FBI is willing to do bilateral victim contact on high signal cases [FBI Operation Level Up].

### IRS Criminal Investigation

IRS-CI has 18 US field offices and an international attaché network. IRS-CI was the lead on the Silk Road / Jimmy Zhong cold case. Crypto centric IRS-CI agents have deeper technical understanding than typical FBI cyber agents at most field offices, and IRS-CI runs many recent crypto laundering prosecutions [IRS-CI 2025 Annual Report]. Worth a parallel report to FBI when the loss is in the seven figure range.

### US Secret Service

Operation Atlantic and other recent multi national operations are led by USSS Cyber Investigations. USSS June 2025 announcement included the largest ever seizure related to crypto confidence scams [USSS]. Reasonable parallel channel for international scope cases.

### DOJ National Cryptocurrency Enforcement Team (NCET)

NCET was disbanded effective April 2025 by the Blanche memo. Existing cases re routed to US Attorneys' Offices and individual prosecution units [Chainalysis, Wiley]. NCET no longer exists as a single entry point. Coordination now flows through US Attorney offices and the FBI Virtual Asset Unit.

### State Attorney General offices

NY AG Letitia James has frozen crypto in scam cases (e.g. $300K freeze August 2025 in remote job scam). California AG Rob Bonta runs an active crypto fraud unit including 42 fake site takedowns in 2024 [NY AG, CA OAG]. If William is in or has a connection to a state with an active AG crypto unit, file there in parallel.

### Chainabuse (TRM Labs)

Free public reporting site at chainabuse.com keyed to wallet addresses. Multi report aggregation strengthens patterns. Reports feed into TRM, Chainalysis (Beacon Network), and law enforcement contacts. No fee. Multiple Operation Shamrock recoveries trace back to Chainabuse linking small reports to large investigations [Chainabuse, Operation Shamrock].

### Exchange compliance portals

Binance: "How to Report Stolen Funds Transferred to Binance" article 360000006051. Provide login screenshots, transaction details, blockchain transaction list. Binance will only release identifying information to law enforcement, not to the victim directly [Binance Support]. Same pattern at OKX, Kraken, Coinbase, Bitfinex, Bitstamp. Each major CEX has a law enforcement portal.

FixedFloat: AML/KYC policy at fixedfloat.investments/aml-kyc-policy. Reserves right to suspend orders, freeze funds, share data including IP addresses with government authorities on request. Will accept victim complaints as part of triggering conditions. A Chief Compliance Officer is the formal LE contact. FixedFloat is reachable. See Larsen case above for evidence it cooperates with US federal court orders [FixedFloat policy, ProtoS].

THORChain: explicitly refuses to block illicit activity by protocol design [The Record, MIT Technology Review]. No freezing pathway. Useful only for evidence preservation via Midgard API and ninerealms.com.

## 5. Evidence packet for law enforcement and exchanges

Required structure for a one stop packet (one PDF + one CSV + the wallet provenance file):

### Cover summary, one page

- Date of incident: July 21 to 23, 2023.
- Total loss at time of theft: $1,675,929.20 (884.82 ETH, 8.6 BNB).
- Attacker pathway in two sentences: ETH wallets to THORChain to BTC to Wasabi to peeling chain, with a FixedFloat side branch.
- Highest priority current lead: bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g, 6.49998534 BTC, currently unspent, subject to low confidence demix caveat.
- Filed under IC3 complaint number XXXXX (fill once filed).

### Victim wallet provenance

- Account ownership documentation for the 10 EVM wallets.
- KYC if any held by an exchange that funded those wallets.
- Date wallets were created, purpose, normal pattern of activity.

### Transaction inventory CSV

Columns: timestamp UTC, chain, tx hash, from address, to address, asset, amount native, amount USD at time, USD source (CoinGecko / CoinMarketCap historical), notes.

Include all 13 high value source transactions, all THORChain in / out hops verified via Midgard, the seven Wasabi deposits, the six coinjoin transactions, the candidate spend tx 1962037495cfc6f39cd0c525b78fdcffddb98de34babdcf785b12208152e9bb2, the FixedFloat related transactions, and the service like branch ending at 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva.

### Wasabi specific exhibits

- Blockstream verification text for each Wasabi deposit address and each downstream address with funded sum, spent sum, current balance, dates verified.
- THORChain Midgard verification text for each in / out pair, including the example 0x655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204 (125.44715147 ETH in, 7.29622713 BTC out).
- Statement of methodology used by the prior demix reviewer and explicit low confidence caveat.
- Graph image of the path (optional but high impact).

### FixedFloat exhibits

- List of FixedFloat related transactions from the CSV.
- The FixedFloat receiving wallet 0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F.
- Time and amount of each swap.
- Note that FixedFloat is the named service in the Chris Larsen forfeiture complaint, so suspicious activity reporting precedent exists.

### Service branch attribution request

- The high volume address 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva (133,000+ funded UTXOs, 9933+ BTC funded sum) needs labeling.
- Public data alone is insufficient. Provide the inputs and ask law enforcement, Chainalysis Reactor users, or TRM Forensics users to label it.

### Discipline rules

- No private keys.
- No seed phrases.
- No direct contact with suspects.
- No claim of recovery being guaranteed.
- Explicit distinction between fact, inference, and speculation in every section.

## 6. Patterns that apply to a low confidence Wasabi demix lead with one unspent BTC address

The dominant successful pattern across Bitfinex, Silk Road, Larsen, and Bybit:

1. Capture is rarely from the mixer itself. It is from where post mixer funds touch identified KYC surfaces (CEX deposit, cloud account, payment processor, fiat off ramp).
2. Until that happens, the work is preservation: keep the demix candidate logged, keep the unspent address under active watchlist, keep the evidence packet ready for the day funds move.
3. Multi report aggregation through Chainabuse and Beacon Network increases the probability that any future movement triggers a real time CEX alert.
4. Civil litigation pathways exist (UK High Court precedent, Edmonds Marshall McMahon) for cases where US federal investigators do not engage, but they are expensive (tens of thousands to millions upfront) and only viable when the unspent address actually moves to a cooperating jurisdiction.

For William specifically: do not commit money to recovery firms today. The right move is to lock in cheap monitoring on the unspent BTC address, file IC3 and FBI field office, and wait. If the 6.49998534 BTC moves, that is the moment when the case becomes actionable.

## 7. Crypto recovery scams to avoid

The June 24, 2024 FBI PSA (alert I-062424-PSA) on fictitious law firms reported $9.9M in additional losses to crypto theft victims during a one year window. Universal red flags from the PSA, the IC3 cryptocurrency page, and the Chainabuse safety guide:

- Anyone who DMs William about his existing theft.
- Anyone who claims FBI, IRS, or CFPB affiliation in unsolicited contact.
- Upfront fees, "back taxes," "release fees," "compliance fees" demanded before recovery.
- Payment in crypto, gift cards, or wire to a foreign account.
- Specific knowledge of prior loss amounts (this signals the scammer bought lists of prior victims).
- WhatsApp group "task forces" with foreign attorneys.
- Promises to "directly freeze" or "directly recover" without law enforcement involvement. Only law enforcement can issue a freeze order.
- Reviews on the firm site that cannot be cross referenced.
- Vague company history, minimal online presence, no Chambers / Legal 500 ranking, no verified bar number.

Legitimate options exist but they are narrow:

- Law enforcement: free.
- Initial blockchain tracing by a private investigator: $0 to ~$800 typical.
- Full civil litigation by a recognized firm (Edmonds Marshall McMahon UK, Asset Reality, US specialized civil counsel): tens of thousands to millions, viable only for very large losses with identified recoverable assets.
- Litigation funding: 30-40% of recovered amount, only for multi million dollar losses.
- Chainabuse community reporting: free.

## 8. What to avoid because it is ineffective or harms the case

- Posting victim wallet addresses publicly with exact loss attribution before filing IC3. It can attract scammers and tip off attackers.
- Direct contact with suspect addresses. Including dust attacks, OP_RETURN messages, or NFT airdrops to suspect addresses. Useful only inside a court ordered civil John Doe lawsuit (LCX v John Doe NY model), not as a vigilante move.
- Engaging "asset recovery" services advertising on Google, Reddit, or X DMs.
- Paying any upfront fee that is not (a) a recognized law firm's transparent retainer with a known billing model or (b) a flat fee to a specific named blockchain analyst with verified track record for short scoped tracing.
- Sharing seed phrases or private keys with anyone for any reason.
- Restating "recovery is likely" in any victim impact statement. Set expectation to "preservation and watchlist now, action if and when funds move."

# Sources Consulted

## Primary government sources

- [FBI IC3 Cryptocurrency Crime Info](https://www.ic3.gov/CrimeInfo/Cryptocurrency) accessed 2026-05-25.
- [FBI PSA I-062424-PSA Fictitious Law Firms Targeting Crypto Scam Victims, June 24 2024](https://www.ic3.gov/PSA/2024/PSA240624).
- [FBI Cryptocurrency Investment Fraud victim resources](https://www.fbi.gov/how-we-can-help-you/victim-services/national-crimes-and-victim-resources/cryptocurrency-investment-fraud).
- [FBI Operation Level Up](https://www.fbi.gov/how-we-can-help-you/victim-services/national-crimes-and-victim-resources/operation-level-up).
- [FBI Cryptocurrency Recovery Fraud Victim Form](https://forms.fbi.gov/cryptorecoveryfraudvictims).
- [IC3 2024 Annual Report PDF](https://www.ic3.gov/AnnualReport/Reports/2024_IC3Report.pdf).
- [IC3 2025 Annual Report PDF](https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf).
- [IRS Criminal Investigation portal](https://www.irs.gov/compliance/criminal-investigation).
- [IRS-CI 2025 Annual Report PDF](https://www.irs.gov/pub/irs-pdf/p3583.pdf).
- [DOJ NCET formation announcement](https://www.justice.gov/archives/opa/pr/deputy-attorney-general-lisa-o-monaco-announces-national-cryptocurrency-enforcement-team).
- [DOJ NCET overview page](https://www.justice.gov/criminal/national-cryptocurrency-enforcement-team).
- [DOJ $225M crypto investment fraud civil forfeiture complaint](https://www.justice.gov/opa/pr/united-states-files-civil-forfeiture-complaint-against-225m-funds-involved-cryptocurrency).
- [USSS Largest Ever Crypto Confidence Scam Seizure, June 2025](https://www.secretservice.gov/newsroom/releases/2025/06/largest-ever-seizure-funds-related-crypto-confidence-scams).
- [Secret Service Mixers Public Alert, May 2025 PDF](https://www.secretservice.gov/sites/default/files/reports/2025-06/Public-Alert-Cryptocurrency-Mixing.pdf).
- [NY AG cryptocurrency resources](https://ag.ny.gov/resources/individuals/investing-finance/cryptocurrency).
- [NY AG $300K crypto freeze, remote job scam](https://ag.ny.gov/press-release/2025/attorney-general-james-freezes-300000-cryptocurrency-linked-scammers-targeting).
- [CA AG fake crypto site takedowns 2024](https://oag.ca.gov/news/press-releases/attorney-general-bonta-protects-californians-shutting-down-42-fake).

## Industry analytics

- [TRM Labs, IC3 2024 report breakdown](https://www.trmlabs.com/resources/blog/a-record-breaking-year-for-cybercrime-key-findings-from-the-fbis-2024-ic3-report).
- [TRM Labs, Bitfinex sentencing and $10B recovery](https://www.trmlabs.com/resources/blog/ilya-lichtenstein-sentenced-for-role-in-bitfinex-hack-in-razzlekhan-case-as-government-recovers-about-10-billion-in-stolen-funds).
- [TRM Labs, ZachXBT US government seizure linkage](https://www.trmlabs.com/resources/blog/zachxbt-uncovers-crypto-theft-network-linked-to-us-government-seizure-funds).
- [TRM Labs, THORChain exploit drains $11M+](https://www.trmlabs.com/resources/blog/thorchain-exploit-drains-usd-11m-across-at-least-nine-chains-what-trm-knows-now).
- [TRM Labs, victim restoration case studies](https://www.trmlabs.com/resources/case-studies/after-the-scam-how-law-enforcement-restores-hope-for-victims).
- [Chainalysis, Operation Atlantic blog](https://www.chainalysis.com/blog/operation-atlantic-freezing-crypto-scam-proceeds/).
- [Chainalysis, Bitfinex hack plea](https://www.chainalysis.com/blog/bitfinex-hack-plea-july-2023/).
- [Chainalysis, Asset Seizure overview](https://www.chainalysis.com/blog/cryptocurrency-asset-seizure/).
- [Chainalysis, Ronin DPRK seizure](https://www.chainalysis.com/blog/axie-infinity-ronin-bridge-dprk-hack-seizure/).
- [Chainalysis, NCET disbanding analysis](https://www.chainalysis.com/blog/ncet-blanche-memo/).
- [Chainabuse: Recovery Guide](https://safety.chainabuse.com/article/the-ultimate-guide-how-to-recover-stolen-cryptocurrency).
- [Chainabuse: Asset Recovery Scammers Guide](https://safety.chainabuse.com/article/understanding-the-recovery-of-stolen-crypto-funds-and-the-role-of-private-investigators).
- [Operation Shamrock](https://www.operationshamrock.org/).

## Case reporting

- [Wikipedia, 2016 Bitfinex hack](https://en.wikipedia.org/wiki/2016_Bitfinex_hack).
- [CNBC, Jimmy Zhong Silk Road story](https://www.cnbc.com/2023/10/17/crypto911.html).
- [CyberScoop, Lichtenstein early release](https://cyberscoop.com/bitfinex-hacker-ilya-lichtenstein-early-release-first-step-act/).
- [CoinDesk, Lichtenstein First Step Act release](https://www.coindesk.com/tech/2026/01/02/crypto-hacker-ilya-lichtenstein-credits-trump-s-first-step-act-for-early-prison-release).
- [BleepingComputer, US seizes $23M LastPass breach crypto](https://www.bleepingcomputer.com/news/security/us-seizes-23-million-in-crypto-stolen-via-password-manager-breach/).
- [ProtoS, Chris Larsen $150M LastPass](https://protos.com/ripple-ceo-chris-larsen-lost-150m-in-xrp-after-lastpass-hack/).
- [Bitcoin.com News, Larsen LastPass forfeiture complaint](https://news.bitcoin.com/ripple-co-founder-chris-larsen-lost-150m-in-xrp-due-to-lastpass-hack-forfeiture-complaint-says/).
- [CoinDesk, Larsen heist details](https://www.coindesk.com/tech/2025/03/08/ripple-co-founder-s-usd150m-xrp-heist-related-to-lastpass-hack-zachxbt).
- [BanklessTimes, Bybit hack 88% traceable](https://www.banklessTimes.com/articles/2025/03/20/bybit-hack-update-1-4b-stolen-funds-88-traceable/).
- [Coinpedia, Bybit tracing $1.4B](https://coinpedia.org/news/bybit-hack-update-tracing-the-1-4-billion-stolen-crypto-funds/).
- [Coingape, Bybit Wasabi laundering $16M](https://coingape.com/bybit-hack-update-wasabi-mixer-used-to-launder-16m-in-stolen-bitcoin/).
- [TheStreet, Bybit $1.5B tracking through mixers](https://www.thestreet.com/crypto/investing/bybit-tracks-1b-in-stolen-crypto-through-mixers).
- [Edmonds Marshall McMahon, crypto wallet freezing orders landmark](https://www.emmlegal.com/news/crypto-wallet-freezing-orders/).
- [Edmonds Marshall McMahon, recovery success story](https://www.emmlegal.com/news/recover-stolen-crypto-assets/).
- [CoinDesk, Wasabi blocks US users](https://www.coindesk.com/policy/2024/04/29/wasabi-wallet-developer-blocks-us-citizens-and-residents-after-samourai-wallet-arrests).
- [Wasabi Blog, zkSNACKs coordinator shutdown](https://blog.wasabiwallet.io/zksnacks-is-discontinuing-its-coinjoin-coordination-service-1st-of-june/).
- [Bitcoinist, Chainalysis demix claims](https://bitcoinist.com/can-chainalysis-break-wasabi-wallets-coinjoins/).
- [CoinGeek, Europol on Wasabi](https://coingeek.com/europol-report-on-wasabi-wallet-reveals-law-enforcement-scrutiny/).
- [The Block, THORChain Lazarus laundering](https://www.theblock.co/post/352987/zachxbt-says-bitcoiner-millions-stolen-crypto-frozen-binance).
- [The Record, THORChain $10M+ stolen](https://therecord.media/more-than-10-million-stolen-crypto-platform-thorchain).
- [MIT Technology Review, THORChain founder profile](https://www.technologyreview.com/2026/02/18/1132587/jean-paul-thorbjornsen-dark-side-crypto-permissionless-dream/).
- [FixedFloat AML/KYC policy](https://www.fixedfloat.investments/aml-kyc-policy).
- [FixedFloat Terms of Service](https://ff.io/terms-of-service).
- [Binance, How to Report Stolen Funds](https://www.binance.com/en/support/faq/how-to-report-stolen-funds-transferred-to-binance-360000006051).
- [ICIJ, Coin Laundry investigation](https://www.icij.org/investigations/coin-laundry/cryptocurrency-exchanges-binance-okx-money-laundering-crime/).
- [Bloomberg Law, Enforcing the Crypto Freeze](https://news.bloomberglaw.com/securities-law/insight-enforcing-the-crypto-freeze).

## Legal references

- [18 USC § 981 Civil Forfeiture, LII Cornell](https://www.law.cornell.edu/uscode/text/18/981).
- [18 USC § 982 Criminal Forfeiture, LII Cornell](https://www.law.cornell.edu/uscode/text/18/982).
- [18 USC § 1956 Money Laundering, LII Cornell](https://www.law.cornell.edu/uscode/text/18/1956).
- [Asset Forfeiture Law Money Laundering Forfeiture Statutes PDF](http://assetforfeiturelaw.us/wp-content/uploads/2016/01/mlfft-tlk.pdf).
- [Lexology, How Courts Tackle Procedural Roadblocks in Crypto Asset Litigation](https://www.lexology.com/library/detail.aspx?g=5c173f0c-d9d0-419b-b3dc-6c73a5b4ebf9).
- [Littleton Chambers, English Freezing and Proprietary Injunctions](https://littletonchambers.com/articles-webinars/cryptoassets-obtaining-english-freezing-and-proprietary-injunctions-in-relation-to-cyberfaud/).
- [Crypto Legal UK, How to Report to FBI IC3](https://www.cryptolegal.uk/report-cryptocurrency-fraud-and-hacks-fbi-ic3/).
- [Lawyer Monthly, Can Courts Freeze Stolen Crypto](https://www.lawyer-monthly.com/2026/01/can-courts-freeze-stolen-crypto-injunctions/).

# Source Quality Assessment

**High confidence:** FBI, IC3, DOJ, USSS, IRS-CI primary sources. Wikipedia entries on Bitfinex hack are well sourced. Chainalysis and TRM Labs reports are industry standard and align across firms.

**Medium confidence:** Industry blog posts at TRM Labs, Chainalysis, and Chainabuse have implicit commercial incentive to overstate analytics value. Treat their case statistics as directionally correct but verify specific numbers against primary government press releases where the case is publicly named.

**Lower confidence:** Search engine summaries of recent press are paraphrased. Direct fetches of the IC3 PSA and Chainabuse guides are first hand. Year markers like "2026" in some article URLs may be repackaged or pre dated content. The Bybit recovery statistics evolved across months in 2025 and 2026, so any specific freeze percentage is a snapshot.

**Speculative:** Pre 2024 zkSNACKs coordinator log retention. There is no public reporting that confirms which records still exist. Treating this as a Round 2 question rather than a fact.

# Open Questions for Round 2

1. **Service attribution for 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva.** What does Chainalysis Reactor, TRM Forensics, or Crystal Intelligence label this address as? The 133K+ UTXO, 9933 BTC funded pattern matches a CEX hot wallet, a payment processor, or a high volume gambling operator. Public block explorers do not label it. Need a request to an analytics firm or law enforcement with paid tools.

2. **What civil and criminal forfeiture status applies if William is not a US person?** The seed file does not state William's jurisdiction. If outside the US, parallel reporting to NCA UK, ACSC AU, Action Fraud, the German BKA, or EU Eurojust may be more effective. Need to confirm William's domicile.

3. **Wasabi 2.0 vs Wasabi 1.0 era of the July 2023 mix.** Was the actual coordinator zkSNACKs Wasabi 2.0 (likely) or a custom coordinator built on the Wasabi codebase (possible)? The Midgard route is confirmed, but the exact coordinator that processed the six coinjoins between July 21 and 23, 2023 should be identified for any future subpoena targeting.

4. **Pre shutdown zkSNACKs subpoena viability.** Is there public reporting of any successful subpoena to zkSNACKs Ltd (Gibraltar) for pre June 2024 coordinator data? If yes, that is a possible avenue for the candidate demix lead.

5. **THORChain Midgard evidence preservation.** Midgard data is cached but technically not guaranteed indefinitely. Has any Round 2 query confirmed durable access to the July 2023 transactions and the full input chain for the example tx 0x655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204?

6. **FixedFloat 2024 hack impact.** FixedFloat itself was hacked for $26M in February 2024. Did that hack and the aftermath affect their cooperation posture with US LE compared to the Larsen case in 2024 to 2025? Is FixedFloat still responsive to suspicious activity reports in 2026?

7. **State of the Lazarus Bybit bounty.** Was any of the Wasabi laundered Bybit BTC traced back from peeling chains? If yes, that methodology applies to William's pattern.

8. **Specific law enforcement contacts.** Does the FBI have a Virtual Asset Unit or designated crypto field office for cold cases? Who is the current SAC or designated agent receiving 2 to 4 year old crypto theft files?

9. **Operation Shamrock and Atlantic intake for older cases.** Both operations are pig butchering focused. Can a non scam crypto theft case from 2023 be added to their coalition watchlists?

10. **Chainalysis Beacon Network access.** Beacon is for institutional flaggers. Is there a public flag submission route for victim cases, or must Beacon entries originate from law enforcement and partner exchanges?

# Actionable Takeaways for William, This Week

Ranked by leverage relative to cost.

1. **File or refresh IC3 (free, 30 minutes).** Use the full evidence packet outlined in section 5. Save the complaint number. This is the canonical entry point that connects William's case to multi victim federal investigations.

2. **Email or call the local FBI field office with the IC3 complaint number and a one page summary (free, 1 hour).** High dollar losses get triage attention when bilateral contact happens. Identify the nearest field office, get the cyber agent or virtual asset unit contact, send the packet.

3. **File Chainabuse reports keyed to every address (free, 1 hour).** Report at chainabuse.com against (a) every victim wallet, (b) the Wasabi deposit address, (c) the candidate demix address, (d) the unspent 6.49998534 BTC address, (e) the FixedFloat receiving wallet, (f) the high volume service address. Use one consistent narrative ID across reports. This activates TRM and Beacon Network linkage.

4. **Set up free watchlist alerts on the unspent BTC address (free, 30 minutes).** Tools: Mempool.space alerts, BlockSci, Etherscan style alerts via third party tools, MetaSleuth free tier. Goal is real time notification if 6.49998534 BTC moves.

5. **Submit a suspicious activity report to FixedFloat (free, 1 hour).** Use the AML/KYC contact at fixedfloat.investments/aml-kyc-policy. Cite the Chris Larsen forfeiture precedent. Provide IDs of the named FixedFloat related transactions and ask whether the receiving 0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F wallet is under any current LE request.

6. **Submit a victim notification to Binance, OKX, Kraken, and Coinbase compliance portals (free, 1 hour each).** Even if no funds have hit them yet, the addresses are on the major exchange watchlists if they get added. Use Binance article 360000006051 procedure as the model and adapt to each.

7. **Decide on jurisdiction strategy (free, 30 minutes thinking).** Confirm William's domicile. If US, IC3 + FBI field office + state AG. If UK, Action Fraud + NCA. If EU, country FIU + Europol referral. If AU, ACSC + AFP.

8. **Do not engage paid "recovery" services this week.** Reread the FBI PSA. The only paid engagement worth considering now is a one shot blockchain tracing pass by a recognized analyst with a flat fee. Do not engage anyone who DMs William first or guarantees recovery.

9. **Preserve evidence (free, ongoing).** Save Midgard API responses for every THORChain hop. Save Blockstream pages for every address. Save the prior demix reviewer's report. Keep timestamps. Keep a clean folder structure mirroring the evidence packet sections.

10. **Round 2 scope.** Service attribution for 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva, FBI field office identification with named agent contact, FixedFloat 2026 cooperation posture, and confirmation of the Wasabi coordinator instance.

# Closing Notes

The strongest case for sustained patience comes from Bitfinex: a 5.5 year gap from theft to mass recovery, predicated on a single off chain mistake by the launderer. The strongest case for low expectations comes from Bybit: a state level launderer with proper operational security keeps recovery in the single digit percentage even with $140M in bounties active. William's case sits in between. It is not Lazarus level sophistication, the unspent address is a real lead, FixedFloat is a reachable jurisdiction, and US LE has demonstrated ability to claw funds from FixedFloat in the Larsen case. The decisive variable is whether the launderer eventually touches an identified KYC surface. The work this week is preservation, watchlisting, and getting on the right multi victim federal investigation lists. The work next week and beyond is patience.

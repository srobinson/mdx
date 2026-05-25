---
title: William Stolen Crypto Round 1 Synthesis
type: research
tags: [crypto-theft, bitcoin, wasabi, thorchain, fixedfloat, mcp, law-enforcement, osint]
summary: Consolidated findings from three Round 1 research lanes, with evidence-backed leads and Round 2 gaps.
status: active
confidence: medium
created: 2026-05-25
updated: 2026-05-25
related:
  - william-crypto-recovery-precedents-round1
  - william-crypto-tools-and-leads-round1
  - william-crypto-mcp-tool-discovery-round1
  - stolen-crypto-case-seed-2026-05-25
---

# Summary

Round 1 produced three durable artifacts:

- `/Users/alphab/.mdx/research/william-crypto-recovery-precedents-round1.md`
- `/Users/alphab/.mdx/research/william-crypto-tools-and-leads-round1.md`
- `/Users/alphab/.mdx/research/william-crypto-mcp-tool-discovery-round1.md`

The case is not currently recoverable by private action alone. It is still actionable as a preservation, watchlist, and law-enforcement escalation case because a low-confidence Wasabi demix branch has a currently unspent `6.49998534 BTC` lead at:

```text
bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
```

All claims below inherit the core caveat: the demix candidate is still low confidence. Downstream addresses are investigative leads, not attribution.

# Converged Findings

## 1. The best recovery pattern is downstream custody, not mixer breakage

All lanes converged on the same operating model. Wasabi 2.x cannot be reliably demixed at protocol level with public methods. Real recoveries happen when launderers later touch a KYC surface, a cloud account, an exchange, an instant swap provider, or a custodial wallet.

Relevant examples from Round 1:

- Bitfinex 2016 recovery years later through off-chain mistakes and law enforcement seizure.
- Chris Larsen / LastPass theft where downstream services including FixedFloat appeared in a federal tracing path.
- Ronin and Bybit examples where only a portion froze, usually at Binance, OKX, or similar custodial endpoints.
- Operation Atlantic and Operation Shamrock showing that aggregated reports and analytics partner feeds can surface otherwise isolated victim cases.

## 2. The live BTC watchlist target is the highest immediate lead

The tools lane independently verified:

```text
Address: bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
WalletExplorer wallet_id: 44582d2a68baaaee
Balance: 6.49998534 BTC
Spent: 0 BTC
```

It has two inbound transactions, including a tiny March 11, 2026 dust UTXO. Treat that dust as forensic noise unless Round 2 can identify the dust funder as another tracer or known wallet.

Recommended alert stack:

- Bitwatch Docker with Telegram alerts.
- MetaSleuth address monitoring.
- Optional cryptocurrencyalerting.com email or webhook fallback.
- Optional QuickNode webhook if William is willing to configure a paid or developer account.

## 3. The service-like branch is probably useful but still unlabeled

Address:

```text
17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva
```

Round 1 evidence:

- WalletExplorer wallet id: `0000001bce8b8aa0`
- More than `148,000` transactions in WalletExplorer.
- More than `133,000` funded UTXOs in Blockstream.
- BitcoinWhosWho has one low-quality sextortion report.

Inference: this looks service-like, possibly exchange, payment processor, gambling, or another high-volume custodian. Public labels did not resolve it. Round 2 should focus on labels from Arkham authenticated search, MistTrack, Caudena, GraphSense, Blockchair, BitcoinWhosWho, and general web OSINT.

## 4. FixedFloat is more important than it looked initially

The case seed contains FixedFloat side paths. Round 1 found a relevant precedent: federal tracing in the Chris Larsen case named FixedFloat among downstream services. That does not prove William's path is recoverable, but it shows FixedFloat can appear in formal recovery and forfeiture work.

Round 2 should verify current FixedFloat legal and compliance contacts, record retention posture, and whether a victim preservation request is worth sending before law enforcement process exists.

## 5. The MCP ecosystem has a useful stack, but no turnkey recovery tool

The MCP lane found several credible tool routes:

Install-first stack:

- MistTrack MCP for direct Wasabi, BTC, ETH, and risk-label work.
- Etherscan MCP for victim EVM transactions and FixedFloat side branch.
- mempool.space MCP for BTC UTXO verification and polling.
- THORChain Midgard MCP for ETH to BTC swap evidence.
- DuckDB MCP for a canonical transaction evidence table from the CSV.

High-value commercial follow-ups:

- Caudena Prism MCP for UTXO path confirmation or rejection of the low-confidence demix candidate.
- AnChain AML MCP for sanctions and audit-friendly reporting.
- Bitquery Coinpath MCP for cross-chain money-flow tracing.

Evidence packaging:

- Neo4j MCP for the graph.
- Excalidraw MCP for the one-page evidence diagram.
- OFAC MCP or Tatum OFAC tracker for sanctions screening.

No public MCP discovered in Round 1 can recover funds directly or replace law enforcement process.

# Immediate Action List

1. Set live alerts on `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`.
2. Build the transaction evidence table from the CSV plus BTC and THORChain evidence.
3. File or update IC3 with the consolidated evidence packet.
4. Call or email the local FBI field office after IC3 filing.
5. Submit private Chainabuse reports for the victim wallets, Wasabi deposit, demix candidate, live address, FixedFloat wallet, and service-like address.
6. Submit SlowMist MistTrack victim intake.
7. Prepare a FixedFloat compliance request, but keep any request careful and evidence based.
8. Do not pay recovery firms or anyone who promises direct fund recovery.

# Round 2 Gaps

Round 2 should answer these before we call the research base solid:

1. Can any public or authenticated source label `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva`?
2. Can any public or authenticated source label the live address `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` or its WalletExplorer cluster `44582d2a68baaaee`?
3. Who funded the March 11, 2026 dust UTXO into the live address, and is that funder a known tracer, service, scammer, or noise source?
4. What are the exact current FixedFloat legal, compliance, and victim-contact paths, and what should the message say?
5. Which law enforcement channels are jurisdiction-dependent once William's domicile is known?
6. Can we verify install commands for the top MCP shortlist against current READMEs and avoid stale package names?
7. Can we produce a canonical transaction table schema and first-pass evidence packet outline suitable for IC3, FBI, Chainabuse, and FixedFloat?

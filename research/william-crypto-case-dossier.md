---
title: William Stolen Crypto Case Dossier
type: research
tags: [crypto-theft, bitcoin, ethereum, thorchain, wasabi, fixedfloat, binance, law-enforcement, evidence-packet]
summary: Consolidated case posture, leads, escalation sequence, tooling plan, and evidence packet checklist from two research rounds.
status: active
confidence: medium
created: 2026-05-25
updated: 2026-05-25
related:
  - stolen-crypto-case-seed-2026-05-25
  - william-crypto-recovery-precedents-round1
  - william-crypto-tools-and-leads-round1
  - william-crypto-mcp-tool-discovery-round1
  - william-crypto-round1-synthesis
  - william-crypto-address-attribution-round2
  - william-crypto-evidence-and-escalation-round2
  - william-crypto-mcp-install-plan-round2
---

# Executive Summary

This is still actionable, but only as a preservation, monitoring, and law enforcement case. Private recovery is not realistic unless the funds move to a custodial surface or a paid analytics platform independently validates the low confidence Wasabi demix candidate.

The strongest live lead remains:

```text
bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
```

Verified May 25, 2026:

```text
Balance: 6.49998534 BTC
Spent: 0 BTC
Mempool activity: 0
```

The strongest new Round 2 lead is that:

```text
17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva
```

is probably part of a Binance cluster, based on WalletExplorer cluster membership plus two independent public sources labeling other addresses in the same cluster as Binance. This is not official Binance confirmation. It is strong enough to include as a preservation lead if, and only if, the Wasabi demix branch is validated or law enforcement chooses to pursue it.

# Core Caveat

The path from the original Wasabi deposit to the downstream candidate address is low confidence. Every external report must say this plainly:

```text
The path from the Wasabi coinjoin output to the current watchlist lead is a low confidence investigative lead. I am asking for preservation and lawful tracing support, not claiming final attribution.
```

# Research Artifacts

Round 1:

- `/Users/alphab/.mdx/research/stolen-crypto-case-seed-2026-05-25.md`
- `/Users/alphab/.mdx/research/william-crypto-recovery-precedents-round1.md`
- `/Users/alphab/.mdx/research/william-crypto-tools-and-leads-round1.md`
- `/Users/alphab/.mdx/research/william-crypto-mcp-tool-discovery-round1.md`
- `/Users/alphab/.mdx/research/william-crypto-round1-synthesis.md`

Round 2:

- `/Users/alphab/.mdx/research/william-crypto-address-attribution-round2.md`
- `/Users/alphab/.mdx/research/william-crypto-evidence-and-escalation-round2.md`
- `/Users/alphab/.mdx/research/william-crypto-mcp-install-plan-round2.md`

# Current Leads

## Lead 1: Live BTC UTXO

```text
Address: bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
WalletExplorer cluster: 44582d2a68baaaee
Balance: 6.49998534 BTC
Status: unspent
```

Why it matters:

- It is still on chain.
- It was funded directly from the low confidence demix candidate.
- If it moves to a custodial service, that may become the highest leverage freeze opportunity.

Action:

- Set two independent alerts today.
- Preserve every spend event immediately if it moves.
- Do not dust, message, or interact with the address.

## Lead 2: Probable Binance Branch

```text
Address: 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva
WalletExplorer cluster: 0000001bce8b8aa0
Branch tx: 29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287
Amount: 0.09998037 BTC
Time: 2024-06-22 15:44:45 UTC
```

Evidence:

- WalletExplorer places `17Stn...` in cluster `0000001bce8b8aa0`.
- Coingrab labels another address in that same cluster as Binance.
- A public legal filing labels another address in that same cluster as Binance.

Confidence:

- High for cluster membership.
- Medium high for probable Binance attribution.
- Not official confirmation.

Action:

- If paid analytics validates the Wasabi demix candidate, ask law enforcement to preserve Binance records for this branch.
- Do not ask Binance to disclose customer data directly to William. That requires law enforcement process.

## Lead 3: FixedFloat Side Path

FixedFloat related items from the source CSV:

```text
0xaa49f832a539cabee457ca3fc2e3e47e70ca7e364ba48161aae8c4e788d07b33
0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3
0x91a3d5976df4c7fb6d000a081855b4fc217d61d6e1b71f5c99205e7dc7c2f63f
0x72d855932534ca55ae820f5ed17de8ac729b1f05b093352b5bca19dcf868f26f
0xb5e309a09f479a87f71b1258380d8b8e62c84163364b3b06762927c476c4d655
```

FixedFloat wallet shown in the CSV:

```text
0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F
```

Current official contacts found:

```text
support@fixedfloat.com
compliance@fixedfloat.com
legal@fixedfloat.com
help@fixedfloat.com
```

Action:

- William can send a preservation request to `help@fixedfloat.com`, copying `compliance@fixedfloat.com`.
- Law enforcement should use `legal@fixedfloat.com` for formal process.
- Do not ask FixedFloat to disclose customer data directly to William.

## Lead 4: March 2026 Dust

```text
Dust tx: 4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5
Dust source: bc1q7x6kj7lg9ls2g6s3wm644s5tuqkkg89dp5t532
WalletExplorer cluster: 703a37cbb4f61eae
```

Assessment:

- The dust source looks like a high volume micro dust dispatcher.
- It is not useful attribution.
- Treat it as forensic noise unless a paid analytics platform labels the source as a known tracer, exchange, or investigator.

# Immediate Sequence

## Today

1. Set live alerts on `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`.
2. Create a clean evidence folder with source CSV, artifacts, explorer JSON, and screenshots.
3. Build the transaction CSV using the schema in `william-crypto-evidence-and-escalation-round2.md`.
4. File or update IC3.
5. File a local police report and get a report number.
6. Submit private Chainabuse reports for the victim wallets, Wasabi deposit, demix candidate, live address, FixedFloat wallet, and probable Binance branch.

## This Week

1. Contact the local FBI field office with the IC3 number and the evidence packet.
2. Send the FixedFloat victim preservation request.
3. Submit a SlowMist MistTrack victim intake.
4. Ask a paid analytics operator or law enforcement partner to validate the Wasabi demix candidate.
5. If validation improves, prepare a Binance preservation request for law enforcement.

## If The Live BTC Moves

1. Capture the tx hash, raw transaction JSON, mempool timestamp, outputs, fee rate, and explorer URL.
2. Update IC3 or the field office contact immediately.
3. Notify USSS field office or `CryptoFraud@SecretService.gov` if no FBI contact is active.
4. Update Chainabuse reports.
5. If the output hits a known exchange, ask law enforcement to use that exchange's legal portal immediately.
6. Add every output to the CSV as child rows.
7. If it peels, keep monitoring the change output.
8. If it enters another mixer, preserve the trail and wait for the next exit.

# Evidence Packet

Create three files:

1. `one-page-summary.pdf`
2. `transaction-inventory.csv`
3. `evidence-index.md`

Transaction inventory fields:

```text
row_id
parent_row_id
evidence_type
confidence
confidence_reason
chain
network
asset
token_contract
tx_hash
block_number
block_timestamp_utc
from_address
from_label
to_address
to_label
memo_or_tag
amount_native
amount_usd_at_time
price_source
explorer_url
api_url
source_document
source_file_sha256
service_name
service_order_id
current_status
current_balance_native
last_verified_at_utc
reported_to
report_or_ticket_id
requested_action
response_status
notes
```

Use confidence values:

```text
fact
high_inference
medium_inference
low_inference
```

# Tool Plan

Install first:

```text
DuckDB MCP
mempool.space MCP
Etherscan MCP
Tatum MCP
Direct THORChain Midgard API
```

Important corrections from live install verification:

- Use `@sanlim/mempool-mcp-server`, not `@alexandresanlim/mempool-mcp-server`.
- THORChain Midgard queries worked with uppercase tx hash and no `0x` prefix.
- `@missionsquad/mcp-thorchain` installs, but it hardcodes stale Midgard endpoints. Use direct Midgard API or patch the server before relying on it.
- `@easysolutions906/mcp-ofac` has no npm `bin`; the documented `npx` command fails. Use local install workaround or skip in favor of Tatum, AnChain, or direct OFAC data.
- MistTrack MCP requires a MistTrack API key with OpenAPI access.
- Caudena Prism and AnChain AML are commercial and should wait until the evidence table exists.

Known good Midgard query shape:

```bash
curl -fsS 'https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204'
```

Do not include `0x`.

# Paid Analytics Query Set

Ask any paid operator these questions:

1. Does the tool reproduce `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` as a post mix candidate from the seven Wasabi deposits?
2. What confidence score, candidate set size, and competing candidates does it return?
3. Which heuristic drives the match: amount, timing, pre mix clustering, post mix clustering, common input ownership, or off chain label?
4. Does the tool label `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` or cluster `0000001bce8b8aa0` as Binance?
5. Can the `0.09998037 BTC` branch on June 22, 2024 be mapped to a Binance deposit or hot wallet by legal process?
6. Does the tool label the live address `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`?
7. Does the tool identify the March 2026 dust source as a tracer, spammer, exchange, or unrelated actor?
8. Can it set alerts on the live UTXO and classify the first hop when it moves?

# Recovery Scam Guardrails

Do not engage:

- Anyone who contacts William first.
- Anyone asking for upfront fees, release fees, tax payments, gas fees, wallet unlock fees, or compliance fees.
- Anyone claiming they can freeze or recover funds without law enforcement.
- Anyone asking for seed phrases, private keys, wallet files, remote desktop, or browser extension installs.
- Telegram, WhatsApp, Reddit, or X recovery contacts.
- Fake law firms, fake investigators, or fake government contacts.

Use only official channels:

- `ic3.gov`
- `fbi.gov`
- `secretservice.gov`
- `chainabuse.com`
- `ff.io`
- official exchange support or law enforcement pages

# Decision

There is enough signal to continue:

- The live BTC address is still unspent.
- The service branch now has a probable Binance lead.
- FixedFloat is a plausible preservation target.
- The evidence packet can be made concrete now.

There is not enough signal to claim recovery is likely:

- The Wasabi demix candidate remains low confidence.
- No public label exists for the live address.
- The dust does not establish ownership.
- Freeze or disclosure requires law enforcement or court process.

The next high leverage work is operational: build the evidence table, file the reports, set alerts, and get one real analytics validation of the Wasabi candidate.

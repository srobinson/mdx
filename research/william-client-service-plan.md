# William Stolen Crypto Client Service Plan

Date: 2026-05-25

Status: working client operations plan. This is not legal advice. For subpoenas, freezes, civil recovery, contingency fee enforceability, or communications that may create legal exposure, William should use counsel.

## Executive Position

We can provide William professional legwork in four lanes:

1. Preserve evidence and make the case easy for law enforcement, exchanges, and analytics firms to consume.
2. Monitor the live BTC and suspect clusters so movement is caught quickly.
3. Prepare escalation packets, templates, and transaction inventories so William does not have to think through process.
4. Coordinate paid analytics and law enforcement escalation, while staying inside clear ethical and legal boundaries.

The practical recovery path is narrow. The current best opportunities are:

- The live unspent BTC at `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`, holding `6.49998534 BTC`.
- The probable Binance branch at `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva`, which may become actionable if validated by a paid analytics provider or law enforcement.
- FixedFloat related traces, where victim support and law enforcement preservation channels exist.

## What We Can Do

### Evidence and Documentation

- Build `transaction-inventory.csv` from the source CSV and enriched on-chain data.
- Normalize every transaction into a single schema: chain, txid, timestamp UTC, asset, amount, USD value, from, to, service, evidence URL, confidence, current status, and next action.
- Create an `evidence-index.md` with every source file, screenshot, API response, email, police report number, and hash.
- Create a one-page case summary for FBI, local police, exchange compliance teams, and paid analytics firms.
- Preserve source artifacts with file hashes and timestamps.
- Capture raw API JSON for key addresses, UTXOs, and txids.

### Monitoring

- Set a watch process for:
  - Wasabi deposit address `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`
  - Demix candidate `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`
  - Live BTC address `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`
  - Probable Binance branch `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva`
  - FixedFloat side path and victim EVM wallets from the CSV
- Check mempool activity and confirmed spends on a schedule.
- When movement happens, capture txid, first seen time if available, block status, fee rate, inputs, outputs, screenshots, raw API JSON, and explorer links.
- Alert William immediately with a prewritten escalation note.

### Reporting and Escalation

- Draft and package the IC3 narrative and evidence attachments for William.
- Draft follow-up language for local police and FBI field office.
- Prepare FixedFloat victim support and law enforcement preservation templates.
- Prepare Binance or Binance.US law enforcement packet language, with the correct boundary that account records and freezes generally require law enforcement or legal process.
- Prepare paid analytics inquiry emails asking for a narrow validation of the Wasabi demix candidate and probable Binance attribution.
- Prepare Chainabuse private reports for the addresses and service paths.

### Vendor and Counsel Coordination

- Identify and compare paid blockchain analytics options.
- Draft the analytics scope so William does not pay for vague reports.
- Ask vendors for a concrete deliverable: attribution confidence, cluster evidence, exchange exposure, seizure/freeze actionability, and law enforcement ready exhibits.
- Prepare a counsel intake packet if William wants a lawyer to pursue subpoenas, preservation letters, or civil recovery.

## What We Should Not Do

- No hacking, unauthorized access, credential guessing, phishing, or social engineering.
- No impersonating William, law enforcement, counsel, or an exchange.
- No contacting the thief or scammer directly unless counsel or law enforcement directs it.
- No promises that funds can be recovered.
- No private key or seed phrase handling unless there is a documented, unavoidable reason.
- No public posting of sensitive identifiers before William approves it.
- No overclaiming the Wasabi demix candidate. Treat it as low confidence unless paid analytics validates it.

## William Zero-Thinking Checklist

William should provide:

1. Written authorization for Stuart to organize evidence, contact analytics vendors, draft reports, and prepare exchange or law enforcement packets.
2. Confirmation of the correct incident year. The file name says July 2021, but the transaction evidence points to July 21 to 23, 2023.
3. Government ID and proof of address, held securely, for counsel, police, exchange, or analytics intake only.
4. Proof that he controlled the victim wallets, such as exchange withdrawal records, wallet screenshots, signed messages if safe, or contemporaneous records.
5. All prior reports: IC3, local police, exchange tickets, insurer, attorney, investigator, or analytics vendor.
6. All communications with scammers, exchanges, recovery firms, or investigators.
7. Device compromise details: wallets used, devices, browsers, extensions, seed storage, remote access tools, cloud backups, and suspicious downloads.
8. Consent on public reporting: private Chainabuse only by default, public only if he approves.
9. Budget approval for paid analytics, legal consultation, and any filing expenses.
10. Agreement on success fee terms and expense handling before work proceeds beyond evidence preparation.

## Engagement Structure

Because William is offering 20 percent of recovered funds, the professional version should be written down before any recovery work:

- Scope: evidence preparation, monitoring, escalation support, vendor coordination, and operational project management.
- Success fee: define exactly what counts as recovered funds, when the fee is earned, whether partial freezes count, and whether returned stablecoins, BTC, ETH, or fiat are valued at recovery date.
- Expenses: analytics, counsel, notarization, records, and filing fees require prior written approval.
- Authority: Stuart may draft and organize, but William signs victim declarations and official reports unless counsel instructs otherwise.
- Legal review: counsel should review fee terms and any legal demand letters.
- Termination: either side can end the engagement, with expenses and already earned fees defined.
- Conflicts: disclose any vendor referral fees or relationships.

## Evidence Folder Structure

Recommended folder:

```text
william-stolen-crypto/
  00_admin/
    authorization.pdf
    engagement-scope.md
    client-intake.md
  01_source/
    Stolen Crypto July 2021 - Summary.csv
    source-file-hashes.txt
  02_chain-data/
    btc/
    eth/
    bsc/
    thorchain/
  03_screenshots/
  04_reports/
    ic3/
    police/
    fbi/
    chainabuse/
  05_exchange-packets/
    fixedfloat/
    binance/
  06_vendor-packets/
    paid-analytics/
    counsel/
  07_outbox/
  08_inbox/
  09_worklog/
```

Minimum evidence controls:

- Hash every source file before editing or transforming it.
- Keep raw source files read-only.
- Store every screenshot with URL and timestamp.
- Store every API response used in conclusions.
- Keep a worklog of who did what and when.
- Separate public, private, and attorney-client material.

## First 72 Hours

### Stuart

1. Build `transaction-inventory.csv`.
2. Hash and preserve the CSV and current research files.
3. Capture fresh Blockstream, mempool, THORChain Midgard, Etherscan, and BscScan data for all known targets.
4. Set alerts or scheduled checks for the live BTC and candidate branches.
5. Draft the one-page summary.
6. Draft IC3 narrative text and attachable transaction table.
7. Draft FixedFloat victim support request.
8. Draft paid analytics inquiry.
9. Prepare a 10 minute client call script and missing-info checklist.

### William

1. Confirm incident year.
2. Confirm ownership and provide authorization.
3. Provide all prior report numbers and communications.
4. Confirm whether he has already contacted FixedFloat, Binance, IC3, FBI, local police, any attorney, or any recovery firm.
5. Approve whether Chainabuse reports should be private only.

## Seven Day Plan

- File or update IC3 with the transaction table and exact hashes.
- File or update local police report.
- Ask local police to route the packet to cyber or financial crimes.
- Contact FBI field office with the IC3 number and one-page summary.
- Submit FixedFloat victim support packet and preserve the law enforcement packet separately.
- Submit paid analytics inquiry with a precise validation scope.
- Prepare Binance branch packet only after paid analytics validates the attribution or law enforcement asks for it.
- Keep daily monitoring logs.

## Thirty Day Plan

- Continue address monitoring and evidence updates.
- Escalate to counsel if a service or exchange confirms exposure or if paid analytics identifies a custodial off-ramp.
- Ask law enforcement or counsel to issue preservation or legal process where needed.
- Package all new movements as supplemental IC3 and police updates.
- Reassess paid analytics value if the live BTC remains dormant.

## Source-Backed Process Notes

- FBI guidance says victims should report via IC3 or contact a local FBI field office and include transaction details: wallet addresses, amounts and cryptocurrency type, dates and times, and transaction IDs. Source: https://www.fbi.gov/how-we-can-help-you/victim-services/national-crimes-and-victim-resources/cryptocurrency-investment-fraud
- FBI also warns that recovery services can be scams, especially those charging upfront fees. Source: https://www.fbi.gov/news/stories/2023-cryptocurrency-fraud-report-released
- IC3 complaint forms ask for a narrative, other agencies already contacted, and whether the complaint updates a prior complaint. Source: https://complaint.ic3.gov/
- FixedFloat lists separate contacts for suspended orders, law enforcement requests, and crime victim support: `compliance@fixedfloat.com`, `legal@fixedfloat.com`, and `help@fixedfloat.com`. Source: https://ff.io/de/support
- Binance.US states its law enforcement process is for law enforcement and government agencies, and that requests should include txid, timestamp UTC, amount, and input and output addresses. Source: https://support.binance.us/en/articles/9842980-binance-us-law-enforcement-guide
- Chainabuse lets victims report scams, opt into support, and submit private reports shared only with law enforcement. Source: https://help.chainabuse.com/
- Chainabuse reporting fields include address, scam category, description, chain, reported loss, evidence, compromise indicators, and consent to be contacted by law enforcement. Source: https://docs.chainabuse.com/docs/post-reports-parameters
- Blockstream Esplora documents address summary, transaction history, mempool transactions, and UTXO endpoints. Source: https://github.com/blockstream/esplora/blob/master/API.md
- THORChain Midgard is a read API for THORChain data and exposes transaction/action lookup endpoints. Source: https://docs.thorchain.org/technology/midgard

## Immediate Answer To William

Suggested wording:

> Yes. I cannot promise recovery, and anyone who does is probably selling hope. What I can do is turn this into a professional recovery file: preserve the evidence, create a transaction inventory, monitor the live BTC, prepare the law enforcement and exchange packets, and coordinate a paid analytics review of the Wasabi trail. The best chance is not arguing with the chain. The best chance is catching a validated trail at a service that can freeze or identify an account through legal process.

## Decision

Proceed as a professional evidence and escalation engagement. The next concrete deliverable should be `transaction-inventory.csv`, followed by the one-page case summary and FixedFloat, IC3, FBI, local police, and paid analytics packets.

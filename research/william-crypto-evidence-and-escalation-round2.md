---
title: William Crypto Evidence and Escalation Packet, Round 2
type: research
tags: [crypto-theft, law-enforcement, evidence-packet, fixedfloat, ic3, exchange-compliance]
summary: Practical evidence schema, official reporting links, jurisdiction routing, and message templates for William's stolen crypto case.
status: active
confidence: medium
created: 2026-05-25
updated: 2026-05-25
related:
  - stolen-crypto-case-seed-2026-05-25
  - william-crypto-round1-synthesis
  - william-crypto-recovery-precedents-round1
---

# Executive Summary

William should treat the case as a preservation and escalation matter, not a private recovery matter. The packet should be filed first with IC3, local police, and the local FBI field office, then used to support service specific preservation requests to FixedFloat and law enforcement requests to exchanges if the BTC lead moves.

The strongest live lead remains `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`, verified on May 25, 2026 as holding `6.49998534 BTC` with no mempool movement. The caveat remains material: the path to that address depends on a low confidence Wasabi demix candidate, so every report should label it as an investigative lead rather than attribution.

# Detailed Findings

## 1. Current case status to state in every packet

Facts to state:

* Source file: `/Users/alphab/Downloads/Stolen Crypto July 2021 - Summary.csv`.
* Incident dates in the CSV: July 21 to July 23, 2023. The filename says July 2021, but the records say July 2023.
* Total value at theft time in the CSV: `$1,675,929.20`.
* Assets in the CSV: `884.8222 ETH` and `8.6 BNB`.
* Main path: victim EVM wallets to THORChain, then BTC to Wasabi.
* Side path: multiple ETH transactions listed as FixedFloat related.
* Wasabi deposit address: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`.
* Low confidence demix candidate: `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`.
* Live lead derived from that candidate: `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`.

Live verification run on May 25, 2026 through Blockstream API:

| Address | Funded BTC | Spent BTC | Current BTC | Mempool tx count | Assessment |
|---|---:|---:|---:|---:|---|
| `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` | `6.49998534` | `0` | `6.49998534` | `0` | Current watchlist priority |
| `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` | `40.70902128` | `40.70902128` | `0` | `0` | Historical Wasabi deposit |
| `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` | `47.63611646` | `47.63611646` | `0` | `0` | Low confidence demix candidate |
| `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` | `9933.53285374` | `9933.53285374` | `0` | `0` | High volume service like branch |

Command evidence:

```bash
python3 - <<'PY'
import urllib.request, json
for a in [
  'bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g',
  'bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s',
  'bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl',
  '17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva',
]:
    data=json.load(urllib.request.urlopen(f'https://blockstream.info/api/address/{a}', timeout=20))
    cs=data['chain_stats']; ms=data['mempool_stats']
    funded=cs['funded_txo_sum']+ms['funded_txo_sum']
    spent=cs['spent_txo_sum']+ms['spent_txo_sum']
    print(a, funded/1e8, spent/1e8, (funded-spent)/1e8, ms['tx_count'])
PY
```

## 2. Evidence packet checklist

Create three deliverables:

1. One page PDF summary for law enforcement intake.
2. Transaction CSV or XLSX with one row per on chain event.
3. Evidence folder with source CSV, screenshots, explorer pages, API JSON, emails, and complaint receipts.

Checklist:

| Section | Required contents | Notes |
|---|---|---|
| Victim identity | William's legal name, address, phone, email, domicile, citizenship, attorney if any | Do not publish publicly |
| Report numbers | IC3 number, local police report number, state complaint number, Chainabuse report links, exchange ticket IDs | Fill after filing |
| Incident summary | July 21 to 23, 2023, loss amount, assets, wallet compromise narrative | State facts only |
| Ownership proof | Screenshots or exports showing William controlled the victim wallets, funding records, exchange withdrawal history | Never include seed phrase or private key |
| Transaction inventory | All victim outflows, THORChain swaps, Wasabi deposits, coinjoins, FixedFloat side path, downstream leads | Use UTC timestamps |
| Methodology | Tools used, explorer URLs, APIs, analyst notes, confidence per hop | Separate fact from inference |
| Current lead | Live BTC address balance, last verified time, mempool status, alert configuration | Reverify before filing |
| Service contacts | FixedFloat ticket, exchange portal notes, law enforcement portal URLs | Victim asks for preservation, law enforcement asks for records or freezes |
| Attachments | CSV, graph, screenshots, JSON, source CSV, correspondence | Hash files for integrity |
| Caveats | Wasabi demix candidate is low confidence; no guarantee of recovery | Repeat in every packet |

## 3. Transaction CSV schema

Use these fields. Keep values copyable. Avoid screenshots as the only record.

| Field | Purpose |
|---|---|
| `row_id` | Stable row ID, for example `WIL-EVM-001` |
| `parent_row_id` | Prior row in the trace, if applicable |
| `evidence_type` | `victim_outflow`, `thorchain_in`, `thorchain_out`, `wasabi_deposit`, `coinjoin`, `demix_candidate`, `fixedfloat_side_path`, `service_branch`, `live_lead` |
| `confidence` | `fact`, `high_inference`, `medium_inference`, `low_inference` |
| `confidence_reason` | Why this row is fact or inference |
| `chain` | Ethereum, BNB Chain, Bitcoin, THORChain reference |
| `network` | Mainnet name |
| `asset` | ETH, BNB, BTC, token symbol |
| `token_contract` | Contract address if tokenized asset |
| `tx_hash` | Full transaction hash |
| `block_number` | Block height if known |
| `block_timestamp_utc` | ISO timestamp in UTC |
| `from_address` | Sender address |
| `from_label` | Victim wallet, THORChain router, suspected service, unknown |
| `to_address` | Recipient address |
| `to_label` | THORChain router, FixedFloat wallet, Wasabi deposit, unknown |
| `memo_or_tag` | THORChain memo, destination tag, order memo, if present |
| `amount_native` | Native asset amount, decimal string |
| `amount_usd_at_time` | USD value at event time |
| `price_source` | CoinGecko, CoinMarketCap, CSV value, other |
| `explorer_url` | Etherscan, Blockstream, Midgard, other |
| `api_url` | API endpoint used for verification |
| `source_document` | Source CSV, screenshot name, exported JSON name |
| `source_file_sha256` | Hash of local evidence file |
| `service_name` | FixedFloat, Binance, OKX, Kraken, Coinbase, unknown |
| `service_order_id` | If known |
| `current_status` | `spent`, `unspent`, `frozen`, `unknown` |
| `current_balance_native` | Balance at latest check |
| `last_verified_at_utc` | Verification timestamp |
| `reported_to` | IC3, local police, Chainabuse, FixedFloat, exchange |
| `report_or_ticket_id` | Complaint number or ticket ID |
| `requested_action` | Preserve records, investigate, freeze, identify account, notify victim |
| `response_status` | Submitted, acknowledged, rejected, pending |
| `notes` | Short analyst note |

Minimum rows to include:

* All high value EVM outflows from the source CSV.
* All FixedFloat related EVM transactions listed in the seed file.
* All THORChain in and out records verified through Midgard.
* All seven Wasabi deposits and six coinjoin transactions from the prior demix review.
* Candidate transaction `1962037495cfc6f39cd0c525b78fdcffddb98de34babdcf785b12208152e9bb2`.
* Live lead address `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` and all inbounds.
* Service like branch `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva`.

## 4. One page summary template

```text
Subject: Cryptocurrency theft report and preservation request
Victim: William [last name], [city, state, country], [phone], [email]
Incident date range: July 21 to July 23, 2023
Loss at time of theft: $1,675,929.20, consisting of 884.8222 ETH and 8.6 BNB

Summary:
Between July 21 and July 23, 2023, cryptocurrency was transferred without authorization from EVM wallets I controlled. The source transaction list is attached. The main path moved ETH through THORChain into BTC, then into a Wasabi wallet deposit address. A separate side path appears to involve FixedFloat related wallets or orders.

Main addresses:
Victim EVM wallets: [attach table]
Wasabi deposit: bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s
Low confidence demix candidate: bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl
Current watchlist lead: bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g, verified [date] with 6.49998534 BTC unspent
FixedFloat related wallet from source CSV: 0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F

Important caveat:
The path from the Wasabi coinjoin output to the current watchlist lead is a low confidence investigative lead. I am asking for review, preservation, and lawful tracing support. I am not claiming final attribution.

Requested law enforcement action:
Please review the attached transaction CSV and evidence folder, preserve records where possible, and advise whether a cyber squad, Secret Service Cyber Fraud Task Force, IRS CI, or relevant exchange legal process should be engaged if the live BTC lead moves.

Attached:
1. Transaction CSV.
2. Wallet ownership proof.
3. Explorer/API verification records.
4. THORChain and Wasabi trace notes.
5. FixedFloat transaction subset.
6. Chainabuse and exchange ticket receipts, if filed.
```

## 5. Official reporting and escalation channels

### IC3

Use IC3 as the baseline report. The FBI and IC3 guidance asks crypto victims to provide transaction details: addresses, amount and cryptocurrency type, date and time, and transaction ID or hash. IC3 also asks for scam context, domains, apps, communications, exchanges used, and timeline. IC3 warns that any follow up contact is at the discretion of the receiving agency and that complainants will not be contacted by IC3 directly.

Links:

* IC3 cryptocurrency page: https://www.ic3.gov/CrimeInfo/Cryptocurrency
* IC3 complaint form: https://complaint.ic3.gov/
* FBI crypto victim guidance: https://www.ic3.gov/PSA/2023/psa230824

### FBI field office

After filing IC3, call or email the FBI field office covering William's residence. FBI Cyber says every one of its 56 field offices has specially trained cyber squads, and that IC3 reports are used for investigative and intelligence purposes. The FBI contact page also says online scams, thefts, fraud, phishing, malware, and ransomware should be reported to IC3, and local field offices can be contacted for federal crime tips or threats.

Links:

* FBI contact page: https://www.fbi.gov/contact-us
* FBI field offices: https://www.fbi.gov/contact-us/field-offices
* FBI cyber page: https://www.fbi.gov/investigate/cyber

### US Secret Service

USSS is relevant for cyber enabled financial crime and crypto scam seizures, especially if funds move through exchange or money laundering infrastructure. The field office page says crimes can be reported to local Secret Service field offices and that most field offices have a Cyber Fraud Task Force. A USSS crypto seizure release also lists `CryptoFraud@SecretService.gov` and IC3 as reporting routes for crypto fraud victims, with details such as websites, phone numbers, emails, social profiles, crypto addresses, hashes, and transaction dates.

Links:

* USSS field offices: https://www.secretservice.gov/contact/field-offices/
* USSS crypto fraud seizure page with `CryptoFraud@SecretService.gov`: https://www.secretservice.gov/newsroom/releases/2022/11/court-authorizes-seizure-domains-used-furtherance-cryptocurrency-pig

### IRS Criminal Investigation

IRS CI investigates tax, Bank Secrecy Act, money laundering, cybercrime, and related financial crimes. Route IRS CI through FBI, USSS, a local US Attorney contact, or a formal victim attorney when the case has a clear money laundering, sanctions, darknet, tax, or forfeiture angle. Do not treat IRS CI as the first public intake for a private theft report.

Links:

* IRS CI home: https://www.irs.gov/compliance/criminal-investigation
* IRS CI annual reports: https://www.irs.gov/compliance/criminal-investigation/irs-criminal-investigation-annual-reports
* J5 crypto risk indicators, showing IRS CI focus on crypto layering and money laundering: https://www.irs.gov/compliance/criminal-investigation/j5-issues-notice-to-financial-institutions-about-risk-indicators-tied-to-cryptocurrency-assets

### Chainabuse

Chainabuse is useful for address based reporting, multi victim matching, and law enforcement visibility. Use private reports where public disclosure could tip the attacker or attract scammers. Chainabuse documentation says mandatory report fields for an address are address, scam category, description, and chain. Optional fields include reported loss, screenshots, IP addresses, token ID, scammer contact information, and permission to be contacted by law enforcement or Chainabuse.

Links:

* Report page: https://www.chainabuse.com/report
* Support page: https://help.chainabuse.com/
* Reporting API fields: https://docs.chainabuse.com/docs/post-reports-parameters
* Source of information: https://docs.chainabuse.com/docs/source-of-information
* Law enforcement guidance: https://safety.chainabuse.com/article/contacting-law-enforcement

### FixedFloat

FixedFloat currently publishes separate support channels:

* General support: `support@fixedfloat.com`
* Suspended orders support: `compliance@fixedfloat.com`
* Law enforcement requests: `legal@fixedfloat.com`
* Victim support, crime related: `help@fixedfloat.com`

FixedFloat terms say it can suspend orders linked to criminal activity, can use partner, public source, victim complaint, and law enforcement information to determine links to criminal activity, and can freeze funds for return to victims with law enforcement assistance. Its terms also say user data, including IP addresses, may be transferred to business partners or government authorities at request.

Links:

* FixedFloat support: https://ff.io/support
* FixedFloat terms: https://ff.io/terms-of-service

### Major exchange portals

| Platform | Victim route | Law enforcement route | Practical note |
|---|---|---|---|
| Binance | Binance Support stolen funds article | Binance LERS via Kodex, global signup at `https://app.kodexglobal.com/binance/signup` | Binance says it cannot unilaterally freeze assets without an official freezing order from law enforcement or a court. |
| OKX | Support ticket if victim has an OKX account or confirmed OKX endpoint | Kodex request, emergency fallback `enforcement@okx.com` for authorized officers | OKX requests chronological incident overview, wallet addresses, hashes, amounts, investigation findings, and actions requested. |
| Kraken | Compliance and Legal inquiry form | Same form for compliance/legal/privacy requests | Kraken page is sparse. Ask the investigator to submit through Kraken's legal inquiry form with the evidence packet. |
| Coinbase | Customer support ticket or complaint if customer affected | Kodex portal for criminal subpoenas and official criminal requests, `subpoenas@coinbase.com` for other LE questions | Coinbase directs criminal matters to Kodex and law enforcement only. |

Links:

* Binance stolen funds article: https://www.binance.com/en/support/faq/how-to-report-stolen-funds-transferred-to-binance-360000006051
* Binance law enforcement requests: https://www.binance.com/en/support/law-enforcement
* OKX law enforcement guide: https://www.okx.com/en-gb/help/okx-law-enforcement-request-guide
* Kraken legal inquiry: https://support.kraken.com/articles/how-do-i-submit-a-legal-inquiry
* Coinbase legal matter page: https://help.coinbase.com/en-gb/coinbase/other-topics/legal-policies/who-do-i-contact-for-a-subpoena-request-or-dispute-or-to-send-a-legal-document

### State, regulatory, and civil routes

William's jurisdiction is unknown. Use this decision tree after domicile is confirmed:

1. If William is in the United States, file IC3, local police, local FBI field office, and Chainabuse first.
2. If William is in California, also submit to California DFPI. DFPI accepts crypto complaints and maintains a crypto scam tracker based on consumer complaints.
3. If William is in New York, also submit to the New York Attorney General. NY OAG states that it is the state securities and commodities regulator for New York, including cryptocurrency, and has recent crypto freezing actions.
4. If another US state, file with that state attorney general consumer protection office and the state securities regulator. Include the IC3 number and transaction CSV.
5. If outside the United States, file with local police and the national cybercrime or financial crime agency. Still file IC3 if there is a US nexus: US victim, US exchange, US infrastructure, US dollar stablecoin, US based service, or US law enforcement prior seizure page match.
6. If a named exchange endpoint appears, ask law enforcement to submit official process through that exchange's law enforcement portal.
7. If the live BTC moves to a stablecoin issuer controlled token or a custodial exchange, the case becomes time sensitive. Escalate immediately to the field office, USSS CFTF, and the relevant exchange or issuer through law enforcement.

Links:

* California DFPI crypto page: https://dfpi.ca.gov/consumers/crypto/
* California DFPI crypto scam tracker: https://dfpi.ca.gov/consumers/crypto/crypto-scam-tracker/
* New York OAG cryptocurrency page: https://ag.ny.gov/resources/individuals/investing-finance/cryptocurrency
* New York OAG 2025 crypto freeze example: https://ag.ny.gov/press-release/2025/attorney-general-james-freezes-300000-cryptocurrency-linked-scammers-targeting
* FTC ReportFraud: https://reportfraud.ftc.gov/
* FTC recovery scam guidance: https://consumer.ftc.gov/articles/refund-and-recovery-scams
* SEC tip or complaint: https://www.sec.gov/tcr
* CFTC complaint: https://www.cftc.gov/complaint

## 6. FixedFloat message template

Send to `help@fixedfloat.com`. Copy `compliance@fixedfloat.com`. Do not send to `legal@fixedfloat.com` unless law enforcement is sending, or unless the message clearly says it is a victim notice and asks where law enforcement should direct process.

```text
Subject: Crime victim preservation request, suspected stolen funds involving FixedFloat addresses, July 2023

FixedFloat team,

I am the victim of a cryptocurrency theft that occurred between July 21 and July 23, 2023. I am preparing reports for IC3, local law enforcement, and the FBI field office. My source transaction file includes several transactions and destination addresses that appear to involve FixedFloat related activity.

I am not asking you to disclose customer data to me. I am asking you to preserve records and tell me what information you need from law enforcement so the appropriate agency can submit a formal request through your law enforcement channel.

Known FixedFloat related details from my source file:

FixedFloat wallet shown in the source CSV:
0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F

FixedFloat related transaction hashes:
0xaa49f832a539cabee457ca3fc2e3e47e70ca7e364ba48161aae8c4e788d07b33
0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3
0x91a3d5976df4c7fb6d000a081855b4fc217d61d6e1b71f5c99205e7dc7c2f63f
0x72d855932534ca55ae820f5ed17de8ac729b1f05b093352b5bca19dcf868f26f
0xb5e309a09f479a87f71b1258380d8b8e62c84163364b3b06762927c476c4d655

Other destination wallets listed near those transactions:
0xbdC4b2D85d9DCC42C3799b4569bd1D7D25D29C03
0x4EC986035B635D09474fC390AcDF5c107DDa4c70
0x09066E7857D3a9a53c9142f8a7eFFcBc7989F1B5

Requested action:
1. Preserve order records, deposit addresses, payout addresses, account emails if any, IP logs, support chats, API metadata, KYC or source of funds documents if any, partner routing records, and blockchain analytics alerts connected to the listed transactions and addresses.
2. Confirm the correct law enforcement contact path and required format for formal requests.
3. Flag any associated orders or addresses so future inbound funds from the same cluster can be reviewed.
4. Provide a ticket or preservation reference number I can give to law enforcement.

Caveat:
The broader BTC path includes a Wasabi demix lead that is low confidence. The FixedFloat related records above are from the original source transaction file and should be evaluated independently.

I can provide the full transaction CSV, explorer links, and complaint numbers once filed. Please do not send personal customer information to me. Please preserve records and direct formal disclosures to law enforcement.

William [last name]
[phone]
[email]
[IC3 number, once filed]
[local police report number, once filed]
```

Law enforcement should send, not William:

* Official preservation letter, subpoena, search warrant, court order, freezing order, or emergency data request.
* Request for customer identity, IP logs, order metadata, payout addresses, partner records, and support communications.
* Instruction to freeze, return, or hold funds.
* MLAT or other cross border legal process, if required.

## 7. IC3 narrative template

```text
I am reporting a cryptocurrency theft from wallets I controlled. The unauthorized transfers occurred between July 21 and July 23, 2023. My source records show a total loss at the time of theft of approximately $1,675,929.20, consisting of 884.8222 ETH and 8.6 BNB.

The attached transaction CSV lists the victim wallets, transaction hashes, timestamps, assets, amounts, recipient addresses, explorer links, and supporting notes. The main path appears to move ETH from my wallets into THORChain router transactions, then out as BTC to the Wasabi deposit address bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s. A separate side path in the source records appears to involve FixedFloat related wallets or orders, including 0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F.

A prior tracing review identified a low confidence Wasabi demix candidate, bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl. Downstream from that candidate, the address bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g currently holds 6.49998534 BTC and was verified as unspent on [date]. I understand this is an investigative lead, not final attribution.

I am asking law enforcement to preserve and review the evidence, determine whether any exchange or service records can identify the current holder or downstream cash out path, and help issue official process if the live BTC address moves to a custodial service. I am not seeking direct contact with any suspect. I have not shared private keys or seed phrases with anyone.

Relevant records attached:
1. Transaction CSV with all known source outflows and downstream leads.
2. Wallet ownership evidence.
3. Explorer and API verification records.
4. THORChain and BTC tracing notes.
5. FixedFloat related transaction subset.
6. Current watchlist status for bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g.
```

## 8. FBI field office email template

```text
Subject: IC3 complaint [number], $1.67M cryptocurrency theft, live BTC preservation lead

Cyber intake team,

I filed IC3 complaint [number] regarding a cryptocurrency theft that occurred between July 21 and July 23, 2023. The loss at the time of theft was approximately $1,675,929.20, consisting primarily of ETH moved through THORChain into BTC and then Wasabi. My evidence packet is attached.

I am requesting field office review because there is a current BTC watchlist lead:

Address: bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
Current balance: 6.49998534 BTC
Last verified: [date and time UTC]
Status: unspent, no mempool activity at last check
Caveat: low confidence lead derived from a Wasabi demix candidate, not final attribution

The case also includes FixedFloat related transactions in the original source file. I have prepared a victim preservation request for FixedFloat and can provide it after filing or at your direction. I understand that customer records or freezes require law enforcement process.

Could your office advise whether this should be routed to a cyber squad, Secret Service Cyber Fraud Task Force, IRS Criminal Investigation, or another federal partner? If the live BTC address moves, I would like to know the fastest way to update an agent or intake channel so official preservation or freeze requests can be sent to any identified custodial endpoint.

Attached:
1. One page summary.
2. Transaction CSV.
3. Evidence folder index.
4. Current Blockstream verification output.
5. FixedFloat subset.
6. Prior tracing caveat and methodology.

William [last name]
[phone]
[email]
[city, state, country]
```

## 9. What to do before and after the live BTC address moves

Before movement:

1. Set at least two independent alerts on `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`.
2. Reverify balance and mempool status daily while escalation is active.
3. File IC3, local police, Chainabuse private reports, and the FBI field office packet now.
4. Prewrite exchange rapid response packets for Binance, OKX, Kraken, Coinbase, and FixedFloat.
5. Hash the evidence folder and keep a read only backup.
6. Do not dust the address, send OP_RETURN messages, airdrop NFTs, or contact any suspected holder.
7. Do not post the full loss narrative publicly.

At the moment of movement:

1. Capture transaction hash, mempool timestamp, fee rate, input and output addresses, explorer URL, and raw transaction JSON.
2. Notify FBI field office contact and local police with the IC3 number.
3. Notify USSS field office or `CryptoFraud@SecretService.gov` if no field contact exists.
4. Update Chainabuse private reports.
5. Trace the first hop quickly. If it lands at a known exchange or stablecoin issuer controlled asset, ask law enforcement to use that platform's portal immediately.
6. Preserve screenshots and API JSON before confirmations and after confirmation.

After movement:

1. Add all outputs to the CSV as new child rows.
2. Do not overstate attribution if the funds fan out or enter another mixer.
3. If a custodial endpoint is identified, provide law enforcement a one page exchange packet: platform, deposit address, transaction hash, timestamp UTC, amount, trace from victim, requested freeze, and complaint numbers.
4. If the movement is a peel chain, keep monitoring every change output.
5. If the movement is a coinjoin or mixer, preserve the trail and wait for downstream exit points.

## 10. Recovery scams to avoid

Avoid:

* Anyone who contacts William first and offers recovery.
* Anyone requesting an upfront fee, release fee, tax, gas fee, compliance fee, wallet unlock fee, or insurance payment.
* Anyone claiming to be FBI, IC3, IRS, CFTC, FTC, USSS, Binance, Coinbase, Chainalysis, Chainabuse, FixedFloat, or TRM through a private DM, Telegram, WhatsApp, or unofficial email.
* Anyone asking for a seed phrase, private key, wallet file, remote desktop, browser extension install, or screen share.
* Anyone claiming they can directly freeze or recover funds without law enforcement.
* Fake Chainabuse, FixedFloat, Coinbase, Binance, or law firm domains from search ads.
* Recovery firms using unverifiable testimonials, copied logos, hidden owners, or pressure tactics.
* Forum comments and Hacker News or Reddit spam that posts a Gmail or Telegram recovery contact.

Use only official domains and known contact pages:

* `.gov` domains for US agencies.
* `ff.io/support` for FixedFloat.
* `chainabuse.com/report` for Chainabuse.
* Exchange support or law enforcement pages from the exchange domain.

The FTC warns that recovery scams target prior victims, that government agencies and legitimate organizations do not ask for money to help recover funds, and that upfront recovery fees are a scam signal. Chainabuse similarly warns that only law enforcement can issue a freeze order.

# Sources Consulted

## Primary government and regulator sources

* FBI contact page: https://www.fbi.gov/contact-us
* FBI Cyber: https://www.fbi.gov/investigate/cyber
* FBI field offices: https://www.fbi.gov/contact-us/field-offices
* IC3 cryptocurrency page: https://www.ic3.gov/CrimeInfo/Cryptocurrency
* IC3 complaint form: https://complaint.ic3.gov/
* FBI crypto victim guidance: https://www.ic3.gov/PSA/2023/psa230824
* USSS field offices: https://www.secretservice.gov/contact/field-offices/
* USSS crypto fraud seizure page: https://www.secretservice.gov/newsroom/releases/2022/11/court-authorizes-seizure-domains-used-furtherance-cryptocurrency-pig
* IRS Criminal Investigation: https://www.irs.gov/compliance/criminal-investigation
* IRS CI annual reports: https://www.irs.gov/compliance/criminal-investigation/irs-criminal-investigation-annual-reports
* J5 crypto risk indicators: https://www.irs.gov/compliance/criminal-investigation/j5-issues-notice-to-financial-institutions-about-risk-indicators-tied-to-cryptocurrency-assets
* FTC ReportFraud: https://reportfraud.ftc.gov/
* FTC recovery scam guidance: https://consumer.ftc.gov/articles/refund-and-recovery-scams
* SEC tip or complaint: https://www.sec.gov/tcr
* CFTC complaint: https://www.cftc.gov/complaint
* California DFPI crypto page: https://dfpi.ca.gov/consumers/crypto/
* California DFPI crypto scam tracker: https://dfpi.ca.gov/consumers/crypto/crypto-scam-tracker/
* New York OAG cryptocurrency page: https://ag.ny.gov/resources/individuals/investing-finance/cryptocurrency
* New York OAG crypto freeze example: https://ag.ny.gov/press-release/2025/attorney-general-james-freezes-300000-cryptocurrency-linked-scammers-targeting

## Exchange and service sources

* FixedFloat support: https://ff.io/support
* FixedFloat terms: https://ff.io/terms-of-service
* Binance stolen funds: https://www.binance.com/en/support/faq/how-to-report-stolen-funds-transferred-to-binance-360000006051
* Binance law enforcement: https://www.binance.com/en/support/law-enforcement
* OKX law enforcement: https://www.okx.com/en-gb/help/okx-law-enforcement-request-guide
* Kraken legal inquiry: https://support.kraken.com/articles/how-do-i-submit-a-legal-inquiry
* Coinbase legal matters: https://help.coinbase.com/en-gb/coinbase/other-topics/legal-policies/who-do-i-contact-for-a-subpoena-request-or-dispute-or-to-send-a-legal-document
* Coinbase phishing and scam guidance: https://help.coinbase.com/en/coinbase/privacy-and-security/avoiding-phishing-and-scams/avoiding-cryptocurrency-scams/phishing

## Chainabuse and industry reporting sources

* Chainabuse report page: https://www.chainabuse.com/report
* Chainabuse support: https://help.chainabuse.com/
* Chainabuse reporting fields: https://docs.chainabuse.com/docs/post-reports-parameters
* Chainabuse source of information: https://docs.chainabuse.com/docs/source-of-information
* Chainabuse law enforcement guidance: https://safety.chainabuse.com/article/contacting-law-enforcement
* Chainabuse investigative scam warning: https://safety.chainabuse.com/article/be-aware-of-investigative-scams-scams-of-scams

## Case files and local evidence

* `/Users/alphab/.mdx/research/stolen-crypto-case-seed-2026-05-25.md`
* `/Users/alphab/.mdx/research/william-crypto-round1-synthesis.md`
* `/Users/alphab/.mdx/research/william-crypto-recovery-precedents-round1.md`
* `/Users/alphab/Downloads/Stolen Crypto July 2021 - Summary.csv`
* Blockstream API live checks on May 25, 2026.

## Community and low weight checks

* Reddit `r/CryptoScams` current and historical threads on IC3, local police, Chainabuse, and recovery scam warnings.
* Reddit `r/CryptoCurrency` historical FixedFloat discussions. These are anecdotal and not used for official contact facts.
* Hacker News search for recovery firms. Results were mostly spam or low quality, useful only as a warning pattern.
* X search for FixedFloat and law enforcement contacts did not produce higher quality information than the official FixedFloat support page.

# Source Quality Assessment

Confidence is medium. Official contact and portal facts are high confidence because they come from government, exchange, or service pages accessed on May 25, 2026. The live BTC balance facts are high confidence for current public chain state because they were checked through Blockstream API during this round.

The legal effectiveness of any channel is medium to low confidence because it depends on William's jurisdiction, law enforcement interest, exchange endpoint identification, and whether the live BTC lead ever moves to a cooperative custodial surface. Community sources were consulted only for scam pattern checks and were not used as authority for official procedures.

# Open Questions

1. William's domicile, citizenship, and state or country of residence.
2. Whether William already filed IC3, local police, Chainabuse, or exchange reports.
3. Whether William can prove ownership of all victim EVM wallets without exposing private keys or seed phrases.
4. Whether the FixedFloat related entries have order IDs, support emails, IP logs, or payout addresses not visible in the source CSV.
5. Whether an authenticated analytics platform can raise or lower confidence in the Wasabi demix candidate.
6. Which field office, USSS CFTF, or state regulator will actually accept the case once jurisdiction is known.

# Actionable Takeaways

1. Build the transaction CSV using the schema above.
2. Generate the one page summary and evidence folder index.
3. File or update IC3 and preserve the complaint number.
4. File a local police report and ask for a report number, even if they cannot investigate deeply.
5. Contact the FBI field office covering William's residence with the IC3 number and evidence packet.
6. Submit private Chainabuse reports for victim wallets, the Wasabi deposit, the low confidence demix candidate, the live BTC lead, the FixedFloat wallet, and the service like branch.
7. Send the FixedFloat victim preservation message to `help@fixedfloat.com`, copying `compliance@fixedfloat.com`.
8. Set alerts on the live BTC lead. Reverify daily while active.
9. If the live BTC moves, capture the transaction immediately and escalate through FBI, USSS, and any identified exchange law enforcement portal.
10. Do not pay any recovery firm and do not share seed phrases, private keys, wallet files, or remote access.

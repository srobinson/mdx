---
title: William Escalation Packet and Communications Templates
type: research
tags: [crypto-theft, evidence-packet, law-enforcement, fixedfloat, binance, ic3, chainabuse, misttrack]
summary: Usable escalation packet, recipient routing table, preservation boundaries, CSV schema, message templates, and client call script for William's stolen crypto case.
status: active
confidence: medium
created: 2026-05-25
updated: 2026-05-25
related:
  - william-crypto-case-dossier
  - william-crypto-evidence-and-escalation-round2
---

# Executive Summary

William should move this case through official reporting, preservation, and evidence channels before any public or commercial recovery effort. The packet below is built for immediate use: IC3, local police, FBI field office, Secret Service, Chainabuse, FixedFloat, Binance, paid analytics, and counsel.

The live BTC lead was rechecked on May 25, 2026 at 13:18:56 UTC through Blockstream. Address `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` still showed `6.49998534 BTC`, zero spent outputs, and zero mempool transactions. The Wasabi demix path remains low confidence, so all outreach must label the live BTC address as a lead, not as proven stolen funds.

# Detailed Findings

## 1. Case posture to state consistently

Use the same position in every report and email:

* Victim: William `[full legal name]`, `[domicile]`, `[phone]`, `[email]`.
* Incident window: July 21 to July 23, 2023, based on the source CSV.
* Loss: source CSV shows total value of `$1,675,929.20`, total ETH of `884.8222`, and total BNB of `8.6`.
* Source wallets: ten EVM wallets listed in the source CSV.
* Primary route: stolen ETH moved through THORChain transactions, then into BTC, then into Wasabi.
* Wasabi deposit address: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`.
* Low confidence demix candidate: `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`.
* Current watchlist lead: `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`.
* Current watchlist verification: Blockstream API on May 25, 2026 at 13:18:56 UTC showed two unspent outputs totaling `649998534` sats, equal to `6.49998534 BTC`, with zero mempool transactions.
* FixedFloat side path: source CSV lists a FixedFloat related wallet, `0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F`, plus related EVM transaction hashes.
* Probable Binance branch: dossier identifies `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` and branch tx `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287` as a probable Binance branch, based on public cluster attribution. Treat this as unconfirmed until paid analytics, law enforcement, or Binance validates it.

## 2. Exact packet inventory

Create a folder named:

```text
William_Crypto_Theft_Escalation_Packet_2026-05-25/
```

Use these files and subfolders:

| File or folder | Required contents | Notes |
|---|---|---|
| `00_one_page_summary.pdf` | Victim identity, incident timeline, loss amount, top addresses, top txids, current lead, caveats, report numbers | Keep to one page. Use UTC timestamps. |
| `01_transaction_inventory.csv` | One row per on chain event using the schema below | Attach to every official report. |
| `02_evidence_index.pdf` | File list, source, collection date, collector, hash if available, notes | This is the table of contents for evidence. |
| `03_incident_narrative.pdf` | Plain English narrative from William, signed and dated | Do not speculate beyond evidence. |
| `04_victim_identity_and_authorization.pdf` | William ID copy if counsel approves, proof of address, signed authorization naming Stuart and counsel if used | Share ID only through official portals or counsel. |
| `05_wallet_ownership_proof/` | Wallet UI screenshots, exchange withdrawal exports, address book screenshots, signed wallet messages if counsel approves | Never include seed phrases or private keys. |
| `06_source_csv/` | Original CSV and a normalized copy | Preserve original filename and metadata. |
| `07_explorer_screenshots/` | Etherscan, BscScan, Blockstream, THORChain, WalletExplorer or paid analytics screenshots | Capture full URL, timestamp, and address bar. |
| `08_raw_blockchain_data/` | Explorer API JSON, transaction raw JSON, block data, address state JSON | Include Blockstream address, UTXO, and mempool JSON for the live lead. |
| `09_fixedfloat_subset/` | FixedFloat related tx list, wallet references, draft email, ticket receipts | Keep independent from the Wasabi demix lead. |
| `10_binance_subset/` | Probable Binance branch trace, paid analytics validation when available, Binance support ticket, law enforcement LERS notes | Label as probable until validated. |
| `11_reporting_receipts/` | IC3 receipt, police report, FBI field office correspondence, USSS notes, FTC receipt, Chainabuse report links, SlowMist case number | Add new receipts immediately. |
| `12_preservation_requests/` | Sent emails, headers, attachments list, ticket IDs, law enforcement process notes | Preserve exact send time and recipient list. |
| `13_client_call_notes/` | Call script, William signoff, missing items list | Use the script below. |

## 3. One page summary template

```text
Subject: William [last name] cryptocurrency theft, July 2023, evidence and preservation packet

Victim
William [full legal name]
Domicile: [city, state, country]
Phone: [phone]
Email: [email]
Counsel: [name, firm, email, phone, if any]
Authorized coordinator: Stuart [details], if William signs authorization

Incident
Between July 21 and July 23, 2023, cryptocurrency moved without authorization from EVM wallets controlled by William. The source CSV lists a total loss of $1,675,929.20, including 884.8222 ETH and 8.6 BNB. Most value moved through THORChain into BTC and then into Wasabi. A side path in the source CSV appears FixedFloat related.

Main known addresses
Wasabi deposit: bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s
Low confidence demix candidate: bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl
Current watchlist lead: bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
FixedFloat related wallet from source CSV: 0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F
Probable Binance branch address: 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva

Current watchlist verification
On May 25, 2026 at 13:18:56 UTC, Blockstream API showed address bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g with 6.49998534 BTC, zero spent outputs, and zero mempool transactions. UTXOs were:
1. 164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187:0, 6.49998240 BTC
2. 4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5:0, 0.00000294 BTC

Important caveat
The path from the Wasabi deposit to the current watchlist lead depends on a low confidence demix candidate. Please treat the live BTC address as an investigative lead requiring validation, not as proven stolen funds.

Request
Please preserve records, review the attached transaction inventory, advise the correct law enforcement or legal process route, and prioritize rapid escalation if the live BTC lead moves to a custodial service or exchange.
```

## 4. Legal and process boundary

Keep this boundary visible in every service request:

* William and Stuart can notify services, provide evidence, ask for records to be preserved, ask for risk flags, and ask where law enforcement should send formal process.
* William and Stuart should not ask services to disclose customer identity, KYC, IP logs, support communications, internal analytics, or account records directly to them.
* Binance's public stolen funds article says Binance needs an official freezing order from law enforcement or a court before it can unilaterally freeze a user asset. Binance also says confidential law enforcement information will not be shared with the victim.
* Binance's law enforcement page routes government and law enforcement agencies to its LERS portal through Kodex. It also has an exigent case type for urgent requests.
* FixedFloat publishes `help@fixedfloat.com` for crime victim support, `compliance@fixedfloat.com` for suspended order support, and `legal@fixedfloat.com` for law enforcement requests. Its terms say it may freeze funds linked to criminal activity based on public sources, business partners, victim complaints, and law enforcement requests, with return to victims assisted by law enforcement.
* Under 18 U.S.C. 2703(f), the statutory preservation duty is triggered by a governmental entity request and generally preserves records for 90 days, extendable for another 90 days by renewed governmental request. A victim preservation request is useful notice, but law enforcement or counsel must carry formal preservation and disclosure process where the law requires it.
* Chainabuse guidance aligns with this boundary: freezing orders come from law enforcement, and private investigators who claim they can issue freezes are a scam risk.

## 5. Recipient routing table

| Recipient | Portal or contact | Purpose | Attach | Sender |
|---|---|---|---|---|
| IC3 | `https://complaint.ic3.gov/` | Baseline federal cybercrime report | One page summary, transaction CSV, incident narrative, top screenshots | William, or counsel with William's signed authority |
| Local police | Local police department for William's domicile | Police report number, detective assignment, formal victim report | One page summary, transaction CSV, incident narrative, ID if required | William |
| FBI field office | `https://www.fbi.gov/contact-us/field-offices` | Follow up after IC3 and request cyber squad routing | IC3 number, one page summary, transaction CSV, live lead status | William or counsel |
| U.S. Secret Service | Nearest field office at `https://www.secretservice.gov/contact/field-offices/`; if crypto investment fraud nexus, `CryptoFraud@SecretService.gov` | Cyber enabled financial crime and CFTF routing | IC3 number, one page summary, transaction CSV, exchange lead summary | William, counsel, or law enforcement |
| FTC | `https://reportfraud.ftc.gov/` | Consumer fraud record and recovery scam guardrail | Narrative and loss summary | William |
| Chainabuse | `https://chainabuse.com/report` | Private reports for malicious addresses and law enforcement visibility | Address list, descriptions, screenshots, report loss, opt in to law enforcement contact if William agrees | Stuart can prepare, William submits or approves |
| FixedFloat victim support | To `help@fixedfloat.com`; copy `compliance@fixedfloat.com` | Victim preservation notice for FixedFloat side path | FixedFloat subset, source CSV excerpt, police or IC3 numbers when available | William or counsel |
| FixedFloat legal | `legal@fixedfloat.com` | Formal law enforcement process | Legal process, preservation letter, court order, subpoena, or freeze request | Law enforcement or counsel where permitted |
| Binance Support | Binance Support through the stolen funds article | Victim report and ticket for probable Binance branch | One page summary, transaction CSV subset, police report, clickable tx links | William or counsel |
| Binance LERS | `https://app.kodexglobal.com/binance/signup` via Binance law enforcement page | Government request, preservation, records, freeze order if legally supported | Legal process package, transaction CSV, trace memo | Law enforcement only |
| SlowMist case evaluation | `https://aml.slowmist.com/recovery-funds.html` | Free case evaluation and potential tracking support | Stolen address, hacker address, amount, narrative | William or Stuart with signed authority |
| MistTrack product support | `Support@MistTrack.io` | Monitoring and paid product inquiry | Watchlist address, required networks, alert recipients | Stuart or William |
| Paid analytics vendor | Chainalysis, TRM, Elliptic, MistTrack, or qualified forensic firm | Validate Wasabi demix, Binance branch, and live lead | Sanitized transaction CSV, known caveats, statement of work request | Stuart, William, or counsel |
| Counsel | Crypto asset recovery or cybercrime attorney | Legal process strategy, subpoenas, preservation, evidence handling | Full packet, authorization, report numbers | William |

## 6. Transaction inventory CSV schema

Required CSV header:

```csv
case_id,row_id,evidence_type,confidence,chain,asset,token_contract,tx_hash,explorer_url,block_height,timestamp_utc,timestamp_source,from_address,from_label,to_address,to_label,amount_native,amount_usd_at_theft,usd_pricing_source,service_name,service_contact,source_file,screenshot_file,raw_json_file,ownership_proof_ref,reported_to,report_id,preservation_target,legal_process_status,notes
```

Allowed `evidence_type` values:

```text
victim_outflow, thorchain_in, thorchain_out, wasabi_deposit, coinjoin, demix_candidate, fixedfloat_side_path, service_branch, live_lead, dust, report_receipt, preservation_request
```

Allowed `confidence` values:

```text
source_csv, explorer_verified, paid_analytics_needed, probable_service, law_enforcement_validated, service_confirmed, low_confidence
```

Example rows for CSV production:

```csv
case_id,row_id,evidence_type,confidence,chain,asset,token_contract,tx_hash,explorer_url,block_height,timestamp_utc,timestamp_source,from_address,from_label,to_address,to_label,amount_native,amount_usd_at_theft,usd_pricing_source,service_name,service_contact,source_file,screenshot_file,raw_json_file,ownership_proof_ref,reported_to,report_id,preservation_target,legal_process_status,notes
william-2023-theft,1,victim_outflow,source_csv,ethereum,ETH,,0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204,https://etherscan.io/tx/0x655a2a55bc724718bca78b7645347f448d1ca52b9f051AC3B6B8F2E36651D204,,2023-07-21T10:00:59Z,source_csv_unverified_timezone,0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0,William wallet,0xD37BbE5744D730a1d98d8DC97c42F0Ca46aD7146,THORChain router,125.4472,237313.39,source_csv,THORChain,,Stolen Crypto July 2021 - Summary.csv,,,,,,,,Main high value ETH outflow to THORChain router. Verify timestamp against Etherscan before final filing.
william-2023-theft,2,fixedfloat_side_path,source_csv,ethereum,ETH,,0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3,https://etherscan.io/tx/0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3,,2023-07-21T19:15:47Z,source_csv_fixedfloat_section,0xa30E54Cb3593c6afCA653621C4D3Ee2105F015aa,William wallet,0xbdC4b2D85d9DCC42C3799b4569bd1D7D25D29C03,FixedFloat related destination,3.88,,source_csv,FixedFloat,help@fixedfloat.com,Stolen Crypto July 2021 - Summary.csv,,,,,FixedFloat,preserve_records,victim notice target; service wallet reference 0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F
william-2023-theft,3,fixedfloat_side_path,source_csv,ethereum,ETH,,0x91a3d5976df4c7fb6d000a081855b4fc217d61d6e1b71f5c99205e7dc7c2f63f,https://etherscan.io/tx/0x91a3d5976df4c7fb6d000a081855b4fc217d61d6e1b71f5c99205e7dc7c2f63f,,2023-07-21T14:06:00Z,source_csv_fixedfloat_section,0x055e6b081F175dB1170350Ba4f23E3a8E0895492,William wallet,0x4EC986035B635D09474fC390AcDF5c107DDa4c70,FixedFloat related destination,2.84,5372.54,source_csv,FixedFloat,help@fixedfloat.com,Stolen Crypto July 2021 - Summary.csv,,,,,FixedFloat,preserve_records,FixedFloat subset.
william-2023-theft,4,fixedfloat_side_path,source_csv,ethereum,ETH,,0x72d855932534ca55ae820f5ed17de8ac729b1f05b093352b5bca19dcf868f26f,https://etherscan.io/tx/0x72d855932534ca55ae820f5ed17de8ac729b1f05b093352b5bca19dcf868f26f,,2023-07-21T18:55:47Z,source_csv_fixedfloat_section,0x2656269BB878cA0c4250A0DF4C15A9CFca0C21AC,William wallet,0x09066E7857D3a9a53c9142f8a7eFFcBc7989F1B5,FixedFloat related destination,3.89,7358.87,source_csv,FixedFloat,help@fixedfloat.com,Stolen Crypto July 2021 - Summary.csv,,,,,FixedFloat,preserve_records,FixedFloat subset.
william-2023-theft,5,fixedfloat_side_path,source_csv,ethereum,ETH,,0xb5e309a09f479a87f71b1258380d8b8e62c84163364b3b06762927c476c4d655,https://etherscan.io/tx/0xb5e309a09f479a87f71b1258380d8b8e62c84163364b3b06762927c476c4d655,,2023-07-22T09:52:11Z,source_csv_fixedfloat_section,0x1c0b5b8D36587d0516839df7EbFB49AD8F3c543c,William wallet,0x1c0b5b8D36587d0516839df7EbFB49AD8F3c543c,source CSV destination repeats sender,0.82,1530.30,source_csv,FixedFloat,help@fixedfloat.com,Stolen Crypto July 2021 - Summary.csv,,,,,FixedFloat,preserve_records,Check source CSV anomaly before filing.
william-2023-theft,6,wasabi_deposit,low_confidence,bitcoin,BTC,,TBD,TBD,,TBD,prior_trace,unknown,THORChain or downstream path,bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s,Wasabi deposit,TBD,,,,William Crypto Case Dossier,,,,,,,,Wasabi deposit address from case dossier. Fill txid from prior trace before filing.
william-2023-theft,7,demix_candidate,low_confidence,bitcoin,BTC,,1962037495cfc6f39cd0c525b78fdcffddb98de34babdcf785b12208152e9bb2,TBD,,TBD,prior_demix_review,unknown,Wasabi coinjoin candidate,bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl,low confidence demix candidate,TBD,,,,William Crypto Evidence and Escalation Packet Round 2,,,,,,,,Needs paid analytics validation.
william-2023-theft,8,live_lead,explorer_verified,bitcoin,BTC,,164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187,https://blockstream.info/tx/164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187,812907,2023-10-19T10:02:51Z,blockstream_api,unknown,prior candidate path,bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g,current watchlist lead,6.49998240,,,,Blockstream API,,,,,IC3,FBI,Chainabuse,watchlist_only,Do not overclaim. Unspent as of 2026-05-25 13:18:56 UTC.
william-2023-theft,9,dust,explorer_verified,bitcoin,BTC,,4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5,https://blockstream.info/tx/4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5,940313,2026-03-11T17:22:44Z,blockstream_api,bc1q7x6kj7lg9ls2g6s3wm644s5tuqkkg89dp5t532,dust source,bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g,current watchlist lead,0.00000294,,,,Blockstream API,,,,,IC3,FBI,Chainabuse,watchlist_only,Do not interact with the address.
william-2023-theft,10,service_branch,probable_service,bitcoin,BTC,,29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287,TBD,,TBD,case_dossier,TBD,TBD,17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva,probable Binance branch,TBD,,,,William Crypto Case Dossier,,,,,Binance,LERS_if_LE_validates,preserve_records,Public cluster attribution only. Needs validation.
```

## 7. Reporting path

### Step 1. Rebuild evidence package

Stuart can prepare the packet. William should approve the narrative, identity material, and any authorization before submission.

Immediate tasks:

* Normalize the CSV with UTC timestamps and clickable explorer URLs.
* Reverify the live BTC address before every filing and after every material delay.
* Add screenshots and raw JSON for every lead address and txid.
* Keep the low confidence Wasabi demix caveat on the first page.

### Step 2. File or update IC3

Use `https://complaint.ic3.gov/` and preserve the complaint number. IC3 and FBI guidance request transaction details including cryptocurrency addresses, amounts and types, dates and times, and transaction hashes. The IC3 cryptocurrency page says complaints can be referred to federal, state, local, international, and partner agencies, and that the complainant should not expect IC3 itself to contact them.

### Step 3. File local police report

William should file with the police department covering his domicile. Ask for a detective, report number, email address for supplemental evidence, and permission to send the transaction CSV. The police report is useful for Binance support, counsel, insurance, and bank or exchange records.

### Step 4. Contact FBI field office

After IC3, contact the FBI field office covering William's residence. The FBI Cyber page says each of the 56 FBI field offices has trained cyber squads and that rapid IC3 reporting can help support lost funds recovery. Use the template below.

### Step 5. Contact Secret Service where relevant

Use the nearest field office from `https://www.secretservice.gov/contact/field-offices/`. Most field offices have a Cyber Fraud Task Force. If the facts fit cryptocurrency investment fraud or another cyber enabled financial crime, the Secret Service page also lists `CryptoFraud@SecretService.gov` for crypto investment fraud victims.

### Step 6. File FTC report

Use `https://reportfraud.ftc.gov/`. FTC reporting will not itself freeze crypto, but it creates a consumer fraud record and reinforces recovery scam precautions. FTC warns that recovery scammers target prior victims and that upfront fees or private requests for financial information are red flags.

### Step 7. Chainabuse reporting strategy

Submit private Chainabuse reports first for sensitive items:

* William's ten victim EVM wallets.
* THORChain router transactions and relevant outputs.
* Wasabi deposit address.
* Low confidence demix candidate.
* Live BTC watchlist address.
* FixedFloat related wallet and associated transactions.
* Probable Binance branch address.

Use private reports where public visibility could alert the actor, invite recovery scammers, or expose William's personal details. Chainabuse states private reports are visible to law enforcement partners and not displayed on the public site. Public reports can be considered later for clearly malicious addresses with no risk of tipping the actor.

### Step 8. FixedFloat preservation notice

Send only after the packet has IC3 or police identifiers if possible. If not, send the victim notice and update later with report numbers. Ask for preservation, risk flagging, ticket confirmation, and correct law enforcement process route.

### Step 9. Binance preservation path

William can open a Binance Support stolen funds ticket with the police report, clickable tx links, and probable Binance branch lead. Formal preservation, records, and freezing should go through law enforcement via Binance LERS or court process.

### Step 10. SlowMist and paid analytics

Submit SlowMist case evaluation through `https://aml.slowmist.com/recovery-funds.html` and consider MistTrack monitoring. For paid analytics, ask vendors to validate three concrete questions:

1. Does independent tooling reproduce the Wasabi demix candidate `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` from the seven Wasabi deposits?
2. Can the current lead `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` be connected to the victim path at a standard suitable for law enforcement or civil process?
3. Is `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` part of a Binance controlled cluster, and can the branch tx `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287` be mapped to a deposit, hot wallet, or cash out path?

# Communications Templates

## 1. FixedFloat victim preservation request

```text
To: help@fixedfloat.com
Cc: compliance@fixedfloat.com
Subject: Crime victim preservation request, suspected stolen funds involving FixedFloat related transactions, July 2023

FixedFloat team,

I am the victim of a cryptocurrency theft that occurred between July 21 and July 23, 2023. I am preparing reports for IC3, local law enforcement, and the FBI field office. My source transaction file includes several Ethereum transactions and destination addresses that appear to be related to FixedFloat.

Please preserve records and risk flags connected to the transactions and addresses below, including order records, deposit addresses, payout addresses, account emails if any, IP logs, support chats, API metadata, KYC or source of funds material if any, partner routing records, internal compliance alerts, and blockchain analytics notes.

Known FixedFloat related wallet from my source file:
0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F

Known FixedFloat related transaction hashes:
0xaa49f832a539cabee457ca3fc2e3e47e70ca7e364ba48161aae8c4e788d07b33
0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3
0x91a3d5976df4c7fb6d000a081855b4fc217d61d6e1b71f5c99205e7dc7c2f63f
0x72d855932534ca55ae820f5ed17de8ac729b1f05b093352b5bca19dcf868f26f
0xb5e309a09f479a87f71b1258380d8b8e62c84163364b3b06762927c476c4d655

Other destination wallets listed near those transactions:
0xbdC4b2D85d9DCC42C3799b4569bd1D7D25D29C03
0x4EC986035B635D09474fC390AcDF5c107DDa4c70
0x09066E7857D3a9a53c9142f8a7eFFcBc7989F1B5

The broader case includes a BTC and Wasabi lead that requires further validation. The FixedFloat related items above come from my original source transaction file and should be evaluated independently.

Please confirm receipt, provide a ticket number, and tell me where law enforcement should send formal preservation, records, or freezing process. I am not requesting disclosure of personal customer information to me. Please preserve relevant records and direct formal disclosures to law enforcement.

Reports filed:
IC3: [number or pending]
Local police: [number or pending]
FBI field office: [office or pending]

Attachments:
1. One page summary
2. FixedFloat transaction subset
3. Source CSV excerpt
4. Police or IC3 receipt if available

William [last name]
[phone]
[email]
[counsel if any]
```

## 2. Binance victim preservation and support ticket

```text
To: Binance Support through the stolen funds support route
Subject: Stolen funds report and preservation request, probable Binance branch, July 2023 theft

Binance Support team,

I am the victim of a cryptocurrency theft that occurred between July 21 and July 23, 2023. I filed or am filing reports with IC3, local law enforcement, and the FBI field office. A tracing review identified a probable Binance related branch that requires preservation and validation.

Please create a ticket, preserve records where possible, and tell me what law enforcement should submit through Binance LERS.

Probable Binance branch details:
Address: 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva
Branch transaction: 29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287
Current status: public cluster attribution suggests this may be related to Binance, but I understand this is not official Binance confirmation.

Case context:
Loss: $1,675,929.20 according to my source CSV
Incident dates: July 21 to July 23, 2023
Wasabi deposit address: bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s
Low confidence demix candidate: bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl
Current watchlist lead: bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g

I understand Binance may require an official freezing order from law enforcement or a court before freezing assets, and that confidential customer or law enforcement information cannot be shared with me. My request is to preserve records, flag the branch for review, and provide instructions for law enforcement.

Reports filed:
IC3: [number or pending]
Local police: [number or pending]
FBI field office: [office or pending]

Attachments:
1. One page summary
2. Transaction inventory CSV
3. Police report or IC3 receipt
4. Explorer links and screenshots for the Binance branch
5. Ownership evidence for my source wallets

William [last name]
[phone]
[email]
[counsel if any]
```

## 3. Binance law enforcement preservation addendum

```text
For law enforcement submission through Binance LERS:

Subject: Preservation and records request, stolen crypto case, probable Binance branch

Agency: [agency]
Officer or agent: [name, badge, email, phone]
Case number: [case number]
Victim: William [last name]
IC3: [number]
Local report: [number]

Requested action:
Please preserve records, account identifiers, KYC, IP logs, device data, support communications, deposit and withdrawal history, internal risk alerts, and blockchain analytics notes associated with the address or branch below, pending legal process. If supported by your procedures and the attached facts, please identify the legal process required for a freeze.

Address: 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva
Branch tx: 29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287
Related case lead: bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g

Attachments:
1. Victim signed statement
2. Transaction inventory CSV
3. Trace memo with caveats
4. Explorer screenshots and raw data
5. IC3 and local report numbers
```

## 4. Paid analytics inquiry

```text
Subject: Paid forensic validation request, BTC, Wasabi demix, Binance branch, William theft case

Hello,

We are seeking a professional blockchain forensic review for a July 2023 theft with a source CSV loss value of $1,675,929.20. The intended output is a concise report suitable for law enforcement, counsel, and exchange preservation requests. We do not need a recovery guarantee and will not pay any success fee to an unsolicited recovery actor.

Scope questions:
1. Can your tooling reproduce or reject the low confidence Wasabi demix candidate below?
2. Can you validate whether the current watchlist lead is connected to the victim path at a confidence level appropriate for law enforcement or civil process?
3. Can you validate whether the probable Binance branch is part of a Binance controlled cluster or another identifiable service?
4. Can you produce a court ready trace report with methodology, confidence labels, source limitations, and all required txids?
5. Can you set monitoring alerts for the live BTC address and notify us if it moves?

Known facts:
Wasabi deposit: bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s
Low confidence demix candidate: bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl
Current watchlist lead: bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
Probable Binance branch address: 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva
Probable Binance branch tx: 29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287
FixedFloat related wallet: 0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F

Please provide:
1. Statement of work
2. Price and timeline
3. Required inputs
4. Analyst credentials
5. Sample report format
6. Chain coverage for BTC, Ethereum, BNB Smart Chain, THORChain, and Wasabi or CoinJoin analysis
7. Disclosure and confidentiality terms

We will provide the source CSV, explorer links, screenshots, raw JSON, and report numbers after NDA or counsel approval.

Stuart [last name]
Authorized coordinator for William [last name], pending signed authorization
[phone]
[email]
```

## 5. FBI field office follow up after IC3

```text
Subject: IC3 complaint [number], $1.67M cryptocurrency theft, live BTC preservation lead

FBI [field office] Cyber Squad,

I filed IC3 complaint [number] regarding a cryptocurrency theft that occurred between July 21 and July 23, 2023. The source CSV loss value is approximately $1,675,929.20. I am contacting the field office covering my residence to provide a complete evidence packet and ask whether this matter should be routed to a cyber squad, Secret Service Cyber Fraud Task Force, IRS Criminal Investigation, or another federal partner.

The strongest current lead is a BTC watchlist address:
bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g

On May 25, 2026 at 13:18:56 UTC, Blockstream API showed that address holding 6.49998534 BTC, with zero spent outputs and zero mempool transactions. The path to this address depends on a low confidence Wasabi demix candidate, so I am asking for investigative review rather than making a final attribution claim.

The case also includes a FixedFloat related side path from the original source CSV and a probable Binance branch that should be validated through law enforcement or paid analytics before any formal freeze request.

Could your office advise the fastest process for updates if the live BTC address moves, and whether you can receive the attached transaction inventory and evidence folder?

Attachments:
1. One page summary
2. Transaction inventory CSV
3. Incident narrative
4. Explorer screenshots and raw data index
5. FixedFloat subset
6. Probable Binance branch subset
7. IC3 receipt

William [last name]
[phone]
[email]
[counsel if any]
```

## 6. Local police detective follow up

```text
Subject: Supplemental evidence for report [number], cryptocurrency theft, July 2023

Detective [name],

Thank you for taking report [number]. I am attaching a structured evidence packet for my cryptocurrency theft case. The source CSV loss value is $1,675,929.20, with unauthorized transfers between July 21 and July 23, 2023.

The packet includes:
1. One page summary
2. Transaction inventory CSV with tx hashes, addresses, amounts, and explorer links
3. Incident narrative
4. Wallet ownership evidence
5. Explorer screenshots and raw blockchain data index
6. FixedFloat side path subset
7. Probable Binance branch subset
8. IC3 complaint number [number]

I understand that exchanges and services generally require law enforcement or court process before disclosing customer records or freezing funds. Please advise whether your department can send formal preservation requests, coordinate with the FBI field office, or provide a detective contact that exchanges may use for follow up.

If the BTC watchlist address moves, I will send a supplemental notice with the txid, mempool timestamp, outputs, and explorer links.

William [last name]
[phone]
[email]
[counsel if any]
```

## 7. Attorney or counsel intake

```text
Subject: Counsel intake request, $1.67M cryptocurrency theft, evidence packet ready

Hello,

I am seeking counsel for a July 2023 cryptocurrency theft. The source CSV loss value is $1,675,929.20. I have a structured evidence packet, IC3 or police reporting status, FixedFloat and Binance preservation targets, and a live BTC watchlist lead that needs careful validation before legal process.

Primary questions for counsel:
1. Can you advise on preservation letters, subpoenas, court orders, or freezing orders for exchanges and services?
2. Can you coordinate with law enforcement if an identified custodial endpoint requires official process?
3. Can you review a paid analytics scope before we spend money on a forensic report?
4. Can you advise on safe identity and wallet ownership proof without exposing private keys or seed phrases?
5. Can you advise whether civil process is viable if law enforcement capacity is limited?

Known facts:
Incident dates: July 21 to July 23, 2023
Source CSV loss value: $1,675,929.20
Wasabi deposit: bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s
Low confidence demix candidate: bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl
Current watchlist lead: bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
FixedFloat related wallet: 0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F
Probable Binance branch: 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva

Important caveat:
The current BTC watchlist lead depends on a low confidence Wasabi demix candidate. We need validation before making strong claims.

Please let me know your conflict check process, retainer model, expected first steps, and whether you have prior experience with crypto asset preservation or exchange legal process.

William [last name]
[phone]
[email]
```

# 10 Minute Client Call Script

## Minute 0 to 1: purpose and authority

* Confirm William is on the call and comfortable discussing the theft.
* Explain that the goal is official reporting and preservation, not a guaranteed recovery promise.
* Confirm whether Stuart is authorized to prepare materials, contact vendors, and draft reports.

Signoff question:

```text
Do you authorize Stuart to prepare the evidence packet and draft communications for your review, without sending identity documents or legal claims until you approve them?
```

## Minute 1 to 2: identity and jurisdiction

Collect:

* Full legal name.
* Current domicile, city, state, country.
* Phone and email.
* Citizenship if relevant.
* Whether William has counsel.
* Whether William is comfortable filing IC3, local police, FTC, and Chainabuse.

## Minute 2 to 3: incident facts

Ask:

* Exact discovery date.
* How the wallets were compromised if known.
* Devices used at the time.
* Whether there are scammer communications, malware indicators, suspicious downloads, Discord or Telegram contacts, browser extensions, or seed storage issues.
* Whether any exchange accounts were compromised.

## Minute 3 to 4: reporting status

Ask:

* Has IC3 already been filed?
* Has local police report been filed?
* Has any FBI field office, Secret Service office, exchange, or analytics vendor been contacted?
* Are there ticket IDs or emails that need to be added to the packet?

## Minute 4 to 5: wallet ownership proof

Ask William to gather:

* Wallet UI screenshots showing each source address.
* Exchange withdrawal records or funding records.
* Device or wallet export screenshots that do not expose private keys.
* Any hardware wallet or account ownership proof counsel approves.

Warning:

```text
Do not send seed phrases, private keys, full wallet backups, or password manager exports to anyone.
```

## Minute 5 to 6: packet approval

Walk through the case posture:

* $1,675,929.20 source CSV loss value.
* THORChain and Wasabi path.
* FixedFloat side path.
* Probable Binance branch.
* Live BTC watchlist lead.
* Low confidence caveat for the Wasabi demix path.

Signoff question:

```text
Do you approve using this case summary in IC3, police, FBI, Chainabuse, FixedFloat, Binance, analytics vendor, and counsel communications, with the caveat that the Wasabi demix path remains low confidence?
```

## Minute 6 to 7: reporting choices

Confirm sequence:

1. IC3.
2. Local police.
3. FBI field office.
4. FTC.
5. Chainabuse private reports.
6. FixedFloat victim notice.
7. Binance support ticket.
8. SlowMist case evaluation.
9. Counsel and paid analytics.

## Minute 7 to 8: privacy and publication

Ask:

* Should Chainabuse reports be private by default?
* Can William opt in to law enforcement contact through Chainabuse?
* Can Stuart share sanitized materials with analytics vendors before counsel review?
* Is public posting prohibited until counsel approves?

Recommended answer:

```text
Private reports first. No public thread, no social media, no direct contact with suspected holders.
```

## Minute 8 to 9: live lead plan

Agree on rapid escalation if the BTC address moves:

* Capture txid, mempool timestamp, outputs, fee, raw JSON, and explorer links.
* Notify FBI field office and local detective.
* Notify Secret Service field office or `CryptoFraud@SecretService.gov` if no active federal contact exists.
* Update Chainabuse private reports.
* Send the exchange packet if a custodial endpoint is identified.

## Minute 9 to 10: close and missing items

Read back missing items:

* IC3 number.
* Police report number.
* William ID and proof of domicile if needed.
* Wallet ownership proof.
* Any existing tickets or emails.
* Counsel decision.
* Permission to contact FixedFloat, Binance, SlowMist, and paid analytics vendors.

Final signoff:

```text
I approve the packet sequence: IC3, local police, FBI field office, FTC, private Chainabuse reports, FixedFloat victim preservation notice, Binance support ticket, SlowMist case evaluation, counsel and paid analytics review.
```

# Source Quality Assessment

Confidence is medium. Official government, exchange, and service pages are current enough for routing as of May 25, 2026. The case facts come from local files and the source CSV, while the live BTC lead was independently rechecked through Blockstream API during this run.

The main uncertainty is attribution. FixedFloat related rows come from William's source CSV and can be handled as an independent preservation target. The Binance branch is probable, based on prior public cluster analysis, but requires paid analytics, law enforcement, or Binance validation. The live BTC lead remains valuable because it is unspent, but the Wasabi demix step is low confidence.

Community sources were treated as low weight. Search results reinforced common advice around law enforcement and recovery scam warnings, but operational routing relies on official pages and the local case dossier.

# Open Questions

1. What is William's domicile and which local police department, FBI field office, and Secret Service field office cover him?
2. Has William already filed IC3, local police, FTC, Chainabuse, or exchange tickets?
3. Can William prove control of all source wallets without exposing seed phrases or private keys?
4. Are any FixedFloat order IDs, support emails, IP logs, or payout addresses available outside the CSV?
5. Can paid analytics validate or reject the Wasabi demix candidate?
6. Can paid analytics or law enforcement validate the probable Binance branch?
7. Does William want counsel before sending FixedFloat, Binance, SlowMist, or paid analytics inquiries?
8. Should Chainabuse reports remain private by default until counsel approves public reporting?

# Actionable Takeaways

1. Build the folder inventory exactly as listed above.
2. Normalize the transaction CSV and fill missing BTC txids from the prior trace before filing.
3. File or update IC3, then local police, then FBI field office.
4. Add FTC and Chainabuse private reports after William approves the privacy posture.
5. Send FixedFloat and Binance victim notices only with clear preservation language and no direct demand for private customer data.
6. Route formal preservation, account records, or freezing through law enforcement or counsel.
7. Start SlowMist case evaluation and a paid analytics quote only after William signs authorization.
8. Keep watch alerts on `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`; if it moves, capture raw data first, then notify FBI, local police, USSS, Chainabuse, and any identified service.

# Sources Consulted

## Local case files

* `/Users/alphab/.mdx/research/william-crypto-case-dossier.md`
* `/Users/alphab/.mdx/research/william-crypto-evidence-and-escalation-round2.md`
* `/Users/alphab/Downloads/Stolen Crypto July 2021 - Summary.csv`

## Live blockchain checks

* Blockstream address API: `https://blockstream.info/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`
* Blockstream UTXO API: `https://blockstream.info/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g/utxo`
* Blockstream mempool API: `https://blockstream.info/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g/txs/mempool`

## Government and law enforcement

* IC3 cryptocurrency page: `https://www.ic3.gov/CrimeInfo/Cryptocurrency`
* IC3 complaint form: `https://complaint.ic3.gov/`
* FBI cryptocurrency victim guidance: `https://www.fbi.gov/how-we-can-help-you/victim-services/national-crimes-and-victim-resources/cryptocurrency-investment-fraud`
* FBI field offices: `https://www.fbi.gov/contact-us/field-offices`
* FBI cyber page: `https://www.fbi.gov/investigate/cyber`
* Secret Service field offices: `https://www.secretservice.gov/contact/field-offices/`
* Secret Service investment fraud and pig butchering page: `https://www.secretservice.gov/investigations/investmentfraud-pigbutchering`
* FTC refund and recovery scams: `https://consumer.ftc.gov/articles/refund-and-recovery-scams`
* FTC fraud report portal: `https://reportfraud.ftc.gov/`
* 18 U.S.C. 2703, preservation and disclosure framework: `https://www.law.cornell.edu/uscode/text/18/2703`
* IRS Criminal Investigation manual section discussing 18 U.S.C. 2703 process and preservation letters: `https://www.irs.gov/irm/part9/irm_09-004-009`

## Exchanges, services, and reporting platforms

* FixedFloat support: `https://ff.io/support`
* FixedFloat terms of service: `https://ff.io/terms-of-service`
* Binance stolen funds support article: `https://www.binance.com/en/support/faq/detail/360000006051`
* Binance law enforcement requests: `https://www.binance.com/en/support/law-enforcement`
* Chainabuse report page: `https://chainabuse.com/report`
* Chainabuse reporting fields: `https://docs.chainabuse.com/docs/post-reports-parameters`
* Chainabuse source of information: `https://docs.chainabuse.com/docs/source-of-information`
* Chainabuse law enforcement guidance: `https://safety.chainabuse.com/article/contacting-law-enforcement`
* Chainabuse investigative scam warning: `https://safety.chainabuse.com/article/be-aware-of-investigative-scams-scams-of-scams`
* Chainabuse general FAQ, including private reports: `https://chainabuse.com/faq/GENERAL`

## Analytics and paid support options

* SlowMist case evaluation: `https://aml.slowmist.com/recovery-funds.html`
* SlowMist case tracking: `https://aml.slowmist.com/case-tracking.html`
* MistTrack homepage: `https://misttrack.io/index.html`
* MistTrack FAQ: `https://misttrack.io/faq.html`
* Chainalysis Global Services: `https://www.chainalysis.com/services/`
* TRM Labs: `https://www.trmlabs.com/`
* TRM contact: `https://www.trmlabs.com/contact-us`
* Elliptic national security and law enforcement intelligence: `https://www.elliptic.co/platform/threat-intelligence`
* Elliptic contact: `https://www.elliptic.co/contact-us`

## Community and web checks

* Reddit searches around Chainabuse, Binance stolen funds, and crypto recovery were consulted only as low weight context. They were not used for contact details or legal process claims.

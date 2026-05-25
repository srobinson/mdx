# IC3 Complaint Draft for William Review

Prepared: 2026-05-25  
Purpose: draft text for William to review, correct, and file at `https://complaint.ic3.gov/`.  
Status: draft only. William must confirm all personal details, dates, amounts, and report numbers before filing.

## Guardrails

- This is a draft for William's review, correction, approval, and filing or sending.
- This is not legal advice.
- No recovery guarantee is made.
- No one should submit, sign, or send this under William's name without William's approval.
- No one should contact, threaten, hack, phish, or interact with any suspected actor or blockchain address.

## Filing Party

- Full legal name: `[William full legal name]`
- Address: `[William street address]`
- City, state, ZIP, country: `[William location]`
- Phone: `[William phone]`
- Email: `[William email]`
- Preferred contact method: `[phone/email]`
- Signature or typed certification name: `[William signature / typed name]`
- Date signed or submitted: `[date]`

## Existing Report Numbers and Contacts

- IC3 complaint number: `[IC3 number, if updating an existing complaint, otherwise pending]`
- Local police report number: `[local police report number or pending]`
- Local police department and detective: `[department, detective, phone, email, if known]`
- FBI field office contact: `[field office, contact, phone, email, if known]`
- Secret Service contact: `[contact or none]`
- FTC report number: `[FTC report number or pending]`
- Chainabuse report links: `[links or pending]`
- FixedFloat ticket or contact: `[ticket or none]`
- Binance or Binance.US ticket: `[ticket or none]`
- Counsel contact: `[name, firm, phone, email, if retained]`

## Incident Date Caveat

The source file name says `Stolen Crypto July 2021 - Summary.csv`. The transaction evidence reviewed for this packet points to July 21 to July 23, 2023, pending William confirmation. William should confirm the correct incident date range and time zone before final submission.

## Complaint Summary

I am reporting unauthorized cryptocurrency transfers from wallets I controlled or used. Based on the source transaction inventory, the reported loss is approximately `$1,675,929.20`, including `884.8222 ETH` and `8.6 BNB`. The transaction evidence currently points to an incident window of July 21 to July 23, 2023, but I need to confirm that window because the source CSV filename references July 2021.

The evidence packet indicates that the main route involved ETH and BNB outflows from EVM wallets, swaps or conversions through THORChain, movement into BTC, and then a deposit into Wasabi. There are additional investigative leads involving a FixedFloat related wallet, a low confidence post Wasabi demix candidate, a current BTC watchlist address, and a probable Binance cluster branch. I am not claiming that these leads prove final attribution. I am asking for law enforcement review, preservation support, and routing to the appropriate cyber or financial crimes personnel.

## Narrative for IC3 Form

On or around `[confirmed incident date range and time zone]`, unauthorized transactions moved cryptocurrency from wallets associated with me. The source records list a total reported loss of approximately `$1,675,929.20`, consisting of `884.8222 ETH` and `8.6 BNB`.

The transaction inventory and supporting evidence identify two THORChain related conversions that appear central to the route:

1. Transaction `655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204`, timestamped 2023-07-21T14:17:43Z, converting `125.44715147 ETH` to `7.29622713 BTC`, with output to the Wasabi deposit address listed below.
2. Transaction `40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C`, timestamped 2023-07-21T15:34:17Z, converting `727.29568000 ETH` to `31.37643194 BTC`, with output to the Wasabi deposit address listed below.

The key address evidence currently includes:

- Wasabi deposit address: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`
- Low confidence post Wasabi demix candidate: `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`
- Current BTC watchlist lead: `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`
- FixedFloat related wallet: `0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F`
- Probable Binance branch address: `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva`
- Probable Binance branch transaction: `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287`

A live BTC validation check on 2026-05-25 found no new spend, no unconfirmed transaction, and no mempool activity for the current BTC watchlist lead `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`. The address retained two unspent outputs totaling `6.49998534 BTC` during the 2026-05-25T13:35:14Z to 13:37:02Z validation window. This address should be treated as an investigative lead requiring validation, not as proven stolen funds.

The probable Binance branch remains unconfirmed. The public evidence shows the branch address `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` was spent by transaction `1829670be43913276482832ef00ee2d7eebd6cd03a2ca2aa7f2d00fbe5d99f79`, confirmed at block `849063`. I understand that public blockchain data does not confirm an official Binance account relationship. I am asking law enforcement to review and preserve relevant evidence through appropriate legal process if a service exposure is validated.

I am requesting that IC3 accept this complaint, preserve the complaint number, route it to the appropriate cyber or financial crimes personnel, and advise the fastest channel for supplemental updates if the live BTC watchlist address moves or if paid analytics validates service exposure.

## Known Caveats

- The incident date is not yet fully confirmed. The source filename references July 2021, while transaction evidence points to July 21 to July 23, 2023.
- The current BTC watchlist address is an investigative lead requiring validation.
- The post Wasabi demix candidate is low confidence and should not be treated as final attribution.
- The probable Binance branch is a cluster lead, not official Binance confirmation.
- The FixedFloat related wallet is a preservation target from the source data and dossier, not service confirmed attribution.
- This report seeks preservation, routing, and investigation. It does not request or represent any guaranteed recovery.

## Requested Law Enforcement Action

1. Create or update an IC3 complaint record for this reported cryptocurrency theft.
2. Route the matter to cybercrime or financial crimes personnel.
3. Preserve the complaint number and provide a mechanism for supplemental transaction updates.
4. Review the attached transaction inventory and evidence index.
5. If service exposure is validated, support preservation requests or lawful process to relevant services, including FixedFloat, Binance or Binance.US as appropriate, Wasabi related service records if available, and any exchange or hosted service identified by investigators.
6. Coordinate with local police, FBI field office, Secret Service, or other agencies as appropriate.

## Exact Attachment List

The following attachments should be included if the IC3 portal permits upload or preserved for supplemental delivery to law enforcement:

1. `00_one_page_summary.pdf`
2. `01_transaction_inventory.csv`
3. `02_evidence_index.pdf`
4. `03_incident_narrative.pdf`
5. `04_victim_identity_and_authorization.pdf`
6. `05_wallet_ownership_proof/`
7. `06_source_csv/`
8. `07_explorer_screenshots/`
9. `08_raw_blockchain_data/`
10. `09_fixedfloat_subset/`
11. `10_binance_subset/`
12. `11_reporting_receipts/`
13. `12_preservation_requests/`
14. `13_client_call_notes/`
15. `/Users/alphab/.mdx/research/data/william-live-check-2026-05-25/20260525T133513Z-fetch-manifest.tsv`
16. `/Users/alphab/.mdx/research/data/william-live-check-2026-05-25/20260525T133658Z-extra-fetch-manifest.tsv`

## Submission Checklist for William

- `[ ]` Confirm full legal name, address, phone, email, and location.
- `[ ]` Confirm the incident date range and time zone.
- `[ ]` Confirm the source wallets and loss amount.
- `[ ]` Confirm whether this is a new IC3 complaint or an update to an existing number.
- `[ ]` Save the IC3 confirmation receipt and complaint number.
- `[ ]` Add the receipt to `11_reporting_receipts/`.
- `[ ]` Send the complaint number to local police, FBI field office, and counsel if retained.

## Signature

`[William full legal name]`  
`[William signature or typed certification]`  
`[Date]`

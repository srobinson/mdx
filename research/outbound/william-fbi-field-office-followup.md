# FBI Field Office Follow Up Draft for William Review

Prepared: 2026-05-25  
Purpose: draft email or letter for William to review, correct, sign, and send to the appropriate FBI field office after filing or updating IC3.  
Status: draft only. William must confirm all personal details, dates, amounts, and report numbers before sending.

## Guardrails

- This is a draft for William's review, correction, approval, and filing or sending.
- This is not legal advice.
- No recovery guarantee is made.
- No one should submit, sign, or send this under William's name without William's approval.
- No one should contact, threaten, hack, phish, or interact with any suspected actor or blockchain address.

## Header

To: `[FBI Field Office / cyber squad contact, if known]`  
Email or address: `[field office email or mailing address]`

From: `[William full legal name]`  
Address: `[William street address]`  
City, state, ZIP, country: `[William location]`  
Phone: `[William phone]`  
Email: `[William email]`

Date: `[date]`

Subject: Follow up to IC3 complaint, reported cryptocurrency theft with live BTC watchlist lead

## Report Numbers

- IC3 complaint number: `[IC3 number]`
- Local police report number: `[local police report number or pending]`
- Local police department and detective: `[department, detective, phone, email, if known]`
- FBI field office contact: `[field office, contact, phone, email, if known]`
- Secret Service contact: `[contact or none]`
- FTC report number: `[FTC report number or pending]`
- Chainabuse report links: `[links or pending]`
- FixedFloat ticket or contact: `[ticket or none]`
- Binance or Binance.US ticket: `[ticket or none]`
- Counsel contact: `[name, firm, phone, email, if retained]`

## Draft Message

Dear `[FBI Cyber Squad / Field Office Contact]`,

I am following up on IC3 complaint `[IC3 number]` regarding a reported cryptocurrency theft involving wallets associated with me. I am requesting routing to the appropriate cyber squad or financial crimes contact and guidance on the fastest channel for supplemental updates if a live BTC watchlist address moves.

The source transaction inventory lists an approximate loss of `$1,675,929.20`, including `884.8222 ETH` and `8.6 BNB`. The source file name says `Stolen Crypto July 2021 - Summary.csv`. The transaction evidence reviewed for this packet points to July 21 to July 23, 2023, pending my confirmation of the correct incident date range and time zone.

The evidence packet indicates ETH and BNB outflows from EVM wallets, conversion through THORChain into BTC, movement into Wasabi, and additional investigative leads involving FixedFloat, a low confidence post Wasabi demix candidate, a current BTC watchlist address, and a probable Binance cluster branch. I am not claiming final attribution. I am asking for review, preservation support where lawful, and routing to the appropriate cyber or financial crimes personnel.

## Key Evidence Summary

Central THORChain related transactions:

1. `655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204`, timestamped 2023-07-21T14:17:43Z, converting `125.44715147 ETH` to `7.29622713 BTC`, with output to the Wasabi deposit address.
2. `40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C`, timestamped 2023-07-21T15:34:17Z, converting `727.29568000 ETH` to `31.37643194 BTC`, with output to the Wasabi deposit address.

Key addresses and leads:

- Wasabi deposit address: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`
- Low confidence post Wasabi demix candidate: `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`
- Current BTC watchlist lead: `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`
- FixedFloat related wallet: `0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F`
- Probable Binance branch address: `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva`
- Probable Binance branch transaction: `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287`

A live BTC validation check on 2026-05-25 found no new spend, no unconfirmed transaction, and no mempool activity for the current BTC watchlist address `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`. It retained two unspent outputs totaling `6.49998534 BTC` during the 2026-05-25T13:35:14Z to 13:37:02Z validation window.

The two unspent outputs identified during that validation were:

1. `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187:0`, `649,998,240` sats, block `812907`, 2023-10-19T11:22:51Z, unspent.
2. `4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5:0`, `294` sats, block `940313`, 2026-03-11T22:02:44Z, unspent.

Please treat the live BTC address as an investigative lead requiring validation, not as proven stolen funds. The path to it depends on a low confidence post Wasabi demix candidate.

The probable Binance branch is unconfirmed. Public evidence shows the branch address `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` was spent by transaction `1829670be43913276482832ef00ee2d7eebd6cd03a2ca2aa7f2d00fbe5d99f79`, confirmed at block `849063`. I understand public blockchain data does not confirm an official Binance account relationship.

## Requested FBI Field Office Action

1. Confirm whether this follow up should be associated with IC3 complaint `[IC3 number]`.
2. Route the matter to the appropriate cyber squad, financial crimes, or digital asset contact.
3. Advise the fastest channel for supplemental updates if the live BTC watchlist address moves.
4. Review the transaction inventory and evidence index.
5. If service exposure is validated, support preservation requests or lawful process to relevant services, including FixedFloat, Binance or Binance.US as appropriate, Wasabi related service records if available, and any other hosted service identified by investigators.
6. Coordinate with local police, Secret Service, IC3, or other agencies as appropriate.

## Caveats

- The incident date discrepancy must be preserved until I confirm the correct date range.
- The live BTC address is a watchlist lead and should not be treated as final attribution without validation.
- The post Wasabi demix candidate is low confidence.
- The probable Binance branch is a cluster lead, not official Binance confirmation.
- The FixedFloat related wallet is a preservation target from the source data and dossier, not service confirmed attribution.
- I am asking for investigation, preservation, routing, and lawful process support where appropriate. I understand there is no guaranteed recovery.

## Exact Attachment List

I can provide the following evidence packet items:

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

## Closing

Please confirm the best point of contact and update channel for this matter. I can provide the transaction inventory, source CSV, screenshots, raw blockchain responses, and report receipts upon request.

Respectfully,

`[William full legal name]`  
`[William signature]`  
`[William phone]`  
`[William email]`  
`[Date]`

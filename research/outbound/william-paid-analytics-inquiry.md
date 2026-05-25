# Paid blockchain analytics inquiry

## Routing

Use a known blockchain analytics vendor, counsel referred investigator, or law enforcement referred investigator. Avoid asset recovery firms that promise recovery or request wallet access.

Current official source checks on 2026-05-25:

1. TRM Labs contact page lists `contact@trmlabs.com` and a contact form: https://www.trmlabs.com/contact-us
2. TRM Forensics describes court defensible tracing and legal process support: https://www.trmlabs.com/blockchain-intelligence-platform/forensics
3. Chainalysis states it does not provide investigation assistance for individual victims and warns about impersonation: https://www.chainalysis.com/scams/

## Subject

Paid analytics validation request: Wasabi demix candidate, live BTC linkage, and probable Binance branch

## Draft message

Hello,

I am assisting William, a reported victim of unauthorized cryptocurrency transfers. We are seeking a paid validation engagement, not asset recovery promises. The immediate need is a narrow, source backed, law enforcement ready report that validates or rejects specific blockchain leads and preserves uncertainty where attribution is not supportable.

Please confirm whether your team can accept this engagement directly, through counsel, or through law enforcement. If your firm does not work with individual victims, please tell us the appropriate referral route.

## Case summary

William reports total losses listed in the source CSV as approximately USD 1,675,929.20, including 884.8222 ETH and 8.6 BNB. Source evidence shows July 21 to July 22, 2023 UTC transaction rows, while the original source filename references July 2021. The transaction identifiers should control the analysis.

The current hypothesis is:

1. ETH and BNB outflows from William controlled wallets.
2. Major ETH flows through THORChain to BTC.
3. BTC deposit to a Wasabi address.
4. A low confidence post Wasabi demix candidate.
5. A live BTC watchlist address holding 6.49998534 BTC as of 2026-05-25T13:35Z.
6. A probable Binance branch requiring validation before any formal preservation or freeze claim.
7. A separate FixedFloat related side path from source CSV transactions.

## Identifiers to analyze

| Role | Identifier | Current confidence |
|---|---|---|
| Wasabi deposit address | `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` | High as deposit address |
| Low confidence demix candidate | `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` | Low |
| Live BTC watchlist address | `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` | Investigative lead |
| Probable Binance branch address | `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` | Probable, unconfirmed |
| Probable Binance branch tx | `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287` | Needs service attribution validation |
| Live BTC funding tx | `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187` | Public chain lead |
| FixedFloat related wallet | `0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F` | Medium as preservation target |

Key THORChain swap records:

| Inbound txid | In asset and amount | BTC output destination | Out amount | Action time UTC |
|---|---:|---|---:|---|
| `655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204` | `125.44715147 ETH` | `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` | `7.29622713 BTC` | 2023-07-21T14:17:43Z |
| `40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C` | `727.29568000 ETH` | `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` | `31.37643194 BTC` | 2023-07-21T15:34:17Z |

## Questions we need answered

1. Can you validate or reject the path from the two THORChain BTC outputs into the Wasabi deposit address?
2. Can you validate or reject `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` as a post Wasabi demix candidate tied to William's funds?
3. Can you validate or reject the linkage from that demix candidate to the live BTC watchlist address `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`?
4. Does `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva`, or the cluster receiving tx `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287`, map to Binance.com, Binance.US, another VASP, or no supported service attribution?
5. If the probable Binance branch is service exposure, what confidence label and supporting evidence can be included in a law enforcement packet without overclaiming?
6. Does any current branch show live funds at a service where preservation or freeze action is time sensitive?
7. Can you provide an alerting option if `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` spends?
8. Can the final report include a clear methodology, confidence levels, raw transaction inventory, graph exhibits, timestamps in UTC, and a preservation ready service exposure section?
9. Can you format the report so law enforcement can use it for IC3, local police, FBI, Secret Service, exchange preservation, or legal process?
10. Can you identify any addresses that should not be publicly reported because they are service deposit addresses, mixer addresses, change addresses, or low confidence leads?

## Required deliverable

A law enforcement ready exhibit with:

1. Executive summary and scope.
2. Transaction graph and CSV table.
3. Source list and collection timestamps.
4. Confidence labels for every attribution claim.
5. Clear caveat that the Wasabi demix path is unvalidated unless your analysis supports it.
6. Clear caveat that the probable Binance branch is not official Binance confirmation unless your analysis supports that label.
7. Service exposure section with preservation targets and lawful process notes.
8. Live BTC monitoring status and recommended alert process.
9. Appendix of raw IDs and explorer links.

## Attachments available under NDA or engagement terms

1. `00_one_page_summary.pdf`
2. `01_transaction_inventory.csv`
3. `02_evidence_index.pdf`
4. `03_incident_narrative.pdf`
5. `04_victim_identity_and_authorization.pdf`
6. `06_source_csv/`
7. `07_explorer_screenshots/`
8. `08_raw_blockchain_data/`
9. `09_fixedfloat_subset/`
10. `10_binance_subset/`
11. `12_preservation_requests/`

Please provide pricing, expected turnaround, conflicts or intake requirements, and whether the engagement should be opened by William, counsel, or law enforcement.

Respectfully,

Stuart  
On behalf of William, with authorization available  
Contact: [Stuart email and phone]

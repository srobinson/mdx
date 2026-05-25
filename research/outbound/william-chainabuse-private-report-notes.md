# Chainabuse private report notes

## Routing

Report URL: https://chainabuse.com/report  
Default visibility: private report first  
Public report: only after William gives written approval

Official source checks on 2026-05-25:

1. Chainabuse FAQ says sensitive cases can be reported privately and private report information is visible to law enforcement partners, not published on Chainabuse: https://chainabuse.com/faq/GENERAL
2. Chainabuse reporting docs say reports require a malicious address or URL, scam category, description, and chain. Optional fields include reported loss, screenshots, IP indicators, token ID, scammer contact information, and consent to be contacted by law enforcement or Chainabuse: https://docs.chainabuse.com/docs/post-reports-parameters

## Submission posture

Use a private report because the case includes high value loss, law enforcement routing, Wasabi related leads, possible service deposit addresses, and low confidence analytics. Do not publicly label Wasabi, Binance, FixedFloat, or any candidate service address as malicious without William approval and analytic validation.

## Reporter fields

Reporter: William `[full legal name]`  
Reporter email: `[William email]`  
Reporter phone: `[William phone]`  
Authorized helper: Stuart `[Stuart contact]`  
Country or jurisdiction: `[William domicile]`  
Law enforcement contact: `[agency, report number, detective, email, phone]` when available

Consent checkboxes for William to approve before submission:

1. I agree to be contacted by law enforcement about this private report: `[yes or no]`
2. I agree to be contacted by Chainabuse about this private report: `[yes or no]`
3. I approve a public Chainabuse report later: `no by default`

## Suggested category

Preferred category: Other hack or unauthorized wallet compromise.  
Fallback category: Phishing, if William's narrative confirms credential theft, seed phrase theft, malicious approval, or phishing.

## Short description

William reports unauthorized cryptocurrency transfers from wallets he controlled. The source CSV lists total losses of approximately USD 1,675,929.20, including 884.8222 ETH and 8.6 BNB. Source transaction rows show July 21 to July 22, 2023 UTC. The original source filename references July 2021, so the transaction identifiers should control review.

Major ETH flows appear to route through THORChain into BTC and then a Wasabi deposit address. A low confidence post Wasabi lead points to a live BTC watchlist address that held 6.49998534 BTC as of a public chain check on 2026-05-25T13:35Z, with no spend and no mempool activity. A separate source CSV side path includes FixedFloat related transactions. A probable Binance branch exists as an unvalidated preservation lead only.

This private report is intended to preserve evidence and support law enforcement triage. It does not assert final attribution for Wasabi, Binance, FixedFloat, or any exchange account.

## Addresses and transaction identifiers

### Primary reported victim outflow and THORChain path

| Role | Identifier | Chain | Notes |
|---|---|---|---|
| THORChain inbound tx | `655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204` | THORChain | `125.44715147 ETH` in, `7.29622713 BTC` out to Wasabi deposit |
| THORChain inbound tx | `40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C` | THORChain | `727.29568000 ETH` in, `31.37643194 BTC` out to Wasabi deposit |
| Wasabi deposit address | `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` | BTC | High confidence deposit destination, not ownership attribution |

### Low confidence BTC leads

| Role | Identifier | Chain | Notes |
|---|---|---|---|
| Demix candidate | `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` | BTC | Low confidence until paid analytics or law enforcement validates |
| Live BTC watchlist address | `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` | BTC | Held 6.49998534 BTC as of 2026-05-25T13:35Z, not proven attribution |
| Live funding tx | `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187` | BTC | Funds the live BTC watchlist address |
| Dust tx | `4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5` | BTC | 294 sats dust, not ownership attribution |

### Probable Binance branch, unvalidated

| Role | Identifier | Chain | Notes |
|---|---|---|---|
| Candidate service address | `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` | BTC | Probable Binance branch, unconfirmed |
| Candidate branch tx | `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287` | BTC | Requires paid analytics or law enforcement validation |
| Upstream branch tx | `4d23a22853686456ae2d8345d0402182ac301bf5aa4010a1f04df90581c2bd8f` | BTC | Low confidence downstream candidate branch |

### FixedFloat related side path from source CSV

| Role | Identifier | Chain | Notes |
|---|---|---|---|
| FixedFloat related wallet | `0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F` | Ethereum | Preservation target from source CSV |
| Ethereum tx | `0xaa49f832a539cabee457ca3fc2e3e47e70ca7e364ba48161aae8c4e788d07b33` | Ethereum | Source CSV FixedFloat section |
| Ethereum tx | `0xb5e309a09f479a87f71b1258380d8b8e62c84163364b3b06762927c476c4d655` | Ethereum | Source CSV FixedFloat section |
| Ethereum tx | `0x91a3d5976df4c7fb6d000a081855b4fc217d61d6e1b71f5c99205e7dc7c2f63f` | Ethereum | Source CSV FixedFloat section |
| Ethereum tx | `0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3` | Ethereum | Source CSV FixedFloat section |
| Ethereum tx | `0x72d855932534ca55ae820f5ed17de8ac729b1f05b093352b5bca19dcf868f26f` | Ethereum | Source CSV FixedFloat section |

## Reported loss

Reported total from source CSV: USD 1,675,929.20  
Reported assets: 884.8222 ETH and 8.6 BNB

## Evidence to attach or reference

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
11. `11_reporting_receipts/`

## Private report notes for Chainabuse moderators

1. Please keep this report private unless William later authorizes public reporting.
2. Several addresses may be service deposit addresses, mixer related addresses, or low confidence candidate addresses. Public labeling could be misleading without further validation.
3. The live BTC address is a watchlist lead, not proven final attribution.
4. The probable Binance branch is a preservation lead, not official Binance confirmation.
5. The Wasabi demix path needs paid analytics or law enforcement validation.
6. If Chainabuse has a law enforcement partner route for high value theft reports, please contact the reporter privately.

## Public version, only if William approves later

A public report should be shorter and should remove:

1. William's name, phone, email, and domicile.
2. Low confidence demix analysis unless validated.
3. Any claim that Binance, FixedFloat, or another service controlled funds unless validated.
4. Any nonpublic law enforcement contact details.

Public wording, if approved and validated:

Reported unauthorized wallet drain with losses listed by the victim at approximately USD 1.675 million. Public transaction identifiers are provided for blockchain safety screening. Service attribution and post Wasabi tracing remain under review.

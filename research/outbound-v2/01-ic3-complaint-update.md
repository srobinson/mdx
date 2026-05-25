# IC3 Complaint Or Update Draft

Official route: https://www.ic3.gov/

This is a draft for you to review.

Use this as the narrative text for a new IC3 complaint or as a supplement to an existing IC3 complaint. Replace bracketed fields before submitting.

## Filing Details

- Filing party: `[your full legal name]`
- Email: `[your email]`
- Phone: `[your phone]`
- Address: `[your address]`
- Existing IC3 complaint number: `[number or none]`
- Local police report number: `[number or pending]`
- FBI field office contacted: `[office or pending]`
- Best incident date range based on current transaction evidence: July 21 to July 22, 2023 UTC

## Complaint Summary

I am reporting unauthorized cryptocurrency transfers from wallets I controlled or used. The visible transaction evidence reviewed so far supports one confirmed on chain loss cluster from July 21 to July 22, 2023 UTC.

The source spreadsheet file name references July 2021, but the visible transaction hashes and public chain timestamps point to July 2023. I am preserving that date conflict because the transaction hashes should control the analysis.

The visible public chain total is:

- `884.822151477364040918 ETH`
- `8.6 BNB`

The visible route includes Ethereum and BSC outflows from 10 listed source wallets, THORChain swaps into BTC, a Wasabi deposit address, a FixedFloat related side path, and a BSC path that reaches an address labeled by BscScan as `SimpleSwap: Binance Deposit`.

I am not claiming final attribution. I am asking for law enforcement review, preservation support, and routing to the appropriate cyber or financial crimes personnel.

## Key Transaction Evidence

Two THORChain actions explain most of the BTC sent to the Wasabi deposit address:

1. `655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204`
   - Time: `2023-07-21T14:17:43Z`
   - Input: `125.44715147 ETH`
   - Output: `7.29622713 BTC`
   - BTC destination: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`

2. `40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C`
   - Time: `2023-07-21T15:34:17Z`
   - Input: `727.29568000 ETH`
   - Output: `31.37643194 BTC`
   - BTC destination: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`

Combined THORChain explained BTC to the Wasabi deposit address:

`38.67265907 BTC`

The Wasabi deposit address lifetime amount was:

`40.70902128 BTC`

The remaining `2.03636221 BTC` came from five smaller BTC deposits that still need source evidence before I can claim the full Wasabi amount was supported by the visible spreadsheet rows.

## Important Addresses And Leads

- Wasabi deposit address: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`
- Low confidence post Wasabi candidate: `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`
- Live BTC lead: `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`
- Live BTC funding transaction: `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187`
- Live BTC funding time: `2023-10-19T11:22:51Z`
- Live BTC balance in the 2026-05-25 recheck: `6.49998534 BTC`
- FixedFloat labeled wallet from public Blockscout labeling: `0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F`
- BSC victim transaction: `0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1`
- BSC second hop to `SimpleSwap: Binance Deposit`: `0xd68a6dccbb3aaed884ad5181dfcc2246e2efad690b838343202ec37ca157bb77`

## Live BTC Lead

The live BTC lead address `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` retained two unspent outputs totaling `6.49998534 BTC` during the 2026-05-25 recheck. Public APIs showed no confirmed spend and no mempool activity at that time.

This is an investigative lead, not proven recovered funds. It should be preserved and monitored because a movement from this address could create a narrow response window for exchange reporting or lawful process if the funds enter a service.

## Requested Action

Please accept this complaint or supplement, preserve the complaint number, and route it to the appropriate cyber or financial crimes personnel.

If the live BTC lead moves, I need to know the fastest channel for submitting supplemental information.

If law enforcement validates service exposure, please consider preservation requests or lawful process to relevant services, including FixedFloat, SimpleSwap, Binance.com, Binance.US if actually relevant, and any other hosted service identified by investigators.

## Attachments To Preserve

- Recheck summary: `START-HERE-RECHECK.md`
- Source spreadsheet export: `william-source-spreadsheet.xlsx`
- Source CSV export: `gid-1211660592.csv`
- Visible row summary: `summary-visible-rows.csv`
- Transaction inventory: `transaction-inventory.csv`
- Live BTC validation memo: `william-live-validation-2026-05-25.md`
- Explorer screenshots or links for each key transaction
- Any prior report numbers, exchange tickets, or service replies


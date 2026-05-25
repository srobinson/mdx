# William Outbound Packet Index

Generated: 2026-05-25 13:53:03 UTC

Updated: 2026-05-25 13:55:00 UTC

## Scope

This index records the outbound packet structure for the current drafting round, validates the transaction inventory CSV, inventories expected drafts, and gives the recommended send order and attachment bundles.

## Source inputs checked

| File | Status |
|---|---|
| `/Users/alphab/.mdx/research/transaction-inventory.csv` | Present, 23854 bytes |
| `/Users/alphab/.mdx/research/william-transaction-inventory-build.md` | Present, 4929 bytes |
| `/Users/alphab/.mdx/research/william-one-page-summary.md` | Present, 3847 bytes |
| `/Users/alphab/.mdx/research/william-client-action-pack.md` | Present, 9458 bytes |
| `/Users/alphab/.mdx/research/william-live-validation-2026-05-25.md` | Present, 13371 bytes |
| `/Users/alphab/.mdx/research/william-escalation-packet-codex.md` | Present, 44760 bytes |

## CSV validation

- Parser: Python `csv.DictReader`.
- File: `/Users/alphab/.mdx/research/transaction-inventory.csv`.
- Result: parsed successfully.
- Data rows: 30.
- Header columns: 21.
- Columns: `case_id, source_file, source_row, incident_date_claimed, observed_timestamp_utc, chain, txid, explorer_url, asset, amount_native, amount_usd_at_time, from_address, to_address, service_hint, service_confidence, role, evidence_file, status, current_owner_hypothesis, next_action, notes`.

## Expected outbound drafts

| Stage | Expected file | Status | Recommended attachment bundle | Notes |
|---|---|---|---|---|
| William approval | `/Users/alphab/.mdx/research/outbound/william-client-authorization-letter.md` | Present | Authorization letter, engagement scope, client action pack, one page summary, transaction inventory for context. | William must approve authority, scope, missing data, and external sending posture before filings under his name. |
| William approval | `/Users/alphab/.mdx/research/outbound/william-engagement-scope-20-percent.md` | Present | Engagement terms, counsel intake if counsel review is selected, client action pack decision prompts. | Counsel review remains recommended before signature. |
| Counsel review if chosen | `/Users/alphab/.mdx/research/outbound/william-counsel-intake.md` | Present | Full packet index, one page summary, transaction inventory, live validation memo, engagement scope, authorization letter. | Use when William selects counsel review or before any legal process language. |
| IC3 | `/Users/alphab/.mdx/research/outbound/william-ic3-draft.md` | Present | One page summary, transaction inventory CSV, incident narrative, top screenshots, source CSV, raw blockchain data where upload limits allow. | William files or counsel files with signed authority. Preserve the complaint number. |
| Local police | `/Users/alphab/.mdx/research/outbound/william-local-police-cover-note.md` | Present | One page summary, transaction inventory CSV, incident narrative, identity and authorization if required, wallet ownership proof, source CSV, explorer screenshots. | Ask for report number, detective assignment, supplemental evidence channel, and cyber or financial crimes routing. |
| FBI follow up | `/Users/alphab/.mdx/research/outbound/william-fbi-field-office-followup.md` | Present | IC3 number, local police report if available, one page summary, transaction inventory CSV, live validation memo, raw API manifests. | Use after IC3 is filed and before any urgent update if the live BTC moves. |
| FixedFloat preservation | `/Users/alphab/.mdx/research/outbound/william-fixedfloat-preservation-request.md` | Present | FixedFloat subset, one page summary, transaction CSV excerpt, report numbers when available, preservation request language. | Send after IC3 or police identifiers if possible. Do not request protected customer data directly. |
| Paid analytics | `/Users/alphab/.mdx/research/outbound/william-paid-analytics-inquiry.md` | Present | Sanitized transaction inventory, one page summary, live validation memo, validation questions, budget cap or quote only instruction. | Use for quotes unless William approves a vendor, scope, deliverable, and price in writing. |
| Chainabuse | `/Users/alphab/.mdx/research/outbound/william-chainabuse-private-report-notes.md` | Present | Address list, roles, screenshots, transaction inventory rows, privacy selection, law enforcement contact opt in if approved. | Private reports are the recommended default until William and counsel approve public content. |
| Binance victim support | `/Users/alphab/.mdx/research/outbound/william-binance-victim-support-note.md` | Present | Probable Binance branch memo, one page summary, transaction CSV subset, police report when available, clickable tx links. | Use only when validated or as a victim support ticket. Formal records, preservation, and freezes require law enforcement or court process through the proper channel. |

## Current outbound directory

- `/Users/alphab/.mdx/research/outbound/william-client-authorization-letter.md` (6734 bytes)
- `/Users/alphab/.mdx/research/outbound/william-binance-victim-support-note.md` (current)
- `/Users/alphab/.mdx/research/outbound/william-chainabuse-private-report-notes.md` (current)
- `/Users/alphab/.mdx/research/outbound/william-counsel-intake.md` (9541 bytes)
- `/Users/alphab/.mdx/research/outbound/william-engagement-scope-20-percent.md` (10607 bytes)
- `/Users/alphab/.mdx/research/outbound/william-fbi-field-office-followup.md` (7503 bytes)
- `/Users/alphab/.mdx/research/outbound/william-fixedfloat-preservation-request.md` (current)
- `/Users/alphab/.mdx/research/outbound/william-ic3-draft.md` (8444 bytes)
- `/Users/alphab/.mdx/research/outbound/william-local-police-cover-note.md` (7205 bytes)
- `/Users/alphab/.mdx/research/outbound/william-paid-analytics-inquiry.md` (current)

## Send order

1. **William approval.** Send William the authorization letter, engagement scope, client action pack, one page summary, and missing item checklist. Do not submit under William's name until he approves the facts, scope, and authority.
2. **Counsel review if chosen.** Send counsel the counsel intake packet, engagement scope, authorization letter, one page summary, transaction inventory, live validation memo, and full packet inventory. Use counsel for legal process, fee review, preservation wording, and identity handling.
3. **IC3 and local police.** File or update IC3 first, then use the local police cover note for William's domicile. Attach the one page summary, transaction inventory CSV, incident narrative, source CSV, wallet ownership proof, screenshots, raw blockchain data, and identity or authorization materials only where appropriate.
4. **FBI field office.** Follow up after IC3 with the IC3 number, local police report if available, one page summary, transaction inventory, live BTC status, and raw API manifests.
5. **FixedFloat.** Send a preservation notice for the FixedFloat side path after report numbers are available if possible. Ask for preservation, risk flagging, ticket confirmation, and the correct law enforcement process route. Do not request protected customer data directly.
6. **Paid analytics.** Request quote only unless William approves vendor, scope, deliverable, and price in writing. Ask the vendor to validate or reject the Wasabi demix candidate, live BTC linkage, and probable Binance branch.
7. **Chainabuse.** Submit private reports first for sensitive addresses if William approves that privacy posture. Public reporting should wait for William and counsel approval of exact content.
8. **Binance.** Use Binance victim support only when the branch is validated or as a clearly caveated victim support ticket. Formal preservation, account records, and freezes require law enforcement or court process through the proper channel.

## Recommended master attachment set

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

## Service and Vendor Draft Status

- `/Users/alphab/.mdx/research/outbound/william-fixedfloat-preservation-request.md`: Present.
- `/Users/alphab/.mdx/research/outbound/william-paid-analytics-inquiry.md`: Present.
- `/Users/alphab/.mdx/research/outbound/william-chainabuse-private-report-notes.md`: Present.
- `/Users/alphab/.mdx/research/outbound/william-binance-victim-support-note.md`: Present.

## Final open items William must provide

1. Full legal name, domicile city and state, phone, email, and preferred contact channel.
2. Exact incident date range and time zone.
3. Confirmation of loss amount, source wallets, and whether the source CSV title date is correct.
4. Prior report numbers or receipts for IC3, local police, FBI, Secret Service, FTC, Chainabuse, FixedFloat, Binance, insurer, counsel, analytics vendor, or recovery firm contacts.
5. Wallet ownership proof that does not expose seed phrases, private keys, or signing material.
6. Original source CSV and any source screenshots, emails, chats, ticket numbers, exchange exports, address book screenshots, or explorer links.
7. FixedFloat order IDs, ticket IDs, payout addresses, memos, support emails, or related details if available.
8. Decision on Chainabuse privacy posture.
9. Paid analytics budget posture: quotes only, fixed cap, or defer.
10. Counsel review decision and counsel contact details if retained.
11. Signed authorization for Stuart and approval for any external draft before submission under William's name.
12. Police department, FBI field office, and Secret Service field office based on William's domicile.
13. Preferred alert path if the live BTC address moves.

## Verification performed

- Created the outbound directory if needed.
- Listed current outbound drafts from `/Users/alphab/.mdx/research/outbound/`.
- Parsed `/Users/alphab/.mdx/research/transaction-inventory.csv` with Python `csv.DictReader`.
- Updated service and vendor draft statuses after the later service/vendor lane completed.

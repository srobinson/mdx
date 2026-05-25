# Friend Packet Update

Task slug: `friend-packet-update`
Created: 2026-05-25

## 1. Scope handled

Draft copy/paste ready updates for William's friend packet based on the spreadsheet recheck. Focus areas:

1. Dates.
2. The possible two hack story.
3. Immediate next actions.

This note does not replace William's own review. It gives conservative wording he can copy into the packet and into reports after he checks the facts.

## 2. Evidence sources read

1. Warroom brief: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/WARROOM-BRIEF.md`.
2. Visible row extract: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/summary-visible-rows.csv`.
3. Extract manifest: `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/manifest.md`.
4. Prior friend packet context:
   1. `/Users/alphab/.mdx/research/william-friend-packet/START-HERE-WILLIAM.md`.
   2. `/Users/alphab/.mdx/research/william-friend-packet/copy-paste-messages.md`.
   3. `/Users/alphab/.mdx/research/william-friend-packet/live-btc-finding-repeatable.md`.
5. Public chain checks saved here:
   1. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/friend-packet-update/chain-timestamps.csv`.
   2. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/friend-packet-update/ethereum-*.json`.
   3. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/friend-packet-update/bsc-*.json`.
   4. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/friend-packet-update/blockstream-live-btc-lead-october-check.json`.
   5. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/friend-packet-update/btc-october-lead-summary.json`.

## 3. Findings

1. Confirmed: the visible spreadsheet rows checked here contain 14 on chain transfers: 13 Ethereum transfers and 1 BSC transfer.
2. Confirmed: those 14 visible transfers occurred from `2023-07-21 13:47:23 UTC` through `2023-07-22 09:52:11 UTC`.
3. Confirmed: the chain values total about `884.822151477 ETH` and `8.6 BNB`. The spreadsheet rounds the ETH total to `884.8222 ETH`.
4. Confirmed: the spreadsheet's upper displayed times are mostly UTC minus four hours. That matches Eastern daylight time for July 2023.
5. Confirmed: two visible rows for address `0x1c0b5b8d36587d0516839df7ebfb49ad8f3c543c` have displayed times that do not line up cleanly with the chain order. Use chain timestamps when precision matters.
6. Confirmed: the lower copied rows in the Summary tab include shifted columns and at least one conflicting UTC time. Those lower copied rows should not be treated as final date evidence without chain verification.
7. Confirmed: the visible spreadsheet evidence checked here supports July 2023 activity. It does not prove a July 2021 event.
8. Confirmed: the live BTC lead `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` received its large current UTXO in Bitcoin transaction `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187` at `2023-10-19 11:22:51 UTC`.
9. Likely: the October 19, 2023 Bitcoin date is a downstream lead date, not enough by itself to prove a separate October hack.
10. Unresolved: William says there were two hacks. This recheck does not identify two separate incident packets. William needs to say exactly which files, wallets, dates, and reports belong to each event.

## 4. Copy/paste packet changes

### A. Replace `START-HERE-WILLIAM.md` Step 3 with this

```text
### Step 3: Confirm the incident dates before you file or update reports

There is a date conflict in the materials.

The current spreadsheet file name or title points to July 2021, but the visible transactions I can verify on public chain data happened on July 21 to July 22, 2023 UTC.

The verified visible spreadsheet range is:

July 21, 2023 at 13:47:23 UTC through July 22, 2023 at 09:52:11 UTC.

If the spreadsheet was showing Eastern daylight time, that is approximately:

July 21, 2023 at 9:47:23 AM EDT through July 22, 2023 at 5:52:11 AM EDT.

Some spreadsheet rows have copied or shifted date fields, so use the chain timestamps as the source of truth.

I also see a separate Bitcoin lead that received funds on October 19, 2023 at 11:22:51 UTC. Treat that as a lead date unless you have separate records showing that it was a separate hack.

Before filing or updating reports, please answer this clearly:

1. Was there one incident or two separate incidents?
2. What exact date, year, and time zone belongs to each incident?
3. Which wallets, accounts, screenshots, emails, reports, and transaction IDs belong to each incident?
```

### B. Add this short explanation after Step 3

```text
Use this wording until the two incident question is clear:

My current spreadsheet evidence shows a cluster of outgoing ETH and BNB transfers on July 21 to July 22, 2023 UTC. Separately, there is a Bitcoin lead funded on October 19, 2023 UTC. I may have other 2021 or October incident records, but I need to separate those records before I describe them as separate hacks.

Do not say the spreadsheet proves a 2021 hack unless you have another source file or report that supports 2021. Do not say the October 19, 2023 Bitcoin lead proves a separate hack unless you can attach separate incident evidence for that date.
```

### C. Replace the first paragraph in the IC3 draft with this

```text
I am reporting unauthorized cryptocurrency transfers from my wallets. My current spreadsheet evidence shows a reported loss of approximately $1,675,929.20, including about 884.8222 ETH and 8.6 BNB.

I am still confirming whether this should be reported as one incident or two separate incidents. The visible spreadsheet transactions I can verify on public chain data occurred from July 21, 2023 at 13:47:23 UTC through July 22, 2023 at 09:52:11 UTC. The spreadsheet file name or title appears to point to July 2021, so I do not want to overstate the date until I reconcile the source files.

There is also a Bitcoin lead funded on October 19, 2023 at 11:22:51 UTC. I am treating that as an investigative lead unless separate records prove it was a separate hack date.
```

### D. Replace the first paragraph in the local police draft with this

```text
Hello,

I need to file or update a report for unauthorized cryptocurrency transfers from my wallets. My current spreadsheet evidence shows a reported loss of approximately $1,675,929.20, including about 884.8222 ETH and 8.6 BNB.

I am still reconciling the incident dates. The visible spreadsheet transactions I can verify on public chain data occurred from July 21, 2023 at 13:47:23 UTC through July 22, 2023 at 09:52:11 UTC. The spreadsheet file name or title appears to point to July 2021, so I need to confirm whether I have a separate 2021 incident file or whether the file name is wrong.

There is also a Bitcoin lead funded on October 19, 2023 at 11:22:51 UTC. I am treating that as an investigative lead unless separate records prove it was a separate hack date.
```

### E. Add this to the checklist message to William

```text
Date cleanup checklist:

1. Write the exact date and time zone for each event I remember.
2. Put every source file into one of these buckets: 2021 event, July 2023 event, October event, or unknown.
3. For each bucket, list the wallets, accounts, transaction IDs, screenshots, emails, support tickets, police reports, IC3 reports, and exchange records.
4. Mark the current spreadsheet as July 21 to July 22, 2023 UTC unless another source proves otherwise.
5. Mark the October 19, 2023 Bitcoin transaction as a lead date, not a separate hack date, unless I can attach separate incident evidence.
6. Keep seed phrases, private keys, recovery phrases, wallet PINs, and signing material out of every shared file.
```

### F. Add this one page summary block for William

```text
Current plain language summary

The spreadsheet I have right now does not cleanly match the story that there was a July 2021 hack. The visible transactions in that spreadsheet verify on chain as July 21 to July 22, 2023 UTC.

The visible spreadsheet transfer window is:
July 21, 2023 13:47:23 UTC to July 22, 2023 09:52:11 UTC.

The spreadsheet total is approximately:
884.8222 ETH and 8.6 BNB, shown as about $1,675,929.20 in the sheet.

There is also a Bitcoin lead that received funds on:
October 19, 2023 11:22:51 UTC.

That October date is useful for monitoring and tracing, but I should not call it a second hack date unless I have separate proof.

The next thing I need to do is separate the evidence into event folders:

1. 2021 evidence, if any.
2. July 2023 spreadsheet evidence.
3. October evidence, if any.
4. Unknown or needs review.

Once that is done, reports can describe the timeline without mixing different events together.
```

## 5. Contradictions or unresolved gaps

1. The file name or title points to July 2021, but the visible on chain transaction rows checked here point to July 2023.
2. William's two hack statement remains unresolved. The current spreadsheet recheck proves one visible July 2023 transaction cluster, plus a later October 19, 2023 Bitcoin lead. It does not prove two separate theft events.
3. If William means October 2025 by "last October," this recheck has not found supporting visible spreadsheet rows for that date.
4. Some lower Summary rows have shifted columns and conflicting times. Chain timestamps should control.

## 6. Repeatable commands and URLs

From the warroom folder:

```bash
python /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/friend-packet-update/william_chain_check.py
python /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/friend-packet-update/william_btc_oct_check.py
cat /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/friend-packet-update/chain-timestamps.csv
cat /Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/friend-packet-update/btc-october-lead-summary.json
```

Public explorer URLs to keep in the packet:

1. `https://etherscan.io/tx/0x662e469715056d9501da5184ec4a2a466b05b3fa656c73d0fb067598b88013c2`
2. `https://etherscan.io/tx/0xb5e309a09f479a87f71b1258380d8b8e62c84163364b3b06762927c476c4d655`
3. `https://bscscan.com/tx/0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1`
4. `https://blockstream.info/tx/164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187`
5. `https://blockstream.info/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`

## 7. Recommended next action for William

1. Confirm whether there were one or two incidents.
2. For each incident, write exact date, year, time zone, wallet, account, and evidence source.
3. Keep the July 2023 spreadsheet evidence separate from any 2021 or October evidence.
4. Use conservative report wording until the timeline is clean.
5. Keep monitoring the live BTC lead, but describe it as an investigative lead that needs validation.

# William Crypto Spreadsheet Recheck Warroom Brief

Created: 2026-05-25

## Goal

Rebuild the case facts from William's actual Google Sheet and public chain data.

Stuart's current concern: William says he was hacked twice, once in 2021 and again last October. The spreadsheet title and dates are confusing. We need a thorough, source backed reconstruction of:

- Which accounts were involved.
- Which transactions belong to each event.
- What the true on chain timestamps are.
- Whether the spreadsheet proves one event or multiple events.
- Which gaps William needs to fill in plain language.

## User Context

William is Stuart's friend. This is friend assistance, not Stuart acting as legal representative. Keep outputs professional and practical. Do not include formal client representation or percentage fee terms.

## Source Files

Primary Google Sheet:

`https://docs.google.com/spreadsheets/d/1gxpxBDgzdLDm_MA2bA5U0szlEE01a-mJ2TlQ4-JV8dY/edit?gid=1211660592#gid=1211660592`

Downloaded local evidence:

- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/gid-1211660592.csv`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/william-source-spreadsheet.xlsx`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/manifest.md`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/manifest.json`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/*.csv`

Orchestrator extracted visible transaction rows:

- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/summary-visible-rows.csv`

Prior packet for context only:

- `/Users/alphab/.mdx/research/william-friend-packet/`
- `/Users/alphab/.mdx/research/william-crypto-case-dossier.md`
- `/Users/alphab/.mdx/research/transaction-inventory.csv`

Known previous Bitcoin context to verify, not assume:

- Wasabi deposit address: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`
- Low confidence post Wasabi candidate: `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`
- Live BTC lead: `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`

## Early Observations Needing Verification

- The CSV in Downloads and the Google Sheet CSV export have identical SHA256:
  `251d96652640e7d1d41d2ae0210647ffcc6aa2a80e3ddeec0e193830ccfcc064`
- The XLSX export contains 13 tabs. Two are blank: `Fixed Float Deposit` and `Sheet5`.
- The visible Summary tab mostly shows July 21 to July 22, 2023, not 2021.
- The XLSX stores dates as Excel serial values such as `45128.41735`, which converts to July 21, 2023 10:00:59 if interpreted with the standard Google Sheets or Excel date serial epoch.
- The Summary tab also contains lower copied rows with UTC timestamps, for example row 42 says `21 Jul, 2023 19:15:47 UTC` for tx `0x931e...`, while the upper summary row says `2023/07/21 10:09:11`. Treat this as a conflict until verified against chain data.

## Research Rules

- Verify against public chain data wherever possible. Do not trust spreadsheet dates or prior notes when the chain can answer.
- Save raw API responses or page evidence under your own subdirectory:
  `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/<your-slug>/`
- Write your final note to:
  `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/agents/<your-slug>.md`
- Include commands, URLs, and source file paths sufficient for Stuart or William to repeat your work.
- Mark every important statement with confidence: confirmed, likely, possible, or unresolved.
- Do not request or imply any need for seed phrases, private keys, passwords, 2FA codes, or exchange login access.
- Do not recommend paid analytics until the public audit ceiling is clear.
- Do not edit files outside `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/`.

## Expected Output Shape

Each agent note should include:

1. Scope handled.
2. Evidence sources read.
3. Findings with exact tx hashes, addresses, dates, and timezones.
4. Contradictions or unresolved gaps.
5. Repeatable commands or URLs.
6. Recommended next action for William, if any.

Reply on the bus with one line only:

`DONE|<slug>|<output-path>|<one-sentence-result>`

If blocked:

`BLOCKED|<slug>|<reason>|<specific-info-needed>`

---
title: Public Tools and Reproducible Workflows for William BTC Wasabi Recheck
type: research
tags: [crypto-tracing, bitcoin, wasabi, osint, public-tools]
summary: Public APIs can prove timestamps, balances, UTXOs, and direct spends, while the Wasabi to postmix link remains unresolved without stronger clustering evidence.
status: active
source: github-researcher
confidence: high
created: 2026-05-25
updated: 2026-05-25
---

## Scope handled

Task slug: `public-tools-demix`.

I looked for public tools, open source repos, APIs, MCPs, notebooks, and repeatable workflows that can help Stuart and William verify dates and accounts, then push the public Wasabi demix audit further before any paid vendor step.

## Executive Summary

Confirmed: public APIs are enough to verify transaction dates, address balances, UTXOs, and the direct `post_wasabi_candidate` to `live_btc_lead` spend. Confirmed: the live BTC lead still has `6.49998534 BTC` from two UTXOs as of the 2026-05-25T15:08Z to 15:09Z recheck.

Unresolved: public evidence still does not prove the Wasabi deposit address links to the post Wasabi candidate. Wasabi 2 WabiSabi coinjoins intentionally break input to output attribution, and the no key public co-spend tool I tested, WalletExplorer, places the Wasabi address, candidate address, and live lead in three different wallet IDs.

## Evidence sources read

### Local files

1. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/WARROOM-BRIEF.md`
2. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/summary-visible-rows.csv`
3. `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/extracted-tabs/manifest.md`
4. `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/public-tools-demix/*`

### Raw evidence saved in this task

1. BTC address API responses: `data/public-tools-demix/blockstream-*.json`, `mempool-*.json`, `blockchaininfo-*.json`, `blockcypher-*.json`, `walletexplorer-*.json`
2. BTC involvement tables: `data/public-tools-demix/wasabi-address-involvement.csv`, `post_candidate-address-involvement.csv`, `live_lead-address-involvement.csv`
3. EVM public RPC proofs: `data/public-tools-demix/evm-rpc-timestamps.json` and `data/public-tools-demix/evm-rpc-raw/*.json`
4. GraphSense unauthenticated API probes: `data/public-tools-demix/graphsense-*.json`
5. OXT availability probes: `data/public-tools-demix/oxt-*.html`

### GitHub repos inspected

Cloned shallow into `/tmp/gh-research` and removed after the research pass.

| Repo | Commit checked | Use | Limit |
|---|---:|---|---|
| `Blockstream/esplora` | `393af736194fc71f63dc9993dab10b2936c2ec15` | REST endpoints for BTC tx, outspends, address history, UTXO state | Public endpoint rate limits and privacy leakage unless self hosted |
| `mempool/mempool` | `22a92d1fbe3ebcc66e603c8f3052d56a2599d961` | Open source explorer and API service running at mempool.space | Same public endpoint limits, self hosting needs Bitcoin infrastructure |
| `citp/BlockSci` | `14ccc9358443b2eb5730bb2902c4b11ab7928abf` | Offline graph analysis and change heuristics | Last code commit inspected was 2020, setup is heavy, docs cite at least 60 GB RAM as of July 2020 |
| `graphsense/graphsense-REST` | `8cf170d5609cbf065b6c1e7ba45e721434ed9219` | Address, entity, neighbor, tags, and tx API shape | Repo says REST interface is retired into `graphsense-lib`; hosted API returned 401 without an API key |
| `iknaio/iknaio-api-tutorial` | `ed7c717877320b25ff66b13628c2916f08d4592a` | Notebooks for BTC address inspection, entity demos, and path search | Requires GraphSense or Iknaio API configuration |
| `Bortlesboat/bitcoin-mcp` | `92ecb9f031cd24c0a8daeffef397773256efe59d` | Current Bitcoin MCP wrapper around local Bitcoin Core or hosted Satoshi API | No license detected, includes broadcast tooling, needs read only hardening before evidence work |
| `runeape-sats/bitcoin-mcp` | `31735fda4cb21d3569ba24f1c74f5fd527954542` | Small MCP around a local Bitcoin full node | Early alpha, low activity, no license detected |

I did not clone `WalletWasabi/WalletWasabi` because GitHub reports about `1,169,193 KB` disk usage. I used the public Wasabi documentation and the small `WalletWasabi/WabiSabi` repository metadata instead.

## Findings with exact hashes, addresses, dates, and timezones

### BTC public API recheck

Confirmed addresses from the brief:

1. Wasabi deposit address: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`
2. Low confidence post Wasabi candidate: `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`
3. Live BTC lead: `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`

Confirmed by Blockstream and mempool.space at 2026-05-25T15:08Z to 15:09Z:

| Address | Confirmed status | Evidence file |
|---|---|---|
| `bc1qwx...mn5s` | Confirmed: 13 chain txs, 7 funded outputs totaling `40.70902128 BTC`, all 7 spent, zero UTXO balance | `blockstream-wasabi_deposit-address.json`, `mempool-wasabi_deposit-address.json` |
| `bc1q9vl...jzdl` | Confirmed: 10 chain txs, 8 funded outputs totaling `47.63611646 BTC`, all 8 spent, zero UTXO balance | `blockstream-post_wasabi_candidate-address.json`, `mempool-post_wasabi_candidate-address.json` |
| `bc1qyt...ptt85g` | Confirmed: 2 funded outputs, zero spent outputs, current UTXO balance `6.49998534 BTC` | `blockstream-live_btc_lead-address.json`, `mempool-live_btc_lead-address.json`, `blockstream-live_btc_lead-utxo.json` |

Confirmed direct candidate to live lead spend:

| Field | Value |
|---|---|
| Tx | `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187` |
| Time | `2023-10-19T11:22:51Z` |
| Input | `650,000,000 sats` from `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` |
| Output | `649,998,240 sats` to `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` |
| Fee | `1,760 sats` |
| Confidence | confirmed |
| Evidence | `post_candidate-address-involvement.csv`, `live_lead-address-involvement.csv` |

Confirmed live lead dust top up:

| Field | Value |
|---|---|
| Tx | `4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5` |
| Time | `2026-03-11T22:02:44Z` |
| Output | `294 sats` to `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` |
| Confidence | confirmed |
| Evidence | `blockstream-live_btc_lead-txs.json`, `live_lead-address-involvement.csv` |

Confirmed Wasabi shaped spends from `bc1qwx...mn5s`:

| Time UTC | Tx | Spent from address | Shape | Confidence |
|---|---|---:|---|---|
| `2023-07-21T20:36:18Z` | `98e5a5cc3a832518b42cdcfe8d73f036d10ec323fb93f2a08801f7e79ab4961c` | `17,886,065 sats` | 157 inputs, 153 outputs | confirmed coinjoin shaped |
| `2023-07-22T22:36:24Z` | `447484229542bdf306892f60fdd328bdfe7c670e42013af4247302e6d3bf0be8` | `3,137,643,194 sats` | 244 inputs, 280 outputs | confirmed coinjoin shaped |
| `2023-07-22T23:24:26Z` | `aa885cb70b96cdf41aa4a4d275dfe8239bf168e6840efd8d6a1f1063b50937b7` | `154,305,749 sats` | 193 inputs, 199 outputs | confirmed coinjoin shaped |
| `2023-07-23T00:34:04Z` | `b0d0afa49018bd9233298b7076a0857ee1599056400d8d459f117211d4da2372` | `729,622,713 sats` | 250 inputs, 285 outputs | confirmed coinjoin shaped |
| `2023-07-23T00:57:46Z` | `185bb4b695f603cefcde666acc740f10559e7ef53ff719970c0b8b7bd6cf7ddd` | `24,514,855 sats` | 257 inputs, 294 outputs | confirmed coinjoin shaped |
| `2023-07-23T00:57:46Z` | `4ef38eddb2e091b2d849a06dd5e8c6f8eded722bc29646d7abfc60f4326574ad` | `6,929,552 sats` | 182 inputs, 248 outputs | confirmed coinjoin shaped |

Limit: coinjoin shaped means the transaction has the large multi input and multi output structure expected from Wasabi style coinjoins. It does not identify which output belongs to William or any attacker.

### EVM public RPC date verification

Confirmed: public Ethereum and BSC JSON RPC can verify spreadsheet dates without explorer accounts or API keys. The top Summary tab appears to display local time that is four hours behind the chain UTC time for many EVM rows.

Examples from `evm-rpc-timestamps.json`:

| Source row | Chain | Tx | Spreadsheet display | Chain time UTC | Confidence |
|---:|---|---|---|---|---|
| 5 | Ethereum | `0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204` | `2023/07/21 10:00:59` | `2023-07-21T14:00:59Z` | confirmed |
| 6 | Ethereum | `0xb5e309a09f479a87f71b1258380d8b8e62c84163364b3b06762927c476c4d655` | `2023/07/22 5:52:11` | `2023-07-22T09:52:11Z` | confirmed |
| 11 | Ethereum | `0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3` | `2023/07/21 10:09:11` | `2023-07-21T14:09:11Z` | confirmed |
| 13 | BSC | `0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1` | `2023/07/21 14:36:20` | `2023-07-21T18:36:20Z` | confirmed |
| 15 | Ethereum | `0x72d855932534ca55ae820f5ed17de8ac729b1f05b093352b5bca19dcf868f26f` | `2023/07/21 14:55:47` | `2023-07-21T18:55:47Z` | confirmed |

Limit: EVM RPC verifies block inclusion times and account addresses. It cannot by itself prove who controlled an account.

## Public tools and workflows worth using now

### 1. Blockstream Esplora API and mempool.space API

Use for BTC address history, UTXOs, tx details, block time, and outspend checks.

Why this matters:

1. Confirmed: both public APIs agreed on all three BTC addresses checked in this task.
2. Confirmed: Esplora exposes `/tx/:txid`, `/tx/:txid/outspend/:vout`, `/tx/:txid/outspends`, `/address/:address`, `/address/:address/txs`, and `/address/:address/utxo`.
3. Confirmed from the cloned Esplora docs: amounts are satoshis, and the API can be self hosted for privacy and security.

Repeatable commands:

```bash
ADDR=bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
curl -sS "https://blockstream.info/api/address/$ADDR" | jq .
curl -sS "https://blockstream.info/api/address/$ADDR/txs" | jq '.[].txid'
curl -sS "https://blockstream.info/api/address/$ADDR/utxo" | jq .

TX=164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187
curl -sS "https://blockstream.info/api/tx/$TX" | jq .
curl -sS "https://blockstream.info/api/tx/$TX/outspends" | jq .
```

Limit: public endpoints leak the queried address set to the service and can rate limit. For a larger case packet, use the same API shape against a self hosted Esplora or mempool instance.

### 2. Ethereum and BSC JSON RPC

Use for EVM timestamp verification independent of spreadsheet formatting and explorer UI.

Repeatable commands:

```bash
TX=0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204
curl -sS https://ethereum.publicnode.com \
  -H 'content-type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getTransactionByHash\",\"params\":[\"$TX\"]}" \
  | jq .result.blockNumber

BLOCK=0x10eb896
curl -sS https://ethereum.publicnode.com \
  -H 'content-type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getBlockByNumber\",\"params\":[\"$BLOCK\",false]}" \
  | jq -r '.result.timestamp' \
  | python3 -c 'import sys,datetime; print(datetime.datetime.fromtimestamp(int(sys.stdin.read(),16), datetime.UTC).isoformat())'
```

Use `https://bsc-dataseed.binance.org/` for BSC rows.

Limit: public RPC endpoints can rate limit and may not expose enriched labels, internal traces, or token metadata consistently. For labels, Etherscan and BscScan free API keys or UI pages are useful, but labels still do not prove control.

### 3. Blockchain.info and BlockCypher cross checks

Use as independent BTC API corroboration for address totals and recent tx history.

Repeatable commands:

```bash
ADDR=bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
curl -sS "https://blockchain.info/rawaddr/$ADDR?limit=50" | jq '{address, final_balance, n_tx, total_received, total_sent}'
curl -sS "https://api.blockcypher.com/v1/btc/main/addrs/$ADDR?limit=50" | jq '{address, balance, final_balance, n_tx, total_received, total_sent}'
```

Limit: API schemas differ and some endpoints paginate or truncate histories. Treat them as corroboration, not the source of truth for demix logic.

### 4. WalletExplorer public API

Use for quick, no key, weak co-spend clustering.

Observed in this task:

| Address | WalletExplorer wallet ID | Confidence |
|---|---|---|
| `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` | `6ba31fe6a6a703ec` | confirmed response |
| `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` | `e2410ffea713c632` | confirmed response |
| `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` | `44582d2a68baaaee` | confirmed response |

Interpretation: WalletExplorer does not publicly cluster the Wasabi deposit, post Wasabi candidate, and live BTC lead together. This weakens any claim that public co-spend clustering alone proves the path.

Repeatable command:

```bash
ADDR=bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl
curl -sS "https://www.walletexplorer.com/api/1/address-lookup?address=$ADDR" | jq .
```

Limit: WalletExplorer says it merges addresses by basic co-spend. Coinjoin transactions are deliberately hostile to simple co-spend clustering, so this is a useful check but not a demix proof.

### 5. GraphSense and Iknaio notebooks

Use for entity graph exploration, path search, TagPacks, address neighbors, address txs, and automation when API access or self hosting is available.

Useful public materials:

1. GraphSense public site says the stack is open source, MIT licensed, supports UTXO and account model ledgers, supports Bitcoin, Ethereum, Tron, and others, and provides REST API workflows.
2. The cloned `graphsense-REST` OpenAPI file exposes address endpoints including `/{currency}/addresses/{address}`, `/entity`, `/links`, `/neighbors`, and transaction endpoints.
3. The cloned `iknaio-api-tutorial` repo has notebooks for inspecting BTC addresses, entity demos, and path search.

Observed limit: unauthenticated calls to `https://api.iknaio.com/stats`, `https://api.iknaio.com/btc/addresses/<address>`, and `/cluster` returned HTTP 401 and were saved in `graphsense-*.json`. Hosted access requires an API key. Self hosting avoids paid vendor dependence but requires infrastructure.

Recommended use: do not start here for the first public audit. Start with Esplora and saved CSV outputs. Use GraphSense after the core public evidence table is stable, especially if William wants path search or entity graph views.

### 6. BlockSci

Use only if a deeper local Bitcoin graph audit is justified.

Why it helps:

1. BlockSci has Python and C++ analysis APIs.
2. It supports heuristic based clustering and change address heuristics.
3. It can work from a full node and can build local analysis data.

Limits from inspected docs:

1. Setup requires a full node first.
2. RPC mode requires `txindex` enabled.
3. Docs cite at least 60 GB RAM to parse Bitcoin as of July 2020, and the chain is larger now.
4. Docs explicitly warn against blindly using one change heuristic for clustering.
5. The inspected repo commit was from 2020, so treat maintenance risk as high.

Recommended use: not the next step for William unless the public API workflow produces a short candidate output set that needs offline ranking.

### 7. Bitcoin MCPs

I found no mature forensic MCP that should be treated as a source of evidence by itself.

Candidate MCPs:

| MCP | Status | Recommendation |
|---|---|---|
| `Bortlesboat/bitcoin-mcp` | Updated 2026-05-18, Python, small repo, local Bitcoin Core or hosted Satoshi API fallback, advertised 49 tools | Possible read only convenience wrapper after code review. Disable or avoid `send_raw_transaction`. Pin commit. No license detected. |
| `runeape-sats/bitcoin-mcp` | Early alpha, Python, local Bitcoin full node, last inspected push 2025-03-28 | Possible reference only. No license detected. |

Limit: an MCP only packages queries. It does not create provenance. Evidence should still cite raw API responses, local node RPC responses, or saved JSON files.

### 8. OXT

OXT has historically been useful for Bitcoin transaction graph visualization. Current status is not dependable for this case. My direct probes to `https://oxt.me/` and transaction or address pages returned local network errors, and current search results include claims that OXT is now defunct. Treat OXT as unavailable unless someone can access it live from a browser.

## Public demix workflow to run next

The public audit can go one step deeper without paid vendors:

1. Confirm the Wasabi deposit address funding path from William controlled accounts.
   Confidence target: confirmed if the source txs came from addresses William recognizes or exchange withdrawal records he can provide.

2. For each Wasabi shaped spend listed above, enumerate every output with:
   `txid`, `vout`, `value_sats`, `address`, `script type`, `spent_by`, `spent_time_utc`, `next hop address`, and `next hop value`.

3. Search for paths from those outputs to any known candidate funding txs:
   `693e7d924bca0c5f8996ee6edf0821b7ce0ffa0d7ccd690842752396f81fbf7f`,
   `f634c560b982a252091fa40540ab31555fefee258c3c0bb0982ce2a58b91ef46`,
   `d60f931dfcc26c267b0e198131efba064bb1e6f4a70c1d8b03c7b468478b092d`,
   `e9073ef4ea2ea53c25ff06f0fbaf043e2c90e2330e22b7ddc752f0bdeafe044f`,
   `5e74975a9d29b9fd7b6ac19202e92e658aaf9f6912230582b0476e9f8be8cb44`,
   `e96fff2f06d1950dbc4a5238e001e5605ef910c0c2950baf053f8d6c02d036cd`,
   and `3200a29a5ef215e73c6d62390425879a86079c14fd77ede2ef173f9642bd0500`.

4. Score any candidate paths only as possible or likely, never confirmed, using:
   value continuity, time gap, script type continuity, consolidation pattern, repeated wallet IDs, and whether independent public tools agree.

5. Preserve all raw JSON for repeatability.

Skeleton command for step 2:

```bash
TX=447484229542bdf306892f60fdd328bdfe7c670e42013af4247302e6d3bf0be8
curl -sS "https://blockstream.info/api/tx/$TX" > "$TX.json"
curl -sS "https://blockstream.info/api/tx/$TX/outspends" > "$TX-outspends.json"
jq -r '.vout[] | [.scriptpubkey_address, .value, .scriptpubkey_type] | @csv' "$TX.json"
jq -r '.[] | [.spent, .txid, .vin] | @csv' "$TX-outspends.json"
```

## Contradictions or unresolved gaps

1. Confirmed: the spreadsheet's visible Summary tab mostly reflects July 21 to July 22, 2023 chain activity, not 2021.
2. Confirmed: the visible top Summary times appear offset from chain UTC by four hours for many EVM rows.
3. Confirmed: the direct candidate to live BTC lead spend happened on `2023-10-19T11:22:51Z`, which aligns with a later 2023 event, not a 2021 event.
4. Unresolved: the Wasabi deposit to post Wasabi candidate bridge remains low confidence. Public co-spend clustering did not prove it.
5. Unresolved: William still needs to identify which source accounts or exchange accounts correspond to the spreadsheet's Ethereum, BSC, THORChain, BTC, and possible exchange withdrawal rows.
6. Unresolved: no public tool can prove hacker identity, exchange account ownership, seed compromise, device compromise, or account login history.

## Recommended next action for William

William should not share seed phrases, private keys, passwords, 2FA codes, or exchange login access.

He should gather exportable records that connect his known accounts to the on chain rows:

1. Exchange withdrawal CSVs or screenshots for July 21 to July 23, 2023, August 17 to October 19, 2023, and any claimed 2021 event.
2. Account names only, not passwords, for the wallet or exchange accounts that owned the source addresses.
3. Any police report, exchange support ticket, or wallet app history that references the tx hashes above.
4. Confirmation whether `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` or `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` ever appeared in his wallet or exchange records.

## Sources consulted

1. Warroom brief: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/WARROOM-BRIEF.md`
2. Visible row inventory: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/summary-visible-rows.csv`
3. Esplora API docs: https://github.com/Blockstream/esplora/blob/master/API.md
4. Mempool repo README: https://github.com/mempool/mempool
5. Wasabi CoinJoin docs: https://docs.wasabiwallet.io/using-wasabi/CoinJoin.html
6. Wasabi coin and transaction graph docs: https://docs.wasabiwallet.io/why-wasabi/Coins.html and https://docs.wasabiwallet.io/why-wasabi/TransactionGraph.html
7. WalletExplorer API and info pages: https://www.walletexplorer.com/api and https://www.walletexplorer.com/info
8. GraphSense site and API docs: https://graphsense.org/ and https://api.ikna.io/
9. Iknaio API tutorial repo: https://github.com/iknaio/iknaio-api-tutorial
10. BlockSci repo and docs: https://github.com/citp/BlockSci
11. Ethereum JSON RPC docs: https://ethereum.org/developers/docs/apis/json-rpc/
12. Bitcoin MCP candidates: https://github.com/Bortlesboat/bitcoin-mcp and https://github.com/runeape-sats/bitcoin-mcp

## Open questions

1. Which exact BTC transaction first moved funds from William controlled infrastructure into `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`?
2. Does William have any exchange record that references `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`, `164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187`, or `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`?
3. Are the spreadsheet rows describing one July 2023 event plus later BTC movements, or do separate 2021 and 2025 events exist in records not yet included?
4. Does a public path search through all Wasabi spend outputs produce a short candidate set, or does WabiSabi ambiguity keep the candidate set too large for a public conclusion?

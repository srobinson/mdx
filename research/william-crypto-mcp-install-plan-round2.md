---
title: William Crypto MCP Install Plan Round 2
type: research
tags: [crypto-theft, mcp, blockchain-forensics, bitcoin, thorchain, wasabi, duckdb, neo4j]
summary: Verified current MCP install commands and trial order for William's crypto theft case, with stale package names and paid-gate caveats separated from no-key tests.
status: active
confidence: high
created: 2026-05-25
updated: 2026-05-25
related:
  - stolen-crypto-case-seed-2026-05-25
  - william-crypto-round1-synthesis
  - william-crypto-mcp-tool-discovery-round1
---

# Executive Summary

The install-first stack should be **DuckDB**, **mempool.space**, **Etherscan**, **Tatum**, and a **patched or direct Midgard route**, followed by MistTrack only after William has a MistTrack plan with OpenAPI access. Several Round 1 commands needed correction: the npm mempool package is `@sanlim/mempool-mcp-server`, the THORChain MCP package installs but hardcodes retired Midgard providers, and the OFAC MCP package currently lacks an npm `bin`, so the README `npx` command fails.

No MCP or vendor trial should be treated as a recovery tool. The goal is to build a defensible evidence table, watch the unspent BTC lead, and identify downstream custodial endpoints that law enforcement or an exchange legal team can act on.

# Detailed Findings

## 1. Install-first ranking

### Rank 1: DuckDB MCP, install now

Purpose: create the canonical evidence database from William's CSV plus all pulled chain evidence.

Current command, verified against PyPI and the package help output:

```bash
mkdir -p /Users/alphab/.mdx/research/data
claude mcp add duckdb --scope user -- \
  uvx mcp-server-duckdb \
  --db-path /Users/alphab/.mdx/research/data/william-case.duckdb \
  --keep-connection
```

Prerequisites: `uv` and Python 3.10 or newer.

Expected output after connection: one `query` tool that can execute SQL against the DuckDB file. The README says `--db-path` is required and `--readonly` plus `--keep-connection` are optional. Local verification of `uvx mcp-server-duckdb --help` showed those exact flags.

Why first: every other tool should write back to this evidence table, rather than becoming scattered chat notes.

Sources: https://github.com/ktanaka101/mcp-server-duckdb , https://pypi.org/project/mcp-server-duckdb/

### Rank 2: mempool.space MCP, install now

Purpose: zero-key Bitcoin checks for UTXOs, transactions, outspends, and mempool activity on the Wasabi deposit, demix candidate, service-like branch, and live watchlist address.

Correct npm package:

```bash
claude mcp add mempool --scope user -- \
  npx -y @sanlim/mempool-mcp-server
```

Optional privacy or local node mode:

```bash
claude mcp add mempool-local --scope user \
  -e MEMPOOL_BASE_URL=http://umbrel.local:3006/api \
  -- npx -y @sanlim/mempool-mcp-server
```

Python alternative:

```bash
claude mcp add mempool-py --scope user \
  -e MEMPOOL_API_URL=mempool.space/api \
  -- uvx --from mempool-mcp mempool-mcp
```

Prerequisites: Node 18 or newer for the npm package, or Python 3.11 or newer for `mempool-mcp`.

Expected output: address info, address transactions, UTXOs, tx details, tx outspends, block data, fees, and mempool data. Local `npx -y @sanlim/mempool-mcp-server --help` confirmed the valid package and the `MEMPOOL_BASE_URL` override.

Correction to Round 1: `@alexandresanlim/mempool-mcp-server` is not published on npm. Use `@sanlim/mempool-mcp-server`.

No credential needed: yes.

Sources: https://github.com/alexandresanlim/mempool-mcp-server , https://pypi.org/project/mempool-mcp/

### Rank 3: Etherscan official MCP, install after William creates a free API key

Purpose: authoritative EVM transaction, address, token transfer, internal transaction, and name tag checks across Ethereum and BNB Smart Chain.

Command from official Etherscan MCP docs:

```bash
export ETHERSCAN_API_KEY='<from etherscan.io>'
claude mcp add --transport http etherscan --scope user \
  https://mcp.etherscan.io/mcp \
  --header "Authorization: Bearer ${ETHERSCAN_API_KEY}"
```

Prerequisites: free Etherscan API key. Etherscan states its V2 system covers 60 plus supported EVM chains through one account and API key, including BNB Smart Chain via chain selection.

Expected output: EVM address balances, normal transactions, internal transactions, ERC-20 and NFT transfers, logs, contract metadata, and name tag lookups through the hosted HTTP MCP.

No credential needed: no. It needs an Etherscan key.

Sources: https://docs.etherscan.io/ai/mcp , https://docs.etherscan.io/introduction

### Rank 4: Tatum Blockchain MCP, install after free key

Purpose: multi-chain fallback for BTC, ETH, BNB, address history, wallet portfolio, block lookup, RPC gateway calls, and malicious-address checks.

Current command, verified against npm metadata and CLI help:

```bash
export TATUM_API_KEY='<from dashboard.tatum.io>'
claude mcp add tatum --scope user \
  -e TATUM_API_KEY="${TATUM_API_KEY}" \
  -- npx -y @tatumio/blockchain-mcp
```

Alternative one-shot config:

```bash
claude mcp add-json tatum '{"command":"npx","args":["-y","@tatumio/blockchain-mcp"],"env":{"TATUM_API_KEY":"<key>"}}'
```

Prerequisites: Tatum API key from the Tatum dashboard. Tatum's page says the key is required for all MCP integrations and its README lists 130 plus networks.

Expected output: 10 blockchain data tools and 4 RPC gateway tools. Local help output confirmed the current CLI exposes `--api-key`, `TATUM_API_KEY`, and 14 total tools.

No credential needed: no, apart from `--help`.

Sources: https://github.com/tatumio/blockchain-mcp , https://tatum.io/mcp

### Rank 5: THORChain Midgard, use direct API now and patch MCP before relying on it

Purpose: prove the ETH to BTC THORChain swap legs from the seed file.

Current direct API, verified live:

```bash
curl -fsS \
  'https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204'

curl -fsS \
  'https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C'
```

Important: omit the `0x` prefix for the EVM hash when querying Midgard by `txid`. With `0x`, the current endpoint returned zero actions. Without `0x`, the endpoint returned one successful swap for each known example.

Live verification on May 25, 2026:

- `655A2A55...D204`: one `swap` action, status `success`, `125.44715147 ETH` in from `0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0`, `7.29622713 BTC` out to `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`.
- `40A3D546...59E2C`: one `swap` action, status `success`, `727.29568000 ETH` in, `31.37643194 BTC` out to `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`.

Published MCP package:

```bash
claude mcp add thorchain --scope user -- \
  npx -y @missionsquad/mcp-thorchain
```

Caveat: the install command is valid and the server starts, but the package currently hardcodes retired Nine Realms endpoints and an old Liquify host path. THORChain's current developer docs state that Nine Realms retired `*.ninerealms.com` endpoints in April 2025 and that clients should use `gateway.liquify.com/chain/thorchain_midgard` or `midgard.thorchain.network`. Local package inspection showed `@missionsquad/mcp-thorchain` still references `https://midgard.ninerealms.com` and `https://midgard.thorchain.liquify.com`. Do not rely on the MCP package for evidence until it is patched or upstream updates provider URLs.

Patch plan:

```bash
git clone https://github.com/MissionSquad/mcp-thorchain.git /tmp/mcp-thorchain
cd /tmp/mcp-thorchain
# edit src/api-client.ts providers to:
# https://gateway.liquify.com/chain/thorchain_midgard
# https://midgard.thorchain.network
npm install
npm run build
claude mcp add thorchain-patched --scope user -- node /tmp/mcp-thorchain/dist/index.js
```

No credential needed: yes, for direct Midgard and for the MCP package.

Sources: https://github.com/MissionSquad/mcp-thorchain , https://dev.thorchain.org/concepts/connecting-to-thorchain.html

### Rank 6: MistTrack MCP, do not run until OpenAPI plan is confirmed

Purpose: direct label, risk, malicious funds, counterparty, and recursive fund-flow analysis for the Wasabi deposit, service-like branch, demix candidate, and live address.

Current command, verified against official README, npm metadata, and CLI help:

```bash
export MISTTRACK_API_KEY='<from MistTrack dashboard with OpenAPI access>'
claude mcp add misttrack --scope user \
  -e MISTTRACK_API_KEY="${MISTTRACK_API_KEY}" \
  -- npx -y misttrack@latest
```

Equivalent explicit key form:

```bash
claude mcp add misttrack --scope user -- \
  npx -y misttrack@latest --key '<key>'
```

Prerequisites: MistTrack API key and a MistTrack plan that supports OpenAPI access. The README says both are required.

Expected output: chain detection, labels, overview, profile, counterparties, risk score V3, malicious fund checks, dashboard links, explorer URLs, and recursive transaction analysis with depth 1 to 3.

No credential needed: only `--help` can be tested without a key. Real checks need a MistTrack OpenAPI key.

Sources: https://github.com/slowmist/MistTrackMCP , https://docs.misttrack.io/openapi/overview

### Rank 7: Bitquery MCP, use after the free developer quota is understood

Purpose: independent cross-chain graph queries and Coinpath style money-flow checks.

Install URL:

```bash
claude mcp add --transport http bitquery --scope user \
  https://mcp.bitquery.io
```

For clients that support OAuth, the first connection should open Bitquery login. For clients without OAuth, Bitquery supports appending `?token=...`, but their own docs warn that URL tokens can leak through logs or shell history. Prefer OAuth or a bearer-token capable client.

Prerequisites: Bitquery account. The Bitquery MCP page recommends OAuth 2.1 and says tokens cache for about 30 days. The Coinpath product page lists a free developer plan with 1,000 trial points, 10 rows per request, and 10 requests per minute. Expect limits.

No credential needed: no.

Sources: https://mcp.bitquery.io/ , https://docs.bitquery.io/docs/usecases/MCP/ , https://bitquery.io/products/coinpath

### Rank 8: Neo4j MCP, install after DuckDB schema is stable

Purpose: materialize the evidence graph for addresses, transactions, services, swaps, UTXOs, clusters, labels, and confidence levels.

Recommended official server command:

```bash
export NEO4J_URI='bolt://localhost:7687'
export NEO4J_USERNAME='neo4j'
export NEO4J_PASSWORD='<password>'
claude mcp add neo4j --scope user \
  -e NEO4J_URI="${NEO4J_URI}" \
  -e NEO4J_USERNAME="${NEO4J_USERNAME}" \
  -e NEO4J_PASSWORD="${NEO4J_PASSWORD}" \
  -e NEO4J_DATABASE=neo4j \
  -e NEO4J_TELEMETRY=false \
  -- uvx neo4j-mcp-server
```

Prerequisites: local Neo4j or AuraDB instance.

Expected output: schema inspection, read Cypher, write Cypher, and GDS procedure listing. Local `uvx neo4j-mcp-server --help` verified the current command and environment variable names.

No credential needed: no, unless only checking help.

Sources: https://github.com/neo4j/mcp , https://github.com/neo4j-contrib/mcp-neo4j

### Rank 9: Excalidraw MCP, install after graph facts are settled

Purpose: create a one-page evidence diagram for IC3, FBI, or exchange legal packets.

Official remote:

```bash
claude mcp add --transport http excalidraw --scope user \
  https://mcp.excalidraw.com
```

Local full canvas toolkit if iterative editing and exports are needed:

```bash
git clone https://github.com/yctimlin/mcp_excalidraw.git /tmp/mcp_excalidraw
cd /tmp/mcp_excalidraw
npm ci
npm run build
PORT=3000 npm run canvas
claude mcp add excalidraw-local --scope user \
  -e EXPRESS_SERVER_URL=http://127.0.0.1:3000 \
  -e ENABLE_CANVAS_SYNC=true \
  -- node /tmp/mcp_excalidraw/dist/index.js
```

Correction: `@excalidraw/excalidraw-mcp` is not published on npm. Use the official remote, the `.mcpb` release, or source build. The yctimlin local server is better for repeatable exports and element-level edits.

No credential needed: yes for the public remote and local build.

Sources: https://github.com/excalidraw/excalidraw-mcp , https://github.com/yctimlin/mcp_excalidraw

### Rank 10: OFAC MCP, use only with a local-install workaround or skip in favor of Tatum/AnChain for address screening

Purpose: sanctions screening. Useful for entity names and SDN list context, but weaker for crypto address checking than Tatum, AnChain, or direct OFAC data workflows.

Package status: `@easysolutions906/mcp-ofac` exists on npm at version `1.0.2`, but it has no `bin` entry. Local verification showed the README command fails:

```bash
npx -y @easysolutions906/mcp-ofac
# npm error: could not determine executable to run
```

Workaround:

```bash
mkdir -p /Users/alphab/.mdx/tools/ofac-mcp
cd /Users/alphab/.mdx/tools/ofac-mcp
npm init -y
npm install @easysolutions906/mcp-ofac
claude mcp add ofac --scope user -- \
  node /Users/alphab/.mdx/tools/ofac-mcp/node_modules/@easysolutions906/mcp-ofac/src/index.js
```

Expected output: the server loads 18,712 SDN entries with a 2026-03-13 publish date, then exposes name screening, batch screening, entity lookup, search, and stats. It is not a robust wallet-address MCP for William's case. The package README and related DEV article discuss wallet screening through a hosted REST API that uses an API key, which is a different surface from the local MCP package.

No credential needed: yes for local name screening, no for the hosted REST API.

Sources: https://www.npmjs.com/package/@easysolutions906/mcp-ofac , https://dev.to/easysolutions906/ofac-sanctions-screening-for-crypto-and-defi-a-developers-guide-3fj1

## 2. Tools that need keys and where they come from

| Tool | Needs key | Where to get it | Paid-risk note |
|---|---:|---|---|
| Etherscan MCP | Yes | Etherscan account API key | Free tier is enough for first pass. Watch rate limits. |
| Tatum MCP | Yes | Tatum dashboard | Free key exists. Avoid write or transaction tools. Monitor quota. |
| MistTrack MCP | Yes | MistTrack dashboard, OpenAPI access | Do not assume free. README requires a plan that supports OpenAPI. |
| AnChain AML MCP | Yes | aml.anchainai.com or AnChain sales/support | Commercial AML API. Use after raw facts are normalized. |
| Caudena Prism MCP | Yes | Existing Caudena account, demo, or trial | No local install. Commercial account likely. Best for demix confirmation if budget exists. |
| Bitquery MCP | Yes | OAuth login or account token | Free developer limits are tight. Avoid URL token if possible. |
| Neo4j MCP | Yes | Local Neo4j or AuraDB credentials | Free local or AuraDB tier can work. |
| Excalidraw MCP | Usually no | Remote MCP or local build | No case-data risk if only drawing sanitized evidence. |
| DuckDB MCP | No | Local file | No vendor exposure. |
| mempool.space MCP | No | Public API or local mempool instance | Public API leaks query interest to mempool.space. Use local node if privacy matters. |
| THORChain Midgard direct | No | Public Midgard endpoint | Include `x-client-id` if making many requests. |
| OFAC local MCP | No | npm local install | Package install workaround needed. Hosted REST API uses keys. |

## 3. What can be tested without credentials today

Test now:

```bash
# BTC live lead, zero key
curl -fsS 'https://mempool.space/api/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g'

# THORChain swap proof, zero key, no 0x prefix
curl -fsS 'https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204'

# DuckDB tool help, zero key
uvx mcp-server-duckdb --help

# mempool npm package help, zero key
npx -y @sanlim/mempool-mcp-server --help

# MistTrack command help, zero key, no data calls
npx -y misttrack@latest --help

# Tatum command help, zero key, no data calls
npx -y @tatumio/blockchain-mcp --help
```

Live BTC lead check on May 25, 2026 returned:

```json
{
  "funded_txo_count": 2,
  "funded_txo_sum": 649998534,
  "spent_txo_count": 0,
  "spent_txo_sum": 0,
  "tx_count": 2,
  "mempool_tx_count": 0
}
```

Interpretation: `6.49998534 BTC` remains unspent and no mempool spend was visible at the moment of testing. This preserves Round 1's watchlist priority.

## 4. Avoid list until budget, legal process, or package fix

Avoid for now:

1. **Caudena Prism MCP** until William has an account, trial, or budget. It is promising for UTXO path confirmation, but the public page gives no installable local package and says authentication uses an existing Caudena account.
2. **AnChain AML MCP** until the raw evidence table exists. The repo requires Python 3.12, `uv`, source clone, and an AnChain API key. Use it for sanctions and report narration after the transaction facts are clean.
3. **MistTrack paid recursion** until the exact query batch is scoped. Recursive tracing can burn API credits. Start with labels and risk on the smallest address set.
4. **THORChain MCP unpatched package** for evidence. It starts, but provider URLs are stale. Direct Midgard curl is currently more reliable.
5. **OFAC local npm command as documented** because the package lacks a `bin`. Use the workaround only if local SDN name screening matters. For wallet sanctions checks, prefer Tatum, AnChain, or direct OFAC data ingestion.
6. **Bitquery URL token form** unless no OAuth path works. URL tokens can leak through history and logs. Use OAuth or a bearer-token capable client.
7. **Any crypto recovery service that asks for up-front fees**. Not an MCP issue, but still the main operational scam risk.

## 5. First 10 queries to run once installed

Run these in order. Persist each result to DuckDB before moving to the next query.

1. **DuckDB import and profile**

   ```sql
   CREATE OR REPLACE TABLE source_csv AS
   SELECT * FROM read_csv_auto('/Users/alphab/Downloads/Stolen Crypto July 2021 - Summary.csv', all_varchar=true);
   SELECT COUNT(*) AS rows, * EXCLUDE () FROM source_csv LIMIT 5;
   ```

   Expected output: row count, actual CSV columns, sample rows, and confirmation that the source dates are July 2023 even though the filename says 2021.

2. **Etherscan transaction proof for the first THORChain router transaction**

   Prompt:

   ```text
   On Ethereum mainnet, fetch full details, receipt status, decoded input if available, internal transfers, ERC-20 transfers, and from/to addresses for tx 0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204. Return JSON with block number, timestamp, from, to, ETH value, token transfers, internal transfers, and any name tags.
   ```

   Expected output: transaction details linking victim wallet `0xaadd5...f1f0` to the THORChain path.

3. **Etherscan victim wallet sweep**

   Prompt:

   ```text
   For Ethereum address 0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0, list outbound transactions from 2023-07-21 through 2023-07-23 UTC, including ETH, ERC-20 transfers, internal transfers, to-address labels, and transaction hashes.
   ```

   Expected output: normalized outbound movement table for the primary victim wallet.

4. **Etherscan or Tatum BNB side check**

   Prompt:

   ```text
   On BNB Smart Chain, check the victim wallets from the case file for outbound BNB and BEP-20 movement from 2023-07-21 through 2023-07-23 UTC. Return tx hash, from, to, asset, amount, timestamp, and known labels.
   ```

   Expected output: either confirmation of the `8.6 BNB` loss surface or a gap that needs manual BscScan follow-up.

5. **Midgard swap proof for `655A...D204`**

   Direct API or patched MCP query:

   ```text
   Query Midgard actions for txid 655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204 with no 0x prefix. Return action type, status, inbound address, inbound asset and amount, outbound address, outbound asset and amount, outbound txid, and height.
   ```

   Expected output: one successful swap, `125.44715147 ETH` to `7.29622713 BTC`, outbound address `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`.

6. **Midgard swap proof for `40A3...9E2C`**

   ```text
   Query Midgard actions for txid 40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C with no 0x prefix. Return the same fields as query 5.
   ```

   Expected output: one successful swap, `727.29568000 ETH` to `31.37643194 BTC`, outbound address `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`.

7. **mempool.space Wasabi deposit address state**

   Prompt:

   ```text
   For BTC address bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s, return address stats, all funded UTXOs, all spends, transaction ids, output indexes, amounts in BTC and sats, confirmation status, and outspends.
   ```

   Expected output: seven funded and seven spent UTXOs totaling `40.70902128 BTC`, plus the spend transactions into Wasabi CoinJoin rounds.

8. **mempool.space demix candidate and October 2023 spend**

   Prompt:

   ```text
   For BTC address bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl and transaction 1962037495cfc6f39cd0c525b78fdcffddb98de34babdcf785b12208152e9bb2, return address stats, tx details, input addresses, output addresses, amounts, and outspend status. Mark the address as low-confidence demix candidate.
   ```

   Expected output: `35.9705224 BTC` path toward `bc1qtvj76tqmhazw8dl5yx9ep9hs32xxlcletrf6p8`, with confidence still inherited from the low-confidence demix candidate.

9. **mempool.space live watchlist address check**

   Prompt:

   ```text
   For BTC address bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g, return address stats, UTXOs, mempool transactions, last seen tx timestamp, and whether any UTXO has been spent.
   ```

   Expected output: `6.49998534 BTC` funded, `0 BTC` spent, `0` mempool transactions unless movement has occurred since this report.

10. **MistTrack plus sanctions label triage on the minimal address set**

   Prompt:

   ```text
   Screen these BTC and ETH addresses with MistTrack labels, risk score, malicious fund exposure, and sanctions flags: bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s, bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl, bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g, 17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva, 0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F, 0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0. Return labels, confidence, risk reasons, and dashboard URLs. Do not run recursive tracing deeper than 1 hop without explicit approval.
   ```

   Expected output: first independent commercial labels for the high-volume service-like address and the live lead, with API spend contained.

## 6. DuckDB persistence plan

Create the following tables. Keep raw JSON alongside normalized columns so later analysts can reproduce the extraction.

```sql
CREATE TABLE IF NOT EXISTS case_addresses (
  address TEXT PRIMARY KEY,
  chain TEXT NOT NULL,
  role TEXT NOT NULL,
  confidence TEXT NOT NULL,
  source TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS evm_transactions (
  tx_hash TEXT PRIMARY KEY,
  chain TEXT NOT NULL,
  block_number BIGINT,
  block_time TIMESTAMP,
  from_address TEXT,
  to_address TEXT,
  native_value_raw TEXT,
  native_value_decimal DECIMAL(38,18),
  status TEXT,
  label_from TEXT,
  label_to TEXT,
  raw_json JSON,
  source_tool TEXT,
  fetched_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evm_token_transfers (
  id TEXT PRIMARY KEY,
  tx_hash TEXT,
  chain TEXT,
  token_contract TEXT,
  token_symbol TEXT,
  from_address TEXT,
  to_address TEXT,
  amount_raw TEXT,
  amount_decimal DECIMAL(38,18),
  raw_json JSON,
  source_tool TEXT
);

CREATE TABLE IF NOT EXISTS thorchain_actions (
  txid TEXT PRIMARY KEY,
  action_type TEXT,
  status TEXT,
  in_address TEXT,
  in_asset TEXT,
  in_amount_raw TEXT,
  out_address TEXT,
  out_asset TEXT,
  out_amount_raw TEXT,
  out_txid TEXT,
  out_height BIGINT,
  raw_json JSON,
  source_url TEXT,
  fetched_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS btc_transactions (
  txid TEXT PRIMARY KEY,
  block_time TIMESTAMP,
  status_confirmed BOOLEAN,
  raw_json JSON,
  source_tool TEXT,
  fetched_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS btc_utxos (
  txid TEXT,
  vout INTEGER,
  address TEXT,
  value_sats BIGINT,
  spent BOOLEAN,
  spent_by_txid TEXT,
  source_tool TEXT,
  fetched_at TIMESTAMP DEFAULT now(),
  PRIMARY KEY (txid, vout)
);

CREATE TABLE IF NOT EXISTS labels_and_risk (
  address TEXT,
  chain TEXT,
  provider TEXT,
  label TEXT,
  risk_score TEXT,
  risk_level TEXT,
  risk_reasons JSON,
  confidence TEXT,
  dashboard_url TEXT,
  raw_json JSON,
  fetched_at TIMESTAMP DEFAULT now(),
  PRIMARY KEY (address, chain, provider, fetched_at)
);

CREATE TABLE IF NOT EXISTS evidence_events (
  event_id TEXT PRIMARY KEY,
  event_time TIMESTAMP,
  event_type TEXT,
  chain TEXT,
  tx_hash TEXT,
  from_address TEXT,
  to_address TEXT,
  asset TEXT,
  amount_decimal DECIMAL(38,18),
  confidence TEXT,
  source_table TEXT,
  source_ref TEXT,
  narrative TEXT
);
```

Initial import task:

```sql
INSERT OR REPLACE INTO case_addresses VALUES
('bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s','BTC','Wasabi deposit','high','case seed','THORChain BTC outbound address'),
('bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl','BTC','demix candidate','low','prior demix review','Treat as investigative lead'),
('bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g','BTC','live watchlist lead','low','Round 1 tracing','6.49998534 BTC unspent as of 2026-05-25'),
('17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva','BTC','service-like branch','medium','Round 1 public data','Very high volume address, unlabeled'),
('0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F','ETH','FixedFloat wallet from CSV','medium','case seed','Needs Etherscan label and retention follow-up');
```

## 7. Neo4j persistence plan

Create graph nodes and relationships only from data already landed in DuckDB. DuckDB remains the canonical table store. Neo4j is for relationship exploration and diagrams.

Recommended node labels:

- `:Address {address, chain, role, confidence}`
- `:Transaction {txid, chain, time, source_tool}`
- `:UTXO {txid, vout, value_sats, spent}`
- `:Service {name, category, confidence}`
- `:Label {provider, value, confidence}`
- `:Case {id, name}`
- `:EvidenceSource {name, url, fetched_at}`

Recommended relationships:

```cypher
(:Case)-[:CONTAINS]->(:Address)
(:Address)-[:SENT {asset, amount, time, confidence}]->(:Transaction)
(:Transaction)-[:OUTPUT {asset, amount, vout}]->(:Address)
(:Transaction)-[:CREATED]->(:UTXO)
(:UTXO)-[:SPENT_BY]->(:Transaction)
(:Address)-[:HAS_LABEL]->(:Label)
(:Label)-[:ASSERTED_BY]->(:EvidenceSource)
(:Address)-[:POSSIBLE_CLUSTER {provider, confidence}]->(:Address)
(:Address)-[:POSSIBLE_SERVICE {confidence}]->(:Service)
(:Transaction)-[:THORCHAIN_SWAP_TO]->(:Transaction)
```

First graph load should include only high and medium confidence edges. The low-confidence Wasabi demix branch should be visibly marked as `confidence: "low"` and never merged into the victim path as a proven fact.

# Sources Consulted

## Official vendor and project sources

- Etherscan MCP docs: https://docs.etherscan.io/ai/mcp
- Etherscan V2 introduction and supported-chain context: https://docs.etherscan.io/introduction
- MistTrack MCP official repo: https://github.com/slowmist/MistTrackMCP
- MistTrack OpenAPI docs: https://docs.misttrack.io/openapi/overview
- Tatum Blockchain MCP repo: https://github.com/tatumio/blockchain-mcp
- Tatum MCP page: https://tatum.io/mcp
- alexandresanlim mempool MCP repo: https://github.com/alexandresanlim/mempool-mcp-server
- mempool-mcp PyPI alternative: https://pypi.org/project/mempool-mcp/
- THORChain MCP repo: https://github.com/MissionSquad/mcp-thorchain
- THORChain current endpoint docs: https://dev.thorchain.org/concepts/connecting-to-thorchain.html
- DuckDB MCP repo: https://github.com/ktanaka101/mcp-server-duckdb
- DuckDB MCP PyPI: https://pypi.org/project/mcp-server-duckdb/
- AnChain AML MCP repo: https://github.com/AnChainAI/aml-mcp
- Caudena Prism MCP announcement: https://caudena.com/prism-mcp-the-first-ai-native-blockchain-intelligence-protocol/
- Bitquery MCP page: https://mcp.bitquery.io/
- Bitquery MCP docs: https://docs.bitquery.io/docs/usecases/MCP/
- Bitquery Coinpath page and pricing: https://bitquery.io/products/coinpath
- Neo4j official MCP repo: https://github.com/neo4j/mcp
- Neo4j Labs MCP repo: https://github.com/neo4j-contrib/mcp-neo4j
- Excalidraw official MCP repo: https://github.com/excalidraw/excalidraw-mcp
- yctimlin Excalidraw MCP repo: https://github.com/yctimlin/mcp_excalidraw
- OFAC MCP package: https://www.npmjs.com/package/@easysolutions906/mcp-ofac
- OFAC MCP related article: https://dev.to/easysolutions906/ofac-sanctions-screening-for-crypto-and-defi-a-developers-guide-3fj1

## Local verification performed

- `npm view misttrack`, `npx -y misttrack@latest --help`
- `npm view @tatumio/blockchain-mcp`, `npx -y @tatumio/blockchain-mcp --help`
- `npm view @sanlim/mempool-mcp-server`, `npx -y @sanlim/mempool-mcp-server --help`
- `npm view @missionsquad/mcp-thorchain`, `npx -y @missionsquad/mcp-thorchain --help`, plus package source inspection for hardcoded provider URLs
- `npm view @easysolutions906/mcp-ofac`, `npx -y @easysolutions906/mcp-ofac` failure, local install plus `node src/index.js` workaround
- `python3 -m pip index versions mcp-server-duckdb`, `uvx mcp-server-duckdb --help`
- `python3 -m pip index versions neo4j-mcp-server`, `uvx neo4j-mcp-server --help`
- Live `curl` checks against `mempool.space/api/address/...` and `gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=...`

# Source Quality Assessment

High confidence:

- Package names and commands verified through npm, PyPI, and local `--help` runs.
- THORChain endpoint migration verified against current THORChain developer docs and live direct API calls.
- DuckDB, Etherscan, Tatum, MistTrack, Neo4j, and Excalidraw install surfaces are backed by official docs or official repos.

Medium confidence:

- Caudena Prism capabilities are based on vendor announcement material. Trial access is needed to verify tool names, pricing, and output quality.
- AnChain AML install is repo-backed, but API pricing and exact quota behavior require AnChain account access.
- Bitquery Coinpath value for this case depends on whether free developer limits allow enough rows for useful flow queries.

Known gaps:

- No paid MistTrack, Caudena, AnChain, or Bitquery credentials were available in this round, so data calls from those tools were not run.
- The THORChain MCP package was not patched during this round. The direct API path was verified instead.
- OFAC local MCP appears focused on name screening, while wallet-address sanctions screening is better handled by another provider or direct OFAC data ingestion.

# Open Questions

1. Does William have or want to create accounts for Etherscan, Tatum, MistTrack, Bitquery, AnChain, or Caudena?
2. Should the THORChain MCP be fork-patched locally, or should the project use direct Midgard API calls for this case?
3. Does William need a local-only privacy posture for BTC lookups? If yes, use a self-hosted mempool instance instead of public mempool.space.
4. Which provider, if any, can independently label `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` without a sales process?
5. Should the final evidence packet include only high-confidence facts, or a separate annex for low-confidence leads such as the demix candidate?

# Actionable Takeaways

1. Install DuckDB and mempool.space MCP immediately. Both are no-key, low-risk, and directly useful.
2. Use direct Midgard API calls now. Patch `@missionsquad/mcp-thorchain` later if MCP parity matters.
3. Create Etherscan and Tatum free keys next. They cover the ETH, BNB, and fallback BTC data layer.
4. Delay MistTrack until the exact address batch is ready and OpenAPI access is confirmed.
5. Treat Caudena and AnChain as paid verification layers, not first-pass infrastructure.
6. Build DuckDB first, then Neo4j, then Excalidraw. Tables before graph, graph before diagram.
7. Preserve the confidence boundary: the live `6.49998534 BTC` address is a watchlist lead because the demix candidate is low confidence.

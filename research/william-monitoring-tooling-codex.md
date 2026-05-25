# William Crypto Monitoring and Tooling Plan

Date: 2026-05-25

Status: orchestrator replacement for the third Codex lane after the pane exceeded the timebox. It uses the existing dossier, live data snapshots in `~/.mdx/research/data/william-live-check-2026-05-25/`, and current package checks captured by the Codex pane.

## Executive Summary

The technical lane should optimize for speed, repeatability, and clean evidence. Do not try to "break" Wasabi. Treat the Wasabi trail as an analytics validation problem and focus local tooling on:

1. Keeping the live BTC target under watch.
2. Building a complete transaction inventory from the CSV.
3. Preserving raw API responses and screenshots.
4. Producing a paid analytics packet that asks the right questions.
5. Escalating only validated service exposure to exchanges, law enforcement, or counsel.

The strongest live technical target remains:

```text
bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
6.49998534 BTC funded
0 BTC spent
0 mempool txs in the 2026-05-25 Blockstream snapshot
```

## Monitoring Targets

### Bitcoin

| Target | Role | Current action |
|---|---|---|
| `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s` | Wasabi deposit address | Preserve as root BTC conversion destination. No balance. |
| `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl` | Low confidence demix withdrawal candidate | Monitor only as candidate until paid analytics validates. |
| `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` | Live unspent BTC lead | High priority alert target. |
| `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` | Probable Binance cluster branch | Preserve attribution evidence and monitor for related movement. |
| `bc1qtvj76tqmhazw8dl5yx9ep9hs32xxlcletrf6p8` | Downstream candidate branch | Monitor as part of candidate trail. |
| `bc1q7x6kj7lg9ls2g6s3wm644s5tuqkkg89dp5t532` | March 2026 dust source | Treat as noise unless new facts connect it. |

### THORChain

| Txid | Role |
|---|---|
| `655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204` | THORSwap ETH to BTC conversion, 125.44715147 ETH in, 7.29622713 BTC out to Wasabi deposit address. |
| `40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C` | THORSwap ETH to BTC conversion, 727.29568000 ETH in, 31.37643194 BTC out to Wasabi deposit address. |

### EVM Victim Wallets

Monitor as source wallets and ownership proof targets:

```text
0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0
0x1c0b5b8d36587d0516839df7ebfb49ad8f3c543c
0x055e6b081f175db1170350ba4f23e3a8e0895492
0xd20a9ed00e37fdaef0a064bc32feb10845053f09
0xa30e54cb3593c6afca653621c4d3ee2105f015aa
0xdfb05c98320d126bcc74f6eb7960e99669dcd49a
0x9dc08da4cbf74f81cffb54cecbd8fdf6554e1d34
0x2656269bb878ca0c4250a0df4c15a9cfca0c21ac
0xfa5f6ed82ae1eac484b91ccde42fe7d64cb68d03
0xf40c09c782c74e932b81473ae68b078f31a358f6
```

## Local Data Store

Create a case data directory:

```bash
case_dir="$HOME/.mdx/research/data/william-live-check-$(date -u +%Y-%m-%d)"
mkdir -p "$case_dir"
```

Preserve source hashes:

```bash
shasum -a 256 "$HOME/Downloads/Stolen Crypto July 2021 - Summary.csv" \
  "$HOME/.mdx/research/william-crypto-case-dossier.md" \
  > "$case_dir/source-hashes.txt"
```

The Codex lane already captured live snapshots under:

```text
/Users/alphab/.mdx/research/data/william-live-check-2026-05-25/
```

This folder includes Blockstream, mempool.space, THORChain Midgard, outspend, and package status data.

## Open Source and Low Cost Stack

### Bitcoin

Use Blockstream Esplora first because it is simple and does not need an API key.

```bash
addr="bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g"
curl -fsS "https://blockstream.info/api/address/$addr" \
  > "$case_dir/blockstream-address-$addr.json"
curl -fsS "https://blockstream.info/api/address/$addr/utxo" \
  > "$case_dir/blockstream-utxo-$addr.json"
curl -fsS "https://blockstream.info/api/address/$addr/txs/mempool" \
  > "$case_dir/blockstream-mempool-$addr.json"
```

Use mempool.space as a second source:

```bash
curl -fsS "https://mempool.space/api/address/$addr" \
  > "$case_dir/mempool-address-$addr.json"
curl -fsS "https://mempool.space/api/address/$addr/txs/mempool" \
  > "$case_dir/mempool-mempool-$addr.json"
```

### THORChain

Use direct Midgard API calls. The known good pattern is uppercase txid without `0x`.

```bash
txid="655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204"
curl -fsS "https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=$txid" \
  > "$case_dir/midgard-actions-$txid.json"
```

### EVM Chains

Use Etherscan and BscScan for transaction receipts and address histories. API keys are helpful for stable rate limits.

Recommended fields to collect:

- transaction hash
- block number
- timestamp
- from
- to
- value
- token transfer logs
- gas payer
- method signature
- explorer URL

### Local Analysis

Use DuckDB for the ledger once `transaction-inventory.csv` exists:

```bash
duckdb "$case_dir/william.duckdb" <<'SQL'
CREATE TABLE IF NOT EXISTS tx_inventory AS
SELECT * FROM read_csv_auto('/Users/alphab/.mdx/research/transaction-inventory.csv');
SELECT chain, service, count(*) AS txs, sum(amount_native) AS amount
FROM tx_inventory
GROUP BY chain, service
ORDER BY chain, amount DESC;
SQL
```

## MCP Status

Current package checks from 2026-05-25:

| Tool | Status | Use |
|---|---|---|
| `mcp-server-duckdb` | PyPI `1.1.0` available | Good local analytics candidate. |
| `@sanlim/mempool-mcp-server` | npm `1.0.1` available | Candidate for Bitcoin mempool data. Direct API remains simpler. |
| `mempool-mcp` | PyPI `0.1.4` available, npm package absent | Python option to test later. |
| `@missionsquad/mcp-thorchain` | npm `1.0.0` available | Do not rely on it until endpoint freshness is verified. Direct Midgard is safer. |
| `misttrack` | npm `1.0.7` available | Only useful with MistTrack API access. |
| `@tatumio/blockchain-mcp` | npm `1.0.5` available | Broad multi-chain option. Likely needs Tatum credentials. |
| `@easysolutions906/mcp-ofac` | npm `1.0.2` available | Sanctions name screening only, not core tracing. |
| `@anchainai/aml-mcp` | npm 404 in live check | Skip until vendor supplies current package or access path. |

## Alerting Plan

### High Priority Alerts

Watch the live BTC address every 10 minutes:

```bash
#!/usr/bin/env bash
set -euo pipefail

addr="bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g"
state="$HOME/.mdx/research/data/william-monitor-state/$addr.json"
tmp="$(mktemp)"
mkdir -p "$(dirname "$state")"

curl -fsS "https://blockstream.info/api/address/$addr" > "$tmp"

if [ -f "$state" ] && ! cmp -s "$state" "$tmp"; then
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  cp "$tmp" "$HOME/.mdx/research/data/william-monitor-state/$addr.changed.$ts.json"
  printf 'CHANGE DETECTED %s %s\n' "$ts" "$addr"
fi

mv "$tmp" "$state"
```

Add a second check for mempool spends:

```bash
curl -fsS "https://blockstream.info/api/address/$addr/txs/mempool"
```

If this returns a non-empty array, treat it as urgent.

### What To Capture On Movement

1. UTC detection time.
2. Raw address JSON from Blockstream and mempool.space.
3. Raw transaction JSON for each new txid.
4. Outspend data for relevant txids.
5. Screenshots from two explorers.
6. Output addresses and values.
7. Any known service attribution.
8. Update email to William, IC3, local police, FBI contact, and counsel if retained.

### Failure Modes

- Public APIs can rate limit or be unavailable.
- Address monitoring may miss first seen time if the check interval is too slow.
- Dust can trigger noisy changes.
- Wasabi demix attribution is probabilistic and should not be presented as fact.
- Exchange cluster labels from public tools are not enough for legal process on their own.

## Transaction Inventory Build Plan

Create:

```text
/Users/alphab/.mdx/research/transaction-inventory.csv
```

Required columns:

```text
case_id,source_file,source_row,incident_date_claimed,observed_timestamp_utc,chain,txid,explorer_url,asset,amount_native,amount_usd_at_time,from_address,to_address,service_hint,service_confidence,role,evidence_file,status,current_owner_hypothesis,next_action,notes
```

Parsing rules:

1. Preserve the source CSV exactly as received.
2. Skip the first three summary rows.
3. Treat the fourth non-empty line as the transaction header.
4. Stop at the first blank logical row after transaction records.
5. Normalize txids by chain:
   - Ethereum and BSC txids retain `0x`.
   - THORChain Midgard lookup uses uppercase txid without `0x`.
   - Bitcoin txids are lowercase hex.
6. Add one derived row for each major BTC lead even if it is not in the original CSV.
7. Attach local evidence JSON paths where available.

Example rows to include:

```csv
case_id,source_file,source_row,incident_date_claimed,observed_timestamp_utc,chain,txid,explorer_url,asset,amount_native,amount_usd_at_time,from_address,to_address,service_hint,service_confidence,role,evidence_file,status,current_owner_hypothesis,next_action,notes
william-crypto,/Users/alphab/Downloads/Stolen Crypto July 2021 - Summary.csv,4,2023-07-21,2023-07-21T10:00:59Z,ethereum,0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204,https://etherscan.io/tx/0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204,ETH,125.44715147,,0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0,THORSwap,THORSwap,high,victim-to-swap,,confirmed,swap to BTC,Preserve Midgard proof,
william-crypto,dossier,derived,2023-07-21,2023-07-21T00:00:00Z,bitcoin,,https://blockstream.info/address/bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s,BTC,40.70902128,,services,bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s,Wasabi,high,mixer-deposit,/Users/alphab/.mdx/research/data/william-live-check-2026-05-25/blockstream-address-bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s.json,spent,mixed,paid analytics validation,
william-crypto,dossier,derived,2026-05-25,2026-05-25T00:00:00Z,bitcoin,,https://blockstream.info/address/bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g,BTC,6.49998534,,unknown,bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g,unknown,medium,live-utxo,/Users/alphab/.mdx/research/data/william-live-check-2026-05-25/blockstream-address-bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g.json,unspent,possible downstream candidate,monitor,
```

## Paid Analytics Escalation

Ask vendors for narrow, testable outputs:

1. Validate or reject linkage from the six Wasabi coinjoins to `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`.
2. Quantify confidence and explain the heuristic class without exposing proprietary methods.
3. Validate whether `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g` is materially linked to William's deposits.
4. Confirm whether `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` is Binance, Binance.US, or another service cluster.
5. Identify any known VASP exposure after the Wasabi withdrawals.
6. Produce law enforcement ready exhibits: graph, table, txids, UTC timestamps, confidence labels, and exchange exposure.
7. State what legal process would be useful and where it should be sent.

Vendors to contact:

- Chainalysis Reactor
- TRM Forensics
- Elliptic Investigator
- Crystal Blockchain
- SlowMist MistTrack
- AnChain or Caudena if their current access path and pricing justify it

Decision rule:

- If analytics cannot validate a VASP exposure, continue monitoring and do not spend heavily.
- If analytics validates Binance or another VASP exposure, prioritize counsel and law enforcement process.
- If the live BTC moves to a service, update all reports immediately and ask law enforcement to send urgent preservation.

## Risk Ranked Lead Table

| Lead | Confidence | Actionability | Next action | Blocker | Owner |
|---|---:|---:|---|---|---|
| Live BTC `bc1qyt...t85g` | Medium | High if moved | Monitor every 10 minutes | No custodial exposure yet | Stuart |
| Probable Binance branch `17Stn...3zva` | Medium high | High if validated | Paid analytics validation | Public labels are not official | Stuart plus vendor |
| Wasabi deposit address | High as deposit | Low alone | Preserve and include in packet | Coinjoin privacy set | Stuart |
| Demix candidate `bc1q9v...zdl` | Low to medium | Medium if validated | Paid analytics query | Needs independent validation | Vendor |
| FixedFloat side path | Medium | Medium | Victim support and LE packet | Service cooperation and records | William plus Stuart |
| March 2026 dust | Low | Low | Record as noise | No attribution value | Stuart |

## 48 Hour Technical Checklist

### Stuart Can Start Now

1. Create `transaction-inventory.csv`.
2. Hash source CSV and all research artifacts.
3. Run fresh Blockstream and mempool.space checks for Bitcoin targets.
4. Run Midgard checks for both THORChain txids.
5. Create `william.duckdb` and load the inventory.
6. Set a cron or launchd job for the live BTC address.
7. Prepare a movement alert template.
8. Prepare paid analytics query packet.
9. Prepare screenshots for the one-page summary.

### Blocked On William

1. Confirm incident year.
2. Confirm ownership proof for the victim wallets.
3. Provide any prior report numbers.
4. Approve paid analytics spend.
5. Approve private Chainabuse reporting.
6. Decide whether counsel should review the 20 percent success fee structure before external outreach.

## Sources

- Blockstream Esplora API documentation: https://github.com/blockstream/esplora/blob/master/API.md
- mempool.space API: https://mempool.space/api
- THORChain Midgard documentation: https://docs.thorchain.org/technology/midgard
- Liquify Midgard API docs: https://gateway.liquify.com/chain/thorchain_midgard/v2/doc
- Etherscan API docs: https://docs.etherscan.io/
- FBI cryptocurrency victim guidance: https://www.fbi.gov/how-we-can-help-you/victim-services/national-crimes-and-victim-resources/cryptocurrency-investment-fraud
- IC3 complaint form: https://complaint.ic3.gov/
- Binance.US law enforcement guide: https://support.binance.us/en/articles/9842980-binance-us-law-enforcement-guide
- FixedFloat support contacts: https://ff.io/de/support
- Chainabuse reporting docs: https://docs.chainabuse.com/docs/post-reports-parameters
- Local package status evidence: `/Users/alphab/.mdx/research/data/william-live-check-2026-05-25/package-status.txt`

## Actionable Takeaway

Build the transaction inventory first, because every serious next step depends on it. In parallel, monitor the live BTC address and prepare the paid analytics packet. Recovery becomes materially more plausible only if a validated trail touches a service that can freeze funds or identify an account through lawful process.

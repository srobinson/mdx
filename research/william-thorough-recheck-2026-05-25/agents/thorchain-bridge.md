---
title: THORChain bridge row recheck for Ethereum tx 0x655a2a55
type: research
tags: [william, crypto, thorchain, ethereum, bitcoin, bridge]
summary: Ethereum tx 0x655a2a55 was a successful THORChain ETH to BTC swap that sent 7.29622713 BTC to bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s.
status: active
confidence: high
created: 2026-05-25
updated: 2026-05-25
---

## Executive Summary

Confirmed. The spreadsheet row for tx `0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204` is an Ethereum mainnet call to THORChain Router v4.1, method `depositWithExpiry`, from `0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0` to router `0xd37bbe5744d730a1d98d8dc97c42f0ca46ad7146`.

The true Ethereum block timestamp is `2023-07-21T14:00:59Z`. The sheet value `2023/07/21 10:00:59` matches that moment if interpreted as US Eastern daylight time, not UTC. THORChain Midgard links the inbound ETH swap to BTC outbound tx `CA88B4956964E3D8BFDAE2800B48F4CB15F8CC52A8554B4BFA301A400805E053`, which paid `7.29622713 BTC` to `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`.

## Detailed Findings

### Scope handled

Rechecked the THORChain and `depositWithExpiry` row for:

- Ethereum tx: `0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204`
- Spreadsheet source row: `summary-visible-rows.csv`, row with `source_row=5`
- Source account shown in sheet: `0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0`
- Router shown in sheet: `0xD37BbE5744D730a1d98d8DC97c42F0Ca46aD7146`

### Ethereum timestamp and transaction facts

Confirmed.

- Ethereum block number: `17,741,974`
- Block hash: `0x5d44722c08a30a62a8af2f16e012c4688a40e7de099f4f92f854c95fe040c4bf`
- Block timestamp: `2023-07-21T14:00:59Z`
- Sender: `0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0`
- Contract called: `0xd37bbe5744d730a1d98d8dc97c42f0ca46ad7146`
- Transaction value: `125.447151477364040918 ETH`
- Receipt status: `0x1`, success

The spreadsheet value `2023/07/21 10:00:59` is not the UTC chain timestamp. It is the same instant displayed as Eastern daylight time.

Evidence:

- Local decode: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/thorchain-bridge/decoded-target.json`
- Ethereum PublicNode transaction, receipt, block:
  - `.../data/thorchain-bridge/https_ethereum_publicnode_com_eth_getTransactionByHash.json`
  - `.../data/thorchain-bridge/https_ethereum_publicnode_com_eth_getTransactionReceipt.json`
  - `.../data/thorchain-bridge/https_ethereum_publicnode_com_eth_getBlockByNumber_0x10eb896.json`
- Cross checks for the block timestamp:
  - `.../data/thorchain-bridge/https_eth_drpc_org_eth_getBlockByNumber.json`
  - `.../data/thorchain-bridge/https_rpc_flashbots_net_eth_getBlockByNumber.json`
  - `.../data/thorchain-bridge/https_1rpc_io_eth_eth_getBlockByNumber.json`

### Contract call meaning

Confirmed.

The input selector is `0x44bc937b`, matching `depositWithExpiry(address payable vault, address asset, uint256 amount, string memo, uint256 expiration)` in THORChain Router v4.1.

Decoded call fields:

- Vault: `0x04e2462f10ba7fe0776af9b9272606af0b974dbb`
- Asset: `0x0000000000000000000000000000000000000000`, native ETH
- Amount: `125.447151477364040918 ETH`
- Memo: `=:BTC.BTC:bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s:704635983:t:30`
- Raw expiry: `1689948644481`. If read as milliseconds, this is `2023-07-21T14:10:44.481Z`. The router contract only checks `block.timestamp < expiration`, so the call passed.

The receipt contains one THORChain Router `Deposit` event:

- Event signature: `Deposit(address indexed to, address indexed asset, uint amount, string memo)`
- Event vault: `0x04e2462f10ba7fe0776af9b9272606af0b974dbb`
- Event asset: native ETH zero address
- Event amount: `125.447151477364040918 ETH`
- Event memo: `=:BTC.BTC:bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s:704635983:t:30`

Meaning. This was a THORChain market swap from ETH to BTC. THORChain documentation defines `=` as market swap, `BTC.BTC` as the target asset, the next field as the destination address, `704635983` as the minimum target amount in 1e8 units, `t` as the affiliate field, and `30` as the fee in basis points. The target floor equals `7.04635983 BTC`.

Evidence:

- THORChain Router source saved locally: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/thorchain-bridge/chain_evm_contracts_THORChain_RouterV4.sol`
  - `event Deposit(...)`: line 42
  - `depositWithExpiry(...)`: lines 69 to 72
  - native ETH branch and event emission: lines 75 to 92
- THORChain EVM transaction docs: https://dev.thorchain.org/concepts/sending-transactions.html
- THORChain memo docs: https://dev.thorchain.org/concepts/memos
- THORChain querying docs for router and base unit behavior: https://dev.thorchain.org/concepts/querying-thorchain.html

### THORChain and Midgard evidence

Confirmed.

Midgard via Liquify returned one action for the same inbound tx when the txid is queried without `0x`:

- Action type: `swap`
- Status: `success`
- THORChain action date: `2023-07-21T14:17:43.813588Z`
- Inbound address: `0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0`
- Inbound asset: `ETH.ETH`
- Inbound amount: `12544715147` in THORChain 1e8 units, equal to `125.44715147 ETH`
- Memo: `=:BTC.BTC:bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s:704635983:t:30`
- Pools: `ETH.ETH`, `BTC.BTC`
- Swap target: `704635983`, equal to `7.04635983 BTC`
- Outbound BTC amount: `729622713`, equal to `7.29622713 BTC`
- Outbound BTC tx: `CA88B4956964E3D8BFDAE2800B48F4CB15F8CC52A8554B4BFA301A400805E053`
- Outbound BTC address: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`

The THORChain action date is later than the Ethereum block timestamp because it reflects THORChain observation or processing time, not the source chain block time.

Evidence:

- Midgard API response: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/thorchain-bridge/https_gateway_liquify_com_chain_thorchain_midgard_v2_actions_txid_655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204.body`
- Repeatable URL: `https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204`
- Explorer UI, useful but not the primary evidence: `https://thorchain.net/tx/655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204`

### BTC outbound link

Confirmed.

Mempool.space confirms BTC tx `ca88b4956964e3d8bfdae2800b48f4cb15f8cc52a8554b4bfa301a400805e053`:

- Confirmed: yes
- Block height: `799,658`
- Block time: `2023-07-21T16:24:48Z`
- Output 0 address: `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`
- Output 0 value: `729,622,713 sats`, equal to `7.29622713 BTC`
- OP_RETURN: `OUT:655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204`

The OP_RETURN directly links the BTC outbound transaction back to the Ethereum inbound tx hash.

Likely useful downstream note. Output 0 was later spent in BTC tx `b0d0afa49018bd9233298b7076a0857ee1599056400d8d459f117211d4da2372` at `2023-07-23T00:34:04Z`. That spend has `250` inputs and `285` outputs with repeated output sizes. This is consistent with a CoinJoin style transaction, but this note does not prove the wallet software or service by itself.

Evidence:

- BTC tx API: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/thorchain-bridge/https_mempool_space_api_tx_ca88b4956964e3d8bfdae2800b48f4cb15f8cc52a8554b4bfa301a400805e053.body`
- BTC tx status: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/thorchain-bridge/https_mempool_space_api_tx_ca88b4956964e3d8bfdae2800b48f4cb15f8cc52a8554b4bfa301a400805e053_status.body`
- BTC outspends: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/thorchain-bridge/https_mempool_space_api_tx_ca88b4956964e3d8bfdae2800b48f4cb15f8cc52a8554b4bfa301a400805e053_outspends.body`
- Recipient address summary: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/thorchain-bridge/https_mempool_space_api_address_bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s.body`
- Spend tx summary: `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/data/thorchain-bridge/https_mempool_space_api_tx_b0d0afa49018bd9233298b7076a0857ee1599056400d8d459f117211d4da2372.body`
- Mempool URL: `https://mempool.space/tx/ca88b4956964e3d8bfdae2800b48f4cb15f8cc52a8554b4bfa301a400805e053`

### Contradictions and gaps

- Confirmed. The sheet time `2023/07/21 10:00:59` should not be treated as UTC. The Ethereum block timestamp is `2023-07-21T14:00:59Z`.
- Confirmed. The sheet amount `125.4472 ETH` is rounded. The on chain value is `125.447151477364040918 ETH`. Midgard reports `125.44715147 ETH` because THORChain normalizes amounts to 1e8 units.
- Confirmed. Liquify Midgard returns the action only when txid is provided without the `0x` prefix. The same query with `0x` returned zero actions.
- Unresolved. Public BTC evidence can prove the BTC output and its later spend, but not the private wallet owner or whether William controlled the destination address.
- Possible. The later BTC spend looks CoinJoin style due to very high input and output counts plus repeated output sizes, but that is not enough to attribute it to Wasabi without a separate BTC tracing analysis.

## Sources Consulted

### Spreadsheet and local case files

- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/WARROOM-BRIEF.md`
- `/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25/summary-visible-rows.csv`
- `/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25/gid-1211660592.csv`

### Ethereum sources

- Ethereum PublicNode JSON RPC: `https://ethereum.publicnode.com`
- dRPC JSON RPC: `https://eth.drpc.org`
- Flashbots RPC block query: `https://rpc.flashbots.net`
- 1RPC block query: `https://1rpc.io/eth`
- Etherscan URL from spreadsheet: `https://etherscan.io/tx/0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204`

### THORChain sources

- THORChain EVM transaction docs: `https://dev.thorchain.org/concepts/sending-transactions.html`
- THORChain memo docs: `https://dev.thorchain.org/concepts/memos`
- THORChain querying docs: `https://dev.thorchain.org/concepts/querying-thorchain.html`
- THORChain Router v4 source from GitLab API: `https://gitlab.com/api/v4/projects/13422983/repository/files/chain%2Fevm%2Fcontracts%2FTHORChain_RouterV4.sol/raw?ref=develop`
- Liquify Midgard action endpoint: `https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204`
- THORChain explorer UI: `https://thorchain.net/tx/655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204`

### Bitcoin sources

- Mempool tx API: `https://mempool.space/api/tx/ca88b4956964e3d8bfdae2800b48f4cb15f8cc52a8554b4bfa301a400805e053`
- Mempool tx page: `https://mempool.space/tx/ca88b4956964e3d8bfdae2800b48f4cb15f8cc52a8554b4bfa301a400805e053`
- Mempool outspends API: `https://mempool.space/api/tx/ca88b4956964e3d8bfdae2800b48f4cb15f8cc52a8554b4bfa301a400805e053/outspends`
- Mempool address API: `https://mempool.space/api/address/bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`

### Failed or limited checks

- `https://midgard.ninerealms.com` and `https://thornode.ninerealms.com` did not resolve from this environment.
- `https://midgard.thorswap.net` and `https://thornode.thorswap.net` returned Cloudflare challenge pages.
- Runescan and ViewBlock returned Cloudflare challenge pages.
- Blockstream API reset the connection during this run.
- Ankr RPC requires an API key.
- LlamaRPC and BlockPI returned gateway errors during this run.

## Source Quality Assessment

Confidence is high for the core facts. Ethereum timestamp, sender, router, amount, and success status were verified from JSON RPC and cross checked against independent block RPC responses. Contract meaning was verified against THORChain Router source and THORChain docs. THORChain swap status and BTC outbound were verified through Midgard. BTC outbound details were verified through Mempool.space.

The main uncertainty is downstream BTC attribution after the THORChain outbound. Public data proves the BTC transaction and later spend, but owner identity and wallet software require separate analysis.

## Open Questions

1. Did William own or recognize `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`?
2. Was the later spend tx `b0d0afa49018bd9233298b7076a0857ee1599056400d8d459f117211d4da2372` part of William's own wallet activity, a mixer or CoinJoin flow, or attacker activity?
3. Does William have wallet export records, exchange withdrawal records, or screenshots that link the ETH source address to him?

## Actionable Takeaways

1. Treat this spreadsheet row as a successful ETH to BTC THORChain swap, not a plain transfer to an Ethereum address.
2. Use `2023-07-21T14:00:59Z` as the Ethereum chain timestamp in any timeline.
3. Preserve both sides of the bridge link:
   - ETH inbound: `0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204`
   - BTC outbound: `ca88b4956964e3d8bfdae2800b48f4cb15f8cc52a8554b4bfa301a400805e053`
4. If tracing continues, start the BTC branch at output 0 of `ca88b495...`, then inspect spend tx `b0d0afa...` as a separate BTC analysis lane.

## Repeatable Commands

```bash
# Ethereum transaction, receipt, and block
TX=0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204
curl -sS https://ethereum.publicnode.com \
  -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_getTransactionByHash","params":["'"$TX"'"]}' | jq .

curl -sS https://ethereum.publicnode.com \
  -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_getTransactionReceipt","params":["'"$TX"'"]}' | jq .

curl -sS https://ethereum.publicnode.com \
  -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_getBlockByNumber","params":["0x10eb896",false]}' | jq .

# THORChain Midgard action. Query without 0x.
curl -sS 'https://gateway.liquify.com/chain/thorchain_midgard/v2/actions?txid=655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204' | jq .

# BTC outbound tx and outspend
BTCTX=ca88b4956964e3d8bfdae2800b48f4cb15f8cc52a8554b4bfa301a400805e053
curl -sS "https://mempool.space/api/tx/$BTCTX" | jq .
curl -sS "https://mempool.space/api/tx/$BTCTX/outspends" | jq .
```

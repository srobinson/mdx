#!/usr/bin/env python3
import csv
import json
import pathlib
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, getcontext

getcontext().prec = 50
BASE = pathlib.Path('/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25')
DATA = BASE / 'data' / 'independent-contradiction-audit'
VISIBLE = BASE / 'summary-visible-rows.csv'

ETH_RPC = 'https://ethereum.publicnode.com'
BSC_RPC = 'https://bsc.publicnode.com'
BLOCKSTREAM = 'https://blockstream.info/api'
UA = 'helioy-independent-contradiction-audit/1.0'


def fetch_url(url, out_path):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    out_path.write_bytes(raw)
    try:
        return json.loads(raw)
    except Exception:
        return raw.decode('utf-8', errors='replace')


def rpc(url, method, params, out_path):
    payload = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(',', ':')).encode(),
        headers={'Content-Type': 'application/json', 'User-Agent': UA},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    out_path.write_bytes(raw)
    data = json.loads(raw)
    if data.get('error'):
        raise RuntimeError(f'{method} error from {url}: {data["error"]}')
    return data


def hexint(value):
    if value in (None, ''):
        return None
    return int(value, 16)


def iso_from_ts(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace('+00:00', 'Z')


def parse_visible_rows():
    rows = []
    with VISIBLE.open(newline='') as f:
        for row in csv.DictReader(f):
            h = row.get('tx_hash_or_note') or ''
            url = row.get('transaction_url') or ''
            sent_to = row.get('sent_to') or ''
            tx = h if h.startswith('0x') and len(h) == 66 else ''
            if not tx:
                for part in (url, sent_to):
                    if '/tx/0x' in part:
                        tx = '0x' + part.split('/tx/0x', 1)[1][:64]
                        break
            if not tx:
                continue
            chain = 'bsc' if 'bscscan.com' in url else 'ethereum'
            rows.append({**row, 'chain': chain, 'tx_hash': tx.lower()})
    return rows


def fetch_evm(rows):
    summaries = []
    seen = set()
    for row in rows:
        tx_hash = row['tx_hash']
        chain = row['chain']
        key = (chain, tx_hash)
        if key in seen:
            continue
        seen.add(key)
        rpc_url = BSC_RPC if chain == 'bsc' else ETH_RPC
        prefix = f'{chain}-{tx_hash}'
        tx_resp = rpc(rpc_url, 'eth_getTransactionByHash', [tx_hash], DATA / f'{prefix}-transaction.json')
        tx = tx_resp['result']
        if not tx:
            summaries.append({'chain': chain, 'tx_hash': tx_hash, 'found': False})
            continue
        block_num = tx.get('blockNumber')
        block_resp = rpc(rpc_url, 'eth_getBlockByNumber', [block_num, False], DATA / f'{prefix}-block.json')
        block = block_resp['result']
        value_native = Decimal(hexint(tx.get('value'))) / Decimal(10) ** 18
        ts = hexint(block.get('timestamp')) if block else None
        summaries.append({
            'chain': chain,
            'tx_hash': tx_hash,
            'found': True,
            'block_number': hexint(block_num),
            'timestamp_utc': iso_from_ts(ts) if ts is not None else '',
            'from': (tx.get('from') or '').lower(),
            'to': (tx.get('to') or '').lower(),
            'value_native': format(value_native, 'f').rstrip('0').rstrip('.') or '0',
            'explorer': ('https://bscscan.com/tx/' if chain == 'bsc' else 'https://etherscan.io/tx/') + tx_hash,
        })
        time.sleep(0.15)
    (DATA / 'evm-chain-summary.json').write_text(json.dumps(summaries, indent=2, sort_keys=True) + '\n')
    with (DATA / 'evm-chain-summary.csv').open('w', newline='') as f:
        fields = ['chain', 'tx_hash', 'found', 'block_number', 'timestamp_utc', 'from', 'to', 'value_native', 'explorer']
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for s in summaries:
            w.writerow({k: s.get(k, '') for k in fields})
    return summaries


def fetch_btc():
    addrs = [
        'bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s',
        'bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl',
        'bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g',
    ]
    txids = [
        '164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187',
        '4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5',
        '29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287',
    ]
    summary = {'fetched_at_utc': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), 'addresses': {}, 'txs': {}}
    for addr in addrs:
        clean = addr.replace(':', '_')
        info = fetch_url(f'{BLOCKSTREAM}/address/{addr}', DATA / f'blockstream-address-{clean}.json')
        utxo = fetch_url(f'{BLOCKSTREAM}/address/{addr}/utxo', DATA / f'blockstream-address-{clean}-utxo.json')
        mempool = fetch_url(f'{BLOCKSTREAM}/address/{addr}/txs/mempool', DATA / f'blockstream-address-{clean}-mempool.json')
        funded = info.get('chain_stats', {}).get('funded_txo_sum', 0) + info.get('mempool_stats', {}).get('funded_txo_sum', 0)
        spent = info.get('chain_stats', {}).get('spent_txo_sum', 0) + info.get('mempool_stats', {}).get('spent_txo_sum', 0)
        summary['addresses'][addr] = {
            'funded_sats': funded,
            'spent_sats': spent,
            'balance_sats': funded - spent,
            'utxo_count': len(utxo) if isinstance(utxo, list) else None,
            'utxo_sats': sum(int(u.get('value', 0)) for u in utxo) if isinstance(utxo, list) else None,
            'mempool_count': len(mempool) if isinstance(mempool, list) else None,
        }
        time.sleep(0.15)
    for txid in txids:
        tx = fetch_url(f'{BLOCKSTREAM}/tx/{txid}', DATA / f'blockstream-tx-{txid}.json')
        status = tx.get('status', {}) if isinstance(tx, dict) else {}
        summary['txs'][txid] = {
            'confirmed': status.get('confirmed'),
            'block_time': iso_from_ts(status['block_time']) if status.get('block_time') else '',
            'vout_count': len(tx.get('vout', [])) if isinstance(tx, dict) else None,
        }
        time.sleep(0.15)
    (DATA / 'btc-current-summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    return summary


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    rows = parse_visible_rows()
    evm = fetch_evm(rows)
    btc = fetch_btc()
    print(json.dumps({'evm_count': len(evm), 'btc_summary': btc}, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()

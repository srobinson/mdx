#!/usr/bin/env python3
import csv
import json
import re
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path('/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25')
SOURCE_ROOT = Path('/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25')
OUT = ROOT / 'data' / 'address-cluster-map'
OUT.mkdir(parents=True, exist_ok=True)
VISIBLE = ROOT / 'summary-visible-rows.csv'
TABS = SOURCE_ROOT / 'extracted-tabs'
ADDR_RE = re.compile(r'0x[a-fA-F0-9]{40}')
TX_RE = re.compile(r'0x[a-fA-F0-9]{64}')

# First hop addresses whose outgoing behavior is material to the cluster question.
# These are derived from spreadsheet rows 5 to 18.
FIRST_HOP_ETH_HISTORY_ALLOWLIST = {
    '0xeec35fd50b5e7344b3e1a7f4384b3cb9365e204a',
    '0x6a7e9ed15ea2c1c7787e68f2ca2df68379ed437e',
    '0xb7917ee3520c4aa56add5d55f6026edeebe99d02',
    '0xbdc4b2d85d9dcc42c3799b4569bd1d7d25d29c03',
    '0x4ec986035b635d09474fc390acdf5c107dda4c70',
    '0x09066e7857d3a9a53c9142f8a7effcbc7989f1b5',
}


def norm_addr(a):
    if not a:
        return a
    a = a.strip()
    return a.lower() if ADDR_RE.fullmatch(a) else a


def chain_from_url(url):
    if 'bscscan.com' in url:
        return 'bsc'
    if 'etherscan.io' in url:
        return 'eth'
    return 'unknown'


def excel_serial_to_utc(serial):
    try:
        x = float(serial)
    except Exception:
        return None
    dt = datetime(1899, 12, 30, tzinfo=timezone.utc) + timedelta(days=x)
    return dt.replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def read_visible_rows():
    rows = []
    with VISIBLE.open(newline='') as f:
        for r in csv.DictReader(f):
            tx = r.get('tx_hash_or_note') or ''
            if not TX_RE.fullmatch(tx):
                m = TX_RE.search((r.get('transaction_url') or '') + ' ' + (r.get('sent_to') or ''))
                tx = m.group(0) if m else ''
            url = r.get('transaction_url') or ''
            rows.append({
                'source_row': int(r['source_row']),
                'address': r.get('address',''),
                'address_lc': norm_addr(r.get('address','')),
                'date_as_displayed': r.get('date_as_displayed',''),
                'date_excel_utc': excel_serial_to_utc(r.get('date_as_displayed','')),
                'transaction_url': url,
                'chain': chain_from_url(url),
                'sent_to_text': r.get('sent_to') or '',
                'sent_to_addresses': ADDR_RE.findall(r.get('sent_to') or ''),
                'value_displayed': r.get('value_displayed',''),
                'amount': r.get('amount',''),
                'token': r.get('token',''),
                'unit_price': r.get('unit_price',''),
                'tx_hash': tx,
                'parse_note': r.get('parse_note',''),
            })
    return rows


def read_tab_refs():
    refs = defaultdict(list)
    for path in sorted(TABS.glob('*.csv')):
        with path.open(newline='') as f:
            for idx, row in enumerate(csv.reader(f), start=1):
                text = ' '.join(row)
                for tx in TX_RE.findall(text):
                    refs[tx.lower()].append({'file': str(path), 'line': idx, 'row': row})
    return refs


def fetch_json(url, path, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 address-cluster-map'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            path.write_bytes(data)
            return json.loads(data.decode('utf-8'))
    except Exception as e:
        path.with_suffix(path.suffix + '.error.txt').write_text(f'{url}\n{repr(e)}\n')
        return {'_error': repr(e), '_url': url}


def fetch_text(url, path, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 address-cluster-map'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            path.write_bytes(data)
            return data.decode('utf-8', errors='replace')
    except Exception as e:
        path.with_suffix(path.suffix + '.error.txt').write_text(f'{url}\n{repr(e)}\n')
        return ''


def rpc(endpoint, method, params, path):
    payload = json.dumps({'jsonrpc':'2.0','method':method,'params':params,'id':1}).encode()
    req = urllib.request.Request(endpoint, data=payload, headers={'Content-Type':'application/json','User-Agent':'address-cluster-map'})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            path.write_bytes(data)
            return json.loads(data.decode())
    except Exception as e:
        path.with_suffix(path.suffix + '.error.txt').write_text(f'{method} {params}\n{repr(e)}\n')
        return {'error': repr(e)}


def wei_to_native(v):
    if v is None:
        return None
    if isinstance(v, str) and v.startswith('0x'):
        n = int(v, 16)
    else:
        n = int(v)
    return n / 10**18


def extract_addr_label(addr_obj):
    if not isinstance(addr_obj, dict):
        return None
    labels = []
    if addr_obj.get('name'):
        labels.append(str(addr_obj['name']))
    meta = addr_obj.get('metadata') or {}
    for tag in meta.get('tags') or []:
        n = tag.get('name')
        if n:
            labels.append(str(n))
    return '; '.join(dict.fromkeys(labels)) if labels else None


def bsc_meta_description(html):
    m = re.search(r'<meta\s+name="Description"\s+content="([^"]+)"', html, re.I)
    if not m:
        m = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html, re.I)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else None


def main():
    rows = read_visible_rows()
    tab_refs = read_tab_refs()
    (OUT / 'parsed-visible-rows.json').write_text(json.dumps(rows, indent=2))
    (OUT / 'tab-transaction-refs.json').write_text(json.dumps(tab_refs, indent=2))

    tx_rows = [r for r in rows if 5 <= r['source_row'] <= 18 and r['tx_hash']]
    eth_txs = sorted({r['tx_hash'].lower() for r in tx_rows if r['chain']=='eth'})
    bsc_txs = sorted({r['tx_hash'].lower() for r in tx_rows if r['chain']=='bsc'})

    blockscout_tx = {}
    for tx in eth_txs:
        blockscout_tx[tx] = fetch_json(f'https://eth.blockscout.com/api/v2/transactions/{tx}', OUT / f'eth-blockscout-tx-{tx}.json')
        time.sleep(0.05)

    eth_addresses = set()
    bsc_addresses = set()
    for r in tx_rows:
        if r['chain'] == 'eth':
            eth_addresses.add(r['address_lc'])
            for a in r['sent_to_addresses']:
                eth_addresses.add(norm_addr(a))
        if r['chain'] == 'bsc':
            bsc_addresses.add(r['address_lc'])
            for a in r['sent_to_addresses']:
                bsc_addresses.add(norm_addr(a))
    for d in blockscout_tx.values():
        for side in ('from','to'):
            h = (d.get(side) or {}).get('hash')
            if h:
                eth_addresses.add(norm_addr(h))

    eth_addr_meta = {}
    for a in sorted(x for x in eth_addresses if x):
        eth_addr_meta[a] = fetch_json(f'https://eth.blockscout.com/api/v2/addresses/{a}', OUT / f'eth-blockscout-address-{a}.json')
        time.sleep(0.05)

    eth_addr_hist = {}
    for a in sorted(FIRST_HOP_ETH_HISTORY_ALLOWLIST):
        eth_addr_hist[a] = fetch_json(f'https://eth.blockscout.com/api/v2/addresses/{a}/transactions', OUT / f'eth-blockscout-address-{a}-transactions.json')
        time.sleep(0.05)
        # Fetch metadata for next-hop destinations in these small first-hop histories.
        for item in eth_addr_hist[a].get('items') or []:
            for side in ('from','to'):
                h = norm_addr((item.get(side) or {}).get('hash'))
                if h and h not in eth_addr_meta:
                    eth_addr_meta[h] = fetch_json(f'https://eth.blockscout.com/api/v2/addresses/{h}', OUT / f'eth-blockscout-address-{h}.json')
                    time.sleep(0.05)

    bsc_rpc_tx = {}; bsc_rpc_receipt = {}; bsc_rpc_block = {}; bsc_code = {}; bsc_meta = {}
    for tx in bsc_txs:
        tx_data = rpc('https://bsc-dataseed.binance.org/', 'eth_getTransactionByHash', [tx], OUT / f'bsc-rpc-tx-{tx}.json')
        bsc_rpc_tx[tx] = tx_data
        bsc_rpc_receipt[tx] = rpc('https://bsc-dataseed.binance.org/', 'eth_getTransactionReceipt', [tx], OUT / f'bsc-rpc-receipt-{tx}.json')
        bn = (tx_data.get('result') or {}).get('blockNumber')
        if bn:
            bsc_rpc_block[tx] = rpc('https://bsc-dataseed.binance.org/', 'eth_getBlockByNumber', [bn, False], OUT / f'bsc-rpc-block-{tx}.json')
        html = fetch_text(f'https://bscscan.com/tx/{tx}', OUT / f'bscscan-tx-{tx}.html')
        (OUT / f'bscscan-tx-{tx}.meta.txt').write_text((bsc_meta_description(html) or '') + '\n')
        for side in ('from','to'):
            h = (tx_data.get('result') or {}).get(side)
            if h:
                bsc_addresses.add(norm_addr(h))
        time.sleep(0.05)
    for a in sorted(x for x in bsc_addresses if x):
        bsc_code[a] = rpc('https://bsc-dataseed.binance.org/', 'eth_getCode', [a, 'latest'], OUT / f'bsc-rpc-code-{a}.json')
        html = fetch_text(f'https://bscscan.com/address/{a}', OUT / f'bscscan-address-{a}.html')
        desc = bsc_meta_description(html) or ''
        (OUT / f'bscscan-address-{a}.meta.txt').write_text(desc + '\n')
        bsc_meta[a] = desc
        time.sleep(0.05)

    tx_table = []
    for r in tx_rows:
        tx = r['tx_hash'].lower()
        if r['chain'] == 'eth':
            d = blockscout_tx.get(tx) or {}
            tx_table.append({
                'summary_row': r['source_row'],
                'tab_refs': tab_refs.get(tx, []),
                'chain': 'Ethereum',
                'tx_hash': tx,
                'sheet_from': r['address'],
                'chain_from': (d.get('from') or {}).get('hash'),
                'sheet_sent_to': r['sent_to_text'],
                'chain_to': (d.get('to') or {}).get('hash'),
                'chain_to_label': extract_addr_label(d.get('to')),
                'chain_to_is_contract': (d.get('to') or {}).get('is_contract'),
                'method': d.get('method'),
                'status': d.get('status') or d.get('result'),
                'timestamp_utc': d.get('timestamp'),
                'sheet_date_displayed': r['date_as_displayed'],
                'sheet_date_excel_utc': r['date_excel_utc'],
                'sheet_amount': r['amount'],
                'chain_amount_native': wei_to_native(d.get('value')),
                'token': 'ETH',
                'decoded_memo': next((p.get('value') for p in (((d.get('decoded_input') or {}).get('parameters')) or []) if p.get('name') == 'memo'), None),
                'transaction_types': d.get('transaction_types'),
            })
        elif r['chain'] == 'bsc':
            d = (bsc_rpc_tx.get(tx) or {}).get('result') or {}
            block = (bsc_rpc_block.get(tx) or {}).get('result') or {}
            ts = None
            if block.get('timestamp'):
                ts = datetime.fromtimestamp(int(block['timestamp'],16), tz=timezone.utc).isoformat().replace('+00:00','Z')
            to = d.get('to'); to_lc = norm_addr(to)
            code = (bsc_code.get(to_lc) or {}).get('result')
            tx_table.append({
                'summary_row': r['source_row'],
                'tab_refs': tab_refs.get(tx, []),
                'chain': 'BNB Smart Chain',
                'tx_hash': tx,
                'sheet_from': r['address'],
                'chain_from': d.get('from'),
                'sheet_sent_to': r['sent_to_text'],
                'chain_to': to,
                'chain_to_label': None,
                'chain_to_is_contract': (code not in (None, '0x')),
                'method': None,
                'status': 'ok' if (bsc_rpc_receipt.get(tx,{}).get('result') or {}).get('status') == '0x1' else None,
                'timestamp_utc': ts,
                'sheet_date_displayed': r['date_as_displayed'],
                'sheet_date_excel_utc': r['date_excel_utc'],
                'sheet_amount': r['amount'],
                'chain_amount_native': wei_to_native(d.get('value')),
                'token': 'BNB',
                'bscscan_tx_meta': (OUT / f'bscscan-tx-{tx}.meta.txt').read_text().strip() if (OUT / f'bscscan-tx-{tx}.meta.txt').exists() else None,
                'bscscan_to_address_meta': bsc_meta.get(to_lc),
            })

    (OUT / 'normalized-transaction-table.json').write_text(json.dumps(tx_table, indent=2))

    first_hop_history_summary = {}
    for a,hist in eth_addr_hist.items():
        compact = []
        for item in (hist.get('items') or [])[:12]:
            compact.append({
                'hash': item.get('hash'),
                'timestamp': item.get('timestamp'),
                'from': (item.get('from') or {}).get('hash'),
                'to': (item.get('to') or {}).get('hash'),
                'from_label': extract_addr_label(item.get('from')),
                'to_label': extract_addr_label(item.get('to')),
                'value_native': wei_to_native(item.get('value')),
                'method': item.get('method'),
                'types': item.get('transaction_types'),
            })
        first_hop_history_summary[a] = compact
    (OUT / 'first-hop-history-summary.json').write_text(json.dumps(first_hop_history_summary, indent=2))

    dest_counts = Counter(norm_addr(t['chain_to']) for t in tx_table)
    source_counts = Counter(norm_addr(t['chain_from']) for t in tx_table)
    summary = {
        'source_rows_used': [r['source_row'] for r in tx_rows],
        'transaction_count': len(tx_table),
        'source_counts': dict(source_counts),
        'destination_counts': dict(dest_counts),
        'eth_address_metadata_keys': sorted(eth_addr_meta),
        'raw_output_dir': str(OUT),
    }
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2))

    md_lines = ['# Address cluster parsed data', '', '## Destination counts']
    for dest,count in dest_counts.most_common():
        label = extract_addr_label(eth_addr_meta.get(dest) or {})
        md_lines.append(f'- `{dest}`: {count}' + (f'; label {label}' if label else ''))
    md_lines += ['', '## Transaction table', '| Summary row | Chain | From | To | Amount | Chain UTC | Method | To label |', '|---:|---|---|---|---:|---|---|---|']
    for t in sorted(tx_table, key=lambda x: x['summary_row']):
        amount = t['chain_amount_native']
        amount_s = f"{amount:.12g} {t['token']}" if amount is not None else ''
        md_lines.append(f"| {t['summary_row']} | {t['chain']} | `{t.get('chain_from')}` | `{t.get('chain_to')}` | {amount_s} | {t.get('timestamp_utc')} | {t.get('method') or ''} | {t.get('chain_to_label') or ''} |")
    md_lines += ['', '## First hop histories']
    for a,items in first_hop_history_summary.items():
        md_lines.append(f'### `{a}`')
        for item in items[:8]:
            label = item.get('to_label') or item.get('from_label') or ''
            native = item['value_native']
            md_lines.append(f"- {item['timestamp']} `{item['hash']}` {native} ETH `{item['from']}` -> `{item['to']}` {item.get('method') or ''} {label}")
    (OUT / 'analysis-data.md').write_text('\n'.join(md_lines) + '\n')

    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()

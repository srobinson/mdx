import csv, json, time, pathlib, urllib.request
from datetime import datetime, timezone

base = pathlib.Path('/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25')
summary = base/'summary-visible-rows.csv'
outdir = base/'data'/'friend-packet-update'
outdir.mkdir(parents=True, exist_ok=True)
endpoints = {
    'ethereum': 'https://ethereum.publicnode.com',
    'bsc': 'https://bsc.publicnode.com',
}

def rpc(chain, method, params, timeout=20):
    url = endpoints[chain]
    payload = json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
    req = urllib.request.Request(url, data=payload, headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0 william-recheck'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())

def chain_from_url(url):
    if 'bscscan.com' in url:
        return 'bsc'
    if 'etherscan.io' in url:
        return 'ethereum'
    return 'unknown'

rows=[]
with summary.open(newline='') as f:
    for row in csv.DictReader(f):
        h = (row.get('tx_hash_or_note') or '').strip()
        if not h.startswith('0x') or len(h) < 66:
            # shifted lower rows have the tx URL in transaction_url; parse last path segment
            url = (row.get('transaction_url') or '').strip()
            if '/tx/' in url:
                h = url.rsplit('/tx/',1)[1].strip()
        if h.startswith('0x') and len(h) >= 66:
            row['_hash'] = h[:66]
            row['_chain'] = chain_from_url((row.get('transaction_url') or '') + ' ' + (row.get('sent_to') or ''))
            rows.append(row)

seen = {}
for r in rows:
    seen.setdefault((r['_chain'], r['_hash']), []).append(r)

summary_rows=[]
for i, ((chain, txh), originals) in enumerate(sorted(seen.items()), 1):
    if chain == 'unknown':
        summary_rows.append({'chain':chain,'tx_hash':txh,'error':'unknown chain'})
        continue
    result = {'chain': chain, 'tx_hash': txh, 'source_rows': ';'.join(o.get('source_row','') for o in originals), 'displayed_dates': ' | '.join(o.get('date_as_displayed','') for o in originals)}
    raw = {'chain': chain, 'endpoint': endpoints[chain], 'tx_hash': txh, 'requests': []}
    try:
        tx_resp = rpc(chain, 'eth_getTransactionByHash', [txh])
        raw['requests'].append({'method':'eth_getTransactionByHash','params':[txh],'response':tx_resp})
        tx = tx_resp.get('result')
        if not tx:
            result['error'] = 'transaction not found'
        else:
            result['from'] = tx.get('from')
            result['to'] = tx.get('to')
            result['block_number_hex'] = tx.get('blockNumber')
            result['value_wei_hex'] = tx.get('value')
            try:
                result['value_native'] = str(int(tx.get('value','0x0'),16) / 10**18)
            except Exception:
                result['value_native'] = ''
            # Some providers include blockTimestamp in tx. Always verify from block when blockNumber exists.
            bn = tx.get('blockNumber')
            if bn:
                block_resp = rpc(chain, 'eth_getBlockByNumber', [bn, False])
                raw['requests'].append({'method':'eth_getBlockByNumber','params':[bn, False],'response':block_resp})
                block = block_resp.get('result')
                if block and block.get('timestamp'):
                    ts = int(block['timestamp'], 16)
                    result['chain_timestamp_unix'] = str(ts)
                    result['chain_timestamp_utc'] = datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            result['explorer_url'] = originals[0].get('transaction_url','') if originals else ''
    except Exception as e:
        result['error'] = repr(e)
        raw['error'] = repr(e)
    (outdir/f'{chain}-{txh}.json').write_text(json.dumps(raw, indent=2, sort_keys=True))
    summary_rows.append(result)
    time.sleep(0.15)

fields = ['chain','tx_hash','source_rows','displayed_dates','chain_timestamp_utc','chain_timestamp_unix','from','to','value_native','block_number_hex','explorer_url','error']
with (outdir/'chain-timestamps.csv').open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(summary_rows)
print(json.dumps(summary_rows, indent=2))

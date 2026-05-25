import json, pathlib, urllib.request
from datetime import datetime, timezone
base = pathlib.Path('/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25')
outdir = base/'data'/'friend-packet-update'
outdir.mkdir(parents=True, exist_ok=True)
lead='bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g'
txh='164f311dea5ac820de0b52677d0e3ce5673bad6e5a45df8d994513588505b187'
urls={
 'address': f'https://blockstream.info/api/address/{lead}',
 'utxo': f'https://blockstream.info/api/address/{lead}/utxo',
 'tx': f'https://blockstream.info/api/tx/{txh}',
 'tx_status': f'https://blockstream.info/api/tx/{txh}/status',
}
raw={}
for name,url in urls.items():
    req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 william-recheck'})
    with urllib.request.urlopen(req,timeout=20) as r:
        data=r.read().decode()
        try: raw[name]={'url':url,'response':json.loads(data)}
        except Exception: raw[name]={'url':url,'response_text':data}
(outdir/'blockstream-live-btc-lead-october-check.json').write_text(json.dumps(raw,indent=2,sort_keys=True))
status=raw['tx_status']['response']
ts=status.get('block_time')
summary={
 'lead_address': lead,
 'funding_tx': txh,
 'blockstream_tx_status': status,
 'block_time_utc': datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC') if ts else None,
 'address_chain_stats': raw['address']['response'].get('chain_stats'),
 'address_mempool_stats': raw['address']['response'].get('mempool_stats'),
 'utxo_count': len(raw['utxo']['response']) if isinstance(raw['utxo']['response'], list) else None,
 'utxos': raw['utxo']['response'],
}
(outdir/'btc-october-lead-summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True))
print(json.dumps(summary, indent=2))

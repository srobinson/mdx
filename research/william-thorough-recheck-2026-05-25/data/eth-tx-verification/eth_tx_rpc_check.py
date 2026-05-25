#!/usr/bin/env python3
"""Verify Ethereum transaction facts from summary-visible-rows.csv via public JSON-RPC."""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = Path('/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25')
INPUT_CSV = BASE / 'summary-visible-rows.csv'
OUT_DIR = BASE / 'data' / 'eth-tx-verification'
OUT_CSV = OUT_DIR / 'eth-tx-verification.csv'
RAW_JSONL = OUT_DIR / 'raw-rpc-responses.jsonl'
MANIFEST = OUT_DIR / 'manifest.json'

RPC_ENDPOINTS = [
    'https://ethereum-rpc.publicnode.com',
    'https://eth.llamarpc.com',
    'https://rpc.flashbots.net',
]

TX_RE = re.compile(r'0x[a-fA-F0-9]{64}')
ETHERSCAN_RE = re.compile(r'https?://(?:www\.)?etherscan\.io/tx/(0x[a-fA-F0-9]{64})')


def read_eth_txs() -> dict[str, dict[str, Any]]:
    txs: dict[str, dict[str, Any]] = {}
    with INPUT_CSV.open(newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            row_text = json.dumps(row, sort_keys=True)
            etherscan_hashes = ETHERSCAN_RE.findall(row_text)
            if not etherscan_hashes:
                continue
            for tx_hash in etherscan_hashes:
                key = tx_hash.lower()
                txs.setdefault(
                    key,
                    {
                        'tx_hash': key,
                        'source_rows': [],
                        'spreadsheet_dates': [],
                        'spreadsheet_addresses': [],
                        'spreadsheet_amounts': [],
                        'spreadsheet_tokens': [],
                        'parse_notes': [],
                    },
                )
                rec = txs[key]
                source_row = row.get('source_row', '').strip()
                if source_row and source_row not in rec['source_rows']:
                    rec['source_rows'].append(source_row)
                date_displayed = row.get('date_as_displayed', '').strip()
                if date_displayed and date_displayed not in rec['spreadsheet_dates']:
                    rec['spreadsheet_dates'].append(date_displayed)
                address = row.get('address', '').strip()
                if address and address not in rec['spreadsheet_addresses']:
                    rec['spreadsheet_addresses'].append(address)
                amount = row.get('amount', '').strip() or row.get('transaction_url', '').strip()
                if amount and amount not in rec['spreadsheet_amounts']:
                    rec['spreadsheet_amounts'].append(amount)
                token = row.get('token', '').strip()
                if token and token not in rec['spreadsheet_tokens']:
                    rec['spreadsheet_tokens'].append(token)
                note = row.get('parse_note', '').strip()
                if note and note not in rec['parse_notes']:
                    rec['parse_notes'].append(note)
    return txs


def rpc_call(method: str, params: list[Any]) -> tuple[Any, dict[str, Any]]:
    errors = []
    payload = {'jsonrpc': '2.0', 'id': int(time.time() * 1000000) % 1000000000, 'method': method, 'params': params}
    body = json.dumps(payload).encode('utf-8')
    for endpoint in RPC_ENDPOINTS:
        req = Request(endpoint, data=body, headers={'content-type': 'application/json', 'user-agent': 'helioy-william-eth-verification/1.0'})
        try:
            with urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            if 'error' in data:
                errors.append({'endpoint': endpoint, 'error': data['error']})
                continue
            return data.get('result'), {'endpoint': endpoint, 'request': payload, 'response': data}
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append({'endpoint': endpoint, 'error': repr(exc)})
    raise RuntimeError(f'All RPC endpoints failed for {method}: {errors}')


def hex_int(value: str | None) -> int | None:
    if value is None:
        return None
    return int(value, 16)


def wei_to_eth(value_hex: str | None) -> str:
    wei = hex_int(value_hex) or 0
    eth = Decimal(wei) / Decimal(10**18)
    text = format(eth, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text or '0'


def verify() -> list[dict[str, Any]]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    txs = read_eth_txs()
    rows = []
    raw_count = 0
    with RAW_JSONL.open('w', encoding='utf-8') as raw:
        for tx_hash in sorted(txs):
            tx, tx_raw = rpc_call('eth_getTransactionByHash', [tx_hash])
            raw.write(json.dumps({'tx_hash': tx_hash, 'method': 'eth_getTransactionByHash', **tx_raw}, sort_keys=True) + '\n')
            raw_count += 1
            if not tx:
                rows.append({
                    'tx_hash': tx_hash,
                    'chain_timestamp_utc': '',
                    'block': '',
                    'from': '',
                    'to': '',
                    'native_value_eth': '',
                    'receipt_status': 'not_found',
                    'receipt_status_hex': '',
                    'source_rows': ';'.join(txs[tx_hash]['source_rows']),
                    'spreadsheet_dates': ' | '.join(txs[tx_hash]['spreadsheet_dates']),
                    'spreadsheet_addresses': ' | '.join(txs[tx_hash]['spreadsheet_addresses']),
                    'spreadsheet_amounts': ' | '.join(txs[tx_hash]['spreadsheet_amounts']),
                    'spreadsheet_tokens': ' | '.join(txs[tx_hash]['spreadsheet_tokens']),
                    'parse_notes': ' | '.join(txs[tx_hash]['parse_notes']),
                    'rpc_endpoint_tx': tx_raw['endpoint'],
                    'rpc_endpoint_receipt': '',
                    'rpc_endpoint_block': '',
                })
                continue

            receipt, receipt_raw = rpc_call('eth_getTransactionReceipt', [tx_hash])
            raw.write(json.dumps({'tx_hash': tx_hash, 'method': 'eth_getTransactionReceipt', **receipt_raw}, sort_keys=True) + '\n')
            raw_count += 1

            block_number_hex = tx.get('blockNumber')
            block, block_raw = rpc_call('eth_getBlockByNumber', [block_number_hex, False])
            raw.write(json.dumps({'tx_hash': tx_hash, 'method': 'eth_getBlockByNumber', **block_raw}, sort_keys=True) + '\n')
            raw_count += 1

            block_number = hex_int(block_number_hex)
            timestamp = hex_int(block.get('timestamp') if block else None)
            timestamp_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC') if timestamp is not None else ''
            status_hex = receipt.get('status') if receipt else None
            status = {'0x1': 'success', '0x0': 'failed'}.get(status_hex or '', 'unknown')

            rows.append({
                'tx_hash': tx_hash,
                'chain_timestamp_utc': timestamp_utc,
                'block': block_number if block_number is not None else '',
                'from': tx.get('from', ''),
                'to': tx.get('to') or '',
                'native_value_eth': wei_to_eth(tx.get('value')),
                'receipt_status': status,
                'receipt_status_hex': status_hex or '',
                'source_rows': ';'.join(txs[tx_hash]['source_rows']),
                'spreadsheet_dates': ' | '.join(txs[tx_hash]['spreadsheet_dates']),
                'spreadsheet_addresses': ' | '.join(txs[tx_hash]['spreadsheet_addresses']),
                'spreadsheet_amounts': ' | '.join(txs[tx_hash]['spreadsheet_amounts']),
                'spreadsheet_tokens': ' | '.join(txs[tx_hash]['spreadsheet_tokens']),
                'parse_notes': ' | '.join(txs[tx_hash]['parse_notes']),
                'rpc_endpoint_tx': tx_raw['endpoint'],
                'rpc_endpoint_receipt': receipt_raw['endpoint'],
                'rpc_endpoint_block': block_raw['endpoint'],
            })

    fieldnames = [
        'tx_hash',
        'chain_timestamp_utc',
        'block',
        'from',
        'to',
        'native_value_eth',
        'receipt_status',
        'receipt_status_hex',
        'source_rows',
        'spreadsheet_dates',
        'spreadsheet_addresses',
        'spreadsheet_amounts',
        'spreadsheet_tokens',
        'parse_notes',
        'rpc_endpoint_tx',
        'rpc_endpoint_receipt',
        'rpc_endpoint_block',
    ]
    with OUT_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    MANIFEST.write_text(
        json.dumps(
            {
                'created_at_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'input_csv': str(INPUT_CSV),
                'output_csv': str(OUT_CSV),
                'raw_jsonl': str(RAW_JSONL),
                'rpc_endpoints': RPC_ENDPOINTS,
                'unique_ethereum_tx_count': len(rows),
                'raw_rpc_response_count': raw_count,
                'excluded': 'Rows without etherscan.io transaction URLs were excluded from this Ethereum mainnet check, including the BscScan BNB row.',
            },
            indent=2,
            sort_keys=True,
        )
        + '\n',
        encoding='utf-8',
    )
    return rows


if __name__ == '__main__':
    rows = verify()
    print(f'wrote {OUT_CSV}')
    print(f'wrote {RAW_JSONL}')
    print(f'wrote {MANIFEST}')
    print(f'unique Ethereum txs: {len(rows)}')
    for row in rows:
        print(row['tx_hash'], row['chain_timestamp_utc'], row['block'], row['from'], row['to'], row['native_value_eth'], row['receipt_status'])

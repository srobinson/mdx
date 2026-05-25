#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import time
import urllib.request
from decimal import Decimal, getcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

ROOT = Path('/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25')
SRC = Path('/Users/alphab/.mdx/research/data/william-google-sheet-2026-05-25')
EXTRACTED = SRC / 'extracted-tabs'
OUT = ROOT / 'data' / 'spreadsheet-baseline'
RPC = OUT / 'rpc'
OUT.mkdir(parents=True, exist_ok=True)
RPC.mkdir(parents=True, exist_ok=True)

XLSX = SRC / 'william-source-spreadsheet.xlsx'
GID_CSV = SRC / 'gid-1211660592.csv'
SUMMARY_RAW = EXTRACTED / '01-Summary.csv'
SUMMARY_VISIBLE = ROOT / 'summary-visible-rows.csv'

TX_RE = re.compile(r'/tx/(0x[a-fA-F0-9]{64})')
HEX_RE = re.compile(r'0x[a-fA-F0-9]{64}')
getcontext().prec = 40


def read_csv(path: Path) -> list[list[str]]:
    with path.open(newline='', encoding='utf-8-sig') as f:
        return [row for row in csv.reader(f)]


def cell_ref_to_rc(ref: str) -> tuple[int, int]:
    m = re.match(r'([A-Z]+)([0-9]+)', ref)
    if not m:
        return (0, 0)
    col_letters, row_s = m.groups()
    col = 0
    for ch in col_letters:
        col = col * 26 + (ord(ch) - 64)
    return int(row_s), col


def read_xlsx_structure() -> list[dict]:
    ns = {
        'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
        'rel': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        'pkgrel': 'http://schemas.openxmlformats.org/package/2006/relationships',
    }
    with ZipFile(XLSX) as z:
        wb = ET.fromstring(z.read('xl/workbook.xml'))
        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        relmap = {r.attrib['Id']: r.attrib['Target'] for r in rels}
        result = []
        for idx, sheet in enumerate(wb.find('main:sheets', ns), 1):
            name = sheet.attrib['name']
            rid = sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            target = relmap[rid].lstrip('/')
            path = 'xl/' + target if not target.startswith('xl/') else target
            root = ET.fromstring(z.read(path))
            rows = root.findall('.//main:sheetData/main:row', ns)
            hidden_rows = [int(r.attrib.get('r', '0')) for r in rows if r.attrib.get('hidden') == '1']
            nonempty_cells = 0
            max_row = 0
            max_col = 0
            visible_nonempty_rows = 0
            for r in rows:
                row_has_value = False
                if r.attrib.get('r'):
                    max_row = max(max_row, int(r.attrib['r']))
                for c in r.findall('main:c', ns):
                    ref = c.attrib.get('r', '')
                    rr, cc = cell_ref_to_rc(ref)
                    max_row = max(max_row, rr)
                    max_col = max(max_col, cc)
                    has_val = c.find('main:v', ns) is not None or c.find('main:is', ns) is not None
                    if has_val:
                        nonempty_cells += 1
                        row_has_value = True
                if row_has_value and r.attrib.get('hidden') != '1':
                    visible_nonempty_rows += 1
            result.append({
                'index': idx,
                'sheet': name,
                'state': sheet.attrib.get('state', 'visible'),
                'target': path,
                'xml_rows': len(rows),
                'visible_nonempty_rows': visible_nonempty_rows,
                'hidden_rows': hidden_rows,
                'nonempty_cells': nonempty_cells,
                'max_row_from_cells': max_row,
                'max_col_from_cells': max_col,
            })
    return result


def csv_profile(path: Path) -> dict:
    rows = read_csv(path)
    return {
        'path': str(path),
        'rows': len(rows),
        'nonempty_rows': sum(any(c.strip() for c in r) for r in rows),
        'max_cols': max((len(r) for r in rows), default=0),
        'bytes': path.stat().st_size,
    }


def excel_serial_to_naive_iso(value: str) -> str:
    if not value:
        return ''
    try:
        serial = float(value)
    except ValueError:
        return ''
    dt = datetime(1899, 12, 30) + timedelta(days=serial)
    return dt.replace(microsecond=0).isoformat(sep=' ')


def clean(s: str) -> str:
    return (s or '').strip()


def tx_hash_from_url_or_text(s: str) -> str:
    m = TX_RE.search(s or '') or HEX_RE.search(s or '')
    return m.group(1).lower() if m else ''


def chain_from_url(url: str) -> str:
    if 'bscscan.com' in url.lower():
        return 'bsc'
    if 'etherscan.io' in url.lower():
        return 'ethereum'
    return ''


def get_row(rows: list[list[str]], one_based: int) -> list[str]:
    return rows[one_based - 1] if 0 <= one_based - 1 < len(rows) else []


def at(row: list[str], idx: int) -> str:
    return row[idx] if idx < len(row) else ''


def extract_summary_rows() -> list[dict]:
    gid = read_csv(GID_CSV)
    raw = read_csv(SUMMARY_RAW)
    out = []
    for source_row in range(5, 19):
        g = get_row(gid, source_row)
        r = get_row(raw, source_row)
        url = clean(at(g, 2))
        raw_serial = clean(at(r, 1))
        out.append({
            'source_kind': 'summary_upper',
            'source_file': str(GID_CSV),
            'source_sheet': 'Summary',
            'source_row': source_row,
            'wallet_address': clean(at(g, 0)),
            'date_displayed': clean(at(g, 1)),
            'date_serial_raw': raw_serial,
            'date_serial_as_wall_clock': excel_serial_to_naive_iso(raw_serial),
            'transaction_url': url,
            'chain': chain_from_url(url),
            'tx_hash': tx_hash_from_url_or_text(url),
            'sent_to': clean(at(g, 3)),
            'value_displayed': clean(at(g, 4)),
            'value_raw': clean(at(r, 4)),
            'amount_displayed': clean(at(g, 5)),
            'amount_raw': clean(at(r, 5)),
            'token': clean(at(g, 6)),
            'unit_price_displayed': clean(at(g, 7)),
            'unit_price_raw': clean(at(r, 7)),
            'note': 'upper summary transaction row',
        })
    # Fixed Float lower rows from the visible Google CSV export. These are not in the same table shape.
    for source_row in range(42, 46):
        g = get_row(gid, source_row)
        url = clean(at(g, 3))
        out.append({
            'source_kind': 'fixed_float_lower',
            'source_file': str(GID_CSV),
            'source_sheet': 'Summary',
            'source_row': source_row,
            'wallet_address': clean(at(g, 0)),
            'date_displayed': clean(at(g, 1)),
            'date_serial_raw': '',
            'date_serial_as_wall_clock': '',
            'transaction_url': url,
            'chain': chain_from_url(url),
            'tx_hash': tx_hash_from_url_or_text(url),
            'sent_to': clean(at(g, 4)),
            'value_displayed': '',
            'value_raw': '',
            'amount_displayed': clean(at(g, 2)),
            'amount_raw': clean(at(g, 2)),
            'token': 'ETH',
            'unit_price_displayed': '',
            'unit_price_raw': '',
            'note': 'lower Fixed Float copied row with its own UTC-labelled time',
        })
    return out


def extract_detail_rows() -> list[dict]:
    rows_out = []
    for p in sorted(EXTRACTED.glob('[0-9][0-9]-*.csv')):
        if p.name.startswith(('01-', '02-', '03-')):
            continue
        rows = read_csv(p)
        wallet = ''
        for row in rows:
            for i, c in enumerate(row):
                if c.strip().lower() == 'address':
                    for nxt in row[i+1:]:
                        if nxt.strip():
                            wallet = nxt.strip()
                            break
                    break
            if wallet:
                break
        for source_row, row in enumerate(rows, 1):
            url_col = None
            for i, c in enumerate(row):
                if TX_RE.search(c or ''):
                    url_col = i
                    break
            if url_col is None:
                continue
            url = clean(row[url_col])
            raw_serial = clean(row[url_col - 1]) if url_col > 0 else ''
            rows_out.append({
                'source_kind': 'detail_tab',
                'source_file': str(p),
                'source_sheet': p.stem[3:],
                'source_row': source_row,
                'wallet_address': wallet,
                'date_displayed': '',
                'date_serial_raw': raw_serial,
                'date_serial_as_wall_clock': excel_serial_to_naive_iso(raw_serial),
                'transaction_url': url,
                'chain': chain_from_url(url),
                'tx_hash': tx_hash_from_url_or_text(url),
                'sent_to': clean(row[url_col + 1]) if url_col + 1 < len(row) else '',
                'value_displayed': '',
                'value_raw': clean(row[url_col + 2]) if url_col + 2 < len(row) else '',
                'amount_displayed': '',
                'amount_raw': clean(row[url_col + 3]) if url_col + 3 < len(row) else '',
                'token': clean(row[url_col + 4]) if url_col + 4 < len(row) else '',
                'unit_price_displayed': '',
                'unit_price_raw': clean(row[url_col + 5]) if url_col + 5 < len(row) else '',
                'note': 'per-wallet detail tab transaction row',
            })
    return rows_out


def rpc_call(url: str, method: str, params: list, timeout: int = 30) -> dict:
    req = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}
    request = urllib.request.Request(
        url,
        data=json.dumps(req).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'User-Agent': 'codex-spreadsheet-baseline'},
    )
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        body = json.loads(resp.read().decode('utf-8'))
    return {'url': url, 'request': req, 'response': body}


def save_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding='utf-8')


def fetch_chain(rows: list[dict]) -> list[dict]:
    endpoints = {
        'ethereum': 'https://ethereum.publicnode.com',
        'bsc': 'https://bsc-dataseed.binance.org',
    }
    unique = []
    seen = set()
    for row in rows:
        key = (row['chain'], row['tx_hash'])
        if row['chain'] in endpoints and row['tx_hash'] and key not in seen:
            seen.add(key)
            unique.append(key)
    results = []
    for chain, tx in unique:
        endpoint = endpoints[chain]
        prefix = f'{chain}-{tx}'
        try:
            tx_resp = rpc_call(endpoint, 'eth_getTransactionByHash', [tx])
            save_json(RPC / f'{prefix}-transaction.json', tx_resp)
            tx_result = tx_resp.get('response', {}).get('result')
            block_hex = tx_result.get('blockNumber') if isinstance(tx_result, dict) else None
            receipt_resp = rpc_call(endpoint, 'eth_getTransactionReceipt', [tx])
            save_json(RPC / f'{prefix}-receipt.json', receipt_resp)
            block_resp = None
            block_result = None
            if block_hex:
                block_resp = rpc_call(endpoint, 'eth_getBlockByNumber', [block_hex, False])
                save_json(RPC / f'{prefix}-block.json', block_resp)
                block_result = block_resp.get('response', {}).get('result')
            ts_hex = None
            if isinstance(block_result, dict):
                ts_hex = block_result.get('timestamp')
            if not ts_hex and isinstance(tx_result, dict):
                ts_hex = tx_result.get('blockTimestamp')
            chain_utc = ''
            if ts_hex:
                chain_utc = datetime.fromtimestamp(int(ts_hex, 16), timezone.utc).isoformat().replace('+00:00', 'Z')
            results.append({
                'chain': chain,
                'tx_hash': tx,
                'rpc_endpoint': endpoint,
                'block_number_hex': block_hex or '',
                'block_number': int(block_hex, 16) if block_hex else '',
                'timestamp_hex': ts_hex or '',
                'chain_utc': chain_utc,
                'transaction_json': str(RPC / f'{prefix}-transaction.json'),
                'receipt_json': str(RPC / f'{prefix}-receipt.json'),
                'block_json': str(RPC / f'{prefix}-block.json') if block_hex else '',
                'confidence': 'confirmed' if chain_utc else 'unresolved',
            })
            time.sleep(0.15)
        except Exception as e:
            results.append({
                'chain': chain,
                'tx_hash': tx,
                'rpc_endpoint': endpoint,
                'block_number_hex': '',
                'block_number': '',
                'timestamp_hex': '',
                'chain_utc': '',
                'transaction_json': '',
                'receipt_json': '',
                'block_json': '',
                'confidence': 'unresolved',
                'error': repr(e),
            })
    return results


def parse_display_date_to_utc(text: str) -> datetime | None:
    text = text.strip()
    for fmt in ['%d %b, %Y %H:%M:%S UTC', '%d %b, %Y %H:%M UTC']:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def parse_summary_wall_clock(text: str) -> datetime | None:
    text = text.strip()
    for fmt in ['%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M']:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def compare_rows(rows: list[dict], chain_rows: list[dict]) -> list[dict]:
    by_tx = {(r['chain'], r['tx_hash']): r for r in chain_rows}
    comparisons = []
    for row in rows:
        cr = by_tx.get((row['chain'], row['tx_hash']))
        chain_dt = None
        if cr and cr.get('chain_utc'):
            chain_dt = datetime.fromisoformat(cr['chain_utc'].replace('Z', '+00:00'))
        sheet_wall = parse_summary_wall_clock(row['date_displayed'])
        if sheet_wall is None and row['date_serial_as_wall_clock']:
            sheet_wall = datetime.fromisoformat(row['date_serial_as_wall_clock'])
        lower_utc = parse_display_date_to_utc(row['date_displayed'])
        delta_seconds = ''
        interpretation = 'unresolved'
        if chain_dt and sheet_wall:
            # Compare treating spreadsheet wall clock as UTC first. A +4h delta means the sheet likely stores New York local wall time.
            delta_seconds = int((chain_dt.replace(tzinfo=None) - sheet_wall).total_seconds())
            if delta_seconds == 14400:
                interpretation = 'spreadsheet wall clock is exactly UTC-4 behind chain UTC, likely EDT display without timezone label'
            elif delta_seconds == 0:
                interpretation = 'spreadsheet wall clock equals chain UTC'
            else:
                interpretation = f'spreadsheet wall clock differs from chain UTC by {delta_seconds} seconds'
        elif chain_dt and lower_utc:
            delta_seconds = int((lower_utc - chain_dt).total_seconds())
            if delta_seconds == 0:
                interpretation = 'UTC-labelled lower row equals chain UTC'
            else:
                interpretation = f'UTC-labelled lower row differs from chain UTC by {delta_seconds} seconds'
        comparisons.append({
            'source_kind': row['source_kind'],
            'source_row': row['source_row'],
            'tx_hash': row['tx_hash'],
            'sheet_date_displayed': row['date_displayed'],
            'date_serial_raw': row['date_serial_raw'],
            'date_serial_as_wall_clock': row['date_serial_as_wall_clock'],
            'chain_utc': cr.get('chain_utc', '') if cr else '',
            'delta_seconds': delta_seconds,
            'interpretation': interpretation,
        })
    return comparisons


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = sorted({k for row in rows for k in row.keys()})
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def extract_native_transactions_from_rpc() -> list[dict]:
    rows = []
    for path in sorted(RPC.glob('*-transaction.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        result = data.get('response', {}).get('result') or {}
        value_hex = result.get('value') or '0x0'
        native_value = Decimal(int(value_hex, 16)) / (Decimal(10) ** 18)
        rows.append({
            'chain': 'bsc' if path.name.startswith('bsc-') else 'ethereum',
            'tx_hash': (result.get('hash') or '').lower(),
            'from': result.get('from') or '',
            'to': result.get('to') or '',
            'native_value': str(native_value.normalize()),
        })
    return rows


def main() -> None:
    structure = read_xlsx_structure()
    save_json(OUT / 'workbook-structure.json', structure)
    profiles = [csv_profile(GID_CSV), csv_profile(SUMMARY_VISIBLE), csv_profile(SUMMARY_RAW)]
    profiles.extend(csv_profile(p) for p in sorted(EXTRACTED.glob('*.csv')) if p.name != '01-Summary.csv')
    save_json(OUT / 'csv-profiles.json', profiles)

    rows = extract_summary_rows() + extract_detail_rows()
    row_fields = ['source_kind','source_file','source_sheet','source_row','wallet_address','date_displayed','date_serial_raw','date_serial_as_wall_clock','transaction_url','chain','tx_hash','sent_to','value_displayed','value_raw','amount_displayed','amount_raw','token','unit_price_displayed','unit_price_raw','note']
    write_csv(OUT / 'normalized-spreadsheet-rows.csv', rows, row_fields)

    chain = fetch_chain(rows)
    write_csv(OUT / 'chain-times.csv', chain, ['chain','tx_hash','rpc_endpoint','block_number_hex','block_number','timestamp_hex','chain_utc','confidence','transaction_json','receipt_json','block_json','error'])
    write_csv(OUT / 'chain-transactions-native.csv', extract_native_transactions_from_rpc(), ['chain','tx_hash','from','to','native_value'])

    comps = compare_rows([r for r in rows if r['source_kind'] in ('summary_upper','fixed_float_lower')], chain)
    write_csv(OUT / 'date-comparisons.csv', comps, ['source_kind','source_row','tx_hash','sheet_date_displayed','date_serial_raw','date_serial_as_wall_clock','chain_utc','delta_seconds','interpretation'])

    print(json.dumps({
        'workbook_sheets': len(structure),
        'normalized_rows': len(rows),
        'unique_chain_txs': len(chain),
        'outputs': [str(OUT / name) for name in ['workbook-structure.json','csv-profiles.json','normalized-spreadsheet-rows.csv','chain-times.csv','chain-transactions-native.csv','date-comparisons.csv']],
    }, indent=2))


if __name__ == '__main__':
    main()

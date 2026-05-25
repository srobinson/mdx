#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
umask 077

readonly ADDRESS="${BTC_ADDRESS:-bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g}"
readonly DATA_DIR="${DATA_DIR:-/Users/alphab/.mdx/research/data/william-live-recheck-2026-05-25}"
readonly TS="$(date -u +%Y%m%dT%H%M%SZ)"
readonly CURL_UA="william-live-btc-check/1.0 read-only evidence capture"

need_tool() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'missing required tool: %s\n' "$1" >&2
    exit 127
  fi
}

json_check() {
  local path="$1"
  python3 - "$path" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    json.load(handle)
PY
}

fetch_json() {
  local label="$1"
  local url="$2"
  local out="$3"
  local tmp="${out}.tmp.$$"

  rm -f "$tmp"
  printf 'GET %s\n' "$url" >&2
  curl \
    --request GET \
    --fail \
    --silent \
    --show-error \
    --location \
    --retry 2 \
    --retry-delay 1 \
    --connect-timeout 10 \
    --max-time 30 \
    --user-agent "$CURL_UA" \
    --header 'Accept: application/json' \
    --output "$tmp" \
    "$url"

  json_check "$tmp"
  mv "$tmp" "$out"
  printf 'saved %s: %s\n' "$label" "$out" >&2
}

need_tool curl
need_tool python3
mkdir -p "$DATA_DIR"

readonly BLOCKSTREAM_ADDRESS_JSON="$DATA_DIR/$TS-blockstream-address-$ADDRESS.json"
readonly BLOCKSTREAM_UTXO_JSON="$DATA_DIR/$TS-blockstream-utxo-$ADDRESS.json"
readonly BLOCKSTREAM_MEMPOOL_JSON="$DATA_DIR/$TS-blockstream-mempool-$ADDRESS.json"
readonly MEMPOOL_ADDRESS_JSON="$DATA_DIR/$TS-mempool-space-address-$ADDRESS.json"
readonly MEMPOOL_UTXO_JSON="$DATA_DIR/$TS-mempool-space-utxo-$ADDRESS.json"
readonly MEMPOOL_MEMPOOL_JSON="$DATA_DIR/$TS-mempool-space-mempool-$ADDRESS.json"

fetch_json \
  'Blockstream address stats' \
  "https://blockstream.info/api/address/$ADDRESS" \
  "$BLOCKSTREAM_ADDRESS_JSON"
fetch_json \
  'Blockstream UTXOs' \
  "https://blockstream.info/api/address/$ADDRESS/utxo" \
  "$BLOCKSTREAM_UTXO_JSON"
fetch_json \
  'Blockstream mempool transactions' \
  "https://blockstream.info/api/address/$ADDRESS/txs/mempool" \
  "$BLOCKSTREAM_MEMPOOL_JSON"
fetch_json \
  'mempool.space address stats' \
  "https://mempool.space/api/address/$ADDRESS" \
  "$MEMPOOL_ADDRESS_JSON"
fetch_json \
  'mempool.space UTXOs' \
  "https://mempool.space/api/address/$ADDRESS/utxo" \
  "$MEMPOOL_UTXO_JSON"
fetch_json \
  'mempool.space mempool transactions' \
  "https://mempool.space/api/address/$ADDRESS/txs/mempool" \
  "$MEMPOOL_MEMPOOL_JSON"

python3 - \
  "$ADDRESS" \
  "$TS" \
  "$DATA_DIR" \
  "$BLOCKSTREAM_ADDRESS_JSON" \
  "$BLOCKSTREAM_UTXO_JSON" \
  "$BLOCKSTREAM_MEMPOOL_JSON" \
  "$MEMPOOL_ADDRESS_JSON" \
  "$MEMPOOL_UTXO_JSON" \
  "$MEMPOOL_MEMPOOL_JSON" <<'PY'
import json
import sys
from decimal import Decimal
from pathlib import Path

SATOSHIS_PER_BTC = Decimal("100000000")
address = sys.argv[1]
ts = sys.argv[2]
data_dir = sys.argv[3]
paths = {
    "Blockstream": {
        "address": Path(sys.argv[4]),
        "utxo": Path(sys.argv[5]),
        "mempool": Path(sys.argv[6]),
    },
    "mempool.space": {
        "address": Path(sys.argv[7]),
        "utxo": Path(sys.argv[8]),
        "mempool": Path(sys.argv[9]),
    },
}

failures = []

def load(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def int_field(obj, key, label):
    value = obj.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, int):
        failures.append(f"{label}.{key} is not an integer")
        return 0
    return value

def btc(sats):
    return Decimal(sats) / SATOSHIS_PER_BTC

def summarize(label, files):
    address_doc = load(files["address"])
    utxos = load(files["utxo"])
    mempool_txs = load(files["mempool"])

    returned_address = address_doc.get("address")
    if returned_address != address:
        failures.append(f"{label} returned address {returned_address!r}, expected {address!r}")

    if not isinstance(utxos, list):
        failures.append(f"{label} UTXO response is not a list")
        utxos = []
    if not isinstance(mempool_txs, list):
        failures.append(f"{label} mempool response is not a list")
        mempool_txs = []

    chain_stats = address_doc.get("chain_stats", {})
    mempool_stats = address_doc.get("mempool_stats", {})
    if not isinstance(chain_stats, dict):
        failures.append(f"{label} chain_stats is not an object")
        chain_stats = {}
    if not isinstance(mempool_stats, dict):
        failures.append(f"{label} mempool_stats is not an object")
        mempool_stats = {}

    chain_funded = int_field(chain_stats, "funded_txo_sum", f"{label}.chain_stats")
    chain_spent = int_field(chain_stats, "spent_txo_sum", f"{label}.chain_stats")
    mempool_funded = int_field(mempool_stats, "funded_txo_sum", f"{label}.mempool_stats")
    mempool_spent = int_field(mempool_stats, "spent_txo_sum", f"{label}.mempool_stats")
    mempool_stats_count = int_field(mempool_stats, "tx_count", f"{label}.mempool_stats")

    utxo_sum = 0
    for index, utxo in enumerate(utxos):
        if not isinstance(utxo, dict):
            failures.append(f"{label} UTXO {index} is not an object")
            continue
        value = utxo.get("value")
        if isinstance(value, bool) or not isinstance(value, int):
            failures.append(f"{label} UTXO {index} value is not an integer")
            continue
        utxo_sum += value

    funded_total = chain_funded + mempool_funded
    spent_total = chain_spent + mempool_spent
    computed_balance = funded_total - spent_total
    mempool_endpoint_count = len(mempool_txs)
    mempool_tx_count = max(mempool_stats_count, mempool_endpoint_count)

    if mempool_stats_count != mempool_endpoint_count:
        failures.append(
            f"{label} mempool_stats.tx_count={mempool_stats_count} but mempool endpoint count={mempool_endpoint_count}"
        )
    if mempool_tx_count == 0 and utxo_sum != computed_balance:
        failures.append(
            f"{label} UTXO sum {utxo_sum} does not equal computed balance {computed_balance}"
        )

    return {
        "label": label,
        "chain_funded": chain_funded,
        "chain_spent": chain_spent,
        "mempool_funded": mempool_funded,
        "mempool_spent": mempool_spent,
        "funded_total": funded_total,
        "spent_total": spent_total,
        "computed_balance": computed_balance,
        "utxo_count": len(utxos),
        "utxo_sum": utxo_sum,
        "mempool_tx_count": mempool_tx_count,
        "files": files,
    }

summaries = [summarize(label, files) for label, files in paths.items()]
reference = summaries[0]
for current in summaries[1:]:
    for key in (
        "funded_total",
        "spent_total",
        "computed_balance",
        "utxo_count",
        "utxo_sum",
        "mempool_tx_count",
    ):
        if reference[key] != current[key]:
            failures.append(
                f"provider mismatch for {key}: {reference['label']}={reference[key]}, {current['label']}={current[key]}"
            )

print("William live BTC recheck")
print(f"timestamp_utc: {ts}")
print(f"address: {address}")
print(f"data_dir: {data_dir}")
print("")
for item in summaries:
    print(f"provider: {item['label']}")
    print(f"  funded sats: {item['funded_total']} total, {item['chain_funded']} confirmed, {item['mempool_funded']} mempool")
    print(f"  spent sats: {item['spent_total']} total, {item['chain_spent']} confirmed, {item['mempool_spent']} mempool")
    print(f"  computed balance: {item['computed_balance']} sats, {btc(item['computed_balance']):.8f} BTC")
    print(f"  UTXO count: {item['utxo_count']}")
    print(f"  UTXO value sum: {item['utxo_sum']} sats")
    print(f"  mempool tx count: {item['mempool_tx_count']}")
    print("")

max_mempool = max(item["mempool_tx_count"] for item in summaries)
if max_mempool > 0:
    print(f"URGENT: mempool activity detected, count={max_mempool}")
else:
    print("Mempool status: no pending transactions found by either provider")

if failures:
    print("Cross check: FAIL")
    for failure in failures:
        print(f"  {failure}")
    sys.exit(2)

print("Cross check: PASS")
PY

#!/usr/bin/env python3
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/Users/alphab/.mdx/research/william-thorough-recheck-2026-05-25")
SOURCE = BASE / "summary-visible-rows.csv"
OUTDIR = BASE / "data" / "orchestrator-chain-check-fast"

RPCS = {
    "ethereum": [
        "https://ethereum.publicnode.com",
        "https://rpc.flashbots.net",
    ],
    "bsc": [
        "https://bsc-rpc.publicnode.com",
        "https://bsc-dataseed.binance.org",
    ],
}


def hex_int(value):
    if not value:
        return None
    return int(value, 16)


def rpc(chain, method, params, raw_name):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    errors = []
    for url in RPCS[chain]:
        proc = subprocess.run(
            [
                "curl",
                "--max-time",
                "10",
                "--silent",
                "--show-error",
                "-X",
                "POST",
                url,
                "-H",
                "content-type: application/json",
                "--data",
                json.dumps(payload),
            ],
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            errors.append({"url": url, "stderr": proc.stderr.strip(), "returncode": proc.returncode})
            continue
        try:
            obj = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            errors.append({"url": url, "error": f"json decode: {exc}", "body": proc.stdout[:500]})
            continue
        if obj.get("error"):
            errors.append({"url": url, "error": obj["error"]})
            continue
        (OUTDIR / raw_name).write_text(
            json.dumps({"url": url, "request": payload, "response": obj}, indent=2),
            encoding="utf-8",
        )
        return obj.get("result"), url
    raise RuntimeError(f"{chain} {method} failed: {errors}")


def load_visible_txs():
    by_tx = {}
    with SOURCE.open(newline="") as f:
        for row in csv.DictReader(f):
            url = row["transaction_url"].strip()
            if "/tx/0x" not in url:
                continue
            tx_hash = url.rsplit("/", 1)[-1].strip()
            chain = "bsc" if "bscscan.com" in url else "ethereum"
            entry = by_tx.setdefault(
                tx_hash,
                {
                    "chain": chain,
                    "tx_hash": tx_hash,
                    "explorer_url": url,
                    "source_rows": [],
                    "spreadsheet_dates": [],
                    "spreadsheet_from_addresses": [],
                },
            )
            entry["source_rows"].append(row["source_row"])
            entry["spreadsheet_dates"].append(row["date_as_displayed"])
            entry["spreadsheet_from_addresses"].append(row["address"])
    return list(by_tx.values())


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    results = []
    for item in load_visible_txs():
        chain = item["chain"]
        tx_hash = item["tx_hash"]
        tx, tx_url = rpc(chain, "eth_getTransactionByHash", [tx_hash], f"{chain}-{tx_hash}-transaction.json")
        receipt, receipt_url = rpc(chain, "eth_getTransactionReceipt", [tx_hash], f"{chain}-{tx_hash}-receipt.json")
        block_number_hex = (tx or {}).get("blockNumber") or (receipt or {}).get("blockNumber")
        block, block_url = rpc(chain, "eth_getBlockByNumber", [block_number_hex, False], f"{chain}-{tx_hash}-block.json")
        ts = hex_int((block or {}).get("timestamp"))
        value_wei = hex_int((tx or {}).get("value")) or 0
        results.append(
            {
                "chain": chain,
                "tx_hash": tx_hash,
                "explorer_url": item["explorer_url"],
                "source_rows": ";".join(item["source_rows"]),
                "spreadsheet_dates": " | ".join(item["spreadsheet_dates"]),
                "spreadsheet_from_addresses": " | ".join(item["spreadsheet_from_addresses"]),
                "block_number": hex_int(block_number_hex),
                "block_timestamp_unix": ts,
                "block_timestamp_utc": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z") if ts else "",
                "from": (tx or {}).get("from", ""),
                "to_transaction": (tx or {}).get("to", ""),
                "native_value_wei": str(value_wei),
                "native_value_eth_or_bnb": f"{value_wei / 10**18:.18f}".rstrip("0").rstrip("."),
                "receipt_status": str(hex_int((receipt or {}).get("status"))) if (receipt or {}).get("status") else "",
                "transaction_rpc": tx_url,
                "receipt_rpc": receipt_url,
                "block_rpc": block_url,
            }
        )
    out_csv = OUTDIR / "verified-chain-timestamps.csv"
    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(out_csv)
    for row in results:
        print(
            row["chain"],
            row["tx_hash"][:12],
            row["block_timestamp_utc"],
            row["from"],
            "->",
            row["to_transaction"],
            row["native_value_eth_or_bnb"],
            "status",
            row["receipt_status"],
        )


if __name__ == "__main__":
    main()

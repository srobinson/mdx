# William Transaction Inventory Build

Created: 2026-05-25

## Summary

Built `/Users/alphab/.mdx/research/transaction-inventory.csv` with 30 data rows and the required header. The inventory preserves parsed source CSV transaction evidence, adds BTC and THORChain derived rows from the dossier and live snapshot files, and keeps attribution language conservative.

## Inputs

| Input | SHA256 |
|---|---|
| `/Users/alphab/Downloads/Stolen Crypto July 2021 - Summary.csv` | `251d96652640e7d1d41d2ae0210647ffcc6aa2a80e3ddeec0e193830ccfcc064` |
| `/Users/alphab/.mdx/research/william-crypto-case-dossier.md` | `b09db7f55ed5af0214b401fbcb99d2d028f6f4917f1365613abce520fc59fd0a` |
| `/Users/alphab/.mdx/research/william-monitoring-tooling-codex.md` | `a55913be57de74ca9db9a086f8ba9166c1227186871fef2401d38a449066a45f` |
| `/Users/alphab/.mdx/research/data/william-live-check-2026-05-25` | snapshot directory, individual JSON files referenced in `evidence_file` |

## Parsing Assumptions

1. Source CSV physical rows 5 through 18 are the main transaction table. Rows 1 through 3 are summary rows and row 4 is the table header.
2. Source CSV main table timestamps are not labeled with a timezone. They were normalized as UTC minus four hours because duplicate FixedFloat rows with explicit UTC times align with that offset in July 2023. This is an evidence preserving assumption, not a service attribution claim.
3. Source CSV rows 42 through 45 are FixedFloat section rows with explicit UTC timestamps. They duplicate or supplement main transaction rows and are retained separately.
4. `amount_native` for source CSV rows uses the positive magnitude from the source amount column. Derived THORChain rows use Midgard base unit conversion to BTC or ETH decimal units.
5. Ethereum and BSC txids retain the `0x` prefix. Bitcoin txids are lowercase. THORChain Midgard txids are uppercase without `0x`.
6. Address aggregate rows use snapshot date `2026-05-25T00:00:00Z` because the snapshot filenames carry the date but the JSON files do not carry exact fetch time metadata.
7. Service labels are intentionally conservative. `high`, `medium-high`, `medium`, `low`, and `unknown` are used exactly as confidence labels, and no row claims official Binance or FixedFloat confirmation.

## Source CSV Rows Included

Included parsed source rows: 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 38, 42, 43, 44, 45.

- Rows 5 through 18: main source transaction table.
- Row 38: standalone FixedFloat related tx URL.
- Rows 42 through 45: FixedFloat deposit section with explicit UTC timestamps.

## Derived Rows Added

Derived roles added:

- `thorchain-swap-output-to-wasabi`
- `thorchain-swap-output-to-wasabi`
- `wasabi-deposit-address`
- `low-confidence-demix-candidate`
- `live-btc-utxo-address`
- `demix-candidate-consolidation`
- `downstream-candidate-branch`
- `live-utxo-funding`
- `probable-binance-branch`
- `march-2026-dust-noise`
- `fixedfloat-side-path-summary`

Key derived coverage:

- Wasabi deposit address `bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s`.
- Low confidence demix candidate `bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl`.
- Live BTC UTXO address `bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g`.
- Probable Binance branch `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` through tx `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287`.
- FixedFloat side path supported by source CSV rows 38 and 42 through 45.
- THORChain txids `655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204` and `40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C`.
- March 2026 dust tx `4fadadf21aa579fa6b2ee370c903b1220ce1c815598ddb3110b8a2087ebd83e5` as noise.

## Validation Commands Run

- python3 /tmp/build_william_inventory.py wrote the CSV and build notes from the provided local inputs.
- Python csv validation confirmed the required header, 30 data rows, all parsed source rows, required derived roles, and existing evidence_file paths.
- wc -l confirmed both output files exist.

## Open Data Gaps

1. The main source CSV timezone is inferred from duplicate FixedFloat rows, not explicitly stated in the CSV.
2. The source CSV gives several EVM destinations without independent service labels. Rows using `possible FixedFloat staging` remain low confidence.
3. The Wasabi demix candidate remains low confidence until paid analytics or law enforcement independently validates it.
4. The probable Binance branch remains medium high, not official confirmation. Binance records require law enforcement process.
5. The dossier states the Binance branch time as `2024-06-22 15:44:45 UTC`, while the Blockstream snapshot for tx `29575abd53550ed73aa606eab43448c43790232388de7152081a322ffd355287` has block time `2024-06-22T14:51:25Z`. The CSV preserves the snapshot time and notes the discrepancy.
6. No broad web research was performed. The inventory uses provided source files and existing local snapshots only.

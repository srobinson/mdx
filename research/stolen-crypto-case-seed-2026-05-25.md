---
title: William Stolen Crypto Case Seed
type: research
tags: [crypto-theft, bitcoin, thorchain, wasabi, law-enforcement, osint]
summary: Shared fact base for a multi-round research sweep into recovery paths, tools, case precedents, and live leads.
status: active
confidence: medium
created: 2026-05-25
updated: 2026-05-25
---

# Summary

William's theft file is `/Users/alphab/Downloads/Stolen Crypto July 2021 - Summary.csv`.

The CSV content shows events on July 21 to 23, 2023, despite the filename saying July 2021. Treat July 2023 as the working incident period until William confirms otherwise.

Known loss surface in the CSV:

- Total value at theft time listed in CSV: `$1,675,929.20`.
- Total ETH listed: `884.8222 ETH`.
- Total BNB listed: `8.6 BNB`.
- Primary destination path: ETH wallets to THORChain router, then BTC to Wasabi.
- Secondary path: some ETH went directly or indirectly to FixedFloat.

# Victim EVM Wallets

```text
0xaadd5f9d0fa1411f612d75336eee5eb87092f1f0
0x1c0b5b8d36587d0516839df7ebfb49ad8f3c543c
0x055e6b081f175db1170350ba4f23e3a8e0895492
0xd20a9ed00e37fdaef0a064bc32feb10845053f09
0xa30e54cb3593c6afca653621c4d3ee2105f015aa
0xdfb05c98320d126bcc74f6eb7960e99669dcd49a
0x9dc08da4cbf74f81cffb54cecbd8fdf6554e1d34
0x2656269bb878ca0c4250a0df4c15a9cfca0c21ac
0xfa5f6ed82ae1eac484b91ccde42fe7d64cb68d03
0xf40c09c782c74e932b81473ae68b078f31a358f6
```

# Initial High Value EVM Transactions From CSV

```text
0x655a2a55bc724718bca78b7645347f448d1ca52b9f051ac3b6b8f2e36651d204
0x662e469715056d9501da5184ec4a2a466b05b3fa656c73d0fb067598b88013c2
0x2ed79b067f3afa2e636ae82f8c0c6cbd59d504aa7f25f146a4d22ef2186fc157
0x91a3d5976df4c7fb6d000a081855b4fc217d61d6e1b71f5c99205e7dc7c2f63f
0xc2235fdf93d6ed97f17ea248d40fbc6c910cb502a63c75f0bb131bbb0fb465a8
0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3
0x0fa037ee4e0a99004dd98ca4827a9aaa9e45e56acd2b74334f09b16ad57050c3
0x266ef6a62efc7fc3e6e8c9e4c0d31f844208429d9e3b58f5d998f8da58c230d1
0xa2dc0cff0e555bf26d8044e39e92071e69587e62bfe4128f827b0eb9bdfc8681
0x72d855932534ca55ae820f5ed17de8ac729b1f05b093352b5bca19dcf868f26f
0xd5a730adbe95e809d765372997260dd7057e959399e9b41d415816218de3686d
0x3f58b9738767a04a8d4701052cbfa378f7cdf9d8a0cfac34b43b0d62f766a7e8
0x85955c171d41591fb52b85f3e4135704f2afb4305ea9ceee1de1ba503703e7f1
```

# THORChain To BTC Path

Wasabi deposit address:

```text
bc1qwxwl5l209je4c2ycr8hc7dq7jqfptk23esmn5s
```

Verified via Blockstream on May 25, 2026:

- Funded UTXO count: `7`.
- Funded sum: `40.70902128 BTC`.
- Spent UTXO count: `7`.
- Spent sum: `40.70902128 BTC`.
- Current balance: `0 BTC`.

Verified THORChain Midgard examples:

- `0x655A2A55BC724718BCA78B7645347F448D1CA52B9F051AC3B6B8F2E36651D204`: `125.44715147 ETH` in, `7.29622713 BTC` out to the Wasabi address.
- `40A3D546F349F9CF8E907B6676E6187AD01F24C76AD9D0B9D2958E8C9E059E2C`: `727.29568000 ETH` in, `31.37643194 BTC` out to the Wasabi address.

# Prior Demix Feedback

A prior demix review said seven deposits went to the same Wasabi deposit address, then forwarded to six coinjoin transactions between July 21 and 23, 2023. The reviewer returned one low confidence candidate:

```text
bc1q9vl045g9ln6eu8vgh2r47zd4sustac9jrtjzdl
```

Verified via Blockstream on May 25, 2026:

- Candidate address funded sum: `47.63611646 BTC`.
- Candidate address spent sum: `47.63611646 BTC`.
- Current balance: `0 BTC`.

Important caution: the prior reviewer called this a low confidence candidate. Treat all downstream paths from this address as investigative leads, not attribution.

# Downstream Lead From Candidate Address

Candidate address spend of interest:

```text
1962037495cfc6f39cd0c525b78fdcffddb98de34babdcf785b12208152e9bb2
```

That transaction spent `35.9705224 BTC` from the candidate address on October 6, 2023 to:

```text
bc1qtvj76tqmhazw8dl5yx9ep9hs32xxlcletrf6p8
```

Subsequent mainline tracing found peeling behavior through 2024. A later branch showed:

```text
bc1qyt2747r9n3dpxq8rgt5e8pc0qy9q0cvcptt85g
```

Verified via Blockstream on May 25, 2026:

- Funded sum: `6.49998534 BTC`.
- Spent sum: `0 BTC`.
- Current balance: `6.49998534 BTC`.
- It also received a tiny extra UTXO on March 11, 2026.

This is the strongest live watchlist lead, subject to the low confidence caveat on the demix candidate.

# Service Like Branch

Another branch sent `0.09998037 BTC` to:

```text
17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva
```

Verified via Blockstream on May 25, 2026:

- Very high volume address, more than `133,000` funded UTXOs and more than `9933 BTC` funded sum.
- Current balance: `0 BTC`.

Public data alone does not identify the service. Research should try to label it from independent sources, but should not overstate attribution.

# FixedFloat From CSV

FixedFloat related entries from the CSV include:

```text
0xaa49f832a539cabee457ca3fc2e3e47e70ca7e364ba48161aae8c4e788d07b33
0x931ebd9671d532e81ef15211ce16e193615765747e4a906d9dabb278f792f2f3
0x91a3d5976df4c7fb6d000a081855b4fc217d61d6e1b71f5c99205e7dc7c2f63f
0x72d855932534ca55ae820f5ed17de8ac729b1f05b093352b5bca19dcf868f26f
0xb5e309a09f479a87f71b1258380d8b8e62c84163364b3b06762927c476c4d655
```

FixedFloat wallet shown in CSV:

```text
0x4E5B2e1dc63F6b91cb6Cd759936495434C7e972F
```

Other destination wallets listed:

```text
0xbdC4b2D85d9DCC42C3799b4569bd1D7D25D29C03
0x4EC986035B635D09474fC390AcDF5c107DDa4c70
0x09066E7857D3a9a53c9142f8a7eFFcBc7989F1B5
```

# Research Questions

1. What real world case examples show successful recovery or freezing after crypto theft involving mixers, bridges, swap services, or CEX endpoints?
2. Which reporting and preservation channels are most likely to matter now: IC3, local police, FBI field office, IRS CI, Secret Service, exchange legal portals, blockchain analytics firms, Chainabuse, TRM, Chainalysis, Elliptic, Crystal, CipherTrace, ZachXBT or similar?
3. What tools can help generate better leads from the specific addresses above, especially Wasabi demix candidates, service attribution, and watchlist alerts?
4. Can any public source label `17StnGroPUsNXBq4AVJQ1fqGftoFZh3zva` or the later peeling chain?
5. What are the highest leverage next steps William can take this week?

# Required Evidence Discipline

- Separate facts from inferences.
- Cite URLs and dates.
- Do not promise recovery.
- Do not contact suspects.
- Do not include private keys or seed phrases.
- Treat the demix candidate as low confidence until independently strengthened.

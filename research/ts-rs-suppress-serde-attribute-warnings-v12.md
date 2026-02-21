---
title: Suppressing ts-rs "failed to parse serde attribute" warnings
type: research
tags: [rust, ts-rs, serde, proc-macro, warnings]
summary: Use the `no-serde-warnings` Cargo feature in ts-rs to silence all "failed to parse serde attribute" warnings. This is the only supported suppression mechanism.
status: active
source: quick-research
confidence: high
created: 2026-03-20
updated: 2026-03-20
---

## Summary

The **only supported way** to suppress ts-rs "failed to parse serde attribute" warnings is the `no-serde-warnings` Cargo feature flag. It exists in v12.0.1 (confirmed against the published Cargo.toml). No rustc-level mechanism can target proc-macro-emitted warnings specifically.

```toml
[dependencies]
ts-rs = { version = "12.0.1", features = ["no-serde-warnings"] }
```

## Details

### How the warning is emitted

ts-rs does not use the `proc_macro_diagnostic` API (still unstable as of 2026). Instead it `eprintln!`s a string formatted to look like a compiler warning. See `macros/src/utils.rs`:

```rust
if cfg!(not(feature = "no-serde-warnings")) {
    crate::utils::warning::print_warning(
        "failed to parse serde attribute",
        ...,
        "ts-rs failed to parse this attribute. It will be ignored.",
    )
}
```

This means:
- `#[allow(...)]` cannot suppress it — it is not a real rustc lint.
- `RUSTFLAGS="-A ..."` cannot suppress it.
- There is no per-attribute or per-struct ts-rs attribute to opt out.
- The `no-serde-warnings` feature is an all-or-nothing gate.

### Which attributes trigger the warning

Any `#[serde(...)]` attribute that ts-rs's parser does not recognise will trigger the warning. Confirmed noisy examples from GitHub issues:
- `try_from = "..."` and `into = "..."` (your case)
- `borrow`
- `deny_unknown_fields`
- `skip_serializing_if = "..."`
- `deserialize_with = "..."`
- `crate = "..."` (fixed in a later patch, was issue #443)

### Safety of suppressing

Per ts-rs maintainer comment on issue #436: when a serde attribute actually breaks type generation (rather than just being irrelevant to TypeScript output), it will manifest as a **compiler error**, not a warning. Silencing warnings with `no-serde-warnings` is safe. `try_from`/`into` are serde de/serialization conversion attributes that have no TypeScript analogue, so the warning is noise.

### Rustc-level suppression (not applicable here)

The proc-macro diagnostic API (`feature(proc_macro_diagnostic)`, tracking issue rust-lang/rust#54140) is still unstable. It would allow warnings with lint IDs that could be `#[allow()]`'d, but ts-rs does not use it. There is no stable rustc mechanism to suppress warnings emitted by a specific proc macro crate.

## Sources

- ts-rs `Cargo.toml` at v12.0.1: `no-serde-warnings = ["ts-rs-macros/no-serde-warnings"]` confirmed present
- ts-rs `macros/src/utils.rs`: `cfg!(not(feature = "no-serde-warnings"))` gate
- GitHub issue Aleph-Alpha/ts-rs#436: "Feature request: Omit warnings for serde attributes that can safely be ignored" (closed, resolved by `no-serde-warnings`)
- GitHub issue Aleph-Alpha/ts-rs#108: "Add option to disable warnings printed from macro during build" (closed, implemented via `no-serde-warnings`)
- GitHub issue Aleph-Alpha/ts-rs#387: `skip_serializing_if` warning (bug, resolved in a later version)
- rust-lang/rust#54140: proc-macro diagnostics tracking issue (still open/unstable)

## Open Questions

- Whether ts-rs will eventually parse and silently discard known-safe attributes (`borrow`, `try_from`, `into`, etc.) rather than requiring a blanket feature flag. The maintainer noted intent to do so in issue #436 but it has not shipped as of v12.0.1.

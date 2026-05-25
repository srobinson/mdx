# Codex Adversarial Review: electron-vs-tauri-2026.md

Independent adversarial pass (Codex / GPT-5.x) on the shell-decision recommendation in
`electron-vs-tauri-2026.md`. Mixture-of-experts second engine. Produced 2026-05-30.

## Verdict: REVISE

The recommendation partially holds and partially flips. It is correct for the existing app
and wrong, by the source doc's own math, for the new shell.

## Single strongest counterargument: greenfield conflation

The recommendation says "keep Electron now" while simultaneously acknowledging that the
littleorgans `apps/` shell does not exist. The phrase is ambiguous between two readings:

- **Safe reading (correct):** do not migrate `transport-matters/desktop`, the existing,
  working Electron app.
- **Dangerous reading:** default the unbuilt littleorgans `apps/` shell to Electron.

The locked baseline's "one Electron shell, three packaged identities" language makes the
dangerous reading easy to inherit by default.

The source doc's own greenfield sensitivity branch (C2 migration-cost → parity) already
scores a Tauri win. Because littleorgans `apps/` *is* greenfield, that branch is the one
that applies. The recommendation did not apply the doc's own greenfield result to the
greenfield case.

## Arithmetic correction

Codex re-derived the weighted scoring and found drift:

- Corrected present-state score: **Electron 72.2 vs Tauri 70.2** (a ~2.0 gap), not the
  70.8 vs 70.6 "near tie" the doc reports.
- Greenfield branch: a **strong Tauri win** (~73.4 vs ~65.8), not the mild ~67 vs ~64 nudge cited.

A "near tie / medium confidence" framing is not accurate once the arithmetic is corrected.
The existing-app case favors Electron more clearly than stated; the greenfield case favors
Tauri more clearly than stated.

## Does the core hold or flip?

- **Holds** for `transport-matters/desktop`: do not migrate a working app. Correct.
- **Flips** for littleorgans `apps/`: greenfield + Rust chassis + Moon + cargo-dist make
  Tauri the default, not the contingency.

## Recommended framing for the downstream desktop gap audit

**Build Tauri greenfield.** The `desktop/` migration audit should assume the
`littleorgans/apps/` shell will be Tauri, and treat `transport-matters/desktop` as a legacy
reference implementation to be replaced, not the permanent shell. Use it as a risk and
pattern source. The validation gates (render parity, migration-cost parity) decide whether
Electron survives as a fallback, but the null hypothesis for the audit is Tauri.

## Reconciliation note

This review does not discard `electron-vs-tauri-2026.md`. The factual research, the criteria,
and the gates stand. What changes is the recommendation's altitude: separate the existing app
(keep Electron) from the new shell (default Tauri), and stop reporting a tie that the corrected
arithmetic does not support. The final shell decision reopens a locked baseline and is the
operator's to make; this review sharpens the inputs.

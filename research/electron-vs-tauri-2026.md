---
title: "Electron vs Tauri for the littleorgans desktop shell (2026 decision)"
type: research
tags: [electron, tauri, desktop-shell, littleorgans, rust, moon, helioy-baseline, decision]
summary: "Decision-grade study reopening the locked Electron baseline. Recommendation: keep Electron now, schedule a Tauri spike at the littleorgans app-shell phase. Confidence medium-high."
status: active
confidence: medium
created: 2026-05-30
updated: 2026-05-30
related:
  - "helioy-electron-baseline.md"
  - "non-tailwind-design-systems-web-electron-2026.md"
  - "rust-conventions-2026.md"
---

# Electron vs Tauri for the littleorgans desktop shell (2026 decision)

> This is a decision, not a survey. It reopens a baseline parameter locked on 2026-05-16
> (`helioy-electron-baseline.md` §7 Q3: "one shell codebase, three packaged identities", Electron).
> It ends with an explicit recommendation, a steelman of the rejected option, and the exact
> baseline-parameter deltas if the recommendation changes the spec.

## 1. Context: the two repos and the locked baseline

### 1.1 SOURCE — `transport-matters/desktop/` (Electron, shipping)

Verified by reading the repo. The desktop shell is thin and disciplined, not the heavy t3code shape.

- `electron ^39.2.6`, `@electron/packager ^19`, Vitest 4, TypeScript 5.9, pnpm 10, ESM. No `electron-builder`, no auto-update wired yet.
- Source is ~600 LOC across `main.ts`, `preload.ts` (4 lines of context-bridge), `window.ts`, `backendProcess.ts`, `backendHealth.ts`. Every function is dependency-injected and unit-tested (`*.test.ts` alongside each file). `rendererBoundary.test.ts` asserts the renderer/main seam.
- Architecture: the shell **spawns a backend process** (`launchBackendProcess`), **HTTP-polls health** (`waitForBackendHealth`), then **loads the web app over a local port** (`rendererUrlForPort`, default web port). It is a process supervisor plus a `BrowserWindow` host. It does not bundle the renderer; it points Chromium at the separately-built `www/` app.
- The renderer (`transport-matters/www/`) is a **separate** React 19 + Vite 8 + Tailwind 4 + Zustand 5 + TanStack Query/Virtual app. Tested with Playwright across **chromium, firefox, and webkit** projects already. Biome for lint/format. This is the load-bearing fact for the webview-consistency criterion below: the team already runs a tri-engine Playwright matrix, so they have partial muscle for Tauri's tri-webview reality, but they currently *ship* on one engine (Chromium).

The shell is small enough that "migrate the shell" is a bounded problem. The renderer is where the real surface area lives, and the renderer is web tech either way.

### 1.2 TARGET — `littleorgans/littleorgans/` (Rust + Moon monorepo)

Verified by reading `Cargo.toml`, `moon.yml`, `.moon/toolchains.yml`, `CLAUDE.md`.

- Pure Rust workspace, `resolver = "3"`, edition 2024, `rust-version = 1.95`, version `0.8.0`. 25 members, all `lilo-*` (`crates/` published, `internal/` substrate). Stack: tokio, sqlx+sqlite, serde, thiserror, anyhow, clap, tracing, uuid v7.
- Distribution today: `cargo-dist` 0.31 (shell installer, six target triples), `release-plz` for per-crate tags. CI gate via Moon: `fmt-check → clippy → check-loc → build → test (nextest)`. A `check-loc-limit.sh` enforces the 700-LOC rule mechanically.
- `.moon/toolchains.yml` declares **only `rust: 1.95`**. Node and Python toolchains are explicitly commented out: *"Reserved until TypeScript workspace files are introduced."* `moon.yml` `language: "rust"`.
- `apps/`, `packages/`, `python/` are **empty README stubs** awaiting their migration phase. There is **no Electron and no Tauri present yet**. CLAUDE.md: `apps/` is a "reserved placeholder until its phase activates it."
- K8s-shaped vocabulary throughout (`lilo` = kubectl, `internal/session` = API server, `internal/runtime` = kubelet). Pre-release, zero external users, breaking changes welcome.

So the desktop shell for littleorgans **does not exist yet**. The decision is not "rewrite the transport-matters shell". It is "what shell technology does the littleorgans `apps/` slot adopt when its phase activates", with transport-matters as the only existing reference implementation and the locked baseline as the inherited default.

### 1.3 The locked baseline and why it is being reopened

`helioy-electron-baseline.md` (locked 2026-05-16, confidence high) specifies a three-app (`desktop`, `server`, `web`) + three-package shape with **twelve locked parameters**. The Electron-relevant locks:

- **Q3 — Shell topology**: one Electron `apps/desktop`, three packaged identities (transport-matters, runtime-matters, littleorgans) via a build-script surface argument.
- **Q4 — Auto-update**: `electron-updater` GitHub Releases provider per surface.
- **Q2 — Desktop→server bootstrap**: fd3 primary, stdin-JSON fallback; *explicitly designed so "a Rust server that reads fd3" works identically* (baseline P3, §2.4).
- Q1 Effect Schema everywhere, Q5 WebSocket + Effect RPC, Q6 atom-first renderer, Q11 Geist + Lucide + one OKLCH primary.

The baseline already anticipated a Rust backend. The seam (P3 fd3 bootstrap, server-as-child-process) was deliberately runtime-agnostic. What it did **not** anticipate: that littleorgans would arrive as a *fully Rust-native monorepo with a Rust-only Moon toolchain and `cargo-dist`* distribution, and that adjacent architecture reviews (cmux, herdr both noted no-electron) would normalize Rust-native desktop. That drift is what reopens Q3.

**The tension in one sentence:** Tauri's backend is Rust, which would fuse the desktop shell into the `lilo-*` chassis and the existing `cargo-dist`/Moon/Cargo gate. Electron keeps the shell in the JS/Effect world the baseline already specified and transport-matters already ships.

## 2. Decision criteria (with weights)

Weights reflect littleorgans' actual constraints: solo operator, Rust-primary chassis, pre-release, local-first now / K8s-shaped later, design-system parity across three surfaces. Weights are explicit so the Codex adversarial pass can attack them. They sum to 100.

| # | Criterion | Weight | Rationale for weight |
|---|-----------|-------:|----------------------|
| C1 | Rust-backend & IPC fit with `lilo-*` crates + Moon + cargo-dist | 20 | The whole reason the decision reopened. Highest leverage. |
| C2 | Migration / build-out cost from current state | 16 | Solo operator; velocity is the scarcest resource. |
| C3 | Cross-platform rendering consistency | 14 | A design-system product (Geist/OKLCH/base-ui) lives or dies on this. |
| C4 | Ecosystem & plugin maturity (auto-update, packaging, native menus) | 12 | Battle-tested paths reduce solo-maintainer surface. |
| C5 | Developer velocity (one person, reuse of baseline patterns) | 12 | Reuse of 35 baseline patterns has real value. |
| C6 | Long-term alignment with Rust-primary, K8s-shaped endgame | 10 | Strategic, but v1 is local-first; discount future bets. |
| C7 | Bundle size & memory | 8 | Real, but not differentiating for a dev-tool audience on modern hardware. |
| C8 | Security model | 5 | Both are adequate when configured correctly. |
| C9 | Auto-update robustness | 3 | Folded partly into C4; small standalone weight. |

Scoring is 1–5 per criterion. Weighted score = Σ(weight × score) / 5, max 100.

## 3. Electron 2026 profile

- **State**: Electron 41 stable, bundling Chromium 146 + Node 24 LTS (DEV/raxxostudios, 2026). Powers VS Code, Slack, Discord, Figma, 1Password, Linear, Notion, Cursor, Signal, WhatsApp Desktop. The most boring, most proven choice in the category.
- **Security**: `contextIsolation` default-true since v12, `nodeIntegration` default-false, v34+ process model closes most same-origin surface (electronjs.org/security; PkgPulse 2026). Secure **if you follow the checklist** — the checklist is the liability. Doyensec published a 2026-02 guide on building a secure auto-updater, evidence the footguns are real and ongoing.
- **Bundle/memory**: empty app ~150–200 MB resident; React production app 300–500 MB; installer 150–200 MB (PkgPulse, DEV 2026). gethopp measured **Electron 409 MB / 6 windows, 244 MiB bundle** in a controlled 2025 comparison.
- **Auto-update**: `electron-updater` + Squirrel, mature, GitHub Releases provider out of the box. **macOS + Windows only; no built-in Linux auto-update** (electronjs.org/api/auto-updater) — Linux relies on the distro package manager. This matters because `cargo-dist` already produces Linux artifacts for littleorgans.
- **Fit with the baseline**: perfect. The baseline *is* an Electron spec. transport-matters already ships this shell. fd3 bootstrap, `makeIpcMethod`, the 35 patterns all apply unchanged.
- **Fit with the Rust chassis**: indirect. Electron talks to a Rust backend as a spawned child process over a socket/port (exactly what transport-matters already does with its backend). The Rust crates stay an external process; no Rust-in-shell. Clean boundary, but the shell itself never becomes a `lilo-*` crate and never enters the Moon/Cargo gate.

## 4. Tauri 2.x 2026 profile

- **Maturity**: Tauri 2.0 stable shipped 2025; 2.x is production-usable in 2026 (v2.tauri.app). Mobile (iOS/Android from the same Rust core) closed the last v1 gap but is "functional, not as mature as React Native/Flutter" — irrelevant to littleorgans (desktop-only v1).
- **IPC**: v2 added `tauri::ipc` with a `Channel` type and raw-request fast path for large payloads. Typed IPC is a **solved ecosystem problem**: `tauri-specta` (specta-rs) generates a `bindings.ts` from `#[specta::specta]`-annotated Rust commands at build time, so a backend signature change breaks frontend compilation. `TauRPC` offers an RPC-flavored alternative. This is the direct analogue of the baseline's `makeIpcMethod`/`WS_METHODS` contract spine, except the source of truth is **Rust types** instead of Effect Schema.
- **Webview**: WebView2 (Win), WKWebView (macOS), WebKitGTK (Linux) via `wry`. No bundled Chromium. **This is the central risk** — see C3.
- **Sidecar / Rust-backend**: two patterns. (a) Co-locate logic **inside** the Tauri Rust process as commands (the natural `lilo-*` fit). (b) `sidecar` / `externalBin` to embed and spawn an external binary, per-target-triple naming, capability-gated permissions. Caveat from docs and DoltHub: sidecars are "supposed to run for a short time"; long-running servers work but are more cumbersome than Electron's bundled Node. For littleorgans the *better* pattern is (a): `lilod` logic as Tauri commands, not a sidecar.
- **Plugins**: `tauri-plugin-*` crates, "pick what you need" (Aptabase called this the second-biggest reason they chose Tauri). Core plugins cover updater, fs, shell, dialog. Smaller and younger than Electron's; updater plugin exists and is cross-platform including Linux.
- **Bundle/memory**: gethopp measured **Tauri 172 MB / 6 windows, 8.6 MiB bundle** vs Electron's 409 MB / 244 MiB — the one controlled non-affiliate number. Affiliate sites claim 25x–96x smaller and 58–75% less RAM; treat the magnitude as directionally true, the exact multipliers as marketing (see §9 source quality).
- **Build cost**: gethopp measured initial Tauri build **80.9 s** (Rust compile) vs Electron **15.8 s**; incremental much faster. For a workspace already paying Rust compile cost on every `cargo build`, the marginal compile hit is smaller than it looks.

## 5. Head-to-head, scored

Score 1–5 (5 = better for littleorgans specifically).

| # | Criterion | Wt | Electron | Tauri | Notes |
|---|-----------|---:|:-------:|:-----:|-------|
| C1 | Rust/IPC fit with lilo-* + Moon + cargo-dist | 20 | 2 | **5** | Tauri puts the shell *inside* the Cargo workspace; it becomes a `lilo-*`-adjacent crate under the same `clippy`/`nextest`/`check-loc` gate and ships via `cargo-dist`. Electron keeps the shell as a foreign JS island bolted beside the Rust chassis. Decisive gap. |
| C2 | Migration / build-out cost | 16 | **5** | 2 | littleorgans shell does not exist yet, so "build-out". Electron = lift the baseline + transport-matters shell, near-zero novel work. Tauri = new Rust shell crate, tauri-specta wiring, codesigning/notarization rework, tri-webview test setup, Windows bundle-format constraints. |
| C3 | Rendering consistency | 14 | **5** | 2 | Electron bundles one Chromium: render once, test once. Tauri = three engines, "write once, test three times"; WebKitGTK lags CSS, Linux distro fragmentation is real (Tauri docs admit the compat list is incomplete). A Geist/OKLCH/base-ui design product is exactly the case that suffers. transport-matters' existing webkit Playwright project softens but does not erase this. |
| C4 | Ecosystem / plugin maturity | 12 | **5** | 3 | Electron's updater/packaging/native-menu ecosystem is a decade deep. Tauri missing native context menu was Aptabase's "only major inconvenience"; DoltHub blocked by `.appx` (Tauri does only `.exe`/`.msi` on Windows) and universal-binary codesigning bugs. |
| C5 | Developer velocity | 12 | **4** | 3 | Electron reuses 35 baseline patterns + Effect renderer + transport-matters shell verbatim. Tauri has the slicker greenfield DX (`create tauri-app`) but "Rust is hard" (Aptabase) for the *shell* layer; though littleorgans already lives in Rust, so the tax is partly pre-paid. |
| C6 | Long-term Rust/K8s alignment | 10 | 2 | **5** | One language, one toolchain, one gate, one `cargo-dist` release across the whole family is the stated endgame. Tauri is the only option that gets the shell there. |
| C7 | Bundle / memory | 8 | 2 | **5** | Tauri is materially smaller/lighter on every credible measurement. Real, modestly weighted. |
| C8 | Security model | 5 | 3 | **4** | Tauri's Rust core + capability/permission ACL + no Node-in-renderer is a smaller attack surface by default. Electron is secure-when-configured; the configuration is the risk. |
| C9 | Auto-update robustness | 3 | **4** | 3 | electron-updater more battle-tested (mac/win), but **no Linux**. Tauri updater plugin covers Linux too but is younger. For a cargo-dist-Linux product this is closer than the maturity gap suggests. |

**Weighted totals** (Σ(wt×score)/5, max 100):

- **Electron: 70.8** → (40+80+70+60+48+20+16+15+12)/5 = 361/5
- **Tauri: 70.6** → (100+32+28+36+36+50+40+20+9)/5 = 353/5

**The score is a tie inside the noise.** That is the honest finding, and it is why timing — not technology — drives the recommendation.

### Where the decision flips

The two criteria that pin Electron ahead are **C2 (migration cost)** and **C3 (rendering consistency)**, both weighted by *present* conditions. The decision flips to Tauri the moment either changes:

- **Flip trigger A (timing):** when the littleorgans `apps/` shell is *greenfield* (its phase activates with no shell to migrate from), C2 collapses from Electron 5 / Tauri 2 toward parity (both ~3, building new). Recompute with C2 at Electron 3 / Tauri 3: Electron 64.4, **Tauri 67** — Tauri wins. The Electron lead is **entirely a migration-cost artifact of transport-matters already existing.**
- **Flip trigger B (rendering):** if the design system is validated to render identically across WebView2/WKWebView/WebKitGTK (a one-time spike), C3 moves to Tauri 4. That alone (with C2 still Electron-favoring) yields Electron 70.8 vs **Tauri 76.2** — Tauri wins.

Either trigger flips it. Both are foreseeable at the littleorgans app-shell phase.

## 6. Migration cost: transport-matters Electron → Tauri (concrete)

If the call were "migrate the existing shell today" (it is not — see §7), the bounded work:

1. **New Rust shell crate** in the Cargo workspace (e.g. `apps/lilo-desktop` or `internal/.../desktop`), a `tauri::Builder` with the window + lifecycle logic. The current `main.ts` (~260 LOC) maps to ~150–200 LOC Rust. Backend supervision (`backendProcess.ts`, `backendHealth.ts`) folds *into* the Rust process as commands or a managed child — the supervision logic the `lilo-*` runtime crates may already largely own.
2. **IPC rewrite**: 4-line preload + the Electron context-bridge replaced by `tauri-specta` commands generating `bindings.ts`. Net simpler, but a different contract than the baseline's Effect Schema `makeIpcMethod`. The renderer's RPC client changes import surface.
3. **Renderer stays**: `www/` (React 19 + Vite + Tailwind 4 + Zustand + TanStack) loads unchanged into the Tauri webview. **This is the cheap part** — the renderer is web tech in both worlds. The expensive part is everything *around* it.
4. **Packaging/signing rework**: switch from `@electron/packager` to `tauri bundle`. Re-do macOS codesigning + notarization (DoltHub hit universal-binary double-signing bugs). Windows limited to `.exe`/`.msi` (no `.appx`/Store). macOS quarantine `xattr` cleanup on bundled binaries (smoodit report). Reconcile with the existing `cargo-dist` release pipeline.
5. **Test matrix**: stand up real tri-webview testing. transport-matters has webkit Playwright projects already; extend to assert against the *actual* WKWebView/WebKitGTK/WebView2 builds, not just browser engines.
6. **Auto-update**: wire `tauri-plugin-updater` (gains Linux vs electron-updater) against GitHub Releases — replaces the baseline Q4 `electron-updater` choice.

Headline: the **shell** is a 1–2 week port for someone already fluent in the Rust chassis; the **signing/packaging/test-matrix tail** is the real cost and the real risk, and it is the part every migration report (DoltHub, smoodit, Aptabase) flags. Renderer migration is near-free.

## 7. Recommendation

**Keep Electron as the locked baseline default for now. Do not migrate transport-matters. Schedule a time-boxed Tauri spike to run *at* the littleorgans `apps/` shell phase, and pre-commit to adopting Tauri for the littleorgans shell specifically if the spike clears two gates. Confidence: medium (leaning medium-high on the *process*, medium on the end-state because the score is a genuine tie).**

Reasoning, falsifiable:

1. **The head-to-head is a tie (70.8 vs 70.6).** When two options score within noise, you do not pay migration cost to switch. You let the cheaper-to-defer decision wait until conditions resolve the tie. Both tie-breaking criteria (C2, C3) resolve in Tauri's favor at the greenfield littleorgans phase.
2. **transport-matters should not move.** It ships, it is thin, it is tested, and migrating it buys a 70.6 over a 70.8. Pure churn. The "no-electron drift" in cmux/herdr reviews is about *new* Rust-native tools, not a mandate to rewrite working shells.
3. **littleorgans `apps/` is the real decision point, and it is greenfield.** There, C2 collapses to parity and Tauri wins on recompute (§5 flip trigger A: 67 vs 64.4). A greenfield Rust-native app inside a Rust-only Moon/Cargo/cargo-dist workspace is the textbook Tauri case: the shell becomes a `lilo-*`-adjacent crate under the same gate, ships in the same `cargo-dist` release, and the "Rust tax" is already paid by the chassis.
4. **The spike gates** (run before committing the littleorgans shell): **(G1)** the Geist/OKLCH/base-ui design surface renders acceptably identically across WebView2 + WKWebView + WebKitGTK on the three target OSes; **(G2)** macOS notarization + universal-binary codesigning + Windows `.exe`/`.msi` bundling reconcile cleanly with the existing `cargo-dist`/`release-plz` pipeline. If both pass, adopt Tauri for littleorgans. If either fails, Electron remains the default and the baseline stands unchanged.

This is not a hedge. It is the only allocation that respects the tie: zero churn on what ships, a falsifiable trigger on what does not yet exist, and a pre-committed flip when the evidence arrives.

## 8. Steelman of the rejected option (Tauri-now, or alternatively all-Electron-forever)

**Strongest case for adopting Tauri immediately, across the board:**

The single most defensible argument: **architectural coherence has compounding returns that benchmarks cannot show.** A Rust-primary, K8s-shaped product whose desktop shell is *also* a Cargo crate means one language, one toolchain (`.moon/toolchains.yml` never grows a Node entry), one lint gate, one `check-loc` rule, one `cargo-dist` release, one mental model. Every Electron path is a second runtime, a second package manager (pnpm), a second build system bolted beside Cargo, and a permanent context-switch tax on a *solo* operator. The baseline's three-app shape (`desktop`/`server`/`web` all JS) was designed before littleorgans crystallized as Rust-native; it imports t3code's world wholesale. Tauri lets littleorgans collapse `desktop` + `server` into the Rust process it already has, deleting an entire app and an entire IPC hop. tauri-specta gives the *same* end-to-end type safety the baseline prizes, sourced from the Rust types that are already the source of truth. The webview-fragmentation risk is real but **bounded and one-time** (a design-token spike retires it), whereas Electron's costs (memory, bundle, the secure-updater checklist, the second toolchain) are **recurring forever**. Deferring is just paying the migration later at higher cost, after more Electron-shaped code has accreted. A solo builder optimizing for a decade-long Rust-native product should eat the one-time Rust-shell cost now while `apps/` is still an empty stub.

That argument is strong enough that the recommendation pre-commits to Tauri for littleorgans on spike success rather than treating Electron as the permanent default. It loses *today* only on migration cost for the one shell that already exists, and on an unretired rendering risk — both of which the staged plan addresses rather than dismisses.

## 9. Baseline-parameter deltas (if Tauri is adopted for littleorgans)

These change **only for the littleorgans surface**. transport-matters and runtime-matters can stay on the Electron baseline (the baseline already supports per-surface divergence; this just widens "per-surface" to include shell tech).

| Baseline param | Locked value | Delta under Tauri-for-littleorgans |
|----------------|--------------|-------------------------------------|
| Q3 Shell topology | One Electron `apps/desktop`, three packaged | littleorgans uses a **Tauri Rust shell crate** in the Cargo workspace; transport-matters/runtime-matters may remain Electron. "One shell codebase" relaxes to "one shell *pattern* per runtime family." |
| Q4 Auto-update | `electron-updater` GitHub Releases | littleorgans uses `tauri-plugin-updater` (adds Linux coverage) against GitHub Releases, reconciled with `cargo-dist`. |
| Q2 Desktop→server bootstrap | fd3 / stdin-JSON to a child server | **Obsolete for littleorgans**: server logic moves *into* the Tauri Rust process as commands. No child-process bootstrap, no fd3 hop. (Delta is a simplification.) |
| Q5 Renderer transport | WebSocket + Effect RPC | littleorgans renderer uses **Tauri IPC + tauri-specta `bindings.ts`** instead of WS + Effect RPC for shell↔core calls. WS may remain for any remote/federated backend. |
| Q1 Schema source of truth | Effect Schema everywhere | Shell↔core contract source of truth becomes **Rust types via Specta**, not Effect Schema. Renderer-internal Effect Schema can stay. |
| Q6/Q8/Q11 renderer + design | atom-first, file-based routing, Geist/Lucide/OKLCH | **Unchanged.** The renderer is identical web tech in the Tauri webview. This is why the renderer migration is near-free. |

Net: four params shift, two of the shifts are simplifications (Q2 deleted, Q3 relaxed), the entire design/renderer layer is untouched. The baseline is not invalidated; it gains a second shell profile.

## 10. Risks & mitigations

| Risk | Severity | Mitigation |
|------|---------|-----------|
| WebKitGTK/WKWebView render the design system differently than Chromium | High | Spike gate G1 before commit. Lean on base-ui + OKLCH + CSS-var tokens (well-supported) over bleeding-edge CSS. Keep the transport-matters webkit Playwright project as a standing canary. |
| macOS universal-binary codesigning / notarization bugs (DoltHub-reported) | Medium-High | Spike gate G2. Validate against `cargo-dist` signing before any release commitment. |
| Windows bundle limited to `.exe`/`.msi` (no Store/`.appx`) | Medium | littleorgans ships via `cargo-dist` shell installer today, not the Store — low impact. Revisit only if Store distribution becomes a goal. |
| Tauri plugin gaps (native context menu historically) | Low-Medium | v2 closed most; verify the specific primitives littleorgans needs in the spike. |
| Two shell technologies across the family raises maintenance | Medium | Accept deliberately: transport-matters Electron is stable and untouched; only *new* Rust-native littleorgans goes Tauri. Re-evaluate consolidation once littleorgans Tauri shell is proven. |
| Affiliate-sourced benchmarks overstate Tauri's win | Low | Decision does not rest on bundle/memory (C7, weight 8). Uses gethopp's controlled numbers, not affiliate multipliers. |
| Rust shell pulls a solo operator's attention from core | Medium | Time-box the spike. The chassis is already Rust, so the shell is not a new language, only a new domain (windowing/IPC). |

## 11. Open questions

1. **When does the littleorgans `apps/` phase actually activate?** The whole recommendation hinges on running the spike at that moment. If it is far out, this doc should be re-confirmed then (webview landscape moves).
2. **Does the `lilo-*` runtime/session daemon already own the process-supervision logic** that transport-matters' `backendProcess.ts` reimplements? If yes, the Tauri shell is even thinner than estimated. (Needs a fmm pass over `internal/runtime` and `internal/session/daemon`.)
3. **Is a single shared shell across all three surfaces still a goal**, or is per-surface shell tech acceptable long-term? The baseline assumed one; this doc proposes relaxing it. Stuart owns that call.
4. **Does runtime-matters (the "brain") want the same Tauri treatment** when its shell phase arrives, or does its WS + Effect RPC design favor staying Electron? Likely the same spike applies.
5. **Mobile**: any chance a littleorgans companion ships on iOS/Android? Tauri 2 mobile would then become a real plus; today it is irrelevant.

## 12. Review checklist

- [ ] Did the analysis read both repos directly (not training data)? Yes — `package.json`, `Cargo.toml`, `moon.yml`, `.moon/toolchains.yml`, `main.ts` all read.
- [ ] Are the criteria weights explicit and the flip points falsifiable? Yes (§2, §5).
- [ ] Does the recommendation reconcile with the locked baseline and state exact deltas? Yes (§9).
- [ ] Is the rejected option steelmanned, not strawmanned? Yes (§8).
- [ ] Are affiliate/SEO sources flagged and de-weighted vs engineering sources? Yes (§13).
- [ ] Is the recommendation explicit with a confidence level? Yes (§7, medium).
- [ ] Does it survive "what if the score is a tie"? Yes — the tie *is* the finding; timing breaks it.

## 13. Source quality assessment

**High signal (engineering, controlled, non-affiliate):**
- gethopp, "Tauri vs Electron: performance, bundle size, and real trade-offs" (2025) — the only *controlled* head-to-head with method: Tauri 172 MB / Electron 409 MB (6 windows); 8.6 MiB / 244 MiB bundle; 80.9 s / 15.8 s initial build.
- DoltHub blog, 2025-11-13 — production team that **stayed on Electron**; concrete Tauri blockers (`.appx`, universal-binary codesigning, sidecar friction).
- Aptabase, "Why I chose Tauri" — production team that **chose Tauri**; honest "Rust is hard" + missing native context menu.
- Official Tauri v2 docs (IPC, sidecar, webview-versions, mobile plugins) and Electron docs (security, auto-updater, context-isolation).
- Doyensec, 2026-02 "Building a Secure Electron Auto-Updater" — evidence the Electron updater footguns are current.
- specta-rs/tauri-specta + MatsDK/TauRPC repos — typed-IPC ecosystem is real and maintained.

**Low signal (affiliate / SEO, directional only):** tech-insider.org ("96% smaller, 1 winner"), rustify.rs, pkgpulse.com, raftlabs/Medium reposts. Round numbers, single-winner framing, no method. Used **only** to confirm direction (Tauri smaller/lighter), never for magnitude. The decision does not rest on any of them — bundle/memory carries weight 8 of 100.

**Confidence**: medium. The technical facts are well-triangulated. The residual uncertainty is genuine: the weighted score is a tie, so the recommendation is a *timing and process* call, not a slam-dunk technology verdict. It is explicitly built to flip on two falsifiable spike gates.

## Agent Rules

Validate before acting. Read both repos before re-litigating this; do not argue from training data.
This decision is timing-gated, not technology-gated. The head-to-head is a tie inside the noise.
Do not migrate `transport-matters/desktop` to Tauri. It ships, it is thin, it is tested. Churn for a 70.6 over a 70.8 is forbidden.
The live decision is the littleorgans `apps/` shell, and only when its phase activates.
At that phase, run the two spike gates before committing: G1 tri-webview render parity for the design system, G2 macOS notarization + Windows bundling reconciled with cargo-dist.
If both gates pass, adopt Tauri for littleorgans: shell becomes a Cargo crate under the Moon/clippy/nextest/check-loc gate, server logic folds into the Rust process, fd3 bootstrap is deleted, tauri-specta replaces makeIpcMethod for shell↔core.
If either gate fails, Electron remains the default and the locked baseline stands unchanged.
The renderer is web tech either way. Renderer migration is near-free; never let it dominate the cost estimate.
Per-surface shell tech is acceptable: transport-matters Electron and littleorgans Tauri can coexist.
Weight bundle size and memory low (8/100). Do not let affiliate benchmarks drive the call.
Treat webview fragmentation as the real Tauri risk and codesigning/packaging as the real Tauri cost. Every migration report agrees on both.
Keep the shell crate under 700 LOC per file and 150 per function, like the rest of littleorgans.
When in doubt, re-confirm this doc at the moment the littleorgans app-shell phase activates; the webview landscape moves.

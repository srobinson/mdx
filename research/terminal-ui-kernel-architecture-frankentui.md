---
title: "FrankenTUI: High-Performance Terminal UI Kernel with Bayesian Intelligence Layer"
type: research
tags: [tui, rust, rendering, bayesian, terminal, dicklesworthstone, ui-kernel]
summary: "880K-line Rust workspace (20 crates) implementing a deterministic TUI kernel with diff-based rendering, inline mode, Bayesian adaptive strategies, and 80+ widgets."
status: active
source: github-researcher
confidence: high
created: 2026-04-24
updated: 2026-04-24
---

## Executive Summary

FrankenTUI is a terminal UI kernel written in Rust (880K lines across 20 crates, 816 source files) by Jeffrey Emanuel (Dicklesworthstone). It positions itself below application frameworks like Ratatui, providing a strict rendering pipeline (Buffer > Diff > Presenter > ANSI) with a one-writer rule, RAII terminal cleanup, inline-mode scrollback preservation, and an adaptive Bayesian intelligence layer that selects diff strategies, coalesces resize events, and gates frame budgets using statistical methods. The project is WIP (v0.3.1), requires Rust nightly (edition 2024), and carries an MIT license with an OpenAI/Anthropic restriction rider.

This is the fourth Dicklesworthstone project reviewed. The same patterns recur: aggressive statistical modeling, exhaustive documentation in module-level doc comments, and a maximalist feature surface. Where CASS and frankensearch applied Bayesian methods to search, FrankenTUI applies them to rendering decisions.

## Architecture

### Crate Dependency Graph

```
ftui (facade/prelude)
  ├── ftui-runtime (Elm/Bubbletea event loop, 97K lines)
  │     ├── ftui-render (buffer, diff, presenter, 43K lines)
  │     │     └── ftui-core (events, capabilities, geometry, 35K lines)
  │     ├── ftui-layout (flex, grid, pane tree, e-graph optimizer, 23K lines)
  │     │     └── ftui-core
  │     └── ftui-backend (trait abstraction)
  ├── ftui-widgets (80+ widgets, 94K lines)
  ├── ftui-extras (mermaid, markdown, VFX, themes, 140K lines)
  ├── ftui-style (CSS-like cascading themes)
  ├── ftui-text (rope editor, BiDi, shaping)
  ├── ftui-tty (native Unix terminal backend)
  ├── ftui-web (WASM backend, host-driven I/O)
  ├── ftui-a11y (accessibility tree)
  ├── ftui-i18n (localization)
  └── ftui-simd (reserved, empty)

Testing:
  ftui-harness (snapshots, shadow-run, benchmarks)
  ftui-pty (PTY-based test utilities)
  ftui-demo-showcase (46 interactive demo screens)
  doctor_frankentui (CI verification suite)
```

### Render Pipeline

The core rendering pipeline is the project's primary contribution:

1. **Model.view()** writes widgets into a `Frame` (which wraps a `Buffer`)
2. **Buffer** is a row-major grid of 16-byte `Cell` structs (4 cells per cache line, by design assertion at compile time)
3. **BufferDiff::compute()** scans dirty rows in cache-friendly blocks (BLOCK_SIZE=4), produces `ChangeRun` sequences
4. **Presenter** converts runs to minimal ANSI using a DP cost model that compares sparse-run emission vs merged write-through per row
5. **TerminalWriter** serializes all output (one-writer rule), manages inline-mode cursor save/restore and scroll regions

Key invariant: `Cell` is exactly 16 bytes (`content: 4B, fg: 4B, bg: 4B, attrs: 4B`), enforced by a `const` assertion against cache line size. This allows the diff engine to compare cells as 128-bit values.

### Elm/Bubbletea Runtime

`ftui-runtime` implements the standard Elm architecture (`Model` trait with `update()` returning `Cmd<Msg>`, `view()` rendering to `Frame`). The `Program` struct (13K lines) is the main loop, integrating:

- Event polling from backends
- Resize coalescing (Bayesian regime detection via BOCPD)
- Frame budget enforcement (PID controller + e-process)
- Diff strategy selection (Bayesian cost model)
- Conformal frame-time prediction
- Effect system with Cx-aware cooperative cancellation
- Subscription management
- State persistence and undo
- Input macro recording/replay
- Pane workspace drag/resize state machine

### Inline Mode

The standout UX feature. `ScreenMode::Inline { ui_height: N }` renders N rows of UI chrome at the bottom while allowing logs to scroll normally above. The `TerminalWriter` manages this through cursor save/restore sequences and scroll region manipulation. This preserves terminal scrollback history, which alt-screen mode destroys.

## Key Patterns

### Bayesian Intelligence Layer

The most distinctive architectural choice. Multiple subsystems use Bayesian inference for runtime decisions:

**Diff Strategy Selection** (`ftui-render/src/diff_strategy.rs`): Maintains a Beta posterior over the change rate `p ~ Beta(alpha, beta)`, updated each frame with observed changed/unchanged cells. Selects between FullDiff, DirtyRowDiff, and FullRedraw using expected cost minimization. Includes conservative mode using the 95th percentile of the posterior for high-variance situations.

**Resize Coalescing** (`ftui-runtime/src/resize_coalescer.rs`, `bocpd.rs`): Uses Bayesian Online Change-Point Detection to distinguish between steady-state and burst resize regimes. Inter-arrival times are modeled as Exponential distributions with different rate parameters. Run-length posterior is truncated at K=100 for O(K) updates.

**Frame Budget** (`ftui-render/src/budget.rs`): PID controller for frame time regulation combined with an anytime-valid e-process for statistical guarantees. Graceful degradation levels: Full > SimpleBorders > NoStyling > Skeleton > TextOnly.

**VOI Sampling** (`ftui-runtime/src/voi_sampling.rs`): Value-of-Information policy for expensive measurements. Uses Beta posterior over violation probability to decide when sampling overhead is worth the information gain.

**Command Palette Scoring** (`ftui-widgets/src/command_palette/scorer.rs`): Bayesian match scoring using posterior odds ratios and evidence ledgers. Each scoring factor contributes a Bayes factor with explainable decomposition.

**Conformal Prediction** (`ftui-runtime/src/conformal_predictor.rs`): Distribution-free upper bounds on frame time using Mondrian (bucketed) conformal prediction.

**E-Process Throttle** (`ftui-runtime/src/eprocess_throttle.rs`): Anytime-valid recomputation throttle for streaming workloads using a wealth-based betting strategy (martingale control).

**Alpha-Investing** (`ftui-runtime/src/alpha_investing.rs`): Sequential FDR control when multiple alerts fire simultaneously. Treats significance level as a spendable resource.

### Data Structure Library

The codebase includes from-scratch implementations of several non-trivial data structures:

- **S3-FIFO cache** (`ftui-core/src/s3_fifo.rs`): Three-queue scan-resistant eviction policy
- **Roaring Bitmap** (`ftui-render/src/roaring_bitmap.rs`): Adaptive array/bitmap containers for cell-level dirty tracking
- **Quotient Filter** (`ftui-render/src/quotient_filter.rs`): Approximate membership for dirty row tracking in large virtualized lists (>1M rows)
- **Fenwick Tree** (`ftui-widgets/src/fenwick.rs`): O(log n) prefix sums for virtualized list height layout
- **E-graph** (`ftui-layout/src/egraph.rs`): Equality saturation for layout constraint optimization
- **Grapheme Pool** (`ftui-render/src/grapheme_pool.rs`): Interned grapheme cluster storage with generation-tagged IDs and reference counting
- **IVM DAG** (`ftui-runtime/src/ivm.rs`): Incremental View Maintenance with delta-propagation for derived render state

### Compile-Time Safety

Every crate enforces `#![forbid(unsafe_code)]` (21 crates total). The workspace uses `edition = "2024"` (Rust nightly). Release profile uses `opt-level = "z"` (size optimization) with LTO, single codegen unit, and `panic = "abort"` except `ftui-extras` which gets `opt-level = 3` for VFX rasterization performance.

### Platform Abstraction

Three backend implementations behind a common `Backend` trait:
- **ftui-tty**: Native Unix terminal using raw termios (replaces crossterm). Handles escape sequence hygiene for SGR mouse, Kitty keyboard protocol, DEC 2026 sync output.
- **ftui-web**: WASM backend with host-driven I/O and deterministic clock. No wasm-bindgen dependency; designed as building blocks for a JS wrapper.
- **Legacy crossterm**: Feature-gated compatibility path in ftui-core.

### Testing Infrastructure

- Snapshot/golden tests with `BLESS=1` update mode
- Shadow-run comparison for deterministic rendering validation
- PTY-based integration tests via `ftui-pty`
- 46 demo screens that double as snapshot test targets
- `doctor_frankentui`: CI verification suite with artifact manifests, coverage gating, and failure matrices
- Deterministic E2E with `E2E_DETERMINISTIC=1 E2E_SEED=N`

## Detailed Findings

### Code Volume Assessment

| Crate | Lines | Notes |
|-------|-------|-------|
| ftui-extras | 140K | Mermaid parser/renderer alone is 35K lines |
| ftui-runtime | 97K | program.rs is 13K, terminal_writer.rs is 6.5K |
| ftui-widgets | 94K | 80+ widget implementations |
| ftui-render | 43K | diff.rs 5K, presenter.rs 5K, buffer.rs 4K, budget.rs 4K |
| ftui-core | 35K | Event handling, capabilities, input parsing |
| ftui-layout | 23K | pane.rs 9K, egraph.rs |
| ftui-demo-showcase | ~40K | 46 demo screens |

The 880K total includes significant test code and demo implementations. The core kernel (core + render + runtime + layout) is roughly 200K lines.

### Relationship to Other Dicklesworthstone Projects

This is the most ambitious project in the series. The statistical/Bayesian approach seen in frankensearch (two-tier scoring, evidence-based ranking) and cass_memory_system (summarization with confidence) appears here as a full intelligence layer integrated into rendering decisions.

The project references `frankenterm-core` as an external dependency in `ftui-pty`, suggesting a companion terminal emulator project (FrankenTerm/frankenterm-web).

### Notable Design Decisions

1. **16-byte Cell invariant**: The decision to lock Cell at exactly 16 bytes with a compile-time assertion ties the entire rendering pipeline to cache-line-aware memory layout. This is a strong bet on performance that constrains future extensibility (no room for additional per-cell metadata without breaking the invariant).

2. **One-writer rule**: All stdout writes go through `TerminalWriter`. This eliminates an entire class of terminal corruption bugs but means every output path (logs, UI, debug) must route through the same serialization point.

3. **Bayesian everything**: The statistical layer adds significant complexity. The BOCPD for resize coalescing, the Beta posterior for diff strategy, the e-process for budget control. These are individually well-motivated but collectively create a dense mathematical substrate. Whether this actually outperforms simpler heuristics in real TUI workloads is an open question.

4. **Edition 2024 / nightly-only**: This limits adoption. Combined with the OpenAI/Anthropic restriction rider on the license, the practical audience is narrowed further.

5. **Massive scope**: Mermaid parsing, 3D data visualization, Quake demos, reaction-diffusion VFX. The extras crate alone is 140K lines. This suggests the project is partially a research vehicle and demo showcase rather than a focused library.

### License

MIT with an explicit rider prohibiting OpenAI, Anthropic, their affiliates, and anyone acting on their behalf from using the software. This is legally novel and its enforceability is untested.

## Dependencies

- `crossterm` (feature-gated, legacy compatibility)
- `signal-hook` (Unix signal handling in ftui-tty)
- `ahash` (fast hashing throughout)
- `smallvec` (inline vectors for layout/render)
- `serde`/`serde_json` (serialization)
- `rustc-hash` (layout crate)
- `arc-swap` (style system)
- `web-time` (platform-agnostic monotonic time, enables WASM)
- `portable-pty` (test harness)
- `frankenterm-core` (companion terminal emulator, used in PTY tests)
- `tracing` (optional structured logging)

## Relevance to Helioy

FrankenTUI's inline mode pattern is directly relevant if Helioy ever needs a terminal dashboard that preserves scrollback (e.g., for Nancy agent output monitoring). The one-writer rule and RAII cleanup patterns are solid engineering that any terminal-touching Rust code should adopt.

The Bayesian intelligence layer is interesting as a precedent for applying statistical methods to UI rendering decisions, but it adds substantial complexity that is hard to justify outside a research context.

The data structure implementations (S3-FIFO, Fenwick tree, Quotient filter, Roaring bitmap) are well-documented reference implementations worth studying individually if those data structures are ever needed.

The Elm/Bubbletea runtime model (`Model` + `update` + `view` + `Cmd`) is the standard functional UI architecture. Nothing novel here, but well-executed.

## Sources Consulted

- `README.md` (full, ~500 lines)
- `Cargo.toml` (workspace root + all 20 crate manifests)
- `PROPOSED_ARCHITECTURE.md` (doctor_frankentui design)
- `LICENSE`
- Core source files: `ftui-core/src/lib.rs`, `ftui-render/src/{diff,presenter,buffer,cell,grapheme_pool,diff_strategy,quotient_filter,roaring_bitmap}.rs`, `ftui-runtime/src/{program,terminal_writer,bocpd,conformal_predictor,eprocess_throttle,voi_sampling,alpha_investing,ivm,effect_system}.rs`, `ftui-layout/src/{pane,egraph}.rs`, `ftui-widgets/src/command_palette/scorer.rs`, `ftui-core/src/{gesture,s3_fifo}.rs`, `ftui-tty/src/lib.rs`, `ftui-web/src/lib.rs`, `ftui-harness/src/lib.rs`, `ftui-extras/src/mermaid.rs`, `ftui-widgets/src/fenwick.rs`
- Git log (50 recent commits, April 9-23 2026)
- GitHub API metadata

## Open Questions

1. **Real-world adoption**: No published crates beyond ftui-core, ftui-layout, ftui-i18n. Is anyone building on this outside the author?
2. **Performance validation**: The Bayesian diff strategy sounds good theoretically. Are there benchmarks showing it outperforms a simple dirty-row heuristic in practice?
3. **Relationship to FrankenTerm**: `frankenterm-core` appears as a dependency. Is there a companion terminal emulator project, and how do they compose?
4. **Stability trajectory**: 880K lines with active security hardening commits (path traversal, signal safety, deadlock prevention). How close is this to a stable API?
5. **Test coverage**: The doctor_frankentui crate has coverage gating. What is the actual coverage percentage across the workspace?

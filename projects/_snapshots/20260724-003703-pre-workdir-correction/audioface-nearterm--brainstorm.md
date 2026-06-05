# Audioface Near-Term Shippable Wins (4 weeks)

**Lens:** Fast, concrete. What ships NOW to make Audioface real and get first users.

**Current state:** Working token lab + composer (`npm start`), procedural Web Audio engine, 12 semantic tokens, 4 presets, 3 sequence flows, 75 tests passing. Package is `private: true` at `0.0.0`. API is split: `createAudioface` (theme resolver) and `createAudiofaceEngine` (playback) — README/AUDIO.md promise a unified `createAudioface().play()` that doesn't exist yet. We own `audioface.dev`, npm, PyPI, and crates names.

---

## Ranked by impact / effort

| # | Item | Effort | Impact | Notes |
|---|------|--------|--------|-------|
| 1 | **Publish `audioface@0.1.0` to npm** | S | ★★★★★ | Unblocks everything. Add `exports`, `files`, `types`, rename/split entry: `createAudioface` + engine wrapper with `.play()`. ~3-line quickstart becomes real. |
| 2 | **audioface.dev landing + live token playground** | M | ★★★★★ | Deploy existing lab (or slimmed playground) to owned domain. "Try it" = first user touchpoint. Static host (Vercel/Cloudflare). |
| 3 | **3-line quickstart in README + docs** | S | ★★★★☆ | `npm i audioface` → `createAudioface({ material: "ceramic" }).play("button.press")`. Copy-paste runnable on CodeSandbox/StackBlitz link. |
| 4 | **Unified public API (`createAudioface` + `.play()`)** | S | ★★★★☆ | Thin facade over themes + engine. `resume()`, `setVolume()`, `mute()`. Matches AUDIO.md contract exactly. Prerequisite for npm ship. |
| 5 | **`useAudioface` React hook** | S | ★★★★☆ | `const { play, resume } = useAudioface(theme)`. Handles gesture unlock + singleton context. Huge adoption lever for React apps. Separate `audioface/react` export. |
| 6 | **Shareable theme permalink (URL hash/query)** | S | ★★★☆☆ | Encode theme JSON in `?t=` or `#theme=`. Composer already exports JSON — wire read on load. Viral loop for designers. |
| 7 | **Sound diff A/B in playground** | M | ★★★★☆ | Lab already has A/B slots — expose as public "compare themes" mode with side-by-side play + waveform sketch. Differentiator vs generic UI kits. |
| 8 | **4 killer default themes (ship presets)** | S | ★★★☆☆ | Studio, Console, Soft Office, Instrument Panel exist — polish, document personality, add 1–2 more (e.g. `glass`, `paper` editorial). Theme gallery on landing. |
| 9 | **60s demo video (token lab walkthrough)** | S | ★★★☆☆ | Screen record: pick material → play sequence → export theme. Embed on landing + README. Low effort, high trust. |
| 10 | **PyPI / crates placeholder + README pointer** | S | ★★☆☆☆ | Publish `0.0.1` stubs that link to npm + docs. Lock names, signal multi-runtime intent. No WASM synth yet — honest "coming soon". |

---

## Effort key

- **S** = 1–2 days
- **M** = 3–5 days
- **L** = 1–2 weeks

---

## Recommended sequencing

### Week 1 — **First-week ship** 🚩

**Ship npm `audioface@0.1.0` with unified `createAudioface().play()` API + 3-line quickstart.**

Why this first:
- Code is ~90% there; gap is packaging + API facade, not new synthesis.
- Owned npm name is worthless until something installs.
- Every other item (React hook, permalink, landing embed, demos) depends on a real package.
- Smallest surface that proves the product promise: procedural tokens, themeable, zero files.

Concrete week-1 checklist:
1. Add `src/index.js` exporting `createAudioface`, `createAudiofaceEngine`, `THEME_PRESETS`, `TOKENS`, `listSequences`.
2. Wrap engine inside `createAudioface` return: `.play(tokenId)`, `.resume()`, `.setVolume()`, `.mute()`.
3. `package.json`: remove `private`, set `version: "0.1.0"`, add `exports`, `files: ["src"]`, `license`.
4. Expand README with install + minimal example + link to lab.
5. `npm publish --access public`.
6. Verify install in fresh dir + run quickstart.

### Week 2

- Deploy lab to **audioface.dev** (playground + theme gallery).
- **Shareable theme permalink** in deployed playground.
- **Demo video** embedded on landing.

### Week 3

- **`useAudioface` React hook** (`audioface/react`).
- **Sound diff A/B** mode on landing (reuse slot UI).

### Week 4

- Polish themes, sequence docs, agent-facing `AUDIO.md` link from npm README.
- PyPI/crates placeholders.
- Gather feedback → plan 0.2 (more tokens, SSR guard, Vue/Svelte adapters).

---

## Minimal public API (v0.1 target)

```ts
import { createAudioface } from "audioface";

const audioface = createAudioface({
  material: "ceramic",
  density: 0.4,
  politeness: 0.72,
  contrast: 0.48,
});

await audioface.resume(); // user gesture
audioface.play("button.press");
audioface.setVolume(0.3);
audioface.mute();
```

Optional re-exports: `THEME_PRESETS`, `TOKENS`, `createAudiofaceEngine` (advanced).

---

## What NOT to ship in 4 weeks

- Full design-system integrations (MUI, Radix, etc.) — wait for hook + feedback.
- Python/Rust runtimes with real synthesis — stubs only.
- Custom token authoring UI — composer export is enough for v0.1.
- Mobile native wrappers.

---

## Success metrics (4-week)

- npm weekly downloads > 0 (any organic install)
- audioface.dev live with playground
- 1 external app/repo using `audioface` in the wild
- README quickstart runnable in < 60 seconds
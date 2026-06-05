---
title: speak-easy PTT flush->final benchmark and fast sherpa flush
type: sessions
tags: [backend, stt, sherpa-onnx, benchmark, latency, speak-easy]
summary: SherpaSession.flush() commits in ~42ms via instant synthetic silence padding; bench --mode ptt PASSES strict and loose at <200ms; live ptt demo (mic/wav/script) proves session reuse E2E; demo doubles as labeled-corpus collector and bench --corpus scores WER against hand-confirmed transcripts
status: active
source: backend-engineer
confidence: high
created: 2026-07-02
updated: 2026-07-02
---

# Summary

Orchestrator-dispatched task (warroom topic `speak-easy-build`). Reframe: real consumers (push-to-talk release, turn detector) finalize externally via `flush()`, so the engine's silence endpoint is off the hot path. Implemented a fast, correct `flush()` and a `--mode ptt` benchmark measuring flush->final. Commits `0331b19` then fix round `0280a25` on `spike/benchmark-sherpa`.

Result (post fix round, both variants over 6 runs): strict release warm median **41.8ms** (cold 40.7ms), loose warm median **44.0ms** (cold 40.4ms), all runs text-correct. PASS (<200ms threshold, ~5x headroom).

Fix round (adversarial review, 2 Majors + 1 human decision):
1. Harness awaits the final EVENT after flush() (`finalAtIndex` on the observer, 10s timeout) instead of assuming synchronous emission; correct for sherpa (sync) and moonshine (async `void #commit`).
2. Two release variants reported per run: strict (last voiced sample, 2140ms, zero real trailing audio; the honest headline) and loose (RMS reference incl. 650ms hangover, 2790ms). Strict passing proves the 1200ms flush padding alone supplies the last word's right context.
3. Stuart's decision: `results/` gitignored, sweep file untracked (kept on disk); bench runs leave the tree clean.

# API Contract

`src/contract.ts` unchanged (requirement). `STTSession.flush()` now commits fast and keeps the session usable:

- Pushes 1200ms of synthetic silence instantly (not real time) so the zipformer chunk-16 encoder's chunk/right-context is satisfied and the last word decodes.
- Never calls `inputFinished()` (that ends the stream); `reset()` inside commit keeps the stream accepting audio.
- No-op after `end()` (guards a native-layer invalid op).

Bench CLI: `pnpm bench --engine sherpa --wav samples/jfk.wav --mode ptt` (mode defaults to `sweep`, preserving prior behavior). PTT mode: manual endpointing, real-time feed to the RMS speech-end reference, then immediate `flush()`; run floor 6; cold = run 1, warm median = runs 2+.

# Database Changes

None.

# Security Considerations

None (local bench spike).

# Performance Notes

- flush->final is dominated by decoding ~2 encoder chunks of silence: ~37-44ms on CPU int8, far under the 200ms budget.
- Word-tolerant gate: word-level edit distance <= 1 vs "and so my fellow americans". Steady-state decode is "AND SAW MY FELLOW AMERICANS" (1 substitution, passes). Fragmented decodes fail.
- Sweep mode re-verified unchanged (~600ms endpoint fall-through), confirming the engine endpointer remains muddy and the external-finalization path is the right product shape.

# Live PTT Demo (commit 629ee95)

Third slice: road-testable demo proving the flush contract end to end.

- `src/capture/ffmpeg.ts`: engine-free mic seam. ffmpeg avfoundation -> 16kHz mono f32le, carry-buffer re-framing into exact 320-sample Float32 frames (readFloatLE copy, alignment-proof), stderr-tail error with macOS mic-permission hint. Electron AudioWorklet replaces this later at the frames-in boundary.
- `src/demo/ptt.ts` (`pnpm demo`): raw-mode Enter start/release loop with live one-line partials and per-utterance release->final latency; toggles serialized through a promise queue; Ctrl+C tears down capture, session, and TTY. `--wav` replays a file per utterance at real-time cadence; `--script "start@0ms,release@2200ms,..."` drives presses deterministically. Final awaited as an event registered before flush() (2s timeout prints "no speech committed"; sherpa emits final only for non-empty text).
- E2E (script mode, jfk.wav): two utterances on the SAME session, both finals "AND SAW MY FELLOW AMERICANS", release->final 41.6ms / 31.9ms, clean exit.
- Bug found by the E2E: fixed per-frame sleep in the wav feed drifted vs wall clock, starving a wall-clock-keyed release of audio (truncated last word, hallucinated tail). Fixed with absolute-deadline cadence. The bench never exposed this because it releases at a frame index.

## Road-test fix round (commit e7eb6bb)

Stuart's live road test failed; three fixes landed:

- Device: `:0` was "Microsoft Teams Audio" (silent virtual) on his Mac, so 14 utterances captured silence. Capture now defaults to `":default"`; `--list-devices` (parses avfoundation `-list_devices` stderr) and `--device <index>` added; the in-use device name prints at startup.
- Ctrl+C: 0x03 was handled but enqueued behind the serialized toggle queue, so a stuck release made the demo feel unkillable. Interrupt bytes (0x03/0x04) now resolve immediately, a second press hard-exits 130, the TTY is restored via a process exit handler, and capture stop() escalates SIGTERM to SIGKILL after 500ms.
- Silent-failure UX: rolling 500ms peak level bar rendered beside partials; a no-text flush prints device + utterance peak + a mic-permission / --list-devices hint.
- Gates: typecheck green; wav E2E stable at 42.7ms/34.8ms (self-test release moved to 2350ms: cold-start decode lag can starve a wall-clock release that has only 60ms margin over the 2140ms voiced end); mic smoke from :default delivered 79 frames, peak 0.23, in 2s (~400ms avfoundation startup before first frame).

# Labeled corpus builder + WER scorer (commit c25c8f9)

Fourth slice: the demo collects ground truth, the bench scores model quality against it. Feeds the upcoming model sweep with Stuart's voice as reference.

- `src/corpus/store.ts`: wav + json sidecar pairs (`utt-<ISO>.wav` + same-stem `.json`). Sidecar schema v1: recordedAt, audio, hypothesis, expected (string|null; null = unlabeled, empty string normalized to null), engineLabel, endpoint, flushToFinalMs, device, peakLevel. Stem claimed with `wx` write flag (same-millisecond collision retries). Hand-editable by design.
- Demo `--save [dir]` (default `corpus/`, gitignored at root only: `/corpus/`) buffers each utterance's frames; after the final, one raw keystroke (s = save, other = discard) then an accept-or-correct line prompt for expected (Enter accepts hypothesis; readline in cooked mode, raw restored after). `--save-all` saves everything unlabeled for unattended runs; `--save` without `--save-all` refuses script/piped runs. Interrupt bytes still bypass everything and answer a pending prompt so the queue drains.
- Bench `--corpus <dir>` (new `src/bench/corpus.ts`): replays labeled pairs through `runPttOnce`, reports per-utterance WER + edits, corpus WER, median flush->final, worst-substitutions tally. `--engine` still selects the engine for the model sweep.
- `src/bench/harness.ts` extracted from run.ts (createEngine, attachSessionObservers, withTimeout, runPttOnce now parameterized by expected); run.ts 606 -> 470 lines and stays a thin CLI. transcript.ts word-error counting now backtracks the DP to a full alignment (substitutions/insertions/deletions); `wordErrorCount` delegates, 8/8 unit tests.
- Release point decision: corpus replay releases at END-OF-CAPTURE, not the RMS strict reference. Demo recordings end at the release keypress, and the RMS tail-noise estimator assumes a quiet trailing window that such captures lack: measured threshold inflation 0.0160 -> 0.1354 and voiced-end misdetection 2140ms -> 1980ms, clipping the final "S" of "AMERICANS" (2 word errors instead of the true 1). End-of-file is the faithful release for release-bounded captures.
- Gitignore trap caught: `corpus/` (unanchored) also ignored the new `src/corpus/` module, silently dropping it from git status; anchored to `/corpus/`.
- Gate: typecheck green; scripted E2E wrote 2 pairs with populated hypotheses; hand-labeled one sidecar; `pnpm bench --engine sherpa --corpus corpus` reported WER=20.0% errors=1/5 subs=[so->saw] flush->final=41.9ms; ptt bench mode re-run PASS (loose warm median 44.6ms) proving the harness extraction did not regress.

## UX fix round (commit e8acdd5)

Two nits from Stuart's live use:

- Corpus saving is armed by default (`corpus/`); `--save <dir>` only overrides the directory, `--no-save` disarms, `--save-all` unchanged. Unattended runs (--script or piped stdin) quietly self-disarm the default with a notice, since the keep/label prompts need a TTY; an explicit `--save` there still errors without `--save-all`; `--no-save` conflicts with `--save`/`--save-all`.
- Default mic is name-resolved: `PREFERRED_MIC_NAMES` in the capture module (default `["MacBook Pro Microphone"]`, case-insensitive substring, list order wins) resolves against the live device list to the matched device's CURRENT index; falls back to `:default` when absent or listing fails; `--device` overrides everything. Startup prints `[1] MacBook Pro Microphone (preferred name match)`.
- Gates: typecheck green; bare scripted replay self-disarms and writes nothing; `--no-save` writes nothing with no notice; `--save-all` still writes pairs; conflict and explicit-save-unattended errors verified; 1.2s live mic smoke showed the name-resolved startup line.
- Note: src/demo/ptt.ts is at 691 lines; the next slice touching it must refactor first (700 hard limit).

# Open Items

- First-partial latency remains ~1.18s (model right context); a smaller-chunk or different model would be needed if early partials matter.
- FLUSH_PADDING_MS=1200 is conservative; could tune down (~800-1000ms) if flush cost ever matters, but at 38ms there is no pressure.
- results/sherpa-sweep.txt sections are upserted independently; section order reflects the most recent mode run.
- Demo mic path (ffmpeg avfoundation) is untested by me (no mic access from this session); Stuart's road test covers it. The wav/script path exercises everything downstream of the frame callback.

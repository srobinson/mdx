---
title: Speak Easy Sherpa Benchmark Implementation
type: sessions
tags: [backend, stt, benchmark, sherpa-onnx, latency]
summary: Implemented and corrected the speak-easy streaming STT latency benchmark with sherpa endpoint sweep results.
status: active
source: backend-engineer
confidence: high
created: 2026-06-21
updated: 2026-06-21
---

## Summary

Implemented the first real latency benchmark for `speak-easy` on branch `spike/benchmark-sherpa`. Initial commit `c6ad061` produced a real sherpa benchmark, but the 92.4 ms headline was corrected as a measurement artifact. Follow-up commits `2d94689` and `06d77d4` corrected the methodology, wrote the full sweep table, and swapped the tiny 20M model for stronger `sherpa-onnx-streaming-zipformer-en-2023-06-26` int8.

Current commit: `06d77d4`.

Current result: no swept endpoint config produces exact JFK expected text. The result file is `results/sherpa-sweep.txt`.

Corrections now in place:

- RMS-window hangover end-of-speech reference replaces raw sample amplitude.
- Runs no longer resolve on the first `final`; final segments are accumulated and selected after reference speech end.
- JFK text comparison is case and punctuation insensitive exact match.
- First partial is split into cold run and warm median excluding run 1.
- `results/sherpa-sweep.txt` records per-config median, text correctness, and actual final text.
- `LESSONS.md` now warns not to confuse lowest measured latency with lowest correct result.

## API Contract

```typescript
export type EndpointMode = "eager" | "turn-aware" | "manual";
export type EndpointConfig = {
  mode?: EndpointMode;
  minTrailingSilenceMs?: number;
  minUtteranceMs?: number;
};

export type STTConfig = {
  sampleRate?: number;
  language?: string;
  endpoint?: EndpointConfig;
};

export interface STTSession extends EventEmitter {
  pushAudio(frame: Float32Array): void;
  flush(): void;
  reset(): void;
  end(): Promise<void>;
}
```

Events remain `partial`, `final`, `endpoint`, and `error`. The `endpoint` event is advisory. `flush()` commits the current hypothesis without closing the session. `reset()` drops the in-flight hypothesis while keeping the session open. `end()` flushes and closes.

## Database Changes

No database changes.

## Security Considerations

The benchmark downloads model assets into ignored local `models/` paths. No secrets are used. WAV fixtures and model assets remain ignored by git. The engine boundary accepts 16 kHz mono `Float32Array` frames and validates sample rate before recognition.

## Performance Notes

Verification commands run after the latest correction:

```bash
pnpm typecheck
pnpm bench --engine sherpa --wav samples/jfk.wav
```

Latest sherpa benchmark result on `samples/jfk.wav`:

- Engine: `sherpa-onnx-node-1.13.3:sherpa-onnx-streaming-zipformer-en-2023-06-26:int8`
- Speech-end detector: RMS window 20 ms, hangover 650 ms, threshold 0.0160
- Reference speech end: 2790 ms
- Expected text: `and so my fellow americans`
- Knee: none
- Trail 80 ms: 252.8 ms, text-correct no, `AND SAW MY FELL OW A MERICANS`
- Trail 120 ms: 602.8 ms, text-correct no, `AND SAW MY FELLOW A MERICANS`
- Trail 160 ms: 599.9 ms, text-correct no, `AND SAW MY FELLOW A MERICANS`
- Trail 200 ms: 599.3 ms, text-correct no, `AND SAW MY FELLOW AMERICANS`
- Trail 300 ms: 604.0 ms, text-correct no, `AND SAW MY FELLOW AMERICANS`
- Event to final: 0.0 ms across the sweep
- Warm first partial median: 1197.2 ms
- First partial root cause: model right context. A direct diagnostic confirmed decode is invoked when sherpa reports readiness per pushed frame, but the model does not emit non-empty text until its chunk/right-context is satisfied.

Moonshine secondary result from the earlier run:

- Engine: `moonshine-cpu`
- Median model-only event to final: 53.2 ms
- Median endpoint to final with file end-of-input: 1316.8 ms
- Status: fail as a primary streaming endpoint engine because it is non-streaming and finalizes at end-of-input

## Open Items

- Decide whether JFK exact text is the right correctness fixture. The stronger streaming Zipformer recognizes `AND SAW MY FELLOW AMERICANS`, which is a plausible homophone but fails exact expected text.
- If exact JFK text is mandatory, test a different streaming model class or a non-zipformer baseline to separate acoustic homophone behavior from endpointing.
- Tune first partial latency separately. Warm first partial improved from roughly 2.1 seconds to roughly 1.2 seconds with the stronger model, but it remains high for conversational use.
- Decide whether production should expose `turn-aware` as endpoint-only or as a host-driven flush policy.

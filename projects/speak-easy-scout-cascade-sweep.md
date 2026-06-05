# Scout: cascade-vs-realtime latency sweep (speak-easy)

Read-only scout of `packages/convo-engine`, `packages/speech-io/src/bench`, and
`packages/browser-voice` on branch `experiment/cascade-models`, run 2026-08-17.
Nothing in the repo was modified. The working tree carried uncommitted WIP
(`runtime.ts`, `browser-voice/src/session.ts`, `llm/src/mercury.ts`) while the
scout ran; it landed mid-scout as `978f667 feat(llm): add Mercury adapter and
browser engine picker`, and the tree is clean at time of writing. Findings
reflect that content, so slice 4's sequencing warning is already satisfied.

Verdict up front: a headless sweep is feasible with no new composition root and
no changes to `ConversationLoop`. Every piece exists. The gaps are that the two
pieces the sweep needs most are not reachable (the wav replay source is private
to a CLI entrypoint, and there is no headless audio sink), and that the loop
drops microphone frames while it is thinking or speaking, so a naive multi
utterance script silently loses turns.

---

## Reuse Map

### (a) How the loop obtains audio

`ConversationLoop` takes audio through an injected seam, never a device.
`AudioSource` (`packages/convo-engine/src/loop.ts`) is a two method push
interface (`start({onFrame, onError})` / `stop()`), supplied as `ConvoDeps.mic`
and re-exported as a type from `packages/convo-engine/src/index.ts`. No engine
or platform detail reaches the loop.

Three implementations exist:

| Implementation | Module | Reachable? |
|---|---|---|
| `MicAudioSource` (ffmpeg capture) | `packages/convo-engine/src/demo.ts` | no, private to the CLI |
| `WavAudioSource` (recorded replay) | `packages/convo-engine/src/demo.ts` | no, private to the CLI |
| `BrowserAudioSource` (websocket frames) | `packages/browser-voice/src/browser-audio.ts` | yes, exported |

`WavAudioSource` is exactly the sweep's frame source: it takes a `WavAudio`,
replays `wav.frames` at `CAPTURE_FRAME_MS` cadence, then appends
`WAV_SILENCE_TAIL_MS` (700ms) of zero frames so eager endpointing fires and the
turn closes. It is already proven by `pnpm convo --wav <path>`.

Two blockers on reusing it as written:

1. **It is private to a script that self-executes.** `demo.ts` ends in a bare
   `await main()`, so importing the module runs the terminal demo. The class has
   to be promoted into a module of its own before any other caller can touch it.
2. **Its cadence drifts.** `WavAudioSource.start` schedules with
   `setTimeout(tick, CAPTURE_FRAME_MS)`, which is the exact pattern
   `#feedWav` in `packages/speech-io/src/demo/ptt.ts` documents as wrong
   ("a fixed sleep per frame accumulates timer overshoot and starves the release
   point of audio"); `#feedWav` schedules each frame against an absolute
   deadline instead. Promote the corrected cadence, not the copy that drifts.

**The turn-taking gap, and the single biggest thing to design for.**
`ConversationLoop.#onFrame` routes frames to the recognizer only while state is
`listening`; in `thinking` or `speaking` the frame is either fed to the barge-in
VAD or dropped. `WavAudioSource` pushes on a wall clock and knows nothing about
loop state, so in a multi utterance script every frame that lands while the
assistant is replying is discarded and that utterance is lost. A sweep source
must gate on the loop returning to `listening`, observable two ways: the
`{ type: "state", state }` event on `ConvoOptions.onEvent`
(`packages/convo-engine/src/events.ts`) or the `ConversationLoop.state` getter.

### (b) Existing wav-push path in `bench` and the demos

The decoder is reusable; the feed loops are not.

- `readWavFrames(path, frameMs)` and `WavAudio` (`packages/speech-io/src/bench/wav.ts`)
  are exported from the speech-io index. `WavAudio` carries `sampleRate`,
  `channels`, `bitsPerSample`, `durationMs`, `samples`, and `frames` already
  chunked and zero padded to a fixed frame size. The decoder hard-rejects
  anything that is not 16kHz mono, which matches `CAPTURE_SAMPLE_RATE` and the
  corpus recordings.
- `runOnce` (`packages/speech-io/src/bench/run.ts`) and `runPttOnce`
  (`packages/speech-io/src/bench/harness.ts`) both push wav frames straight into
  an `STTSession` and never construct a loop, a responder, or a sink. They also
  score every run against the hard-coded `EXPECTED_JFK_TRANSCRIPT`
  (`packages/speech-io/src/bench/config.ts`). Neither is a base for a
  loop-level sweep; treat them as precedent for shape only.
- `#feedWav` (`packages/speech-io/src/demo/ptt.ts`) is the third feeder and the
  only correct one. It is a private method on the PTT demo class.

Utterance inventory already exists: `corpus/` holds 13 wav plus json sidecar
pairs (16kHz mono, gitignored). `readCorpusEntries(dir)` in
`packages/speech-io/src/corpus/store.ts` returns `CorpusEntry[]` with
`sidecar.expected` (the labelled reference text) and `sidecar.hypothesis`.
Note this loader is **not** exported from the speech-io index, so the sweep
either adds the export or reads the sidecars itself.

### (c) How the loop knows playback drained, and whether a headless sink exists

The drain signal is `AudioSink.end()` resolving. `ConversationLoop.#runTurn`
awaits `sink?.end()` after the responder stream completes and before
`#recordTurn`, so sink latency gates when the turn is recorded and when the loop
returns to `listening`.

Two implementations, both real:

- `createSegmentPlayer(sampleRate)` (`packages/speech-io/src/tts/player.ts`):
  ffplay over a stdin PCM pipe, falling back to afplay. `end()` resolves on
  process exit, so it costs the full spoken duration in wall clock.
- `BrowserAudioSink` (`packages/browser-voice/src/browser-audio.ts`): `end()`
  resolves when the browser acks with `playback-drained`, bounded by
  `PLAYBACK_TIMEOUT_MS`.

**There is no headless or null sink in `src`.** The only one that exists is
`FakeSink`, private to `packages/convo-engine/src/loop.test.ts`. Writing one is
about twenty lines: `open()` noop, `write(segment)` accumulating
`segment.audioDurationMs`, `interrupt()` resolving the accumulated position,
`end()` resolving immediately.

A null sink is metrics-safe, and this is worth stating explicitly in
CASCADE-SWEEP.md. `#runTurn` stamps `firstAudioAt` with the loop's own `now()`
when the first `audio` event arrives, *before* `createSink` is called, and
`spokenMs` is summed from `segment.audioDurationMs`, so none of the three
headline numbers depend on the sink at all. The honest caveat is the one
`tts/player.ts` already documents in `SINK_PRIMER_MS` and
`DEVICE_OPEN_EST_MS` (500ms measured ffplay CoreAudio open): a sweep run with a
null sink reports first-audio at segment arrival and excludes device open
latency, exactly as the live demo's numbers do.

Second effect of a null sink: the loop returns to `listening` as soon as the
last segment is handed over rather than after the reply finishes playing, which
is what makes the scripted source in (a) mandatory rather than optional.

### (d) What `runtime.ts` exposes for config enumeration

`createConversationRuntime(config: RuntimeConfig, env = process.env)` returns
`{ stt, responder, label }` and is exported from the convo-engine index.
`RuntimeConfig` already spans the whole matrix the sweep wants:
`responder` (`"cascade" | "realtime"`), `llmProvider` (`"cerebras" | "mercury"`),
`llmModel`, `llmReasoningEffort` (Mercury `instant` / `low`),
`ttsEngine` (`"sherpa" | "cartesia"`), `ttsModel`, `voice`. So **no new
composition root is needed**; the sweep is a loop over `RuntimeConfig` literals.

Four rough edges to plan around:

1. `buildResponder`, `buildChatModel`, and `buildTts` are module-private.
   `createConversationRuntime` always constructs `new SherpaEngine()`, calls
   `prepare()`, and wraps it in `withRewrite`, and there is no way to hand it a
   prebuilt `VoiceToText`. Every config in the matrix therefore rebuilds the STT
   stack even though STT is constant across the sweep. The cost is an
   `ensureModel` asset check per config rather than a re-download (the sherpa
   recognizer is constructed per `open()` regardless), so this is a cleanliness
   problem more than a runtime one, but it means the sweep cannot hold STT
   fixed by construction.
2. `RuntimeConfig.llmReasoningEffort` is typed `MercuryReasoningEffort`, which
   the convo-engine index does not re-export (it exports `LlmProvider` and
   `TtsEngine` but not this). A sweep outside the package can only name it as
   `RuntimeConfig["llmReasoningEffort"]`. Also flagged independently by the
   `/code-review` run on the current diff.
3. `label` is the only config identity that comes back, and `TurnMetrics` has no
   config field, so the sweep must pair `{ config, label }` with each turn's
   metrics itself.
4. Precedent, not reusable code: `runtimeConfigFor`
   (`packages/browser-voice/src/session.ts`) already maps a three-way engine
   choice (`realtime`, `mercury-instant`, `mercury-low`) onto `RuntimeConfig`.
   It hard-codes `llmProvider: "mercury"` for every cascade start and drops
   `llmModel` entirely, so it cannot express the Cerebras arm the sweep needs.
   Copy the shape, not the function.

### (e) Metrics shapes and the existing results writer

`packages/convo-engine/src/metrics.ts`:

- `TurnMetrics = { turn, transcript, endpointToFinalMs, endpointToFirstTokenMs, endpointToFirstAudioMs, tokenCount, spokenMs }`.
  Every interval is anchored at the endpoint, and `endpointToFirstAudioMs` is
  documented as the headline.
- `buildTurnMetrics(turn, transcript, ts, tokenCount, spokenMs)` where
  `TurnTimestamps = { endpointAt, finalAt, firstTokenAt, firstAudioAt }`.
- `formatTurnLine(metrics)` renders the live per-turn line.
- `formatSessionSummary(turns)` renders `session summary: N turn(s), medians:`
  followed by the three medians, marking first-audio `(headline)`. This is the
  per-config block the sweep wants verbatim.

Two ways to collect: the `ConversationLoop.metrics` getter
(`readonly TurnMetrics[]`) or the `{ type: "metrics", metrics }` conversation
event. Export gap: the convo-engine index exports `type TurnMetrics` only, not
`buildTurnMetrics`, `formatTurnLine`, or `formatSessionSummary`, so a sweep
living outside the package cannot format anything today.

Results writers: `upsertReportSection(path, header, lines)` in
`packages/speech-io/src/bench/report.ts` is the **only** reusable one. It
mkdir -p's the directory, replaces the one `# <title>` section it owns, and
leaves sibling sections intact; `writeSherpaSweep` and `writePttReport` use it
to maintain `results/sherpa-sweep.txt` (`SHERPA_SWEEP_PATH` in
`bench/config.ts`). **No JSON or CSV writer exists anywhere in the repo.** The
TTS sweeps write only wavs plus a console table (`printColumns` in
`packages/speech-io/src/tts/sweep.ts`) and `runCorpusBench` writes no file at
all; in both cases a human transcribes the console numbers into the markdown.

Shared cell formatters, all already exported through the speech-io index and
already used by convo-engine's `metrics.ts`: `formatMs` (1 decimal plus `ms`),
`formatOptionalMs` (`n/a`), `formatBoolean` (`y`/`n`), `median`,
`medianOptional`.

### (f) How MODEL-SWEEP.md and TTS-SWEEP.md are structured

Both are hand-written at the repo root, committed, and generated by no tool.
Shared skeleton to match:

1. `# <Title>` then a short goal paragraph, no badges, no TOC, no date line.
2. A method section (`## Method`, or `## Models compared` plus
   `## Config surface` in the TTS doc): bullets naming corpus, scorer, latency
   definition, and normalization, with inline commands in backticks.
3. `## Results`: one table.
4. `## Findings`: bold-lead bullets (`- **Winner: ...**`), each a short
   paragraph.
5. Optional dated experiment sections for follow-up arms, with a
   `> Superseded by ...` blockquote when a later section overrides an earlier
   recommendation.
6. `## Recommendation`.
7. `## Reproduce`: one fenced block with no language tag, holding full
   `node packages/...` paths (deliberately not the `pnpm bench` / `pnpm convo`
   aliases) with trailing `#` comments aligned into a column, followed by a
   closing paragraph naming the registry file and where outputs land.

Cell conventions: ids in backticks, winner in `**bold**`, `(**default**)` on the
selected row, `—` for not applicable in doc tables and `n/a` where the number
came from `formatOptionalMs`, latency to one decimal with a `ms` suffix, WER as
`12.8% (6/47)`, RTF to three decimals, `yes`/`no` in doc tables while the
machine-written `.txt` uses `y`/`n`, no footnotes anywhere, and the human
verdict recorded with a dated attribution ("Per Stuart's verdict (2026-07-04)").
Header rows use plain `|---|` with no alignment colons; only the machine-written
`results/sherpa-sweep.txt` uses `---: ` alignment.

Proposed CASCADE-SWEEP.md results table, matching those conventions and the
three metrics the loop already records:

```
| Config | Responder | LLM | TTS | endpoint->stt-final | endpoint->first-token | endpoint->first-audio | turns | text |
|---|---|---|---|---|---|---|---|---|
```

---

## Quality Map

Measurements first: nothing in the scouted area exceeds the 700 line guardrail
and no function exceeds ~150 lines. Largest files are
`convo-engine/src/responder/openai-realtime.test.ts` (648),
`convo-engine/src/responder/openai-realtime.ts` (491),
`speech-io/src/bench/run.ts` (491), `convo-engine/src/loop.test.ts` (430),
`convo-engine/src/loop.ts` (382), `convo-engine/src/demo.ts` (293). Longest
functions: `ConversationLoop.#runTurn` (~90), `RealtimeSession.respond` (~84),
`startBrowserVoiceServer` (~73). The repo gate is `pnpm -r typecheck` and
`pnpm -r test` (`node --test`); there is no lint or formatter anywhere.

Ranked, with the sweep-relevant ones first.

1. **Four independent wav feeders, and the drift fix landed in only one.**
   `#feedWav` (`speech-io/src/demo/ptt.ts`) uses absolute deadline scheduling
   and carries the comment explaining why; `runOnce` (`bench/run.ts`),
   `runPttOnce` (`bench/harness.ts`), and `WavAudioSource.start`
   (`convo-engine/src/demo.ts`) all still use the fixed per-frame sleep the
   comment warns about. The published bench latency numbers come from a
   drifting feeder. The sweep must not become the fifth copy.
2. **Reusable audio adapters trapped in a CLI entrypoint.** `MicAudioSource`
   and `WavAudioSource` are private to `convo-engine/src/demo.ts`, which
   self-executes via `await main()`. `BrowserAudioSource` was written from
   scratch in browser-voice as a result. This is the direct blocker on the
   sweep and the cheapest thing to fix.
3. **No headless sink, and the responder seam is unexported.** Covered in
   Reuse Map (c). Separately, `VoiceResponder`, `ResponderSession`,
   `ResponderEvent`, and `CascadeResponder`
   (`convo-engine/src/responder/contract.ts`) are absent from the convo-engine
   index even though the exported `ConversationRuntime.responder` is typed
   `VoiceResponder`; `fakeRuntime` in `browser-voice/src/host.test.ts` compiles
   only by structural match. The file's own doc comment calls it the seam "for
   embedders".
4. **The bench scores every wav against a hard-coded transcript.** `runOnce`
   and `runPttSummary` pass `EXPECTED_JFK_TRANSCRIPT` unconditionally and
   `parseArgs` has no `--expected`, so `pnpm bench --wav anything.wav` reports
   `FAIL`. The corpus path already solved this by reading
   `entry.sidecar.expected`; the wav path never got the same treatment. Any
   text-correctness column in CASCADE-SWEEP.md should follow the corpus path.
5. **Four hand-rolled CLI arg parsers with four different contracts.**
   `demo.ts parseArgs`, `bench/run.ts parseArgs`, `speech-io/src/demo/args.ts
   parseArgs`, and the `tts/sweep.ts` caller each re-implement flag pairing and
   unknown-flag errors, and they disagree: only `run.ts` validates integers
   (`parsePositiveInteger`), so `pnpm convo --max-turns abc` yields `NaN` and
   silently disables the turn cap; only `demo.ts` handles the bare `--` that
   pnpm forwards. A fifth sweep CLI would make it five.
6. **`bench/` is a public dependency of production code.** The speech-io index
   re-exports `readWavFrames` from `bench/wav.ts`, `formatMs`/`formatOptionalMs`
   from `bench/format.ts`, and `median`/`medianOptional` from `bench/stats.ts`,
   and `convo-engine/src/metrics.ts` (production instrumentation) imports two of
   them. The domain now depends on a directory named for a dev harness. The
   names are general purpose; the directory is not.
7. **Half-finished provider migration across the two hosts.** `DemoArgs` in
   `convo-engine/src/demo.ts` structurally carries `llmProvider` and
   `llmReasoningEffort` but `parseArgs` defines no flags for either, so the
   terminal demo cannot reach Mercury; `runtimeConfigFor` in browser-voice
   hard-codes `llmProvider: "mercury"` so the browser cannot reach Cerebras.
   `buildChatModel` still supports both. Neither host can express the full
   matrix the sweep is being built to measure, which is precisely why the sweep
   needs its own config table rather than a host flag.
8. **From the concurrent `/code-review` on the uncommitted diff, and relevant
   here:** `runtimeConfigFor` destructures `llmModel` out of the defaults and
   never restores it, so `SPEAKEASY_MODEL` read in `browser-voice/src/server.ts`
   is silently discarded; and `MercuryReasoningEffort` is used in the public
   `RuntimeConfig` without a matching re-export. Both land in `runtime.ts` and
   `session.ts`, the two files the sweep depends on and the other agent is
   currently committing.
9. **Duplicated test doubles, no shared fixture module.** `FakeSTTSession`
   (`convo-engine/src/loop.test.ts`) and `FakeSttSession`
   (`browser-voice/src/host.test.ts`) are near-identical EventEmitter STT fakes;
   `FakeTTS` and `StubTTS` duplicate the token-to-segment fake; the
   `AudioSegment` literal is rebuilt in five places. The sweep's tests will want
   the same doubles a sixth time.
10. **Coverage holes exactly where the sweep will build.** `runtime.ts`,
    `demo.ts`, and `server.ts` have no tests; `bench/` has exactly one test file
    (`transcript.test.ts`), leaving `wav.ts` (295 lines of RIFF parsing),
    `speech.ts`, `stats.ts`, `harness.ts`, `report.ts`, and `run.ts parseArgs`
    untested. Two tests in `host.test.ts` start the host without injecting
    `createRuntime` and fall through to the real `createConversationRuntime`;
    they pass only because no `start` command is ever sent, so any new test that
    sends `start` without a factory would load real ONNX models and dial live
    APIs.
11. **Smaller items.** `firstPartialMedian` is computed in `runEngineSummary`
    and stored on `Summary` but never read. `decodeWavFrames`, `canTransition`,
    and `CONVO_STATES` are exported with no external consumer. `PttRunResult` is
    rendered field-for-field twice (`printPttSummary` with spaces,
    `formatPttRow` with pipes), so a new column must be added in both.
    `state.ts`'s header still says v1 does not listen while speaking although
    `LEGAL_TRANSITIONS` and the barge-in VAD say otherwise, and
    `AudioSink.interrupt` in `loop.ts` carries two stacked doc comments, the
    first superseded when the method gained its return value. `CascadeSession.interrupt`
    ignores the `playedAudioMs` promise the contract requires and the loop
    constructs, so the two responders honor different halves of one interface.
    `SHERPA_SWEEP_PATH` is a bare relative path while `TTS_RESULTS_DIR` uses
    `join(process.cwd(), ...)`, two conventions for one output tree.

---

## Plan

Boundary call first, because it decides where everything lands: the sweep drives
`ConversationLoop`, and `convo-engine` depends on `speech-io`, not the reverse.
Putting a loop-driving sweep under `packages/speech-io/src/bench` would invert
the dependency. **The sweep belongs in `packages/convo-engine`**, reusing
speech-io's decoder, formatters, and report writer through the package index,
with a root `pnpm cascade-sweep` script alongside the existing runners.

### Slice 1: promote the audio adapters out of the demo

Move `MicAudioSource` and `WavAudioSource` from `convo-engine/src/demo.ts` into
their own module (`src/audio/`), adopt the absolute-deadline cadence from
`#feedWav` rather than the drifting `setTimeout`, export both from the index,
and leave `demo.ts` importing them. Mechanical move plus one behavior fix,
stated as such.
Gate: `pnpm -r typecheck`, `pnpm -r test`, and `pnpm convo --wav corpus/<file>
--max-turns 1` still completes a turn.

### Slice 2: headless sink

Add `createNullSink()` in the same `src/audio/` module, exported: `open()` noop,
`write` accumulating `segment.audioDurationMs`, `interrupt()` resolving the
accumulated position, `end()` resolving immediately. Unit test asserting the
accumulated position and that `end()` does not wait.
Gate: `pnpm -r test`.

### Slice 3: scripted multi-utterance source

Add `ScriptedWavSource implements AudioSource` that holds an ordered list of
`WavAudio` utterances and pushes the next one only after the loop reports
`state: "listening"` again, with a per-utterance silence tail so eager
endpointing fires. This is the piece that makes a headless multi-turn sweep
correct rather than lossy. Test with the existing loop fakes: two utterances,
assert two `metrics` events and no dropped turn.
Gate: `pnpm -r test`.

### Slice 4: reach the config matrix

Re-export `MercuryReasoningEffort` and the responder contract types from the
convo-engine index, and either export `buildResponder` or let
`createConversationRuntime` accept a prebuilt `stt` so the sweep holds STT fixed
across configs. Sequence this **after** the concurrent WIP on `runtime.ts` and
`session.ts` lands, or it will conflict.
Gate: `pnpm -r typecheck`.

### Slice 5: the sweep runner

`packages/convo-engine/src/sweep/run.ts`: a declarative array of
`{ id, config: RuntimeConfig }` rows covering realtime, cascade x
{cerebras, mercury-instant, mercury-low} x {sherpa, cartesia}; for each row,
build the runtime, run the scripted source over the pinned utterances with the
null sink, collect `TurnMetrics` from the `metrics` event, and print
`formatSessionSummary` per config. A config whose key is missing or whose API
call fails must be recorded as skipped and the matrix must continue, never
abort. Keep matrix expansion a pure function so it is unit testable without
network.
Gate: `pnpm -r test` for the pure parts, one live single-config run for the
wiring.

### Slice 6: results and the document

Write per-config medians through `upsertReportSection` into
`results/cascade-sweep.txt`, matching the `writeSherpaSweep` precedent, plus a
raw per-turn dump so the distribution survives (see decisions). Then write
`CASCADE-SWEEP.md` by hand from the run, following the skeleton and cell
conventions in Reuse Map (f), with the null-sink caveat stated in the method
section and the verdict recorded as a dated attribution.
Gate: the doc's own `## Reproduce` block, run verbatim.

### Decisions needed

1. **Feed cadence.** Real time (bench precedent, keeps endpoint anchoring
   honest against wall-clock network legs) or faster than real time (cheaper
   sweeps, but sherpa finalizes on samples while Realtime, Cerebras, Mercury,
   and Cartesia stay on the wall clock, which skews the comparison). Recommend
   real time.
2. **Utterance set.** All 13 `corpus/` pairs or a pinned subset. Recommend a
   pinned, labelled subset so text correctness can be reported next to latency,
   and note that `corpus/` is gitignored, so the doc must name the utterances.
3. **Cold turn handling.** The bench convention treats run 1 as cold
   (`DEFAULT_RUNS = 5`, `PTT_MIN_RUNS = 6`, cold reported separately from the
   warm median). Realtime and Cartesia both pay connection setup on turn 1.
   Recommend the same split: report cold turn and warm median separately.
4. **Results format.** `upsertReportSection` text only (matches every existing
   precedent, no JSON writer exists in the repo) or text plus a JSON per-turn
   dump. The brief asks for per-turn `TurnMetrics` in `results/`, and medians
   alone discard the distribution. Recommend both, with the JSON writer as new
   and clearly owned by the sweep.
5. **Scope of the matrix per run.** Sweeping every arm costs four API keys and
   real money per pass. Recommend a `--only <id>` filter so single arms can be
   re-run without paying for the whole matrix.
6. **Whether slice 4 exports `buildResponder` or injects `stt`.** Injection
   keeps one composition root and is the smaller public surface; exporting
   `buildResponder` is smaller to write. Recommend injection.

### Tests and gates

`pnpm -r typecheck` and `pnpm -r test` are the entire repo gate; there is no
lint or formatter to satisfy. New unit tests should cover the null sink, the
scripted source turn-taking, matrix expansion, and results row formatting, all
with injected fakes. Given finding 10, no new test may construct a runtime
without injecting a factory, or it will load real ONNX models and dial live
APIs. Consider extracting the duplicated STT/TTS fakes into a shared fixture
module as part of slice 3 rather than writing a sixth copy.

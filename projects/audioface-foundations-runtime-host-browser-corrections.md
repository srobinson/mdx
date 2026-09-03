---
title: Audioface browser host boundary correction
type: projects
tags: [audioface, foundations, browser, worker, boundary, verification]
summary: Program call admission now measures the complete worker envelope and preserves the generation when one call exceeds the byte cap.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-program-host-spec, audioface-foundations-runtime-host-browser-build, audioface-foundations-runtime-host-browser-review]
confidence: high
---

# Browser host boundary correction

The correction is committed at `3221511a59170b3fafaaa6924cf1a25f98a26b37` on `probe/foundation-integrated`. Its base is `efa6af6f8283efe0dfd362b74c74c11bdf16d2ca`. The source tree is clean. The active [program host specification](/Users/alphab/.mdx/design/audioface-foundation-program-host-spec.md) remains SHA256 `3f32506eb9bbbddc3a9500455d3fa177e23aef370cd3ff2dfbd0f7d8f8aa7574`. The main README remains SHA256 `f34eb76a9bd6818ccb3ae8243755c6e4598d93efccfe182d5d37bf550f254525`.

## Cause and correction

`ProgramClient.request` measured the bare `ProgramAction`. The worker measured the larger `WorkerCall`, which adds `kind` and `serial`. A bare action measured at 65,535 bytes passed main admission. Its wrapped form exceeded the 65,536 byte cap at worker ingress. The worker treated that ingress failure as terminal, ended the generation and settled unrelated callers with unknown application.

The client now constructs one typed `WorkerCall` with its next serial, measures that object through the existing `programEnvelopeBytes` authority, admits the caller latch, then posts the same object. A local capacity refusal occurs before the serial changes and before the pending caller map changes. The worker keeps its ingress check.

The existing measurement returns sizes in three byte steps because it conservatively measures the JSON length at three bytes per code unit. The focused cases are therefore 65,532 bytes, 65,535 bytes and 65,538 bytes. The first two pass client admission. The last fails locally. A 65,536 byte serialized result is not representable under this measurement.

## Reuse and hygiene

The correction reuses `WorkerCall`, `programEnvelopeBytes`, `postWorkerControl`, the pending caller map and the existing worker validation. It adds no measurement helper, protocol type or wrapper constructor. The rejected request consumes no call serial. Caller capacity remains unchanged.

The reviewer noted other posting forms. They have separate responsibilities. `postWorkerControl` writes main control to a `Worker` or `MessagePort` and supports transferred ports. `postPortMessage` writes typed audio host messages without transfer ownership. `ProgramPort.send` owns direct program transport accounting and verified backing transfer behavior. The worklet's direct inspection and fatal messages are proof and terminal controls outside the audio host message type. Consolidating these paths would merge different contracts, so this correction leaves them separate.

Production disposal is also unchanged. Main confirms disposal only after context closure or offline completion, then removes listeners, terminates the worker, closes the port and disconnects the node. The proof only `program-disposed` worker control does not replace that teardown.

## Focused proof

The independent pre correction reproduction recorded a 65,535 byte bare action whose wrapper exceeded capacity. Both the oversized caller and an earlier open settled `generation-ended`, the worker ended and main recorded the capacity error. The focused regression then failed with `Missing expected exception` before the production change.

At the committed SHA, the regression passes. The real three realm proof sends the 65,532 and 65,535 byte envelopes, refuses 65,538 bytes before admission, and retains an existing trigger scheduled for frame 4,096. A following valid trigger applies at frame 768. The earlier trigger later applies at frame 4,096. The worker remains active, client pending state returns to zero and main records no failure.

## Browser and repository gates

The exact SHA [verification manifest](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-browser-corrections/verification-final.json) records these results:

| Gate | Result |
| --- | --- |
| `pnpm run check` | Exit 0, 503 passed, zero failed, typecheck, lint, format and structure passed |
| Focused regression | Exit 0, one passed |
| Three realm boundary proof | Exit 0, generation and unrelated callers preserved |
| Bounds and sizing | Exit 0, maximum file 603 lines, maximum function 144 lines |
| Headless Chrome | 22 cases, 88 browser to Node channel comparisons, five legacy events, realtime pass |
| Headed Chrome | 22 cases, 88 browser to Node channel comparisons, five legacy events, realtime pass |
| Negative controls | Ten expected exit 1 results for sample, outcome, worker, processor and timeout faults |

The 22 `sampleSha256` identities are pre sum Sound 1 captures. They match the prior `e6ddf9d` single runtime proof in both browser modes. All 22 final mixed channel 0 hashes differ from those prior values. Each final mixed capture matches its current Node reference with zero mismatches.

| Artifact | SHA256 |
| --- | --- |
| `index.html` | `52d8bf55f7aef4c46585beb7c2c5e6b0413e42be7718a996dc2ea3308a46339f` |
| `null-test.html` | `5b1eb98a1709149454e6a5b7c0e6a320060e78dbba3aa0ff9e31c1c92552019d` |
| `program-test.html` | `a1df22897543357f65915e65c980f8e24f8d6c9d46b19781493c281cdcd8c181` |
| `program-worker.js` | `7dc3b028d854e8b0615bdeca8263f833dc65f5ba73bf4733a0d251f16a196cc0` |
| `program-worklet.js` | `3584011e097de4a64819b9d6ef3423978a39a0e8581154c096929c7ce78465e5` |

Only `index.html` and `program-test.html` changed because they embed the corrected client. Fresh headed and headless runs executed both changed pages. `null-test.html`, `program-worker.js` and `program-worklet.js` are byte identical to the independently reviewed `efa6af6` artifacts, so their prior source identity and direct transport evidence carry forward. The fresh runs still execute the unchanged worker and worklet artifacts.

The verifier closed every session that it created. The preexisting `tm`, `audioface-branding` and `tm-s2` sessions remain untouched. This correction makes no deadline, dropout or performance claim.

The report and digest are readable. Markdown indexing returned `Path outside root` for this project report, so the index configuration remains unchanged.

Evidence: `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-browser-corrections/`. Pending: independent delta review of `3221511a59170b3fafaaa6924cf1a25f98a26b37`.

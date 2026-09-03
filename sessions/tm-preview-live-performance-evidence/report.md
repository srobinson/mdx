# Preview live performance verification

Observed 2026-09-08T01:06:21.112906+00:00.

Preview backend PID 97301 started at 2026-09-08T00:53:56Z with version 0.3.0.post1.dev574+g0c6a57559. Its interpreter resolves both changed modules to this checkout. HEAD is 0c6a57559a1c6cc2487946b9c614517ebbc18fbb on fix/support-derivation-causes. The working tree remained clean. No source changes, push, or restart were performed.

## Live measurements

| Path | Median ms | p95 ms | Maximum ms |
| --- | ---: | ---: | ---: |
| backend | 1.307 | 2.670 | 24.933 |
| terminal | 1.680 | 3.441 | 6.781 |
| actual PTY reply | 0.847 | 1.860 | 2.231 |

The sampler ran 100.3 seconds, with 972 samples and 960 samples carrying an active journal. There were no HTTP failures. CPU from cumulative process time deltas: backend 5.54%, gateway 4.04%, shared proxy 15.44% of one core. Other active diagnostics contributed to this load.

The journal grew from 4128 to 12744108 bytes while transport.json retained one modification timestamp. Terminal snapshot mean rose from 1.38 to 2.50 ms between the first and last streaming quarters as the returned snapshot grew. It remained responsive.

The actual PTY test sent 40 inputs through the preview Python WebSocket bridge to a temporary gateway shell and a line reader, then validated transformed replies. Inputs had three leading spaces and 68 bytes at 40 columns, exercising wrapping. Command echo could not satisfy the check. All replies arrived. A separate shell command test also passed 40/40, at 88.24 ms median and 143.36 ms p95, including shell processing and prompt hooks. Closing each socket terminated its owned shell.

## Capture correctness

- Exchange 7e45e75b-c611-4c71-8866-dacac785bfbe: 2359 transport messages, 15561 response characters, completed, response/events/turn exactly equal to full replay. Input file hashes stayed stable during proof.
- Exchange fc4aeac1-3a7f-4894-b23b-a8b49947abe0: 2989 transport messages, 19639 response characters, completed, response/events/turn exactly equal to full replay. Input file hashes stayed stable during proof.

Both probe deliveries reached completed through wait_for_reply. The final audit covers all five completed probe exchanges and passes all five. No unfinished probe exchange remains. The temporary probe and diagnostic helper were closed through the control plane. No watch subscription remains.

## Separate reproduced defect

Workspace watch registration twice returned busy_gateway. The actual gateway Activity SSE endpoint returned HTTP 200 and a valid snapshot with 410 items and 1110132 bytes. IncrementalSseFrames defaults to 1048576 bytes and emitted zero frames for that exact snapshot. The same parser configured to fit the snapshot emitted it intact. This prevents Activity readiness and causes registration timeout. No fix was made in this performance verification.

Reproduce with api/.venv/bin/python -B probe-watch.py from the evidence folder. The script records the current snapshot hash and metrics, without persisting its content.

## Boundaries and reruns

These are current live measurements, not a matched before/after desktop benchmark. Historical performance comparisons remain in the previous handoff. The initial 60-second sample completed after the first stream; its files are named after-first-stream and are not used as sustained-stream evidence.

Desktop renderer paint, frame pacing, and key-to-pixel latency remain unmeasured. The exposed CDP interface is scoped to browser panes and there were no attachable pane targets. No renderer restart or configuration change was made. PTY round trips prove the transport path, not pixel presentation.

The sampler end_marker field can match text from an earlier retained response and is not completion proof. Completion is established independently by delivery status and replay of provider terminal evidence.

Scripts: sample-live.py --run RUN_ID --seconds 100 --label NAME; probe-pty.py --mode raw --label NAME; audit-replay.py; probe-watch.py. Run the latter three with api/.venv/bin/python -B. The sampler and watch script contain the observed gateway port and process IDs; resolve the current runtime before rerunning after a restart.

Supporting JSON and JSONL files retain the exact measurements. Full source gates were already passed at this unchanged commit according to the incoming handoff; they were not repeated for read-only runtime observation.

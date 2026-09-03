# Recovered agent conversations

Recovered 61 visible messages from all 10 launched agent runs using TM conversation. Every run was read from the beginning through its last available page. All returned message text is complete; no older or newer pages remain and no history rotation was reported.

This preserves user prompts and assistant commentary/final responses. It does not recover raw tool calls, tool results, or internal reasoning. Complete conversation retrieval does not mean the agents completed their assigned audits. Statements below remain agent-reported findings, pending final reconciliation.

## Audit conversations

| Agent | Messages | Saved conversation |
| --- | ---: | --- |
| catalog | 7 | [catalog.md](catalog.md) |
| autopilot | 7 | [autopilot.md](autopilot.md) |
| authority | 6 | [authority.md](authority.md) |
| orchestration | 7 | [orchestration.md](orchestration.md) |
| runtime | 6 | [runtime.md](runtime.md) |
| portfolio | 4 | [portfolio.md](portfolio.md) |
| reconciliation-check | 6 | [reconciliation-check.md](reconciliation-check.md) |
| consolidation | 5 | [consolidation.md](consolidation.md) |

## Incident investigations

| Agent | Messages | Saved conversation |
| --- | ---: | --- |
| stalled-investigation | 5 | [stalled-investigation.md](stalled-investigation.md) |
| latency-investigation | 8 | [latency-investigation.md](latency-investigation.md) |

The incident conversations include causal claims subsequently corrected. Use CX entry `01a06fee-b5be-7ee3-84f3-97b545546874` for the corrected CPU handoff: the busy Docker workload was TM Postgres, and Stuart reported CPU normalized after closing agents. Neither an unrelated-VM explanation nor a proven desktop cleanup leak should be inferred from these older transcripts.

## Useful audit findings recovered

- [Orchestration](orchestration.md): #573 contains partially shipped work from #622/#629, while queued-delivery binding defects remain. The agent prioritized #574/#573, then #624. Its final report was not saved.
- [Authority](authority.md): requested-policy metadata exists, but effective authority still follows raw launch grants. The agent identified duplicated transport-setting relocation scope between #599 and #600.
- [Reconciliation check](reconciliation-check.md): the agent recorded additional caveats about #629 coverage and the unproven account-aware-catalog premise. These survive even though its report files were never created.
- [Runtime](runtime.md): the agent recorded separate home-persistence and log-destination gaps, the login remediation boundary, and claimed focused checks passed. Raw test output is outside this retrieval surface.
- [Autopilot](autopilot.md): the agent distinguished current implementation from open PRs #463/#464 and reported all 26 embedded reference cells were first-turn, without envelope references. That observation alone does not establish a new certification run as a blocking dependency.
- [Consolidation](consolidation.md): one high-confidence proposal, merge #459 into #460. Other apparent duplicates were judged distinct outcomes or tracking parents. Its separate saved report contains proposed amendments.

## Evidence files

Each conversation has a matching `.pages.json` preserving raw TM page envelopes and `.messages.json` preserving reconstructed messages and completeness metadata. `manifest.json` maps every name to its full run ID. Run `python3 verify-recovery.py` to repeat the saved-artifact checks.


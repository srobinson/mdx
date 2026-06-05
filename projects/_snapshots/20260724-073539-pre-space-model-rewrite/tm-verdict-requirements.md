# Provider-rejection verdict surface — requirements

New branch `feat/launch-verdict-surface` off merged main (3ae57012, which landed the launch contract #311). Own PR.

## Goal
When a managed launch's selected model is rejected by the provider, surface that verdict to the caller. Today the launch reports success even when the provider rejected the model. This is a **requirement of launch**, both use cases below.

## Governing contract
`LAUNCH-CONTRACT.md` is the authority. Relevant:
- Line 178-179: "Authentication and provider access observations never authorize or block launch. **Provider rejection is surfaced from the live run.**" — this feature implements that sentence.
- `LaunchResult.PromptReceipt` = `submitted` | `unknown` | `failed` (348-352). `failed` = native submission failed.
- Surface-don't-gatekeep stays: we STILL spawn; we report the verdict, never pre-block. (Decision cx 019f7a4b.)

## The two surfaces (both required)
1. **Prompted launch** (request has `first_prompt`): the provider rejection lands on that first turn, within the bounded delivery-proof deadline. Surface as `LaunchResult.PromptReceipt = failed` with a reason/code, in the synchronous launch result.
2. **Interactive launch** (no `first_prompt`): the rejection only happens on the first *user* turn, AFTER `launch()` returned. The synchronous receipt cannot carry it. Surface it as a **post-launch run-state signal** the agent/director reads from the live run (run status / control-plane run read model / run event stream — scout determines the right seam).

## Per-harness source (already captured — READ it, do not re-capture)
- **claude** → transcript error frame: `error: "model_not_found"`, `isApiErrorMessage: true`, `apiErrorStatus` (404). Durable in the transcript.
- **codex** → **WIRE** `transport.json` server error frame: `{"type":"error","status":400,"error":{"type":"invalid_request_error","message":"The '<model>' model is not supported ..."}}`. LOAD-BEARING: codex MUST be read from the WIRE, NOT its transcript — the codex rollout records a FALSE `task_complete` on rejection (proven: run 87ca05c9 transport.json vs rollout 019f799c). Decision cx 019f7a4b.

## Scout deliverables (Phase 1, before building)
Write to `~/.mdx/projects/tm-verdict-scout.md`, reply one line (counts + the key reuse verdict).
1. **Does the existing PromptReceipt/delivery-proof path already resolve `failed` on a provider rejection**, or only prove submission? Trace `launch_service._resolve_first_prompt` / `delivery_proof.py` / `drift_observer`. Cite file+symbol. If it already detects the error frame, the prompted surface may be near-free.
2. **Where the wire/transcript error frame is detected today** (drift_emitter? the wire/transcript adapters? the tailer?) — reuse that detection, don't write a second parser. Confirm the codex 400 is reachable from the capture the launch path can see, and claude's transcript error likewise.
3. **The interactive run-state seam**: where does a run's post-launch provider-rejection verdict live or belong — run status, the control-plane run read model (controlplane read_store / run views), the run event stream? What does an agent/director query to learn "my run's model was rejected"? Cite the existing run-read surfaces.
4. **Contract/doc grounding**: reconcile with LAUNCH-CONTRACT.md (PromptReceipt, LaunchResult, any run-observation contract) + RUNTIME-SURFACING / CONTROLPLANE docs. Flag any doc that must be extended.
5. **Reuse map** (capability → owner file+symbol or none-found+searches), **slice plan** (PR-sized, both surfaces), **failing-test design** (fail-before/pass-after) for: prompted claude rejection → PromptReceipt failed; prompted codex rejection → PromptReceipt failed FROM THE WIRE; interactive rejection → run-state signal reflects it; surface-don't-gatekeep preserved (run still spawns).
6. **Biggest blast-radius risk.**

Apply a reuse/dedup/dead-code lens throughout (do not reinvent error detection that exists). After the scout I review the plan and surface open decisions before you build.

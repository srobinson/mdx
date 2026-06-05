# Activity product plane type standard position

## Recommendation

Use a split standard.

Opaque ids should be branded strings at the product boundary: `RunId`, `WorkspaceId`, `EventId`, `RecordId`. These values are not meaningful strings inside the domain, and mixing them is a real class of bug. Branding is worth the tiny ceremony because every future context will pass the same ids through ports, facts, projections, and server surfaces. Keep constructors at IO boundaries, not inside the pure domain.

Known but extensible sets should use open enums. `Harness` should be `KnownHarness | (string & {})`, with `knownHarnesses = ["claude", "codex"] as const` exported from the harness bundle registry, not from Activity. Adding a harness then means adding a bundle and conformance fixture, with zero Activity domain edits. The domain should rename `RuntimeKind` and `runtime` to `Harness` and `harness`, then treat it as metadata only. No switch on harness belongs in `runActivityMachine`.

Sequence cursor keys are not ids. Keep them as a closed local vocabulary, for example `runActivityEventStreams = ["lifecycle", "record"] as const`, because Activity owns those two streams.

## Magic strings and constants

Single source strings that cross module, package, or plane boundaries. Allow bare literals only when they are local syntax or type discriminants that TypeScript must see directly.

Status names are Activity domain vocabulary. `activityStatuses` in `packages/activity/src/domain/runActivityMachine.ts` is the right source. XState state keys may stay as literals, but exported consumers and tests should derive from that tuple.

Harness ids must come from the harness registry. The current `RuntimeKind = "claude" | "codex"`, `RunStartedEvent.runtime`, `RunActivityContext.runtime`, and the test fixture value `runtime: "claude"` should move to `Harness` and import known harness values only where fixtures need them.

Activity event discriminators such as `"run.started"`, `"record.tool_use"`, and `"usage.recorded"` are the machine protocol. The interface discriminants can stay literal, but repeated operational checks such as `eventStream()` comparing `"run.started"` and `"run.exited"` should use an exported `runActivityEventTypes` constant object from the Activity domain module. Runtime adapters should import those constants when producing events.

Port DTO kinds in `ActivityRecordKind` and `RunLifecycleEventType` should get exported const tuples in `ports.ts`, because adapters and tests will share them.

Cross plane database strings must not be repeated from memory. `tm_events` and `run_lifecycle` should live in a small session store contract artifact, with Python producer and TS consumer importing or generating named constants from it. Activity should consume those constants through its adapter layer, never from the domain machine.

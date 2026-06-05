---
title: Issue 35 architecture scout for the launch payload and capture terms
type: projects
tags:
  - littleorgans
  - issue-35
  - launch-payload
  - transport
  - session
  - runtime
  - architecture
summary: Read-only scout of the current launch path and architecture docs so Issue 35 can lock one optional envelope, its decoder, absent-field behavior, and CLI vocabulary.
status: active
project: littleorgans
related:
  - littleorgans-transport-capture--synthesis
  - littleorgans-schedule-matters-spec
  - helioy-product-direction
confidence: high
created: 2026-08-16
updated: 2026-08-16
---

# Issue 35 architecture scout

Read-only scout of `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans` at `main` (`5ace7db89dac7fe875edd626bf6222202f70b340`, 2026-08-16). No repository files were written.

Issue 35 asks the architecture documents to lock one launch attachment shape so Issue 41 can add a typed field without another protocol change. Issue 35 itself forbids launch code, a Transport crate, provider parsing, and Schedule types.

## Components found

| Name | Path | Role today |
| --- | --- | --- |
| Session `SpawnRequest` | `internal/session/core/src/proto/spawn.rs` | Operator and Session RPC launch intent. Concrete Runtime fields plus role, workspace, namespace, labels, force. No Transport field. |
| `SpawnLaunch` | `internal/session/driver/src/driver.rs` | Session to Runtime execution request. Same concrete process fields. `target` is still `String`. |
| Runtime `SpawnRequest` | `crates/lilo-rm-core/src/types/spawn.rs` | Runtime launch contract and the value stored in `session_spawn_intents.spawn_request_json`. Includes `SessionId`. No Transport field. |
| `runtime_spawn_request` | `internal/session/driver/src/conv.rs` | Copies `SpawnLaunch` fields into Runtime `SpawnRequest`. No extra slot to forward. |
| `RuntimePort::spawn` | `internal/session/driver/src/port.rs` | In-process and socket adapters take `session_id: &str` plus `SpawnLaunch`. |
| `InProcessRuntime::spawn` | `internal/session/driver/src/in_process.rs` | Rebuilds Runtime `SpawnRequest` and calls `RuntimeService::spawn`. |
| `DaemonState::spawn` | `internal/session/daemon/src/handler/spawn.rs` | Mints `SessionId`, builds `SpawnLaunch`, persists Runtime `SpawnRequest`, then calls the port. |
| `PendingSpawnIntent` / `SessionSpawnIntent` | `internal/session/store/src/postgres/spawn_intents.rs` | Persist and reload Runtime `SpawnRequest` as JSON text. Status `pending`, `resolved`, or `aborted`. |
| `spawn_domain` | `internal/runtime/daemon/src/api.rs` | Turns Runtime `SpawnRequest` into `LaunchSpec`, then host or Docker `prepare_launch`. |
| `LaunchSpec` | `crates/lilo-rm-core/src/launcher.rs` | Process argv, env, cwd, optional `ShellResume`. This is what the shim fetches. |
| `LaunchEnv` / `upsert_launch_env` | `crates/lilo-rm-core/src/launcher.rs` | Existing process injection type. Session already upserts `LILO_AGENT_*` here. |
| Runtime `CaptureRequest` / `PaneSnapshot` | `crates/lilo-rm-core/src/capture.rs` | Tmux pane snapshot. This is `lilo capture` and `lilo runtime capture`. |
| Session `CaptureRequest` | `internal/session/core/src/proto/session.rs` | Session polish wrapper around the same pane snapshot. |
| `RUNTIME_PROTOCOL_VERSION` | `crates/lilo-rm-core/src/version.rs` | String `"0.8"` plus capability flags. Runtime wire version, not a Transport envelope version. |
| `SessionId` | `crates/lilo-common/src/id.rs` | Join key across Session, Runtime, and future Transport. |

No `LaunchAttachment`, capture lease type, Transport port, `lilo transport` command, or `internal/transport` tree exists at this commit.

## Flow

### Current session-backed launch

1. `lilo run` or `lilo create session` sends Session `SpawnRequest` over `LilodRpc::Session`.
2. `DaemonState::spawn` mints `SessionId::new()` (UUIDv4).
3. `normalize_spawn_request` and `resolve_agent_config` fill directory, namespace, and optional agent env.
4. `spawn_launch` builds `SpawnLaunch`, merging caller env and `LILO_AGENT_SESSION_ID`, `LILO_AGENT_ROLE`, `LILO_AGENT_WORKSPACE`.
5. `runtime_spawn_request` builds Runtime `SpawnRequest`.
6. Transaction A writes Identity audit, `session_spawn_intents` (`spawn_request_json` plus `session_draft_json`), and Runtime `Forking`.
7. `RuntimePort::spawn` starts the shim. `spawn_domain` builds `LaunchSpec` from the concrete Runtime fields only.
8. Transaction B inserts the Session row as `Running`, stores Runtime `Running`, and resolves the intent.
9. Startup `reconcile_pending_spawn_intent` reloads the stored Runtime `SpawnRequest` but does not call `spawn` again. If the lifecycle is `Running`, it completes Transaction B. Otherwise it aborts the intent.

Raw `lilo runtime spawn` uses `RuntimeRpc::Spawn` on the same `RuntimeService`. It writes Runtime lifecycle only. No Session row, no intent row, no place for Session to attach Transport state.

### Target launch in the governing docs

`docs/architecture/system.md` heading **Session Backed Launch**:

1. Session mints `SessionId` and persists occupant intent.
2. Identity authorizes.
3. Session asks Transport to prepare capture for that `SessionId`.
4. Transport returns an opaque capture lease and launch additions.
5. Session submits the occupant and opaque launch payload to Schedule.
6. Schedule places and asks Runtime to execute.
7. Runtime starts the shim without interpreting capture policy.
8. Transport observes the provider wire.
9. Session exposes the joined read model to Canvas.

The v0.8 path skips Schedule. `system.md` heading **First Architecture Proof** says the current Session to Runtime route may implement the proof if the attachment stays opaque so Schedule can later forward the same value.

`docs/architecture/transport.md` heading **Launch Boundary** repeats the two-noun return (lease and launch additions) and says Session includes them in the launch payload. Schedule treats the entire occupant launch payload as opaque. Runtime applies the launch specification.

Issue 35 and review **Proposal 3** collapse those two nouns into one optional versioned envelope on the execution request. Issue 41 is the typed implementation of that field. Issue 37 still owns first-proof product choices (required capture, blocking versus passive, edit policy).

## Files read

Governing and instructions:

- `docs/architecture/system.md`
- `docs/architecture/session.md`
- `docs/architecture/runtime.md`
- `docs/architecture/schedule.md`
- `docs/architecture/transport.md`
- `docs/architecture/canvas.md`
- `docs/architecture/review/README.md`
- `docs/architecture/review/component-flow.md`
- `docs/architecture/review/data-boundaries.md`
- `docs/architecture/review/data-boundaries-findings.md`
- `docs/architecture/review/doc-code-drift.md`
- `docs/architecture/review/cliproxyapi-lessons-for-first-transport-proof.md`
- `NOTES/v1-v2-strategy.md`
- `CLAUDE.md` / `Agents.md` (same Transport and command-surface text)
- `~/.mdx/_schema.md`

Issue and program:

- GitHub Issue 35
- GitHub Issue 41 (blocked by 35)
- GitHub Issue 42 (parent tracker)

Current launch and capture code:

- `internal/session/core/src/proto/spawn.rs`
- `internal/session/driver/src/driver.rs`
- `internal/session/driver/src/port.rs`
- `internal/session/driver/src/conv.rs`
- `internal/session/driver/src/in_process.rs`
- `internal/session/daemon/src/handler/spawn.rs`
- `internal/session/store/src/postgres/spawn_intents.rs`
- `crates/lilo-rm-core/src/types/spawn.rs`
- `crates/lilo-rm-core/src/launcher.rs`
- `crates/lilo-rm-core/src/capture.rs`
- `crates/lilo-rm-core/src/version.rs`
- `internal/runtime/daemon/src/api.rs`
- `internal/session/app/src/cli/capture.rs`
- `internal/session/app/src/cli/cli_def.rs`
- `crates/lilo/src/cli.rs`
- `crates/lilo/src/cli/generated_help.rs`
- `internal/runtime/app/src/cli.rs`

Prior study, not governing for this lock:

- `~/.mdx/projects/littleorgans-transport-capture--synthesis.md` (2026-07-31)
- `~/.mdx/projects/littleorgans-transport-capture-boundary-map--brainstorm.md`

How explorer prompt shape from `~/.grok` / pstack `how/references/explorer-prompt.md`.

## Boundaries

| Boundary | In | Out |
| --- | --- | --- |
| Operator to Session | Session `SpawnRequest` (runtime, role, workspace, target, isolation, env, mounts, labels, force) | Session record, polish verbs including pane `lilo capture` |
| Session to Runtime today | `SpawnLaunch` then Runtime `SpawnRequest` | `Lifecycle`, pane address, log paths |
| Session intent store | Runtime `SpawnRequest` JSON in `spawn_request_json` | Reloaded `SessionSpawnIntent` for reconcile |
| Runtime to process | `LaunchSpec` (argv, env, cwd, shell resume) | Shim ready and exit evidence |
| Session to Transport (docs only) | typed `SessionId` | opaque lease and launch additions, later one envelope |
| Session to Schedule (docs only) | occupant plus opaque launch payload | placement evidence |
| Schedule to Runtime (docs only) | same opaque occupant launch payload | execution at the selected target |
| Canvas to `lilod` (docs only) | Session and Transport read and command models | no storage reads |
| Pane snapshot | `lilo capture` / `lilo runtime capture` | tmux `PaneSnapshot`, never a Transport record |

Ownership already written down:

- Session attaches and persists intent. It does not parse provider payloads (`system.md`, `session.md`).
- Transport owns decoding of provider traffic and of the attachment contents (`transport.md`).
- Runtime applies process launch fields and must not interpret capture policy (`runtime.md`, `system.md`).
- Schedule, when activated, forwards the occupant launch payload without reading provider, overlay, or harness semantics (`schedule.md` headings **Thin Topology Intent** and **Transport Boundary**).
- Canvas never owns the envelope (`canvas.md`).

Dependency direction that #35 must not invert: Runtime does not depend on Session crates. Session already imports Runtime launch types (`IsolationPolicy`, `LaunchEnv`, `MountSpec`, `ShellResume`). A shared envelope type can live in `lilo-common` (already the home of `SessionId`) without a Transport crate.

## Non-obvious things

**Two layers share the words "launch payload".** `schedule.md` **Thin Topology Intent** uses opaque launch payload for the whole occupant spec: Runtime fields, agent config references, resume material, and a Transport lease. Issue 35 and review **Proposal 3** use the same phrase for one new optional field on the existing spawn types. If the docs keep one name for both, #41 will not know whether to wrap `SpawnRequest` or add a field.

**Transport's return is two nouns; the execution field should be one value.** `system.md` step 4 and `transport.md` **Launch Boundary** say "opaque capture lease and launch additions." Review **Proposal 3** and Issue 35 recommend one envelope. Two new fields would teach Session, Runtime, and later Schedule the Transport split (lease versus additions) before Transport exists.

**Process injection already has a type.** `LaunchEnv` and `LaunchSpec.env` are how Session injects `LILO_AGENT_*` and how launchers will later inject a base URL or proxy. Runtime applies those fields today. Encoding env inside an opaque blob would force Runtime or Session to decode Transport contents. Merging Transport-supplied `Vec<LaunchEnv>` into the existing env field, when Transport prepare exists, needs no second spawn field.

**`spawn_request_json` stores the Runtime request, not the Session RPC request.** Old pending rows are Runtime `SpawnRequest` JSON. #41's "old pending intent JSON still deserializes" applies there. Reconcile does not re-spawn, so the field is a durable copy of what was launched, plus a deserialize contract, not a replay of Transport prepare.

**Neither spawn struct uses `deny_unknown_fields`.** New optional fields with `#[serde(default, skip_serializing_if = "Option::is_none")]` match `image` and `shell_resume`. Old JSON becomes `None`. New JSON with the field is ignored by older readers. Adding `deny_unknown_fields` later would break that.

**`CLAUDE.md` states the attach as current.** The paragraph "Session prepares capture ... and attaches an opaque capture lease to the launch payload. The current v0.8 path passes that payload directly to Runtime" has no code behind it. `doc-code-drift.md` already flags this. The governing lock should speak in target language until #41 lands.

**Capture is already three English words.** Runtime pane snapshot (`lilo capture`, help: "Capture the current terminal output of one session"), documented Transport wire capture, and the undocumented capture lease. Session and Runtime each export a `CaptureRequest`. Identity authorizes session capture as `Read` and runtime capture as `Logs` (`data-boundaries-findings.md` item 15).

**The July 2026 Transport capture synthesis is a prior study, not this lock.** `~/.mdx/projects/littleorgans-transport-capture--synthesis.md` treats a one-use lease as something that carries child launch material into `LaunchSpec`, wants mandatory capture, and lists `lilo transport list|show|export`. That study also kept v1 mutation off. The August architecture first proof includes an authorized tool-description edit. Issue 37 owns those product choices. #35 must not import mandatory capture, MITM, `ANTHROPIC_BASE_URL`, or observation-only policy.

**Operator Session `SpawnRequest` is the wrong attach point.** Transport prepare happens after the operator request arrives. Putting the envelope on the inbound RPC would let a client inject a fake lease. The execution types are `SpawnLaunch` and Runtime `SpawnRequest`. That reading matches Issue 41 "Session and Runtime launch requests" without growing a CLI flag.

**Raw `lilo runtime spawn` stays envelope-absent.** `system.md` limits the first Transport slice to session-backed `lilo run`. Diagnostic spawn has no Session prepare step.

## Open questions

These stay open after #35. They are not required to lock the envelope.

1. How the child process first sees the envelope (reserved `LILO_*` env, file, or a later Transport helper). New env names need `lilo-paths::env` and `scripts/check-env.sh`. Do not invent a name in this issue.
2. Whether Transport prepare also returns ordinary `Vec<LaunchEnv>` for Session to merge. That is a Transport port shape, not a second spawn field.
3. Required versus optional capture, blocking versus passive hold, and failure posture. `system.md` **Product Decisions Still Open** items 2 and 4; Issue 37.
4. Transport implementation language, process topology, and table ownership. `transport.md` leaves these open. `CLAUDE.md` repeats that.
5. Type name bikeshed (`LaunchAttachment` versus `OpaqueLaunchEnvelope`). The field meaning matters more than the ident.
6. Whether published `lilo-rm-core` should grow a capability flag when the field exists. `RuntimeCapability` is the existing additive gate. Not needed to write the docs.
7. Postgres owner of Transport records and the Session joined transcript read model. `transport.md` **Capture Record**; review component-flow open question 7.

## Least speculative lock

Grounded in the current spawn types, serde defaults, `spawn_request_json`, and the August architecture. These five answers are what Issue 35 should record.

### 1. One envelope, not two spawn fields

Use one optional attachment on the execution path.

Separate lease and additions fields would leak Transport's internal split into Session, Runtime, and later Schedule. No Transport implementation exists to justify that split. Review **Proposal 3** already asks for one domain-neutral payload. Issue 35's own recommendation matches.

Keep `LaunchEnv` as the only process-visible injection type. When Transport prepare exists, Session may merge already-typed env into the existing field. That merge is not a second envelope.

### 2. Kind, version, and opaque value

Carry one optional struct:

- `kind`: string, Transport-owned. No enum in Session or Runtime. An enum would freeze Transport kinds in the wrong crate.
- `version`: `u32`, Transport-owned per kind, first written value `1`. Do not reuse `RUNTIME_PROTOCOL_VERSION` (`"0.8"`). That string versions the Runtime wire.
- `value`: JSON (`serde_json::Value`) with no documented keys at the Session, Schedule, or Runtime layer. `spawn_request_json` is already JSON. Bytes or base64 would add an encoding that no spawn field uses.

Serde shape follows `image` and `shell_resume`: `#[serde(default, skip_serializing_if = "Option::is_none")]`.

Recommended field name: `launch_attachment`. Avoid `capture` (pane snapshot collision). Avoid `launch_payload` (Schedule occupant-spec collision). Avoid `capture_lease` (too narrow once additions live inside `value`).

Recommended type home for #41: `lilo-common`, beside `SessionId`. `lilo-rm-core` already depends on it. `SpawnLaunch` and Runtime `SpawnRequest` both share the type. Do not put provider fields or Transport kinds in `lilo-rm-core`.

Do not add the field to inbound Session `SpawnRequest` until a caller other than the Session daemon must supply it.

### 3. Decoder owner

Transport decodes `kind`, `version`, and `value`.

Session may test presence (`Some` versus `None`) after it asked Transport to prepare. Session, Schedule, and Runtime copy the struct as a unit. They do not switch on `kind` or read `value`. Unknown-kind policy belongs to Transport when that context exists.

### 4. Absent field

Missing JSON key means no Transport attachment. Launch behavior stays what it is at this commit.

Old pending `spawn_request_json` deserializes as `None`. New writers omit the key when the value is `None`. Raw `lilo runtime spawn` stays absent. Do not add `deny_unknown_fields` on either `SpawnRequest`.

Required-capture behavior is out of scope for #35 and #41.

### 5. Command vocabulary

`lilo capture` remains the session-backed tmux pane snapshot. Help already says "Capture the current terminal output of one session" (`crates/lilo/src/cli/generated_help.rs` `CAPTURE_LONG_ABOUT`). `lilo runtime capture` is the diagnostic pane snapshot (`internal/runtime/app/src/cli.rs` `CAPTURE_ABOUT`).

Provider traffic verbs belong under a future `lilo transport ...` namespace once a vertical slice proves real verbs (`CLAUDE.md` **Command surface and substrate-boundary rule**; Issue 42 program constraint). Transport does not own a spawn command. Do not add that namespace in #35 or #41.

Locked prose terms for the architecture docs:

| Term | Meaning |
| --- | --- |
| Pane snapshot | `lilo capture` / `lilo runtime capture` |
| Provider capture or wire capture | Transport observation of harness to provider traffic |
| Launch attachment | The optional kind, version, value field |
| Occupant launch spec | Concrete Runtime launch fields plus optional launch attachment. This is what Schedule later forwards as a whole |
| Capture lease | Transport-internal token inside `value`, not a Session or Runtime field name |

## Reuse map

Issue 35's acceptance is a documentation lock. Reuse the existing headings. Do not add an architecture file, a crate, or a command.

| Document | Heading to extend | What to write |
| --- | --- | --- |
| `docs/architecture/system.md` | **Schedule receives an opaque launch payload** and **Session Backed Launch** steps 4 to 5 | Distinguish occupant launch spec from launch attachment. Step 4 becomes: Transport returns one launch attachment. Step 5: Session attaches it to the occupant launch spec. |
| `docs/architecture/system.md` | **First Architecture Proof** | Keep the opaque-so-Schedule-can-forward sentence. Name the attachment field, not a second payload type. |
| `docs/architecture/transport.md` | **Launch Boundary** | Replace "lease and launch additions" with one attachment. State Transport owns kind, version, and value. Session attaches. Runtime and Schedule do not decode. |
| `docs/architecture/schedule.md` | **Thin Topology Intent** and **Transport Boundary** | Occupant launch spec stays Schedule-opaque as a whole. Inside it, the only Transport-shaped field is the optional attachment. |
| `docs/architecture/session.md` | **Design intent** and **Stable flows** | Session prepares Transport, attaches the optional field, persists it through existing `spawn_request_json`. Operator RPC does not accept the field. |
| `docs/architecture/runtime.md` | **Design intent** and **Contracts** | Runtime `SpawnRequest` may carry `launch_attachment`. Runtime applies concrete process fields and `LaunchSpec` only. |
| `CLAUDE.md` / `Agents.md` | Transport paragraph and **Command surface** | Mark attach as target until #41 lands. Keep `lilo capture` as pane snapshot. Keep future `lilo transport ...`. |
| `docs/architecture/review/README.md` | **Proposal 3** | After the lock, mark the proposal accepted and point at the architecture headings. The review page stays a discussion record. |

Do not edit `docs/architecture/canvas.md`. Canvas consumes read models and does not carry the envelope.

Do not edit `NOTES/v1-v2-strategy.md` for this lock. That note maps v1 contracts to a later cluster. The envelope is a v1 Session to Runtime field.

Do not copy July synthesis mandatory-capture or observation-only rules into these headings.

Issue 41 then adds the field on `SpawnLaunch` and Runtime `SpawnRequest`, threads it through `runtime_spawn_request`, `InProcessRuntime`, `RtmdDriver`, and intent JSON, and keeps absent equal to today's launch.

## Quality map

| Signal | Evidence | Remedy in the doc change |
| --- | --- | --- |
| Same word, three meanings | `lilo capture` pane snapshot; Transport wire capture; capture lease | Use the term table above in every touched heading. |
| Same phrase, two layers | Schedule occupant launch payload versus Issue 35 envelope | Occupant launch spec versus launch attachment. |
| Present tense without code | `CLAUDE.md` attach paragraph; `doc-code-drift.md` finding 2 | Target language until #41. |
| Two-noun return versus one field | `system.md` step 4; `transport.md` **Launch Boundary**; Proposal 3 | One attachment in all three. |
| Dual `SpawnRequest` | Session RPC versus Runtime contract; `conv.rs` translator | Keep both. Attach on the execution side only. |
| Dual `CaptureRequest` | `lilo-session-core` and `lilo-rm-core` | Leave the types. Docs must say pane snapshot. |
| Generated help drift | Unified `CAPTURE_ABOUT` "Capture session output" versus session `SESSION_CAPTURE_ABOUT` "tmux pane scrollback" versus runtime "pane snapshot" | Architecture lock does not regenerate help. Later copy can say pane snapshot everywhere. |
| File size | Architecture docs 110 to 259 lines. `spawn.rs` 439, `conv.rs` 387, `types/spawn.rs` 460. All under the 700 line cap. | Doc edits stay in existing files. #41 must not grow `spawn.rs` past the cap without a split. |
| Persistence reuse | `spawn_request_json` already serializes Runtime `SpawnRequest` | No new table. No Transport store. |
| Version collision | `RUNTIME_PROTOCOL_VERSION = "0.8"` | Attachment version is a separate `u32`. |
| Prior study drift | July synthesis versus August first proof (edit and forward) | Cite the study as history. Do not merge it into the lock. |
| Hygiene of the lock itself | Duplication across five architecture files | One canonical paragraph in `system.md`, short pointers in the context docs. Do not invent a sixth architecture page. |

## Verification

```text
git status --short   # empty in the repository
git rev-parse HEAD   # 5ace7db89dac7fe875edd626bf6222202f70b340
```

Claims above were checked against the listed architecture headings and the named types at that commit. No `just` gate was run. Issue 35 is a documentation decision; the repository tree was left pristine.

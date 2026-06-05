# littleorgans Transport Capture Synthesis: Codex Evidence Review

Status: COMPLETE

Updated: 2026-07-31

Worker Status: No nested workers. This was an independent read only review.

## Findings

No P0 finding was identified. Eight P1 corrections are required before this
synthesis can govern implementation or support an enterprise claim.

### P1. The release gate permits an advertised runtime to escape the mandatory capture invariant

The synthesis promises that every session backed run is captured
(`littleorgans-transport-capture--synthesis.md:9,96`) and calls this a locked
product invariant. Its minimum v1 and implementation sequence qualify only
Claude, while Codex opens later (`:78,83,340,346`).

The pinned littleorgans source advertises both runtimes today:

- `internal/runtime/launchers/src/lib.rs::dispatch` accepts Claude and Codex.
- `internal/runtime/launchers/src/lib.rs::registered_launchers` returns both.
- `crates/lilo/src/cli/generated_help.rs::RUN_EXAMPLES` and
  `CREATE_EXAMPLES` present Codex as a normal session runtime.

A global `RuntimeCapability::WireCapture` flag does not close this hole. A
daemon can advertise capture while lacking an adapter for one registered
runtime.

Required correction:

1. Lock one release rule: every registered model runtime has a qualified
   adapter, or that runtime is refused before any agent process exists.
2. Add a conformance gate that iterates `registered_launchers()` and requires a
   capture adapter plus an end to end refusal or capture test for each entry.
3. Make doctor and protocol capability reporting runtime specific.
4. State whether Codex is removed from the generated v1 command surface or is a
   v1 release requirement. “Codex later” cannot coexist with the current
   universal invariant.

### P1. The evidence vocabulary and acceptance denominator overclaim byte fidelity

The synthesis says the product records exactly what the agent sent and received
(`:9`), calls the v1 path “passthrough-perfect by construction” (`:75`), names
exact wire bytes as the root of trust (`:224-237`), and promotes the fixture
corpus as an exact wire round trip (`:295`).

The pinned experimental source proves a narrower mechanism:

- `api/src/transport_matters/exchange_recorder/artifacts.py::request_raw_bytes`
  prefers `get_text()` and UTF-8 re-encoding. Its own comment says it prefers a
  content decoded body.
- `extract_response` also calls `get_text()` and re-encodes the result.
- `api/src/transport_matters/session/test_wire_normalization.py::
  test_fixture_request_round_trips_exactly` compares reconstructed messages,
  system parts, and tool definitions with parsed request structures. It does
  not compare HTTP octets.
- Fixture `meta.json` contains only a request body byte count.
- The accepted test input explicitly records the missing test:
  `littleorgans-transport-capture-test-evidence--brainstorm.md:70` says there is
  no parse and serialize round trip against real captured provider wire bytes.

An application layer reverse proxy also terminates and reissues HTTP. HTTP
version, request line, header serialization, compression, chunk framing, and
TLS records can change while model payload semantics remain correct. The
write-time removal of credential values further means the persisted record
cannot be a verbatim HTTP request.

Required correction:

1. Replace “wire bytes” with exact artifact names such as
   `client_body_bytes`, `decoded_provider_body_bytes`,
   `response_stream_chunk_bytes`, and normalized headers.
2. Reserve “wire octets” for a capture point that observes those octets.
3. Split the acceptance suite into relay fidelity, persisted body fidelity,
   structured projection round trip, and intentional secret omission.
4. Add an independent client and upstream byte oracle. The existing fixture
   corpus can prove structural reconstruction and a body byte budget. It cannot
   prove full wire equality.
5. Reclassify E4 and the “passthrough-perfect” statement until the independent
   oracle passes.

### P1. The authority model makes control state both authoritative and replayable

E5 and section 8 say tier 1 files are the sole authority and every Postgres row
is a replayable projection (`:224,373`). Other sections depend on Postgres for
facts that cannot be reconstructed from capture content:

- authorization audit and the composite spawn intent (`:256`);
- capture readiness and session state (`:258-260,273`);
- retention holds, deletion intent, and tombstones (`:233,276-278,324`);
- audit survival after content deletion (`:278`);
- access audit for raw reads and exports (`:250`).

The document also calls the index row the bootstrap arbiter for deletion
(`:233`). A replayable cache cannot safely arbitrate whether bytes stay denied
after a crash. Dropping and rebuilding all capture rows could resurrect
tombstoned content or erase a hold.

Required correction:

1. Define two authorities. Immutable content bytes can be filesystem authority.
   Authorization, audit, lifecycle, hold, and deletion control records require
   a transactional control ledger.
2. Identify only derived search and read model rows as rebuildable.
3. Specify recovery precedence for every file and ledger disagreement,
   including a missing row, missing directory, staged delete, hold, and
   incomplete audit outcome.
4. Revise E5 from an accepted blanket rule. Its content half is supported. Its
   control half remains unresolved until the crash matrix proves it.

### P1. The enterprise claim describes agent behavior that Transport cannot evidence

The synthesis asks “what did my agent actually do?” (`:35`) and says every
agent action on the host is evidenced (`:63,313`). It later narrows coverage to
model inference (`:202`) and explicitly rejects capture of agent shell commands
(`:422`). Provider exchanges cannot prove filesystem writes, shell effects,
network tool calls, or other runtime side effects.

The launch claim is also ahead of the state machine. Section 1 says capture
upgrades launch truth to “the agent reached the provider and got a response”
(`:37`). The mandatory sequence commits Session Running after Runtime and
Transport readiness, before the first provider request or response
(`:254-262`).

Required correction:

1. State the product claim as evidence of model inference exchanges.
2. Describe Runtime lifecycle, tool effects, and model traffic as distinct
   evidence classes with explicit coverage.
3. Add a first exchange receipt or equivalent state. Running means process and
   capture readiness. A positive provider response is later evidence.
4. Remove “every agent action” and “whether a human touched it” unless a
   separate, authenticated provenance source proves those facts.

### P1. Credential transit, the capture listener, and audited raw access lack one coherent threat model

Section 9 says Transport receives at most a minimum lifetime handle and never
spends credentials (`:243`). The next paragraph acknowledges that every
intercepted request carries live credentials (`:245`). A redirect proxy sees and
forwards the credential in memory. Its safe boundary is transient processing
without ownership, reuse, refresh, or persistence.

The same section says capture adds no listener door (`:248`), while the launch
sequence requires a per session loopback listener (`:257-259`). The listener is
a new data plane door even if operator RPC remains on the existing socket.
Readiness proves that it is bound. The synthesis does not bind each accepted
connection or request to the launched process.

The enterprise claim also requires audited raw reads, while v1 exposes
`lilo transport paths` and stores readable raw content under the operator owned
`~/.lilo` tree (`:80,250,283`). Direct same UID file reads bypass Identity and
the access audit.

Required correction:

1. Define Transport as a transient processor of provider credentials. State the
   exact prohibited credential operations and the write boundary that removes
   secrets.
2. Threat model the data plane listener separately from operator RPC. Add
   process or session binding, host and path validation, connection limits,
   request limits, deadlines, and hostile local sibling tests.
3. Replace “no new listener doors” with “no new management listener.”
4. Scope audited access honestly for v1. For an enterprise guarantee, raw
   content must be opaque outside the authorized service path, or direct file
   access must be an explicit unaudited boundary. `paths` cannot silently bypass
   the claim.

### P1. The default interception decision omits a confirmed product regression

Anthropic currently documents both sides of the redirect decision. Setting only
`ANTHROPIC_BASE_URL` preserves a saved subscription login, which supports the
proposed X1 experiment. Anthropic also documents that Remote Control is disabled
when that variable points at any host other than `api.anthropic.com`, beginning
with Claude Code 2.1.196. Its environment reference says MCP tool search is
disabled by default for a non-first-party base URL unless
`ENABLE_TOOL_SEARCH=true` and the proxy supports the required blocks.

Primary sources reviewed on 2026-07-31:

- [Anthropic gateway subscription behavior](https://code.claude.com/docs/en/llm-gateway)
- [Anthropic Remote Control requirements](https://code.claude.com/docs/en/remote-control)
- [Anthropic environment variables](https://code.claude.com/docs/en/env-vars)

The phase one protocol report recorded the Remote Control loss, but the
definitive synthesis omitted it. The evidence-supported ledger labels redirect
mode adoptable without further ceremony (`:365,369`). Mandatory enrollment
therefore changes an advertised
harness capability without an explicit product decision.

Required correction:

1. Move E1 to unresolved until X1 and a harness feature matrix pass.
2. Add Remote Control and MCP tool search to the compatibility contract and
   operator disclosure.
3. Gate each supported Claude Code version on inference, streaming, tools,
   subagents, MCP tool search, resume, background work, and known first-party
   feature loss.
4. Decide whether Remote Control is intentionally unavailable under
   littleorgans capture. A mandatory capture product cannot leave this as an
   accidental side effect.

### P1. Deletion and retention acceptance does not close every copy of captured content

The release assertion says delete leaves no rows and no session directory
(`:307`). The design also creates transcript snapshots, quarantine and dead
letter evidence, exports, staged delete directories, future content addressed
blobs, and backups whose declared unit is the capture run directory. Identity
audit intentionally survives deletion.

Removing a session row and one directory proves only the primary live path.
Content addressed blobs may be shared. Export bundles may sit outside
`~/.lilo`. Backups and filesystem snapshots may retain content. Dead letter and
quarantine records can contain the same sensitive bytes.

Required correction:

1. Add a data lineage table for every content class, replica, projection,
   export, quarantine record, backup, and audit residue.
2. Define delete, expiry, hold, and cryptographic erase behavior per class.
3. State which external exports and backups are outside daemon authority.
4. Test deletion closure across all owned roots and indexes, including
   reference counted blobs and crash recovery. Preserve only a minimized audit
   fact whose surviving fields are enumerated.

### P1. The jurisdiction specific legal statement is marked as a primary sourced fact without primary support

Section 2 marks as fact that consent is unavailable in employment and that
works council rights apply across DE, NL, AT, and SE (`:65`). The referenced
protocol report R37 cites two commercial secondary pages. It provides no
primary authority for NL, AT, or SE.

Primary material supports a narrower statement. EDPB consent guidance identifies
the employer and employee power imbalance. German BetrVG section 87(1)(6)
addresses co-determination for technical systems intended to monitor employee
behavior or performance:

- [EDPB Guidelines 05/2020 on consent](https://www.edpb.europa.eu/documents/guideline/guidelines-052020-on-consent-under-regulation-2016679_en)
- [German BetrVG section 87](https://www.gesetze-im-internet.de/betrvg/__87.html)

Those sources do not establish the four-country conclusion as written, and
application depends on deployment facts and legal analysis.

Required correction:

1. Downgrade the statement to a legal risk and keep U9 unresolved.
2. Remove the unsupported country list or attach jurisdiction specific primary
   authority reviewed by counsel.
3. Make the enterprise managed-deployment posture a release gate. The
   one-operator v1 assumption does not prove that an operator is outside an
   employment relationship.

## Verified strengths

1. The governing product frame is correct: Transport is mandatory and native
   to littleorgans.
2. The requested littleorgans pin
   `98d8928941b5b5db670ed73ed06af57f61dcfa0a` is the current checkout commit.
3. The requested experimental pin
   `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55` exists and was inspected
   immutably. The live experimental checkout is currently
   `ed099336ebfa9e72da32ed547b29b932f077ccbd`, so review evidence was taken from
   the requested commit rather than the moving checkout.
4. `transport-matters/NOTES/` was neither read nor cited in this review.
5. The pinned littleorgans Cargo, Rust, workflow, tooling, script, and test
   surfaces contain no transport-matters, `TRANSPORT_MATTERS_*`, mitmproxy, or
   provider base URL integration. Cargo metadata contains only littleorgans
   workspace packages.
6. The synthesis proposes no invocation, package, version, FFI, vendoring, or
   subprocess relationship with `tm`. Its zero dependency direction passes.
7. `LaunchSpec` is a credible single interposition seam. The failure matrices,
   typed uncertainty, unknown-shape preservation, secret-free intent repair,
   and explicit rejection map form a strong foundation once the findings above
   are corrected.

## Review method

- Read the definitive synthesis and the status verified phase one and phase two
  inputs needed to challenge each load bearing claim.
- Checked both immutable source pins directly.
- Re-ran source checks for registered launchers, generated CLI exposure, Cargo
  membership, zero dependency, raw artifact construction, response streaming,
  redaction, and fixture round trip assertions.
- Checked current primary vendor documentation for the external redirect and
  compatibility claims.
- Made no repository or synthesis edits.

Verdict: CORRECTION REQUIRED

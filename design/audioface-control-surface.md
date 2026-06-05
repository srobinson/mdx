---
title: Audioface Control Surface
type: design
tags: [audioface, control, adapters, contracts]
summary: One addressed control model projected into every adapter, so adding a control requires no per adapter work
status: active
project: audioface
---

# Control surface

Binding. Derived from the `# Structure, arena decision` section of
`~/.mdx/design/audioface-foundation-decision.md`, which wins on any disagreement.

## The requirement, stated as a falsifiable predicate

Adding a control appears in the CLI, the MCP tools, the HTTP API and the UI without an adapter file
changing. An answer that writes a flag per parameter, a route per parameter, a tool per parameter or
a widget per parameter has failed.

Adding a control *kind* is different and must cost. It breaks every adapter's exhaustive switch at
typecheck through `assertNever`, which is the correct place to pay.

## What the existing model already gives us

`packages/contract/src/address.ts` already carries the whole grammar this design needs.

- `ParameterAddress` is a branded string with roots `patch`, `output`, `trigger`, `layer`.
- `ADDRESS_COLLECTIONS` is `processors`, `envelope-segments`, `connections`.
- `AddressChild` is `{ collection, id }`, so collection members are addressed by id and never by
  position.

The address stability graft is therefore already satisfied. A positional index cannot appear in an
address because the grammar has no syntax for one. When scenario authoring arrives it becomes a
fourth entry in `ADDRESS_COLLECTIONS` and inherits the property for free.

## The manifest

`ControlManifest` describes what can be controlled. It is projected from the parameter registry rows
and the patch structure. It is never hand written and never enumerated in an adapter.

`ControlSchema` is a recursive discriminated union over seven kinds.

- `number`, `boolean`, `enum`, `text` are leaves. Each carries `address`, `label`, `group`, `unit`,
  `range`, `curve`, `default`, `authority` and `lifetime`.
- `object` carries `fields`.
- `list` carries an `AddressCollection` and a `member` schema.
- `union` carries a discriminant and its variants, which is how a layer source and a connection
  source are described.

Two leaf columns carry rules that used to live in prose.

`authority` is `patch`, `pack`, `listener` or `foundation`. It is what makes agreement 7 structural:
the master limiter is `foundation`, so no pack and no adapter can reach it, and the stress gate
cannot be defeated. A write against insufficient authority is a typed issue, never a throw.

`lifetime` is `frozen` or `live`. The resolver reads it to decide freeze against pass through. This
is the listener fields correction expressed as data. Pan, width and distance become `live` rows when
they land rather than a special case in the resolver.

## The edit model

Three operations, exhaustive, closed.

- `set` targets a leaf address and carries a value.
- `insert` targets a collection and carries a member.
- `remove` targets a collection member by id.

`ApplyControlEdits` carries a target, a nonempty edit list and an `expectedRevision`. Application is
atomic: every edit lands or none do. A revision mismatch is a typed `ControlIssue`, because a UI open
beside an MCP agent editing the same patch is the normal case here.

Three operations rather than a value operation plus a separate structural operation, because
`packages/patch/src/patch-editing.ts` already ships `deleteLayer` and `retypeLayer` alongside
`editParameter`. Structural editing exists today. A patch is a tree and a flat row list cannot
describe one.

## The projection

`patch` owns the rows and the projection function. `contract` owns the manifest, the schema union,
the edit union and the control vocabulary the leaves are built from: `ParameterUnit`, `LegalRange`,
`ResponseCurve`, `ParameterScope`, `ParameterGroup`.

Those five move out of `packages/patch/src/registry/definition.ts` into the contract, because an
adapter switching on a range or a curve must not import `patch`. What stays behind is
`ParameterResolution` and everything else that only resolution needs. `ParameterDefinition` is then
the control descriptor plus its resolution rule.

## The conformance test

One test, at the seam, not four.

Every row in the registry projects to a manifest leaf with a known kind, a legal range, a default
inside that range and a parse path. Adding a row the surface cannot express turns it red. This is the
checkable form of the requirement at the top of this document.

## Adapter shapes, for reference

- CLI. `audioface controls`, `audioface get <target> <address>`, `audioface edit <target> ...`.
  Three verbs. The address is an argument validated against the manifest, never a flag.
- MCP. Tool count equals operation count. The address is a plain string and `describe_controls` is
  the discovery path, matching `controls <target>` and `GET /targets/:id`.

  An earlier draft of this document said the address argument was `z.enum(manifest.addresses())`
  built at server construction. That was wrong, and wrong twice. It measured at 1647 leaf
  occurrences serialising to 43946 bytes in two tools, so every client paid about 88KB on every
  `tools/list`. More importantly it was semantically wrong: there are only 95 unique address
  strings, and an address is an instance path carrying layer and processor ids, so an enum spanning
  targets advertises `layer/layer-07/AMP-01` to a patch that owns two layers. The assumption came
  from a candidate that modelled addresses as flat catalog keys. They are not.
- HTTP. The address is in the path. There is no route table.
- UI. One total function from a leaf schema to a widget, closed by `assertNever`.

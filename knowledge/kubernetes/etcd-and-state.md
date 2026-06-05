---
title: etcd & Cluster State
type: knowledge
tags: [kubernetes, kthw, etcd, state, datastore]
summary: etcd is the only stateful component in Kubernetes; every other process is stateless and stores all cluster state here. KTHW runs a single member over plaintext HTTP on localhost as a teaching simplification of production's TLS quorum.
status: active
source: https://github.com/kelseyhightower/kubernetes-the-hard-way
license: Apache-2.0, CC-BY-NC-SA-4.0
related: [index, control-plane-internals, security-at-rest-and-rbac]
confidence: high
---

# etcd & Cluster State

## Concept

etcd is the **single source of truth** for a Kubernetes cluster. Every other component
is stateless and stores all of its state, every Node, Pod, Secret, ConfigMap,
ServiceAccount, and RBAC object, as keys in etcd
(`docs/07-bootstrapping-etcd.md:3`). KTHW makes this concrete by bootstrapping a
**single-member** etcd on the `server` machine, run as a plain systemd unit with all
flags inline and no separate config file (`units/etcd.service:8`).

Because etcd is the only stateful piece, the whole cluster's durability question
reduces to one question: *is etcd intact?* Lose etcd and you lose the cluster, even if
every binary is still running.

## Why it exists

Kubernetes deliberately concentrates all mutable state in one datastore so the rest of
the system can be stateless and horizontally restartable. The apiserver is a pure
translation/authz/admission layer in front of etcd; it caches and watches but owns no
durable state of its own. That design is what lets you kill and restart the apiserver,
controller-manager, and scheduler freely (see `control-plane-internals`) without data
loss: the truth is in etcd, not in any process's memory. The flip side is that etcd's
**integrity, encryption, and backup are the cluster's integrity, encryption, and
backup**. Everything else is replaceable; etcd is not.

## KTHW implementation

KTHW runs one etcd member named `controller`, listening over **plaintext HTTP on
localhost only**:

> Quoted from KTHW (Apache-2.0): units/etcd.service

```
ExecStart=/usr/local/bin/etcd \
  --name controller \
  --listen-client-urls http://127.0.0.1:2379 \
  --advertise-client-urls http://127.0.0.1:2379 \
  --initial-cluster controller=http://127.0.0.1:2380 \
  --initial-cluster-state new \
  --data-dir=/var/lib/etcd
```

- **Single member**: `--name controller` (`units/etcd.service:8`) with
  `--initial-cluster controller=http://127.0.0.1:2380`
  (`units/etcd.service:14`) and `--initial-cluster-state new`
  (`units/etcd.service:15`). One member, no quorum, no peers.
- **Plaintext, localhost client API**: `--listen-client-urls` /
  `--advertise-client-urls http://127.0.0.1:2379`
  (`units/etcd.service:11`, `units/etcd.service:12`). The scheme is `http`, not
  `https`: there is no client TLS and no auth. This is safe *only* because the single
  consumer (the apiserver) is co-located on the same box, reaching it via
  `--etcd-servers=http://127.0.0.1:2379` (`units/kube-apiserver.service:16`).
- **Peer URLs on :2380**: `--initial-advertise-peer-urls` /
  `--listen-peer-urls http://127.0.0.1:2380`
  (`units/etcd.service:9`, `units/etcd.service:10`) plus
  `--initial-cluster-token etcd-cluster-0` (`units/etcd.service:13`). Present for
  completeness, but with one member there is no peer to talk to.
- **State on disk**: `--data-dir=/var/lib/etcd` (`units/etcd.service:16`), with the
  directory created (`docs/07-bootstrapping-etcd.md:39`) and locked down to
  `chmod 700` (`docs/07-bootstrapping-etcd.md:40`).
- **Readiness + supervision**: `Type=notify` (`units/etcd.service:6`) makes systemd
  wait for etcd's own ready signal before considering the unit started;
  `Restart=on-failure` (`units/etcd.service:17`) supervises it.

Verification is a one-liner, `etcdctl member list`
(`docs/07-bootstrapping-etcd.md:69`), which prints the single `controller` member with
its `http://` peer and client URLs and `false` for "is learner"
(`docs/07-bootstrapping-etcd.md:73`).

**Vestigial TLS artifact:** the lab copies `ca.crt` and the `kube-api-server` keypair
into `/etc/etcd/` (`docs/07-bootstrapping-etcd.md:41`), yet the running unit never
references them: etcd here speaks plaintext HTTP. These files are leftovers from an
era when etcd used client/peer TLS; they are unused in the current plaintext-localhost
configuration and are worth recognizing as a vestige rather than a working dependency.

## What managed K8s hides

Managed control planes (EKS/GKE/AKS) hide etcd **entirely**: you never see it, back it
up, or connect to it. KTHW exposes the whole thing as one local service, which makes the
production gap visible:

- **Quorum and HA.** Production etcd runs a quorum of 3 or 5 members so a single node
  loss does not lose the cluster. KTHW's single member
  (`units/etcd.service:14`) has no fault tolerance by design.
- **TLS everywhere.** Production etcd uses client *and* peer TLS with mutual
  authentication. KTHW's plaintext `http://127.0.0.1` channel
  (`units/etcd.service:11`) is a teaching shortcut, defensible only because of
  co-location.
- **Backup / restore / defrag.** Managed etcd snapshots and compacts on a schedule;
  here there is nothing but a `--data-dir` (`units/etcd.service:16`) you would have to
  back up yourself.
- **Secret encryption at rest** is also invisible in managed K8s. Whether Secrets sit
  in etcd as plaintext or ciphertext is an apiserver concern, not an etcd one (see
  `security-at-rest-and-rbac`).

## Gotchas

- **Plaintext localhost is non-production.** The `http://127.0.0.1` client and peer URLs
  (`units/etcd.service:11`, `units/etcd.service:10`) are fine for the lab, but copying
  these units toward a real deployment without adding client/peer TLS and quorum is a
  trap.
- **Losing etcd loses the cluster.** Every binary can be healthy while the cluster state
  is gone if `--data-dir=/var/lib/etcd` (`units/etcd.service:16`) is destroyed. etcd is
  the one component whose backup actually matters.
- **The apiserver↔etcd channel is unencrypted here.** Anyone with localhost access on
  `server` can read etcd directly over `http://127.0.0.1:2379`
  (`units/kube-apiserver.service:16`); only Secret *contents* are protected, and only
  if encryption-at-rest is configured (`security-at-rest-and-rbac`).
- **The `/etc/etcd/` certs are a red herring.** Do not assume etcd is using TLS just
  because `ca.crt` and `kube-api-server.{crt,key}` were copied there
  (`docs/07-bootstrapping-etcd.md:41`): the unit ignores them.
- **Single-member "cluster" still uses peer flags.** `--initial-cluster` and the peer
  URLs (`units/etcd.service:14`, `units/etcd.service:9`) are present but inert with one
  member; do not read them as evidence of HA.

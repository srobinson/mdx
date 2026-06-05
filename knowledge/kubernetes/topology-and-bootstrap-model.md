---
title: Topology & Bootstrap Model
type: knowledge
tags: [kubernetes, kthw, topology, bootstrap, machines]
summary: The KTHW 4-machine layout, machines.txt as the topology source of truth, and why the 13-step bootstrap is a forced dependency chain rather than a checklist.
status: active
source: https://github.com/kelseyhightower/kubernetes-the-hard-way
license: Apache-2.0, CC-BY-NC-SA-4.0
related: [index, pki-and-identity, control-plane-internals]
confidence: high
---

# Topology & Bootstrap Model

## Concept

KTHW runs on **four machines**, and the shape of the cluster is the shape of those four boxes:

```
jumpbox   admin home base. Runs every command in the tutorial; holds the binaries.
          Not part of the cluster.                                        1 CPU / 512MB
server    the ENTIRE control plane on one node: kube-apiserver,
          kube-controller-manager, kube-scheduler, and etcd.              1 CPU / 2GB
node-0    worker: kubelet + containerd + kube-proxy.  pod subnet 10.200.0.0/24
node-1    worker: kubelet + containerd + kube-proxy.  pod subnet 10.200.1.0/24
```

All four are Debian 12 (bookworm), ARM64 or AMD64, on the same network (`docs/01-prerequisites.md:7`). Their CPU/RAM/disk requirements are fixed up front so every later step is reproducible (`docs/01-prerequisites.md:9-14`). Note what the layout does **not** have: no HA control plane, no separate etcd tier, no cloud provider. "The control plane" is literally one VM.

The topology is not implicit — it lives in a file. `machines.txt` is the cluster's **machine database**: one row per machine carrying four fields, the IPv4 address, the FQDN, the short hostname, and the pod subnet (`docs/03-compute-resources.md:10`, `:13`). The worker rows assign each node its own `/24` out of the `10.200.0.0/16` pod space — `node-0` gets `10.200.0.0/24`, `node-1` gets `10.200.1.0/24` (`docs/03-compute-resources.md:22-24`).

That file is the single source of truth. Steps 3, 5, 9, and 11 all consume it with the same shell idiom — `while read IP FQDN HOST SUBNET; do … done < machines.txt` — to distribute SSH keys, set hostnames, template per-node config, and add routes (`docs/03-compute-resources.md:79-81`). Change a row and you change what the whole bootstrap does.

## Why it exists

The 4-machine model exists because KTHW deliberately removes the cloud. With no metadata service, no managed DNS, and no provided VPC routing, the topology and naming you would normally get for free must be built by hand (`docs/13-cleanup.md:7`).

Two substitutes carry the weight:

**`/etc/hosts` + hostnames are the DNS substitute.** Kubernetes clients are told to address the API server by the `server` hostname, not an IP, and workers register themselves by hostname (`docs/03-compute-resources.md:100`). To make those names resolve everywhere, step 3 generates a shared `hosts` block and appends it to `/etc/hosts` on the jumpbox and on all three cluster machines (`docs/03-compute-resources.md:131`, `:170`, `:215-219`). There is no DNS server in this tutorial — `/etc/hosts` *is* the name service.

**The jumpbox is the one-time binary distributor.** Rather than every node pulling its own binaries, the jumpbox downloads the whole set once (over 500MB) and sorts it into `client/`, `controller/`, `worker/`, and `cni-plugins/` (`docs/02-jumpbox.md:51-53`, `:82`, `:95-99`). The exact binary set and pinned versions come from an architecture-specific manifest fetched with `wget -i downloads-$(dpkg --print-architecture).txt` (`docs/02-jumpbox.md:64-68`, `downloads-amd64.txt:1`, `downloads-arm64.txt:1`). Later steps `scp` from those sorted directories to each node; without the layout there is nothing to copy.

## KTHW implementation

The bootstrap is a **forced dependency chain**, and the topology step (3) is what later identity and networking steps hang on.

Step 3 does three topology jobs in order: it distributes SSH keys so the jumpbox can drive each box (`docs/03-compute-resources.md:79-81`), it sets each machine's hostname and rewrites its `127.0.1.1` line to the FQDN plus short name, and it lays down the shared `/etc/hosts` block. The load-bearing pair is a per-row loop that `sed`-rewrites the `127.0.1.1` entry to `<FQDN> <HOST>` (`docs/03-compute-resources.md:108`) and then runs `hostnamectl set-hostname <HOST>` on each machine (`docs/03-compute-resources.md:110`). Those two operations fix, for every box, both how it answers `hostname` and how it resolves its own name.

Everything downstream depends on those names being correct *before* the next step runs:

- **Step 4 (certs)** mints the apiserver cert with SANs that include `server.kubernetes.local`, and each kubelet cert with `CN=system:node:<host>`. Those names are exactly the hostnames fixed in step 3. Certs before kubeconfigs.
- **Step 5 (kubeconfigs)** embeds those certs and points each consumer at `https://server.kubernetes.local:6443`. Kubeconfigs before services.
- **Steps 8–9 (control plane, workers)** start the services that present and verify those certs; workers register under the hostnames from step 3.
- **Step 11 (routes)** re-reads `machines.txt` to add a route to each node's pod `/24`.

This is why the order is non-negotiable: each step writes the inputs the next step verifies. A topology mistake in step 3 does not fail in step 3 — it fails three steps later as a TLS or registration error. See [`pki-and-identity`](pki-and-identity.md) for how the names become identities and [`control-plane-internals`](control-plane-internals.md) for what consumes them.

## What managed K8s hides

EKS, GKE, AKS, and `kubeadm` provision automatically everything step 3 does by hand:

- **Node registration.** Managed control planes hand a node its identity and join token; here you set the hostname, place the per-node cert, and let the kubelet register under `system:node:<host>` yourself.
- **Image and binary distribution.** Managed nodes boot from an image with the runtime and `kubelet` already baked in; here the jumpbox downloads and ships every binary (`docs/02-jumpbox.md:51-53`).
- **Cluster DNS and naming.** Cloud DNS (or CoreDNS plus a cloud resolver) gives you stable names; here `/etc/hosts` is the entire name service (`docs/03-compute-resources.md:131`).
- **The topology database itself.** A cloud tracks instances, IPs, and CIDRs in its control plane; KTHW makes that explicit as a four-column text file you edit.

Seeing the four-machine layout as a plain file makes concrete what a managed cluster abstracts: a cluster is a known set of hosts, each with an identity and a pod CIDR, that can all resolve and reach each other.

## Gotchas

**Hostname / `/etc/hosts` drift is the silent killer.** Three things must agree: the rows in `machines.txt`, the appended `/etc/hosts` block, and what `hostnamectl set-hostname` set on each box (`docs/03-compute-resources.md:108`, `:110`). If they disagree, the failure surfaces far from its cause — a kubelet registers under the wrong name, or a client connects and the API server's certificate SANs do not match the name used, producing `x509: certificate is valid for X, not Y`. The fix lives in step 3, but the symptom appears in steps 8–10. (Cross-reference: SAN validation is owned by [`pki-and-identity`](pki-and-identity.md).)

**Editing `machines.txt` after the fact is not free.** Because steps 3, 5, 9, and 11 all read it, a row changed after certs are minted leaves the certs, kubeconfigs, and routes pointing at the old values. Treat `machines.txt` as the cluster's schema: change it first, then re-run the dependent steps.

**The pod subnet column is load-bearing, not decorative.** The fourth field per worker row (`10.200.0.0/24`, `10.200.1.0/24`) is templated into each node's bridge config and into the static routes. A typo here produces a cluster where same-node pods work and cross-node pods hang. (Cross-reference: the routing consequences are owned by [`networking-model`](networking-model.md).)

**The jumpbox is not a cluster member.** It runs commands and stores binaries; it does not run a kubelet and never registers. Treating it as a node, or expecting workloads to land on it, is a common early confusion.

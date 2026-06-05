---
title: Kubernetes Fundamentals (KTHW backbone)
type: knowledge
tags: [kubernetes, kthw, index, fundamentals]
summary: Entry point to the Kubernetes fundamentals curriculum seeded from kubernetes-the-hard-way — the 4-VM topology, the 13-step bootstrap arc, and the study order across nine modules.
status: active
source: https://github.com/kelseyhightower/kubernetes-the-hard-way
license: Apache-2.0, CC-BY-NC-SA-4.0
related: [topology-and-bootstrap-model, pki-and-identity, kubeconfig-and-authn, control-plane-internals, etcd-and-state, worker-runtime-stack, networking-model, security-at-rest-and-rbac, operations-and-failure-modes]
confidence: high
---

# Kubernetes Fundamentals (KTHW backbone)

This curriculum teaches Kubernetes by the route managed platforms hide: bootstrapping a cluster by hand. It is seeded from Kelsey Hightower's *Kubernetes The Hard Way* (KTHW), distilled into nine modules of original synthesis. The thesis of the whole domain is that a Kubernetes cluster is not magic — it is a handful of plain processes wired together by TLS identity, one datastore, and a few static routes. Once you have placed every cert, written every kubeconfig, and added every route yourself, `kubeadm` / EKS / GKE stop being black boxes.

Read this index first, then the modules in study order. The flagship is [`pki-and-identity`](pki-and-identity.md): the PKI is the cluster's identity system, and most of Kubernetes' authz follows from it.

## Domain overview

**The 4-VM topology.** The whole cluster runs on four plain Debian 12 (bookworm) machines, ARM64 or AMD64, on one network (`docs/01-prerequisites.md:7`):

```
jumpbox   admin home base — runs every command, holds the downloaded binaries   (1 CPU, 512MB)
server    the ENTIRE control plane on one node: apiserver + controller-manager
          + scheduler + etcd                                                     (1 CPU, 2GB)
node-0    worker: kubelet + containerd + kube-proxy   pod subnet 10.200.0.0/24   (1 CPU, 2GB)
node-1    worker: kubelet + containerd + kube-proxy   pod subnet 10.200.1.0/24   (1 CPU, 2GB)
```

The control plane is not highly available — it is a single `server` node (`docs/01-prerequisites.md:9-14`). Each worker owns a non-overlapping `/24` slice of the `10.200.0.0/16` pod space, recorded per row in `machines.txt` (`docs/03-compute-resources.md:22-24`).

**Versions (current era).** Kubernetes v1.32.x, containerd v2.1.x, CNI plugins v1.6.x, etcd v3.6.x (`README.md:22-25`). The binary manifest pins exact builds: kubectl/kube-* v1.32.3, etcd v3.6.0-rc.3, containerd 2.1.0-beta.0, CNI v1.6.2, runc v1.3.0-rc.1, crictl v1.32.0 (`downloads-amd64.txt:1-11`, `downloads-arm64.txt:1-11`).

**Post-GCP, cloud-agnostic.** Earlier editions provisioned Google Compute Engine VMs, load balancers, and VPC routes via `gcloud`. The current edition is cloud-agnostic: every step runs on the jumpbox, server, or nodes, with no cloud provider integration (`docs/13-cleanup.md:7`). There is no cloud `LoadBalancer` and no metadata service — which is precisely why DNS, routing, and identity are all wired by hand.

## The 13-step arc

The bootstrap is a forced dependency chain. Each step exists because the next one cannot proceed without it; the order is non-negotiable (certs before kubeconfigs before services; etcd before the apiserver; workers before pod routes).

1. **Prerequisites** (`docs/01-prerequisites.md`) — confirm four Debian 12 VMs at the pinned specs. A fixed OS/arch baseline keeps every later apt, binary, and systemd step reproducible.
2. **Set up the jumpbox** (`docs/02-jumpbox.md`) — install tooling, clone the repo, download ~500MB of binaries once and sort them into `client/ controller/ worker/ cni-plugins/`. One download host is the single source of truth for what ships to every node.
3. **Provision compute resources** (`docs/03-compute-resources.md`) — author `machines.txt` (the topology database), enable root SSH, set hostnames, and append a shared `/etc/hosts` block. This is the cluster's DNS substitute, since there is no cloud metadata service.
4. **Provision the CA and TLS certs** (`docs/04-certificate-authority.md`) — self-sign one CA and mint eight leaf certs whose CN/O fields become Kubernetes identities. Every component-to-component call is mutual TLS rooted here.
5. **Generate kubeconfigs** (`docs/05-kubernetes-configuration-files.md`) — package each client cert + the CA + a server URL into a per-consumer kubeconfig. The embedded cert is the identity the apiserver will see.
6. **Data-encryption config and key** (`docs/06-data-encryption-keys.md`) — generate a 32-byte key and an `EncryptionConfiguration` so Secrets are encrypted at rest in etcd instead of stored in plaintext.
7. **Bootstrap etcd** (`docs/07-bootstrapping-etcd.md`) — start a single-member etcd on localhost. It is the only stateful component and must be up before the apiserver.
8. **Bootstrap the control plane** (`docs/08-bootstrapping-kubernetes-controllers.md`) — start apiserver, controller-manager, and scheduler on `server`, then apply the apiserver→kubelet ClusterRole that makes `kubectl logs/exec/top` work.
9. **Bootstrap the workers** (`docs/09-bootstrapping-kubernetes-workers.md`) — install runc, CNI plugins, containerd, kubelet, and kube-proxy per node; template each node's pod subnet; load `br-netfilter`. This is where containers actually run.
10. **Configure kubectl for remote access** (`docs/10-configuring-kubectl.md`) — build a jumpbox `~/.kube/config` pointed at the `server` hostname so the cluster can be driven over the network instead of by SSH.
11. **Provision pod network routes** (`docs/11-pod-network-routes.md`) — add static routes so each node can reach the others' pod CIDRs. KTHW's bridge CNI only wires same-node pods; this is the clearest "managed K8s hides this" moment.
12. **Smoke test** (`docs/12-smoke-test.md`) — prove encryption-at-rest, Deployments, port-forward, logs, exec, and NodePort. A diagnostic matrix where each check localizes a different subsystem.
13. **Cleanup** (`docs/13-cleanup.md`) — delete the VMs. In the post-GCP era there are no cloud resources to deprovision.

## Study order

Read the nine modules in this order. Each line says when to reach for it.

1. [`topology-and-bootstrap-model`](topology-and-bootstrap-model.md) — start here; the 4-machine layout, `machines.txt`, and why the 13 steps are ordered the way they are.
2. [`pki-and-identity`](pki-and-identity.md) — read for any TLS, certificate, identity, or "why is RBAC denying this" question. The flagship trust web.
3. [`kubeconfig-and-authn`](kubeconfig-and-authn.md) — read when you need to understand how a component's identity is packaged and presented to the apiserver.
4. [`control-plane-internals`](control-plane-internals.md) — read when reasoning about apiserver / controller-manager / scheduler behavior, flags, or which secrets each holds.
5. [`etcd-and-state`](etcd-and-state.md) — read when thinking about cluster state, durability, or backup and restore.
6. [`worker-runtime-stack`](worker-runtime-stack.md) — read when pods will not start or you are debugging kubelet, containerd, or the CRI.
7. [`networking-model`](networking-model.md) — read when pod-to-pod or Service routing fails, or to understand what a CNI actually does.
8. [`security-at-rest-and-rbac`](security-at-rest-and-rbac.md) — read when handling Secrets encryption, RBAC bindings, or admission control.
9. [`operations-and-failure-modes`](operations-and-failure-modes.md) — read when verifying a cluster or triaging a failure; the consolidated gotcha catalogue cross-linking the other eight.

## Source & license

Seeded from [kubernetes-the-hard-way](https://github.com/kelseyhightower/kubernetes-the-hard-way), which is **dual-licensed**:

- **Apache-2.0** covers the code artifacts: `configs/`, `units/`, and `ca.conf` (`LICENSE`). These may be quoted in short with an attribution notice.
- **CC-BY-NC-SA-4.0** covers the prose: `README.md`, `COPYRIGHT.md`, and the `docs/*.md` labs (`README.md:9`). This prose is **never** reproduced verbatim in these modules.

Every module in this curriculum is original synthesis written in our own words. Citations point into the on-disk REFS clone as `<repo-relative-path>:<line>` so each claim is verifiable against ground truth.

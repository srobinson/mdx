---
title: Networking Model
type: knowledge
tags: [kubernetes, kthw, networking, cni, pod-cidr, kube-proxy, routes]
summary: The KTHW pod/service address plan and why a bridge CNI plus hand-added static routes stands in for a real CNI, the single highest-value "what managed K8s hides" layer.
status: active
source: https://github.com/kelseyhightower/kubernetes-the-hard-way
license: Apache-2.0, CC-BY-NC-SA-4.0
related: [index, worker-runtime-stack, control-plane-internals]
confidence: high
---

# Networking Model

Kubernetes promises a flat network: every pod gets its own routable IP and pods
reach each other directly, with no NAT between them. KTHW builds that promise
from primitives: a bridge CNI plugin for intra-node addressing and a handful of
static routes for cross-node reachability, so the work a production CNI does
automatically becomes visible. This is the module where "the CNI" stops being a
black box.

## Concept

There are two separate, non-overlapping address spaces, plus the per-node carve:

| Space | CIDR | Notes | Source |
|---|---|---|---|
| Pod network (whole cluster) | `10.200.0.0/16` | carved into a `/24` per node | `units/kube-controller-manager.service:8`, `configs/kube-proxy-config.yaml:6` |
| node-0 pod subnet | `10.200.0.0/24` | this node's pod IPs | `docs/03-compute-resources.md:23` |
| node-1 pod subnet | `10.200.1.0/24` | this node's pod IPs | `docs/03-compute-resources.md:24` |
| Service network | `10.32.0.0/24` | ClusterIP VIPs, distinct from pods | `units/kube-controller-manager.service:15` |
| `kubernetes` Service VIP | `10.32.0.1` | first address of the service CIDR | convention (see `pki-and-identity` SANs) |

The per-node slice comes from the cluster's topology database, `machines.txt`,
whose fourth column is `POD_SUBNET` (`docs/03-compute-resources.md:10`,
`docs/03-compute-resources.md:13`). A pod's address is **not** the same kind of
thing as a Service's address: pod IPs are real, routable, ephemeral interface
addresses; Service IPs are virtual and exist only as kube-proxy iptables rules.
Keeping the two `/16`-vs-`/24` spaces straight is the first conceptual hurdle.

## Why it exists

Every pod needs an IP that other pods can reach without translation. That breaks
into two problems:

1. **Intra-node**: pods on the same node need IPs and a path to each other and to
   the outside. A CNI bridge solves this locally.
2. **Cross-node**: a pod on node-0 must reach a pod on node-1, whose `/24` lives
   on a different machine. Something has to tell node-0's kernel that
   `10.200.1.0/24` is "over there, via node-1's host IP."

A real CNI (Calico, Cilium, flannel) solves problem 2 dynamically (by an
overlay, BGP, or by programming cloud-VPC routes), so operators never see it.
KTHW omits the dynamic layer and makes you install the cross-node routes by hand
(`docs/11-pod-network-routes.md:3`, `docs/11-pod-network-routes.md:5`). The
result is the most illuminating failure mode in the whole tutorial: skip the
routes and same-node pods work while cross-node pods hang, which is exactly the
shape of a broken CNI in production.

## KTHW implementation

**Same-node addressing: the bridge CNI.** Each worker drops two CNI config files
into `/etc/cni/net.d`. The bridge plugin (`configs/10-bridge.conf`) creates a
Linux bridge `cni0` (`configs/10-bridge.conf:5`), acts as the pods' gateway
(`configs/10-bridge.conf:6`), masquerades pod egress to the outside world
(`configs/10-bridge.conf:7`), and hands out IPs from the node's slice with the
`host-local` IPAM (`configs/10-bridge.conf:8-9`) plus a default route
(`configs/10-bridge.conf:13`). The slice is a placeholder, `"SUBNET"`
(`configs/10-bridge.conf:11`):

```json
"ranges": [
  [{"subnet": "SUBNET"}]
]
```
> Quoted from KTHW (Apache-2.0): configs/10-bridge.conf

That `SUBNET` token is replaced per node at deploy time with that node's
`POD_SUBNET` from `machines.txt` (`docs/09-bootstrapping-kubernetes-workers.md:13-22`),
which is what gives node-0 `10.200.0.0/24` and node-1 `10.200.1.0/24` without the
ranges overlapping. The second CNI file is the trivial loopback plugin
(`configs/99-loopback.conf:4`) that wires each pod's `lo`.

**Cross-node reachability: manual static routes.** The bridge knows nothing about
other nodes. KTHW substitutes a real CNI's cross-node data path with explicit L3
routes: for every node, add a route saying "the other node's pod `/24` is
reachable via that node's host IP." The server learns both node subnets, and
each node learns the other's (`docs/11-pod-network-routes.md:27-40`). Generically:

```
# on each host, for every *other* node:
ip route add <other-node-pod-/24> via <other-node-host-IP>
```

The IPs and subnets are pulled from `machines.txt`
(`docs/11-pod-network-routes.md:17-21`), and the result is verifiable in the
routing table: entries for `10.200.0.0/24` and `10.200.1.0/24` pointing at host
IPs (`docs/11-pod-network-routes.md:52-53`). In production a CNI installs these
routes (or an overlay) automatically and dynamically as nodes join; doing it by
hand, with a fixed route per node, is the lesson
(`docs/11-pod-network-routes.md:7`).

**Service routing: kube-proxy in iptables mode.** Service VIPs are not real
interfaces; kube-proxy turns them into NAT rules. It runs in iptables mode
(`configs/kube-proxy-config.yaml:5`) and is told the pod space via
`clusterCIDR: "10.200.0.0/16"` (`configs/kube-proxy-config.yaml:6`). Those
iptables rules only see bridged pod traffic once each worker has loaded the
`br-netfilter` kernel module (`docs/09-bootstrapping-kubernetes-workers.md:116-123`)
and enabled the bridge netfilter sysctls
`net.bridge.bridge-nf-call-iptables = 1` (and the ip6 variant)
(`docs/09-bootstrapping-kubernetes-workers.md:127-131`). Without that module +
sysctl pair, packets crossing the `cni0` bridge bypass netfilter entirely, so
kube-proxy's rules are present but never match.

**The full picture:**

```
        node-0 (10.200.0.0/24)                 node-1 (10.200.1.0/24)
   ┌───────────────────────────┐          ┌───────────────────────────┐
   │ pod ── cni0 bridge ── pod  │          │ pod ── cni0 bridge ── pod  │
   │      (host-local IPAM)     │          │      (host-local IPAM)     │
   │            │ host NIC      │          │       host NIC │           │
   └────────────┼──────────────┘          └────────────────┼──────────┘
                │   ip route add 10.200.1.0/24 via node-1-IP │
                └──────────────── static routes ─────────────┘
                       (the layer a real CNI would automate)

   Service VIPs (10.32.0.0/24): no interface, kube-proxy iptables NAT,
   effective only after br-netfilter + bridge-nf-call-iptables sysctls.
```

## What managed K8s hides

This module is the highest-value "managed K8s hides this" payload in KTHW.

- **The CNI plugin itself.** EKS/GKE/AKS ship a CNI (AWS VPC CNI, Cilium, etc.) as
  a managed DaemonSet; you never write a `bridge` conf or pick an IPAM.
- **Cross-node routing.** The static `ip route` step is replaced by the provider's
  VPC route tables, an overlay (VXLAN/Geneve), or BGP, installed and updated
  automatically as nodes scale. KTHW's hand-added routes are the thing you never
  see do its job.
- **kube-proxy mode and the bridge sysctls.** Managed nodes preload
  `br-netfilter` and the netfilter sysctls and run kube-proxy (or replace it,
  e.g. Cilium's eBPF dataplane) for you; the mode choice is made upstream.
- **CIDR planning.** The pod `/16`, the `/24`-per-node carve, and the service
  `/24` are picked and kept non-overlapping by the platform; here you assign them
  by hand in `machines.txt` and the control-plane flags.

## Gotchas

- **Forgetting the static routes.** The classic half-working state: intra-node
  pod-to-pod works, cross-node pod-to-pod hangs
  (`docs/11-pod-network-routes.md:3`). The symptom mimics an application bug, but
  the cause is a missing route.
- **Missing `br-netfilter` / bridge sysctls.** Services appear configured but pod
  traffic silently bypasses kube-proxy's iptables rules
  (`docs/09-bootstrapping-kubernetes-workers.md:116-133`); symptoms mimic flaky
  DNS or Service resolution. Shared with the `worker-runtime-stack` module.
- **Confusing the two CIDRs.** `10.200.0.0/16` (pods) and `10.32.0.0/24`
  (services) are different spaces with different semantics; a pod will never have
  a `10.32.x.x` address, and `10.32.0.1` is the `kubernetes` Service VIP rather
  than a pod address.
- **Overlapping per-node subnets.** If the `SUBNET` templating
  (`docs/09-bootstrapping-kubernetes-workers.md:13-22`) gives two nodes the same
  `/24`, IPAM hands out duplicate pod IPs and routing becomes ambiguous.
- **Routes are static.** Add a third node and you must add its routes on every
  existing host by hand, precisely the toil a dynamic CNI removes.

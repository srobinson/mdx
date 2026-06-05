---
title: Worker Runtime Stack
type: knowledge
tags: [kubernetes, kthw, kubelet, containerd, cri, runc, kube-proxy]
summary: How a KTHW worker runs pods. kubelet drives containerd over the CRI, containerd uses runc, and the cgroupDriver/SystemdCgroup contract must agree or nothing schedules.
status: active
source: https://github.com/kelseyhightower/kubernetes-the-hard-way
license: Apache-2.0, CC-BY-NC-SA-4.0
related: [index, networking-model, control-plane-internals]
confidence: high
---

# Worker Runtime Stack

The worker node is where PodSpecs become running processes. KTHW installs four
cooperating pieces per worker (`docs/09-bootstrapping-kubernetes-workers.md:3`):
runc, the CNI plugins, containerd, kubelet, and kube-proxy. This module covers
the runtime call chain (kubelet → containerd → runc) and the dataplane agent
(kube-proxy). CNI and the pod-network address plan are owned by the sibling
`networking-model` module.

## Concept

A worker is a layered delegation across cooperating processes:

```
 apiserver  ──watch pods──►  kubelet  ──CRI gRPC──►  containerd  ──OCI──►  runc ──► container
                              (node agent)            (CRI runtime)        (spawner)
                                  │
                                  └── kube-proxy programs iptables for Service VIPs (separate path)
```

- **kubelet** is the node agent. It registers the node, watches the API server
  for pods bound to this node, and reconciles them into running containers. It
  runs as a plain systemd unit that delegates to a `--config` YAML
  (`units/kubelet.service:8-9`).
- **containerd** is the CRI runtime kubelet talks to over a local Unix socket. It
  pulls images, manages the container lifecycle, and shells out to runc.
- **runc** is the OCI runtime that actually clones the namespaces/cgroups and
  execs the container process. It is invoked by containerd, never directly by
  kubelet.
- **kube-proxy** is a parallel agent. It does not run pods; it writes the
  node's iptables rules so Service ClusterIPs and NodePorts load-balance to pod
  endpoints (`units/kube-proxy.service:6-7`, `configs/kube-proxy-config.yaml:5`).

The contract that binds the layers is the **CRI** (Container Runtime Interface):
a stable gRPC API so the kubelet is agnostic to which runtime sits below it.
kubelet reaches containerd at `unix:///var/run/containerd/containerd.sock`
(`configs/kubelet-config.yaml:14`).

## Why it exists

Kubernetes deliberately split "the thing that decides what should run" (kubelet)
from "the thing that runs it" (the container runtime) so the runtime is
pluggable. The CRI is the seam. KTHW makes the seam visible by wiring it by
hand: you choose containerd, point the kubelet's `containerRuntimeEndpoint` at
its socket, and the two halves must agree on how Linux cgroups are driven. Get
that agreement wrong and the kubelet and runtime each try to own the cgroup
hierarchy, so pods never stabilize. That agreement is the single most important
contract on the worker, and managed Kubernetes hides it entirely.

kube-proxy exists as a separate process because Service routing is a dataplane
concern independent of the pod lifecycle: pods come and go, but the iptables
rules that map a stable Service VIP to the current endpoint set are maintained
continuously, in band with the node's kernel netfilter tables.

## KTHW implementation

**The cgroupDriver / SystemdCgroup contract.** On Debian 12 the init system is
systemd, which expects to be the single writer of the cgroup tree. Both the
kubelet and containerd must therefore be told to use the systemd cgroup driver,
and the two settings must match exactly. KTHW sets them in two different files.

On the kubelet side (`configs/kubelet-config.yaml:13`):

```yaml
cgroupDriver: systemd
```
> Quoted from KTHW (Apache-2.0): configs/kubelet-config.yaml

On the containerd side (`configs/containerd-config.toml:10`):

```toml
SystemdCgroup = true
```
> Quoted from KTHW (Apache-2.0): configs/containerd-config.toml

If these disagree (one `systemd`, one `cgroupfs`), the kubelet and containerd
place containers in different cgroup subtrees and pods crash-loop with cgroup
errors. There is no warning at install time; the failure only shows when a pod
is scheduled.

**The containerd CRI config.** Beyond the cgroup driver, the runtime block
(`configs/containerd-config.toml:5-8`) selects the overlayfs snapshotter
(`snapshotter = "overlayfs"`), names `runc` as the default runtime
(`default_runtime_name = "runc"`), and binds the runc handler to the v2 shim
(`runtime_type = "io.containerd.runc.v2"`). The CNI block tells containerd where
to find plugins and config (`configs/containerd-config.toml:12-13`:
`bin_dir = "/opt/cni/bin"`, `conf_dir = "/etc/cni/net.d"`). That is the
handoff point to the `networking-model` module.

**The containerd unit.** containerd runs with resource-isolation directives that
matter on a node packed with pods (`units/containerd.service:7-13`):
`ExecStartPre=/sbin/modprobe overlay` loads the overlay module the snapshotter
needs; `Delegate=yes` lets systemd hand the cgroup subtree to containerd to
subdivide; `KillMode=process` stops systemd from killing the container children
when containerd restarts; `OOMScoreAdjust=-999` makes the runtime nearly
unkillable under memory pressure so the node does not lose its runtime first.

**kubelet authentication and authorization.** The kubelet serves its own HTTPS
API on port 10250 (`configs/kubelet-config.yaml:20`) for `logs`, `exec`, and
metrics. It does not trust callers blindly. Anonymous access is off
(`configs/kubelet-config.yaml:5-6`); incoming clients are verified against the
cluster CA via x509 (`configs/kubelet-config.yaml:9-10`); and every authenticated
request is authorized by asking the API server, because authn webhook is on
(`configs/kubelet-config.yaml:7-8`) and `authorization.mode: Webhook`
(`configs/kubelet-config.yaml:11-12`). This is the worker-side half of the
apiserver→kubelet reverse-trust path; the RBAC binding that makes it answer
`yes` lives in the `pki-and-identity` and `control-plane-internals` modules.
The kubelet's own serving cert is the per-node `kubelet.crt`/`kubelet.key`
(`configs/kubelet-config.yaml:24-25`).

**Node-shaped settings.** `registerNode: true` (`configs/kubelet-config.yaml:22`)
makes the kubelet self-register with the API server on start. Swap is tolerated
rather than required-off: `failSwapOn: false` (`configs/kubelet-config.yaml:16`)
with `swapBehavior: NoSwap` (`configs/kubelet-config.yaml:18-19`). `maxPods: 16`
(`configs/kubelet-config.yaml:17`) is a teaching-scale cap.

**Startup ordering.** The kubelet unit declares
`After=containerd.service` / `Requires=containerd.service`
(`units/kubelet.service:4-5`) so the CRI socket exists before the kubelet dials
it. The worker starts the three services in dependency order
(`docs/09-bootstrapping-kubernetes-workers.md:171-174`): containerd, then
kubelet, then kube-proxy. Binaries land in the expected paths first: runc,
kubelet, kube-proxy, crictl into `/usr/local/bin`, containerd into `/bin`
(`docs/09-bootstrapping-kubernetes-workers.md:100-106`). Success is the node
reporting `Ready` to the API server
(`docs/09-bootstrapping-kubernetes-workers.md:202-204`).

**kube-proxy.** It runs in iptables mode (`configs/kube-proxy-config.yaml:5`)
over the cluster pod CIDR `10.200.0.0/16` (`configs/kube-proxy-config.yaml:6`).
Its iptables rules only see bridged pod traffic once the worker has loaded
`br-netfilter` and enabled the bridge sysctls
(`docs/09-bootstrapping-kubernetes-workers.md:116-133`), covered in depth by
`networking-model`.

## What managed K8s hides

On EKS/GKE/AKS, or even with kubeadm, this entire stack is pre-baked into the
node image or installed by a bootstrap agent:

- **The runtime install and CRI wiring.** You never choose containerd, point the
  kubelet socket at it, or pick a snapshotter; the node AMI ships it configured.
- **The cgroup-driver agreement.** kubeadm aligns kubelet and the runtime on the
  systemd driver for you; a managed node never exposes the two knobs that must
  match.
- **kubelet registration and credentials.** Bootstrap-token / TLS-bootstrap flows
  auto-issue the kubelet's cert and register the node; KTHW pre-mints the
  per-node cert and turns on `registerNode` by hand.
- **kube-proxy mode and the bridge sysctls.** Managed nodes preload
  `br-netfilter` and the netfilter sysctls and run kube-proxy (or a CNI's
  replacement) as a managed DaemonSet; you never set them.

## Gotchas

- **cgroup-driver mismatch.** kubelet `cgroupDriver: systemd`
  (`configs/kubelet-config.yaml:13`) must equal containerd `SystemdCgroup = true`
  (`configs/containerd-config.toml:10`). A mismatch crash-loops pods with cgroup
  errors and is silent until the first pod schedules.
- **kubelet started before containerd.** Without
  `After=`/`Requires=containerd.service` (`units/kubelet.service:4-5`) the kubelet
  races the CRI socket and logs runtime-connection errors.
- **Wrong runtime endpoint.** `containerRuntimeEndpoint`
  (`configs/kubelet-config.yaml:14`) must point at the actual containerd socket;
  a typo presents as a permanently `NotReady` node.
- **Missing `br-netfilter` / bridge sysctls.** Pods get IPs and same-node traffic
  works, but kube-proxy's Service rules silently never apply to bridged traffic
  (`docs/09-bootstrapping-kubernetes-workers.md:116-133`). Forward-reference to
  `networking-model`.
- **Forgetting the apiserver→kubelet RBAC binding.** The worker correctly refuses
  the API server's `logs`/`exec` calls (Webhook authz,
  `configs/kubelet-config.yaml:11-12`) until the cluster grants user `kubernetes`
  that permission; symptom is `kubectl logs/exec` returning 403. The binding is
  in `pki-and-identity` / `control-plane-internals`.
- **Swap assumptions.** KTHW tolerates swap (`failSwapOn: false`); copying these
  configs to a cluster that expects swap-off changes scheduling/accounting
  behavior.

---
title: Operations & Failure Modes
type: knowledge
tags: [kubernetes, kthw, operations, smoke-test, debugging, gotchas]
summary: The KTHW smoke-test as a per-subsystem diagnostic matrix, systemd-based debugging of each component, and a consolidated gotcha catalogue that cross-links every other module by slug.
status: active
source: https://github.com/kelseyhightower/kubernetes-the-hard-way
license: Apache-2.0, CC-BY-NC-SA-4.0
related: [index, pki-and-identity, networking-model, worker-runtime-stack, security-at-rest-and-rbac]
confidence: high
---

# Operations & Failure Modes

How you prove a hand-built cluster works, how you localize a fault when it does not, and a single catalogue of the failure modes the other eight modules each warn about.

## Concept

The smoke test is not a demo; it is a diagnostic matrix. Each check exercises a different subsystem, so a single failing check points at the broken layer rather than at "the cluster." Debugging is uniform because KTHW runs every component as a plain systemd service (no static pods, no self-hosting): each binary is one unit you inspect with `systemctl` and `journalctl`.

## Why it exists

When a distributed system is "down," the expensive part is deciding *where* it is down. KTHW's smoke test is structured so that encryption, the scheduler, the kubelet/runtime, the API-server-to-kubelet path, and Service routing each have their own check; a failure isolates the responsible component. And because there is no managed control plane, the observability surface is the OS: `journalctl -u <unit>` is the log aggregator, `systemctl status` is the health dashboard.

## KTHW implementation

### Smoke-test matrix

Each row is one check from `docs/12-smoke-test.md` and the subsystem it proves:

- **Encryption at rest** (`docs/12-smoke-test.md:5`): create a Secret, then read its value directly from etcd and hexdump it (`docs/12-smoke-test.md:19-20`). The `k8s:enc:aescbc:v1:key1` prefix (`docs/12-smoke-test.md:49`) proves the `aescbc` provider engaged. Exercises API-server encryption + etcd. See `security-at-rest-and-rbac`.
- **Deployments** (`docs/12-smoke-test.md:51`): `kubectl create deployment nginx` (`docs/12-smoke-test.md:58`); the pod reaching `Running` exercises the scheduler, controller-manager, and the kubelet/containerd path.
- **Port forwarding** (`docs/12-smoke-test.md:73`): `kubectl port-forward` (`docs/12-smoke-test.md:87`) exercises the API server's streaming path into the kubelet.
- **Logs** (`docs/12-smoke-test.md:122`): `kubectl logs` (`docs/12-smoke-test.md:129`) exercises the API-server-to-kubelet RBAC grant on `nodes/log`.
- **Exec** (`docs/12-smoke-test.md:137`): `kubectl exec` (`docs/12-smoke-test.md:144`) exercises the same RBAC grant (`nodes/proxy`) plus the container runtime attach.
- **NodePort Service** (`docs/12-smoke-test.md:151`): `kubectl expose --type NodePort` (`docs/12-smoke-test.md:158-159`) then a `curl` to the node port exercises kube-proxy's iptables rules and cross-node routing. `LoadBalancer` is explicitly out of scope because there is no cloud provider integration (`docs/12-smoke-test.md:162`).

### systemd debugging

The control-plane lab establishes the debugging idiom (`docs/08-bootstrapping-kubernetes-controllers.md`): `systemctl is-active <unit>` for a yes/no (`docs/08-bootstrapping-kubernetes-controllers.md:124`), `systemctl status <unit>` for process + recent log detail (`docs/08-bootstrapping-kubernetes-controllers.md:130`), and `journalctl -u <unit>` for full logs (`docs/08-bootstrapping-kubernetes-controllers.md:136`).

Each component maps to exactly one unit:

- **etcd** (`units/etcd.service`): `Type=notify` (`units/etcd.service:6`) means systemd waits for etcd's own readiness signal before declaring it started.
- **kube-apiserver** (`units/kube-apiserver.service`): the fattest unit, all flags inline.
- **kubelet** (`units/kubelet.service`): ordered after the runtime with `After=containerd.service` and `Requires=containerd.service` (`units/kubelet.service:4-5`).
- **containerd** (`units/containerd.service`): `Restart=always` (`units/containerd.service:9`) and a modprobe precondition (`units/containerd.service:7`).

Every unit uses `Restart=on-failure` with `RestartSec=5` (for example `units/kube-apiserver.service:30-31`, `units/etcd.service:17-18`). The practical consequence: a misconfigured component does not stay dead, it crash-loops, so `is-active` can flap to `activating` and the real signal is in the journal, not in the active state.

Teardown is trivial because all state lives on the four machines: the current cloud-agnostic era performs every step on the jumpbox, server, or nodes (`docs/13-cleanup.md:7`), so cleanup is just deleting the VMs (`docs/13-cleanup.md:9`) with no cloud resources to deprovision.

## What managed K8s hides

- **The control plane has no journal you touch.** Providers expose health dashboards, automated probes, and auto-remediation instead of `journalctl` against the API server.
- **Node failures self-heal.** Node problem detection and managed node-group replacement stand in for hand-debugging a wedged kubelet.
- **The smoke test becomes SLOs.** Per-subsystem manual checks are replaced by provider SLOs and an observability stack you bolt on, not commands you run by hand.

## Gotchas catalogue (consolidated index)

The single place to start when a symptom does not name its cause. Each row links the responsible module by slug.

| Symptom | Root cause | Module |
|---|---|---|
| `x509: certificate is valid for X, not Y` | API server cert missing a required SAN | [pki-and-identity](pki-and-identity.md) |
| kubelet registers under the wrong name; TLS / Node-authorizer failures | `machines.txt`, `/etc/hosts`, and hostname drift | [topology-and-bootstrap-model](topology-and-bootstrap-model.md) |
| works on the server, fails from the jumpbox | admin kubeconfig server URL (`127.0.0.1` vs hostname) | [kubeconfig-and-authn](kubeconfig-and-authn.md) |
| `kubectl logs/exec/top` return 403 | API-server-to-kubelet ClusterRole never applied | [security-at-rest-and-rbac](security-at-rest-and-rbac.md) |
| Secrets readable in the etcd hexdump | encryption provider order (`identity` placed first) | [security-at-rest-and-rbac](security-at-rest-and-rbac.md) |
| pods crash-loop with cgroup errors | kubelet `cgroupDriver` not equal to containerd `SystemdCgroup` | [worker-runtime-stack](worker-runtime-stack.md) |
| Services look up but pod traffic bypasses kube-proxy | missing `br-netfilter` / bridge sysctls | [networking-model](networking-model.md) |
| same-node pods reachable, cross-node pods hang | missing static pod-CIDR routes | [networking-model](networking-model.md) |
| CRI connection errors at boot | kubelet started before containerd (systemd ordering) | [control-plane-internals](control-plane-internals.md) |
| etcd "works" but is a production trap | plaintext localhost, single member, no quorum or TLS | [etcd-and-state](etcd-and-state.md) |

---
title: Control Plane Internals
type: knowledge
tags: [kubernetes, kthw, apiserver, controller-manager, scheduler, control-plane]
summary: The Kubernetes control plane is three independent binaries (kube-apiserver, kube-controller-manager, kube-scheduler) on one node, each with its own x509 identity, kubeconfig, secrets, and failure mode, read from their KTHW systemd units.
status: active
source: https://github.com/kelseyhightower/kubernetes-the-hard-way
license: Apache-2.0, CC-BY-NC-SA-4.0
related: [index, pki-and-identity, etcd-and-state, security-at-rest-and-rbac]
confidence: high
---

# Control Plane Internals

## Concept

"The control plane" is not one program. It is **three independent processes** that
KTHW installs side by side on the single `server` machine
(`docs/08-bootstrapping-kubernetes-controllers.md:3`):

- **kube-apiserver**: the front door and the *only* component that talks to etcd. It
  serves the REST API and performs authentication, authorization, admission, and
  encryption-at-rest.
- **kube-controller-manager**: the reconciliation engine. It runs the control loops
  (node, deployment/replicaset, service-account-token, CSR signing, …) that drive
  actual state toward desired state.
- **kube-scheduler**: watches for unscheduled pods and binds each one to a node.

Each runs as a plain systemd service that you `enable` and `start` directly
(`docs/08-bootstrapping-kubernetes-controllers.md:111`,
`docs/08-bootstrapping-kubernetes-controllers.md:114`). There is no self-hosting and
no static-pod manifest here: the control plane is three units on one box. Crucially,
each binary holds a **different** identity and a **different** set of secrets, and the
distinction is what the rest of this module makes concrete.

```
                          server (single node)
   ┌──────────────────────────────────────────────────────────────┐
   │                                                                │
   │   kube-scheduler ───┐                                          │
   │   (system:kube-      │  watch/bind via kubeconfig              │
   │    scheduler)        ▼                                         │
   │                  kube-apiserver ───────────►  etcd             │
   │   kube-controller-   ▲   ▲        --etcd-servers   (only       │
   │   manager ───────────┘   │         http://127.0.0.1:2379       │
   │   (holds ca.key +        │                         talker)     │
   │    SA signing key)       │ presents kube-api-server.crt        │
   │                          ▼ as a CLIENT to kubelets             │
   │                    node-0 / node-1 kubelets                    │
   └──────────────────────────────────────────────────────────────┘
```

## Why it exists

Splitting the control plane into three binaries buys **separation of identity and
blast radius**. The apiserver is the single chokepoint for authn/authz and the sole
writer to etcd, so it can enforce one consistent policy. The controller-manager and
scheduler are *clients* of the apiserver exactly like any kubectl user; they hold no
special API privilege beyond what their x509 identity grants through RBAC
(`system:kube-controller-manager`, `system:kube-scheduler`; see `pki-and-identity`).
That means a compromised scheduler cannot write to etcd directly, and a crashed
controller-manager does not take the API surface down with it. The three-way split
also localizes failure: a scheduling outage, a reconciliation outage, and an API
outage are three distinct, separately diagnosable events.

## KTHW implementation

All three units share the same skeleton (`ExecStart` a single binary with flags,
`Restart=on-failure`, `RestartSec=5`), but differ entirely in what flags, and
therefore what powers and secrets, each one carries.

### kube-apiserver

The apiserver unit is "fat": every flag is inline. The load-bearing ones:

> Quoted from KTHW (Apache-2.0): units/kube-apiserver.service

- **Only etcd talker**: `--etcd-servers=http://127.0.0.1:2379`
  (`units/kube-apiserver.service:16`). No other component opens an etcd connection;
  every read/write of cluster state funnels through here.
- **Authorization chain**: `--authorization-mode=Node,RBAC`
  (`units/kube-apiserver.service:12`). The Node authorizer scopes each kubelet to its
  own node's objects; RBAC handles everyone else.
- **Trust anchor for clients**: `--client-ca-file=/var/lib/kubernetes/ca.crt`
  (`units/kube-apiserver.service:14`). Every incoming client cert is verified against
  this CA; the cert's CN becomes the username and each O becomes a group.
- **Admission**: `--enable-admission-plugins=…,NodeRestriction,…`
  (`units/kube-apiserver.service:15`). `NodeRestriction` pairs with the Node
  authorizer so a compromised kubelet cannot edit other nodes' objects.
- **Encryption at rest**:
  `--encryption-provider-config=/var/lib/kubernetes/encryption-config.yaml`
  (`units/kube-apiserver.service:18`). Turns on Secret encryption in etcd (see
  `security-at-rest-and-rbac`).
- **Reverse trust to kubelets**: `--kubelet-client-certificate=…kube-api-server.crt`
  and `--kubelet-client-key=…kube-api-server.key`
  (`units/kube-apiserver.service:20`, `units/kube-apiserver.service:21`), with
  `--kubelet-certificate-authority=…ca.crt` (`units/kube-apiserver.service:19`) to
  verify the kubelet's serving cert. The apiserver **reuses its own keypair as a
  client cert** when it calls into kubelets for `logs`/`exec`/metrics. This is the
  subtle reverse direction the RBAC apply below exists to authorize.
- **Service-account token verification**:
  `--service-account-key-file=…service-accounts.crt`
  (`units/kube-apiserver.service:23`) holds the *public* half that verifies SA token
  signatures; `--service-account-issuer=https://server.kubernetes.local:6443`
  (`units/kube-apiserver.service:25`) sets the JWT issuer. The matching *private*
  signer lives in the controller-manager (below).
- **Serving cert**: `--tls-cert-file=…kube-api-server.crt`
  (`units/kube-apiserver.service:27`). The same `kube-api-server` cert (CN=`kubernetes`)
  is both the API's serving cert and the kubelet-client cert (see `pki-and-identity`).

**Secrets the apiserver holds:** the `kube-api-server` keypair (serving + kubelet
client) and the service-account *public* verification key. It does **not** hold
`ca.key`.

### kube-controller-manager

The controller-manager is where the cluster's most sensitive private keys live.

> Quoted from KTHW (Apache-2.0): units/kube-controller-manager.service

- **Holds the CA private key**: `--cluster-signing-cert-file=…ca.crt` and
  `--cluster-signing-key-file=…ca.key`
  (`units/kube-controller-manager.service:10`,
  `units/kube-controller-manager.service:11`). Because the CM signs CSRs (for example,
  kubelet serving certs), `ca.key` is copied to the `server` and read here. This is
  the only control-plane process trusted with the CA private key.
- **Holds the SA token signer**:
  `--service-account-private-key-file=…service-accounts.key`
  (`units/kube-controller-manager.service:14`). The CM signs service-account JWTs with
  this private key; the apiserver verifies them with the public half
  (`units/kube-apiserver.service:23`). Signer here, verifier there.
- **Roots SA trust**: `--root-ca-file=…ca.crt`
  (`units/kube-controller-manager.service:13`) is injected into every SA token secret
  so in-cluster pods can verify the apiserver.
- **Least privilege per loop**: `--use-service-account-credentials=true`
  (`units/kube-controller-manager.service:16`) makes each controller loop authenticate
  as its own service account.
- **Address coherence**: `--cluster-cidr=10.200.0.0/16`
  (`units/kube-controller-manager.service:8`) and
  `--service-cluster-ip-range=10.32.0.0/24`
  (`units/kube-controller-manager.service:15`) are the pod and service address spaces
  the CM must keep consistent (see `networking-model`).
- **Its own identity**: `--kubeconfig=…kube-controller-manager.kubeconfig`
  (`units/kube-controller-manager.service:12`) authenticates the CM to the apiserver as
  user `system:kube-controller-manager`.

**Secrets the CM holds:** `ca.key` (CSR signing) and `service-accounts.key` (SA token
signing). These are the crown jewels; the apiserver deliberately does not have them.

### kube-scheduler

The scheduler unit is "thin": it carries almost no flags and defers everything to a
config file.

> Quoted from KTHW (Apache-2.0): units/kube-scheduler.service

```
ExecStart=/usr/local/bin/kube-scheduler \
  --config=/etc/kubernetes/config/kube-scheduler.yaml \
```

The `--config` points at `kube-scheduler.yaml`
(`units/kube-scheduler.service:7`), which is just as small:

> Quoted from KTHW (Apache-2.0): configs/kube-scheduler.yaml

- `clientConnection.kubeconfig: "/var/lib/kubernetes/kube-scheduler.kubeconfig"`
  (`configs/kube-scheduler.yaml:4`), the scheduler's identity, user
  `system:kube-scheduler`.
- `leaderElection.leaderElect: true` (`configs/kube-scheduler.yaml:6`): harmless on a
  single-instance cluster, but the production-correct default for HA.

The scheduler holds **no special secrets**. Its entire authority comes from its RBAC
identity: it can read unscheduled pods and write pod/node bindings because the built-in
`system:kube-scheduler` ClusterRole grants exactly that, and nothing more.

### The apiserver → kubelet RBAC apply

Bootstrapping the three units is not enough. When you run `kubectl logs/exec/top`, the
**apiserver becomes a client of the kubelet** and must be authorized by the kubelet,
which in Webhook mode asks the apiserver itself via SubjectAccessReview
(`docs/08-bootstrapping-kubernetes-controllers.md:154`,
`docs/08-bootstrapping-kubernetes-controllers.md:156`). User `kubernetes` (the
apiserver's CN) has no such permission by default, so KTHW applies a ClusterRole and
binding:

> Quoted from KTHW (Apache-2.0): configs/kube-apiserver-to-kubelet.yaml

- ClusterRole `system:kube-apiserver-to-kubelet`
  (`configs/kube-apiserver-to-kubelet.yaml:8`) grants verbs `*`
  (`configs/kube-apiserver-to-kubelet.yaml:19`) on the kubelet subresources
  `nodes/proxy`, `nodes/stats`, `nodes/log`, `nodes/spec`, `nodes/metrics`
  (`configs/kube-apiserver-to-kubelet.yaml:13`).
- It is bound to **User `kubernetes`**
  (`configs/kube-apiserver-to-kubelet.yaml:33`) via `kubectl apply -f
  kube-apiserver-to-kubelet.yaml`
  (`docs/08-bootstrapping-kubernetes-controllers.md:167`).

Skip this apply and the cluster looks healthy while `kubectl logs/exec/top` return
403 Forbidden. Full trust-web detail lives in `pki-and-identity`.

### Startup ordering: by retry, not by declaration

The control-plane units do **not** declare systemd `After=`/`Requires=` dependencies;
their `[Unit]` sections carry only `Description`/`Documentation`. The apiserver depends
on etcd (`units/kube-apiserver.service:16`) but does not encode that as a unit
dependency. Ordering is achieved two ways: the start command lists the units in order
(`docs/08-bootstrapping-kubernetes-controllers.md:114`), and each unit's
`Restart=on-failure` / `RestartSec=5` (`units/kube-apiserver.service:30`) lets the
apiserver crash-and-retry until etcd is reachable. The lab even warns to allow ~10
seconds for the API server to initialize
(`docs/08-bootstrapping-kubernetes-controllers.md:119`). This is the opposite of the
worker stack, where the kubelet *does* declare `After=/Requires=containerd` (see
`worker-runtime-stack`).

## What managed K8s hides

EKS/GKE/AKS/kubeadm present "the control plane" as one opaque managed surface. KTHW
exposes what that surface actually is:

- **Three binaries, three identities, three failure modes.** Managed control planes
  give you one endpoint; here you can `systemctl status kube-scheduler` independently
  of the apiserver (`docs/08-bootstrapping-kubernetes-controllers.md:124`).
- **Where the private keys live.** Managed K8s never shows you that the
  controller-manager holds `ca.key` and the SA signing key while the apiserver does
  not. That asymmetry is invisible until you build it by hand.
- **The apiserver→kubelet reverse trust + RBAC binding** that makes `kubectl
  logs/exec` work (`configs/kube-apiserver-to-kubelet.yaml`). Managed clusters ship
  this binding pre-applied.
- **No declarative unit ordering.** Managed systems orchestrate component startup; here
  it is start-order plus restart-retry, and you see the apiserver bounce until etcd
  answers.

## Gotchas

- **Skipping the apiserver-to-kubelet RBAC apply.** The cluster comes up clean but
  `kubectl logs/exec/top` return 403 Forbidden, the single most common "everything
  works except observability" trap
  (`configs/kube-apiserver-to-kubelet.yaml:33`,
  `docs/08-bootstrapping-kubernetes-controllers.md:167`).
- **Confusing which process holds which secret.** `ca.key` and `service-accounts.key`
  live in the *controller-manager*
  (`units/kube-controller-manager.service:11`,
  `units/kube-controller-manager.service:14`), not the apiserver. Place them wrong and
  CSR signing or SA token signing silently fails.
- **Assuming systemd enforces ordering.** It does not for these units. If etcd is down,
  the apiserver does not "wait": it fails and is restarted on a 5-second loop
  (`units/kube-apiserver.service:30`). Watching `journalctl -u kube-apiserver`
  (`docs/08-bootstrapping-kubernetes-controllers.md:136`) during early bring-up shows
  the retries, which can look like a real failure if you do not expect them.
- **Treating the scheduler as privileged.** It holds no secrets; if scheduling breaks,
  the cause is almost always its RBAC identity
  (`configs/kube-scheduler.yaml:4`), not a missing credential.
- **"Encryption is on" without checking the apiserver flag.** Encryption at rest only
  applies because `--encryption-provider-config`
  (`units/kube-apiserver.service:18`) is set *and* the provider order is correct (see
  `security-at-rest-and-rbac`).

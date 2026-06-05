---
title: PKI & Identity (the TLS trust web)
type: knowledge
tags: [kubernetes, kthw, pki, tls, certificates, rbac, identity]
summary: One self-signed CA mints eight leaf certificates whose CN and O fields become Kubernetes usernames and groups, so x509 identity drives RBAC and the Node Authorizer with no extra config; the apiserver cert is both a serving cert and the client cert it presents back to kubelets.
status: active
source: https://github.com/kelseyhightower/kubernetes-the-hard-way
license: Apache-2.0, CC-BY-NC-SA-4.0
related: [index, kubeconfig-and-authn, control-plane-internals, security-at-rest-and-rbac]
confidence: high
---

# PKI & Identity (the TLS trust web)

## Concept

Every component-to-component call in Kubernetes is mutual TLS, and KTHW builds the whole trust system from one root. A single self-signed Certificate Authority (`CA:TRUE`, `ca.conf:7`; `CN = CA`, `ca.conf:14`) signs **eight leaf certificates**, one per identity in the cluster. The CA keypair is created with a 4096-bit key and a long validity (`openssl req -x509 ... -days 3653`, `docs/04-certificate-authority.md:22-28`); the eight leaves are then minted in a single loop that names each cert and pulls its definition from a matching `[section]` of `ca.conf` (`docs/04-certificate-authority.md:44-50` lists the set; `docs/04-certificate-authority.md:53-68` is the sign loop using `-section ${i}` and `-copy_extensions copyall`).

The single most important idea: **a cert's `CN` becomes a Kubernetes username and each `O` becomes a Kubernetes group.** Authorization is therefore downstream of x509 — you choose who someone *is* at cert-minting time.

The eight leaves, each from its own `ca.conf` section:

| # | Cert (section) | `CN` → username | `O` → group | Identity / role |
|---|---|---|---|---|
| 1 | admin (`ca.conf:16`) | `admin` (`ca.conf:22`) | `system:masters` (`ca.conf:23`) | cluster-admin via a built-in binding |
| 2 | service-accounts (`ca.conf:32`) | `service-accounts` (`ca.conf:38`) | — | SA-token signing keypair (no client identity) |
| 3 | node-0 (`ca.conf:49`) | `system:node:node-0` (`ca.conf:64`) | `system:nodes` (`ca.conf:65`) | kubelet identity **and** node serving cert |
| 4 | node-1 (`ca.conf:70`) | `system:node:node-1` (`ca.conf:85`) | `system:nodes` (`ca.conf:86`) | same, for node-1 |
| 5 | kube-proxy (`ca.conf:93`) | `system:kube-proxy` (`ca.conf:108`) | `system:node-proxier` (`ca.conf:109`) | proxy identity |
| 6 | kube-controller-manager (`ca.conf:116`) | `system:kube-controller-manager` (`ca.conf:131`) | `system:kube-controller-manager` (`ca.conf:132`) | controller-manager identity |
| 7 | kube-scheduler (`ca.conf:139`) | `system:kube-scheduler` (`ca.conf:154`) | `system:system:kube-scheduler` (`ca.conf:155`) | scheduler identity (note the doubled `system:` prefix) |
| 8 | kube-api-server (`ca.conf:168`) | `kubernetes` (`ca.conf:194`) | — | apiserver serving cert + apiserver-as-client-to-kubelet cert |

## Why it exists

Kubernetes consumes `CN`/`O` straight from the verified client cert, so the identities baked into the eight leaves wire up RBAC and the Node Authorizer with **zero extra YAML for most of them**:

- **admin → cluster-admin.** `O = system:masters` (`ca.conf:23`) hits a built-in ClusterRoleBinding that grants full cluster-admin. No RBAC object is written for the admin user; the group name alone is load-bearing.
- **kubelets → Node Authorizer.** The Node Authorizer only authorizes a kubelet if it presents group `system:nodes` with username `system:node:<nodeName>`. KTHW documents that contract inline at `ca.conf:42-47`, and the node-0/node-1 DN blocks (`ca.conf:64-65`, `ca.conf:85-86`) satisfy it exactly. This pairs with the apiserver's `--authorization-mode=Node,RBAC` (`units/kube-apiserver.service:12`) and the `NodeRestriction` admission plugin to keep one kubelet from editing another node's objects.
- **controllers / scheduler / proxy → built-in `system:*` roles.** Their `CN`s (`system:kube-controller-manager`, `system:kube-scheduler`, `system:kube-proxy`) line up with the default ClusterRoles shipped by Kubernetes, so each component gets exactly its own least-privilege identity.

The trust anchor that makes any of this fire is the apiserver's `--client-ca-file=/var/lib/kubernetes/ca.crt` (`units/kube-apiserver.service:14`): it is the single CA the apiserver trusts to verify presented client certs, and only after that verification does `CN`/`O` get mapped to user/group. The plain client certs default to `extendedKeyUsage = clientAuth` only (`ca.conf:200-203`), so they can authenticate but cannot serve.

## KTHW implementation

### The apiserver cert does double duty (serving + client)

The `kube-api-server` cert is the one leaf that is both a server cert and a client cert. Its extensions declare both roles:

> Quoted from KTHW (Apache-2.0): ca.conf
```ini
nsCertType = client, server   # ca.conf:177 (extendedKeyUsage = clientAuth, serverAuth at ca.conf:175)
```

**As a serving cert**, it must carry every name a client might dial. The Subject Alternative Names live in a dedicated block:

> Quoted from KTHW (Apache-2.0): ca.conf
```ini
[kube-api-server_alt_names]   # ca.conf:182
IP.0  = 127.0.0.1             # ca.conf:183
IP.1  = 10.32.0.1             # ca.conf:184  (first IP of the 10.32.0.0/24 service CIDR; the in-cluster `kubernetes` Service)
DNS.0 = kubernetes            # ca.conf:185
...
DNS.5 = server.kubernetes.local      # ca.conf:190
DNS.6 = api-server.kubernetes.local  # ca.conf:191
```

That cert is installed as the apiserver's serving cert via `--tls-cert-file`/`--tls-private-key-file` (`units/kube-apiserver.service:27-28`).

**As a client cert**, the *same file* is what the apiserver presents when it calls *into* a kubelet (for `kubectl logs/exec/top`, metrics, and node proxying). The unit reuses the identical keypair:

> Quoted from KTHW (Apache-2.0): units/kube-apiserver.service
```ini
--kubelet-client-certificate=/var/lib/kubernetes/kube-api-server.crt   # units/kube-apiserver.service:20
--kubelet-client-key=/var/lib/kubernetes/kube-api-server.key           # units/kube-apiserver.service:21
--kubelet-certificate-authority=/var/lib/kubernetes/ca.crt             # units/kube-apiserver.service:19
```

So when the apiserver dials a kubelet, the kubelet sees a client whose `CN = kubernetes`.

### The reverse-trust RBAC binding (or: why `kubectl logs` 403s without it)

The kubelet authenticates that incoming apiserver connection against the cluster CA, then asks the apiserver (webhook authz) whether user `kubernetes` is allowed to hit `nodes/log`, `nodes/proxy`, and friends. **That permission does not exist by default.** KTHW supplies it by applying a ClusterRole and binding it to the apiserver's identity:

> Quoted from KTHW (Apache-2.0): configs/kube-apiserver-to-kubelet.yaml
```yaml
kind: ClusterRole
name: system:kube-apiserver-to-kubelet   # configs/kube-apiserver-to-kubelet.yaml:8
# resources: nodes/proxy, nodes/stats, nodes/log, nodes/spec, nodes/metrics  (lines 13-17)
# verbs: "*"  (line 19)
---
subjects:
  - kind: User             # configs/kube-apiserver-to-kubelet.yaml:32
    name: kubernetes       # configs/kube-apiserver-to-kubelet.yaml:33
```

Without applying this (a step in control-plane bootstrap), the cluster looks healthy but `kubectl logs/exec/top` against any pod returns **403 Forbidden**. The binding name `system:kube-apiserver-to-kubelet` is bound to **User `kubernetes`** precisely because that is the `CN` of the apiserver cert.

### Distribution

The minted certs are scattered to where each component reads them: each node receives the cluster CA plus its own cert renamed to `kubelet.crt`/`kubelet.key` (`docs/04-certificate-authority.md:82-94`); the `server` receives `ca.key` (which the controller-manager uses to sign CSRs), the apiserver cert, and the `service-accounts` key/cert (`docs/04-certificate-authority.md:98-104`). ServiceAccount tokens are signed with `service-accounts.key`, not `ca.key` (`units/kube-apiserver.service:24`). The presence of `ca.key` on the control-plane node is what lets the controller-manager act as an online signer (see `control-plane-internals`).

## What managed K8s hides

EKS, GKE, AKS, and `kubeadm` generate and rotate this entire cert mesh for you, so most operators never see that x509 *is* the identity layer. What KTHW exposes:

- The cluster has exactly one root of trust, and you decide every identity at mint time through `CN`/`O`.
- RBAC and the Node Authorizer are **downstream** of certificates; `O = system:masters` granting cluster-admin is a property of a string in a cert, not a console toggle.
- The apiserver→kubelet channel is a real client/server TLS hop with its own RBAC, not magic plumbing — and it is opt-in (the `system:kube-apiserver-to-kubelet` binding).
- Cert/SAN rotation, which managed control planes do invisibly, is a manual `openssl` exercise here.

## Gotchas

- **Missing SANs.** If the apiserver cert omits a name a client uses (e.g. `server.kubernetes.local` or `10.32.0.1`), that client fails TLS with `x509: certificate is valid for X, not Y`. The full required set is `ca.conf:182-191`.
- **Wrong `O` group → silent RBAC denial.** A kubelet cert that is not `O = system:nodes` / `CN = system:node:<name>` is rejected by the Node Authorizer even though TLS succeeds; the failure surfaces as authorization errors, not cert errors.
- **Forgetting the apiserver→kubelet binding.** Everything schedules and runs, but `kubectl logs/exec/top` returns 403 until `configs/kube-apiserver-to-kubelet.yaml` is applied.
- **The doubled scheduler `O` is an inert typo.** `O = system:system:kube-scheduler` (`ca.conf:155`) is a genuine double-prefix typo, but it changes nothing: the scheduler is authorized by its **username** `system:kube-scheduler` (`CN`, `ca.conf:154`), which the default `system:kube-scheduler` ClusterRoleBinding binds as a `User`, not a group. No built-in binding consults that `O` group, so removing or fixing the doubled prefix would not affect authorization. Contrast `admin`, where `O = system:masters` *is* the group that grants cluster-admin.
- **`clientAuth`-only defaults.** The generic client certs use `default_req_extensions` with `extendedKeyUsage = clientAuth` only (`ca.conf:200-203`); they cannot be used as serving certs. Only node certs and the apiserver cert carry `serverAuth`.

## Trust web (text diagram)

```
                         self-signed root
                         ca.crt / ca.key            (CN=CA, CA:TRUE, ca.conf:7,14)
                                │ signs all 8 leaves
   ┌─────────────┬─────────────┼───────────────┬──────────────────────┬───────────────┐
   │             │             │               │                      │               │
 admin       kube-proxy   kube-controller-   kube-scheduler      kube-api-server   node-0 / node-1
 CN=admin    CN=system:    manager           CN=system:          CN=kubernetes     CN=system:node:N
 O=system:   kube-proxy    CN/O=system:      kube-scheduler      (no O)            O=system:nodes
 masters     O=system:     kube-controller-  O=system:system:    SANs:             (+ service-accounts
             node-proxier  manager           kube-scheduler      127.0.0.1,         CN=service-accounts,
                                                                 10.32.0.1,         used only to sign/
                                                                 *.kubernetes.local SA tokens)
   │             │             │               │                  │  ▲                  │
   │ client      │ client      │ client        │ client           │  │ serving cert     │ kubelet serving
   ▼             ▼             ▼               ▼          serving  ▼  │ to all clients   ▼ + client cert
 kubectl ──────────────────────────────────────────────►  kube-apiserver ◄──────────── kubelet (node-0/1)
                                                                ▲   │
                                  apiserver as CLIENT presents  │   │  presents kube-api-server.crt
                                  kube-api-server.crt (CN=kubernetes) │  → kubelet authn via ca.crt,
                                  authorized by ClusterRole           │  authz via webhook → 403 unless
                                  system:kube-apiserver-to-kubelet ───┘  the binding exists

 verification anchor: apiserver --client-ca-file=ca.crt (units/kube-apiserver.service:14)
                      maps verified cert CN→username, O→group, then Node,RBAC decides (line 12)
```

> Trust web above is original synthesis. CN/O/SAN values are facts from `ca.conf`; flag and binding facts from `units/kube-apiserver.service` and `configs/kube-apiserver-to-kubelet.yaml` (Apache-2.0).

See also: `kubeconfig-and-authn` (how each identity is packaged for a client), `control-plane-internals` (who holds `ca.key` and the SA signing key), and `security-at-rest-and-rbac` (the RBAC layer these identities feed).

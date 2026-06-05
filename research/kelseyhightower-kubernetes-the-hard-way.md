---
title: Kubernetes The Hard Way — Expert Knowledge Synthesis
type: research
tags: [kubernetes, kthw, kelseyhightower, k8s-internals, pki, tls, etcd, kubelet, systemd, cni, rbac, encryption-at-rest, teaching, skill-source]
summary: Expert reference distilled from the post-GCP (v1.32) edition of Kelsey Hightower's Kubernetes The Hard Way — the 13-step bootstrap arc, every component's systemd unit + config, the full PKI/TLS trust web from ca.conf, and a knowledge taxonomy for packaging into a skill.
status: active
source: github-researcher
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

# Kubernetes The Hard Way — Expert Knowledge Synthesis

> Repo on disk: `/Users/alphab/Dev/LLM/DEV/helioy/REFS/kubernetes-the-hard-way`
> All file:line citations below point into that tree.

---

## 1. What this is & current era

Kubernetes The Hard Way (KTHW) is Kelsey Hightower's canonical pedagogical tutorial that bootstraps a Kubernetes cluster by hand, with **no scripts and no installer**, so the learner internalizes every moving part that `kubeadm`/EKS/GKE hide. The current era is **post-GCP and cloud-agnostic**: earlier versions provisioned Google Compute Engine VMs, load balancers, and VPC routes via `gcloud`; the present edition (`docs/13-cleanup.md:7`) is "agnostic — all configuration is performed on the `jumpbox`, `server`, or nodes." It runs on **four plain Debian 12 (bookworm) ARM64 or AMD64 machines** (`docs/01-prerequisites.md:7`): a `jumpbox` (admin/home base), a single `server` (the *entire* control plane on one node), and two workers `node-0` / `node-1`. There is no HA control plane and no cloud provider integration; `LoadBalancer` Services are explicitly out of scope (`docs/12-smoke-test.md:162`).

Component versions (`README.md:22-25`): Kubernetes **v1.32.x** (binaries pinned to v1.32.3 in `downloads-*.txt`), containerd **v2.1.x** (2.1.0-beta.0), CNI plugins **v1.6.x** (v1.6.2), etcd **v3.6.x** (v3.6.0-rc.3), runc v1.3.0-rc.1, crictl v1.32.0. The whole doc corpus is ~6,400 words across 13 markdown labs.

**Stats (fetched 2026-06-05 via `gh api`):** ~48,500 stars, ~15,700 forks, 49 open issues, ~44 contributor pages (hundreds of contributors), last push **2025-04-10**, default branch `master`. **Dual license** (important, see §8): the *code* artifacts (`configs/`, `units/`, `ca.conf`) are **Apache-2.0** (`LICENSE`), while the *prose/documentation* (README, COPYRIGHT.md, the `docs/*.md` labs) is **CC BY-NC-SA 4.0** (`README.md:9`, `COPYRIGHT.md:3`).

---

## 2. The 13-step arc as a mental model

This is the spine. Each step: **what you do** / **why it exists — what breaks without it**.

1. **Prerequisites** (`docs/01`) — Confirm 4 Debian 12 VMs with the right CPU/RAM/disk (jumpbox 512MB, server + each node 2GB). *Why:* KTHW pins an exact OS and arch so every later command (apt packages, binary arch, systemd) is reproducible. Without a known baseline, kernel modules and `dpkg --print-architecture` branching break.

2. **Set up the jumpbox** (`docs/02`) — Install `wget curl vim openssl git`, clone the repo, download ~500MB of binaries once into `downloads/`, untar and sort them into `client/ controller/ worker/ cni-plugins/`, install `kubectl`. *Why:* one download host conserves bandwidth and gives a single source of truth for binaries pushed to every node. Without the sorted layout, later `scp downloads/controller/*` / `downloads/worker/*` copy steps have nothing to grab.

3. **Provision compute resources** (`docs/03`) — Create `machines.txt` (the "machine database": `IPV4 FQDN HOSTNAME POD_SUBNET` per line), enable root SSH, distribute SSH keys, set hostnames, and **append a shared `/etc/hosts` block to the jumpbox and all three nodes**. *Why:* this is the DNS substitute for the whole tutorial. Clients address the API server as `server.kubernetes.local`, not an IP; workers register by hostname. Without consistent `/etc/hosts` + hostnames, TLS SAN validation and kubelet node registration both fail. `machines.txt` is read by `while read IP FQDN HOST SUBNET` loops in steps 3, 5, 9, 11 — it is the cluster's source of truth for topology.

4. **Provision the CA & generate TLS certs** (`docs/04`) — Use `openssl` + `ca.conf` to self-sign a CA (`ca.key`/`ca.crt`, 4096-bit, valid 3653 days) then mint **8 leaf certs** (admin, node-0, node-1, kube-proxy, kube-scheduler, kube-controller-manager, kube-api-server, service-accounts), each from its own `[section]` in `ca.conf`. Distribute kubelet certs to the nodes, apiserver/CA/service-account certs to the server. *Why:* every component-to-component call in Kubernetes is mutual TLS. The CA is the single root of trust; the **CN/O fields baked here drive RBAC later** (§4). Without correct SANs and CN/O, the apiserver rejects clients or clients reject the server's hostname.

5. **Generate kubeconfigs** (`docs/05`) — Wrap each client cert + the CA + the server URL into a kubeconfig (`kubectl config set-cluster/set-credentials/set-context`) for kubelet (node-0, node-1), kube-proxy, kube-controller-manager, kube-scheduler, and admin. *Why:* a kubeconfig is the portable bundle a component reads to know *where* the API server is and *how* to authenticate. The cert chosen determines the identity the apiserver sees. Note the server URL split: components use `https://server.kubernetes.local:6443`; admin uses `https://127.0.0.1:6443` (it runs *on* the server in step 8) until step 10 re-points it.

6. **Generate the data-encryption config & key** (`docs/06`) — `head -c 32 /dev/urandom | base64` → `ENCRYPTION_KEY`, `envsubst` it into `encryption-config.yaml`, ship to the server. *Why:* enables **encryption of Secrets at rest in etcd**. Without it, anyone with etcd/disk access reads Secrets in plaintext. The smoke test (step 12) proves it worked by hexdumping the raw etcd value.

7. **Bootstrap etcd** (`docs/07`) — Install `etcd`/`etcdctl`, drop `etcd.service`, start a **single-member** etcd listening on localhost (127.0.0.1:2379 client, :2380 peer). *Why:* etcd is the *only* stateful component; every other K8s process is stateless and stores all cluster state here. Single-node = no quorum/HA, deliberately simplified. Without etcd up first, the apiserver cannot start.

8. **Bootstrap the control plane** (`docs/08`) — Install kube-apiserver, kube-controller-manager, kube-scheduler on `server`; place certs/kubeconfigs/encryption-config; drop systemd units; start all three. Then `kubectl apply` the `system:kube-apiserver-to-kubelet` ClusterRole + binding. *Why:* this is the brain. The RBAC apply is what lets the apiserver call back into kubelets for logs/exec/metrics (§4). Without it, `kubectl logs/exec/top` against pods returns 403.

9. **Bootstrap the workers** (`docs/09`) — Per node: install runc, CNI plugins, containerd, kubelet, kube-proxy; template `10-bridge.conf` and `kubelet-config.yaml` with that node's `SUBNET`; load `br-netfilter`, set bridge sysctls; disable swap; start containerd → kubelet → kube-proxy. *Why:* this is where containers actually run. The per-node SUBNET templating is what gives each node a non-overlapping pod CIDR. Without `br-netfilter` + the iptables sysctls, bridged pod traffic bypasses kube-proxy's iptables rules and Services break.

10. **Configure kubectl for remote access** (`docs/10`) — Build a default `~/.kube/config` on the jumpbox pointing at `https://server.kubernetes.local:6443` with the admin cert. *Why:* lets you drive the cluster from the jumpbox over the network (vs. SSHing into the server). Relies on the step-3 `/etc/hosts` entry to resolve the hostname and the step-4 SAN to validate it.

11. **Provision pod network routes** (`docs/11`) — Add **static `ip route` entries** so each node knows that another node's pod CIDR (`10.200.0.0/24`, `10.200.1.0/24`) is reachable `via` that node's host IP. *Why:* KTHW's `bridge` CNI only wires pods *within* a node. Cross-node pod-to-pod traffic needs L3 routes that a real CNI (Calico/Cilium/flannel) would normally install dynamically. Without these routes, a pod on node-0 cannot reach a pod on node-1. This is the single most illuminating "managed K8s hides this" moment.

12. **Smoke test** (`docs/12`) — Prove: (a) **encryption at rest** by hexdumping a Secret from etcd and seeing the `k8s:enc:aescbc:v1:key1` prefix; (b) Deployments (nginx); (c) port-forward; (d) logs; (e) exec; (f) NodePort Service. *Why:* each check exercises a different subsystem (etcd encryption, scheduler, kubelet/containerd, apiserver→kubelet RBAC, kube-proxy). It is a diagnostic matrix, not a demo.

13. **Cleanup** (`docs/13`) — Delete the VMs. *Why:* state lives only on the four machines; there are no cloud resources to deprovision in this era.

---

## 3. Component deep-dives

For each: job · the exact unit + config that runs it · the flags that matter and why.

### etcd
**Job:** the cluster's only datastore; holds all API objects and cluster state. **Runs via** `units/etcd.service` (no separate config file; all flags inline). **Key flags** (`units/etcd.service:7-16`): `--name controller` (member name, must be unique in cluster); `--listen-client-urls`/`--advertise-client-urls http://127.0.0.1:2379` and peer URLs on `:2380`; `--initial-cluster controller=http://127.0.0.1:2380` with `--initial-cluster-state new`; `--data-dir=/var/lib/etcd`. **What matters:** everything is **plaintext HTTP on localhost** — no TLS, no auth — because the apiserver is co-located on the same box (`--etcd-servers=http://127.0.0.1:2379`). This is a teaching simplification; production etcd uses client/peer TLS and multi-member quorum. `Type=notify` means systemd waits for etcd's readiness signal.

### kube-apiserver
**Job:** the front door — the only component that talks to etcd; serves the REST API, does authn/authz, admission, and encryption. **Runs via** `units/kube-apiserver.service`. **Key flags** (`units/kube-apiserver.service:6-29`):
- `--authorization-mode=Node,RBAC` — two authorizers chained: Node authorizer scopes what each kubelet can read (only its own node's objects), RBAC handles everything else.
- `--client-ca-file=/var/lib/kubernetes/ca.crt` — the trust anchor for *verifying every client cert*; the client's CN becomes the username, O becomes the group.
- `--encryption-provider-config=.../encryption-config.yaml` — turns on at-rest Secret encryption.
- `--kubelet-client-certificate`/`--kubelet-client-key=.../kube-api-server.{crt,key}` — the cert the apiserver **presents to kubelets** when it calls them (logs/exec/metrics). Reuses the apiserver's own keypair as a client cert.
- `--kubelet-certificate-authority=.../ca.crt` — verifies kubelet serving certs.
- `--service-account-key-file=service-accounts.crt` (verify SA token signatures) and `--service-account-signing-key-file=service-accounts.key` + `--service-account-issuer=https://server.kubernetes.local:6443`.
- `--enable-admission-plugins=NamespaceLifecycle,NodeRestriction,LimitRanger,ServiceAccount,DefaultStorageClass,ResourceQuota` — NodeRestriction pairs with the Node authorizer to stop a compromised kubelet editing other nodes.
- `--service-cluster-ip-range` implied via `10.32.0.0/24`; `--service-node-port-range=30000-32767`; `--tls-cert-file/--tls-private-key-file=kube-api-server.{crt,key}` (serving cert).

### kube-controller-manager
**Job:** runs the control loops (node, replicaset, deployment, service-account-token, CSR signing, etc.) that reconcile desired vs. actual state. **Runs via** `units/kube-controller-manager.service`; auth via `kube-controller-manager.kubeconfig`. **Key flags** (`units/kube-controller-manager.service:6-17`):
- `--cluster-cidr=10.200.0.0/16` and `--service-cluster-ip-range=10.32.0.0/24` — the two address spaces it must keep coherent (pods vs. services).
- `--cluster-signing-cert-file=ca.crt` + `--cluster-signing-key-file=ca.key` — **the CM holds the CA private key** so it can sign CSRs (e.g., kubelet serving certs). This is why `ca.key` is copied to the server in step 8.
- `--service-account-private-key-file=service-accounts.key` — signs SA tokens (the matching public half is the apiserver's `--service-account-key-file`).
- `--root-ca-file=ca.crt` — injected into every SA's token secret so pods can verify the apiserver.
- `--use-service-account-credentials=true` — each controller loop uses its own SA, enabling least-privilege.

### kube-scheduler
**Job:** watches for unscheduled pods and binds each to a node via predicates/priorities. **Runs via** `units/kube-scheduler.service`, which is thin (`--config=/etc/kubernetes/config/kube-scheduler.yaml`). **Config** (`configs/kube-scheduler.yaml`): `clientConnection.kubeconfig` points at `kube-scheduler.kubeconfig`; `leaderElection.leaderElect: true` (harmless on a single node, but the production-correct default for HA). The scheduler holds no special secrets; its power comes entirely from its RBAC identity `system:kube-scheduler`.

### kubelet
**Job:** the node agent — registers the node, watches the apiserver for pods assigned to it, drives containerd to run them, reports status, and serves logs/exec/metrics. **Runs via** `units/kubelet.service` (note `After=/Requires=containerd.service` — ordering matters) → `--config=/var/lib/kubelet/kubelet-config.yaml` + `--kubeconfig`. **Config** (`configs/kubelet-config.yaml`):
- `authentication.anonymous.enabled: false`, `webhook.enabled: true`, `x509.clientCAFile: ca.crt` — the kubelet authenticates *incoming* apiserver calls via the cluster CA and delegates authz to the apiserver.
- `authorization.mode: Webhook` — every request to the kubelet API is checked via SubjectAccessReview against the apiserver (this is why the step-8 RBAC ClusterRole is required).
- `cgroupDriver: systemd`, `containerRuntimeEndpoint: unix:///var/run/containerd/containerd.sock` — must match containerd's `SystemdCgroup = true`.
- `tlsCertFile/tlsPrivateKeyFile: kubelet.{crt,key}` — its serving cert (the per-node `node-0.crt`/`node-1.crt`).
- `maxPods: 16`, `failSwapOn: false`, `swapBehavior: NoSwap`, `resolvConf: /etc/resolv.conf`, `registerNode: true`.

### kube-proxy
**Job:** programs the node's dataplane so Service ClusterIPs/NodePorts load-balance to pod endpoints. **Runs via** `units/kube-proxy.service` → `--config=/var/lib/kube-proxy/kube-proxy-config.yaml`. **Config** (`configs/kube-proxy-config.yaml`): `mode: "iptables"`, `clusterCIDR: "10.200.0.0/16"`, kubeconfig at `/var/lib/kube-proxy/kubeconfig`. **What matters:** iptables mode writes NAT/filter rules; it only works because step 9 loaded `br-netfilter` and set `net.bridge.bridge-nf-call-iptables=1`, so bridged pod traffic is seen by iptables.

### containerd + CNI
**Job:** containerd is the CRI runtime kubelet talks to; it uses runc to spawn containers and invokes CNI plugins to wire pod networking. **Runs via** `units/containerd.service` (`ExecStartPre=/sbin/modprobe overlay`, `Delegate=yes`, `OOMScoreAdjust=-999`) → `/etc/containerd/config.toml`. **Config** (`configs/containerd-config.toml`): `snapshotter = "overlayfs"`, `default_runtime_name = "runc"`, `runtime_type = "io.containerd.runc.v2"`, **`SystemdCgroup = true`** (must match kubelet's `cgroupDriver: systemd` or pods crash-loop), and CNI `bin_dir = /opt/cni/bin` / `conf_dir = /etc/cni/net.d`. **CNI:** two conf files — `configs/10-bridge.conf` (a `bridge` plugin, `cni0`, `isGateway: true`, `ipMasq: true`, `host-local` IPAM over the node's templated `SUBNET`, default route) and `configs/99-loopback.conf` (the `lo` plugin). The bridge handles intra-node pod IPs; cross-node reachability is the *static routes* of step 11, not CNI.

---

## 4. The PKI / TLS trust web (the hardest, most valuable part)

Everything flows from one self-signed CA (`ca.crt`/`ca.key`, CN=`CA`, `ca.conf:14`). Each leaf cert's **CN → Kubernetes username** and **O → Kubernetes group**, and those identities are what RBAC/Node-authorizer act on. The certs come from named sections in `ca.conf`.

### Every certificate (from `ca.conf`)

| Cert (section) | CN (→ user) | O (→ group) | Role | Presented by → to |
|---|---|---|---|---|
| CA (`[req]`) | `CA` | — | root of trust | n/a (signs all) |
| admin (`[admin]`, `ca.conf:16-23`) | `admin` | **`system:masters`** | cluster-admin | kubectl/admin → apiserver |
| node-0 (`[node-0]`, `:49-68`) | **`system:node:node-0`** | **`system:nodes`** | kubelet identity + serving cert | kubelet → apiserver, and serves apiserver |
| node-1 (`[node-1]`, `:70-89`) | `system:node:node-1` | `system:nodes` | same, node-1 | same |
| kube-proxy (`:92-112`) | `system:kube-proxy` | `system:node-proxier` | proxy identity | kube-proxy → apiserver |
| kube-controller-manager (`:115-135`) | `system:kube-controller-manager` | `system:kube-controller-manager` | CM identity | CM → apiserver |
| kube-scheduler (`:138-158`) | `system:kube-scheduler` | `system:system:kube-scheduler` (note doubled prefix, a known quirk) | scheduler identity | scheduler → apiserver |
| kube-api-server (`:168-197`) | `kubernetes` | — | apiserver serving + kubelet-client cert | apiserver → clients & apiserver → kubelets |
| service-accounts (`:32-38`) | `service-accounts` | — | SA token signing keypair | CM signs / apiserver verifies tokens |

**Why CN/O matter:** Kubernetes maps the cert's CN to a username and each O to a group *with zero extra config*. So `O=system:masters` (admin) hits a built-in ClusterRoleBinding granting cluster-admin — no RBAC YAML needed for the admin. `system:nodes` + `system:node:<name>` is the exact contract the **Node Authorizer** requires (documented inline at `ca.conf:42-47`): a kubelet is only authorized if it presents that group+username pattern. The other `system:*` users line up with built-in controller/scheduler/proxy ClusterRoles.

**SANs that matter:** The apiserver cert's `subjectAltName` (`ca.conf:182-191`) must list every name clients use: `127.0.0.1`, `10.32.0.1` (the first IP of the service CIDR — the in-cluster `kubernetes` Service), `kubernetes[.default[.svc[.cluster[.local]]]]`, `server.kubernetes.local`, `api-server.kubernetes.local`. Omit any one and the corresponding client connection fails TLS verification. This is the #1 source of "x509: certificate is valid for … not …" errors.

### Kubeconfig generation (step 05) — which cert goes where, and why

A kubeconfig bundles **{CA cert (to trust the server)} + {a client cert+key (the identity)} + {server URL}**. Step 5 builds one per consumer (`docs/05`):
- **node-0/node-1 kubeconfig** → embeds `node-N.crt/key` under user `system:node:node-N`, server `https://server.kubernetes.local:6443`. *Why this cert:* only the matching per-node cert satisfies the Node Authorizer for that node.
- **kube-proxy.kubeconfig** → `kube-proxy.crt/key`, user `system:kube-proxy`.
- **kube-controller-manager.kubeconfig** / **kube-scheduler.kubeconfig** → their respective certs/users.
- **admin.kubeconfig** → `admin.crt/key`, but **server `https://127.0.0.1:6443`** because in step 8 the admin runs *on* the server before remote access exists. Step 10 generates a *second* admin kubeconfig pointing at the hostname for jumpbox use.

All use `--embed-certs=true` so the kubeconfig is self-contained and copyable to another host.

### The apiserver → kubelet client cert (the subtle reverse direction)

Most certs are clients calling *into* the apiserver. The exception: when you run `kubectl logs/exec/top`, the **apiserver becomes a client of the kubelet**. It presents `kube-api-server.crt` (`--kubelet-client-certificate`, `units/kube-apiserver.service:20`) — CN=`kubernetes` — to the kubelet. The kubelet authenticates it via `clientCAFile: ca.crt`, then asks the apiserver (Webhook authz) whether user `kubernetes` may hit `nodes/log`, `nodes/proxy`, etc. That permission does **not** exist by default, which is why `configs/kube-apiserver-to-kubelet.yaml` creates a ClusterRole `system:kube-apiserver-to-kubelet` (verbs `*` on `nodes/proxy|stats|log|spec|metrics`) and binds it to **User `kubernetes`** (`configs/kube-apiserver-to-kubelet.yaml:32-34`). Without this apply (step 8), `kubectl logs` returns 403 Forbidden.

### Trust web, as text

```
                         self-signed
                         ca.crt / ca.key  (CN=CA)
                              │ signs all leaves
        ┌─────────────────────┼─────────────────────────────────────┐
        │                     │                                      │
   admin.crt            kube-api-server.crt                    node-0.crt / node-1.crt
 (CN=admin,            (CN=kubernetes; SANs incl.              (CN=system:node:node-N,
  O=system:masters)     server.kubernetes.local, 10.32.0.1)     O=system:nodes)
        │                     │   ▲                                   │
        │ client              │   │ serving cert to all clients       │ kubelet serving cert
        ▼                     ▼   │                                   ▼  + kubelet client cert
   kubectl ───────────► kube-apiserver ◄──────────────────────── kubelet (node-0/1)
                          ▲  ▲  ▲  │ (apiserver as CLIENT, presents
                          │  │  │  │  kube-api-server.crt → kubelet:
   kube-controller-manager│  │  │  │  authz via ClusterRole
   (system:kube-controller-manager) │  system:kube-apiserver-to-kubelet)
   kube-scheduler ────────┘  │  │
   (system:kube-scheduler)   │  │
   kube-proxy ───────────────┘  │
   (system:kube-proxy,          │
    O=system:node-proxier)      │
                                ▼
   service-accounts.key (sign SA tokens, in CM) ⇄ service-accounts.crt (verify, in apiserver)
   etcd ⇄ apiserver: PLAINTEXT http://127.0.0.1:2379 (no TLS — co-located, teaching simplification)
```

---

## 5. Cross-cutting concepts

### Encryption at rest (step 06 + `configs/encryption-config.yaml`)
`EncryptionConfiguration` declares, for `resources: [secrets]`, a provider list `[aescbc(key1=$ENCRYPTION_KEY), identity]`. **Order is semantically critical:** the *first* provider encrypts new writes; *all* listed providers can decrypt. With `aescbc` first, Secrets are AES-CBC encrypted; `identity` last is the plaintext fallback for reading legacy data. Flip the order (`identity` first) and you silently *disable* encryption. The key is 32 random bytes base64'd (`docs/06:12`), wired into the apiserver via `--encryption-provider-config`. Step 12 proves it: the etcd value for `/registry/secrets/default/...` is prefixed `k8s:enc:aescbc:v1:key1` (`docs/12:49`) instead of readable YAML. **Caveat taught implicitly:** only `secrets` are encrypted here; ConfigMaps and other objects remain plaintext in etcd.

### Pod network routes (step 11) — why static routes substitute for a real CNI
**Pod CIDR layout:** the whole pod space is `10.200.0.0/16` (`--cluster-cidr`); each node owns a `/24` slice — node-0 = `10.200.0.0/24`, node-1 = `10.200.1.0/24` (from `machines.txt` col 4, templated into `10-bridge.conf`). The Service CIDR is a *separate* space, `10.32.0.0/24`, with `10.32.0.1` reserved for the in-cluster `kubernetes` Service. The `bridge` CNI gives pods IPs within their node's `/24` but knows nothing about other nodes. KTHW substitutes a **real CNI's cross-node data path with three static `ip route add <other-node-CIDR> via <other-node-IP>` commands** (`docs/11:26-42`) on the server and each node. A production CNI (Calico/Cilium/flannel) installs these routes (or an overlay) automatically and dynamically; doing it by hand is the lesson — it makes the Kubernetes networking model ("every pod gets a routable IP, no NAT between pods") concrete.

### The systemd bootstrapping model
There is **no kubelet static-pod / self-hosting**: every K8s process is a plain systemd service (`units/*.service`), `enable`d + `start`ed directly. Patterns worth noting: thin units that delegate to a `--config` YAML (scheduler, kubelet, kube-proxy) vs. fat units with all flags inline (apiserver, controller-manager, etcd); uniform `Restart=on-failure` / `RestartSec=5`; explicit ordering only where it matters (`kubelet After=/Requires=containerd`); containerd's resource-isolation directives (`Delegate=yes`, `KillMode=process`, `OOMScoreAdjust=-999`, raised `LimitNOFILE`). Debugging is `systemctl is-active/status` + `journalctl -u <svc>` (`docs/08:124-137`).

---

## 6. What "the hard way" teaches that managed K8s hides

EKS/GKE/AKS/kubeadm abstract all of the following; KTHW forces you to confront each:

- **The PKI is the cluster's identity system.** Managed K8s auto-rotates a cert mesh you never see. KTHW shows that CN=user, O=group, and that RBAC is downstream of x509. (`ca.conf`)
- **etcd is the whole truth and is just a process.** Managed control planes hide etcd entirely; here it's one localhost service you can `etcdctl get` against (`docs/07`, `docs/12`).
- **The control plane is three independent binaries, not "the control plane."** apiserver / controller-manager / scheduler have distinct identities, kubeconfigs, and failure modes (`docs/08`).
- **Node Authorizer + NodeRestriction.** Why a kubelet's cert *must* be `system:node:<name>`/`system:nodes` (`ca.conf:42-47`).
- **The apiserver→kubelet reverse trust + RBAC binding** that makes `kubectl logs/exec` work (`configs/kube-apiserver-to-kubelet.yaml`).
- **Encryption at rest is opt-in and provider-ordered.** Secrets are plaintext in etcd until you configure it, and only the resources you list (`configs/encryption-config.yaml`).
- **Pod networking = routable IPs + a route to every pod CIDR.** A CNI's job is demystified into "bridge + static routes" (`docs/11`).
- **cgroup driver and runtime endpoint must agree** between kubelet and containerd or nothing schedules (`SystemdCgroup`/`cgroupDriver`).
- **kube-proxy needs bridge-netfilter sysctls** or Service iptables rules silently don't apply to pod traffic (`docs/09:116-133`).
- **Service-account tokens are a signed-JWT system** with a private signer in the CM and a public verifier in the apiserver (`ca.conf:25-38`, two CM/apiserver flags).
- **No cloud LoadBalancer / cloud provider** means NodePort is your only external entry and cross-node routing is manual (`docs/12:162`).

---

## 7. Common failure points & gotchas

- **Cert SAN mismatches** — the apiserver cert must SAN-list every name a client uses (`server.kubernetes.local`, `10.32.0.1`, `127.0.0.1`, the `kubernetes.*` DNS set). Missing one → `x509: certificate is valid for X, not Y`. (`ca.conf:182-191`)
- **`/etc/hosts` + hostname drift** — if `machines.txt`, the appended `/etc/hosts` block, and `hostnamectl` disagree, kubelets register under the wrong name and SAN/Node-authorizer checks fail. (`docs/03`)
- **Wrong kubelet cert CN/O** — anything other than `system:node:<name>` + `O=system:nodes` is rejected by the Node Authorizer.
- **kube-scheduler O quirk** — `O=system:system:kube-scheduler` (doubled prefix) in `ca.conf:155`; matches the built-in binding, but looks like a typo and trips people who "fix" it.
- **Encryption provider order** — putting `identity` before `aescbc` disables encryption silently; the only signal is the missing `k8s:enc:aescbc` prefix in step 12.
- **cgroup driver mismatch** — kubelet `cgroupDriver: systemd` must equal containerd `SystemdCgroup = true`, else pods crash-loop with cgroup errors.
- **Missing `br-netfilter` / bridge sysctls** — Services appear up but pod traffic bypasses kube-proxy iptables; symptoms look like DNS/Service flakiness. (`docs/09:116-133`)
- **Skipping the apiserver-to-kubelet RBAC apply** — cluster looks healthy but `kubectl logs/exec/top` return 403. (`docs/08:160-169`)
- **systemd ordering** — kubelet starting before containerd (missing `After=/Requires=`) yields CRI connection errors.
- **Forgetting the static pod routes (step 11)** — intra-node pods work, cross-node pod-to-pod hangs; the most confusing "half-working" state.
- **etcd plaintext localhost** — fine here, but a trap if anyone copies these units toward production without adding TLS/quorum.
- **admin kubeconfig server URL** — the step-5 admin config uses `127.0.0.1` (on-server); using it from the jumpbox fails until step 10's hostname-based config exists.

---

## 8. Licensing implications

**Dual-licensed repo — this is the crux for packaging.**
- **Prose/docs** (`docs/*.md`, `README.md`, `COPYRIGHT.md`) → **CC BY-NC-SA 4.0** (`README.md:9`).
- **Code artifacts** (`configs/`, `units/`, `ca.conf`) → **Apache-2.0** (`LICENSE` file).

What this means if we package derived knowledge into a Helioy skill:

- **Original synthesis is freely usable.** Facts, the bootstrap sequence, "the apiserver reuses its cert as a kubelet client" — these are *uncopyrightable facts and procedures*. A skill written in our own words, explaining the same concepts, carries **no license obligation** and can be commercial/closed. This document is exactly that: original synthesis, safe to build on.
- **Copied prose triggers CC BY-NC-SA 4.0** in full: (a) **Attribution** to Kelsey Hightower + link to the work and license; (b) **NonCommercial** — cannot be used in a commercial/paid product or paywalled context; (c) **ShareAlike** — any derivative *of the prose* must be relicensed CC BY-NC-SA 4.0. The NC term is the killer for a commercial skill: do **not** paste doc paragraphs into a sellable artifact.
- **Copying config/unit files** (Apache-2.0) is fine even commercially, but requires preserving the license/notice and is **Apache-2.0, not CC** — keep the two buckets mentally separate.
- **Practical rule for the skill:** teach the *concepts* in our own prose (no obligation), cite KTHW as the source/inspiration as a courtesy and for credibility, and **never reproduce doc text verbatim** in any commercial Helioy surface. If we ever want to quote a lab snippet, quote the Apache-2.0 config/unit (with notice), not the CC-NC prose.

---

## 9. Knowledge taxonomy for skill / cm packaging

Proposed grouping of the teachable units into 9 coherent modules (names + scope). This is the chunking for part 2 of the parent task.

1. **`k8s-topology-and-bootstrap-model`** — the 4-machine layout (jumpbox/server/2 workers), the post-GCP cloud-agnostic era, `machines.txt` as topology source of truth, the 13-step arc as an ordered dependency chain, and why ordering is forced (etcd→apiserver→workers→routes).

2. **`k8s-pki-and-identity`** *(flagship — densest, most valuable)* — self-signed CA, the 8 leaf certs, **CN→user / O→group** mapping, SAN requirements, the apiserver↔kubelet reverse trust, and how x509 identity feeds RBAC + Node Authorizer. Source of truth: `ca.conf`.

3. **`k8s-kubeconfig-and-authn`** — what a kubeconfig is, the cert-per-consumer pattern, `--embed-certs`, server-URL choices (localhost vs hostname), and how this is just PKI packaged for a client.

4. **`k8s-control-plane-internals`** — apiserver / controller-manager / scheduler as three binaries: each one's job, systemd unit, config, the flags that matter, and which secrets each holds (CM holds `ca.key` + SA signing key; apiserver holds serving + kubelet-client certs).

5. **`k8s-etcd-and-state`** — etcd as the single stateful component, the localhost-plaintext teaching simplification vs. production TLS/quorum, and `etcdctl` as the introspection tool.

6. **`k8s-worker-runtime-stack`** — kubelet + containerd + runc + CRI, the `cgroupDriver`/`SystemdCgroup` contract, kubelet config (webhook authn/authz, serving cert, maxPods/swap), and the containerd CRI config.

7. **`k8s-networking-model`** — pod CIDR `/16`-per-cluster `/24`-per-node layout, the Service CIDR `10.32.0.0/24`, bridge CNI vs. cross-node static routes, kube-proxy iptables mode, `br-netfilter` + bridge sysctls. The "CNI demystified" module.

8. **`k8s-security-at-rest-and-rbac`** — encryption-at-rest config (provider ordering, what's covered), the `system:kube-apiserver-to-kubelet` ClusterRole/binding, service-account token signing/verification, and admission plugins (NodeRestriction).

9. **`k8s-operations-and-failure-modes`** — systemd bootstrapping/debugging (`systemctl`, `journalctl`), the smoke-test diagnostic matrix, and the consolidated gotcha catalogue from §7 (SANs, hostnames, cgroup mismatch, route gaps, RBAC 403s, encryption order).

(Modules 2 and 7 are the two with the highest "this is what managed K8s hides" payload and should anchor any teaching artifact.)

---

## 10. Relevance to Helioy

Per the locked v1/v2 strategy (Helioy v1 = local-first laboratory borrowing **K8s vocabulary as a forward-compat contract**; v2 = K8s + CRDs + Knative endgame), genuine KTHW-level fluency is strategically load-bearing, not incidental. Specific transfers:
- **The reconciliation/control-loop model** (controller-manager) is the conceptual template for Helioy's `*-matters` organs reconciling desired vs. actual state.
- **etcd-as-single-source-of-truth** maps to cm/am as Helioy's state stores; the "everything else is stateless" discipline is worth importing.
- **PKI-as-identity** (CN→user, O→group) is a clean model if Helioy ever needs inter-agent authn on helioy-bus.
- **The systemd thin-unit→`--config`-YAML pattern** mirrors how Helioy plugins separate launch from declarative config.
- When v2's K8s/CRD surface materializes, this taxonomy is the onboarding spine.

---

## Sources consulted
- `README.md`, `COPYRIGHT.md`, `LICENSE`, `.gitignore`
- `docs/01-prerequisites.md` … `docs/13-cleanup.md` (full corpus)
- `ca.conf` (PKI definitions)
- `configs/`: `encryption-config.yaml`, `kube-apiserver-to-kubelet.yaml`, `kubelet-config.yaml`, `kube-proxy-config.yaml`, `kube-scheduler.yaml`, `containerd-config.toml`, `10-bridge.conf`, `99-loopback.conf`
- `units/`: `etcd.service`, `kube-apiserver.service`, `kube-controller-manager.service`, `kube-scheduler.service`, `kubelet.service`, `kube-proxy.service`, `containerd.service`
- `downloads-arm64.txt` / `downloads-amd64.txt`
- `gh api repos/kelseyhightower/kubernetes-the-hard-way` (stats, fetched 2026-06-05)

## Open questions
- The doc corpus never explicitly shows the `kube-api-server` cert being placed for etcd peer use, yet `docs/07:41` copies `kube-api-server.{key,crt}` into `/etc/etcd/` — these appear unused given etcd runs plaintext HTTP. Worth confirming whether this is vestigial from a TLS-etcd era.
- `O=system:system:kube-scheduler` (doubled prefix) in `ca.conf:155` — confirm against the live built-in ClusterRoleBinding whether the doubled form is intentional or a long-standing benign typo.
- KTHW pins pre-release binaries (etcd-rc, containerd-beta, runc-rc); not relevant to concepts but worth noting if we ever script a reproduction.

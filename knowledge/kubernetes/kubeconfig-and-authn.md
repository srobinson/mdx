---
title: Kubeconfigs & Authentication
type: knowledge
tags: [kubernetes, kthw, kubeconfig, authn, embed-certs]
summary: A kubeconfig packages one identity for a client as {CA cert + client cert/key + server URL}; KTHW builds one per consumer with --embed-certs so each file is self-contained, and the admin config deliberately uses 127.0.0.1 on the server before a hostname-based config is generated for remote use.
status: active
source: https://github.com/kelseyhightower/kubernetes-the-hard-way
license: Apache-2.0, CC-BY-NC-SA-4.0
related: [index, pki-and-identity, control-plane-internals]
confidence: high
---

# Kubeconfigs & Authentication

## Concept

A kubeconfig is the portable bundle a Kubernetes client reads to answer two questions: *where is the API server* and *who am I*. Structurally it is three things stitched together:

1. a **cluster** entry — the CA cert to trust plus the server URL,
2. a **credentials** entry — one client cert + key (the identity), and
3. a **context** — the pairing of a cluster with a user.

KTHW builds these with three `kubectl config` verbs in sequence: `set-cluster`, `set-credentials`, `set-context` (then `use-context`). It generates **one kubeconfig per consumer** — node-0 and node-1 kubelets, kube-proxy, kube-controller-manager, kube-scheduler, and the admin user — each embedding the matching identity from the PKI module:

| Consumer | Identity (user) embedded | Generated at |
|---|---|---|
| node-0 / node-1 kubelet | `system:node:<host>` | `docs/05-kubernetes-configuration-files.md:18-39` (set-credentials, `docs/05-kubernetes-configuration-files.md:25`) |
| kube-proxy | `system:kube-proxy` | `docs/05-kubernetes-configuration-files.md:52-74` (set-credentials, `docs/05-kubernetes-configuration-files.md:60`) |
| kube-controller-manager | `system:kube-controller-manager` | `docs/05-kubernetes-configuration-files.md:86-108` (set-credentials, `docs/05-kubernetes-configuration-files.md:94`) |
| kube-scheduler | `system:kube-scheduler` | `docs/05-kubernetes-configuration-files.md:121-143` (set-credentials, `docs/05-kubernetes-configuration-files.md:129`) |
| admin | `admin` | `docs/05-kubernetes-configuration-files.md:155-177` (set-credentials, `docs/05-kubernetes-configuration-files.md:163`) |

## Why it exists

Each component must authenticate to the apiserver as its *own* identity, because that identity is what RBAC and the Node Authorizer act on (see `pki-and-identity`). The cert alone establishes who you are, but a process also needs to know the server address and which CA to trust. The kubeconfig is exactly that packaging: it makes an identity portable and droppable onto whichever machine runs the component. The user name chosen in each `set-credentials` call (e.g. `system:node:node-0`) is not cosmetic — it must match the `CN` of the embedded client cert, or the apiserver will authenticate the connection as a different (or unauthorized) identity.

## KTHW implementation

### `--embed-certs=true` makes each file self-contained

Every `set-cluster` and `set-credentials` call passes `--embed-certs=true`, which inlines the CA and the client cert/key as base64 blobs *inside* the kubeconfig rather than leaving filesystem path references (`docs/05-kubernetes-configuration-files.md:21`, `docs/05-kubernetes-configuration-files.md:28` and the parallel lines in each block). The payoff is that the resulting file can be `scp`'d to another host and still work, with no companion cert files to copy. KTHW relies on this when it distributes the kube-proxy and kubelet kubeconfigs to the worker nodes (`docs/05-kubernetes-configuration-files.md:189-199`) and the controller-manager, scheduler, and admin kubeconfigs to the `server` (`docs/05-kubernetes-configuration-files.md:203-207`).

### The server-URL split: `127.0.0.1` then the hostname

The admin kubeconfig is generated **twice on purpose**, with two different server URLs:

- **Step 05 (on/for the server):** the admin config points at `--server=https://127.0.0.1:6443` (`docs/05-kubernetes-configuration-files.md:160`). At this point in the build the admin runs *on* the `server` node itself, before any network-facing remote access exists, so loopback is correct.
- **Step 10 (for the jumpbox):** a second admin kubeconfig is written to the default location `~/.kube/config` pointing at `--server=https://server.kubernetes.local:6443` (`docs/10-configuring-kubectl.md:39`). This is the one used to drive the cluster remotely from the jumpbox over the network.

Two details make step 10 distinct from step 05: it omits `--kubeconfig`, so `kubectl` writes to the default `~/.kube/config` (`docs/10-configuring-kubectl.md:35-50`), and its `set-credentials admin` call does **not** pass `--embed-certs` (`docs/10-configuring-kubectl.md:41-43`), so it references `admin.crt`/`admin.key` on disk rather than inlining them. The cluster entry still embeds the CA (`docs/10-configuring-kubectl.md:38`). The hostname resolves only because of the shared `/etc/hosts` block from the topology step, and TLS validates only because `server.kubernetes.local` is a SAN on the apiserver cert (see `pki-and-identity`). A quick `curl --cacert ca.crt https://server.kubernetes.local:6443/version` confirms reachability before the config is written (`docs/10-configuring-kubectl.md:13-16`), and the cluster then reports `v1.32.3` for both client and server (`docs/10-configuring-kubectl.md:64-66`).

The worker and proxy kubeconfigs always target the hostname `https://server.kubernetes.local:6443` (`docs/05-kubernetes-configuration-files.md:22`, `docs/05-kubernetes-configuration-files.md:57`), since those components run on the nodes and reach the control plane over the network from the start.

## What managed K8s hides

On EKS/GKE/AKS you run a helper such as `aws eks update-kubeconfig` or `gcloud container clusters get-credentials` and a ready-made kubeconfig appears, usually wired to a token/exec-plugin auth flow rather than a raw client cert. KTHW exposes what that helper actually assembles: a CA to trust, a per-identity client credential, and a server URL — and that components other than your CLI (the kubelet, proxy, scheduler, controller-manager) each carry their own kubeconfig with their own identity, which managed offerings provision invisibly.

## Gotchas

- **Wrong server URL (loopback vs hostname).** Copying the step-05 admin kubeconfig (`127.0.0.1`, `docs/05-kubernetes-configuration-files.md:160`) to the jumpbox fails: the apiserver cert is not valid for a remote `127.0.0.1`, so you get an `x509` SAN error. The hostname-based step-10 config is the one for remote use.
- **Non-embedded certs break when copied.** A kubeconfig generated without `--embed-certs=true` only holds filesystem paths; move it to a host that lacks those cert files and auth fails. KTHW's worker/proxy configs embed precisely so they survive the `scp` to the nodes.
- **User name must match the cert CN.** The `set-credentials <user>` name has to equal the embedded cert's `CN` (e.g. `system:node:node-0`); a mismatch means the apiserver authenticates you as the cert's real identity, not the name you typed, often producing confusing RBAC denials.
- **Embedding is a secret-handling concern.** An embedded kubeconfig contains a usable private key; treat it like the credential it is, not like a config file.

See also: `pki-and-identity` (where these identities and the SANs come from) and `control-plane-internals` (the components that consume these kubeconfigs).

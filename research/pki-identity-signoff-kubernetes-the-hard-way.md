---
title: PKI Identity Signoff for Kubernetes The Hard Way
type: research
tags: [kubernetes, kthw, pki, tls, rbac, code-review, moe-signoff]
summary: Technical review of the PKI and identity knowledge doc found two required corrections, verified both were applied, and sent clean final signoff.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

## Executive Summary

Reviewed `~/.mdx/knowledge/kubernetes/pki-and-identity.md` against live Kubernetes The Hard Way repo sources. The core trust model is correct, including eight leaf certificates, x509 CN and O identity mapping, Node Authorizer identity requirements, apiserver certificate double duty, exact apiserver SANs, and the apiserver to kubelet RBAC binding. The two required corrections were applied and verified live, so clean final signoff was sent.

## Project Metadata

- Project: `kubernetes-the-hard-way`
- Type: Markdown tutorial plus shell, OpenSSL, YAML, and systemd assets
- Scope reviewed: `ca.conf`, `configs/kube-apiserver-to-kubelet.yaml`, `configs/kubelet-config.yaml`, `units/kube-apiserver.service`, `docs/04-certificate-authority.md`, `docs/05-kubernetes-configuration-files.md`, and the PKI knowledge artifact
- fmm status: no `.fmm.db` present, so structural reads fell back to targeted shell line reads
- Tutorial target: four ARM64 or AMD64 machines on one network, one control plane node, two workers, and one jumpbox, per `README.md:18-29`
- Component versions: Kubernetes v1.32.x, containerd v2.1.x, CNI v1.6.x, etcd v3.6.x, per `README.md:20-25`
- License signal: tutorial content is CC BY NC SA 4.0, per `README.md:7-9`

## Architecture

KTHW builds one self signed CA, then uses `ca.conf` to mint eight component leaf certificates in `docs/04-certificate-authority.md:44-68`. `docs/05-kubernetes-configuration-files.md` packages the client certificates into kubeconfigs for kubelet, kube proxy, controller manager, scheduler, and admin at `docs/05-kubernetes-configuration-files.md:11-38`, `50-73`, `84-107`, `119-142`, and `153-176`.

The apiserver trusts client certificates through `--client-ca-file=/var/lib/kubernetes/ca.crt` at `units/kube-apiserver.service:14` and authorizes with `--authorization-mode=Node,RBAC` at `units/kube-apiserver.service:12`. The kubelet uses webhook authorization, which makes the apiserver to kubelet RBAC path load bearing, per `configs/kubelet-config.yaml:11-12`.

## Key Patterns

- x509 subject values are the identity source: Kubernetes maps certificate CN to username and O values to groups. The reviewed artifact aligns with Kubernetes authentication docs and with `ca.conf` CN and O fields.
- Node identities are intentionally shaped: node certificates use `CN=system:node:<nodeName>` and `O=system:nodes` at `ca.conf:64-65` and `ca.conf:85-86`, matching the Node Authorizer contract documented in `ca.conf:42-47`.
- KTHW reuses the apiserver serving certificate as the kubelet client certificate. The same `kube-api-server.crt` appears in `--tls-cert-file` at `units/kube-apiserver.service:27` and `--kubelet-client-certificate` at `units/kube-apiserver.service:20`.

## Detailed Findings

### Correct findings verified

1. Certificate count and names match. The docs loop mints exactly eight leaves: `admin`, `node-0`, `node-1`, `kube-proxy`, `kube-scheduler`, `kube-controller-manager`, `kube-api-server`, and `service-accounts` at `docs/04-certificate-authority.md:44-50`. The matching `ca.conf` sections are at `ca.conf:16`, `32`, `49`, `70`, `93`, `116`, `139`, and `168`.
2. The artifact's CN and O table matches `ca.conf`: admin at `ca.conf:22-23`, service accounts at `ca.conf:38`, nodes at `ca.conf:64-65` and `85-86`, kube proxy at `ca.conf:108-109`, controller manager at `ca.conf:131-132`, scheduler at `ca.conf:154-155`, and apiserver at `ca.conf:194`.
3. Admin cluster admin access is correct. `O=system:masters` at `ca.conf:23` maps to the Kubernetes default `cluster-admin` binding for the `system:masters` group.
4. Node Authorizer identity is correct. Kubelets use `system:nodes` plus `system:node:<nodeName>` at `ca.conf:64-65` and `85-86`; the apiserver enables `Node,RBAC` at `units/kube-apiserver.service:12` and NodeRestriction at `units/kube-apiserver.service:15`.
5. The apiserver SANs match `ca.conf:182-191`: `127.0.0.1`, `10.32.0.1`, `kubernetes`, `kubernetes.default`, `kubernetes.default.svc`, `kubernetes.default.svc.cluster`, `kubernetes.svc.cluster.local`, `server.kubernetes.local`, and `api-server.kubernetes.local`.
6. The apiserver to kubelet client cert reuse is correct. `--kubelet-client-certificate` and `--tls-cert-file` both point to `/var/lib/kubernetes/kube-api-server.crt` at `units/kube-apiserver.service:20` and `27`.
7. The apiserver to kubelet RBAC binding is correct. `configs/kube-apiserver-to-kubelet.yaml:22-33` binds role `system:kube-apiserver-to-kubelet` to subject kind `User`, name `kubernetes`, matching the apiserver certificate CN at `ca.conf:194`.

### Required corrections

1. `~/.mdx/knowledge/kubernetes/pki-and-identity.md:117` now describes `O=system:system:kube-scheduler` at `ca.conf:155` as an inert typo. It correctly says scheduler authorization keys on the CN username `system:kube-scheduler` at `ca.conf:154` and that no built in binding consults the doubled group.
2. `~/.mdx/knowledge/kubernetes/pki-and-identity.md:101` now says `ca.key` signs CSRs, and that ServiceAccount tokens are signed with `service-accounts.key`, wired by `--service-account-signing-key-file=/var/lib/kubernetes/service-accounts.key` at `units/kube-apiserver.service:24`.

## Dependencies

- OpenSSL generates the CA, CSRs, and signed leaves in `docs/04-certificate-authority.md:21-68`.
- systemd launches the apiserver with trust, authorization, service account, and serving certificate flags in `units/kube-apiserver.service:6-29`.
- Kubernetes x509 authentication maps CN to username and O to groups. Source checked against the official Kubernetes authentication docs: <https://kubernetes.io/docs/reference/access-authn-authz/authentication/>.
- Kubernetes RBAC default roles bind `system:masters` to `cluster-admin`, and bind scheduler, controller manager, and proxy component privileges to users. Source checked against official RBAC docs: <https://kubernetes.io/docs/reference/access-authn-authz/rbac/>.
- Kubernetes Node Authorizer requires kubelets in `system:nodes` with username `system:node:<nodeName>`. Source checked against official Node Authorization docs: <https://kubernetes.io/docs/reference/access-authn-authz/node/>.

## Relevance to Helioy

This review is useful for Helioy Kubernetes curriculum work because it isolates the high value mental model: Kubernetes identity is often minted before YAML appears. The correction around scheduler `O` also prevents a common teaching error: copied certificate fields may be real without being authorization critical.

## Verification

- fmm attempted first and failed because `/Users/alphab/Dev/LLM/DEV/helioy/REFS/kubernetes-the-hard-way/.fmm.db` is absent.
- Live line reads were used for every requested source.
- A peer consensus round converged on the same two required corrections.
- Owner applied both corrections, then the artifact was re-read live.
- Clean bus signoff sent with exact final signoff language on topic `moe-pki-signoff`.

## Final Signoff

After the owner applied both changes, the artifact was re-read live at `~/.mdx/knowledge/kubernetes/pki-and-identity.md:1-151`. Clean signoff was sent on the `moe-pki-signoff` bus thread with: `I sign off on pki-and-identity.md as currently filed`.

## Open Questions

None for the requested signoff.

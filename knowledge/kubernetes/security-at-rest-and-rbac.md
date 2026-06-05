---
title: Security at Rest & RBAC
type: knowledge
tags: [kubernetes, kthw, encryption, rbac, secrets, admission]
summary: How KTHW encrypts Secrets at rest with an order-sensitive EncryptionConfiguration, and how it grants the API server RBAC to call back into kubelets, plus service-account token signing and admission control.
status: active
source: https://github.com/kelseyhightower/kubernetes-the-hard-way
license: Apache-2.0, CC-BY-NC-SA-4.0
related: [index, pki-and-identity, control-plane-internals]
confidence: high
---

# Security at Rest & RBAC

This module covers two security surfaces that KTHW forces you to wire by hand: confidentiality of Secrets stored in etcd, and the authorization that lets the API server reach kubelets. Both are invisible defaults in managed Kubernetes.

## Concept

Two distinct mechanisms live here:

1. **Encryption at rest.** The API server can encrypt selected resource types before they land in etcd, driven by an `EncryptionConfiguration` object that lists one or more *providers* in priority order.
2. **Authorization (RBAC).** The x509 identities minted in the PKI module (`CN` to user, `O` to group) only matter once a rule grants them verbs on resources. The load-bearing case in KTHW is the reverse-direction grant that lets the API server act as a *client* of each kubelet for `logs`, `exec`, and metrics. Two supporting pieces round it out: admission control and service-account token signing.

## Why it exists

Without encryption at rest, a Secret object is stored in etcd (and therefore in disk images and backups) as base64-decoded plaintext; anyone who can read the etcd data directory can read every Secret. Turning it on is opt-in and, crucially, *order-sensitive*: the first provider in the list encrypts new writes, while every listed provider is still tried for decrypts. That asymmetry is the whole rotation story.

Without the API server to kubelet RBAC grant, the cluster comes up healthy and pods schedule, but `kubectl logs`, `kubectl exec`, and `kubectl top` return `403 Forbidden`. The reason is that the kubelet runs in Webhook authorization mode and asks the API server, via SubjectAccessReview, whether the calling identity may hit `nodes/log`, `nodes/proxy`, and friends. That permission does not exist by default, so it must be created.

## KTHW implementation

### Encryption at rest

The key is 32 random bytes, base64-encoded (`docs/06-data-encryption-keys.md:12`), then substituted into the config template before it ships to the server (`docs/06-data-encryption-keys.md:20`). The config scopes encryption to `secrets` only and declares an ordered provider list: `aescbc` with `key1` first (`configs/encryption-config.yaml:7`), `identity` last (`configs/encryption-config.yaml:11`).

> Quoted from KTHW (Apache-2.0): configs/encryption-config.yaml
```yaml
providers:
  - aescbc:
      keys:
        - name: key1
          secret: ${ENCRYPTION_KEY}
  - identity: {}
```

`aescbc` first means new Secret writes are AES-CBC encrypted; `identity` last is the plaintext passthrough that can still decrypt any pre-existing unencrypted data. The config is wired into the API server with `--encryption-provider-config` (`units/kube-apiserver.service:18`).

The proof is in the smoke test: a Secret is created, then its raw value is read straight from etcd and hexdumped (`docs/12-smoke-test.md:19-20`). The stored bytes carry the `k8s:enc:aescbc:v1:key1` prefix (`docs/12-smoke-test.md:49`) rather than readable YAML, confirming the `aescbc` provider with `key1` did the encryption. Note the scope: only `secrets` are listed, so ConfigMaps and other objects remain plaintext in etcd here.

### API server to kubelet authorization

The grant is a ClusterRole named `system:kube-apiserver-to-kubelet` (`configs/kube-apiserver-to-kubelet.yaml:8`) that allows all verbs on the kubelet subresources `nodes/proxy`, `nodes/stats`, `nodes/log`, `nodes/spec`, and `nodes/metrics` (`configs/kube-apiserver-to-kubelet.yaml:13-19`). A ClusterRoleBinding ties that role to a single subject: the **User** `kubernetes` (`configs/kube-apiserver-to-kubelet.yaml:32-33`).

> Quoted from KTHW (Apache-2.0): configs/kube-apiserver-to-kubelet.yaml
```yaml
subjects:
  - apiGroup: rbac.authorization.k8s.io
    kind: User
    name: kubernetes
```

`kubernetes` is the `CN` of the API server's own certificate, which it presents as a client cert when calling kubelets (the full reverse-trust mechanics are in `pki-and-identity`). The binding is applied once, during control-plane bootstrap (`docs/08-bootstrapping-kubernetes-controllers.md:167`). Skip that apply and `kubectl logs/exec/top` fail with 403.

### Admission control and service-account tokens

The API server enables an admission plugin chain that includes `NodeRestriction` (`units/kube-apiserver.service:15`). It pairs with the Node authorizer half of `--authorization-mode=Node,RBAC` (`units/kube-apiserver.service:12`): the Node authorizer scopes what each kubelet may *read* to its own node, and `NodeRestriction` stops a compromised kubelet from *editing* other nodes' objects.

Service-account tokens are a signed-JWT system. The API server verifies token signatures with `--service-account-key-file` and issues/signs with `--service-account-signing-key-file` (`units/kube-apiserver.service:23-24`). The matching private signer is held by the controller-manager (see `control-plane-internals`).

## What managed K8s hides

- **KMS-backed envelope encryption.** EKS/GKE wire Secret encryption to a cloud KMS and rotate the key encryption key for you; you never generate a raw 32-byte key or order providers by hand.
- **Default RBAC and the apiserver-to-kubelet wiring.** The bootstrap role set and the `system:kube-apiserver-to-kubelet` grant are pre-applied, so `kubectl logs/exec` simply work.
- **Curated admission defaults.** The admission plugin chain (including `NodeRestriction`) is configured by the provider.

## Gotchas

- **Provider order is a silent footgun.** Putting `identity` before `aescbc` disables encryption with no error; the only signal is the missing `k8s:enc:aescbc` prefix when you hexdump the etcd value.
- **Rotation needs the old key retained.** To rotate, add the new key as the first `aescbc` key but keep the previous key in the list (and `identity` only if legacy plaintext exists) until every Secret has been rewritten, or you lose the ability to decrypt old data.
- **Encryption scope is narrow.** Only the resource types you list are encrypted; everything else (ConfigMaps included) stays plaintext in etcd.
- **Forgetting the RBAC apply looks like a healthy cluster.** Pods run, but `kubectl logs/exec/top` return 403. The diagnostic walk lives in `operations-and-failure-modes`.

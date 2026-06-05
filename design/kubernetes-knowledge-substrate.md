---
title: Kubernetes Knowledge Substrate (KTHW-seeded)
type: design
tags: [kubernetes, knowledge-base, kthw, curriculum, mdx-schema, cm, licensing]
summary: Package kubernetes-the-hard-way into a canonical ~/.mdx/knowledge/kubernetes/ curriculum (index + 9 modules) with thin cm/study/content adapters. Phased first build = curriculum + cm pointer; skill and reusable playbook are deferred fast-follows.
status: active
created: 2026-06-05
updated: 2026-06-05
project: helioy
related: [kelseyhightower-kubernetes-the-hard-way]
confidence: high
---

# Kubernetes Knowledge Substrate (KTHW-seeded)

## Context & motivation

`kelseyhightower/kubernetes-the-hard-way` (KTHW, ~48.5k stars) is the canonical pedagogical artifact for understanding how a Kubernetes cluster is bootstrapped from first principles. The current era is post-GCP: four plain Debian-12 VMs (a `jumpbox`, one `server` running the whole control plane, workers `node-0`/`node-1`), Kubernetes v1.32, etcd v3.6, containerd v2.1, CNI v1.6. The corpus is small (13 docs, ~6,100 words, plus 8 `configs/`, 7 `units/`, and `ca.conf`).

Goal: become genuine experts and package that expertise so it serves four purposes at once (Stuart: "all of the above"):
1. **Agent expertise** for Helioy's K8s-shaped v2 endgame (CRDs, Knative, control-plane patterns).
2. **A reusable repo→knowledge pattern**, with KTHW as the pilot instance.
3. **Personal mastery** (study material).
4. **A content seam** feeding blog-architect / social-loop.

The structural insight: this is not "skill **or** cm". It is one canonical knowledge substrate with thin adapters per consumer, the little-organs shape. Build the knowledge once; let each purpose draw from it.

Inputs already produced this session:
- Repo cloned to `~/Dev/LLM/DEV/helioy/REFS/kubernetes-the-hard-way`.
- Long-form synthesis at `~/.mdx/research/kelseyhightower-kubernetes-the-hard-way.md`.
- cm decision entry `019e9490-b6d1-7b91-b09b-da9002d0ab9b`.
- New `knowledge/` category added to `~/.mdx/_schema.md`.

## Decisions locked (brainstorm outcome)

| Decision | Choice |
|---|---|
| Container shape | One canonical substrate, thin adapters |
| Canonical home | `~/.mdx/knowledge/kubernetes/` (new schematized category) |
| Domain framing | "Kubernetes fundamentals, KTHW backbone" — can absorb kubeadm/CKA/operators/CRDs later without re-homing |
| First build scope | Curriculum + cm pointer. Skill and reusable playbook deferred |
| Design-doc location | `~/.mdx/design/` (`type: design`), overriding the skill default |

## Architecture: one home, thin adapters

| Layer | Role | In first plan? |
|---|---|---|
| Source of truth | REFS clone + `research/kelseyhightower-kubernetes-the-hard-way.md` | Done |
| Canonical substrate | `~/.mdx/knowledge/kubernetes/` (index + 9 modules), md-matters indexed | Yes |
| Agent-expertise adapter | md-matters retrieval + one cm `reference` pointer entry routing into the curriculum | Yes |
| Study adapter | `index.md` defines module order; the curriculum is the study path | Falls out |
| Content adapter | blog-architect / social-loop read `~/.mdx/knowledge/` on demand | Free (already reads ~/.mdx) |
| Reusable-pattern adapter | clone→research→curriculum generalized into a `playbooks/` recipe | Deferred |
| Skill adapter | thin `kubernetes-fundamentals` skill routing into the curriculum | Deferred |

DRY guarantee: the 9 modules exist once, in the substrate. cm holds a pointer, not a copy. The research artifact stays at a different altitude (a narrative synthesis essay), so it complements rather than duplicates the operational modules.

## Canonical home & file layout

```
~/.mdx/knowledge/kubernetes/
├── index.md                          # domain overview, 4-VM topology, 13-step arc, study order, source/license
├── topology-and-bootstrap-model.md   # 4-VM layout, machines.txt, the forced 13-step dependency chain
├── pki-and-identity.md               # FLAGSHIP: CA, 8 certs, CN→user / O→group, apiserver↔kubelet reverse-trust, SANs
├── kubeconfig-and-authn.md           # cert-per-consumer, --embed-certs, server-URL choices (127.0.0.1 vs hostname)
├── control-plane-internals.md        # apiserver / controller-manager / scheduler: units, configs, which secrets each holds
├── etcd-and-state.md                 # single stateful member, plaintext-localhost teaching shortcut vs prod TLS/quorum
├── worker-runtime-stack.md           # kubelet + containerd + runc + CRI, cgroupDriver/SystemdCgroup contract, kube-proxy
├── networking-model.md               # HIGH payload: pod /16-per-cluster /24-per-node, service CIDR, bridge CNI vs static routes
├── security-at-rest-and-rbac.md      # encryption provider ordering, apiserver-to-kubelet RBAC, SA token signing, admission
├── operations-and-failure-modes.md   # systemd debug, smoke-test matrix, gotcha catalogue
└── _versions/                        # historical versions, excluded from search
```

10 files (index + 9 modules). Module order lives in `index.md`, never in numeric filename prefixes (per `_schema.md`).

## Module interface (uniform shape)

Every module is independently readable and independently retrievable, and follows one shape.

**Frontmatter** (per `_schema.md`): `title`, `type: knowledge`, `tags`, `summary`, `status: active`, `source: https://github.com/kelseyhightower/kubernetes-the-hard-way`, `license` (per quoted content), `related` (sibling module slugs), `confidence`.

**Body**, in order:
1. **Concept** — what this is, in our own words.
2. **Why it exists** — what breaks without it. The pedagogical spine.
3. **KTHW implementation** — concrete walkthrough with `file:line` citations into the REFS clone (e.g. `configs/kube-apiserver-to-kubelet.yaml`, `ca.conf`, `units/kube-apiserver.service`).
4. **What managed K8s hides** — the EKS/GKE/kubeadm abstraction this exposes.
5. **Gotchas** — where learners get stuck (cert SANs, `/etc/hosts`, systemd ordering, cgroup driver mismatch, encryption order, RBAC 403 on `kubectl logs/exec`).

The flagship `pki-and-identity.md` must fully render the trust web: one self-signed CA → 8 leaves; CN→username and O→group consumed by RBAC with zero extra config; the apiserver cert (`CN=kubernetes`) doubling as both serving cert and the client cert it presents to kubelets, which is why `configs/kube-apiserver-to-kubelet.yaml` binds a ClusterRole to User `kubernetes`.

## Licensing discipline (contract, not afterthought)

KTHW is dual-licensed (verified): `LICENSE` = Apache-2.0 (governs `configs/`, `units/`, `ca.conf`); `COPYRIGHT.md` = CC BY-NC-SA 4.0 (governs tutorial prose).

- **Original synthesis** in our own words = ours, freely usable including commercially. Facts and procedures are not copyrightable.
- **Apache-2.0 snippets** (`configs/`, `units/`, `ca.conf`) = safe to quote **with notice**.
- **CC BY-NC-SA prose** = never pasted verbatim into the curriculum. Cite and link only.
- Every module records `source` and `license` in frontmatter so the derived-knowledge boundary stays auditable.

## cm pointer entry (the agent-expertise adapter)

One `cx_store` entry, kind `reference`, scope `global/project:helioy`:
- **title**: routes the agent to the curriculum (e.g. "Kubernetes fundamentals knowledge lives in ~/.mdx/knowledge/kubernetes/").
- **body**: the 10-file map, one line per module, plus a "recall this when doing K8s / control-plane / CRD / cluster-bootstrap work" trigger note.
- **tags**: `["kubernetes", "knowledge-base", "pointer", "kthw"]`.

This is a pointer, not a knowledge copy. It exists so a future session doing K8s work is routed into the substrate via `cx_recall`.

## Verification (docs, so "tests" = checks)

1. **Citations resolve**: every `file:line` in every module points at a real line in the REFS clone.
2. **Retrieval works**: md-matters reindexes; `md_search "kubernetes pki"` returns `pki-and-identity.md`.
3. **No verbatim CC-NC prose**: spot-grep module sentences against `docs/*.md` to confirm synthesis, not copy.
4. **Schema-valid frontmatter**: every doc validates against `_schema.md` (required fields present, `type: knowledge`).
5. **cm pointer retrievable**: `cx_recall` with a K8s summary surfaces the pointer entry.

## Scope: deferred fast-follows

Out of the first plan, structured so they slot in trivially later:
- **Thin `kubernetes-fundamentals` skill** (via helioy-skill-creator): a router whose SKILL.md points into `knowledge/kubernetes/`, activating during K8s work.
- **repo→knowledge playbook** (`~/.mdx/playbooks/`): generalizes clone→research→curriculum, KTHW as the pilot instance.

## Build phases (outline for the implementation plan)

1. **Scaffold**: create `~/.mdx/knowledge/kubernetes/` + `_versions/`; write `index.md`.
2. **Author the 9 modules**: each from the research artifact + REFS ground truth, uniform shape, real citations. Parallelizable across modules.
3. **Licensing pass**: confirm no verbatim CC-NC prose; confirm Apache snippets carry notice; fill `source`/`license` frontmatter.
4. **Index & retrieval**: finalize `index.md` study order; reindex md-matters; run the retrieval smoke test.
5. **cm pointer**: store the `reference` entry; confirm `cx_recall` surfaces it.
6. **Verify**: run all five verification checks; fix gaps.
7. **(Optional) commit** `~/.mdx` if Stuart asks.

## Risks / open notes

- Module authoring must stay synthesis, not paraphrase-close-to-source, to keep the CC-NC boundary clean. The licensing pass is the guard.
- `index.md` is a category entry point with no underscore, so md-matters indexes it (only `_versions/` is excluded).
- Forward-compat: when v2 K8s work (CRDs/Knative) begins, new modules join this same domain directory rather than spawning a parallel home.

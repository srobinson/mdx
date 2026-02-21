---
title: kubernetes/kubernetes monorepo layout patterns and applicability to littleorgans
type: research
tags: [kubernetes, monorepo, layout, cargo-workspaces, moon, littleorgans, k8s-shape, multi-binary, staging, vendor, build-system]
summary: Anatomical tour of the kubernetes/kubernetes repo (cmd, pkg, staging, vendor, api, build, hack, test, plugin, third_party) with verdicts on what to copy, what to translate, what to skip for a four-substrate Rust monorepo at littleorgans/littleorgans scale.
status: active
source: github-researcher
confidence: high
created: 2026-05-25
updated: 2026-05-25
---

# kubernetes/kubernetes monorepo layout patterns and applicability to littleorgans

## Executive summary

kubernetes/kubernetes is a 454K-LOC Go monorepo that ships roughly two dozen binaries (kubelet, kube-apiserver, kube-controller-manager, kube-scheduler, kube-proxy, kubeadm, kubectl, kubectl-convert, kubemark, plus a long tail of code-generators) from one source tree, and simultaneously publishes ~35 separate Go modules to standalone read-only mirror repos under github.com/kubernetes. The two load-bearing innovations are `staging/`, which lets one source tree be both a private and a public artifact, and a layered `.import-restrictions` enforcement tool that turns architectural intent into a build-time DAG check. Most of the rest is mechanical: Go-specific (vendoring, ldflags, generated code, code-generators) or operational-scale-specific (multi-version Kubernetes API surface, publishing-bot bureaucracy, contributor-mailing-list approval gates).

For Stuart's four-substrate Rust collapse into littleorgans, the **transferable core is six patterns**: tiny `cmd/X/main.go` shells delegating to library packages; a single shared `component-base`-style crate for cross-binary plumbing; a published-types crate that every binary and external client speaks (the cri-api equivalent); `.import-restrictions`-style DAG enforcement; ldflags-style version injection (`env! macros` in Rust); and the cut between in-tree and out-of-tree (kubelet vs CRI implementations, controller-manager vs cloud providers). The **non-transferable bulk** is staging itself, the publishing-bot, vendor/, the multi-version API contract machinery, and the scale-driven hack/ menagerie.

The k8s-shape that littleorgans's CLAUDE.md already advertises is real and load-bearing. Adopting the structural patterns above will keep that shape readable to anyone who has ever written a Kubernetes operator, which is most of the target audience.

---

## 1. Top-level directory layout

Sizes from a fresh clone of master (no submodules, blob filter):

| Dir | Size | Purpose |
| --- | ---: | --- |
| `staging/` | 143 M | Source of truth for ~35 modules also published as `github.com/kubernetes/api`, `client-go`, `apimachinery`, `kubectl`, `kubelet`, `cri-api`, etc. Authoritative; the published repos are sync targets. |
| `vendor/` | 65 M | Mechanically generated vendored copy of every external dependency. Includes a `vendor/k8s.io/...` view of the staging modules wired via go.work and `replace` directives. |
| `pkg/` | 50 M | Private library code for the binaries built from this repo. Importing `k8s.io/kubernetes/pkg/...` from anywhere outside the repo is forbidden. |
| `test/` | 29 M | Integration, e2e, e2e_node, conformance, fuzz, soak, and shared test fixtures. |
| `api/` | 16 M | Generated OpenAPI / Swagger specs (`openapi-spec/swagger.json`, `openapi-spec/v3/*.json`) and api-linter rules and violation exception lists. Not Go source. |
| `CHANGELOG/` | 12 M | One markdown file per minor release, going back to 1.0. |
| `cmd/` | 5.4 M | One subdirectory per binary. Each `main.go` is a 30-50 line shell that delegates to an `app/` subpackage. Includes server binaries (apiserver, kubelet, etc.) and dev tools (import-boss, genfeaturegates, gendocs, etc.). |
| `hack/` | 2.5 M | 100+ scripts for codegen, vendor updates, lint, boilerplate enforcement, version stamping. The "out-of-band Make targets" pile. |
| `cluster/` | 1.9 M | Cluster provisioning helpers (kube-up.sh era); largely legacy. |
| `plugin/` | 1.8 M | Built-in admission controllers and authentication plugins (compiled into kube-apiserver). |
| `LICENSES/` | 1.7 M | Per-dependency license file collected from vendor. |
| `logo/` | 788 K | Branding assets. |
| `third_party/forked/` | 296 K | Forked upstream source that lives as part of the tree (golang stdlib expansion, gonum, libcontainer-cgroups, etc.). Not vendored because they have been modified. |
| `build/` | 188 K | The actual Make orchestration (`build/root/Makefile` is what `./Makefile` symlinks to), the dockerized release builder, image build scripts. |
| `docs/` | 8 K | Stub pointing at git.k8s.io/community. Effectively empty. |

### The load-bearing distinction: cmd/ vs pkg/

The single most important convention in the tree.

**`cmd/X/X.go`** is always a `package main` that does almost nothing:

```go
// cmd/kubelet/kubelet.go
package main

import (
    "context"
    "os"
    "k8s.io/component-base/cli"
    _ "k8s.io/component-base/logs/json/register"
    _ "k8s.io/component-base/metrics/prometheus/clientgo"
    _ "k8s.io/component-base/metrics/prometheus/version"
    "k8s.io/kubernetes/cmd/kubelet/app"
)

func main() {
    command := app.NewKubeletCommand(context.Background())
    code := cli.Run(command)
    os.Exit(code)
}
```

Three things happen here and nowhere else:

1. The blank-imported `_ "k8s.io/component-base/logs/json/register"` side-effect packages register format support, metrics, telemetry. These cannot live in a library because they touch global state.
2. The Cobra `*cobra.Command` tree is constructed in the sibling `app/` subpackage (`cmd/kubelet/app/server.go`, 1450 lines).
3. The actual kubelet implementation lives in `pkg/kubelet/` (a much larger tree).

The split lets every cmd/X's actual library code be reused: `cmd/kubemark/hollow-node.go` reuses the kubelet machinery; integration tests embed pieces of `cmd/kube-apiserver/app` directly to spin up an apiserver in-process.

**`pkg/X/`** is unexported-by-convention. The top-level `pkg/.import-restrictions` declares the rule:

```yaml
# pkg/.import-restrictions
rules:
  - selectorRegexp: k8s[.]io/kubernetes
    allowedPrefixes: ['']
    forbiddenPrefixes:
      - k8s.io/kubernetes/cmd      # pkg/ may not depend on cmd/
      - github.com/ghodss/yaml     # banned dep
      - github.com/ishidawataru/sctp
      - k8s.io/kubectl/pkg/scheme
```

So `pkg/` is the layer where _multiple_ binaries' internal logic lives; `cmd/X/app/` is the layer that wires a specific binary; `cmd/X/X.go` is the bare entry point. A change to a controller logic file in `pkg/controller/...` is a change to a library; a change in `cmd/kube-controller-manager/app/...` is wiring; a change in `cmd/kube-controller-manager/controller-manager.go` would be vanishingly rare.

### staging/ — the bit that does the heavy lifting

`staging/src/k8s.io/{api, apimachinery, client-go, kubectl, kubelet, cri-api, component-base, apiserver, ...}` is the source of truth for code that is _also_ published as standalone Go modules under `github.com/kubernetes/<name>`. The publishing direction is one-way: changes flow PR-to-kubernetes/kubernetes-to-staging-to-mirror, never the other way; the published mirrors carry banner READMEs telling outside contributors to send PRs to the main repo.

From `staging/README.md`:
> The code in the staging/ directory is authoritative, i.e. the only copy of the code. You can directly modify such code.

The published mirrors exist so external projects (operators, controllers, third-party tooling) can `go get k8s.io/client-go@v0.30.0` without dragging the entire 454K-LOC k8s tree as a dependency. The published mirror has a slim `go.mod` listing only the dependencies that this module actually uses.

This is a hard problem with no Cargo equivalent: in Go, a module is a versioning unit and an import-path unit at the same time, and import paths cannot be rewritten without breaking every consumer. So you cannot publish `pkg/foo` as `k8s.io/foo` without the source being _physically located_ where the import path says it is. Staging is the workaround.

The whole thing is held together by **two go-tooling tricks** (see §4 below): a `go.work` file at the root, and `replace` directives in `go.mod` files. These translate `k8s.io/api` ↔ `./staging/src/k8s.io/api` whenever the kubernetes repo itself is building.

---

## 2. Multi-binary build

### Where binaries are declared

`hack/lib/golang.sh` enumerates the binaries the build system knows about. Three categories:

```bash
# hack/lib/golang.sh:69-83 — server binaries (linux only)
kube::golang::server_targets() {
  local targets=(
    cmd/kube-proxy
    cmd/kube-apiserver
    cmd/kube-controller-manager
    cmd/kubelet
    cmd/kubeadm
    cmd/kube-scheduler
    staging/src/k8s.io/component-base/logs/kube-log-runner
    staging/src/k8s.io/kube-aggregator
    staging/src/k8s.io/apiextensions-apiserver
    cluster/gce/gci/mounter
  )
  echo "${targets[@]}"
}
```

```bash
# hack/lib/golang.sh:258-261 — client binaries (all supported platforms)
readonly KUBE_CLIENT_TARGETS=(
  cmd/kubectl
  cmd/kubectl-convert
)
```

```bash
# hack/lib/golang.sh:126-134 — node binaries (the kubelet runs on every k8s node)
kube::golang::node_targets() {
  local targets=(
    cmd/kube-proxy
    cmd/kubeadm
    cmd/kubelet
    staging/src/k8s.io/component-base/logs/kube-log-runner
  )
  echo "${targets[@]}"
}
```

Notice: some targets are in `cmd/`, some are inside `staging/src/k8s.io/...` (kube-aggregator and apiextensions-apiserver). The build system does not care; it asks Go to compile a `package main` from wherever it is.

### How shared code is factored

Three layers of sharing, from most-shared to least:

1. **`staging/src/k8s.io/component-base/`** — pure plumbing every binary needs. Logging registration, metrics registration, Cobra `cli.Run` wrapper, feature-gate machinery, version-injection vars, `verflag.PrintAndExitIfRequested()`. Every binary main.go in the repo imports this; every binary main.go has the same shape because of it.

2. **`pkg/X/`** — domain code shared between binaries that participate in the same subsystem. Examples: `pkg/proxy/` is shared by `cmd/kube-proxy` and `cmd/kubemark/hollow-proxy`; `pkg/kubelet/` is shared by `cmd/kubelet` and `cmd/kubemark/hollow-kubelet`; `pkg/controlplane/` underpins `cmd/kube-apiserver`.

3. **`cmd/X/app/`** — binary-specific wiring. Cobra command construction, flag parsing, config loading, lifecycle. Lives next to its binary so it can be reused by tests (e.g., `test/integration/framework/controlplane_utils.go` directly imports `k8s.io/kubernetes/pkg/api/legacyscheme` and `k8s.io/kubernetes/pkg/generated/openapi` to spin up an apiserver in-process).

The reason this avoids each binary "including everything" is the standard Go behaviour of dead-code elimination at link time plus deliberate import discipline. There is no per-binary `Cargo.toml` features dance; Go just doesn't ship symbols you don't reference.

### Build orchestration

The Make tree is the user-facing entry point:

- `./Makefile` is a symlink to `build/root/Makefile`.
- `build/root/Makefile` defines `all`, `test`, `test-integration`, `test-e2e-node`, `verify`, `update`, `release`, `cross`, `quick-release`, `package`, and a generated `$(CMD_TARGET)` rule per binary.
- Heavy lifting is in `hack/lib/golang.sh` (compile orchestration), `hack/lib/version.sh` (ldflag construction), and `build/lib/release.sh` (tarball assembly).

Ldflag injection (the version stamping mechanism) happens here:

```bash
# hack/lib/version.sh:155-162
function add_ldflag() {
    local key=${1}
    local val=${2}
    ldflags+=(
      "-X 'k8s.io/client-go/pkg/version.${key}=${val}'"
      "-X 'k8s.io/component-base/version.${key}=${val}'"
    )
}
```

The variables being overwritten live in `staging/src/k8s.io/component-base/version/base.go`:

```go
// staging/src/k8s.io/component-base/version/base.go:30-57
var (
    gitMajor string
    gitMinor string
    gitVersion   = "v0.0.0-master+$Format:%H$"
    gitCommit    = "$Format:%H$"
    gitTreeState = ""
    buildDate    = "1970-01-01T00:00:00Z"
)
```

The `$Format:%H$` strings are also git-archive substitution markers (per `.gitattributes`), so a tarball downloaded from GitHub gets _some_ version info even without git. Every binary in the tree gets the same ldflags; the version package is imported transitively by everything via component-base.

There is no Bazel today. There used to be (kubernetes/kubernetes used Bazel from ~2017 to ~2020) and it was removed. ko (the imageless Go-container builder) is used in some sister repos but not in the main kubernetes/kubernetes Makefile. Image building is `build/release-images.sh` driving `docker buildx`.

---

## 3. Internal API contracts between binaries

How does the source layer express "kubelet and kube-apiserver agree on the shape of a Pod"?

Three contract surfaces, layered:

### 3.1 The kube API itself

Every type the apiserver serves (Pod, Service, Deployment, ConfigMap, ...) is declared exactly once in `staging/src/k8s.io/api/<group>/<version>/types.go`. For example, the Pod type lives at `staging/src/k8s.io/api/core/v1/types.go` (8519 lines). The companion files are mostly generated:

```
staging/src/k8s.io/api/core/v1/
  types.go                              # hand-written
  generated.proto                       # generated from types.go
  generated.pb.go                       # generated from .proto (protobuf binding)
  zz_generated.deepcopy.go              # generated DeepCopy() methods
  zz_generated.prerelease-lifecycle.go  # generated lifecycle hooks
  zz_generated.model_name.go            # generated reverse lookup
  types_swagger_doc_generated.go        # generated OpenAPI doc snippets
  register.go                           # hand-written scheme registration
```

The contract is `types.go`. Everything else is downstream. The codegen runs via `hack/update-*.sh` scripts and is verified by `hack/verify-*.sh` mirrors in CI.

The published artifact `k8s.io/api` is _just_ this directory plus its siblings. Every external Kubernetes client (controllers, operators, kubectl plugins, third-party API gateways) imports the same `k8s.io/api/core/v1` types module that kube-apiserver itself uses. There is exactly one definition of `corev1.Pod` in the Go ecosystem.

### 3.2 The kubelet ↔ container runtime contract (CRI)

This is the cleanest example because it crosses a process boundary _outside_ the Kubernetes monorepo (containerd, cri-o, others implement it).

```
staging/src/k8s.io/cri-api/pkg/apis/runtime/v1/
  api.proto         # the gRPC service definition
  api.pb.go         # generated protobuf bindings
  api_grpc.pb.go    # generated gRPC client/server
  constants.go      # hand-written constants
```

The kubelet at `pkg/kubelet/cri/` consumes this; containerd's cri plugin and cri-o consume it via their own Go module dependency on `k8s.io/cri-api`. Same generated code on both sides, guaranteed by both projects depending on the same published version of the module.

### 3.3 Inter-component HTTP / config contracts

Components that talk to the apiserver use `staging/src/k8s.io/client-go/`. Components that expose their own config to admins use the `staging/src/k8s.io/<component>-config/` pattern (kube-proxy config, kubelet config, scheduler config) — typed configuration files versioned the same way as API types.

### The single types crate question

There is no single `k8s.io/types` module. There are ~35 staging modules. But the modules form a strict layering:

- `k8s.io/apimachinery` (object metadata, runtime.Object, schemes, generic codec) — depends on nothing k8s-specific
- `k8s.io/api` (the typed types, all built-in resources) — depends on apimachinery only
- `k8s.io/client-go` (the typed client for talking to apiserver) — depends on api + apimachinery
- `k8s.io/component-base` (CLI, logging, metrics, feature gates, version) — depends on apimachinery + client-go
- `k8s.io/apiserver` (the generic apiserver library) — depends on the above
- everything else builds on these

The layering is enforced at build time by import-boss (see §1) reading `.import-restrictions` files in each module. From `staging/src/k8s.io/api/.import-restrictions`:

```yaml
- baseImportPath: "./staging/src/k8s.io/api"
  allowedImports:
  - k8s.io/api
  - k8s.io/apimachinery
  - k8s.io/klog
```

That says "k8s.io/api may only import itself, apimachinery, and klog. If you add anything else, the verify step fails." This is how a 35-module monorepo stays acyclic.

---

## 4. Vendored vs staging — how dual citizenship works

The two mechanisms are different and you need both.

### Vendored

`vendor/` is a literal copy of every external dependency, generated by `hack/update-vendor.sh`. Reproducibility: builds work offline, with the exact byte-for-byte sources k8s tested against, no surprise upstream changes during a release. This is just `go mod vendor` with policy on top (license verification, dependency-allowlisting via `hack/lint-dependencies.sh`).

`vendor/k8s.io/...` is also populated — but those entries are symlinks-in-spirit. They are how Go's vendor tooling expresses what go.work + replace already established.

### Staging mechanism, step by step

The puzzle: `pkg/kubelet/kubelet.go` imports `k8s.io/api/core/v1`. That same `k8s.io/api/core/v1` is also a published Go module at `github.com/kubernetes/api`. How does Go resolve the import to the local `staging/src/k8s.io/api/core/v1` when building from the kubernetes repo?

Two interlocking files:

**`go.work`** at the repo root (lines 1-37):

```
go 1.26.0
godebug default=go1.26
use (
    .
    ./staging/src/k8s.io/api
    ./staging/src/k8s.io/apiextensions-apiserver
    ./staging/src/k8s.io/apimachinery
    ./staging/src/k8s.io/apiserver
    ./staging/src/k8s.io/cli-runtime
    ./staging/src/k8s.io/client-go
    ... 31 more staging modules ...
)
```

A Go workspace lists multiple modules that should be built together. Inside a workspace, when one module imports another by its declared module path (e.g., `k8s.io/api`), Go uses the local source.

**`go.mod`** at the repo root has matching `require` and `replace` blocks:

```
require (
    ...
    k8s.io/api v0.0.0
    k8s.io/apimachinery v0.0.0
    k8s.io/client-go v0.0.0
    ...
)

replace (
    k8s.io/api => ./staging/src/k8s.io/api
    k8s.io/apimachinery => ./staging/src/k8s.io/apimachinery
    k8s.io/client-go => ./staging/src/k8s.io/client-go
    ... 30+ more
)
```

The version `v0.0.0` is a placeholder; the `replace` rewrites the path to local. When `go build ./cmd/kubelet/...` runs, every `k8s.io/api`-prefixed import resolves to the local staging tree.

Inside each staging module's own go.mod, the same trick repeats with relative paths to siblings:

```
# staging/src/k8s.io/client-go/go.mod (tail)
replace (
    k8s.io/api => ../api
    k8s.io/apimachinery => ../apimachinery
    k8s.io/streaming => ../streaming
)
```

When the publishing-bot runs (a separate repository, github.com/kubernetes/publishing-bot, fired by `staging/publishing/rules.yaml`), it:

1. Reads each rule (which staging module, which target branch, which dependencies).
2. Copies the directory contents to the destination repo.
3. Rewrites the go.mod: strips `replace ../...` lines, replaces `v0.0.0` with a real semver derived from the kubernetes release tag (e.g., `v1.30.0` → `v0.30.0` for client-go).
4. Force-pushes to the published mirror.

From `staging/publishing/rules.yaml`:

```yaml
- destination: client-go
  branches:
  - name: master
    dependencies:
    - repository: apimachinery
      branch: master
    source:
      branch: master
      dirs:
      - staging/src/k8s.io/client-go
```

**What problem does this solve that just publishing separate repos would not?** Three things:

1. **Atomic cross-cutting changes.** If you need to add a new field to a Pod, the wire format (proto), the apiserver storage code, the client-go DTOs, every controller that handles Pods, and the kubectl printer all need to change together. Across separate repos this is impossible without flag days. In one repo it is one PR.
2. **No version-resolution lag.** Inside k8s, every component is always on the same line of code. There is no "but client-go v0.29.3 has a bug fixed in apimachinery v0.29.4 which isn't released yet" situation.
3. **External consumers still get small modules.** A controller that depends on `client-go` doesn't drag in the kubelet, scheduler, or 65 MB of vendor.

The cost is the entire publishing-bot bureaucracy plus the import-restrictions enforcement plus the requirement that no staging module ever imports `k8s.io/kubernetes` (the parent repo) — because then it could not be published standalone. That last rule is enforced by `staging/src/k8s.io/apiserver/.import-restrictions`:

```yaml
rules:
  - selectorRegexp: k8s[.]io/kubernetes
    forbiddenPrefixes:
      - ''
```

---

## 5. Version handling

### The hierarchy

- The kubernetes repo carries a single git tag per release: `v1.30.0`, `v1.30.1`, etc. Tag lives on the kubernetes/kubernetes git history.
- Each staging module gets its own derived semver on publish: `v0.30.0` for client-go, apimachinery, api, etc. The convention is "k8s 1.X = staging-module 0.X" — chosen so staging modules can later go to v1 without colliding with the k8s repo's v1.
- Inside the kubernetes/kubernetes repo, staging module go.mod files all declare `version: v0.0.0`. The publishing-bot rewrites this at publish time.

### The binary version

Every binary built from the tree gets its version baked in by ldflags. From `hack/lib/version.sh:165-177`:

```bash
add_ldflag "buildDate" "$(${DATE} ${SOURCE_DATE_EPOCH:+...} -u +'%Y-%m-%dT%H:%M:%SZ')"
if [[ -n ${KUBE_GIT_COMMIT-} ]]; then
    add_ldflag "gitCommit" "${KUBE_GIT_COMMIT}"
    add_ldflag "gitTreeState" "${KUBE_GIT_TREE_STATE}"
fi
add_ldflag "gitVersion" "${KUBE_GIT_VERSION}"
add_ldflag "gitMajor" "${KUBE_GIT_MAJOR}"
add_ldflag "gitMinor" "${KUBE_GIT_MINOR}"
```

The same ldflag pair is added to both `k8s.io/client-go/pkg/version` and `k8s.io/component-base/version` (lines 159-161 of version.sh) — historical reason, both packages predate component-base. Every binary that imports either gets stamped.

When you run `kubectl version` you see this baked-in info. When you run `kube-apiserver --version` you see the same baked-in info. The same code path generates both, because everything goes through `staging/src/k8s.io/component-base/version/verflag`.

### Source-of-truth fallback

`base.go` has hard-coded fallback strings:
- `gitVersion = "v0.0.0-master+$Format:%H$"` (the `$Format:` placeholder is replaced by git-archive)
- `DefaultKubeBinaryVersion = "1.37"` (a const updated by hand once per release)

So a `go build` from a tarball download still produces a binary with a sensible version string.

---

## 6. Where kubectl lives

kubectl is in staging, not in pkg/. Look at `staging/src/k8s.io/kubectl/pkg/`:

```
staging/src/k8s.io/kubectl/
  go.mod              # its own module
  pkg/
    cmd/              # the kubectl command tree (cobra)
    apps/
    config/
    describe/
    drain/
    explain/
    polymorphichelpers/
    proxy/
    ...
```

`cmd/kubectl/kubectl.go` is the same 30-line shell as every other cmd/ entry point: imports `k8s.io/kubectl/pkg/cmd`, calls `cmd.NewDefaultKubectlCommand()`, runs it.

The reason kubectl lives in staging is the same as client-go: thousands of third-party tools (helm, krew plugins, k9s, lens, every IDE extension) link against `k8s.io/kubectl` to reuse its printer machinery, its YAML-edit machinery, etc. Putting it in staging makes that import work for outsiders.

**kubectl does not import apiserver internals.** It talks to apiserver exclusively over the public HTTP API using client-go, exactly like any third-party tool would. The codebase enforces this: kubectl is in staging, and staging modules cannot import the apiserver's internal `pkg/...` tree.

The implication for layout: kubectl is structurally a peer of the server binaries, not a derived artifact of them. Its own `pkg/cmd/...` tree has the equivalent of a kubelet's `pkg/kubelet/...` tree — the depth and surface area are comparable.

---

## 7. Testing topology

Three layers, three locations:

### Unit tests — colocated

Every Go package has its `*_test.go` files next to the source. `pkg/kubelet/kubelet_test.go` lives next to `pkg/kubelet/kubelet.go`. `go test ./pkg/kubelet/...` runs them. No central test directory for unit tests.

### Integration tests — `test/integration/`

```
test/integration/
  apimachinery/
  apiserver/
  auth/
  certificates/
  controlplane/
  scheduler/
  scheduler_perf/
  framework/         # ← shared utilities
  ...
```

Each subdirectory spins up real component binaries _in-process_ using the cmd/X/app packages and a shared `test/integration/framework/` library that knows how to:

- Start an etcd subprocess (`test/integration/framework/etcd.go`).
- Spin up an apiserver in-process (`controlplane_utils.go` directly imports `k8s.io/kubernetes/pkg/api/legacyscheme` and `k8s.io/kubernetes/pkg/generated/openapi`).
- Construct a kubeclient against the in-process apiserver.

```go
// test/integration/framework/controlplane_utils.go:18-32 (excerpt)
import (
    openapinamer "k8s.io/apiserver/pkg/endpoints/openapi"
    genericapiserver "k8s.io/apiserver/pkg/server"
    "k8s.io/apiserver/pkg/server/options"
    "k8s.io/apiserver/pkg/storage/storagebackend"
    "k8s.io/kubernetes/pkg/api/legacyscheme"
    "k8s.io/kubernetes/pkg/generated/openapi"
)
```

The scheduler integration test starts an apiserver, an etcd, and a scheduler in the same process, exercises them across an HTTP loop, then tears them down. This works because each binary is built from `package main` that delegates to an `app/` library — anything `main` can do, the integration test can do.

The cost: integration tests don't run "the same binary kubelet customers run." They run an in-process reconstruction. The reconstruction is the same code, but lifecycle ordering can diverge. This is one reason the e2e tier exists.

### E2E tests — `test/e2e/` and `test/e2e_node/`

The e2e tier launches actual binaries against actual clusters (which may be local kind/minikube clusters, GCE/AWS clusters, or kubemark-simulated clusters). Tests are Ginkgo-driven.

`test/e2e/e2e.go` is the bootstrap (418 lines). `test/e2e/framework/` has the cluster-aware helpers. Subdirectories under `test/e2e/` are grouped by SIG / area: `auth/`, `apps/`, `network/`, `scheduling/`, `storage/`, etc.

`test/e2e_node/` is a special variant: tests that target only the kubelet's behavior, running a real kubelet binary on a real node without the rest of the control plane.

### test/ has its own import restrictions

```yaml
# test/e2e_node/.import-restrictions (excerpt)
- baseImportPath: "./test/e2e_node"
  allowedImports:
    - k8s.io/api
    - k8s.io/apimachinery
    - k8s.io/client-go
    - k8s.io/kubernetes/pkg/kubelet/...  # narrowly allowed
    ...
```

So tests can reach into the kubelet's internals where they specifically need to, without that becoming a backdoor for production code.

### How one component's test exercises another without forcing a full build

Two answers:

1. **Tests live in the same module as the code.** A test in `pkg/kubelet/...` can import anything any binary can import, because they're all the same `k8s.io/kubernetes` module.
2. **In-process spinup via cmd/X/app.** Because the binary's main is so thin, the entire startup path is library code. `test/integration/framework/` calls into it directly.

There is no `go test ./...` that runs everything; that would take hours. The Makefile and CI matrix carve up the test surface: `make test WHAT=./pkg/kubelet` runs only those package tests; `make test-integration WHAT=./test/integration/scheduler` runs only that subdirectory; etc.

---

## 8. What is conspicuously NOT in the repo

The cut between what is in kubernetes/kubernetes and what is not has a principle behind it.

**In the repo:**
- The five control-plane binaries that define what a Kubernetes cluster _is_: apiserver, controller-manager, scheduler, kubelet, kube-proxy.
- kubectl.
- The built-in admission controllers and authenticators (`plugin/pkg/admission/...`, `plugin/pkg/auth/...`).
- All the typed API resources (Pod, Service, Deployment, etc.).
- The shared client (client-go) and shared APIs (api, apimachinery).
- kubeadm (cluster bootstrap).

**Not in the repo, on purpose:**
- **etcd.** The cluster's persistent storage. Maintained by CNCF, used as a library via `go.etcd.io/etcd/...`. Reasoning: etcd predates k8s, has many other users, and changing its release cadence to k8s's would be a coordination disaster.
- **CRI implementations.** containerd, cri-o, others. Kubelet defines the contract (cri-api), runtimes implement it independently. This was the famous Dockershim removal in k8s 1.24 — pulling out the last container runtime that lived in-tree. Reasoning: container runtimes are themselves large projects (containerd is ~100K LOC) with their own communities; baking one in violates the "do one thing" principle.
- **CNI plugins.** Network plumbing. Calico, Cilium, Flannel are all external. Kubelet defines a small interface (CNI itself is a separate spec under github.com/containernetworking).
- **CSI plugins.** Storage drivers. Same logic: external because there are dozens of them and they evolve independently.
- **Cloud provider implementations.** The "cloud-controller-manager" pattern was introduced specifically to move AWS, Azure, GCP, etc. integrations out of tree to separate repos under github.com/kubernetes/cloud-provider-{aws,azure,gcp,...}. The in-tree controller manager still has a generic harness; provider-specific code lives elsewhere.
- **Observability tooling.** Prometheus, Grafana, Jaeger, OpenTelemetry collectors. Used as dependencies (otelhttp instrumentation imports), not vended.
- **The dashboard.** kubernetes/dashboard is a separate repo.
- **Helm.** Different project entirely.

**The principle:** in-tree is "the contract and the reference implementation of the cluster control-plane primitives." Out-of-tree is "everything that plugs _into_ those primitives." The contracts themselves are the load-bearing artifact, and they live in staging modules so external implementers can depend on them directly.

A useful litmus: if removing this component would mean Kubernetes is no longer Kubernetes, it is in-tree. If removing this component just means you need to install a different vendor's plugin, it is out-of-tree.

---

## Applicability assessment for littleorgans

Stuart's situation:
- Four substrates today: session-matters, runtime-matters, identity-matters, transport-matters.
- Each is a separate Rust repo with its own Cargo workspace, release-plz, CI.
- Goal: collapse into one polyglot monorepo at `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans` (private, Moon-driven), with cascading per-`*-matters` releases to public MIT mirrors under `github.com/littleorgans`.
- Drivers: stop the versioning hell across repos, unify standards, unify `~/.{rtm,sm,im}` configs into `~/.lilo`, ship one binary instead of three.

The pattern-by-pattern verdict:

### Pattern 1: `cmd/X/main.rs` as a thin shell, library lives elsewhere

**Verdict: transfers cleanly.** This is the single highest-value pattern for littleorgans, and it transfers cheaper to Cargo than to Go.

In Cargo terms:

```
littleorgans/
  Cargo.toml                          # workspace root
  crates/
    lilo/                             # the single user-facing binary crate
      Cargo.toml                      # [[bin]] name = "lilo"
      src/
        main.rs                       # 30-50 lines, dispatches subcommand
        bin/sm.rs                     # optional alternate entry: lilo-sm symlink
        bin/rtm.rs                    # optional alternate: lilo-rtm symlink
    sm-app/                           # session-matters wiring (~ cmd/X/app/)
      src/lib.rs                      # builds the clap App, owns flag parsing
    sm-core/                          # session-matters internals (~ pkg/sm/)
    rtm-app/
    rtm-core/
    im-core/
    tm-core/
    component-base/                   # ~ k8s.io/component-base
```

Each `*-app` crate exports a `pub fn build_command() -> clap::Command` plus `pub fn run(matches) -> ExitCode`. `main.rs` in `lilo/` is:

```rust
fn main() -> ExitCode {
    component_base::init_logging();
    component_base::register_metrics();
    let cmd = clap::Command::new("lilo")
        .subcommand(sm_app::build_command())
        .subcommand(rtm_app::build_command())
        .subcommand(im_app::build_command());
    let matches = cmd.get_matches();
    match matches.subcommand() {
        Some(("sm", m)) => sm_app::run(m),
        Some(("rtm", m)) => rtm_app::run(m),
        Some(("im", m)) => im_app::run(m),
        _ => unreachable!(),
    }
}
```

This is the **"one binary runtime"** that's already on Stuart's driver list. Subcommand dispatch from a single binary gives the unification benefit; the per-substrate `*-app` crates keep the internal organization that maps to kubelet/apiserver/scheduler.

Single-binary or per-substrate? Both, cheaply. Cargo lets you declare multiple `[[bin]]` targets:

```toml
# lilo/Cargo.toml
[[bin]]
name = "lilo"
path = "src/main.rs"

[[bin]]
name = "sm"          # built when needed; or use cargo install --bin
path = "src/bin/sm.rs"

[[bin]]
name = "rtm"
path = "src/bin/rtm.rs"
```

Or use a single binary that detects `argv[0]` (the busybox / git-shim trick):

```rust
fn main() -> ExitCode {
    let argv0 = std::env::args().next().unwrap();
    let name = std::path::Path::new(&argv0).file_name().unwrap().to_str().unwrap();
    match name {
        "sm" => sm_app::run_standalone(...),
        "rtm" => rtm_app::run_standalone(...),
        "lilo" | _ => lilo_dispatch(...),
    }
}
```

Recommendation: ship `lilo` as primary, ship the standalones as symlinks to `lilo` resolved by argv[0]. This is how busybox works; this is how rustc/rustdoc/cargo work in nightly builds. Same binary, three names. Avoids cmd/X duplication entirely.

### Pattern 2: `pkg/` for binary-private code

**Verdict: transfers in spirit, mechanism differs.** Cargo's mechanism is workspace member crates; the spiritual equivalent of "private to this repo" is "not published to crates.io."

In `littleorgans/`:
- `crates/` holds everything published.
- `internal/` (or a sibling top-level dir) holds workspace members that are explicitly not published. Each has `publish = false` in its `Cargo.toml`.
- The CI release pipeline only publishes `crates/*`. `internal/*` is buildable but unreleasable.

This is cleaner than Go's `pkg/`-by-convention because Cargo enforces it: `cargo publish` literally refuses to publish a `publish = false` crate.

Note: Stuart's published crates today are `lilo-rm-core@0.7.1`, `lilo-rm-client@0.7.1`, `lilo-im-core@0.1.1`, `lilo-im-store@0.1.1`. These map directly to the staging-equivalent: they are "calling card" public artifacts external Rust consumers might use, parallel to k8s.io/api / k8s.io/client-go.

### Pattern 3: `staging/` — dual-citizenship publishing

**Verdict: k8s-scale only, with an interesting twist for littleorgans.** Do not adopt the staging mechanism. Reason: Rust does not have Go's "the import path is the module path is the on-disk path" problem. Cargo can publish a workspace member crate to crates.io without that crate having to live anywhere special on disk; you just `cargo publish -p lilo-rm-core` from the monorepo root.

So the `staging/` directory itself is unnecessary in Rust.

**But the underlying problem k8s solved is still real for littleorgans:** the public mirror repos under `github.com/littleorgans/` need to look like real, self-buildable Rust projects, not just thin wrappers pointing at the monorepo. From the direction doc, open item #4: "If the mirror is a git push from the monorepo, can a fork actually `cargo build` against it? Each mirror must be self-buildable, not require monorepo context. This is a non-trivial CI constraint."

The k8s answer (publishing-bot rewriting go.mod to strip relative-path replaces and inject real semver) translates to: at mirror push time, rewrite the per-substrate `Cargo.toml` to:
1. Remove the workspace inheritance (`workspace = true` keys become concrete values resolved from the workspace root).
2. Convert path dependencies (`some-other-crate = { path = "../other-crate" }`) into registry dependencies (`some-other-crate = "0.1.0"`) — but only for siblings that have their own mirrors.
3. Inject the release semver.

This is a real piece of CI engineering. It is _easier_ than the publishing-bot because Rust's tooling is younger and less surface-area-rich, but it is not free. The k8s playbook (rules.yaml + a dedicated rewriter) is the right shape.

**Concrete recommendation:** build a small `lilo-mirror-publish` tool in `tools/` of the monorepo. Inputs: monorepo state + version tag. Outputs: per-mirror staged tarballs ready to force-push to each `github.com/littleorgans/<substrate>` repo. Run it from CI on release.

### Pattern 4: `vendor/`

**Verdict: k8s-scale only.** Cargo.lock + a strict crates.io supply-chain policy (cargo-deny, cargo-audit) does what k8s gets from `vendor/`. Cargo does have `cargo vendor` if needed for offline builds, but for solo-builder Stuart this is unnecessary noise. Skip.

### Pattern 5: `component-base` equivalent — shared plumbing

**Verdict: transfers cleanly. This is the second-highest-value pattern.**

Create `crates/lilo-common/` (or similar) with: logging setup (tracing-subscriber, OTel exporter wiring), metrics registration, version constants (`env!("VERGEN_GIT_SHA")`), config-file discovery (`~/.lilo/...`), graceful-shutdown helpers (tokio signal handling), CLI common flags (`--verbose`, `--config`, `--version`).

Every `*-app` crate imports `lilo-common`. Every binary's main.rs calls `lilo_common::init()` first.

This is the antidote to "unifying standards" being a vibe instead of a contract: the crate is the contract.

### Pattern 6: Single types crate (or layered types crates)

**Verdict: transfers in spirit, mechanism differs.** This is the most architecturally important transferable pattern, and Rust's type system actually does it better than Go.

The k8s shape:
- `k8s.io/apimachinery` — generic object metadata, runtime types, schemes
- `k8s.io/api` — the typed types (Pod, Service, ...)
- `k8s.io/cri-api` — the kubelet ↔ runtime contract (proto)
- `k8s.io/client-go` — the typed client to the apiserver

The littleorgans shape (recommended):

```
crates/
  lilo-types/             # everything that crosses a daemon boundary
    src/
      lib.rs
      session/            # types the sm wire protocol uses
      runtime/            # types the rtm wire protocol uses
      identity/           # types im publishes
      transport/          # types tm publishes
  lilo-protocol/          # the protobuf / capnp / postcard wire schemas (if non-trivial)
  lilo-client/            # client library for talking to lilo daemons over wire
    src/
      sm.rs               # SessionClient
      rtm.rs              # RuntimeClient
      im.rs               # IdentityClient
```

Discipline: anything that the `sm` daemon sends to the `sm` client over the wire is a type defined in `lilo-types::session`. Anything internal to the sm daemon is in `lilo-sm-core` and is not re-exported.

This corresponds to "the kubelet and the apiserver agree on the shape of a Pod." For littleorgans: the `rtm-shim` (kubelet-shim equivalent) and the `rtm` daemon (kubelet equivalent) must agree on the wire shape; the `sm` daemon (apiserver) and the `sm` client (kubectl) must agree.

The `lilo-*` published crates today (lilo-rm-core, lilo-rm-client) are already on this trajectory. The monorepo migration should solidify it: each cross-daemon contract gets its own crate; each substrate has both a `-core` (private) and a `-types` (public) crate, plus a `-client` (also public) where there is a non-trivial client.

### Pattern 7: `.import-restrictions` DAG enforcement

**Verdict: transfers cleanly, with caveats.** Cargo enforces some of this naturally (you can only depend on what's in your Cargo.toml), but not all of it. Two specific k8s tricks worth keeping:

a) **A staging crate must not depend on the monorepo.** In Rust this becomes "a published crate (`publish = true`) must not depend on a `publish = false` crate." This is enforced by `cargo publish --dry-run`; it will refuse. So it's free.

b) **A binary's internals must not be importable from peer binaries.** In Cargo this is achieved by having the `*-app` crates be `publish = false` and the `*-core` crates depend only on `*-types` siblings, never on peer `*-core` crates. There is no native Cargo tool for "ban this dependency pattern" beyond explicit Cargo.toml entries.

For the cross-cutting policy (e.g., "no crate in `internal/` may depend on a specific blacklisted dependency"), tools that exist: `cargo-deny`, `cargo-machete`, or a small `xtask` script that walks `cargo metadata --format-version 1` and asserts a topology. The k8s answer is import-boss (a custom Go tool, ~600 lines). The Rust answer can be `cargo-deny` plus 50 lines of xtask checking the topology graph from `cargo metadata`.

Worth it for littleorgans? Marginal at four substrates. Becomes valuable around 8-10 crates. Stuart's current published crate count is 4 and the post-migration count is probably ~15 (4 substrates × ~3 crates each, plus shared). The dependency graph will not be cyclic by accident at that size; explicit topology checks are an artifact of 35 modules and 5000 contributors, not 15 crates and 1 contributor.

**Recommendation:** skip the explicit `.import-restrictions` file for now. Revisit if the dependency graph ever becomes confusing or someone adds a load-bearing wrong dependency.

### Pattern 8: Version injection via ldflags

**Verdict: transfers cleanly, easier in Rust.** Rust has three off-the-shelf ways and one is clearly best:

- `vergen` crate: a build.rs that sets `cargo:rustc-env=VERGEN_GIT_SHA=...` and exposes those at compile time via `env!("VERGEN_GIT_SHA")`.
- `built` crate: similar, broader (target triple, profile, time, features).
- `option_env!()` macro + a build.rs writing `cargo:rustc-env=...`.

Adopt `vergen` (or `built`) in `lilo-common`. Every binary that calls `lilo_common::version_string()` gets the same baked-in info. Reproducible builds (SOURCE_DATE_EPOCH) work the same way Go's do.

### Pattern 9: In-tree vs out-of-tree cut (CRI principle)

**Verdict: transfers cleanly, but the cut is different.** This is the most strategically important pattern for Stuart to internalize. The k8s answer: "in-tree is the contract and the reference implementation; out-of-tree is everything that plugs into the contract."

For littleorgans, the analogous question is: what stays in the monorepo, and what becomes a future pluggable thing? Stuart's CLAUDE.md framing already implies the answer:

- **In-tree (in the littleorgans monorepo):** the four substrates (session, runtime, identity, transport), their wire contracts, their reference daemons, their CLIs, helix, the shared crates.
- **Pluggable, eventually:** specific "executor" backends inside the runtime (the equivalent of CRI plugins), specific storage backends inside session (think etcd ↔ pluggable storage), specific identity providers inside identity (OIDC ↔ SAML ↔ proprietary), specific transport observability sinks.

The way to honor the principle is to **define each pluggability boundary as a trait in a `-types`/`-api` crate** that lives in the monorepo, even if the only impl today is the in-tree one. That way, third parties (or Stuart himself in v2) can implement the trait in a separate repo without touching the monorepo.

This is exactly how `k8s.io/cri-api` looks today: the trait (gRPC interface) is in-tree, the implementations (containerd, cri-o) are external.

### Pattern 10: `hack/` script directory

**Verdict: anti-pattern at this scale.** k8s has 100+ shell scripts in `hack/` for codegen, vendor updates, lint, boilerplate enforcement, etc. This is a historical accumulation pre-dating standard Go tooling. Modern Rust has standardised tooling (`cargo fmt`, `cargo clippy`, `cargo test`, `cargo build`) that does most of what hack does. Moon will subsume the build-orchestration parts.

For codegen specifically (protobuf, OpenAPI), use build.rs or a dedicated `xtask` crate. The `cargo xtask` pattern is the modern Rust equivalent of `make update`.

Do not create a `hack/` directory. Use `xtask`, build.rs, and Moon tasks.

### Pattern 11: Per-component config schemas (kubelet config, scheduler config, etc.)

**Verdict: transfers cleanly.** Each daemon has its own config file shape. k8s versions these as their own typed APIs (`kubeletconfig.config.k8s.io/v1beta1`).

For littleorgans: each `*-app` crate ships its own typed config struct + serde derive + a layered loader (defaults → config file → env vars → CLI flags). Lives in `lilo-{substrate}-config` if shared with clients, otherwise in the `-app` crate itself.

The unification of `~/.{rtm,sm,im}` into `~/.lilo/{rtm,sm,im}.toml` (Stuart's driver #4) is exactly this pattern. One config root, per-daemon subtrees, defined as Rust structs in named crates.

### Pattern 12: `test/integration/` with in-process daemon spinup

**Verdict: transfers cleanly. Very high value.** k8s tests that a scheduler in-process can drive a kube-apiserver in-process against an etcd subprocess. For littleorgans the equivalent: a test that spins up an in-process `sm` daemon and an in-process `rtm` daemon and exercises their wire protocol via the published client.

Mechanism: the `*-app` crates already expose `run(matches) -> ExitCode`. Add `pub fn spawn_for_tests(config: TestConfig) -> JoinHandle<...>` that does the same setup without process exit. The integration test crate (`tests/integration/sm_rtm_handshake.rs` at the workspace root, or a dedicated `crates/integration-tests/`) imports the app crates directly and orchestrates them.

This is more powerful than separate-repo integration testing: you can drive end-to-end scenarios at the test boundary that today require running two real binaries via a subprocess harness.

### Pattern 13: `e2e/` for real-binary tests

**Verdict: transfers in spirit, scale-down.** k8s e2e launches actual binaries against actual clusters. For littleorgans v0: a small set of "smoke tests" that exec the actual `lilo` binary in a temp directory, validate it boots, validate basic CLI commands. Lives in `tests/e2e/` at workspace root.

Do not build the full e2e framework. A handful of shell-script-style Rust tests (assert_cmd crate) is fine.

### Pattern 14: `third_party/forked/` for modified upstream code

**Verdict: skip until needed.** k8s has this because at scale, they have had to fork pieces of the Go stdlib and other deps. At Stuart's scale this won't come up. If it does, a `vendor/` directory under MIT-compatible terms is the right answer; don't sweat the layout.

### Pattern 15: `CHANGELOG/CHANGELOG-1.X.md` per minor release

**Verdict: anti-pattern at this scale, transfer in spirit.** k8s has 27 per-minor-release changelog files, mostly auto-generated from PR labels. For littleorgans, use a single `CHANGELOG.md` with sections per version, ideally driven by release-plz (which Stuart already uses). release-plz is the right tool; do not invent a parallel changelog scheme.

### Pattern 16: Single version across all artifacts (Stuart's decision #9)

**Verdict: transfers cleanly. k8s does this implicitly already.** Inside k8s, every binary built from the same commit gets the same baked-in version. The staging-module-versions look different (v0.30.0 vs v1.30.0) only because Go modules require semver and they did not want to commit to v1.0.0 yet.

For littleorgans v0 (single-version-for-everything per direction doc decision #9), this is exactly k8s's behavior. Adopt with confidence. The door-open-to-per-artifact-semver-later (also decision #9) is the same path k8s left open for itself with the v0.X vs v1.X split.

The mechanism: the workspace root `Cargo.toml` declares `version = "0.1.0"` once, and every member crate declares `version.workspace = true`. Bump in one place, every artifact updates.

### Pattern 17: Mirror repos as MIT-licensed read-only artifacts (decision #7)

**Verdict: this maps perfectly to k8s's published-staging-repos model.** k8s does exactly this for client-go, api, apimachinery, kubectl, etc. The mirror repos:
- Carry the same license as the parent (in k8s's case, Apache 2.0 throughout; for littleorgans, MIT throughout per decision #7).
- Have a banner at the top of every README saying "do not PR here, go to the source repo." See `staging/src/k8s.io/api/CONTRIBUTING.md` for the literal text.
- Get tagged with each release.
- Carry their own GitHub Releases with binaries attached (k8s does this for kubectl; littleorgans wants it per-substrate).

Adopt the banner-README pattern verbatim. Adopt the "PRs ignored, file issues in source repo" stance for v0; revisit if community organically forms.

---

## What this means for the migration sequence

Translating the direction doc's open item #3 ("Migration sequencing") through the k8s lens:

1. **Stand up the monorepo with shared plumbing first.** Empty `littleorgans/` Cargo workspace, plus `crates/lilo-common`, `crates/lilo-types`, `crates/lilo-client`, `crates/lilo`. The `lilo` binary doesn't do anything yet beyond `--version` and `--help`. Validate end-to-end: Moon build, CI green, mirror publish dry-run succeeds.

2. **Migrate the first substrate.** Pick the smallest. Each substrate becomes three crates: `crates/lilo-{substrate}-types` (public), `crates/lilo-{substrate}-app` (publish = false), `crates/lilo-{substrate}-core` (publish = false). The `lilo` binary grows a subcommand. The substrate's existing published crates (`lilo-im-core`, etc.) become aliases / wrappers around the new layout if needed.

3. **Stand up the mirror-publishing tool.** Validate against the first substrate. This is the work that has no k8s shortcut; treat it as a discrete project.

4. **Migrate remaining substrates.** Each is the same shape; mostly mechanical.

5. **Add `lilo-common` enrichment as needs surface.** Logging, metrics, config, version, signal handling. Pull common code out as it appears duplicated across substrate `-app` crates.

---

## Summary table

| Pattern | k8s mechanism | littleorgans verdict | Effort to adopt |
| --- | --- | --- | --- |
| `cmd/X` thin shells | `package main` delegating to `app/` lib | **Transfers cleanly** — Cargo `[[bin]]` + argv[0] dispatch | Low |
| `pkg/` for internals | Convention + import-boss | **Transfers in spirit** — Cargo `publish = false` | Free |
| `staging/` dual-citizenship | `go.work` + `replace` + publishing-bot | **k8s-scale only** — Rust doesn't need this | N/A |
| Mirror publishing | publishing-bot rewriting go.mod | **Transfers in spirit** — build a `lilo-mirror-publish` xtask | Medium |
| `vendor/` | `go mod vendor` + license policy | **k8s-scale only** — Cargo.lock + cargo-deny suffices | N/A |
| `component-base` shared plumbing | Single utility module imported everywhere | **Transfers cleanly** — `crates/lilo-common` | Low |
| Single types crate (`k8s.io/api`) | Staging module per contract layer | **Transfers in spirit** — `crates/lilo-types` + `-protocol` | Medium |
| `.import-restrictions` DAG | import-boss + per-dir YAML | **k8s-scale only at four substrates** — revisit at 10+ | N/A for now |
| Version injection | ldflags `-X` into `version.gitCommit` | **Transfers cleanly** — `vergen` or `built` | Low |
| In-tree vs out-of-tree (CRI) | Contract crate + external impls | **Transfers cleanly** — trait in `-types`, impl out-of-tree | Strategic |
| `hack/` script menagerie | 100+ shell scripts | **Anti-pattern at this scale** — use xtask + Moon | N/A |
| Per-component config schemas | Versioned config types per binary | **Transfers cleanly** — typed structs in `-app` crates | Low |
| In-process integration tests | `cmd/X/app` spawned from test framework | **Transfers cleanly, high value** | Medium |
| Real-binary e2e tests | Ginkgo + cluster harnesses | **Scale-down** — `assert_cmd` smoke tests | Low |
| `third_party/forked/` | Tracked forks of upstream | **Skip until needed** | N/A |
| Multi-file `CHANGELOG/` | One file per minor release | **Anti-pattern at this scale** — release-plz output | N/A |
| Single version for all artifacts | Bake same ldflag into every binary | **Transfers cleanly** — `version.workspace = true` | Free |
| MIT mirror repos | Apache mirrors with banner READMEs | **Transfers cleanly** — copy the banner pattern | Free |

---

## Sources consulted

- `README.md`, `AGENTS.md` — top-level project framing and contributor rules.
- `staging/README.md` — the canonical explanation of the staging mechanism.
- `staging/publishing/rules.yaml`, `staging/publishing/import-restrictions.yaml` — the publishing-bot config and the cross-module import-allowlist.
- `go.mod`, `go.work`, `staging/src/k8s.io/client-go/go.mod` — the replace-directive trick and per-module go.mod shape.
- `cmd/kubelet/kubelet.go`, `cmd/kube-apiserver/apiserver.go`, `cmd/kubectl/kubectl.go` — the thin-shell main.go pattern (lines 1-35 in each).
- `cmd/kubelet/app/server.go` (1450 lines) — the heavy-lifting app/ package.
- `hack/lib/golang.sh` (lines 69-345) — binary target enumeration, build flags.
- `hack/lib/version.sh` (lines 151-180) — ldflag construction for version injection.
- `staging/src/k8s.io/component-base/version/base.go` — the ldflag-injection target.
- `staging/src/k8s.io/api/core/v1/types.go` (8519 lines) — the canonical typed API contract example.
- `staging/src/k8s.io/cri-api/pkg/apis/runtime/v1/api.proto` — the kubelet ↔ runtime gRPC contract.
- `pkg/.import-restrictions`, `staging/src/k8s.io/apiserver/.import-restrictions`, `cmd/kube-apiserver/.import-restrictions` — the DAG enforcement files.
- `test/integration/framework/controlplane_utils.go` — in-process apiserver bootstrapping pattern.
- `test/e2e/e2e.go` (lines 1-50, 418 total) — e2e test bootstrap.
- `build/root/Makefile` — top-level orchestration.
- The user's `~/.mdx/projects/helioy-product-direction.md` — locked decisions about Moon, public mirrors, single version, MIT cascading releases.

## Open questions

1. **Mirror publishing tool design.** This is the most novel piece of engineering for littleorgans. Does it run as a Moon task? A GitHub Action? A standalone Rust binary in `tools/`? What is the rewrite contract for path deps in inter-substrate crate references? Worth a separate research/design doc.
2. **Helix's place in the layout.** Decision #5 says Helix moves into the monorepo as an internal consumer of cm/am/fmm/helioy-bus via workspace deps. Where does it sit topologically — at the `crates/` level like a substrate, or under `helix/` as the direction doc's diagram suggests? Affects mirror-publishing rules (Helix should not get a public mirror per decision #12).
3. **Polyglot question.** The direction doc names Moon as the build tool with Rust + TS + Python first-class. The k8s pattern map above assumes Rust-only. For the Electron + web app side (TS), the patterns that transfer are different: Turborepo/Moon task orchestration replaces Make, package.json workspaces replace Cargo workspaces, no staging-equivalent is needed because npm doesn't have Go's path-equals-module problem.
4. **CRI-equivalent boundary identification.** Which boundaries inside littleorgans should be defined as traits-in-types-crates so that v2 can swap implementations? Likely candidates: runtime executor backend, session storage backend, identity provider backend, transport observability sink. Worth a follow-up architectural doc.

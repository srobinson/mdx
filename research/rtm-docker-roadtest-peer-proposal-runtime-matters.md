---
title: rtm Docker Road Test Peer Proposal
type: research
tags: [runtime-matters, docker, rtm, alp-2643, peer-review]
summary: Peer consensus conditions for making rtm Docker isolation execute a real Claude runtime image and survive kill cleanup.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

## Executive Summary

The current Docker isolation path injects a host resolved launcher path into `docker run`, while the example image does not install the Claude runtime binary. The smallest aligned patch is to pass a container resolvable agent command, install Claude Code in the reference Dockerfile, support local image architecture inspection, correct README daemon startup examples, and add regression coverage for absolute host launcher paths.

## Project Metadata

- Language: Rust workspace plus Dockerfile examples
- CLI binary: `rtm` from `crates/rtm-cli`
- Runtime daemon: `crates/rtm-daemon`
- Docker reference image: `examples/dockerfiles/claude.Dockerfile`
- Current branch verified: `nancy/ALP-2643`
- Docker server verified: `27.5.1`

## Architecture

Docker isolation wraps launcher output in the daemon backend:

- `crates/rtm-daemon/src/backend.rs:76-88` routes Docker spawn preparation into `docker_runtime::docker_run_launch`.
- `crates/rtm-daemon/src/docker_runtime.rs:20-44` builds the final host shim argv for `docker run`.
- `crates/rtm-launchers/src/lib.rs:47-52` returns a launcher argv whose first element may be host resolved.
- `crates/rtm-launchers/src/lib.rs:90-108` resolves the launcher binary with `which`, returning an absolute host path when available.
- `crates/rtm-daemon/src/server.rs:41-49` loads `DockerPreflightConfig::from_env()` once at daemon startup.

## Key Patterns

- The Docker image contract is image agnostic: the image owns making `claude`, `codex`, or another runtime binary resolvable on PATH.
- The daemon owns Docker command construction and preflight. Per spawn image selection would require a broader CLI, core, wire, and daemon contract change.
- The README local image example must be self proving without registry only manifest metadata.

## Detailed Findings

### Bug A: host path leaks into container argv

`docker_run_launch` calls `launch.command()?` at `crates/rtm-daemon/src/docker_runtime.rs:27`, then appends it to the Docker argv at `crates/rtm-daemon/src/docker_runtime.rs:30`. Since launcher resolution can produce `/Users/alphab/.local/bin/claude`, Docker attempts to execute a host path that does not exist in the container.

Recommended patch: derive a container command from the original runtime argv, preferably basename preserving plain commands, and append existing arguments. Do not drop the command and rely only on image `CMD`, because runtime selection should remain explicit.

### Bug B: reference Dockerfile lacks Claude Code

`examples/dockerfiles/claude.Dockerfile:14-16` installs only base utilities, then `examples/dockerfiles/claude.Dockerfile:21` declares `CMD ["claude"]`. Direct local probe found no `claude` on PATH.

Recommended patch: install Node 20 and `@anthropic-ai/claude-code` globally before switching to the non root runtime user.

### Bug C: image env is daemon startup bound

`crates/rtm-daemon/src/server.rs:41-49` loads Docker preflight config once. `crates/rtm-daemon/src/backend.rs:81-85` reads the image from daemon config during spawn preparation.

Recommended patch: update README examples to place `RTM_DOCKER_IMAGE=runtime-matters-claude:local` on `rtm daemon start`, not `rtm spawn`.

### Bug D: registry manifest preflight rejects local images

`crates/rtm-daemon/src/docker_preflight.rs:125-146` uses `docker manifest inspect`. Local only images can fail registry lookup even when `docker image inspect` proves they exist locally and match host architecture.

Recommended patch: on arm64, fall back to `docker image inspect --format '{{.Architecture}}'` when manifest lookup fails. Accept local `arm64`, reject known mismatches, and keep the env escape only for unusual operator override.

## Verification Gate

After edits, require:

```bash
just check && just build && just test

docker build -f examples/dockerfiles/claude.Dockerfile -t runtime-matters-claude:local .
docker image inspect runtime-matters-claude:local --format 'user={{json .Config.User}} arch={{.Architecture}} cmd={{json .Config.Cmd}} entrypoint={{json .Config.Entrypoint}}'
docker run --rm runtime-matters-claude:local claude --version

export RTM_HOME="$(mktemp -d)"
export RTM_SOCKET_PATH="$RTM_HOME/rtmd.sock"
export RTM_DB_PATH="$RTM_HOME/rtm.db"
export RTM_DOCKER_IMAGE=runtime-matters-claude:local
cargo run -p rtm-cli -- daemon start >"$RTM_HOME/daemon.log" 2>&1 &
DAEMON_PID=$!
until [ -S "$RTM_SOCKET_PATH" ]; do sleep 0.1; done

SESSION_ID="$(uuidgen | tr '[:upper:]' '[:lower:]')"
cargo run -p rtm-cli -- spawn --runtime claude --session-id "$SESSION_ID" --target headless --isolation docker --cwd "$PWD"
docker ps --filter "name=rtm-$SESSION_ID" --format '{{.Names}} {{.Image}} {{.Status}} {{.Command}}'
docker exec "rtm-$SESSION_ID" sh -lc 'command -v claude && ps -ef | grep -F claude | grep -v grep'
cargo run -p rtm-cli -- kill "$SESSION_ID"
! docker ps --filter "name=rtm-$SESSION_ID" --format '{{.Names}}' | grep -q .
cargo run -p rtm-cli -- daemon stop
wait "$DAEMON_PID" || true
```

## Dependencies

- Docker CLI and daemon
- Node 20 for Claude Code installation
- `@anthropic-ai/claude-code` npm package
- Rust workspace test gates through `just`

## Relevance to Helioy

This patch set determines whether runtime isolation can be validated as a real substrate rather than a host path simulation. The fix also tightens Helioy's worker done bar by requiring real Docker build and run proof, not a fake Docker shim.

## Open Questions

- Whether a future issue should add per spawn Docker image selection.
- Whether the example should use Anthropic devcontainer features instead of direct Node plus npm install commands.


## Round 2 Consensus

Pane A and pane B converged on conditional signoff. The agreed conditions are:

1. `docker_run_launch` must pass a container resolvable command, not the host absolute path. Add a regression test where `argv[0]` is an absolute host path and Docker argv contains `claude`.
2. `examples/dockerfiles/claude.Dockerfile` must install a real Claude Code binary on PATH. `docker run --rm runtime-matters-claude:local claude --version` must succeed.
3. Arm64 preflight must accept local images through `docker image inspect --format '{{.Architecture}}'` fallback when registry manifest inspect fails, while preserving rejection for known non arm64 local images.
4. README must document that `RTM_DOCKER_IMAGE` is read by `rtm daemon start`, and changing it requires daemon restart.
5. Verification must include real Docker build, direct Docker run, daemon start with image env, real `rtm spawn`, visible container and runtime process, real `rtm kill`, and absence of the container afterward. `rtm doctor` may be supplemental health output only, because current `doctor.rs:72-98` does not inspect the configured image.

Additional verified details:

- `crates/rtm-daemon/src/spawn_preflight.rs:96-120` gates the manifest check to `host_arch == "aarch64"`.
- `crates/rtm-cli/tests/common/docker.rs:59-64` executes simulated container commands on the host and can mask host path leakage.
- Existing `crates/rtm-daemon/src/docker_runtime.rs` tests use bare runtime command names, so they do not currently catch absolute path leakage.


## Final Peer Consensus

Pane A conceded the `rtm doctor` objection after rereading `crates/rtm-daemon/src/doctor.rs:72-98`. Current doctor output does not inspect the configured Docker image, so it cannot prove the local image architecture fallback. It remains supplemental health output only unless the doctor surface is expanded.

Both panes reached clean consensus on the patch set definition and final signoff phrase:

`I sign off on the rtm Docker road-test patch set as currently filed`

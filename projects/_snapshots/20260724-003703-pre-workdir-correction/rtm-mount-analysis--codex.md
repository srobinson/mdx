# rtm Docker mount analysis, Codex

## 1. Where docker argv is built

The spawn path reaches Docker argv construction through the daemon handler. `RuntimeRpc::Spawn` runs preflight, builds the launcher `LaunchSpec`, calls `RuntimeBackends::prepare_launch`, stores the launch, then starts the backend (crates/rtm-daemon/src/handler.rs:103-111). `RuntimeBackends::prepare_launch` dispatches Docker requests to `DockerRuntimeBackend.prepare_launch` (crates/rtm-daemon/src/backend.rs:33-42). The Docker backend passes the session id, profile, selected image, launch spec, and target into `docker_runtime::docker_run_launch` (crates/rtm-daemon/src/backend.rs:77-88). `docker_runtime::docker_run_launch` is a wrapper that supplies the resolved Docker binary path to `docker_argv::docker_run_launch` (crates/rtm-daemon/src/docker_runtime.rs:12-27, crates/rtm-daemon/src/docker_runtime.rs:29-37).

The argv construction site is `crates/rtm-daemon/src/docker_argv.rs:14-89`:

```rust
14  pub(crate) fn docker_run_launch(
15      session_id: Uuid,
16      profile: &IsolationProfile,
17      image: &str,
18      launch: &LaunchSpec,
19      target: &SpawnTarget,
20      docker_command: &str,
21  ) -> Result<LaunchSpec> {
22      let command = launch.command()?;
23      let tmux_target = matches!(target, SpawnTarget::Tmux(_));
24      let mut run_argv = docker_run_argv(
25          session_id,
26          profile,
27          image,
28          launch,
29          tmux_target,
30          docker_command,
31      );
32      run_argv.push(container_command(command));
33      run_argv.extend(launch.argv.iter().skip(1).cloned());
34
35      let argv = match target {
36          SpawnTarget::Headless(_) => run_argv,
37          SpawnTarget::Tmux(_) => docker_tmux_attach_argv(run_argv),
38      };
39
40      Ok(LaunchSpec {
41          argv,
42          env: launch.env.clone(),
43          cwd: launch.cwd.clone(),
44          shell_resume: launch.shell_resume.clone(),
45      })
46  }
47
48  fn docker_run_argv(
49      session_id: Uuid,
50      profile: &IsolationProfile,
51      image: &str,
52      launch: &LaunchSpec,
53      tmux_target: bool,
54      docker_command: &str,
55  ) -> Vec<String> {
56      let cwd = path_arg(&launch.cwd);
57      let mut argv = docker_run_base_argv(session_id, cwd, tmux_target, docker_command);
58      if profile.name.as_deref() != Some("own-init") {
59          argv.push("--init".to_owned());
60      }
61      append_env_args(&mut argv, &launch.env);
62      argv.push(image.to_owned());
63      argv
64  }
65
66  fn docker_run_base_argv(
67      session_id: Uuid,
68      cwd: String,
69      tty: bool,
70      docker_command: &str,
71  ) -> Vec<String> {
72      let mut argv = vec![
73          docker_command.to_owned(),
74          "run".to_owned(),
75          "--rm".to_owned(),
76          "--name".to_owned(),
77          container_name(session_id),
78          "--label".to_owned(),
79          format!("{RTM_DOCKER_SESSION_LABEL}={session_id}"),
80          "--mount".to_owned(),
81          format!("type=bind,src={cwd},dst={cwd}"),
82          "--workdir".to_owned(),
83          cwd,
84      ];
85      if tty {
86          argv.extend(["-d".to_owned(), "-i".to_owned(), "-t".to_owned()]);
87      }
88      argv
89  }
```

Docker options must be inserted before the image argument because `docker_run_argv` pushes the image at line 62, and `docker_run_launch` appends the runtime command and its args after that at lines 32-33 (crates/rtm-daemon/src/docker_argv.rs:32-33, crates/rtm-daemon/src/docker_argv.rs:61-63). The tmux path still uses the same `run_argv`, then wraps it in a shell command for `docker attach` (crates/rtm-daemon/src/docker_argv.rs:91-99).

## 2. What `IsolationPolicy::Docker` carries today

`IsolationPolicy` is serde tagged with `type` and `payload`, and the Docker variant carries an `IsolationProfile` (crates/rtm-core/src/isolation.rs:7-13). `IsolationProfile` has one field, `name: Option<String>`, and that field is skipped when it is `None` (crates/rtm-core/src/isolation.rs:60-63). Therefore a plain `docker` policy serializes with an empty payload by serde shape: `Docker(IsolationProfile { name: None })` has no serializable profile fields (crates/rtm-core/src/isolation.rs:7-13, crates/rtm-core/src/isolation.rs:60-63). The nonempty profile shape is covered by the lifecycle serde test, which expects `{"type":"docker","payload":{"name":"locked"}}` when `name` is present (crates/rtm-core/tests/serde_snapshots.rs:401-417).

`SpawnRequest` currently carries `session_id`, `runtime`, `isolation`, `image`, `env`, `cwd`, `target`, `force`, and `shell_resume`; it has no mount field (crates/rtm-core/src/types/spawn.rs:77-92). The CLI exposes `--isolation` as `host|docker[:PROFILE]`, plus separate `--image`, `--cwd`, and `--env` inputs (crates/rtm-cli/src/cli/spawn.rs:14-36). The CLI sends exactly those fields in `SpawnRequest` (crates/rtm-cli/src/cli/spawn.rs:38-72). Docker isolation also clears inherited caller env by default, then applies explicit `--env` overrides (crates/rtm-cli/src/cli/spawn.rs:74-83).

The Docker argv builder has one built in bind mount today: it mounts the spawn cwd to the same path inside the container and sets Docker workdir to that same path (crates/rtm-daemon/src/docker_argv.rs:80-83). This differs from the project and doctor surfaces, which describe `/workspace` as the default or canonical container workspace (PROJECT.md:127-129, crates/rtm-daemon/src/doctor.rs:88-91).

## 3. What `docker:PROFILE` does

The suffix parser only strips `docker:` and stores the remaining string in `IsolationProfile.name` (crates/rtm-core/src/isolation.rs:48-58). Display writes `docker` and appends `:{name}` only when the profile name exists (crates/rtm-core/src/isolation.rs:21-33). Plain `docker` parses as `Docker(IsolationProfile::default())` (crates/rtm-core/src/isolation.rs:36-45).

Current profile names are switches, not config lookups. Preflight accepts `None`, `default`, `own-init`, `allow-root`, and `arm64-manifest-escape`; it rejects `pattern-e`, `tmux-primary`, `privileged`, and every other name (crates/rtm-daemon/src/spawn_preflight.rs:69-102). `own-init` has one argv effect: it suppresses `--init` (crates/rtm-daemon/src/docker_argv.rs:56-60). `allow-root` is a preflight escape hatch for root image metadata (crates/rtm-daemon/src/spawn_preflight.rs:150-153). `arm64-manifest-escape` is a preflight escape hatch for arm64 manifest validation (crates/rtm-daemon/src/spawn_preflight.rs:155-161).

No current daemon profile loader admits mounts. `DaemonConfig` has endpoint, shim path, log root, store, reconcile, and Docker preflight config fields (crates/rtm-daemon/src/server/config.rs:11-18). `DaemonConfig::from_env` builds those fields from runtime path, store, reconcile, and Docker preflight sources (crates/rtm-daemon/src/server/config.rs:21-30). Docker preflight env covers only `RTM_DOCKER_IMAGE`, `RTM_DOCKER_ALLOW_ROOT_IMAGE_USER`, and `RTM_DOCKER_ALLOW_ARM64_MANIFEST_ESCAPE` (crates/rtm-daemon/src/docker_preflight.rs:8-29). The project doc mentions an example operator profile fragment with `mounts`, but that fragment has no matching code field in `DaemonConfig`, `DockerPreflightConfig`, `IsolationProfile`, or `SpawnRequest` (PROJECT.md:174-185, crates/rtm-daemon/src/server/config.rs:11-18, crates/rtm-daemon/src/docker_preflight.rs:13-17, crates/rtm-core/src/isolation.rs:60-63, crates/rtm-core/src/types/spawn.rs:77-92).

## 4. Ranked options

| Rank | Option | Estimated change | Surface | Assessment |
| --- | --- | ---: | --- | --- |
| 1 | C. Add daemon env such as `RTM_DOCKER_MOUNTS` and parse it at the argv site | 25 to 45 LOC plus tests | `crates/rtm-daemon/src/docker_argv.rs` | Smallest code surface because argv construction already owns Docker options and image ordering (crates/rtm-daemon/src/docker_argv.rs:56-63). This is global daemon state, not per spawn. It is best for a local experiment, weak as product API. |
| 2 | A. Extend `IsolationProfile` with `mounts` and plumb to `docker_run_argv` | 80 to 140 LOC plus serde and argv tests | `rtm-core`, `rtm-cli`, `rtm-daemon`, snapshots | Best contract. The Docker policy payload is already the Docker specific wire envelope (crates/rtm-core/src/isolation.rs:7-13, crates/rtm-core/src/isolation.rs:60-63). Pre release status makes a protocol shape change acceptable, but it still requires type, parser, serde, and test updates. |
| 3 | B. Add `rtm spawn --mount HOST:CONTAINER` | 100 to 170 LOC plus snapshots | CLI UX plus the same wire and daemon work as option A | A CLI flag alone cannot reach the daemon because `SpawnArgs` has no mount field and sends a `SpawnRequest` with no mount field (crates/rtm-cli/src/cli/spawn.rs:14-36, crates/rtm-cli/src/cli/spawn.rs:56-67, crates/rtm-core/src/types/spawn.rs:77-92). This is the nicest human interface, but it is not the smallest implementation. |

Option B is a UX layer over option A. If the caller is a typed RPC client, option A is enough. If the caller is the `rtm` binary, option B becomes the public syntax for option A (crates/rtm-cli/src/cli/spawn.rs:38-72, crates/rtm-core/src/types/spawn.rs:77-92).

## 5. Recommended one line or smallest delta

No valid one line change lets a caller pass arbitrary `HOST:CONTAINER` mounts. The one line looking spots are the fixed cwd mount at lines 80-81 and the profile name check at lines 58-59, but neither accepts caller supplied mount data (crates/rtm-daemon/src/docker_argv.rs:56-63, crates/rtm-daemon/src/docker_argv.rs:80-83). Hardcoding a second `--mount` at line 80 would enable one local credential test, but it would not let the caller pass a mount and would bake a credential path into daemon code (crates/rtm-daemon/src/docker_argv.rs:72-84, PROJECT.md:174-177).

The smallest realistic delta for the immediate experiment is an env driven daemon hook in `docker_run_argv`, before the image push:

```rust
// before, crates/rtm-daemon/src/docker_argv.rs:56-62
let cwd = path_arg(&launch.cwd);
let mut argv = docker_run_base_argv(session_id, cwd, tmux_target, docker_command);
if profile.name.as_deref() != Some("own-init") {
    argv.push("--init".to_owned());
}
append_env_args(&mut argv, &launch.env);
argv.push(image.to_owned());
```

```rust
// after, minimum hook location
let cwd = path_arg(&launch.cwd);
let mut argv = docker_run_base_argv(session_id, cwd, tmux_target, docker_command);
append_mount_args_from_env(&mut argv)?;
if profile.name.as_deref() != Some("own-init") {
    argv.push("--init".to_owned());
}
append_env_args(&mut argv, &launch.env);
argv.push(image.to_owned());
```

That hook belongs between base argv construction and the image push because Docker options must precede the image (crates/rtm-daemon/src/docker_argv.rs:56-63). A robust implementation would change `docker_run_argv` from `Vec<String>` to `Result<Vec<String>>`, add a parser for one or more `HOST:CONTAINER[:ro]` specs, insert `--mount type=bind,src=...,dst=...`, and add focused tests beside the existing argv tests (crates/rtm-daemon/src/docker_argv.rs:48-64, crates/rtm-daemon/src/docker_argv.rs:149-180). That is a small patch, but it is not one line.

For the durable product API, prefer option A with a CLI flag layered on top. Add a `DockerBindMount` type to `IsolationProfile`, keep mount data in the Docker policy payload, reject malformed specs before Docker, and render each as Docker `--mount` before the image (crates/rtm-core/src/isolation.rs:7-13, crates/rtm-core/src/isolation.rs:60-63, crates/rtm-cli/src/cli/spawn.rs:14-36, crates/rtm-daemon/src/docker_argv.rs:56-63). This matches the existing protocol boundary and avoids global daemon credential leakage (crates/rtm-core/src/types/spawn.rs:77-92, PROJECT.md:174-177).

## 6. What would break

Accepting arbitrary profile names as mount specs would bypass the current preflight gate that rejects unknown Docker profiles (crates/rtm-daemon/src/spawn_preflight.rs:75-102). That would blur security policy with transport syntax and weaken the existing rejection tests for unsupported profiles (crates/rtm-daemon/src/spawn_preflight/tests.rs:170-194, crates/rtm-daemon/src/spawn_preflight/tests.rs:468-480).

An env var approach is daemon global. Any `RTM_DOCKER_MOUNTS` value would affect every Docker spawn handled by that daemon, while the current `SpawnRequest` model is per spawn for `isolation`, `image`, `env`, `cwd`, `target`, and `force` (crates/rtm-core/src/types/spawn.rs:77-92). That is acceptable for a local proof, risky for shared credentials (PROJECT.md:174-177).

A wire payload change requires serde and snapshot updates. Docker policy serialization is governed by `IsolationPolicy` and `IsolationProfile` (crates/rtm-core/src/isolation.rs:7-13, crates/rtm-core/src/isolation.rs:60-63). Existing tests assert current Docker isolation JSON when `name` is present (crates/rtm-core/tests/serde_snapshots.rs:401-417).

Any new mount parser must handle colons and path edge cases deliberately. The requested `-v HOST:CONTAINER` shorthand is compact, but current Docker argv generation uses `--mount type=bind,src=...,dst=...` for the cwd bind mount (crates/rtm-daemon/src/docker_argv.rs:80-83). Staying with `--mount` keeps the style consistent, but commas in paths need validation or rejection because Docker `--mount` uses comma separated key value fields (crates/rtm-daemon/src/docker_argv.rs:80-83).

The workspace contract needs attention before mounting credentials into runtime home paths. Docs and doctor report `/workspace` as the canonical default, while current argv mounts and works in the caller cwd path inside the container (PROJECT.md:127-129, crates/rtm-daemon/src/doctor.rs:88-91, crates/rtm-daemon/src/docker_argv.rs:80-83). A credential mount to `/root/.claude` also may not help an image running as a non root user, and the image contract requires a non root `USER` by default (PROJECT.md:142-145).

## Verification notes

The fmm index was present and current for all 135 indexed files via `fmm validate`. The structural path above used fmm file outlines, symbol reads, dependency graph, and targeted line reads. No target code was modified.

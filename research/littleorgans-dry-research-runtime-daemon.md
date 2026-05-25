slice: runtime-daemon
scope: internal/runtime/daemon
DUP
internal/runtime/daemon/src/event_log.rs:L126-L153 :: internal/runtime/daemon/src/event_log.rs:L209-L235 | event append persistence path | high
internal/runtime/daemon/src/service.rs:L56-L82 :: internal/runtime/daemon/src/server/runner.rs:L18-L40 | daemon bootstrap and reconcile setup | high
internal/runtime/daemon/src/docker_runtime.rs:L52-L68 :: internal/runtime/daemon/src/docker_runtime.rs:L71-L86 | docker running probe async blocking | med
internal/runtime/daemon/src/docker_preflight.rs:L94-L122 :: internal/runtime/daemon/src/docker_preflight.rs:L147-L175 | docker image inspect metadata flow | med
internal/runtime/daemon/src/docker_preflight.rs:L193-L200 :: internal/runtime/daemon/src/docker_runtime.rs:L116-L123 | stderr fallback helper | med
internal/runtime/daemon/src/backend.rs:L65-L69 :: internal/runtime/daemon/src/backend.rs:L91-L95 | backend shim spawn body | med
internal/runtime/daemon/src/server/termination.rs:L114-L132 :: internal/runtime/daemon/src/server/termination.rs:L134-L156 | terminal lifecycle update flow | med
internal/runtime/daemon/src/docker_argv.rs:L323-L332 :: internal/runtime/daemon/src/docker_argv.rs:L368-L377 | docker launch test setup | low
internal/runtime/daemon/src/spawn_preflight/tests/mounts.rs:L39-L47 :: internal/runtime/daemon/src/spawn_preflight/tests/mounts.rs:L62-L70 | preflight pass assertion wrapper | low
internal/runtime/daemon/src/server/tests.rs:L9-L21 :: internal/runtime/daemon/src/server/tests.rs:L30-L42 | terminal nudge failure assertion | low
internal/runtime/daemon/src/service.rs:L134-L146 :: internal/runtime/daemon/src/service.rs:L160-L176 | service config fixture | low
internal/runtime/daemon/src/backend.rs:L186-L201 :: internal/runtime/daemon/src/shim_socket.rs:L254-L265 | daemon config fixture | low

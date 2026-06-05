---
title: "Tier 2 spike: mitmproxy runtime reverse mode mutation"
type: research
tags: [transport-matters, performance, proxy, mitmproxy, captured-run, tier-2]
summary: "mitmproxy 12.2.2 can add and remove reverse proxy modes at runtime on one live DumpMaster; flows expose both listen sockname and proxy_mode for run attribution."
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

# Tier 2 spike: mitmproxy runtime reverse mode mutation

## Verdict

**YES runtime mode mutation.** On mitmproxy 12.2.2, a live `mitmproxy.tools.dump.DumpMaster` accepted `master.options.update(mode=[...])` while running. The proxy added a new `reverse:...@127.0.0.1:PORT` listener, removed an existing listener, kept untouched listeners working, and attributed each flow to the correct listen port.

## Version and repo resolution

- Repo resolver: `api/src/transport_matters/cli/launch_runtime.py:75-86` resolves a runnable `mitmdump` from the venv scripts dir first, then `PATH`.
- Dependency declaration: `api/pyproject.toml:41` has `mitmproxy>=12.2,<13`.
- Lockfile: `api/uv.lock:839-871` pins `mitmproxy` 12.2.2.
- Runtime command: `api/.venv/bin/mitmdump --version` reported `Mitmproxy: 12.2.2`, `Python: 3.14.5`, `OpenSSL: 3.5.6`, `Platform: macOS-26.5.1-arm64-arm-64bit-Mach-O`.

## Exact API used

The experiment started mitmproxy in process:

```python
opts = options.Options(
    confdir=confdir,
    listen_host="127.0.0.1",
    mode=[mode_a, mode_keep],
)
master = DumpMaster(opts, with_termlog=False, with_dumper=False)
```

It mutated the live listener set through:

```python
master.options.update(mode=[mode_a, mode_keep, mode_b])
master.options.update(mode=[mode_keep, mode_b])
```

Source support:

- `mitmproxy/options.py:108-120` defines `mode` as a sequence and documents multiple proxy server types plus per mode `@listen_port` or `@listen_host:listen_port` overrides.
- `mitmproxy/addons/proxyserver.py:258-304` parses updated `mode` values, checks duplicate listen addresses, and, when running, schedules `self.servers.update(modes)`.
- `mitmproxy/addons/proxyserver.py:55-99` preserves existing matching instances, starts missing ones, stops removed ones, and updates under a lock.
- `mitmproxy/addons/proxyserver.py:306-310` uses the same `Servers.update` path for initial server setup.

Caveat: `master.options.update(...)` schedules the server update asynchronously through the proxyserver addon. Production code should wait for readiness by polling the new listener, observing `proxyserver.servers.is_updating`, or using an explicit control acknowledgement. Treat route registration as complete only after the new listener accepts a probe.

## Flow to listen port attribution signal

Use `flow.client_conn.proxy_mode.custom_listen_port` as the primary mode signal and `flow.client_conn.sockname[1]` as the concrete local socket signal. In this experiment they matched for every request. `flow.client_conn.proxy_mode.full_spec` also carried the complete reverse spec, including the listen port. `flow.server_conn.address` identified the upstream target, which is useful as a sanity check but not as the run key.

Source support:

- `mitmproxy/connection.py:174-190` defines `Client.sockname` as the local address that received the connection and stores `proxy_mode` on the client connection.
- `mitmproxy/proxy/server.py:473-479` constructs the client from `writer.get_extra_info("sockname")` and assigns `proxy_mode=mode`.
- `mitmproxy/proxy/mode_servers.py:193-195` passes the server instance mode into the live connection handler.

Observed record example:

```json
{"path":"/after-add-b","client_sockname":["127.0.0.1",58733],"proxy_mode_custom_listen_port":58733,"proxy_mode_full_spec":"reverse:http://127.0.0.1:58730@127.0.0.1:58733","server_address_at_request":["127.0.0.1",58730]}
```

## Architecture consequence

Choose **incremental register and deregister on a single shared proxy** for Tier 2. A proxy pool or restart with debounce is not required for basic route churn.

Recommended design consequences:

1. Keep one long lived shared mitmproxy process.
2. Allocate one loopback listen port per captured run.
3. Register a per run binding keyed by listen port before exposing the new mode.
4. Append a `reverse:UPSTREAM@127.0.0.1:PORT` entry with `master.options.update(mode=[...])`.
5. Wait for readiness on the new listener before spawning the client.
6. On teardown, remove the mode, wait for the listener to close, then delete the binding after in flight flows drain.
7. In addon handlers, resolve the binding from `flow.client_conn.proxy_mode.custom_listen_port` or `flow.client_conn.sockname[1]`.
8. Keep a bounded supervisor story because one shared proxy becomes a shared failure domain.

## Empirical result summary

Initial state:

- `A` listener proxied to upstream `A`.
- `KEEP` listener proxied to upstream `KEEP`.

Runtime add:

- Added `B` listener with `master.options.update(mode=[A, KEEP, B])`.
- `B` proxied to upstream `B`.
- `KEEP` still proxied to `KEEP`.
- `A` still proxied to `A`.

Runtime remove:

- Removed `A` with `master.options.update(mode=[KEEP, B])`.
- Curl to `A` failed with exit 7, connection refused.
- `KEEP` still proxied to `KEEP`.
- `B` still proxied to `B`.

## Experiment script

Path: `/tmp/tm_mitm_runtime_modes_spike.py`

```python
#!/usr/bin/env python3
import asyncio
import contextlib
import http.server as http_server
import importlib.metadata
import json
import os
import socket
import socketserver
import tempfile
import threading
import time
from pathlib import Path

from mitmproxy import http as mitm_http, options
from mitmproxy.tools.dump import DumpMaster


def reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class LabelHandler(http_server.BaseHTTPRequestHandler):
    label = "unset"

    def do_GET(self):
        body = f"upstream={self.label} path={self.path}\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http_server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_upstream(label: str, port: int):
    handler = type(f"{label}Handler", (LabelHandler,), {"label": label})
    server = ThreadedHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, name=f"upstream-{label}", daemon=True)
    thread.start()
    return server


class FlowRecorder:
    def __init__(self):
        self.started = asyncio.Event()
        self.records = []

    def running(self):
        self.started.set()

    def request(self, flow: mitm_http.HTTPFlow):
        mode = flow.client_conn.proxy_mode
        self.records.append(
            {
                "hook": "request",
                "path": flow.request.path,
                "client_peername": flow.client_conn.peername,
                "client_sockname": flow.client_conn.sockname,
                "proxy_mode_full_spec": getattr(mode, "full_spec", repr(mode)),
                "proxy_mode_custom_listen_port": getattr(mode, "custom_listen_port", None),
                "proxy_mode_data": getattr(mode, "data", None),
                "server_address_at_request": flow.server_conn.address,
            }
        )

    def response(self, flow: mitm_http.HTTPFlow):
        mode = flow.client_conn.proxy_mode
        self.records.append(
            {
                "hook": "response",
                "path": flow.request.path,
                "status_code": flow.response.status_code if flow.response else None,
                "client_peername": flow.client_conn.peername,
                "client_sockname": flow.client_conn.sockname,
                "proxy_mode_full_spec": getattr(mode, "full_spec", repr(mode)),
                "proxy_mode_custom_listen_port": getattr(mode, "custom_listen_port", None),
                "proxy_mode_data": getattr(mode, "data", None),
                "server_address_at_response": flow.server_conn.address,
                "server_peername_at_response": flow.server_conn.peername,
            }
        )


async def curl(url: str, *, expect_success: bool = True) -> dict:
    cmd = ["curl", "--max-time", "2", "-sS", url]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    result = {
        "cmd": " ".join(cmd),
        "exit": proc.returncode,
        "stdout": out.decode(errors="replace"),
        "stderr": err.decode(errors="replace"),
    }
    ok = proc.returncode == 0
    if expect_success and not ok:
        raise AssertionError(f"curl failed unexpectedly: {result}")
    if not expect_success and ok:
        raise AssertionError(f"curl succeeded unexpectedly: {result}")
    return result


async def retry_curl(url: str, *, expect_success: bool, label: str, timeout: float = 8.0) -> dict:
    deadline = time.monotonic() + timeout
    last = None
    while True:
        try:
            result = await curl(url, expect_success=expect_success)
            print(f"{label} {json.dumps(result, sort_keys=True)}", flush=True)
            return result
        except AssertionError as exc:
            last = exc
            if time.monotonic() >= deadline:
                raise AssertionError(f"{label} timed out: {last}") from exc
            await asyncio.sleep(0.1)


async def wait_proxy_update_idle(master: DumpMaster) -> None:
    await asyncio.sleep(0.05)
    proxyserver = master.addons.get("proxyserver")
    deadline = time.monotonic() + 8.0
    while getattr(proxyserver.servers, "is_updating", False):
        if time.monotonic() >= deadline:
            raise TimeoutError("proxyserver.servers stayed updating")
        await asyncio.sleep(0.05)


async def main() -> None:
    version = importlib.metadata.version("mitmproxy")
    print(f"MITMPROXY_VERSION={version}", flush=True)

    upstream_a = reserve_port()
    upstream_keep = reserve_port()
    upstream_b = reserve_port()
    listen_a = reserve_port()
    listen_keep = reserve_port()
    listen_b = reserve_port()

    servers = [
        start_upstream("A", upstream_a),
        start_upstream("KEEP", upstream_keep),
        start_upstream("B", upstream_b),
    ]

    mode_a = f"reverse:http://127.0.0.1:{upstream_a}@127.0.0.1:{listen_a}"
    mode_keep = f"reverse:http://127.0.0.1:{upstream_keep}@127.0.0.1:{listen_keep}"
    mode_b = f"reverse:http://127.0.0.1:{upstream_b}@127.0.0.1:{listen_b}"

    confdir = tempfile.mkdtemp(prefix="tm-mitm-conf-")
    opts = options.Options(
        confdir=confdir,
        listen_host="127.0.0.1",
        mode=[mode_a, mode_keep],
    )
    master = DumpMaster(opts, with_termlog=False, with_dumper=False)
    recorder = FlowRecorder()
    master.addons.add(recorder)

    print(f"UPSTREAM_PORTS={json.dumps({'A': upstream_a, 'KEEP': upstream_keep, 'B': upstream_b}, sort_keys=True)}", flush=True)
    print(f"LISTEN_PORTS={json.dumps({'A': listen_a, 'KEEP': listen_keep, 'B': listen_b}, sort_keys=True)}", flush=True)
    print(f"INITIAL_MODES={json.dumps([mode_a, mode_keep])}", flush=True)

    run_task = asyncio.create_task(master.run(), name="mitmproxy-master")
    try:
        await asyncio.wait_for(recorder.started.wait(), timeout=12)
        await wait_proxy_update_idle(master)

        await retry_curl(f"http://127.0.0.1:{listen_a}/initial-a", expect_success=True, label="CURL_INITIAL_A")
        await retry_curl(f"http://127.0.0.1:{listen_keep}/initial-keep", expect_success=True, label="CURL_INITIAL_KEEP")

        add_modes = [mode_a, mode_keep, mode_b]
        print(f"ACTION_ADD_API=master.options.update(mode={json.dumps(add_modes)})", flush=True)
        master.options.update(mode=add_modes)
        await wait_proxy_update_idle(master)
        await retry_curl(f"http://127.0.0.1:{listen_b}/after-add-b", expect_success=True, label="CURL_AFTER_ADD_B")
        await retry_curl(f"http://127.0.0.1:{listen_keep}/after-add-keep", expect_success=True, label="CURL_AFTER_ADD_KEEP")
        await retry_curl(f"http://127.0.0.1:{listen_a}/after-add-a", expect_success=True, label="CURL_AFTER_ADD_A")

        remove_modes = [mode_keep, mode_b]
        print(f"ACTION_REMOVE_API=master.options.update(mode={json.dumps(remove_modes)})", flush=True)
        master.options.update(mode=remove_modes)
        await wait_proxy_update_idle(master)
        await retry_curl(f"http://127.0.0.1:{listen_a}/after-remove-a", expect_success=False, label="CURL_AFTER_REMOVE_A_EXPECT_FAIL")
        await retry_curl(f"http://127.0.0.1:{listen_keep}/after-remove-keep", expect_success=True, label="CURL_AFTER_REMOVE_KEEP")
        await retry_curl(f"http://127.0.0.1:{listen_b}/after-remove-b", expect_success=True, label="CURL_AFTER_REMOVE_B")

        print("ATTRIBUTION_RECORDS_JSON=" + json.dumps(recorder.records, sort_keys=True), flush=True)
        summary = {
            "verdict": "YES",
            "mutation_api": "master.options.update(mode=[...])",
            "flow_attribution_signal": "flow.client_conn.sockname[1] and flow.client_conn.proxy_mode.full_spec/custom_listen_port",
            "confdir": confdir,
        }
        print("SUMMARY_JSON=" + json.dumps(summary, sort_keys=True), flush=True)
    finally:
        master.shutdown()
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.wait_for(run_task, timeout=8)
        for server in servers:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    asyncio.run(main())

```

## Observed command output

Command:

```bash
api/.venv/bin/python /tmp/tm_mitm_runtime_modes_spike.py > /tmp/tm_mitm_runtime_modes_spike.out 2>&1; code=$?; echo EXIT=$code >> /tmp/tm_mitm_runtime_modes_spike.out
```

Output:

```text
MITMPROXY_VERSION=12.2.2
UPSTREAM_PORTS={"A": 58728, "B": 58730, "KEEP": 58729}
LISTEN_PORTS={"A": 58731, "B": 58733, "KEEP": 58732}
INITIAL_MODES=["reverse:http://127.0.0.1:58728@127.0.0.1:58731", "reverse:http://127.0.0.1:58729@127.0.0.1:58732"]
CURL_INITIAL_A {"cmd": "curl --max-time 2 -sS http://127.0.0.1:58731/initial-a", "exit": 0, "stderr": "", "stdout": "upstream=A path=/initial-a\n"}
CURL_INITIAL_KEEP {"cmd": "curl --max-time 2 -sS http://127.0.0.1:58732/initial-keep", "exit": 0, "stderr": "", "stdout": "upstream=KEEP path=/initial-keep\n"}
ACTION_ADD_API=master.options.update(mode=["reverse:http://127.0.0.1:58728@127.0.0.1:58731", "reverse:http://127.0.0.1:58729@127.0.0.1:58732", "reverse:http://127.0.0.1:58730@127.0.0.1:58733"])
CURL_AFTER_ADD_B {"cmd": "curl --max-time 2 -sS http://127.0.0.1:58733/after-add-b", "exit": 0, "stderr": "", "stdout": "upstream=B path=/after-add-b\n"}
CURL_AFTER_ADD_KEEP {"cmd": "curl --max-time 2 -sS http://127.0.0.1:58732/after-add-keep", "exit": 0, "stderr": "", "stdout": "upstream=KEEP path=/after-add-keep\n"}
CURL_AFTER_ADD_A {"cmd": "curl --max-time 2 -sS http://127.0.0.1:58731/after-add-a", "exit": 0, "stderr": "", "stdout": "upstream=A path=/after-add-a\n"}
ACTION_REMOVE_API=master.options.update(mode=["reverse:http://127.0.0.1:58729@127.0.0.1:58732", "reverse:http://127.0.0.1:58730@127.0.0.1:58733"])
CURL_AFTER_REMOVE_A_EXPECT_FAIL {"cmd": "curl --max-time 2 -sS http://127.0.0.1:58731/after-remove-a", "exit": 7, "stderr": "curl: (7) Failed to connect to 127.0.0.1 port 58731 after 0 ms: Couldn't connect to server\n", "stdout": ""}
CURL_AFTER_REMOVE_KEEP {"cmd": "curl --max-time 2 -sS http://127.0.0.1:58732/after-remove-keep", "exit": 0, "stderr": "", "stdout": "upstream=KEEP path=/after-remove-keep\n"}
CURL_AFTER_REMOVE_B {"cmd": "curl --max-time 2 -sS http://127.0.0.1:58733/after-remove-b", "exit": 0, "stderr": "", "stdout": "upstream=B path=/after-remove-b\n"}
ATTRIBUTION_RECORDS_JSON=[{"client_peername": ["127.0.0.1", 58734], "client_sockname": ["127.0.0.1", 58731], "hook": "request", "path": "/initial-a", "proxy_mode_custom_listen_port": 58731, "proxy_mode_data": "http://127.0.0.1:58728", "proxy_mode_full_spec": "reverse:http://127.0.0.1:58728@127.0.0.1:58731", "server_address_at_request": ["127.0.0.1", 58728]}, {"client_peername": ["127.0.0.1", 58734], "client_sockname": ["127.0.0.1", 58731], "hook": "response", "path": "/initial-a", "proxy_mode_custom_listen_port": 58731, "proxy_mode_data": "http://127.0.0.1:58728", "proxy_mode_full_spec": "reverse:http://127.0.0.1:58728@127.0.0.1:58731", "server_address_at_response": ["127.0.0.1", 58728], "server_peername_at_response": ["127.0.0.1", 58728], "status_code": 200}, {"client_peername": ["127.0.0.1", 58736], "client_sockname": ["127.0.0.1", 58732], "hook": "request", "path": "/initial-keep", "proxy_mode_custom_listen_port": 58732, "proxy_mode_data": "http://127.0.0.1:58729", "proxy_mode_full_spec": "reverse:http://127.0.0.1:58729@127.0.0.1:58732", "server_address_at_request": ["127.0.0.1", 58729]}, {"client_peername": ["127.0.0.1", 58736], "client_sockname": ["127.0.0.1", 58732], "hook": "response", "path": "/initial-keep", "proxy_mode_custom_listen_port": 58732, "proxy_mode_data": "http://127.0.0.1:58729", "proxy_mode_full_spec": "reverse:http://127.0.0.1:58729@127.0.0.1:58732", "server_address_at_response": ["127.0.0.1", 58729], "server_peername_at_response": ["127.0.0.1", 58729], "status_code": 200}, {"client_peername": ["127.0.0.1", 58738], "client_sockname": ["127.0.0.1", 58733], "hook": "request", "path": "/after-add-b", "proxy_mode_custom_listen_port": 58733, "proxy_mode_data": "http://127.0.0.1:58730", "proxy_mode_full_spec": "reverse:http://127.0.0.1:58730@127.0.0.1:58733", "server_address_at_request": ["127.0.0.1", 58730]}, {"client_peername": ["127.0.0.1", 58738], "client_sockname": ["127.0.0.1", 58733], "hook": "response", "path": "/after-add-b", "proxy_mode_custom_listen_port": 58733, "proxy_mode_data": "http://127.0.0.1:58730", "proxy_mode_full_spec": "reverse:http://127.0.0.1:58730@127.0.0.1:58733", "server_address_at_response": ["127.0.0.1", 58730], "server_peername_at_response": ["127.0.0.1", 58730], "status_code": 200}, {"client_peername": ["127.0.0.1", 58740], "client_sockname": ["127.0.0.1", 58732], "hook": "request", "path": "/after-add-keep", "proxy_mode_custom_listen_port": 58732, "proxy_mode_data": "http://127.0.0.1:58729", "proxy_mode_full_spec": "reverse:http://127.0.0.1:58729@127.0.0.1:58732", "server_address_at_request": ["127.0.0.1", 58729]}, {"client_peername": ["127.0.0.1", 58740], "client_sockname": ["127.0.0.1", 58732], "hook": "response", "path": "/after-add-keep", "proxy_mode_custom_listen_port": 58732, "proxy_mode_data": "http://127.0.0.1:58729", "proxy_mode_full_spec": "reverse:http://127.0.0.1:58729@127.0.0.1:58732", "server_address_at_response": ["127.0.0.1", 58729], "server_peername_at_response": ["127.0.0.1", 58729], "status_code": 200}, {"client_peername": ["127.0.0.1", 58742], "client_sockname": ["127.0.0.1", 58731], "hook": "request", "path": "/after-add-a", "proxy_mode_custom_listen_port": 58731, "proxy_mode_data": "http://127.0.0.1:58728", "proxy_mode_full_spec": "reverse:http://127.0.0.1:58728@127.0.0.1:58731", "server_address_at_request": ["127.0.0.1", 58728]}, {"client_peername": ["127.0.0.1", 58742], "client_sockname": ["127.0.0.1", 58731], "hook": "response", "path": "/after-add-a", "proxy_mode_custom_listen_port": 58731, "proxy_mode_data": "http://127.0.0.1:58728", "proxy_mode_full_spec": "reverse:http://127.0.0.1:58728@127.0.0.1:58731", "server_address_at_response": ["127.0.0.1", 58728], "server_peername_at_response": ["127.0.0.1", 58728], "status_code": 200}, {"client_peername": ["127.0.0.1", 58745], "client_sockname": ["127.0.0.1", 58732], "hook": "request", "path": "/after-remove-keep", "proxy_mode_custom_listen_port": 58732, "proxy_mode_data": "http://127.0.0.1:58729", "proxy_mode_full_spec": "reverse:http://127.0.0.1:58729@127.0.0.1:58732", "server_address_at_request": ["127.0.0.1", 58729]}, {"client_peername": ["127.0.0.1", 58745], "client_sockname": ["127.0.0.1", 58732], "hook": "response", "path": "/after-remove-keep", "proxy_mode_custom_listen_port": 58732, "proxy_mode_data": "http://127.0.0.1:58729", "proxy_mode_full_spec": "reverse:http://127.0.0.1:58729@127.0.0.1:58732", "server_address_at_response": ["127.0.0.1", 58729], "server_peername_at_response": ["127.0.0.1", 58729], "status_code": 200}, {"client_peername": ["127.0.0.1", 58747], "client_sockname": ["127.0.0.1", 58733], "hook": "request", "path": "/after-remove-b", "proxy_mode_custom_listen_port": 58733, "proxy_mode_data": "http://127.0.0.1:58730", "proxy_mode_full_spec": "reverse:http://127.0.0.1:58730@127.0.0.1:58733", "server_address_at_request": ["127.0.0.1", 58730]}, {"client_peername": ["127.0.0.1", 58747], "client_sockname": ["127.0.0.1", 58733], "hook": "response", "path": "/after-remove-b", "proxy_mode_custom_listen_port": 58733, "proxy_mode_data": "http://127.0.0.1:58730", "proxy_mode_full_spec": "reverse:http://127.0.0.1:58730@127.0.0.1:58733", "server_address_at_response": ["127.0.0.1", 58730], "server_peername_at_response": ["127.0.0.1", 58730], "status_code": 200}]
SUMMARY_JSON={"confdir": "/var/folders/15/l6zdb_ln4tq4slrn7c3hps7m0000gn/T/tm-mitm-conf-f756sl15", "flow_attribution_signal": "flow.client_conn.sockname[1] and flow.client_conn.proxy_mode.full_spec/custom_listen_port", "mutation_api": "master.options.update(mode=[...])", "verdict": "YES"}
EXIT=0

```

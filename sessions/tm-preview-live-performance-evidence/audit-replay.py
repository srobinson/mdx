#!/usr/bin/env python3
"""Read captured artifacts, reuse pure replay APIs, write only audit output.
Run with repository api/.venv/bin/python -B and --repo when located elsewhere.
No storage backend, database, network, repair service, or capture writer is invoked.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser()
parser.add_argument('--repo', type=Path, default=Path('/Users/alphab/Dev/LLM/DEV/helioy/transport-matters'))
args = parser.parse_args()
out = Path(__file__).resolve().parent
repo = args.repo.resolve()
head = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
expected = '0c6a57559a1c6cc2487946b9c614517ebbc18fbb'
if head != expected:
    raise SystemExit(f'Expected {expected}, found {head}')
status_before = subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'], text=True)
sys.path.insert(0, str(repo / 'api/src'))


def guard(event, values):
    if event == 'open':
        path, mode, flags = values
        writing = isinstance(mode, str) and any(c in mode for c in 'wax+')
        writing = writing or isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writing and (not isinstance(path, (str, bytes, os.PathLike)) or Path(os.fsdecode(path)).resolve().parent != out or not Path(os.fsdecode(path)).name.startswith('audit-')):
            raise PermissionError('Audit denies write outside audit artifacts')
    if event in {'os.remove', 'os.rename', 'os.rmdir', 'os.mkdir', 'os.truncate', 'os.chmod', 'os.utime', 'os.link', 'os.symlink', 'subprocess.Popen', 'socket.connect', 'socket.bind'}:
        raise PermissionError(f'Audit denies {event}')


sys.addaudithook(guard)
from transport_matters.storage.disk_layout import DiskStorageLayout
from transport_matters.storage.base import ExchangeArtifacts, CodexDerivedArtifactFiles
from transport_matters.storage.codex_stream import apply_stream
from transport_matters.codex.derivation_codec import serialize_codex_events_jsonl, serialize_codex_turn_json
from transport_matters.codex.repair_rebuild import rebuild_codex_derived_artifacts
from transport_matters.codex.response_parser import parse_codex_response_payloads
from transport_matters.codex.protocol import CODEX_TERMINAL_EVENT_TYPES

root = Path.home() / '.transport-matters-preview/workspaces/dev-helioy-transport-matters/ecd9b0df'
runs = ['642f2051-70cb-4e77-8bb4-7c10d09cfdef', 'dd117da2-e994-4ec5-8515-8bc0e68ba303']


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def inventory(directory):
    return {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(directory.iterdir()) if p.is_file()}


def compare(left, right):
    def value(item):
        if isinstance(item, tuple):
            return [x.model_dump(mode='json') for x in item]
        return item.model_dump(mode='json') if item is not None else None
    a, b = value(left), value(right)
    return {'equal': a == b, 'stored_sha256': digest(a), 'replayed_sha256': digest(b)}


def audit(directory):
    before = inventory(directory)
    paths = DiskStorageLayout(directory.parent).artifact_paths(directory)
    fields = {}
    for field in ['request_raw', 'request_ir', 'request_curated_raw', 'request_curated_ir', 'request_audit', 'response_raw', 'response_ir', 'transport', 'turn']:
        path = getattr(paths, field)
        if path.exists():
            fields[field] = path.read_bytes() if field.endswith('_raw') else json.loads(path.read_bytes())
    if paths.events.exists():
        fields['events'] = [json.loads(line) for line in paths.events.read_bytes().splitlines() if line.strip()]
    snapshot = ExchangeArtifacts.model_validate(fields)
    artifacts = apply_stream(paths.codex_stream, snapshot)
    artifacts.validate_codex_derived_artifacts()
    turn = artifacts.turn
    if turn is None or artifacts.transport is None:
        return {'path': str(directory), 'error': 'Missing derived turn or transport'}
    derived_files = CodexDerivedArtifactFiles(events_jsonl=serialize_codex_events_jsonl(artifacts.events or ()), turn_json=serialize_codex_turn_json(turn))
    replay, diagnostics = rebuild_codex_derived_artifacts(exchange_id=turn.exchange_id, artifacts=artifacts, derived_files=derived_files)
    server = [m for m in artifacts.transport.messages if m.direction == 'server' and not m.dropped and isinstance(m.payload_json, dict)]
    payloads = [m.payload_json for m in server]
    response = parse_codex_response_payloads(payloads, default_model=artifacts.request_ir.model)
    terminals = [{'type': m.payload_json.get('type'), 'ts': m.ts.isoformat() if m.ts else None, 'status': m.payload_json.get('response', {}).get('status')} for m in server if m.payload_json.get('type') in CODEX_TERMINAL_EVENT_TYPES]
    checks = {'events': compare(artifacts.events, replay.events), 'turn': compare(turn, replay.turn)} if replay else {}
    if artifacts.response_ir is not None:
        checks['response'] = compare(artifacts.response_ir, response)
    journal = paths.codex_stream.read_bytes() if paths.codex_stream.exists() else b''
    stable = before == inventory(directory)
    completed = turn.status == 'completed' and bool(terminals) and artifacts.response_ir is not None
    return {'path': str(directory), 'exchange_id': turn.exchange_id, 'status': turn.status, 'terminal_cause': turn.terminal_cause, 'completed_evidence': completed, 'snapshot_status': snapshot.turn.status if snapshot.turn else None, 'journal_commits': journal.count(b'\n'), 'journal_torn_tail_bytes': len(journal.rsplit(b'\n', 1)[-1]), 'transport_messages': len(artifacts.transport.messages), 'server_event_counts': dict(collections.Counter(p.get('type') for p in payloads)), 'last_server_ts': server[-1].ts.isoformat() if server and server[-1].ts else None, 'provider_terminals': terminals, 'transport_close_present': artifacts.transport.close is not None, 'semantic_events': len(artifacts.events or ()), 'text_chars': turn.text_chars, 'tool_calls': turn.tool_calls, 'response_present': artifacts.response_ir is not None, 'checks': checks, 'diagnostics': [d.model_dump(mode='json') for d in diagnostics], 'source_files_stable': stable, 'source_files': before, 'pass': completed and stable and bool(checks) and all(c['equal'] for c in checks.values()) and not diagnostics}


results = []
for run in runs:
    if results and all(r.get('completed_evidence') for r in results):
        break
    directories = sorted((root / run).glob('*/turn.json'))
    if run == runs[1]:
        directories = [p for p in directories if json.loads(p.read_bytes()).get('status') == 'completed'][:8]
    else:
        directories = directories[-16:]
    for turn_path in directories:
        results.append({'run_id': run, **audit(turn_path.parent)})
report = {'observed_at': datetime.now(timezone.utc).isoformat(), 'source_head': head, 'source_worktree_status_before': status_before, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'scope': runs, 'results': results, 'completed_pass_count': sum(r.get('pass', False) for r in results), 'boundaries': ['Selection bounded to latest 16 primary exchanges and, when incomplete, first 8 completed fallback exchanges.', 'No latency sampling or performance improvement claim.', 'Replay uses captured transport, not an independent vendor transcript.', 'Operator facts and turn identity reuse stored metadata through the existing rebuild API.', 'No capture, database, process, or repository writes. Python audit hook denies network and writes outside audit-prefixed output files.', 'Open exchanges are point-in-time observations, not final parity proof.', 'File hash stability is checked across each read and replay; later producer changes remain possible.', 'Exact source HEAD verified; running preview process build identity is not verified.']}
(out / 'audit-result.json').write_text(json.dumps(report, indent=2) + '\n')
lines = ['---', 'title: Preview Codex replay evidence audit', 'type: sessions', 'tags: [transport-matters, codex, replay, performance]', 'summary: Read-only captured artifact comparison against full replay', 'status: active', 'created: 2026-09-08', 'updated: 2026-09-08', '---', '', f'Observed {report["observed_at"]} at source {head}.', '', f'Completed exchanges passing all comparisons: {report["completed_pass_count"]}.', '']
for r in results:
    lines.append(f'- {r["run_id"]}, {r.get("exchange_id", "unknown")}: status {r.get("status")}; pass {r.get("pass")}; messages {r.get("transport_messages")}; journal commits {r.get("journal_commits")}; comparisons {json.dumps({k: v["equal"] for k, v in r.get("checks", {}).items()})}.')
lines.extend(['', 'A provider terminal, completed turn, and stored response establish exchange completion. A remaining manifest or open WebSocket does not establish an unfinished response. Absent terminal evidence with an open turn establishes only that the captured exchange was still open at observation.', '', 'Rerun:', '', '```sh', f'{repo}/api/.venv/bin/python -B {out}/audit-replay.py', '```', '', 'The DiskStorage read path can rewrite transport during redaction. This script uses DiskStorageLayout and ExchangeArtifacts directly, apply_stream for journal hydration, rebuild_codex_derived_artifacts for full semantic replay, and parse_codex_response_payloads for full response parsing. It does not call the storage reader or repair service.', '', *report['boundaries'], '', 'Exact comparison hashes, input file hashes, provider event counts, terminal timestamps, and diagnostics are in audit-result.json.'])
(out / 'audit-report.md').write_text('\n'.join(lines) + '\n')
print(json.dumps({'completed_pass_count': report['completed_pass_count'], 'exchanges': len(results), 'open_exchanges': [r['exchange_id'] for r in results if r.get('status') == 'open'], 'result': str(out / 'audit-result.json')}))

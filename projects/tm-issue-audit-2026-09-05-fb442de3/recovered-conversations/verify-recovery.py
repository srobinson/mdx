import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'manifest.json').read_text())
total = 0
for run in manifest['runs']:
    name = run['name']
    data = json.loads((root / f'{name}.messages.json').read_text())
    pages = json.loads((root / f'{name}.pages.json').read_text())['pages']
    messages = data['messages']
    assert not pages[0]['result']['has_older'], name
    assert not pages[-1]['result']['has_newer'], name
    assert not any(p['result']['rotated'] for p in pages), name
    assert len(messages) == run['messages'], name
    assert len({m['id'] for m in messages}) == len(messages), name
    assert [m['turn'] for m in messages] == list(range(1, len(messages) + 1)), name
    for message in messages:
        assert message['complete'] and message['fully_recovered'], (name, message['id'])
        assert len(message['text']) == message['total_chars'], (name, message['id'])
    text = (root / f'{name}.md').read_text()
    assert all(m['text'] in text for m in messages), name
    total += len(messages)
print(f'Verified {len(manifest["runs"])} runs and {total} complete messages; no missing pages or rotated history.')

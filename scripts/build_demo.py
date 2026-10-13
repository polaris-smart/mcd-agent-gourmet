"""Publish only the explicitly sanitized snapshot; no credentials or raw responses."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gourmet.core import validate_snapshot
manifest = json.loads((ROOT / 'fixtures/demo-snapshots.json').read_text(encoding='utf-8'))
snapshots = []
for filename in manifest:
    path = (ROOT / 'fixtures' / filename).resolve()
    if path.parent != (ROOT / 'fixtures').resolve():
        raise ValueError('Demo sources must be explicitly listed public fixtures.')
    snapshot = validate_snapshot(json.loads(path.read_text(encoding='utf-8')))
    if snapshot['mode'] != 'snapshot':
        raise SystemExit('Only historical snapshots can be bundled into the public demo.')
    snapshots.append(snapshot)
if not snapshots:
    raise ValueError('At least one public snapshot is required.')
(ROOT / 'docs/data.js').write_text('window.GOURMET_SNAPSHOTS = ' + json.dumps(snapshots,ensure_ascii=False,indent=2).replace('</','<\\/') + ';\nwindow.GOURMET_DATA = window.GOURMET_SNAPSHOTS[0];\n',encoding='utf-8')
print('Built docs/data.js from %d public snapshots' % len(snapshots))

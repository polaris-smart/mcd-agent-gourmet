"""Publish only the explicitly sanitized snapshot; no credentials or raw responses."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gourmet.core import validate_snapshot
p = validate_snapshot(json.loads((ROOT / 'fixtures/snapshot.json').read_text(encoding='utf-8')))
if p['mode'] != 'snapshot':
    raise SystemExit('Only historical snapshots can be bundled into the public demo.')
extra = validate_snapshot(json.loads((ROOT / 'fixtures/customized-snapshot.json').read_text(encoding='utf-8')))
if extra['mode'] != 'snapshot':
    raise SystemExit('Only historical snapshots can be bundled into the public demo.')
(ROOT / 'docs/data.js').write_text('window.GOURMET_SNAPSHOTS = ' + json.dumps([p,extra],ensure_ascii=False,indent=2).replace('</','<\\/') + ';\nwindow.GOURMET_DATA = window.GOURMET_SNAPSHOTS[0];\n',encoding='utf-8')
print('Built docs/data.js from fixtures/snapshot.json')

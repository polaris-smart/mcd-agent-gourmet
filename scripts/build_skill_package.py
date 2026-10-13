"""Build an allowlisted WorkBuddy distribution, with no local account data."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(output):
    files = {'SKILL.md': (ROOT/'SKILL.md').read_text().replace('python3 demo.py', 'python3 scripts/demo.py').replace('--plan fixtures/', '--plan scripts/fixtures/').encode(),
             'LICENSE':(ROOT/'LICENSE').read_bytes()}
    for name in ('demo.py', 'gourmet/__init__.py', 'gourmet/core.py', 'gourmet/mcp.py',
                 'gourmet/live.py', 'gourmet/member.py', 'gourmet/coupons.py', 'gourmet/stores.py', 'gourmet/channels.py',
                 'gourmet/customize.py', 'gourmet/catalog.py', 'fixtures/plan.json',
                 'fixtures/snapshot.json', 'fixtures/customized-snapshot.json', 'fixtures/coupon-demo.json'):
        files['scripts/'+name] = (ROOT/name).read_bytes()
    for name in ('references/mcp-capabilities.md', 'docs/validation.md', 'docs/workbuddy-market.md'):
        target = name if name.startswith('references/') else 'references/'+Path(name).name
        files[target] = (ROOT/name).read_bytes()
    files['SKILL.md'] = files['SKILL.md'].replace(b'docs/validation.md', b'references/validation.md')
    # Validate required marketplace fields without a third-party YAML dependency.
    skill = files['SKILL.md'].decode()
    front = skill.split('---',2)[1]
    for key in ('description','description_zh','description_en','version','author'):
        if not any(line.startswith(key+': ') and line.split(': ',1)[1].strip() for line in front.splitlines()):
            raise ValueError('Missing marketplace field: '+key)
    for name, payload in files.items():
        if name.endswith('.json'):
            data=json.loads(payload)
            def check(value):
                if isinstance(value,dict):
                    if {'token','authorization','couponId','couponCode','accountId','addressId'} & set(value):
                        raise ValueError('Private field in '+name)
                    for item in value.values():check(item)
                elif isinstance(value,list):
                    for item in value:check(item)
            check(data)
    output = Path(output)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,payload in files.items():archive.writestr('mcd-agent-gourmet/'+name,payload)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:raise ValueError('Corrupt archive')
        for name,payload in files.items():
            if archive.read('mcd-agent-gourmet/'+name)!=payload:raise ValueError('Archive mismatch')
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    print(json.dumps({'path':str(output.resolve()),'files':len(files),'sha256':digest},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',required=True,type=Path)
    build(p.parse_args().output)

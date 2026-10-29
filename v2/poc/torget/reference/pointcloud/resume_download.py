#!/usr/bin/env python3
"""Resume the one identified official LAZ download using already-set environment auth.
Never accepts credentials on command line or writes/logs them. No dependency install.
"""
from pathlib import Path
import base64, hashlib, json, os, sys, urllib.request, urllib.error
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
LIMIT_BYTES=200_000_000
item=next(f for f in json.loads((HERE/'search.json').read_text())['features'] if f['id']=='19b002-63925_3225_25')
asset=item['assets']['data']
expected=int(asset['file:size'])
assert expected < LIMIT_BYTES
user=os.environ.get('LM_USER'); password=os.environ.get('LM_PASS')
if not user or not password:
    print('STOP: LM_USER and/or LM_PASS missing. No account access attempted and no raw data downloaded.')
    raise SystemExit(2)
auth=base64.b64encode((user+':'+password).encode()).decode()
outdir=ROOT/'v2/poc/torget/data/downloads';outdir.mkdir(parents=True,exist_ok=True)
out=outdir/asset['title'];part=out.with_suffix(out.suffix+'.partial')
checksum=asset.get('file:checksum','')
expected_sha256=checksum[4:] if checksum.startswith('1220') else None
if out.exists() and out.stat().st_size==expected:
    if not expected_sha256 or hashlib.file_digest(out.open('rb'),'sha256').hexdigest()==expected_sha256:
        print('Already downloaded and verified:',out.name,out.stat().st_size,'bytes')
        raise SystemExit(0)
req=urllib.request.Request(asset['href'],headers={'Authorization':'Basic '+auth,'User-Agent':'Kvarnbyn research PoC'})
try:
    with urllib.request.urlopen(req,timeout=90) as response:
        announced=int(response.headers.get('Content-Length',str(expected)))
        if announced>LIMIT_BYTES or announced!=expected:
            print('STOP: file size differs from reviewed STAC metadata.')
            raise SystemExit(3)
        digest=hashlib.sha256();total=0
        with part.open('wb') as stream:
            while True:
                block=response.read(1<<20)
                if not block:break
                total+=len(block)
                if total>LIMIT_BYTES:raise RuntimeError('Reviewed download limit exceeded')
                digest.update(block);stream.write(block)
except urllib.error.HTTPError as error:
    print('STOP: official data endpoint returned HTTP',error.code,'; no credentials printed.')
    raise SystemExit(4)
if total!=expected or (expected_sha256 and digest.hexdigest()!=expected_sha256):
    print('STOP: downloaded file failed size/checksum verification; partial file retained locally.')
    raise SystemExit(5)
part.replace(out)
print('Downloaded and verified:',out.name,total,'bytes')

"""Fetch one small CC0 pure-sky HDRI with reproducible source information."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parent
ASSET='kloofendal_48d_partly_cloudy_puresky'
UA='KvarnbynFPS-PoC/0.1 (CC0 environment preparation)'
def get(url):
    request=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(request,timeout=60) as response:return response.read()
info=json.loads(get(f'https://api.polyhaven.com/info/{ASSET}'))
files=json.loads(get(f'https://api.polyhaven.com/files/{ASSET}'))
source=files['hdri']['1k']['hdr']
assert source['size']<5_000_000
raw=get(source['url'])
assert len(raw)==source['size']
assert hashlib.md5(raw).hexdigest()==source['md5']
path=ROOT/f'{ASSET}_1k.hdr';path.write_bytes(raw)
manifest={
    'asset_id':ASSET,'name':info['name'],'file':path.name,
    'source_page':f'https://polyhaven.com/a/{ASSET}',
    'source_metadata_api':f'https://api.polyhaven.com/info/{ASSET}',
    'source_file_api':f'https://api.polyhaven.com/files/{ASSET}',
    'source_url':source['url'],'license':'CC0-1.0','license_url':'https://polyhaven.com/license',
    'authors':info['authors'],'source_white_balance_kelvin':info.get('whitebalance'),
    'source_categories':info['categories'],'source_capture_coords':info.get('coords'),
    'retrieved_at':datetime.now(timezone.utc).isoformat(),'bytes':len(raw),
    'md5':source['md5'],'sha256':hashlib.sha256(raw).hexdigest(),
    'resolution':'1k','format':'Radiance HDR, linear high dynamic range',
    'use':'Generic blue daytime sky/clouds and environment lighting proxy, no photographic terrain or location backdrop.',
    'limits':['This is a generic sky proxy, not the actual sky above Kvarnbyn.',
        'Original capture is South Africa, not Sweden; white balance is neutral daylight at 5400K.',
        'Pure-sky edit removes the geographic horizon. The HDRI contains a bright sun, so align or balance it with the scene directional sun to avoid conflicting light directions.',
        'The preview is tone mapped for inspection; use the .hdr source for lighting and Godot PanoramaSkyMaterial.'],
}
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(manifest,ensure_ascii=False,indent=2))

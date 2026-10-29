"""Verify source checksums and portable model structure. Runs in normal Python.
With Blender, also verifies the append/place helper and shared-mesh placements.
"""
from pathlib import Path
import hashlib
import json
import struct

ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'manifest.json').read_text())
checked=0
for maps in [x['maps'] for x in manifest['materials'].values()]+[manifest['foliage_atlas']['maps']]:
    for source in maps.values():
        path=ROOT/source['path']
        assert path.stat().st_size==source['size'],path
        assert hashlib.md5(path.read_bytes()).hexdigest()==source['md5'],path
        checked+=1
models=[]
for path in sorted((ROOT/'vegetation').glob('*.glb')):
    raw=path.read_bytes()
    assert raw[:4]==b'glTF'
    size=struct.unpack_from('<I',raw,12)[0]
    data=json.loads(raw[20:20+size])
    leaves=next(m for m in data['materials'] if m['name'].startswith('Foliage'))
    assert leaves['alphaMode']=='MASK'
    assert .44 < leaves['alphaCutoff'] < .46
    assert leaves['doubleSided']
    triangles=sum(data['accessors'][p['indices']]['count']//3 for m in data['meshes'] for p in m['primitives'])
    assert triangles<15000
    assert all('uri' not in i for i in data['images'])
    models.append({'path':path.name,'bytes':len(raw),'triangles':triangles,'alpha_mode':'MASK','embedded_images':len(data['images'])})
report={'verified_source_files':checked,'source_asset_bytes':manifest['download_bytes'],'models':models}
try:
    import bpy
except ImportError:
    pass
else:
    import sys
    sys.path.insert(0,str(ROOT))
    from blender_vegetation import place_tree
    first=place_tree('Broadleaf_A',location=(10,2,1),scale=1.2)
    second=place_tree('Broadleaf_A',location=(-10,2,1),scale=.8)
    assert tuple(first.location)==(10.,2.,1.)
    assert tuple(second.location)==(-10.,2.,1.)
    first_mesh={o.data.as_pointer() for o in first.children if o.type=='MESH'}
    second_mesh={o.data.as_pointer() for o in second.children if o.type=='MESH'}
    assert len(first_mesh)==2 and first_mesh==second_mesh
    report['blender_append_placements']='passed; same-variant instances share mesh/material data'
(ROOT.parent/'asset-docs'/'QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))

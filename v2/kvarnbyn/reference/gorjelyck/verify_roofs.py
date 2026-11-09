"""Independent delivered GLB check: every upward visible roof triangle is solid."""
import importlib.util, json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('layout',ROOT/'reference/vag-hus/verify_layout.py')
layout=importlib.util.module_from_spec(spec);spec.loader.exec_module(layout)
data=layout.exported_roads(ROOT/'godot/assets/world.glb',extra_names=('roof',),include_roads=False,exclude_prefixes=('Far',))
def top(triangles):
    normal=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    lengths=np.linalg.norm(normal,axis=1)
    return triangles[(lengths>1e-8)&(normal[:,1]>.02*lengths)]
visible=layout.canonical(top(data['visible']));collision=layout.canonical(top(data['collision']))
def rows(array):return set(map(tuple,array))
missing=rows(visible)-rows(collision)
# Existing explicit colliders may tessellate the same coplanar quad along the
# opposite diagonal. Check actual plane coverage for unmatched triangles.
import shapely
from shapely.strtree import STRtree
collider_triangles=top(data['collision'])
polygons=shapely.polygons(collider_triangles[:,:,[0,2]])
tree=STRtree(polygons)
uncovered=[]
for row in missing:
    tri=np.array(row).reshape(3,3)/1000
    polygon=shapely.Polygon(tri[:,[0,2]])
    ids=tree.query(polygon.buffer(.002),predicate='intersects')
    valid=[]
    for i in ids:
        ct=collider_triangles[i];n=np.cross(ct[1]-ct[0],ct[2]-ct[0]);n=n/np.linalg.norm(n)
        if max(abs((tri-ct[0])@n))<.003:valid.append(polygons[i].buffer(.002))
    cover=shapely.union_all(valid) if valid else shapely.Polygon()
    if polygon.difference(cover).area>1e-5:uncovered.append(row)
missing=uncovered
report={'passed':not missing,'visible_upward_roof_triangles':len(visible),'collision_upward_roof_triangles':len(collision),'missing_collision_triangles':len(missing),'scope':'all delivered visible upward roof faces; no builder functions used'}
(ROOT/'evidence/gorjelyck/roof-mesh-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report));raise SystemExit(0 if report['passed'] else 1)

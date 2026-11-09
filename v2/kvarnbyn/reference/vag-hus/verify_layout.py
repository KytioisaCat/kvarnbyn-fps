"""Independent QA of source footprints, final site and delivered GLB roads.
No road-layout builder functions are used: inspect the actual output geometry.
"""
import argparse, json, struct, hashlib, re
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString
from shapely.strtree import STRtree

ROOT=Path(__file__).resolve().parents[2]

def transform(node):
    if 'matrix' in node:return np.array(node['matrix']).reshape(4,4,order='F')
    x,y,z,w=node.get('rotation',[0,0,0,1])
    rot=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                  [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                  [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
    m=np.eye(4);m[:3,:3]=rot@np.diag(node.get('scale',[1,1,1]));m[:3,3]=node.get('translation',[0,0,0]);return m


def exported_roads(path, extra_names=(), include_roads=True, exclude_prefixes=()):
    data=path.read_bytes();size=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+size]);start=28+size
    def acc(index):
        a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']]
        dtype=np.dtype({5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']]);n={'SCALAR':1,'VEC3':3}[a['type']]
        return np.ndarray((a['count'],n),dtype=dtype,buffer=data,offset=start+v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',dtype.itemsize*n),dtype.itemsize))
    result={'visible':[],'collision':[]}
    def visit(index,parent):
        node=doc['nodes'][index];m=parent@transform(node);name=node.get('name','')
        if 'mesh' in node and not name.startswith(exclude_prefixes) and ((include_roads and re.match(r'^(?:COL_)?(?:asphalt|paving|walkway|trail|street_setts|street_edges|street_gravel_edges)-?\d+_-?\d+__',name,re.I)) or any(prefix.lower() in name.lower() for prefix in extra_names)):
            for primitive in doc['meshes'][node['mesh']]['primitives']:
                vertices=acc(primitive['attributes']['POSITION']).astype(float)
                vertices=(np.c_[vertices,np.ones(len(vertices))]@m.T)[:,:3]
                ids=acc(primitive['indices']).ravel()if'indices'in primitive else np.arange(len(vertices))
                result['collision'if name.startswith('COL_')else'visible'].append(vertices[ids].reshape(-1,3,3))
        for child in node.get('children',[]):visit(child,m)
    for index in doc['scenes'][doc.get('scene',0)]['nodes']:visit(index,np.eye(4))
    return {k:np.concatenate(v)for k,v in result.items()}


def intrusions(triangles,buildings):
    projected=shapely.polygons(triangles[:,:,[0,2]])
    tree=STRtree(projected);found=[]
    for b in buildings:
        footprint=Polygon(b.get('build_footprint_xz',b['footprint_xz'])).buffer(-.035)
        ids=tree.query(footprint,predicate='intersects')
        if not len(ids):continue
        area=float(shapely.area(shapely.intersection(projected[ids],footprint)).sum())
        if area>.03:found.append({'id':b['id'],'area_m2':round(area,4)})
    return found


def canonical(triangles):
    points=np.round(triangles*1000).astype(np.int64)
    points=np.array([p[np.lexsort(p.T[::-1])]for p in points]).reshape(-1,9)
    return points[np.lexsort(points.T[::-1])]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--glb',type=Path)
    parser.add_argument('--out',type=Path,default=ROOT/'evidence/road-layout-check.json')
    args=parser.parse_args()
    city=json.loads((ROOT/'data/city.json').read_text());site=json.loads((ROOT/'data/site.json').read_text())
    houses=city['buildings'];roads=city['roads'];checks={};detail={}
    tris=np.array([t for kind,tiles in site['meshes'].items()if kind in('asphalt','paving','walkway','trail','street_setts','street_edges','street_gravel_edges')for ts in tiles.values()for t in ts])
    bad=intrusions(tris,houses);checks['built_street_surfaces_outside_all_house_walls']=not bad;detail['site_intrusions']=bad
    corrected=[b for b in houses if b.get('footprint_road_correction_m2')]
    known={b['building'] for b in json.loads((ROOT/'evidence/road-mesh-overlaps-before.json').read_text())}
    checks['road_blocking_house_expansions_removed']=known.issubset({b['id'] for b in corrected}) and all(Polygon(b['build_footprint_xz']).symmetric_difference(Polygon(b['footprint_xz'])).area<1e-6 for b in corrected)
    detail['corrected_house_ids']=[b['id']for b in corrected]
    nodes={};disconnected=[]
    for r in roads:
        for node,p in zip(r['node_ids'],r['line_xz']):
            if node is None:continue
            if node in nodes and nodes[node]!=p:disconnected.append(node)
            nodes[node]=p
    checks['shared_road_junctions_still_connected']=not disconnected
    detail['shared_node_mismatches']=disconnected
    checks['reviewed_street_profiles_applied']=sum(bool(r.get('width_profile_m'))for r in roads)>=3
    kinds={}
    for key in ('roten_mesh_kinds','stalliden_mesh_kinds','stalliden_garden_mesh_kinds','m25_mesh_kinds','north_bank_mesh_kinds'): kinds.update(site.get(key,{}))
    walk_keys=[key for key,kind in kinds.items() if kind in ('asphalt','paving','walkway','trail','gravel','stone')]
    extra=np.array([t for key in walk_keys for ts in site['meshes'][key].values() for t in ts])
    extra_bad=intrusions(extra,houses)
    checks['authored_walkways_outside_house_interiors']=not extra_bad
    detail['authored_walkway_intrusions']=extra_bad
    tree=STRtree([Polygon(b.get('build_footprint_xz',b['footprint_xz'])).buffer(-.12)for b in houses])
    nav=json.loads((ROOT/'godot/assets/nav.json').read_text());blocked=[]
    for a,b in nav['edges']:
        line=LineString([(nav['nodes'][i][0],nav['nodes'][i][2])for i in(a,b)])
        for k in tree.query(line,predicate='intersects'):
            if line.intersection(tree.geometries[k]).length>.2:blocked.append([a,b,houses[k]['id']])
    checks['navigation_edges_do_not_cross_house_interiors']=not blocked;detail['blocked_nav_edges']=blocked
    if args.glb:
        result=exported_roads(args.glb)
        for kind,triangles in result.items():
            found=intrusions(triangles,houses);checks['exported_'+kind+'_roads_outside_house_walls']=not found;detail[kind+'_intrusions']=found
        checks['exported_roads_match_current_site_geometry']=np.array_equal(canonical(tris),canonical(result['visible']))
        checks['exported_visible_and_collision_roads_match']=np.array_equal(canonical(result['visible']),canonical(result['collision']))
        detail['exported_road_triangles']={k:len(v)for k,v in result.items()}
        all_walks=exported_roads(args.glb,tuple(walk_keys)+('Bridge_deck','Stairs','Gotafors_platform','Gotafors_step','Gotafors_approach'))
        extra_bad=intrusions(all_walks['visible'],houses)
        checks['exported_walkways_stairs_and_bridge_decks_outside_houses']=not extra_bad
        collision_bad=intrusions(all_walks['collision'],houses)
        checks['exported_walk_collisions_outside_houses']=not collision_bad
        detail['all_walk_collision_intrusions']=collision_bad
        detail['all_walk_floor_intrusions']=extra_bad
        detail['glb_sha256']=hashlib.sha256(args.glb.read_bytes()).hexdigest()
    report=dict(passed=all(checks.values()),checks=checks,detail=detail,buildings_checked=len(houses),roads_checked=len(roads),site_triangles_checked=len(tris))
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False));raise SystemExit(0 if report['passed']else 1)
if __name__=='__main__':main()

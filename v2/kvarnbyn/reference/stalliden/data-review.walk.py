"""CPU-only baseline review. Writes only sibling data-review.walk.json.

No engine, scene rebuild, rendering, network or source-data mutation is used.
GLB triangles are read after scene-node transforms, in glTF/Godot XYZ.
"""
from pathlib import Path
import hashlib, json, math, struct, sys
import numpy as np
from shapely.geometry import LineString, Point, Polygon

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'v2/kvarnbyn/pipeline'))
from common import raw_height, lonlat

# This is a frozen baseline, not an evergreen QA command. Refuse to relabel new
# production inputs as ca119f9 after another agent starts building Stalliden.
baseline_file = OUT/'data-review.json'
baseline_hashes = json.loads(baseline_file.read_text())['meta']['source_hashes'] if baseline_file.exists() else {}
for relative, digest in baseline_hashes.items():
    actual=hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()
    if actual != digest:
        raise SystemExit('Frozen baseline input changed: '+relative+'; preserve existing data-review.walk.json.')

city = json.loads((ROOT/'v2/kvarnbyn/data/city.json').read_text())
site = json.loads((ROOT/'v2/kvarnbyn/data/site.json').read_text())
osm = json.loads((ROOT/'tools/osm_raw.json').read_text())
ways = {e['id']: e for e in osm['elements'] if e['type']=='way'}
roads = {r['id']:r for r in city['roads']}
stairs = {r['id']:r for r in site['stairs']}
ROUTE = ['w461711525','w461711523','w461711524']
ordered = [p for wid in ROUTE for p in roads[wid]['line_xz'][::-1]][:]
ordered = [p for i,p in enumerate(ordered) if i==0 or p!=ordered[i-1]]
route = LineString(ordered)
connector_xz = roads['w1227769459']['line_xz'][:5][::-1] + roads['w1227769458']['line_xz'][1:]
connector = LineString(connector_xz)
area = route.union(connector).buffer(3.0)
MIN, MAX = np.array(area.bounds[:2]), np.array(area.bounds[2:])

def rnd(v):
    if isinstance(v,np.ndarray): return np.round(v,5).tolist()
    return round(float(v),5)

def transform(node):
    if 'matrix' in node:return np.array(node['matrix']).reshape(4,4,order='F')
    x,y,z,w=node.get('rotation',[0,0,0,1])
    r=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
    m=np.eye(4);m[:3,:3]=r@np.diag(node.get('scale',[1,1,1]));m[:3,3]=node.get('translation',[0,0,0]);return m

def load_glb(path):
    data=path.read_bytes();size,tag=struct.unpack_from('<II',data,12)
    doc=json.loads(data[20:20+size]);binstart=28+size
    def acc(idx):
        a=doc['accessors'][idx];v=doc['bufferViews'][a['bufferView']]
        typ={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1',5122:'<i2',5120:'i1'}[a['componentType']]
        count={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
        dt=np.dtype(typ);offset=binstart+v.get('byteOffset',0)+a.get('byteOffset',0)
        return np.ndarray((a['count'],count),dtype=dt,buffer=data,offset=offset,
                          strides=(v.get('byteStride',dt.itemsize*count),dt.itemsize))
    result=[]
    def visit(ni,parent):
        node=doc['nodes'][ni];m=parent@transform(node);name=node.get('name','')
        if 'mesh' in node and (name.startswith('COL_') or name.startswith(('Terrain','Stairs','Stair_rail','Asphalt','Paving','Walkway','Trail'))):
            for prim in doc['meshes'][node['mesh']]['primitives']:
                a=doc['accessors'][prim['attributes']['POSITION']]
                lo,hi=np.array(a['min']),np.array(a['max'])
                corners=np.array([[x,y,z,1] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])])@m.T
                if not (np.any(corners[:,[0,2]].max(0)<MIN) or np.any(corners[:,[0,2]].min(0)>MAX)):
                    vv=acc(prim['attributes']['POSITION']).astype(float)
                    vv=np.c_[vv,np.ones(len(vv))]@m.T
                    ids=acc(prim['indices']).reshape(-1) if 'indices' in prim else np.arange(len(vv))
                    tt=vv[ids,:3].reshape(-1,3,3)
                    keep=np.all(tt[:,:,[0,2]].max(1)>=MIN,axis=1)&np.all(tt[:,:,[0,2]].min(1)<=MAX,axis=1)
                    tt=tt[keep]
                    if len(tt):result.append((name,tt))
        for ch in node.get('children',[]):visit(ch,m)
    for ni in doc['scenes'][doc.get('scene',0)]['nodes']:visit(ni,np.eye(4))
    digest=hashlib.sha256()
    for name,tt in result:digest.update(name.encode());digest.update(tt.astype('<f8').tobytes())
    return result,dict(path=str(path.relative_to(ROOT)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                       corridor_geometry_sha256=digest.hexdigest(),node_primitives=len(result),triangles=sum(len(t) for _,t in result))

class Probe:
    def __init__(self, meshes):
        self.t=np.concatenate([t for _,t in meshes]);self.names=np.concatenate([[n]*len(t) for n,t in meshes])
        self.min=self.t[:,:,[0,2]].min(1);self.max=self.t[:,:,[0,2]].max(1)
        normal=np.cross(self.t[:,1]-self.t[:,0],self.t[:,2]-self.t[:,0])
        self.ny=np.abs(normal[:,1])/np.maximum(1e-30,np.linalg.norm(normal,axis=1))
    def hits(self,x,z):
        ids=np.where(np.all(self.min<=[x+1e-6,z+1e-6],1)&np.all(self.max>=[x-1e-6,z-1e-6],1)&(self.ny>1e-5))[0]
        if not len(ids):return []
        t=self.t[ids];a=t[:,0];b=t[:,1]-a;c=t[:,2]-a
        den=b[:,0]*c[:,2]-b[:,2]*c[:,0];u=((x-a[:,0])*c[:,2]-(z-a[:,2])*c[:,0])/den
        v=(b[:,0]*(z-a[:,2])-b[:,2]*(x-a[:,0]))/den;keep=(u>=-1e-5)&(v>=-1e-5)&(u+v<=1+1e-5)
        return [dict(name=str(self.names[i]),y=rnd(y),slope=rnd(math.sqrt(max(0,1-self.ny[i]**2))/self.ny[i]))
                for i,y in zip(ids[keep],(a[:,1]+u*b[:,1]+v*c[:,1])[keep])]

def expected(wid,d):
    r=roads[wid];l=LineString(r['line_xz']);source_d=l.length-d
    if wid in stairs:
        pp=np.array(stairs[wid]['points']);ss=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pp[:,[0,2]],axis=0),axis=1))]
        return float(np.interp(source_d,ss,pp[:,1]))+.02
    # Footway endpoints are anchored by independently generated neighbouring stairs.
    a=stairs['w461711525']['points'][0][1]+.02;b=stairs['w461711524']['points'][-1][1]+.02
    return a+(b-a)*d/l.length

def ground_hit(hits,ref,collision):
    eligible=[h for h in hits if (h['name'].startswith('COL_')==collision)
              and not h['name'].startswith(('COL_H','COL_Lamps','COL_Bounds','COL_River','COL_Bridge_rail','Stair_rail'))
              and abs(h['y']-ref)<2.0]
    return max(eligible,key=lambda h:h['y']) if eligible else None

def profile(probe,wid,spacing=.25,offset=0):
    l=LineString(roads[wid]['line_xz'][::-1]);result=[];prev=None
    for d in np.linspace(0,l.length,math.ceil(l.length/spacing)+1):
        p=l.interpolate(d);aa=l.interpolate(max(0,d-.05));bb=l.interpolate(min(l.length,d+.05))
        delta=np.array([bb.x-aa.x,bb.y-aa.y]);delta/=np.linalg.norm(delta);p=np.array([p.x,p.y])+np.array([-delta[1],delta[0]])*offset
        ref=expected(wid,d);hits=probe.hits(*p);col=ground_hit(hits,ref,True);vis=ground_hit(hits,ref,False)
        row=dict(d=rnd(d),x=rnd(p[0]),z=rnd(p[1]),expected_stair_or_anchor_y=rnd(ref),raw_dem_y=rnd(raw_height(*p)-18),
                 collision=col,visible=vis,collision_stair=[h for h in hits if h['name'].startswith('COL_Stairs')],
                 visible_stair=[h for h in hits if h['name'].startswith('Stairs')],
                 nearby_house_surfaces=[h for h in hits if h['name'].startswith('COL_H') and ref-.5<h['y']<ref+2.1])
        if col and vis:row['visible_minus_collision']=rnd(vis['y']-col['y'])
        if col and prev:row['collision_delta']=rnd(col['y']-prev)
        prev=col['y'] if col else None;result.append(row)
    return result

raw,rawmeta=load_glb(ROOT/'v2/kvarnbyn/blender/world_raw.glb')
opt,optmeta=load_glb(ROOT/'v2/kvarnbyn/godot/assets/world.glb')
probe=Probe(opt)
reviews=[]
for wid in ROUTE:
    lanes={str(off):profile(probe,wid,offset=off) for off in (0,-.65,.65)}
    centre=lanes['0'];stairs_only=[r for r in centre if r['collision_stair'] and r['visible_stair']]
    diffs=[abs(max(h['y'] for h in r['visible_stair'])-max(h['y'] for h in r['collision_stair'])) for r in stairs_only]
    floors=[r['collision']['y'] for r in centre if r['collision']]
    delta=[abs(r.get('collision_delta',0)) for r in centre]
    rr=roads[wid]
    low_grade_runs=[]
    if wid in stairs:
        pp=np.array(stairs[wid]['points'][::-1]);ss=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pp[:,[0,2]],axis=0),axis=1))]
        gg=np.abs(np.diff(pp[:,1])/np.diff(ss))
        for threshold in (.02,.05,.08):
            start=None
            for i,flag in enumerate(gg<=threshold):
                if flag and start is None:start=i
                if start is not None and (not flag or i==len(gg)-1):
                    end=i if not flag else i+1
                    low_grade_runs.append(dict(max_grade=threshold,length_m=rnd(ss[end]-ss[start]),d_start=rnd(ss[start]),d_end=rnd(ss[end]),
                                               start_xyz=rnd(pp[start]),end_xyz=rnd(pp[end])))
                    start=None
    reviews.append(dict(id=wid,name=rr['name'],kind=rr['kind'],source_osm=ways[rr['osm_way_id']]['tags'],
                        source_nodes=rr['node_ids'][::-1],line_xz=rr['line_xz'][::-1],length_m=rnd(LineString(rr['line_xz']).length),
                        current_width_m=rr['width_m'],width_evidence='class default; no OSM width tag',
                        floor_start_y=floors[0],floor_end_y=floors[-1],max_abs_collision_delta_at_025m=rnd(max(delta)),
                        max_abs_visible_step_minus_ramp=rnd(max(diffs)) if diffs and wid in stairs else None,
                        missing_collision_by_lane={k:sum(r['collision'] is None for r in v) for k,v in lanes.items()},
                        missing_stair_ramp_by_lane={k:sum(not r['collision_stair'] for r in v) for k,v in lanes.items()} if wid in stairs else None,
                        low_grade_runs_from_site=low_grade_runs,
                        lanes=lanes))

# Exact OSM corners and joins, sampled before/after each feature. Footway joins
# use each side's actual road direction, and do not pretend to be shared levels.
feature_points=[(f'w525 corner {i}',p) for i,p in enumerate(roads['w461711525']['line_xz'][1:-1],1)]
feature_points += [('Roten M / w525',(87.166,98.474)),('w525 / w523',(28.66,84.937)),
                   ('w523 / w524',(18.196,88.822)),('w524 / w1227769459',(10.751,94.845))]
features=[]
for label,point in feature_points:
    p=Point(point);distance=route.project(p);row=dict(label=label,xz=point,d_from_Roten=rnd(distance),samples=[])
    for off in (-1,-.5,-.25,0,.25,.5,1):
        q=route.interpolate(min(route.length,max(0,distance+off)));hits=probe.hits(q.x,q.y)
        candidates=[(w,LineString(roads[w]['line_xz']).distance(q)) for w in ROUTE];wid=min(candidates,key=lambda a:a[1])[0]
        ll=LineString(roads[wid]['line_xz'][::-1]);ref=expected(wid,ll.project(q));col=ground_hit(hits,ref,True)
        row['samples'].append(dict(d_offset=off,x=rnd(q.x),z=rnd(q.y),collision=col,
                                   ground_hits=[h for h in hits if h['name'].startswith(('COL_Terrain','COL_Stairs','COL_paving','COL_trail','COL_asphalt'))]))
    features.append(row)

# Sample real continuation, plus both sides of source joins. Road connections are
# exact shared-node OSM routes; floor heights remain generated-game evidence.
connector_profile=[]
for d in np.linspace(0,connector.length,math.ceil(connector.length/.25)+1):
    p=connector.interpolate(d);ref=float(raw_height(p.x,p.y)-18)+.1
    hits=probe.hits(p.x,p.y);col=ground_hit(hits,ref,True)
    connector_profile.append(dict(d=rnd(d),x=rnd(p.x),z=rnd(p.y),raw_dem_y=rnd(ref-.1),collision=col,
                                  visible=ground_hit(hits,ref,False)))

joins=[]
join_data=[('Roten M / w525',(87.166,98.474),'w330280688','w461711525'),
           ('w525 / w523',(28.66,84.937),'w461711525','w461711523'),
           ('w523 / w524',(18.196,88.822),'w461711523','w461711524'),
           ('w524 / parallel footpath',(10.751,94.845),'w461711524','w1227769459'),
           ('parallel footpath / connector',(47.725,146.030),'w1227769459','w1227769458'),
           ('connector / Norra Forsakersgatan',(47.148,151.117),'w1227769458','w63073062')]
for label,pt,from_id,to_id in join_data:
    ref=float(raw_height(*pt)-18)+.1;hits=probe.hits(*pt)
    points=[]
    for wid in (from_id,to_id):
        l=LineString(roads[wid]['line_xz']);d=l.project(Point(pt))
        # Multiple branches exist when the shared node is an interior path node.
        for sign in (-1,1):
            if not 0<=d+sign*.01<=l.length:continue
            branch=[]
            for delta in (.001,.01,.1,.25,.5,1):
                if not 0<=d+sign*delta<=l.length:continue
                p=l.interpolate(d+sign*delta);hh=probe.hits(p.x,p.y)
                cc=ground_hit(hh,ref,True)
                branch.append(dict(distance_from_join_m=sign*delta,x=rnd(p.x),z=rnd(p.y),collision=cc))
            points.append(dict(road_id=wid,direction_along_OSM=sign,points=branch))
    joins.append(dict(label=label,xz=pt,raw_dem_y=rnd(ref-.1),
                      exact_xy_ground_hits=[h for h in hits if h['name'].startswith(('COL_Stairs','COL_paving','COL_trail','COL_asphalt','COL_Terrain'))],
                      branches=points))

def wall_slice_distance(x,z,y):
    result=[]
    for name,tt in opt:
        if not name.startswith('COL_H'):continue
        mask=(tt[:,:,1].min(1)<=y)&(tt[:,:,1].max(1)>=y)&(tt[:,:,[0,2]].min(1)[:,0]<x+3)&(tt[:,:,[0,2]].max(1)[:,0]>x-3)
        for tri in tt[mask]:
            crosses=[]
            for a,b in zip(tri,np.roll(tri,-1,axis=0)):
                if (a[1]<=y<=b[1] or b[1]<=y<=a[1]) and abs(b[1]-a[1])>1e-8:
                    q=a+(b-a)*(y-a[1])/(b[1]-a[1]);crosses.append(q[[0,2]])
            if len(crosses)>=2 and np.linalg.norm(crosses[0]-crosses[1])>1e-8:
                ln=LineString(crosses[:2]);p=ln.interpolate(ln.project(Point(x,z)))
                result.append(dict(name=name,distance_m=rnd(ln.distance(Point(x,z))),wall_xz=[rnd(p.x),rnd(p.y)],height_y=rnd(y)))
    return min(result,key=lambda a:a['distance_m']) if result else None

pinches=[]
for wid,xx,zz in [('w92331938',46.7372,81.4151),('w92332157',54.2096,92.0937)]:
    d=LineString(roads['w461711525']['line_xz'][::-1]).project(Point(xx,zz));ref=expected('w461711525',d)
    floor=ground_hit(probe.hits(xx,zz),ref,True)
    slices=[wall_slice_distance(xx,zz,floor['y']+h) for h in (.3,.9,1.47)]
    slices=[s for s in slices if s];gap=min(s['distance_m'] for s in slices)
    pinches.append(dict(building_id=wid,address=next(b.get('address') for b in city['buildings'] if b['id']==wid),
                         centre_xz=[xx,zz],d_from_Roten=rnd(d),floor=floor,actual_COL_wall_slices=slices,
                         closest_wall_distance_m=gap,nominal_2m_band_encroachment_m=rnd(1-gap),
                         nominal_band_free_width_to_opposite_edge_m=rnd(1+gap),
                         capsule_radius_m=.29,centreline_horizontal_margin_m=rnd(gap-.29),
                         wall_side_lane_065m_horizontal_margin_m=rnd(gap-.65-.29),
                         caveat='Triangle horizontal wall slices, not a physics-engine capsule test. Opposite 1m band edge is assumed geometry, not a measured real rail.'))

dense_step_summary=[]
for wid in ('w461711525','w461711524'):
    l=LineString(roads[wid]['line_xz'][::-1]);last=None;increments=[];missing=0
    for d in np.linspace(0,l.length,math.ceil(l.length/.025)+1):
        p=l.interpolate(d);hh=[h for h in probe.hits(p.x,p.y) if h['name'].startswith('Stairs')]
        top=max((h['y'] for h in hh),default=None)
        if top is None:missing+=1
        if top is not None and last is not None and abs(top-last)>.001:increments.append(abs(top-last))
        last=top
    dense_step_summary.append(dict(road_id=wid,sampling_spacing_max_m=.025,missing_visible_step_top=missing,
                                   max_adjacent_visible_top_change_m=rnd(max(increments)),
                                   nonzero_top_change_count=len(increments)))

road_links=[]
for point in [(87.166,98.474),(28.66,84.937),(18.196,88.822),(10.751,94.845)]:
    close=[]
    for r in city['roads']:
        if LineString(r['line_xz']).distance(Point(point))<.01:
            close.append(dict(id=r['id'],name=r['name'],kind=r['kind'],line_xz=r['line_xz'],node_ids=r['node_ids']))
    road_links.append(dict(xz=point,connected_roads=close))

review=dict(meta=dict(date='2026-11-01',baseline_commit='ca119f9',coordinates='x east / z south; local y = m above sea level minus 18',
                     baseline_input_sha256=baseline_hashes,
                     evidence='Actual GLB triangle rays + generated city/site + raw DEM. No visual reality verification and no engine/capsule execution.',
                     route='From Roten M to lower parallel footpath; Norra Forsåkersgatan carriageway is a separate road.',
                     floor_note='Highest non-building ground hit within 2m of local stair/anchor reference; building roofs, lamps and rails excluded explicitly. This is a floor-ray review, not capsule clearance validation.',
                     step_note='Rendered step tops and smooth collision ramps are separate. Rails are rendered only and have no COL_ counterpart.',
                     sampling_spacing_max_m=.25,lane_offsets_m=[0,-.65,.65],glb=[rawmeta,optmeta],
                     geometry_identical_in_corridor=rawmeta['corridor_geometry_sha256']==optmeta['corridor_geometry_sha256']),
            route_length_m=rnd(route.length),road_links=road_links,roads=reviews,features=features,joins=joins,
            actual_export_wall_pinches=pinches,actual_export_visible_riser_summary=dense_step_summary,
            recommended_connected_route_to_Norra_Forsakersgatan=dict(road_ids=ROUTE+['w1227769459','w1227769458','w63073062'],
                 after_stair_line_xz=connector_xz,after_stair_length_m=rnd(connector.length),
                 full_length_to_carriageway_m=rnd(route.length+connector.length),
                 note='At bottom stair turn southeast along parallel path, then connector to the carriageway shared node. No direct OSM cross-connection at the bottom stair.',
                 actual_export_profile=connector_profile),
            player=dict(radius_m=.29,height_m=1.76,max_floor_angle_degrees=55,floor_snap_m=.5,step_height_m=.23,
                        source='godot/scripts/player.gd; actual capsule not executed'),
            inference_limits=['OSM does not encode exact stair flights or landings, widths, handrails, or step counts here.',
                              'DTM and smoothed site profile cannot establish real walls, yard levels, stair landing levels, or hidden risers.',
                              'Rays do not prove a capsule can pass a sharp corner or a join.'])
(OUT/'data-review.walk.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(meta=review['meta'],route_length_m=review['route_length_m'],roads=[{k:v for k,v in r.items() if k!='lanes'} for r in reviews]),ensure_ascii=False,indent=2))

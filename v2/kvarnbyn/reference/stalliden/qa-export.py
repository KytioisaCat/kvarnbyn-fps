"""Actual exported GLB floor QA, independent of the Godot capsule walk.
Run with the staged raw GLB and site; optional baseline verifies preserved floor kinds.
"""
from pathlib import Path
import argparse,hashlib,json,math,struct,sys
import numpy as np
import shapely
from shapely.geometry import Point,Polygon,LineString
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[4]
parser=argparse.ArgumentParser()
parser.add_argument('--glb',type=Path,required=True)
parser.add_argument('--site',type=Path,required=True)
parser.add_argument('--baseline',type=Path)
parser.add_argument('--site-baseline',type=Path)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
MIN,MAX=np.array([-8,66]),np.array([132,142])
def rnd(v):return np.round(v,6).tolist() if isinstance(v,np.ndarray) else round(float(v),6)
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
        if 'mesh' in node and name.startswith(('COL_Terrain','COL_asphalt','COL_paving','COL_walkway','COL_trail','COL_Stairs','COL_Stalleliden_ground_','Terrain','Stairs','Asphalt','Paving','Walkway','Trail','Stalleliden_ground_','Stalleliden_steps','Stalleliden_risers','Bridge_deck','COL_Bridge','Water')):
            for prim in doc['meshes'][node['mesh']]['primitives']:
                a=doc['accessors'][prim['attributes']['POSITION']]
                lo,hi=np.array(a['min']),np.array(a['max'])
                corners=np.array([[x,y,z,1] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])])@m.T
                preserve=name.startswith(('Asphalt','COL_asphalt','Water','Bridge_deck','COL_Bridge'))
                if preserve or not (np.any(corners[:,[0,2]].max(0)<MIN) or np.any(corners[:,[0,2]].min(0)>MAX)):
                    vv=acc(prim['attributes']['POSITION']).astype(float)
                    vv=np.c_[vv,np.ones(len(vv))]@m.T
                    ids=acc(prim['indices']).reshape(-1) if 'indices' in prim else np.arange(len(vv))
                    tt=vv[ids,:3].reshape(-1,3,3)
                    keep=np.all(tt[:,:,[0,2]].max(1)>=MIN,axis=1)&np.all(tt[:,:,[0,2]].min(1)<=MAX,axis=1)
                    tt=tt if preserve else tt[keep]
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


meshes,info=load_glb(args.glb.resolve());probe=Probe(meshes)
site=json.loads(args.site.read_text());meta=site['stalliden'];points=[]
for path in meta['ground_checks']['paths'][:1]:
    q=np.asarray(path['points'])
    for i,p in enumerate(q):
        a=q[max(0,i-1)];b=q[min(len(q)-1,i+1)];v=(b-a)[[0,2]];v/=max(np.linalg.norm(v),1e-9);n=np.array([-v[1],v[0]])
        for side in (-.2,0,.2):points.append([p[0]+side*n[0],p[1],p[2]+side*n[1]])
errors=[];max_gap=0;intentional_step_gap=0
for x,ref,z in points:
    hits=probe.hits(x,z)
    cols=[h for h in hits if h['name'].startswith('COL_') and not h['name'].startswith('COL_Bridge_rail') and abs(h['y']-ref)<.8]
    visible=[h for h in hits if not h['name'].startswith('COL_') and abs(h['y']-ref)<.8]
    if not cols or not visible:
        errors.append(dict(xz=[x,z],expected_y=ref,reason='missing collision or visible floor',hits=hits));continue
    c=min(cols,key=lambda h:abs(h['y']-ref));v=min(visible,key=lambda h:abs(h['y']-c['y']))
    delta=abs(c['y']-v['y']);max_gap=max(max_gap,delta)
    limit=.18 if v['name'].startswith(('Stalleliden_steps','Stalleliden_risers')) else .08
    if limit==.18:intentional_step_gap=max(intentional_step_gap,delta)
    if abs(c['y']-ref)>.18 or delta>limit:
        errors.append(dict(xz=[x,z],expected_y=ref,collision=c,visible=v,gap_m=delta))
plants=[]
nt=int(site['stalliden_garden']['trees']);ns=int(site['stalliden_garden']['shrubs'])
for kind,items in [('tree',site['authored_trees'][-nt:] if nt else []),('shrub',site['shrubs'][-ns:] if ns else [])]:
    for item in items:
        x,y,z=item[:3];hits=probe.hits(x,z)
        cols=[h for h in hits if h['name'].startswith('COL_') and not h['name'].startswith('COL_Bridge_rail') and abs(h['y']-y)<.8]
        h=min(cols,key=lambda h:abs(h['y']-y)) if cols else None
        error=abs(h['y']-y) if h else None
        plants.append(dict(kind=kind,position=[x,y,z],floor=h,error_m=error,passed=error is not None and error<.08))
report=dict(passed=not errors and len(plants)==nt+ns and bool(plants) and all(p['passed'] for p in plants),scope='actual raw GLB transformed triangles; centre and +/-20 cm along complete route',
            glb=info,samples=len(points),missing_or_mismatched=len(errors),max_render_collision_gap_m=max_gap,
            max_intentional_step_gap_m=intentional_step_gap,plant_checks=plants,errors=errors)
if args.baseline:
    before,binfo=load_glb(args.baseline.resolve())
    def signature(meshes,prefixes):
        h=hashlib.sha256();count=0
        for name,t in sorted(meshes,key=lambda v:v[0]):
            if name.startswith(prefixes):h.update(name.encode());h.update(t.astype('<f8').tobytes());count+=len(t)
        return dict(sha256=h.hexdigest(),triangles=count)
    report['baseline']=binfo
    report['preserved']={key:dict(before=signature(before,prefix),after=signature(meshes,prefix)) for key,prefix in {
        'asphalt':('Asphalt','COL_asphalt'),'water':('Water',),'bridges':('Bridge_deck','COL_Bridge')}.items()}
    report['passed']=report['passed'] and all(v['before']==v['after'] and v['before']['triangles']>0 for v in report['preserved'].values())
if args.site_baseline:
    old=json.loads(args.site_baseline.read_text())
    report['preserved_site_data']={k:site['meshes'][k]==old['meshes'][k] for k in ('asphalt','water')}
    report['preserved_site_data']['bridges']=site['bridges']==old['bridges']
    report['baseline_site_sha256']=hashlib.sha256(args.site_baseline.read_bytes()).hexdigest()
    report['passed']=report['passed'] and all(report['preserved_site_data'].values())
args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('errors','baseline','glb','plant_checks')},ensure_ascii=False))
raise SystemExit(0 if report['passed'] else 3)

"""Read-only M24/M25 geometry/entry study; output files stay beside this script.

No engine, GPU, scene rebuild or product mutation. Baseline floor samples are
actual transformed GLB triangles. Entry QA is analytic and needs root's native
capsule/export validation after integration.
"""
from pathlib import Path
import ast, hashlib, json, math, struct, sys, subprocess
from types import SimpleNamespace
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'v2/kvarnbyn/pipeline'))
from common import raw_height
from authored_ground import SurfaceReference
from m25_ground import M25Ground

INPUTS=[ROOT/'v2/kvarnbyn/data/city.json',ROOT/'v2/kvarnbyn/data/site.json',
        ROOT/'v2/kvarnbyn/blender/world_raw.glb',ROOT/'v2/kvarnbyn/pipeline/m25_ground.py']
spec_file=OUT/'m25.json'
if spec_file.exists():INPUTS.append(spec_file)
hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUTS}
frozen_file=OUT/'data-review-agent.json'
if frozen_file.exists():
    previous=json.loads(frozen_file.read_text()).get('input_sha256',{})
    for p in INPUTS[:3]:
        key=str(p.relative_to(ROOT))
        if previous.get(key)!=hashes[key]:
            raise SystemExit('Frozen baseline changed: '+key+'; keep this report and run final export/capsule QA instead')
city=json.loads(INPUTS[0].read_text());site=json.loads(INPUTS[1].read_text())
baseline_city_bytes=subprocess.check_output(['git','show','HEAD:v2/kvarnbyn/data/city.json'],cwd=ROOT)
baseline_city=json.loads(baseline_city_bytes)
baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
buildings={b['id']:b for b in baseline_city['buildings']}

# Reuse only pure transformed-triangle reader/probe definitions, not that QA's
# CLI or top-level execution. This does not run or modify any other test file.
source=ROOT/'v2/kvarnbyn/reference/stalliden/qa-export.py'
tree=ast.parse(source.read_text());defs=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ('rnd','transform','load_glb','Probe')]
space=dict(ROOT=ROOT,MIN=np.array([30,65]),MAX=np.array([90,110]),np=np,json=json,math=math,struct=struct,hashlib=hashlib)
exec(compile(ast.Module(body=defs,type_ignores=[]),str(source),'exec'),space)
meshes,glb=space['load_glb'](INPUTS[2]);probe=space['Probe'](meshes)

def r(v):return round(float(v),6)
def ab(b,p,origin=None):
    origin=np.asarray(origin if origin is not None else b['centroid_xz']);d=np.asarray(p)-origin;u=np.asarray(b['major_axis_xz']);v=np.array([u[1],-u[0]])
    return [r(np.dot(d,u)/np.dot(u,u)),r(np.dot(d,v)/np.dot(v,v))]
def contours(items):return unary_union([Polygon(q['outer'],q.get('holes',[])) for q in items])
def floor(p,ref):
    hits=[h for h in probe.hits(*p) if h['name'].startswith('COL_') and not h['name'].startswith('COL_Bridge_rail') and abs(h['y']+18-ref)<3]
    hit=min(hits,key=lambda q:abs(q['y']+18-ref)) if hits else None
    return dict(raw_m=r(hit['y']+18),collider=hit['name']) if hit else None

main=site['stalliden']['profiles']['w461711525'];mainline=LineString(main['line_xz']);q=np.asarray(main['points']);ss=np.array([mainline.project(Point(p[0],p[2])) for p in q])
def stair(p):
    s=mainline.project(Point(p));n=mainline.interpolate(s)
    raw=float(np.interp(s,ss,q[:,1]))+18
    return dict(xz=[r(n.x),r(n.y)],raw_m=r(raw),distance_m=r(Point(p).distance(mainline)),actual_col=floor([n.x,n.y],raw))

report=dict(scope='Read-only data/actual baseline GLB analysis, not a field survey or engine run',input_sha256=hashes,glb=glb,buildings=[],baseline_city=dict(commit=baseline_commit,sha256=hashlib.sha256(baseline_city_bytes).hexdigest(),note='Old generic house fields use committed HEAD city; entry QA uses working city/spec'))
for ident in ['w92331938','w92332157']:
    b=buildings[ident];original=Polygon(b['footprint_xz']);built=Polygon(b['build_footprint_xz']);origin=np.asarray(b['build_footprint_xz']).mean(0)
    edge=b['street_edge'];a=np.array(b['build_footprint_xz'][edge]);c=np.array(b['build_footprint_xz'][(edge+1)%len(b['build_footprint_xz'])]);v=c-a;L=np.linalg.norm(v);count=max(1,int(L/2.9));slot=count//2
    door=a+v*((slot+.5)/count);out=np.array([-v[1],v[0]])/L
    threshold=b['base_height_raw_m']+.45;standing=door+out*.45
    west_a=np.array(b['footprint_xz'][0]);west_b=np.array(b['footprint_xz'][-1]);west=[]
    for t in np.linspace(0,1,9):
        p=west_a+t*(west_b-west_a);dtm=float(raw_height(*p));outside=p+out*.35
        west.append(dict(t=r(t),xz=[r(x) for x in p],ab=ab(b,p),raw_dtm_m=r(dtm),outside_xz=[r(x) for x in outside],actual_floor=floor(outside,float(raw_height(*outside))),nearest_stair=stair(p)))
    item=dict(id=ident,address=b.get('address'),source=b['source'],base_raw_m=b['base_height_raw_m'],wall_m=b['wall_height_m'],roof_rise_m=b['roof_rise_m'],
        eave_raw_m=r(b['base_height_raw_m']+b['wall_height_m']),ridge_raw_m=r(b['base_height_raw_m']+b['wall_height_m']+b['roof_rise_m']),
        original_area_m2=r(original.area),built_area_m2=r(built.area),extra_area_m2=r(built.difference(original).area),
        city_frame=dict(origin_xz=b['centroid_xz'],axis_xz=b['major_axis_xz'],axis_length=r(np.linalg.norm(b['major_axis_xz'])),
                        convention='Exactly modelkit.Frame; a east along stored axis, +b north/left of east axis'),
        current_roof_frame_origin_xz=[r(x) for x in origin],
        original_vertices=[dict(xz=p,ab_city=ab(b,p),ab_current_roof=ab(b,p,origin),raw_dtm_m=r(raw_height(*p))) for p in b['footprint_xz']],
        current_generic_door=dict(edge=edge,xz=[r(x) for x in door],ab_city=ab(b,door),threshold_raw_m=r(threshold),
                                  standing_xz=[r(x) for x in standing],standing_floor=floor(standing,float(raw_height(*standing))),nearest_stair=stair(door),status='generic guess; root photo shows no west-gable door for M25'),
        current_stone_shell_height_m=r(threshold-(b['ground_min_raw_m']-.35)),west_facade=west)
    report['buildings'].append(item)

m25=buildings['w92332157'];base=Polygon(m25['footprint_xz']);neighbors=[]
for b in baseline_city['buildings']:
    if b['id']==m25['id']:continue
    poly=Polygon(b['footprint_xz']);distance=base.distance(poly)
    if distance<25:
        neighbors.append(dict(id=b['id'],address=b.get('address'),centroid_xz=b['centroid_xz'],ab_from_m25_city=ab(m25,b['centroid_xz']),
                              footprint_gap_m=r(distance),base_raw_m=b['base_height_raw_m'],ridge_assumed_raw_m=r(b['base_height_raw_m']+b['wall_height_m']+b['roof_rise_m']),
                              roof_color_sample=b['roof_color'],footprint_xz=b['footprint_xz']))
report['neighbors']=neighbors

# Freeze the existing stair interface from already-generated site data. The
# resulting analytic module does not construct a substitute staircase.
coverage=unary_union([contours(s['contours']) for s in site['stalliden']['surfaces']])
tiles={}
urban=[]
for kind in ('asphalt','paving','walkway','trail'):
    for tile,tt in site['meshes'][kind].items():
        tiles[kind+tile]=tt
        for t in tt:
            a=np.asarray(t)[:,[0,2]]
            if np.any(a.max(0)<[30,65]) or np.any(a.min(0)>[90,110]):continue
            p=Polygon(a)
            if p.area>1e-10:urban.append(p)
for key,tt in site['meshes'].items():
    if key.startswith('stalliden_') and not key.startswith('stalliden_garden_'):
        for tile,tri in tt.items():tiles[key+tile]=tri
reference=SurfaceReference(tiles,raw_height,18,0,(30,65,90,110))
def old_height(x,z,original):
    return np.where(shapely.covers(coverage.buffer(1e-7),shapely.points(x,z)),reference.height(np.asarray(x),np.asarray(z)),original)
frozen=SimpleNamespace(active=True,stairs=site['stalliden']['flights'],coverage=coverage,height=old_height)
houses=unary_union([Polygon(b['footprint_xz']) if b['id']==M25Ground.HOUSE else Polygon(b['footprint_xz']).union(Polygon(b.get('build_footprint_xz',b['footprint_xz']))) for b in city['buildings']])
water=unary_union([Polygon(p['polygon_xz']) for p in city['water_polygons']])
forbidden=houses.buffer(.05).union(water).union(unary_union(urban))
specfile=OUT/'m25.json'
spec=json.loads(specfile.read_text()) if specfile.exists() else {}
entryspec=dict(floor_raw_m=spec.get('override',{}).get('base_height_raw_m',33.10))
if 'door' in spec:entryspec['door_ab']=[spec['door']['a'],spec['door']['b']]
entry=M25Ground(city,frozen,forbidden,box(30,65,90,110),raw_height,18,entryspec)
checks=[]
def check(name,passed,**detail):checks.append(dict(test=name,passed=bool(passed),**detail))
check('active',entry.active,area_m2=r(entry.coverage.area),surfaces=len(entry.surfaces))
check('no_existing_stair_coverage_overlap',entry.coverage.intersection(coverage).area<1e-8,overlap_m2=r(entry.coverage.intersection(coverage).area))
check('no_forbidden_overlap',entry.coverage.intersection(forbidden).area<1e-8)
for i,a in enumerate(entry.surfaces):
    for b in entry.surfaces[i+1:]:check('disjoint_'+a['id']+'_'+b['id'],a['geom'].intersection(b['geom']).area<1e-8)
line=LineString(entry.path_xz);q=shapely.get_coordinates(line.segmentize(.025));ds=np.array([line.project(Point(p)) for p in q]);h=entry._finished(q[:,0],q[:,1]);
offset_fail=[];clearance=[]
for i,p in enumerate(q):
    a=q[max(0,i-1)];b=q[min(len(q)-1,i+1)];v=b-a;v/=max(np.linalg.norm(v),1e-9);n=np.array([-v[1],v[0]])
    clearance.append(Point(p).distance(forbidden))
    for sign in (-1,0,1):
        t=p+n*sign*.2
        if not entry.coverage.union(coverage).buffer(1e-6).covers(Point(t)):offset_fail.append(t.tolist())
check('complete_path_plusminus_20cm',not offset_fail,failed=offset_fail[:10],samples=len(q)*3)
check('capsule_centres_clear_static_houses',min(clearance)>.29,minimum_clearance_m=r(min(clearance)))
check('walkable_height_profile',np.max(np.abs(np.diff(h))/np.maximum(np.diff(ds),1e-8))<.65,max_slope=r(np.max(np.abs(np.diff(h))/np.maximum(np.diff(ds),1e-8))))
seams=[]
for i,a in enumerate(entry.surfaces):
    for b in entry.surfaces[i+1:]:
        seam=a['geom'].boundary.intersection(b['geom'].boundary)
        coords=shapely.get_coordinates(seam.segmentize(.1))
        if not len(coords):continue
        delta=np.abs(a['height_fn'](coords[:,0],coords[:,1])-b['height_fn'](coords[:,0],coords[:,1]))
        seams.append(dict(a=a['id'],b=b['id'],max_m=r(max(delta))))
check('internal_height_seams',all(s['max_m']<.025 for s in seams),seams=seams)
seam=entry.coverage.boundary.intersection(coverage.boundary);coords=shapely.get_coordinates(seam.segmentize(.025))
if len(coords):
    new=entry.height(coords[:,0],coords[:,1],raw_height(coords[:,0],coords[:,1]))
    # Site triangles are rounded to millimetres while analytic contours are not.
    # Sample 5 mm inside the existing stair face, avoiding raw-DTM fallback on
    # a mathematical edge just outside the rounded exported polygon.
    toward=entry.anchor-coords;toward/=np.linalg.norm(toward,axis=1)[:,None]
    inside=coords+toward*.005
    old=reference.height(inside[:,0],inside[:,1]);delta=np.abs(new-old)
    check('exact_old_landing_join',float(max(delta))<.01,samples=len(coords),max_m=r(max(delta)),bad=[dict(xz=p.tolist(),new=r(a),old=r(b)) for p,a,b in zip(coords,new,old) if abs(a-b)>.01])
else:check('exact_old_landing_join',False,reason='No shared boundary')
wall_tests=[]
for edge,(a,b) in enumerate(zip(m25['footprint_xz'],m25['footprint_xz'][1:]+m25['footprint_xz'][:1])):
    a=np.array(a);b=np.array(b);v=b-a;n=np.array([v[1],-v[0]])/np.linalg.norm(v)
    for t in np.linspace(0,1,21):
        p=a+(b-a)*t+n*.1
        if float(raw_height(*p))<=33.1 or entry.footprint.buffer(.055).covers(Point(p)):continue
        new=float(entry.height([p[0]],[p[1]],raw_height([p[0]],[p[1]]))[0])
        wall_tests.append(dict(edge=edge,xz=p.tolist(),raw_old_m=r(raw_height(*p)),raw_new_m=r(new)))
check('high_ground_clear_of_painted_wall',all(t['raw_new_m']<=33.11 for t in wall_tests),samples=len(wall_tests),max_new_raw_m=max((t['raw_new_m'] for t in wall_tests),default=0))
report['entry']=dict(passed=all(c['passed'] for c in checks),checks=checks,metadata=entry.metadata(),wall_tests=wall_tests,
                     scope='Analytic CPU only; root must test actual final Blender/GLB and player capsule')
for p in INPUTS:
    if hashlib.sha256(p.read_bytes()).hexdigest()!=hashes[str(p.relative_to(ROOT))]:raise SystemExit('Input changed during audit; rerun')
(OUT/'data-review-agent.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(passed=report['entry']['passed'],checks=checks),ensure_ascii=False,indent=2))
raise SystemExit(0 if report['entry']['passed'] else 3)

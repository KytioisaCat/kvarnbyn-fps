"""Independent CPU QA for the proposed Stalliden garden.

Writes only sibling qa-garden.json. Uses no rendering/engine/network, and does
not import or run site.py. Input hashes are captured before garden import.
"""
from pathlib import Path
import hashlib,importlib,json,math,sys
sys.dont_write_bytecode=True
import numpy as np
import shapely
from shapely.geometry import Point,Polygon,LineString,box
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'v2/kvarnbyn/pipeline'))
from common import raw_height
from authored_ground import SurfaceReference
from stalliden import StallidenGround

def r(v):return round(float(v),7)
def xylist(p):return [r(v) for v in p]
def parts(geom,kind):
    if geom.is_empty:return []
    if geom.geom_type==kind:return [geom]
    return [p for g in getattr(geom,'geoms',[]) for p in parts(g,kind)]

def context():
    files=[ROOT/'v2/kvarnbyn/data/city.json',ROOT/'v2/kvarnbyn/data/site.json',
           ROOT/'v2/kvarnbyn/pipeline/stalliden.py',ROOT/'v2/kvarnbyn/pipeline/stalliden_garden.py']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    city=json.loads(files[0].read_text());site=json.loads(files[1].read_text())
    work=box(-6,69,126,156);tiles={};poly=[]
    for kind in ('asphalt','paving','walkway','trail'):
        for tile,triangles in site['meshes'][kind].items():
            tiles[kind+tile]=triangles
            for tri in triangles:
                a=np.asarray(tri)
                if np.any(a[:,[0,2]].max(0)<[-8,67]) or np.any(a[:,[0,2]].min(0)>[128,158]):continue
                p=Polygon(a[:,[0,2]])
                if p.area>1e-9:poly.append(p)
    urban=unary_union(poly)
    houses=unary_union([Polygon(b['footprint_xz']).union(Polygon(b.get('build_footprint_xz',b['footprint_xz']))) for b in city['buildings']])
    water=unary_union([Polygon(p['polygon_xz']) for p in city['water_polygons']])
    bridge=unary_union([LineString(q['line_xz']).buffer(q['width_m']/2+.3,cap_style=2) for q in city['roads'] if q['bridge']])
    domain=StallidenGround.original_domain(city)
    forbidden=houses.buffer(.05).union(water).union(bridge).union(urban.difference(domain))
    reference=SurfaceReference(tiles,lambda x,z:raw_height(x,z)+.05,18,0,(-8,67,128,158))
    stalliden=StallidenGround(city,forbidden,work,raw_height,reference.height,18)
    # Garden may occupy natural verges but no old road, new path, house or water.
    garden_forbidden=houses.buffer(.05).union(water).union(bridge).union(urban).union(stalliden.coverage)
    return dict(city=city,site=site,work=work,urban=urban,houses=houses,water=water,bridge=bridge,
                reference=reference,stalliden=stalliden,garden_forbidden=garden_forbidden,hashes=hashes)

def surface_at(garden,x,z):
    points=shapely.points(x,z);height=np.asarray(raw_height(x,z),float).copy().ravel();used=np.zeros(len(height),bool)
    for s in garden.surfaces:
        hit=(~used)&shapely.covers(s['geom'].buffer(1e-7),points)
        if hit.any():height[hit]=np.asarray(s['height_fn'](np.asarray(x)[hit],np.asarray(z)[hit])).ravel();used[hit]=True
    return height

def serializable_signature(garden):
    """Stable comparison of geometry, sampled heights, structures and planting."""
    surface=[]
    for s in garden.surfaces:
        coords=shapely.get_coordinates(s['geom'].segmentize(.35));h=s['height_fn'](coords[:,0],coords[:,1])
        surface.append(dict(id=s['id'],kind=s['kind'],wkb=s['geom'].wkb_hex,heights=np.asarray(h).ravel().tolist()))
    planting=garden.planting(lambda x,z:surface_at(garden,x,z),18)
    return json.dumps(dict(surfaces=surface,walls=garden.walls,fences=garden.fences,planting=planting,metadata=garden.metadata()),sort_keys=True,default=lambda a:a.tolist() if isinstance(a,np.ndarray) else str(a))

def run():
    c=context()
    module=importlib.import_module('stalliden_garden')
    cls=getattr(module,'StallidenGarden',None) or getattr(module,'Garden',None)
    if cls is None:raise SystemExit('Garden class is not published yet.')
    garden=cls(c['city'],c['stalliden'],c['garden_forbidden'],raw_height,18)
    checks=[]
    def check(name,ok,**details):checks.append(dict(name=name,passed=bool(ok),**details))
    check('active_garden_has_surfaces',not garden.coverage.is_empty and bool(garden.surfaces),
          coverage_m2=r(garden.coverage.area),surfaces=len(garden.surfaces))
    check('garden_does_not_overlap_forbidden',garden.coverage.intersection(c['garden_forbidden']).area<1e-8,
          overlap_m2=r(garden.coverage.intersection(c['garden_forbidden']).area))
    check('finished_raw_ground_surface_kinds',all(s['kind'] in ('grass','soil') and s.get('lift_m',0)==0 for s in garden.surfaces))
    trees,shrubs=garden.planting(lambda x,z:surface_at(garden,x,z),18)
    check('requested_plant_counts',4<=len(trees)<=6 and 30<=len(shrubs)<=60,trees=len(trees),shrubs=len(shrubs))
    main=c['stalliden'].lines[c['stalliden'].MAIN]
    corridor=main.buffer(1.1)
    plant_diagnostics=[]
    for kind,items in [('tree',trees),('shrub',shrubs)]:
        for i,item in enumerate(items):
            p=Point(item[0],item[2]);source_y=float(surface_at(garden,[p.x],[p.y])[0])-18
            inside=[b['id'] for b in c['city']['buildings'] if Polygon(b['footprint_xz']).union(Polygon(b.get('build_footprint_xz',b['footprint_xz']))).covers(p)]
            plant_diagnostics.append(dict(kind=kind,index=i,position=item,route_distance_m=r(p.distance(main)),
                                          house_distance_m=r(p.distance(c['houses'])),inside_houses=inside,
                                          base_error_m=r(abs(item[1]-source_y)),inside_garden=garden.coverage.buffer(1e-7).covers(p)))
    check('plant_centres_clear_main_plusminus_11m',all(p['route_distance_m']>=1.1-1e-6 for p in plant_diagnostics),
          minimum_m=min((p['route_distance_m'] for p in plant_diagnostics),default=0))
    check('tree_centres_at_least_08m_from_houses',all(p['house_distance_m']>=.8-1e-6 for p in plant_diagnostics if p['kind']=='tree'))
    check('no_plants_inside_any_house',all(not p['inside_houses'] for p in plant_diagnostics))
    check('plants_rest_on_own_finished_ground',all(p['base_error_m']<=.05 for p in plant_diagnostics),
          max_error_m=max((p['base_error_m'] for p in plant_diagnostics),default=0))
    check('plants_inside_authored_green_ground',all(p['inside_garden'] for p in plant_diagnostics))
    other=cls(c['city'],c['stalliden'],c['garden_forbidden'],raw_height,18)
    first=serializable_signature(garden);second=serializable_signature(other)
    check('deterministic_geometry_heights_planting_metadata',first==second,sha256=hashlib.sha256(first.encode()).hexdigest())
    # Structural schemas and edge diagnostics are added after the author has
    # published the final wall/fence API. Never guess an unannounced schema.
    for relative,digest in c['hashes'].items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=digest:raise SystemExit('Input changed during QA: '+relative+'; rerun.')
    report=dict(meta=dict(scope='Independent CPU analytic geometry only; no exported triangles or capsule execution.',input_sha256=c['hashes']),
                passed=all(q['passed'] for q in checks),checks=checks,plants=plant_diagnostics,
                walls=garden.walls,fences=garden.fences,metadata=garden.metadata())
    (OUT/'qa-garden.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=lambda a:a.tolist() if isinstance(a,np.ndarray) else str(a))+'\n')
    print(json.dumps(dict(passed=report['passed'],checks=checks),ensure_ascii=False,indent=2))

if __name__=='__main__':run()

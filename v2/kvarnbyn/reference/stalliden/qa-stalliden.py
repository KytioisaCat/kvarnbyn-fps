"""Independent CPU QA of StallidenGround; only qa-stalliden.* is written.

This checks proposed analytic surfaces and metadata, not exported triangles or
Godot capsule movement. Baseline data-review.* files remain untouched.
"""
from pathlib import Path
import hashlib,json,math,sys
sys.dont_write_bytecode=True
import numpy as np
import shapely
from shapely.geometry import Point,Polygon,LineString,box
from shapely.ops import unary_union,nearest_points

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'v2/kvarnbyn/pipeline'))
model_path=ROOT/'v2/kvarnbyn/pipeline/stalliden.py'
model_hash_at_import=hashlib.sha256(model_path.read_bytes()).hexdigest()
from common import raw_height
from authored_ground import SurfaceReference
from stalliden import StallidenGround

def rounded(value):return round(float(value),7)
def pointlist(q):return [rounded(v) for v in q]
def parts(g,kind):
    if g.is_empty:return []
    if g.geom_type==kind:return [g]
    return [p for gg in getattr(g,'geoms',[]) for p in parts(gg,kind)]

city_path=ROOT/'v2/kvarnbyn/data/city.json';site_path=ROOT/'v2/kvarnbyn/data/site.json'
city=json.loads(city_path.read_text());site=json.loads(site_path.read_text())
work=box(-6,69,126,156)
tiles={};oldpolys=[]
for kind in ('asphalt','paving','walkway','trail'):
    for tile,triangles in site['meshes'][kind].items():
        tiles[kind+tile]=triangles
        for t in triangles:
            a=np.asarray(t)
            if np.any(a[:,[0,2]].max(0)<[-8,67]) or np.any(a[:,[0,2]].min(0)>[128,158]):continue
            p=Polygon(a[:,[0,2]])
            if p.area>1e-9:oldpolys.append(p)
urban=unary_union(oldpolys)
houses=unary_union([Polygon(b['footprint_xz']) for b in city['buildings']])
water=unary_union([Polygon(p['polygon_xz']) for p in city['water_polygons']])
bridges=unary_union([LineString(r['line_xz']).buffer(r['width_m']/2+.3,cap_style=2) for r in city['roads'] if r['bridge']])
domain=StallidenGround.original_domain(city)
unrelated=urban.difference(domain)
forbidden=houses.buffer(.05).union(water).union(bridges).union(unrelated)
reference=SurfaceReference(tiles,lambda x,z:raw_height(x,z)+.05,18,0,(-8,67,128,158))
g=StallidenGround(city,forbidden,work,raw_height,reference.height,18)
metadata=g.metadata()

checks=[];findings=[]
def check(name,passed,**details):checks.append(dict(name=name,passed=bool(passed),**details))
check('active_and_expected_geometry_count',g.active and len(g.surfaces)==21 and len(g.stairs)==16 and len(g.rails)==2,
      coverage_m2=g.coverage.area,surfaces=len(g.surfaces),flights=len(g.stairs),rail_chains=len(g.rails))
expected=[41.43306061908406,23.788434644396553,20.95528358341079,18.490215901785714]
check('four_finished_anchors',np.max(np.abs(np.array(g.anchor_heights)-expected))<1e-6,
      actual_raw_m=g.anchor_heights,expected_raw_m=expected)
check('no_forbidden_area_overlap',g.coverage.intersection(forbidden).area<1e-8,
      overlap_m2=g.coverage.intersection(forbidden).area,
      houses_overlap_m2=g.coverage.intersection(houses).area,unrelated_urban_overlap_m2=g.coverage.intersection(unrelated).area)

# Deliberately non-geographic fallback detects accidental modification outside
# coverage independently of raw-height coincidence or original road levels.
xx,zz=np.meshgrid(np.arange(-6,126.001,.25),np.arange(69,156.001,.25));x,z=xx.ravel(),zz.ravel()
outside=~shapely.covers(g.coverage,shapely.points(x,z));original=1000+x*.17-z*.11
changed=g.height(x,z,original)
check('outside_coverage_exactly_unchanged',np.array_equal(changed[outside],original[outside]),
      outside_samples=int(outside.sum()),max_change_m=rounded(np.max(np.abs(changed[outside]-original[outside]))))

# Shared analytic-surface boundaries should not create hidden risers. Explicit
# visible treads are measured separately; these surfaces are collision floors.
seams=[]
for i,a in enumerate(g.surfaces):
    for b in g.surfaces[i+1:]:
        seam=a['geom'].boundary.intersection(b['geom'].boundary)
        pts=[]
        for line in parts(seam,'LineString'):pts.extend(list(line.segmentize(.05).coords))
        pts.extend([(p.x,p.y) for p in parts(seam,'Point')])
        if not pts:continue
        q=np.array(pts);ha=np.asarray(a['height_fn'](q[:,0],q[:,1])).ravel();hb=np.asarray(b['height_fn'](q[:,0],q[:,1])).ravel()
        delta=np.abs(ha-hb);worst=int(np.argmax(delta))
        seams.append(dict(a=a['id'],b=b['id'],samples=len(q),max_delta_m=rounded(delta[worst]),worst_xz=pointlist(q[worst]),
                          raw_heights_m=[rounded(ha[worst]),rounded(hb[worst])],shared_boundary_length_m=rounded(seam.length)))
check('analytic_floor_seams_below_023m',all(s['max_delta_m']<=.23 for s in seams),
      seam_count=len(seams),max_delta_m=max((s['max_delta_m'] for s in seams),default=0))

routes=[]
for wid in (g.MAIN,g.WALK,g.LOWER):
    line=g.lines[wid]
    for offset in (-.49,-.2,0,.2,.49):
        ss=np.linspace(0,line.length,math.ceil(line.length/.025)+1)
        q=shapely.get_coordinates(shapely.line_interpolate_point(line,ss));a=shapely.get_coordinates(shapely.line_interpolate_point(line,np.maximum(0,ss-.01)))
        b=shapely.get_coordinates(shapely.line_interpolate_point(line,np.minimum(line.length,ss+.01)));delta=b-a;delta/=np.linalg.norm(delta,axis=1)[:,None]
        q+=np.c_[-delta[:,1],delta[:,0]]*offset
        fallback=reference.height(q[:,0],q[:,1]);h=g.height(q[:,0],q[:,1],fallback).ravel()
        covered=shapely.covers(g.coverage.buffer(1e-7),shapely.points(q))
        retained=shapely.covers(unrelated.buffer(1e-7),shapely.points(q))
        supported=covered|retained;diff=np.abs(np.diff(h));j=int(np.argmax(diff))
        routes.append(dict(road_id=wid,offset_m=offset,samples=len(q),uncovered=int((~supported).sum()),
                           not_in_new_coverage=int((~covered).sum()),retained_original_urban_used=int(((~covered)&retained).sum()),
                           floor_coverage_note='New surface OR actual retained original urban outside the replacement mask; original parallel path wins at the lower stair foot.',
                           max_adjacent_height_delta_m=rounded(diff[j]),worst_start_xz=pointlist(q[j]),worst_end_xz=pointlist(q[j+1]),
                           actual_adjacent_sample_distance_m=rounded(np.linalg.norm(q[j+1]-q[j])),
                           raw_heights_m=[rounded(h[j]),rounded(h[j+1])]))
check('main_walk_lower_centre_and_side_profiles',all(r['uncovered']==0 and r['max_adjacent_height_delta_m']<=.23 for r in routes),profiles=routes)
pinch_checks=[]
for ident,x0,z0 in [('w92331938',46.7372,81.4151),('w92332157',54.2096,92.0937)]:
    line=g.lines[g.MAIN];station=line.project(Point(x0,z0));p=line.interpolate(station);a=line.interpolate(station-.01);b=line.interpolate(station+.01)
    v=np.array([b.x-a.x,b.y-a.y]);v/=np.linalg.norm(v);n=np.array([-v[1],v[0]]);centre=np.array([p.x,p.y])
    cross=LineString([centre-n*1.2,centre+n*1.2]);free=g.coverage.intersection(cross)
    segment=next((seg for seg in parts(free,'LineString') if seg.distance(Point(centre))<1e-6),None)
    pinch_checks.append(dict(building_id=ident,centre_xz=pointlist(centre),surface_width_m=rounded(segment.length) if segment else 0,
                             full_capsule_body_band_halfwidth_m=.49,
                             clipped_surface_covers_body_band=g.coverage.covers(LineString([centre-n*.49,centre+n*.49]))))
check('M24_M25_clipped_band_covers_body_corridor',all(p['clipped_surface_covers_body_band'] for p in pinch_checks),pinches=pinch_checks)

full_paths=[]
for route in g._routes:
    line=LineString(route['xz']);q=shapely.get_coordinates(line.segmentize(.025));old=reference.height(q[:,0],q[:,1]);h=g.height(q[:,0],q[:,1],old).ravel()
    ds=np.abs(np.diff(h));worst=int(np.argmax(ds))
    absent_new_but_old_removed=shapely.covers(domain,shapely.points(q))&~shapely.covers(g.coverage.buffer(1e-7),shapely.points(q))
    full_paths.append(dict(id=route['id'],samples=len(q),max_floor_delta_m=rounded(ds[worst]),
                           worst_xz_start=pointlist(q[worst]),worst_xz_end=pointlist(q[worst+1]),
                           original_floor_removed_but_no_new_surface_points=int(absent_new_but_old_removed.sum()),
                           original_floor_removed_but_no_new_surface_xz=[pointlist(p) for p in q[absent_new_but_old_removed]],
                           note='Uses original finished-floor callback outside new coverage. Removed-band terrain integration must supply those points.'))
check('full_metadata_paths_connected_with_original_floor_callback',
      all(p['max_floor_delta_m']<=.23 and p['original_floor_removed_but_no_new_surface_points']==0 for p in full_paths),
      paths=full_paths,replacement_gap_requirement='No metadata-path point may lose its original floor through the replacement mask without receiving a new surface.')
check('visible_authored_risers_below_0165m',all(st['riser_m']<=.165+1e-8 and all(not t['collision'] for t in st['treads']) for st in g.stairs),
      max_riser_m=max(st['riser_m'] for st in g.stairs),treads=sum(len(st['treads']) for st in g.stairs))

railchecks=[]
for rail in g.rails:
    q=np.array(rail['points']);line=g.lines[rail['way_id']];ln=LineString(q[:,[0,2]])
    segments=[]
    for i,(a,b) in enumerate(zip(q,q[1:])):
        seg=LineString([a[[0,2]],b[[0,2]]]);distance=seg.distance(line)
        if distance<.525:
            p0,p1=nearest_points(seg,line)
            segments.append(dict(index=i,start_xyz=pointlist(a),end_xyz=pointlist(b),centreline_distance_m=rounded(distance),
                                 rail_point_xz=[rounded(p0.x),rounded(p0.y)],route_point_xz=[rounded(p1.x),rounded(p1.y)],
                                 required_clearance_m=.525))
    collision_area=ln.buffer(rail['collider_width_m']/2).intersection(line.buffer(.49)).area
    railchecks.append(dict(id=rail['id'],minimum_centreline_distance_m=rounded(ln.distance(line)),
                           body_corridor_overlap_m2=rounded(collision_area),segments_encroaching=segments))
check('rails_clear_body_corridor_plusminus_02m',all(r['body_corridor_overlap_m2']<1e-8 for r in railchecks),rails=railchecks)

blockers=[]
for block in metadata['ground_checks']['blockers']:
    ray=LineString([(block['from'][0],block['from'][2]),(block['to'][0],block['to'][2])]);hits=[]
    for rail in g.rails:
        ln=LineString([(p[0],p[2]) for p in rail['points']]);area=ln.buffer(rail['collider_width_m']/2)
        if ray.intersects(area):hits.append(rail['id'])
    blockers.append(dict(id=block['id'],expected_blocked=block['blocked'],intersected_rail_chains=hits,
                          matches_in_2d=bool(hits)==block['blocked'],note='2D rail metadata intersection only; exported rail posts and full 3D ray/capsule still require engine QA.'))
check('blocker_true_false_metadata_2d',all(b['matches_in_2d'] for b in blockers),blockers=blockers)

# Outer seam diagnostics distinguish retained urban, removed old road margin and
# natural ground. Differences against raw DTM are integration evidence only.
edge=[]
for poly in parts(g.coverage,'Polygon'):
    for ring in [poly.exterior]+list(poly.interiors):
        line=LineString(ring.coords)
        for station in np.arange(.02,line.length,.1):
            p=line.interpolate(station);a=line.interpolate(max(0,station-.005));b=line.interpolate(min(line.length,station+.005));v=np.array([b.x-a.x,b.y-a.y]);L=np.linalg.norm(v)
            if L<1e-9:continue
            normal=np.array([-v[1],v[0]])/L;p0=np.array([p.x,p.y]);q0,q1=p0-normal*.002,p0+normal*.002
            cov0=g.coverage.contains(Point(q0));cov1=g.coverage.contains(Point(q1))
            if cov0==cov1:continue
            inside,outside=(q0,q1) if cov0 else (q1,q0)
            h0=float(g.height([inside[0]],[inside[1]],reference.height([inside[0]],[inside[1]]))[0]);h1=float(reference.height([outside[0]],[outside[1]])[0])
            raw=float(raw_height([outside[0]],[outside[1]])[0])
            kind='preserved_urban' if unrelated.covers(Point(outside)) else ('removed_old_band' if domain.covers(Point(outside)) else 'natural_margin')
            surface_id=next((s['id'] for s in g.surfaces if s['geom'].covers(Point(inside))),None)
            edge.append(dict(kind=kind,surface_id=surface_id,xz=pointlist(p0),inside_raw_m=rounded(h0),old_finished_outside_raw_m=rounded(h1),
                              dem_outside_raw_m=rounded(raw),delta_to_old_finished_m=rounded(abs(h0-h1)),delta_to_raw_dem_m=rounded(abs(h0-raw))))
edge_summary={}
for kind in ('preserved_urban','removed_old_band','natural_margin'):
    rows=[r for r in edge if r['kind']==kind]
    edge_summary[kind]=dict(samples=len(rows),worst_to_old_finished=sorted(rows,key=lambda q:-q['delta_to_old_finished_m'])[:8],
                            worst_to_raw_dem=sorted(rows,key=lambda q:-q['delta_to_raw_dem_m'])[:8])
check('preserved_urban_boundary_tie_below_023m',all(e['delta_to_old_finished_m']<=.23 for e in edge if e['kind']=='preserved_urban'),
      max_delta_m=max((e['delta_to_old_finished_m'] for e in edge if e['kind']=='preserved_urban'),default=0),
      note='Across 4mm boundary normal. This tests unchanged original urban, including the direct connector clip edge.')
connector_edges=[e for e in edge if e['kind']=='preserved_urban' and e['surface_id']=='stalliden_norra_pedestrian_link']
check('connector_preserved_urban_edge_below_023m',all(e['delta_to_old_finished_m']<=.23 for e in connector_edges),
      samples=len(connector_edges),max_delta_m=max((e['delta_to_old_finished_m'] for e in connector_edges),default=0),
      worst=sorted(connector_edges,key=lambda q:-q['delta_to_old_finished_m'])[:3])

if hashlib.sha256(model_path.read_bytes()).hexdigest()!=model_hash_at_import:
    raise SystemExit('stalliden.py changed during QA; rerun to record a consistent review.')

result=dict(meta=dict(date='2026-11-01',qa_scope='Independent analytic CPU review only. No engine, GPU, network, or baseline mutation.',
                     hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (city_path,site_path,ROOT/'v2/kvarnbyn/pipeline/stalliden.py')},
                     forbidden_recipe='Original+model houses clipped internally; external original footprints buffer0.05, water polygons, bridge halfwidth+0.3; all old asphalt/paving/walkway/trail triangles outside original_domain.',
                     coordinates='Finished raw metres above sea level; local Y=raw-18.'),
            passed=all(c['passed'] for c in checks),checks=checks,analytic_surface_seams=sorted(seams,key=lambda q:-q['max_delta_m']),
            edge_summary=edge_summary,old_replacement_uncovered_area_m2=rounded(g.replacement_domain.difference(g.coverage).area),
            connector=dict(line_xz=[list(p) for p in g._connector.coords],anchors=g.connector_anchor,
                           new_surface_area_m2=rounded(sum(s['geom'].area for s in g.surfaces if s['id']=='stalliden_norra_pedestrian_link'))),
            metadata_source={k:metadata[k] for k in ('source','observed','estimated','height_units')},
            limitations=['Does not test triangulation of these analytic surfaces.',
                         'Does not test the root integration terrain cut/feather or removal of original urban/stairs.',
                         'Does not prove exported rail mesh/collision presence or actual player-capsule passage.'])
(OUT/'qa-stalliden.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(passed=result['passed'],checks=[{k:v for k,v in c.items() if k not in ('profiles','rails','blockers','worst')} for c in checks],
                     worst_seams=result['analytic_surface_seams'][:3],rail=railchecks,
                     edge_worst={k:v['worst_to_old_finished'][:2] for k,v in edge_summary.items()}),ensure_ascii=False,indent=2))

"""Read-only Roten M data review; writes only sibling data-review.* artifacts."""
from pathlib import Path
import json, math, sys
import numpy as np
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import nearest_points
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'v2/kvarnbyn/pipeline'))
from common import raw_height, local, lonlat

OUT = Path(__file__).resolve().parent
city = json.loads((ROOT / 'v2/kvarnbyn/data/city.json').read_text())
site = json.loads((ROOT / 'v2/kvarnbyn/data/site.json').read_text())
osm = json.loads((ROOT / 'tools/osm_raw.json').read_text())
nodes = {n['id']: n for n in osm['elements'] if n['type'] == 'node'}
ways = {w['id']: w for w in osm['elements'] if w['type'] == 'way'}
zone = box(75, 80, 125, 135)
IDS = ['w92332120', 'w92331973', 'w92332141']
buildings = [next(b for b in city['buildings'] if b['id'] == wid) for wid in IDS]
terrain = site['terrain']; H = np.asarray(terrain['heights']).reshape(terrain['nz'], terrain['nx'])
triangles = []
for kind in ('asphalt', 'paving', 'walkway', 'trail', 'soil'):
    for bucket in site['meshes'].get(kind, {}).values():
        for tri in bucket:
            a = np.asarray(tri)
            if max(a[:, 0]) < 70 or min(a[:, 0]) > 130 or max(a[:, 2]) < 75 or min(a[:, 2]) > 140: continue
            triangles.append((kind, a))


def sample(x, z):
    raw = float(raw_height([x], [z])[0])
    fx, fz = (x-terrain['x0'])/terrain['step'], (z-terrain['z0'])/terrain['step']
    i, k = int(fx), int(fz); u, v = fx-i, fz-k
    current = (H[k,i]*(1-u)+H[k,i+1]*u)*(1-v)+(H[k+1,i]*(1-u)+H[k+1,i+1]*u)*v + 18
    floor = []
    for kind, a in triangles:
        if not a[:,0].min()-1e-6 <= x <= a[:,0].max()+1e-6 or not a[:,2].min()-1e-6 <= z <= a[:,2].max()+1e-6: continue
        m = np.vstack([a[:,0], a[:,2], np.ones(3)])
        if abs(np.linalg.det(m)) < 1e-8: continue
        uv = np.linalg.solve(m, [x,z,1])
        if min(uv) >= -1e-7: floor.append(dict(kind=kind, height_raw_m=round(float(uv@a[:,1])+18,3)))
    lon, lat = lonlat(x,z)
    return dict(x=round(float(x),3), z=round(float(z),3), lat=round(float(lat),7), lon=round(float(lon),7),
                raw_dem_m=round(raw,3), local_raw_y_m=round(raw-18,3),
                site_terrain_bilinear_raw_m=round(float(current),3), built_surface_data=floor,
                inside_buildings=[b['id'] for b in city['buildings'] if Polygon(b['footprint_xz']).contains(Point(x,z))])


selected_roads = [r for r in city['roads'] if LineString(r['line_xz']).intersects(zone.buffer(6))]
roads = []
for r in selected_roads:
    ln = LineString(r['line_xz']); clip = ln.intersection(zone.buffer(6))
    pieces = [clip] if clip.geom_type == 'LineString' else [q for q in getattr(clip, 'geoms', []) if q.geom_type == 'LineString']
    samples = []
    for q in pieces:
        for d in np.linspace(0,q.length,max(2,int(math.ceil(q.length/2))+1)):
            p = q.interpolate(d); samples.append(sample(p.x,p.y))
    roads.append(dict(id=r['id'], name=r['name'], kind=r['kind'], width_m=r['width_m'],
                      width_source='osm' if ways[r['osm_way_id']].get('tags',{}).get('width') else 'current assumed road-class rule, not measured',
                      osm_tags=ways[r['osm_way_id']].get('tags',{}),
                      clipped_line_xz=[list(q.coords) for q in pieces], samples=samples))

building_reviews = []
for b in buildings:
    poly = Polygon(b['footprint_xz']); q = np.asarray(b['footprint_xz']); edge_reviews=[]
    for j, (a,c) in enumerate(zip(q,np.roll(q,-1,axis=0))):
        length = np.linalg.norm(c-a)
        if length < 3: continue
        mid=(a+c)/2; n=np.array([-(c-a)[1],(c-a)[0]])/length
        if poly.contains(Point(*(mid+n*.5))): n=-n
        points=[sample(*(mid+n*d)) for d in (0,1,2,3,4,5)]
        edge_reviews.append(dict(edge_index=j, a_xz=a.tolist(), b_xz=c.tolist(), length_m=round(float(length),3),
                                 outward_xz=n.tolist(), samples=points,
                                 dem_change_outward_5m=round(points[-1]['raw_dem_m']-points[0]['raw_dem_m'],3)))
    near=[]
    for r in sorted(city['roads'],key=lambda r:LineString(r['line_xz']).distance(poly))[:4]:
        pr, pb = nearest_points(LineString(r['line_xz']),poly)
        near.append(dict(id=r['id'],name=r['name'],kind=r['kind'],distance_to_centreline_m=round(pr.distance(pb),3),
                         road_point=sample(pr.x,pr.y),house_point=sample(pb.x,pb.y)))
    corner=[sample(*p) for p in b['footprint_xz']]
    building_reviews.append(dict(id=b['id'], address=b.get('address'), centroid_xz=b['centroid_xz'], footprint_xz=b['footprint_xz'],
                                 build_footprint_xz=b.get('build_footprint_xz'), source=b['source'], osm_tags=ways[b['osm_way_id']].get('tags',{}),
                                 build_rect=b['build_rect'], osm_area_m2=round(poly.area,3),
                                 build_area_m2=round(Polygon(b['build_footprint_xz']).area,3),
                                 build_outside_osm_area_m2=round(Polygon(b['build_footprint_xz']).difference(poly).area,3),
                                 current_base_raw_m=b['base_height_raw_m'], current_base_y_m=b['base_y_m'],
                                 dem_corner_min_m=min(s['raw_dem_m'] for s in corner),dem_corner_max_m=max(s['raw_dem_m'] for s in corner),
                                 corner_samples=corner, edges=edge_reviews, nearest_roads=near))

raw_barriers=[]
for e in osm['elements']:
    t=e.get('tags',{})
    if not ('barrier' in t or t.get('man_made') in ('retaining_wall','wall')): continue
    if e['type']=='node': geom=Point(local(e['lon'],e['lat'])); coords=[[geom.x,geom.y]]
    elif e['type']=='way':
        coords=[local(nodes[n]['lon'],nodes[n]['lat']) for n in e['nodes'] if n in nodes]
        if len(coords)<2: continue
        geom=LineString(coords)
    else: continue
    raw_barriers.append(dict(id=str(e['type'])[0]+str(e['id']), tags=t,line_xz=coords,distance_to_zone_m=round(geom.distance(zone),2)))
near_barriers=[r for r in raw_barriers if r['distance_to_zone_m']<=30]

def edge_for(wid,index):
    return next(e for b in building_reviews if b['id']==wid for e in b['edges'] if e['edge_index']==index)

review_targets=[]
for letter,wid,idx,why in [
    ('A','w92332120',8,'M29 väst/sydväst: leta efter plan gård, murkrön och murfot ned mot lägre tomt.'),
    ('B','w92332141',1,'M31 öst/sydöst: nivåskillnad upp mot Roten M-stigen; skilj trappa, mur och slänt.'),
    ('C','w92332141',9,'M31 nordväst: kontrollera var berget/slänten bryter, och om tomten har en skarp murkant.'),
    ('D','w92332120',6,'M29 södra urtag: kontrollera tomtnivån mot Stockliden och eventuell kort stödmur.'),
    ('E','w92331973',1,'M30 sydöst: hur entrégård/plantering möter Roten M-stigen och M29:s högre sida.'),
]:
    e=edge_for(wid,idx)
    usable=[]
    for p in e['samples']:
        if any(other!=wid for other in p['inside_buildings']): break
        usable.append(p)
    end=usable[-1]
    review_targets.append(dict(label=letter,building_id=wid,edge_index=idx,question=why,
                               start=e['samples'][0],end=end,
                               dem_delta_m=round(end['raw_dem_m']-e['samples'][0]['raw_dem_m'],3),
                               usable_distance_m=len(usable)-1,
                               warning='Profile stops before a neighbouring building. Longer DEM samples are not valid open-ground references.' if len(usable)<len(e['samples']) else None,
                               samples=e['samples']))

xs=np.arange(75,126,dtype=float);zs=np.arange(80,136,dtype=float);X,Z=np.meshgrid(xs,zs);DEM=raw_height(X,Z)
review=dict(meta=dict(date='2026-10-30',source_commit='321954c',bounds_xz=[75,80,125,135],origin=city['meta']['origin'],
                     coordinate_note='x east, z south, local Y = metres above sea level minus 18.',
                     epistemic_status='DATA INTERPRETATION ONLY. No visual observations; no wall, terrace or garden boundary confirmed.',
                     height_note='Raw LiDAR ground DEM is bilinearly sampled from the existing ~1 m raster. Current terrain values are bilinear samples of site.json 2 m grid, not an actual-mesh/BVH probe. Built surface data are sampled from site mesh triangles; stairs are listed separately.',
                     caveat='Building footprint DEM samples may be interpolated across buildings; they do not measure finished floors, wall tops or wall feet.'),
            buildings=building_reviews,roads=roads,inspection_targets=review_targets,
            barriers=dict(raw_osm_within_30m=near_barriers,city_within_30m=[b for b in city['barriers'] if LineString(b['line_xz']).distance(zone)<=30],
                          nearest_raw_osm=sorted(raw_barriers,key=lambda r:r['distance_to_zone_m'])[:3],note='Absence in OSM is not evidence of absence in the real place.'),
            existing_trees=[t for t in site['trees'] if zone.contains(Point(t[0],t[2]))],
            stairs=[s for s in site['stairs'] if LineString([(p[0],p[2]) for p in s['points']]).intersects(zone.buffer(6))],
            raw_dem_grid=dict(x0=75,z0=80,spacing_m=1,nx=51,nz=56,heights_raw_m=np.round(DEM,2).tolist(),note='Interpretation support; not proposed terrace elevations.'))
(OUT/'data-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2))

# Lightweight CPU-only top plan; height shading is DEM, not inferred wall geometry.
img=Image.new('RGB',(1270,1050),'#faf9f4');draw=ImageDraw.Draw(img)
font_path='/System/Library/Fonts/Supplemental/Arial.ttf'
font=ImageFont.truetype(font_path,18);small=ImageFont.truetype(font_path,15);title=ImageFont.truetype(font_path,28)
left,top,scale=75,120,14
def xy(x,z):return (round(left+(x-75)*scale),round(top+(z-80)*scale))
def height_color(h):
    u=max(0,min(1,(h-31)/12));return tuple(round(a+(b-a)*u) for a,b in zip((188,205,214),(194,178,124)))
draw.text((50,28),'Roten M 29–31 — datagranskning',font=title,fill='#172a34')
draw.text((50,70),'DTM-tolkning. Murar och tomtnivåer måste verifieras visuellt.',font=font,fill='#394c55')
for k in range(55):
    for i in range(50):
        a=xy(75+i,80+k);b=xy(76+i,81+k);draw.rectangle((*a,*b),fill=height_color(DEM[k,i]))
for v in range(75,126,5):
    draw.line([xy(v,80),xy(v,135)],fill='#b8b7a9',width=1);draw.text((xy(v,80)[0]-10,top-24),str(v),font=small,fill='#394c55')
for v in range(80,136,5):
    draw.line([xy(75,v),xy(125,v)],fill='#b8b7a9',width=1);draw.text((left-34,xy(75,v)[1]-7),str(v),font=small,fill='#394c55')
for r in roads:
    for line in r['clipped_line_xz']:
        clipped=LineString(line).intersection(zone)
        lines=[clipped] if clipped.geom_type=='LineString' else [q for q in getattr(clipped,'geoms',[]) if q.geom_type=='LineString']
        for ln in lines:
            points=[xy(*p) for p in ln.coords]
            draw.line(points,fill='#8a9392' if r['kind']!='steps' else '#cf975e',width=max(3,round(r['width_m']*scale)))
            draw.line(points,fill='#f3f1e9',width=2)
for b in city['buildings']:
    if not Polygon(b['footprint_xz']).intersects(zone):continue
    clipped=Polygon(b['footprint_xz']).intersection(zone)
    polys=[clipped] if clipped.geom_type=='Polygon' else [q for q in getattr(clipped,'geoms',[]) if q.geom_type=='Polygon']
    for poly in polys:
        points=[xy(*p) for p in poly.exterior.coords]
        draw.polygon(points,fill='#fffdf8' if b['id'] in IDS else '#ddd9cf',outline='#3e4648',width=3)
    c=b['centroid_xz'];label=b.get('address','').replace('Roten M ','M ').replace('Royens gata ','R ')
    if b['id'] in IDS:draw.text((xy(*c)[0]-24,xy(*c)[1]-10),label,font=font,fill='#172a34')
for t in review['existing_trees']:
    p=xy(t[0],t[2]);r=round(2.8*scale);draw.ellipse((p[0]-r,p[1]-r,p[0]+r,p[1]+r),outline='#446e3d',width=3)
for b in buildings:
    at=xy(*b['centroid_xz'])
    draw.text((at[0]-24,at[1]-10),b['address'].replace('Roten M ','M '),font=font,fill='#172a34')
for text,x,z in [('Roten M',84,100),('Royens gata',112,119),('Stockliden',108,132),('Stalliden',76,98)]:
    at=xy(x,z);bounds=draw.textbbox(at,text,font=small)
    draw.rectangle((bounds[0]-2,bounds[1]-2,bounds[2]+2,bounds[3]+2),fill='#faf9f4')
    draw.text(at,text,font=small,fill='#273d47')
for target in review_targets:
    a,b=target['start'],target['end'];pa,pb=xy(a['x'],a['z']),xy(b['x'],b['z'])
    draw.line((pa,pb),fill='#b42e42',width=4)
    for pt in (pa,pb):draw.ellipse((pt[0]-4,pt[1]-4,pt[0]+4,pt[1]+4),fill='#b42e42')
    draw.text((pb[0]-7,max(top+4,pb[1]-22)),target['label'],font=font,fill='#8a172d')
# Clip stroke widths as well as centre-lines at the map frame.
for rect in [(0,90,left-1,910),(left+701,90,1269,910),(0,891,1269,1000),(0,90,1269,top-1)]:
    draw.rectangle(rect,fill='#faf9f4')
for v in range(75,126,5):draw.text((xy(v,80)[0]-10,top-24),str(v),font=small,fill='#394c55')
for v in range(80,136,5):draw.text((left-34,xy(75,v)[1]-7),str(v),font=small,fill='#394c55')
draw.rectangle((left,top,left+700,top+770),outline='#374d55',width=2)
draw.text((820,120),'Kontrollera i platsreferensen',font=font,fill='#172a34')
for n,t in enumerate(review_targets):
    y=170+n*117
    draw.text((820,y),f"{t['label']}  {next(b['address'] for b in buildings if b['id']==t['building_id'])}",font=font,fill='#8a172d')
    a,b=t['start'],t['end']
    draw.text((820,y+27),f"x/z {a['x']:.1f}, {a['z']:.1f}",font=small,fill='#273d47')
    draw.text((820,y+49),f"→ {b['x']:.1f}, {b['z']:.1f}",font=small,fill='#273d47')
    draw.text((820,y+72),f"DTM {a['raw_dem_m']:.2f} → {b['raw_dem_m']:.2f} m ö.h.",font=small,fill='#273d47')
draw.text((820,810),'Inga murar/staket i OSM',font=font,fill='#172a34')
draw.text((820,838),'inom 30 m från rutan.',font=small,fill='#273d47')
draw.text((820,865),'Deras verkliga lägen är okända.',font=small,fill='#273d47')
draw.text((75,920),'N ↑   x öst / z syd. Skala: 10 m',font=font,fill='#172a34')
draw.line((75,960,215,960),fill='#172a34',width=5)
draw.text((450,920),'DTM-färg: blågrått 31 m → sand 43 m ö.h.',font=small,fill='#394c55')
draw.text((300,950),'Grön ring: enda befintliga trädplaceringen i rutan.',font=small,fill='#394c55')
draw.text((75,1003),'Källor: OpenStreetMap-bidragsgivare (ODbL), Lantmäteriets DTM; aktuell city/site-data 2026-10-30.',font=small,fill='#394c55')
img.save(OUT/'data-review.jpg',quality=89)
print('WROTE',OUT/'data-review.json',OUT/'data-review.jpg')
print('DEM_RANGE',float(DEM.min()),float(DEM.max()))

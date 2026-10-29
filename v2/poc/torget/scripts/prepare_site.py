"""Prepare a small, authored site from the surveyed map references.
Run with tools/venv/bin/python. The finished surfaces are authored/exported in Blender.
"""
from pathlib import Path
import json, math
import numpy as np
from PIL import Image
from shapely.geometry import LineString, Polygon, Point, box
from shapely.ops import unary_union, triangulate

HERE=Path(__file__).resolve().parents[1]
REPO=HERE.parents[2]
city=json.loads((HERE/'data/city_spec.json').read_text())
meta=city['meta']; origin=meta['origin']; offset=origin['y_offset_m']
lm=json.loads((REPO/'tools/lidar_meta.json').read_text())
dem=np.array(Image.open(REPO/'tools/lidar_1m.png'),dtype=np.float64)/lm['png_scale']+lm['png_offset_m']*-1

def raw(x,z):
    lon=origin['lon']+x/59560;lat=origin['lat']-z/111320
    fx=(lon-lm['lon0'])/(lm['lon1']-lm['lon0'])*(lm['w']-1);fz=(lm['lat1']-lat)/(lm['lat1']-lm['lat0'])*(lm['h']-1)
    ix=max(0,min(lm['w']-2,int(fx)));iz=max(0,min(lm['h']-2,int(fz)));tx=fx-ix;tz=fz-iz
    return float((dem[iz,ix]*(1-tx)+dem[iz,ix+1]*tx)*(1-tz)+(dem[iz+1,ix]*(1-tx)+dem[iz+1,ix+1]*tx)*tz)

area=box(-66,-66,66,66)
river=city['waterways'][0]
river_line=LineString(river['line_xz']);river_shape=river_line.buffer(4.25,cap_style=2,join_style=2)
buildings=unary_union([Polygon(b['footprint_xz']) for b in city['buildings']])
road_items=[];paths=[];bridges=[]
for r in city['roads']:
    line=LineString(r['line_xz'])
    if r['bridge']:bridges.append(r);continue
    if r['kind'] in ['residential','tertiary','unclassified','service']:
        # Anchored authored profiles: 3-point mean eliminates single-pixel DTM grooves.
        heights=[raw(x,z) for x,z in r['line_xz']]
        if r['name']=='Kvarnbygatan':
            heights=[max(h,17.65) for h in heights]
        heights=[(heights[max(0,i-1)]+2*h+heights[min(len(heights)-1,i+1)])/4 for i,h in enumerate(heights)]
        road_items.append((r,line,heights))
    elif r['kind'] in ['path','footway']:
        paths.append((r,line))
asphalt=unary_union([line.buffer(r['width_m']/2,cap_style=2,join_style=2) for r,line,_ in road_items]).intersection(area).difference(river_shape.buffer(.02)).difference(buildings.buffer(.03))
sidewalk=unary_union([line.buffer(r['width_m']/2+1.3,cap_style=2,join_style=2) for r,line,_ in road_items]+[line.buffer(r['width_m']/2,cap_style=2,join_style=2) for r,line in paths]).intersection(area).difference(asphalt).difference(buildings.buffer(.04)).difference(river_shape.buffer(.04))
parking=[];squares=[]
for s in city['surfaces']:
    p=Polygon(s['polygon_xz'])
    (squares if s['kind']=='square' else parking).append((s,p))
parking_geom=unary_union([p for _,p in parking])
square_geom=unary_union([p for _,p in squares])
asphalt=asphalt.union(parking_geom).difference(square_geom)
sidewalk=sidewalk.union(square_geom).difference(asphalt)
# Raised stone promenade beside the river is visible in reference views.
promenade=river_shape.buffer(1.35).difference(river_shape).difference(buildings).intersection(area)
sidewalk=sidewalk.union(promenade).difference(asphalt)
authored=json.loads((HERE/'reference/authored_ground.json').read_text())
authored_plates=[]
for item in authored['pavement_polygons']:
    poly=Polygon(item['polygon_xz'])
    if item['id']=='torget_connected_forecourt':plane=[-.004065,-.011889,17.495]
    else:
        coords=np.array(item['polygon_xz']);values=np.array([raw(x,z) for x,z in coords]);fit=np.linalg.lstsq(np.column_stack([coords,np.ones(len(coords))]),values,rcond=None)[0]
        magnitude=math.hypot(fit[0],fit[1])
        if magnitude>.08:fit[:2]*=.08/magnitude
        plane=fit.tolist()
    authored_plates.append((item,poly,plane))
planters=unary_union([Polygon(p['polygon_xz']) for p in authored['planter_polygons']])
forecourt=authored_plates[0][1]
retained_driving=unary_union([line.buffer(r['width_m']/2,cap_style=2,join_style=2) for r,line,_ in road_items if r['name']!='Gamla Torget'])
asphalt=asphalt.difference(forecourt).union(retained_driving.intersection(forecourt)).difference(planters).difference(buildings).difference(river_shape)
sidewalk=sidewalk.union(unary_union([p for _,p,_ in authored_plates])).difference(asphalt).difference(buildings.buffer(.04)).difference(river_shape.buffer(.04)).difference(planters)
urban=asphalt.union(sidewalk).buffer(.2)


def line_height(line,coords,heights,x,z):
    q=line.project(Point(x,z));acc=0
    for i,(a,b) in enumerate(zip(coords,coords[1:])):
        seg=math.dist(a,b)
        if q<=acc+seg or i==len(coords)-2:
            t=max(0,min(1,(q-acc)/max(seg,.001)));return heights[i]*(1-t)+heights[i+1]*t
        acc+=seg
    return heights[-1]


def grade(x,z):
    original=raw(x,z);p=Point(x,z)
    for item,poly,plane in authored_plates:
        distance=poly.distance(p)
        if distance<1.5:
            a,b,c=plane;t=max(0,1-distance/1.5)
            original=original*(1-t)+(a*x+b*z+c)*t
            break
    for s,poly in squares+parking:
        distance=poly.distance(p)
        if distance<1.5:
            a,b,c=s['ground_plane_raw'];level=a*x+b*z+c;t=max(0,1-distance/1.5)
            return original*(1-t)+level*t
    best=None
    for r,line,heights in road_items:
        if r['name']=='Gamla Torget' and forecourt.contains(p):continue
        distance=line.distance(p);normalized=distance-r['width_m']/2
        if normalized<2 and (best is None or normalized<best[0]):
            best=(normalized,line_height(line,r['line_xz'],heights,x,z))
    if best:
        t=max(0,min(1,1-best[0]/2));return original*(1-t)+best[1]*t
    return original


def water_height(x,z):
    # Authored falling channel. DTM water points are not a surveyed water surface.
    coords=river['line_xz'];heights=[16.15,16.12,16.07,15.8,15.45,14.7,14.4,14.0,13.25,12.8,12.45,12.4]
    return line_height(river_line,coords,heights,x,z)


def height(x,z):
    h=grade(x,z)
    d=river_shape.distance(Point(x,z))
    if river_shape.contains(Point(x,z)):return min(h,water_height(x,z)-.7)
    # The designed street surface owns its footprint. Keep the background terrain
    # beneath it; it must never poke through a long polygon triangle.
    if urban.contains(Point(x,z)):h-=.08
    return h


def triangles(geom,kind):
    result=[]
    polygons=list(geom.geoms) if hasattr(geom,'geoms') else [geom]
    for poly in polygons:
        if poly.is_empty or poly.area<.05:continue
        xmin,zmin,xmax,zmax=poly.bounds
        for x0 in range(math.floor(xmin/2)*2,math.ceil(xmax/2)*2,2):
            for z0 in range(math.floor(zmin/2)*2,math.ceil(zmax/2)*2,2):
                cell=poly.intersection(box(x0,z0,x0+2,z0+2))
                if cell.is_empty or cell.area<.0001:continue
                for tri in triangulate(cell):
                    if not cell.covers(tri):continue
                    points=[]
                    for x,z in list(tri.exterior.coords)[:3]:
                        y=(water_height(x,z) if kind=='water' else grade(x,z)+(.13 if kind=='sidewalk' else .05 if kind=='soil' else .04))-offset
                        points.append([round(x,4),round(y,4),round(z,4)])
                    result.append(points)
    return result

meshes={'asphalt':triangles(asphalt,'asphalt'),'sidewalk':triangles(sidewalk,'sidewalk'),'water':triangles(river_shape.intersection(area),'water'),'soil':triangles(planters,'soil')}
terrain=[]
for z in range(-140,142,2):
    terrain.append([[x,round(height(x,z)-offset,4),z] for x in range(-140,182,2)])
curbs=[]
bridge_clearance=unary_union([LineString(b['line_xz']).buffer(b['width_m']/2+1.6) for b in bridges])
for geom in [asphalt]:
    polys=list(geom.geoms) if hasattr(geom,'geoms') else [geom]
    for poly in polys:
        rings=[poly.exterior]+list(poly.interiors)
        for ring in rings:
            coords=list(ring.coords)
            for a,b in zip(coords,coords[1:]):
                if math.dist(a,b)<.2:continue
                if bridge_clearance.contains(Point((a[0]+b[0])/2,(a[1]+b[1])/2)):continue
                curbs.append([[a[0],grade(*a)-offset+.11,a[1]],[b[0],grade(*b)-offset+.11,b[1]]])
result={'meta':{'note':'Authored road profiles, kerb widths and water levels for first visual proof; not a city-scale solver.','vertical_exaggeration':1,'y_offset_m':offset},'meshes':meshes,'terrain':terrain,'curbs':curbs,'bridge':bridges,'road_profiles':[{'id':r['id'],'line_xz':r['line_xz'],'raw_heights_m':heights,'width_m':r['width_m']} for r,_,heights in road_items]}
result['authored_plates']=[{'id':i['id'],'plane_raw':plane} for i,_,plane in authored_plates]
result['planters']=authored['planter_polygons']
skirts=[]
for kind,geom in [('asphalt',asphalt),('sidewalk',sidewalk)]:
    polys=list(geom.geoms) if hasattr(geom,'geoms') else [geom]
    for poly in polys:
        if poly.is_empty or not hasattr(poly,'exterior'):continue
        for ring in [poly.exterior]+list(poly.interiors):
            coords=list(ring.segmentize(1).coords)
            for a,b in zip(coords,coords[1:]):
                ha=grade(*a)-offset;hb=grade(*b)-offset;top=.13 if kind=='sidewalk' else .04
                skirts.append([[a[0],ha+top,a[1]],[b[0],hb+top,b[1]],[b[0],hb-.28,b[1]],[a[0],ha-.28,a[1]]])
result['surface_foundations']=skirts
(HERE/'data/site_meshes.json').write_text(json.dumps(result,separators=(',',':')))
print({key:len(value) for key,value in meshes.items()},'terrain',len(terrain),'curbs',len(curbs))

#!/usr/bin/env python3
"""Tolkning: OSM + LiDAR-DTM + ortofoto + klasskarta → stadsbeskrivning (data/city.json).

Inget här är geometri. Varje hus får en hustyp (arketyp) och parametrar som Blender-bygget
använder; varje värde märks med källa: `observed` (handgranskat, torget-provet), `osm`,
`ortho` (uppmätt ur flygfotot) eller `assumed` (tolkningsregel). Så syns vad husrundorna
i Fas C ska förbättra.

    tools/venv/bin/python v2/kvarnbyn/pipeline/interpret.py
"""
import json, math
from collections import Counter
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, box, Point
from shapely.ops import unary_union, linemerge

from common import (ZONE, BACKDROP, DATA, TORGET, Y_OFFSET, V1_ORIGIN, raw_height, ortho_rgb,
                    load_osm, way_xz, stable_hash, r3)

zone = box(*ZONE)
backdrop = box(*BACKDROP)
j, nodes, ways = load_osm()

# ---------- handgranskade hus från torget-provet (observed) ----------
torget = json.loads((TORGET / 'data/city_spec.json').read_text())
HEROES = {b['osm_way_id']: b for b in torget['buildings'] if not b['name'].startswith('Bakgrundshus')}
factory = json.loads((TORGET / 'reference/industrial_backdrop.json').read_text())
FACTORY_ID = factory['identification']['correct_osm_way_id']
roten_m29 = json.loads((DATA.parent / 'reference/roten-m/house.json').read_text())
stalliden_houses = json.loads((DATA.parent / 'reference/stalliden/houses.json').read_text())

# ---------- paletter (assumed: typiska kulörer i Kvarnbyn, inte uppmätta per hus) ----------
WOOD = ['#efece4', '#efece4', '#e9dcae', '#8e3326', '#8e3326', '#cfccc2', '#bcc6a8', '#bccad0', '#d8b46c', '#e6d8c0']
PLASTER = ['#ebe3cd', '#e3d2ae', '#f0ece2', '#d8c6a4', '#cfc8bb', '#e4c9a6']
BRICK = ['#9a5640', '#8f4a36', '#a8644a']
TRIM_LIGHT = '#ece8de'


def pick(palette, wid, salt):
    return palette[int(stable_hash(wid, salt) * len(palette)) % len(palette)]


def roof_from_ortho(poly):
    """Takets färg ur ortofotot (median inne i fotavtrycket) → material + kulör."""
    inner = poly.buffer(-0.8)
    g = inner if not inner.is_empty and inner.area > 4 else poly
    minx, minz, maxx, maxz = g.bounds
    rng = np.random.default_rng(abs(hash(round(minx * 1000))) % (2**32))
    xs = rng.uniform(minx, maxx, 500); zs = rng.uniform(minz, maxz, 500)
    m = shapely.contains_xy(g, xs, zs)
    if m.sum() < 5:
        return 'roof_tiles_grey', '#6b6a66', 'assumed'
    rgb = np.median(ortho_rgb(xs[m], zs[m]), axis=0)
    r, gg, b = rgb
    mx, mn = max(rgb), min(rgb); v = mx; s = 0 if mx == 0 else (mx - mn) / mx
    hue = 0
    if mx != mn:
        if mx == r: hue = (60 * ((gg - b) / (mx - mn)) + 360) % 360
        elif mx == gg: hue = 60 * ((b - r) / (mx - mn)) + 120
        else: hue = 60 * ((r - gg) / (mx - mn)) + 240
    # vårfotot är blekt: lyft mättnad lite för kulören som används
    boost = np.clip((rgb - rgb.mean()) * 1.35 + rgb.mean(), 0, 1)
    hexc = '#%02x%02x%02x' % tuple(int(c * 255) for c in boost)
    if v < 0.33:
        return 'metal_dark', hexc, 'ortho'
    if (hue < 32 or hue > 335) and s > 0.22:
        return 'roof_tiles', hexc, 'ortho'
    if s < 0.13 and v > 0.58:
        return 'flat_light', hexc, 'ortho'
    return 'roof_tiles_grey', hexc, 'ortho'


def classify(tags, area, w, l, roof_mat, near_river):
    tag = tags.get('building', 'yes')
    if tag in ('garage', 'garages', 'shed', 'carport', 'hut', 'roof', 'service') or area < 32 or (area < 55 and w < 4.6):
        return 'bod'
    if tag in ('school', 'kindergarten', 'public', 'civic', 'church', 'college'):
        return 'offentlig'
    if tag in ('industrial', 'warehouse', 'manufacture') or (area >= 700 and near_river):
        return 'industri'
    if tag in ('apartments', 'dormitory') or (area >= 300 and w >= 9 and l / max(w, 1) >= 2.0) or area >= 700:
        return 'flerbostad'
    if tag in ('office', 'commercial', 'retail') and area > 250:
        return 'flerbostad'
    return 'trahus'


def building_spec(w, poly, tags, river):
    wid = w['id']
    rect = poly.minimum_rotated_rectangle
    rc = list(rect.exterior.coords)[:-1]
    lens = [math.dist(rc[i], rc[(i + 1) % 4]) for i in range(4)]
    k = max(range(4), key=lambda i: lens[i])
    u = (np.array(rc[(k + 1) % 4]) - np.array(rc[k])) / max(lens[k], 1e-6)
    if u[0] < 0: u = -u
    L, W = max(lens), min(lens)
    area = poly.area
    foot = [tuple(p) for p in poly.exterior.coords[:-1]]
    ground = raw_height([p[0] for p in foot], [p[1] for p in foot])
    near_river = river is not None and poly.distance(river) < 45
    roof_mat, roof_col, roof_src = roof_from_ortho(poly)
    arch = classify(tags, area, W, L, roof_mat, near_river)
    src = {}
    levels = None
    if tags.get('building:levels'):
        try: levels = max(1, int(round(float(tags['building:levels'])))); src['levels'] = 'osm'
        except ValueError: pass
    hrng = stable_hash(wid, 'h')
    if arch == 'bod':
        levels = levels or 1; wall = 2.5 + 0.4 * hrng; rise = min(1.6, W * 0.22); shape = 'gabled' if W > 3 else 'pent'
        fac_mat = 'wood'; fac = pick(['#8e3326', '#8e3326', '#cfccc2', '#efece4', '#6f6a60'], wid, 'f')
    elif arch == 'trahus':
        if not levels: levels = 1 if area < 75 else 2
        wall = {1: 3.1, 2: 5.7}.get(levels, levels * 2.8 + 0.3) + 0.3 * hrng
        if levels == 2 and area < 115: wall = 4.4 + 0.3 * hrng   # 1½-plan: låg övervåning under brant tak
        rise = W * (0.42 if levels == 1 else 0.36); shape = 'hipped' if (area > 140 and stable_hash(wid, 'r') < 0.35) else 'gabled'
        fac_mat = 'plaster' if (area > 110 and stable_hash(wid, 'm') < 0.18) else 'wood'
        fac = pick(PLASTER if fac_mat == 'plaster' else WOOD, wid, 'f')
    elif arch == 'flerbostad':
        if not levels: levels = 4 if area > 700 else 3
        wall = levels * 2.85 + 0.7; rise = 1.6 if roof_mat != 'flat_light' and levels <= 5 else 0.0
        shape = 'gabled' if rise > 0 else 'flat'
        fac_mat = 'brick' if stable_hash(wid, 'm') < 0.3 else 'plaster'
        fac = pick(BRICK if fac_mat == 'brick' else PLASTER, wid, 'f')
    elif arch == 'industri':
        if not levels: levels = 3 if area < 1500 else 4
        wall = levels * 3.9 + 0.6; rise = 0.0; shape = 'flat'; fac_mat = 'brick'; fac = pick(BRICK, wid, 'f')
    else:  # offentlig
        if not levels: levels = 2
        wall = levels * 3.4 + 0.6; rise = W * 0.25; shape = 'hipped'; fac_mat = 'plaster'; fac = pick(PLASTER, wid, 'f')
    src.setdefault('levels', 'assumed')
    base = float(np.percentile(ground, 65))
    spec = dict(id='w%d' % wid, osm_way_id=wid, name=tags.get('name', ''), archetype=arch, priority='context',
                levels=int(levels), wall_height_m=round(wall, 2), roof_rise_m=round(rise, 2), roof_shape=shape,
                roof_material=roof_mat, roof_color=roof_col, facade_material=fac_mat, facade_color=fac,
                trim_color=TRIM_LIGHT, base_height_raw_m=round(base, 3), base_y_m=round(base - Y_OFFSET, 3),
                ground_min_raw_m=round(float(ground.min()), 3), footprint_xz=[r3(p) for p in foot],
                centroid_xz=r3((poly.centroid.x, poly.centroid.y)), major_axis_xz=r3(u), major_length_m=round(L, 3),
                minor_width_m=round(W, 3), area_m2=round(area, 1),
                source=dict(footprint='osm', levels=src['levels'], heights='assumed', roof_color=roof_src,
                            roof_material=roof_src, facade='assumed', archetype='assumed'),
                osm_tags=tags)
    if tags.get('addr:street'):
        spec['address'] = (tags.get('addr:street', '') + ' ' + tags.get('addr:housenumber', '')).strip()
    return spec


# ---------- ån ----------
river_lines = [LineString(way_xz(w, nodes)) for w in ways if w.get('tags', {}).get('waterway') == 'river']
river_lines = [l for l in river_lines if l.intersects(backdrop)]
river_merged = linemerge(unary_union(river_lines))
river_polys = []
for w in ways:
    t = w.get('tags', {})
    if t.get('natural') == 'water' and w['nodes'][0] == w['nodes'][-1]:
        p = Polygon(way_xz(w, nodes)).buffer(0)
        if p.intersects(backdrop): river_polys.append(p)
river_geom = unary_union([l.buffer(4.25, cap_style=2, join_style=2) for l in river_lines] + river_polys)

# ---------- hus ----------
buildings, backdrop_buildings = [], []
counts = Counter()
for w in ways:
    t = w.get('tags', {})
    if 'building' not in t or t.get('amenity') == 'shelter' or t.get('building') == 'roof':
        continue
    p = way_xz(w, nodes)
    if len(p) < 4: continue
    poly = Polygon(p)
    if not poly.is_valid: poly = poly.buffer(0)
    if poly.is_empty or poly.geom_type != 'Polygon' or poly.area < 6: continue
    c = poly.centroid
    if zone.contains(c):
        if w['id'] in HEROES:
            spec = dict(HEROES[w['id']])
            spec['source'] = dict(footprint='osm', facade='observed', heights='observed_estimate', roof='observed')
            spec['archetype_family'] = 'hero'
            spec.setdefault('area_m2', round(poly.area, 1))
        else:
            spec = building_spec(w, poly, t, river_geom)
            if w['id'] == FACTORY_ID:
                est = factory['authored_volume_estimate']
                spec.update(name='Stora Götafors', archetype='industri', priority='landmark', levels=est['visible_levels_river_side_approx'],
                            wall_height_m=est['wall_height_m'], roof_rise_m=0.0, roof_shape='flat', facade_material='brick',
                            facade_color=est['facade_color'], roof_color=est['roof_color'], base_height_raw_m=est['base_height_raw_m'],
                            base_y_m=round(est['base_height_raw_m'] - Y_OFFSET, 3), sign='STORA GÖTAFORS')
                spec['source'].update(heights='observed_estimate', facade='observed')
        if spec['id'] == roten_m29['id']:
            spec.update(name=roten_m29['name'], authored_model='roten_m29', priority='landmark',
                        levels=1, wall_height_m=3.25, roof_rise_m=2.15, roof_shape='joined_gables',
                        facade_material='wood', facade_color=roten_m29['wall_color'],
                        trim_color=roten_m29['trim_color'], roof_material='roof_tiles', roof_color='#855b47')
            spec['source'].update(levels='observed', facade='observed', roof_shape='observed',
                                  heights='observed_estimate', roof_color='observed_estimate',
                                  roof_material='observed', roof_subdivision='observed_estimate')
        context = stalliden_houses['buildings'].get(spec['id'])
        if context:
            spec.update(context['override']); spec['name'] = context['name']
            spec['source'].update(context['source'])
        buildings.append(spec); counts[spec['archetype']] += 1
    elif backdrop.contains(c):
        L = poly.minimum_rotated_rectangle
        lv = t.get('building:levels')
        try: lv = int(round(float(lv)))
        except (TypeError, ValueError): lv = None
        a = poly.area
        if lv is None: lv = 1 if a < 60 else 2 if a < 300 else 3 if a < 1500 else 4
        foot = [tuple(q) for q in poly.simplify(0.6).exterior.coords[:-1]]
        g = raw_height([q[0] for q in foot], [q[1] for q in foot])
        _, roof_col, _ = roof_from_ortho(poly)
        backdrop_buildings.append(dict(id='w%d' % w['id'], footprint_xz=[r3(q) for q in foot], base_y_m=round(float(np.percentile(g, 50)) - Y_OFFSET, 2),
                                       ground_min_y_m=round(float(g.min()) - Y_OFFSET, 2), height_m=round(lv * 3.0 + 0.6, 1),
                                       roof_color=roof_col, facade_color=pick(PLASTER + WOOD[:3], w['id'], 'f')))

# ---------- gator, ytor, barriärer, skog ----------
WIDTH = {'primary': 9.0, 'secondary': 8.0, 'tertiary': 7.0, 'residential': 5.5, 'living_street': 5.0, 'unclassified': 5.0,
         'service': 3.5, 'pedestrian': 4.0, 'footway': 2.0, 'path': 1.8, 'cycleway': 2.5, 'steps': 2.0, 'track': 3.0,
         'motorway': 11.0, 'motorway_link': 6.0, 'trunk': 10.0, 'trunk_link': 6.0, 'primary_link': 6.0, 'secondary_link': 6.0, 'tertiary_link': 5.5}
work = zone.buffer(60)
roads, surfaces, barriers, forests = [], [], [], []
for w in ways:
    t = w.get('tags', {}); p = way_xz(w, nodes)
    if len(p) < 2: continue
    line = LineString(p)
    if not line.intersects(work): continue
    closed = len(p) > 3 and w['nodes'][0] == w['nodes'][-1]
    hw = t.get('highway')
    kind = None
    if t.get('amenity') == 'parking' and closed and t.get('parking') not in ('underground', 'multi-storey', 'rooftop'): kind = 'parking'
    elif hw == 'pedestrian' and t.get('area') == 'yes' and closed: kind = 'square'
    elif t.get('leisure') in ('pitch', 'playground') and closed: kind = t['leisure']
    if kind:
        poly = Polygon(p).buffer(0)
        if poly.geom_type == 'Polygon' and poly.area > 20:
            surfaces.append(dict(id='w%d' % w['id'], kind=kind, name=t.get('name', ''), surface=t.get('surface', ''),
                                 polygon_xz=[r3(q) for q in poly.exterior.coords[:-1]], osm_tags=t))
        continue
    if hw in WIDTH and t.get('area') != 'yes':
        width = WIDTH[hw]
        if t.get('width'):
            try: width = max(1.5, min(16, float(str(t['width']).replace('m', ''))))
            except ValueError: pass
        roads.append(dict(id='w%d' % w['id'], osm_way_id=w['id'], name=t.get('name', ''), kind=hw, width_m=width,
                          bridge=bool(t.get('bridge')) and t.get('bridge') != 'no', tunnel=bool(t.get('tunnel')) and t.get('tunnel') != 'no',
                          layer=t.get('layer', '0'), surface=t.get('surface', ''), line_xz=[r3(q) for q in p], node_ids=w['nodes'],
                          sidewalk=t.get('sidewalk', '')))
    if t.get('barrier') in ('wall', 'retaining_wall', 'hedge', 'fence', 'guard_rail') and line.intersects(zone):
        barriers.append(dict(id='w%d' % w['id'], kind=t['barrier'], line_xz=[r3(q) for q in p]))
    if (t.get('landuse') == 'forest' or t.get('natural') in ('wood', 'scrub')) and closed:
        poly = Polygon(p).buffer(0)
        if not poly.is_empty: forests.append(dict(id='w%d' % w['id'], polygon_xz=[r3(q) for q in (poly.exterior.coords[:-1] if poly.geom_type == 'Polygon' else [])]))

waterways = []
for g in (river_merged.geoms if hasattr(river_merged, 'geoms') else [river_merged]):
    coords = list(g.simplify(0.5).coords)
    waterways.append(dict(name='Mölndalsån', line_xz=[r3(q) for q in coords], channel_width_m=8.5, width_source='assumed'))
water_polys = [dict(polygon_xz=[r3(q) for q in p.exterior.coords[:-1]]) for p in river_polys if p.geom_type == 'Polygon']

# ---------- byggunderlag: förenklat fotavtryck + gatufasad (Blender saknar shapely) ----------
street_lines = [LineString(r['line_xz']) for r in roads if r['kind'] not in ('path', 'track') and not r['tunnel']]
from shapely.strtree import STRtree as _T
_st = _T(street_lines)
for b in buildings:
    if b.get('archetype_family') == 'hero':
        continue
    poly = Polygon(b['footprint_xz']).buffer(0)
    rect = poly.minimum_rotated_rectangle
    fill = poly.area / max(rect.area, 1e-6)
    simple = b['archetype'] in ('trahus', 'bod', 'offentlig') and fill >= 0.72 and not b.get('keep_osm_footprint')
    foot = list(rect.exterior.coords)[:-1] if simple else [tuple(q) for q in (poly if b.get('keep_osm_footprint') else poly.simplify(0.25)).exterior.coords[:-1]]
    if Polygon(foot).exterior.is_ccw: foot = foot[::-1]          # medurs i (x,z) = moturs i Blender (x,−z)
    b['build_footprint_xz'] = [r3(q) for q in foot]
    b['build_rect'] = bool(simple)
    b['footprint_fill'] = round(fill, 3)
    mids = [((foot[i][0] + foot[(i + 1) % len(foot)][0]) / 2, (foot[i][1] + foot[(i + 1) % len(foot)][1]) / 2) for i in range(len(foot))]
    d = [min(1e9, _st.query_nearest(Point(m), return_distance=True)[1][0]) if street_lines else 1e9 for m in mids]
    lens = [math.dist(foot[i], foot[(i + 1) % len(foot)]) for i in range(len(foot))]
    cand = [i for i in range(len(foot)) if lens[i] >= 2.4] or list(range(len(foot)))
    b['street_edge'] = int(min(cand, key=lambda i: d[i]))
    b['street_distance_m'] = round(float(d[b['street_edge']]), 2)

meta = dict(schema_version=1, created='2026-10-29', name='Kvarnbyn — spelbar zon (Fas A)',
            origin=torget['meta']['origin'], projection=torget['meta']['projection'],
            zone=dict(min_x=ZONE[0], min_z=ZONE[1], max_x=ZONE[2], max_z=ZONE[3]),
            backdrop=dict(min_x=BACKDROP[0], min_z=BACKDROP[1], max_x=BACKDROP[2], max_z=BACKDROP[3]),
            v1_origin_xz=r3(V1_ORIGIN),
            v1_points=dict(spawn=r3((447.2 - V1_ORIGIN[0], 53.0 - V1_ORIGIN[1])), cap_A=r3((89.4 - V1_ORIGIN[0], -106.6 - V1_ORIGIN[1])),
                           cap_B=r3((208 - V1_ORIGIN[0], 10 - V1_ORIGIN[1])), cap_C=r3((282 - V1_ORIGIN[0], -101 - V1_ORIGIN[1]))),
            data_sources=torget['meta']['data_sources'],
            source_legend=dict(observed='handgranskat (Street View/Wikimedia) i torget-provet', osm='OpenStreetMap-tagg',
                               ortho='mätt ur Lantmäteriets ortofoto 2024', assumed='tolkningsregel i interpret.py — förbättras i husrundor'))
city = dict(meta=meta, buildings=buildings, backdrop_buildings=backdrop_buildings, roads=roads, surfaces=surfaces,
            waterways=waterways, water_polygons=water_polys, barriers=barriers, forests=forests,
            reviewed_houses={'roten_m29': roten_m29},
            authored_ground=json.loads((TORGET / 'reference/authored_ground.json').read_text()))
DATA.mkdir(parents=True, exist_ok=True)
(DATA / 'city.json').write_text(json.dumps(city, ensure_ascii=False, separators=(',', ':')))
print('hus i zonen:', len(buildings), dict(counts))
print('kulisshus:', len(backdrop_buildings), '| gator:', len(roads), '(broar', sum(r['bridge'] for r in roads), ') | ytor:', Counter(s['kind'] for s in surfaces),
      '| barriärer:', len(barriers), '| skog:', len(forests), '| å-linjer:', len(waterways), '| vattenytor:', len(water_polys))
print('city.json', round((DATA / 'city.json').stat().st_size / 1e6, 2), 'MB')

#!/usr/bin/env python3
"""Platsens markytor för hela zonen: terräng, gator, trottoarer, kantsten, ytor, ån, broar.

Generalisering av torget-provets prepare_site.py, skriven för att skala (spatial index och
vektoriserad shapely i stället för loopar över alla vägar per punkt).

Regler:
- Gatuprofil = LiDAR-DTM längs mittlinjen, utjämnad (~6 m), så att diken/gropar i DTM:en
  inte syns. Gatan äger sin yta; terrängen under sänks och blandas ut 2,5 m utanför.
- Parkeringar/torg = plan anpassat mot DTM (lutning ≤ 6 %), plan äger ytan.
- Ån: vattenyta längs mittlinjen ur DTM, utjämnad och aldrig stigande nedströms;
  botten 0,7 m under ytan; stenmur där strandkanten ligger ≥ 0,8 m över vattnet.
- Broar: däck rakt mellan landningarnas gatuhöjder, minst 2 m över vattnet.

    tools/venv/bin/python v2/kvarnbyn/pipeline/site.py
"""
import json, math, time
import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, Point, box, MultiPolygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
import mapbox_earcut as earcut

from common import ZONE, BACKDROP, DATA, Y_OFFSET, raw_height, land_class

T0 = time.time()
city = json.loads((DATA / 'city.json').read_text())
zone = box(*ZONE)
work = zone.buffer(30, join_style=2)
TILE = 100.0
DRIVE = {'primary', 'secondary', 'tertiary', 'residential', 'living_street', 'unclassified', 'service',
         'primary_link', 'secondary_link', 'tertiary_link', 'trunk', 'trunk_link', 'motorway', 'motorway_link'}
SIDEWALK = {'primary', 'secondary', 'tertiary', 'residential', 'living_street', 'unclassified', 'tertiary_link'}
FOOT = {'footway', 'pedestrian', 'cycleway'}   # trappor byggs som egna steg (stairs)
TRAIL = {'path', 'track'}


def log(msg):
    print(f'[{time.time() - T0:6.1f}s] {msg}', flush=True)


def polys_of(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    return [p for p in getattr(g, 'geoms', []) if isinstance(p, Polygon) and not p.is_empty]


# ---------- profiler längs gator ----------
def profile_for(line):
    L = line.length
    n = max(2, int(math.ceil(L / 2.0)) + 1)
    s = np.linspace(0, L, n)
    pts = shapely.line_interpolate_point(line, s)
    xy = shapely.get_coordinates(pts)
    h = raw_height(xy[:, 0], xy[:, 1])
    if n >= 5:
        k = np.array([1, 4, 6, 4, 1], float); k /= k.sum()
        hp = np.pad(h, 2, mode='edge')
        h = np.convolve(hp, k, mode='valid')
    return s, h


roads = [r for r in city['roads'] if not r['tunnel']]
ground_roads, bridge_roads = [], []
for r in roads:
    line = LineString(r['line_xz'])
    if not line.intersects(work) or line.length < 0.5: continue
    (bridge_roads if r['bridge'] else ground_roads).append((r, line))
profiles = []
for r, line in ground_roads:
    s, h = profile_for(line)
    profiles.append((r, line, s, h))
log(f'{len(profiles)} gatuprofiler, {len(bridge_roads)} broar')

# ---------- ån ----------
river_lines = [LineString(w['line_xz']) for w in city['waterways']]
river_lines = [l for l in river_lines if l.intersects(work.buffer(200))]
water_polys = [Polygon(p['polygon_xz']).buffer(0) for p in city['water_polygons']]
channel = unary_union([l.buffer(w['channel_width_m'] / 2, cap_style=2, join_style=2) for l, w in zip(river_lines, city['waterways'])] + water_polys).buffer(0)
channel = channel.intersection(work)
river_prof = []
for line in river_lines:
    L = line.length; n = max(2, int(L / 2) + 1); s = np.linspace(0, L, n)
    xy = shapely.get_coordinates(shapely.line_interpolate_point(line, s))
    # vattenytan: lägsta DTM i tvärled (±3 m) ≈ vattenspegeln i laserdatan
    d = np.array([[0, 0]])
    nx = np.gradient(xy[:, 0]); nz = np.gradient(xy[:, 1]); nl = np.hypot(nx, nz) + 1e-9
    ox, oz = -nz / nl, nx / nl
    samples = np.stack([raw_height(xy[:, 0] + ox * t, xy[:, 1] + oz * t) for t in (-3, -1.5, 0, 1.5, 3)])
    h = samples.min(axis=0)
    if h[0] < h[-1]: xy, h, s = xy[::-1], h[::-1], (L - s)[::-1]; line = LineString(xy)
    k = np.ones(7) / 7; h = np.convolve(np.pad(h, 3, mode='edge'), k, mode='valid')
    h = np.minimum.accumulate(h)                     # aldrig uppför nedströms
    river_prof.append((LineString(xy), np.linspace(0, LineString(xy).length, len(h)), h))
river_tree = STRtree([p[0] for p in river_prof]) if river_prof else None


def water_level(x, z):
    x = np.atleast_1d(x); z = np.atleast_1d(z)
    pts = shapely.points(x, z)
    idx = river_tree.nearest(pts)
    out = np.empty(len(x))
    for k in np.unique(idx):
        sel = idx == k; line, s, h = river_prof[k]
        out[sel] = np.interp(shapely.line_locate_point(line, pts[sel]), s, h)
    return out


# ---------- ytor (plan) ----------
surfaces = []
for s in city['surfaces']:
    poly = Polygon(s['polygon_xz']).buffer(0)
    if poly.is_empty or not poly.intersects(work): continue
    q = np.array(poly.exterior.coords)
    inner = shapely.get_coordinates(shapely.points(q))
    ys = raw_height(q[:, 0], q[:, 1])
    a, b, c = np.linalg.lstsq(np.column_stack([q[:, 0], q[:, 1], np.ones(len(q))]), ys, rcond=None)[0]
    lim = 0.015 if s['kind'] == 'pitch' else 0.06
    sl = math.hypot(a, b)
    if sl > lim:
        a, b = a * lim / sl, b * lim / sl
        c = float(np.median(ys - a * q[:, 0] - b * q[:, 1]))
    surfaces.append((s, poly, (a, b, c)))
surf_tree = STRtree([p for _, p, _ in surfaces]) if surfaces else None

# ---------- polygoner för gator ----------
buildings = unary_union([Polygon(b['footprint_xz']).buffer(0) for b in city['buildings']])
drive_lines = [(r, line) for r, line, _, _ in profiles if r['kind'] in DRIVE]
asphalt = unary_union([line.buffer(r['width_m'] / 2, cap_style=2, join_style=2) for r, line in drive_lines])
def has_sidewalk(r):
    tag = r.get('sidewalk', '')
    if tag in ('no', 'none', 'separate'): return False
    if tag in ('both', 'left', 'right', 'yes'): return True
    return r['kind'] in ('primary', 'secondary', 'tertiary', 'tertiary_link')   # villagator utan tagg: ingen trottoar
side = unary_union([line.buffer(r['width_m'] / 2 + 1.6, cap_style=2, join_style=2) for r, line in drive_lines if has_sidewalk(r)])
footw = unary_union([line.buffer(r['width_m'] / 2, cap_style=1, join_style=1) for r, line, _, _ in profiles if r['kind'] in FOOT])
trail = unary_union([line.buffer(r['width_m'] / 2, cap_style=1, join_style=1) for r, line, _, _ in profiles if r['kind'] in TRAIL])
surf_union = unary_union([p for _, p, _ in surfaces]) if surfaces else Polygon()
parking_u = unary_union([p for s, p, _ in surfaces if s['kind'] == 'parking']) if surfaces else Polygon()
square_u = unary_union([p for s, p, _ in surfaces if s['kind'] == 'square']) if surfaces else Polygon()
other_u = unary_union([p for s, p, _ in surfaces if s['kind'] in ('pitch', 'playground')]) if surfaces else Polygon()
bridge_clear = unary_union([LineString(r['line_xz']).buffer(r['width_m'] / 2 + 0.3, cap_style=2) for r, _ in bridge_roads]) if bridge_roads else Polygon()
cut = buildings.buffer(0.05).union(channel.buffer(0.05)).union(bridge_clear)
asphalt = asphalt.union(parking_u).difference(square_u).difference(other_u).difference(cut).intersection(work)
centre = Point(0, 0).buffer(140)                       # gatsten kring Gamla torget, annars asfalterad gångbana
paving_all = side.union(footw).union(square_u).difference(asphalt).difference(other_u).difference(cut).intersection(work)
paving = paving_all.intersection(centre.union(square_u.buffer(2)))
walkway = paving_all.difference(paving)
trail = trail.difference(asphalt).difference(paving_all).difference(other_u).difference(cut).intersection(work)
pitch_u = unary_union([p for s, p, _ in surfaces if s['kind'] == 'pitch']).difference(cut).intersection(work) if surfaces else Polygon()
play_u = unary_union([p for s, p, _ in surfaces if s['kind'] == 'playground']).difference(cut).intersection(work) if surfaces else Polygon()
urban = unary_union([asphalt, paving_all, pitch_u, play_u])
log(f'ytor: asfalt {asphalt.area:.0f} m², gatsten {paving.area:.0f} m², gångbana {walkway.area:.0f} m², stig {trail.area:.0f} m², å {channel.area:.0f} m²')

# ---------- höjd för en byggd yta i punkter ----------
road_lines = [line for _, line, _, _ in profiles]
road_tree = STRtree(road_lines)


def surface_height(x, z):
    """Höjd (rå m ö.h.) för gator/ytor i punkterna: plan om i en yta, annars närmaste gatuprofil."""
    x = np.atleast_1d(np.asarray(x, float)); z = np.atleast_1d(np.asarray(z, float))
    pts = shapely.points(x, z)
    out = np.full(len(x), np.nan)
    if surfaces:
        pi, si = surf_tree.query(pts, predicate='within')
        for k in np.unique(si):
            sel = pi[si == k]; a, b, c = surfaces[k][2]
            out[sel] = a * x[sel] + b * z[sel] + c
    rest = np.isnan(out)
    if rest.any():
        idx = road_tree.nearest(pts[rest]); ri = np.nonzero(rest)[0]
        for k in np.unique(idx):
            sel = ri[idx == k]; _, line, s, h = profiles[k]
            out[sel] = np.interp(shapely.line_locate_point(line, pts[sel]), s, h)
    return out


def distance_to(geom, x, z):
    return shapely.distance(geom, shapely.points(x, z))


# ---------- terräng ----------
def terrain_grid(bounds, step, conform):
    x0, z0, x1, z1 = bounds
    xs = np.arange(math.floor(x0 / step) * step, x1 + step, step)
    zs = np.arange(math.floor(z0 / step) * step, z1 + step, step)
    X, Z = np.meshgrid(xs, zs)
    H = raw_height(X.ravel(), Z.ravel())
    if conform:
        xf, zf = X.ravel(), Z.ravel()
        # gator/ytor: terrängen under ytan, 2,5 m utblandning
        d = distance_to(urban, xf, zf)
        near = d < 2.5
        if near.any():
            sh = surface_height(xf[near], zf[near])
            t = np.clip(1 - d[near] / 2.5, 0, 1)
            inside = d[near] <= 0
            target = np.where(inside, sh - 0.12, sh)
            H[near] = H[near] * (1 - t) + target * t
        # ån: botten under vattenytan, 1,5 m släntkant
        dc = distance_to(channel, xf, zf)
        inch = dc < 1.5
        if inch.any() and river_prof:
            wl = water_level(xf[inch], zf[inch])
            bed = wl - 0.7
            t = np.clip(1 - dc[inch] / 1.5, 0, 1)
            H[inch] = np.where(dc[inch] <= 0, np.minimum(H[inch], bed), H[inch] * (1 - t) + np.minimum(H[inch], wl + 0.25) * t)
    cls = land_class(X.ravel(), Z.ravel())
    if conform:
        g = cls.reshape(X.shape[0], X.shape[1], 4)
        k = np.array([1, 4, 6, 4, 1], float); k /= k.sum()
        for axis in (0, 1):
            g = np.apply_along_axis(lambda v: np.convolve(np.pad(v, 2, mode='edge'), k, mode='valid'), axis, g)
        cls = g.reshape(-1, 4)
    return dict(x0=float(xs[0]), z0=float(zs[0]), step=step, nx=len(xs), nz=len(zs),
                heights=[round(float(v) - Y_OFFSET, 3) for v in H],
                land=[[round(float(a), 2) for a in c] for c in cls] if conform else None)


tb = work.bounds
fine = terrain_grid(tb, 2.0, True)
log(f'terräng zon: {fine["nx"]}×{fine["nz"]} punkter à 2 m')
coarse = terrain_grid(BACKDROP, 8.0, False)
log(f'terräng kuliss: {coarse["nx"]}×{coarse["nz"]} punkter à 8 m')

# ---------- trianglar för byggda ytor, per 100 m-ruta ----------
def triangulate(geom, height_fn, lift):
    """Polygoner → trianglar med höjd, klippta i 2 m-celler så att ytan följer profilen."""
    out = {}
    for poly in polys_of(geom):
        minx, minz, maxx, maxz = poly.bounds
        gx = np.arange(math.floor(minx / 2) * 2, maxx, 2.0); gz = np.arange(math.floor(minz / 2) * 2, maxz, 2.0)
        if len(gx) == 0 or len(gz) == 0: continue
        GX, GZ = np.meshgrid(gx, gz)
        cells = shapely.box(GX.ravel(), GZ.ravel(), GX.ravel() + 2, GZ.ravel() + 2)
        hit = shapely.intersects(cells, poly)
        pieces = shapely.intersection(cells[hit], poly)
        for piece in pieces:
            for pp in polys_of(piece):
                if pp.area < 1e-4: continue
                rings = [np.array(pp.exterior.coords)[:-1]] + [np.array(r.coords)[:-1] for r in pp.interiors]
                verts = np.vstack(rings)
                ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
                tri = earcut.triangulate_float64(verts, ends).reshape(-1, 3)
                if len(tri) == 0: continue
                y = height_fn(verts[:, 0], verts[:, 1]) + lift - Y_OFFSET
                cx, cz = verts[:, 0].mean(), verts[:, 1].mean()
                key = '%d_%d' % (math.floor(cx / TILE), math.floor(cz / TILE))
                bucket = out.setdefault(key, [])
                for a, b, c in tri:
                    bucket.append([[round(float(verts[i, 0]), 3), round(float(y[i]), 3), round(float(verts[i, 1]), 3)] for i in (a, b, c)])
    return out


def plane_height(x, z):
    return surface_height(x, z)


meshes = {
    'asphalt': triangulate(asphalt, surface_height, 0.03),
    'paving': triangulate(paving, surface_height, 0.13),
    'walkway': triangulate(walkway, surface_height, 0.12),
    'trail': triangulate(trail, lambda x, z: raw_height(x, z), 0.05),
    'pitch': triangulate(pitch_u, surface_height, 0.05),
    'playground': triangulate(play_u, surface_height, 0.05),
}
if river_prof:
    meshes['water'] = triangulate(channel, lambda x, z: water_level(x, z), 0.0)
log('trianglar: ' + ', '.join(f'{k} {sum(len(v) for v in m.values())}' for k, m in meshes.items()))

# ---------- kantsten mellan asfalt och trottoar, fundament runt upphöjda ytor ----------
kerbs = []
pave_b = paving_all.buffer(0.3)
for poly in polys_of(asphalt):
    for ring in [poly.exterior] + list(poly.interiors):
        seg = ring.segmentize(3.0); c = np.array(seg.coords)
        a, b = c[:-1], c[1:]
        L = np.hypot(*(b - a).T)
        mid = (a + b) / 2
        ok = (L > 0.2) & shapely.contains_xy(pave_b, mid[:, 0], mid[:, 1])
        if not ok.any(): continue
        ha = surface_height(a[ok, 0], a[ok, 1]); hb = surface_height(b[ok, 0], b[ok, 1])
        for (p, q, y1, y2) in zip(a[ok], b[ok], ha, hb):
            kerbs.append([round(float(p[0]), 3), round(float(y1 + 0.13 - Y_OFFSET), 3), round(float(p[1]), 3),
                          round(float(q[0]), 3), round(float(y2 + 0.13 - Y_OFFSET), 3), round(float(q[1]), 3)])
log(f'kantsten: {len(kerbs)} bitar')

# ---------- åmurar ----------
river_walls = []
if river_prof:
    for poly in polys_of(channel):
        for ring in [poly.exterior] + list(poly.interiors):
            seg = ring.segmentize(2.5); c = np.array(seg.coords)
            a, b = c[:-1], c[1:]; mid = (a + b) / 2
            inside_zone = shapely.contains_xy(zone.buffer(10), mid[:, 0], mid[:, 1])
            if not inside_zone.any(): continue
            wl = water_level(mid[:, 0], mid[:, 1])
            d = b - a; L = np.hypot(*d.T) + 1e-9; nrm = np.column_stack([-d[:, 1], d[:, 0]]) / L[:, None]
            # utåt = bort från vattnet
            probe = mid + nrm * 1.2
            flip = shapely.contains_xy(channel, probe[:, 0], probe[:, 1])
            nrm[flip] *= -1
            bank = raw_height(mid[:, 0] + nrm[:, 0] * 2.0, mid[:, 1] + nrm[:, 1] * 2.0)
            if len(profiles):
                road_near = distance_to(urban, mid[:, 0] + nrm[:, 0] * 2, mid[:, 1] + nrm[:, 1] * 2) < 1.0
                if road_near.any():
                    bank[road_near] = np.maximum(bank[road_near], surface_height(mid[road_near, 0] + nrm[road_near, 0] * 2, mid[road_near, 1] + nrm[road_near, 1] * 2))
            for k in np.nonzero(inside_zone & (bank - wl > 0.8) & ~shapely.contains_xy(bridge_clear.buffer(1.0), mid[:, 0], mid[:, 1]))[0]:
                river_walls.append(dict(a=[round(float(a[k, 0]), 3), round(float(a[k, 1]), 3)], b=[round(float(b[k, 0]), 3), round(float(b[k, 1]), 3)],
                                        top_y=round(float(bank[k] + 0.12 - Y_OFFSET), 3), bottom_y=round(float(wl[k] - 1.0 - Y_OFFSET), 3),
                                        out=[round(float(nrm[k, 0]), 3), round(float(nrm[k, 1]), 3)]))
log(f'åmurar: {len(river_walls)} segment')

# ---------- broar ----------
bridges = []
for r, line in bridge_roads:
    if not line.intersects(zone.buffer(10)): continue
    c = np.array(line.coords)
    ends = []
    for p in (c[0], c[-1]):
        near = [(pr, ln) for pr, ln in zip(profiles, road_lines) if ln.distance(Point(p)) < 1.0]
        h = None
        if near:
            h = float(surface_height([p[0]], [p[1]])[0])
        if h is None: h = float(raw_height([p[0]], [p[1]])[0])
        ends.append(h)
    L = line.length; n = max(2, int(L / 2) + 1); s = np.linspace(0, L, n)
    xy = shapely.get_coordinates(shapely.line_interpolate_point(line, s))
    deck = ends[0] + (ends[1] - ends[0]) * s / max(L, 1e-6)
    if river_prof and line.intersects(channel):
        wl = water_level(xy[:, 0], xy[:, 1]); inch = shapely.contains_xy(channel, xy[:, 0], xy[:, 1])
        if inch.any(): deck = np.maximum(deck, np.where(inch, wl + 2.0, -1e9))
        k = np.ones(5) / 5; deck = np.convolve(np.pad(deck, 2, mode='edge'), k, mode='valid')
        deck[0], deck[-1] = ends
    ground = raw_height(xy[:, 0], xy[:, 1])
    bridges.append(dict(id=r['id'], name=r['name'], kind=r['kind'], width_m=max(r['width_m'], 2.4 if r['kind'] in FOOT | TRAIL else r['width_m']),
                        points=[[round(float(x), 3), round(float(y - Y_OFFSET), 3), round(float(z), 3)] for (x, z), y in zip(xy, deck)],
                        ground_y=[round(float(g - Y_OFFSET), 3) for g in ground]))
log(f'broar i zonen: {len(bridges)}')

# ---------- markhöjd för möbler/lyktor (enkel tabell ur gatuprofilerna) ----------
lamps = []
for r, line, s, h in profiles:
    if r['kind'] not in SIDEWALK or not line.intersects(zone): continue
    for d in np.arange(12, line.length - 6, 32.0):
        p = line.interpolate(d); q = line.interpolate(min(line.length, d + 0.5))
        dx, dz = q.x - p.x, q.y - p.y; ln = math.hypot(dx, dz) or 1
        ox, oz = -dz / ln, dx / ln
        side_ = 1 if int(d / 32) % 2 == 0 else -1
        x = p.x + ox * side_ * (r['width_m'] / 2 + 0.9); z = p.y + oz * side_ * (r['width_m'] / 2 + 0.9)
        if not zone.contains(Point(x, z)) or buildings.buffer(0.6).contains(Point(x, z)) or channel.buffer(0.5).contains(Point(x, z)): continue
        y = float(surface_height([x], [z])[0]) + 0.13
        lamps.append([round(x, 3), round(y - Y_OFFSET, 3), round(z, 3), round(-ox * side_, 3), round(-oz * side_, 3)])
log(f'gatlyktor: {len(lamps)}')

# ---------- trappor ----------
stairs = []
for r, line, s_, h_ in profiles:
    if r['kind'] != 'steps' or not line.intersects(zone.buffer(5)): continue
    L = line.length; n = max(2, int(L / 0.35) + 1); ss = np.linspace(0, L, n)
    xy = shapely.get_coordinates(shapely.line_interpolate_point(line, ss))
    hh = np.interp(ss, s_, h_)
    stairs.append(dict(id=r['id'], width_m=max(1.6, r['width_m']), points=[[round(float(x), 3), round(float(y - Y_OFFSET), 3), round(float(z), 3)] for (x, z), y in zip(xy, hh)]))
log(f'trappor: {len(stairs)} st, {sum(len(t["points"]) for t in stairs)} provpunkter')

# ---------- träd: skogsytor ur klasskartan + OSM-skog, jittrat rutnät ----------
rng = np.random.default_rng(29)
gx = np.arange(ZONE[0] - 20, ZONE[2] + 20, 8.5); gz = np.arange(ZONE[1] - 20, ZONE[3] + 20, 8.5)
GX, GZ = np.meshgrid(gx, gz)
TX = GX.ravel() + rng.uniform(-3.5, 3.5, GX.size); TZ = GZ.ravel() + rng.uniform(-3.5, 3.5, GX.size)
forest_w = land_class(TX, TZ)[:, 2]
osm_forest = unary_union([Polygon(f['polygon_xz']).buffer(0) for f in city['forests'] if len(f['polygon_xz']) >= 3])
in_osm = shapely.contains_xy(osm_forest, TX, TZ) if not osm_forest.is_empty else np.zeros(len(TX), bool)
keep = (forest_w > 0.55) | (in_osm & (forest_w > 0.3))
blocked = unary_union([urban, channel, buildings.buffer(2.0), bridge_clear]).buffer(2.5)
keep &= ~shapely.contains_xy(blocked, TX, TZ)
idx = np.nonzero(keep)[0]
if len(idx) > 1800: idx = rng.choice(idx, 1800, replace=False)
TY = raw_height(TX[idx], TZ[idx]) - Y_OFFSET
trees = [[round(float(x), 2), round(float(y), 2), round(float(z), 2), round(float(rng.uniform(1.05, 1.85)), 2), int(rng.integers(0, 3)), round(float(rng.uniform(0, 6.283)), 2)]
         for x, y, z in zip(TX[idx], TY, TZ[idx])]
log(f'träd: {len(trees)}')

site = dict(meta=dict(note='Markytor för Fas A, genererade av site.py. y = rå höjd − 18 m.', y_offset_m=Y_OFFSET, tile_m=TILE,
                      zone=list(ZONE), backdrop=list(BACKDROP)),
            terrain=fine, terrain_backdrop=coarse, meshes=meshes, kerbs=kerbs, river_walls=river_walls, bridges=bridges,
            lamps=lamps, trees=trees, stairs=stairs, surfaces=[dict(id=s['id'], kind=s['kind'], plane_raw=[round(float(v), 6) for v in pl]) for s, _, pl in surfaces])
(DATA / 'site.json').write_text(json.dumps(site, separators=(',', ':')))
log(f'site.json {((DATA / "site.json").stat().st_size / 1e6):.1f} MB')

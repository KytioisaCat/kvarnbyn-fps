"""Byggda plana ytor (VISION.md §3): torg, parkeringar, planer, lekplatser ur OSM-polygoner.
Varje flat får ett PLAN (minsta kvadrat mot LiDAR-marken inne i polygonen, med lutningsgräns
per typ) och blir ett eget objekt: egen mesh, kantsten mot omgivande mark, terrängen
konformeras till planet, och vägar som går genom ytan binds till planet i profil-lösaren.
"En parkering måste vara platt." Plandetektion i LiDAR (ytor OSM saknar) kommer senare."""
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString

from .common import load_osm

# typ → (material, maxlutning, kantstenshöjd)
KINDS = {
    'parking':    ('asphalt', 0.06, 0.12),
    'square':     ('sett', 0.04, 0.12),
    'pitch':      ('pitch', 0.02, 0.0),
    'playground': ('playground', 0.03, 0.08),
}


class Flat:
    def __init__(self, way, poly, kind, name):
        self.way = way; self.poly = poly; self.kind = kind; self.name = name
        self.material, self.maxgrade, self.kerb = KINDS[kind]
        self.plane = None          # (a, b, c): h = a·x + b·z + c  (spelhöjd)
        self.line = LineString(poly.exterior.coords)   # för avstånd i ägarlogiken
        self.cls = 'flat'; self.width = 5.0; self.bridge = False; self.tunnel = False
        self.stats = {}

    def h_at_xy(self, x, z):
        a, b, c = self.plane
        return a * np.asarray(x) + b * np.asarray(z) + c


def kind_of(t):
    if t.get('amenity') == 'parking' and t.get('parking') not in ('multi-storey', 'underground', 'rooftop'): return 'parking'
    if (t.get('highway') == 'pedestrian' and t.get('area') == 'yes') or t.get('place') == 'square': return 'square'
    if t.get('leisure') == 'pitch': return 'pitch'
    if t.get('leisure') == 'playground': return 'playground'
    return None


def load(area, nodes=None, ways=None):
    if nodes is None: nodes, ways = load_osm()
    xmin, xmax, zmin, zmax = area
    out = []
    for w in ways:
        t = w.get('tags', {})
        k = kind_of(t)
        if not k or w['nodes'][0] != w['nodes'][-1]: continue
        pts = [nodes[n] for n in w['nodes'] if n in nodes]
        if len(pts) < 4: continue
        poly = Polygon(pts)
        if not poly.is_valid: poly = poly.buffer(0)
        if poly.is_empty or poly.area < 30: continue
        cx, cz = poly.centroid.x, poly.centroid.y
        if not (xmin <= cx <= xmax and zmin <= cz <= zmax): continue
        out.append(Flat(w['id'], poly, k, t.get('name', '')))
    return out


def fit_planes(flats, ground, road_model_lines=None, log=print):
    """Plan per flat: minsta kvadrat mot markceller (1 m) inne i polygonen, robust (kasta
    avvikare > 0,5 m två varv), sedan lutningen klämd till typens max (riktningen behålls)."""
    for f in flats:
        minx, minz, maxx, maxz = f.poly.bounds
        xs, zs = np.meshgrid(np.arange(np.floor(minx), np.ceil(maxx) + 1), np.arange(np.floor(minz), np.ceil(maxz) + 1))
        X = xs.ravel(); Z = zs.ravel()
        inside = shapely.contains_xy(f.poly, X, Z)
        X, Z = X[inside], Z[inside]
        if len(X) < 6:
            cx, cz = f.poly.centroid.x, f.poly.centroid.y
            X = np.array([cx]); Z = np.array([cz])
        G = ground.at(X, Z)
        A = np.column_stack([X, Z, np.ones_like(X)])
        w = np.ones_like(G)
        for _ in range(3):
            sol, *_ = np.linalg.lstsq(A * w[:, None], G * w, rcond=None)
            res = G - A @ sol
            w = (np.abs(res) < 0.5).astype(float) + 1e-3
        a, b, c = sol
        slope = np.hypot(a, b)
        clamped = False
        if slope > f.maxgrade:
            k = f.maxgrade / slope
            a2, b2 = a * k, b * k
            # behåll medelhöjden i polygonens tyngdpunkt
            cx, cz = f.poly.centroid.x, f.poly.centroid.y
            c = (a * cx + b * cz + c) - (a2 * cx + b2 * cz)
            a, b = a2, b2; clamped = True
        f.plane = (a, b, c)
        res = G - (a * X + b * Z + c)
        f.stats = {'cells': int(len(X)), 'slope': float(np.hypot(a, b)), 'clamped': clamped,
                   'dev_p50': float(np.percentile(np.abs(res), 50)), 'dev_max': float(np.abs(res).max()),
                   'lidar_range': float(G.max() - G.min())}
        log(f'  flat {f.kind:10s} {f.name[:18]:18s} way {f.way}: {f.stats["cells"]} celler, LiDAR-spann {f.stats["lidar_range"]:.2f} m → '
            f'plan lutning {f.stats["slope"]*100:.1f} %{" (klämd)" if clamped else ""}, avvikelse p50 {f.stats["dev_p50"]:.2f} max {f.stats["dev_max"]:.2f} m')
    return flats

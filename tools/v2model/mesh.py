"""Geometri ur nät + löst profil: vägband per kant (exakta tvärsnitt), korsningspolygoner
(shapely-komplement, earcut), kantsten runt all asfalt, brodäck med sidor/undersida, räcken,
pelare. Allt i spelkoordinater (x, y=höjd, z). Trianglar CCW sedda uppifrån för ytor som vänder
uppåt."""
import numpy as np
import mapbox_earcut as earcut
from shapely.geometry import Polygon, MultiPolygon, LineString, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree

KERB_H = 0.12
KERB_W = 0.30
DECK_T = 1.2
RAIL_H = 1.1
PIER_SPACING = 24.0
PIER_MIN_H = 2.5


class MeshBuf:
    """Samlar trianglar per material."""

    def __init__(self):
        self.parts = {}   # material → (positions list, indices list)

    def add_tri(self, mat, a, b, c):
        pos, idx = self.parts.setdefault(mat, ([], []))
        base = len(pos)
        pos.extend([a, b, c]); idx.extend([base, base + 1, base + 2])

    def add_quad(self, mat, a, b, c, d):
        """a b c d i ordning runt kvadraten; två trianglar (a,b,c) (a,c,d)."""
        self.add_tri(mat, a, b, c); self.add_tri(mat, a, c, d)

    def add_polygon_top(self, mat, poly, height_fn):
        """Triangulera en shapely-polygon (med hål) som uppåtvänd yta."""
        if poly.is_empty: return
        if isinstance(poly, MultiPolygon):
            for p in poly.geoms: self.add_polygon_top(mat, p, height_fn)
            return
        rings = [np.array(poly.exterior.coords)[:-1]] + [np.array(r.coords)[:-1] for r in poly.interiors]
        rings = [r for r in rings if len(r) >= 3]
        if not rings: return
        verts = np.vstack(rings)
        ring_ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
        tri = earcut.triangulate_float64(verts, ring_ends)
        ys = height_fn(verts[:, 0], verts[:, 1])
        P = np.column_stack([verts[:, 0], ys, verts[:, 1]])
        pos, idx = self.parts.setdefault(mat, ([], []))
        base = len(pos)
        pos.extend(map(tuple, P))
        # earcut ger CW i (x, z)-planet med z nedåt på skärmen = CCW uppifrån i vår konvention? kontrollera via signerad area
        tri = tri.reshape(-1, 3)
        for t in tri:
            a, b, c = P[t[0]], P[t[1]], P[t[2]]
            cross = (b[0] - a[0]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[0] - a[0])
            if cross > 0:     # medurs sett uppifrån (x höger, z "ner") → vänd
                idx.extend([base + t[0], base + t[2], base + t[1]])
            else:
                idx.extend([base + t[0], base + t[1], base + t[2]])

    def add_wall(self, mat, ring, y_top_fn, y_bot_fn, outward=True):
        """Vertikal vägg längs en ring (lista av (x,z)); y_top/y_bot funktioner av (x,z)."""
        ring = np.asarray(ring)
        for (x1, z1), (x2, z2) in zip(ring[:-1], ring[1:]):
            t1, t2 = y_top_fn(x1, z1), y_top_fn(x2, z2)
            b1, b2 = y_bot_fn(x1, z1), y_bot_fn(x2, z2)
            a, b, c, d = (x1, t1, z1), (x2, t2, z2), (x2, b2, z2), (x1, b1, z1)
            if outward: self.add_quad(mat, a, b, c, d)
            else: self.add_quad(mat, a, d, c, b)

    def arrays(self):
        out = {}
        for mat, (pos, idx) in self.parts.items():
            out[mat] = (np.array(pos, dtype=np.float32), np.array(idx, dtype=np.uint32))
        return out


def strip_polygon(xy, w):
    """Band kring en polylinje med halvbredd w/2: vänster/höger punkter per vertex (miter)."""
    xy = np.asarray(xy, dtype=np.float64)
    d = np.diff(xy, axis=0)
    L = np.hypot(d[:, 0], d[:, 1]); L[L == 0] = 1e-9
    t = d / L[:, None]
    nrm = np.column_stack([-t[:, 1], t[:, 0]])          # vänster normal
    N = np.zeros_like(xy)
    N[0] = nrm[0]; N[-1] = nrm[-1]
    for i in range(1, len(xy) - 1):
        m = nrm[i - 1] + nrm[i]
        ml = np.hypot(*m)
        if ml < 1e-6: N[i] = nrm[i]; continue
        m /= ml
        scale = 1.0 / max(0.5, np.dot(m, nrm[i]))         # miter, begränsad
        N[i] = m * scale
    left = xy + N * (w / 2); right = xy - N * (w / 2)
    return left, right


class RoadModel:
    def __init__(self, net, h, ground, flats=()):
        self.net = net; self.h = h; self.ground = ground; self.flats = list(flats)
        self.edges_by_layer = {}
        for e in net.edges:
            if e.tunnel: continue
            self.edges_by_layer.setdefault('bridge' if e.bridge else 'ground', []).append(e)
        self.trees = {k: STRtree([e.line for e in v]) for k, v in self.edges_by_layer.items()}

    def height_at(self, xs, zs, layer='ground'):
        """Profilhöjd i (x,z). Ägarpolygonen (vägband eller korsning) som ligger närmast punkten
        avgör vilken kant som gäller — inte närmaste centrumlinje (en gångstig 2 m från en
        gata får annars äga gatans kant). Höjden interpoleras längs ägarkanten."""
        xs = np.atleast_1d(np.asarray(xs, dtype=np.float64)); zs = np.atleast_1d(np.asarray(zs, dtype=np.float64))
        pts = [Point(x, z) for x, z in zip(xs, zs)]
        out = np.empty(len(pts))
        owners = getattr(self, 'owners', {}).get(layer)
        if owners is None:                        # före build(): fall tillbaka på centrumlinjer
            edges = self.edges_by_layer[layer]; tree = self.trees[layer]
            idx = tree.nearest(pts)
            for k, (p, j) in enumerate(zip(pts, idx)):
                e = edges[j]; out[k] = np.interp(e.line.project(p), e.s, self.h[e.vidx])
            return out
        polys, owner_edges, tree = owners
        idx = tree.nearest(pts)
        PEDC = ('footway', 'path', 'steps', 'cycleway', 'track', 'pedestrian')
        for k, (p, j) in enumerate(zip(pts, idx)):
            # innehåller flera polygoner punkten (överlapp): körväg vinner över gångstig, sedan bredast
            hits = [jj for jj in tree.query(p, predicate='intersects')]
            if len(hits) > 1:
                def prio(jj):
                    es_ = owner_edges[jj]; e0 = es_[0]
                    return (0 if any(x.cls not in PEDC for x in es_) else 1, -max(x.width for x in es_))
                j = min(hits, key=prio)
            cands = owner_edges[j]
            if len(cands) == 1:
                e = cands[0]
            else:                                 # korsning: närmaste av de anslutande kanterna
                e = min(cands, key=lambda ee: ee.line.distance(p))
            out[k] = self._h_of(e, p)
        return out

    def _h_of(self, e, p):
        if hasattr(e, 'plane'): return float(e.h_at_xy(p.x, p.y))
        return float(np.interp(e.line.project(p), e.s, self.h[e.vidx]))

    def _set_owners(self, layer, polys, owner_edges):
        self.owners = getattr(self, 'owners', {})
        self.owners[layer] = (polys, owner_edges, STRtree(polys))

    def edge_strip_poly(self, e, trim):
        """Bandpolygon för kanten, trimmad `trim[node]` meter från vardera ändnod."""
        s0 = min(trim.get(e.nodes[0], 0.0), e.s[-1] * 0.45)
        s1 = min(trim.get(e.nodes[1], 0.0), e.s[-1] * 0.45)
        if e.s[-1] - s0 - s1 < 1.0:
            return None, None
        ss = np.concatenate([[s0], e.s[(e.s > s0) & (e.s < e.s[-1] - s1)], [e.s[-1] - s1]])
        xy = np.column_stack([np.interp(ss, e.s, e.xy[:, 0]), np.interp(ss, e.s, e.xy[:, 1])])
        hh = np.interp(ss, e.s, self.h[e.vidx])
        L, R = strip_polygon(xy, e.width)
        poly = Polygon(np.vstack([L, R[::-1]]))
        if not poly.is_valid: poly = poly.buffer(0)
        return (xy, hh, L, R), poly

    def build(self, log=print):
        net = self.net
        mb = MeshBuf()
        # trimavstånd per nod = halva bredaste anslutande kanten + 0,5
        incident = {}
        for e in net.edges:
            for nid in e.nodes: incident.setdefault(nid, []).append(e)
        trim = {nid: (max(x.width for x in es) / 2 + 0.5 if len(es) > 1 else 0.0) for nid, es in incident.items()}
        strips = {}
        polys_by_layer = {'ground': [], 'bridge': []}
        flat_union = unary_union([f.poly for f in self.flats]).buffer(0) if self.flats else Polygon()
        for e in net.edges:
            if e.tunnel: continue                      # under mark: ritas inte (M3: underfart)
            data, poly = self.edge_strip_poly(e, trim)
            if data is None: continue
            if not e.bridge and not flat_union.is_empty and poly.intersection(flat_union).area > 0.8 * poly.area:
                e.in_flat = True                       # ytan (torget, p-platsen) äger vägen: inget eget band
                continue
            strips[e.id] = (data, poly)
            layer = 'bridge' if e.bridge else 'ground'
            if not (e.steplike or e.stair or e.cls == 'steps'):   # trappor är strukturer PÅ marken: ingen konformering/kantsten
                polys_by_layer[layer].append(poly)
            xy, hh, L, R = data
            base_mat = 'deck' if e.bridge else ('steps' if (e.steplike or e.stair) else ('path' if e.cls in ('footway', 'path', 'cycleway', 'track') else 'asphalt'))
            for i in range(len(xy) - 1):
                mat = base_mat
                if e.stair_seg is not None and not e.bridge:
                    mat = 'steps' if _seg_is_stair(e, xy[i], xy[i + 1]) else base_mat
                a = (L[i][0], hh[i], L[i][1]); b = (R[i][0], hh[i], R[i][1])
                c = (R[i + 1][0], hh[i + 1], R[i + 1][1]); d = (L[i + 1][0], hh[i + 1], L[i + 1][1])
                # CCW uppifrån: a(L_i) → d(L_i+1) → c(R_i+1) → b(R_i)?  kontrollera med kryssprodukt
                mb.add_quad(mat, a, b, c, d) if _ccw_up(a, b, c) else mb.add_quad(mat, a, d, c, b)
        owner_polys = {'ground': [], 'bridge': []}; owner_edges = {'ground': [], 'bridge': []}
        for f in self.flats:                               # byggda plana ytor: egna ägare med plan
            owner_polys['ground'].append(f.poly); owner_edges['ground'].append([f])
            polys_by_layer['ground'].append(f.poly)
            mb.add_polygon_top(f.material, f.poly, lambda xs, zs, f=f: f.h_at_xy(xs, zs))
        for e in net.edges:
            if e.id in strips and not e.tunnel:
                L_ = 'bridge' if e.bridge else 'ground'
                owner_polys[L_].append(strips[e.id][1]); owner_edges[L_].append([e])
        # korsningar: (union av anslutande kanters fulla band inom radie) − (trimmade band)
        junction_polys = {'ground': [], 'bridge': []}
        pending_junctions = []
        for nid, es in incident.items():
            es = [e for e in es if not e.tunnel and not getattr(e, 'in_flat', False)]
            if len(es) < 2: continue
            layer = 'bridge' if any(e.bridge for e in es) else 'ground'
            r = trim[nid] + max(e.width for e in es) / 2 + 1.0
            x, z = net.V[net.node_vidx[nid]]
            disk = Point(x, z).buffer(r, 16)
            full = unary_union([e.line.buffer(e.width / 2, cap_style=2, join_style=2, mitre_limit=2.0) for e in es])
            junc = full.intersection(disk)
            cut = unary_union([strips[e.id][1] for e in es if e.id in strips])
            junc = junc.difference(cut).buffer(0)
            if junc.is_empty: continue
            junction_polys[layer].append(junc)
            polys_by_layer[layer].append(junc)
            owner_polys[layer].append(junc); owner_edges[layer].append([e for e in es if e.id in strips] or es)
            pending_junctions.append((layer, junc, nid))
        for L_ in ('ground', 'bridge'):
            if owner_polys[L_]: self._set_owners(L_, owner_polys[L_], owner_edges[L_])
        for layer, junc, _nid in pending_junctions:
            mat = 'deck' if layer == 'bridge' else 'asphalt'
            mb.add_polygon_top(mat, junc, lambda xs, zs, L=layer: self.height_at(xs, zs, L))
        # kantsten runt all markasfalt
        road_union = unary_union(polys_by_layer['ground']).buffer(0)
        self.road_union = road_union
        rings = []
        for p in (road_union.geoms if isinstance(road_union, MultiPolygon) else [road_union]):
            rings.append(np.array(p.exterior.coords))
            rings += [np.array(r.coords) for r in p.interiors]
        hfn = lambda x, z: float(self.height_at([x], [z], 'ground')[0])
        kerb_outer = road_union.buffer(KERB_W, join_style=2, mitre_limit=2.0)
        kerb_band = kerb_outer.difference(road_union).buffer(0)
        mb.add_polygon_top('kerb', kerb_band, lambda xs, zs: self.height_at(xs, zs, 'ground') + KERB_H)
        for ring in rings:
            mb.add_wall('kerb', ring, lambda x, z: hfn(x, z) + KERB_H, hfn, outward=True)
        # ytterkjol: döljer att 1 m-terrängen inte kan möta kantstenskrönet exakt
        outer_rings = []
        for p in (kerb_outer.geoms if isinstance(kerb_outer, MultiPolygon) else [kerb_outer]):
            outer_rings.append(np.array(p.exterior.coords)); outer_rings += [np.array(r.coords) for r in p.interiors]
        for ring in outer_rings:
            mb.add_wall('kerb', ring, lambda x, z: hfn(x, z) + KERB_H, lambda x, z: hfn(x, z) - 0.55, outward=True)
        self.kerb_outer = kerb_outer
        # broar: däck-kropp (sidor + undersida) och räcken PER SAMMANHÄNGANDE BROGRUPP —
        # annars spänner sidorna mellan Mölndals bro och gångbron bredvid på annan höjd
        parent = {}
        def find(x):
            while parent.setdefault(x, x) != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        bridge_edges = [e for e in net.edges if e.bridge and e.id in strips]
        for e in bridge_edges:
            find(('e', e.id))
            for nid in e.nodes: parent[find(('n', nid))] = find(('e', e.id))
        groups = {}
        for e in bridge_edges: groups.setdefault(find(('e', e.id)), []).append(e)
        junction_owner_nodes = {nid: junc for layer_, junc, nid in pending_junctions if layer_ == 'bridge'}
        self.deck_groups = []
        for root, ges in groups.items():
            polys = [strips[e.id][1] for e in ges]
            seen = set()
            for e in ges:
                for nid in e.nodes:
                    if nid in junction_owner_nodes and nid not in seen:
                        polys.append(junction_owner_nodes[nid]); seen.add(nid)
            deck = unary_union(polys).buffer(0)
            if deck.is_empty: continue
            lines = [e.line for e in ges]; gtree = STRtree(lines)
            def gh(x, z, ges=ges, gtree=gtree):
                p = Point(x, z); e = ges[int(gtree.nearest(p))]
                return float(np.interp(e.line.project(p), e.s, self.h[e.vidx]))
            def gh_arr(xs, zs, gh=gh): return np.array([gh(x, z) for x, z in zip(xs, zs)])
            self.deck_groups.append((deck, ges))
            # landfästen: gruppens noder där vägen fortsätter på mark (eller slutar) — där ska
            # varken räcke eller däckvägg gå tvärs över körbanan
            gids = {e.id for e in ges}
            abut = []
            for e in ges:
                for nid in e.nodes:
                    others = [o for o in incident.get(nid, []) if o.id not in gids]
                    if others or len(incident.get(nid, [])) == 1:
                        abut.append((np.array(net.V[net.node_vidx[nid]]), max([e.width] + [o.width for o in others]) / 2 + 1.5))
            def at_end(p0, p1):
                m = (np.asarray(p0) + np.asarray(p1)) / 2
                return any(np.hypot(*(m - c)) < r for c, r in abut)
            for p in (deck.geoms if isinstance(deck, MultiPolygon) else [deck]):
                ext = np.array(p.exterior.coords)
                for seg in _split_ring(ext, at_end):
                    mb.add_wall('concrete', seg, gh, lambda x, z, gh=gh: gh(x, z) - DECK_T, outward=True)
                    mb.add_wall('rail', seg, lambda x, z, gh=gh: gh(x, z) + RAIL_H, gh, outward=True)
                    mb.add_wall('rail', seg, lambda x, z, gh=gh: gh(x, z) + RAIL_H, gh, outward=False)
                tmp = MeshBuf()
                tmp.add_polygon_top('x', p, lambda xs, zs, gh_arr=gh_arr: gh_arr(xs, zs) - DECK_T)
                pos, idx = tmp.parts.get('x', ([], []))
                P = np.array(pos)
                for t in np.array(idx).reshape(-1, 3):
                    mb.add_tri('concrete', tuple(P[t[0]]), tuple(P[t[2]]), tuple(P[t[1]]))
        self.deck_union = unary_union([d for d, _ in self.deck_groups]).buffer(0) if self.deck_groups else Polygon()
        # pelare längs brokanter
        npier = 0
        for e in net.edges:
            if not e.bridge or e.cls in ('footway', 'path', 'steps'): continue
            for s in np.arange(PIER_SPACING / 2, e.s[-1], PIER_SPACING):
                x = np.interp(s, e.s, e.xy[:, 0]); z = np.interp(s, e.s, e.xy[:, 1])
                top = np.interp(s, e.s, self.h[e.vidx]) - DECK_T
                gy = float(self.ground.at(x, z))
                if top - gy < PIER_MIN_H: continue
                _box(mb, 'concrete', x, z, 1.4, 1.4, gy - 1.0, top + 0.05); npier += 1
        log(f'  meshar: ' + ', '.join(f'{k} {len(v[0]) // 3} tri' for k, v in mb.arrays().items()) + f', {npier} pelare')
        return mb


def _split_ring(ring, skip):
    """dela en ring i delpolylinjer, utan segmenten där skip(p0, p1) är sant"""
    out, cur = [], [ring[0]]
    for p0, p1 in zip(ring[:-1], ring[1:]):
        if skip(p0, p1):
            if len(cur) > 1: out.append(np.array(cur))
            cur = [p1]
        else:
            cur.append(p1)
    if len(cur) > 1: out.append(np.array(cur))
    return out


def _seg_is_stair(e, p0, p1):
    """är bandsegmentet (mellan två förtätade punkter) ett trappsegment i lösningen?"""
    if e.stair_seg is None or not e.stair_seg.any(): return False
    mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    s_ = e.line.project(Point(mid))
    k = int(np.clip(np.searchsorted(e.s, s_) - 1, 0, len(e.stair_seg) - 1))
    return bool(e.stair_seg[k])


def _ccw_up(a, b, c):
    return (b[0] - a[0]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[0] - a[0]) < 0


def _box(mb, mat, x, z, w, d, y0, y1):
    hx, hz = w / 2, d / 2
    c = [(x - hx, z - hz), (x + hx, z - hz), (x + hx, z + hz), (x - hx, z + hz), (x - hx, z - hz)]
    mb.add_wall(mat, c, lambda *_: y1, lambda *_: y0, outward=True)
    mb.add_quad(mat, (x - hx, y1, z - hz), (x - hx, y1, z + hz), (x + hx, y1, z + hz), (x + hx, y1, z - hz))

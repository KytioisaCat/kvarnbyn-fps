"""Vägnät som graf ur OSM: ways delas vid delade noder → kanter med attribut. Varje kant
förtätas till ≤ STEP m mellan vertex. Alla vertex (gemensamma noder + inre) får ett index i
den globala höjdvektorn som profil-lösaren löser."""
from collections import defaultdict

import numpy as np
from shapely.geometry import LineString

from .common import ROAD, load_osm

STEP = 4.0


class Edge:
    __slots__ = ('id', 'way', 'cls', 'width', 'maxgrade', 'bridge', 'tunnel', 'layer', 'name',
                 'xy', 'vidx', 's', 'line', 'nodes', 'steplike', 'stair', 'stair_seg', 'in_flat')

    def __init__(self):
        self.vidx = []   # index i höjdvektorn per vertex (inkl. ändnoder)
        self.steplike = False
        self.stair = False
        self.stair_seg = None
        self.in_flat = False


class Network:
    def __init__(self):
        self.edges = []
        self.node_vidx = {}       # OSM-nod-id → vertexindex (delade korsningsnoder)
        self.V = []               # vertexkoordinater [x, z]
        self.vkind = []           # 'node' | 'inner'

    def new_vertex(self, x, z, kind):
        self.V.append((x, z)); self.vkind.append(kind)
        return len(self.V) - 1

    @property
    def n(self):
        return len(self.V)


def build(area, nodes=None, ways=None):
    """area = (xmin, xmax, zmin, zmax). Kanter vars någon punkt ligger i området tas med
    (hela kanten, så nätet inte klipps mitt i en bro)."""
    if nodes is None:
        nodes, ways = load_osm()
    xmin, xmax, zmin, zmax = area
    roads = []
    for w in ways:
        t = w.get('tags', {})
        cls = t.get('highway')
        if cls not in ROAD: continue
        if t.get('area') == 'yes': continue
        pts = [n for n in w['nodes'] if n in nodes]
        if len(pts) < 2: continue
        if not any(xmin <= nodes[n][0] <= xmax and zmin <= nodes[n][1] <= zmax for n in pts): continue
        roads.append((w, pts))
    roads, n_noded = node_crossings(roads, nodes)
    # noder som delas av ≥2 ways, eller är ändpunkter → grafnoder
    count = defaultdict(int)
    for w, pts in roads:
        for n in set(pts): count[n] += 1
    net = Network()
    eid = 0
    for w, pts in roads:
        t = w.get('tags', {})
        cls = t['highway']
        width, maxgrade, _ = ROAD[cls]
        if t.get('width'):
            try: width = max(2.0, min(20.0, float(str(t['width']).replace('m', '').strip())))
            except ValueError: pass
        if t.get('lanes'):
            try: width = max(width, 3.25 * int(t['lanes']))
            except ValueError: pass
        bridge = bool(t.get('bridge')) and t.get('bridge') != 'no'
        tunnel = bool(t.get('tunnel')) and t.get('tunnel') != 'no'
        try: layer = int(t.get('layer', 0))
        except ValueError: layer = 0
        # dela way:en vid delade noder
        cut = [0] + [i for i in range(1, len(pts) - 1) if count[pts[i]] > 1] + [len(pts) - 1]
        for a, b in zip(cut[:-1], cut[1:]):
            seg = pts[a:b + 1]
            e = Edge()
            e.id = eid; eid += 1
            e.way = w['id']; e.cls = cls; e.width = width; e.maxgrade = maxgrade
            e.bridge = bridge; e.tunnel = tunnel; e.layer = layer; e.name = t.get('name', '')
            e.nodes = (seg[0], seg[-1])
            xy = [nodes[n] for n in seg]
            # förtäta
            dense = [xy[0]]
            for (x1, z1), (x2, z2) in zip(xy[:-1], xy[1:]):
                L = np.hypot(x2 - x1, z2 - z1)
                k = max(1, int(np.ceil(L / STEP)))
                for j in range(1, k + 1):
                    dense.append((x1 + (x2 - x1) * j / k, z1 + (z2 - z1) * j / k))
            e.xy = np.array(dense)
            for i, (x, z) in enumerate(dense):
                if i == 0 or i == len(dense) - 1:
                    nid = seg[0] if i == 0 else seg[-1]
                    if nid not in net.node_vidx:
                        net.node_vidx[nid] = net.new_vertex(x, z, 'node')
                    e.vidx.append(net.node_vidx[nid])
                else:
                    e.vidx.append(net.new_vertex(x, z, 'inner'))
            d = np.hypot(np.diff(e.xy[:, 0]), np.diff(e.xy[:, 1]))
            e.s = np.concatenate([[0], np.cumsum(d)])
            e.line = LineString(e.xy)
            net.edges.append(e)
    net.n_noded = n_noded
    return net


def node_crossings(roads, nodes):
    """OSM-ways i samma nivå som korsar varandra utan gemensam nod (slarv i kartan, eller en
    plankorsning som bara ritats över) får en syntetisk gemensam nod i skärningspunkten.
    Bro/tunnel-ways nodas inte mot markvägar (de ska korsa fritt)."""
    from shapely.geometry import LineString
    from shapely.strtree import STRtree
    def level(t):
        if t.get('bridge') and t['bridge'] != 'no': return 1
        if t.get('tunnel') and t['tunnel'] != 'no': return -1
        return 0
    lines = [LineString([nodes[n] for n in pts]) for _, pts in roads]
    tree = STRtree(lines)
    inserts = defaultdict(list)     # way-index → [(segmentindex, t, nod-id)]
    new_id = [-1]
    added = 0
    for i, (wi, pi) in enumerate(roads):
        ti = wi.get('tags', {})
        for j in tree.query(lines[i], predicate='crosses'):
            if j <= i: continue
            wj, pj = roads[j]
            if level(ti) != level(wj.get('tags', {})): continue
            if set(pi) & set(pj): continue            # delar redan nod
            inter = lines[i].intersection(lines[j])
            pts_ = [inter] if inter.geom_type == 'Point' else [q for q in getattr(inter, 'geoms', []) if q.geom_type == 'Point']
            for q in pts_:
                nid = new_id[0]; new_id[0] -= 1
                nodes[nid] = (q.x, q.y)
                for k, ln in ((i, lines[i]), (j, lines[j])):
                    sproj = ln.project(q)
                    cum = 0.0; seg = 0
                    coords = list(ln.coords)
                    for a in range(len(coords) - 1):
                        L = ((coords[a+1][0]-coords[a][0])**2 + (coords[a+1][1]-coords[a][1])**2) ** 0.5
                        if cum + L >= sproj - 1e-9: seg = a; break
                        cum += L
                    inserts[k].append((seg, sproj, nid))
                added += 1
    out = []
    for k, (w, pts) in enumerate(roads):
        if k in inserts:
            pts = list(pts)
            for seg, sproj, nid in sorted(inserts[k], key=lambda t: -t[1]):   # bakifrån så index håller
                pts.insert(seg + 1, nid)
        out.append((w, pts))
    return out, added


def stats(net):
    nb = sum(e.bridge for e in net.edges); nt = sum(e.tunnel for e in net.edges)
    L = sum(e.s[-1] for e in net.edges)
    return (f'{len(net.edges)} kanter ({nb} bro, {nt} tunnel), {len(net.node_vidx)} korsningsnoder '
            f'({getattr(net, "n_noded", 0)} nodade korsningar utan OSM-nod), {net.n} vertex, {L/1000:.1f} km väg')

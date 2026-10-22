"""Global profil-lösare: en höjd per vertex i hela vägnätet, löst i ett svep som viktad minsta
kvadrat med villkor (v2/VISION.md §3b):

  * markpassning:   h_i ≈ g_i                         (vanlig väg; trappor starkt)
  * jämnhet:        h_{i-1} − 2 h_i + h_{i+1} ≈ 0      (längs varje kant; broar styvare)
  * korsningar:     delade vertex → automatiskt lika höjd
  * maxlutning:     |h_{i+1} − h_i| ≤ g_max · Δs        (hinge, itereras)
  * broar:          däck ≥ korsad väg + fri höjd + däcktjocklek; däck ≥ mark + 0,5 (hinge)
  * tunnlar:        h ≤ mark − täckning                 (hinge)

Hinge-villkoren läggs till som straffrader där de bryts, och systemet löses om tills inget
nytt bryts (vanligen 3–6 varv). Lösaren är tät numpy (några tusen okända räcker gott).
"""
import numpy as np
from shapely.geometry import Point
from shapely.strtree import STRtree

CLEARANCE_ROAD = 4.7      # fri höjd över korsad körväg (m)
CLEARANCE_PED = 2.6       # fri höjd över korsad gångväg
CLEARANCE_WATER = 2.5
DECK_T = 1.2              # däcktjocklek körbro (m)
DECK_T_PED = 0.5          # gångbro
PED = ('footway', 'path', 'steps', 'cycleway', 'track', 'pedestrian')
STEPLIKE_GRADE = 0.30     # gångväg vars mark lutar mer än så i snitt är i praktiken en trappa


def deck_t(e):
    return DECK_T_PED if e.cls in PED else DECK_T


def clearance_over(e):
    return CLEARANCE_PED if e.cls in PED else CLEARANCE_ROAD


def steplike(e, g):
    """gångväg på brant mark: följ marken (trappa), ingen lutningsgräns, inget däck"""
    if e.cls == 'steps': return True
    if e.cls not in PED or e.s[-1] < 1e-6: return False
    gg = g[e.vidx]
    return abs(gg[-1] - gg[0]) / e.s[-1] > STEPLIKE_GRADE
W_GROUND = 1.0
W_GROUND_STEPS = 6.0
W_SMOOTH = 4.0
W_SMOOTH_BRIDGE = 25.0
W_SMOOTH_PEDBRIDGE = 20.0
W_HINGE = 30.0            # fysiska villkor (markband)
W_CLEAR = 100.0           # fri höjd: bron ska lyftas, inte vägen under tryckas ner
STAIR_GRADE = 0.30        # gångkant vars ändnoder ligger på olika nivå (≥ 30 %) = trappa mellan nivåerna
W_GRADE = 10.0            # önskemål (maxlutning) — markbandet vinner i branter
BAND = 0.6                # vanlig väg får avvika ±BAND från marken (DTM:en har redan skärningar/bankar)
MAX_ITER = 18


def _solve_normal(n, rows, cols, vals, rhs):
    """Normalekvationer AᵀA h = Aᵀb byggda direkt ur radlistorna (ingen tät A). Varje rad har
    ≤ 3 koefficienter, så AᵀA fylls med np.add.at över radernas koefficientpar."""
    rows = np.asarray(rows); cols = np.asarray(cols); vals = np.asarray(vals, dtype=np.float64)
    rhs = np.asarray(rhs, dtype=np.float64)
    order = np.argsort(rows, kind='stable')
    rows, cols, vals = rows[order], cols[order], vals[order]
    starts = np.searchsorted(rows, np.arange(rhs.size))
    ends = np.searchsorted(rows, np.arange(rhs.size), side='right')
    lin, wts, bi, bw = [], [], [], []
    for k in range(1, 4):                       # rader med exakt k koefficienter
        sel = np.nonzero(ends - starts == k)[0]
        if sel.size == 0: continue
        idx = starts[sel][:, None] + np.arange(k)[None, :]
        C = cols[idx]; Vv = vals[idx]; B = rhs[sel]
        for i in range(k):
            bi.append(C[:, i]); bw.append(Vv[:, i] * B)
            for j in range(k):
                lin.append(C[:, i] * n + C[:, j]); wts.append(Vv[:, i] * Vv[:, j])
    ATA = np.bincount(np.concatenate(lin), weights=np.concatenate(wts), minlength=n * n).reshape(n, n)
    ATb = np.bincount(np.concatenate(bi), weights=np.concatenate(bw), minlength=n)
    ATA[np.diag_indices(n)] += 1e-6
    return np.linalg.solve(ATA, ATb)


def find_crossings(net):
    """(bro-kant, vertexindex på bron, korsad kant, vertexindex på den korsade) för varje ställe
    en bro-kant korsar en kant i lägre lager."""
    lower = [e for e in net.edges if not e.bridge and not e.tunnel]   # tunnlar under en bro kräver ingen fri höjd
    tree = STRtree([e.line for e in lower])
    out = []
    for b in net.edges:
        if not b.bridge: continue
        for j in tree.query(b.line, predicate='intersects'):
            e = lower[j]
            if set(e.nodes) & set(b.nodes): continue        # delar nod = ansluter, korsar inte
            inter = b.line.intersection(e.line)
            pts = [inter] if inter.geom_type == 'Point' else [g for g in getattr(inter, 'geoms', []) if g.geom_type == 'Point']
            for p in pts:
                sb = b.line.project(p); se = e.line.project(p)
                ib = int(np.argmin(np.abs(b.s - sb))); ie = int(np.argmin(np.abs(e.s - se)))
                out.append((b, b.vidx[ib], e, e.vidx[ie]))
    return out


def solve(net, ground, water_lines=None, log=print, flats=()):
    h, g, crossings = _solve(net, ground, water_lines, log, flats)
    stairs = 0
    for e in net.edges:
        if e.cls in PED and not e.steplike and e.s[-1] > 1.0 and (not e.bridge or e.s[-1] < 12.0):
            if abs(h[e.vidx[-1]] - h[e.vidx[0]]) / e.s[-1] > STAIR_GRADE:
                e.stair = True; stairs += 1
    for e in net.edges:
        if e.stair: e.bridge = False
    if stairs:
        log(f'  {stairs} gångkanter mellan nivåer → trappor (struktur, rak linje mellan noderna); löser om')
        h, g, crossings = _solve(net, ground, water_lines, log, flats)
    # segment på gångkanter som ändå måste klättra > 30 % är trappor (material + undantag i grindar)
    nseg = 0
    for e in net.edges:
        hh = h[e.vidx]
        gr = np.abs(np.diff(hh) / np.maximum(np.diff(e.s), 1e-6))
        e.stair_seg = (gr > STAIR_GRADE) if e.cls in PED else np.zeros(len(gr), bool)
        nseg += int(e.stair_seg.sum())
    if nseg: log(f'  {nseg} trappsegment på gångkanter')
    return h, g, crossings


def _solve(net, ground, water_lines=None, log=print, flats=()):
    n = net.n
    V = np.array(net.V)
    g = ground.at(V[:, 0], V[:, 1])
    rows, cols, vals, rhs = [], [], [], []
    r = [0]

    def add(coef, b):
        for c, v in coef:
            rows.append(r[0]); cols.append(c); vals.append(v)
        rhs.append(b); r[0] += 1

    # markpassning
    for e in net.edges:
        if e.bridge and steplike(e, g):
            e.bridge = False                      # "bro" i OSM men en trappa på en slänt
        e.steplike = steplike(e, g)
        if e.bridge or e.stair:
            continue
        w = W_GROUND_STEPS if e.steplike else W_GROUND
        tgt = -4.0 if e.tunnel else 0.0
        for i in e.vidx:
            add([(i, w)], w * (g[i] + tgt))
    # svag regularisering för brovertex (så systemet är bestämt även för en bro utan korsningar)
    for e in net.edges:
        if e.bridge:
            for i in e.vidx:
                add([(i, 0.02)], 0.02 * (g[i] + 1.0))
    # jämnhet längs kant
    for e in net.edges:
        if e.steplike: continue
        w = (W_SMOOTH_PEDBRIDGE if e.cls in PED else W_SMOOTH_BRIDGE) if e.bridge else (40.0 if e.stair else W_SMOOTH)
        for a, b, c in zip(e.vidx[:-2], e.vidx[1:-1], e.vidx[2:]):
            add([(a, w), (b, -2 * w), (c, w)], 0.0)
    # jämnhet ÖVER noder: där två kanter möts som fortsättning (samma OSM-way, t.ex. rondell,
    # eller nod med exakt två kanter) — annars blir varje kort kantbit sin egen ö (v1:s rondell!)
    incident = {}
    for e in net.edges:
        for end, nid in enumerate(e.nodes):
            incident.setdefault(nid, []).append((e, end))
    ncross = 0
    for nid, lst in incident.items():
        if len(lst) < 2: continue
        for a in range(len(lst)):
            for b in range(a + 1, len(lst)):
                (e1, end1), (e2, end2) = lst[a], lst[b]
                if e1 is e2: continue
                # fortsättning: samma way, grad-2-nod, eller två brokanter (en brogrupp är EN struktur)
                if not (e1.way == e2.way or len(lst) == 2 or (e1.bridge and e2.bridge)): continue
                if e1.steplike or e2.steplike: continue
                if len(e1.vidx) < 2 or len(e2.vidx) < 2: continue
                mid = net.node_vidx[nid]
                prev = e1.vidx[-2] if end1 == 1 else e1.vidx[1]
                nxt = e2.vidx[-2] if end2 == 1 else e2.vidx[1]
                w = (W_SMOOTH_PEDBRIDGE if e1.cls in PED else W_SMOOTH_BRIDGE) if (e1.bridge and e2.bridge) else W_SMOOTH
                add([(prev, w), (mid, -2 * w), (nxt, w)], 0.0); ncross += 1
    log(f'  jämnhet över {ncross} nodövergångar')
    # vägar inne i en byggd plan yta (parkering, torg) ligger PÅ planet
    nflat = 0
    if flats:
        import shapely as _sh
        for e in net.edges:
            if e.bridge or e.tunnel: continue
            reach = e.width / 2 + 0.5                       # även en gata vars band överlappar ytan
            for i in e.vidx:
                x, z = net.V[i]
                for f in flats:
                    if _sh.contains_xy(f.poly, x, z) or f.poly.distance(_sh.points(x, z)) <= reach:
                        add([(i, 60.0)], 60.0 * float(f.h_at_xy(x, z))); nflat += 1
                        break
        log(f'  {nflat} vägvertex bundna till flats-plan')
    # rampzon: vertex inom 8 m från en flat slipper markbandet (infarten får jämna ut skillnaden)
    ramp_free = set()
    if flats:
        import shapely as _sh
        for e in net.edges:
            if e.bridge or e.tunnel: continue
            for i in e.vidx:
                x, z = net.V[i]
                if any(f.poly.distance(_sh.points(x, z)) <= 8.0 for f in flats): ramp_free.add(i)
    net.ramp_free = ramp_free
    from shapely.geometry import Point
    from shapely.strtree import STRtree
    glist = [e for e in net.edges if not e.bridge and not e.tunnel]
    gtree = STRtree([e.line for e in glist])
    nsnap = 0
    for nid, lst in incident.items():
        if len(lst) != 1: continue
        e0, _ = lst[0]
        if e0.bridge or e0.tunnel: continue
        vi = net.node_vidx[nid]
        p = Point(net.V[vi])
        for j in gtree.query(p.buffer(0.1), predicate='intersects'):
            pass
        best = None
        for j in gtree.query(p.buffer(12.0)):
            e = glist[j]
            if e is e0 or nid in e.nodes: continue
            d = e.line.distance(p)
            if d <= e.width / 2 + 0.6 and (best is None or d < best[0]):
                best = (d, e)
        if best is None: continue
        e = best[1]
        k = int(np.argmin(np.abs(e.s - e.line.project(p))))
        add([(vi, 30.0), (e.vidx[k], -30.0)], 0.0); nsnap += 1
    log(f'  {nsnap} lösa ändar snappade till vägen de mynnar i')
    # trottoar intill gata: gångkantens vertex inne i (eller 0,3 m från) en körvägs band
    # ligger på gatans höjd + kantsten (annars överlappar banden på olika höjd)
    motor = [e for e in glist if e.cls not in PED]
    mtree = STRtree([e.line for e in motor])
    nside = 0
    for e in glist:
        if e.cls not in PED: continue
        for k, vi in enumerate(e.vidx):
            p = Point(net.V[vi])
            best = None
            for j in mtree.query(p.buffer(8.0)):
                m = motor[j]
                if vi in m.vidx: continue
                d = m.line.distance(p)
                if d <= m.width / 2 + e.width / 2 + 0.3 and (best is None or d < best[0]): best = (d, m)
            if best is None: continue
            m = best[1]; kk = int(np.argmin(np.abs(m.s - m.line.project(p))))
            add([(vi, 20.0), (m.vidx[kk], -20.0)], 20.0 * 0.12); nside += 1
    log(f'  {nside} gångvertex bundna till intilliggande gata (+0,12 m)')
    n_base = r[0]
    A_base = (rows[:], cols[:], vals[:], rhs[:])

    crossings = [c for c in find_crossings(net)]
    # vatten: brovertex över vattenlinjer
    water_hits = []
    if water_lines:
        wtree = STRtree(water_lines)
        for b in net.edges:
            if not b.bridge: continue
            for j in wtree.query(b.line, predicate='intersects'):
                inter = b.line.intersection(water_lines[j])
                pts = [inter] if inter.geom_type == 'Point' else [p for p in getattr(inter, 'geoms', []) if p.geom_type == 'Point']
                for p in pts:
                    ib = int(np.argmin(np.abs(b.s - b.line.project(p))))
                    water_hits.append((b, b.vidx[ib]))
    log(f'  korsningar bro/väg: {len(crossings)}, bro/vatten: {len(water_hits)}')

    h = None
    hinges = {}   # nyckel → (coef, rhs, kind) aktiva straffrader (aktiv mängd)
    for it in range(MAX_ITER):
        rows, cols, vals, rhs = [list(x) for x in A_base]
        r[0] = n_base
        for key, (coef, b, _kind) in hinges.items():
            add(coef, b)
        h = _solve_normal(n, rows, cols, vals, rhs)

        # --- utvärdera alla villkor: brutna → in i mängden; uppfyllda med marginal → ut
        want = {}
        for e in net.edges:                                   # maxlutning (önskemål)
            if e.steplike or e.stair: continue
            for k, (a_, b_) in enumerate(zip(e.vidx[:-1], e.vidx[1:])):
                ds = e.s[k + 1] - e.s[k]
                if ds < 1e-6: continue
                grade = (h[b_] - h[a_]) / ds
                key = ('g', e.id, k)
                if abs(grade) > e.maxgrade - 1e-3 or key in hinges:
                    sgn = np.sign(grade) if abs(grade) > 1e-9 else 1.0
                    if key in hinges and abs(grade) < e.maxgrade - 2e-3:
                        continue                              # inaktiv → släpp
                    want[key] = ([(b_, W_GRADE), (a_, -W_GRADE)], W_GRADE * sgn * e.maxgrade * ds, 'g')
        for e in net.edges:                                   # markband för vanlig väg
            if e.bridge or e.tunnel or e.stair: continue
            for i in e.vidx:
                if i in ramp_free: continue
                d = h[i] - g[i]
                key = ('m', i)
                if d < -BAND + 1e-3:
                    want[key] = ([(i, W_HINGE)], W_HINGE * (g[i] - BAND), 'm')
                elif d > BAND - 1e-3:
                    want[key] = ([(i, W_HINGE)], W_HINGE * (g[i] + BAND), 'm')
        for b_, ib, e, ie in crossings:                       # fri höjd över korsad väg
            if not b_.bridge: continue
            key = ('c', ib, ie)
            need = clearance_over(e) + deck_t(b_)
            floor = max(h[ie], g[ie]) + need + 0.05   # mot vägen under, aldrig under markens krav; liten marginal
            if h[ib] < floor + 0.02:
                want[key] = ([(ib, W_CLEAR)], W_CLEAR * floor, 'c')   # ensidigt: bara bron lyfts
        for b_, ib in water_hits:
            need = g[ib] + CLEARANCE_WATER + deck_t(b_)
            if h[ib] < need + 0.02:
                want[('w', ib)] = ([(ib, W_HINGE)], W_HINGE * need, 'w')
        for e in net.edges:                                   # bro över mark, tunnel under
            if e.bridge:
                for i in e.vidx[1:-1]:
                    if h[i] < g[i] + 0.5 + 0.02:
                        want[('b', i)] = ([(i, W_HINGE)], W_HINGE * (g[i] + 0.5), 'b')
            if e.tunnel:
                for i in e.vidx[1:-1]:
                    if h[i] > g[i] - 3.0 - 0.02:
                        want[('t', i)] = ([(i, W_HINGE)], W_HINGE * (g[i] - 3.0), 't')
        added = len(set(want) - set(hinges)); dropped = len(set(hinges) - set(want))
        hinges = want
        kinds = {}
        for _k, (_c, _r, kind) in hinges.items(): kinds[kind] = kinds.get(kind, 0) + 1
        log(f'  varv {it + 1}: {r[0]} rader, {len(hinges)} aktiva villkor {kinds} (+{added} −{dropped})')
        if added == 0 and dropped == 0:
            break
    net.last_hinges = hinges; net.last_rows = (rows, cols, vals, rhs)
    return h, g, crossings

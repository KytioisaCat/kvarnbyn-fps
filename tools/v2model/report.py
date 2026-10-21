"""Mätgrindar och rapport (markdown + profilbild). Bygget stoppar (exit 1) om en grind bryts."""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .common import HERE
from .profile import CLEARANCE_ROAD, DECK_T

OUTDIR = os.path.join(HERE, 'out')

GATES = {
    'max_grade_excess': 0.03,     # överskridande av klassens maxlutning (andel)
    'bump_4m': 0.20,              # |andra differens| per 4 m längs körväg (m)
    'bump_4m_ped': 0.50,          # gångvägar följer marken (LiDAR-steg, trappsteg) — mildare
    'min_clearance': 4.5,         # fri höjd över korsad väg (m, däck − väg − däcktjocklek)
    'road_vs_ground_p90': 0.6,    # vanlig väg mot LiDAR
    'deck_above_ground': 0.3,     # däck över mark överallt (m)
    'terrain_under_road_max': 0.05, # terräng ≤ vägyta + 5 cm inne i asfalten (1 m-gridens interpolation; kantstenens vägg döljer 12 cm)
    'kerb_above_top_max': 0.03,   # terräng vid kantstenens ytterkant får inte sticka upp över krönet (m)
    'kerb_below_skirt_p99': 0.50,  # … och inte ligga under kjolens underkant (m)
}


def evaluate(net, h, g, crossings, model, conformed_ground, mesh_stats, conform_stats, log=print):
    rows = []
    ok_all = True

    def gate(name, value, limit, higher_is_better=False, unit='m', detail=''):
        nonlocal ok_all
        ok = value >= limit if higher_is_better else value <= limit
        ok_all &= ok
        rows.append((name, value, limit, ok, unit, detail))

    # lutning
    worst = 0.0; worst_e = None
    bumps = []
    nstep = 0
    worst_bump = (0.0, None, None)
    worst_bump_ped = (0.0, None, None)
    PEDC = ('footway', 'path', 'steps', 'cycleway', 'track', 'pedestrian')
    portal = set()                      # noder där en tunnel möter ytan: bulan där är en portal/trappa
    for e in net.edges:
        if e.tunnel or e.cls == 'steps' or e.stair: portal.update(e.vidx[:1] + e.vidx[-1:])   # portaler och trappanslutningar
    for e in net.edges:
        if e.steplike or e.stair or e.tunnel: nstep += 1; continue
        hh = h[e.vidx]; gr = np.abs(np.diff(hh) / np.maximum(np.diff(e.s), 1e-6))
        ss = e.stair_seg if e.stair_seg is not None else np.zeros(len(gr), bool)
        if ss.any():
            nstep += 1
            gr = gr[~ss]
        exc = gr.max() - e.maxgrade if len(gr) else 0
        if exc > worst: worst, worst_e = exc, e
        if len(hh) > 2:
            d2 = np.abs(np.diff(hh, 2))
            keep = ~(ss[:-1] | ss[1:])        # bula vid ett trappsegment räknas inte
            keep &= np.array([not (set(e.vidx[k:k + 3]) & portal) for k in range(len(e.vidx) - 2)])
            if keep.any():
                kb = int(np.argmax(np.where(keep, d2, -1)))
                if e.cls in PEDC:
                    if d2[kb] > worst_bump_ped[0]: worst_bump_ped = (float(d2[kb]), e, tuple(np.round(e.xy[kb + 1]).tolist()))
                else:
                    bumps += list(d2[keep])
                    if d2[kb] > worst_bump[0]: worst_bump = (float(d2[kb]), e, tuple(np.round(e.xy[kb + 1]).tolist()))
    gate('maxlutning: överskridande (ej trappor)', worst, GATES['max_grade_excess'], unit='', detail=f'{worst_e.cls} {worst_e.name!r} way {worst_e.way}' if worst_e else '')
    gate('bula körväg: max |2:a diff| per 4 m', max(bumps) if bumps else 0, GATES['bump_4m'],
         detail=(f'{worst_bump[1].cls} {worst_bump[1].name!r} way {worst_bump[1].way} vid {worst_bump[2]}' if worst_bump[1] else ''))
    gate('bula gångväg: max |2:a diff| per 4 m (ej trappor)', worst_bump_ped[0], GATES['bump_4m_ped'],
         detail=(f'{worst_bump_ped[1].cls} {worst_bump_ped[1].name!r} way {worst_bump_ped[1].way} vid {worst_bump_ped[2]}; ' if worst_bump_ped[1] else '') + f'{nstep} trappor/branta gångvägar/tunnlar undantagna')
    # fri höjd
    from .profile import deck_t, clearance_over
    clr = [(h[ib] - h[ie] - deck_t(b) - (clearance_over(e) - CLEARANCE_ROAD), b, e) for b, ib, e, ie in crossings if b.bridge]
    if clr:
        m = min(clr, key=lambda t: t[0])
        gate('fri höjd över korsad väg (min, normerad till 4,7 för gång 2,6)', m[0], GATES['min_clearance'], higher_is_better=True,
             detail=f'{m[1].name or m[1].cls} över {m[2].name or m[2].cls}')
    # väg mot mark
    dev = np.concatenate([np.abs(h[e.vidx] - g[e.vidx]) for e in net.edges if not e.bridge and not e.tunnel])
    gate('vanlig väg − LiDAR (p90)', float(np.percentile(dev, 90)), GATES['road_vs_ground_p90'])
    # däck över mark
    dm = [float(np.min(h[e.vidx[1:-1]] - g[e.vidx[1:-1]])) for e in net.edges if e.bridge and len(e.vidx) > 2]
    if dm: gate('däck över mark (min)', min(dm), GATES['deck_above_ground'], higher_is_better=True)
    # terräng efter konformering: inne i asfalt ≤ vägyta; vid kantstenens ytterkant = krön
    import shapely
    ru = model.road_union
    # sampla 3000 slumppunkter i asfalten
    rng = np.random.default_rng(1)
    minx, minz, maxx, maxz = ru.bounds
    P = np.column_stack([rng.uniform(minx, maxx, 20000), rng.uniform(minz, maxz, 20000)])
    inside = shapely.contains_xy(ru, P[:, 0], P[:, 1])
    P = P[inside][:3000]
    if len(P):
        road_y = model.height_at(P[:, 0], P[:, 1], 'ground')
        terr_y = conformed_ground.at(P[:, 0], P[:, 1])
        over_r = terr_y - road_y
        wi = np.argsort(over_r)[-3:][::-1]
        gate('terräng över vägyta inne i asfalt (max)', float(np.max(over_r)), GATES['terrain_under_road_max'],
             detail=', '.join(f'{over_r[i]:.2f} m vid ({P[i, 0]:.0f}, {P[i, 1]:.0f})' for i in wi))
    ko = model.kerb_outer
    ring = np.array(ko.exterior.coords) if ko.geom_type == 'Polygon' else np.vstack([np.array(p.exterior.coords) for p in ko.geoms])
    ring = ring[:: max(1, len(ring) // 3000)]
    kerb_y = model.height_at(ring[:, 0], ring[:, 1], 'ground') + 0.12
    terr_y = conformed_ground.at(ring[:, 0] , ring[:, 1])
    over = terr_y - kerb_y
    worst_i = np.argsort(over)[-3:][::-1]
    gate('terräng över kantstenskrön vid ytterkanten (p99)', float(np.percentile(over, 99)), GATES['kerb_above_top_max'],
         detail='max ' + ', '.join(f'{over[i]:.2f} m vid ({ring[i, 0]:.0f}, {ring[i, 1]:.0f})' for i in worst_i) + ' — kandidater för stödmur')
    gate('terräng under kantstenskrön vid ytterkanten (p99)', float(np.percentile(kerb_y - terr_y, 99)), GATES['kerb_below_skirt_p99'])
    return rows, ok_all


def write(rows, ok_all, net, h, g, mesh_stats, conform_stats, area_name, extra_lines=()):
    os.makedirs(OUTDIR, exist_ok=True)
    L = [f'# v2model-rapport — område `{area_name}`', '']
    L += [f'Nät: {net_stats(net)}', '']
    L += ['| Mätgrind | Värde | Gräns | OK | Detalj |', '|---|---|---|---|---|']
    for name, v, lim, ok, unit, det in rows:
        L.append(f'| {name} | {v:.3f} {unit} | {lim} | {"✅" if ok else "❌"} | {det} |')
    L += ['', f'**Resultat: {"ALLA GRINDAR OK" if ok_all else "GRIND BRUTEN — bygget stoppat"}**', '']
    L += ['Meshar: ' + ', '.join(f'{k} {v} tri' for k, v in mesh_stats.items()), '']
    L += ['Konformering: ' + ', '.join(f'{k} {v:.2f}' if isinstance(v, float) else f'{k} {v}' for k, v in conform_stats.items()), '']
    L += list(extra_lines)
    path = os.path.join(OUTDIR, f'report_{area_name}.md')
    open(path, 'w').write('\n'.join(L) + '\n')
    return path


def net_stats(net):
    from .network import stats
    return stats(net)


def profile_png(net, h, g, name_filter, path, title):
    """Längsprofil (mark vs löst höjd) längs alla kanter med namnet, sorterade i en kedja."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    es = [e for e in net.edges if e.name == name_filter and e.cls in ('tertiary', 'secondary', 'primary', 'residential')]
    if not es: return None
    # kedja ihop via delade noder (grådig)
    chain = [es.pop(0)]
    changed = True
    while es and changed:
        changed = False
        for e in list(es):
            if e.nodes[0] == chain[-1].nodes[1]: chain.append(e); es.remove(e); changed = True
            elif e.nodes[1] == chain[-1].nodes[1]:
                e.xy = e.xy[::-1]; e.vidx = e.vidx[::-1]; e.s = e.s[-1] - e.s[::-1]; e.nodes = e.nodes[::-1]
                chain.append(e); es.remove(e); changed = True
            elif e.nodes[1] == chain[0].nodes[0]: chain.insert(0, e); es.remove(e); changed = True
            elif e.nodes[0] == chain[0].nodes[0]:
                e.xy = e.xy[::-1]; e.vidx = e.vidx[::-1]; e.s = e.s[-1] - e.s[::-1]; e.nodes = e.nodes[::-1]
                chain.insert(0, e); es.remove(e); changed = True
    S, H, G, B = [], [], [], []
    s0 = 0
    for e in chain:
        S += list(e.s + s0); H += list(h[e.vidx]); G += list(g[e.vidx]); B += [e.bridge] * len(e.vidx); s0 += e.s[-1]
    S, H, G = np.array(S), np.array(H), np.array(G)
    W, Hh = 1400, 420; m = 50
    im = Image.new('RGB', (W, Hh), 'white'); d = ImageDraw.Draw(im)
    try: font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 13)
    except OSError: font = ImageFont.load_default()
    d.font = font
    ymin, ymax = min(G.min(), H.min()) - 2, max(G.max(), H.max()) + 2
    sx = lambda s: m + (s / S.max()) * (W - 2 * m)
    sy = lambda y: Hh - m - (y - ymin) / (ymax - ymin) * (Hh - 2 * m)
    for yv in range(int(ymin), int(ymax) + 1, 2):
        d.line([(m, sy(yv)), (W - m, sy(yv))], fill=(235, 235, 235)); d.text((4, sy(yv) - 6), f'{yv}', fill=(120, 120, 120))
    d.line([(sx(s), sy(v)) for s, v in zip(S, G)], fill=(120, 90, 40), width=2)
    for i in range(len(S) - 1):
        d.line([(sx(S[i]), sy(H[i])), (sx(S[i + 1]), sy(H[i + 1]))], fill=(200, 40, 40) if B[i] else (30, 90, 200), width=3)
    d.text((m, 8), f'{title} — brun = LiDAR-mark ×1,2, blå = löst vägprofil, röd = brodäck; x = meter längs vägen, y = m ö.h. (spelhöjd)', fill=(0, 0, 0))
    im.save(path)
    return path

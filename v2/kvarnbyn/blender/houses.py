"""Hus ur hustyp (arketyp) för Fas A — lätta men riktiga fasader.

Varje hus: granitsockel ner till lägsta mark, väggar i rätt material och kulör, fönster med
foder, spröjs, bleck och mörkt glas (ingen öppning i väggen — billigt), dörr mot gatan,
tak (sadel/valm/platt med takfot) och skorsten. Ungefär 90 trianglar per fönster.

Koordinater: plan (x öster, z söder); Blender (x, −z, y). Fotavtryck medurs i plan = moturs
i Blender, så utåtnormalen för kanten a→b är (dy, −dx) i Blender-planet.
"""
import math, zlib
from modelkit import Frame, roof, text


def h01(*parts):
    """Stabilt 0..1 ur id (inbyggd hashning slumpas per körning)."""
    return zlib.crc32('|'.join(map(str, parts)).encode()) / 0xFFFFFFFF

WINDOW = {   # bredd, höjd, bröstningshöjd över våningens golv
    'trahus': (1.0, 1.3, 0.85), 'bod': (0.7, 0.6, 1.1), 'flerbostad': (1.3, 1.4, 0.9),
    'industri': (2.0, 2.4, 0.9), 'offentlig': (1.3, 1.8, 0.9),
}
BAY = {'trahus': 2.9, 'bod': 3.5, 'flerbostad': 3.1, 'industri': 3.9, 'offentlig': 3.0}


def _edge_frame(a, b):
    ax, ay = a[0], -a[1]; bx, by = b[0], -b[1]
    dx, dy = bx - ax, by - ay; L = math.hypot(dx, dy) or 1e-6
    u = (dx / L, dy / L); out = (u[1], -u[0])
    return (ax, ay), u, out, L


def window(K, name, M, at, w, h, trim, muntins=True, sill=True):
    """at(s, depth, height) → Blender-punkt; s längs väggen, depth utåt."""
    t, d = 0.075, 0.11
    K.box(name, trim, at(-w / 2 - t / 2, d / 2, h / 2), (t, d, h + 2 * t), *_uv(at))
    K.box(name, trim, at(w / 2 + t / 2, d / 2, h / 2), (t, d, h + 2 * t), *_uv(at))
    K.box(name, trim, at(0, d / 2, h + t / 2), (w, d, t), *_uv(at))
    K.box(name, trim, at(0, d / 2, -t / 2), (w, d, t), *_uv(at))
    K.face(name + '_Glass', M['glass_dark'], [at(-w / 2, 0.045, 0), at(w / 2, 0.045, 0), at(w / 2, 0.045, h), at(-w / 2, 0.045, h)],
           [(0, 0), (1, 0), (1, 1), (0, 1)])
    if muntins:
        K.box(name, trim, at(0, 0.07, h / 2), (0.045, 0.05, h), *_uv(at))
        K.box(name, trim, at(0, 0.07, h * 0.58), (w, 0.05, 0.04), *_uv(at))
    if sill:
        K.box(name, M['metal_sill'], at(0, 0.13, -0.11), (w + 0.2, 0.2, 0.04), *_uv(at))


def _uv(at):
    p0 = at(0, 0, 0); p1 = at(1, 0, 0)
    return ((p1[0] - p0[0], p1[1] - p0[1]),)


def door(K, name, M, at, w, h, leaf, trim):
    t = 0.09
    for s in (-w / 2 - t / 2, w / 2 + t / 2):
        K.box(name, trim, at(s, 0.06, h / 2), (t, 0.12, h + t), *_uv(at))
    K.box(name, trim, at(0, 0.06, h + t / 2), (w + 2 * t, 0.12, t), *_uv(at))
    K.box(name, leaf, at(0, 0.03, h / 2), (w, 0.06, h), *_uv(at))
    K.box(name, M['metal_sill'], at(w * 0.3, 0.09, h * 0.47), (0.12, 0.05, 0.03), *_uv(at))
    K.box(name, M['stone'], at(0, 0.35, -0.08), (w + 0.6, 0.7, 0.16), *_uv(at))


def build_house(K, b, M, ground, tile):
    arch = b['archetype']
    foot = b['build_footprint_xz']
    base = b['base_y_m']; wall = b['wall_height_m']; levels = max(1, b['levels'])
    eave = base + wall
    wallmat = M['wall'](b)
    trim = M['trim_dark'] if b['facade_material'] == 'wood' and b['facade_color'] in ('#efece4', '#e9dcae', '#e6d8c0', '#cfccc2') and (h01(b['id'], 'trim') < 0.33) else M['trim_light']
    if b['facade_material'] == 'wood' and b['facade_color'] == '#8e3326':
        trim = M['trim_light']
    name = 'H%s' % tile
    nm = name
    # sockel
    low = b.get('ground_min_raw_m', b['base_height_raw_m']) - 18.0 - 0.35
    sock = 0.45 if arch in ('trahus', 'offentlig') else 0.25
    n = len(foot)
    for i in range(n):
        a, c = foot[i], foot[(i + 1) % n]
        K.face(nm + '_Plinth', M['stone'], [(a[0], -a[1], low), (c[0], -c[1], low), (c[0], -c[1], base + sock), (a[0], -a[1], base + sock)])
    # väggar
    for i in range(n):
        a, c = foot[i], foot[(i + 1) % n]
        K.face(nm + '_Walls', wallmat, [(a[0], -a[1], base + sock), (c[0], -c[1], base + sock), (c[0], -c[1], eave), (a[0], -a[1], eave)])
    K.shell('COL_' + nm, M['collision'], [tuple(p) for p in foot], low, eave - low)
    # fönster och dörr
    ww, wh, sill_h = WINDOW[arch]; bay = BAY[arch]
    if arch == 'trahus' and levels == 2 and wall < 5.0:
        floors = [(base + sock, 2.55), (base + sock + 2.6, wall - sock - 2.6)]
    else:
        fh = (wall - sock) / levels
        floors = [(base + sock + k * fh, fh) for k in range(levels)]
    street = b.get('street_edge', 0)
    for i in range(n):
        a, c = foot[i], foot[(i + 1) % n]
        (ax, ay), u, out, L = _edge_frame(a, c)
        if L < 2.3: continue
        count = max(1, int(L / bay))
        if arch == 'bod' and i != street: count = 0 if L < 5 else 1
        at_edge = lambda s, d, h, ax=ax, ay=ay, u=u, out=out: (ax + u[0] * s + out[0] * d, ay + u[1] * s + out[1] * d, h)
        door_slot = count // 2 if i == street else -1
        for f, (fy, fh) in enumerate(floors):
            hh = min(wh, fh - 0.75) if arch != 'industri' else min(wh, fh - 0.9)
            if hh < 0.45: continue
            for k in range(count):
                s = (k + 0.5) * L / count
                at = lambda ss, d, h, s=s, fy=fy: at_edge(s + ss, d, fy + h)
                if f == 0 and k == door_slot and arch != 'industri':
                    dw = 1.0 if arch in ('trahus', 'bod') else 1.4
                    door(K, nm, M, lambda ss, d, h, s=s: at_edge(s + ss, d, base + sock + h), dw, 2.1, M['door'](b), trim)
                    continue
                if arch == 'bod' and f == 0 and i == street and k == 0 and L > 5.5:
                    # garageport
                    gw = min(2.6, L * 0.5)
                    K.box(nm, M['door'](b), at_edge(s, 0.03, base + sock + 1.05), (gw, 0.06, 2.1), u)
                    continue
                window(K, nm, M, lambda ss, d, h, s=s, fy=fy, sh=sill_h if arch != 'industri' else 0.8: at_edge(s + ss, d, fy + sh + h),
                       ww, hh, trim, muntins=arch in ('trahus', 'offentlig', 'bod'))
        # balkonger på flerbostadshusens långsida mot gatan (1960-tal)
        if arch == 'flerbostad' and i == street and levels >= 2 and b['facade_material'] == 'plaster':
            for f, (fy, fh) in enumerate(floors[1:], start=1):
                for k in range(0, count, 2):
                    s = (k + 0.5) * L / count
                    K.box(nm + '_Balcony', M['concrete'], at_edge(s, 0.65, fy - 0.08), (2.4, 1.3, 0.16), u)
                    K.box(nm + '_Balcony', M['balcony'](b), at_edge(s, 1.28, fy + 0.5), (2.4, 0.06, 1.0), u)
                    for sx in (-1.18, 1.18):
                        K.box(nm + '_Balcony', M['balcony'](b), at_edge(s + sx, 0.65, fy + 0.5), (0.06, 1.3, 1.0), u)
    # tak
    roofmat = M['roof_for'](b)
    if b['roof_shape'] == 'flat' or b['roof_rise_m'] <= 0.05 or not b.get('build_rect'):
        K.polygon(nm + '_Roof', M['roof_flat'](b), [tuple(p) for p in foot], eave + 0.02)
        for i in range(n):
            a, c = foot[i], foot[(i + 1) % n]
            (ax, ay), u, out, L = _edge_frame(a, c)
            K.box(nm + '_Roof', M['coping'], (ax + u[0] * L / 2, ay + u[1] * L / 2, eave + 0.3), (L + 0.3, 0.3, 0.6), u)
        top = eave + 0.6
    else:
        L, W = b['major_length_m'], b['minor_width_m']
        cx = sum(p[0] for p in foot) / n; cz = sum(p[1] for p in foot) / n
        fr = Frame((cx, cz), b['major_axis_xz'])
        top = roof(K, nm + '_Roof', fr, L, W, eave, b['roof_rise_m'], roofmat, wallmat, hipped=b['roof_shape'] == 'hipped')
        if arch in ('trahus', 'offentlig', 'flerbostad'):
            sx = L * (0.2 if h01(b['id'], 'ch') < 0.5 else -0.2)
            K.box(nm + '_Chimney', M['chimney'], fr.p(sx, W * 0.12, eave + b['roof_rise_m'] * 0.75 + 0.5), (0.6, 0.6, b['roof_rise_m'] * 0.5 + 1.2), fr.u)
    if b.get('sign'):
        a, c = foot[street], foot[(street + 1) % n]
        (ax, ay), u, out, L = _edge_frame(a, c)
        text(b['sign'], nm + '_Sign', (ax + u[0] * L / 2 + out[0] * 0.2, ay + u[1] * L / 2 + out[1] * 0.2, eave - 1.6), out, 1.1, M['sign_dark'])
    return top


def build_backdrop_house(K, b, M, tile):
    foot = b['footprint_xz']
    if len(foot) < 3: return
    area2 = sum(foot[i][0] * foot[(i + 1) % len(foot)][1] - foot[(i + 1) % len(foot)][0] * foot[i][1] for i in range(len(foot)))
    if area2 > 0: foot = foot[::-1]
    base = b['ground_min_y_m'] - 0.3; top = b['base_y_m'] + b['height_m']
    mat = M['far_wall'](b)
    for i in range(len(foot)):
        a, c = foot[i], foot[(i + 1) % len(foot)]
        K.face('Far%s_Walls' % tile, mat, [(a[0], -a[1], base), (c[0], -c[1], base), (c[0], -c[1], top), (a[0], -a[1], top)])
    K.polygon('Far%s_Roof' % tile, M['far_roof'](b), [tuple(p) for p in foot], top)

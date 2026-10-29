"""Hjältehusen från PoC Gamla torget — Codex handgjorda modeller (build_scene.py rad 155–262),
flyttade hit nästan ordagrant så att de byggs likadant i hela världen. Fasaderna är granskade mot
Street View/Wikimedia (se ../../poc/torget/reference/OBSERVATIONER.md)."""
import math
from mathutils import Vector
from modelkit import Frame, roof, text, window, facade


def ensure_ccw(poly):
    poly = list(poly); area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))
    return list(reversed(poly)) if area > 0 else poly


def build_hip_polygon(K, M, name, poly, eave, rise, ridge=None):
    c = Vector((sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)))
    p = [Vector(a) + (Vector(a) - c).normalized() * .28 for a in poly]
    if ridge is None: ridge = [(c.x - .1, c.y), (c.x + .1, c.y)]
    r = [(x, -z, eave + rise) for x, z in ridge]
    points = [(v.x, -v.y, eave) for v in p]
    if len(p) == 5:
        faces = [[points[0], points[1], r[0]], [points[1], points[2], r[1], r[0]], [points[2], points[3], r[1]], [points[3], points[4], r[1]], [points[4], points[0], r[0], r[1]]]
    else:
        faces = [[points[i], points[(i + 1) % len(points)], r[0]] for i in range(len(points))]
    for f in faces:
        f = list(map(Vector, f))
        if (f[1] - f[0]).cross(f[2] - f[0]).z < 0: f.reverse()
        K.face(name, M['metal'], f)
        if len(f) == 4:
            for k in range(1, math.ceil((f[1] - f[0]).length / .65)):
                t = k / max(1, math.ceil((f[1] - f[0]).length / .65)); start = f[0].lerp(f[1], t); end = f[3].lerp(f[2], t); start.z += .018; end.z += .018
                K.beam(name, M['metal'], start, end, .012, 4)
    for a, b in zip(points, points[1:] + points[:1]):
        K.beam(name, M['white'], (a[0], a[1], a[2] - .08), (b[0], b[1], b[2] - .08), .06)


def shell_and_facades(K, M, ground, b, mat, trim):
    poly = ensure_ccw(b['footprint_xz']); base = b['base_y_m']; height = b['wall_height_m']; levels = b['levels']; name = b['id']
    K.shell('COL_' + name, M['collision'], poly, base - .4, height + .4)
    for a, bb in zip(poly, poly[1:] + poly[:1]):
        low = min(ground(*a), ground(*bb), base) - .25
        K.face(name + '_Foundation', M['stone'], [(a[0], -a[1], low), (bb[0], -bb[1], low), (bb[0], -bb[1], base + .28), (a[0], -a[1], base + .28)])
        if math.dist(a, bb) > 2:
            civic = b['id'] == 'w92332122'
            facade(K, name, (a[0], -a[1]), (bb[0], -bb[1]), base, height, mat, trim, M['glass'], M['white'], levels=4 if civic else levels,
                   bays=8 if civic and math.dist(a, bb) > 25 else None, panel=mat in [M['panel'], M['cream']], ornate=civic,
                   floor_heights=[1.8, 2.6, 3.5, 2.4] if civic else None)
    return poly


def build_krakan(K, M, ground, krakan, offset):
    for volume in krakan['volumes']:
        poly = ensure_ccw(volume['footprint_xz']); base = volume['base_height_raw_m'] - offset; height = volume['wall_height_m']; name = volume['id']
        K.shell('COL_' + name, M['collision'], poly, base - .35, height + .35)
        fronts = [f for f in krakan['street_facades'] if f['volume'] == name]
        for a, b in zip(poly, poly[1:] + poly[:1]):
            isfront = next((f for f in fronts if (math.dist(a, f['edge_xz'][1]) < .2 and math.dist(b, f['edge_xz'][0]) < .2) or (math.dist(a, f['edge_xz'][0]) < .2 and math.dist(b, f['edge_xz'][1]) < .2)), None)
            if isfront:
                bays = len(isfront['lower_bays']); up = isfront.get('upper_bays', bays)
                types = isfront['lower_bays'] if math.dist(a, isfront['edge_xz'][0]) < .2 else list(reversed(isfront['lower_bays']))
                facade(K, name, (a[0], -a[1]), (b[0], -b[1]), base, height, M['panel'], M['green'], M['glass'], M['white'], levels=volume['levels'], bays=bays, panel=True,
                       awning=M['blue'] if name == 'krakan_west' else None, sign='KRÅKANS KROG' if name == 'krakan_west' else None, floor_bays=[bays, up], lower_types=types)
            elif math.dist(a, b) > 2:
                facade(K, name, (a[0], -a[1]), (b[0], -b[1]), base, height, M['panel'], M['green'], M['glass'], M['white'], levels=volume['levels'], panel=True)
            low = min(ground(*a), ground(*b), base) - .3
            K.face(name + '_Foundation', M['stone'], [(a[0], -a[1], low), (b[0], -b[1], low), (b[0], -b[1], base + .18), (a[0], -a[1], base + .18)])
        if name == 'krakan_west':
            build_hip_polygon(K, M, name + '_Roof', volume['footprint_xz'], base + height, volume['roof_rise_m'], [(7, 30.3), (16.5, 29.1)])
            for x, z in [(9.5, 29.8), (16.1, 29.4)]:
                K.box(name + '_Chimneys', M['metal'], (x, -z, base + height + 1.9), (.65, .65, .9)); K.box(name + '_Chimneys', M['metal'], (x, -z, base + height + 2.4), (.8, .8, .12))
        else:
            axis = Vector(krakan['major_axis_xz']); c = [sum(v[i] for v in poly) / len(poly) for i in [0, 1]]; fr = Frame(c, axis); L = 10.2 if name == 'krakan_link' else 22.3; W = 9.6
            roof(K, name + '_Roof', fr, L, W, base + height, volume['roof_rise_m'], M['metal'], M['white'], seams=True)
            for da in ([0] if name == 'krakan_link' else [-5, 5]):
                dc = fr.p(da, -W / 2 + .12, base + height - .65)
                K.box(name + '_Dormers', M['panel'], dc, (2.1, .7, 1.5), fr.u)
                normal = (-fr.v[0], -fr.v[1]); window(K, name + '_Dormers', (dc[0] + normal[0] * .4, dc[1] + normal[1] * .4, dc[2] - .5), fr.u, normal, .85, 1.12, M['green'], M['glass'], M['white'])
                p1 = fr.p(da - 1.2, -W / 2 - .5, base + height + .1); p2 = fr.p(da + 1.2, -W / 2 - .5, base + height + .1); p3 = fr.p(da, -W / 2 - .5, base + height + 1)
                K.face(name + '_Dormers', M['panel'], [p1, p2, p3]); K.face(name + '_Dormers', M['metal'], [p1, p3, fr.p(da, -W / 2 + 1.5, base + height + 1), fr.p(da - 1.2, -W / 2 + 1.5, base + height + .1)]); K.face(name + '_Dormers', M['metal'], [p3, p2, fr.p(da + 1.2, -W / 2 + 1.5, base + height + .1), fr.p(da, -W / 2 + 1.5, base + height + 1)])
        for x, z in volume['footprint_xz'][::2]:
            K.beam(name + '_Downpipes', M['white'], (x, -z, base + .2), (x, -z, base + height - .2), .055)


def build_hero(K, M, ground, b):
    mat = M['brick'] if 'brick' in b['archetype'] else M['cream'] if b['id'] == 'w92332122' else M['plaster'] if b['id'] == 'w92332103' else M['panel']
    trim = M['rust'] if b['id'] == 'w92332122' else M['white']
    poly = shell_and_facades(K, M, ground, b, mat, trim)
    rect = b['rectangle_xz']; center = [sum(p[i] for p in rect) / 4 for i in [0, 1]]; fr = Frame(center, b['major_axis_xz']); base = b['base_y_m']; eave = base + b['wall_height_m']
    roofmat = M['metal'] if b['id'] == 'w92332103' else M['roof']
    if b['id'] == 'w92332103':
        roof(K, b['id'] + '_RoofWest', Frame((-16.4, -31.3), (.615, -.788)), 20.8, 5.6, eave, 1.8, roofmat, mat, hipped=True, seams=True)
        roof(K, b['id'] + '_RoofSouth', Frame((-10.6, -23.6), (.84, -.543)), 14.6, 10.1, eave, 2.0, roofmat, mat, hipped=True, seams=True)
    else:
        roof(K, b['id'] + '_Roof', fr, b['major_length_m'], b['minor_width_m'], eave, b['roof_rise_m'], roofmat, mat)
    K.box(b['id'] + '_Chimney', M['brick'], fr.p(b['major_length_m'] * .22, 0, eave + b['roof_rise_m'] + .45), (.7, .8, 1.15), fr.u)
    if b['id'] == 'w92332122':
        L = b['major_length_m']; W = b['minor_width_m']; normal = (-fr.v[0], -fr.v[1])
        for h in [1.8, 4.5, 7.7, 9.6]: K.box(b['id'] + '_Bands', M['rust'], fr.p(0, -W / 2 - .15, base + h), (L + .12, .18, .2), fr.u)
        edges = [(a, bb) for a, bb in zip(poly, poly[1:] + poly[:1]) if math.dist(a, bb) > 25]
        a, bb = max(edges, key=lambda e: Vector((-(e[0][1] + e[1][1]) / 2, -(e[0][0] + e[1][0]) / 2)).dot(Vector((-(e[1][1] - e[0][1]), -(e[1][0] - e[0][0]))).normalized()))
        direction = Vector((bb[0] - a[0], -(bb[1] - a[1]))).normalized(); front_normal = (direction.y, -direction.x)
        sx = a[0] + (bb[0] - a[0]) * .32 + front_normal[0] * .35; sy = -a[1] - (bb[1] - a[1]) * .32 + front_normal[1] * .35
        text('MUSIKSKOLAN', b['id'] + '_Sign', (sx, sy, base + 1.98), front_normal, .39, M['rust'])
        cp = Vector(fr.p(0, -W / 2 - .28, base + 8.1)); K.beam(b['id'] + '_Clock', M['white'], cp, cp + Vector((*normal, 0)) * .025, .42, 48)
        for dx, dy in [(.02, .27), (.22, -.08)]:
            end = cp + Vector((fr.u[0] * dx, fr.u[1] * dx, dy)); cp2 = cp + Vector((*normal, 0)) * .04; end += Vector((*normal, 0)) * .04; K.beam(b['id'] + '_ClockHands', M['black'], cp2, end, .018, 6)
    if b['id'] == 'w92332103':
        edge = max(zip(poly, poly[1:] + poly[:1]), key=lambda e: ((e[0][1] + e[1][1]) / 2 if math.dist(*e) > 4 else -1000))
        a, bb = edge; d = Vector((bb[0] - a[0], -(bb[1] - a[1]))); d.normalize(); out = (d.y, -d.x); cx = (a[0] + bb[0]) / 2; cy = -(a[1] + bb[1]) / 2
        K.box('Corpus_signboard', M['black'], (cx + out[0] * .24, cy + out[1] * .24, base + 3.05), (5.2, .15, .58), (d.x, d.y)); text('CORPUS PIZZA', 'Corpus_letters', (cx + out[0] * .33, cy + out[1] * .33, base + 3.05), out, .36, M['white'])

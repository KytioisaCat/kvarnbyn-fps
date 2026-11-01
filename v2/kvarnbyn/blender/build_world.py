"""Bygger hela Kvarnbyns spelbara zon i Blender ur data/city.json + data/site.json och exporterar
blender/world_raw.glb + godot-metadata. Återanvänder torget-provets kit, material och träd.

    v2/.tools/Blender.app/Contents/MacOS/Blender -b --python v2/kvarnbyn/blender/build_world.py
"""
from pathlib import Path
import argparse, json, math, sys, time, zlib
import bpy, bmesh

HERE = Path(__file__).resolve().parents[1]           # v2/kvarnbyn
TORGET = HERE.parent / 'poc/torget'
for p in [HERE / 'blender', TORGET / 'scripts', TORGET / 'assets-src']:
    sys.path.insert(0, str(p))
from modelkit import Kit, color
from blender_materials import pbr_material, solid_material
from blender_vegetation import place_tree, load_library
from blender_finish import apply_finish
import houses, heroes, roten, stairkit

T0 = time.time()
def log(m): print(f'[{time.time() - T0:6.1f}s] {m}', flush=True)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--stage-dir', type=Path, help='Read site.json and write model/metadata here; leave active Godot assets intact.')
parser.add_argument('--save-blend', action='store_true', help='Save the staged scene for geometry probes.')
options = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
CITY = json.loads((HERE / 'data/city.json').read_text())
OUT = options.stage_dir.resolve() if options.stage_dir else HERE / 'blender'
OUT.mkdir(parents=True, exist_ok=True)
SITE = json.loads(((OUT if options.stage_dir else HERE / 'data') / 'site.json').read_text())
OFFSET = CITY['meta']['origin']['y_offset_m']
GODOT = OUT if options.stage_dir else HERE / 'godot/assets'; GODOT.mkdir(parents=True, exist_ok=True)
TILE = SITE['meta']['tile_m']

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for d in [bpy.data.materials, bpy.data.meshes, bpy.data.curves, bpy.data.objects]:
    for item in list(d):
        if item.users == 0: d.remove(item)
K = Kit(); K.window_batch_name = 'WindowInteriors'


def h01(*parts): return zlib.crc32('|'.join(map(str, parts)).encode()) / 0xFFFFFFFF


def pbr(key, name=None, tint=None, strength=.35):
    m = pbr_material(key, name, base_color=color(tint) if tint else None, normal_strength=strength)
    m['tile_size_m'] = float(m['tile_size_m'][0]); return m


# ---------- material ----------
M = {
    'panel': pbr('plaster', 'Painted_clapboard', '#eeeae0', .12), 'cream': pbr('plaster', 'Cream_clapboard', '#ded7c3', .12),
    'plaster': pbr('plaster', 'Corpus_plaster', '#e8e1cf', .3), 'brick': pbr('brick', 'Historic_brick', None, .65),
    'roof': pbr('roof_tiles', 'Clay_roof_tiles', None, .6), 'asphalt': pbr('asphalt', 'Road_asphalt', None, .32),
    'paving': pbr('cobblestone', 'Granite_setts', None, .55), 'grass': pbr('grass', 'Grass_ground', None, .55),
    'stone': pbr('rock', 'Granite_foundation', None, .55),
    'green': solid_material('Krakan_green', color('#225747'), .6), 'rust': solid_material('Musikskolan_oxblood', color('#914d40'), .65),
    'white': solid_material('Offwhite_trim', color('#e9e4d9'), .65), 'blue': solid_material('Blue_awning', color('#154b89'), .82),
    'metal': solid_material('Standing_seam_roof', color('#343b40'), .58, .18), 'iron': solid_material('Street_iron', color('#313738'), .6, .25),
    'glass': solid_material('Window_glass', color('#344b52'), .18, .32), 'black': solid_material('Sign_black', color('#172426'), .8),
    'water': solid_material('WaterFlow', color('#31575a'), .34, .03), 'curb': solid_material('Worn_granite_kerb', color('#99998d'), .88),
    'collision': solid_material('Collision_only', (1, 0, 1, 1), 1),
}
apply_finish(M, glass=True)
gb = M['glass'].node_tree.nodes.get('Principled BSDF'); gb.inputs['Alpha'].default_value = .18
M['glass'].diffuse_color = tuple(M['glass'].diffuse_color[:3]) + (.18,); M['glass'].surface_render_method = 'DITHERED'
M.update({
    'rock': pbr('natural_rock', 'Bedrock', None, .7), 'forest': pbr('grass', 'Forest_floor', '#5a5f3c', .7),
    'walkway': pbr('asphalt', 'Walkway_asphalt', '#8d8c88', .3),
    'trail': pbr('asphalt', 'Gravel_path', '#77736a', .5), 'pitch': solid_material('Artificial_turf', color('#3f6e35'), .9),
    'playground': pbr('asphalt', 'Playground_sand', '#c9b48a', .3),
    'glass_dark': solid_material('Window_dark', color('#27353b'), .12, .35), 'metal_sill': solid_material('Window_sill', color('#7d8183'), .45, .6),
    'concrete': pbr('plaster', 'Concrete', '#b9b6ae', .4), 'coping': solid_material('Coping', color('#55585a'), .5, .4),
    'chimney': pbr('brick', 'Chimney_brick', None, .6), 'sign_dark': solid_material('Sign_dark', color('#1c2224'), .8),
    'trim_light': solid_material('Trim_light', color('#ece8de'), .65), 'trim_dark': solid_material('Trim_darkgreen', color('#2f4a3a'), .6),
    'lamp_glass': solid_material('Lamp_glass', color('#f4ead2'), .3),
    'soil': pbr('grass', 'Planter_soil', '#413b2e', .35),
})
_cache = {}


def cached(key, make):
    if key not in _cache: _cache[key] = make()
    return _cache[key]


def quant(hexc, steps=6):
    v = hexc.lstrip('#'); c = [int(v[i:i + 2], 16) for i in (0, 2, 4)]
    return '#' + ''.join('%02x' % (min(255, round(x / (255 / steps)) * round(255 / steps))) for x in c)


def wall_mat(b):
    if b.get('reviewed_cottage'):
        c = b['facade_color']
        return cached(('clapboard',c),lambda:pbr('plaster','Reviewed_clapboard_'+c.lstrip('#'),c,.10))
    if b['facade_material'] == 'brick':
        return M['brick']
    key = 'wood' if b['facade_material'] == 'wood' else 'plaster'
    c = b['facade_color']
    return cached(('wall', key, c), lambda: pbr('wood_painted' if key == 'wood' else 'plaster', 'Wall_%s_%s' % (key, c.lstrip('#')), c, .55 if key == 'wood' else .3))


def roof_mat(b):
    rm = b['roof_material']; c = quant(b.get('roof_color', '#6b6a66'))
    if rm == 'roof_tiles': return cached(('roof', 'tile', c), lambda: pbr('roof_tiles', 'Roof_tile_%s' % c.lstrip('#'), c, .6))
    if rm == 'roof_tiles_grey': return cached(('roof', 'grey', c), lambda: pbr('roof_tiles', 'Roof_concrete_tile_%s' % c.lstrip('#'), c, .55))
    return cached(('roof', 'metal', c), lambda: solid_material('Roof_metal_%s' % c.lstrip('#'), color(c), .55, .2))


def roof_flat(b): return cached(('flat',), lambda: solid_material('Roof_felt', color('#3a3c3e'), .92))


DOORS = ['#2f4a3a', '#5a3a28', '#7a2a22', '#3b4a5a', '#24282a', '#6d6a5e']
BALC = ['#e8e4dc', '#9aa3a8', '#7d5a45', '#c2b59b']
def door_mat(b): c = DOORS[int(h01(b['id'], 'door') * len(DOORS))]; return cached(('door', c), lambda: solid_material('Door_%s' % c.lstrip('#'), color(c), .55))
def balc_mat(b): c = BALC[int(h01(b['id'], 'balc') * len(BALC))]; return cached(('balc', c), lambda: solid_material('Balcony_%s' % c.lstrip('#'), color(c), .6, .2))
def far_wall(b): c = quant(b['facade_color'], 4); return cached(('far', c), lambda: solid_material('Far_wall_%s' % c.lstrip('#'), color(c), .85))
def far_roof(b): c = quant(b.get('roof_color', '#555555'), 4); return cached(('farr', c), lambda: solid_material('Far_roof_%s' % c.lstrip('#'), color(c), .8))


M.update(wall=wall_mat, roof_for=roof_mat, roof_flat=roof_flat, door=door_mat, balcony=balc_mat, far_wall=far_wall, far_roof=far_roof)
M['reviewed_trim'] = lambda b: cached(('reviewed_trim',b['trim_color']),lambda:solid_material('Reviewed_ochre_trim',color(b['trim_color']),.72))
M['reviewed_sash'] = lambda b: cached(('reviewed_sash',b['sash_color']),lambda:solid_material('Reviewed_redbrown_sash',color(b['sash_color']),.68))


def tile_of(x, z): return '%d_%d' % (math.floor(x / TILE), math.floor(z / TILE))


# ---------- terräng ----------
T = SITE['terrain']; NX, NZ, X0, Z0, ST = T['nx'], T['nz'], T['x0'], T['z0'], T['step']
TH = T['heights']; TL = T['land']


def ground(x, z):
    fx = max(0, min(NX - 1.001, (x - X0) / ST)); fz = max(0, min(NZ - 1.001, (z - Z0) / ST)); i = int(fx); k = int(fz); tx = fx - i; tz = fz - k
    h = lambda a, b: TH[b * NX + a]
    return (h(i, k) * (1 - tx) + h(i + 1, k) * tx) * (1 - tz) + (h(i, k + 1) * (1 - tx) + h(i + 1, k + 1) * tx) * tz


for k in range(NZ - 1):
    for i in range(NX - 1):
        ids = [k * NX + i, k * NX + i + 1, (k + 1) * NX + i + 1, (k + 1) * NX + i]
        xs = [X0 + i * ST, X0 + (i + 1) * ST, X0 + (i + 1) * ST, X0 + i * ST]; zs = [Z0 + k * ST, Z0 + k * ST, Z0 + (k + 1) * ST, Z0 + (k + 1) * ST]
        ys = [TH[j] for j in ids]
        land = [sum(TL[j][c] for j in ids) / 4 for c in range(4)]
        slope = (max(ys) - min(ys)) / ST
        mat = M['rock'] if (land[3] > 0.5 or slope > 0.95) else M['forest'] if land[2] > 0.6 else M['grass']
        t = tile_of(xs[0], zs[0])
        tile_m = mat.get('tile_size_m', 2.5)
        replacement = SITE.get('terrain_overrides', {}).get(str(k * (NX - 1) + i))
        faces = [[(x, -z, y) for x, y, z in tri][::-1] for tri in replacement] if replacement is not None else [[(x, -z, y) for x, y, z in zip(xs, ys, zs)][::-1]]
        for pts in faces:
            if (pts[1][0] - pts[0][0]) * (pts[2][1] - pts[0][1]) - (pts[1][1] - pts[0][1]) * (pts[2][0] - pts[0][0]) < 0: pts.reverse()
            K.face('Terrain' + t, mat, pts, [(p[0] / tile_m, p[1] / tile_m) for p in pts])
            K.face('COL_Terrain' + t, M['collision'], pts)
log(f'terräng zon: {(NX - 1) * (NZ - 1)} rutor')
C = SITE['terrain_backdrop']; CX, CZ, CX0, CZ0, CS = C['nx'], C['nz'], C['x0'], C['z0'], C['step']; CH = C['heights']
fx0, fz0, fx1, fz1 = X0 + ST, Z0 + ST, X0 + (NX - 2) * ST, Z0 + (NZ - 2) * ST
for k in range(CZ - 1):
    for i in range(CX - 1):
        xa, xb, za, zb = CX0 + i * CS, CX0 + (i + 1) * CS, CZ0 + k * CS, CZ0 + (k + 1) * CS
        if xa >= fx0 and xb <= fx1 and za >= fz0 and zb <= fz1: continue
        ids = [k * CX + i, k * CX + i + 1, (k + 1) * CX + i + 1, (k + 1) * CX + i]
        ys = [CH[j] - (1.5 if (fx0 - 8 < xa < fx1 + 8 and fz0 - 8 < za < fz1 + 8) else 0.0) for j in ids]
        pts = [(x, -z, y) for x, y, z in zip([xa, xb, xb, xa], ys, [za, za, zb, zb])][::-1]
        K.face('FarTerrain' + tile_of(xa, za), M['forest'] if h01(i // 6, k // 6) < 0.45 else M['grass'], pts, [(p[0] / 8, p[1] / 8) for p in pts])
log('terräng kuliss klar')

# ---------- byggda ytor ----------
MAT = {'asphalt': M['asphalt'], 'paving': M['paving'], 'walkway': M['walkway'], 'trail': M['trail'], 'pitch': M['pitch'], 'playground': M['playground'], 'water': M['water'], 'soil': M['soil']}
for key, kind in SITE.get('roten_mesh_kinds', {}).items():
    MAT[key] = M[{'gravel': 'trail', 'rock': 'rock', 'grass': 'grass', 'paving': 'paving'}[kind]]
for key, kind in SITE.get('stalliden_mesh_kinds', {}).items():
    MAT[key] = M[kind]
for key, kind in SITE.get('stalliden_garden_mesh_kinds', {}).items():
    MAT[key] = M[kind]
reviewed_setts = roten.sett_segments(CITY)
for kind, tiles in SITE['meshes'].items():
    mat = MAT[kind]; tm = mat.get('tile_size_m', 3)
    for t, tris in tiles.items():
        for tri in tris:
            selected = M['paving'] if kind in ('asphalt', 'walkway', 'trail') and roten.is_sett(tri, reviewed_setts) else mat
            tm = selected.get('tile_size_m', 3)
            pts = [(x, -z, y) for x, y, z in tri]
            if ((pts[1][0] - pts[0][0]) * (pts[2][1] - pts[0][1]) - (pts[1][1] - pts[0][1]) * (pts[2][0] - pts[0][0])) < 0: pts.reverse()
            is_m29 = kind.startswith('m29_')
            is_stalliden = kind.startswith('stalliden_')
            render_name = 'Roten_ground_' + kind + t if is_m29 else 'Stalleliden_ground_' + kind + t if is_stalliden else kind.title() + t
            col_name = 'COL_Roten_ground_' + kind + t if is_m29 else 'COL_Stalleliden_ground_' + kind + t if is_stalliden else 'COL_' + kind + t
            if kind not in SITE.get('roten_collision_only', []) + SITE.get('stalliden_collision_only', []):
                K.face(render_name, selected, pts, [(p[0] / tm, p[1] / tm) for p in pts])
            if kind != 'water': K.face(col_name, M['collision'], pts)
for x1, y1, z1, x2, y2, z2 in SITE['kerbs']:
    L = math.hypot(x2 - x1, z2 - z1)
    if L < 0.05: continue
    u = ((x2 - x1) / L, -(z2 - z1) / L)
    K.box('Kerbs' + tile_of(x1, z1), M['curb'], ((x1 + x2) / 2, -(z1 + z2) / 2, (y1 + y2) / 2 - .1), (L + .02, .14, .22), u)
log('gator, kantsten klara')
roten.build_garden(K, M, SITE.get('roten_m29', {}))
stairkit.build(K, M, SITE.get('stalliden', {}), ground)
stairkit.garden(K, M, SITE.get('stalliden_garden', {}))
for xa, za, ta, ba, xb, zb, tb, bb in SITE.get('roten_supports', []):
    pts = [(xa,-za,ba),(xb,-zb,bb),(xb,-zb,tb),(xa,-za,ta)]
    K.face('Roten_ground_edges', M['rock'], pts)
    K.face('Roten_ground_edges', M['rock'], pts[::-1])
    K.face('COL_Roten_ground_edges', M['collision'], pts)

# Authored Torget surfaces are cut into the ground and have filled edge faces.
# The foundations meet terrain below; they are not unsupported floating slabs.
for xa, za, ta, ba, xb, zb, tb, bb in SITE.get('authored_supports', []):
    pts = [(xa, -za, ba), (xb, -zb, bb), (xb, -zb, tb), (xa, -za, ta)]
    t = tile_of(xa, za)
    K.face('Paving_foundation' + t, M['stone'], pts)
    K.face('Paving_foundation' + t, M['stone'], pts[::-1])
    K.face('COL_Paving_foundation' + t, M['collision'], pts)
for xa, ya, za, xb, yb, zb in SITE.get('planter_kerbs', []):
    L = math.hypot(xb - xa, zb - za)
    if L < .01: continue
    u = ((xb - xa) / L, -(zb - za) / L)
    centre = ((xa + xb) / 2, -(za + zb) / 2, (ya + yb) / 2 + .08)
    size = (L + .015, .18, .26)
    t = tile_of(xa, za)
    K.box('Planter_kerb' + t, M['curb'], centre, size, u)
    K.box('COL_Planter_kerb' + t, M['collision'], centre, size, u)
for x, y, z, s, v, yaw in SITE.get('authored_trees', []):
    # Only the young street-tree trunks block walking; foliage is permeable.
    K.beam('COL_Young_tree' + tile_of(x, z), M['collision'], (x, -z, y - .05), (x, -z, y + 2.1), .09, 8)

# ---------- åmurar ----------
for w in SITE['river_walls']:
    a, b = w['a'], w['b']; L = math.dist(a, b)
    if L < 0.05: continue
    u = ((b[0] - a[0]) / L, -(b[1] - a[1]) / L); o = (w['out'][0], -w['out'][1])
    cx, cy = (a[0] + b[0]) / 2 + w['out'][0] * .2, -(a[1] + b[1]) / 2 - w['out'][1] * .2
    top, bot = w['top_y'], w['bottom_y']
    t = tile_of(a[0], a[1])
    K.box('River_wall' + t, M['stone'], (cx, cy, (top + bot) / 2), (L + .05, .45, top - bot), u)
    K.box('River_cap' + t, M['curb'], (cx, cy, top + .06), (L + .05, .6, .14), u)
    K.box('COL_River_wall' + t, M['collision'], (cx, cy, (top + bot) / 2 + .6), (L + .05, .45, top - bot + 1.2), u)
    if top - bot > 2.0:
        p0 = (a[0] + w['out'][0] * .1, -a[1] - w['out'][1] * .1); p1 = (b[0] + w['out'][0] * .1, -b[1] - w['out'][1] * .1)
        for hh in (.55, 1.05): K.beam('River_rail' + t, M['iron'], (p0[0], p0[1], top + .12 + hh), (p1[0], p1[1], top + .12 + hh), .025)
        K.beam('River_rail' + t, M['iron'], (p0[0], p0[1], top + .12), (p0[0], p0[1], top + 1.18), .035)
log('åmurar klara')

# ---------- broar ----------
for br in SITE['bridges']:
    P = br['points']; W = br['width_m']; foot = br['kind'] in ('footway', 'path', 'steps', 'cycleway', 'track', 'pedestrian')
    deck = M['trail'] if foot else M['asphalt']; t = tile_of(P[0][0], P[0][2])
    for (xa, ya, za), (xb, yb, zb) in zip(P, P[1:]):
        L = math.hypot(xb - xa, zb - za)
        if L < 1e-3: continue
        ux, uz = (xb - xa) / L, (zb - za) / L; ox, oz = -uz * W / 2, ux * W / 2
        A = [(xa + ox, -(za + oz), ya), (xa - ox, -(za - oz), ya), (xb - ox, -(zb - oz), yb), (xb + ox, -(zb + oz), yb)]
        top = A if ((A[1][0] - A[0][0]) * (A[2][1] - A[0][1]) - (A[1][1] - A[0][1]) * (A[2][0] - A[0][0])) > 0 else A[::-1]
        K.face('Bridge_deck' + t, deck, top); K.face('COL_Bridge' + t, M['collision'], top)
        for s in (1, -1):
            p0 = (xa + ox * s, -(za + oz * s)); p1 = (xb + ox * s, -(zb + oz * s))
            K.face('Bridge_side' + t, M['stone' if not foot else 'iron'], [(p0[0], p0[1], ya - .6), (p1[0], p1[1], yb - .6), (p1[0], p1[1], yb), (p0[0], p0[1], ya)])
            K.face('Bridge_side' + t, M['stone' if not foot else 'iron'], [(p0[0], p0[1], ya), (p1[0], p1[1], yb), (p1[0], p1[1], yb - .6), (p0[0], p0[1], ya - .6)])
            for hh in (.5, 1.05): K.beam('Bridge_rail' + t, M['iron'], (p0[0], p0[1], ya + hh), (p1[0], p1[1], yb + hh), .03)
            K.beam('Bridge_rail' + t, M['iron'], (p0[0], p0[1], ya), (p0[0], p0[1], ya + 1.08), .03)
            K.box('COL_Bridge_rail' + t, M['collision'], ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (ya + yb) / 2 + .6), (L, .12, 1.2), (ux, -uz))
    G = br['ground_y']; acc = 0.0
    for idx in range(1, len(P) - 1):
        acc += math.hypot(P[idx][0] - P[idx - 1][0], P[idx][2] - P[idx - 1][2])
        if acc >= 14 and P[idx][1] - G[idx] > 3.0:
            acc = 0; K.box('Bridge_pier' + t, M['stone'], (P[idx][0], -P[idx][2], (P[idx][1] + G[idx] - 1) / 2), (1.0, W * .7, P[idx][1] - G[idx] + 1), (1, 0))
log(f'broar: {len(SITE["bridges"])}')

# ---------- trappor (Royens trappor m.fl.): steg à ~16 cm, räcken, osynlig ramp för gång ----------
for st in SITE.get('stairs', []):
    P = st['points']; W = st['width_m']; t = tile_of(P[0][0], P[0][2])
    h0 = P[0][1]
    q = lambda y: h0 + round((y - h0) / 0.16) * 0.16
    for (xa, ya, za), (xb, yb, zb) in zip(P, P[1:]):
        L = math.hypot(xb - xa, zb - za)
        if L < 1e-3: continue
        ux, uz = (xb - xa) / L, (zb - za) / L
        top = max(q(ya), q(yb)) if abs(yb - ya) < 0.02 else q((ya + yb) / 2)
        bottom = min(ground(xa, za), ground(xb, zb)) - 0.4
        K.box('Stairs' + t, M['stone'], ((xa + xb) / 2, -(za + zb) / 2, (top + bottom) / 2), (L + .02, W, top - bottom), (ux, -uz))
        ox, oz = -uz * W / 2, ux * W / 2
        A = [(xa + ox, -(za + oz), ya + .02), (xa - ox, -(za - oz), ya + .02), (xb - ox, -(zb - oz), yb + .02), (xb + ox, -(zb + oz), yb + .02)]
        A = A if ((A[1][0] - A[0][0]) * (A[2][1] - A[0][1]) - (A[1][1] - A[0][1]) * (A[2][0] - A[0][0])) > 0 else A[::-1]
        K.face('COL_Stairs' + t, M['collision'], A)
    for sgn in (1, -1):
        rail = []
        for i in range(0, len(P), 3):
            x, y, z = P[i]; j = min(i + 1, len(P) - 1); i0 = max(0, j - 1)
            dx, dz = P[j][0] - P[i0][0], P[j][2] - P[i0][2]; L = math.hypot(dx, dz) or 1
            rail.append((x - dz / L * W / 2 * sgn, -(z + dx / L * W / 2 * sgn), y))
        for a, b in zip(rail, rail[1:]):
            K.beam('Stair_rail' + t, M['iron'], (a[0], a[1], a[2] + .9), (b[0], b[1], b[2] + .9), .025)
        for a in rail[::2]:
            K.beam('Stair_rail' + t, M['iron'], (a[0], a[1], a[2]), (a[0], a[1], a[2] + .92), .025)
log(f'trappor: {len(SITE.get("stairs", []))}')

# ---------- hus ----------
heroes_done = 0; houses_done = 0
for b in CITY['buildings']:
    if b.get('authored_model') == 'roten_m29':
        roten.build_house(K, M, ground, b, CITY['reviewed_houses']['roten_m29'])
        heroes_done += 1
    elif b.get('archetype_family') == 'hero':
        if b['id'] == 'w92331981': heroes.build_krakan(K, M, ground, b, OFFSET)
        else: heroes.build_hero(K, M, ground, b)
        heroes_done += 1
    else:
        houses.build_house(K, b, M, ground, tile_of(*b['centroid_xz'])); houses_done += 1
log(f'hus: {heroes_done} hjältehus, {houses_done} tolkade')
for b in CITY['backdrop_buildings']:
    houses.build_backdrop_house(K, b, M, tile_of(*b['footprint_xz'][0]))
log(f'kulisshus: {len(CITY["backdrop_buildings"])}')

# ---------- gatlyktor ----------
for x, y, z, dx, dz in SITE['lamps']:
    t = tile_of(x, z); h = 5.2; ax, ay = x + dx * .8, -(z + dz * .8)
    K.beam('Streetlamps' + t, M['iron'], (x, -z, y), (x, -z, y + h), .06, 8)
    K.beam('Streetlamps' + t, M['iron'], (x, -z, y + h), (ax, ay, y + h - .08), .035, 6)
    K.box('Streetlamps' + t, M['iron'], (ax, ay, y + h - .16), (.5, .32, .14))
    K.box('Streetlamp_glass' + t, M['lamp_glass'], (ax, ay, y + h - .25), (.38, .24, .04))
    K.box('COL_Lamps' + t, M['collision'], (x, -z, y + h / 2), (.14, .14, h))

# ---------- gränsväggar ----------
zx0, zz0, zx1, zz1 = SITE['meta']['zone']
for (xa, za), (xb, zb) in [((zx0, zz0), (zx1, zz0)), ((zx1, zz0), (zx1, zz1)), ((zx1, zz1), (zx0, zz1)), ((zx0, zz1), (zx0, zz0))]:
    L = math.hypot(xb - xa, zb - za)
    K.box('COL_Bounds', M['collision'], ((xa + xb) / 2, -(za + zb) / 2, 40), (L + 2, 1.0, 140), ((xb - xa) / L, -(zb - za) / L))

objects = K.finish()
for obj in objects:
    if obj.name.startswith('COL_'): obj.hide_render = True; obj.display_type = 'WIRE'
    elif any(k in obj.name for k in ['Terrain', 'Water']) or (obj.name.startswith(('Roten_ground_', 'Stalleliden_ground_')) and not obj.name.startswith(('Roten_ground_edges', 'Stalleliden_ground_edges'))):
        bm = bmesh.new(); bm.from_mesh(obj.data); bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.0001); bm.to_mesh(obj.data); bm.free()
        for poly in obj.data.polygons: poly.use_smooth = True
log(f'objekt: {len(objects)}')

# ---------- träd ----------
names = ['Broadleaf_A', 'Broadleaf_B', 'Broadleaf_C']
for n, (x, y, z, s, v, yaw) in enumerate(SITE['trees']):
    place_tree(names[v], location=(x, -z, y), scale=s, yaw=yaw, name='Tree_%d' % n)
for n, (x, y, z, s, v, yaw) in enumerate(SITE.get('authored_trees', [])):
    place_tree(names[v], location=(x, -z, y), scale=s, yaw=yaw, name='Young_tree_%d' % n)
for n, (x, y, z, horizontal, vertical, v, yaw) in enumerate(SITE.get('shrubs', [])):
    root = place_tree(names[v], location=(x, -z, y), scale=1., yaw=yaw, name='Planter_shrub_%d' % n)
    root.scale = (horizontal, horizontal, vertical)
log(f'träd: {len(SITE["trees"])} skog + {len(SITE.get("authored_trees", []))} gatuträd + {len(SITE.get("shrubs", []))} låga buskproxyer')

# ---------- metadata för Godot ----------
pts = CITY['meta']['v1_points']


def eye(x, z, up=1.7): return [round(x, 2), round(ground(x, z) + up, 2), round(z, 2)]


def paved_eye(x, z):
    """Torget's review camera is 1.7 m above the rendered/COL floor, not buried terrain."""
    floor = ground(x, z)
    for kind in SITE['meshes']:
        if kind == 'water': continue
        for tiles in SITE['meshes'].get(kind, {}).values():
            for a, b, c in tiles:
                if not min(a[0], b[0], c[0]) - .001 <= x <= max(a[0], b[0], c[0]) + .001 or not min(a[2], b[2], c[2]) - .001 <= z <= max(a[2], b[2], c[2]) + .001: continue
                den = (b[2]-c[2])*(a[0]-c[0]) + (c[0]-b[0])*(a[2]-c[2])
                if abs(den) < 1e-10: continue
                u = ((b[2]-c[2])*(x-c[0]) + (c[0]-b[0])*(z-c[2])) / den
                v = ((c[2]-a[2])*(x-c[0]) + (a[0]-c[0])*(z-c[2])) / den
                if min(u, v, 1-u-v) >= -1e-6: floor = max(floor, u*a[1] + v*b[1] + (1-u-v)*c[1])
    return [round(x, 2), round(floor + 1.7, 3), round(z, 2)]


views = [
    dict(id='spawn', name='Görjelycksgatan (start)', position=eye(*pts['spawn']), target=[pts['spawn'][0] - 60, ground(*pts['spawn']) + 4, pts['spawn'][1] - 70]),
    dict(id='torget', name='Gamla torget', position=paved_eye(-8.5, 8), target=[-40, 4.5, -8]),
    dict(id='krakan', name='Kråkans krog', position=eye(8, 48), target=[11, 2.2, 30]),
    dict(id='roten', name='Roten M', position=eye(pts['cap_B'][0] + 14, pts['cap_B'][1] + 12), target=[pts['cap_B'][0] - 30, ground(*pts['cap_B']) + 3, pts['cap_B'][1] - 25]),
    dict(id='roten-gavel', name='Roten M 29 – gaveln', position=paved_eye(120.7, 114.7), target=[105.8, 27.0, 120.5]),
    dict(id='roten-gard', name='Roten M 29 – gården', position=paved_eye(106.5, 116.5), target=[101.7, 25.2, 119.0]),
    dict(id='roten-tradgard', name='Roten M 29 – trädgården', position=paved_eye(95, 132.5), target=[97.7, 25.3, 123]),
    dict(id='m30', name='Roten M 30', position=paved_eye(109,114), target=[100.9,27.5,103.4]),
    dict(id='stalleliden-ovre', name='Stalleliden – övre delen', position=paved_eye(85.5,99.1), target=[63,18.5,98]),
    dict(id='stalleliden-mitt', name='Stalleliden – mittpartiet', position=paved_eye(35,83.3), target=[53,14,85]),
    dict(id='stalleliden-nedre', name='Stalleliden – nedre delen', position=paved_eye(16.5,90.3), target=[48,14,83]),
    dict(id='royen', name='Royens trappor', position=eye(*pts['cap_C']), target=[pts['cap_C'][0] - 50, ground(*pts['cap_C']) + 2, pts['cap_C'][1] + 30]),
    dict(id='oversikt', name='Överblick', position=[180, 150, 330], target=[60, 0, 40], free_flight=True),
]
probe = []
for r in CITY['roads']:
    if r['tunnel'] or r['bridge'] or r['kind'] in ('path', 'track', 'steps'): continue
    pts_ = r['line_xz']
    acc = 0.0
    for (xa, za), (xb, zb) in zip(pts_, pts_[1:]):
        L = math.hypot(xb - xa, zb - za); acc += L
        if acc > 45 and zx0 + 3 < xa < zx1 - 3 and zz0 + 3 < za < zz1 - 3:
            acc = 0; probe.append([round(xa, 2), round(ground(xa, za), 2), round(za, 2)])
meta = dict(title='Kvarnbyn', probe_points=probe, stalliden_ground_checks=SITE.get('stalliden', {}).get('ground_checks', {}), m29_ground_checks=SITE.get('roten_m29', {}).get('ground_checks', {}),
            spawn=dict(position=[round(pts['spawn'][0], 2), round(ground(*pts['spawn']), 2), round(pts['spawn'][1], 2)],
                                          target=views[0]['target'], snap_to_ground=True),
            views=views, bounds=dict(min=[zx0, -40, zz0], max=[zx1, 120, zz1]),
            lamps=[[x, y + 4.95, z] for x, y, z, dx, dz in SITE['lamps']],
            attribution=['Kartdata © OpenStreetMap-bidragsgivare (ODbL)', 'Höjddata och ortofoto: Lantmäteriet', 'Material, lövatlas och himmel: Poly Haven (CC0)', 'Modeller: projektet Försvara Kvarnbyn'],
            notes=['Fas A: tolkade hus (assumed) + handgranskade hjältehus vid torget (observed).'])
(GODOT / 'world_meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1))

if options.save_blend:
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'world.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUT / 'world_raw.glb'), export_format='GLB', export_cameras=False, export_lights=False, export_apply=True,
                          export_yup=True, export_extras=True, export_image_format='AUTO', export_materials='EXPORT')
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('COL_') and o.users_collection and not o.name.startswith(('Broadleaf',)) and '_Bark' not in o.name and '_Leaves' not in o.name)
report = dict(objects=len(bpy.data.objects), meshes=len(bpy.data.meshes), materials=len(bpy.data.materials), triangles_excl_trees=tris,
              trees=len(SITE['trees']), authored_trees=len(SITE.get('authored_trees', [])), shrubs=len(SITE.get('shrubs', [])), raw_glb_mb=round((OUT / 'world_raw.glb').stat().st_size / 1e6, 1), seconds=round(time.time() - T0, 1))
((OUT if options.stage_dir else HERE / 'evidence') / 'scene_metrics.json').write_text(json.dumps(report, indent=1))
print('SCENE_METRICS', json.dumps(report))

#!/usr/bin/env python3
"""Bygger public/flats.js ur osm_raw.json: byggda plana ytor + broar.

Filen bar tidigare två handextraherade listor (2026-08) för den gamla, mindre
kartan. Sedan kartan växte (+50 % radie, Pass B) saknade ytterområdet både
parkeringsplattning och brodäck — detta skript gör extraktionen reproducerbar
och körs efter build_data2.py (samma bbox via bbox.py, samma projektion).

  window.KVARNBYN_FLATS   = [{k, s, a, p}]   k: parking|pitch|playground|square
                                             s: surface-tagg ('' om saknas), a: m²
  window.KVARNBYN_BRIDGES = [{k, w, p}]      OSM bridge=yes-ways kedjade (samma
                                             highway-klass + namn, delad ändnod)
                                             till spann landfäste→landfäste

Körs i tools/:  python3 build_flats.py
"""
import json, math
from bbox import LAT0, LAT1, LON0, LON1

CLAT = (LAT0 + LAT1) / 2; CLON = (LON0 + LON1) / 2
MLAT = 111320.0; MLON = 111320.0 * math.cos(math.radians(CLAT))
def xz(lat, lon): return ((lon - CLON) * MLON, -(lat - CLAT) * MLAT)
def rnd(pts): return [[round(x, 1), round(z, 1)] for x, z in pts]

osm = json.load(open('osm_raw.json'))
nodes = {e['id']: (e['lat'], e['lon']) for e in osm['elements'] if e['type'] == 'node'}
ways = [e for e in osm['elements'] if e['type'] == 'way']
def coords(w): return [xz(*nodes[n]) for n in w['nodes'] if n in nodes]

def area(pts):
    a = 0.0
    for i in range(len(pts)):
        x1, z1 = pts[i]; x2, z2 = pts[(i + 1) % len(pts)]
        a += x1 * z2 - x2 * z1
    return abs(a) / 2

# ---- byggda plana ytor ----
flats = []
for w in ways:
    t = w.get('tags', {})
    if w['nodes'][0] != w['nodes'][-1] or len(w['nodes']) < 4: continue  # bara slutna ringar
    if 'building' in t: continue
    k = None
    if t.get('amenity') == 'parking':
        if t.get('parking') in ('multi-storey', 'underground', 'rooftop'): continue
        k = 'parking'
    elif t.get('leisure') in ('pitch', 'playground'): k = t['leisure']
    elif t.get('place') == 'square' or (t.get('highway') == 'pedestrian' and t.get('area') == 'yes'): k = 'square'
    if not k: continue
    pts = coords(w)[:-1]
    if len(pts) < 3: continue
    a = area(pts)
    if a < 40: continue  # småytor ger inget plattningsvärde men kostar
    flats.append({'k': k, 's': t.get('surface', ''), 'a': int(round(a)), 'p': rnd(pts)})

# ---- broar: kedja bridge=yes-ways med samma klass+namn via delade ändnoder ----
BRIDGE_W = {'path': 2.6, 'footway': 2.8, 'cycleway': 2.5, 'steps': 2.4, 'service': 4.5,
            'residential': 6.5, 'living_street': 5.5, 'unclassified': 6, 'tertiary': 8,
            'secondary': 8, 'primary': 9, 'trunk_link': 8, 'motorway_link': 8, 'motorway': 11}
bws = [w for w in ways if w.get('tags', {}).get('bridge') in ('yes', 'viaduct', 'movable')
       and w['tags'].get('highway') in BRIDGE_W and len(w['nodes']) >= 2]
used = set()
chains = []
def key(w): return (w['tags']['highway'], w['tags'].get('name', ''))
by_key = {}
for w in bws: by_key.setdefault(key(w), []).append(w)
for k, group in by_key.items():
    pool = {w['id']: list(w['nodes']) for w in group}
    while pool:
        wid, nds = pool.popitem()
        chain = list(nds); ids = [wid]
        grew = True
        while grew:
            grew = False
            for oid, onds in list(pool.items()):
                if onds[0] == chain[-1]: chain += onds[1:]
                elif onds[-1] == chain[0]: chain = onds[:-1] + chain
                elif onds[-1] == chain[-1]: chain += list(reversed(onds))[1:]
                elif onds[0] == chain[0]: chain = list(reversed(onds))[:-1] + chain
                else: continue
                del pool[oid]; ids.append(oid); grew = True
        pts = [xz(*nodes[n]) for n in chain if n in nodes]
        if len(pts) < 2: continue
        # ids = OSM-way-id:n i kedjan — game.js kopplar vägar till SIN bro via dem (inte närhet)
        chains.append({'k': k[0], 'w': BRIDGE_W[k[0]], 'ids': ids, 'p': rnd(pts)})

out = ('window.KVARNBYN_FLATS = ' + json.dumps(flats, separators=(',', ':'), ensure_ascii=False) + ';\n' +
       'window.KVARNBYN_BRIDGES = ' + json.dumps(chains, separators=(',', ':'), ensure_ascii=False) + ';\n')
open('../public/flats.js', 'w', encoding='utf-8').write(out)
import collections
print('flats:', len(flats), dict(collections.Counter(f['k'] for f in flats)))
print('brokedjor:', len(chains), 'ur', len(bws), 'bridge-ways;', dict(collections.Counter(c['k'] for c in chains)))
print('flats.js', len(out) // 1024, 'KB')

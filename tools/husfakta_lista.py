#!/usr/bin/env python3
"""Kandidatlista för husfakta: vilka hus är värda att titta på och beskriva i public/husfakta.js?

Skriver tools/husfakta_kandidater.md med, per hus: nyckel (w<id>), namn/POI, adress, vad OSM
redan vet (våningar, kulör, takform, material), vad husfakta.js redan säger, och länkar att
TITTA på: OSM-way:en och en Street View-vy vid huset (mänskligt referensmaterial — beskriv i
ord i husfakta.js, ta aldrig in bilderna i spelet; KRAVSPEC §4).

Urval: namngivna byggnader, hus som innehåller en restaurang-/POI-nod (poi.json), hus inom 30 m
från zonerna A/B/C och basen, samt Kvarnbykärnan (x 60–340, z −200–80) längs de namngivna gatorna.

Körs i tools/:  python3 husfakta_lista.py
"""
import json, math, re, pathlib
from bbox import LAT0, LAT1, LON0, LON1

here = pathlib.Path(__file__).resolve().parent
CLAT = (LAT0 + LAT1) / 2; CLON = (LON0 + LON1) / 2
MLAT = 111320.0; MLON = 111320.0 * math.cos(math.radians(CLAT))
def xz(lat, lon): return ((lon - CLON) * MLON, -(lat - CLAT) * MLAT)
def latlon(x, z): return (CLAT - z / MLAT, CLON + x / MLON)

src = (here.parent / 'public' / 'data.js').read_text(encoding='utf-8')
D = json.loads(src[src.index('=') + 1:].rstrip().rstrip(';'))
B = D['buildings']
hf_src = (here.parent / 'public' / 'husfakta.js').read_text(encoding='utf-8')
hf = {}
if 'KVARNBYN_HUSFAKTA' in hf_src:  # kommentarrader bort, sedan objektet efter '=' fram till sista ';'
    body = re.sub(r'^\s*//.*$', '', hf_src, flags=re.M).split('window.KVARNBYN_HUSFAKTA =', 1)[1].strip().rstrip(';')
    hf = json.loads(body)

def pip(x, z, P):
    w = False
    for i in range(len(P)):
        j = (i - 1) % len(P)
        if (P[i][1] > z) != (P[j][1] > z) and x < (P[j][0] - P[i][0]) * (z - P[i][1]) / (P[j][1] - P[i][1]) + P[i][0]: w = not w
    return w
def cen(p): return (sum(x for x, _ in p) / len(p), sum(z for _, z in p) / len(p))

poi = {}
try:
    for e in json.load(open(here / 'poi.json'))['elements']:
        t = e.get('tags', {})
        la = e.get('lat') or e.get('center', {}).get('lat'); lo = e.get('lon') or e.get('center', {}).get('lon')
        if not (la and lo and t.get('name')): continue
        x, z = xz(la, lo)
        for b in B:
            if pip(x, z, b['p']): poi.setdefault(b['id'], []).append(t['name'])
except FileNotFoundError:
    pass

zones = [tuple(c['pos']) for c in D['caps']] + [tuple(D['spawn'])]
rows = []
for b in B:
    if b['t'] in ('garage', 'garages', 'shed', 'carport', 'roof'): continue
    c = cen(b['p'])
    why = []
    if b.get('n'): why.append('namngiven')
    if b['id'] in poi: why.append('POI: ' + ', '.join(poi[b['id']]))
    if any(math.dist(c, zc) < 30 for zc in zones): why.append('vid zon')
    if 60 < c[0] < 340 and -200 < c[1] < 80 and b.get('addr'): why.append('Kvarnbykärnan')
    if not why: continue
    key = f"w{b['id']}"
    osm = ', '.join(f"{k}={b[k]}" for k in ('lv', 'col', 'rs', 'mat') if k in b) or '–'
    have = hf.get(key) or (b.get('addr') and hf.get(b['addr']))
    lat, lon = latlon(*c)
    rows.append((why, key, b.get('n', ''), b.get('addr', ''), osm,
                 ', '.join(f"{k}={v}" for k, v in (have or {}).items() if k not in ('kommentar', 'kalla')) or '–',
                 f"https://www.openstreetmap.org/way/{b['id']}",
                 f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat:.6f},{lon:.6f}"))

rows.sort(key=lambda r: (0 if any(w.startswith('POI') for w in r[0]) else 1 if 'namngiven' in r[0] else 2, r[3] or r[2]))
out = ['# Husfakta — kandidater att titta på', '',
       f'{len(rows)} hus. Öppna Street View-länken, TITTA, och skriv fakta i `public/husfakta.js` under nyckeln.',
       'Bilder tas aldrig in i spelet — bara beskrivningen (kulör, våningar, tak, material, skylt).', '',
       '| Varför | Nyckel | Namn | Adress | OSM vet | husfakta.js har | Länkar |', '|---|---|---|---|---|---|---|']
for why, key, n, addr, osm, have, osmurl, sv in rows:
    out.append(f"| {'; '.join(why)} | `{key}` | {n} | {addr} | {osm} | {have} | [OSM]({osmurl}) · [Street View]({sv}) |")
(here / 'husfakta_kandidater.md').write_text('\n'.join(out) + '\n', encoding='utf-8')
print(f'{len(rows)} kandidater → tools/husfakta_kandidater.md')

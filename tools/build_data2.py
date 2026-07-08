import json, math
import numpy as np
from PIL import Image, ImageDraw

osm = json.load(open('osm_raw.json'))
LAT0, LAT1, LON0, LON1 = 57.6495, 57.6625, 12.008, 12.044
CLAT = (LAT0+LAT1)/2; CLON = (LON0+LON1)/2
MLAT = 111320.0; MLON = 111320.0*math.cos(math.radians(CLAT))
def xz(lat, lon): return ((lon-CLON)*MLON, -(lat-CLAT)*MLAT)

nodes = {e['id']:(e['lat'],e['lon']) for e in osm['elements'] if e['type']=='node'}
ways = [e for e in osm['elements'] if e['type']=='way']
def way_coords(w): return [xz(*nodes[n]) for n in w['nodes'] if n in nodes]
def rnd(pts): return [[round(x,1),round(z,1)] for x,z in pts]

X0, Z1 = xz(LAT1, LON0)[0], xz(LAT1, LON0)[1]   # west, north(z neg)
X1, Z0 = xz(LAT0, LON1)[0], xz(LAT0, LON1)[1]   # east, south(z pos)

# ---- terräng: Lantmäteriets 1 m-LiDAR (lat/lon-linjärt, rad 0 = norr i filen) ----
full = np.load('lidar_full.npy').astype(float)  # (1447, 2144)
H, W = full.shape
ROWS, COLS = 724, 1072   # ~2 m rutnät i spelet
rr = np.linspace(H-1, 0, ROWS).round().astype(int)  # spelets rad 0 = söder
cc = np.linspace(0, W-1, COLS).round().astype(int)
elev = full[np.ix_(rr, cc)]
terrain = {'rows':ROWS,'cols':COLS,'x0':round(X0,1),'x1':round(X1,1),'z0':round(Z0,1),'z1':round(Z1,1),
           'elev':[round(float(v),1) for v in elev.flatten()]}
def elev_at(x, z):
    fx = (x-X0)/(X1-X0)*(COLS-1); fz = (z-Z0)/(Z1-Z0)*(ROWS-1)
    c = max(0,min(COLS-2,int(fx))); r = max(0,min(ROWS-2,int(fz)))
    tx=fx-c; tz=fz-r
    return float((elev[r,c]*(1-tx)+elev[r,c+1]*tx)*(1-tz) + (elev[r+1,c]*(1-tx)+elev[r+1,c+1]*tx)*tz)

# ---- ortho sampling for roof colors ----
ortho = Image.open('ortho_full.png'); OW, OH = ortho.size
oarr = np.asarray(ortho)
def to_px(x, z):
    return ((x-X0)/(X1-X0)*OW, (z-Z1)/(Z0-Z1)*OH)
def poly_color(poly):
    pxs = [to_px(p[0],p[1]) for p in poly]
    xs=[p[0] for p in pxs]; ys=[p[1] for p in pxs]
    x0,x1 = int(max(0,min(xs))), int(min(OW-1,max(xs)))
    y0,y1 = int(max(0,min(ys))), int(min(OH-1,max(ys)))
    if x1-x0 < 2 or y1-y0 < 2: return None
    mask = Image.new('L',(x1-x0,y1-y0),0)
    ImageDraw.Draw(mask).polygon([(px-x0,py-y0) for px,py in pxs], fill=1)
    m = np.asarray(mask).astype(bool)
    if m.sum() < 4: return None
    sub = oarr[y0:y1, x0:x1][m]
    med = np.median(sub, axis=0)  # median resists cloud/shadow edges
    # lift brightness and boost saturation (aerial photos are muted)
    import colorsys
    h,sv,v = colorsys.rgb_to_hsv(med[0]/255, med[1]/255, med[2]/255)
    sv = min(1.0, sv*1.75); v = min(1.0, v*1.45 + 0.06)
    r,g,b = [int(c*255) for c in colorsys.hsv_to_rgb(h,sv,v)]
    return f'{r:02x}{g:02x}{b:02x}'

buildings = []
for w in ways:
    t = w.get('tags',{})
    if 'building' not in t: continue
    pts = way_coords(w)
    if len(pts) < 4: continue
    if pts[0]==pts[-1]: pts = pts[:-1]
    if len(pts) < 3: continue
    levels = t.get('building:levels')
    try: levels = float(levels)
    except: levels = None
    h = t.get('height')
    try: h = float(str(h).replace('m','').strip())
    except: h = None
    if h is None:
        h = (levels or (1 if t['building'] in ('garage','garages','shed','carport') else 2))*3.0 + 1.5
    col = poly_color(pts) or '9a8f80'
    buildings.append({'p':rnd(pts),'h':round(h,1),'t':t['building'],'n':t.get('name',''),'c':col})
print('buildings with colors:', len(buildings))

ROAD_W = {'primary':9,'secondary':8,'tertiary':7,'residential':6,'living_street':5.5,'unclassified':6,
          'service':4,'pedestrian':4,'footway':2.2,'path':1.8,'steps':2.5,'cycleway':2.5,'track':3}
roads = []
for w in ways:
    t = w.get('tags',{})
    hw = t.get('highway')
    if hw not in ROAD_W: continue
    pts = way_coords(w)
    if len(pts) >= 2: roads.append({'p':rnd(pts),'w':ROAD_W[hw],'k':hw,'n':t.get('name','')})

water = []
for w in ways:
    t = w.get('tags',{})
    if t.get('natural')=='water':
        closed = len(w['nodes']) > 3 and w['nodes'][0] == w['nodes'][-1]
        pts = way_coords(w)
        if closed and len(pts)>=4:
            water.append({'p':rnd(pts),'poly':True})
        elif len(pts)>=2:
            water.append({'p':rnd(pts),'poly':False})  # open shoreline piece -> ribbon
    elif t.get('waterway') in ('river','stream','canal'):
        pts = way_coords(w)
        if len(pts)>=2: water.append({'p':rnd(pts),'poly':False})

green = []
for w in ways:
    t = w.get('tags',{})
    forest = t.get('landuse') == 'forest' or t.get('natural') in ('wood','scrub')
    other = t.get('landuse') in ('grass','meadow','recreation_ground','cemetery') or t.get('leisure') in ('park','pitch','playground','garden')
    if forest or other:
        pts = way_coords(w)
        if len(pts)>=3: green.append({'p':rnd(pts),'k':'forest' if forest else 'green'})
print('skogspolygoner:', sum(1 for g in green if g['k']=='forest'))

def street_pts(name):
    out=[]
    for rd in roads:
        if rd['n']==name: out += rd['p']
    return out
def centroid(name):
    pts = street_pts(name)
    return [round(sum(p[0] for p in pts)/len(pts),1), round(sum(p[1] for p in pts)/len(pts),1)]

gp = street_pts('Görjelycksgatan')
spawn = max(gp, key=lambda p: elev_at(p[0],p[1]))
capA, capB, capC = centroid('Gamla Torget'), centroid('Roten M'), centroid('Royens trappor')
entry = min(street_pts('Forsebron'), key=lambda p: elev_at(p[0],p[1]))
entry = [round(entry[0],1), round(entry[1],1)]

# ---- landmarks ----
marks = []
def bld_centroid(name_sub):
    for b in buildings:
        if name_sub.lower() in b['n'].lower():
            xs=[p[0] for p in b['p']]; zs=[p[1] for p in b['p']]
            return [round(sum(xs)/len(xs),1), round(sum(zs)/len(zs),1)], b['h']
    return None, None
for nm, kind in [('Kvarnbytornet','bld'),('Mölndal Galleria','bld'),('Mölndal stadsmuseum','bld'),
                 ('Fässbergs kyrka','bld'),('Mölndals Stadshus','bld'),('Kulturhuset Möllan','bld')]:
    pos, h = bld_centroid(nm)
    if pos: marks.append({'n':nm,'p':pos,'h':round(h+18,0),'k':'bld'})
for nm in ['Götaforsliden','Kvarnbygatan','Forsebron','Görjelycksgatan']:
    marks.append({'n':nm,'p':centroid(nm),'h':14,'k':'street'})
for nm, street in [('Mölndals centrum','Mölndals Torg'),('Glasberget','Glasbergsgatan'),
                   ('Kikås','Kikåsgatan'),('Störtfjället','Störtfjällsgatan'),('Forsåker','Norra Forsåkersgatan')]:
    marks.append({'n':nm,'p':centroid(street),'h':40,'k':'district'})
for m in marks: print(m['n'], m['p'], round(elev_at(m['p'][0],m['p'][1]),1),'m')

walls = []
for w in ways:
    t = w.get('tags',{})
    k = t.get('barrier')
    if t.get('natural') == 'cliff': k = 'cliff'
    if k in ('wall','retaining_wall','fence','hedge','city_wall','guard_rail','cliff'):
        pts = way_coords(w)
        if len(pts) >= 2: walls.append({'p':rnd(pts),'k':k})
print('walls:', len(walls))

data = {'terrain':terrain,'buildings':buildings,'roads':roads,'water':water,'green':green,'walls':walls,
        'spawn':spawn,'caps':[{'id':'A','name':'Gamla Torget','pos':capA,'r':16},
                              {'id':'B','name':'Roten M','pos':capB,'r':15},
                              {'id':'C','name':'Royens trappor','pos':capC,'r':15}],
        'enemyEntry':entry,'marks':marks}
out = 'window.KVARNBYN_DATA = ' + json.dumps(data, separators=(',',':'), ensure_ascii=False) + ';'
open('data.js','w',encoding='utf-8').write(out)
print('data.js', len(out)//1024, 'KB | spawn', spawn, round(elev_at(*spawn),1),'m')

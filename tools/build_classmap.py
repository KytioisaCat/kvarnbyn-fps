"""Klasskarta för marken (2 m/cell): R=asfalt, G=gräs, B=skog, svart(=inget)=berg.
Kombinerar ortofotots färg+textur, LiDAR-lutning/lokala toppar, OSM-polygoner
(skog, parkering, berg, byggnader, vägar). Skrivs till classmap.png."""
import json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

LON0, LON1, LAT0, LAT1 = 12.008, 12.044, 57.6495, 57.6625
CLAT, CLON = (LAT0+LAT1)/2, (LON0+LON1)/2
MLAT = 111320.0; MLON = 111320.0*math.cos(math.radians(CLAT))
def xz(lat, lon): return ((lon-CLON)*MLON, -(lat-CLAT)*MLAT)
X0, Z1 = xz(LAT1, LON0); X1, Z0 = xz(LAT0, LON1)   # väst, norr / öst, syd

COLS, ROWS = 1072, 724   # 2 m/cell, rad 0 = norr
def to_px(x, z): return ((x-X0)/(X1-X0)*COLS, (z-Z1)/(Z0-Z1)*ROWS)

osm = json.load(open('osm_raw.json'))
nodes = {e['id']:(e['lat'],e['lon']) for e in osm['elements'] if e['type']=='node'}
ways = [e for e in osm['elements'] if e['type']=='way']
def coords(w): return [to_px(*xz(*nodes[n])) for n in w['nodes'] if n in nodes]

def raster(draw_fn):
    im = Image.new('L', (COLS, ROWS), 0)
    draw_fn(ImageDraw.Draw(im))
    return np.asarray(im) > 0

ROAD_W = {'primary':9,'secondary':8,'tertiary':7,'residential':6,'living_street':5.5,'unclassified':6,
          'service':4,'pedestrian':4,'footway':2.2,'path':1.8,'steps':2.5,'cycleway':2.5,'track':3}
def draw_roads(d):
    for w in ways:
        t = w.get('tags',{})
        if t.get('highway') not in ROAD_W: continue
        pts = coords(w)
        if len(pts) < 2: continue
        d.line(pts, fill=255, width=max(1, round((ROAD_W[t['highway']]+1)/2)))
def draw_parking(d):
    for w in ways:
        if w.get('tags',{}).get('amenity')=='parking':
            p = coords(w)
            if len(p) >= 3: d.polygon(p, fill=255)
def draw_wood(d):
    for w in ways:
        t = w.get('tags',{})
        if t.get('natural') in ('wood','scrub') or t.get('landuse')=='forest':
            p = coords(w)
            if len(p) >= 3: d.polygon(p, fill=255)
def draw_rock(d):
    for w in ways:
        if w.get('tags',{}).get('natural') in ('bare_rock','scree','rock'):
            p = coords(w)
            if len(p) >= 3: d.polygon(p, fill=255)
def draw_bld(d):
    for w in ways:
        if 'building' in w.get('tags',{}):
            p = coords(w)
            if len(p) >= 3: d.polygon(p, fill=255)
def draw_water(d):
    for w in ways:
        t = w.get('tags',{})
        if t.get('waterway') in ('river','stream','canal'):
            p = coords(w)
            if len(p) >= 2: d.line(p, fill=255, width=6)

roads = raster(draw_roads); parking = raster(draw_parking)
wood = raster(draw_wood); rockOsm = raster(draw_rock)
bld = raster(draw_bld); water = raster(draw_water)
# husnärhet/hustäthet: andel husyta inom ~25 m
bimg = Image.fromarray((bld*255).astype(np.uint8)).filter(ImageFilter.BoxBlur(12))
bldDens = np.asarray(bimg).astype(float)/255.0

# ---- ortofoto-statistik per cell (medel + texturstd av luminans) ----
ortho = np.asarray(Image.open('ortho_full.png'), dtype=float)  # 4530x6711
OH, OW = ortho.shape[:2]
bh, bw = OH//ROWS, OW//COLS   # ~6x6 px per cell
o = ortho[:ROWS*bh, :COLS*bw]
blk = o.reshape(ROWS, bh, COLS, bw, 3)
mean = blk.mean(axis=(1,3))                      # (ROWS,COLS,3)
lum = o @ np.array([0.299,0.587,0.114])
lblk = lum[:ROWS*bh//bh*bh, :].reshape(ROWS, bh, COLS, bw)
tex = lblk.std(axis=(1,3))
R,G,B = mean[:,:,0], mean[:,:,1], mean[:,:,2]
L = 0.299*R+0.587*G+0.114*B
sat = (mean.max(axis=2)-mean.min(axis=2))/(mean.max(axis=2)+1e-6)
green = G - (R+B)/2

# ---- LiDAR: lutning + lokal prominens ----
dem = np.load('lidar_full.npy')                  # 1447x2144, 1 m, rad0=norr
gy, gx = np.gradient(dem)
slope1 = np.hypot(gx, gy)
ri = np.clip((np.arange(ROWS)+0.5)*dem.shape[0]/ROWS, 0, dem.shape[0]-1).astype(int)
ci = np.clip((np.arange(COLS)+0.5)*dem.shape[1]/COLS, 0, dem.shape[1]-1).astype(int)
slope = slope1[np.ix_(ri, ci)]
def boxblur(a, r):
    k = 2*r+1
    c = np.cumsum(np.cumsum(np.pad(a, ((r+1,r),(r+1,r)), mode='edge'), axis=0), axis=1)
    return (c[k:,k:]-c[:-k,k:]-c[k:,:-k]+c[:-k,:-k])/(k*k)
demC = dem[np.ix_(ri, ci)]
prom = demC - boxblur(demC, 20)                  # topp som sticker upp ur ~40 m-omgivning

# ---- klassning ----
CLS = np.full((ROWS, COLS), 1, dtype=np.uint8)   # 0=asfalt 1=gräs 2=skog 3=berg
texN = tex / (L + 12)                            # texturmått, normaliserat mot ljushet
# skog: OSM-facit ELLER knottrigt+mörkt utan hustäthet ELLER mörk brant (skuggig skogssluttning)
forest = wood \
       | ((texN > 0.16) & (L < 118) & (bldDens < 0.12) & ~bld) \
       | ((L < 58) & (slope > 0.30) & ~bld) \
       | ((texN > 0.20) & (L < 100) & ~bld)
# berg: OSM ELLER grå+slät+ogrön yta som är brant/uppstickande — även inne bland husen (Glasberget!)
rock = rockOsm \
     | ((green < 6) & (sat < 0.15) & (L > 78) & (texN < 0.13) & ((slope > 0.35) | (prom > 1.2)) & ~bld) \
     | ((sat < 0.07) & (L > 108) & (texN < 0.10) & (bldDens < 0.22) & ~bld)   # öppna hällar/bergsplatåer
CLS[forest] = 2
CLS[rock & ~wood & ~(forest & ~wood)] = 3
CLS[water] = 1
CLS[roads | parking] = 0
CLS[bld] = 1

out = np.zeros((ROWS, COLS, 3), dtype=np.uint8)
out[CLS==0] = (255,0,0); out[CLS==1] = (0,255,0); out[CLS==2] = (0,0,255); out[CLS==3] = (0,0,0)
img = Image.fromarray(out).filter(ImageFilter.GaussianBlur(0.6))
img.save('classmap.png')

def spot(x, z, label, r=0):
    px, pz = to_px(x, z)
    # arealsökning: dominant klass (utom gräs) inom radien r meter, annars mittcellen
    if r:
        rr = int(r/2)
        sub = CLS[max(0,int(pz)-rr):int(pz)+rr, max(0,int(px)-rr):int(px)+rr]
        import collections
        cnt = collections.Counter(sub.flatten().tolist())
        print(f"{label:38s} → omgivning {r} m: " + ' '.join(f"{['asfalt','gräs','skog','berg'][k]}={v*100//sub.size}%" for k,v in cnt.most_common()))
        return
    c = CLS[int(pz), int(px)]
    print(f"{label:38s} → {['asfalt','gräs','skog','berg'][c]}  (L={L[int(pz),int(px)]:.0f} tex={texN[int(pz),int(px)]:.2f} sat={sat[int(pz),int(px)]:.2f} slope={slope[int(pz),int(px)]:.2f} prom={prom[int(pz),int(px)]:.1f} husD={bldDens[int(pz),int(px)]:.2f})")
print('andelar: asfalt %.1f%% gräs %.1f%% skog %.1f%% berg %.1f%%' % tuple((CLS==i).mean()*100 for i in range(4)))
spot(895, 415, 'Glasberget (berg bland husen?)', 60)
spot(870, 380, 'Glasberget sluttning', 50)
spot(560, 60,  'öster om spawn-parkeringen (skog?)')
spot(620, 110, 'längre öster in i skogen (skog?)')
spot(430, 90,  'villaträdgård nära spawn (gräs?)')
spot(400, -320,'branten N om Kvarnbygatan', 50)
spot(-180, -100,'Störtfjället', 50)
spot(463, 26,  'parkeringen vid spawn (asfalt?)')

import json, math

osm = json.load(open('osm_raw.json'))
el = json.load(open('elevation.json'))

LAT0 = (el['lat0']+el['lat1'])/2
LON0 = (el['lon0']+el['lon1'])/2
MLAT = 111320.0
MLON = 111320.0*math.cos(math.radians(LAT0))

def xz(lat, lon):
    return ((lon-LON0)*MLON, -(lat-LAT0)*MLAT)

nodes = {e['id']:(e['lat'],e['lon']) for e in osm['elements'] if e['type']=='node'}
ways = [e for e in osm['elements'] if e['type']=='way']

# terrain grid -> local coords. row 0 = lat0 (south), col 0 = lon0 (west)
rows, cols = el['rows'], el['cols']
x_min, z_at_lat1 = xz(el['lat1'], el['lon0'])  # north-west corner
x_min2, z_at_lat0 = xz(el['lat0'], el['lon0'])
x_max, _ = xz(el['lat0'], el['lon1'])
elev = [ (e if e is not None else 5.0) for e in el['elev'] ]

terrain = {
    'rows': rows, 'cols': cols,
    'x0': x_min, 'x1': x_max,        # west -> east
    'z0': z_at_lat0, 'z1': z_at_lat1, # south (z pos) -> north (z neg)
    'elev': [round(e,1) for e in elev]
}

def way_coords(w):
    return [xz(*nodes[n]) for n in w['nodes'] if n in nodes]

def rnd(pts):
    return [[round(x,1),round(z,1)] for x,z in pts]

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
    btype = t['building']
    buildings.append({'p': rnd(pts), 'h': round(h,1), 't': btype, 'n': t.get('name','')})

ROAD_W = {'primary':9,'secondary':8,'tertiary':7,'residential':6,'living_street':5.5,
          'unclassified':6,'service':4,'pedestrian':4,'footway':2.2,'path':1.8,
          'steps':2.5,'cycleway':2.5,'track':3}
roads = []
for w in ways:
    t = w.get('tags',{})
    hw = t.get('highway')
    if not hw or hw not in ROAD_W: continue
    pts = way_coords(w)
    if len(pts) < 2: continue
    roads.append({'p': rnd(pts), 'w': ROAD_W[hw], 'k': hw, 'n': t.get('name','')})

water = []
for w in ways:
    t = w.get('tags',{})
    if t.get('natural')=='water' or t.get('waterway') in ('riverbank',):
        pts = way_coords(w)
        if len(pts)>=3: water.append({'p': rnd(pts), 'poly': True})
    elif t.get('waterway') in ('river','stream','canal'):
        pts = way_coords(w)
        if len(pts)>=2: water.append({'p': rnd(pts), 'poly': False})

green = []
for w in ways:
    t = w.get('tags',{})
    if t.get('landuse') in ('grass','forest','meadow','recreation_ground','cemetery') or t.get('leisure') in ('park','pitch','playground','garden'):
        pts = way_coords(w)
        if len(pts)>=3: green.append({'p': rnd(pts)})

# elevation lookup for placing named points
def elev_at(x, z):
    fx = (x - terrain['x0'])/(terrain['x1']-terrain['x0'])*(cols-1)
    fz = (z - terrain['z0'])/(terrain['z1']-terrain['z0'])*(rows-1)
    c = max(0,min(cols-2,int(fx))); r = max(0,min(rows-2,int(fz)))
    tx = fx-c; tz = fz-r
    def E(rr,cc): return elev[rr*cols+cc]
    return (E(r,c)*(1-tx)+E(r,c+1)*tx)*(1-tz) + (E(r+1,c)*(1-tx)+E(r+1,c+1)*tx)*tz

def street_pts(name):
    out=[]
    for rd in roads:
        if rd['n']==name: out += rd['p']
    return out

# spawn: highest point on Görjelycksgatan
gp = street_pts('Görjelycksgatan')
spawn = max(gp, key=lambda p: elev_at(p[0],p[1]))
print('spawn', spawn, round(elev_at(*spawn),1),'m')

def centroid(name):
    pts = street_pts(name)
    x = sum(p[0] for p in pts)/len(pts); z = sum(p[1] for p in pts)/len(pts)
    return [round(x,1), round(z,1)]

def endpoint_lowest(name):
    pts = street_pts(name)
    p = min(pts, key=lambda p: elev_at(p[0],p[1]))
    return [round(p[0],1), round(p[1],1)]

capA = centroid('Gamla Torget')
capB = centroid('Roten M')
capC = centroid('Royens trappor')
enemy_entry = endpoint_lowest('Forsebron')
for nm,p in [('A Gamla Torget',capA),('B Roten M',capB),('C Royens trappor',capC),('entry',enemy_entry),]:
    print(nm, p, round(elev_at(*p),1),'m')

data = {'terrain': terrain, 'buildings': buildings, 'roads': roads, 'water': water, 'green': green,
        'spawn': spawn,
        'caps': [
            {'id':'A','name':'Gamla Torget','pos':capA,'r':16},
            {'id':'B','name':'Roten M','pos':capB,'r':15},
            {'id':'C','name':'Royens trappor','pos':capC,'r':15}],
        'enemyEntry': enemy_entry}
out = 'window.KVARNBYN_DATA = ' + json.dumps(data, separators=(',',':')) + ';'
open('data.js','w').write(out)
print('data.js', len(out)//1024, 'KB')

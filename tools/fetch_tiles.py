import math, io, time, urllib.request, json
import numpy as np
from PIL import Image

LAT0, LAT1 = 57.6495, 57.6625
LON0, LON1 = 12.008, 12.044

def tile_xy(lat, lon, z):
    n = 2**z
    x = (lon + 180) / 360 * n
    lr = math.radians(lat)
    y = (1 - math.log(math.tan(lr) + 1/math.cos(lr)) / math.pi) / 2 * n
    return x, y

def fetch(url, retries=3):
    for a in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'kvarnbyn-game/1.0'})
            with urllib.request.urlopen(req, timeout=30) as f:
                return f.read()
        except Exception as e:
            print('retry', url, e); time.sleep(2)
    raise SystemExit('failed ' + url)

def stitch(urlfmt, z, mode):
    x0, y1 = tile_xy(LAT0, LON0, z)   # south-west
    x1, y0 = tile_xy(LAT1, LON1, z)   # north-east
    tx0, tx1 = int(x0), int(x1)
    ty0, ty1 = int(y0), int(y1)
    W, H = (tx1-tx0+1)*256, (ty1-ty0+1)*256
    img = Image.new(mode, (W, H))
    ntiles = (tx1-tx0+1)*(ty1-ty0+1)
    i = 0
    for tx in range(tx0, tx1+1):
        for ty in range(ty0, ty1+1):
            data = fetch(urlfmt.format(z=z, x=tx, y=ty))
            t = Image.open(io.BytesIO(data)).convert(mode)
            img.paste(t, ((tx-tx0)*256, (ty-ty0)*256))
            i += 1
            if i % 40 == 0: print(f'{i}/{ntiles}')
    # crop to exact bbox
    px0 = (x0 - tx0) * 256; px1 = (x1 - tx0) * 256
    py0 = (y0 - ty0) * 256; py1 = (y1 - ty0) * 256
    return img, (px0, py0, px1, py1)

# --- elevation from terrarium z15 ---
img, (px0, py0, px1, py1) = stitch('https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png', 15, 'RGB')
a = np.asarray(img, dtype=np.float64)
elev_full = a[:,:,0]*256 + a[:,:,1] + a[:,:,2]/256 - 32768
np.save('terrarium_full.npy', elev_full)
json.dump({'px0':px0,'py0':py0,'px1':px1,'py1':py1,'shape':list(elev_full.shape)}, open('terrarium_meta.json','w'))
print('terrarium', elev_full.shape, 'crop window px', round(px0), round(py0), round(px1), round(py1))
sub = elev_full[int(py0):int(py1), int(px0):int(px1)]
print('elev range in bbox:', round(sub.min(),1), '-', round(sub.max(),1))

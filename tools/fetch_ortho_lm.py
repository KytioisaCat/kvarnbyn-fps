#!/usr/bin/env python3
"""Hämtar Lantmäteriets ortofoto (öppna data, CC BY 4.0) för Kvarnbyn-bboxen
och bygger ortho_full.png + ortho.jpg i lat/lon-linjär projektion (samma
mappning som spelets terräng-UV och takfärgssamplingen förväntar sig).

Kräver Geotorget-inloggning — sätt miljövariabler (dela dem inte med någon):
    export LM_USER='ditt-geotorget-användarnamn'
    export LM_PASS='ditt-lösenord'
    ./venv/bin/python fetch_ortho_lm.py

Källa: STAC-kollektionen orto-g2-2024 (0,16 m/px, GeoTIFF/COG, SWEREF99 TM).
"""
import json, math, os, sys, urllib.request

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds
from rasterio.io import MemoryFile
from PIL import Image

LON0, LON1 = 12.008, 12.044
LAT0, LAT1 = 57.6495, 57.6625
OUT_W, OUT_H = 6711, 4530          # ~0,3 m/px i full storlek (som tidigare)
TEX_W = 4096                        # speltexturen

USER = os.environ.get("LM_USER")
PASS = os.environ.get("LM_PASS")
if not USER or not PASS:
    sys.exit("Sätt LM_USER och LM_PASS (Geotorget-kontot) i miljön först — se filhuvudet.")

# ---- 1. hitta rutorna via STAC (öppet API, ingen auth) ----
req = urllib.request.Request(
    "https://api.lantmateriet.se/stac-bild/v1/search",
    data=json.dumps({"collections": ["orto-g2-2024"],
                     "bbox": [LON0, LAT0, LON1, LAT1], "limit": 20}).encode(),
    headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as f:
    items = json.load(f)["features"]
urls = [it["assets"]["data"]["href"] for it in items]
print(f"{len(urls)} COG-rutor täcker området")

# ---- 2. ladda ner rutorna med Basic-auth (robustare än GDAL:s vsicurl) ----
import base64
os.makedirs("cache", exist_ok=True)
auth = base64.b64encode(f"{USER}:{PASS}".encode()).decode()
paths = []
for u in urls:
    name = u.rsplit("/", 1)[-1]
    path = os.path.join("cache", name)
    paths.append(path)
    if os.path.exists(path) and os.path.getsize(path) > 1e6:
        print("  cachad:", name)
        continue
    print("  hämtar", name, "…", flush=True)
    r = urllib.request.Request(u, headers={"Authorization": "Basic " + auth})
    try:
        with urllib.request.urlopen(r, timeout=600) as f, open(path, "wb") as out:
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            sys.exit("401 Unauthorized — kontot saknar nedladdningsrätt eller fel uppgifter.\n"
                     "Logga in på geotorget.lantmateriet.se och gör en (gratis) beställning av\n"
                     "'Ortofoto Nedladdning' — det aktiverar nedladdningsrättigheten på kontot.")
        raise
    print("   ", os.path.getsize(path) // (1 << 20), "MB")

datasets = [rasterio.open(p) for p in paths]
print("mosaikar (nedsamplat till 0,32 m via COG-overviews)…", flush=True)
mosaic, src_transform = merge(datasets, res=(0.32, 0.32))
src_crs = datasets[0].crs
for ds in datasets:
    ds.close()
print("mosaik:", mosaic.shape)

# ---- 3. omprojicera till lat/lon-linjärt rutnät (EPSG:4326) ----
dst = np.zeros((3, OUT_H, OUT_W), dtype=np.uint8)
dst_transform = from_bounds(LON0, LAT0, LON1, LAT1, OUT_W, OUT_H)
reproject(source=mosaic[:3], destination=dst,
          src_transform=src_transform, src_crs=src_crs,
          dst_transform=dst_transform, dst_crs="EPSG:4326",
          resampling=Resampling.bilinear)

img = Image.fromarray(np.moveaxis(dst, 0, -1), "RGB")
img.save("ortho_full.png")
json.dump({"w": OUT_W, "h": OUT_H}, open("ortho_meta.json", "w"))
tex = img.resize((TEX_W, int(OUT_H * TEX_W / OUT_W)), Image.LANCZOS)
tex.save("ortho.jpg", quality=85)
print(f"klart: ortho_full.png {img.size} + ortho.jpg {tex.size}")
print("Nästa steg: ./venv/bin/python build_data2.py && cp data.js ../public/ && cp ortho.jpg ../public/")

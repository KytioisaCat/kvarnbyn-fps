#!/usr/bin/env python3
"""Hämtar Lantmäteriets markhöjdmodell 1 m (LiDAR, CC0) för Kvarnbyn-bboxen
och skriver lidar_full.npy + lidar_meta.json i lat/lon-linjärt rutnät (1 m).

Kräver Geotorget-inloggning — sätt miljövariabler (dela dem inte med någon):
    export LM_USER='...'   export LM_PASS='...'
    ./venv/bin/python fetch_lidar.py
"""
import base64, json, os, sys, urllib.request

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds

LON0, LON1 = 12.008, 12.044
LAT0, LAT1 = 57.6495, 57.6625
OUT_W, OUT_H = 2144, 1447  # ~1 m/px

USER, PASS = os.environ.get("LM_USER"), os.environ.get("LM_PASS")
if not USER or not PASS:
    sys.exit("Sätt LM_USER och LM_PASS (Geotorget) i miljön först.")

req = urllib.request.Request(
    "https://api.lantmateriet.se/stac-hojd/v1/search",
    data=json.dumps({"bbox": [LON0, LAT0, LON1, LAT1], "limit": 20}).encode(),
    headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as f:
    feats = json.load(f)["features"]
urls = [ft["assets"]["data"]["href"] for ft in feats
        if ft.get("collection", "").startswith("mhm-") and "/grid1m/" in ft["assets"]["data"]["href"]]
print(f"{len(urls)} grid1m-rutor täcker området")

os.makedirs("cache", exist_ok=True)
auth = base64.b64encode(f"{USER}:{PASS}".encode()).decode()
paths = []
for u in urls:
    name = u.rsplit("/", 1)[-1]
    path = os.path.join("cache", name)
    paths.append(path)
    if os.path.exists(path) and os.path.getsize(path) > 1e5:
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
            sys.exit("401 — kolla LM_USER/LM_PASS och att beställningen är aktiv.")
        raise
    print("   ", os.path.getsize(path) // (1 << 20), "MB")

datasets = [rasterio.open(p) for p in paths]
mosaic, src_transform = merge(datasets)
src_crs = datasets[0].crs
for ds in datasets:
    ds.close()
print("mosaik:", mosaic.shape, "| höjdspann:", float(np.nanmin(mosaic)), "-", float(np.nanmax(mosaic)))

dst = np.full((OUT_H, OUT_W), np.nan, dtype=np.float32)
reproject(source=mosaic[0], destination=dst,
          src_transform=src_transform, src_crs=src_crs,
          dst_transform=from_bounds(LON0, LAT0, LON1, LAT1, OUT_W, OUT_H),
          dst_crs="EPSG:4326", resampling=Resampling.bilinear,
          src_nodata=datasets and None, dst_nodata=np.nan)
np.save("lidar_full.npy", dst)
json.dump({"w": OUT_W, "h": OUT_H, "lon0": LON0, "lon1": LON1, "lat0": LAT0, "lat1": LAT1,
           "note": "rad 0 = norr (lat1), lat/lon-linjärt, meter över havet"},
          open("lidar_meta.json", "w"))
print(f"klart: lidar_full.npy ({OUT_W}x{OUT_H}, 1 m) — säg till Claude att integrera!")

#!/usr/bin/env python3
"""Kompakt, versionsbar form av LiDAR-höjdgriden.

lidar_full.npy (27 MB float32, gitignorerad) <-> lidar_1m.png (16-bit gråskala, committad)
+ lidar_meta.json. Kodning: pixel = round((höjd_m + OFFSET) * SCALE), dvs 1 cm-upplösning,
0..65535 täcker -10..+645 m. Rad 0 = norr, lat/lon-linjärt (se lidar_meta.json).

Syfte: en molnsession (git-klon utan tools/cache) ska kunna köra pipelinen och v2-exporten
utan Lantmäteriet-konto. Användning:

    python3 tools/lidar_png.py pack     # npy -> png (körs lokalt efter fetch_lidar.py)
    python3 tools/lidar_png.py unpack   # png -> npy (körs i molnet vid behov)

I pipeline-skripten: `from lidar_png import load_dem; dem = load_dem()` — tar npy om den
finns, annars png.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
NPY = os.path.join(HERE, "lidar_full.npy")
PNG = os.path.join(HERE, "lidar_1m.png")
META = os.path.join(HERE, "lidar_meta.json")
OFFSET = 10.0   # m, så att -10 m -> 0
SCALE = 100.0   # pixel per m -> 1 cm


def pack():
    dem = np.load(NPY).astype(np.float64)
    q = np.round((dem + OFFSET) * SCALE)
    assert q.min() >= 0 and q.max() <= 65535, (q.min(), q.max())
    img = Image.fromarray(q.astype(np.uint16))
    img.save(PNG, optimize=True)
    meta = json.load(open(META))
    meta.update({"png": os.path.basename(PNG), "png_offset_m": OFFSET, "png_scale": SCALE,
                 "png_note": "höjd_m = pixel / png_scale - png_offset_m; uint16 gråskala"})
    json.dump(meta, open(META, "w"), ensure_ascii=False, indent=1)
    back = load_png()
    err = np.abs(back - dem).max()
    print(f"skrev {PNG} ({os.path.getsize(PNG)/1e6:.1f} MB), {img.size}, max rundningsfel {err*100:.2f} cm")


def load_png():
    img = Image.open(PNG)
    assert img.mode in ("I;16", "I;16B", "I"), img.mode
    q = np.array(img, dtype=np.float64)
    return (q / SCALE - OFFSET).astype(np.float32)


def unpack():
    dem = load_png()
    np.save(NPY, dem)
    print(f"skrev {NPY} {dem.shape}")


def load_dem():
    """npy om den finns (exakt), annars png (1 cm-kvantiserad)."""
    if os.path.exists(NPY):
        return np.load(NPY)
    return load_png()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pack"
    {"pack": pack, "unpack": unpack}[cmd]()

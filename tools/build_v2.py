#!/usr/bin/env python3
"""Exportsteg för v2-motorn: motorvänliga datafiler till v2/public/data/.

Körs från tools/ (med venv:en: numpy + pillow räcker — rasterio behövs inte):

    cd tools && venv/bin/python build_v2.py            # allt
    cd tools && venv/bin/python build_v2.py --no-ortho # hoppa över ortofotot (långsamt)

Källorna är committade, så steget går i vilken klon som helst utan Lantmäteriet-konto:
  lidar_1m.png + lidar_meta.json  (LiDAR 1 m, 16-bit, 1 cm-kvantiserad)
  classmap.png                    (2 m, R=asfalt G=gräs B=skog svart=berg)
  ortho8k.jpg                     (Lantmäteriets ortofoto, CC BY 4.0, 8192×5529)
  osm_raw.json                    (M2–M3: hus, vägar, murar, vatten — ännu inte exporterat här)

Utdata (allt lat/lon-linjärt i SAMMA projektion som v1, se ARKITEKTUR.md):
  height.png   1 m-höjdkarta som 8-bit RGB: R = hög byte, G = låg byte av
               q = round((h_m + 10) * 100), dvs h_m = (R*256 + G)/100 - 10. Medvetet utan
               alfa (canvas-compositing förstör alfapackade värden). Rad 0 = norr.
               Höjderna är RÅ (före 1,2× överdrift och åfåre-nedskärning) — motorn gör det,
               precis som v1, så origHeightAt/heightAt kan återskapas.
  classmap.png kopia av klasskartan (1610×1086, 2 m/cell, rad 0 = norr).
  ortho_8k.jpg / ortho_4k.jpg  ortofotot i två storlekar; motorn väljer efter MAX_TEXTURE_SIZE.
  meta.json    bbox, spelkoordinater (x0/x1/z0/z1), bildstorlekar, kodning, EXAG, attribution.

Spelkoordinater: x = (lon − CLON)·MLON, z = −(lat − CLAT)·MLAT (meter, z positiv = söder).
Terrängens UV = (x−x0)/(x1−x0), (z−z1)/(z0−z1) — samma för höjd, klass och orto.
"""
import argparse
import json
import math
import os
import shutil
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
from bbox import LAT0, LAT1, LON0, LON1  # noqa: E402
from lidar_png import OFFSET, SCALE, load_dem  # noqa: E402

OUT = os.path.join(HERE, '..', 'v2', 'public', 'data')
CLAT, CLON = (LAT0 + LAT1) / 2, (LON0 + LON1) / 2
MLAT = 111320.0
MLON = 111320.0 * math.cos(math.radians(CLAT))
EXAG = 1.2   # v1:s höjdöverdrift (game.js) — behålls för igenkänning av backarna


def xz(lat, lon):
    return ((lon - CLON) * MLON, -(lat - CLAT) * MLAT)


def export_height():
    dem = load_dem().astype(np.float64)              # (2171, 3219), rad 0 = norr
    q = np.round((dem + OFFSET) * SCALE)
    assert q.min() >= 0 and q.max() <= 65535, (q.min(), q.max())
    q = q.astype(np.uint16)
    rgb = np.zeros(dem.shape + (3,), dtype=np.uint8)
    rgb[..., 0] = q >> 8
    rgb[..., 1] = q & 0xFF
    path = os.path.join(OUT, 'height.png')
    Image.fromarray(rgb, 'RGB').save(path, optimize=True)
    # kontroll: avkoda som motorn gör
    back = Image.open(path).convert('RGB')
    arr = np.asarray(back).astype(np.float64)
    h = (arr[..., 0] * 256 + arr[..., 1]) / SCALE - OFFSET
    err = np.abs(h - dem).max()
    assert err < 0.006, err
    print(f'height.png {dem.shape[1]}×{dem.shape[0]} ({os.path.getsize(path)/1e6:.1f} MB), '
          f'{dem.min():.1f}–{dem.max():.1f} m, max avkodningsfel {err*100:.2f} cm')
    return dem.shape


def export_classmap():
    src = os.path.join(HERE, 'classmap.png')
    im = Image.open(src)
    assert im.mode == 'RGB', im.mode
    path = os.path.join(OUT, 'classmap.png')
    shutil.copyfile(src, path)
    print(f'classmap.png {im.size[0]}×{im.size[1]} ({os.path.getsize(path)/1e6:.1f} MB)')
    return im.size


def export_ortho(skip=False):
    src = os.path.join(HERE, 'ortho8k.jpg')
    im = Image.open(src)
    sizes = {}
    if skip:
        for name in ('ortho_8k.jpg', 'ortho_4k.jpg'):
            p = os.path.join(OUT, name)
            if os.path.exists(p):
                sizes[name] = list(Image.open(p).size)
        print('ortho: hoppar över (--no-ortho), behåller befintliga filer', sizes)
        return sizes
    p8 = os.path.join(OUT, 'ortho_8k.jpg')
    shutil.copyfile(src, p8)
    sizes['ortho_8k.jpg'] = list(im.size)
    w4 = 4096
    h4 = round(im.size[1] * w4 / im.size[0])
    im4 = im.resize((w4, h4), Image.LANCZOS)
    p4 = os.path.join(OUT, 'ortho_4k.jpg')
    im4.save(p4, quality=82, optimize=True, progressive=True)
    sizes['ortho_4k.jpg'] = [w4, h4]
    for name in sizes:
        p = os.path.join(OUT, name)
        print(f'{name} {sizes[name][0]}×{sizes[name][1]} ({os.path.getsize(p)/1e6:.1f} MB)')
    return sizes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-ortho', action='store_true', help='hoppa över ortofotoexporten')
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    hshape = export_height()
    csize = export_classmap()
    osizes = export_ortho(args.no_ortho)

    x0, z1 = xz(LAT1, LON0)   # väst, norr (z negativ)
    x1, z0 = xz(LAT0, LON1)   # öst, syd (z positiv)
    meta = {
        'version': 1,
        'bbox': {'lat0': LAT0, 'lat1': LAT1, 'lon0': LON0, 'lon1': LON1},
        'center': {'lat': CLAT, 'lon': CLON},
        'mPerDegLat': MLAT, 'mPerDegLon': MLON,
        'x0': round(x0, 2), 'x1': round(x1, 2), 'z0': round(z0, 2), 'z1': round(z1, 2),
        'note': 'x = (lon−center.lon)·mPerDegLon, z = −(lat−center.lat)·mPerDegLat; '
                'rad 0 i alla bilder = norr (z1); UV = ((x−x0)/(x1−x0), (z−z1)/(z0−z1))',
        'exag': EXAG,
        'height': {'file': 'height.png', 'w': hshape[1], 'h': hshape[0],
                   'offsetM': OFFSET, 'scale': SCALE,
                   'decode': 'h_m = (R*256 + G)/scale − offsetM (rå LiDAR, före exag/åfåra)'},
        'classmap': {'file': 'classmap.png', 'w': csize[0], 'h': csize[1],
                     'classes': 'R=asfalt G=gräs B=skog svart=berg'},
        'ortho': {name: {'w': s[0], 'h': s[1]} for name, s in osizes.items()},
        'attribution': ['Höjddata och ortofoto: © Lantmäteriet (CC BY 4.0)',
                        'Kartdata: © OpenStreetMap-bidragsgivare (ODbL)'],
    }
    with open(os.path.join(OUT, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print('meta.json skriven:', {k: meta[k] for k in ('x0', 'x1', 'z0', 'z1')})


if __name__ == '__main__':
    main()

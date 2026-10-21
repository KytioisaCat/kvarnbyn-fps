Genererade motorfiler för v2 — skrivs av `tools/build_v2.py` (kör `cd tools && venv/bin/python
build_v2.py`) och **committas** så att bygget går utan Python. Källorna ligger i `tools/`
(`lidar_1m.png`, `classmap.png`, `ortho8k.jpg`, `osm_raw.json`) + `public/husfakta.js`.

| Fil | Innehåll |
|---|---|
| `meta.json` | bbox, spelkoordinater (x0/x1/z0/z1), projektion, kodning, EXAG, attribution |
| `height.png` | höjdkarta 1 m (3219×2171) som 8-bit RGB: `h = (R·256+G)/100 − 10` m, rå LiDAR före överdrift |
| `classmap.png` | markklasser 2 m: R=asfalt, G=gräs, B=skog, svart=berg |
| `ortho_8k.jpg`, `ortho_4k.jpg` | Lantmäteriets ortofoto (CC BY 4.0); motorn väljer efter `MAX_TEXTURE_SIZE` |

Rad 0 i alla bilder = norr. Kommer (M2–M3): hus, vägar, murar, broar, flats, vatten.

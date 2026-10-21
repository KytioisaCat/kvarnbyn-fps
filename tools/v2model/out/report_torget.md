# v2model-rapport — område `torget`

Nät: 562 kanter (73 bro, 1 tunnel), 457 korsningsnoder (2 nodade korsningar utan OSM-nod), 6906 vertex, 24.7 km väg

| Mätgrind | Värde | Gräns | OK | Detalj |
|---|---|---|---|---|
| maxlutning: överskridande (ej trappor) | 0.011  | 0.03 | ✅ | living_street 'Franckegatan' way 78040332 |
| bula körväg: max |2:a diff| per 4 m | 0.151 m | 0.2 | ✅ | residential 'Samuel Norbergs gata' way 394752536 vid (117.0, -172.0) |
| bula gångväg: max |2:a diff| per 4 m (ej trappor) | 0.426 m | 0.5 | ✅ | footway 'Stockliden' way 1227769456 vid (218.0, 26.0); 22 trappor/branta gångvägar/tunnlar undantagna |
| fri höjd över korsad väg (min, normerad till 4,7 för gång 2,6) | 4.536 m | 4.5 | ✅ | footway över footway |
| vanlig väg − LiDAR (p90) | 0.128 m | 0.6 | ✅ |  |
| däck över mark (min) | 0.437 m | 0.3 | ✅ |  |
| terräng över vägyta inne i asfalt (max) | 0.031 m | 0.05 | ✅ | 0.03 m vid (-99, -26), 0.03 m vid (-165, -243), 0.03 m vid (-101, -111) |
| terräng över kantstenskrön vid ytterkanten (p99) | -0.004 m | 0.03 | ✅ | max 0.93 m vid (132, -233), 0.22 m vid (-270, -16), 0.17 m vid (128, -123) — kandidater för stödmur |
| terräng under kantstenskrön vid ytterkanten (p99) | 0.359 m | 0.5 | ✅ |  |

**Resultat: ALLA GRINDAR OK**

Meshar: asphalt 11574 tri, deck 2253 tri, path 4516 tri, steps 244 tri, kerb 77663 tri, concrete 3760 tri, rail 3664 tri

Konformering: cells_road 100192, cells_kerb 11910, cells_blend 176344, change_p50 0.11, change_p90 0.37, change_max 6.09

Profilbild: `v2model/out/profil_molndals_bro.png`
Tid: 68 s

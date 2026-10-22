# v2model-rapport — område `torget`

Nät: 562 kanter (73 bro, 1 tunnel), 457 korsningsnoder (2 nodade korsningar utan OSM-nod), 6906 vertex, 24.7 km väg

| Mätgrind | Värde | Gräns | OK | Detalj |
|---|---|---|---|---|
| maxlutning: överskridande (ej trappor) | 0.011  | 0.03 | ✅ | living_street 'Franckegatan' way 78040332 |
| bula körväg: max |2:a diff| per 4 m | 0.151 m | 0.2 | ✅ | residential 'Samuel Norbergs gata' way 394752536 vid (117.0, -172.0) |
| bula gångväg: max |2:a diff| per 4 m (ej trappor) | 0.426 m | 0.5 | ✅ | footway 'Stockliden' way 1227769456 vid (218.0, 26.0); 22 trappor/branta gångvägar/tunnlar undantagna |
| fri höjd över korsad väg (min, normerad till 4,7 för gång 2,6) | 4.536 m | 4.5 | ✅ | footway över footway |
| vanlig väg − LiDAR (p90) | 0.135 m | 0.6 | ✅ |  |
| däck över mark (min) | 0.437 m | 0.3 | ✅ |  |
| terräng över vägyta inne i asfalt (max) | 0.031 m | 0.05 | ✅ | 0.03 m vid (-99, -26), 0.03 m vid (-101, -111), 0.01 m vid (-138, -108) |
| flats: terräng mot planet inne i ytan (max) | 0.038 m | 0.05 | ✅ | playground '' way 1159593171 |
| flats: vägyta inne i ytan mot planet (max) | 0.006 m | 0.06 | ✅ | parking '' way 1462984309 |
| flats: planets lutning (max) | 0.060  | 0.0605 | ✅ | parking ''; 5 klämda av 20 |
| terräng över kantstenskrön vid ytterkanten (p99) | -0.000 m | 0.03 | ✅ | max 0.83 m vid (192, 60), 0.27 m vid (-131, -78), 0.22 m vid (-270, -16) — kandidater för stödmur |
| terräng under kantstenskrön vid ytterkanten (p99) | 0.361 m | 0.5 | ✅ |  |

**Resultat: ALLA GRINDAR OK**

Meshar: asphalt 11426 tri, deck 2253 tri, path 4516 tri, steps 244 tri, pitch 2 tri, sett 8 tri, playground 8 tri, kerb 74793 tri, concrete 3450 tri, rail 3044 tri, wall 1254 tri

Konformering: wall_cells 11760, cells_road 112067, cells_kerb 12042, cells_blend 170708, change_p50 0.10, change_p90 0.32, change_max 3.87, wall_segments 209, wall_length_m 757.27, wall_max_h 5.46

Profilbild: `v2model/out/profil_molndals_bro.png`
Tid: 57 s

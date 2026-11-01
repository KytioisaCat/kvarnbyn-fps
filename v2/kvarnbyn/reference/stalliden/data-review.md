# M30/M31 och Stalliden — fryst dataunderlag

2026-11-01, före nybyggnad, baslinje `ca119f9`. [Planbild](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/reference/stalliden/data-review.walk.jpg), [faktisk export-/gånggranskning](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/reference/stalliden/data-review.walk.md), [hus/DTM/vägdata](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/reference/stalliden/data-review.json) och [exportens provvärden](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/reference/stalliden/data-review.walk.json). Källhashar hindrar att senare resultat felmärks som baslinje.

Höjddata är tolkning av markmodell, inte observation av verkliga murar, golv eller vilplan. Exporterade meshhöjder är däremot faktiska modelldata. Ingen motor-, GPU- eller browserkörning har gjorts för datagranskningen. Koordinater: x öst/z syd; lokal Y = höjd över havet −18 m.

| Hus | Centrum x/z | Nuvarande antagen bas, m ö.h. | OSM / byggkontur |
|---|---|---:|---|
| M30, w92331973 | 100,886 /103,444 | 42,242 | 85,88 /85,91 m²; i praktiken samma rektangel |
| M31, w92332141 | 83,763 /88,295 | 40,058 | 102,63 /113,13 m²; tio hörn förenklas till fyra, 10,50 m² modell utanför OSM |

M31:s byggkontur kommer som närmast 3,604 m från huvudtrappans mittlinje (OSM-konturen 3,916 m), så den blockerar inte det antagna 2 m-bandet. M30 ligger 7,730 m från huvudtrappans närmaste del och 1,59 m från Roten M-stigens mittlinje. M31:s sydöstra tomt har nivåskillnad mot stigen, men **den ger inget bevis för en hög stödmur**. Konturer för nya gårdar måste förhålla sig till både original och byggkontur.

Den kritiska byggträngseln finns i stället vid **M24 w92331938**, trappmitt 46,737 /81,415 (vägg 0,737 m från mitten), och **M25 w92332157**, 54,210 /92,094 (0,943 m). Original-OSM och modeller ligger nästan lika här. En generell bredd på 2 m går in i hushörnen; två meter är en byggregel, inte ett uppmätt mått. Uppgifterna säger att bredd/linjeföring behöver platsanpassas, inte att hus ska kapas.

Hela nedåtstråket består av **w461711525 → w461711523 → w461711524**, därefter parallellstigen **w1227769459**. En verklig OSM-koppling till Norra Forsåkersgatan finns söderut via **w1227769458**, totalt 165,4 m från Roten-knuten. Direkt från trappfoten över till körbanan finns ingen delad nod. En eventuell kort topologisk fotgängarlänk där är ett nytt, uppskattat byggbeslut.

Exportgranskningens viktigaste fynd: 25,9 cm nivåskillnad vid huvudtrappans nedre fog; ytterligare 25,9 cm mellan gångdelen och nedre trappan; terräng upp till 50,8 cm över avsedd ramp på ett sidoprov; synliga räcken utan räckeskollision. Vanliga synliga steg är högst 16 cm i de täta proven. Nuvarande profil saknar författade vilplan, och OSM-hörnen får inte kallas verkliga avsatser. Alla exakta koordinater, höjder och provbegränsningar finns i exportgranskningen.

Lämplig nästa ground-/QA-del: en gemensam finished-höjd genom hela kedjan, platsanpassad bredd vid M24/M25 och explicit skillnad mellan steg, mellanliggande gångytor och kollisionsramp. Därefter faktisk kapselgång upp och ned genom alla fogar och svängar utan teleportering. Byggda murar och exakta flykt-/vilplanslägen kräver separat synreferens; denna baslinje innehåller inga sådana påståenden.

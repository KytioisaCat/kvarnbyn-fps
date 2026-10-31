# Roten M 29–31 — dataunderlag 2026-10-30

**Börja den visuella kontrollen vid A/D, väst och söder om M29, och B, mellan M31 och Roten M-stigen.** DTM:n visar nivåskillnader där, men anger inte om kanterna är stödmurar, berg, slänter eller trappor. Ingen mur, terrasskontur eller färdig gårdsnivå är visuellt bekräftad i denna granskning.

[Topplan](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/reference/roten-m/data-review.jpg) · [Koordinater/prover/OSM-taggar](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/reference/roten-m/data-review.json)

Rutan är **x 75–125, z 80–135 m**. Origo 57,65690 N / 12,02780 E; x öst, z syd. Lokal Y = höjd över havet −18 m. Höjderna nedan är **tolkade markprover ur befintlig DTM**, inte inmätta murkrön, murfötter eller färdiga golv. Byggnadsfotavtryckens DTM kan vara interpolerad genom husen. `site.json` har ett 2-metersfält konformerat mot vägar; jämförelsevärden i JSON är bilinjär sampling av detta fält, inget actual-mesh-/BVH-prov. Inga grafik- eller spelprov har körts.

| Hus, OSM-id | Centrum x/z | Nuvarande antagen husbas, m ö.h. | DTM vid OSM-hörnen, m ö.h. |
|---|---|---:|---:|
| M29, w92332120 | 100,228 / 120,086 | 41,861 | 40,407–42,557 |
| M30, w92331973 | 100,886 / 103,444 | 42,242 | 41,214–42,890 |
| M31, w92332141 | 83,763 / 88,295 | 40,058 | 38,937–40,819 |

Husbaserna kommer från den nuvarande tolkningen, där markprovernas 65:e percentil används. De är ingen oberoende referens för terrasshöjd. OSM har adress och `building=yes`, men inga vånings-/höjdtaggar för de tre husen. M29:s elva hörn behålls i byggmodellen. M31 förenklas däremot från tio hörn till en rektangel: **102,63 →113,13 m²**, med 10,50 m² modell utanför det ursprungliga fotavtrycket. Kontrollera hörn/utbyggnader innan en ny tomtkant läggs nära huset; topplanen visar OSM-konturen.

| Markering i topplanen | Från x/z → till x/z | DTM-höjd från → till | Vad platsreferensen behöver avgöra |
|---|---|---|---|
| A, M29 väst/sydväst | 93,9 /120,1 →91,4 /121,8, 3 m | 41,81 →40,18 m | Finns en plan gård och skarp kant i det smala mellanrummet? Vilken sida är murkrön/murfot? |
| B, M31 öst/sydöst | 88,5 /90,1 →91,7 /94,0, 5 m | 40,24 →42,11 m | Hur möter den lägre hustomten stigen ovanför: stödmur, entrétrappa eller slänt? |
| C, M31 nordväst | 80,9 /84,4 →77,7 /80,6, 5 m | 38,98 →37,56 m | Finns en tomtmur eller följer kanten berg/slänt? Längre mot rutans NV-hörn faller DTM:n ännu kraftigare. |
| D, M29 södra urtag | 100,8 /126,4 →96,6 /129,2, 5 m | 41,09 →39,36 m | Var slutar tomtnivån före Stockliden? Finns en kort vägg/trappa i nivåbrottet? |
| E, M30 sydöst | 104,7 /107,8 →108,0 /111,6, 5 m | 42,76 →42,05 m | Hur möter entrégård/plantering Roten M-stigen och M29:s norra sida? |

**A får inte förlängas till femmetersprovet som en fri markprofil:** då ligger punkten i grannhuset `w92331991`. Det längre provet finns kvar i JSON med byggnadsflagga, men topplanens kontrollsträcka slutar före grannhuset. Samtliga profiler börjar vid fasadliv; de bekräftar inte markmaterial eller murtyp.

Närmaste stråk är `w330280688` **Roten M** (gångstig), `w92332123` **Royens gata** (gångfartsområde), `w461711525` **Stalliden** (trappor), samt Stocklidens gångdel `w1227769456` och trappdel `w236136748`. Roten M går från Royens gata vid **116,922 /118,244** förbi **102,461 /112,578** till **87,166 /98,474**, där Stalliden ansluter. M30 ligger 1,59 m från dess centrumlinje och M31 4,52 m. Avstånden är inte fria gångbredder.

Rå-OSM anger **`surface=sett` för Royens gata, Roten M, Stalliden och Stocklidens trappdel**. Stocklidens trappor har även `handrail=yes`, `incline=down` och `ramp=no`. Kontrollera stenläggningens verkliga kontinuitet och kanter i bilderna; de nuvarande 2/5-metersbredderna är generella byggregler, inga uppmätta gatubredder. M29 ligger bara 2,12 m från Royens gatas centrumlinje, så ett 5 m brett vägband måste klippas mot huset. Lägg ingen planteringsremsa enbart efter den antagna vägbredden.

**Murar/staket:** inga linjer eller noder för mur, stödmur, häck eller staket finns i rå-OSM inom 30 m från rutan; samma gäller `city.barriers`. Närmaste rå-OSM-mur ligger 41,28 m från rutan (`w92331953`). Frånvaron är en datalucka. Ny placering måste komma från den visuella granskningen. Nuvarande `site.json` har ett skogsträd i rutan, vid **100,02 /82,66**; det är en genererad placering, ingen verifierad trädkarta.

Det råa 1-metersrutnätet spänner över **31,17–42,98 m ö.h.** i hela arbetsrutan. Rutan ska inte planas ut i ett enda plan. Vid A–E skiljer sig befintligt konformerat terrängfält från rå DTM med ungefär 1–11 cm vid ändpunkterna. Underlaget visar alltså redan höjdskillnaderna; det som återstår att tolka är de byggda gränserna och vilka ytor som faktiskt är plana. Skapa inga numeriska terrassplan före den visuella kontrollen.

Källor: aktuell `city.json`/`site.json` efter leveransen `321954c`, råa `tools/osm_raw.json`, `tools/lidar_1m.png` och `lidar_meta.json`. OSM © OpenStreetMap-bidragsgivare (ODbL); DTM © Lantmäteriet enligt projektets källdokumentation. Endast nya `data-review.*`-filer har skrivits. Ingen browser har öppnats. Inga produktions-/dagboksändringar, ingen commit eller push.

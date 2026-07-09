# Arkitektur & beslutslogg — Försvara Kvarnbyn

Syftet med detta dokument: en ny session (eller människa) ska på fem minuter förstå
*varför* saker ser ut som de gör. Läs CLAUDE.md för arbetsflöden/fällor och TODO.md
för läget — detta är bakgrunden och besluten.

## Vision

Joels barndoms-FPS i Kvarnbyn, Mölndal. **Ledstjärnan är igenkänning** — Joel ska
känna igen sig från barndomen. Det slår allt annat: hellre rätt siluett på fel sätt
än snygg grafik på fel plats. All speltext på svenska. Målbild för en runda: ~5 min.

## Historik i korthet (varför det blev så här)

1. **v1**: OSM-byggnader som färgade lådor + EU-DEM 25 m-terräng → Joel kände inte igen sig.
2. **Satellitvarvet**: Esri-ortofoto draperat + takfärger samplade ur fotot + landmärkesskyltar
   + 1,5× höjdöverdrift. Bättre, men Esri-licensen tillåter inte redistribution.
3. **Lantmäteriet-varvet** (kräver Geotorget-konto + produktbeställning per produkt):
   ortofoto 0,16 m (CC BY 4.0, flygår 2024, vårbilder!) + **1 m LiDAR-terräng**.
   LiDAR:n gav de riktiga murarna/branterna → överdriften sänktes till 1,2×.
4. **Klasskartevarvet**: vårfotot är gråblekt → pixelfärg räcker inte. En offline-byggd
   klasskarta (asfalt/gräs/skog/berg per 2 m-cell) styr nu färgsättning, detaljtexturer
   och vegetation.
5. **Befrielseläget**: vågförsvar ersattes med "fienden håller nästan allt, pusha ut dem".

## Datakällor & licenser

| Data | Källa | Licens | Hämtas med |
|---|---|---|---|
| Byggnader, vägar, murar, skog, parkeringar, POI | OSM Overpass | ODbL | `tools/overpass_query.txt` |
| Ortofoto 0,16 m (2024) | Lantmäteriet STAC (`api.lantmateriet.se/stac-bild/v1`, kollektion `orto-g2-2024`) | CC BY 4.0 | `tools/fetch_ortho_lm.py` |
| Markhöjd 1 m (LiDAR) | Lantmäteriet STAC (`stac-hojd/v1`, grid1m, 4 rutor 639**_32**) | CC0/öppna data | `tools/fetch_lidar.py` |
| three.js r160 | vendorerad | MIT | `public/three.module.js` |

Nedladdning från `dl1.lantmateriet.se` kräver Basic-auth med Joels Geotorget-konto:
`LM_USER`/`LM_PASS` som miljövariabler — **aldrig i chat, repo eller filer**. STAC-METADATA
är öppen utan konto. Historiska ortofoton 1960–1999 finns i samma API (framtida läge).
Attributionsraden i spelets HUD måste behållas.

## Pipeline (tools/, Python-venv i tools/venv)

```
overpass_query.txt ──curl──► osm_raw.json
fetch_ortho_lm.py  ────────► cache/*.tif ─► ortho_full.png (6711×4530) + ortho.jpg (4k)
make_ortho8k.py    ────────► (ur cache) ─► public/ortho.jpg (8192px, 0,26 m/px)
fetch_lidar.py     ────────► cache/*.tif ─► lidar_full.npy (2144×1447, 1 m)
build_classmap.py  ────────► public/classmap.png (1072×724, 2 m/cell)
build_data2.py     ────────► public/data.js (~4 MB)
```

- **Allt är lat/lon-linjärt**: spelkoordinat x = (lon−12.026)·59560 m, z = −(lat−57.656)·111320 m.
  Ortho/klasskarta/terräng delar exakt samma mappning → terrängens UV = (x,z) normaliserat.
- `build_data2.py` samplar **takfärg per byggnad** (median över fotavtrycket, mättnadsboostad
  eftersom vårfotot är blekt) och genererar terränggrid (2 m ur LiDAR), vägar, murar,
  vatten (endast SLUTNA ringar!), landmärken, capture points.
- `build_classmap.py` klassar mark ur foto (färg + **textur/knottrighet**), LiDAR
  (lutning + lokal prominens = berg i dagen) och OSM (väg/parkering/skog/hus-närhet).
  Kodning i PNG: R=asfalt, G=gräs, B=skog, **svart=berg (residual i shadern)** —
  medvetet RGB utan alfakanal (canvas-compositing förstör alfapackade klasser).

## Runtime-arkitektur (public/game.js, ~2 800 rader, en fil med avsikt)

Tre höjdfunktioner — använd rätt:
- `heightAt` = LiDAR-terräng × **EXAG 1,2** med åfåran nedskuren (~2 m under vattenytan)
- `origHeightAt` = före nedskärningen (broar, vattenyta, stödmursgenerering refererar hit)
- `groundInfoAt` = `heightAt` + vägdäck ovanpå (broar är gångbara!) + "står jag på väg"

Bärande delsystem och deras beslut:
- **Rendering**: allt statiskt merge:as till få draw calls (väggar/tak/vägar/murar/vatten);
  träd/lyktor/bilar/tuvor är InstancedMesh. Terrängen är **MeshBasicMaterial** —
  flygfotot har verklighetens ljus inbakat; Lambert ovanpå blev överexponerat blåstick.
- **Splat-shader** (onBeforeCompile på terrängmaterialet): klasskartan väljer detaljtextur
  (asfalt/gräs/skog/granit-med-mossa) inom ~18–85 m och **färgtonar fotot per klass på
  alla avstånd** (skog → mättad grönska osv). Detaljtexturerna är procedurella canvas.
- **Kollision/sikt**: ingen triangel-raycast. Kulor/LOS = analytisk ray-march
  (`pointBlocked`) mot polygon/segment/cirkel-hashar (`bldHash`/`wallHash`/`obstHash`,
  cellstorlek `CELL=24`). Skogsceller ackumulerar "lövdjup" — sikt blockeras efter ~14 m.
  **Nya hinder måste in i rätt hash**, annars går kulor igenom.
- **Tak**: alla tak bär spelaren. Platta = topY; sadeltak = interpolerad höjd nock→takfot
  (`roofYAt`); 0,6 m step-up-assist vid kanter. Sadeltaksinfo sparas per byggnad (`gable`).
- **Byggnader**: nästan-rektangulära fotavtryck snappas till minsta omslutande rektangel
  (fyller ≥68 %); småhus < 350 m² får träpanel, större slät puts (två fasadtexturer);
  vita kulörer (Joels fakta: Kvarnbyn är vita trä-/putshus); ~hälften av småhusen i
  kärnan (x 60–340, z −200–80) sänks till 1 våning (seedat på position = stabilt).
- **Murar**: OSM-barriärer + **procedurella stödmurar** ur väg×terräng-tvärlutning
  (diff >1,35 m vid vägkant) + räcken där marken störtar (>2,2 m, hoppbara).
- **Broar**: solida däck + sidobalkar där vägbana >0,9 m över mark **och <22 m från ån**
  (annars falska broar i branta korsningar — inträffade vid Royens trappor).
- **Rörelse**: branthetsspärr med **1,6 m lookahead** (aldrig per frame-steg — brus),
  spärr 0,60 / tung klättring 0,38, vägar/trappor alltid gångbara (Royens trappor är
  0,61 längs linjen!), kravla fritt i/vid åfåran. Vägfart 1,0 / terräng 0,8 / skog 0,5 /
  vatten 0,35 + ström som drar nedströms + skada i vitvatten. Crouch = håll C (bryter LOS
  bakom cover). Rakethopp: Space i luften, håll för mer kraft (tap ~3 m, full ~12 m).
- **AI**: vägnätsgraf + A*; fiender skjuter under framryckning, strafe:ar i närstrid,
  fastna-detektor (ompathning). **Soldatmodellerna är byggda med ansiktet åt −Z** →
  yaw = `atan2(-dx, -dz)` — `lookAt` pekar +Z och blir 180° fel!
- **Spawns**: LOS + avståndsgate (aldrig <60 m eller i spelarens synfält) över tre
  infallsvägar (Forsebron, syd, öst).

## Gameplay-design (befrielseläget, beslutat 2026-07-09)

- Start: fienden äger **A Gamla Torget, B Roten M, C Royens trappor** + ~36 man på
  kartan; spelaren har bara **D Basen** (spawnplatsen, Görjelycksgatans topp).
  Basen faller = förlust. Alla zoner återtagna + alla nedkämpade = seger.
- Fiender har roller: ~55 % **garnison** (tilldelas slumpad egen zon, vandrar dit och
  bemannar — ger rörelse över kartan), resten **anfallare** mot närmaste icke-egna zon.
- Fienden får förstärkningar (3 grupper à 6) **endast medan de håller zoner**
  ("försörjningslinjer") → att ta zoner har strategiskt värde.
- Allierade (9 st): 3 **basvakter** + 6 **anfallare** som pushar närmaste fiendezon,
  kan själva ta zoner, strosar kring sina positioner; stupade ersätts från basen var 45 s.
- Zonlogik: fiender i zon utan försvarare → progress upp; egna i zon utan fiender → ned.
  Hotlogik driver skärmkantspil + larm + minimap-ping (allt pekar på samma zon).
- Balansmått: total fiendebudget ~54; simulerad "realistisk spelare" (1 kill/5 s +
  allierade) klarar rundan på ~3,5–5 min. Testrigg: se CLAUDE.md (debughookarna).

## Viktiga beslut & motiv (kronologiskt urval)

| Beslut | Motiv |
|---|---|
| Three.js utan byggsteg, allt i en game.js | Iterationstakt slår struktur för ett hobbyprojekt; deploy = statiska filer |
| Stanna i Three.js (inte UE5/Unity/Arma) tills vidare | Utvärderat: UE5+Cesium är rätt väg OM projektet växer; iterationstakten här är oslagbar. Datapipelinen återanvänds vid byte |
| Esri-ortofoto ersatt med Lantmäteriet | Esris villkor förbjuder redistribution av bakade tiles; LM är CC BY 4.0 och skarpare |
| Terräng MeshBasic (oskuggad) | Fotot har ljuset inbakat; scenljus ovanpå blev blekt/blått |
| Klasskarta offline i pipeline (inte runtime-klassning) | Vårfotots färger kräver flera signaler (textur, LiDAR-lutning, OSM); tungt att göra i JS varje load |
| Berg = svart/residual i klasskartans RGB | Alfakanal förstörs av canvas-premultiply vid drawImage |
| Vatten: endast slutna OSM-ringar blir ytor | Öppna strandlinjer triangulerades till jättepolygon över halva kartan (dyr bugg) |
| data.js som JSON (~4 MB) i stället för binärt | Enkelhet; Pages gzip:ar till ~1 MB; parse < 200 ms |
| Cache-bust med `?v=N` på data.js/game.js/ortho/classmap | Webbläsare + Pages cachar aggressivt; N bumpas vid VARJE ändring av filerna |
| Fysik "fuskar" (ray-march, cylinderhinder, ingen fysikmotor) | Räcker för känslan; 55 fiender + 15 000 träd på ~1 ms/frame |

## Kända skulder / öppna frågor

- **Musikskolans skylt** står på skolhuset väster om ån (gissning — OSM saknar POI:n).
  Joel ska bekräfta/flytta.
- Joel ska peka ut **hemliga stigar** i skogen som saknas i OSM (ritas då in i datan).
- Vårfotot: gräs/skog gråblekt → klasstintning kompenserar, men hösten 2025-fotot vore bättre
  om G2-området omflygs.
- Fasaderna är procedurella (inte husens riktiga) — promenadfoton/drönare är planen (TODO).
- Ljudlandskapet är minimalt (syntetiska skott, forsbrus) — punkt i backloggen.
- `updateWaves` heter kvar så trots att vågorna är borta (befrielseläget) — omdöp vid tillfälle.

## Deploy & repo

GitHub: `KytioisaCat/kvarnbyn-fps` (Joels **privata** konto — inte jobbets, aldrig GitLab).
Push till `main` → GitHub Actions → Pages: https://kytioisacat.github.io/kvarnbyn-fps/
Licensfrågor för publicering: se DEPLOY.md (löst 2026-07-08 i och med Lantmäteriet-bytet).

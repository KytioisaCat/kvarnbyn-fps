# Arkitektur & beslutslogg — Försvara Kvarnbyn

Syftet med detta dokument: en ny session (eller människa) ska på fem minuter förstå
*varför* saker ser ut som de gör. Läs CLAUDE.md för arbetsflöden/fällor och TODO.md
för läget — detta är bakgrunden och besluten. **KRAVSPEC.md** är den teknikoberoende
kravbilden (vad Joel önskar sig, oavsett implementation) — utgå från den vid större
omprövningar eller nya planer.

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
build_classmap.py  ────────► public/classmap.png (1608×1086, 2 m/cell)
build_data2.py     ────────► public/data.js (~9 MB; hus/vägar bär OSM-way-id + husfakta-taggar)
build_flats.py     ────────► public/flats.js (byggda plana ytor + brokedjor med way-id:n)
husfakta_lista.py  ────────► husfakta_kandidater.md (hus att titta på → public/husfakta.js, för hand)
```

Bbox:en är en enda sanning i `tools/bbox.py` (Pass A, 2026-09) — kartan växte +50 % i radie
(Pass B) med oförändrat centrum så alla spelkoordinater är stabila.

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
- **Splat-shader** (onBeforeCompile på terrängmaterialet): klasskartan väljer markmaterial
  och **färgtonar fotot per klass på alla avstånd** (skog → mättad grönska osv).
  Närfältet (<30 m, uttonat till 110 m) ÄGS av 512px-detaljtexturerna (procedurell canvas:
  gräs/asfalt/skogsbotten/granit) — fotot bidrar där med *ljus* men bara 35 % färg
  (vårfotot är gråblekt och smetar annars över kulörerna). Bakat per-vertex-terrängljus
  (`aGround.x`) ger relief, branthet (`aGround.y`) blandar in berg i slänter, makrobrus
  på 45 m-skalan dödar tiling. Kvällsläget dämpar detaljfältet via uniform `uNight`
  (sätts i `applyNightMode` — Basic-materialets färgtint räcker inte då detaljfältet
  har eget golv).
- **Byggda plana ytor** (`public/flats.js`, extraherad ur OSM: parkeringar/planer/
  lekplatser/torg): terrängen **plattas vid load** med minsta-kvadrat-plan per polygon
  (gradient klämd till 8 %, 3,5 m feather-kant) FÖRE origElev-kopian så båda höjdgriddar
  delar plan mark. Ytmeshar ovanpå (+0,08 m): asfalt med genererade **P-rutelinjer**
  (orienterade via minAreaRect, klippta mot polygonen), grus på planer, smågatsten på
  torg. Principen: **människobyggt = platt, natur = gropig** — LiDAR-brus × EXAG gav
  annars 10–30 cm gropar på asfalt (uppmätt), ögat avslöjar det direkt. OBS: OSM-ringar
  har blandad vridriktning — trianglarnas front tvingas uppåt per triangel, annars
  flippar DoubleSide-normalen och ytan blir svart. Tuvor/stenar cullas via `flatAt`
  (spatial hash), som också ger full gångfart på hårdgjorda ytor.
- **Kollision/sikt**: ingen triangel-raycast. Kulor/LOS = analytisk ray-march
  (`pointBlocked`) mot polygon/segment/cirkel-hashar (`bldHash`/`wallHash`/`obstHash`,
  cellstorlek `CELL=24`). Skogsceller ackumulerar "lövdjup" — sikt blockeras efter ~14 m.
  **Nya hinder måste in i rätt hash**, annars går kulor igenom.
- **Tak**: alla tak bär spelaren. Platta = topY; sadeltak = interpolerad höjd nock→takfot
  (`roofYAt`); 0,6 m step-up-assist vid kanter. Sadeltaksinfo sparas per byggnad (`gable`).
- **Husfakta** (2026-09-10): hur enskilda hus SER UT ligger som data, inte kod. Två källor slås
  ihop per hus i `factsFor`: OSM-taggar ur data.js (`lv` våningar, `col` kulör, `rs` takform,
  `mat` material, `addr`) och `public/husfakta.js` (handförfattat, nyckel `w<OSM-id>` eller adress;
  fält farg/vaningar/hojd/tak/takfarg/material/skylt/kommentar/kalla). Arbetssättet är KRAVSPEC
  §4:s: **titta** på foton/Street View som referens och beskriv i ord — aldrig pixlar in i
  spelet. `tools/husfakta_lista.py` genererar kandidatlistan med länkar. Svenska färgnamn och
  CSS-namn stöds; OSM:s skrikiga namn ('yellow') dämpas i HSL. Tegel är tredje fasadmaterial.
  `skylt` blir en textplatta på fasaden som vetter mot närmaste gata (roadHash-probe 3 m ut).
- **Byggnader**: nästan-rektangulära fotavtryck snappas till minsta omslutande rektangel
  (fyller ≥68 %); småhus < 350 m² får träpanel, större slät puts (två fasadtexturer);
  vita kulörer (Joels fakta: Kvarnbyn är vita trä-/putshus); ~hälften av småhusen i
  kärnan (x 60–340, z −200–80) sänks till 1 våning (seedat på position = stabilt).
- **Murar**: OSM-barriärer + **procedurella stödmurar** ur väg×terräng-tvärlutning
  (diff >1,35 m vid vägkant) + räcken där marken störtar (>2,2 m, hoppbara).
- **Broar** (v2, 2026-09-10): OSM `bridge=yes`-ways kedjas i `tools/build_flats.py` (namn+klass
  via delade ändnoder) till spann med **linjärt däck landfäste→landfäste** och **OSM-way-id:n**.
  Vägar kopplas till SIN kedja via way-id (`bridgeByWay`) — v1 matchade på närhet + riktning,
  och då stal viadukten höjd åt gångbron intill medan gatan under ibland kastades upp.
  Knutpunkter **mellan** broar (ändpunkt som ligger på en annan kedjas däck: ramp ↔ rondellen
  uppe på Mölndals bro, cykelbana som ansluter mitt på viadukten) tar **grannens faktiska
  däckhöjd där** — vid rampens landfäste är det marken, uppe på viadukten är det däcket. Bara
  kedjor som bevisligen är **viadukter** (korsar en annan väg som inte själv är bro/tunnel, en
  bit in på spannet) får delta i knutlyft; rondellen (sluten slinga utan landfästen) **seedas**
  till mark + 6 m och ramperna hämtar sin topp därifrån (tre varv). v2.0 lade alltid på +6 m i
  varje knut → små gångbroar över ån och stigar vid brofästena svävade i luften utan ramp
  ("sticker upp i ingenting", Joel 2026-09-10). **Branta "broar" (>25 %) släpps** helt — det är
  trappor/ramper på en bergssida taggade bridge; ett linjärt däck blev ett 26 m högt torn vid
  (−168,−199). Inre brytpunkter på en bredare parallell kedjas däck snappar till den (ramp upp,
  gemensam nivå, ramp ner); lutningsspärr 10 % bara för viadukter med bilväg (högst 8 m lyft).
  Däcket är facit på bron, marken får bara lyfta banan de sista 12 m mot ett riktigt landfäste.
  **Verifiera alltid från luften och från vägbanan** (`__aerial`/`__onRoad`-hjälpare i sessions-
  loggen; `window.__THREE` finns för raycast) — en provkamera som råkar stå inne i ett hus ser
  en jättevägg och lurar en att jaga brofel som inte finns. Rendering:
  **sammanhängande däckband** med gering (v1:s per-segment-lådor med överlapp skar i varandra),
  räcken som `guard_rail`-murar bara på fria kanter (körbana + gångbana på samma bro får inget
  räcke emellan). `groundInfoAt(x,z,refY)` ger däcket bara till den som är uppe på det — man kan
  gå under. Otaggade broar: heuristik där vägbana >0,9 m över mark **och <22 m från ån**.
  **Mätmetod**: proben går 1 m-steg längs alla vägar/kedjor med refY-spårning via
  `__game.groundInfoAt` och räknar höjdhopp >45 cm — 4 716 → 842 av 203 000 steg. Kör den igen
  vid ändringar i vägar/broar/terräng (koden ligger i sessionsloggen 2026-09-10; ~40 rader JS).
- **Gångyta = ritad bana**: `roadSegs.ya/yb` använder samma tvärsnitts-max som ribbon-renderingen
  (med tak 1,2 m så kanten alltid är klivbar) — förr mättes gångytan i mittlinjen och fötterna
  sjönk upp till 2,8 m ner i asfalten på tvärlutande gator (4 % av segmenten >40 cm).
  `groundInfoAt` tar dessutom **närmaste segment per väg**: grannsegment längs samma lutande gata
  gav (klämd projektion mot sin bortre ände) 1–1,5 m-hopp.
- **Vägrendering**: polylinjer förtätas till 3,5 m-segment och varje tvärsnitt tar
  **max över bredden** (plan i tvärled, som riktiga vägar) — annars stack terrängbulor
  mitt på långa OSM-segment upp genom vägbanan ("grön jord i gatan").
- **Rörelse**: branthetsspärr med **1,6 m lookahead** (aldrig per frame-steg — brus),
  spärr 0,60 / tung klättring 0,38, vägar/trappor alltid gångbara (Royens trappor är
  0,61 längs linjen!), kravla fritt i/vid åfåran. Vägfart 1,0 / terräng 0,8 / skog 0,5 /
  vatten 0,35 + ström som drar nedströms + skada i vitvatten. Crouch = håll C (bryter LOS
  bakom cover). Rakethopp: Space i luften, håll för mer kraft (tap ~3 m, full ~12 m).
- **AI**: vägnätsgraf + A*; fiender skjuter under framryckning, strafe:ar i närstrid.
  Fastna-detektorn (ingen förflyttning på 1,6 s) triggar en **flyktmanöver** (`planEscape`):
  proba sidled/bakåt mot `insideAnyBuilding`, gå åt fritt håll ~1 s (eskalerar vid
  upprepning), räkna sen om vägen från den nya positionen — waypoint-hopp räckte inte
  när soldater klämdes i inre hörn mellan två hus. **Soldatmodellerna är byggda med ansiktet åt −Z** →
  yaw = `atan2(-dx, -dz)` — `lookAt` pekar +Z och blir 180° fel!
- **Spawns**: LOS + avståndsgate (aldrig <60 m eller i spelarens synfält) över tre
  infallsvägar (Forsebron, syd, öst).
- **Kartor**: minikartan är zoombar (60–420 m radie; scrollhjul, +/− via `e.key` så svenskt
  tangentbord fungerar, tryck på kartan på mobil; sparas i localStorage) med skalstock; taktiska
  kartan zoomar 1–4,5× som ett utsnitt centrerat på spelaren, klämt mot kartkanten.
- **Input**: desktop = pointer lock + WASD/mus; pekskärm (detekteras med `pointer: coarse`,
  tvingas med `#touch`/`#desktop` i URL:en) = DOM-touchkontroller: analog spak (full
  utstyrning = sprint, liten = smyg), sikt-drag på fri yta (första touchen utanför
  kontrollerna), HUKA är **växlande** (håll-knapp funkar inte med två tummar upptagna),
  hoppknappen återanvänder raketlogiken (`tryRocket`). Vid start: fullskärm +
  landskapslås i stället för pointer lock. DPR-tak 1,5 på mobil (fillrate-gräns).

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

## Datorversionens soldat- och tillgångspipeline (2026-10-30)

`v2/kvarnbyn/rebuild.sh` bygger även `blender/build_ak5.py` och `build_soldier.py` före
Godot-import. Quaternius SWAT-källan (3,37 MB, CC0) och licens/hash versionshanteras;
genererade GLB-filer och Mac-appen förblir lokala. Tvåhandsfattning bakas offline i Blender.
`soldier_visual.gd` väljer klipp utifrån verklig lokal rörelse och följer huvudbenet med
huvudträffzonen. Samma egenbyggda Ak 5 används i spelarens vy och på soldaten.

`soldier_tactics.gd` använder vägnätet för långa sträckor och lågfreventa beslut om korta
flank-/skyddsförflyttningar. Golvprover och kapselsvep prövar kandidaterna mot faktisk
kollisionsgeometri. Målet koms ihåg kort efter tappad sikt; inget exakt följande genom väggar.
Varje skott kräver både aktuell huvud- och mynningssikt. Lite högre fiendetryck styrs via
`enemy_fire_interval_scale`/`enemy_accuracy_scale` i `site.py` → `game.json`.

Det återkopplade torgunderlaget använder uttryckliga graderingskanter i meshen, ankarhöjder
från triangulerad befintlig mark och exakt terrängklippning. Detta pass omfattar förgården och
tre planteringsöar; den grövre nordbanksytan behöver eget platsprov. Höjder/konturer är
uppskattade, medan förekomst av stenläggning och tre unga träd är visuellt observerad.

**Importfälla:** MultiMesh-data från en headless import kan tappa GPU-buffertens placeringar.
Importören sparar därför även CPU-transformer på noden; runtime återställer bufferten en gång.
`configure_import.gd` rensar bara världens genererade scen-cache så pass två verkligen kör det
aktuella importskriptet. `verify_trees.gd` kontrollerar de sparade placeringarna, och nativebilden
måste också visa grönskan. Tidiga FPS-mätningar utan synliga träd ersattes med ett nytt prov.

Alla agentkörda Godot-prov ska vara ljudlösa (`--audio-driver Dummy` och mutad masterbuss).
Vanlig manuell spelstart har ljud. Provflaggorna capture/bot/probe/walktest mutar automatiskt.

## Platsprov Roten M 29 (2026-10-31)

`reference/roten-m/OBSERVATIONER.md` skiljer faktisk bildgranskning från uppskattade mått.
Street View augusti 2024 och publik exteriör visar låga sammanbyggda vita trähus, små
gårdsnivåer, naturligt berg och låg stenbäddkant. DTM:s nivåskillnad vid M31 bevisar ingen
stödmur; den byggs först efter egen visuell kontroll. M30/M31 är fortsatt osäkra kontexthus.

`house.json` → `interpret.py` → `blender/roten.py` ersätter M29:s gamla automatiska
tvåvånings-/valmningstolkning. OSM-fotavtrycket behålls; takdelning, höjder och dolda
fasader är uppskattade. Inga referensfoton används som material i spelet.

`roten_ground.py` ger disjunkta sten/grus/gräs/bergytor. Anslutningar förankras i befintliga
färdiga gångtrianglar inklusive respektive ytlyft. En lokal viktad planförlängning undviker
höjdknäcken när närmaste kant växlar mellan Royens gata och Roten M. Gamla gatu-, vatten-
och brotrianglar ändras inte. OSM:s `surface=sett` styr ett lokalt materialval i Blender.
Nya ytor klipper terrängen exakt och deras ytterkanter fylls som slutna markvolymer.
Kantfyllningarna är byggteknisk tolkning, inte fler visuellt belagda murar.

Små trädgårdsformer trianguleras med **0,4 m** celler: världens vanliga 2 m-nät tappade
upp till 31 cm av bergens/terrassernas form i faktisk Godot-geometri. Tre synliga steg har
en sammanhängande kollisionsramp; bild-/gångytans avsiktliga skillnad är högst ett steg.
`verify_roten.gd` provar den importerade världen med riktiga golvstrålar, spelarkapseln,
öppen grind och staketstopp; `qa_roten_ground.py` jämför Blender-mesharnas bild-/gångytor.

## Sammanhängande Stalleliden (2026-11-01)

`reference/stalliden/OBSERVATIONER.md` dokumenterar faktiskt granskad Street View för
M30 och fotografens trapp-/M25-bilder från 2017. M30 får stående vit panel, ockrafoder,
rödbruna detaljer och liten vindruta; höjderna förblir antagna. M31 får ursprunglig
OSM-kontur med klippt antaget sadeltak, men ingen ny påstått verifierad fasad eller hög mur.

`stalliden.py` författar hela vägen från Roten M till Norra Forsåkersgatan som en
sammanhängande färdig höjdprofil. Ankare tas från gamla triangulerade färdiga gångytor,
inklusive deras respektive ytlyft; nya callbacks har **lift 0**. Två gamla generiska
trappor och deras räcken ersätts. Vilplan delar 16 korta lopp; synliga steg följer
osynliga kollisionsramper med högst ett stegs avvikelse. `stairkit.py` bygger även riktiga
tunna slutna räckeskolliderare. Terrängklippning och 0,3 m trianglar med mjuka marginaler
hindrar gamla grova grästrianglar från att skära igenom stegen.

Originalbandet undantar uttryckligen parallellstigen och körbanan vid trappfoten.
En kort uppskattad fotgängarlänk kopplar trappans botten till gatans nät; noden förs in
även i soldaternas graf. Ingen tidigare körbana tas bort. `stalliden_garden.py` ger
gräs, fem träd, 42 buskgrupper och en kort uppskattad mur/plank på den visuellt belagda
norra tomten. Tekniska kantfyllningar märks separat från observerade murmotiv.

`world_meta.stalliden_ground_checks` körs med samma riktiga kapselprov som M29 via
`verify_roten.gd --check-key=stalliden_ground_checks`. Båda hela 112 m-banorna, punktprov,
räckesstopp och fri passage är obligatoriska i `rebuild.sh`. `reference/stalliden/qa-export.py`
provar dessutom transformerade GLB-trianglar. Slutbilder tas med release-appens vanliga
`--view/--capture`-flaggor; `--script` ignoreras av release-mallen och är bara för editorn.
Se `RESULTAT-STALLELIDEN.md` för omfattning och återstående husarbete.

## Viktiga beslut & motiv (kronologiskt urval)

| Beslut | Motiv |
|---|---|
| Three.js utan byggsteg, allt i en game.js | Iterationstakt slår struktur för ett hobbyprojekt; deploy = statiska filer |
| Stanna i Three.js (inte UE5/Unity/Arma) tills vidare | Utvärderat: UE5+Cesium är rätt väg OM projektet växer; iterationstakten här är oslagbar. Datapipelinen återanvänds vid byte |
| **2026-10-21: v2 = ny kod i samma repo** (`v2/`, Three.js+TS+Vite), v1 fryst i `public/` | "Ser verkligt ut" är hela arkitekturen (PBR, IBL, skuggor, asset-format), inte en renderare att byta i game.js. Nytt repo förkastat: pipeline, kalibreringar, husfakta, beslutslogg och v1 som facit bor här. Webben valt framför UE5/Godot: Joel spelar från länk på telefonen utan nedladdningar (mätt uppkoppling), telefonen är test-GPU:n. Plan: `v2/PLAN.md` |
| **2026-10-29: Spelet = Godot-datorapp i `v2/kvarnbyn/`** (Fas A värld + Fas B spel) | Joel godkände PoC-grafiken och sa att ett FPS ska spelas med mus och tangentbord på dator. Forward+ med realtids-GI (SDFGI) i stället för ljusbake. Fiender/allierade följer vägnätsgrafen (AStar3D ur OSM) som i v1; v1 facit för funktioner, inte för känsla. Fiendens erövringstakt halverad mot v1 (basen föll på < 5 s). Soldater > 90 m bort utan kollisionsfysik (fysiken tog 9 ms/steg) |
| **2026-10-22: Omstart — v2:s skelett underkänt** | Fyra försök (v1, v2-terräng, v2-vägnät, v2-flats) ritade rådata direkt och såg "fruktansvärt" ut för Joel. Diagnos: vi ritar data i stället för att bygga en värld av tillgångar; handskriven motor; punktmolnet oanvänt. Ny väg i `OMSTART.md`: tolka → bygg med riktiga verktyg → spela; motorval Unity/webb eller Unreal/PC öppet |
| **2026-10-21: v2 bygger banan som geometri offline (`tools/v2model/`), inte som draperingar i webbläsaren** | Joels krav: CoD-look ur dåliga data = konstruerad geometri (plana ytor, kantsten, riktiga broar), inte foto på brusigt höjdfält. v1:s broar blev aldrig rätt eftersom varje objekt lappades för sig i game.js. v2: vägnät som graf, EN global profil-lösning med villkor (fri höjd, jämnhet över noder, markband), terrängen räknas om mot vägarna, mätgrindar stoppar bygget. Bevis på Mölndals bro + torget samma kväll, alla grindar gröna (`v2/docs/bevis-torget-2026-10-21/`). Splats/fotogrammetri lagda på is: inga fångster att utgå från |
| **2026-10-21: v2 byggs lokalt, inte i molnet** | Claude Code cloud-sessioner provades (miljö + setup-script klara) men Consats Claude-org saknar GitHub-connectorn och den kan inte aktiveras. Källdata (`tools/lidar_1m.png`, `tools/osm_raw.json`) förblir committade så pipelinen går i vilken klon som helst utan Lantmäteriet-konto |
| LiDAR-griden committad som 16-bit PNG + OSM-råfil committad | Molnsessioner klonar bara git; 2,7 GB Lantmäteriet-cache finns bara lokalt. 1 cm-kvantisering (4,9 MB) räcker för allt utom fetch_* |
| Esri-ortofoto ersatt med Lantmäteriet | Esris villkor förbjuder redistribution av bakade tiles; LM är CC BY 4.0 och skarpare |
| Terräng MeshBasic (oskuggad) | Fotot har ljuset inbakat; scenljus ovanpå blev blekt/blått |
| Klasskarta offline i pipeline (inte runtime-klassning) | Vårfotots färger kräver flera signaler (textur, LiDAR-lutning, OSM); tungt att göra i JS varje load |
| Berg = svart/residual i klasskartans RGB | Alfakanal förstörs av canvas-premultiply vid drawImage |
| Vatten: endast slutna OSM-ringar blir ytor | Öppna strandlinjer triangulerades till jättepolygon över halva kartan (dyr bugg) |
| data.js som JSON (~4 MB) i stället för binärt | Enkelhet; Pages gzip:ar till ~1 MB; parse < 200 ms |
| Cache-bust med `?v=N` på data.js/game.js/ortho/classmap | Webbläsare + Pages cachar aggressivt; N bumpas vid VARJE ändring av filerna |
| Fysik "fuskar" (ray-march, cylinderhinder, ingen fysikmotor) | Räcker för känslan; 55 fiender + 15 000 träd på ~1 ms/frame |
| Touchkontroller som DOM-element (inte ritade i canvas) | CSS sköter layout/safe-areas/media queries gratis; touch-targets får egna event utan hit-testning i JS |
| Människobyggt = platt, natur = gropig (flats plattas i runtime, inte pipeline) | Ögat avslöjar vågig asfalt direkt men förlåter gropigt gräs; runtime-plattning ur flats.js slipper pipeline-körning och håller data.js orörd |
| Närfältet ägs av detaljtexturer, fotot ger bara ljus + 35 % färg | Vårfotot är gråblekt — full fotomultiplikation smetade grått över gräsgrönskan; luminansen behåller ändå skuggor/solfläckar och kvällstonen |
| Väg↔bro via OSM-way-id, inte närhet | Närhetsmatchning lät viadukten stjäla höjd åt gångbron intill (4–5 m-klippor uppmätta); id:n är exakta och gratis ur samma OSM-data |
| Broknutar tar grannens däckhöjd; bara rondellen seedas mark + 6 m; branta broar släpps | +6 m i alla knutar (v2.0) fick gångbroar att sväva; grannens faktiska höjd är marken vid landfästen och däcket på viadukten. DTM:en under rondellen är gatan nedanför → 6 m ≈ fri höjd + däck |
| Gångyta = ritad vägbana, närmaste segment per väg | Det ögat ser ska bära fötterna; max över alla grannsegment gav klämda höjder från bortre ändar |
| Husfakta som data (husfakta.js + OSM-taggar) | Igenkänning kräver att enskilda hus kan rättas mot verkligheten, hus för hus, utan kodändring — och KRAVSPEC förbjuder bilder från karttjänster, så beskrivning i ord är vägen |
| Mätdriven geometrifix (probe före/efter) | "Knasiga ytor" är omöjliga att felsöka med ögat i 3 400 hus och 2 500 vägar — proben pekade direkt på Mölndals bro, klämda projektioner och sjunkande gångyta |

## Kända skulder / öppna frågor

- **Musikskolans skylt** står på skolhuset väster om ån (gissning — OSM saknar POI:n).
  Joel ska bekräfta/flytta.
- Joel ska peka ut **hemliga stigar** i skogen som saknas i OSM (ritas då in i datan).
- Vårfotot: gräs/skog gråblekt → klasstintning kompenserar, men hösten 2025-fotot vore bättre
  om G2-området omflygs.
- Fasaderna är procedurella (inte husens riktiga) — husfakta.js är vägen att rätta dem hus för
  hus (kandidatlista i tools/husfakta_kandidater.md); promenadfoton/drönare längre fram (TODO).
- Broar: Gunnebogatans bro (NV) och cykelbanan vid Mölndals bros västra landfäste har kvar
  1–2 m-steg; E6:ans broar saknar vägbana (`motorway` ej i ROAD_W); 20 tunnelvägar ritas på ytan.
- Ljudlandskapet är minimalt (syntetiska skott, forsbrus) — punkt i backloggen.
- `updateWaves` heter kvar så trots att vågorna är borta (befrielseläget) — omdöp vid tillfälle.

## Deploy & repo

GitHub: `KytioisaCat/kvarnbyn-fps` (Joels **privata** konto — inte jobbets, aldrig GitLab).
Push till `main` → GitHub Actions → Pages: https://kytioisacat.github.io/kvarnbyn-fps/
Licensfrågor för publicering: se DEPLOY.md (löst 2026-07-08 i och med Lantmäteriet-bytet).

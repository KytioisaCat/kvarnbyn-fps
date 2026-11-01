# TODO — Försvara Kvarnbyn

Idébacklogg. En punkt i taget, ~30 min styck. Bocka av med `[x]` och flytta till
Klart-sektionen med datum. Claude: läs denna fil vid sessionstart (se CLAUDE.md).

## Omstart 2026-10-22 (läs `OMSTART.md` först)

Joel underkände v2:s approach helt. Ny väg: datan tolkas till en stadsbeskrivning, världen byggs
med riktiga verktyg och tillgångar (motor + vägverktyg + arketyp-kit + punktmoln), inget mer
handskrivet ritande av rådata. v2/ och tools/v2model/ ligger kvar som historik/tolkningsdelar.

- [x] PoC-sekvens och verktyg godkända/genomförda 2026-10-29; aktiv väg är Godot desktop i `v2/kvarnbyn/`.
- [x] Joels dom 2026-10-29: grafiken är rätt; målplattform dator (mus+tangentbord)
- [x] Beslut om `v2/poc/NASTA-FAS.md` (Joel ja 2026-10-29)
- [x] Fas A bedömd genom Joels dom över det spelbara Fas B-provet (2026-10-30).
- [x] Fas B — spelbart (2026-10-29): vapen, reload, hopp, fiender, zoner, HUD; `v2/kvarnbyn/RESULTAT-FAS-B.md`
- [x] Joels dom över Fas B (2026-10-30): bättre än v1, mer action; ville ha raket/flygläge för test → klart
- [ ] **Joels bedömning av soldat-/vapenpasset** (`v2/kvarnbyn/RESULTAT-SOLDATER.md`): utseende, aktivitet och svårighet.
- [ ] **Joels bedömning av kvällsljuset** (`v2/kvarnbyn/RESULTAT-KVALL.md`): läsbarhet i strid, stämning och lyktövergångar under promenad.
- [ ] **Världen (kärnan)**: fortsatt grönska och terrasser per plats. M29 och Stallelidens första gång-/platsprov är genomförda. Nästa husarbete: visuellt belägga M31 och återskapa M24/M25:s volymer, grunder, tak och entréer längs trappan. Granska innan nya höga murar byggs.
- [ ] **Joels bedömning av Stalleliden/M30** (`v2/kvarnbyn/RESULTAT-STALLELIDEN.md`): igenkänning och gångstråk; grannhusen är fortfarande delvis generiska.
- [ ] **Joels bedömning av Roten M 29** (`v2/kvarnbyn/RESULTAT-ROTEN.md`): igenkänning, husproportioner och markmiljö. Övriga grannhus är fortfarande generiska.
- [ ] **Nordbanken**: kontrollera uppskattad stenläggningskontur och anslutande gatuprofiler i ett separat platsprov; inte inkluderad i förgårdspasset.
- [ ] Framtid: pacing (Gamla torget som lugn bas med NPC:er, anfall mot Mölndals centrum via berget/ån), världen ut till Mölndals centrum och Götaforsliden
- [ ] **Fas C** — kvällsljus, husrundor (Street View som referens), staket/häckar/trädgårdar, järnväg
- [ ] Tolkning: takform/takhöjd/nockriktning per hus + träd ur punktmolnet; arketyp per hus
- [ ] Ett arketyp-kit + ett hjältehus (Blender) med riktiga material
- [ ] Första beviset: EN bild vid Gamla torget som ser ut som ett spel (hus, gata, träd, bakat ljus)

### Föreslagna kontrollprov efter lägesgenomgång 2026-10-29

- [ ] **Exportprov tidigt i PoC 0–1**: ett igenkännbart hus + gatan framför i Blender;
  prova samma modell/material via glTF i Godot Compatibility med bakat ljus. Jämför från
  samma kamera och ögonhöjd på telefonen. En fin Cycles-bild bevisar inte spelversionens look.
- [ ] **Terräng på webben separat**: Terrain3D:s webbexport beskrivs fortfarande som
  experimentell av projektet. Börja motorprovet med en liten statisk terrängmodell ur vår
  LiDAR; testa Terrain3D separat på Joels telefon innan hela kvarteret byggs kring tillägget.
  Källa: https://terrain3d.readthedocs.io/en/stable/docs/platforms.html
- [ ] **Punktmoln i liten skala före helautomatik**: testa takhöjd/takform på 5–10 hus mot
  referenser och märk osäkra slutsatser. Utvärdera trädposition/höjd separat; artbestämning
  och exakt nockriktning ska inte förutsättas fungera från glesa punkter.

## v1-backlogg (FRYST 2026-10-21 — v1 är referens, bara hotfixar på Joels begäran)

- [ ] **Husfakta: fyll i hjältehusen** — gå igenom `tools/husfakta_kandidater.md` (93 hus med
  Street View-länkar att TITTA på), skriv kulör/våningar/tak/material i `public/husfakta.js`
  för Corpus, Kråkan, Götaforsliden-raden, Roten M, stadsmuseet (aldrig bilder in i spelet)
- [ ] **Bro-rester** — Gunnebogatans bro (NV; OSM-ändarna ger 28 % däcklutning, nu klämd till 8 %)
  och gång-/cykelbanan vid Mölndals bros västra landfäste (−800,180) har kvar 1–2 m-steg;
  motorvägsbroarna (E6) saknar vägbana helt (`motorway` ej i ROAD_W) — proben: se ARKITEKTUR.md
- [ ] **Tunnlar** — 20 vägar taggade tunnel (`tu:1` i data.js) ritas fortfarande som ytvägar;
  rita underfart eller dölj dem under marken

- [ ] **Frontlinje på kartorna** — tona fiendekontrollerat område rött på minimap/M-kartan
  med gränslinje + anfallspilar från de tre infallsvägarna (förslag 2 från frontlinje-rundan)

- [ ] **Ljudlandskap** — fotsteg (asfalt/gräs olika), vapenljudsvarianter, avlägset
  stridsmuller när AI strider utom synhåll, vind i träden
- [ ] **Vapenpaket** — ADS på högerklick (zoom + lägre spridning), prickskyttegevär,
  hagelgevär, vapenväxling 1/2/3
- [ ] **Granater** — kast med G, kastbåge, explosion med splash-skada
- [ ] **Förnödenheter** — ammo-/förbandslådor vid egna capture points, respawn mellan vågor
- [ ] **Fiendevariation** — rusare (snabb/svag), tungt infanteri (3× HP, långsam),
  prickskytt (håller avstånd, siktvarning); vågorna blandar typerna
- [ ] **Poäng & highscore** — kills/headshots/återtag ger poäng, slutstatistik,
  localStorage-highscore
- [ ] **Launch-polish** — OG-metataggar + delningsbild, favicon, mute-knapp,
  muskänslighet, "spela igen" utan omladdning

## Idéer längre fram (större än 30 min)

- [ ] Historiskt läge: Lantmäteriets historiska ortofoton 1960–1999 finns i samma
  STAC-API (`orto-historiska-*`) — barndoms-Kvarnbyn! (samma nedladdningsrätt krävs)
- [ ] Fasadtexturer från Joels promenadfoton (EXIF-GPS+kompass → matcha mot husens
  fotavtryck, räta upp i perspektiv, projicera på väggarna)
- [ ] Drönarfotogrammetri av kärnkvarteren (instruktionsmejl till piloten är skrivet)
- [ ] Multiplayer/co-op (kräver server — utanför statiska sajtens ram)
- [ ] Motorbyte UE5 + Cesium om projektet växer (datapipelinen återanvänds)

## Klart

- [x] 2026-11-01 — **Kvällsljus och gatlyktor**: valbart Eftermiddag/Kväll i menyn, varm låg sol/sval himmel, befintliga lyktor med glöd och högst åtta närliggande skuggljus. Integrationsprov för meny/material/ljuspool; native stridsprov 69/65 FPS median för eftermiddag/kväll på M5. Resultat: `v2/kvarnbyn/RESULTAT-KVALL.md`.

- [x] 2026-11-01 — **Stalleliden + M30/M31, första platsprov**: sammanhängande 112 m-stråk, korta lopp/vilplan, verkligt räckesstopp, fem träd/42 buskgrupper; M30:s belagda gavel och M31:s ursprungliga kontur. 2 088 GLB-prover och riktiga kapseln åt båda håll gröna, full återbyggnad/Mac-app. Mått och dolda fasader fortsatt uppskattade. `v2/kvarnbyn/RESULTAT-STALLELIDEN.md`.

- [x] 2026-10-31 — **Roten M 29**: faktiskt granskad Street View/exteriör, låg vit husgrupp med rund gavelruta, cirka 83,5 m² gård/grus/gräs/berg, tre steg, låg stenbäddkant, öppen grind, staket, två träd och 17 buskgrupper. Verklig kapselgång, faktiska Blender-meshar och Mac-export verifieras i `v2/kvarnbyn/RESULTAT-ROTEN.md`; M30/M31 kvarstår.

- [x] 2026-10-30 — **Torgförgården återkopplad**: 940 m² sten, 82 m² planteringar, tre unga träd och 24 buskproxyer; 3 757 actual-mesh-prov utan hål/höjdspikar. Även skogsträdens tappade placeringar efter Godot-import rättade och visuellt kontrollerade i Mac-exporten. Nordbanken återstår som separat platsprov.

- [x] 2026-10-30 — **Soldater och Ak 5**: riggad Quaternius CC0-modell (62 ben/24 klipp), bakad gevärsfattning, flank-/skyddsmål och färsk mynningssikt; ny egen Blender-Ak 5 med sikt- och omladdningsprov. Fiendens eldintervall ×0,92 och träffchans ×1,08 ligger i `site.py` → `game.json`. Resultat: `v2/kvarnbyn/RESULTAT-SOLDATER.md`.
- [x] 2026-10-30 — **Tysta agentprov**: Dummy-ljuddrivrutin och automatisk mute i provskript/capture/bot. Regeln står i CLAUDE.md/AGENTS.md.

- [x] 2026-10-29 — **Fas A: Kvarnbyn 900×700 m som Mac-app** (`v2/kvarnbyn/`): 381 tolkade hus +
  hjältehus, gator, ån, broar, Royens trappor, träd, realtids-GI, 111–120 fps, gångtest 180/180.

- [x] 2026-10-29 — **PoC Gamla torget: Blender-innehåll + Godot-webbprov** (Codex byggde, Claude
  slutförde): Kråkan, Corpus, Musikskolan m.fl. ur kit med CC0-material, egna träd, bakat ljus,
  FPS-kontroller dator/touch, webbexport 51 MB för telefon, 120 fps på M5. Se
  `v2/poc/torget/RESULTAT.md`. Telefonprov och Joels bedömning återstår. `DAGBOK.md` infört
  för överlämning mellan agenter.

- [x] 2026-10-29 — **Lägesgenomgång efter omstarten**: senaste incheckade riktningen är
  `OMSTART.md` → `POC-PLANER.md` (2026-10-22), inte de gamla Three.js-delmålen.
  Inga PoC-leveranser eller Blender-/Godot-projekt hittades i repot. `v2/PLAN.md` märkt
  som historik; kontrollprov för export, webbterräng och punktmoln tillagda som förslag.
  Inget motorval fastslaget och inga nedladdningar gjorda i denna genomgång.

- [x] 2026-10-22 — **M1b flats + stödmurar + bergväggar** (alla 12 grindar gröna, bilder i
  `v2/docs/bevis-torget-2026-10-21/` dag 2): `flats.py` (plan per OSM-yta, vägar bundna till
  planet, egen mesh/kantsten, konformering), `walls.py` (stödmurar ur konformeringens resultat,
  757 m), konformeringen blendar inte över terrasskanter, triplanär bergtextur på branta ytor,
  räcken bara längs brosidor, gång på däck (raycast), spawn på bron, `?at=` startplatser, port 5187

- [x] 2026-10-21 (kväll) — **Bevis: Mölndals bro + vägnätet runt Gamla torget byggt offline, alla
  8 mätgrindar gröna** (`v2/docs/bevis-torget-2026-10-21/`). Ny pipeline `tools/v2model/`:
  vägnätsgraf ur OSM (nodar korsningar utan nod), global profil-lösare (aktiv mängd: markband,
  jämnhet inom/över noder, maxlutning, fri höjd per klass, däck över mark, tunnlar, trappor,
  trottoar bunden till gata, lösa ändar snappade), band + korsningspolygoner + kantsten med kjol,
  brodäck per brogrupp med sidor/undersida/räcken/pelare, terrängkonformering, rapport.
  `v2/src/roads.ts` laddar mesharna; `__fly` för bevisbilder. VISION.md §3b: varför detta inte är v1.

- [x] 2026-10-21 — **v2 lokalt i stället för molnet**: molnformuleringar bort ur docs, `v2`-server i
  `.claude/launch.json` (Vite 5173), `tools/build_v2.py` exporterar `height.png` (1 m, RGB hi/lo-
  byte), `classmap.png`, `ortho_8k/4k.jpg`, `meta.json` till `v2/public/data/` (committat, 19 MB);
  M1-motorkod (terräng-LOD 128 m-rutor 1/2/4/8/16 m med kjolar, ortofoto + v1:s procedurella
  markdetaljer nära, Sky + sol med följande skuggkamera + PMREM-IBL, FPS-styrning mus/touch)
- [x] 2026-10-21 — **M0 klart, M1 byggd**: `npm install` (three 0.180, vite 6.4.4), lockfile committad,
  `npm run build` grönt, smoke-testat i preview (442 rutor, 0,77 M tri, inga konsolfel), pushat

- [x] 2026-10-21 — **Förberett för v2 i molnet**: `v2/` scaffold (Vite/TS/Three.js, `PLAN.md`),
  deploy-workflow bygger v2 under `/v2/` med v1 kvar på roten, `.claude/cloud-setup.sh`,
  LiDAR-griden committad som 16-bit PNG (`tools/lidar_1m.png`, 1 cm-kvantiserad, 4,9 MB) och
  `tools/osm_raw.json` committad så pipelinen går utan Lantmäteriet; git-tagg `v1` på sista
  rena v1-committen

- [x] 2026-09-10 — **Broar & gångytor v2** (mätdrivet: probe som går 1 m-steg längs alla vägar och
  brodäck via debughookarna `__game.groundInfoAt/bridgeChains/roadSegs`): vägar kopplas till SIN
  bro via OSM-way-id (`tools/build_flats.py` skriver `ids` per kedja, `build_data2.py` `id` per väg)
  i stället för närhet + riktningsfilter — viadukten stal höjd åt gångbron intill; knutpunkter
  mellan broar (ramp ↔ rondell uppe på Mölndals bro) är inga landfästen → mark + 6 m; spann som
  ansluter på en bredare parallell bro snappar till dess nivå; lutningsspärr 10 %; gångytan är nu
  exakt den ritade banan (tvärsnitts-max med tak 1,2 m — förr sjönk fötterna upp till 2,8 m i
  asfalten) och `groundInfoAt` tar närmaste segment per väg (grannsegment på lutande gator gav
  1–1,5 m-hopp). Resultat: 4 716 → 842 höjdhopp >45 cm på 203 000 provsteg. Däcken är
  sammanhängande band med gering (inte överlappande lådor), räcken = kolliderbara/hoppbara
  `guard_rail`-murar på fria kanter. flats/broar regenererade för hela nya kartan (173 → 365 ytor,
  44 → 65 brokedjor)
- [x] 2026-09-10 — **Broar v2.1 (Joels speltest: "sticker upp i ingenting")**: v2.0:s knutregel lade
  +6 m på varje ändpunkt som delade nod med en annan brokedja → 30 kedjor lyfta, små gångbroar
  över ån svävade och en trappa vid (−168,−199) blev ett 26 m-torn. Nu: bara viadukter (korsar
  annan väg) deltar, knutar tar grannens faktiska däckhöjd, rondellen seedas, branta (>25 %)
  kedjor släpps → 12 lyfta ändar, alla i trafikplatsen Mölndals bro. Verifierat från luften och
  vägbanan; `window.__THREE` exponerad för raycast-felsökning
- [x] 2026-09-10 — **Zoombara kartor**: minikartan 60–420 m radie (scrollhjul, +/−, tryck på kartan
  på mobil; sparas i localStorage) med skalstock; taktiska kartan (M) zoomar 1–4,5× centrerad på
  spelaren med scroll/+/−
- [x] 2026-09-10 — **Husfakta-lagret**: `public/husfakta.js` beskriver hur enskilda hus SER UT som
  data (farg, vaningar, hojd, tak, takfarg, material, skylt; nyckel `w<OSM-id>` eller adress);
  OSM-taggarna (151 hus med våningar, 60 med kulör, 26 med takform, 7 material) läses automatiskt
  ur data.js och husfakta.js vinner; tegel som tredje fasadmaterial; skyltar på fasaden mot
  närmaste gata (Corpus Pizzeria, Kråkans Krog, Mölndals stadsmuseum, Kulturhuset Möllan m.fl.);
  `tools/husfakta_lista.py` → `husfakta_kandidater.md` med 93 hus + Street View-länkar att titta på

- [x] 2026-08-08 — **Riktiga broar + vägar som aldrig försvinner**: OSM `bridge=yes` (59 ways)
  kedjas till spann med plana däck landfäste→landfäste — Mölndals bro finns nu på riktigt
  (går att gå både PÅ och UNDER, riktningsfilter så gatan under viadukten inte kastas upp);
  vägar förtätas till 3,5 m-segment + tvärsnitts-max så terräng aldrig sticker genom asfalten
  (Götaforsliden hel hela vägen); `groundInfoAt(refY)` skiljer på/under däck

- [x] 2026-08-08 — **Flyktmanöver för fastklämda soldater**: fastna-detektorn triggar nu
  en probad flykt (sidled/bakåt, `insideAnyBuilding`-test, eskalerande tid vid upprepning)
  i stället för bara waypoint-hopp — fiender och allierade tar sig ur hushörn och räknar
  om vägen från den fria positionen; syntettest med 1,3 m-gap mellan hus verifierat

- [x] 2026-08-06 — **Markgrafik-overhaul**: byggda plana ytor (147 parkeringar, 7 planer,
  16 lekplatser, 3 torgytor ur OSM → `flats.js`) plattas med minsta-kvadrat-plan + mjuk
  kant (gropighet 10 cm → 2,5 cm per cell); riktiga ytmeshar med P-rutelinjer, grus och
  smågatsten; markmaterial v2 (512px-texturer: gräs med vårblommor, asfalt, skogsbotten,
  granit+lav) som ÄGER närfältet med fotot som ljusmakro (35 % färg), bakat terrängljus,
  branthets-berg och makrobrus mot tiling; vägar med asfalttextur; kvällsläget dämpar
  detaljfältet (uNight); tuvor/stenar cullas från byggda ytor; full fart på hårdgjort

- [x] 2026-07-09 — **Mobilanpassning**: touchkontroller (virtuell spak med analog fart,
  full utstyrning = sprint; sikt-drag på fri skärmyta; ELD/HOPP/⟳/HUKA/KARTA-knappar),
  viewport-meta, kompakt HUD på små skärmar (hälsa/ammo flyttar till mitten), fullskärm +
  landskapslås vid start, porträtt-hint, DPR-tak 1,5 på mobil, `#touch`/`#desktop` i
  URL:en tvingar läget (test/felsökning)

- [x] 2026-07-09 — **Markklassningskartan**: pipeline (`tools/build_classmap.py`) klassar varje
  2 m-cell som asfalt/gräs/skog/berg ur ortofotots färg+textur, LiDAR-lutning/lokala toppar
  och OSM (skog, 170 parkeringar, berg, husnärhet) → `classmap.png`. Styr splat-shadern
  (+ ny granitdetalj med mossfläckar), färglägger fotot per klass även på håll (vårgrå skog
  blir grön), 15 000 träd (tät skog, buskar på hällar), tuvor undviker berg. Parkeringen
  vid spawn = asfalt, smygstigen österut går genom tät skog.

- [x] 2026-07-08 (sent): alla tak gångbara — sadeltak har riktig lutande takyta (nock→takfot),
  step-up 0,6 m; raket med håll-för-kraft (tap ~3 m, full ~12 m), snällare fallskada;
  8192px-marktextur ur 0,16 m-cachen + detaljbrus i markshadern; håll-C för crouch

- [x] 2026-07-08 (kväll, sprint från speltest): minimap-pil rättvänd + tydligare prickar;
  Roten M snappad till gatan; croucha på C; gå på platta tak (med fallskada över kanten);
  fler fiender (30 ockupanter, vågor 10+3n, konstant tryck, tak 55); skog från OSM-polygoner
  + pixelkluster — blockerar sikt efter 14 m, långsam off-road, stigar fria (obs: LM-fotot
  är vårtaget/gråblått → pixelklassning sekundär, OSM natural=wood är facit).
  Joel ska peka ut hemliga stigar i skogen senare.

- [x] 2026-07-07 — Spel v1: kartdata, terräng, FPS-kärna, vågor, capture points
- [x] 2026-07-07 — Satellitmark + riktiga takfärger + landmärken + 1,5× branthet
- [x] 2026-07-07 — Vita trä/puts-fasader, sadeltak, murar/stödmurar, branthetsspärr
- [x] 2026-07-07 — Forsen nedsänkt (ström, skada, broar, räcken), vägrenar/mittlinjer,
  vägfart, gatlyktor, parkerade bilar, forsbrus, fallskada
- [x] 2026-07-07 — Aggressiv AI (eld under framryckning, närmaste-mål, fastna-detektor),
  mobila medhjälpare med förstärkningar, start mitt i invasionen, fastna-fix
- [x] 2026-07-07 — GitHub + Pages-deploy: https://kytioisacat.github.io/kvarnbyn-fps/
- [x] 2026-07-08 (natt) — Ockupationsläge: 18 fiender håller kartan från start (fri zon
  170 m kring basen), förstärkningar från tre håll, strafe i närstrid, större vågor
- [x] 2026-07-08 (natt) — Riktiga soldatmodeller: väst/ryggsäck/hjälm, tvåhandsfattat
  vapen, benanimation, mynningseld, siktar i höjdled mot målet
- [x] 2026-07-08 (natt) — Kvällsläge (checkbox på startskärmen): stjärnhimmel, månljus,
  tända lyktor med glöd + ljusgölar, varmlysta fönster
- [x] 2026-07-08 (natt) — Träd från ortofotots pixlar: riktiga positioner + kronfärger,
  ~2 400 st, stamkollision
- [x] 2026-07-08 (natt) — Taktisk fullskärmskarta på M: ortofoto, frontläge, alla styrkor
- [x] 2026-07-08 — **Lantmäteriet-bytet klart** (båda beställningarna godkända):
  ortofoto 0,16 m (2024, molnfritt, CC BY 4.0) ersätter Esri → licensrent att publicera;
  terräng från 1 m-LiDAR i 2 m-grid — riktiga murar/branter (Royens trappor brantast, 0,61!),
  EXAG 1,5→1,2, branthetsspärr omkalibrerad (block 0,60 / tungt 0,38), åfåre-nedskärningen
  reducerad (LiDAR:n har den riktiga ravinen), attribution uppdaterad

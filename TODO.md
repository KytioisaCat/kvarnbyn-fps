# TODO — Försvara Kvarnbyn

Idébacklogg. En punkt i taget, ~30 min styck. Bocka av med `[x]` och flytta till
Klart-sektionen med datum. Claude: läs denna fil vid sessionstart (se CLAUDE.md).

## Backlogg (~30 min styck)

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

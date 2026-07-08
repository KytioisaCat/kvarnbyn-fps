# TODO — Försvara Kvarnbyn

Idébacklogg. En punkt i taget, ~30 min styck. Bocka av med `[x]` och flytta till
Klart-sektionen med datum. Claude: läs denna fil vid sessionstart (se CLAUDE.md).

## Pågående sprint (Joels feedback 2026-07-08, en commit per färdig punkt)

- [ ] **Minimap-fixar** — vänd spelarpilen rätt (pekar 180° fel), större/tydligare
  fiendeprickar, något större synradie (gäller även pilen på taktiska kartan)
- [ ] **Flytta Roten M (B)** — punkten står halvt i ett hus; snappa till närmsta
  gatunod så ringen ligger på gatan
- [ ] **Croucha på C** — toggle: lägre ögonhöjd, halverad fart, svårare att träffa,
  bryter fiendens siktlinje bakom sandsäckar/murar
- [ ] **Gå på tak** — platta tak blir gångbara: hoppa ner från höjder, landa och
  spring längs taket (sadeltak förblir solida)
- [ ] **Fler fiender** — ockupationen ~30 man, större och tätare vågor, nästa våg
  triggar redan vid ≤6 kvar eller på timer (konstant tryck), tak på ~55 samtidiga
- [ ] **Skog där ortofotot visar skog** — tätareträdplantering i skogspartierna,
  skogen blockerar siktlinjer/kulor efter ~14 m djup, långsammare att röra sig i
  (stigarna genom = fria korridorer). Joel pekar ut hemliga stigar senare

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

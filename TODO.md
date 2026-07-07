# TODO — Försvara Kvarnbyn

Idébacklogg. En punkt i taget, ~30 min styck. Bocka av med `[x]` och flytta till
Klart-sektionen med datum. Claude: läs denna fil vid sessionstart (se CLAUDE.md).

## Blockerat (väntar på externt)

- [ ] **Byt satellitbild till Lantmäteriet** — beställning av "Ortofoto Nedladdning"
  ligger hos Lantmäteriet för beslut (lagd 2026-07-07, sommarkö väntas).
  När Joel fått nedladdningsrätt: kör `tools/fetch_ortho_lm.py` (kräver LM_USER/LM_PASS
  i miljön — aldrig i chat/repo), sen `build_data2.py`, kopiera till `public/`,
  uppdatera attributionsrad till "© Lantmäteriet, CC BY 4.0" (index.html + README),
  bumpa `?v=`, committa. Tills dess ligger Esri-bilden kvar på sajten (medvetet beslut,
  formellt villkorsbrott med låg risk — ska bort så fort LM-datan är inne).
- [ ] **LiDAR-terräng 1 m** — beställning av "Markhöjdmodell" ligger också för
  handläggning. När filerna kommer: lägg i `tools/lidar/`, bygg om terrängen,
  ta bort 1,5×-överdriften (EXAG i game.js), omkalibrera branthetsspärr + stödmurar.

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

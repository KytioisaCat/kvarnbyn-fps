# v2 — ny grafikmotor: plan och spelregler för sessioner

**Mål**: samma spel, samma by, men det ska *se verkligt ut*. Kraven står i `../KRAVSPEC.md`
(teknikoberoende, utgå alltid från den). Dagens spel i `../public/` är **facit för känsla,
balans och beteenden** — läs `../public/game.js` som referens, ändra det aldrig.
Kalibreringar och dyrt inlärda fällor står i `../ARKITEKTUR.md` och gäller oavsett motor.

## Teknikval (beslutade 2026-10-21)

- **Webben, inte UE5/Godot.** Joel spelar från en länk i telefonen; utvecklingen sker i
  Claude Code cloud-sessioner (ingen GPU i VM:en, ingen nedladdning till Joels laptop).
- **Three.js + TypeScript + Vite.** `WebGPURenderer` när projektet är moget, med automatisk
  WebGL2-fallback — Joels telefon är målhårdvaran och måste alltid fungera. Börja i
  WebGL2 (`WebGLRenderer`), byt renderare först när grundscenen står.
- **Deploy**: push till `main` → `.github/workflows/deploy.yml` bygger `v2/` och lägger den
  under `/v2/`; v1 ligger kvar på roten. Spelbart på
  <https://kytioisacat.github.io/kvarnbyn-fps/v2/>.
- **Data**: nytt pipelinesteg `tools/build_v2.py` (att skriva) exporterar motorvänliga filer
  till `v2/public/data/`: binär höjdkarta (ur `tools/lidar_1m.png`, 1 m), klasskarta som
  textur, hus som glTF/binära buffertar med OSM-id + husfakta, vägar/murar/broar/flats.
  Källorna finns i git (`tools/lidar_1m.png`, `tools/osm_raw.json`, `tools/ortho8k.jpg`,
  `tools/classmap.png`, `public/husfakta.js`) — Lantmäteriet-konto behövs inte.
- **Tillgångar**: bara CC0/CC BY (Poly Haven, ambientCG, egna). Aldrig kommersiella
  gatubilder eller kartor in i produkten. Attribution visas i spelet.

## Vad "ser verkligt ut" betyder (prioritetsordning)

1. **Ljus**: fysikaliskt baserat (PBR), HDRI/procedurell himmel med IBL, solkaskadskuggor,
   AgX/ACES-tonemapping, GTAO, bloom, dimma i åravinen. Dag- och kvällsläge (kvällen med
   riktiga ljuskällor vid gatlyktor och lysta fönster).
2. **Terräng**: splat-map ur klasskartan (asfalt/gräs/berg/skog) med riktiga texturer nära,
   ortofotot som färgton på håll. Byggda plana ytor plana med linjer och kantsten.
   Höjdöverdrift 1,2× behålls (igenkänning av backarna).
3. **Hus**: procedurella fasader per byggnad från husfakta + OSM-taggar — fönster, dörrar,
   takpannor, puts/trä/tegel med riktiga material. Hjältehusen (Corpus, Kråkan, museet)
   extra omsorg. Tak beträdbara.
4. **Vegetation**: instansierade trädmodeller med LOD och vind; skog som blockerar sikt.
5. **Gatubild**: gatlyktor, bilar, vägmarkeringar, räcken, stödmurar.
6. Först därefter: soldatmodeller med animation, vapen, ljud.

Mobil först: KTX2-texturer, Draco/meshopt, LOD, budget ~60 fps på Joels telefon.

## Arbetssätt i molnet

- **Committa och pusha till `main` vid varje delmål** (VM:en kan återvinnas; Joel har godkänt
  push till main). Varje push deployar — skriv inte sönder bygget; `npm run build` ska gå
  igenom innan push.
- **Smoke-test i VM:en**: `npm run build` + headless Chromium (Playwright, mjukvaru-WebGL)
  laddar `dist/` utan konsolfel och tar en screenshot. Det visuella omdömet är Joels, på
  telefonen — be om feedback i stället för att gissa.
- **Debughookar** som i v1: `window.__frame(dt)`, `window.__v2` (scene/camera/renderer),
  senare `__look/__fire/__game`. Starta via klick på `#overlay`.
- Ett delmål per session. Uppdatera `../TODO.md` (avsnittet v2) och denna fil när beslut
  fattas. Rör aldrig `../public/` (v1 är fryst som referens).

## Delmål (i ordning)

- [ ] **M0 Skalet**: `npm install`, lockfile committad, bygget deployar till `/v2/`, Joel ser
      den roterande lådan på telefonen med renderarnamn i statusraden.
- [ ] **M1 Terrängen**: `tools/build_v2.py` → höjdkarta + klasskarta; terrängmesh med LOD,
      PBR-splat, ortofoto på håll, FPS-kamera med WASD/touch, sol + himmel + tonemapping.
      Joel-test: "känns Götaforsliden lika brant?"
- [ ] **M2 Husen**: fotavtryck → väggar/tak, fasadgenerator från husfakta, skuggor.
      Joel-test: hjältehusen igenkännbara.
- [ ] **M3 Gatubild & vegetation**: vägar med markeringar, flats, broar (v1:s brokedjor),
      murar, lyktor, bilar, träd.
- [ ] **M4 Kväll**: kvällsläge med ljuskällor och stjärnhimmel.
- [ ] **M5 Spelet**: fysik/rörelse enligt KRAVSPEC (port av v1:s kalibreringar), zoner, AI,
      vapen, HUD — tills v2 vinner Joel-testet. Då flyttas v1 till `/legacy/`.

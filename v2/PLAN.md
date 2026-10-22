# v2 — ny grafikmotor: plan och spelregler för sessioner

**Mål**: samma spel, samma by, men det ska *se verkligt ut* — "så likt Call of Duty som möjligt i
en webbläsare". Vad det betyder och vägen dit: **`VISION.md`** (läs den före delmålen). Kraven står i `../KRAVSPEC.md`
(teknikoberoende, utgå alltid från den). Dagens spel i `../public/` är **facit för känsla,
balans och beteenden** — läs `../public/game.js` som referens, ändra det aldrig.
Kalibreringar och dyrt inlärda fällor står i `../ARKITEKTUR.md` och gäller oavsett motor.

## Teknikval (beslutade 2026-10-21)

- **Webben, inte UE5/Godot.** Joel spelar från en länk i telefonen utan nedladdningar;
  telefonen är test-GPU:n. Utvecklingen sker lokalt på Joels laptop (molnsessioner provades
  2026-10-21 men Consats Claude-org saknar GitHub-connectorn — föreslå dem inte igen).
- **Three.js + TypeScript + Vite.** `WebGPURenderer` när projektet är moget, med automatisk
  WebGL2-fallback — Joels telefon är målhårdvaran och måste alltid fungera. Börja i
  WebGL2 (`WebGLRenderer`), byt renderare först när grundscenen står.
- **Deploy**: push till `main` → `.github/workflows/deploy.yml` bygger `v2/` och lägger den
  under `/v2/`; v1 ligger kvar på roten. Spelbart på
  <https://kytioisacat.github.io/kvarnbyn-fps/v2/>.
- **Data**: pipelinesteget `tools/build_v2.py` exporterar motorvänliga filer till
  `v2/public/data/` (committade, så bygget går utan Python): höjdkarta 1 m ur
  `tools/lidar_1m.png` som 8-bit RGB-PNG (R=hög byte, G=låg byte, 1 cm-steg — canvas-
  avkodbar, ingen alfa), klasskarta, ortofoto i 4k+8k, `meta.json` med bbox/projektion;
  senare (M2–M3) hus med OSM-id + husfakta, vägar/murar/broar/flats.
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

## Arbetssätt (lokalt)

- **Committa och pusha till `main` vid varje delmål** (Joel har godkänt push till main).
  Varje push deployar — skriv inte sönder bygget; `npm run build` ska gå igenom innan push.
- **Mätt uppkoppling**: fråga Joel innan `npm install`, nya paket eller nedladdade tillgångar,
  och säg ungefärlig storlek. Håll beroendelistan kort.
- **Smoke-test i preview** (`.claude/launch.json` → `v2`, Vite på port 5187): ladda sidan utan
  konsolfel, stega med `window.__frame(dt)`, ta screenshot. Det visuella omdömet är Joels, på
  telefonen via <https://kytioisacat.github.io/kvarnbyn-fps/v2/> — be om feedback i stället
  för att gissa.
- **Debughookar** som i v1: `window.__frame(dt)`, `window.__v2` (scene/camera/renderer),
  senare `__look/__fire/__game`. Starta via klick på `#overlay`.
- Ett delmål per pass. Uppdatera `../TODO.md` (avsnittet v2) och denna fil när beslut
  fattas. Rör aldrig `../public/` (v1 är fryst som referens).

## Delmål (i ordning) — omgjorda 2026-10-21 enligt VISION.md §3

- [x] **M0 Skalet** (2026-10-21): bygge, deploy under `/v2/`, lockfile.
- [x] **M1a Terräng + bevis på metoden** (2026-10-21): LiDAR-terräng med LOD; offline-modellen
      `tools/v2model/` bygger vägnätet som geometri (profil-lösare, kantsten, broar, konformering,
      mätgrindar). Bevis: `docs/bevis-torget-2026-10-21/`.
- [ ] **M1b Flats**: torg/parkeringar/planer som plan + kantsten + konformering (OSM-polygoner
      + plandetektion i LiDAR); samma grindar. Joel-test: "är p-platsen vid torget platt?"
- [ ] **M1c Hela kartan**: gles lösare (scipy) eller områdesvis; spelaren går på däck/trappor;
      stödmurar där rapporten pekar; tunnelportaler.
- [ ] **M2 Husen**: fotavtryck → väggar, riktiga tak, fasadgrid ur husfakta, sockel mot konformerad mark.
- [ ] **M3 Material & gatubild**: PBR-texturer (CC0) med normalkartor på de konstruerade ytorna,
      vägmarkeringar, lyktor, bilar, staket, häckar, träd.
- [ ] **M4 Ljus**: WebGPU-efterbehandling (TAA, GTAO, bloom, dimma), kväll med riktiga lampor.
- [ ] **M5 Spelet**: fysik/rörelse enligt KRAVSPEC (port av v1:s kalibreringar), zoner, AI,
      vapen, HUD — tills v2 vinner Joel-testet. Då flyttas v1 till `/legacy/`.

### Offline-modellen (`tools/v2model/`)

    cd tools && venv/bin/python -m v2model.build --area torget   # ~1 min, exit 1 om grind bryts
    venv/bin/python build_v2.py --no-ortho                        # höjdkarta ur lidar_conformed.npy
    cd ../v2 && npm run build

Beroenden i `tools/venv`: numpy, pillow, shapely, mapbox_earcut (`triangle` bygger inte på
Python 3.14 — band + earcut i stället). Områden definieras i `v2model/common.py` (`AREAS`).
Utdata: `v2/public/data/roads.{json,bin}`, `tools/lidar_conformed.npy` (gitignorerad; återskapas),
rapport i `tools/v2model/out/`. Lösaren är tät numpy: ~7 000 okända på 7 s per varv, 10–20 varv.

Moduler (`src/`): `world.ts` (meta + höjdfält, `heightAt` = rå × 1,2 som v1), `terrain.ts`
(128 m-rutor, LOD 1/2/4/8/16 m efter avstånd 150/380/850/1600 m, kjolar mot sprickor, normaler
ur 1 m-fältet, CCW uppifrån; material = MeshStandard + `onBeforeCompile`-detalj ur klasskartan),
`ground.ts` (v1:s canvasgenererade detaljtexturer asfalt/gräs/skog/berg + makrobrus, porterade
rakt av — blandningsformeln i shadern är också v1:s: klasstonat foto på håll, detalj × fotoljus
nära 30–110 m, branta ytor → berg), `sky.ts` (three/addons `Sky`, sol 34° från SV, en skugg-
kamera 220 m som följer spelaren — CSM senare), `controls.ts` (pointer lock + touch: vänster
halva gå, höger titta), `roads.ts` (laddar v2model-meshar per material), `main.ts`.
Debughookar: `__frame(dt)`, `__look(yaw,pitch)`, `__tp(x,z)` (gå), `__fly(x,y,z)` (fri kamera), `__v2`.
Debughookar: `__frame(dt)`, `__look(yaw,pitch)`, `__tp(x,z)`, `__v2.{world,terrain,player,…}`.
- [ ] **M2 Husen**: fotavtryck → väggar/tak, fasadgenerator från husfakta, skuggor.
      Joel-test: hjältehusen igenkännbara.
- [ ] **M3 Gatubild & vegetation**: vägar med markeringar, flats, broar (v1:s brokedjor),
      murar, lyktor, bilar, träd.
- [ ] **M4 Kväll**: kvällsläge med ljuskällor och stjärnhimmel.
- [ ] **M5 Spelet**: fysik/rörelse enligt KRAVSPEC (port av v1:s kalibreringar), zoner, AI,
      vapen, HUD — tills v2 vinner Joel-testet. Då flyttas v1 till `/legacy/`.

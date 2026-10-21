# Vad "ser verkligt ut" betyder — och hur vi tar oss dit (2026-10-21)

Joels krav, med hans ord: *så likt Call of Duty som möjligt i en webbläsare, utan att det blir för
stort eller tungt.* Inte 8k → 16k. Detta dokument är svaret på "har du förstått, och har du en idé?".

## 1. Vad CoD-looken faktiskt består av

Ingenting i en CoD-bana är "hög upplösning" i sig. Looken kommer av fem saker, i den här ordningen:

| # | Vad | Hur CoD gör det | Vad vi har i dag |
|---|-----|-----------------|------------------|
| 1 | **Innehåll som är fotograferat, inte ritat** | Fotogrammetri: 200-kamera-riggar skannar riktiga föremål och miljöer (Modern Warfare 2019) | Kartdata + ortofoto + procedurella fasader. Ingenting är fotograferat på plats |
| 2 | **Material som svarar på ljus** | PBR med normal-/roughness-kartor på allt; våt asfalt speglar, grus bryter ljuset | Ortofoto som färg + canvasritade "texturer" utan normalkartor |
| 3 | **Ljus som är förberäknat** | Bakad global illumination (voxlar/lightmaps) + dynamisk sol, AO, reflektioner, volymetrisk dimma | Sol + himmel-IBL + en skuggkamera. Ingen GI, ingen AO, inga reflektioner |
| 4 | **Efterbehandling** | TAA, bloom, färggradering, linsdefekter, rörelseoskärpa | ACES-tonemapping, inget annat |
| 5 | **Täthet** | Skräp, dekaler, smuts, gräs, buskar, kablar, skyltar — varje kvadratmeter har något | Tom mark |

Källor: Activisions egna [Modern Warfare-genomgång](https://blog.activision.com/call-of-duty/2019-06/Initial-Intel-Call-of-Duty-Modern-Warfares-game-engine-is-put-through-its-paces),
[GamesBeat om fotogrammetrin](https://gamesbeat.com/call-of-duty-modern-warfares-photogrammetry-captures-gritty-realism-like-never-before/),
[Activision Research: Large-Scale GI](https://research.activision.com/publications/2021/09/large-scale-global-illumination-in-call-of-duty).

**Slutsats 1**: punkt 1 är den som avgör. Procedurella fasader ur OSM når aldrig dit — Unigine och
Esri CityEngine har gjort det i 15 år och resultatet är alltid "stad i ett simulatorspel", aldrig
"Kvarnbyn". Punkt 2–5 är teknik som finns i webbläsaren i dag (se §2) och som jag kan bygga.

## 2. Vad webbläsaren klarar 2026

- **WebGPU finns överallt**, inklusive iPhone (Safari 26, sept 2025). Three.js faller tillbaka till WebGL2
  automatiskt. ([migreringsguide 2026](https://www.utsubo.com/blog/webgpu-threejs-migration-guide))
- **Three.js WebGPU har AAA-efterbehandlingen**: GTAO, screen-space-reflektioner (`webgpu_postprocessing_ssr`),
  TAA, bloom — community-renderaren Shade visar hela kedjan i 42 fps i 5K på en M2.
  ([Shade](https://discourse.threejs.org/t/shade-webgpu-graphics/66969), [SSGI-demo](https://ssgi-webgpu-demo.vercel.app/))
- **Unity 6.6 och Babylon 9** kör WebGPU i produktion med GPU-driven rendering, volymetriskt ljus,
  klustrade ljus. ([Unity 6.6](https://app.cinevva.com/news/2026-09-01-unity-6-6-webgpu-production),
  [Babylon 9](https://blogs.windows.com/blog/2026/03/26/announcing-babylon-js-9-0/))
- **Gaussian splats = fotorealistiska riktiga platser i webbläsaren.** Spark 2.0 (MIT, Three.js) strömmar
  100M+ splats med LoD och klarar 4M splats i 60 fps på iPhone 14+. Ett rikt utomhusmotiv är ~25 MB som SPZ.
  ([Spark](https://sparkjs.dev/docs/overview/), [Swyvl-jämförelse](https://swyvl.io/blog/best-gaussian-splat-viewers/),
  [SPZ-formatet](https://scaniverse.com/news/spz-gaussian-splat-open-source-file-format))
- **Någon har redan gjort en spelbar FPS på en skannad plats**: kollisioner, bakat ljus, navmesh och AI
  ovanpå en splat-scen i PlayCanvas. ([Tom's Hardware](https://tomshardware.com/software/programming/developer-creates-a-basic-first-person-shooter-game-using-gaussian-splats-and-you-can-play-it-for-free-in-your-browser))
- **Fångst kräver ingen rigg längre**: Brush (öppen källkod, kör på Mac utan CUDA) eller Scaniverse/Polycam
  tränar splats ur mobilvideo. ([PlayCanvas verktygslista](https://developer.playcanvas.com/user-manual/gaussian-splatting/creating/recommended-tools))

**Slutsats 2**: tekniken för CoD-looken finns i webbläsaren. Det som saknas i vårt projekt är
*innehållet* — och det enda sättet att få Kvarnbyns innehåll utan en art-avdelning är att fotografera
Kvarnbyn.

## 3. Två vägar, och varför det blir en hybrid

| | **A. Fånga Kvarnbyn (splats)** | **B. Procedurellt AAA-lite** |
|---|---|---|
| Hur | Joel filmar kvarteren med telefonen (plus drönare för tak). Brush/Scaniverse → SPZ. Spark strömmar splats ovanpå vår LiDAR-terräng (kollisioner) och OSM-fotavtryck (väggar) | CC0 PBR-texturer med normalkartor, modulära fasadkit, skannade CC0-rekvisita (Poly Haven), instansierad vegetation, GTAO/SSR/TAA/bloom |
| Igenkänning | **Maximal** — det är bokstavligen Kvarnbyn | Generisk: "ett svenskt villaområde" |
| Tak | Fotoreal | Battlefield 3-nivå om allt går vägen, med månaders art-arbete |
| Kostnad för Joel | ~1 dag filmning för kärnkvarteren, 25–50 MB per kvarter strömmat | Ingen filmning, men oändligt med texturjobb |
| Svagheter | Ljuset är inlåst vid fångsttillfället (kväll = färggradering, inte riktiga lampor). Spelaren kastar ingen skugga på splats. Folk/bilar/registreringsskyltar som råkar komma med måste undvikas eller maskas | Ser aldrig ut som Kvarnbyn på nära håll |
| Vad som är dynamiskt | Soldater, vapen, effekter, fordon är meshar med PBR och ljus matchat mot fångsten | Allt |

**Hybrid** (rekommendation):
- **Splats för miljön där spelaren går** — Gamla torget, Kvarnbygatan, Götaforsliden, Royens trappor,
  hjältehusen. Det är där "Joel-testet" avgörs.
- **Procedurell terräng + B-tekniken** utanför de fångade zonerna (kullarna, skogen, E6-sidan) och som
  fallback medan fångsten pågår. Allt jag redan byggt (LiDAR-terräng, LOD, klasskarta) blir fysik- och
  bakgrundslager — inget är bortkastat.
- **En gemensam ljus-/efterbehandlingskedja** (WebGPU: TAA, GTAO på mesharna, bloom, färggradering,
  dimma i åravinen) som binder ihop splat och mesh så sömmen inte syns.
- **Mobilbudget**: ~1M splats synliga åt gången (Spark LoD), 4k-foto, halv upplösning på efterbehandling.
  Mål 30 fps stabilt på Joels telefon, 60 på dator.

## 4. Bevis före löfte: en veckas prov

Innan vi bestämmer oss gör vi ett prov på **ett kvarter** (förslag: Gamla torget med Kråkan):

1. Joel filmar kvarteret med telefonen (4K, långsam gång, två varv på olika höjd, 5–10 min,
   undvik folk och bilar). Jag skriver en filmguide på en sida.
2. Jag tränar splats i Brush lokalt (eller Joel i Scaniverse direkt i telefonen), exporterar SPZ.
3. Jag lägger in Spark i v2, positionerar splatten mot LiDAR + ortofoto (vi har exakta koordinater),
   kollisioner från terrängen och fotavtrycken, soldater som meshar i samma scen.
4. Joel går runt kvarteret på telefonen. Mått: fps, MB, och frågan *"är det här Kvarnbyn?"*

Faller provet (fps, storlek, utseende) går vi väg B fullt ut och vet varför. Lyckas det har vi en
pipeline: film → splat → spelbart kvarter, och kan ta ett kvarter i taget.

## 5. Vad som INTE ändras

Spelmekaniken (KRAVSPEC.md), v1 som facit för känsla och kalibreringar, CC0/CC BY-regeln för
nedladdade tillgångar (splats av Kvarnbyn är Joels egna), svenska i all speltext, mätt uppkoppling
(fråga före nedladdning), telefonen som test-GPU.

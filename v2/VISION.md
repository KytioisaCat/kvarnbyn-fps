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

## 3. Joels korrigering (2026-10-21, kväll): vi kommer inte ha fotograferat innehåll

Splat-demos (Grace Cathedral, Sumygins FPS) visar rätt *nivå*, men de bygger på högupplösta
fångster som vi inte kommer att ha, inte i närheten. Våra förutsättningar är LiDAR 1 m (markmodell),
OSM-polygoner, ortofoto 0,16–0,4 m och husfakta. **Vägen är därför att konstruera en digital
representation: geometri.** Inte drapera ett foto över ett brusigt höjdfält, utan bygga banan som en
level designer skulle — rena ytor, raka kanter, riktiga material — men genererat ur datan.

### Principen: varje byggd yta är ett objekt, inte terräng

| Objekt | Datakälla | Vad som konstrueras | Mått (före/efter) |
|---|---|---|---|
| **Parkeringar, torg, planer, skolgårdar** | OSM-polygoner + **plandetektion i LiDAR** (RANSAC inom asfaltklass — fångar gårdar/uppfarter OSM saknar) | Minsta-kvadrat-plan med lutningsgräns (p-plats ≤ 3 %), egen mesh med kantsten 12 cm, terrängen skärs ner/blendas i ett band utanför | max avvikelse från planet inom polygonen → 0; inga 10–30 cm-bulor |
| **Vägar** | OSM-centrumlinjer + klass | Tvärsnitt (körbana, kantsten, trottoar), längsprofil filtrerad längs vägen med max-lutning, korsningar lösta, terrängen konformerad till vägkanten (ingen "grön jord i gatan"), markeringar, brunnar, lyktor | steg längs centrumlinjen (v1:s probe), tvärfall |
| **Trappor, stödmurar, murar** | OSM barrier/steps + LiDAR-steg | Riktiga trappsteg och murkrön som geometri, terrängen bruten vid muren | Royens trappor: stegantal/steghöjd rimliga |
| **Hus** | Fotavtryck + våningar + roof:shape + husfakta | Väggar, riktiga tak (sadel/valm ur fotavtryckets form när OSM saknar), sockel, fönster-/dörrgrid per fasad ur husfakta, takfot, stuprör | hjältehusen igenkännbara |
| **Mark som inte är byggd** | LiDAR + klasskarta | Terräng (det som finns i dag), gräs/berg/skogsbotten som rena PBR-material; ortofotot bara som färgvariation på håll | — |
| **Vegetation, gatubild** | klasskarta, OSM, husfakta | instansierade träd/buskar, staket, häckar, bilar på p-platser, skyltar | — |

Det tekniska hjärtat är **terrängkonformering**: höjdfältet är inte längre sanningen, det är ett
startvärde. Vägar, flats, murar och hus är *villkor*; höjdfältet räknas om så att det möter dem
exakt (kantsten mot gata, gräs mot mur), med mjuk övergång utanför. v1 gjorde en enklare variant
(flats plattades med mjuk kant); v2 gör det för allt byggt, i 1 m, och mäter.

### Varför det ger looken trots dåliga data

CoD-banor är också "bara" geometri + tiled-material + ljus. Fotogrammetrin i §1 ger *materialen*,
inte strukturen. Det som gör att en spelbana ser verklig ut på nära håll är: plana ytor är plana,
kanter är skarpa, material har normalkartor, och det finns täthet (kantsten, markeringar, brunnar,
lyktor, bilar). Allt det kan konstrueras. Det som INTE går att få ur datan är enskilda husens
riktiga fasader — där är husfakta + Joels ögon enda källan, hus för hus, och hjältehusen tas först.

### Ordning (ersätter M1–M3 i PLAN.md)

1. **Flats + plandetektion + konformering** — p-platsen vid torget ska vara plan med kantsten. Mått före/efter.
2. **Vägar som meshar** med tvärsnitt och konformering; markeringar.
3. **Hus med riktiga tak och fasadgrid** ur husfakta; murar och trappor som geometri.
4. **Material**: riktiga PBR-set med normalkartor (CC0, engångsnedladdning) på de konstruerade ytorna.
5. **Ljus/efterbehandling** (WebGPU: TAA, GTAO, bloom, dimma) — binder ihop allt.
6. **Täthet**: lyktor, bilar, staket, häckar, träd.

Splat-spåret läggs på is. Om Joel någon gång filmar ett kvarter kan det läggas in som ett lager,
men planen får inte vila på det.

## 4. Vad som INTE ändras

Spelmekaniken (KRAVSPEC.md), v1 som facit för känsla och kalibreringar, CC0/CC BY-regeln för
nedladdade tillgångar, svenska i all speltext, mätt uppkoppling (fråga före nedladdning), telefonen
som test-GPU, mätdriven geometrifix (probe före/efter — ARKITEKTUR.md).

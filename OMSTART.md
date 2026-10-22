# Omstart 2026-10-22 — tillbaka till ritbordet

Joels dom efter fyra försök (v1, v2-terräng, v2-vägnät, v2-flats): *"det ser fruktansvärt ut, vi
byter approach helt; använd datan för att dra slutsatser, bygg sedan världen med andra metoder,
verktyg och ramverk; kopiera gärna någon annans."* Det här dokumentet är svaret: en ärlig diagnos,
vad andra gör, och en ny plan. Inget i det bygger vidare på hur v1/v2 ritar världen.

## 1. Diagnos: varför det blev dåligt fyra gånger

Det var inte otur och inte dålig data. Det var samma grundfel varje gång:

1. **Vi ritar data, inte en värld.** Varje version har ritat råmaterialet direkt: höjdgriden med
   flygfotot på, OSM-linjer som band, fotavtryck som lådor. Så gör inget spel som ser bra ut.
   I ett spel är datan *ritningen*; utseendet kommer från *tillgångar* — modeller, material,
   ljus — som någon har byggt och som placeras enligt ritningen. Vi har haft noll tillgångar.
2. **Vi har handskrivit motorn.** Terräng-LOD, vägmeshar, broar, konformering, skuggor,
   kantstenar: allt är problem som Unity, Unreal och Blender-tillägg löste för tio år sedan.
   Två dagar gick åt till att bygga en sämre EasyRoads3D. Ett "skelett som är rätt" är ändå ett
   skelett.
3. **Vi använder bara en bråkdel av datan.** LiDAR:n vi använder är *markmodellen*: hus och träd
   är bortrensade. Vi vet alltså inget om takhöjder, takformer eller var träden står — trots att
   Lantmäteriets punktmoln innehåller allt det, öppet (CC0), 1–2 punkter/m².
4. **Kraven "telefon, länk, inga nedladdningar" drev oss mot "generera allt i webbläsaren"** —
   motsatsen till hur snygga spel görs (förbyggt innehåll, bakat ljus, strömmat).

Slutsats: inte mer av samma. Byt *kategori* av lösning.

## 2. Hur andra gör (research 2026-10-22)

**Riktiga platser ur öppen data, med resultat som folk tycker ser bra ut:**

- **OSM → Blender (Blosm) → Buildify-kit → Unreal/Unity.** Blosm importerar OSM-fotavtryck och
  terräng, Buildify (gratis, Geometry Nodes) bygger hus ur *modulära fasadkit*: väggmoduler per
  våning, fönster, dörrar, tak. Författaren själv säger att det låga proxy-kitet ska bytas mot
  riktiga tillgångar (Megascans) — det är kitet som avgör utseendet, inte generatorn.
  ([Buildify](https://www.cgchannel.com/2022/07/download-free-blender-3d-building-generator-buildify/),
  [Blosm](https://github.com/vvoovv/blosm), [SideFX: City building with OSM](https://www.sidefx.com/tutorials/city-building-with-osm-data/))
- **CityBLD (Unreal 5)** gör gator med korsningar, trottoarer, kantsten och modulära hus ur
  OSM-import; en Manhattan-rekreation visades som demo. Men realdata-importen är "under aktiv
  utveckling", OSM-städning krävs, och det är Unreal = ingen webbläsare.
  ([CityBLD realdata](https://worldbld.notion.site/Real-World-Data-Basics-e00da3966fcf4bcda6749931c8b85dc2),
  [Manhattan-demo](https://hitmarker.net/news/a-recreation-of-manhattan-in-unreal-engine-made-using-new-world-building-tool-citybld-521222))
- **Vägverktyg** som gör det jag handskrev: EasyRoads3D (Unity) deformerar terrängen till vägen,
  gör korsningar, kantsten, markeringar; UE5 landscape splines. Mogna, beprövade.
  ([EasyRoads3D-recension](https://previewlabs.com/roadpath-tool-vs-easyroads3d/))
- **Vad som ser dåligt ut och varför:** Hop.earth (OSM + LiDAR-racing i webbläsaren) får kritiken
  *"världen känns gles och tom, städerna består av identiska hus placerade ungefär där de riktiga
  står"* — exakt vår sjukdom: data utan tillgångar.
  ([t3n om Hop.earth](https://t3n.de/news/racing-game-browser-gesamte-welt-1758359/))
- **Vad som ser bra ut och varför:** rekreationer av riktiga gränder i UE5 byggs med Megascans-
  material, modellerade hus från foton och ljus matchat mot platsen — en fiktiv Hongkong-gränd tog
  fyra dagar för en van artist. Looken kommer från material + ljus + täthet, inte från data.
  ([80.lv Hongkong-gränd](https://80.lv/articles/realistic-hong-kong-alley-made-with-megascans-unreal-engine-5),
  [Polycount Hastings-gränd](https://polycount.com/discussion/comment/2759327/))

**Motorer och webben (2026):**

| Motor | Webb/telefon | Tak för realism | Verktyg vi får gratis |
|---|---|---|---|
| **Unity 6.6 (URP)** | Ja — WebGPU produktionsklar sedan 6.6 (sept 2026), WebGL2-fallback, mobilwebbläsare stöds | AAA-lite: bakat GI (lightmaps/APV), PBR, efterbehandling, ej Lumen | Terrain (LiDAR-höjdkarta in), EasyRoads3D, vegetation, lightmapper, Asset Store |
| **Unreal 5** | Nej (PC-nedladdning eller pixel streaming) | Högst: Lumen, Nanite, Megascans gratis i UE, PCG, CityBLD | Landscape, splines, PCG, Megascans |
| **Godot 4** | Bara Compatibility-renderaren (WebGL2, inget WebGPU) | Lågt för realism | — |
| **three.js (vårt)** | Ja | Beror helt på innehållet vi matar in; allt verktyg saknas | inget |

([Unity 6.6 WebGPU](https://app.cinevva.com/news/2026-09-01-unity-6-6-webgpu-production),
[Godot webbexport](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_web.html))

**Data vi inte använt:**

- **Lantmäteriets laserpunktmoln** ("Laserdata Nedladdning, skog"/NH): öppet CC0, 1–2 p/m², via
  STAC-API sedan 1 juni 2026, rutor 2,5 km. Punkterna är klassade mark/vatten/bro/oklassat —
  *oklassat = hus och träd*. Med fotavtryck ovanpå ger det takhöjd, takfot, takform (sadel/valm/
  platt), nockriktning per hus, och trädpositioner med höjd och kronstorlek.
  ([produktbeskrivning](https://www.lantmateriet.se/globalassets/geodata/geodataprodukter/hojddata/pb_laserdata_nedladdning_skog.pdf),
  [produktnyheter STAC](https://www.lantmateriet.se/sv/geodata/vara-produkter/Produktnyheter/))
- **Lantmäteriets Byggnad (vektor)**: fotavtryck med ändamål, avgift 0 kr, GeoPackage via STAC.
- **Kvarnbyns byggnadsbestånd** (riksintresse): arbetarbostäder i trä på bergssluttningarna från
  mitten av 1800-talet, äldre kvarngårdar, industribyggnader i tegel från 1800-talets senare
  hälft. Det är *få arketyper* — det gör en modulär kit-strategi realistisk.
  ([Trafikverkets kulturarvsanalys](https://bransch.trafikverket.se/contentassets/17dee024e88743f7a5d4e6ba086dbb49/kulturarvsanalys/kulturarvsanalys-kapitel-5-bebyggelse.pdf))

## 3. Den nya approachen: tolka → bygg → spela

### A. Tolka (Python, vår pipeline — det enda vi behåller)

Datan blir en **stadsbeskrivning** (JSON), alltså slutsatser, inte geometri:

- **Hus**: fotavtryck (Lantmäteriet + OSM), våningar, takfots- och nockhöjd, takform och
  nockriktning (ur punktmolnet inne i fotavtrycket), **arketyp** (trä-arbetarbostad 1800-tal,
  kvarngård, tegelindustri, flerbostadshus 1900-tal, villa, modern), fasadkulör (husfakta/orto),
  hjältelista (Corpus, Kråkan, museet …).
- **Gator**: centrumlinje, klass, bredd, trottoar/kantsten, trappor, stödmurar (LiDAR-språng).
- **Terräng**: LiDAR-markmodell som höjdkarta (den är bra).
- **Vegetation**: träd ur punktmolnet (position, höjd, kronradie, barr/löv), häckar, skogskanter.
- **Ytor**: torg, parkeringar, planer. **Vatten**: ån, forsen.

Detta är Joels idé: "här är ett hus, nu ska vi bygga *det* huset" — inte "här är en polygon".

### B. Bygg (riktiga verktyg, inget handskrivet)

- **Terräng** i motorns terrängsystem ur höjdkartan, auto-material efter lutning/höjd med riktiga
  PBR-set (gräs, berg, skogsbotten, grus).
- **Gator** med ett beprövat vägverktyg (korsningar, kantsten, markeringar, terrängen anpassas).
- **Hus** ur **arketyp-kit**: för varje arketyp ett modulärt kit (väggmodul per våning, fönster,
  dörr, sockel, takfot, takmoduler, skorsten) med riktiga material. Ett skript sätter ihop varje
  hus ur beskrivningen: fotavtryck → våningar × moduler, tak enligt punktmolnet. Hjältehusen
  görs färdiga för hand mot Joels foton/Street View.
- **Vegetation**: riktiga trädmodeller instansierade där punktmolnet säger, gräs, häckar.
- **Ljus**: motorns bakade GI + sol i realtid + efterbehandling (det CoD gör).
- **Gatubild**: lyktor, bilar, staket, skyltar, sopkärl — täthet.

### C. Spela

Spelmekaniken enligt KRAVSPEC, portad till motorn (v1 förblir facit för känsla/kalibrering).

## 4. Valet som avgör allt: var ska det spelas?

| | **Unity 6 → webbläsare (telefon via länk)** | **Unreal 5 → PC** |
|---|---|---|
| Joels krav "länk på telefonen" | Uppfylls (första laddning 50–150 MB, sedan cachat) | Nej: nedladdning, PC |
| Visuellt tak | AAA-lite: bakat ljus, PBR, bra material — "ser ut som ett spel" | CoD-nivå möjlig: Lumen, Nanite, Megascans |
| Verktyg för vår pipeline | Terrain, EasyRoads3D (köp), vegetation, lightmapper | Landscape, splines/CityBLD (köp), PCG, Megascans gratis |
| Risk | WebGPU på telefoner varierar; byggstorlek | Allt tungt: 40 GB motor, GB av tillgångar; Joels nät |
| Min rekommendation | **Ja, om telefonen är ett krav** | Ja, om PC är OK och målet är maxkvalitet |

Båda kräver nedladdningar som vårt mätta nät måste planera för: Unity Hub+Editor ~5 GB,
Unreal ~40 GB, Blender ~0,3 GB, tillgångspaket 0,5–5 GB.

## 5. Första beviset — och vad som INTE ska visas igen

Inga fler "skelett" eller "det är bättre än förra gången". Nästa sak Joel får se är **en enda
bild som ser ut som ett spel**: ett hjältehus vid Gamla torget ur ett arketyp-kit med riktiga
material, gatan framför med kantsten och markeringar, ett par träd från punktmolnet, bakat ljus.
Ser den inte bra ut visas den inte, då fortsätter jobbet.

Steg till dit:
1. Beslut: Unity/webb eller Unreal/PC (§4). Nedladdningar planeras till bra nät.
2. Ladda punktmolnsrutan för Kvarnbyn (CC0, ~100 MB) och Lantmäteriets byggnadsvektor; skriv
   tolkningen (takform, träd) — mätbar: takhöjd per hus mot ortofotots skuggor/Street View.
3. Ett arketyp-kit (trä-arbetarbostad) + ett hjältehus för hand, i Blender, med material.
4. Terräng + gata + hus + träd + bakat ljus i motorn, en bild.

## 6. Vad som behålls, vad som läggs ner

- **Behålls**: `tools/` som tolkningspipeline (bbox, OSM, LiDAR, orto, husfakta, klasskarta), v1
  som facit för spelkänsla och kalibreringar, KRAVSPEC.md, licensregeln (CC0/CC BY i produkten;
  köpta tillgångar efter deras licens), svenska.
- **Läggs ner**: v2:s renderare och `tools/v2model/` som *produkt*. Delar återanvänds som
  tolkning (vägnätsgraf, profil-lösaren som "hur lutar gatan", flats-planen, stödmurs-
  detektionen) — de är slutsatser ur datan, och det är det de ska vara.

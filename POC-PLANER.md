# Proof of concept-planer (2026-10-22)

Joels ram: *CoD från 2007–2012 räcker; det går i webbläsaren (GTA, CoD, Wii-spel körs ju där);
noll kronor; tokens bara de dagar som blir över i veckan; tajt scope; PoC:er som jag bygger och
Joel bedömer.* Det här dokumentet är planen för det. Läs `OMSTART.md` för diagnosen.

## 1. Hur GTA, CoD och Wii-spel körs i webbläsaren (research)

Det är **inte streaming**. Det är spelens motorer som körs lokalt i webbläsaren:

- **GTA III / Vice City**: de bakåtkonstruerade motorerna re3/reVC (C++) kompileras till
  WebAssembly med Emscripten, renderar via WebGL 2, och spelaren lägger in *sina egna* spelfiler
  (modeller, texturer, kartan) som lagras i webbläsarens OPFS. Ingen server.
  ([reVC-port](https://github.com/joncodeofficial/gta-vice-city-wasm), [förklaring](https://portedgames.com/gta-vice-city/))
- **Call of Duty**: Black Ops-zombies är en dekompilering av originalet, kompilerad till WASM
  med WGPU-rendering; CoD 2-klienten är motorn rekonstruerad mot WASM + WebGL 2 (två kartor,
  TDM funkar). Heise/Kotaku tillskriver dekompileringsvågen Claude Opus 5.5.
  ([cod2-wasm](https://github.com/tonga54/cod2-wasm), [Heise](https://www.heise.de/en/news/Halo-Vice-City-Black-Ops-AI-ports-of-games-run-in-the-browser-11485764.html))
- **Wii**: Dolphin-emulatorn kompilerad till WASM med en PowerPC→WASM-JIT och WebGPU-renderare —
  en teknisk demo, inte publik än. ([Dolphin WebGPU-demo](https://www.digitalcitizen.life/new-super-mario-bros-wii-runs-inside-google-chrome-in-early-dolphin-webgpu-demo/))
- **Doom 3 / Quake 3**: idTech4 (d3wasm) och ioquake3 (Q3JS) kompilerade med Emscripten, WebGL.
  ([d3wasm](https://github.com/gabrielcuvillier/d3wasm), [Q3JS](https://q3js.com/quake-3-webassembly))

**Slutsatsen som spelar roll för oss**: en motor från 2005–2012 med lightmaps, normalkartor och
måttliga polygonmängder kör utmärkt i webbläsaren, även på telefon. Det som gör att de spelen ser
bra ut är *tillgångarna* som proffs byggde — kartorna, husen, materialen, det bakade ljuset. Det
är exakt den del vi har saknat. Tekniken är löst; innehållet är jobbet.

## 2. Målbild: "CoD 4 – MW2-look" (2007–2011)

Det receptet är känt och billigt: statisk värld med **bakade lightmaps** (GI gratis i runtime),
**PBR-light** material med normalkartor, **modulära huskit**, hero-objekt, dekaler, instansierad
vegetation, dimma, enkel efterbehandling (bloom, färggradering). Inga realtids-GI, inget
raytracing. Det är precis vad WebGL 2/WebGPU klarar på en telefon om innehållet är byggt så.

## 3. Scope: Kvarnbyn, inte Mölndal

Dagens karta (3,2 × 2,2 km) är 5–10× för stor. Spelytan blir **kärnan av Kvarnbyn**, ungefär
Gamla torget – Kvarnbygatan – Götaforsliden – Royens trappor – Forsebron, uppskattningsvis
**500 × 400 m**, med kullarna runt om som kuliss (terräng utan detalj). PoC:erna görs på
**ett kvarter: Gamla torget, ~120 × 120 m**. Exakt ruta sätts när första PoC:n börjar.

## 4. Pipelinen vi testar (gemensam för alla PoC:er)

```
tolka (Python, tools/)  →  bygg innehåll (Blender)  →  sätt ihop & baka (motor)  →  exportera (webb / desktop)
```

- **Tolka**: stadsbeskrivning ur datan — fotavtryck, våningar, takhöjd/takform ur punktmolnet,
  arketyp per hus, gator med bredd/kantsten, träd, ytor, murar. (Delar av `tools/v2model/`
  återanvänds här som tolkning.)
- **Bygg innehåll (Blender, gratis)**: arketyp-kit (väggmoduler, fönster, dörrar, tak) med CC0-
  material från Poly Haven/ambientCG; skript sätter ihop varje hus ur beskrivningen; hjältehus
  justeras för hand mot Joels foton. Terräng ur LiDAR. Export glTF.
- **Sätt ihop & baka (motor)**: terräng, vägar med vägverktyg, hus, träd, ljus bakas till
  lightmaps, FPS-kontroller.
- **Exportera**: webb (och/eller desktop).

## 5. PoC-alternativen

| | **PoC G: Godot 4** | **PoC U: Unity 6 Personal** | **PoC T: Blender → three.js** | **PoC E: Unreal 5 (desktop)** |
|---|---|---|---|---|
| Kostnad | 0 kr, öppen källkod | 0 kr under 200 k$ (Personal) | 0 kr | 0 kr (Megascans gratis i UE) |
| Nedladdning | **~0,1 GB** motor + Blender 0,3 GB | ~5 GB Hub+Editor + Blender | Blender 0,3 GB | ~40 GB + tillgångar |
| Webb/telefon | Ja, WebGL 2 (Compatibility): lightmaps ja, glow ja, **ingen SSAO/SSR/volymdimma** | Ja, **WebGPU produktionsklar** (6.6) + WebGL 2, officiellt mobilstöd | Ja (det vi har) | Nej (bara inofficiella portar) |
| Desktop-version ur samma projekt | **Ja: Forward+ med SDFGI/SSAO/volymdimma** — två nivåer, ett projekt | Ja (URP/HDRP) | Nej | Ja, högsta nivån |
| Verktyg gratis | Terrain3D (heightmap-import), Blender-import, lightmapper | Terrain, lightmapper; bra vägverktyg kostar (EasyRoads3D) | Inga — allt i Blender | Landscape, PCG, Megascans |
| Passar mitt arbetssätt | **Bäst**: scener och skript är textfiler, allt går att generera och granska utan GUI | Sämre: scener kräver Editorn för import/bake, YAML-tunga | Bra, men spelkoden förblir handskriven | Sämst: tung, binär, GUI-driven |
| Visuellt tak på webb | CoD 4-nivå med bra innehåll | CoD 4–MW2-nivå, lite mer efterbehandling | Beror helt på innehållet | — |
| Risk | Webb-exporten är "here be dragons"; lightmaps måste bakas på desktop | Licens/konto, storlek, mindre insyn för mig | Vi fastnar i handskrivet igen | Nät, disk, tid; inte telefon |

**Rekommendation: börja med PoC G (Godot)**, eftersom den kostar noll, laddar ner minst, ger
*både* webb/telefon och en snyggare desktopversion ur samma projekt, och jag kan arbeta i den
utan att klicka i ett GUI (viktigt för tokens). Om Godots webbexport inte håller måttet byter vi
runtime till Unity (PoC U) — innehållet (Blender-kit, glTF, tolkningen) följer med oförändrat.
Innehållssteget i Blender är gemensamt och **det första vi gör oavsett motor**.

## 6. PoC-sekvens (varje PoC = ett autonomt pass, Joel bedömer efteråt)

1. **PoC 0 — Innehåll (Blender, ingen motor)**: ett arketyp-kit (trä-arbetarbostad 1800-tal,
   stående panel, spröjsade fönster, plåt- eller tegeltak) + ett hjältehus vid Gamla torget för
   hand + gatan framför med kantsten + 3 träd (CC0-modeller) + terräng ur LiDAR, Cycles-renderad
   bild med sol. **Bedöms: ser kvarteret ut som Kvarnbyn?** Ser det inte bra ut i Blender kommer
   det aldrig att göra det i en motor.
2. **PoC 1 — Godot webb**: samma kvarter in i Godot, Terrain3D, lightmaps bakade, FPS-kamera,
   webbexport → länk på telefonen. **Bedöms: samma look som i Blender? fps? laddtid?**
3. **PoC 2 — Godot desktop (Forward+)**: samma projekt, SDFGI/SSAO/dimma, macOS-bygge.
   **Bedöms: är desktop-nivån värd det?**
4. (Vid behov) **PoC U** Unity webb med samma innehåll.
5. **Tolkningen i full skala**: punktmoln → tak och träd för hela kärnan; kit för de 4–6
   arketyperna; hus sätts ihop per beskrivning; hjältehusen för hand.

## 7. Arbetssätt för att inte springa iväg i tokens

- **Allt pass börjar med en brief i repot** (`poc/<namn>/BRIEF.md`): scope, färdigdefinition,
  vad som får laddas ner, vad som INTE ingår. Passet slutar med `RESULTAT.md` + bilder + commit.
  Joel läser resultatet när han har tid, inte chatten.
- **Ett pass = ett PoC.** Inga "medan jag ändå är här". Upptäckter går in i backloggen.
- **Visa bara det som ser bra ut.** Håller bilden inte måttet mot målbilden (§2) visas den inte,
  i stället står det i RESULTAT.md vad som saknas.
- **Nedladdningar som checklista** (§8) som Joel godkänner i klump, helst på bra nät.
- **Chatten kort.** Beslut och motiv i docs. Opus 5.5 på passen; billigare modell för rutin.

## 8. Nedladdningar för PoC 0–2 (Joel godkänner)

| Vad | Storlek | Varför |
|---|---|---|
| Blender 4.x | ~300 MB | innehåll, kit, bake |
| Godot 4.x (editor) + webb-exportmallar | ~60 + ~70 MB | PoC 1–2 |
| Terrain3D (Godot-addon) | ~20 MB | terräng ur heightmap |
| CC0-material (Poly Haven/ambientCG), ~10 set à 2k | ~200 MB | panel, tegel, plåt, asfalt, gatsten, gräs, berg |
| CC0-trädmodeller (Poly Haven/Quaternius), 3–5 st | ~100 MB | träd |
| Lantmäteriets punktmolnsruta 2,5 km (CC0, STAC) | ~100 MB | takformer, träd (PoC 0 klarar sig utan) |
| **Summa** | **~0,9 GB** | |

Unity (~5 GB) och Unreal (~40 GB) bara om PoC G faller eller Joel vill ha desktop-max.

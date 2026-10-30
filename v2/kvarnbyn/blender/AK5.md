# Ak 5 — egen Blender-modell för förstapersonsvyn

`build_ak5.py` bygger en sammanhängande, förenklad spelmodell av den äldre gröna
Ak 5:an. Visuell förlaga är **Armémuseums AM.009994**, ett exemplar från 1986:
[DigitaltMuseum](https://digitaltmuseum.se/011024265451/556-mm-automatkarbin-5),
[museets fotografi speglat på Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Ak_5_early_production_example,_AM.009994,_04.jpg).
Fotografiet betraktades som formreferens; inga referenspixlar, logotyper eller
färdiga vapenmodeller har lagts i produkten. Geometri/material är handförfattade
i projektets Blender-skript, med konstnärligt förenklade proportioner.

## Bygg och importera

Från repots rot:

```sh
v2/.tools/Blender.app/Contents/MacOS/Blender -b --python v2/kvarnbyn/blender/build_ak5.py
v2/.tools/Godot.app/Contents/MacOS/Godot --audio-driver Dummy --headless --editor --path v2/kvarnbyn/godot --import --quit
```

`-- --render` efter Blender-kommandot ger också en separat studiorender.
På den här Macen behöver native Blender/Godot normal macOS-grafikåtkomst.

Genererad leverans: `godot/assets/weapons/ak5_view.glb`, **711 336 bytes**,
**15 052 trianglar** inklusive glovhänder och ärmar, elva små Principled-material,
inga bildtexturer. GLB/importcache är gitignorerade. Modellen måste byggas före
Godot-import på en ny klon och finnas som resurs i macOS-exporten:
`res://assets/weapons/ak5_view.glb`.

## Vad som byggs

- Fasade kanter, pressad grön låda, separat lock och synliga kosmetiska reglage.
- Avsmalnande polymerhandskydd med diagonala greppåsar och ventilationsdetaljer.
- Pipa, ihålig mynning, öppna bakre/främre järnsikten.
- Klassisk gles fällkolvssiluett, gummibakkappa, grepp och magasinbrunn.
- Måttligt böjt plåtmagasin med pressade ribbor, som kan flyttas vid omladdning.
- Egna rundade glovhänder och förenklade ärmar. De är inte riggade för en fullständig
  hand-för-hand-omladdning; magasinrörelsen är fortfarande stiliserad.

## Axel- och nodkontrakt

Godot: **−Z framåt, +Y upp**, meter. Den synliga vapensiluetten är cirka 1,05 m lång.
Förstapersonsvyn använder samma visuella skala, 0,55, som föregående Fas B-vapen.

| Nod | Innehåll / lokal position i Godot |
|---|---|
| `Ak5_Body` | Fast vapenkropp, kolv, handskydd, pipa och sikten |
| `Magazine` | Separat flyttbart magasin |
| `Charging_Handle` | Separat kosmetiskt handtag |
| `Firing_Hand` | Höger glovhand och ärm — ta bort för tredje person |
| `Support_Hand` | Vänster glovhand och ärm — ta bort för tredje person |
| `Muzzle` | `[0, 0.018, -0.623]` |
| `Sight_Rear` | `[0, 0.117, 0.142]` |
| `Sight_Front` | `[0, 0.117, -0.432]` |

Ungefärliga handmål för en tredjepersonsrigg: höger handflata
`[0.034,-0.095,0.137]`, stödhand `[-0.031,-0.042,-0.247]`. Värdena är visuella
riggningsmål, inte produktionsmått.

`weapon.gd` läser modellens ankare och låter mynningsflamman/spårljus börja i den
ritade mynningen. I stillastående ADS flyttas den gemensamma sikthöjden 0,117 m
ned till kamerans siktlinje. Träffstrålen utgår som tidigare från kameran; pipan
ligger därför lite under siktlinjen. Rörelse, rekyl och spridning är kvar.

Omladdningens längd och ljudhändelser är kvar: 1,7 s, eller 2,2 s från tomt.
Vapnets kosmetiska omladdningspose har höjts och vridits så att modellen och
magasinrörelsen syns i bild; den tidigare posen gömde nästan hela det nya vapnet.
Magasin och handtag återställs vid färdig omladdning och `refill()`.

## Verifiering

```sh
v2/.tools/Godot.app/Contents/MacOS/Godot --audio-driver Dummy --headless --path v2/kvarnbyn/godot --script res://scripts/verify_weapon.gd
v2/.tools/Godot.app/Contents/MacOS/Godot --audio-driver Dummy --path v2/kvarnbyn/godot --script res://scripts/verify_weapon.gd -- --screenshots
v2/.tools/Godot.app/Contents/MacOS/Godot --audio-driver Dummy --path v2/kvarnbyn/godot --script res://scripts/capture_weapon_world.gd
```

`evidence/weapon/weapon_qa.json` innehåller kontroller av import/ankare, automateld
med ammunition, sikte, mynningsplacering, vanliga/tomma omladdningstider och
återställning av komponenter. Nativebilderna visar höftläge, ADS och omladdning;
`ak5_world_*` tas dessutom i den riktiga världen med dess ljus och HUD.

Första godkända teknikprovet: **0,0 px siktfel** för både bakre och främre siktet
vid stillastående ADS, och återfyllning på 1,7167/2,2167 s i 60 Hz-provet
(inom ett simuleringsteg från avsedda tider). Nativeprovet kördes i Godot 4.7.2,
Forward+/Metal, Apple M5. Ingen ändring av skada, spridning eller skottfunktion.

Alla automatiska Godot-prov ska vara ljudlösa: kör alltid `--audio-driver Dummy`.
Båda vapenprovskripten tystar dessutom masterbussen först i `_initialize()`.
Detta påverkar inte ljudet när Joel startar den vanliga spelappen.

Senaste verkliga världskontrollen gav **0,154 px** största siktavvikelse
(flyttalsavrundning långt från världsorigo), med rätt mynningspunkt. Fångsten
låter NPC:ernas fysik landa och fryser sedan världen för samma vy mellan poserna;
bildernas FPS-text är därför inte ett prestandatest.

- [Höftläge](../evidence/weapon/ak5_world_hip.jpg)
- [Siktläge](../evidence/weapon/ak5_world_ads.jpg)
- [Omladdning](../evidence/weapon/ak5_world_reload.jpg)
- [Separat modellvy](../evidence/weapon/ak5_model.jpg)

Fullstora PNG-fångster och GLB finns lokalt men är gitignorerade. De små
JPEG-kopiorna och QA-rapporterna kan versionshanteras.

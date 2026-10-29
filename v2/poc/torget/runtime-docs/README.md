# Godot-provet vid Gamla torget

Det här är visnings- och gånglagret för den färdiga Blender-miljön. Godot 4.7.2 Standard,
Compatibility/WebGL 2, GDScript. Ingen egen renderare eller fysikmotor. Det är ett miljöprov,
inte en port av soldater, vapen och zoner.

## Innehållskontrakt

- `godot/assets/world.glb`: modeller och material, Y upp, lokala meter.
- `godot/assets/world_meta.json`: titel, startpunkt, vyer och attribution (schema nedan).
- Förenklade kollisionsmeshar börjar med `COL_`; de döljs och används endast av Godots fysik.
  Finns inga sådana meshar används synliga meshar med undantag för vatten, löv och små dekorobjekt.
- Material med namnet `WaterFlow` får diskreta rörliga ytnormaler i runtime. Det ersätter inte
  geometri för forsstråk, kantkontakt eller skum. Vattenytan är opak för stabil sortering på webben.
- Blenders kameror och ljus används som referens. Godots kamera samt `lighting.gd` äger spelvyn.

```json
{
  "title": "Gamla torget",
  "spawn": {
    "position": [0, 0, 14],
    "yaw_degrees": 0,
    "pitch_degrees": 0,
    "snap_to_ground": true
  },
  "views": [
    {
      "id": "torget",
      "name": "Torget",
      "position": [0, 2, 14],
      "target": [0, 2, 0],
      "eye_position": true
    }
  ],
  "bounds": {"min": [-60, -20, -60], "max": [60, 40, 60]},
  "attribution": ["Kartdata © OpenStreetMap-bidragsgivare. Höjddata: Lantmäteriet."]
}
```

`spawn.position` är fotposition. `views[].position` är ögonposition om inte
`eye_position=false` anges. `target` har företräde över yaw/pitch. Startpunkten kan snäppas
mot riktig kollisionsyta med en lodrät stråle. `bounds` är underlag för provets avgränsning,
inte en automatisk osynlig vägg i den nuvarande kontrollern.

## Kontroller

- Dator: WASD/piltangenter, mus, mellanslag för hopp, Shift för snabbare gång. Esc pausar.
  R återställer startpunkten, F11 växlar helskärm, H döljer gränssnittet för jämförelsebilder.
- Telefon: vänster tumme går med analog spak, höger tumme tittar, Hoppa är en separat knapp.
  Pekfingrar spåras separat och släppta fingrar nollställer rörelsen.
- Kameran är 1,65 m över fötterna. Kapseln kliver över vanliga kantstenar upp till 23 cm.
- Vyerna i menyn håller kameran still tills man börjar utforska därifrån.

## Lokal körning och export

Från repots rot, med den lokala binären `v2/.tools/Godot.app/Contents/MacOS/Godot`:

```sh
v2/.tools/Godot.app/Contents/MacOS/Godot --headless --path v2/poc/torget/godot --editor --import --quit
v2/.tools/Godot.app/Contents/MacOS/Godot --path v2/poc/torget/godot
mkdir -p v2/poc/torget/web
v2/.tools/Godot.app/Contents/MacOS/Godot --headless --path v2/poc/torget/godot --export-release Webb ../web/index.html
```

Webbexporten använder projektets svenska HTML-skal och single-threaded-mallen. Den behöver
inga särskilda isoleringsheaders, men ska serveras via HTTP/HTTPS och inte öppnas som lokal fil.
Godots webbutmatning måste behålla sina filnamn tillsammans. Den lokala exportmallen är en
utvecklingsinstallation och ska inte läggas i Git.

## Bakning av ljus

Förbered först modellimporten efter den första importen:

```sh
v2/.tools/Godot.app/Contents/MacOS/Godot --headless --path v2/poc/torget/godot --script res://scripts/configure_import.gd
v2/.tools/Godot.app/Contents/MacOS/Godot --headless --path v2/poc/torget/godot --editor --import --quit
v2/.tools/Godot.app/Contents/MacOS/Godot --headless --path v2/poc/torget/godot --script res://scripts/prepare_bake.gd
```

Importen genererar unika UV2-koordinater med 0,5 m texelstorlek och 2× täthet på Kråkan,
Corpus och Musikskolan (effektivt 0,25 m). Vegetation får dynamisk GI och utesluts från
ljuskartorna; osynliga kollisionsmeshar och trädmeshar får inga extra ljuskarts-UV på import.
`prepare_bake.gd` sparar
`assets/baked_world.tscn` med modellen, dagsljus, sol, ljuskartor och en förhandskamera.
Kör sedan en **grafisk** editor med en GPU-renderare som stöder lightmappern:

```sh
v2/.tools/Godot.app/Contents/MacOS/Godot --path v2/poc/torget/godot --editor --rendering-method forward_plus --rendering-driver vulkan -- --bake-kvarnbyn
```

Den uttryckliga flaggan aktiverar en lokal editorhjälpare som väljer `BakatLjus` och trycker
på editorns egen **Bake Lightmaps**-knapp. Den gör ingen bakning vid vanliga import- eller
editorstarter. Resultatet skrivs till `assets/bake_report.json`; framgång kräver faktisk ljusdata
med användare och en sparad scen. Om editorns knapp ändras eller ett fel kräver dialog kan man
öppna `assets/baked_world.tscn`, välja `BakatLjus` och baka manuellt.

Runtime kan läsa den förberedda scenen även innan bakningen lyckats, men rapporterar då
`baked_lightmaps=false`. Enbart filens existens räknas inte som lyckad ljusbake.

Systemprovet lyckades på M5 med Vulkan/MoltenVK: 252 modeller på 2 min 10 s med de första,
tätare inställningarna. Metal-renderaren fastnade i `timeout waiting for fence`; använd
Vulkan för bakning på denna dator. Runtime fortsätter använda Compatibility/OpenGL.

## Prov och jämförelsebilder

Verifierad fysik: samma riktiga spelarkontroller gick över 20 cm kantsten, stannade vid en
vägg, höll 1,65 m ögonhöjd och slutade röra sig vid paus. Kommandot returnerade 0.

```sh
v2/.tools/Godot.app/Contents/MacOS/Godot --headless --path v2/poc/torget/godot --script res://scripts/verify_controller.gd
```

En vanlig grafisk körning kan spara en bild från exakt vald kamera och sedan avsluta:

```sh
v2/.tools/Godot.app/Contents/MacOS/Godot --path v2/poc/torget/godot -- --view=torget --hide-ui --capture=/tmp/torget-godot.png --frames=45
```

`--probe` släpper spelaren vid vald startpunkt, stegar 90 fysikrutor och kräver att spelaren
landar på en riktig kollisionsyta. Headless-körning räcker för fysik; bilder kräver grafik.

Webbläsaren exponerar `window.__kvarnbyn.state` och `window.__kvarnbyn.command(JSON.stringify(...))`.
Kommandon: `begin`, `pause`, `reset`, `view` med `index`, `quality` med `index`, `ui` med
`visible`, `teleport` med `position`, `yaw`, `pitch`, `free_flight`, `hold`, samt `look` med
`target`. Bryggans yaw/pitch är radianer. Metadatafilens vinklar är grader. Tillståndet innehåller
modell-/triangelantal, kollisionsantal, laddtid, aktuell spelarposition, renderade trianglar,
draw calls och aktuell bildfrekvens. Lägg `?touch=1` på URL:en för prov av pekgränssnitt på dator.
Renderingtiderna är millisekunder. GPU-tid 0 betyder att drivrutinen inte levererat en mätning,
inte att GPU-arbetet är gratis. För verktyg som läser en isolerad DOM finns samma snapshot som
JSON i `#kvarnbyn-debug-state`, utan synlig teknisk text i spelet.

## Primärkällor

- [Godots webbexport](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_web.html):
  WebGL 2/Compatibility, single-threaded-export och mobilbegränsningar.
- [LightmapGI](https://docs.godotengine.org/en/stable/classes/class_lightmapgi.html):
  statiska ljuskartor, GPU-stöd för bakning och avgränsning till editorn.
- [Modellimportens inställningar](https://docs.godotengine.org/en/stable/classes/class_resourceimporterscene.html):
  Static Lightmaps, UV2 och texelstorlek.

Godot kan visa om miljön fungerar tekniskt. Joels igenkänning och det visuella omdömet behöver
bedömas separat på den verkliga telefonen.

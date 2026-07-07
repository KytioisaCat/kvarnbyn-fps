# Försvara Kvarnbyn

Ett FPS byggt på riktig kartdata över Kvarnbyn i Mölndal. Du spawnar högst upp på
Görjelycksgatan och försvarar kvarteren mot en invasionsstyrka som kommer nedifrån
Forsebron och trycker uppåt genom de branta gatorna.

## Spela

```bash
python3 -m http.server 8763 --directory public
```

Öppna <http://localhost:8763> i webbläsaren och klicka för att börja.

- **WASD** springa · **Shift** sprinta · **Space** hoppa
- **Vänsterklick** skjut · **R** ladda om
- Huvudskott ger direktdöd

## Gameplay

Tre capture points på riktiga platser, i stigande ordning upp mot din bas:

| Punkt | Plats | Höjd |
|-------|----------------|------|
| A | Gamla Torget | 33 m |
| B | Roten M | 35 m |
| C | Royens trappor | 44 m |

Fienden erövrar punkterna nerifrån och upp — faller **C** är slaget förlorat.
Stå själv i en förlorad zon (utan fiender i närheten) för att ta tillbaka den och
flytta frontlinjen nedåt igen. Blåa AI-försvarare hjälper till vid varje punkt och
återuppstår mellan vågorna. Överlev alla **8 vågor** för att vinna.

## Kartdatan

Allt i världen är riktigt:

- **Byggnader, gator, vatten och grönområden** från OpenStreetMap (Overpass API),
  ~1 660 byggnader och ~1 340 vägsegment kring Kvarnbyn (bbox 57.6495–57.6625 N, 12.008–12.044 E)
- **Satellitfoto** (Esri World Imagery, z18 ≈ 0,3 m/px) draperat över terrängen och som minimap.
  Varje byggnads **takfärg samplas ur fotot** (median över fotavtrycket), så husen har sina
  verkliga färger; fasaderna får fönster och färgsätts utifrån taket
- **Terräng** i ~5 m-grid från AWS Terrain Tiles (terrarium), med **1,5× vertikal förstärkning**
  så att de branta gatorna känns som de gör i benen — 3 m vid ån till 91 m (137 m i spelet) på bergen
- **Sadeltak** genereras på småhusen, platta tak på större byggnader; nästan-rektangulära
  fotavtryck snappas till rena rektanglar (minsta omslutande rektangel)
- **Fasader**: vita/benvita med stående träpanel på småhus och slät puts på större hus
  (procedurella texturer) — enligt hur Kvarnbyn faktiskt ser ut
- **Murar och naturliga spärrar**: OSM-barriärer (murar, staket, häckar) plus **procedurellt
  genererade stödmurar** där terrängen reser sig brant intill gatukanterna. Sluttningar
  brantare än ~0,35 går inte att klättra (0,25–0,35 = tung klättring) — man rör sig
  naturligt längs gator och trappor. Murar blockerar även kulor och siktlinjer
- **Forsen på riktigt**: Mölndalsåns fåra är nedskuren ~3 m i terrängen med strömmande,
  skummande vatten. Man kan ramla i — strömmen drar en nedströms, vitvattnet gör skada,
  och man kravlar upp vid kanten. Vägarna ligger kvar som **broar** över fåran (Forsebron!),
  med räcken där gatan går längs stupet. Forsens brus hörs och stiger när man närmar sig
- **Fallskada** vid höga fall (t.ex. från broräcket ner i fåran)
- **Vägkänsla**: ljusa vägrenar och streckade mittlinjer gör gatorna tydliga, och man
  springer ~20 % fortare på väg än i terräng (och bara 35 % i vatten)
- **Gatlyktor och parkerade bilar** längs gatorna — bilarna fungerar som cover och
  blockerar kulor, lyktstolparna har kollision
- **Landmärken**: svävande skyltar på Kvarnbytornet, stadsmuseet, Fässbergs kyrka,
  gatorna kring Kvarnbyn samt stadsdelarna (Glasberget, Kikås, Störtfjället, Forsåker, centrum)
- Fiendernas AI navigerar med A* längs det riktiga gatunätet (trappor och gångvägar inräknade)

### Bygga om datan

```bash
cd tools
python3 -m venv venv && ./venv/bin/pip install pillow numpy
# 1. OSM-data
curl -s -X POST "https://overpass-api.de/api/interpreter" \
  --data-urlencode "data@overpass_query.txt" -o osm_raw.json
# 2. Höjd-tiles (terrarium z15) → terrarium_full.npy
./venv/bin/python fetch_tiles.py
# 3. Satellit-tiles (Esri z18) → ortho_full.png + public/ortho.jpg
./venv/bin/python fetch_ortho.py && cp ortho.jpg ../public/
# 4. Generera public/data.js (terräng + hus med takfärger + landmärken)
./venv/bin/python build_data2.py && cp data.js ../public/
```

## Teknik

- Three.js (vendorerad i `public/three.module.js`), ingen byggkedja — bara statiska filer
- Terräng (125 k verts), husväggar, tak, vägar och sandsäckar är sammanslagna geometrier
  (en draw call per lager); fasadtexturen är procedurell (canvas)
- Terrängen renderas oskuggad (MeshBasic) eftersom flygfotot redan har verklighetens ljus inbakat
- Skott och siktlinjer använder en analytisk ray-march mot husens polygoner i stället för
  triangel-raycast, så det klarar full våg på 60 fps
- Kartdata © OpenStreetMap-bidragsgivarna (ODbL) · Flygbild © Esri, Maxar, Earthstar Geographics ·
  Höjddata © Copernicus EU-DEM (via AWS Terrain Tiles)

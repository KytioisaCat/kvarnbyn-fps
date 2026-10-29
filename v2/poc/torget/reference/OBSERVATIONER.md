# Platsunderlag — Gamla torget, granskat 2026-10-29

Underlag till första Blender/Godot-provet, inte en uppmätning. Målet är rätt gaturum och siluetter.
Alla siffror för vägg-/takhöjd är uppskattningar om inte annat uttryckligen anges.

## Rutan och koordinaterna

- Centrum: **57.65690 N, 12.02780 E**. Lokalt `(x,z)=(0,0)` här.
- Rutan: **120×120 m**, x/z från −60 till +60. X österut, Z söderut, Y upp.
- Äldre spelkoordinat i centrum: `(107.208, −100.188)`.
- Höjder: **ingen höjdöverdrift (1,0)**. Lokal Y = rå DTM-höjd −18,0 m.
- Rå markhöjd i centrum: 18,057 m ö.h. DTM:n beskriver mark, inte hustak eller trädtoppar.
- `data/terrain.json`: 121×121 cellvärden, 1 m steg. Rader går norr→söder.
- `data/city_spec.json`: 12 byggnader, 29 klippta väglinjer, 3 markytor och åns centrumlinje.
- Husfotavtryck behålls hela även där de skär rutans kant, så kulisshus inte kapas på mitten.

## Faktisk visuell inspektion i Google Maps

Google Street View öppnades och granskades manuellt via webbläsaren **2026-10-29**.
Bilddatum på de granskade panoramorna: **maj 2026**. Ingen inloggning krävdes.
Inga Street View-pixlar, skärmbilder, texturer eller skördade modelldata ingår i produkten.
Länkarna är återbesöksbara referenser, och observationerna nedan är manuellt författade.

### Kråkans Krog — Götaforsliden 1, OSM w92331981

[Vy från Forsebron mot huvudfasaden](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=57.65652,12.02796&heading=10&pitch=5&fov=85).
[Vy nära entrén/mellandelen](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=57.656641,12.028225).

- Vit **liggande** träpanel, tydligt väderpåverkad; mörkgröna dörrar och foder, vita spröjs.
- Västra huvudvolymen: två hela våningar och lågt **valmat mörkt plåttak**.
- Den breda sneda fronten har **3 övre tvåluftsfönster**, med sex rutor per fönster.
- Bottenfronten har **4 axlar**: dörr, fönster, glasad dörr, fönster. I maj 2026 finns blå
  markiser över de tre sista; den vänstra dörren saknar markis. Text: KRÅKANS KROG.
- Den följande knäckta fasaden mot öster har 2 övre fönster och 2 nedre fönster med blå markiser.
- Lägre mellandel med frontespis över en dörr; den har en rundad blå entrémarkis.
- Östra delen: sadeltak, två små frontespiser/dörrpartier mot gatan. Inte samma takhöjd som huvudvolymen.
- Låg grå sockel, vit hängränna/stuprör, enkla vägglampor, grön postlåda och bänk vid fronten.
- Gatan ligger mycket nära huset. En smal småstensremsa/trottoar med låg granitkant följer fasaden.

Den centrala OSM-polygonen omfattar alltså **tre takvolymer**, inte ett enda enhetligt 49 m-hus.
Handtolkade polygoner i `volumes` och fasadrytm i `street_facades` anger hur provmodellen ska delas.
Volymgränser är uppskattade genom OSM-fasadbrytningar + foto/ortofoto, inte mätta taklinjer.

### Gamla stadshuset / Musikskolan — Gamla torget43, OSM w92332122

[Vy från torget mot Musikskolan](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=57.65688,12.02745&heading=300&pitch=10&fov=90).

- Det höga långsmala huset **väster om Corpus**, med det lägre tegelhuset i sydväst.
- Ljus gräddvit liggande panel, rödbruna vertikala fönsterfoder och våningsband, rött sadeltak.
- **8 fönsteraxlar** längs torgets långfasad. Höjden delas i låg butikssockel, bostadsvåning,
  hög sal och små högt sittande fönster. De två övre fönsternivåerna kopplas med höga dekorativa foder.
- Bottenvåningens verksamheter har förändrats: frisör/restaurang i maj 2026.
  Den äldre MUSIKSKOLAN-skylten syns tydligt i 2013-fotot och kan användas i ett uttalat äldre miljöprov.
- Tak- och fönsterrytmen är viktigare för igenkänning än en stor skylt på ett schablonhus.

### Corpus Pizzeria — Gamla torget45B, OSM w92332103

Samma torgpanorama, vridet mot norr/öster, granskades visuellt.

- **Två våningar, ljus gräddvit PUTS**, enkelt vita foder, mörkt valmat tak.
- Övre fönster små och nästan kvadratiska; större öppningar/entré i bottenvåningen.
- **Svart skylt med vit text CORPUS PIZZA**, lång fasadskylt samt skylt på hörnet.
- Huset är **inte gamla stadshuset**. Matchningen i äldre husfakta till w92332103 är rimlig.
- Mörka takprofilen kan vara plåt med pannprofil; exakt taktäckning är fortfarande osäker.

### Gamla brandstationen — Gamla torget41, OSM w92332096

- Lägre rött tegelhus i anslutning till Musikskolans sydvästgavel.
- Ljusa tegel-/stenomfattningar kring fönster och dörrar, mörkrött tegeltak.
- Byggnadsordningen41/43/45 bekräftas av Mölndals stadsmuseums bildmetadata.

### Gaturummet och siktlinjerna

- Torget är småskaligt och svagt lutande; **grå/brun smågatsten**, granitkanter och planteringsöar.
- Framför Musikskolan: tre unga gatuträd, långa bänkar, låga ljusa betongpollare,
  cykelställ och smala svarta ljusstolpar. Gatan förbi torget har asfalt och markerad cykelbana.
- Forsebron har betongkant och tydliga räcken. Från dess södra landfäste syns Kråkans sneda front,
  medan Musikskolans höga ljusa/rödbruna fasad syns bakom till vänster.
- Forsen är en **trång, byggd ränna med murade/höga bankar** direkt norr om Kråkan.
  Den ska inte bli en bred naturlig bäck i en grässluttning.
- Blicken uppför Götaforsliden behöver en tegelindustri som fond, men det är kuliss utanför första 120 m-rutan.
- Dagens ortofoto 2024 innehåller byggarbetsplats på andra sidan ån. Provets färdiga gaturum får därför
  utformas mot de visuellt granskade 2026-vyerna, med en tydligt noterad blandning av källår.

## Ytterligare fotoreferenser (endast observation)

- [Götaforsliden1, foto01](https://commons.wikimedia.org/wiki/File:G%C3%B6taforsliden_1_i_M%C3%B6lndal_01.JPG),
  Historiker, 2013-04-05, CC BY-SA 3.0. Visuellt granskat.
- [Götaforsliden1, foto02](https://commons.wikimedia.org/wiki/File:G%C3%B6taforsliden_1_i_M%C3%B6lndal_02.JPG),
  Historiker, 2013-04-05, CC BY-SA 3.0. Visuellt granskat; särskilt tydlig volym- och fasadrytm.
- [Gamla stadshuset](https://commons.wikimedia.org/wiki/File:Gamla_stadshuset_i_M%C3%B6lndal.JPG),
  Historiker, 2013-04-05, CC BY-SA 3.0. Visuellt granskat.
- [Museets beskrivning av byggnadsordningen41/43/45](https://digitaltmuseum.se/011014739586/gamla-torget-i-molndal-1970-tal-fran-vanster-kvarnbygatan-41-viktualieforeningens).

Wikimediafotona laddades enbart till tillfällig lokal analyscache under `/private/tmp`.
`ortho_osm_study.jpg` är däremot vår egen annoterade studie av Lantmäteriets befintliga ortofoto,
CC BY 4.0: © Lantmäteriet, bearbetning med OSM-geometri © OpenStreetMap-bidragsgivare (ODbL).
Den är referensmaterial, inte en fasadtextur.

## Osäkerheter som måste stå kvar

- Inga laserpunktmoln har analyserats här. Nock-/takfotshöjder och träd är inte inmätta.
- Byggnadshöjder är uppskattade från våningsantal och proportioner; skala mot fotot före detaljering.
- DTM:n kan ligga på bank, bädd eller vatten i ån och är inte en vattenståndsmätning.
- Vägbredder och brodäck kräver författad utformning. Centrumlinjer är inte färdiga gator.
- Bakgrundshus utanför de fyra granskade byggnaderna har schablonfasader märkta låg säkerhet.
- Sökning efter kommunala fasadritningar gav ännu inga exakta mått för Kråkan.

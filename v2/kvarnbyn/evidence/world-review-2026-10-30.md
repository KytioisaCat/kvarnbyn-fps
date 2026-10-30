# Oberoende världsgranskning — 2026-10-30

**Rekommendation:** gör nästa världspass på en liten tomtgrupp vid **Roten M 29–31**. Där kan ett enda prov visa om plana tomtnivåer, verkliga markgränser och grönska nära spelaren gör Kvarnbyn mer igenkännligt. Att bara öka den totala trädmängden löser inte de tre hinder som syns nedan.

Granskningen utgår från de tre översta överlämningarna i `DAGBOK.md`, `TODO.md`, `RESULTAT.md` och `RESULTAT-FAS-B.md`. Jag har tittat på de sparade Godotbilderna `spawn.jpg`, `torget.jpg`, `roten.jpg` och `royen.jpg` i `evidence/shots/` (tagna 2026-10-29) och kontrollerat aktuell kod samt `data/city.json`/`data/site.json`. Detta är en oberoende granskning av underlag och sparat bildresultat, **inte Joels godkännande eller en ny fullständig genomgång av den körande appen**. Inga produktionsfiler har ändrats.

## Tre konkreta igenkänningshinder

### 1. Grönskan finns på kartan men saknas i de små gaturummen

**Observerat i bilderna:** torget saknar närliggande gatuträd; Roten M har kala gräsremsor ända fram till fasaderna. Royens bild visar en stor bar slänt mellan trappan och industrin. Det gör både gatornas skala och tomternas avgränsning svåra att läsa.

**Verifierat i konstruktionen:** träd accepteras bara där klasskartan säger skog, alternativt OSM-skog med tillräcklig skogsvikt. De placeras på ett jittrat 8,5-metersrutnät. Därefter rensas de bort inom 2,5 m från byggda markytor och effektivt 4,5 m från hus. Blender bygger bara tre lövträdsvarianter; inga buskar eller häckar byggs. Se [trädurvalet](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/pipeline/site.py:368) och [instanseringen](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/blender/build_world.py:278).

Mätning av faktiska placeringar i `site.json` (horisontellt avstånd, inga påståenden om kamerans synfält):

| Mätcentrum, lokalt x/z | Träd inom 25 m | Inom 50 m | Närmaste träd |
|---|---:|---:|---:|
| Torgkameran −8,5 / 8 | 0 | 0 | 55,4 m |
| Zon B, Roten M 100,792 / 110,188 | 0 | 4 | 27,5 m |
| Zon C, Royens trappor 174,792 / −0,812 | 2 | 3 | 3,2 m |
| Startpunkten 339,992 / 153,188 | 3 | 8 | 12,1 m |

**Data eller bygge? Båda.** Vi saknar placerade trädgårdsbuskar/häckar och individuella gatuträd i stadsbeskrivningen. Urvalsregeln utesluter samtidigt de smala gröna tomtremsor som behöver växtlighet. Totalsiffran 1 570 träd säger därför lite om miljön framför spelaren. Tre unga träd framför Musikskolan är visuellt noterade i [gårdagens manuella Street View-granskning](/Users/joel/Workspace/kvarnbyn/v2/poc/torget/reference/OBSERVATIONER.md:72), med bilddatum maj 2026; deras exakta lägen och mått är uppskattade.

### 2. Husen står på sammanhängande slänter i stället för läsbara tomtnivåer

**Observerat:** i [Roten M-bilden](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/evidence/shots/roten.jpg) fortsätter grässluttningen utan avbrott mellan husen. Vänster hus får en lång hög stensockel men ingen plan gård eller murkant utanför huset. I [Royens bild](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/evidence/shots/royen.jpg) blir större delen av mellanrummet en diagonal gräskil. Det är precis den typ av jämn sluttning Joel pekade ut som fel.

**Verifierat:** [terrängsteget](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/pipeline/site.py:185) konformerar höjdfältet mot gator/OSM-ytor och ån. Det finns inga tomtplan eller uppdelningar vid trädgårdsmurar. Blender ritar ett sammanhängande 2-metershöjdfält; branta rutor får bergmaterial, se [markmeshen](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/blender/build_world.py:128). Husens bas sätts till markprovernas 65:e percentil och [stensockeln dras till lägsta markprov](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/blender/houses.py:74). Det kan ge höga socklar men skapar ingen terrass.

**Data eller bygge? Båda.** Dagens OSM-underlag innehåller 8 staket, 3 murar och 2 vägräcken i zonen, men **0 stödmurar och 0 häckar**. `interpret.py` kan läsa sådana taggar, men de befintliga `barriers` används dessutom inte av `site.py`/`build_world.py`. De 608 byggda åmurssegmenten gäller kanalbanken och fyller inte denna lucka. Det går alltså inte att få riktiga terrasser enbart genom att slå på en befintlig lista. Exakt vilka murar och nivåer som finns vid Roten M återstår att verifiera visuellt; jag har inte mätt in dem här.

### 3. Torgytorna återgår till vägband och gräsgap trots befintligt platsunderlag

**Observerat:** [torgbilden](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/evidence/shots/torget.jpg) visar en stor asfaltförgrund, smala separata stenband och gräs mellan förgårdsytorna. Planteringsöarna saknas. Fasadernas förhållande till torget blir därför för glest och generellt.

**Verifierat:** [tolkningen](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/pipeline/interpret.py:279) läser gårdagens `authored_ground.json` till `city.json`, men inga anrop i mark-/Blendersteget använder fältet. [Markytorna](/Users/joel/Workspace/kvarnbyn/v2/kvarnbyn/pipeline/site.py:110) kommer i stället från OSM:s parkeringar/torg/lekyta och buffrade väglinjer. Gatsten inom 140 m från origo byter material på de ytor som redan finns; den fyller inte ut den saknade förgården.

**Data eller bygge? Här finns redan användbart underlag, men kopplingen saknas.** Stadsbeskrivningen bär förgårdspolygonen `torget_connected_forecourt` (1 444 m²) och tre planteringsöar (26–29 m² vardera). Sammanhängande stenläggning och planteringar är observerade; **polygonernas exakta konturer och höjder är inte inmätta**. Den större nordbanksytan i samma fil är en grövre uppskattning och bör inte appliceras okritiskt. Klipp en kommande torgyta mot hus, asfalt och å, förena den med befintlig stenläggning och skapa kantsten bara vid verkliga ytterkanter.

## Ett avgränsat nästa platsprov

**Roten M 29–31, med närmaste tomtkanter:** lokal ruta **x 75–125, z 80–135 m** (50 × 55 m), samma origo 57,65690 N / 12,02780 E. OSM-husen är `w92332120` (29), `w92331973` (30) och `w92332141` (31); 33 och Royens gata 34 ligger i provets kant. Detta är en föreslagen arbetsruta, ingen fastighetsgräns. Den befintliga Roten-kameran ligger på **[114,79; 24,16; 122,19]**, riktad mot **[70,792; 27,480; 85,188]**, och kan användas för före/efter.

Första steget i nästa pass är en riktad visuell kontroll av just dessa tomter: markera synliga murkrön, murfötter, plana gårdar, infarter, trappor, häckar och träd. Google Maps kunde inte öppnas i detta pass eftersom webbläsarytan saknades; ingen ny Street View-observation för Roten M påstås här. Det gamla torgunderlaget är däremot manuellt granskat. Kvarvarande dolda tomtkanter och alla höjder ska uttryckligen märkas uppskattade.

Bygg sedan **bara verifierade nivåer och växtgrupper i denna ruta**, med riktiga vertikala murar mellan nivåerna och separata gränser för gräs, grus/sten och asfalt. Behåll hus och dagens ljus oförändrade så platsens förbättring går att bedöma. Låt inte en global slumpmässig trädökning ersätta placerade häckar, buskage och små träd här.

Provet är redo för Joels bedömning när samma ögonhöjdsvy före/efter visar tydliga tomtnivåer, närbilder visar hur murfot/mark/sten möts utan glipor och gångproben längs gatans/infartens faktiska kollisionsyta saknar hål och oavsiktliga hopp över 22 cm vid 0,5-meterssteg. Trappsteg bedöms separat. Lägg även en vy längs muren för att visa nivåskillnaden; ett fågelperspektiv räcker inte. **Detta är föreslagna leveransgrindar, inte ett påstående att igenkänningen är uppnådd.**

# Karta — övre Görjelycksgatan / startkvarteret

**Status:** klart för detta delpass, integrerat i main och ordinarie app2026-11-09. **Startcommit:**aed6132. **Gren:**codex/karta/gorjelyck.
**Arbetskopia:**/private/tmp/kvarnbyn-karta-gorjelyck.

Fortsättning på Joels uttryckliga beställning att iterera olika områden tills
agentens tokenutrymme tar slut. Första gaturundorna är redan levererade i appen.
Granska nu riktiga panoramor vid spawn, identifiera hus mot OSM/flera ankare,
rätta säkert synliga fasader/tak/gatukopplingar och prova samma nya/äldre grindar.
Ingen obelagd överföring av en fasad till närmaste hus. Ingen bildtextur från Google.

Reserverat: nya reference/gorjelyck-källor, pipeline/interpret.py för läsning av
flera separata områdesunderlag, lokala mark-/husdetaljer vid behov. Gemensamma
blender/build_world.py/capture_road_review.gd endast avgränsad vy-/provkoppling.
Egen värld/assets/import/export/cache; delade verktygsbinärer read-only.
Alla Godot-körningar Dummy + master mute. Spelbalans/rörelse/civila bevaras.

Joel lade under passet till att sadeltaken inte går att stå på. Orsak bekräftad:
vanliga sadeltak från modelkit.roof har synlig geometri, men bara husets väggskal
fick kollision. Spåret utökas med gångytor från de faktiska synliga takplanen,
gemensamt takprov i riktig värld/export samt en avgränsad world.gd-provkoppling.

## Återupptaget 2026-11-09

Joel bekräftade fortsatt arbete: taken först, sedan fasader/trappor/entréer kring
Götaforsliden; parkeringar och mindre planteringar där det hjälper igenkänning.
Häckar, träd och gatsten lägre prioritet. Ingen parallell agent beställd tydligt.
Föregående Blender-takbygge blev inte exekverat: automatisk granskningsfunktion
saknade arbetsplatskrediter. Ny uttrycklig fortsättningsbegäran; försöker ordinarie
byggning igen. Källor/startkvarter finns isolerade här, ännu inte integrerade.

## Första verifierade delresultat 2026-11-09

- Fyra trähus matchade med två faktiska augusti2024-panoramaankare: vit låg
  panel/takkupa, separat vit östdel, rött och gult hus med lägre huvudvåningar.
  Originalkonturer kvar; sammanfogade deltak/verandor/häckar återstår. Flytande
  antaget vindsfönster på östdelen upptäckt i nativebild och borttaget före leverans.
- Två Åldermans-profiler:4,3/3,0m,65cm grusverge, utan att flytta spawn eller
  dela OSM-korsning. Menynamnet förtydligat. Fler granskningsunderlag kan läsas
  från separata reference/*/reviews.json; dubblett-id stoppar bygget.
- Takens synliga plan kompletterade med fysisk kollision, inklusive kupor och
  skorstenar. All29540uppåtvänd takgeometri i spelområdet täckt i GLB-provet;
  bakgrundshus utanför zonen undantagna. 15tak ×landning/stillastående/gång/krok
  +metadatagrind =76 gröna i källvärlden. Native faktisk landning på vita huset
  har3,5cm fot-/takskillnad; bild granskad. Samma gemensamma prov i release.
- Gatugrind12,88574synliga/kolliderande trianglar:0husintrång, navkorsningar och
  anslutningar gröna. Alla180globala gångpunkter och31nya gatuprover gröna;
  källvärldens civila29 och krok27+stad gröna. Ett civilprov startades först
  felaktigt med --explore; kördes om i riktig strid, grönt. Inga spelvärden ändrade.
- Ny faktisk närgranskning vid G17/G18: G18-dörr i övre änden,3gatubaypositioner,
  G17 saknar generiska balkonger. Plattform/räcke och infarter/trappor återstår;
  dold trappanslutning har inte hittats på. Nästa platsprov prioriterar dem.

Slutpaket byggs separat som v2/.tools/Kvarnbyn-tak-02.zip. Ej installerat ännu.
Råloggar lokalt v2/.tools/*-delivery*, *-final* och roof-*. Kända CA/ObjectDB-
avslutsvarningar separerade från stdout. Inga Street View-pixlar distribueras.

Integrationskontrollen reproducerade city/site/nav/game byteidentiskt. Kartbilden
var också identisk, men map.json bar city-hashen före den sista fönsterplaceringen.
Kartmetadata omgenererad före leverans; nytt slutpaket tak-03 väljs. Inga ändrade
pixlar eller gångytor. Detta är skälet till omexporten, inte ett nytt kartpass.

Slutkvitto: tak-03 installerad och samtliga apppayloadhashar matchar.76takprov i
installerad app +kartresurser gröna; civila29 i tak-03. De övriga releasegrindarna
är från geometriskt/kodmässigt identiska tak-02 (endast map.json-källhash byttes).
8världsfiler jämförda, identiska efter integration. Manifest i ordinarie projekt
evidence/delivery-roofs-2026-11-09.json; tidigare app bevarad därs v2/.tools/
kvarnbyn-tak-20261109/previous. Fortsatt Götaforsarbete får egen logg/arbetskopia.

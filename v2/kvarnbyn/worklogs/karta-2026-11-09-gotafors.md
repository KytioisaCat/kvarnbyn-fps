# Karta — Götaforslidens entréer och närfasader

**Status:** klart, integrerat och installerat i ordinarie app. **Startcommit:**e35a855. **Gren:**codex/karta/gotafors-entres.
**Arbetskopia:**/private/tmp/kvarnbyn-karta-gotafors.

Joel vill fortsätta med fasader/trappor/portar/parkeringars igenkänning kring
Götaforsliden, lägre prioritet för häckar/träd/gatsten. Takpasset och fyra trähus
är redan installerade/verifierade. Ny arbetskopia med egna assets/cache/export;
endast verktygsappar läses genom separata länkar. Inga samtidiga underagenter.

Reserverat: reference/gotafors, egna Blender-/markdetaljer för bekräftade entréer,
befintlig G18/G17-review om närgranskningen kan belägga mer. site/build_world
endast smal integration av detta platsprov, ingen spelbalans. Master mute/Dummy.

Underlag: maj2026-pano KcCRF9O_ugcT21i2VurKLQ faktiskt granskat. G18 lång
upphöjd plattform, gulgrön dörr och vitt rör-/enkelt träräcke, grå grund/natursten,
träspaljé på övre änden. Anslutningen till övre gatan behöver ses från andra hållet
innan en dold trappa modelleras. G17-gröna portar, naturstensgrund; glasad entré
i högra indragna delen, men exakt koppling till OSM-delfasad måste säkerställas.

Första platsprovet: G18-plattform5,5×1,05m, topp22,959 (samma som dörrtröskeln),
ljust tvåliggarräcke. Nivåanslutning2,4m från övre sidan,3uppskattade steg à18cm
från befintlig verklig gatuyta22,42. Ingen observerad exakt stegräkning påstås.
G18:s generiska dörrplatta tas bort för att slippa dubbla ytor. Spaljén återstår.
Lokal väglinje justerad ytterligare57/71cm från G18 för fri passage;381hus/352vägar
fortsatt gröna i källkontroll. Ny värld/prov ännu inte granskad eller levererad.

Reserverar även smal world.gd-koppling --entrance-export-check och parametrisering
av befintlig road_check.gd: samma verkliga kapselkontroll på entréns metadata.
Ingen ändring av rörelse-/stridskod. Allt ljudlöst. Före-vyer sparade från samma
kameror innan den nya geometrin importeras; mått och källor i entrance.json.

Första riktiga kapselprovet grönt: plattform upp/ned (första10kontrollerna), högsta höjdfel19,7cm respektive9,8cm. Gata31,
krok+stad och180globala landningspunkter gröna. Nativebild fångade att front-
kameran låg inne i G17 och hamnade på taket; kameran rättad till faktisk pano-
punkt och förebild tas om i levererad oförändrad tak-03-värld. Trappans första
80cm-djupa terrassplan ändras till34cm-steg plus nedre vilplan. Gångprovet
utökas att starta på riktig väglinje, inte genom placering på första steget.

Markytorna skärs även bort under entréns stöd/anslutning; vägen ska inte bara
döljas under en ny låda. Entréns samma källmått styr skärningen. Slutlig byggning
och utökat gatuanslutningsprov återstår före export/integration.

Slutanslutningen nåddes åt båda håll från riktig gata, men trappans legitima
step-up gav26,5cm tillfälligt höjdfel mot en interpolerad mittlinje. Plana
gators25cm-gräns behålls; entréprovet får35cm transientgräns och ett nytt
strängare krav efter25vilofysiksteg: riktig markkontakt och <16cm fel.
Ingen spelarfysik ändras. Kamerans vymenyval flyttas till övre panoramapunkten
för att undvika en gammal kamera som låg inne i G17. Ny slutbyggning krävs.

Efter markskärningen blev det slutliga nedre vilplanet22,268m och antalet
anslutningssteg4 (cirka17,3cm höga,34cm djupa), inte den första prototypens3.
Det utökade provet från gatan når båda målen:26,5/18,7cm transient, men bara
0,08/0,95cm höjdfel efter vila och riktig markkontakt.13kontroller gröna.

## Slutprov klart för integration

Slutpaket v2/.tools/Kvarnbyn-gotafors-01.zip och entrance-app-01. Release:
entré13, gator31 och tak76 gröna, med riktig kapsel/markkontakt.13entréprov
innefattar gatuanslutning,9golvpunkter,2gångstråk (cirka8m vardera) och räcke.
Native slutbilder från båda sidor granskade mot omtagna före-bilder. G18 står
mörkt i gatans skugga; plattformens form/anslutning är synlig, men skuggornas
läsbarhet är en separat förbättringsidé. Inga bildpixlar från Google i produkten.

Geometrigrind12 grön:88458synliga/kollisionsvägtrianglar exakt mot aktuell site,
0husintrång inklusive exporterade plattforms-/steg-/vilplansytor. Takgeometrin
fortsatt0saknade kollisionsytor. Vägen/markytan är bortskuren under entrén.
G18-vygenväg använder nu övre panoramapunkten. Föregående app ligger kvar tills
integratören reproducerat paketets data och genomfört separat namnbyte.

Slutkvitto: installerad entré13 +karta gröna. Samtliga appfiler matchar det
verifierade paketet;8världsfiler byteidentiska efter integration. Native releasevy
granskad. Manifest i ordinarie projekt evidence/delivery-gotafors-2026-11-09.json.
Tak-03 bevarad lokalt;13skyddade spel-/NPC-filer fortfarande byteidentiska.

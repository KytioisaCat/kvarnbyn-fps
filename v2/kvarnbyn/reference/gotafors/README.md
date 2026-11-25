# Götaforslidens entréer — platsprov 2026-11-09

Street View faktiskt granskad från både nedre och övre sidan av G18. Panorama-id,
datum, riktningar och observationer i `entrance.json`. Ingen fotopixel i spelet.

G18 har en lång upphöjd betongplattform vid den gulgröna dörren, ljusa enkla
räcken, naturstensgrund och spaljé runt övre hörnet. Första provet bygger själva
plattformen och tvåliggarräcket; spaljé, värmepump och smådetaljer återstår.
Alla mått och anslutningssteg är uppskattningar. Fyra steg i slutprovet är en funktionell
anpassning mellan dörrtröskeln och levererad gatuhöjd, inte en observerad
stegräkning bakom spaljén. Stegprovet ska bedömas med detta förbehåll.

Lokala vägförskjutningen ger utrymme mellan plattform och G17 utan att flytta
OSM-husen. Samma linje används för asfalt/kollision/karta/nav. G18:s generiska
ensamma dörrplatta ersätts av plattformens sammanhängande yta.

`gotafors_details.py` bygger synliga och fysiska ytor från samma värden. Platsens
metadata provas med riktiga golvstrålar, spelarkapsel till/från dörren och räcket.
`--entrance-export-check` återanvänder samma kontroll som gaturundorna med ett
annat metadatafält. `verify_roten.gd --check-key=gotafors_ground_checks` ger ett
utförligare prov. Geometri-QA läser också de exporterade plattforms-/stegytorna.

G17:s L-form behöver fortsatt avläsning per delfasad. Uppströmsfasaden har gröna
portar/överljus och låga steg. Första provets globala vånings-/sockelnivåer räcker
inte för att hävda exakta dörrhöjder längs hela backen. Parkeringar, planteringar
och fler hus behandlas i följande delpass; de är inte färdigmodellerade här.

## Parkerade bilar, 2026-11-25

Tre biltak avlästes i Lantmäteriets ortofoto från 2024 (`public/ortho.jpg`,
8192 × 5529 px, CC BY 4.0). Bildcentrum i pixlar från övre vänstra hörnet:
silver (5004, 2403), grafit (4866, 2502), blågrå (4878, 2528).
Längdaxlarna följer bilden. Kulör, karossform och vilken ände som är fram
är tolkningar. Parkeringen visar ett urval ur det fotograferade ögonblicket.
En andra ljus bil på gården utelämnades eftersom två hjul hamnade utanför
den byggda asfalten. Varje bil vilar på ett plan anpassat till fyra hjulpunkter.
`parked-cars.json` kopplar modellerna till OSM-ytorna och `parking-views.json`
anger kamerorna för bildprov.

## Nivåerna vid Lilla Götafors och Franckegatan, 2026-11-25

Gatufotot visar hur Götaforsliden stiger förbi Lilla Götafors, medan entrén
på gaveln ligger lägre. Fotot från åsidan visar den stenklädda kanten på den
lägre avsatsen. Båda bilderna visar också kvarnens tegelgavel och sadeltak.
[Från gatan](https://commons.wikimedia.org/wiki/File:Lilla_G%C3%B6tafors_i_M%C3%B6lndals_Kvarnby_03.JPG)
och [från ån](https://commons.wikimedia.org/wiki/File:Lilla_G%C3%B6tafors_i_M%C3%B6lndals_Kvarnby_02.JPG).

De två korta murstråken följer nivåerna mellan gatan och kvarnen.
Franckegatans tredje stråk följer den stenstödda gröna slänten på panoramats
högra sida (posten francke i ../vag-hus/reviews.json). Ortofoton från
Lantmäteriet 2024 och markmodellen ger stöd för läge och lutning. Murändar,
tjocklek, materialdetaljer och anslutande markbredder är visuella
uppskattningar. Terrassernas ytskikt ansluter till den lokala terränghöjden.
Gatuytan behåller sin längslutning. Linjer och bredder i terraces.json.

## Takgranskning, 2026-11-25

381 individuella husutsnitt i spelzonen jämfördes översiktligt med modellens
taktyp i Lantmäteriets ortofoto 2024. Ett urval närgranskades i originalrutorna
(0,16 m). De 1 734 förenklade kulisshusen utanför spelzonen ingick inte.

roof-review.json anger 19 plana eller mycket flacka huvudtak och fem tak med
tydlig nock. G17:s mörka L-formade tak behåller sin plana huvudform. Huset
bakom Lilla Götafors (w92332117) får plant tak. Lilla Götafors får rött
tegeltak och tegelfasad efter gatubilderna. Av de 24 takbesluten ändrar 16
den levererade huvudformen. Åtta andra var redan plana i spelet, ibland för
att byggaren använde en plan reservform på en oregelbunden huskontur.

Exakt lutning på låglutande tak, nivåer på takinstallationer, radhusens
förskjutna delfall och skymda tak är inte inmätta. Särskilt Villa Korndal
(w90143419), w564428618/619 och w629220978 har mer komplicerade deltak
än nuvarande modell. De behöver författade delvolymer.

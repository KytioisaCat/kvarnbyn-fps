# Lilla huset på norra åbanken — lokal inventering2026-11-02

**Inget befintligt OSM-fotavtryck har hittats för det lilla huset i projektets
lokala extrakt.** Det finns inte heller en säker sluten takkontur att återanvända
ur2024-ortot. Mörka ortofält får inte bli nya byggnadspolygoner utan mer stöd.
Ingen modell, kod eller befintlig resultatfil ändrades i denna inventering.
Arbetsnamnet intagshus betecknar här bara läget vid anläggningen; husets exakta
funktion är inte fastställd.

## Underlag och avgränsning

Kontrollerat lokalt: `tools/osm_raw.json`, `tools/ortho8k.jpg`,
`v2/kvarnbyn/data/city.json`, `data/site.json` samt referenskartorna
[ortho_alignment.jpg](ortho_alignment.jpg) och [ortho_crop_2024.jpg](ortho_crop_2024.jpg).
OSM-extraktets egen tidsstämpel är **2026-09-03T13:16:30Z**. Denna inventering har
inte gjort en ny nätfråga mot dagens OSM och säger därför bara vad som finns i
projektets källdata. Granskat område: x[-35,25],z[0,35].

Koordinater: x öster/z söder i meter; origo57,65690N/12,02780E. Lokalt Godot-Y är
rå markhöjd minus18m. Höjderna nedan är DTM-mark, **inte laseruppmätt takhöjd**.

## Vad OSM faktiskt innehåller

Det lokala extraktet har inga relationer. I arbetsrutan finns inga relevanta
taggade noder och endast två skärande byggnadskonturer:

| OSM | Befintlig match | Konturens hela bbox x/z | Befintlig modellbas Y |
|---|---|---|---|
| w92331981 | Kråkans krog, på åns sydsida | x[2,370;50,209],z[17,110;35,222] |−0,750m, visuellt uppskattad |
| w92332145 | Stora kontors-/kontexthuset vid bron, ej lilla huset | x[−49,834;−23,866],z[28,787;57,419] |−1,432m, schablon |

Ingen av dem ger ett rimligt fotavtryck för lilla låga huset på den norra banken.
Övriga relevanta objekt är vägar, Forsebron, åns centrumlinje och torgets yta.
Det finns ingen separat registrerad intagsbassäng-/takpolygon här i extraktet.

## Siktuppgifter från roots faktiska Maps-granskning

Den här agenten har bara läst lokala data. Följande bildobservationer och riktningar
är **rapporterade av root**, som faktiskt granskade panoramorna under samma pass:

| Kamera | Lokalt x/z | Rapporterad riktning till huset |
|---|---|---|
| 45Kvarnbygatan, maj2026, panoZcfLUaEvEvdds8CYt5lQTg |[−25,06;3,13] |cirka115°, korrigerad efter objektets läge till vänster om123° bildcentrum |
| 8Kvarnbygatan, maj2026, panoi4aplezFKoyidT1kSnnXgA |[20,31;−5,69] |cirka225° mot öst-/nordöstfasadens dörr |
| 6Kvarnbygatan, maj2026, panoRhipc3Db_NukAEeSpCyZZQ |[−7,1055;8,4279] |cirka132,8–133° mot kroppens mitt, uppskattat från bildläge |

[Första två panoramornas referenslänkar](OBSERVATIONER.md).
[Tredje kameran, centrerad och faktiskt verifierad](https://www.google.com/maps/@57.6568243,12.0276807,19a,75y,133.51h,85t/data=!3m7!1e1!3m5!1sRhipc3Db_NukAEeSpCyZZQ!2e0!6shttps:%2F%2Fstreetviewpixels-pa.clients6.google.com%2Fv1%2Fthumbnail%3Fcb_client%3Dmaps_sv.tactile%26w%3D900%26h%3D600%26pitch%3D5%26panoid%3DRhipc3Db_NukAEeSpCyZZQ%26yaw%3D133.50693748840504!7i16384!8i8192).

Root ser i närbilden en tydligt rundad/oval långfasad och rundad platt taksarg;
det är **inte ett enkelt rektangulärt boxhus**. Nedre delen är ljus klinker/plint,
överdelen rödbrunt tegel, bred röd takkant och låg grön/mossig ovansida. Smala
vertikala öppningar och en mörkröd dörr syns. GC-banan passerar på gat-/nordsidan.
Detta stödjer form och material men innehåller inga uppmätta byggnadshöjder.

## Grov triangulering och ortokandidater

Med riktningar räknade0°norr/90°öster och de två korrigerade siktuppgifterna
115°/225° blir strålskärningen ungefär **x−0,1,z14,8**. Med±3° i båda riktningarna
flyttar skärningen inom ungefär x[−2,7;2,4],z[13,1;16,6]. Det är ett grovt
**inspektionsområde för siktpunkten**, inte husets bbox eller fastighetsgräns.
Riktningarna kan dessutom avse olika punkter på huset.

Den tidigare123°/225°-skärningen vid x−2,9,z17,5 är ersatt:123° var bildcentrum,
inte själva husets riktning. Den ska inte styra en modellplacering.

| Lokal ortodetalj | Bedömning |
|---|---|
| Kompakt blandning av mörka/ljusa ytor omkring x[−10,3],z[10,19] | Relevant sökområde. Mörka fält kan vara skugga/intagsdetaljer, medan ett ljust gröntonat tak kan ligga öster/söder om dem. Ingen säker sluten kontur. |
| Mörk västlig del ungefär vid[−8,12] | Ligger på nuvarande GC-asfalt i nya markprovet. Att kalla hela denna mörka yta hus skulle vara ett obelagt antagande. |
| Stor mörk rektangulär del omkring[22,6], delvis öster om arbetsrutan | Riktningarna pekar inte hit. Ska hållas åtskild från lilla huset; vatten/intagsbassäng/skugga är fortsatt möjliga tolkningar. |
| Långsmalt mörkt fält längre söderut vid ån | Sammanfaller med faktisk vatten-/kanalkontext och Kråkans skugga; inget nytt tak belagt. |

Ortot visar bygg-/markarbeten2024. En senare färdig yta eller byggnad2026 kan därför
sakna tydlig motsvarighet. Ingen takfärg ensam har använts för att skilja vatten,
skugga och byggnad åt.

Tredje närvyn stöder den korrigerade placeringen: från C3 till[0,15] är bäringen
cirka132,8°. Root rapporterar kroppens bildbredd ungefär215pixlar och takets
ungefär289pixlar i en1280pixelbred vy; med uppskattad kamerageometri är kroppens
4,5–5m diameter och takets ungefär6m förenliga med detta. Perspektiv/FOV och vilket
fasadparti som centrerats är inte kalibrerade. Ingen exakt cirkelform är inmätt.

## Föreslagen geometrisk arbetshypotes — inte en modellleverans

För ett kommande separat platsprov kan **centrum[0,15], kroppsradius2,3m** användas
som uttryckligen uppskattad startform: rund paviljong eller kort kapsel. Det ger
16,612m² och bbox x[−2,3;2,3],z[12,7;17,3]. Ett tänkt tak med radius3m motsvarar
ungefär6m total bredd. De synliga murförbandens krökning är starkt bildstöd för
rundad kropp; en cylinder/cirkel är fortfarande en förenkling av den okända planen.

Beräknat mot levererad Northbank-mark och befintliga vatten-/golvtrianglar:

| Kontroll | Husets r2,3m | Takets r3m |
|---|---:|---:|
| Överlapp ny GC-asfalt |0m² |0m² |
| Överlapp ny gångsten mot ån |0m² |1,638m² |
| Minavstånd till gångstenen |0,054m |överlapp |
| Minavstånd till GC-asfalten |1,254m |fortsatt fri |
| Minavstånd till befintlig vattenmesh |2,883m |2,183m |
| Minavstånd till gamla körbaneasfalten |9,224m |8,524m |

Husets54mm marginal till gångstenen är mycket mindre än placeringens osäkerhet.
Ingen faktisk fri passage har därför bevisats för ett färdigt hus. Taköverhänget
kräver även verklig kontroll av spelarens huvudhöjd om det hänger över gångytan.
Den befintliga vattenmeshen saknar det fotograferade intagets detaljer; ett positivt
avstånd till dagens vatten bevisar inte att en ny byggnad undviker den riktiga bassängen.

En hel cirkulär stenkrans med ytterradius2,8m blir8,008m² utanför huset, varav
0,916m² redan är Northbank-golv. Ytterradius3,1m blir13,566m², varav2,058m² redan är
Northbank. En50m² annulus kräver ytterradiuscirka4,605m, överlappar dagens gångytor
12,607m² och kommer inom0,578m från nuvarande vattenmesh. En sådan stor helkrans
rekommenderas inte på det här underlaget. Om ett litet prov görs senare bör det
begränsas till en smal anslutning på gat-/östsidan och bevara befintliga gångägare.

## Befintliga markhöjder vid sökområdet

| Prov x/z | Rå DTM m | Lokalt Y m | Nuvarande Northbank-yta vid exakt punkten |
|---|---:|---:|---|
|[0;14,7] |16,775 |−1,225 |ingen ny hårdgjord yta |
|[0;15] |16,636 |−1,364 |ingen ny hårdgjord yta |
|[−2;13] |17,537 |−0,463 |river_side_setts |
|[−2;17] |16,245 |−1,755 |ingen |
|[2;13] |17,136 |−0,864 |ingen |
|[2;17] |16,030 |−1,970 |ingen |
|[−8;12] |17,671 |−0,329 |GC-asfalt |

DTM-nivåerna varierar kraftigt mot banken. De kan inte användas direkt som
husgolv eller tak, och de färdiga hårdgjorda ytorna kan ligga högre än DTM:n.
En eventuell modell behöver eget mark-/kollisionsprov där tomten möter GC-stråket.
Faktisk exporterad COL-terräng vid[0,15] ligger påY−1,170, vid[2,15] påY−1,518 och
vid[0;17,3] påY−2,008. Aktuell färdig gångsten strax nordväst, prov[−2,13], ligger på
Y−0,054 (raw17,946m). Detta ger ungefär1,1–1,3m nivåskillnad från centrum till gången,
och ytterligare fall söderut. Att ta husbasen direkt ur DTM skulle därför ge fel
anslutning; att lägga allt plant i gångens höjd skulle i stället kräva betydande
uppfyllnad. Inget av detta har visuellt belagts som en ny hög mur.

C3:s aktuella spelmark vid[−7,1055;8,4279] ärY−0,168 i förplatsen. Det är en
modellhöjd och inte en uppmätt höjd för Streetview-kameran.

## Vad som återstår före modell

- Använd tredje närvyn och de två övriga vyerna för en gemensam ungefärlig planform;
  försök inte slå ihop två mörka ortofält till ett bassänghus.
- Fastställ en ungefärlig oval/kapselkontur och dess ändpunkter på norra banken.
  Befintlig OSM-källa kan inte leverera den.
- Håll GC-banan norr om huset och kontrollera dess fria bredd när fotavtrycket
  väl finns. Siktpunktens osäkerhetsområde tangerar nuvarande gångsten i nordväst.
- Intagsräckets och bassängernas form är en separat uppgift. Dagens enkla
  kanalpolygon bevisar inte den fotograferade anläggningens planform.

## Avgränsningsbeslut från root

**Huset byggs inte i det här passet.** Nära exteriörbild finns nu, men hus, smal
stenanslutning och intags-/plazageometri behöver behandlas tillsammans i ett eget
platsprov. Rapportens cirkel är en märkt arbetshypotes. Ingen hög ny fyllnadsmur,
hel stenplatta eller bassängform läggs till utifrån den. Den befintliga vattenytans
planform bevaras under det separata visuella vattenpasset.

Root verifierade slutligen samma närpano med huset centrerat vid133,51°/75°FOV.
Det stödjer den grova placeringen men ersätter inte en inmätt planform. Flik6 är
stängd efter granskning; inga Maps-pixlar sparades i projektet.

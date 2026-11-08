# Gator mot hus — referensrundor 2026-11-08

Joel beställde återkommande Street View-rundor och ville få bort gator genom hus.
`reviews.json` innehåller de faktiskt granskade panoramorna, fotograferingsdatum,
observationer och separata uppskattade byggvärden. Inga Google-pixlar finns i
spelmaterial eller Git. Skymda fasader är inte granskade.

## Första rundorna

1. **Gamla torget/Kvarnbygatan**, maj 2026: orienteringsankare, bred asfalt med
   körfältsmarkeringar och separerade gång-/cykelytor. Ingen generell avsmalning.
2. **Götaforsliden 18**, maj 2026: krämfärgad stående panel, gröna T-formade
   fönster/dörr, två fulla fönsterrader och grå/stensockel. Smal asfaltgata med
   stenlagd ränna. Första breddförsöket var för stort mot den orörda motsatta
   huskonturen; minskad lokal körbana till uppskattade 2,7 m och liten förskjutning.
   Mått, dolda sidor och entréplattformens exakta utformning återstår.
3. **Royens gata 1**, augusti 2024: vit stående panel, rödbruna ospröjsade fönster,
   grå putsad suterrängvåning med fönster, två ytterligare vita fönsterrader.
   Smågatsten och trång passage; uppskattad lokal bredd 3,2 m. Taket har inte
   kunnat bedömas i den granskade vyn och tidigare takantagande ligger kvar.
4. **Franckegatan**, augusti 2024, panoramat benämnt 7 Franckegatan: mycket
   smal asfalt, gatstenskanter, staket/grönska till vänster och stenstödd grön
   slänt till höger. Västra gatuhuset identifierat mot sin placering/fotavtryck,
   inte givet en obelagd gatuadress. Vit panel/foder och låg främre gavel;
   bakre höjd/delvolymer skymda. Uppskattad körbana 3,0 m.

## Diagnos och rättning

Den råa väg-bufferten berörde52hus/väg-par, men det var **inte52ritade fel**:
markbyggaren hade redan klippt bort OSM-husens originalkonturer. Kontroll av
färdiga marktrianglar visade12intrång, totalt cirka21,9m². Alla berodde på att
byggaren förstorat oregelbundna OSM-hus till omslutande rektanglar. Den synliga
husmodellen och markklippningen använde alltså olika konturer.

Nu återställs originalkonturen när rektangelförenklingen skulle blockera ett
vägstråk (13hus). Antaget sadel-/valmtak klipps mot rätt kontur i stället för
att falla tillbaka till ett obelagt platt tak. Markklippningen använder samma
byggkontur som hus/kollision. Originalhusens kartpositioner har inte flyttats.

Tre lokala gatulinjer och breddprofiler är justerade och tonas tillbaka till
ursprungligt läge/bredd. En ansluten infart följer sin gemensamma OSM-nod, så
att inget glapp skapas i navgrafen. OSM-källinjen och källnoderna sparas separat.
Vägbanan, markhöjder, kantsten, navgraf och spelkarta byggs från samma tolkning.
En låg gatstensbård ersätter den orimliga tunna gräsremsan vid de granskade gatorna.

## Verifiering

- `verify_layout.py` granskar381hus och352vägar, alla väg-/gångtrianglar och
  navgrafens kanter. Den läser också levererad GLB, kräver samma vägytor som i
  site.json och samma geometri i render-/kollisionsytorna. Separat kontroll
  inkluderar författade gångytor, trappor och brodäck.
- `road_ground_checks` exporteras med världen. Befintliga `verify_roten.gd`
  använder den riktiga spelarkapseln för tre gator åt båda håll, punktprover
  och husväggsblockering. Ingen ersättningsfysik eller testgolv.
- `capture_road_review.gd` ger samma fem före/efterkameror. Slutbilderna måste
  granskas i Godot; en lyckad polygonkontroll ensam bevisar inte igenkänning.

Nästa rundor: fler hus längs Götaforsliden/Royens gata, entréplattformar och
närliggande grönska; därefter andra tydligt avgränsade kvarter. Det finns fortsatt
stora generiska och ej granskade områden i världen.

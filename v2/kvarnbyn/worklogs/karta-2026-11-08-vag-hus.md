# Karta — gator mot hus, referensrundor

**Status:** pågår. **Startcommit:**1b14efc. **Gren:**codex/karta/vag-hus.
**Arbetskopia:**/private/tmp/kvarnbyn-karta-vagar.

Joel vill ha flera granskningsrundor mot Street View, bättre hus/gaturum och
framför allt inga gator som klipper genom hus. Kontrollera först om felet är
vägmittlinje, antagen bredd, förenklat husfotavtryck eller höjd/överbyggnad.
Ingen förutsättning att OSM-husen är exakta eller vägdata alltid fel.

Reserverat: pipeline/interpret.py, site.py och tillhörande plats-/QA-moduler,
hus-/vägreferenser samt avgränsade världsvyer/metadata i blender/build_world.py.
Sakjusteringar av Blender-husmoduler endast om faktisk bildreferens motiverar.
Rebuild/kontrollkoppling vid integration. Spelregler och civil-/rörelselogik bevaras.
Egen värld/assets/import/export/cache, återanvänder verktygsbinärer read-only.
Alla Godot-prov ljudlösa. Inga Street View-pixlar i spelmaterial.

## Mellanläge efter första två rundorna

Joel har utökat uppdraget: fortsätt iterera olika områden tills tillgängliga tokens tar slut.
Nuvarande etapp har 13 återställda OSM-huskonturer, tre lokala vägprofiler och
sidoförskjutningar, en medflyttad anslutande infart, tre referensbaserade fasadpass.
Street View faktiskt granskad: torget maj2026, G18 maj2026, Royens1 augusti2024,
Franckegatan augusti2024. Panoid/observationer/uppskattade mått i reviews.json.
Artefakt-QA grön för381hus/352vägar: render-/kollisionsvägtrianglar överensstämmer
med aktuell site, inga intrång i husväggar, hela navgrafen utan husgenomskärningar.
Alla sex verkliga gångsträckor fram/backåt passerade. Ett blockerprov riktades mot
utsidan av ett konkavt hushörn (felaktig testgeometri); mål ändrat till en säker
punkt inne i polygonen. Kräver omgenerering av metadata och nytt fullprov.
Native före/efter granskade, fasadläkt har minskats till rimligare djup efter bilden.
Kvar innan etappleverans: sista byggning, referensfotologg, utvidgad QA även för
författade gång-/trapp-/broytor, regressioner/export/ordinarie app och central integration.
Spel/civila/krokvärden ska bevaras. Därefter fortsätt nytt avgränsat område.

### Tredje passet pågår

Utvidgat artefaktprov passerade även för författade gångytor, trappor och brodäck.
Alla primära synliga/kollisionsvägtrianglar matchar varandra och aktuell site.
Andra bildrundan granskad: minskar nya fasadläktens överdrivna djup och lägger
cirka28cm låg gatstensbård vid de tre granskade vägpartierna i stället för gräs.
Ny byggning körs (egen session5603); därefter optimizer/import/prov i ordning.
Sex verkliga gångstråk var gröna redan före sista detaljpasset. G18:s för höga
entré/avsaknad av rätt betongplattform är dokumenterad kvarstående platsfråga,
inte färdigbedömd. Baslinje-/Street View-underlag och lokala värden sparade.

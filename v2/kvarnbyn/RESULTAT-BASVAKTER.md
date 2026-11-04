# Basvakterna återkommer som vakter — 2026-11-04

Stupade basvakter ersätts nu av nya vakter. När förstärkning kommer återställs
truppens tre vaktplatser, och återstående ersättare blir anfallare. Vaktmålet är
fortfarande basen vid Royens trappor(C).

Tidigare började omgången med tre vakter och sex anfallare, men samtliga ersättare
fick anfallsrollen. Ett prov med riktiga soldater, dödshändelser och ordinarie
förstärkningstimer visade felet: efter att de tre vakterna stupat bestod nästa
fulla trupp av noll vakter och nio anfallare.

Antal soldater,45sekunders väntetid, fiendetryck, hälsa och skada behåller sina
värden. Överlevande soldaters roller ändras inte. Rättningen kan göra basen bättre
försvarad; den är ingen mätning av hur lätt eller svår en mänsklig omgång blir.

19 kontroller passerar i den importerade spelvärlden: rena vaktförluster,
anfallsförluster, blandade förluster, heltruppsförlust, väntetid, återstart,
måletC och kvoterna0/9,9/9,2/5 samt12önskade vakter av totalt4 (begränsas till4).
En separat kontroll i den exporterade Mac-appen passerar: tre riktiga vakter
stupas, och nästa förstärkning återställer tre vakter i en trupp på nio.

Full återbyggnad/Mac-export passerar på128s inklusive tidigare gång-, soldat-,
vapen-, ljus-, fors-, kart-, mål- och frontprov. Alla agentkörningar är tysta.
Världens råa/optimeradeGLB, kartbild, spelkonfiguration och AI-vägnät har exakt
samma filhashar som kartleveransen. Rättningen ligger i hur roller tilldelas.

[Prov före rättning](evidence/allied-roles-before.json) ·
[Prov efter rättning](evidence/allied-roles-check.json) ·
[Exporterad apps prov](evidence/guards-export-check.json) ·
[Leveransdata](evidence/delivery-guards-2026-11-04.json).

Den nya Mac-appen innehåller också [kartans frontläge](RESULTAT-FRONT.md) och
[forsens rörelse](RESULTAT-FORS.md). Stora genererade filer finns endast lokalt.

## Ett nytt omgångsstickprov

Den exporterade appens tysta botprov nådde900,1 spelsekunder: alla zoner egna,
9allierade varav3vakter,78nedkämpade/31huvudträffar,0egna dödsfall och5fiender
kvar. Det blev tidsgräns, **inte seger**. Inga motor-/skriptfel i loggen.

Det är ett oseedat stickprov och ingen kontrollerad jämförelse mot den äldre
förlusten. Botens kod väljer fortfarande basC som gångmål när alla zoner är egna;
en riktig patrull/rensningsfas återstår. Ingen ytterligare balansändring gjordes
utifrån utfallet. [Omgångsdata](evidence/round-2026-11-04.json).

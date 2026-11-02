# Avgränsat punktmolnsprov — läge 2026-11-02

Målet är bättre underlag för tak- och trädhöjder. Detta pass har kontrollerat
metadata och åtkomst, inte mätt tak eller ändrat husmodeller.

## Vad som faktiskt finns

Lokalt finns markmodell och ortofoto, men inga LAS/LAZ-punktmoln. Markmodellen
kan inte tala om hur höga taken eller träden är. Inget Lantmäteriet-systemkonto är
konfigurerat i den här agentprocessen; inga inloggningsuppgifter har lästs/sparats.

Lantmäteriets öppna STAC-katalog har kollektionen `dsm-skoglig-copc`.
[Produktdokumentation](https://geotorget.lantmateriet.se/dokument/projects/laserdata-nedladdning-skog-api/released/1/).
En sökning över de fem provhusen gav två överlappande leveransrutor:

| Kandidat | Storlek enligt STAC | Insamling | Punkttäthet |
|---|---:|---|---:|
| `19b002-639_32` | 1 604 050 596 byte | 2019-11-29 | 1,2/m² |
| **`19b002-63925_3225_25`** | **90 989 680 byte, cirka 91 MB** | 2019-11-29 | 1,2/m² |

Den mindre rutan räcker för hela provet. Den stora filen behövs inte.
Metadata anger EPSG:5845. Kollektionens licensfält är `other`; anta inte att
äldre villkor för en annan markprodukt också gäller denna punktmolnsprodukt.

En HEAD-begäran utan inloggning till den lilla datafilen gav **401**. Inga
punktmolnsbyte hämtades. Produktbehörigheten måste finnas på ett systemkonto före
nedladdning. Konto/behörighet hanteras av Joel; skriv aldrig uppgifter i dagbok,
repo eller chatt. Metadata och åtkomstprovet finns i `pilot-metadata-2026-11-02.json`.

## Konkret nästa prov

Kråkan, Corpus, Musikskolan, M25 och M29 är valda eftersom de redan har visuellt
underlag. Exakta OSM-id:n/fotavtryck och befintliga uppskattade höjder ligger i
metadatafilen. De gamla modellhöjderna är jämförelsevärden, inte facit.

1. Hämta endast den lilla rutan efter att behörighet är tillgänglig. Lagra den
   lokalt/gitignorerat; spara filhash och metadata. Inga kontouppgifter i skript.
2. Läs hela LAZ-filen och klipp till provområdet. Lantmäteriet rapporterade
   [ett COPC-indexfel den 5 oktober 2026](https://www.lantmateriet.se/sv/geodata/vara-produkter/Produktnyheter/Geografisk-information/rattning-av-laserdata-nedladdning-skog/).
   Bekräfta rättningsstatus före strömmande delurval; datumet på en ny metadatapost
   bevisar inte i sig att varje index är rättat.
3. Kontrollera koordinater/höjdsystem mot den befintliga markmodellen innan
   punkter jämförs med husen. Anta inte att vegetations-/byggnadsklasser finns:
   inventera de faktiska klasskoderna först.
4. Gör punktbilder och separata takplansförslag för fem hus. Redovisa antal
   punkter, spridning, möjliga trädkronor och osäkerhet. Inga automatiska globala
   höjdbyten innan bilder och profiler är granskade.
5. Testa därefter trädposition/höjd i en liten ruta. Exakt artbestämning ingår inte.

Mölndals stads öppna datasida gav inget verifierat färdigt 3D-byggnadspaket i
sökningen. Det betyder inte att ett sådant saknas; inget paket har hämtats.
[Kommunens öppna data](https://www.molndal.se/kommun-och-politik/kvalitet-och-utveckling/oppna-data).

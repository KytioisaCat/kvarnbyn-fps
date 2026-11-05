# Botens rensningspatrull — 2026-11-05

Den automatiska testspelaren söker nu vidare längs kända gator när alla zoner
är återtagna. Tidigare blev gångmålet alltid bas C. Patrullen läser inga osedda
fiendepositioner. Människans styrning och soldaternas AI är oförändrade.

En riktig navnod per 65 m-ruta ger 138 patrullmål i det sammanhängande vägnätet.
Närmaste obesökta mål väljs först; efter ett helt varv börjar ett nytt. Vid
stillastående under 14 sekunders aktiv patrullgång provas nästa mål. Basanfall
eller återerövrad zon tar över. Synlig strid har samma prioritet som tidigare.

16 kontroller passerar för verkliga zonmål och navgraf, målbyte, omvägar,
fastnandetid, baslarm, full täckning före omtag och oberoende av osedda fiender.
De simulerade ankomsterna i dessa kontroller är inte gångbevis.

Separat i den exporterade Mac-appen gick den riktiga kapseln 216,33 m och nådde
tre patrullmål utan överhoppade mål. Alla 1 904 fysiksteg hade markkontakt.
Det är en kontrollerad provvärld med egna zoner och utan strid, inte en vunnen
spelomgång eller ett prestandamått.

Det vanliga seedade omgångsprovet förlorade vid 140,7 spelsekunder, före
rensningsfasen: 27 nedkämpade, 14 huvudträffar, en egen död och 63 fiender kvar.
Det säger inget om patrullens förmåga att vinna en hel omgång. Slutdiagnostiken
hittade bland annat många fastnaförsök vid Stallelidens mitt; fortsatt felsökning
är noterad i TODO. Ingen balansändring gjordes från detta stickprov.

Full återbyggnad/Mac-export passerade på 140 s med gamla grindar och de nya
målproven. Därefter tillkom den isolerade gångfixturen; slutimport/export,
målprov och release-gångprov passerar också. Världens råa/optimerade GLB,
kartbild, spelkonfiguration och AI-vägnät har identiska SHA-256 som föregående
leverans. Alla agentkörningar använder Dummy-ljud och mutad masterbuss.

Vid avslut rapporterar motorn ObjectDB-varningar (14 i editorfixturen,
57 i omgångsprovet); ingen sådan varning syntes i release-gångprovet.
Det återstår att felsöka livscykeln separat. Omgångens stdout/stderr flätades
samman i JSON-raden; den sparade analysen tar bara bort den explicit angivna
varningstexten. Framtida omgångar bör spara stdout och stderr i olika loggfiler.

[Kontroller](evidence/patrol-check.json) ·
[Gång i exporterad app](evidence/patrol-export-check.json) ·
[Omgång](evidence/patrol-round-2026-11-04.json) ·
[Leveransdata](evidence/delivery-patrol-2026-11-05.json).

# Berg, hällar och låga stenmurar — första passet 2026-11-08

Joels platsminne: Glasberget är främst klippor, med skog och grönt ovanpå.
Målet är att läsa terrängen som berg med vegetation på avsatser, inte en
sammanhängande gräsmatta. Första passet ändrar material, inte LiDAR-höjder.

## Underlag och säkerhet

- Befintlig Lantmäteriet-DTM och klasskarta ger höjd, rå lutning och marktäcke.
  Byggda vägytors höjdskärning används inte som bevis för naturlig klippa.
- [Mölndalsbostäder: Glasberget](https://molndalsbostader.se/bo-hos-oss/vara-omraden/glasberget/)
  beskriver områdets bergiga terräng, hällar, raviner och träd. Stöd för karaktären,
  inte för exakt geometri på varje bergvägg.
- [Mölndals stadsmuseum: Lilla Glasberget](https://digitaltmuseum.se/011014715540/utsikt-fran-berget-mellan-franckegatan-och-aldermansgatan-lilla-glasberget)
  lokaliserar enligt bildtiteln kullen mellan Franckegatan och Åldermansgatan.
  Originalbilden kunde inte öppnas; ingen fasad-/geometrimätning från den.
- Google Street View, granskat i webbläsaren: 3 Franckegatan och 2 Åldermansgatan,
  augusti2024: brant gaturum, naturligt berg med murgröna, korta stenbaser/murar.
  2 Norra Forsåkersgatan, maj2026: låga murar med staket och trappöppningar.
  Bilderna används bara för visuell referens; inga bildpixlar ingår i spelet.
- Efter Joels förtydligande följdes startgatans korsning: 13 Åldermansgatan
  (augusti2024), 35 och24 Görjelycksgatan (september2022), samma parkerings-/bergsida
  även juni2011. Villor, grov stenmur, träd och tät vegetation är synliga. Just
  klippans fulla kontur skyms delvis; Joels platsminne och DTM kompletterar bilderna.
  Huvudprovet är nu från spawn[340,153] mot bergsidan kring[490,250], inte den
  första översiktskameran längre åt sydost. Lägg inte hela klippmotivet på Lilla
  Glasberget väster om spawn av enbart namnlikheten.
- OSM-linjerna w90143431 och w92331953 anger murarnas planläge. De är märkta
  `wall`, inte uppmätta stödmurar. Höjd0,6–1,45m, bredd0,42m och stenmaterial
  är uppskattade. Ingen hög, hypotetisk terrass har skurits in i marken.

## Avgränsning

Lilla Glasberget ligger i spelkärnan. Det större Glasberget ligger till stor del
i kulissen sydost om kärnan. Spelgränsen flyttas inte. De mjuka områdesmaskerna
i `pipeline/terrain_cover.py` är konstnärliga första uppskattningar, inte inmätta
bergkonturer. Klippor prioriteras efter rå lutning; flackare hällar inom dessa
områden varvas med växtlighet. Exakta klippstup, avsatser, sprickor och murarnas
trapp-/grindöppningar återstår att platsgranska innan finmodellering.

Materialet är befintliga Poly Haven `rock_01` (CC0), en visuell bergproxy;
vi gör inget påstående om den lokala bergartens exakta färg eller geologi.
Triplanär projektion undviker utdragna texturer på branta sidor. Kontinuerliga
vertexvikter blandar berg/gräs/skogsmark utan gamla fyrkantiga materialfläckar.

Kontrollbilder: `capture_terrain.gd`, fem kameror före/efter och två kompletterande
vyer mot klippfasaden från startområdet efter Joels förtydligande. Höjdfälten
och alla icke-terrängdelar av site.json jämförs för att upptäcka oavsiktliga ändringar.

# Startkvarteret: Görjelycksgatan / Åldermansgatan

Granskat 2026-11-08 direkt i Google Street View, från två panoramapunkter
tagna i augusti 2024 och en äldre kompletterande vy från juni 2011.
Panorama-id, datum, riktningar och observationer finns i `reviews.json`.
Inga fotopixlar sparas som spelmaterial eller distribueras med projektet.

Startpunkten ligger vid korsningen mellan servicevägen Görjelycksgatan
`w1197238920` och Åldermansgatan `w1197238918`. Den ligger kvar där Joel har
spelat. Menynamnet förtydligas, utan att Street Views adressrubrik får flytta
en OSM-byggnad eller bli ett påhittat husnummer.

## Vad som kan beläggas

- `w92331966`: vita västra trähuset. Låg huvudvåning och vind, stående vit
  panel, vita korsspröjs, rött tegeltak, västlig gavel med vindsfönster och en
  central gatvänd takkupa. Tidigare två fulla våningar plus stort tak var fel.
- `w92500208`: vit östra del med egen gavel och veranda. Separat OSM-kontur;
  får egen låg sadeltaksvolym i stället för generiskt plant mörkt tak.
- `w92500355`: röda grannhuset längre österut. Stående röd panel, vita foder
  och knutar, låg huvudvåning och vind samt flera tegeltäckta gavlar.
- `w92332156`: gula trähuset sydväst om startpunkten. Låg huvudvåning,
  stående gul panel, vita foder, tegeltak och tredelat frontgavel-fönster.
  Det delvis skymda gula huset `w92331987` får inga ärvda fasaduppgifter.
- Huvudgatan har asfalt med grus-/gräsverge; den sydvästra grenen är smalare.
  Här ska de tidigare granskade gatornas smågatstensbård inte återanvändas.

## Tolkning som återstår

Höjder, fönstermått, färgkoder och gatubredd är visuella uppskattningar, inte
inmätta mått. OSM-fotavtrycken behålls. Takens huvudsakliga riktning följer
konturerna; exakta deltak i röda huset samt verandor, spjälstaket, häckar och
stenmurar återstår. Detta är ett platsprov, inte fyra färdiga specialmodeller.

`views.json` ger fyra fasta före-/eftervyer och nya val under **Gaturunda**.
Bildprovet körs med `capture_road_review.gd`, `--views=res://../reference/gorjelyck/views.json`
och `--image-dir=res://../evidence/gorjelyck`. Alla automatiska spelprov är ljudlösa.

## Gångbara tak, tillägg 2026-11-09

Vanliga tak hade synliga sadel-/valmplan men bara huskroppens skal kolliderade.
`blender/roof_collisions.py` kompletterar tak, kupor och skorstenar från deras
faktiska synliga ytor före export. Befintliga explicita takytor återanvänds utan
identiska dubbla kollisionspolygoner. Bakgrundshusen utanför spelområdet undantas.
Ingen generell höjning av spelarens klätter-/lutningsgräns.

Oberoende kontroll läser den levererade GLB:n: synliga uppåtvända taktrianglar
ska täckas av samma lutande kollisionsgeometri. Annan trianguleringsdiagonal på
samma plan godtas genom geometrisk täckningskontroll. 15 riktiga takprov omfattar
landning från luft, stillastående, gång och krokfäste; både vanliga, handbyggda och
OSM-klippta tak. Samma kontroll körs i editor och release med `--roof-export-check`.
Nativebilden `evidence/gorjelyck/roof-standing.png` kommer från riktig landning,
inte en fritt flygande kamera. Rörelsevärden, världslager och stridsregler behålls.

Bildgranskningen fångade ett felplacerat vindsfönster vid den vita östra delen.
Det renderas inte innan dess sammanfogade deltak har lösts; ett observerat fönster
ska inte sväva framför ett antaget takplan.

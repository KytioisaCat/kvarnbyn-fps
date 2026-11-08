# Spel — fyra unika civila NPC:er

**Status:** klart — redo för integration. **Startcommit:**5ee54e1. **Gren:**codex/spel/civila.
**Arbetskopia:**/private/tmp/kvarnbyn-spel-civila.

Joel har valt Lars Gahrn, Per Andersson, fiktiva Ronny Jönsson och Linnea
Rönnqvist från Nyhetsshowen. Hitta/granska bildreferenser, bygg egna separata
civila 3D-gestaltningar och integrera i riktiga Godot-världen.

Reserverat: nya civilian/NPC-skript, ny Blender-byggare och fyra modellfiler,
bild-/källmanifest, prov och civilkonfiguration. Avgränsad gemensam koppling i
world.gd (spawn, uppdatering, exportprov), weapon.gd (civilträff utan blod/poäng),
rebuild.sh/export vid integration. Ingen annan skrivare i dessa filer nu.
Världens GLB/nav/karta/spelbalans ska förbli oförändrade. Lokala tillgångar
kopierade till egen assets/cache; endast verktygsappar återanvänds via länkar.

Alla agentprov ljudlösa. Referensfoton används vid formgivning och ingår inte
som fotopixlar i de levererade modellerna. Referruttag sparas lokalt med
källhänvisning; storleken hålls liten. Ingen röstkloning eller verkliga citat
planeras; eventuella repliker är egna, tydligt spelpåhittade.

## Resultat

- Fem granskade referensfoton, cirka 0,5 MB, endast lokalt i egen verktygsmapp.
  Källor/URL/hashar/visuella observationer i `reference/npc/selected-civilians-2026-11-08.json`.
- Egna separata riggade modeller: Lars lång/mycket smal, Per normalbyggd,
  Ronny rundlagd med mage, Linnea kvinnlig siluett enligt Joels tillägg.
  Civila vardagskläder, inga soldatmesh/vapen; 16 ben och fem egna klipp var.
- Fyra personer på torgets hårdgjorda ytor, kort promenad/hälsning/samtal med E.
  Egna spelpåhittade repliker, inga verkliga citat/röster. Namn/Civil vid fokus.
  Vymenyn får fyra genvägar. NPC-placeringar är fiktiva, inte hemadresser.
- Kollisionslager 8, fristående från soldatlag och zon-/målpooler. Vådaskott
  stoppas med Startle/varning utan skada/blod/träffmarkör/poäng. Soldater avstår
  när civil blockerar. Spelare går inte rakt genom en civil; krok fäster bara värld.
- 29 riktiga stadsprov gröna även i release: importerad rigg/animation, markkontakt/
  gång, tangent-E, sikt/hinder, pausad UI, skydd mot kropp/huvudskott, AI och omstart.
  Regression: vapen13, krok27, rörelsemeny25, karta/paus19, terräng7 +272murstrålar,
  vanliga kontroller och soldattaktik gröna. Åtta värld-/kart-/spelfiler byteidentiska.
- Native Forward+-bilder på torget, ansiktsbilder och femfigursjämförelse med soldat
  granskade. Lars/Per flyttade ur rabatterna efter första bildprovet. Linneas håryta
  och civil-/krokhjälpens överlappning rättade. Detta är första stiliserade likheter,
  inte färdigt fotorealistiskt porträttarbete; Joels bedömning återstår.
- Mac-exporten måste lista fyra GLB-resurser uttryckligen; första isolerade
  releaseprovet avslöjade att enbart skript-preloads inte räckte. Rättat och nytt
  rent paket verifierat. Stdout/stderr separerade för maskinläsbara slutprov.

Integratören återstår att lägga till centrala TODO/arkitektur/krav/dagboksanteckningar,
kopiera lokala modellutdata och installera verifierad app/ZIP på Joels ordinarie plats.
Stora GLB/foton/exporter/bildprov committas inte. Reproducerbar byggare, importinställningar,
rigg/runtime/källmanifest och små kontrollrapporter committas.

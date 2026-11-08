# Två parallella spår — spel och karta

Beslutat med Joel 2026-11-08. Samma spel och repository, separata arbetskopior,
tydligt filansvar och en gemensam integration. Målet är att kunna finjustera
spelupplevelsen samtidigt som Kvarnbyn blir mer igenkännligt.

## Roller och arbetskopior

| Spår | Ansvar | Normal leverans |
|---|---|---|
| **Spel** | Rörelse, gripkrok, vapen, soldater/AI, antal, skjutbeteende, balans och spel-HUD | En liten prövad kod-/konfigurationsändring |
| **Karta** | Hus, terräng, gator, trappor, grönska, material, miljöljus och kartunderlag | Ett avgränsat platsprov med referenser, bild och gång-/kollisionsprov |
| **Integration** | Delade gränssnitt, sammanföring, centrala statusdokument och godkänd spelapp | Båda spårens ändringar testade tillsammans på main |

Två samtidiga uppdrag ska ha **varsin Git-worktree och varsin gren**. Två grenar
i samma arbetsmapp skyddar inte från att filer och exporter skrivs över.
Namnen ska ange spår och uppgift, exempelvis `codex/spel/landningsglid` respektive
`codex/karta/krakan-fasad`. Main är den gemensamma, integrerade versionen.

Exempel för en integratör, när separata arbetskopior faktiskt ska startas:

```sh
git worktree add ../kvarnbyn-spel -b codex/spel/landningsglid main
git worktree add ../kvarnbyn-karta -b codex/karta/krakan-fasad main
```

Detta dokument startar inga nya chattar, grenar eller arbetskopior i sig.

## Filansvar

Sökvägarna nedan är relativa till `v2/kvarnbyn/`.

| Område | Ägare |
|---|---|
| `config/gameplay.json` | Spel: soldatantal, förstärkningar, fångsttakt, HP, vapensiffror, soldatfart/sikt/eld/skada och basens zon-id |
| `godot/scripts/player.gd`, `grapple.gd`, `movement_*.gd`, `weapon.gd`, `game.gd`, `soldier*.gd`, `bot_patrol.gd`, `hud.gd`, `fx.gd`, `sfx.gd` | Spel, med tillhörande prov |
| `blender/build_ak5.py`, `build_soldier.py`, soldat-/vapenkällor | Spel, trots att byggskripten ligger i Blender-mappen |
| Övrig `blender/`, platsreferenser, författad hus-/markdata och `pipeline/` | Karta; `site.py` bestämmer geografiska zon-/spawn-/infallslägen och läser spelbalansen ur konfigurationsfilen |
| `godot/scripts/lighting.gd`, `street_lights.gd`, `river_water.gd`, miljöshader och modellimport | Karta, med tillhörande bild-/gång-/materialprov |
| `godot/scripts/world.gd`, `overlay.gd`, `project.godot`, `export_presets.cfg`, `rebuild.sh` | Gemensamma kopplingspunkter: reservera en avgränsad ändring innan två uppdrag rör dem |
| Rotens `DAGBOK.md`, `TODO.md`, `ARKITEKTUR.md`, `KRAVSPEC.md`, `CLAUDE.md`/`AGENTS.md` | Integration under parallellt arbete |
| Genererad `data/city.json`, `godot/assets/game.json`, `nav.json` och gemensamma resultatmanifest | Återskapas/uppdateras vid integration; arbetsspåren behandlar dem inte som manuella källor |

Ett filnamn som inte passar listan avgörs utifrån dess funktion, och ägaren skrivs
i uppdragets logg före ändring. En reserverad gemensam fil har en ansvarig skrivare
åt gången. Behov av den andra sidans arbete lämnas som en konkret ändringsbegäran
i loggen; skriv inte samtidigt i samma kopplingspunkt.

## Gränsen mellan spel och värld

Spelbalans hör hemma i `config/gameplay.json`; rörelsens standardvärden i
`movement_settings.gd`. Ändra inte `site.py` för att få fler soldater eller andra
eldintervall. `site.py` kombinerar balansen med världens koordinater till samma
`game.json` som tidigare. Därmed kräver en balansändring ingen ändring av kartkod.

Världen levererar lokal meterkoordinat med Y upp, kollisionslager 1, fungerande
gång-/tak-/broytor, metadata, navigeringsgraf, kartbild och zon-/spawn-/infallslägen.
Spelaren ligger på lager 2 och använder världens kolliderare. Ändringar av
koordinatsystem, kollisionslager, filformat eller resursnamn är gränssnittsändringar
och ska integreras uttryckligen. Att två diffar går att merga betyder inte att
en ny dörr, trappa eller spawn är spelbar; det avgörs av det gemensamma provet.

En godkänd världsversion identifieras av **källcommit och filhashar**, inte bara
av namnet `world.glb`. Paketen måste hålla ihop: GLB, `world_meta.json`, `nav.json`,
kart-PNG/-JSON och vattenfält. Spelspåret använder en bestämd godkänd värld som
grund och byter till en ny sådan vid en tydlig integrationspunkt.

## Lokala filer och byggning

Varje arbetskopia har egna `godot/.godot/`, `godot/assets/`, `staging/`,
`evidence/`, `desktop/` och provloggar. **Symlänka inte skrivbara byggmappar eller
hela `v2/.tools/` mellan spåren.** En redan byggd värld kan kopieras lokalt till
den andra arbetskopian; en symlänk som kartbyggaren senare skriver genom isolerar
inte arbetet. Stora genererade modeller/exporter ska fortsatt inte committas.

Verktygsbinärer får återanvändas från befintlig installation via läsning eller
separata länkar till själva Godot-/Blender-appen. Provutdata ska ändå ligga i den
aktuella arbetskopian. Källtexturer och övriga lokala, ignorerade beroenden måste
finnas där innan en kartbyggnad går att återupprepa; Git-worktree kopierar dem inte.
Ingen ny nätverksnedladdning krävs bara för att skapa två arbetskopior.

Spelspåret kan ändra kod och importera/exportera sin Godot-app utan att köra
Blender. Efter en balansändring kan platsdata genereras i en isolerad stagingmapp:

```sh
tools/venv/bin/python v2/kvarnbyn/pipeline/site.py \
  --stage-dir v2/kvarnbyn/staging/spelbalans
cp v2/kvarnbyn/staging/spelbalans/game.json v2/kvarnbyn/godot/assets/game.json
```

Detta görs i spårets egen arbetskopia och använder dess senast godkända kartkällor.
Kopiera inte stagingens världsfiler in i det andra spåret. Kartspåret kör den
vanliga världskedjan i sin arbetskopia. Alla agentprov är fortsatt ljudlösa.

## Loggning utan dokumentkonflikter

Alla läser fortfarande de tre senaste centrala dagboksinläggen, TODO och
arkitekturen vid start. Under **parallellt arbete** skriver varje arbetsspår
start och slut i en **egen ny loggfil**, exempelvis:

- `v2/kvarnbyn/worklogs/spel-2026-11-08-landningsglid.md`
- `v2/kvarnbyn/worklogs/karta-2026-11-08-krakan.md`

Det ersätter arbetsspårets direkta skrivning i de centrala statusdokumenten.
Integratören sammanför loggarna till DAGBOK/TODO/ARKITEKTUR/KRAVSPEC. På så sätt
blir inte varje liten spel- eller husändring en konflikt på samma rubriker.
Vid vanligt ensamarbete gäller den ordinarie dagboksrutinen.

Varje logg innehåller roll, uppgift, startcommit, reserverade filer, ändrade
gränssnitt, utförda prov, källor/antaganden, artifacternas sökvägar/hashar och vad
som återstår. Nya backloggidéer och föreslagna beslut skrivs där för integration.

## Så förs ändringarna ihop

1. Starta båda spåren från en känd godkänd commit och ange respektive ansvar.
2. Gör små, separata commits med spårets egen logg. Använd explicita filnamn vid
   staging; `git add .` kan fånga genererade data och en annan uppgifts filer.
3. Integratören tar en färdig ändring i taget till en integrationsgren från aktuell
   main. Läs överlämningen och diffen; sammanför källor, inte konkurrerande
   genererade kart-/speldata.
4. Återskapa genererade JSON-filer från de sammanförda källorna. Bygg eller välj
   rätt värld och exportera en gemensam spelapp. Kopiera inte den ena sidans gamla
   app ovanpå den andras och anta att ändringarna följt med.
5. Prova spelrörelse/vapen/AI och kartans ändrade gång-/kollisionsytor tillsammans.
   En ny värld behöver dessutom bildprov från relevanta platser. Krok och höga
   farter ska prövas där om en ny geometri påverkar dem.
6. Uppdatera centrala statusdokument och leveransmanifest. Bara integratören för
   den gemensamma versionen till main och uppdaterar Joels ordinarie Mac-app.

Spåren får spara/pusha sina egna arbetsgrenar. Den befintliga tillåtelsen att
pusha main används av integratören, inte av två parallella skrivare. Detta är en
arbetsfördelning, inte en garanti för att gränssnittsändringar aldrig behöver
samordnas.

## Kort uppdragsform

Ange **Spel** eller **Karta**, en avgränsad uppgift och önskad leverans. Exempel:
”Spel: justera fiendens eld och antal; använd senaste godkända värld” respektive
”Karta: förbättra Kråkans fasad och anslutande gångyta; behåll spelreglerna”.
Varje uppdrag får sin egen arbetskopia; integratören för ihop det färdiga arbetet.

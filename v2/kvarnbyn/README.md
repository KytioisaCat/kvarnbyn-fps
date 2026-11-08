# Försvara Kvarnbyn — aktiv datorversion

Blender bygger världen och modellerna, Godot 4.7.2 kör spelet med Forward+ och realtidsljus.
`../poc/torget/` är fryst material-/kitreferens. Äldre Three.js-kod är historik.

## Spela lokalt

Efter återbyggnad finns den uppackade Mac-appen här:

```sh
open "v2/kvarnbyn/desktop/app/Försvara Kvarnbyn.app"
```

WASD · mus · vänsterklick skjut · högerklick gripkrok · Q sikta · R ladda om · Shift spring · C huka ·
mellanslag hoppa/raketdubbelhopp · F flygtest · M karta · E prata · Esc paus.

**Gripkrok:** sikta på ett hus eller terrängen inom 42 m och håll **höger musknapp**. Kroken
vevar in automatiskt. Håll framåt + sidled för att bygga fart i en sving, hoppa
och släpp höger musknapp för att slungas vidare. Farten följer med genom släppet; fäst igen för
nästa båge. Efter landning bromsar du gradvis, med längre glid om du hukar.
Linan bryts om ett nytt hinder kommer emellan. Karta, paus och död släpper kroken.
Fartbygget är en avsiktlig feature med Prawn i Subnautica 1 som referens; se
projektets `KRAVSPEC.md`, ticket **RÖR-01**. Joels bedömning av känslan återstår.

**Finjustera själv:** tryck **Esc** för **Rörelse & gripkrok**. Fyra flikar har
24 reglage med exakta sifferfält och enheter: Gripkrok, Efter släpp, Gång & hopp
och Raket. Ändra ett reglage eller skriv ett tal, tryck Esc och prova. Dina värden
sparas lokalt mellan starter. **Återställ standard** ger tillbaka startvärdena;
**Kopiera värden** låter dig dela hela uppsättningen i chatten. **Övriga
inställningar** öppnar den tidigare menyn för bland annat bildkvalitet och ljus.
Fartmätaren kan slås av/på i rörelsemenyn och visar markfart även efter kroksläpp.

Nya standardvärden efter Joels prov: indragning **6 m/s** (tidigare 9),
dragacceleration **20 m/s²** (32), markbroms **3,5 m/s²** (9) och hukbroms
**1,5 m/s²** (4). Svingacceleration är fortsatt **19 m/s²**, farttak **30 m/s**
och luftmotstånd **0**. Alla dessa finns i menyn.

Minikartan följer dig med norr uppåt. Den stora kartan pausar spelet och visar
husen, ån, din riktning, zonerna och allierade. M eller Esc återgår till spelet.
Röd/blå ton visar läget kring zonerna; den streckade fronten följer ägarbyten.
Pilar visar möjliga förstärkningshåll medan fienden kan få fler soldater.
Pågående basanfall får gul varning i stora kartan.
Målpilen visar riktning och avstånd till nästa område. En pågående attack mot
den återtagna basen prioriteras med texten Försvara C.

**Civila på Gamla torget:** Lars Gahrn, Per Andersson, Ronny Jönsson och Linnea
Rönnqvist har egna stiliserade modeller, kroppstyper, civil klädsel och fem
animationer var. Lars är lång/mycket smal, Per normalbyggd, Ronny rundare med
mage och Linnea har en kvinnlig siluett. De promenerar korta sträckor, hälsar
och kan prata: titta på en person inom 3,8 m och tryck **E**. Replikerna är
påhittade för spelet. Vymenyn innehåller en genväg till varje person.

De är skyddade civila utan vapen och ingår inte bland stridsmål eller zontagare.
Ett vådaskott stoppas, personen reagerar och du får en civilvarning; inga blod-,
träffmarkörs- eller poängeffekter. Soldater håller inne skott när en civil skymmer.
Bildkällor/designobservationer: `reference/npc/selected-civilians-2026-11-08.json`.
Referensfotona används lokalt vid formgivning och ingår inte i spelets tillgångar.
Första modellerna är stiliserade versioner att förfina efter Joels spelprov.

**Gaturundor:** vymenyn har fem genvägar som börjar **Gaturunda**. Första passet
rättar tre lokala vägpartier vid Götaforsliden/Royens gata/Franckegatan,
13förstorade huskonturer och fyra fasader. Street View-referenser och osäkerheter
finns i `reference/vag-hus/README.md`. Det är ett delpass; stora delar av världens
fasader och tomter är fortfarande generiska eller uppskattade.

## Bygg om

Från repots rot: `v2/kvarnbyn/rebuild.sh`. Kräver projektets lokala Blender/Godot-verktyg
under `v2/.tools/`, Godots macOS-mall och Pythonmiljön `tools/venv/`. Kedjan tolkar data,
bygger mark/värld, bygger Ak 5/soldat/fyra civila, optimerar GLB, importerar, kör kontrollprov och
exporterar/packar upp Mac-appen. `--no-export` hoppar över appen; `--bot` kör även en hel botomgång.
Loggar finns i `evidence/`. Misslyckade bygge-/kontrollsteg avbryter kedjan.

**Agenternas tester är alltid tysta:** `--audio-driver Dummy`; testskript och automatiska
capture/bot/probe/walktest mutar dessutom masterbussen. Stäng inte andra Godot-processer.
Vanlig manuell spelstart har ljud.

Genererade GLB/.blend/exporter är lokala och gitignorerade. Soldatens lilla oförändrade
CC0-källa ligger i `assets-src/soldier/`, med licens och hash. Material/träd återanvänds
från det befintliga torget-provet.

## Resultat och nästa steg

- [Husstatus: långt ifrån färdigt](HUSSTATUS-2026-11-06.md)
- [Helskärmsflyt och kvarstående hack](RESULTAT-FLYT.md)

- [Botens rensningspatrull](RESULTAT-BOTPATRULL.md)

- [Basvakter efter förluster](RESULTAT-BASVAKTER.md)
- [Kartans frontläge och förstärkningshåll](RESULTAT-FRONT.md)
- [Forsens rörelse och skum](RESULTAT-FORS.md) — tre nya forsvyer i menyn
- [Målvisning och basvarning](RESULTAT-MALVISNING.md)
- [Norra åbanken och spelkartan](RESULTAT-NORRA-ABANKEN.md)
- [Senaste husprovet: M25 och entrégången](RESULTAT-M25.md)
- [Kvällsljus och gatlyktor](RESULTAT-KVALL.md) — välj Eftermiddag/Kväll i start- eller pausmenyn
- [Stalleliden och M30/M31](RESULTAT-STALLELIDEN.md)
- [Roten M 29](RESULTAT-ROTEN.md)
- [Soldater, vapen och torgförgården](RESULTAT-SOLDATER.md)
- [Fas B: spelregler och grundkänsla](RESULTAT-FAS-B.md)
- [Fas A: hela världen](RESULTAT.md)
- [Vapenmodell och verifiering](blender/AK5.md)
- [Soldatkälla och återbyggnad](assets-src/soldier/README.md)
- [Referenser och begränsningar för Roten M](reference/roten-m/OBSERVATIONER.md)

Läs alltid de tre senaste posterna i projektets `DAGBOK.md` före nästa pass.

Civilprov: `--headless --fixed-fps 60 --script res://scripts/verify_civilians.gd -- --no-pointer-lock --no-movement-profile` (alltid `--audio-driver Dummy`).
Samma 29 kontrollprov körs inuti exporterad app med `--civilian-export-check`.
`blender/build_civilians.py` skapar fyra separata GLB:er ur egen geometri/rigg/animation,
`civilian_roster.gd` äger placering/rörelse/repliker och `civilian_world.gd` interaktion/UI.

Gatu-/huskontroll: `tools/venv/bin/python v2/kvarnbyn/reference/vag-hus/verify_layout.py --glb v2/kvarnbyn/godot/assets/world.glb`.
Den färdiga appens ljudlösa `--road-export-check` provar golv, väggar och de tre
stråken med den riktiga spelarkapseln åt båda håll; kör med `--explore`,
`--no-pointer-lock`, `--no-movement-profile`, `--fixed-fps 60` och `--audio-driver Dummy`.

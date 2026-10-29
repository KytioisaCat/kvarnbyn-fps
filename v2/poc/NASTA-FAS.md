# Nästa fas efter PoC Gamla torget (beslutad 2026-10-29: Joel sa ja, Fas A körs först)

## Joels dom över PoC:n (2026-10-29)

*"Är den här typen av grafik det jag vill ha? Svar ja."* Med lite ljuseffekter för stämning och
skjutmekanik "är vi hemma". Fel finns men arbetssättet håller. **Målplattform: dator med mus och
tangentbord.** Telefonen är en kul bonus, inte poängen. Nästa önskan: en större värld, närmare
v1:s, till en spelbar version, och sedan förbättra miljön del för del, hus för hus.

## Tre beslut som styr allt

1. **Plattform: Godot som datorapp (Forward+), inte webben (Compatibility).** På datorn får vi
   det som ger stämning: SSAO, volymetrisk dimma, glow/bloom, bättre skuggor, SDFGI eller
   tätare ljuskartor. Samma projekt och samma Blender-innehåll; webbexporten finns kvar som
   bonus med enklare ljus. macOS först (Joels dator), Windows-export ur samma projekt.
2. **Världens storlek: 900 × 700 m spelbar zon (~370 hus), kulisser ut till v1:s gränser.**
   | Ruta kring Gamla torget | Hus i OSM | varav med våningstagg |
   |---|---|---|
   | 120 × 120 m (PoC) | 10 | 0 |
   | 600 × 500 m | 189 | 9 |
   | **900 × 700 m** | **370** | **9** |
   | 1 300 × 1 000 m | 713 | 25 |
   | hela v1 (3,2 × 2,2 km) | 3 460 | — |
   900 × 700 täcker torget, Götaforsliden, Kvarnbygatan, Royen, Forsåker, ån och broarna.
   Utanför: terräng + enkla husvolymer som kuliss, i låg detalj.
3. **Street View som referens, inte som texturer.** Google Maps villkor förbjuder att ladda ned
   eller skörda Street View-bilder och bygga innehåll av pixlarna, och spelet ligger publikt på
   GitHub Pages. Det som ger "rätt hus med rätt fasad" är *observationerna*: kulör, panelriktning,
   våningar, fönsterrytm, takform, skyltar — det Codex gjorde för Kråkan, Corpus och Musikskolan.
   Agenten tittar i Street View i webbläsaren, mappar mot ortofoto/OSM och skriver fakta i
   `city_spec.json`; utseendet byggs med kit + CC0-material. Joels egna foton får användas som
   pixlar om han vill.

## Fas A — större värld, automatisk tolkning — KLAR 2026-10-29 (`../kvarnbyn/RESULTAT.md`)

- `city_spec` för ~370 hus automatiskt: fotavtryck (OSM), **arketyp** ur form/storlek/läge
  (trävilla, arbetarbostad 1800-tal, lamellhus, tegelindustri, garage, kvarngård), takfärg och
  -form ur ortofotot, våningar ur arketyp + fotavtryck (punktmoln när `LM_USER`/`LM_PASS` finns).
  Varje värde märks *antagen* eller *observerad* — så syns vad som ska förbättras.
- Kit per arketyp (Codex `modelkit` utökas), LOD för hus långt bort, gator/terräng för hela zonen.
- Godot desktop: Forward+, ljuskartor i delar (eller SDFGI), prestandamätning.
- **Klart när:** man kan gå runt i hela zonen på datorn, allt har ett rimligt hus, inget är lådor.

## Fas B — spelbart — KLAR 2026-10-29 (`../kvarnbyn/RESULTAT-FAS-B.md`)

Porta v1:s spel till Godot: vapen (hitscan, rekyl, ammo, **reload**), **hopp**, fiender med
navmesh och AI, zonerna med capture points, HUD, ljud. **Joel 2026-10-29: v1 är facit för
*funktionerna* (fiender, vapen, reload, hopp m.m. ska med), men INTE för känslan** — han tyckte
inte att v1:s känsla satt. Känslan (rörelse, vapentyngd, ljud, träffåterkoppling) designas om
mot moderna FPS-referenser. **Klart när:** en runda går att spela från start till seger/förlust.

## Fas C — iterera (löpande, när det finns tokens)

- Stämning: kvällsljus, gatlyktor som lyser, dimma i åravinen, bloom.
- **Husrundor**: 5–10 hus per runda, Street View-observation → `city_spec` → bygg om → jämförbild.
  Hjältehus och husen längs huvudgatorna först.

## Arbetssätt

Ett pass = en brief här i `v2/poc/`, avslutas med `RESULTAT.md`, bilder och dagboksinlägg.
`rebuild.sh` måste fortsätta fungera efter varje pass. Stora genererade filer committas inte.

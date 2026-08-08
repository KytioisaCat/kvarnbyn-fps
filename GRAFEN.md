# Kunskapsgrafen — hur den används och underhålls

Grafen i `graphify-out/` är ett **index över projektet**, byggt med
[graphify](https://github.com/safishamsi/graphify). Syftet är billig navigering: att
svara på "var bor X" och "vem anropar X" för ett par kilobyte kontext i stället för att
läsa 3 000 rader `game.js`.

Detta dokument är projektets egna regler. Det är **fristående** — det ärver inga regler
från globalt installerade skills eller andra projekt, och gäller bara detta repo.

## Grundregeln

> **Grafen är ett index, aldrig facit. `public/game.js` är sanningen.**

Grafen kan vara inaktuell, sakna kanter och innehålla gissningar (kanter märkta
`INFERRED`/`AMBIGUOUS` är just gissningar). Fatta aldrig ett beslut och skriv aldrig
kod enbart på grafens ord — använd den för att *hitta rätt ställe*, läs sedan filen.

## Vad grafen innehåller

Två lager med helt olika ekonomi. Skillnaden styr allt underhåll:

| Lager | Innehåll | Kostnad | Byggs om |
|---|---|---|---|
| **AST** | Alla funktioner i `game.js` och `tools/*.py` + anropskanter | Gratis, deterministisk, ~2 sekunder | Så ofta du vill |
| **Semantiskt** | Arkitekturbeslut och motiv ur ARKITEKTUR.md, KRAVSPEC.md m.fl. | LLM — dyrt (~130 k tokens och ~10 min för dokumenten) | Bara när dokumenten ändrats materiellt |

Kända luckor (var ärlig om dessa i stället för att lita blint):

- Det semantiska passet över **koden** kördes aldrig — anropskanter finns via AST, men
  "vilka funktioner hör konceptuellt ihop" saknas för `game.js` och pipelinen.
- Några filer saknar semantisk extraktion (rebuild-skriptet listar dem vid varje körning).

## Fråga grafen — kommandona

Alla verifierade i detta repo:

```bash
graphify explain "planEscape"                  # vad är det, fil:rad, vem anropar det
graphify affected "heightAt()" --depth 1       # vad påverkas om jag ändrar detta
graphify path "updateEnemy()" "heightAt()"     # hur hänger två saker ihop
graphify query "hur fungerar brosystemet"      # bredare kontext kring ett ämne
```

**Läs aldrig in `graph.json` eller `GRAPH_REPORT.md` i kontexten.** De är byggda för att
frågas, inte läsas — och rapporten växer med grafen. Öppna gärna `graphify-out/graph.html`
i webbläsaren om du är människa och vill se strukturen visuellt.

## När ska grafen användas — och när inte

**Fråga grafen först** när du:

- letar efter var något bor ("var sätts fallskadan?")
- vill veta vad som påverkas av en ändring (`affected` före en refaktorering)
- orienterar dig i ett område du inte rört på länge
- vill förstå varför ett beslut fattades (det semantiska lagret bär motiven)

**Hoppa över grafen och gå direkt till filen** när du:

- ska **ändra** kod — läs alltid den riktiga koden före en edit
- felsöker konkret beteende (grafen vet inte vad som händer i runtime)
- redan vet exakt var du ska (`grep` är snabbare för en känd sträng)
- arbetar i ett område du precis ändrat i denna session — då är grafen per definition
  gammal

## Bygg om grafen

### Efter kodändringar (gratis, kör gärna ofta)

```bash
python3 tools/rebuild_graph.py && graphify export html
```

Cirka två sekunder, noll tokens. Parsar om AST-lagret och återanvänder det semantiska
lagret ur `graphify-out/cache/`. Rimlig vana: kör det när en session lagt till, döpt om
eller tagit bort funktioner — inte efter varje liten redigering.

> ### ⚠️ Kör INTE `graphify update .` i detta repo
>
> Det bara kommandot skannar hela trädet och drar in `public/three.module.js`
> (vendorerat Three.js, ~2 300 symboler) och `public/data.js` (4 MB genererad kartdata).
> Grafen svällde i test från 247 till **2 562 noder** och 186 communities — vår egen kod
> dränktes i brus, community-namnen slogs sönder och `graph.json` växte till 2,4 MB.
> `tools/rebuild_graph.py` finns just för att hålla urvalet kurerat.
>
> Skulle det ändå hända: graphify tar automatiskt en backup i `graphify-out/<datum>/` —
> kopiera tillbaka `graph.json`, `GRAPH_REPORT.md`, `manifest.json` och
> `.graphify_labels.json` därifrån, och kör sedan rebuild-skriptet.

### Efter dokumentändringar (kostar tokens — planera)

Det semantiska lagret täcker ARKITEKTUR.md, KRAVSPEC.md, CLAUDE.md, TODO.md, DEPLOY.md
och README.md. Kör bara om när innehållet ändrats **materiellt** — nya arkitekturbeslut
eller ny kravbild, inte när en TODO-rad bockats av.

```
/graphify . --update
```

Regler för den körningen:

1. **Säg först vad det kostar och hur lång tid det tar.** Erfarenhet från bygget:
   elva markdown-filer tog ~11 minuter och ~130 k tokens i en subagent, helt tyst under
   tiden. Att starta det utan förvarning ser ut som att sessionen har hängt sig.
2. **Sätt `GEMINI_API_KEY` om kostnaden ska bort från sessionen** — då kör graphify
   extraktionen mot Gemini i stället för via Claude-subagenter.
3. **Kör inte mitt i annat arbete.** Gör det som en egen uppgift, inte som ett sidospår
   i en feature.
4. `--update` extraherar bara om filer som ändrats (hashar i `manifest.json`), så det är
   billigare än ett fullt bygge.

### Om filurvalet ändras

Nya källfiler eller dokument läggs till i listorna högst upp i `tools/rebuild_graph.py`.
Håll genererat, vendorerat och binärt material **utanför** — det är hela poängen med det
kurerade urvalet.

## Vad som versionshanteras

Committas (så nya sessioner har grafen direkt): `graph.json`, `graph.html`,
`GRAPH_REPORT.md`, `manifest.json`, `cost.json`.
Ignoreras (lokalt): `graphify-out/cache/` och `graphify-out/.graphify_*`.

Cachen ligger lokalt, vilket betyder att `tools/rebuild_graph.py` på en **ny maskin**
tappar det semantiska lagret tills `/graphify . --update` körts en gång. AST-lagret
byggs alltid om gratis.

## Community-namnen

Klustren har svenska namn (t.ex. "Rendering, kollision & soldater") som ligger hårdkodade
i `tools/rebuild_graph.py`. Nya kluster får platshållaren `Community N` — döp om dem i
skriptet när de dyker upp, annars tappar rapporten sitt värde.

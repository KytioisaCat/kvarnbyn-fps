# Försvara Kvarnbyn — projektinstruktioner

**Läs `TODO.md` först** vid varje sessionstart — den är projektets backlogg och
statusminne. Bocka av utfört arbete där (flytta till Klart med datum) och lägg
nya idéer i backloggen i stället för att hålla dem i huvudet.
**Läs sedan `ARKITEKTUR.md`** — arkitektur, datakällor/licenser, gameplay-design
och beslutslogg med motiv (varför saker är som de är). Uppdatera den när nya
beslut fattas eller gamla omprövas.

## Vad detta är

Joels barndoms-FPS: försvara Kvarnbyn i Mölndal mot en invasion, byggt på riktig
kartdata. Ledstjärnan är **igenkänning** — Joel ska känna igen sig från barndomen.
Realism slår alltid teknisk elegans; svenska i all speltext och UI.

## v2 — ny motor (från 2026-10-21) — OBS: omstart 2026-10-22, läs `OMSTART.md` först

**2026-10-22**: Joel underkände v2:s sätt att rita rådata (terräng + vägband + flats). Ny approach
i `OMSTART.md`: tolka datan till en stadsbeskrivning, bygg världen med riktig motor, vägverktyg,
arketyp-kit och Lantmäteriets punktmoln. Bygg inte vidare på `v2/src` eller `tools/v2model/`
som produkt. Stycket nedan är historik tills OMSTART-planen ersätter det.

**Allt nytt arbete sker i `v2/`** (Three.js + TypeScript + Vite) och byggs **lokalt på Joels
laptop**; Joel bedömer det visuella på telefonen via GitHub Pages. (Molnsessioner provades
2026-10-21 och föll på att Consats Claude-org saknar GitHub-connectorn — föreslå dem inte igen.)
Läs **`v2/PLAN.md`** först i varje v2-session: teknikval, delmål, arbetssätt. `public/` är
**v1, fryst som referens/facit** — läs `public/game.js` för kalibreringar och beteenden, men
ändra aldrig där (undantag: om Joel uttryckligen ber om en v1-hotfix). Pipelinen i `tools/`
delas; v2:s exportsteg är `tools/build_v2.py` → `v2/public/data/`. Regler: pusha till `main`
vid varje delmål, `npm run build` måste gå igenom före push (varje push deployar), smoke-testa
i preview men låt Joel bedöma det visuella på telefonen. **Laptopen har mätt uppkoppling** —
fråga före `npm install`/nedladdningar och säg storlek.

## Struktur

- `v2/` — **nya motorn** (Vite/TS/Three.js); deployas under `/v2/`; plan i `v2/PLAN.md`
- `public/` — **v1**, hela gamla spelet, statiska filer utan byggsteg (fryst referens, deployas på roten)
  - `game.js` — all spellogik/rendering (Three.js, vendorerad `three.module.js`)
  - `data.js` — genererad kartdata (terräng, hus med takfärger + OSM-id/husfakta-taggar, vägar
    med OSM-id, murar, landmärken)
  - `flats.js` — genererade byggda plana ytor + brokedjor (med OSM-way-id:n)
  - `husfakta.js` — handförfattat: hur enskilda hus ser ut (farg/vaningar/tak/material/skylt)
  - `ortho.jpg` — Lantmäteriets ortofoto 0,16 m (CC BY 4.0), lat/lon-linjärt
- `tools/lidar_1m.png` + `lidar_meta.json` — LiDAR 1 m som 16-bit PNG (committad källa;
  `lidar_png.py pack/unpack`), `tools/osm_raw.json` — OSM-extraktet (committat) → pipelinen går i
  vilken klon som helst utan Lantmäteriet
- `tools/` — Python-datapipeline (OSM Overpass → terräng-tiles → ortofoto → `data.js`);
  venv i `tools/venv/`. Ordning: `bbox.py` (bbox = enda sanningen) → `fetch_tiles.py` →
  `fetch_ortho*.py` → `fetch_lidar.py` → `build_classmap.py` → `build_data2.py` → `build_flats.py`;
  `husfakta_lista.py` ger kandidatlistan för husfakta
- `.github/workflows/deploy.yml` — push till `main` deployar `public/` till GitHub Pages

## Arbetsflöden

- **Hitta i koden — fråga grafen först, läs filen sen.** `graphify-out/` är ett index
  över projektet (~245 noder: funktionerna i `game.js` + pipelinen, plus besluten ur
  ARKITEKTUR.md/KRAVSPEC.md). Kostar ett par kB kontext i stället för 3 000 rader:
  ```bash
  graphify explain "planEscape"                 # vad är det, fil:rad, vem anropar det
  graphify affected "heightAt()" --depth 1      # vad påverkas om jag ändrar detta
  graphify query "hur fungerar brosystemet"     # bredare kontext kring ett ämne
  ```
  Tre regler: **läs aldrig in `graph.json`/`GRAPH_REPORT.md` i kontexten** (fråga dem);
  **läs alltid den riktiga filen innan du ändrar** — grafen är index, `game.js` är facit;
  **kör aldrig `graphify update .`** (drar in three.module.js + data.js och sväller grafen
  10×) — använd `python3 tools/rebuild_graph.py` som är gratis och kurerad.
  Fullständiga riktlinjer inkl. när det semantiska lagret ska byggas om: **`GRAFEN.md`**.
- **Kör lokalt:** v1: `python3 -m http.server 8763 --directory public`; v2: `cd v2 && npm run dev`
  (port 5187). Båda finns i `.claude/launch.json` (`kvarnbyn` resp. `v2`)
- **Testa i preview:** rAF sover i headless — stega spelet med debughookarna
  `window.__frame(dt)`, `window.__game`, `window.__look(yaw,pitch)`, `window.__fire()`.
  Starta via klick-event på `#overlay` (preview_click når inte lyssnaren; använd
  `dispatchEvent(new MouseEvent('click',{bubbles:true}))`)
- **Cache:** webbläsaren cachar aggressivt — bumpa `?v=N` på `data.js`/`game.js`/`flats.js`/
  `husfakta.js` i `index.html` vid varje ändring av dem
- **Geometri-/gångytefel:** felsök med proben, inte ögat — `__game.groundInfoAt/bridgeChains/
  roadSegs` är exponerade; gå 1 m-steg längs vägar/kedjor med refY-spårning och räkna hopp
  (recept i ARKITEKTUR.md under Broar)
- **Deploy:** committa + pusha till `main` (Joel har godkänt push); workflowen bygger v2 och lägger
  v1 på roten, v2 under `/v2/`; sajten: https://kytioisacat.github.io/kvarnbyn-fps/ (v2:
  https://kytioisacat.github.io/kvarnbyn-fps/v2/) — repo: KytioisaCat/kvarnbyn-fps
  (Joels privata GitHub-konto, INTE jobbkontot; aldrig GitLab)

## Fällor (dyrt inlärda)

- OSM-vattenpolygoner måste vara slutna ringar — öppna strandlinjer trianguleras
  till jättepolygoner över hela kartan
- Terrängmeshens trianglar ska vara CCW sedda uppifrån, annars backface-cullas allt
- Höjder: `heightAt` = nedskuren terräng ×1,2 (EXAG, LiDAR 2 m-grid); `origHeightAt` =
  före åfåran; `groundInfoAt` = mark + vägdäck (broar!) — använd rätt för rätt sak
- Branthetsspärren mäter med 1,6 m lookahead, aldrig per frame-steg (för brusigt);
  vägar/trappor alltid gångbara (road-exempt), spärr 0,60 / tung klättring 0,38
  (Royens trappor 0,61 längs linjen — därför måste trappor vara exempta)
- Kulor/siktlinjer använder analytisk ray-march (`pointBlocked`), inte trianglar —
  nya hinder måste in i respektive spatial hash (`bldHash`/`wallHash`/`obstHash`)
- Aldrig inloggningsuppgifter/API-nycklar i chat, repo eller filer — miljövariabler
  som Joel sätter själv (t.ex. LM_USER/LM_PASS för Lantmäteriet)

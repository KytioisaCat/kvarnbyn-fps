# Försvara Kvarnbyn — projektinstruktioner

**Läs `TODO.md` först** vid varje sessionstart — den är projektets backlogg och
statusminne. Bocka av utfört arbete där (flytta till Klart med datum) och lägg
nya idéer i backloggen i stället för att hålla dem i huvudet.

## Vad detta är

Joels barndoms-FPS: försvara Kvarnbyn i Mölndal mot en invasion, byggt på riktig
kartdata. Ledstjärnan är **igenkänning** — Joel ska känna igen sig från barndomen.
Realism slår alltid teknisk elegans; svenska i all speltext och UI.

## Struktur

- `public/` — hela spelet, statiska filer utan byggsteg
  - `game.js` — all spellogik/rendering (Three.js, vendorerad `three.module.js`)
  - `data.js` — genererad kartdata (terräng, hus med takfärger, vägar, murar, landmärken)
  - `ortho.jpg` — Lantmäteriets ortofoto 0,16 m (CC BY 4.0), lat/lon-linjärt
- `tools/` — Python-datapipeline (OSM Overpass → terräng-tiles → ortofoto → `data.js`);
  venv i `tools/venv/`. Ordning: `fetch_tiles.py` → `fetch_ortho*.py` → `build_data2.py`
- `.github/workflows/deploy.yml` — push till `main` deployar `public/` till GitHub Pages

## Arbetsflöden

- **Kör lokalt:** `python3 -m http.server 8763 --directory public` (finns i `.claude/launch.json`)
- **Testa i preview:** rAF sover i headless — stega spelet med debughookarna
  `window.__frame(dt)`, `window.__game`, `window.__look(yaw,pitch)`, `window.__fire()`.
  Starta via klick-event på `#overlay` (preview_click når inte lyssnaren; använd
  `dispatchEvent(new MouseEvent('click',{bubbles:true}))`)
- **Cache:** webbläsaren cachar aggressivt — bumpa `?v=N` på `data.js`/`game.js`
  i `index.html` vid varje ändring av dem
- **Deploy:** committa + pusha till `main` (Joel har godkänt push); sajten:
  https://kytioisacat.github.io/kvarnbyn-fps/ — repo: KytioisaCat/kvarnbyn-fps
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

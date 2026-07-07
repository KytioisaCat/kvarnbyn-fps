# Publicera Försvara Kvarnbyn

Allt är förberett lokalt: git-repo med första commit, `.gitignore` och en
GitHub Actions-workflow (`.github/workflows/deploy.yml`) som deployar `public/`
till GitHub Pages vid varje push till `main`.

**Föreslaget repo-namn:** `forsvara-kvarnbyn` (alternativ: `kvarnbyn-fps`).

## 1. Skapa repot och pusha

Kräver [GitHub CLI](https://cli.github.com/) (`brew install gh`) och inloggning (`gh auth login`).

```bash
cd ~/Workspace/kvarnbyn
gh repo create forsvara-kvarnbyn --public --source=. --push
```

Det skapar repot under ditt konto, sätter `origin` och pushar `main`.

## 2. GitHub Pages aktiveras automatiskt

Workflown använder `actions/configure-pages` med `enablement: true`, så Pages
slås på av sig själv vid första körningen (källa: *GitHub Actions*). Följ första
deployen med:

```bash
gh run watch
```

Om första körningen mot förmodan skulle faila på Pages-aktivering, aktivera
manuellt och kör om:

```bash
gh api "repos/{owner}/forsvara-kvarnbyn/pages" -X POST -f build_type=workflow
gh workflow run deploy.yml
```

(eller via webben: **Settings → Pages → Source: GitHub Actions**)

## 3. Spela

Förväntad URL (ersätt `ANVANDARNAMN` med ditt GitHub-användarnamn):

```
https://ANVANDARNAMN.github.io/forsvara-kvarnbyn/
```

Alla sökvägar i spelet är relativa, så det fungerar direkt under underkatalogen.
Varje ny push till `main` deployar om automatiskt.

## Licens och attribution

Spelet blandar egen kod med tredjepartsdata — därför ligger ingen enkel
LICENSE-fil i roten ännu. Läget per komponent:

| Komponent | Källa | Licens | Status |
|---|---|---|---|
| `game.js`, `index.html`, `tools/` | Egen kod | Ditt val | OK |
| `public/three.module.js` | three.js r160 | MIT | OK — licensheadern ligger kvar i filen |
| `public/data.js` (byggnader, vägar m.m.) | OpenStreetMap via Overpass | ODbL 1.0 | OK — attribution finns i spelet (`index.html`) och i README |
| Höjddata i `data.js` | AWS Terrain Tiles (terrarium) / Copernicus EU-DEM | Fri med attribution | OK — attribution finns |
| `public/ortho.jpg` | Esri World Imagery-tiles (hopsydda) | Esris villkor | **Problem — se nedan** |

### ortho.jpg — Esri World Imagery

Esris villkor ger **ingen rätt att ladda ner, lagra och vidaredistribuera**
tiles från standardlagret World Imagery. Export är bara tillåten via det
särskilda lagret "World Imagery (for Export)", och även då enbart för användning
**inom ArcGIS-appar**. Att checka in den hopsydda `ortho.jpg` i ett publikt repo
och servera den från en publik sajt är alltså inte en gråzon utan ett
villkorsbrott, även med attribution.

**Rekommenderat alternativ (bäst):** byt till **Lantmäteriets Ortofoto
Nedladdning** — öppna data under **CC BY 4.0** sedan februari 2025, hämtas via
STAC-API, och har dessutom *högre* upplösning (0,16 m/px mot Esris ~0,3 m/px
på z18). Då är bilden tveklöst fri att redistribuera; uppdatera
`tools/fetch_ortho.py` och attributionsraden ("© Lantmäteriet, CC BY 4.0").

**Alternativ 2:** hämta Esri-tiles i klienten vid runtime (så basemappen är
tänkt att användas, med attribution) i stället för att distribuera en bakad
bild. Nackdelar: tekniskt sett kräver Esris nuvarande villkor åtkomst via
ArcGIS-plattformen (API-nyckel, gratisnivå finns), och pipelinen samplar
takfärger ur bilden vid byggtid — det steget försvinner.

**Alternativ 3 (snabbast, tillfälligt):** publicera utan `ortho.jpg` (grå/enfärgad
terräng som fallback) tills Lantmäteriet-bytet är gjort.

Obs: takfärgerna i `data.js` är samplade ur Esri-bilden vid byggtid. Enstaka
medianfärgvärden per byggnad är i praktiken försumbart, men bygger du om datan
mot Lantmäteriet-fotot försvinner även den fotnoten.

### Vad du bör välja som licens

- **Egen kod:** MIT är det naturliga valet för ett hobbyspel (enkelt, tillåtande,
  matchar three.js). Lägg då en `LICENSE`-fil med MIT-texten men **skriv uttryckligen
  att den bara gäller den egna koden**, t.ex. en rad i README/LICENSE:
  "Koden är MIT. Kartdata i `data.js` är © OpenStreetMap-bidragsgivarna (ODbL).
  three.module.js är MIT © Three.js Authors."
- **Lägg inte en enda repo-täckande licens** rakt av — `data.js` är en bearbetning
  av OSM-data och förblir ODbL oavsett vad du skriver, och `ortho.jpg` kan du
  inte licensiera alls (den är Esris).
- Behåll attributionsraden i spelet (`index.html`) — den uppfyller ODbL- och
  Copernicus-kraven; byt Esri-delen när ortofotot byts.

## Källor (Esri/licens)

- [Esri World Imagery Uses Permitted](https://www.arcgis.com/home/item.html?id=8e90a00a0a6845a49262e0b756f57a10)
- [World Imagery (for Export)](https://www.arcgis.com/home/item.html?id=226d23f076da478bba4589e7eae95952)
- [Esri Web Site and Service Terms of Use](https://www.esri.com/en-us/legal/terms/web-site-service)
- [Lantmäteriet — Öppna data](https://www.lantmateriet.se/oppnadata)
- [Lantmäteriet — Ortofoto Nedladdning](https://www.lantmateriet.se/sv/geodata/vara-produkter/produktlista/ortofoto-nedladdning/)

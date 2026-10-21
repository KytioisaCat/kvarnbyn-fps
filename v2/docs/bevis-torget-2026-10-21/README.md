# Bevis 2026-10-21: Mölndals bro + vägnätet runt Gamla torget, byggt offline

Första körningen av metoden i `VISION.md` §3b: en offline-modell i Python (`tools/v2model/`)
som bygger vägnätet som geometri ur OSM + LiDAR, med en global profil-lösare, terräng-
konformering och mätgrindar. Inget är lappat i webbläsaren. Webbläsaren renderar bara.

Område: x −680…260, z −260…160 (Gamla torget, Forsebron, Mölndals bro, rondellen vid
Broplatsen, E6/Göteborgsvägen under bron). 562 kanter, 72 brokanter, 24,7 km väg.

## Mätgrindar — alla gröna

Se [report_torget.md](report_torget.md). Sammanfattat:

| Grind | Värde | Gräns |
|---|---|---|
| Maxlutning överskriden (körväg, ej trappor) | 1,1 %-enheter | 3 |
| Bula körväg per 4 m | 0,15 m | 0,20 |
| Bula gångväg per 4 m (ej trappor) | 0,43 m | 0,50 |
| Fri höjd över korsad väg, minst | 4,54 m | 4,5 |
| Vanlig väg mot LiDAR, p90 | 0,13 m | 0,6 |
| Brodäck över mark, minst | 0,44 m | 0,3 |
| Terräng över vägyta inne i asfalt, max | 0,03 m | 0,05 |
| Terräng över kantstenskrön, p99 | 0,00 m | 0,03 |
| Terräng under kantstenskrön, p99 | 0,36 m | 0,5 |

Grinden "terräng över kantstenskrön" listar sina tre värsta ställen (0,93 m vid (132, −233)
osv.) — det är **stödmurar som saknas i modellen**, kandidatlistan för M3.

## Längsprofil Mölndals bro

![profil](profil_molndals_bro.png)

Brun = LiDAR-marken (×1,2), röd = det lösta brodäcket. Däcket ligger 10–15 m, faller 4 m
från Kvarnbyn-sidan ned mot Broplatsen med högst 5,5 % lutning, och håller ≥ 5,4 m fri höjd
över Göteborgsvägen och E6. Ingen "+6 m i knutar", inget "grannens däckhöjd": däcket är
resultatet av villkoren fri höjd, jämnhet och landfästen = mark.

## Bilder (renderade i v2, headless)

| | |
|---|---|
| ![](01-dacket-vasterut.jpg) På däcket, västerut. Plan väg, kantsten, räcken. | ![](02-under-bron-goteborgsvagen.jpg) Under bron från Göteborgsvägen: däckkropp, pelare, räcke, bank. |
| ![](03-rondellen-uppifran.jpg) Rondellen vid Broplatsen rakt uppifrån — en sammanhängande struktur, inte v1:s "öar". | ![](04-bron-fran-luften.jpg) Bron från luften: Mölndals bro över E6 och Göteborgsvägen. |
| ![](05-torget-fran-luften.jpg) Gamla torget från luften: gator med kantsten. Själva torget är ännu terräng (flats = nästa steg). | ![](06-dacket-fran-kvarnbynsidan.jpg) Däcket från Kvarnbyn-sidan. |

## Vad som är gjort i metoden (jämfört med v1)

- **Offline, i Python** (`tools/v2model/`): `network.py` (graf ur OSM, delning vid delade noder,
  nodning av korsningar utan OSM-nod), `profile.py` (global minsta-kvadrat med aktiv mängd:
  markband ±0,6 m, jämnhet inom och ÖVER noder, maxlutning per klass, fri höjd per klass,
  däck över mark, tunnlar under mark, trappor som struktur, trottoar bunden till gatan),
  `mesh.py` (band per kant, korsningspolygoner som komplement, kantsten med kjol, brodäck per
  sammanhängande grupp med sidor/undersida/räcken/pelare), `conform.py` (terrängen räknas om
  inne i och runt vägarna), `report.py` (grindar + profilbild), `build.py`.
- **Villkor, inte lappar.** Varje bro är kanter med `layer=1` och ett villkor till. Rondellen
  och Broslättsgatans bro blev rätt först när en brogrupp behandlades som EN struktur
  (jämnhet över noder mellan brokanter) — exakt det v1 aldrig hade.
- **Mätgrindar stoppar bygget.** Under kvällen bröts i tur och ordning: korsad väg trycktes
  ner i stället för att bron lyftes (ensidigt villkor), tunnelstig under bro krävde fri höjd
  (uteslut tunnlar), gångstig 2 m från gatan ägde gatans höjd (ägarpolygon med prioritet),
  rondellens kantbitar var öar (jämnhet över noder). Alla syntes i rapporten innan de syntes
  i bild.

## Vad som INTE är gjort

- **Flats** (torget, parkeringar) — nästa steg: plan + kantsten + konformering med samma maskineri.
- **Stödmurar** där terrängen hamnar > 0,3 m över kantstenen (listan i rapporten).
- **Hela kartan**: lösaren är tät numpy (7 000 okända på 7 s); hela kartan kräver gles lösare
  (scipy, ~35 MB nedladdning) eller områdesvis lösning med överlapp.
- **Spelaren går inte på däcken** ännu (terrängklamp) — `__fly` användes för bilderna. M5.
- **Material**: enfärgad asfalt/betong; riktiga texturer och markeringar kommer med material-steget.
- Tunnelportaler ritas inte (tunnelstigen döljs).

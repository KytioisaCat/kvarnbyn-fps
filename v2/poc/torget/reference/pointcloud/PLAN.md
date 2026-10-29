# Separat punktmolnsprov — status 2026-10-29

**Rådata kunde inte hämtas i denna körning.** De redan avsedda miljövariablerna `LM_USER`
och `LM_PASS` var båda osatta. Den officiella råfilens endpoint svarade **HTTP 401** på
ett anrop utan inloggning. Inga nya kontosteg, inloggningar eller beställningar genomfördes.
Ingen rå laserdata laddades ned och inga hustak har mätts i punktmoln.

## Exakt identifierad datakälla

| Fält | Verifierat värde |
|---|---|
| API | `https://api.lantmateriet.se/stac-hojd/v1` |
| STAC-kollektion | `dsm-skoglig-copc` (Laserdata Skog) |
| Ny ruta | `19b002-63925_3225_25`, 2,5×2,5 km |
| Fil | `y19b002-63925_3225_25.copc.laz` |
| Storlek | **90 989 680 byte**, cirka 91 MB / 86,8 MiB |
| Antal punkter | 16 536 359 |
| Skanningsdatum | 2019-11-29 till 2019-11-30 |
| Nominell punkttäthet | 1,2 punkter/m² enligt `punkttathet` |
| Plan/höjd | SWEREF 99 TM + RH2000, EPSG:5845 |
| Rutgränser | öst 322500–325000 m; nord 6392500–6395000 m |
| Filens senaste uppdaterade metadata | 2026-10-14 |
| Åtkomsttest | metadata HTTP 200; råfil utan auth HTTP 401 |
| Nedladdad rådata | **0 byte** |

Sökningen använde provrutans WGS84-bbox:
`[12.02679261,57.65636101,12.02880739,57.65743899]`.

Öppen sökning via POST till `/search`, med JSON:

```json
{"bbox":[12.02679261,57.65636101,12.02880739,57.65743899],"limit":100}
```

Den gav tre träffar: markmodellen, den äldre 10 km-punktmolnsrutan och den nya 2,5 km-rutan.
**Välj den nya lilla rutan**, som håller sig under uppdragets 200 MB-gräns.
`search.json`, `collections.json` och `tile_info.json` är sparad offentlig metadata.
`STATUS.json` är den korta maskinläsbara statusen. Inga inloggningsuppgifter finns i filerna.

[Officiell råfil](https://dl1.lantmateriet.se/hojd/data/pointcloud/sls/19b002/y19b002-63925_3225_25.copc.laz).
[Öppen filmetadata](https://dl1.lantmateriet.se/hojd/pub/pointcloud/sls/19b002/y19b002-63925_3225_25_info.json).

## Korrigering jämfört med den gamla projektplanen

- Lantmäteriet meddelade 20 oktober 2026 att COPC-indexfelet har rättats och rutindelningen
  åter är 2,5 km. Den lokala API-sökningen bekräftar att både gammal och ny ruta syns för platsen.
- Laserdata Skog ska **inte märkas CC0**. De officiella villkoren 2026-05-20§3.1 anger
  **CC BY 4.0** och anger hur källa, Lantmäteriet och bearbetning ska redovisas.
  Detta gäller den här laserprodukten; det ändrar inte automatiskt licensetiketten på vår
  tidigare anskaffade markmodell eller ortofoto.

Källor:
[Produktdokumentation](https://geotorget.lantmateriet.se/dokument/projects/laserdata-nedladdning-skog-api/released/1/),
[Lantmäteriets produktnyheter](https://www.lantmateriet.se/produktnyheter),
[användningsvillkor](https://www.lantmateriet.se/globalassets/geodata/geodataprodukter/anvandningsvillkor-for-laserdata-nedladdning-skog.pdf).

## Återuppta när befintlig behörighet finns i miljön

`resume_download.py` använder enbart redan satta miljövariabler. Utan dem stoppar det med
exitkod2, före autentiserad åtkomst eller nedladdning. Skriptet beställer inte behörigheter.

```sh
python3 v2/poc/torget/reference/pointcloud/resume_download.py
```

Skriptet kontrollerar den granskade filstorleken, 200 MB-taket och STAC:s SHA256-checksumma.
Filen sparas enbart under `data/downloads/`, där rådata är gitignorerad.
Inga paket har installerats i det här provet. Vid återupptagen mätning räcker normalt
`laspy` + `lazrs` och befintlig Pythonmiljös numpy/shapely/rasterio, utan någon ny motor.

## Avgränsat mätprov: åtta hus

Mätmål: w92331981 (Kråkan, uppdelad i 3 takvolymer), w92332103 (Corpus), w92332122 (Musikskolan),
w92332096 (tegelhuset), w92332039, w92332089, w629220976 och w629220977.

1. Transformera husfotavtrycken från WGS84 till SWEREF 99 TM(EPSG 3006), med explicit
   X=öst/Y=nord. LAS/COPC-höjder är RH2000 och ska jämföras med vår råa markmodell, utan EXAG.
2. Läs filen i chunkar och klipp till hela provrutan +10 m marginal. Behåll punkternas klass,
   returinformation och absolut Z. Punktmolnet är från 2019, medan referensbilderna är från 2026.
3. Klipp huskandidater till fotavtryckets indragna polygon. Skilj markklass från oklassade
   objekt och byggnadspunkter. Oklassat betyder **inte automatiskt hustak**; även träd finns där.
4. För varje separat takvolym: redovisa antal kandidater, marktäckning, robust Z-fördelning
   och eventuella plan som klarar RANSAC med rimlig residual. Skorstenar, trädkronor och
   enstaka högsta punkter får inte bli nockhöjd.
5. Rapportera sadel/valm/platt endast när flera takplan faktiskt stöds av punkterna.
   Nockriktning behöver motstående takplan och jämförelse med ortofoto. Saknas stödet ska
   resultatet vara **okänt/låg säkerhet**. En percentil är inte i sig en inmätt takfot.
6. Jämför punktmolnets råhöjder och siluetter mot de manuella referenserna innan något ändras
   i byggmodellen. Rapportera till root separat; skriv inte över `city_spec.json` automatiskt.

En användbar resultatrad ska minst innehålla `osm_id`, `volume_id`, `point_count`,
`ground_height_raw_m`, `roof_height_range_raw_m`, `fitted_planes`, `residual_m`,
`coverage`, `roof_shape`, `confidence` och `limitations`.

Trädposition/höjd kan undersökas senare. Någon säker artbestämning från det här glesa
punktmolnet ingår inte och är inte bevisad.

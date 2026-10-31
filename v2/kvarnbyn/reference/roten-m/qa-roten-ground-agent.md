# Oberoende CPU-QA — Roten M29

**Status:** klart 2026-10-31. Samtliga modulprov, materialskarvar, täta gångprofiler och
staketets höjdprov är gröna. Maskinläsbart resultat och källhash finns i
`qa-roten-ground-agent.json`. Faktisk Blender-/Godot-verifiering redovisas separat i
`../../RESULTAT-ROTEN.md`.

Kontrollen gäller modulens data och gränssnitt. Inga Blender-/Godot-/browserjobb
eller nedladdningar används. Produktionsfiler redigeras inte.

## Kontroller

- Giltiga, positiva och ömsesidigt disjunkta ytpolygoner; deras union motsvarar `coverage`.
- Geometri klipps mot verkliga hus-/väg-/vattenhinder och arbetsruta. Små arbetsrutor och helt blockerad mark hanteras.
- `height` lämnar indata orörd och ger exakt ursprungshöjd utanför `coverage`.
- Ytornas höjdfunktioner och `height` använder råa meter över havet och ger finita värden, även på polygonkanter.
- Gånganslutningar jämförs med faktiska trianglar i befintlig `site.json` och site-pipelinens utjämnade gatuprofiler.
- Träd-/buskposter följer avtalade listformat, har positiva skalor och lokalt Y = rå färdig markhöjd − 18 m.
- Strukturer har uttryckliga lokala höjder; tre entrésteg har rimliga, monotona nivåer.
- Ingen ny M31-mur och ingen utplaning av hela rutan 50×55 m.
- Metadata är JSON-serialiserbar och skiljer visuellt observerade element från uppskattade mått och höjder.

## Oberoende förprov

Lokalt huskoordinatsystem: o=(95,921;111,420), u=(0,559;0,829), v=(0,829;−0,559).

| Plats | x/z | Rå DTM | Närmaste gatuprofil | Slutsats |
|---|---|---:|---:|---|
| Gårdsurtag, a=10,3 / b=2,1 | 103,420 / 118,785 | 41,783 | 42,381 (Roten M) | Att fortsätta gatuprofilen in i gården skulle höja den cirka 0,60 m. |
| Sydkant, a=12,5 / b=−4 | 99,592 / 124,018 | 41,226 | 40,000 (Stockliden) | Närmaste gata är ingen säker gårdshöjd; skillnaden är cirka −1,23 m. |
| Royens gata, a=17 / b=8 | 112,056 / 121,041 | 40,991 | 40,522 (Royens gata) | Faktisk befintlig vägyta är cirka 40,558 m ö.h. inklusive ytlyft. |

Gatuprofilen är beräknad med samma 2 m-prov och fempunktsutjämning som
`site.py`; den är inte en inmätt färdig markhöjd. Husbasen 41,861 m ö.h. är
65:e percentil av tidigare DTM-prover och får inte beskrivas som oberoende survey.

Källor: aktuella `data/city.json`, `data/site.json`, `pipeline/common.py`,
`pipeline/site.py` samt `OBSERVATIONER.md` och `data-review.md` i denna mapp.

## Kör om

```bash
PYTHONDONTWRITEBYTECODE=1 tools/venv/bin/python v2/kvarnbyn/reference/roten-m/qa-roten-ground-agent.py
```

Testet skriver bara sin egen syskonfil `qa-roten-ground-agent.json` och avslutar
med kod 1 om en invariant eller gångprofil fallerar. Det startar inga motorer
och skriver inte till speldata.

## Hittade fel under granskningen

1. Ny grindinfart låg 0,337 m över Royens gata: rättad genom anslutning till
   vägarnas faktiska ytor, därefter flytt av entrén 0,55 m för att hålla stegens
   hörn borta från vägklippningen. Alla materialskarvar blev då kontinuerliga.
2. Två föreslagna träd föll i berg/sten och uteslöts: ersatta med två positioner
   inom gräsytorna. Senaste växtprov har två träd och 17 buskar.
3. Anslutning mot närmaste punkt på en union av två vägkanter gav en ny
   Voronoi-knäck inne i grusytan: 0,336 m över 2,5 cm nära x 112,737 / z 118,200.
   Rättad 2026-10-31 med lokal viktad planförlängning från båda vägkanterna.
   Slutprovet har högst 2,3 cm höjdändring per 5 cm längs grindens ramp och grus.
4. Tom arbetsruta gav tom väggeometri utan gräns; hanteras nu uttryckligen.

Denna kontroll använder höjdfunktioner. Därför tillkom även faktisk mesh- och kapsel-QA:
världens 2 m-triangulering tappade små bergformer, vilket rättades till 0,4 m för M29.

Blockerstrålen för vinstaketet ligger vid korsningen 0,864 m över staketbasen
och 0,336 m under dess topp. Den är därmed riktad genom staketets höjdintervall.
Den verkliga spelarens passage och den importerade kollisionsmeshen behöver
fortfarande kontrolleras av runtime-provet; denna QA använder bara CPU-data.

# Fas A — Kvarnbyn som spelbar värld (start 2026-10-29)

Beslut i `../poc/NASTA-FAS.md` (Joel sa ja 2026-10-29). Bygger vidare på PoC Gamla torget
(`../poc/torget/`, fryst som referens) med samma origo, samma Blender-kit och samma CC0-material.

## Mål

Hela Kvarnbyns kärna, **900 × 700 m** (v1-koordinater x −250…650, z −400…300; täcker v1:s
zoner Gamla torget, Roten M, Royens trappor och spawn vid Görjelycksgatan), som en Godot-
**datorapp** (Forward+) man kan gå runt i med mus och tangentbord. Utanför zonen: terräng och
enkla husvolymer ut till v1:s gränser som kuliss.

## Färdigdefinition

- Varje hus i zonen (~370) är byggt ur ett kit för sin **hustyp**; ingen låda utan fönster.
  Värden märkta `observed` (hjältehusen från torget-provet) eller `assumed` (tolkat).
- Gator, trottoarer, kantsten, parkeringar, torg, ån med murar, broar, terräng med rätt mark.
- Träd ur klasskartans skogsytor + gatuträd.
- Godot Forward+ med realtidsljus (SDFGI, SSAO, glow, dimma) — ingen ljusbake.
- Spelaren kan gå runt hela zonen utan att falla igenom eller fastna; osynliga gränsväggar.
- Mätningar: tid för bygge/import, trianglar, draw calls, fps på M5. Bilder från ögonhöjd.
- `rebuild.sh` bygger om allt; `RESULTAT.md` skiljer mätt från Joels bedömning.

## Avgränsning

Ingen strid, inga fiender, inga vapen (Fas B). Ingen Street View-runda per hus (Fas C).
Ingen webbexport som mål. Inga nya nedladdningar utöver det som redan finns lokalt.

## Struktur

`pipeline/` (Python, tools/venv) → `data/city.json`, `data/site.json` →
`blender/build_world.py` (Blender) → `blender/world_raw.glb` → `godot/` (Forward+).
Delade CC0-material/träd läses från `../poc/torget/assets-src/`.

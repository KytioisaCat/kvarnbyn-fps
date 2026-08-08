# Graph Report - .  (2026-08-08)

## Corpus Check
- Large corpus: 31 files · ~848,051 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 247 nodes · 423 edges · 14 communities (13 shown, 1 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 15 edges (avg confidence: 0.9)
- Token cost: 15,000 input · 10,500 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Speltillstånd & runtime-globaler|Speltillstånd & runtime-globaler]]
- [[_COMMUNITY_Arkitekturbeslut & motiv|Arkitekturbeslut & motiv]]
- [[_COMMUNITY_Rendering, kollision & soldater|Rendering, kollision & soldater]]
- [[_COMMUNITY_Spelloop, HUD & zonlogik|Spelloop, HUD & zonlogik]]
- [[_COMMUNITY_Markklassning & markshader|Markklassning & markshader]]
- [[_COMMUNITY_Kartdatagenerering & landmärken|Kartdatagenerering & landmärken]]
- [[_COMMUNITY_Höjd, siktlinjer & spawns|Höjd, siktlinjer & spawns]]
- [[_COMMUNITY_Äldre datapipeline (v1)|Äldre datapipeline (v1)]]
- [[_COMMUNITY_Texturer & geometrisammanslagning|Texturer & geometrisammanslagning]]
- [[_COMMUNITY_Tile-hämtning (äldre)|Tile-hämtning (äldre)]]
- [[_COMMUNITY_Vägband & kartgränser|Vägband & kartgränser]]
- [[_COMMUNITY_Koordinatmappning|Koordinatmappning]]

## God Nodes (most connected - your core abstractions)
1. `updateEnemy()` - 20 edges
2. `updatePlayer()` - 17 edges
3. `updateAlly()` - 16 edges
4. `frame()` - 13 edges
5. `CLAUDE.md — Projektinstruktioner` - 11 edges
6. `heightAt()` - 10 edges
7. `groundInfoAt()` - 9 edges
8. `coords()` - 9 edges
9. `DEPLOY.md — Publicering, licens & attribution` - 9 edges
10. `updateClutter()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `README.md — Spelbeskrivning` --references--> `three.module.js — Three.js r160 (vendorerad, MIT)`  [EXTRACTED]
  README.md → public/three.module.js
- `Igenkänning (ledstjärnan)` --semantically_similar_to--> `Joel-testet (främsta framgångskriterium)`  [INFERRED] [semantically similar]
  ARKITEKTUR.md → KRAVSPEC.md
- `CLAUDE.md — Projektinstruktioner` --references--> `data.js — Genererad kartdata (~4 MB JSON)`  [EXTRACTED]
  CLAUDE.md → public/data.js
- `CLAUDE.md — Projektinstruktioner` --references--> `ortho.jpg — Lantmäteriets ortofoto (draperad marktextur)`  [EXTRACTED]
  CLAUDE.md → public/ortho.jpg
- `DEPLOY.md — Publicering, licens & attribution` --conceptually_related_to--> `Krav: licenser som tillåter faktisk användning och spridning`  [INFERRED]
  DEPLOY.md → KRAVSPEC.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Python-datapipelinen i tools/ (källdata → speldata)** — tools_overpass_query, tools_fetch_ortho_lm, tools_fetch_lidar, tools_build_classmap, tools_build_data2, tools_make_ortho8k [EXTRACTED 1.00]
- **Delad lat/lon-linjär koordinatmappning över alla kartlager** — arkitektur_latlon_mappning, public_ortho, public_classmap, public_data [EXTRACTED 1.00]
- **Kompensation för det gråblekta vårfotot (klassning + tintning + detaljtexturer)** — arkitektur_lantmateriet_ortofoto, arkitektur_klasskarta, arkitektur_splat_shader [INFERRED 0.85]

## Communities (14 total, 1 thin omitted)

### Community 0 - "Speltillstånd & runtime-globaler"
Cohesion: 0.02
Nodes (76): Krav: raketdubbelhopp med doserbar kraft, ACCENTS, allies, bigmapEl, bldHash, bldPolys, bmCanvas, bridgeChains (+68 more)

### Community 1 - "Arkitekturbeslut & motiv"
Cohesion: 0.08
Nodes (37): ARKITEKTUR.md — Arkitektur & beslutslogg, AI-flyktmanöver för fastklämda soldater (planEscape), Befrielseläget (gameplay-design 2026-07-09), Branthetsspärr med 1,6 m lookahead, Brosystem med plana däck (bridgeDeckAt), Cache-bust med ?v=N, Byggda plana ytor plattas i runtime (flats), Tre höjdfunktioner: heightAt / origHeightAt / groundInfoAt (+29 more)

### Community 2 - "Rendering, kollision & soldater"
Cohesion: 0.12
Nodes (31): addTracer(), animateSoldier(), audio(), bilinear(), collideBuildings(), collideObstacles(), collideWalls(), damageEnemy() (+23 more)

### Community 3 - "Spelloop, HUD & zonlogik"
Cohesion: 0.13
Nodes (20): addSeg(), animate(), assignEnemyRole(), drawBigmap(), drawMinimap(), endGame(), flatAt(), flatInPoly() (+12 more)

### Community 4 - "Markklassning & markshader"
Cohesion: 0.18
Nodes (15): Markklassningskarta (asfalt/gräs/skog/berg per 2 m-cell), Kvällsläge (stjärnhimmel, lyktor, uNight), Splat-shader (onBeforeCompile på terrängmaterialet), classmap.png — Markklassningskarta (2 m/cell, RGB-kodad), coords(), draw_bld(), draw_parking(), draw_roads() (+7 more)

### Community 5 - "Kartdatagenerering & landmärken"
Cohesion: 0.17
Nodes (11): OSM Overpass-data (byggnader, vägar, murar, skog, parkeringar, POI), Krav: hjälteplatser (Corpus Pizzeria, Kråkans krog, Grevedämmet), Krav: namngivna landmärken igenkännbara i världen, centroid(), poly_color(), street_pts(), to_px(), way_coords() (+3 more)

### Community 6 - "Höjd, siktlinjer & spawns"
Cohesion: 0.36
Nodes (8): forestAt(), heightAt(), makeSoldier(), pickSpawnPoint(), pointBlocked(), raycastWorld(), spawnAlly(), spawnEnemy()

### Community 7 - "Äldre datapipeline (v1)"
Cohesion: 0.39
Nodes (6): centroid(), elev_at(), endpoint_lowest(), street_pts(), way_coords(), xz()

### Community 8 - "Texturer & geometrisammanslagning"
Cohesion: 0.40
Nodes (5): applyNightMode(), barricade(), makeFacadeTex(), mergeGeoms(), paintGeom()

### Community 9 - "Tile-hämtning (äldre)"
Cohesion: 0.83
Nodes (3): fetch(), stitch(), tile_xy()

### Community 10 - "Vägband & kartgränser"
Cohesion: 0.67
Nodes (3): inBounds(), randomOccupationPos(), ribbonGeom()

## Ambiguous Edges - Review These
- `README.md — Spelbeskrivning` → `Befrielseläget (gameplay-design 2026-07-09)`  [AMBIGUOUS]
  README.md · relation: references

## Knowledge Gaps
- **79 isolated node(s):** `flats`, `flatHash`, `origElev`, `canvas`, `renderer` (+74 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `README.md — Spelbeskrivning` and `Befrielseläget (gameplay-design 2026-07-09)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `CLAUDE.md — Projektinstruktioner` connect `Arkitekturbeslut & motiv` to `Speltillstånd & runtime-globaler`?**
  _High betweenness centrality (0.117) - this node is a cross-community bridge._
- **Why does `data.js — Genererad kartdata (~4 MB JSON)` connect `Arkitekturbeslut & motiv` to `Kartdatagenerering & landmärken`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Why does `Splat-shader (onBeforeCompile på terrängmaterialet)` connect `Markklassning & markshader` to `Speltillstånd & runtime-globaler`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **What connects `flats`, `flatHash`, `origElev` to the rest of the system?**
  _84 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Speltillstånd & runtime-globaler` be split into smaller, more focused modules?**
  _Cohesion score 0.021739130434782608 - nodes in this community are weakly interconnected._
- **Should `Arkitekturbeslut & motiv` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._
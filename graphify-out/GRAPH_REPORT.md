# Graph Report - /Users/joel/Workspace/kvarnbyn  (2026-08-08)

## Corpus Check
- 22 files · ~33,907 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 243 nodes · 399 edges · 16 communities (14 shown, 2 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 15 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

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
- [[_COMMUNITY_Höjdhämtning (äldre)|Höjdhämtning (äldre)]]
- [[_COMMUNITY_Ortofotohämtning (äldre)|Ortofotohämtning (äldre)]]

## God Nodes (most connected - your core abstractions)
1. `updateEnemy()` - 20 edges
2. `updatePlayer()` - 17 edges
3. `updateAlly()` - 16 edges
4. `frame()` - 13 edges
5. `heightAt()` - 10 edges
6. `groundInfoAt()` - 9 edges
7. `coords()` - 9 edges
8. `updateClutter()` - 8 edges
9. `playTone()` - 8 edges
10. `playerShoot()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `Igenkänning (ledstjärnan)` --semantically_similar_to--> `Joel-testet (främsta framgångskriterium)`  [INFERRED] [semantically similar]
  /Users/joel/Workspace/kvarnbyn/ARKITEKTUR.md → /Users/joel/Workspace/kvarnbyn/KRAVSPEC.md
- `Esri World Imagery (ersatt ortofotokälla)` --conceptually_related_to--> `Lantmäteriets ortofoto 0,16 m (CC BY 4.0, flygår 2024)`  [INFERRED]
  /Users/joel/Workspace/kvarnbyn/DEPLOY.md → /Users/joel/Workspace/kvarnbyn/ARKITEKTUR.md
- `README.md — Spelbeskrivning` --references--> `Befrielseläget (gameplay-design 2026-07-09)`  [AMBIGUOUS]
  /Users/joel/Workspace/kvarnbyn/README.md → /Users/joel/Workspace/kvarnbyn/ARKITEKTUR.md
- `DEPLOY.md — Publicering, licens & attribution` --conceptually_related_to--> `Krav: licenser som tillåter faktisk användning och spridning`  [INFERRED]
  /Users/joel/Workspace/kvarnbyn/DEPLOY.md → /Users/joel/Workspace/kvarnbyn/KRAVSPEC.md
- `DEPLOY.md — Publicering, licens & attribution` --references--> `GitHub Pages deploy-workflow (deploy.yml)`  [EXTRACTED]
  /Users/joel/Workspace/kvarnbyn/DEPLOY.md → /Users/joel/Workspace/kvarnbyn/.github/workflows/deploy.yml

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Python-datapipelinen i tools/ (källdata → speldata)** — tools_overpass_query, tools_fetch_ortho_lm, tools_fetch_lidar, tools_build_classmap, tools_build_data2, tools_make_ortho8k [EXTRACTED 1.00]
- **Delad lat/lon-linjär koordinatmappning över alla kartlager** — arkitektur_latlon_mappning, public_ortho, public_classmap, public_data [EXTRACTED 1.00]
- **Kompensation för det gråblekta vårfotot (klassning + tintning + detaljtexturer)** — arkitektur_lantmateriet_ortofoto, arkitektur_klasskarta, arkitektur_splat_shader [INFERRED 0.85]

## Communities (16 total, 2 thin omitted)

### Community 0 - "Speltillstånd & runtime-globaler"
Cohesion: 0.02
Nodes (77): Branthetsspärr med 1,6 m lookahead, Krav: raketdubbelhopp med doserbar kraft, ACCENTS, allies, bigmapEl, bldHash, bldPolys, bmCanvas (+69 more)

### Community 1 - "Arkitekturbeslut & motiv"
Cohesion: 0.11
Nodes (34): addSeg(), addTracer(), animateSoldier(), assignEnemyRole(), audio(), collideBuildings(), collideObstacles(), collideWalls() (+26 more)

### Community 2 - "Rendering, kollision & soldater"
Cohesion: 0.10
Nodes (23): ARKITEKTUR.md — Arkitektur & beslutslogg, Befrielseläget (gameplay-design 2026-07-09), Igenkänning (ledstjärnan), Lantmäteriets ortofoto 0,16 m (CC BY 4.0, flygår 2024), Lantmäteriets STAC-API (Geotorget), Markhöjd 1 m LiDAR (Lantmäteriet, CC0), Oskuggad terräng (MeshBasicMaterial), OSM Overpass-data (byggnader, vägar, murar, skog, parkeringar, POI) (+15 more)

### Community 3 - "Spelloop, HUD & zonlogik"
Cohesion: 0.13
Nodes (17): animate(), drawBigmap(), drawMinimap(), flatAt(), flatInPoly(), frame(), inBounds(), insideAnyBuilding() (+9 more)

### Community 4 - "Markklassning & markshader"
Cohesion: 0.24
Nodes (11): coords(), draw_bld(), draw_parking(), draw_roads(), draw_rock(), draw_water(), draw_wood(), Klasskarta för marken (2 m/cell): R=asfalt, G=gräs, B=skog, svart(=inget)=berg. (+3 more)

### Community 5 - "Kartdatagenerering & landmärken"
Cohesion: 0.21
Nodes (9): Krav: hjälteplatser (Corpus Pizzeria, Kråkans krog, Grevedämmet), Krav: namngivna landmärken igenkännbara i världen, centroid(), poly_color(), street_pts(), to_px(), way_coords(), xz() (+1 more)

### Community 6 - "Höjd, siktlinjer & spawns"
Cohesion: 0.17
Nodes (12): AI-flyktmanöver för fastklämda soldater (planEscape), Brosystem med plana däck (bridgeDeckAt), Cache-bust med ?v=N, Byggda plana ytor plattas i runtime (flats), Tre höjdfunktioner: heightAt / origHeightAt / groundInfoAt, Markklassningskarta (asfalt/gräs/skog/berg per 2 m-cell), Kvällsläge (stjärnhimmel, lyktor, uNight), Splat-shader (onBeforeCompile på terrängmaterialet) (+4 more)

### Community 7 - "Äldre datapipeline (v1)"
Cohesion: 0.22
Nodes (11): bilinear(), heightAt(), makeSoldier(), origHeightAt(), pickSpawnPoint(), pointBlocked(), pointInPoly(), roofSupportAt() (+3 more)

### Community 8 - "Texturer & geometrisammanslagning"
Cohesion: 0.39
Nodes (6): centroid(), elev_at(), endpoint_lowest(), street_pts(), way_coords(), xz()

### Community 9 - "Tile-hämtning (äldre)"
Cohesion: 0.40
Nodes (5): applyNightMode(), barricade(), makeFacadeTex(), mergeGeoms(), paintGeom()

### Community 10 - "Vägband & kartgränser"
Cohesion: 0.83
Nodes (3): fetch(), stitch(), tile_xy()

## Ambiguous Edges - Review These
- `Befrielseläget (gameplay-design 2026-07-09)` → `README.md — Spelbeskrivning`  [AMBIGUOUS]
  /Users/joel/Workspace/kvarnbyn/README.md · relation: references

## Knowledge Gaps
- **79 isolated node(s):** `flats`, `flatHash`, `origElev`, `canvas`, `renderer` (+74 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Befrielseläget (gameplay-design 2026-07-09)` and `README.md — Spelbeskrivning`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `TODO.md — Backlogg & statusminne` connect `Höjd, siktlinjer & spawns` to `Rendering, kollision & soldater`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._
- **Why does `Markklassningskarta (asfalt/gräs/skog/berg per 2 m-cell)` connect `Höjd, siktlinjer & spawns` to `Markklassning & markshader`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._
- **What connects `flats`, `flatHash`, `origElev` to the rest of the system?**
  _86 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Speltillstånd & runtime-globaler` be split into smaller, more focused modules?**
  _Cohesion score 0.021505376344086023 - nodes in this community are weakly interconnected._
- **Should `Arkitekturbeslut & motiv` be split into smaller, more focused modules?**
  _Cohesion score 0.1140819964349376 - nodes in this community are weakly interconnected._
- **Should `Rendering, kollision & soldater` be split into smaller, more focused modules?**
  _Cohesion score 0.10153846153846154 - nodes in this community are weakly interconnected._
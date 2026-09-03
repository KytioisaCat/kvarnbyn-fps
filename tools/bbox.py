#!/usr/bin/env python3
"""Kartans bounding box — SINGLE SOURCE OF TRUTH för hela datapipelinen.

Alla skript i tools/ som behöver kartans utbredning importerar härifrån:

    from bbox import LAT0, LAT1, LON0, LON1

Ändra ALDRIG bbox-siffror direkt i de enskilda skripten eller för hand i
overpass_query.txt / poi_query.txt. Gör så här i stället:

  1. Ändra LAT0/LAT1/LON0/LON1 nedan.
  2. Kör `python3 bbox.py` i tools/ — skriver om båda query-filerna.
  3. Kör pipelinen enligt ARKITEKTUR.md (ny OSM/LiDAR/orto/classmap/data.js).

Värdena är WGS84 lat/lon. Spelprojektionen är lat/lon-linjär, se ARKITEKTUR.md.
"""

LAT0, LAT1 = 57.64625, 57.66575   # syd, nord (+50 % radie runt 57.656)
LON0, LON1 = 11.999, 12.053       # väst, öst (+50 % radie runt 12.026)

CLAT = (LAT0 + LAT1) / 2
CLON = (LON0 + LON1) / 2

# Mindre ruta över centrum — restaurangsökningen i poi_query är avsiktligt
# snävare (bara centrumkärnan) och följer därför INTE huvud-boxen.
FOOD_LAT0, FOOD_LAT1 = 57.652, 57.658
FOOD_LON0, FOOD_LON1 = 12.015, 12.03


def area_str(lat0=LAT0, lon0=LON0, lat1=LAT1, lon1=LON1):
    """Overpass area-filter: (syd,väst,nord,öst)."""
    return f"({lat0},{lon0},{lat1},{lon1})"


# Samma way-typer som overpass_query.txt alltid haft (ODbL-data till data.js).
# Större fråga sedan +50 %-utvidgningen (2026-09-03): 2,25× yta.
OVERPASS_TIMEOUT = 120
OVERPASS_WAYS = [
    'way["building"]',
    'way["highway"]',
    'way["waterway"]',
    'way["natural"="water"]',
    'way["natural"="cliff"]',
    'way["natural"="wood"]',
    'way["natural"="scrub"]',
    'way["natural"="bare_rock"]',
    'way["natural"="scree"]',
    'way["natural"="grassland"]',
    'way["amenity"="parking"]',
    'way["barrier"]',
    'way["landuse"]',
    'way["leisure"]',
]

# Samma POI-rader som poi_query.txt alltid haft.
POI_TIMEOUT = 60
POI_QUERIES = [
    'nwr["name"~"Corpus",i]',
    'nwr["name"~"usikskola|ulturskola",i]',
    'nwr["name"~"Grevedämmet"]',
]


def render_overpass_query():
    lines = [f"[out:json][timeout:{OVERPASS_TIMEOUT}];", "("]
    lines += [f"  {w}{area_str()};" for w in OVERPASS_WAYS]
    lines += [");", "out body;", ">;", "out skel qt;", ""]
    return "\n".join(lines)


def render_poi_query():
    lines = [f"[out:json][timeout:{POI_TIMEOUT}];", "("]
    lines += [f"  {q}{area_str()};" for q in POI_QUERIES]
    food = area_str(FOOD_LAT0, FOOD_LON0, FOOD_LAT1, FOOD_LON1)
    lines += [f'  node["amenity"~"restaurant|fast_food|pizzeria"]{food};',
              ");", "out center tags;", ""]
    return "\n".join(lines)


def main():
    here = __import__("pathlib").Path(__file__).resolve().parent
    (here / "overpass_query.txt").write_text(render_overpass_query())
    (here / "poi_query.txt").write_text(render_poi_query())
    print("bbox:", area_str(), "-> overpass_query.txt + poi_query.txt omskrivna")


if __name__ == "__main__":
    main()

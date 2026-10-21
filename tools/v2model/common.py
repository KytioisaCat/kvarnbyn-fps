"""Gemensamt: projektion (identisk med v1/build_data2.py), markmodell, vägklasser, områden."""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
from bbox import LAT0, LAT1, LON0, LON1          # noqa: E402
from lidar_png import load_dem                     # noqa: E402

CLAT, CLON = (LAT0 + LAT1) / 2, (LON0 + LON1) / 2
MLAT = 111320.0
MLON = 111320.0 * math.cos(math.radians(CLAT))
EXAG = 1.2                       # spelhöjd = rå LiDAR × EXAG (v1:s kalibrering)


def xz(lat, lon):
    return ((lon - CLON) * MLON, -(lat - CLAT) * MLAT)


X0, Z1 = xz(LAT1, LON0)          # väst, norr (z negativ)
X1, Z0 = xz(LAT0, LON1)          # öst, syd (z positiv)

# Provområden: (xmin, xmax, zmin, zmax) i spelkoordinater
AREAS = {
    'torget': (-680, 260, -260, 160),     # Gamla torget + Mölndals bro + Forsebron
    'all': (X0, X1, Z1, Z0),
}

# vägklass → (bredd m, maxlutning, trottoar m). v1:s bredder + motorväg/länkar som saknades.
ROAD = {
    'motorway':      (11.0, 0.06, 0.0), 'motorway_link': (6.0, 0.08, 0.0),
    'trunk':         (10.0, 0.06, 0.0), 'trunk_link':    (6.0, 0.08, 0.0),
    'primary':       (9.0, 0.08, 2.0),  'primary_link':  (6.0, 0.10, 0.0),
    'secondary':     (8.0, 0.08, 2.0),  'secondary_link': (6.0, 0.10, 0.0),
    'tertiary':      (7.0, 0.14, 2.0),  'tertiary_link': (5.5, 0.14, 0.0),
    # Kvarnbyns backgator är branta på riktigt (LiDAR): 20 % tillåts för bostadsgator
    'residential':   (6.0, 0.20, 1.5),  'living_street': (5.5, 0.20, 0.0),
    'unclassified':  (6.0, 0.20, 0.0),  'service':       (4.0, 0.22, 0.0),
    'pedestrian':    (4.0, 0.10, 0.0),  'footway':       (2.2, 0.30, 0.0),   # gång: ramp ≤ 30 %, brantare = trappa
    'path':          (1.8, 0.30, 0.0),  'cycleway':      (2.5, 0.12, 0.0),
    'track':         (3.0, 0.20, 0.0),  'steps':         (2.5, 0.70, 0.0),
}


class Ground:
    """Markmodell i spelhöjd (rå × EXAG), bilinjär, rad 0 = norr."""

    def __init__(self):
        self.raw = load_dem().astype(np.float64)
        self.h, self.w = self.raw.shape
        self.sx = (self.w - 1) / (X1 - X0)
        self.sz = (self.h - 1) / (Z0 - Z1)

    def at(self, x, z):
        x = np.asarray(x, dtype=np.float64); z = np.asarray(z, dtype=np.float64)
        fx = (x - X0) * self.sx; fz = (z - Z1) * self.sz
        c = np.clip(np.floor(fx).astype(int), 0, self.w - 2)
        r = np.clip(np.floor(fz).astype(int), 0, self.h - 2)
        tx = np.clip(fx - c, 0, 1); tz = np.clip(fz - r, 0, 1)
        a = self.raw
        v = (a[r, c] * (1 - tx) + a[r, c + 1] * tx) * (1 - tz) + (a[r + 1, c] * (1 - tx) + a[r + 1, c + 1] * tx) * tz
        return v * EXAG

    def cell_of(self, x, z):
        """(rad, kolumn) närmaste cell."""
        return (np.rint((z - Z1) * self.sz).astype(int), np.rint((x - X0) * self.sx).astype(int))


def load_osm():
    osm = json.load(open(os.path.join(TOOLS, 'osm_raw.json')))
    nodes = {e['id']: xz(e['lat'], e['lon']) for e in osm['elements'] if e['type'] == 'node'}
    ways = [e for e in osm['elements'] if e['type'] == 'way']
    return nodes, ways

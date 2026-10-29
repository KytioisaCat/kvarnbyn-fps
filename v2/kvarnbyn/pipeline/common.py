"""Gemensamt för Kvarnbyns pipeline: origo, zon, projektion, markmodell och ortofoto.

Samma origo som PoC Gamla torget (57.65690 N, 12.02780 E, y = rå höjd − 18 m), så torgets
handgjorda hjältehus kan återanvändas ordagrant. Lokala koordinater: x österut, z söderut, meter.
"""
from pathlib import Path
import json, math
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parents[1]          # v2/kvarnbyn
REPO = HERE.parents[1]
TORGET = REPO / 'v2/poc/torget'
ASSETS = TORGET / 'assets-src'
DATA = HERE / 'data'

ORIGIN_LON, ORIGIN_LAT = 12.02780, 57.65690
SX, SZ = 59560.0, 111320.0
Y_OFFSET = 18.0
# v1-spelkoordinat för origo (v1: x=(lon−12.026)·59560, z=−(lat−57.656)·111320)
V1_ORIGIN = ((ORIGIN_LON - 12.026) * SX, -(ORIGIN_LAT - 57.656) * SZ)

# Spelbar zon: v1 x −250…650, z −400…300 → lokalt
ZONE = (-250 - V1_ORIGIN[0], -400 - V1_ORIGIN[1], 650 - V1_ORIGIN[0], 300 - V1_ORIGIN[1])
# Kuliss: terräng och enkla husvolymer ut till hit (v1:s karta, något inskränkt)
BACKDROP = (-1100 - V1_ORIGIN[0], -900 - V1_ORIGIN[1], 1400 - V1_ORIGIN[0], 800 - V1_ORIGIN[1])

_lm = json.loads((REPO / 'tools/lidar_meta.json').read_text())
_dem = None
_ortho = None
_classmap = None


def lonlat(x, z):
    return ORIGIN_LON + np.asarray(x) / SX, ORIGIN_LAT - np.asarray(z) / SZ


def local(lon, lat):
    return ((lon - ORIGIN_LON) * SX, -(lat - ORIGIN_LAT) * SZ)


def _grid_uv(x, z, w, h):
    lon, lat = lonlat(x, z)
    u = (lon - _lm['lon0']) / (_lm['lon1'] - _lm['lon0']) * (w - 1)
    v = (_lm['lat1'] - lat) / (_lm['lat1'] - _lm['lat0']) * (h - 1)
    return u, v


def raw_height(x, z):
    """Rå markhöjd (m ö.h.) ur LiDAR-DTM 1 m, bilinjär. Vektoriserad."""
    global _dem
    if _dem is None:
        img = np.asarray(Image.open(REPO / 'tools/lidar_1m.png'), dtype=np.float64)
        _dem = img / _lm['png_scale'] - _lm['png_offset_m']
    h, w = _dem.shape
    u, v = _grid_uv(np.asarray(x, float), np.asarray(z, float), w, h)
    i = np.clip(np.floor(u).astype(int), 0, w - 2); k = np.clip(np.floor(v).astype(int), 0, h - 2)
    fx = np.clip(u - i, 0, 1); fz = np.clip(v - k, 0, 1)
    d = _dem
    return d[k, i] * (1 - fx) * (1 - fz) + d[k, i + 1] * fx * (1 - fz) + d[k + 1, i] * (1 - fx) * fz + d[k + 1, i + 1] * fx * fz


def ortho_rgb(x, z):
    """Ortofotots färg (0..1) i punkterna. Lantmäteriet 2024, CC BY 4.0."""
    global _ortho
    if _ortho is None:
        Image.MAX_IMAGE_PIXELS = None
        _ortho = np.asarray(Image.open(REPO / 'tools/ortho8k.jpg'))
    h, w = _ortho.shape[:2]
    u, v = _grid_uv(np.asarray(x, float), np.asarray(z, float), w, h)
    i = np.clip(np.rint(u).astype(int), 0, w - 1); k = np.clip(np.rint(v).astype(int), 0, h - 1)
    return _ortho[k, i] / 255.0


def land_class(x, z):
    """Klasskartan (2 m): returnerar (asfalt, gräs, skog, berg) vikter 0..1."""
    global _classmap
    if _classmap is None:
        _classmap = np.asarray(Image.open(REPO / 'tools/classmap.png').convert('RGB'), dtype=np.float64) / 255.0
    h, w = _classmap.shape[:2]
    u, v = _grid_uv(np.asarray(x, float), np.asarray(z, float), w, h)
    i = np.clip(np.rint(u).astype(int), 0, w - 1); k = np.clip(np.rint(v).astype(int), 0, h - 1)
    c = _classmap[k, i]
    rock = np.clip(1 - c[..., 0] - c[..., 1] - c[..., 2], 0, 1)
    return np.stack([c[..., 0], c[..., 1], c[..., 2], rock], axis=-1)


def load_osm():
    j = json.loads((REPO / 'tools/osm_raw.json').read_text())
    nodes = {n['id']: n for n in j['elements'] if n['type'] == 'node'}
    ways = [w for w in j['elements'] if w['type'] == 'way']
    return j, nodes, ways


def way_xz(w, nodes):
    return [local(nodes[n]['lon'], nodes[n]['lat']) for n in w['nodes'] if n in nodes]


def stable_hash(*parts):
    """Deterministiskt tal 0..1 ur id — samma hus får samma färg varje bygge."""
    s = '|'.join(map(str, parts))
    h = 2166136261
    for ch in s.encode():
        h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    return h / 0xFFFFFFFF


def r3(v):
    return [round(float(a), 3) for a in v]

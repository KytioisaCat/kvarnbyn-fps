"""Export: roads.json (materialtabell) + roads.bin (float32 positioner, uint32 index) till
v2/public/data/, och konformerad DEM till tools/lidar_conformed.npy (build_v2.py läser den)."""
import json
import os

import numpy as np

from .common import TOOLS

OUT = os.path.join(TOOLS, '..', 'v2', 'public', 'data')


def write_meshes(arrays, name='roads'):
    os.makedirs(OUT, exist_ok=True)
    meta = {'materials': {}, 'format': 'pos f32 xyz ×3 per tri-vertex; idx u32; offsets i bytes'}
    blobs = []
    off = 0
    for mat, (pos, idx) in arrays.items():
        p = pos.astype('<f4').tobytes(); i = idx.astype('<u4').tobytes()
        meta['materials'][mat] = {'posOffset': off, 'posCount': len(pos), 'idxOffset': off + len(p), 'idxCount': len(idx)}
        blobs += [p, i]; off += len(p) + len(i)
    with open(os.path.join(OUT, f'{name}.bin'), 'wb') as f:
        for b in blobs: f.write(b)
    with open(os.path.join(OUT, f'{name}.json'), 'w') as f:
        json.dump(meta, f)
    return off


def write_dem(raw):
    np.save(os.path.join(TOOLS, 'lidar_conformed.npy'), raw.astype(np.float32))

"""Compare delivered geometry with the accepted world, independently of Blender.

Checks every existing mesh's expanded triangle positions, not just file sizes.
Only the two new wall meshes and their collision meshes may be added.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import numpy as np


def geometry(path):
    data = path.read_bytes()
    size = struct.unpack_from('<I', data, 12)[0]
    doc = json.loads(data[20:20+size])
    start = 28+size

    def accessor(index):
        a = doc['accessors'][index]
        view = doc['bufferViews'][a['bufferView']]
        dtype = np.dtype({5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']])
        count = {'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
        return np.ndarray((a['count'], count), dtype=dtype, buffer=data,
                          offset=start+view.get('byteOffset',0)+a.get('byteOffset',0),
                          strides=(view.get('byteStride', dtype.itemsize*count), dtype.itemsize))

    meshes = {}
    rock = []
    terrain_nodes = 0
    for node in doc['nodes']:
        if 'mesh' not in node:
            continue
        digest = hashlib.sha256()
        for primitive in doc['meshes'][node['mesh']]['primitives']:
            position = accessor(primitive['attributes']['POSITION'])
            ids = accessor(primitive['indices']).ravel() if 'indices' in primitive else np.arange(len(position))
            digest.update(position[ids].astype('<f4').tobytes())
            if node['name'].startswith(('Terrain', 'FarTerrain')):
                terrain_nodes += 1
                color_id = primitive['attributes'].get('COLOR_0')
                if color_id is not None:
                    color = accessor(color_id)
                    if color.dtype.kind == 'u':
                        color = color / np.iinfo(color.dtype).max
                    rock.extend(color[:,0])
        meshes[node['name']] = dict(triangles_sha256=digest.hexdigest(),
                                   transform={key:node[key] for key in ('translation','rotation','scale','matrix') if key in node})
    return meshes, np.asarray(rock), terrain_nodes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('baseline-glb','glb','before-site','site','out'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    before, _, _ = geometry(args.baseline_glb)
    after, rock, terrain_nodes = geometry(args.glb)
    changed = [name for name in before if name not in after or before[name] != after[name]]
    added = [name for name in after if name not in before]
    a, b = json.loads(args.before_site.read_text()), json.loads(args.site.read_text())
    checks = {}
    checks['existing_mesh_geometry_unchanged'] = not changed
    checks['only_mapped_walls_added'] = len(added) == 4 and all('Mapped_stone_wall_w' in name for name in added)
    checks['height_fields_unchanged'] = all(a[key]['heights']==b[key]['heights'] for key in ('terrain','terrain_backdrop'))
    checks['other_site_fields_unchanged'] = all(a[key]==b[key] for key in a if key not in ('terrain','terrain_backdrop'))
    checks['cover_exported_in_primary_color'] = len(rock)>100000 and rock.min()<.01 and rock.max()>.99 and ((rock>.15)&(rock<.85)).sum()>10000
    report = dict(passed=all(checks.values()), checks={key:bool(value) for key,value in checks.items()},
                  compared_meshes=len(before), added=added, changed=changed, terrain_primitives=terrain_nodes,
                  cover_vertices=len(rock), blended_vertices=int(((rock>.15)&(rock<.85)).sum()),
                  baseline_sha256=hashlib.sha256(args.baseline_glb.read_bytes()).hexdigest(),
                  glb_sha256=hashlib.sha256(args.glb.read_bytes()).hexdigest())
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()

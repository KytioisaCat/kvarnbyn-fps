"""Fetch the small CC0 material kit. No API keys, Blender files, or 8K maps.
Run with ordinary Python; downloads are checked against Poly Haven's source MD5.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parent
DOCS = ROOT.parent / 'asset-docs'
USER_AGENT = 'KvarnbynFPS-PoC/0.1 (CC0 game asset preparation)'
SELECTION = {
    'wood_painted': ('wood_plank_wall', '2k', 'Use normal/roughness with off-white base color for painted cladding; source albedo is bare wood.'),
    'plaster': ('white_plaster_rough_01', '1k', 'Small-scale rough plaster; choose façade base color from house reference.'),
    'brick': ('red_bricks_04', '1k', 'Historic red brick walls and chimney faces.'),
    'roof_tiles': ('clay_roof_tiles_02', '2k', 'Weathered clay roof tiles; orient UV rows down roof slope.'),
    'asphalt': ('asphalt_02', '2k', 'Road asphalt; source captures a 3 m square.'),
    'cobblestone': ('cobblestone_floor_04', '2k', 'Small granite paving; source captures a 1.5 m square.'),
    'grass': ('grass_ground', '1k', 'Mixed grass/ground around rock and garden edges.'),
    'rock': ('granite_wall', '1k', 'Granite block foundation/retaining wall, not raw bedrock.'),
    'natural_rock': ('rock_01', '1k', 'Natural weathered grey solid rock, not masonry. Generic bedrock proxy, not measured on-site geology.'),
    'bark': ('bark_willow', '1k', 'Willow bark used on generic broadleaf tree assets; not a species or position measurement.'),
}

def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def get_json(url):
    return json.loads(get(url))


def save_verified(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        data = destination.read_bytes()
        if hashlib.md5(data).hexdigest() == source['md5']:
            return
    data = get(source['url'])
    if hashlib.md5(data).hexdigest() != source['md5']:
        raise ValueError(f'Checksum mismatch: {source["url"]}')
    destination.write_bytes(data)


def material_task(item):
    semantic, (asset_id, resolution, note) = item
    metadata = get_json(f'https://api.polyhaven.com/info/{asset_id}')
    files = get_json(f'https://api.polyhaven.com/files/{asset_id}')
    out = {
        'asset_id': asset_id,
        'name': metadata['name'],
        'source_page': f'https://polyhaven.com/a/{asset_id}',
        'source_api': f'https://api.polyhaven.com/files/{asset_id}',
        'license': 'CC0-1.0',
        'license_url': 'https://polyhaven.com/license',
        'authors': metadata.get('authors', {}),
        'resolution': resolution,
        'tile_size_m': [round(float(x) / 1000, 3) for x in metadata.get('dimensions', [2000, 2000])[:2]],
        'notes': note,
        'maps': {},
    }
    for semantic_map, source_map in [('albedo', 'Diffuse'), ('roughness', 'Rough'), ('normal', 'nor_gl')]:
        source = files[source_map][resolution]['jpg']
        destination = ROOT / 'materials' / semantic / source['url'].rsplit('/', 1)[-1]
        save_verified(source, destination)
        out['maps'][semantic_map] = {
            'path': destination.relative_to(ROOT).as_posix(),
            **{k: source[k] for k in ('url', 'size', 'md5')},
            'color_space': 'sRGB' if semantic_map == 'albedo' else 'Non-Color',
        }
    print(f'{semantic}: {sum(x["size"] for x in out["maps"].values()) / 1e6:.2f} MB', flush=True)
    return semantic, out


def foliage_task():
    asset_id = 'tree_small_02'
    metadata = get_json(f'https://api.polyhaven.com/info/{asset_id}')
    files = get_json(f'https://api.polyhaven.com/files/{asset_id}')
    out = {
        'asset_id': asset_id,
        'source_page': f'https://polyhaven.com/a/{asset_id}',
        'license': 'CC0-1.0',
        'license_url': 'https://polyhaven.com/license',
        'authors': metadata.get('authors', {}),
        'notes': 'Photographed leaf/branch atlas only, not the multi-million-polygon full tree. Source species is Burkea africana. Generic foliage proxy, not a measured Swedish species.',
        'maps': {},
    }
    for semantic_map, source_map, fmt in [
        ('leaf_albedo', 'leaves_diff', 'jpg'), ('leaf_alpha', 'leaves_alpha', 'png'),
        ('leaf_roughness', 'leaves_rough', 'jpg'), ('leaf_normal', 'leaves_nor_gl', 'jpg'),
        ('branch_albedo', 'branch_diff', 'jpg'), ('branch_roughness', 'branch_rough', 'jpg'),
        ('branch_normal', 'branch_nor_gl', 'jpg'),
    ]:
        source = files[source_map]['1k'][fmt]
        destination = ROOT / 'vegetation' / 'textures' / source['url'].rsplit('/', 1)[-1]
        save_verified(source, destination)
        out['maps'][semantic_map] = {'path': destination.relative_to(ROOT).as_posix(), **{k: source[k] for k in ('url', 'size', 'md5')}}
    return out


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as executor:
        materials = dict(executor.map(material_task, SELECTION.items()))
    foliage = foliage_task()
    manifest = {
        'schema_version': 1,
        'retrieved_at': datetime.now(timezone.utc).isoformat(),
        'purpose': 'Kvarnbyn Gamla torget Blender/Godot proof of concept',
        'source_license': {'id': 'CC0-1.0', 'url': 'https://polyhaven.com/license'},
        'normal_convention': 'OpenGL (+Y)',
        'texture_dimensions_unit': 'meters (source API dimensions are millimeters)',
        'materials': materials,
        'foliage_atlas': foliage,
    }
    manifest['download_bytes'] = sum(v['size'] for m in materials.values() for v in m['maps'].values()) + sum(v['size'] for v in foliage['maps'].values())
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(f'Total verified asset bytes: {manifest["download_bytes"]} ({manifest["download_bytes"] / 1e6:.2f} MB)')

if __name__ == '__main__':
    main()

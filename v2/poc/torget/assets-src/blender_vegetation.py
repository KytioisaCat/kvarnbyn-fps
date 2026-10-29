"""Place shared-mesh tree assets into another Blender scene.

    from blender_vegetation import place_tree
    place_tree('Broadleaf_B', location=(20, -7, 2.0), scale=1.1, yaw=.4)

Coordinates are Blender world meters, Z up. Textures are packed in the library.
"""
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parent
_LIBRARY = None


def load_library():
    global _LIBRARY
    if _LIBRARY is None:
        with bpy.data.libraries.load(str(ROOT / 'vegetation' / 'vegetation.blend'), link=False) as (source, target):
            target.collections = [name for name in source.collections if name in ['Broadleaf_A', 'Broadleaf_B', 'Broadleaf_C']]
        _LIBRARY = {}
        for collection in target.collections:
            # A datablock can receive a suffix on repeated imports; original source
            # name is available in the root-empty name before the first dot.
            root = next(obj for obj in collection.objects if obj.type == 'EMPTY' and obj.parent is None)
            _LIBRARY[root.name.split('.')[0]] = collection
    return _LIBRARY


def place_tree(variant='Broadleaf_A', location=(0, 0, 0), scale=1.0, yaw=0.0, collection=None, name=None):
    source = load_library()[variant]
    target = collection or bpy.context.scene.collection
    originals = list(source.objects)
    copies = {}
    for obj in originals:
        new = obj.copy()
        # Share mesh/material data; only transforms vary between placements.
        target.objects.link(new)
        copies[obj] = new
    for original, new in copies.items():
        if original.parent in copies:
            new.parent = copies[original.parent]
    root = next(new for old, new in copies.items() if old.type == 'EMPTY' and old.parent is None)
    root.name = name or variant + '_Instance'
    root.location = location
    root.rotation_euler = (0, 0, yaw)
    root.scale = (scale, scale, scale)
    return root

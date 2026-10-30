"""Blender actual-mesh QA for the staged Torget pass; optional matched preview.

Blender -b <stage>/world.blend --python qa_torg_ground.py -- --site <stage>/site.json
    --report <small-report.json> --label after --render <preview.jpg>
Checks actual COL and rendered meshes, not a duplicate analytical height solver.
"""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

p = argparse.ArgumentParser()
p.add_argument('--site', type=Path, required=True)
p.add_argument('--report', type=Path, required=True)
p.add_argument('--label', default='after')
p.add_argument('--render', type=Path)
p.add_argument('--strict', action='store_true')
args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
site = json.loads(args.site.read_text())
root = Path(__file__).resolve().parents[1]
# The same observed coverage is used for both before and after sampling.
coverage_site = json.loads((args.site.parent.parent / 'after/site.json').read_text())
coverage = coverage_site['authored_ground']['pavement']
planters = coverage_site['authored_ground']['planters']


def in_ring(x, z, ring):
    inside = False
    for (xa, za), (xb, zb) in zip(ring, ring[1:] + ring[:1]):
        if (za > z) != (zb > z) and x < (xb - xa) * (z - za) / (zb - za) + xa:
            inside = not inside
    return inside


def contains(x, z, records):
    return any(in_ring(x, z, c['outer']) and not any(in_ring(x, z, h) for h in c['holes'])
               for r in records for c in r['contours'])


def make_bvh(prefixes):
    verts, triangles, labels = [], [], []
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not obj.name.startswith(prefixes): continue
        obj.data.calc_loop_triangles()
        matrix = obj.matrix_world
        for tri in obj.data.loop_triangles:
            pts = [matrix @ obj.data.vertices[i].co for i in tri.vertices]
            if max(q.x for q in pts) < -70 or min(q.x for q in pts) > 75 or max(-q.y for q in pts) < -45 or min(-q.y for q in pts) > 60: continue
            j = len(verts); verts.extend(pts); triangles.append((j, j+1, j+2)); labels.append(obj.name)
    return (BVHTree.FromPolygons(verts, triangles, all_triangles=True), labels) if triangles else (None, [])


def ray(tree, x, z):
    bvh, labels = tree
    if bvh is None: return None
    loc, normal, index, distance = bvh.ray_cast(Vector((x, -z, 80)), Vector((0, 0, -1)), 150)
    return (loc.z, labels[index]) if loc is not None else None


collision = make_bvh(('COL_Terrain', 'COL_asphalt', 'COL_paving', 'COL_walkway', 'COL_soil', 'COL_Planter_kerb', 'COL_Bridge'))
rendered = make_bvh(('Terrain', 'Asphalt', 'Paving', 'Walkway', 'Soil', 'Planter_kerb', 'Bridge_deck'))
paving = make_bvh(('COL_paving',))
terrain = make_bvh(('COL_Terrain',))
samples, holes, mismatch, grass, hops = {}, [], [], [], []
max_delta = 0.; max_hop = 0.
for ix in range(240):
    x = -55.75 + ix * .5
    for iz in range(112):
        z = -27.75 + iz * .5
        if not contains(x, z, coverage) or contains(x, z, planters): continue
        a, b, c, t = ray(collision, x, z), ray(rendered, x, z), ray(paving, x, z), ray(terrain, x, z)
        if a is None: holes.append([x, z]); continue
        samples[(ix, iz)] = a[0]
        if b is None or abs(a[0] - b[0]) > .012: mismatch.append([x, z, a, b])
        if b is not None: max_delta = max(max_delta, abs(a[0] - b[0]))
        if c is None: grass.append([x, z, a[1]])
for (ix, iz), h in samples.items():
    for dx, dz in ((1, 0), (0, 1)):
        key = (ix + dx, iz + dz)
        if key not in samples: continue
        delta = abs(samples[key] - h)
        max_hop = max(max_hop, delta)
        if delta > .22:
            x, z = -55.75 + ix * .5, -27.75 + iz * .5
            # A thin planter can cross between two samples; do not count its curb as an unintentional step.
            if not contains(x + dx * .25, z + dz * .25, planters):
                hops.append(dict(x=x, z=z, step_m=round(delta, 4), direction=[dx, dz]))
summary = dict(label=args.label, actual_blend=bpy.data.filepath, spacing_m=.5,
               pavement_samples=len(samples), holes=len(holes), render_collision_mismatch=len(mismatch),
               max_render_collision_delta_m=round(max_delta, 5), samples_without_paving=len(grass),
               unintended_hops_over_022m=len(hops), max_hop_m=round(max_hop, 4),
               first_holes=holes[:15], first_mismatches=mismatch[:15], first_hops=sorted(hops, key=lambda q:-q['step_m'])[:30],
               authored_tree_count=len(site.get('authored_trees', [])), shrub_count=len(site.get('shrubs', [])))
before = json.loads((args.site.parent.parent / 'before/site.json').read_text())
summary['asphalt_triangles_unchanged'] = before['meshes']['asphalt'] == site['meshes']['asphalt']
summary['water_triangles_unchanged'] = before['meshes']['water'] == site['meshes']['water']
summary['bridge_decks_unchanged'] = before['bridges'] == site['bridges']
floor_at_eye = ray(collision, -8.5, 8)
eye_y = floor_at_eye[0] + 1.7 if floor_at_eye else 1.37
summary['comparison_camera'] = dict(position=[-8.5, round(eye_y, 4), 8], actual_floor_y_m=floor_at_eye[0] if floor_at_eye else None,
                                     eye_height_over_COL_m=1.7 if floor_at_eye else None)
summary['pass'] = len(holes) == 0 and len(mismatch) == 0 and len(hops) == 0 and len(grass) == 0 and all(summary[k] for k in ('asphalt_triangles_unchanged', 'water_triangles_unchanged', 'bridge_decks_unchanged'))
args.report.parent.mkdir(parents=True, exist_ok=True)
args.report.write_text(json.dumps(summary, indent=2))
print('TORG_QA', json.dumps(summary), flush=True)

if args.render:
    # Matched Blender previews, not a claim of Godot visual acceptance.
    # Same fixed eye-height camera and lighting for before/after.
    for obj in list(bpy.data.objects):
        if obj.type in ('CAMERA', 'LIGHT'): bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.cycles.device = 'CPU'
    scene.render.resolution_x = 1280; scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'JPEG'; scene.render.image_settings.quality = 88
    world = bpy.data.worlds.new('QA_daylight'); world.use_nodes = True; scene.world = world
    nodes = world.node_tree.nodes; links = world.node_tree.links
    background = nodes.get('Background'); background.inputs['Strength'].default_value = .6
    texture = nodes.new('ShaderNodeTexEnvironment')
    texture.image = bpy.data.images.load(str(root / 'godot/assets/sky.hdr'), check_existing=True)
    links.new(texture.outputs['Color'], background.inputs['Color'])
    data = bpy.data.lights.new('QA_sun', 'SUN'); data.energy = 2.; data.angle = math.radians(.6)
    sun = bpy.data.objects.new('QA_sun', data); scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(32), math.radians(-22), math.radians(-42))
    data = bpy.data.cameras.new('QA_eye'); camera = bpy.data.objects.new('QA_eye', data); scene.collection.objects.link(camera)
    camera.location = (-8.5, -8, eye_y)
    target = Vector((-40, 8, 4.5)); camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
    data.sensor_fit = 'VERTICAL'; data.sensor_height = 24.; data.lens = 24 / (2 * math.tan(math.radians(72 / 2)))
    data.clip_end = 2000; scene.camera = camera
    scene.view_settings.view_transform = 'AgX'
    args.render.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(args.render)
    bpy.ops.render.render(write_still=True)
if args.strict and not summary['pass']:
    raise RuntimeError('Torget actual-mesh QA failed; see ' + str(args.report))

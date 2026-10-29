"""Render changed materials from an in-memory scene copy. Never save torget.blend."""
from pathlib import Path
import json,sys
import bpy
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT.parent
sys.path.insert(0,str(ROOT))
from blender_finish import apply_finish
bpy.ops.wm.open_mainfile(filepath=str(HERE/'blender/torget.blend'))
materials={key:bpy.data.materials.get(name) for key,name in {
    'panel':'Painted_clapboard','cream':'Cream_clapboard','plaster':'Corpus_plaster',
    'metal':'Standing_seam_roof','grass':'Grass_ground',
}.items()}
materials={key:value for key,value in materials.items() if value is not None}
apply_finish(materials)
scene=bpy.context.scene
scene.cycles.device='CPU'
scene.cycles.samples=24
scene.cycles.max_bounces=4
scene.render.resolution_x=1200
scene.render.resolution_y=750
scene.render.resolution_percentage=100
for view in ['krakan','oversikt']:
    camera=bpy.data.objects.get('View_'+view)
    if camera is None: continue
    scene.camera=camera
    scene.render.filepath=str(ROOT/'finish'/('after_'+view+'.png'))
    bpy.ops.render.render(write_still=True)
# Also export a small material-only mesh to prove the nodes survive glTF.
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.data.objects:
    if obj.type=='MESH' and any(material in materials.values() for material in obj.data.materials):
        if obj.name.startswith('krakan_west'):
            obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'finish'/'qa_krakan_finish.glb'),
    export_format='GLB',use_selection=True,export_cameras=False,export_lights=False,
    export_apply=True,export_yup=True,export_materials='EXPORT')
print('FINISH_SCENE_QA_READY',ROOT/'finish')

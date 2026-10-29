"""Render/export a standalone wall with the three real interior proxy variants."""
from pathlib import Path
import json,math,sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT.parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE/'scripts'))
from blender_windows import add_interior,make_window_materials
from blender_materials import pbr_material,solid_material
from blender_finish import apply_painted_finish
from modelkit import Kit,color
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
kit=Kit();kit.window_materials=make_window_materials();kit.window_batch_name='Shared_Window_Interiors'
wall=pbr_material('plaster','QA_PaintedWall',base_color=color('#eeeae0'),normal_strength=.12)
wall['tile_size_m']=1.0;apply_painted_finish(wall)
trim=solid_material('QA_GreenTrim',color('#225747'),.62)
white=solid_material('QA_Offwhite',color('#e9e4d9'),.72)
glass=solid_material('QA_GlassAlpha20',color('#344b52'),.1,0)
glass.use_backface_culling=True;glass.surface_render_method='DITHERED'
glass.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value=.2
floor=solid_material('QA_Ground',color('#858477'),.9)
metrics=[]
labels=['Delvis gardin','Delvis persienn','Mörkt klart','Butiksdörr · ingen gardin']
for index,x in enumerate([-3.15,-1.05,1.05,3.15]):
    width=.95;height=1.8;bottom=.8;panel_width=2.1;wall_height=3.2
    # A real hole: two side piers plus a wall strip above/below the opening.
    for sign in [-1,1]:
        kit.box('QA_Wall',wall,(x+sign*(panel_width+width)/4,.07,wall_height/2),((panel_width-width)/2,.14,wall_height))
    kit.box('QA_Wall',wall,(x,.07,bottom/2),(width,.14,bottom))
    kit.box('QA_Wall',wall,(x,.07,(bottom+height+wall_height)/2),(width,.14,wall_height-bottom-height))
    at=lambda a,d,h,xx=x:(xx+a,-d,bottom+h)
    result=add_interior(kit,'QA_Window',at,(1,0),(0,-1),width,height,index==3,index)
    result['label']=labels[index];metrics.append(result)
    kit.face('QA_FrontGlass',glass,[at(-width/2,.025,0),at(width/2,.025,0),at(width/2,.025,height),at(-width/2,.025,height)],[(0,0),(1,0),(1,1),(0,1)])
    for a in [-width/2,width/2]:kit.box('QA_Frame',trim,at(a,.085,height/2),(.08,.12,height+.15))
    for h in [0,height]:kit.box('QA_Frame',trim,at(0,.085,h),(width+.16,.12,.08))
    kit.box('QA_Mullion',white,at(0,.09,height/2),(.035,.035,height-.05))
    for h in [height*.35,height*.68]:kit.box('QA_Mullion',white,at(0,.09,h),(width-.05,.035,.025))
    # Neutral labels are comparison annotation, not part of the game kit.
    data=bpy.data.curves.new('QA_Label','FONT');data.body=labels[index];data.align_x='CENTER';data.size=.13
    obj=bpy.data.objects.new('QA_Label',data);bpy.context.collection.objects.link(obj);obj.location=(x,-.08,3.03);obj.rotation_euler=(math.pi/2,0,0);obj.data.materials.append(trim)
kit.box('QA_Floor',floor,(0,-2,-.07),(12,9,.12))
kit.finish()
world=bpy.data.worlds.new('QA_Sky');world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.55,.68,.85,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6
bpy.context.scene.world=world
bpy.ops.object.light_add(type='SUN',location=(-6,-5,8));sun=bpy.context.object
sun.rotation_euler=(math.radians(30),math.radians(-20),math.radians(-35));sun.data.energy=2.5;sun.data.angle=math.radians(3)
bpy.ops.object.camera_add(location=(3.1,-11.6,3.3));camera=bpy.context.object
camera.rotation_euler=(Vector((0,0,1.65))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=44
scene=bpy.context.scene;scene.camera=camera;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=1800;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ROOT/'finish'/'windows_qa.png')
bpy.ops.render.render(write_still=True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'finish'/'qa_windows.glb'),export_format='GLB',export_cameras=False,export_lights=False,export_apply=True,export_materials='EXPORT')
(ROOT/'finish'/'windows_qa.json').write_text(json.dumps({'variants':metrics,'glass':'single-sided alpha 0.20, roughness 0.10; verify blending/sorting and shadows on phone',
    'geometry':'Real wall openings in this independent QA wall; no original scene loaded or saved.',
    'batching':'kit.window_batch_name can merge all opaque interiors into shared material batches across buildings.',
    'limits':'Only an 8cm visual cavity, not enterable rooms or a complete physical window assembly.'},ensure_ascii=False,indent=2)+'\n')
print('WINDOWS_QA_READY',ROOT/'finish'/'windows_qa.png')

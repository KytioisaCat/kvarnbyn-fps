"""Convert the licensed Quaternius soldier into a small, reproducible Godot asset.
Blender -b --python-exit-code 1 --python v2/kvarnbyn/blender/build_soldier.py [-- --preview]
"""
import bpy, json, hashlib, math, sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets-src/soldier/Swat.gltf'
OUT = ROOT / 'godot/assets/characters/soldier.glb'
REPORT = ROOT / 'evidence/soldier-model.json'
EXPECTED = '622b3f36fcac90539ef8f7121ec1f11b5e1ae603a085019b3fa96eba20dddfd3'
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != EXPECTED:
    raise RuntimeError('Soldier source hash does not match the licensed source receipt')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
# Imported custom bone shapes and the source pistol are not part of our rifle soldier.
for ob in list(bpy.data.objects):
    if ob.type == 'MESH' and (ob.parent != rig or ob.name == 'Pistol'):
        bpy.data.objects.remove(ob, do_unlink=True)
# Keep the authored faceting on hard armour; smooth fabric, skin and rounded helmet pieces.
for ob in rig.children:
    if ob.type == 'MESH':
        for poly in ob.data.polygons:
            poly.use_smooth = True
for mat in bpy.data.materials:
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Roughness'].default_value = .78 if mat.name != 'Visor' else .22
        bsdf.inputs['Metallic'].default_value = .04 if mat.name != 'Visor' else .35
# Runtime selects team material variants and animation, without duplicating mesh/skin data.
anim = rig.animation_data
for track in anim.nla_tracks:
    track.mute = True
anim.action = bpy.data.actions['Idle_Gun_Pointing']
bpy.context.scene.frame_set(0)
# Adapt the source's one-handed pistol clips to a shouldered two-hand rifle pose.
# IK is baked offline into ordinary rotation tracks; runtime needs no IK solver per soldier.
scene = bpy.context.scene
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
scene.frame_set(0)
bpy.context.view_layer.update()
def chest_target(name, position):
    ob = bpy.data.objects.new(name, None)
    scene.collection.objects.link(ob)
    ob.parent = rig; ob.parent_type = 'BONE'; ob.parent_bone = 'Chest'
    bpy.context.view_layer.update()
    ob.matrix_world.translation = Vector(position)
    bpy.context.view_layer.update()
    return ob
from mathutils import Quaternion
wrist_rotation=(rig.matrix_world @ rig.pose.bones['Wrist.R'].matrix).to_quaternion()
right = chest_target('RifleGrip_R', (-.146, -.115, 1.326))
left = chest_target('RifleGrip_L', (-.096, -.395, 1.367))
for ob,q in [(right,wrist_rotation),(left,Quaternion((wrist_rotation.w,wrist_rotation.x,-wrist_rotation.y,-wrist_rotation.z)) @ Quaternion((0,1,0),-math.pi/2))]:
    m=q.to_matrix().to_4x4();m.translation=ob.matrix_world.translation
    ob.matrix_world=m
    bpy.context.view_layer.update()
for side,target in [('R',right),('L',left)]:
    con=rig.pose.bones['Wrist.'+side].constraints.new('COPY_ROTATION')
    con.target=target;con.owner_space='WORLD';con.target_space='WORLD'
# Freeze both gripping hands from the source's closed pistol hand, mirroring the left.
finger_targets=[]
for pb in rig.pose.bones:
    if pb.name.endswith(('.L','.R')) and any(pb.name.startswith(prefix) for prefix in ['Index','Middle','Ring','Pinky','Thumb']):
        right_bone=rig.pose.bones.get(pb.name[:-2]+'.R')
        if right_bone:
            q=right_bone.rotation_quaternion.copy()
            target=bpy.data.objects.new('Grip_'+pb.name,None);scene.collection.objects.link(target)
            target.rotation_mode='QUATERNION'
            target.rotation_quaternion=Quaternion((q.w,q.x,-q.y,-q.z)) if pb.name.endswith('.L') else q
            con=pb.constraints.new('COPY_ROTATION');con.target=target;con.owner_space='LOCAL';con.target_space='LOCAL'
            finger_targets.append(target)
constraints = []
for side, target in [('R',right),('L',left)]:
    con = rig.pose.bones['LowerArm.'+side].constraints.new('IK')
    con.name='Rifle grip (baked)'; con.target=target; con.chain_count=2
    con.use_stretch=False
    constraints.append(con)
for bone in rig.data.bones:
    bone.select = bone.name in ['UpperArm.L','LowerArm.L','UpperArm.R','LowerArm.R','Wrist.L','Wrist.R'] or (bone.name.endswith(('.L','.R')) and any(bone.name.startswith(p) for p in ['Index','Middle','Ring','Pinky','Thumb']))
bpy.ops.object.mode_set(mode='POSE')
for action in bpy.data.actions:
    if action.name not in ['Idle','Idle_Gun','Idle_Gun_Pointing','Idle_Gun_Shoot','Run','Run_Shoot','Run_Back','Run_Left','Run_Right','Walk']:
        continue
    anim.action=action
    bpy.ops.nla.bake(frame_start=0, frame_end=math.ceil(action.frame_range.y), step=1,
        only_selected=True, visual_keying=True, clear_constraints=False, clear_parents=False,
        use_current_action=True, bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
for bone in rig.pose.bones:
    for con in list(bone.constraints): bone.constraints.remove(con)
for ob in [right,left]+finger_targets: bpy.data.objects.remove(ob,do_unlink=True)
anim.action = bpy.data.actions['Idle_Gun_Pointing']
scene.frame_set(0); bpy.context.view_layer.update()

# Animation root XY displacement would compete with CharacterBody3D. This pack is in-place;
# retain vertical hip movement and verify root drift explicitly in the build report.
root_drift = {}
for action in bpy.data.actions:
    curves = action.fcurves if hasattr(action, 'fcurves') else []
    for fc in curves:
        if fc.data_path == 'pose.bones["Root"].location' and fc.array_index in (0, 1):
            values = [k.co.y for k in fc.keyframe_points]
            if values: root_drift.setdefault(action.name, []).append(max(values)-min(values))
# Share the same authored Ak 5 silhouette between first and third person. Keep only the
# weapon itself; source hands/sleeves belong exclusively to the first-person view model.
rifle_source=ROOT/'godot/assets/weapons/ak5_view.glb'
if not rifle_source.exists():
    raise RuntimeError('Build build_ak5.py before build_soldier.py')
old=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(rifle_source))
new=set(bpy.data.objects)-old
for ob in list(new):
    if ob.name.startswith(('Firing_Hand','Support_Hand')):
        new.remove(ob);bpy.data.objects.remove(ob,do_unlink=True)
rifle=next(o for o in new if o.parent is None)
rifle.name='Soldier_Ak5'
rifle.rotation_euler.z=math.pi
rifle.scale=Vector((.78,.78,.78))
rifle.location=Vector((-.12,-.30,1.40))
bpy.context.view_layer.update()
world_matrix=rifle.matrix_world.copy()
rifle.parent=rig;rifle.parent_type='BONE';rifle.parent_bone='Chest'
bpy.context.view_layer.update()
rifle.matrix_world=world_matrix
bpy.context.view_layer.update()

# glTF's NLA export uses the track/action names; each strip becomes a separate named clip.
anim.action = None
for track in anim.nla_tracks:
    track.mute = False
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(OUT), export_format='GLB', export_animations=True,
    export_animation_mode='NLA_TRACKS', export_nla_strips=True, export_skins=True,
    export_def_bones=True, export_yup=True, export_apply=False,
    export_materials='EXPORT', export_cameras=False, export_lights=False)
triangles = sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in rig.children_recursive if ob.type=='MESH')
report = {'source_sha256': EXPECTED, 'source_bytes': SOURCE.stat().st_size,
          'output_bytes': OUT.stat().st_size, 'sha256': hashlib.sha256(OUT.read_bytes()).hexdigest(),
          'triangles': triangles, 'bones': len(rig.data.bones),
          'animations': {a.name: round((a.frame_range.y-a.frame_range.x)/bpy.context.scene.render.fps,4) for a in bpy.data.actions},
          'root_xy_drift_m': root_drift, 'forward_axis': '+Z (runtime visual rotates 180 degrees)',
          'license': 'CC0-1.0', 'author': 'Quaternius',
          'modifications': ['removed source pistol and custom bone shape', 'smooth normals', 'PBR roughness/metal calibration', 'baked two-hand rifle upper-body IK on locomotion clips']}
REPORT.write_text(json.dumps(report, indent=2)+'\n')
print('KVARNBYN_SOLDIER_MODEL',json.dumps(report))
if '--preview' in sys.argv:
    for track in anim.nla_tracks: track.mute=True
    scene=bpy.context.scene
    scene.render.engine='CYCLES'; scene.cycles.samples=24
    scene.render.resolution_x=960;scene.render.resolution_y=960;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('World');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.38,.46,.55,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6
    bpy.ops.object.light_add(type='AREA',location=(2,-4,5));bpy.context.object.data.energy=700;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=4
    bpy.ops.object.camera_add(location=(2.6,-4.5,2.3));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,.95))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=60;scene.camera=cam
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.02));floor=bpy.context.object
    m=bpy.data.materials.new('Ground');m.diffuse_color=(.16,.19,.2,1);floor.data.materials.append(m)
    for clip,frame in [('Idle_Gun_Pointing',18),('Run_Shoot',10),('Run_Left',10),('Death',25)]:
        anim.action=bpy.data.actions[clip];scene.frame_set(frame)
        scene.render.filepath=str(ROOT/'evidence'/f'soldier_blender_{clip}.png');bpy.ops.render.render(write_still=True)

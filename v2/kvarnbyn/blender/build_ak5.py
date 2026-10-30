"""Author a cosmetic first-person Ak 5 model and export it to Godot.

Run from the repository root:
  v2/.tools/Blender.app/Contents/MacOS/Blender -b --python v2/kvarnbyn/blender/build_ak5.py

Reference: Swedish Army Museum AM.009994 (1986 Ak 5), observed as visual reference.
No photograph is embedded. Shapes/proportions are authored for a game, not CAD.
Blender +Y is forward and +Z up; glTF becomes Godot -Z forward and +Y up.
"""
from pathlib import Path
from collections import defaultdict
import json,math,sys
import bpy
from mathutils import Vector

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent
OUT=PROJECT/'godot/assets/weapons'
QA=PROJECT/'evidence/weapon'
OUT.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)


def srgb(hex_color):
    c=[int(hex_color[i:i+2],16)/255 for i in (1,3,5)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)+(1,)


def material(name,color,roughness,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=srgb(color)
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=srgb(color);p.inputs['Roughness'].default_value=roughness;p.inputs['Metallic'].default_value=metal
    return m

M={
    'receiver':material('Ak5_Parkerized_Olive','#4e5846',.38,.52),
    'polymer':material('Ak5_Green_Polymer','#485b37',.61),
    'rib':material('Ak5_Moulded_Green','#3a4b2d',.58),
    'steel':material('Ak5_Burnished_Steel','#242a2b',.32,.82),
    'edge':material('Ak5_Machined_Edges','#555b57',.27,.86),
    'recess':material('Ak5_Recesses','#111715',.76,.18),
    'magazine':material('Ak5_Magazine_Steel','#555a51',.42,.68),
    'rubber':material('Ak5_Rubber','#1c211d',.83),
    'glove':material('Ak5_Gloves','#625e48',.84),
    'seam':material('Ak5_Glove_Seams','#454734',.92),
    'sleeve':material('Ak5_Field_Sleeve','#526344',.90),
}
GROUPS=defaultdict(list)


def register(obj,name,mat,group='Body',smooth=False):
    obj.name=name;obj.data.materials.append(M[mat])
    for polygon in obj.data.polygons:polygon.use_smooth=smooth
    GROUPS[group].append(obj)
    return obj


def bevel(obj,amount=.002,segments=2):
    if amount<=0:return obj
    mod=obj.modifiers.new('Soft machined edges','BEVEL');mod.width=amount;mod.segments=segments
    mod.affect='EDGES'
    mod=obj.modifiers.new('Weighted face normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=40
    return obj


def box(name,center,size,mat='receiver',radius=.002,rot=(0,0,0),group='Body'):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center,rotation=rot)
    obj=bpy.context.object;obj.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    register(obj,name,mat,group)
    return bevel(obj,radius)


def mesh(name,vertices,faces,mat='receiver',group='Body',radius=0,smooth=False):
    data=bpy.data.meshes.new(name+'_Mesh');data.from_pydata(vertices,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    register(obj,name,mat,group,smooth)
    return bevel(obj,radius)


def prism(name,profile,width,mat='receiver',group='Body',radius=.0015):
    """Extrude an artistic Y/Z silhouette across X."""
    vertices=[(x,y,z) for x in [-width/2,width/2] for y,z in profile]
    n=len(profile)
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    for i in range(n):
        j=(i+1)%n;faces.append((i,j,n+j,n+i))
    return mesh(name,vertices,faces,mat,group,radius)


def tube(name,a,b,radius,mat='steel',sides=20,group='Body',radius2=None):
    a,b=Vector(a),Vector(b);axis=b-a
    bpy.ops.mesh.primitive_cone_add(vertices=sides,radius1=radius if radius2 is None else radius2,radius2=radius,depth=axis.length,location=(a+b)/2)
    obj=bpy.context.object;obj.rotation_euler=axis.to_track_quat('Z','Y').to_euler()
    register(obj,name,mat,group,True)
    return bevel(obj,min(.001,radius*.15),2)


def path_tube(name,points,radius,mat='steel',group='Body',sides=8):
    vertices=[]
    for i,p in enumerate(points):
        tangent=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])
        tangent.normalize();guide=Vector((1,0,0)) if abs(tangent.x)<.8 else Vector((0,1,0))
        u=tangent.cross(guide).normalized();v=tangent.cross(u)
        vertices.extend(tuple(Vector(p)+radius*(u*math.cos(j*math.tau/sides)+v*math.sin(j*math.tau/sides))) for j in range(sides))
    faces=[]
    for i in range(len(points)-1):
        for j in range(sides):
            jj=(j+1)%sides;faces.append((i*sides+j,i*sides+jj,(i+1)*sides+jj,(i+1)*sides+j))
    faces.extend([tuple(range(sides-1,-1,-1)),tuple((len(points)-1)*sides+j for j in range(sides))])
    return mesh(name,vertices,faces,mat,group,smooth=True)


def ring(name,center,outer,inner,depth,mat='steel',segments=32,group='Body'):
    """A real sight aperture, aligned along the barrel (Y)."""
    cx,cy,cz=center;verts=[]
    for y in [cy-depth/2,cy+depth/2]:
        for r in [outer,inner]:
            verts.extend((cx+r*math.cos(i*math.tau/segments),y,cz+r*math.sin(i*math.tau/segments)) for i in range(segments))
    faces=[]
    for i in range(segments):
        j=(i+1)%segments
        faces.extend([(i,j,2*segments+j,2*segments+i),(segments+j,segments+i,3*segments+i,3*segments+j),
            (j,i,segments+i,segments+j),(2*segments+i,2*segments+j,3*segments+j,3*segments+i)])
    return mesh(name,verts,faces,mat,group,smooth=True)


# Folded/stamped receiver, with distinct top cover and lower magwell profile.
prism('Receiver_shell',[(-.174,-.026),(-.174,.050),(-.143,.073),(.102,.073),(.141,.048),(.141,-.034),(.034,-.054),(-.083,-.054),(-.105,-.027)],.060,'receiver',radius=.003)
prism('Pressed_top_cover',[(-.169,.054),(-.135,.080),(.105,.080),(.129,.065),(.129,.052),(-.169,.052)],.047,'receiver',radius=.002)
box('Top_cover_spine',(0,-.016,.080),(.025,.262,.007),'receiver',.002)
for side in [-1,1]:
    box('Receiver_lower_flange',(side*.030,-.017,-.025),(.005,.25,.011),'receiver',.001)
    # A stamped seam and flat side panel give the body a continuous silhouette.
    box('Receiver_side_seam',(side*.031,-.014,.055),(.002,.263,.004),'steel',.0005)
    for y in [-.135,.107]:tube('Receiver_pin',(side*.030,y,-.009),(side*.034,y,-.009),.0042,'edge',16)
# Cosmetic ejection opening/charging handle, no internal or functional geometry.
box('Ejection_port',(0.0314,-.006,.027),(.002,.108,.027),'recess',.002)
box('Ejection_lip',(0.034,-.008,.044),(.006,.113,.006),'receiver',.001)
box('Bolt_visible',(0.0325,-.018,.028),(.002,.072,.016),'steel',.001)
tube('Charging_handle_stem',(.032,-.035,.043),(.058,-.035,.043),.004,'steel',12,group='Bolt')
box('Charging_handle_knob',(.059,-.035,.043),(.018,.020,.013),'steel',.004,group='Bolt')
# Opposite side selector and small shallow stamped marks.
tube('Selector_pin',(-.031,-.117,-.002),(-.036,-.117,-.002),.005,'steel',16)
box('Selector_lever',(-.036,-.102,-.005),(.006,.036,.007),'steel',.002,rot=(.1,0,0))
for y in [-.125,-.108,-.091]:box('Selector_marks',(-.0316,y,.012),(.001,.005,.0016),'edge',.0003)

# Magwell joins the receiver rather than floating below a box.
prism('Magazine_well',[(-.016,-.034),(.067,-.034),(.063,-.087),(-.015,-.087)],.049,'receiver',radius=.0025)
box('Magazine_catch',(.030,.029,-.055),(.008,.024,.012),'steel',.0015)
# Pistol grip: tapered and raked, with a rounded heel.
prism('Pistol_grip',[(-.130,-.040),(-.083,-.048),(-.110,-.176),(-.160,-.180),(-.176,-.157)],.040,'polymer',radius=.006)
for i in range(5):
    z=-.095-i*.013;y=-.108-(abs(z)-.095)*.44
    for side in [-1,1]:box('Grip_moulding',(side*.0208,y,z),(.0018,.032,.0022),'rib',.0005,rot=(.35,0,0))
# Trigger guard is an open loop, with room to see the curved cosmetic trigger.
path_tube('Trigger_guard',[(-.021,-.102,-.053),(-.021,-.100,-.104),(-.021,-.081,-.116),(-.021,-.020,-.114),(-.021,-.008,-.097),(-.021,-.008,-.070)],.003,'steel',sides=8)
path_tube('Trigger',[(-.002,-.072,-.054),(-.002,-.074,-.080),(-.002,-.064,-.094)],.0022,'steel',sides=8)

# Tapered green handguard, an oval/flattened moulding with diagonal tactile ribs.
verts=[]
sections=[(.112,.030,.047),(.130,.035,.048),(.292,.032,.044),(.335,.027,.040)]
profile=[(-.72,-1),(.72,-1),(1,-.65),(1,.52),(.66,1),(-.66,1),(-1,.52),(-1,-.65)]
for y,w,h in sections:verts.extend((x*w,y,.018+z*h) for x,z in profile)
faces=[tuple(range(7,-1,-1)),tuple(24+i for i in range(8))]
for k in range(3):
    for i in range(8):faces.append((k*8+i,k*8+(i+1)%8,(k+1)*8+(i+1)%8,(k+1)*8+i))
mesh('Green_handguard',verts,faces,'polymer',radius=.003)
box('Handguard_top_strip',(0,.222,.069),(.036,.217,.012),'steel',.002)
for y in [.143,.166,.189,.212,.235,.258,.281,.304]:
    for side in [-1,1]:
        pts=[(side*.026,y-.005,-.025),(side*.035,y+.004,-.005),(side*.034,y+.013,.025),(side*.025,y+.022,.050)]
        path_tube('Handguard_diagonal_rib',pts,.0014,'rib',sides=6)
for side in [-1,1]:
    for y in [.151,.185,.219]:box('Handguard_vent',(side*.0354,y,.034),(.0015,.015,.006),'recess',.002)
for y in [.145,.183,.221,.259,.297]:box('Top_vent',(0,y,.0756),(.018,.015,.001),'recess',.001)

# Exposed barrel, gas tube silhouette, front sight base and vented flash hider.
tube('Barrel',(0,.304,.018),(0,.568,.018),.0098,'steel',24)
tube('Gas_tube',(0,.303,.061),(0,.435,.061),.008,'receiver',20)
tube('Barrel_collar',(0,.337,.018),(0,.362,.018),.014,'steel',24)
box('Front_sight_base',(0,.430,.058),(.032,.027,.079),'receiver',.003)
ring('Front_sight_hood',(0,.432,.117),.015,.011,.015,'steel',32)
box('Front_sight_post',(0,.432,.105),(.0025,.005,.024),'steel',.0004)
tube('Front_sight_crosspin',(-.025,.430,.059),(.025,.430,.059),.004,'edge',16)
tube('Barrel_step',(0,.529,.018),(0,.568,.018),.0125,'steel',24)
# Hollow rim and dark central opening are readable from side/reload views.
ring('Flash_hider',(0,.590,.018),.016,.009,.054,'steel',32)
ring('Flash_hider_front_rim',(0,.619,.018),.0165,.010,.006,'edge',32)
for a in [0,math.pi/2,math.pi,math.pi*1.5]:
    x=.0161*math.cos(a);z=.018+.0161*math.sin(a)
    box('Flash_hider_slot',(x,.589,z),(.007,.030,.002),'recess',.001,rot=(0,a-math.pi/2,0))
# Rear aperture and guarding ears. Sight centers and front tip are both z=.117.
box('Rear_sight_base',(0,-.139,.087),(.040,.044,.020),'receiver',.002)
for side in [-1,1]:prism('Rear_sight_ear',[(-.161,.087),(-.159,.123),(-.141,.126),(-.123,.115),(-.121,.087)],.007,'steel',radius=.001)
# Move the two identical prisms to the actual sides after construction.
for obj,side in zip(GROUPS['Body'][-2:],[-1,1]):obj.location.x=side*.0165
ring('Rear_sight_aperture',(0,-.142,.117),.008,.0048,.008,'steel',24)
box('Rear_sight_stem',(0,-.143,.101),(.010,.011,.018),'steel',.001)

# Classic folding stock: two sparse struts and the distinct vertical rubber butt.
box('Stock_hinge',(0,-.180,.017),(.054,.027,.080),'receiver',.004)
tube('Stock_upper_strut',(0,-.190,.042),(0,-.397,.018),.0095,'receiver',16)
tube('Stock_lower_strut',(0,-.195,-.036),(0,-.396,-.077),.0085,'receiver',16)
tube('Stock_diagonal',(0,-.202,-.038),(0,-.393,.016),.0065,'receiver',16)
prism('Butt_frame',[(-.405,.045),(-.384,.038),(-.391,-.107),(-.416,-.111),(-.423,-.092)],.036,'receiver',radius=.004)
prism('Rubber_buttpad',[(-.422,.044),(-.408,.041),(-.414,-.112),(-.428,-.109)],.043,'rubber',radius=.003)
for z in [.018,-.005,-.028,-.051,-.074,-.097]:box('Buttpad_rib',(0,-.428,z),(.039,.002,.002),'rubber',.0005)
ring('Rear_sling_loop',(.024,-.390,.037),.007,.0045,.004,'steel',16)

# Slightly curved 30-round steel magazine, intentionally not an AK banana shape.
mag_profile=[(-.013,-.068),(.057,-.068),(.060,-.121),(.077,-.228),(.068,-.262),(.010,-.267),(.001,-.223),(-.007,-.145)]
prism('Magazine',mag_profile,.035,'magazine','Magazine',.002)
for side in [-1,1]:
    for offset in [.0,.020,.040]:
        pts=[(side*.0182,.006+offset,-.096),(side*.0188,.009+offset,-.142),(side*.0188,.022+offset,-.225),(side*.0185,.023+offset,-.250)]
        path_tube('Magazine_stamped_rib',pts,.0011,'steel','Magazine',6)
box('Magazine_floorplate',(0,.040,-.266),(.041,.064,.008),'steel',.002,group='Magazine')

# Gloved hands are rounded articulated forms, with a loose cloth cuff/sleeve.
def ellipsoid(name,center,size,mat='glove',group='Hands'):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=1,location=center)
    obj=bpy.context.object;obj.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return register(obj,name,mat,group,True)

ellipsoid('Right_glove_palm',(.034,-.137,-.095),(.026,.039,.043))
for j in range(4):
    y=-.115-j*.015
    path_tube('Right_glove_finger',[(.042,y,-.082),(.023,y-.004,-.069),(-.001,y-.008,-.074),(-.012,y-.010,-.090)],.007,'glove','Hands',8)
    ellipsoid('Right_knuckle',(.049,y,-.087),(.008,.009,.012),'seam')
path_tube('Right_thumb',[(.032,-.109,-.108),(.007,-.092,-.091),(-.010,-.100,-.074)],.009,'glove','Hands',10)
tube('Right_cuff',(.050,-.176,-.131),(.064,-.217,-.155),.031,'seam',16,'Hands',.033)
tube('Right_sleeve',(.064,-.210,-.154),(.122,-.430,-.245),.040,'sleeve',20,'Hands',.053)
ellipsoid('Support_glove_palm',(-.031,.247,-.042),(.029,.045,.026),'glove','SupportHand')
for j in range(4):
    y=.214+j*.020
    path_tube('Support_fingers',[(-.037,y,-.037),(-.045,y,-.009),(-.030,y,.010),(-.012,y,.011)],.0075,'glove','SupportHand',8)
path_tube('Support_thumb',[(-.010,.277,-.048),(.020,.267,-.041),(.025,.240,-.030)],.009,'glove','SupportHand',10)
tube('Support_cuff',(-.049,.216,-.064),(-.069,.179,-.094),.030,'seam',16,'SupportHand',.032)
tube('Support_sleeve',(-.070,.178,-.094),(-.125,-.076,-.275),.040,'sleeve',20,'SupportHand',.050)

# Apply bevels then merge static parts into a few material batches.
assembled={}
for group,objects in GROUPS.items():
    for obj in objects:
        bpy.context.view_layer.objects.active=obj
        for modifier in list(obj.modifiers):
            try:bpy.ops.object.modifier_apply(modifier=modifier.name)
            except RuntimeError:pass
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.join()
    obj=bpy.context.object;obj.name={'Body':'Ak5_Body','Hands':'Firing_Hand','SupportHand':'Support_Hand','Bolt':'Charging_Handle'}.get(group,group)
    # Keep dynamic component origins in coherent local coordinates.
    origin=Vector((0,.019,-.068)) if group=='Magazine' else Vector((.045,-.035,.043)) if group=='Bolt' else Vector((0,0,0))
    matrix=obj.matrix_world.copy()
    for vertex in obj.data.vertices:vertex.co=matrix@vertex.co-origin
    obj.matrix_world.identity();obj.location=origin
    assembled[group]=obj
root=bpy.data.objects.new('Ak5_View',None);bpy.context.collection.objects.link(root)
for obj in assembled.values():obj.parent=root
# Named glTF nodes become exact Godot-local placement references.
anchors={
    'Muzzle':(0,.623,.018),
    'Sight_Rear':(0,-.142,.117),
    'Sight_Front':(0,.432,.117),
}
for name,location in anchors.items():
    marker=bpy.data.objects.new(name,None);marker.location=location;marker.empty_display_size=.01;marker.parent=root;bpy.context.collection.objects.link(marker)
root['model_note']='Own authored cosmetic game model, observed from Swedish Army Museum AM.009994; no reference image embedded.'
root['sight_height_m']=.117
bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
for obj in root.children:obj.select_set(True)
bpy.context.view_layer.objects.active=root
path=OUT/'ak5_view.glb'
bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True,export_cameras=False,export_lights=False,export_materials='EXPORT')
triangles=sum(sum(len(p.vertices)-2 for p in obj.data.polygons) for obj in assembled.values())
report={'asset':'ak5_view.glb','bytes':path.stat().st_size,'triangles':triangles,'objects':len(assembled),'materials':len(M),
    'axes':'Godot -Z forward, +Y up, meters','sight_height_m':.117,'muzzle_godot':[0,.018,-.623],
    'reference':'Swedish Army Museum AM.009994, 1986 Ak 5; artistic silhouette reference only',
    'anchors_godot':{key:[p[0],p[2],-p[1]] for key,p in anchors.items()}}
(QA/'model_metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('AK5_MODEL',json.dumps(report),flush=True)
if '--render' in args:
    world=bpy.data.worlds.new('Preview_world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.65,.75,.88,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45;bpy.context.scene.world=world
    for location,energy,size in [((.5,.15,1),70,.8),((-.5,-.3,.7),45,.7)]:
        bpy.ops.object.light_add(type='AREA',location=location);light=bpy.context.object;light.data.energy=energy;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add(location=(1.05,.83,.64));cam=bpy.context.object;cam.rotation_euler=(Vector((0,.08,-.015))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=54
    scene=bpy.context.scene;scene.camera=cam;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(QA/'ak5_model.png')
    bpy.ops.render.render(write_still=True)

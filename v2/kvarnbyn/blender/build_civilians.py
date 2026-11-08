"""Own stylised civilian likenesses from the documented reference observations.

No portrait pixels, soldier meshes, guns or downloaded animation packs. All
geometry, materials and five civilian animation clips are authored here.
Blender -b --python-exit-code 1 --python build_civilians.py
"""
from pathlib import Path
import bpy, math, json, random, hashlib
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'godot/assets/characters'
OUT.mkdir(parents=True, exist_ok=True)
reports = []


def material(name, hexcolor, rough=.8, metal=0.):
    h=hexcolor.lstrip('#'); srgb=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    rgba=tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in srgb)+(1,)
    m=bpy.data.materials.new(name);m.diffuse_color=rgba;m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=rgba
    p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    return m


def bind(obj, mat, bone='Chest'):
    obj.data.materials.append(mat)
    for face in obj.data.polygons:face.use_smooth=True
    group=obj.vertex_groups.new(name=bone);group.add(list(range(len(obj.data.vertices))),1.,'REPLACE')
    mod=obj.modifiers.new('Civilian skin','ARMATURE');mod.object=rig
    obj.parent=rig
    return obj


def mesh(name, verts, faces, mat, bone='Chest'):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob)
    return bind(ob,mat,bone)


def ellipsoid(name, p, size, mat, bone='Head', segments=24, rings=14):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=p)
    ob=bpy.context.object;ob.name=name;ob.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return bind(ob,mat,bone)


def box(name,p,size,mat,bone='Chest',bevel=.01):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p)
    ob=bpy.context.object;ob.name=name;ob.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=ob.modifiers.new('Soft tailored edges','BEVEL');mod.width=bevel;mod.segments=2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return bind(ob,mat,bone)


def tube(name, points, radius, mat, bone='Head', sides=7):
    verts=[]
    for i,p in enumerate(points):
        p=Vector(p);axis=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])).normalized()
        aux=Vector((0,0,1)) if abs(axis.z)<.95 else Vector((1,0,0))
        u=axis.cross(aux).normalized();v=axis.cross(u)
        for j in range(sides):verts.append(p+radius*(u*math.cos(j*math.tau/sides)+v*math.sin(j*math.tau/sides)))
    faces=[(i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j) for i in range(len(points)-1) for j in range(sides)]
    faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))])
    return mesh(name,verts,faces,mat,bone)


def rings(name, sections, mat, bone='Chest', sides=32):
    # Sections: height, X radius, Y radius, Y centre. True volume, not flat cards.
    verts=[(rx*math.cos(j*math.tau/sides),cy+ry*math.sin(j*math.tau/sides),z) for z,rx,ry,cy in sections for j in range(sides)]
    faces=[(i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j) for i in range(len(sections)-1) for j in range(sides)]
    faces.extend([tuple(reversed(range(sides))),tuple((len(sections)-1)*sides+j for j in range(sides))])
    return mesh(name,verts,faces,mat,bone)


def limb(name,a,b,r1,r2,mat,bone):
    a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,1,0))).normalized();v=axis.cross(u)
    verts=[p+radius*(u*math.cos(j*math.tau/16)+v*math.sin(j*math.tau/16)) for p,radius in [(a,r1),(b,r2)] for j in range(16)]
    faces=[(j,(j+1)%16,16+(j+1)%16,16+j) for j in range(16)]
    faces.extend([tuple(reversed(range(16))),tuple(range(16,32))])
    return mesh(name,verts,faces,mat,bone)


def make_rig():
    data=bpy.data.armatures.new('CivilianSkeleton');ob=bpy.data.objects.new('CivilianRig',data)
    bpy.context.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    definitions=[('Root',(0,0,0),(0,0,.15),None),('Hips',(0,0,.91),(0,0,1.08),'Root'),('Chest',(0,0,1.08),(0,0,1.42),'Hips'),('Head',(0,0,1.43),(0,0,1.79),'Chest')]
    for side,s in [('L',1),('R',-1)]:
        definitions += [('UpperArm.'+side,(s*.24,0,1.39),(s*.29,0,1.11),'Chest'),('Forearm.'+side,(s*.29,0,1.11),(s*.31,-.015,.87),'UpperArm.'+side),('Hand.'+side,(s*.31,-.015,.87),(s*.31,-.015,.76),'Forearm.'+side),('Thigh.'+side,(s*.105,0,.94),(s*.105,0,.52),'Hips'),('Shin.'+side,(s*.105,0,.52),(s*.105,0,.12),'Thigh.'+side),('Foot.'+side,(s*.105,0,.12),(s*.105,-.16,.075),'Shin.'+side)]
    for name,head,tail,parent in definitions:
        bone=data.edit_bones.new(name);bone.head=head;bone.tail=tail
        if parent:bone.parent=data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob


def face(profile):
    width=profile['head_width']; bottom=1.49;top=1.81
    rings('Face_shape',[(bottom,.055,.06,0),(1.53,width*.77,.078,-.01),(1.59,width,.096,0),(1.67,width,.103,.005),(1.74,width*.91,.094,.01),(1.79,width*.65,.067,.014),(top,.025,.025,.014)],skin,'Head',40)
    ellipsoid('Neck',(0,0,1.46),(.065,.063,.095),skin)
    for s in [-1,1]:
        ellipsoid('Ear',(s*(width+.004),.001,1.638),(.023,.016,.043),skin)
        ellipsoid('Ear_inner',(s*(width+.009),-.014,1.638),(.011,.003,.026),skin_shadow)
        x=s*.049;z=1.674
        ellipsoid('Eye_socket',(x,-.089,z),(.030,.012,.017),skin_shadow)
        ellipsoid('Eye_white',(x,-.102,z),(.021,.008,.0095),ivory)
        ellipsoid('Iris',(x,-.109,z),(.008,.0025,.008),iris)
        ellipsoid('Pupil',(x,-.111,z),(.0038,.0015,.0047),dark)
        tube('Upper_lid',[(x-.022,-.108,z),(x,-.112,z+.010),(x+.022,-.108,z)],.0035,skin)
        tube('Eyebrow',[(x-.025,-.101,z+.026),(x,-.108,z+.031),(x+.025,-.100,z+.026)],.0045,hair)
        ellipsoid('Cheek',(s*.072,-.073,1.617),(.027,.010,.025),skin)
    nose=profile['nose']
    ellipsoid('Nose_bridge',(0,-.105,1.648),(.018,.024,.043),skin)
    ellipsoid('Nose_tip',(0,-.132,1.617),nose,skin)
    for s in [-1,1]:
        ellipsoid('Nostril',(s*nose[0]*.7,-.14,1.602),(.005,.004,.003),skin_shadow)
    mouth_width=.046 if profile['id']=='per' else .031
    ellipsoid('Mouth',(0,-.094,1.568),(mouth_width,.014,.015 if profile['id']=='per' else .006),mouth)
    tube('Lower_lip',[(-mouth_width,-.102,1.568),(0,-.110,1.558),(mouth_width,-.102,1.568)],.0045,lips)
    if profile['id']=='per':box('Smile_teeth',(0,-.109,1.575),(.065,.006,.008),ivory,'Head',.002)
    if profile['id'] in ['lars','per']:
        beard=material('White_beard' if profile['id']=='lars' else 'Salt_pepper_stubble','#e5e3d9' if profile['id']=='lars' else '#636057')
        if profile['id']=='lars':
            rings('Long_white_beard',[(1.12,.035,.027,-.094),(1.18,.088,.057,-.10),(1.31,.137,.072,-.092),(1.45,.145,.070,-.075),(1.55,.112,.045,-.073),(1.59,.065,.030,-.09)],beard,'Head')
            # Wisps and streaks give a tapered uneven beard silhouette.
            rng=random.Random(54)
            for n in range(42):
                x=rng.uniform(-.12,.12);z=1.50+rng.uniform(-.07,.07);end=z-rng.uniform(.18,.36)
                tube('Beard_wisp',[(x,-.115,z),(x*.9,-.166,z-.10),(x*.68,-.145,end)],rng.uniform(.002,.004),beard)
            for s in [-1,1]:
                ellipsoid('Beard_cheek',(s*.103,-.048,1.56),(.033,.046,.084),beard)
        else:
            ellipsoid('Stubble_chin',(0,-.075,1.531),(.075,.043,.033),beard)
            for s in [-1,1]:ellipsoid('Stubble_jaw',(s*.075,-.046,1.56),(.035,.028,.048),beard)
        for s in [-1,1]:ellipsoid('Moustache',(s*.023,-.105,1.592),(.031,.012,.011),beard)


def hair_and_hat(profile):
    if profile['id']=='linnea':
        # Shoulder-length parted hair, face opening and lighter tips from refs.
        verts=[];rows=14;sides=48
        for i in range(rows):
            t=i/(rows-1)
            for j in range(sides):
                a=j*math.tau/sides;front=max(0.,-math.sin(a))
                # The centre front opens above eyebrows; side/back reach shoulders.
                lower=1.36+.365*front**5
                z=1.827*(1-t)+lower*t
                bulge=math.sqrt(max(0.0,1.0-((z-1.69)/.15)**2)) if z>1.69 else 1.0
                rx=.144*bulge+.006;ry=.132*bulge+.006
                verts.append((rx*math.cos(a),.027+ry*math.sin(a),z))
        ob=mesh('Shoulder_length_parted_hair',verts,[tuple(reversed((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))) for i in range(rows-1) for j in range(sides)]+[tuple(range(sides))],hair)
        warm=material('Hair_light_tips','#9b7549');ob.data.materials.append(warm)
        for p in ob.data.polygons:
            if p.center.z<1.48:p.material_index=1
        for s in [-1,1]:
            for n in range(8):
                x=s*(.088+n*.007)
                tube('Hair_strand',[(x*.6,-.07,1.79),(x,-.103,1.65),(x*1.08,-.080,1.48),(x*.97,-.038,1.38)],.0035,hair if n%2 else warm)
        return
    if profile['id']=='per':
        # Receding curly hairline and grey temples, not a closed helmet mesh.
        rng=random.Random(76)
        for n in range(58):
            a=rng.uniform(0,math.tau);front=max(0,-math.sin(a));z=1.745+rng.uniform(0,.045)+front*.015
            x=.109*math.cos(a);y=.012+.090*math.sin(a)
            ellipsoid('Hair_curl',(x,y,z),(.024,.019,.020),hair,segments=12,rings=8)
        grey=material('Grey_temples','#77736b')
        for s in [-1,1]:ellipsoid('Temple',(s*.111,.015,1.69),(.012,.045,.047),grey)
        return
    for s in [-1,1]:ellipsoid('Side_hair',(s*.116,.015,1.69),(.014,.053,.043),hair)
    leather=profile['id']=='ronny'
    cap=material('Black_leather_cap' if leather else 'Navy_cloth_cap','#171b1d' if leather else '#292c36',.36 if leather else .95)
    ellipsoid('Cap_crown',(0,.012,1.785),(.145,.135,.067 if leather else .055),cap)
    ellipsoid('Cap_peak',(0,-.116,1.768),(.150,.114,.013),cap)
    band=material('Cap_band','#101318',.42)
    rings('Cap_band',[(1.738,.143,.125,.012),(1.762,.145,.128,.012)],band,'Head')
    if leather:
        for i in range(23):
            a=math.pi+i*math.pi/22
            ellipsoid('Cap_chain',(.142*math.cos(a),.012+.130*math.sin(a),1.764),(.005,.005,.004),metal,segments=8,rings=6)
    if profile['id']=='lars':
        for s in [-1,1]:
            x=s*.05
            points=[(x+.039*math.cos(i*math.tau/32),-.122,1.674+.029*math.sin(i*math.tau/32)) for i in range(33)]
            tube('Round_spectacles',points,.0018,metal)
            tube('Spectacle_arm',[(s*.089,-.12,1.675),(s*.123,-.03,1.680),(s*.12,.016,1.67)],.002,metal)
        tube('Spectacle_bridge',[(-.010,-.124,1.674),(0,-.132,1.682),(.010,-.124,1.674)],.0018,metal)


def body(profile):
    pid=profile['id'];width=profile['width'];jacket=material('Outerwear_'+pid,profile['coat'],.43 if pid=='ronny' else .93)
    shirt=material('Shirt_'+pid,profile['shirt']);pants=material('Trousers_'+pid,profile['pants'])
    shoe=material('Shoes_'+pid,'#e2dfd5' if pid=='linnea' else '#292b2d',.8)
    sections={
        'lars':[(.90,.150,.085,0),(1.02,.157,.092,0),(1.19,.170,.094,0),(1.36,.182,.090,0),(1.43,.130,.075,0)],
        'per':[(.90,.200,.123,0),(1.02,.230,.153,0),(1.19,.244,.145,0),(1.36,.240,.131,0),(1.43,.160,.100,0)],
        'ronny':[(.90,.255,.180,-.018),(1.02,.285,.230,-.040),(1.16,.292,.224,-.038),(1.29,.275,.188,-.016),(1.39,.270,.153,0),(1.44,.170,.110,0)],
        'linnea':[(.90,.232,.137,0),(1.00,.219,.128,0),(1.13,.175,.113,0),(1.27,.211,.147,-.014),(1.36,.210,.125,0),(1.43,.140,.090,0)],
    }[pid]
    outer=rings('Tailored_torso',sections,jacket)
    outer.data.materials.append(skin if pid=='ronny' else shirt)
    # Open jackets reveal a shirt/chest at the front. Distinct actual volumes.
    for p in outer.data.polygons:
        if p.normal.y<-.35 and abs(p.center.x)<(.13 if pid=='ronny' else .105) and pid in ['per','ronny','lars']:p.material_index=1
    if pid in ['per','ronny','lars']:
        lapel=material('Lapel_'+pid,profile['coat'],.4 if pid=='ronny' else .9)
        for s in [-1,1]:
            mesh('Jacket_lapel',[(s*.075,-.105,1.43),(s*.175,-.122,1.36),(s*.105,-.164,1.20),(s*.065,-.13,1.34)],[(0,1,2,3)],lapel)
            box('Jacket_pocket',(s*.16,-.121,1.06),(.085,.013,.08),jacket,bevel=.006)
        for z in [1.02,1.13]:ellipsoid('Jacket_button',(.106,-.152,z),(.009,.005,.009),metal,'Chest',12,8)
    else:
        rings('Sweatshirt_collar',[(1.414,.080,.078,0),(1.44,.075,.07,0)],jacket)
        box('Sweatshirt_hem',(0,0,.931),(width*1.64,.24,.047),jacket)
    for side,s in [('L',1),('R',-1)]:
        upper='UpperArm.'+side;fore='Forearm.'+side;hand='Hand.'+side
        ellipsoid('Soft_shoulder',(s*.225,0,1.39),(.083,.081,.083),jacket,upper)
        limb('Jacket_upper_sleeve',(s*.225,0,1.39),(s*.29,0,1.11),.082,.064,jacket,upper)
        ellipsoid('Sleeve_elbow',(s*.29,0,1.11),(.063,.063,.066),jacket,fore)
        limb('Jacket_lower_sleeve',(s*.29,0,1.11),(s*.31,-.015,.88),.064,.043,jacket,fore)
        limb('Sleeve_cuff',(s*.31,-.015,.91),(s*.31,-.015,.875),.047,.046,jacket,fore)
        ellipsoid('Palm',(s*.31,-.014,.83),(.036,.026,.054),skin,hand)
        for i in range(4):
            x=s*.31+(i-1.5)*.015
            tube('Finger',[(x,-.015,.805),(x,-.023,.775),(x,-.023,.762+abs(i-1.5)*.005)],.007,skin,hand)
        tube('Thumb',[(s*.28,-.014,.84),(s*.263,-.03,.811),(s*.27,-.037,.79)],.010,skin,hand)
        thigh='Thigh.'+side;shin='Shin.'+side;foot='Foot.'+side
        limb('Trouser_upper',(s*.105,0,.96),(s*.105,0,.54),.101,.075,pants,thigh)
        if pid=='ronny':
            limb('Shorts_cuff',(s*.105,0,.59),(s*.105,0,.52),.088,.088,pants,thigh)
            limb('Bare_lower_leg',(s*.105,0,.53),(s*.105,0,.15),.069,.046,skin,shin)
        else:limb('Trouser_lower',(s*.105,0,.53),(s*.105,0,.13),.075,.051,pants,shin)
        ellipsoid('Knee',(s*.105,0,.53),(.073,.075,.065),pants if pid!='ronny' else skin,shin)
        box('Shoe',(s*.105,-.046,.075),(.115,.242,.118),shoe,foot,.025)
        sole=material('Sole_'+side+'_'+pid,'#b9b7ae' if pid in ['per','linnea'] else '#15191b')
        box('Shoe_sole',(s*.105,-.048,.025),(.118,.247,.038),sole,foot,.012)
        for z in [.08,.10]:tube('Shoe_lace',[(s*.105-.035,-.11,z),(s*.105+.035,-.11,z)],.002,ivory,foot)
    if pid=='ronny':
        red=material('Red_leather_panels','#af2a26',.44)
        outer.data.materials.append(red)
        for polygon in outer.data.polygons:
            if polygon.normal.y<-.25 and abs(polygon.center.x)>.13:polygon.material_index=2
        for s in [-1,1]:
            mesh('Red_jacket_panel',[(s*.22,-.095,.94),(s*.24,-.09,1.38),(s*.13,-.145,1.34),(s*.15,-.15,.94)],[(0,1,2,3)],red)
            box('Red_shoulder',(s*.245,-.035,1.391),(.11,.13,.025),red,'UpperArm.'+('L' if s==1 else 'R'))
            for n in range(8):ellipsoid('Metal_stud',(s*.205,-.137,1.10+n*.029),(.004,.003,.004),metal,'Chest',8,6)
        ellipsoid('Navel',(0,-.270,1.005),(.009,.003,.006),skin_shadow,'Chest')
    if pid=='lars':
        book=material('Book_cover','#40533b');pages=material('Book_pages','#c9c2a6')
        box('History_book_pages',(.34,-.048,.829),(.105,.028,.165),pages,'Hand.L',.004)
        for y in [-.067,-.028]:box('History_book_cover',(.34,y,.829),(.115,.008,.174),book,'Hand.L',.003)
    if pid=='linnea':
        mic=material('Microphone_foam','#292a2d');handle=material('Microphone_handle','#45565b',.4)
        limb('Reporter_microphone',(-.31,-.046,.84),(-.31,-.046,1.03),.012,.014,handle,'Hand.R')
        ellipsoid('Microphone_head',(-.31,-.046,1.065),(.030,.029,.042),mic,'Hand.R')
        box('Reporter_notebook',(.33,-.055,.84),(.10,.026,.14),ivory,'Hand.L',.004)


def animate(profile):
    rig.animation_data_create();fps=24;bpy.context.scene.render.fps=fps
    for clip,duration in [('Idle',4.),('Walk',1.4),('Talk',3.),('Wave',2.4),('Startle',1.6)]:
        action=bpy.data.actions.new(clip);rig.animation_data.action=action
        count=round(duration*fps)
        for frame in range(0,count+1,2):
            phase=frame/count*math.tau
            for pb in rig.pose.bones:pb.rotation_mode='XYZ';pb.rotation_euler=(0,0,0);pb.location=(0,0,0);pb.scale=(1,1,1)
            rig.pose.bones['Chest'].scale.z=1.+.005*math.sin(phase)
            rig.pose.bones['Head'].rotation_euler.y=.035*math.sin(phase)
            if clip=='Walk':
                for side,s in [('L',1),('R',-1)]:
                    rig.pose.bones['Thigh.'+side].rotation_euler.x=s*.34*math.sin(phase)
                    rig.pose.bones['Shin.'+side].rotation_euler.x=-max(0.,s*math.sin(phase))*.36
                    rig.pose.bones['UpperArm.'+side].rotation_euler.x=-s*.20*math.sin(phase)
            elif clip=='Talk':
                energy={'lars':.16,'per':.45,'ronny':.36,'linnea':.20}[profile['id']]
                rig.pose.bones['UpperArm.R'].rotation_euler.x=-energy*(.5-.5*math.cos(phase))
                rig.pose.bones['Forearm.R'].rotation_euler.x=-.4*(.5-.5*math.cos(phase))
                rig.pose.bones['Head'].rotation_euler.x=.045*math.sin(phase*2)
            elif clip=='Wave':
                amount=math.sin(phase*.5)**2
                rig.pose.bones['UpperArm.R'].rotation_euler.z=-1.2*amount
                rig.pose.bones['Forearm.R'].rotation_euler.z=-.6*amount
                rig.pose.bones['Hand.R'].rotation_euler.x=.35*math.sin(phase*3)*amount
            elif clip=='Startle':
                amount=math.sin(phase*.5)**2
                for side,s in [('L',1),('R',-1)]:
                    rig.pose.bones['UpperArm.'+side].rotation_euler.x=-.8*amount
                    rig.pose.bones['Forearm.'+side].rotation_euler.x=-.65*amount
            for pb in rig.pose.bones:
                pb.keyframe_insert('rotation_euler',frame=frame);pb.keyframe_insert('location',frame=frame);pb.keyframe_insert('scale',frame=frame)
        track=rig.animation_data.nla_tracks.new();track.name=clip
        track.strips.new(clip,0,action)
    rig.animation_data.action=None


profiles=[
    dict(id='lars',name='Lars Gahrn',head_width=.113,nose=(.019,.025,.024),width=.180,coat='#252d2d',shirt='#71765c',pants='#454745',hair='#b8b7af',skin='#c79d83',height=1.88),
    dict(id='per',name='Per Andersson',head_width=.124,nose=(.022,.026,.020),width=.244,coat='#87532e',shirt='#5e9cbb',pants='#384756',hair='#42362b',skin='#d2a386',height=1.80),
    dict(id='ronny',name='Ronny Jönsson',head_width=.142,nose=(.030,.031,.026),width=.275,coat='#20262b',shirt='#c59172',pants='#aaa79d',hair='#473527',skin='#c99876',height=1.77),
    dict(id='linnea',name='Linnea Rönnqvist',head_width=.115,nose=(.017,.019,.018),width=.208,coat='#bec1c4',shirt='#bec1c4',pants='#252c3d',hair='#5a412c',skin='#d5ad94',height=1.69),
]
for profile in profiles:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rig=make_rig()
    skin=material('Skin_'+profile['id'],profile['skin'],.67);skin_shadow=material('Skin_detail','#956c5e')
    hair=material('Hair_'+profile['id'],profile['hair']);dark=material('Pupil','#161d22')
    iris=material('Iris','#67858a');ivory=material('Ivory','#e7e2d8');mouth=material('Mouth','#67413c');lips=material('Lips','#ab756e')
    metal=material('Pewter','#a5aaa7',.3,.65)
    body(profile);face(profile);hair_and_hat(profile)
    def silhouette(v):
        v=v.copy();pid=profile['id'];z=v.z
        if pid=='lars' and z<1.45:
            v.x*=.81;v.y*=.88
        elif pid=='ronny' and z<1.45:
            v.x*=1.12
        elif pid=='linnea' and z<.96:
            # Wider pelvis and slimmer ankles; maintain clothed natural anatomy.
            v.x*=1.15 if z>.65 else 1.02
        return v
    for ob in list(bpy.data.objects):
        if ob.type!='MESH':continue
        transform=ob.matrix_world.copy();inverse=transform.inverted()
        for vertex in ob.data.vertices:vertex.co=inverse @ silhouette(transform @ vertex.co)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in rig.data.edit_bones:
        bone.head=silhouette(bone.head);bone.tail=silhouette(bone.tail)
    bpy.ops.object.mode_set(mode='OBJECT')
    # Merge own components into a skinned mesh: few draws, preserved vertex groups.
    meshes=[ob for ob in bpy.data.objects if ob.type=='MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for ob in meshes:ob.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join()
    joined=bpy.context.object;joined.name='Civilian_'+profile['id']
    # Scale all authored geometry and rest bones together; head/feet stay coherent.
    factor=profile['height']/1.85
    rig.scale=(factor,)*3
    animate(profile)
    bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
    path=OUT/('civilian_'+profile['id']+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_yup=True,
        export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,
        export_skins=True,export_def_bones=True,export_materials='EXPORT',export_cameras=False,export_lights=False)
    reports.append(dict(id=profile['id'],name=profile['name'],path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,
                        bones=len(rig.data.bones),triangles=sum(len(p.vertices)-2 for p in joined.data.polygons),materials=len(joined.data.materials),clips=['Idle','Walk','Talk','Wave','Startle'],
                        source='Own authored geometry and animation; reference photos not embedded',forward='+Z in Godot; runtime model rotated PI to match player/soldier headings',height_estimated_m=profile['height'],body_type={'lars':'long and very slim','per':'average build','ronny':'round belly and broad torso','linnea':'female silhouette, defined waist and hips'}[profile['id']]))
(ROOT/'evidence/civilian-models.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
print('KVARNBYN_CIVILIAN_MODELS',json.dumps(reports,ensure_ascii=False))

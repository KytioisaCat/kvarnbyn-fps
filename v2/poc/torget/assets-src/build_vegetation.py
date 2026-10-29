"""Build three mobile-sized, asymmetric broadleaf tree proxies in Blender.

Blender 4.5: blender -b --python assets-src/build_vegetation.py
No spheres/cones for canopies: tapered branching tubes and photographed alpha foliage.
Not a botanical reconstruction; see asset-docs/README.md and manifest.json.
"""
from pathlib import Path
import json
import math
import random
import sys
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from blender_materials import pbr_material, solid_material

OUT = ROOT / 'vegetation'
OUT.mkdir(parents=True, exist_ok=True)
MANIFEST = json.loads((ROOT / 'manifest.json').read_text())
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    if c.name != 'Collection':
        bpy.data.collections.remove(c)


def leaf_texture():
    """Channel-pack CC0 source albedo + source opacity without changing pixels."""
    maps = MANIFEST['foliage_atlas']['maps']
    diffuse = bpy.data.images.load(str(ROOT / maps['leaf_albedo']['path']), check_existing=True)
    alpha = bpy.data.images.load(str(ROOT / maps['leaf_alpha']['path']), check_existing=True)
    n = diffuse.size[0] * diffuse.size[1] * 4
    rgba = np.empty(n, dtype=np.float32)
    mask = np.empty(n, dtype=np.float32)
    diffuse.pixels.foreach_get(rgba)
    alpha.pixels.foreach_get(mask)
    rgba = rgba.reshape((-1, 4))
    rgba[:, 3] = mask.reshape((-1, 4))[:, 0]
    image = bpy.data.images.new('Foliage_rgba_CC0', width=diffuse.size[0], height=diffuse.size[1], alpha=True)
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw = str(OUT / 'textures' / 'foliage_rgba_1k.png')
    image.file_format = 'PNG'
    image.save()
    image.pack()
    return image


def foliage_material(image, name, tint):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.use_backface_culling = False
    material.surface_render_method = 'DITHERED'
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = image
    tex.extension = 'CLIP'
    links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    # A recognized alpha clip node exports as glTF MASK, not expensive BLEND.
    clip = nodes.new('ShaderNodeMath')
    clip.operation = 'GREATER_THAN'
    clip.inputs[1].default_value = .45
    links.new(tex.outputs['Alpha'], clip.inputs[0])
    links.new(clip.outputs[0], bsdf.inputs['Alpha'])
    bsdf.inputs['Roughness'].default_value = .82
    # A low portable emissive term approximates light through thin leaves.
    links.new(tex.outputs['Color'], bsdf.inputs['Emission Color'])
    bsdf.inputs['Emission Strength'].default_value = .10
    bsdf.inputs['IOR'].default_value = 1.35
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    # Tint lives in diffuse_color as an import hint; texture is portable.
    material.diffuse_color = (*tint, 1)
    material['source_page'] = 'https://polyhaven.com/a/tree_small_02'
    material['license'] = 'CC0-1.0'
    material['alpha_cutoff'] = .45
    material['botanical_status'] = 'generic proxy, source leaves Burkea africana'
    return material


LEAF_IMAGE = leaf_texture()
LEAF_MATERIALS = [
    foliage_material(LEAF_IMAGE, 'Foliage_Mask_01_CC0', (.25, .39, .09)),
]
BARK = pbr_material('bark', normal_strength=.7)


class MeshBuilder:
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.uv = []

    def face(self, coords, uv):
        start = len(self.vertices)
        self.vertices.extend(tuple(c) for c in coords)
        self.faces.append(tuple(range(start, start + len(coords))))
        self.uv.append(uv)

    def tube(self, points, radius, sides=5, taper=.06, noise=0.0):
        cumulative = [0.0]
        for a, b in zip(points, points[1:]):
            cumulative.append(cumulative[-1] + (b-a).length)
        rings = []
        for i, p in enumerate(points):
            tangent = (points[min(i+1,len(points)-1)] - points[max(0,i-1)]).normalized()
            guide = Vector((0,0,1)) if abs(tangent.z)<.94 else Vector((1,0,0))
            u = tangent.cross(guide).normalized()
            v = tangent.cross(u).normalized()
            r = radius * (1 - (i/(len(points)-1))*(1-taper))
            rings.append([p + r*(1+noise*math.sin(i*2.7+j*1.8)) * (u*math.cos(j*math.tau/sides)+v*math.sin(j*math.tau/sides)) for j in range(sides)])
        for i in range(len(rings)-1):
            for j in range(sides):
                j2 = (j+1)%sides
                self.face([rings[i][j],rings[i][j2],rings[i+1][j2],rings[i+1][j]],
                    [(j/sides,cumulative[i]/.8),((j+1)/sides,cumulative[i]/.8),((j+1)/sides,cumulative[i+1]/.8),(j/sides,cumulative[i+1]/.8)])
        # small end caps; roots meet the ground plane, not a floating trunk end.
        self.face(list(reversed(rings[0])),[(.5,.5)]*sides)
        self.face(rings[-1],[(.5,.5)]*sides)

    def card(self, center, length_axis, width_axis, length, width, atlas):
        l = length_axis.normalized()*length/2
        w = width_axis.normalized()*width/2
        # Slight fold across center improves close silhouettes without many faces.
        # The alpha atlas supplies the connected leaf shoot, six to eight leaves.
        coords = [center-w-l,center+w-l,center+w+l,center-w+l]
        x0,y0,x1,y1 = atlas
        self.face(coords,[(x0,y0),(x1,y0),(x1,y1),(x0,y1)])

    def object(self, name, collection, material):
        mesh = bpy.data.meshes.new(name+'_mesh')
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.materials.append(material)
        mesh.update()
        uv = mesh.uv_layers.new(name='UVMap')
        for poly, face_uvs in zip(mesh.polygons,self.uv):
            for loop_index, value in zip(poly.loop_indices,face_uvs):
                uv.data[loop_index].uv = value
        obj = bpy.data.objects.new(name,mesh)
        collection.objects.link(obj)
        return obj


def curve_path(start,end,rng,bend=.12,steps=5):
    result=[]
    for i in range(steps):
        t=i/(steps-1)
        p=start.lerp(end,t)
        p += Vector((math.sin(t*math.pi)*rng.uniform(-bend,bend),math.sin(t*math.pi)*rng.uniform(-bend,bend),-.25*math.sin(t*math.pi)))
        result.append(p)
    return result


def build_tree(name, seed, height, width, trunk_radius):
    rng=random.Random(seed)
    collection=bpy.data.collections.new(name)
    bark=MeshBuilder()
    leaves=MeshBuilder()
    trunk=[]
    for i in range(15):
        t=i/14
        trunk.append(Vector((.16*math.sin(t*4.5+seed)+.1*t,.12*math.sin(t*5.3),t*height*.91)))
    bark.tube(trunk,trunk_radius,sides=9,taper=.1,noise=.10)
    # A handful of flared roots gives a grounded base, not a cylinder on a plate.
    for i in range(6):
        a=i*math.tau/6+rng.uniform(-.2,.2)
        start=Vector((0,0,.30))
        end=Vector((math.cos(a)*trunk_radius*3.3,math.sin(a)*trunk_radius*3.3,.015))
        bark.tube(curve_path(start,end,rng,bend=.04,steps=3),trunk_radius*.55,sides=5,taper=.08)
    for i in range(15):
        t=.28+i/14*.56
        base=trunk[min(13,int(t*14))]
        a=i*2.3999632297+rng.uniform(-.25,.25)+seed
        crown_envelope=max(.32,math.sin((t-.14)/.89*math.pi))
        radius=width*crown_envelope*rng.uniform(.74,1.12)
        end=Vector((base.x+math.cos(a)*radius,base.y+math.sin(a)*radius,height*(.43+.45*i/14+rng.uniform(-.025,.025))))
        path=curve_path(base,end,rng,bend=.11,steps=6)
        bark.tube(path,trunk_radius*(.55-.22*t),sides=6,taper=.09,noise=.12)
        for j in range(7):
            s=.30+j/6*.68
            index=min(4,int(s*5))
            b=path[index].lerp(path[index+1],s*5-index)
            angle=a+rng.uniform(-1.2,1.2)
            reach=width*rng.uniform(.23,.51)
            tip=b+Vector((math.cos(angle)*reach,math.sin(angle)*reach,height*rng.uniform(-.025,.065)))
            twig=curve_path(b,tip,rng,bend=.07,steps=4)
            bark.tube(twig,trunk_radius*.17*(1-.35*s),sides=4,taper=.08,noise=.1)
            for k in range(4):
                # Multiple uneven shoots along each outer twig make branch-defined lobes.
                leaf_position=twig[-2].lerp(tip,.10+k*.30)
                shoot_angle=angle+rng.uniform(-1.5,1.5)
                shoot_direction=Vector((math.cos(shoot_angle),math.sin(shoot_angle),rng.uniform(-.35,.55))).normalized()
                leaf_position+=shoot_direction*rng.uniform(.12,.48)
                length=rng.uniform(.62,1.08)*(height/7.4)**.35
                # Clean right-hand cluster of the CC0 atlas. Image y reversed to UV.
                atlas=(.515,.395,.851,.97)
                axis=shoot_direction
                u=axis.cross(Vector((0,0,1))).normalized()
                if u.length<.01: u=Vector((1,0,0))
                v=axis.cross(u).normalized()
                for rotation in [rng.uniform(-.3,.3),math.pi/2+rng.uniform(-.3,.3)]:
                    across=u*math.cos(rotation)+v*math.sin(rotation)
                    leaves.card(leaf_position,axis,across,length,length*.58,atlas)
    # Top shoots fill the tapered crown, with a small characteristic gap on one side.
    for i in range(20):
        a=rng.uniform(0,math.tau)
        position=trunk[-2]+Vector((math.cos(a)*rng.uniform(.15,.75),math.sin(a)*rng.uniform(.15,.75),rng.uniform(-.1,.4)))
        axis=Vector((math.cos(a)*.5,math.sin(a)*.5,1)).normalized()
        across=axis.cross(Vector((1,0,0))).normalized()
        leaves.card(position,axis,across,.85,.51,(.515,.395,.851,.97))
    root=bpy.data.objects.new(name,None)
    collection.objects.link(root)
    root['asset_kind']='generic_broadleaf_proxy'
    root['height_m']=height
    root['seed']=seed
    root['source_leaf_species']='Burkea africana; generic proxy, not species reconstruction'
    root['license']='Own authored geometry; CC0 source textures'
    bobj=bark.object(name+'_Bark',collection,BARK)
    lobj=leaves.object(name+'_Leaves',collection,LEAF_MATERIALS[0])
    bobj.parent=root
    lobj.parent=root
    for p in bobj.data.polygons: p.use_smooth=True
    # Smoothly outward-facing normals give photographed leaf cards leaflike lighting.
    for p in lobj.data.polygons: p.use_smooth=True
    crown_center=Vector((0,0,height*.68))
    normals=[]
    for vertex in lobj.data.vertices:
        outward=vertex.co-crown_center
        outward.z += height*.30
        normals.append(outward.normalized())
    lobj.data.normals_split_custom_set_from_vertices(normals)
    tris=sum(len(poly.vertices)-2 for o in [bobj,lobj] for poly in o.data.polygons)
    return collection,root,tris


assets=[]
for args in [('Broadleaf_A',19,7.8,2.25,.23),('Broadleaf_B',63,6.5,2.5,.19),('Broadleaf_C',108,8.6,1.85,.18)]:
    collection,root,tris=build_tree(*args)
    bpy.context.scene.collection.children.link(collection)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in collection.objects: obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.gltf(filepath=str(OUT/(args[0]+'.glb')),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True,export_texcoords=True,export_normals=True,export_materials='EXPORT')
    bpy.context.scene.collection.children.unlink(collection)
    assets.append({'name':args[0],'triangles':tris,'height_m':args[2],'file':args[0]+'.glb','collection':collection})
    print('TREE',args[0],tris,'triangles',flush=True)

# Presentation scene only. Collections remain local with all tree origins at (0,0,0).
for i,a in enumerate(assets):
    instance=bpy.data.objects.new(a['name']+'_Preview',None)
    instance.instance_type='COLLECTION'
    instance.instance_collection=a['collection']
    instance.location=(i*7.4,0,0)
    bpy.context.scene.collection.objects.link(instance)

bpy.ops.mesh.primitive_plane_add(size=200,location=(7,0,-.025))
ground=bpy.context.object
ground.name='Preview_Ground'
ground.data.materials.append(pbr_material('grass',normal_strength=.4))
# UV scale 200m plane with a 2.51m grass tile.
for uv in ground.data.uv_layers.active.data: uv.uv*=80
bpy.ops.object.light_add(type='SUN',location=(-10,-14,18))
sun=bpy.context.object
sun.name='Preview_Sun'
sun.rotation_euler=(math.radians(27),math.radians(-28),math.radians(-28))
sun.data.energy=3.0
sun.data.angle=math.radians(3)
sun.data.color=(1,.90,.75)
world=bpy.data.worlds.new('Preview_Sky')
world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.46,.64,.85,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55
bpy.context.scene.world=world
bpy.ops.object.camera_add(location=(22,-30,12))
camera=bpy.context.object
camera.rotation_euler=(Vector((7.4,0,4.4))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.lens=47
bpy.context.scene.camera=camera
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=64
scene.cycles.use_denoising=True
scene.render.resolution_x=1800
scene.render.resolution_y=1000
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(OUT/'trees_preview.png')
scene.view_settings.view_transform='AgX'
# Save packed source project. Export collections are independently appendable.
for image in bpy.data.images:
    if image.source=='FILE' and image.has_data: image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'vegetation.blend'))
(OUT/'vegetation-manifest.json').write_text(json.dumps({
    'generated_by':'build_vegetation.py; Blender 4.5',
    'geometry_license':'CC0-1.0 (authored for this project)',
    'texture_sources':['https://polyhaven.com/a/bark_willow','https://polyhaven.com/a/tree_small_02'],
    'botanical_status':'Generic broadleaf proxies, not surveyed species or measured trees.',
    'assets':[{k:v for k,v in a.items() if k!='collection'} for a in assets]
},ensure_ascii=False,indent=2)+'\n')
bpy.ops.render.render(write_still=True)
print('VEGETATION_READY',OUT,flush=True)

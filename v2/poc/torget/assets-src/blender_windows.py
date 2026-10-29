"""Small physical interior/curtain proxies for real façade openings.

Root's window kit supplies its local-to-world callback:
    add_interior(kit, name, at, u, outward, width, height, door=False, variant=0)

Local a runs horizontally, depth is positive toward the street, h starts at the
window's bottom. The front glass is at depth .025; curtains stay at 0..+.005;
backing is at -.08. Uses only ordinary opaque Principled materials and quads.
No room illumination, procedural shader, alpha texture, or baked-light trick.
"""
import math

_CACHE=None


def _linear(hex_color):
    color=[int(hex_color[i:i+2],16)/255 for i in (1,3,5)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in color)+(1,)


def make_window_materials():
    """Create once, or assign this result to kit.window_materials explicitly."""
    import bpy
    global _CACHE
    try:
        if _CACHE and all(material.name in bpy.data.materials for material in _CACHE.values()):
            return _CACHE
    except ReferenceError:
        pass
    palette={
        'room_partial':('#1d2927',.94),
        'room_blind':('#202826',.94),
        'room_clear':('#172127',.94),
        'reveal':('#706e62',.90),
        'curtain':('#c0bba9',.93),
        'blind':('#acb5aa',.82),
        'cord':('#807e70',.95),
    }
    _CACHE={}
    for key,(color,roughness) in palette.items():
        material=bpy.data.materials.new('WindowInterior_'+key)
        material.use_nodes=True
        material.diffuse_color=_linear(color)
        bsdf=material.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value=_linear(color)
        bsdf.inputs['Roughness'].default_value=roughness
        bsdf.inputs['Metallic'].default_value=0
        material.use_backface_culling=True
        material['asset_kind']='authored_window_interior_proxy'
        _CACHE[key]=material
    return _CACHE


def add_interior(kit,name,at,u,outward,width,height,door=False,variant=0):
    """Add a 8cm-deep cavity and one of three stable window states.

    0: partial folded curtains, 1: partially lowered horizontal blind,
    2: dark clear room. Doors always keep the room clear.
    Returns variant and triangle count for authoring/build metrics.
    """
    if width<=0 or height<=0: raise ValueError('Window dimensions must be positive')
    materials=getattr(kit,'window_materials',None)
    if materials is None:
        materials=make_window_materials()
        kit.window_materials=materials
    state=2 if door else int(variant)%3
    triangle_count=0
    def face(suffix,material,points):
        nonlocal triangle_count
        batch_name=getattr(kit,'window_batch_name',name+'_Interior')
        kit.face(batch_name+suffix,materials[material],points)
        triangle_count+=len(points)-2
    left=-width*.49;right=width*.49
    bottom=height*.012;top=height*.988
    back=-.08
    front=.0
    state_material=['room_partial','room_blind','room_clear'][state]
    face('_Back',state_material,[at(left,back,bottom),at(right,back,bottom),at(right,back,top),at(left,back,top)])
    # Reveal normals face into the cavity, with a slightly lighter inner sill.
    face('_Reveal','reveal',[at(left,front,bottom),at(left,back,bottom),at(left,back,top),at(left,front,top)])
    face('_Reveal','reveal',[at(right,back,bottom),at(right,front,bottom),at(right,front,top),at(right,back,top)])
    face('_Reveal','reveal',[at(left,back,top),at(right,back,top),at(right,front,top),at(left,front,top)])
    face('_Reveal','reveal',[at(left,front,bottom),at(right,front,bottom),at(right,back,bottom),at(left,back,bottom)])
    if state==0:
        # Seven real folds per panel; two height segments soften the fabric profile.
        segments=14
        for start,end,phase in [(-width*.48,-width*.20,.1),(width*.25,width*.48,.7)]:
            rows=[]
            for row_fraction in [0,.53,1]:
                row=[]
                for i in range(segments+1):
                    t=i/segments
                    a=start+(end-start)*t
                    depth=.0025+.0025*math.cos(t*math.pi*segments+phase)
                    depth=max(0,min(.005,depth+.0005*math.sin(row_fraction*math.pi)))
                    hem=height*(.035+.008*math.sin(t*math.pi*2+phase))
                    h=hem+(height*.973-hem)*row_fraction
                    row.append(at(a,depth,h))
                rows.append(row)
            for row in range(len(rows)-1):
                for i in range(segments):
                    face('_Curtain','curtain',[rows[row][i],rows[row][i+1],rows[row+1][i+1],rows[row+1][i]])
    elif state==1:
        # A partially lowered blind; twelve tilted slats form actual small shadows.
        span=height*.52
        count=12
        step=span/count
        for i in range(count):
            h=top-i*step
            face('_Blind','blind',[at(left+.015,-.009,h-step*.69),at(right-.015,-.009,h-step*.69),at(right-.015,.004,h+step*.15),at(left+.015,.004,h+step*.15)])
        # Fine lift cords, behind glass and in front of the slats.
        for a in [-width*.29,width*.29]:
            cord_width=max(.002,width*.003)
            face('_Cord','cord',[at(a-cord_width,.005,top-span),at(a+cord_width,.005,top-span),at(a+cord_width,.005,top),at(a-cord_width,.005,top)])
        face('_BlindHeader','blind',[at(left,0,top-step*.22),at(right,0,top-step*.22),at(right,.004,top),at(left,.004,top)])
    assert triangle_count<150
    return {'variant':['partial_curtain','partial_blind','dark_clear'][state],
        'triangles':triangle_count,'back_depth_m':back,'curtain_front_depth_m':.005}

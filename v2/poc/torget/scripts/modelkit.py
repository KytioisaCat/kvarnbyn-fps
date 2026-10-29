"""Small Blender authoring kit. Geometry is authored in meters, not rendered from OSM.
Batch by logical object/material so export keeps a modest surface count.
"""
import math
from collections import defaultdict
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from blender_windows import add_interior


def color(hex_value):
    value = hex_value.lstrip('#')
    srgb = [int(value[i:i+2], 16) / 255 for i in (0,2,4)]
    return tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in srgb) + (1,)


class Kit:
    def __init__(self):
        self.batches = {}
        self.materials = {}
        self.objects = []

    def face(self, name, material, points, uv=None):
        key = (name, material.name)
        batch = self.batches.setdefault(key, {'verts':[], 'faces':[], 'uv':[], 'mat':material})
        points = [tuple(p) for p in points]
        start = len(batch['verts'])
        batch['verts'].extend(points)
        batch['faces'].append(tuple(range(start,start+len(points))))
        if uv is None:
            u = (Vector(points[1])-Vector(points[0])).normalized()
            normal = u.cross(Vector(points[-1])-Vector(points[0])).normalized()
            v = normal.cross(u)
            tile = float(material.get('tile_size_m', 1.0))
            origin = Vector(points[0])
            uv = [((Vector(p)-origin).dot(u)/tile, (Vector(p)-origin).dot(v)/tile) for p in points]
        batch['uv'].extend(uv)

    def box(self, name, material, center, size, u=(1,0), v=None):
        v = v or (-u[1],u[0])
        cx,cy,cz = center
        dx,dy,dz = [s/2 for s in size]
        points=[(cx+u[0]*x+v[0]*y,cy+u[1]*x+v[1]*y,cz+z) for x,y,z in [(-dx,-dy,-dz),(dx,-dy,-dz),(dx,dy,-dz),(-dx,dy,-dz),(-dx,-dy,dz),(dx,-dy,dz),(dx,dy,dz),(-dx,dy,dz)]]
        faces=[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
        if u[0]*v[1]-u[1]*v[0] < 0:
            faces=[tuple(reversed(f)) for f in faces]
        for f in faces:self.face(name,material,[points[i] for i in f])

    def beam(self,name,material,a,b,radius=.04,sides=8):
        a,b=Vector(a),Vector(b)
        axis=(b-a).normalized()
        other=Vector((0,0,1)) if abs(axis.z)<.95 else Vector((1,0,0))
        u=axis.cross(other).normalized();v=axis.cross(u).normalized()
        rings=[[p+(u*math.cos(i*math.tau/sides)+v*math.sin(i*math.tau/sides))*radius for i in range(sides)] for p in [a,b]]
        for i in range(sides):
            j=(i+1)%sides
            self.face(name,material,[rings[0][i],rings[0][j],rings[1][j],rings[1][i]])
        self.face(name,material,list(reversed(rings[0])))
        self.face(name,material,rings[1])

    def polygon(self,name,material,poly,height):
        verts=[Vector((x,-z,height(x,z) if callable(height) else height)) for x,z in poly]
        for tri in tessellate_polygon([verts]):
            pts=[verts[i] for i in tri] if isinstance(tri[0],int) else list(tri)
            if (pts[1]-pts[0]).cross(pts[2]-pts[0]).z<0:pts.reverse()
            self.face(name,material,pts,[(p.x/float(material.get('tile_size_m',1)),-p.y/float(material.get('tile_size_m',1))) for p in pts])

    def shell(self,name,material,poly,base,height):
        self.polygon(name,material,poly,base+height)
        for a,b in zip(poly,poly[1:]+poly[:1]):
            self.face(name,material,[(a[0],-a[1],base),(b[0],-b[1],base),(b[0],-b[1],base+height),(a[0],-a[1],base+height)])

    def finish(self):
        for (name,matname),b in self.batches.items():
            mesh=bpy.data.meshes.new(name+'Mesh');mesh.from_pydata(b['verts'],[],b['faces']);mesh.materials.append(b['mat']);mesh.update()
            layer=mesh.uv_layers.new(name='UVMap')
            for i,uv in enumerate(b['uv']):layer.data[i].uv=uv
            obj=bpy.data.objects.new(name+'__'+matname,mesh);bpy.context.collection.objects.link(obj);self.objects.append(obj)
        return self.objects


class Frame:
    """Plan coordinates x east/z south, Blender x east/y north, local a/b meters."""
    def __init__(self,center,axis):
        self.cx,self.cz=center
        self.u=(axis[0],-axis[1]);self.v=(-self.u[1],self.u[0])

    def p(self,a,b,h):return (self.cx+self.u[0]*a+self.v[0]*b,-self.cz+self.u[1]*a+self.v[1]*b,h)
    def xz(self,a,b):
        p=self.p(a,b,0);return (p[0],-p[1])


def roof(kit,name,frame,length,width,eave,rise,material,trim,hipped=False,seams=False):
    l,w=length/2+.32,width/2+.32
    p=lambda a,b,h:frame.p(a,b,h)
    ridge=max(0,l-w) if hipped else l
    # top surfaces are wound upward
    kit.face(name,material,[p(-l,-w,eave),p(l,-w,eave),p(ridge,0,eave+rise),p(-ridge,0,eave+rise)])
    kit.face(name,material,[p(l,w,eave),p(-l,w,eave),p(-ridge,0,eave+rise),p(ridge,0,eave+rise)])
    if hipped:
        kit.face(name,material,[p(-l,w,eave),p(-l,-w,eave),p(-ridge,0,eave+rise)])
        kit.face(name,material,[p(l,-w,eave),p(l,w,eave),p(ridge,0,eave+rise)])
    else:
        kit.face(name,trim,[p(-l,-w,eave),p(-l,0,eave+rise),p(-l,w,eave)])
        kit.face(name,trim,[p(l,w,eave),p(l,0,eave+rise),p(l,-w,eave)])
    for b in [-w,w]:
        kit.box(name,trim,p(0,b,eave-.1),(2*l,.13,.22),frame.u)
        kit.beam(name,material,p(-l,b,eave-.04),p(l,b,eave-.04),.065)
    for a in [-l,l]:
        for b in [-w,w]:
            kit.beam(name,trim,p(a,b,eave),p(math.copysign(ridge,a),0,eave+rise),.045)
    if seams:
        for i in range(int(length/.6)+1):
            a=-length/2+i*.6
            if hipped and abs(a)>ridge:
                top=eave+rise*(l-abs(a))/(l-ridge);rwidth=w*(l-abs(a))/(l-ridge)
            else:top=eave+rise;rwidth=w
            for side in [-1,1]:
                kit.beam(name,material,p(a,side*w,eave+.018),p(a,side*max(0,w-rwidth),top+.018),.012,4)
    return eave+rise


def text(body,name,position,facing,size,material,align='CENTER'):
    curve=bpy.data.curves.new(name,'FONT');curve.body=body;curve.align_x=align;curve.align_y='CENTER';curve.size=size;curve.extrude=.002;curve.bevel_depth=.0005
    obj=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(obj);obj.location=position
    normal=Vector((facing[0],facing[1],0));obj.rotation_euler=normal.to_track_quat('Z','Y').to_euler();obj.data.materials.append(material)
    return obj


def window(kit,name,wallpoint,u,outward,width,height,trim,glass,white,door=False,awning=None,label=None,closed=False):
    x,y,bottom=wallpoint;center=(x,y,bottom+height/2)
    at=lambda a,b,h:(x+u[0]*a+outward[0]*b,y+u[1]*a+outward[1]*b,bottom+h)
    variant=(int(abs(x)*31+abs(y)*17+bottom*13))%3
    if not closed:add_interior(kit,name,at,u,outward,width,height,door=door or awning is not None,variant=variant)
    kit.face(name+'_Glass',trim if closed else glass,[at(-width/2,.025,0),at(width/2,.025,0),at(width/2,.025,height),at(-width/2,.025,height)],[(0,0),(1,0),(1,1),(0,1)])
    for a in [-width/2,width/2]:kit.box(name,trim,at(a,.085,height/2),(.08,.14,height+.16),u)
    for h in [0,height]:kit.box(name,trim,at(0,.085,h),(width+.16,.16,.08),u)
    kit.box(name,trim,at(0,.13,height+.14),(width+.27,.24,.12),u)
    if door:
        kit.box(name,trim,at(0,.072,height*.22),(width-.12,.08,height*.43),u)
        kit.box(name,white,at(width*.32,.19,height*.47),(.045,.04,.17),u)
    elif awning is None:
        kit.box(name,white,at(0,.13,height/2),(.048,.05,height-.1),u)
        for h in [height*.35,height*.68]:kit.box(name,white,at(0,.13,h),(width-.1,.055,.035),u)
        kit.box(name,trim,at(0,.16,-.08),(width+.3,.36,.095),u)
    if awning is not None:
        lo=height+.2;hi=height+.65
        kit.face(name,awning,[at(-width*.65,.14,hi),at(width*.65,.14,hi),at(width*.65,.92,lo),at(-width*.65,.92,lo)],[(0,0),(1,0),(1,1),(0,1)])
        kit.face(name,awning,[at(-width*.65,.92,lo),at(width*.65,.92,lo),at(width*.65,.92,lo-.24),at(-width*.65,.92,lo-.24)])
        for a in [-width*.65,width*.65]:kit.face(name,awning,[at(a,.14,hi),at(a,.92,lo),at(a,.92,lo-.24),at(a,.14,lo-.24)])
        if label:text(label,name+'_AwningLetters',at(0,.931,lo-.115),outward,min(.16,width/9),white)


def facade(kit,name,a,b,base,height,wallmat,trim,glass,white,levels=2,bays=None,panel=False,awning=None,sign=None,door_index=None,ornate=False,floor_bays=None,lower_types=None,floor_heights=None):
    a,b=Vector(a),Vector(b);d=b-a;length=d.length;u=(d.x/length,d.y/length);outward=(u[1],-u[0]);mid=(a+b)/2
    pos=lambda s,o,h:(a.x+u[0]*s+outward[0]*o,a.y+u[1]*s+outward[1]*o,h)
    count=bays or max(1,round(length/3.1))
    rows=[]
    for floor in range(levels):
        count=floor_bays[min(floor,len(floor_bays)-1)] if floor_bays else count
        spacing=length/count
        fh=floor_heights[floor] if floor_heights else (height-.35)/levels
        y0=base+.15+sum(floor_heights[:floor]) if floor_heights else base+.35+floor*(height-.35)/levels
        wh=min(1.75,fh*.63)
        if ornate:wh=min(2.2,fh*.75)
        for i in range(count):
            width=min(1.28,spacing*.58);door=floor==0 and i==door_index
            if floor==0 and lower_types:door='door' in lower_types[i]
            bottom=base+.13 if door else y0+.55
            if ornate:bottom=y0+.18
            hh=fh*.84 if door else wh
            rows.append((spacing*(i+.5),bottom,width,hh,door,floor,i))
    # Real openings: the structural wall stops at window reveals. Otherwise the
    # glass would show an unbroken white wall immediately behind every pane.
    cuts=sorted(set([base,base+height]+[max(base,min(base+height,h)) for _,bt,_,hh,*_ in rows for h in [bt-.035,bt+hh+.035]]))
    for lo,hi in zip(cuts,cuts[1:]):
        if hi-lo<.001:continue
        mid_height=(lo+hi)/2
        holes=[(s-ww/2-.035,s+ww/2+.035) for s,bt,ww,hh,*_ in rows if bt-.035<mid_height<bt+hh+.035]
        ends=sorted(set([0,length]+[max(0,min(length,e)) for pair in holes for e in pair]))
        for l,r in zip(ends,ends[1:]):
            if r-l<.005 or any(l+.001>=p and r-.001<=q for p,q in holes):continue
            kit.box(name,wallmat,pos((l+r)/2,0,mid_height),(r-l,.14,hi-lo),u)
    if panel:
        pitch=.165
        for j in range(int(height/pitch)):
            low=base+j*pitch;high=min(base+height,low+pitch-.006)
            holes=[]
            for s,bt,ww,hh,*_ in rows:
                if high>bt-.08 and low<bt+hh+.1:holes.append((s-ww/2-.1,s+ww/2+.1))
            ends=sorted([0,length]+[max(0,min(length,e)) for pair in holes for e in pair])
            for l,r in zip(ends,ends[1:]):
                if r-l<.02 or any(l+.001>=p and r-.001<=q for p,q in holes):continue
                kit.box(name,wallmat,pos((l+r)/2,.095,(low+high)/2),(r-l,.055,high-low),u)
    for s,bottom,ww,hh,door,floor,i in rows:
        has_awning=floor==0 and (not lower_types or lower_types[i]!='green_door')
        closed=floor==0 and lower_types and lower_types[i]=='green_door'
        window(kit,name,pos(s,.14,bottom),u,outward,ww,hh,trim,glass,white,door,awning if has_awning else None,sign if has_awning else None,closed=closed)
        if ornate:
            kit.box(name,trim,pos(s,.15,base+.36+floor*(height-.35)/levels),(ww+.5,.18,.12),u)
            if floor==levels-1:
                apex=bottom+hh+.42
                kit.face(name,trim,[pos(s-ww*.68,.17,bottom+hh+.19),pos(s+ww*.68,.17,bottom+hh+.19),pos(s,.17,apex)])
    for i in [0,1]:kit.box(name,white,pos(length*i,.15,base+height/2),(.17,.18,height),u)
    kit.box(name,white,pos(length/2,.13,base+height-.08),(length,.24,.16),u)
    return u,outward

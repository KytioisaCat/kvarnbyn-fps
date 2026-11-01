"""Local reviewed cottage details; visible facts and estimates live in houses.json.
M30's paint/standing boards and tiny attic opening are observed. M31 only loses
its enclosing rectangle; its unverified paint and roof heights stay assumed.
"""
import math
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from modelkit import Frame


def clipped_roof(K,b,M,material,wallmat,name):
    """Keep an assumed gable while clipping its planes to the original footprint."""
    foot=b['build_footprint_xz'];rect=foot
    centre=b['centroid_xz'];fr=Frame(centre,b['major_axis_xz'])
    eave=b['base_y_m']+b['wall_height_m'];rise=b['roof_rise_m'];half=b['minor_width_m']/2
    def local(q):
        dx,dz=q[0]-fr.cx,q[1]-fr.cz
        return (dx*fr.u[0]-dz*fr.u[1],dx*fr.v[0]-dz*fr.v[1])
    points=[local(q) for q in foot]
    def height(a,c):return eave+rise*max(0.,1-abs(c)/half)
    def clip(poly,side):
        out=[]
        for a,c in zip(poly,poly[1:]+poly[:1]):
            ia=a[1]*side>=-1e-7;ib=c[1]*side>=-1e-7
            if ia:out.append(a)
            if ia!=ib:
                t=-a[1]/(c[1]-a[1]);out.append((a[0]+t*(c[0]-a[0]),0.))
        return out
    # Triangulate the original concave footprint before half-plane clipping.
    vv=[Vector((*q,0)) for q in points]
    for tri in tessellate_polygon([vv]):
        source=[vv[i] for i in tri] if isinstance(tri[0],int) else tri
        for side in (-1,1):
            q=clip([(v.x,v.y) for v in source],side)
            if len(q)<3:continue
            face=[Vector(fr.p(a,c,height(a,c))) for a,c in q]
            if (face[1]-face[0]).cross(face[2]-face[0]).z<0:face.reverse()
            K.face(name+'_Roof',material,face)
            K.face('COL_'+name+'_Roof',M['collision'],face)
    for a,c in zip(points,points[1:]+points[:1]):
        edge=[a,c]
        if a[1]*c[1]<-1e-8:
            t=-a[1]/(c[1]-a[1]);edge=[a,(a[0]+t*(c[0]-a[0]),0.),c]
        for p,q in zip(edge,edge[1:]):
            face=[]
            for v in [fr.p(*p,eave),fr.p(*q,eave),fr.p(*q,height(*q)),fr.p(*p,height(*p))]:
                if not face or math.dist(face[-1],v)>1e-7:face.append(v)
            if len(face)>2 and math.dist(face[0],face[-1])<1e-7:face.pop()
            if len(face)>=3:
                K.face(name+'_Gables',wallmat,face);K.face(name+'_Gables',wallmat,face[::-1])
                K.face('COL_'+name+'_Roof',M['collision'],face)
            K.beam(name+'_Roofedge',M['trim_light'],fr.p(*p,height(*p)),fr.p(*q,height(*q)),.05,4)
    return eave+rise


def standing_boards(K,b,M,wallmat,foot,floors,ww,wh,sill_h,name,bay):
    if b.get('panel_orientation')!='vertical':return
    base=b['base_y_m'];sock=.45;street=b.get('street_edge',0)
    for i,(a,c) in enumerate(zip(foot,foot[1:]+foot[:1])):
        A=Vector((a[0],-a[1]));B=Vector((c[0],-c[1]));L=(B-A).length
        if L<.1:continue
        d=(B-A)/L;u=(d.x,d.y);out=(u[1],-u[0]);count=max(1,int(L/bay));cuts=[]
        for f,(fy,fh) in enumerate(floors):
            hh=min(wh,fh-.75)
            if L<2.3 or hh<.45:continue
            for k in range(count):
                s=(k+.5)*L/count
                door=f==0 and i==street and k==count//2
                cuts.append((s,base+sock if door else fy+sill_h,1.0 if door else ww,2.1 if door else hh))
        for j in range(math.floor(L/.18)+1):
            s=min(L-.02,j*.18+.01);intervals=[(base+sock,base+b['wall_height_m'])]
            for centre,bt,w,h in cuts:
                if abs(s-centre)<w/2+.13:
                    intervals=[(lo,min(hi,bt-.13)) for lo,hi in intervals if lo<bt-.13]+[(max(lo,bt+h+.13),hi) for lo,hi in intervals if hi>bt+h+.13]
            for lo,hi in intervals:
                if hi-lo<.02:continue
                K.box(name+'_Standing_boards',wallmat,(A.x+d.x*s+out[0]*.055,A.y+d.y*s+out[1]*.055,(lo+hi)/2),(.032,.035,hi-lo),u)


def attic_window(K,b,M,trim,sash,name,add_window):
    spec=b.get('gable_window')
    if not spec:return
    foot=b['build_footprint_xz'];centre=[sum(q[i] for q in foot)/len(foot) for i in (0,1)]
    # modelkit.roof puts its gable at the .32 m overhang, not the wall plane.
    # Place the opening in front of that plane so the solid gable cannot hide it.
    fr=Frame(centre,b['major_axis_xz']);a=spec.get('end',1)*(b['major_length_m']/2+.34)
    side=1 if a>=0 else -1;eave=b['base_y_m']+b['wall_height_m'];y=eave+spec['above_eave_m']
    at=lambda s,d,h:fr.p(a+side*d,s,y+h)
    add_window(K,name,M,at,spec['width_m'],spec['height_m'],trim,muntin_mat=sash)
    # Standing strips on the observed front gable, outside the attic opening.
    half=b['minor_width_m']/2
    for i in range(math.ceil(2*half/.18)):
        c=-half+(i+.5)*.18;top=eave+b['roof_rise_m']*(1-abs(c)/(half+.32))
        intervals=[(eave,top)]
        if abs(c)<spec['width_m']/2+.13:
            intervals=[(eave,y-.12),(y+spec['height_m']+.12,top)]
        for lo,hi in intervals:
            if hi-lo>.02:K.beam(name+'_Gable_boards',M['wall'](b),fr.p(a+side*.045,c,lo),fr.p(a+side*.045,c,hi),.016,4)

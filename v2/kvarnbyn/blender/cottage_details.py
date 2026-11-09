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
    centre=b.get('roof_center_xz',b['centroid_xz']);fr=Frame(centre,b['major_axis_xz'])
    eave=b['base_y_m']+b['wall_height_m'];rise=b['roof_rise_m'];half=b['minor_width_m']/2
    def local(q):
        dx,dz=q[0]-fr.cx,q[1]-fr.cz
        return (dx*fr.u[0]-dz*fr.u[1],dx*fr.v[0]-dz*fr.v[1])
    points=[local(q) for q in foot]
    hipped=b['roof_shape']=='hipped'
    planes=[(0.,-rise/half,rise),(0.,rise/half,rise)]
    if hipped:
        length=b['major_length_m']/2
        planes += [(-rise/half,0.,rise*length/half),(rise/half,0.,rise*length/half)]
    def plane_value(plane,p):return plane[0]*p[0]+plane[1]*p[1]+plane[2]
    def height(a,c):return eave+max(0.,min(plane_value(p,(a,c)) for p in planes))
    def roof_region(poly,index):
        # Split at every roof-plane intersection, including hip diagonals.
        for other in range(len(planes)):
            if index==other:continue
            result=[]
            for a,c in zip(poly,poly[1:]+poly[:1]):
                va=plane_value(planes[index],a)-plane_value(planes[other],a)
                vc=plane_value(planes[index],c)-plane_value(planes[other],c)
                if va<=1e-8:result.append(a)
                if (va<=0)!=(vc<=0):
                    t=va/(va-vc);result.append((a[0]+t*(c[0]-a[0]),a[1]+t*(c[1]-a[1])))
            poly=result
            if len(poly)<3:return []
        return poly
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
        for index in range(len(planes)):
            q=roof_region([(v.x,v.y) for v in source],index)
            if len(q)<3:continue
            face=[Vector(fr.p(a,c,height(a,c))) for a,c in q]
            if (face[1]-face[0]).cross(face[2]-face[0]).z<0:face.reverse()
            K.face(name+'_Roof',material,face)
            K.face('COL_'+name+'_Roof',M['collision'],face)
    for a,c in zip(points,points[1:]+points[:1]):
        edge=[a,c]
        times=[0.,1.]
        for i in range(len(planes)):
            for j in range(i+1,len(planes)):
                va=plane_value(planes[i],a)-plane_value(planes[j],a)
                vc=plane_value(planes[i],c)-plane_value(planes[j],c)
                if va*vc < -1e-8:times.append(va/(va-vc))
        edge=[(a[0]+t*(c[0]-a[0]),a[1]+t*(c[1]-a[1])) for t in sorted(set(times))]
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
            positions=b.get('street_bays_m',[]) if i==street else []
            if not positions:positions=[(k+.5)*L/count for k in range(count)]
            for k,s in enumerate(positions):
                door=f==0 and i==street and k==b.get('street_door_index',len(positions)//2) and b.get('street_door',True)
                cuts.append((s,base+sock if door else fy+sill_h,1.0 if door else ww,2.1 if door else hh))
        for j in range(math.floor(L/.18)+1):
            s=min(L-.02,j*.18+.01);intervals=[(base+sock,base+b['wall_height_m'])]
            for centre,bt,w,h in cuts:
                if abs(s-centre)<w/2+.13:
                    intervals=[(lo,min(hi,bt-.13)) for lo,hi in intervals if lo<bt-.13]+[(max(lo,bt+h+.13),hi) for lo,hi in intervals if hi>bt+h+.13]
            for lo,hi in intervals:
                if hi-lo<.02:continue
                K.box(name+'_Standing_boards',wallmat,(A.x+d.x*s+out[0]*b.get('panel_batten_depth_m',.055),A.y+d.y*s+out[1]*b.get('panel_batten_depth_m',.055),(lo+hi)/2),(.032,b.get('panel_batten_thickness_m',.035),hi-lo),u)


def attic_window(K,b,M,trim,sash,name,add_window):
    spec=b.get('gable_window')
    if not spec:return
    foot=b['build_footprint_xz'];centre=[sum(q[i] for q in foot)/len(foot) for i in (0,1)]
    # modelkit.roof puts its gable at the .32 m overhang, not the wall plane.
    # Place the opening in front of that plane so the solid gable cannot hide it.
    fr=Frame(b.get('roof_center_xz',centre),b['major_axis_xz']);a=spec.get('end',1)*(b['major_length_m']/2+.34)
    side=1 if a>=0 else -1;eave=b['base_y_m']+b['wall_height_m'];y=eave+spec['above_eave_m']
    at=lambda s,d,h:fr.p(a+side*d,s,y+h)
    if spec.get('front_xz'):
        x,z=spec['front_xz']
        at=lambda s,d,h:(x+fr.v[0]*s+fr.u[0]*side*(d+.045),-z+fr.v[1]*s+fr.u[1]*side*(d+.045),y+h)
    lights=spec.get('vertical_lights',0)
    add_window(K,name,M,at,spec['width_m'],spec['height_m'],trim,muntin_mat=sash,muntins=not lights)
    for i in range(1,lights):
        K.box(name+'_Attic_lights',sash,at(spec['width_m']*(i/lights-.5),.07,spec['height_m']/2),(.045,.05,spec['height_m']),fr.v)
    if spec.get('front_xz'):return
    # Standing strips on the observed front gable, outside the attic opening.
    half=b['minor_width_m']/2
    for i in range(math.ceil(2*half/.18)):
        c=-half+(i+.5)*.18;top=eave+b['roof_rise_m']*(1-abs(c)/(half+.32))
        intervals=[(eave,top)]
        if abs(c)<spec['width_m']/2+.13:
            intervals=[(eave,y-.12),(y+spec['height_m']+.12,top)]
        for lo,hi in intervals:
            if hi-lo>.02:K.beam(name+'_Gable_boards',M['wall'](b),fr.p(a+side*.045,c,lo),fr.p(a+side*.045,c,hi),.016,4)


def roof_dormer(K,b,M,trim,sash,name,add_window):
    """Observed small street gable; roof valleys meet the main roof planes.

    Dimensions live in the area review. Both visible roof/cheeks and collider
    faces share the same vertices; the main roof remains underneath.
    """
    spec=b.get('roof_dormer')
    if not spec:return
    fr=Frame(b['roof_center_xz'],b['major_axis_xz'])
    side=spec['side'];half=b['minor_width_m']/2+.32
    eave=b['base_y_m']+b['wall_height_m'];rise=b['roof_rise_m']
    a=spec['centre_a_m'];w=spec['width_m']/2
    low=eave+spec['side_above_eave_m'];high=eave+spec['ridge_above_eave_m']
    front=side*(half+.03)
    join=lambda height:side*half*(1-(height-eave)/rise)
    at=lambda s,d,h:fr.p(a+s,front+side*d,eave+h)
    def face(label,mat,points):
        K.face(name+label,mat,points);K.face(name+label,mat,points[::-1])
        K.face('COL_'+name+label,M['collision'],points)
    front_points=[fr.p(a-w,front,eave-.02),fr.p(a+w,front,eave-.02),fr.p(a+w,front,low),fr.p(a,front,high),fr.p(a-w,front,low)]
    face('_Dormer_front',M['wall'](b),front_points)
    for sign in (-1,1):
        face('_Dormer_roof',M['roof_for'](b),[fr.p(a,front,high+.025),fr.p(a+sign*w,front,low+.025),fr.p(a+sign*w,join(low),low+.025),fr.p(a,join(high),high+.025)])
        face('_Dormer_cheek',M['wall'](b),[fr.p(a+sign*w,front,eave),fr.p(a+sign*w,join(low),low),fr.p(a+sign*w,front,low)])
        K.beam(name+'_Dormer_barge',trim,fr.p(a,front+side*.045,high),fr.p(a+sign*w,front+side*.045,low),.055,4)
    add_window(K,name+'_Dormer_window',M,lambda s,d,h:at(s,d,spec['window_above_eave_m']+h),spec['window_width_m'],spec['window_height_m'],trim,muntin_mat=sash)

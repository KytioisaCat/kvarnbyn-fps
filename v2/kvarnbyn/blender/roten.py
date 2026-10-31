"""M29 from reviewed exterior references; dimensions and hidden detail remain estimates.

Own geometry/materials only. See reference/roten-m/OBSERVATIONER.md. The original
OSM shell is retained, but the invented tall hipped roof is replaced by low joined
volumes. This authoring helper deliberately does not alter the frozen Torget kit.
"""
import math
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from modelkit import Frame, color, window, text
from blender_materials import solid_material


def sett_segments(city):
    """OSM sett tags verified around M29; material only, existing geometry wins."""
    reviewed = {'w330280688', 'w92332123', 'w461711525', 'w236136748'}
    return [(a, b, r['width_m']/2) for r in city['roads']
            if r['id'] in reviewed and r.get('surface') == 'sett'
            for a,b in zip(r['line_xz'],r['line_xz'][1:])]


def is_sett(triangle, segments):
    x=sum(p[0] for p in triangle)/3; z=sum(p[2] for p in triangle)/3
    if not (75 <= x <= 125 and 80 <= z <= 135): return False
    for a,b,radius in segments:
        dx,dz=b[0]-a[0],b[1]-a[1]
        t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/max(1e-8,dx*dx+dz*dz)))
        if math.hypot(x-a[0]-t*dx,z-a[1]-t*dz) <= radius+.02:return True
    return False


def build_house(K, M, ground, b, spec):
    axis = spec['axis_xz']; length = math.hypot(*axis)
    fr = Frame(spec['origin_xz'], [a / length for a in axis])
    base = b['base_y_m']; name = 'Roten_M29'
    wall = M['panel']
    trim = solid_material('M29_ochre_trim', color(spec['trim_color']), .74)
    sash = solid_material('M29_redbrown_sash', color(spec['sash_color']), .66)
    board = solid_material('M29_white_board', color(spec['wall_color']), .84)
    poly = b['footprint_xz']
    # CCW in Blender. Normal points out from each edge.
    area = sum(a[0]*c[1]-c[0]*a[1] for a,c in zip(poly,poly[1:]+poly[:1]))
    if area > 0: poly = list(reversed(poly))
    def ab(p):
        dx, dz = p[0]-fr.cx, p[1]-fr.cz
        return dx*fr.u[0]-dz*fr.u[1], dx*fr.v[0]-dz*fr.v[1]
    def eave_at(a,c):
        if a > 11.7 and c > -4.55: return 3.25
        if c > -1.6 and a < 9.1: return 2.65
        return 2.85
    # Each tuple is centre along edge, sill, width, height, door.
    for a, c in zip(poly, poly[1:]+poly[:1]):
        A, B = Vector((a[0],-a[1])), Vector((c[0],-c[1])); d=B-A; L=d.length
        u=(d.x/L,d.y/L); out=(u[1],-u[0]); mid=ab(((a[0]+c[0])/2,(a[1]+c[1])/2))
        h=eave_at(*mid); low=min(ground(*a),ground(*c),base)-.3
        # Fill the foundation down to actual terrain; no hovering cottage.
        K.face(name+'_Stone',M['stone'],[(A.x,A.y,low),(B.x,B.y,low),(B.x,B.y,base+.12),(A.x,A.y,base+.12)])
        K.face('COL_'+name,M['collision'],[(A.x,A.y,low),(B.x,B.y,low),(B.x,B.y,base+h),(A.x,A.y,base+h)])
        at=lambda s,o,y:(A.x+u[0]*s+out[0]*o,A.y+u[1]*s+out[1]*o,base+y)
        openings=[]
        # Street-facing gable is deliberately blank below its observed round attic window.
        if mid[1] > 5.4:
            pass
        elif mid[0] > 17.7:
            for t in (.28,.68):
                openings += [(L*t,.55,1.05,1.65,False),(L*t,2.65,.95,.40,False)]
        elif 8.6 < mid[0] < 9.2 and mid[1] > -1.6:
            openings=[(L*.55,.12,1.0,2.05,True)]
        elif 11.5 < mid[0] < 12.2 and mid[1] > -1.7:
            openings=[(L*.55,.60,1.05,1.40,False)]
        elif L > 3.2:
            count=max(1,round(L/4.0))
            openings=[(L*(i+.5)/count,.60,1.03,1.50,False) for i in range(count)]
        cuts=sorted(set([0,h]+[max(0,min(h,y)) for s,bt,w,hh,door in openings for y in (bt-.03,bt+hh+.03)]))
        for lo,hi in zip(cuts,cuts[1:]):
            y=(lo+hi)/2
            holes=[(s-w/2-.035,s+w/2+.035) for s,bt,w,hh,_ in openings if bt-.035<y<bt+hh+.035]
            ends=sorted(set([0,L]+[max(0,min(L,v)) for pair in holes for v in pair]))
            for l,r in zip(ends,ends[1:]):
                if r-l < .002 or any(l+.001>=p and r-.001<=q for p,q in holes): continue
                K.box(name+'_Walls',wall,at((l+r)/2,0,y),(r-l,.12,hi-lo),u)
        # Actual standing lock strips, rather than the old horizontal log bands.
        for i in range(int(L/.18)+1):
            s=min(L,i*.18)
            intervals=[(0,h)]
            for centre,bt,w,hh,_ in openings:
                if abs(s-centre) < w/2+.10:
                    intervals=[(lo,min(hi,bt-.1)) for lo,hi in intervals if lo<bt-.1]+[(max(lo,bt+hh+.1),hi) for lo,hi in intervals if hi>bt+hh+.1]
            for lo,hi in intervals:
                if hi-lo>.02: K.box(name+'_Vertical_boards',board,at(s,.085,(lo+hi)/2),(.035,.035,hi-lo),u)
        for s,bt,w,hh,door in openings:
            window(K,name,at(s,.08,bt),u,out,w,hh,trim,M['glass'],sash,door=door)
            for dx in (-w/2+.065,w/2-.065): K.box(name+'_Sash',sash,at(s+dx,.18,bt+hh/2),(.05,.04,hh-.04),u)
            if door:
                for y in (bt+.10,bt+hh-.02): K.box(name+'_Door',sash,at(s,.19,y),(w-.12,.05,.10),u)
                text('Rot. M Nr 29',name+'_Address',at(s,.19,bt+hh+.33),out,.13,M['black'])
        for s in (0,L): K.box(name+'_Corners',board,at(s,.10,h/2),(.13,.12,h),u)
        K.box(name+'_Sill',board,at(L/2,.09,.08),(L,.15,.14),u)

    def clip(points, coordinate, boundary, keep):
        result=[]
        for a,c in zip(points,points[1:]+points[:1]):
            ia=(a[coordinate]-boundary)*keep>=-1e-7; ib=(c[coordinate]-boundary)*keep>=-1e-7
            if ia:result.append(a)
            if ia!=ib:
                t=(boundary-a[coordinate])/(c[coordinate]-a[coordinate]); result.append(tuple(a[j]+t*(c[j]-a[j]) for j in range(2)))
        return result

    for volume in spec['roofs']:
        contour=volume['polygon_ab']; coord=1 if volume['ridge_axis']=='a' else 0
        ridge=volume['ridge_at']; hw=volume['half_width']; eave=volume['eave_m']; rise=volume['rise_m']
        def height(a,c): return base+eave+rise*max(0,1-abs((a,c)[coord]-ridge)/hw)
        # Split at ridge before triangulation, giving actual angled roof/COL planes.
        for side in (-1,1):
            points=clip(contour,coord,ridge,side)
            if len(points)<3:continue
            vv=[Vector((a,c,0)) for a,c in points]
            for tri in tessellate_polygon([vv]):
                q=[vv[i] for i in tri] if isinstance(tri[0],int) else tri
                p=[fr.p(t.x,t.y,height(t.x,t.y)) for t in q]
                if (Vector(p[1])-Vector(p[0])).cross(Vector(p[2])-Vector(p[0])).z < 0:p.reverse()
                K.face(name+'_Roof_'+volume['id'],M['roof'],p)
                K.face('COL_'+name+'_Roof',M['collision'],p)
        # Gable fill to roof, edge boards, gutter and vertical board detail.
        for a,c in zip(contour,contour[1:]+contour[:1]):
            lo=base+eave; ha,hc=height(*a),height(*c)
            # Subdivide the edge at ridge so a gable has its true triangular peak.
            qq=[a,c]
            if (a[coord]-ridge)*(c[coord]-ridge)<-1e-8:
                t=(ridge-a[coord])/(c[coord]-a[coord]); qq=[a,tuple(a[j]+t*(c[j]-a[j]) for j in range(2)),c]
            for p,q in zip(qq,qq[1:]):
                roof_p,roof_q=fr.p(*p,height(*p)),fr.p(*q,height(*q))
                if max(height(*p),height(*q))>lo+.01:
                    face=[]
                    for vertex in [fr.p(*p,lo),fr.p(*q,lo),roof_q,roof_p]:
                        if not face or math.dist(vertex,face[-1])>1e-7:face.append(vertex)
                    if math.dist(face[0],face[-1])<1e-7:face.pop()
                    K.face(name+'_Gables',wall,face)
                    # Backface also makes estimated roof joins solid in both views.
                    K.face(name+'_Gables',wall,face[::-1])
                    K.face('COL_'+name+'_Roof',M['collision'],face)
                K.beam(name+'_Bargeboards',board,roof_p,roof_q,.065,4)
                dist=math.dist(p,q)
                for j in range(max(1,math.ceil(dist/.18))):
                    t=(j+.5)/max(1,math.ceil(dist/.18)); v=tuple(p[k]+t*(q[k]-p[k]) for k in range(2)); top=height(*v)
                    if top>lo+.02: K.beam(name+'_Gable_boards',board,fr.p(*v,lo),fr.p(*v,top),.016,4)
        # One modest brick chimney per old house volume.
        if volume['id'] in ('west','street'):
            ac=(6,-4.025) if volume['id']=='west' else (15.03,.2)
            top=height(*ac)
            K.box(name+'_Chimneys',M['brick'],fr.p(*ac,top+.35),(.6,.65,1.05),fr.u)
            K.box(name+'_Chimneys',M['curb'],fr.p(*ac,top+.90),(.75,.78,.1),fr.u)

    # Recognisable round attic window on the NE street gable (observed).
    specw=spec['round_window']; a,c=specw['a'],specw['b']
    centre=Vector(fr.p(a,c+.035,base+specw['bottom_m']+specw['diameter_m']/2))
    normal=Vector((*fr.v,0)); horizontal=Vector((*fr.u,0)); vertical=Vector((0,0,1))
    def ring(radius,depth):
        return [centre+normal*depth+(horizontal*math.cos(i*math.tau/48)+vertical*math.sin(i*math.tau/48))*radius for i in range(48)]
    r=specw['diameter_m']/2
    K.face(name+'_Round_glass',M['glass_dark'],list(reversed(ring(r,.12))))
    for outer,inner,material,depth in ((r+.12,r+.05,trim,.14),(r+.05,r,sash,.17)):
        A,B=ring(outer,depth),ring(inner,depth)
        for i in range(48):
            j=(i+1)%48;K.face(name+'_Round_frame',material,[A[i],A[j],B[j],B[i]])
            K.face(name+'_Round_frame',material,[B[i],B[j],A[j],A[i]])
    for sign in (-1,1):
        d=(horizontal+vertical*sign).normalized()*r
        K.beam(name+'_Round_cross',sash,centre+normal*.20-d,centre+normal*.20+d,.017,6)
    for a,c in ((18.2,5.71),(11.86,5.71),(18.2,-4.39)):
        K.beam(name+'_Downpipes',board,fr.p(a,c,base+.1),fr.p(a,c,base+3.15),.047,8)


def build_garden(K, M, meta):
    """Observed low edges and garden fencing, at explicitly estimated coordinates."""
    timber=solid_material('M29_weathered_gate',color('#82745b'),.88)
    for wall in meta.get('walls',[]):
        a,b=wall['a'],wall['b'];L=math.dist(a,b)
        u=((b[0]-a[0])/L,-(b[1]-a[1])/L);base,top=wall['bottom_y'],wall['top_y'];h=top-base
        K.box('COL_Roten_wall',M['collision'],((a[0]+b[0])/2,-(a[1]+b[1])/2,(base+top)/2),(L,wall['width_m'],h),u)
        for row in range(2):
            n=max(1,math.ceil(L/.48));step=L/n
            for i in range(n):
                fraction=(i+.5)/n;z=base+h*(row+.5)/2
                K.box('Roten_wall',M['stone'],(a[0]+(b[0]-a[0])*fraction,-a[1]-(b[1]-a[1])*fraction,z),
                      (step-.012,wall['width_m']+(.018 if (i+row)%2 else 0),h/2-.012),u)
    def fence(points,height):
        for a,b in zip(points,points[1:]):
            L=math.hypot(b[0]-a[0],b[2]-a[2])
            if L<.02:continue
            u=((b[0]-a[0])/L,-(b[2]-a[2])/L)
            # Thin board gaps cannot fit a player; solid narrow collision matches that barrier.
            K.box('COL_Roten_fence',M['collision'],((a[0]+b[0])/2,-(a[2]+b[2])/2,(a[1]+b[1])/2+height/2),(L,.09,height),u)
            n=max(1,round(L/.15))
            for i in range(n+1):
                t=i/n;x=a[0]+(b[0]-a[0])*t;z=a[2]+(b[2]-a[2])*t;y=a[1]+(b[1]-a[1])*t
                K.box('Roten_fence',timber,(x,-z,y+height/2),(.075,.055,height-.08),u)
                K.face('Roten_fence',timber,[(x-u[0]*.0375,-z-u[1]*.0375,y+height-.08),(x+u[0]*.0375,-z+u[1]*.0375,y+height-.08),(x,-z,y+height)])
            for fraction in (.26,.72):
                K.beam('Roten_fence',timber,(a[0],-a[2],a[1]+height*fraction),(b[0],-b[2],b[1]+height*fraction),.032,4)
    for item in meta.get('fences',[]):
        if item['kind']=='open_gate':
            a,b=item['hinge_xz'],item['latch_xz'];dx,dz=b[0]-a[0],b[1]-a[1]
            end=[a[0]+dz,a[1]-dx];y=item['base_y']
            fence([[a[0],y,a[1]],[end[0],y,end[1]]],item['height_m'])
            for p in (a,b):K.box('Roten_gateposts',timber,(p[0],-p[1],y+.55),(.12,.12,1.1))
        else:fence(item['points'],item['height_m'])
    for steps in meta.get('steps',[]):
        for tread in steps['treads']:
            for contour in tread['contours']:
                # Small clipped treads have no holes; keep their exact outside cut.
                poly=contour['outer'];top=tread['top_y'];bottom=top-steps['riser_m']
                K.polygon('Roten_steps',M['stone'],poly,top)
                for a,b in zip(poly,poly[1:]+poly[:1]):
                    p=[(a[0],-a[1],bottom),(b[0],-b[1],bottom),(b[0],-b[1],top),(a[0],-a[1],top)]
                    K.face('Roten_steps',M['stone'],p);K.face('Roten_steps',M['stone'],p[::-1])

"""Own schematic cycle/arrow paint on the reviewed northern-bank asphalt.

White cycle markings are observed in Maps May2026. Exact glyph shape, spacing,
width and placement are estimates. No image pixels, collision, rail or furniture.
Every vertex is 1cm over actual authored SITE asphalt triangles; no DTM fallback.
"""
import bisect
import math
from modelkit import color
from blender_materials import solid_material


class _AsphaltFloor:
    def __init__(self,site):
        self.grid={};self.cell=2.
        for key,kind in site.get('north_bank_mesh_kinds',{}).items():
            if kind!='asphalt':continue
            for triangles in site['meshes'].get(key,{}).values():
                for a,b,c in triangles:
                    den=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
                    if abs(den)<1e-12:continue
                    record=(a,b,c,den)
                    for ix in range(math.floor(min(a[0],b[0],c[0])/self.cell),math.floor(max(a[0],b[0],c[0])/self.cell)+1):
                        for iz in range(math.floor(min(a[2],b[2],c[2])/self.cell),math.floor(max(a[2],b[2],c[2])/self.cell)+1):
                            self.grid.setdefault((ix,iz),[]).append(record)

    def height(self,x,z):
        for a,b,c,den in self.grid.get((math.floor(x/self.cell),math.floor(z/self.cell)),[]):
            u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/den
            v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/den
            if min(u,v,1-u-v)>=-1e-6:return u*a[1]+v*b[1]+(1-u-v)*c[1]
        return None


class _Route:
    def __init__(self,points):
        self.points=points;self.s=[0.]
        for a,b in zip(points,points[1:]):self.s.append(self.s[-1]+math.dist(a,b))
        self.length=self.s[-1]

    def point(self,s):
        s=max(0.,min(self.length,s));i=min(len(self.points)-2,max(0,bisect.bisect_right(self.s,s)-1))
        t=(s-self.s[i])/max(1e-9,self.s[i+1]-self.s[i]);a,b=self.points[i],self.points[i+1]
        return (a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)

    def frame(self,s):
        p=self.point(s);a,b=self.point(s-.25),self.point(s+.25)
        dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz)
        forward=(dx/length,dz/length);across=(-forward[1],forward[0])
        return p,forward,across


def _ribbon(a,b,width):
    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
    if length<1e-8:return []
    nx,ny=-dy/length*width/2,dx/length*width/2
    pieces=[];count=max(1,math.ceil(length/.12))
    for i in range(count):
        t0,t1=i/count,(i+1)/count
        p=(a[0]+dx*t0,a[1]+dy*t0);q=(a[0]+dx*t1,a[1]+dy*t1)
        pieces.append([(p[0]+nx,p[1]+ny),(q[0]+nx,q[1]+ny),(q[0]-nx,q[1]-ny),(p[0]-nx,p[1]-ny)])
    return pieces


def _glyph():
    faces=[]
    # A schematic side-view bicycle with rear/front wheel along the route.
    # Its own frame stays within about0.9m across the2.8m asphalt lane.
    for cx,cy in ((.15,-.5),(.15,.5)):
        for i in range(24):
            a,b=math.tau*i/24,math.tau*(i+1)/24
            faces.append([(cx+r*math.cos(t),cy+r*math.sin(t)) for r,t in ((.30,a),(.30,b),(.26,b),(.26,a))])
    rear=(.15,-.5);front=(.15,.5);crank=(0.,-.05);seat=(-.28,-.25);head=(-.25,.37)
    for a,b in [(rear,seat),(seat,crank),(crank,rear),(crank,head),(head,seat),(head,front),
                (seat,(-.40,-.25)),((-.40,-.40),(-.40,-.10)),
                (head,(-.42,.45)),((-.42,.45),(-.42,.64))]:faces.extend(_ribbon(a,b,.04))
    # Stem and triangle meet without coplanar overlapping faces.
    faces.extend(_ribbon((0,1.02),(0,1.58),.09))
    faces.append([(-.28,1.58),(.28,1.58),(0,2.0)])
    return faces


def build(K,M,SITE):
    meta=SITE.get('north_bank',{})
    result=dict(attempted=0,built=0,omitted=[],glyphs=[],status='Own cycle/arrow paint; observed motif, all metric shape/positions estimated')
    points=meta.get('route_xz',[])
    if not meta.get('active') or len(points)<2:return result
    route=_Route(points);floor=_AsphaltFloor(SITE);faces=_glyph()
    paint=solid_material('Northbank_white_road_paint',color('#e5e4dc'),.88)
    blend=float(meta.get('endpoint_blend_m',6.))
    for station in (18.,42.,66.):
        result['attempted']+=1
        if station-.85<blend or station+2.0>route.length-blend:
            result['omitted'].append(dict(station_m=station,reason='endpoint transition'))
            continue
        origin,forward,across=route.frame(station)
        def world(p):return (origin[0]+across[0]*p[0]+forward[0]*p[1],origin[1]+across[1]*p[0]+forward[1]*p[1])
        ready=[];valid=True
        for face in faces:
            xz=[world(p) for p in face]
            # Corners, edge midpoints and centre must all be actual asphalt.
            probes=xz+[((a[0]+b[0])/2,(a[1]+b[1])/2) for a,b in zip(xz,xz[1:]+xz[:1])]
            probes.append((sum(p[0] for p in xz)/len(xz),sum(p[1] for p in xz)/len(xz)))
            if any(floor.height(*p) is None for p in probes):valid=False;break
            pts=[(x,-z,floor.height(x,z)+.01) for x,z in xz]
            area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(pts,pts[1:]+pts[:1]))
            if area<0:pts.reverse()
            ready.append(pts)
        if not valid:
            result['omitted'].append(dict(station_m=station,reason='glyph crosses asphalt boundary'))
            continue
        for pts in ready:K.face('Northbank_cycle_markings',paint,pts)
        result['built']+=1
        result['glyphs'].append(dict(station_m=station,centre_xz=list(origin),paint_faces=len(ready),floor_offset_m=.01))
    return result

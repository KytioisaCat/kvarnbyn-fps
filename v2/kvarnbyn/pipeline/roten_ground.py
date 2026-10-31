"""Small, observed M29 garden/courtyard study. No file writes or GPU work.

RotenGround(city, forbidden, work, raw_height, base_surface_height, offset)
expects vectorised callbacks in RAW metres above sea level. The connection
callback must sample the existing FINISHED walking surface, including its lift
(e.g. SurfaceReference on the original urban triangles with lift=0).

All surface height_fn callbacks and height() return FINISHED raw heights;
triangulate with lift=0. Arrays/structural *_y fields use local Y = raw-offset.
Render surfaces individually, preserving grading boundaries. The stair ramp
has render=False, collision_only=True; its .steps treads are the visible mesh.
Cut terrain under ALL coverage, including the invisible stair ramp, and give
all surface meshes matching COL geometry. Do not extend urban conformation
outside coverage: garden margins already blend to raw terrain.

Reference: reference/roten-m/OBSERVATIONER.md, inspected by root 2026-10-30.
Surface character, low stone edge, steps/gate/vegetation are observed. ALL
contours, placement, species, dimensions and heights below are estimates.
No M30/M31 terrace/wall is created.
"""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union


def _parts(g, kind):
    if g.is_empty: return []
    if g.geom_type == kind: return [g]
    return [p for child in getattr(g, 'geoms', []) for p in _parts(child, kind)]


def _contours(g):
    return [dict(outer=[list(p) for p in q.exterior.coords[:-1]],
                 holes=[[list(p) for p in r.coords[:-1]] for r in q.interiors]) for q in _parts(g, 'Polygon')]


def _vectors(x, z):
    x, z = np.broadcast_arrays(np.atleast_1d(np.asarray(x, float)), np.atleast_1d(np.asarray(z, float)))
    return x.ravel(), z.ravel(), x.shape


def _ease(t):
    t = np.clip(t, 0., 1.)
    return t*t*(3.-2.*t)


class RotenGround:
    ORIGIN = np.array([95.921, 111.42])
    U = np.array([.559, .829])
    V = np.array([.829, -.559])
    HOUSE = 'w92332120'

    def __init__(self, city, forbidden, work, raw_height, base_surface_height, offset):
        self.city, self.raw_height, self.connection_height = city, raw_height, base_surface_height
        self.offset = float(offset)
        self.surfaces, self.walls, self.fences, self.steps, self.rocks = [], [], [], [], []
        self.coverage = Polygon()
        self._inv = np.linalg.inv(np.column_stack((self.U, self.V)))
        self._active = any(b.get('id') == self.HOUSE for b in city.get('buildings', []))
        self._work = box(75, 80, 125, 135).intersection(work)
        self._routes = []
        if not self._active: return

        houses = unary_union([Polygon(b.get('build_footprint_xz', b['footprint_xz'])).union(Polygon(b['footprint_xz']))
                               for b in city['buildings']]).buffer(.045)
        road_shapes = []
        self._entry_road = Polygon()
        for r in city.get('roads', []):
            if r.get('tunnel') or len(r.get('line_xz', [])) < 2: continue
            line = LineString(r['line_xz'])
            if not line.intersects(self._work.buffer(5)): continue
            radius = float(r.get('width_m', 2.))/2
            band = line.buffer(radius, cap_style=1 if r.get('kind') in ('footway','path','cycleway','pedestrian','steps') else 2, join_style=2)
            road_shapes.append(band)
            if r.get('id') == 'w330280688': self._entry_road = band
        self._road_bands = unary_union(road_shapes)
        self.forbidden = houses.union(self._road_bands).union(forbidden)
        self._allowed = self._work.difference(self.forbidden)
        if self._entry_road.is_empty: self._entry_road = self._road_bands
        boundary = LineString() if self._road_bands.is_empty else self._road_bands.boundary.intersection(self._work.buffer(2))
        self._street_anchors = shapely.get_coordinates(boundary.segmentize(.25))
        self._street_heights = np.asarray(self.connection_height(self._street_anchors[:,0], self._street_anchors[:,1]))

        # DTM samples inside the observed courtyard opening, not a claimed floor survey.
        q = np.asarray([self.xz(a,b) for a in (9.6,10.3,11.1) for b in (-.6,1.6,4.)])
        self.courtyard_raw = float(np.median(self.raw_height(q[:,0],q[:,1])))
        self.front_raw = self.courtyard_raw - .02
        self.step_rise_m = .55/3
        self.step_low_raw = self.front_raw - .55
        courtyard = self.poly([(8.91,-1.52),(11.86,-1.52),(11.85,5.71),(8.90,5.71)]).intersection(self._allowed)
        self._courtyard = courtyard
        self._gate_low_line = LineString([self.xz(14.40,8.78),self.xz(15.65,8.78)])

        self._proposals = []
        self._add('m29_courtyard','paving',courtyard,self._constant(self.courtyard_raw),50)
        self._add('m29_gravel_entry','gravel',self.poly([(8.90,5.65),(11.85,5.65),(11.6,10.9),(8.9,9.8)]),self._entry_height,30)
        self._add('m29_front_landing','paving',self.poly([(14.40,5.76),(15.65,5.76),(15.65,7.58),(14.40,7.58)]),self._constant(self.front_raw),50)
        self._add('m29_gate_steps','paving',self.poly([(14.40,7.58),(15.65,7.58),(15.65,8.78),(14.40,8.78)]),self._step_height,60,
                  render=False,collision_only=True,visible_height_tolerance_m=self.step_rise_m)
        self._add('m29_gate_approach','gravel',self.poly([(14.40,8.78),(15.65,8.78),(16.10,13.9),(14.20,13.0)]),self._gate_approach,35)

        west = self.poly([(1.,-6.58),(11.7,-6.58),(11.7,-8.4),(9.4,-9.0),(2.5,-8.8),(1.,-8.2)]).intersection(self._allowed)
        south = self.poly([(12.2,-4.44),(18.7,-4.44),(19.7,-5.9),(17.7,-7.8),(12.2,-7.9)]).intersection(self._allowed)
        self._garden = west.union(south)
        west_h = float(self.raw_height(*self._xy_arrays([(7.,-7.45)]))[0])
        south_h = float(self.raw_height(*self._xy_arrays([(15.7,-6.3)]))[0])
        self._west_grade = self._terrace(west,west_h)
        self._south_grade = self._terrace(south,south_h)
        self._add('m29_west_grass','grass',west,self._west_grade,10)
        self._add('m29_south_grass','grass',south,self._south_grade,10)
        # A small sitting pad belongs to the same lower level; no new retaining wall.
        self._add('m29_sitting_pad','paving',self.poly([(14.,-7.1),(16.6,-7.1),(16.6,-5.25),(14.,-5.25)]),self._south_grade,40)
        self._add('m29_front_planting','grass',self.poly([(12.4,5.76),(14.40,5.76),(14.40,7.42),(12.4,7.42)]),self._constant(self.front_raw),20)

        for ident, outline, base, bulge in [
            ('m29_west_bedrock',[(1.6,-6.66),(4.1,-6.66),(4.5,-7.6),(3.4,-8.1),(1.7,-7.7)],self._west_grade,.22),
            ('m29_south_bedrock',[(17.0,-5.1),(18.6,-5.0),(19.1,-5.9),(18.1,-6.8),(16.9,-6.4)],self._south_grade,.18),
            ('m29_front_bedrock',[(12.5,5.84),(13.65,5.84),(14.12,6.55),(13.80,7.26),(12.55,7.20)],self._constant(self.front_raw),.14),
        ]:
            geom = self.poly(outline).intersection(self._allowed)
            fn = self._rock_grade(geom,base,bulge)
            self._add(ident,'rock',geom,fn,45)
            self.rocks.append(dict(id=ident,kind='terrain_outcrop',contours=_contours(geom),height_status='estimated low terrain dome',max_bulge_m=bulge))

        # Disjoint surfaces make material and grading boundaries explicit mesh edges.
        used = Polygon()
        for s in sorted(self._proposals,key=lambda s:-s['priority']):
            s['geom'] = s['geom'].intersection(self._allowed).difference(used).buffer(0)
            if s['geom'].is_empty or s['geom'].area < .02: continue
            self.surfaces.append(s); used = used.union(s['geom'])
        self.coverage = used.buffer(0)
        if self.coverage.is_empty:
            self._active=False
            return
        self._structures()
        self._routes = [dict(id='m29_courtyard_entry',ab=[(10.3,9.8),(10.3,5.8),(10.3,1.5),(10.3,-.5)]),
                        dict(id='m29_open_gate_steps',ab=[(15.025,12.6),(15.025,8.78),(15.025,7.58),(15.025,6.1)])]

    def xz(self,a,b): return self.ORIGIN+self.U*a+self.V*b
    def _xy_arrays(self,ab):
        q=np.asarray([self.xz(a,b) for a,b in ab]);return q[:,0],q[:,1]
    def ab(self,x,z): return self._inv @ np.vstack((x-self.ORIGIN[0],z-self.ORIGIN[1]))
    def poly(self,ab): return Polygon([self.xz(a,b) for a,b in ab])
    def _constant(self,h):
        return lambda x,z: np.full(np.broadcast(np.atleast_1d(x),np.atleast_1d(z)).shape,float(h))
    def _add(self,ident,kind,geom,fn,priority,**extra):
        record=dict(id=ident,kind=kind,geom=geom,height_fn=fn,lift_m=0.,priority=priority,
                    render=True,collision_only=False,estimated=True)
        record.update(extra)
        self._proposals.append(record)

    def _connection(self,x,z,target,inner,road=None):
        x,z,shape=_vectors(x,z);pts=shapely.points(x,z)
        road=self._entry_road if road is None else road
        if road.is_empty:return np.full(shape,target)
        d=shapely.distance(pts,road)
        q=shapely.get_point(shapely.shortest_line(pts,road),-1)
        h=np.asarray(self.connection_height(shapely.get_x(q),shapely.get_y(q)),float)
        # A nearest edge can switch between Royens gata and Roten M, whose
        # heights differ. Extend their local weighted plane into the approach;
        # keep the exact preserved street height only right at the boundary.
        if road is self._road_bands and len(self._street_anchors)>=3:
            for i in range(len(x)):
                if d[i] < .005: continue
                dx=self._street_anchors[:,0]-x[i];dz=self._street_anchors[:,1]-z[i]
                distance2=dx*dx+dz*dz;take=np.argsort(distance2)[:40]
                A=np.column_stack((dx[take],dz[take],np.ones(len(take))))
                w=1/(distance2[take]+.04)
                centre=float(np.median(self._street_heights[take]))
                fit=np.linalg.solve((A.T*w)@A+np.diag([.01,.01,.00001]),(A.T*w)@(self._street_heights[take]-centre))
                smooth=centre+fit[2]
                h[i] += (smooth-h[i])*float(_ease(d[i]/.45))
        di=shapely.distance(pts,inner)
        weight=_ease(d/np.maximum(d+di,1e-8))
        weight=np.where(d>=4.,1.,weight)
        return (h*(1-weight)+target*weight).reshape(shape)
    def _entry_height(self,x,z): return self._connection(x,z,self.courtyard_raw,self._courtyard)
    def _gate_approach(self,x,z):
        # This approach can be clipped by Royens gata before reaching Roten M.
        # Tie to whichever preserved street band actually owns the cut edge.
        return self._connection(x,z,self.step_low_raw,self._gate_low_line,self._road_bands)
    def _step_height(self,x,z):
        x,z,shape=_vectors(x,z);b=self.ab(x,z)[1]
        return (self.step_low_raw+.55*np.clip((8.78-b)/1.2,0,1)).reshape(shape)
    def _terrace(self,geom,level):
        def fn(x,z):
            x,z,shape=_vectors(x,z);raw=np.asarray(self.raw_height(x,z),float)
            d=shapely.distance(shapely.points(x,z),geom.boundary)
            w=_ease(d/.65)
            return (raw+w*np.clip(level-raw,-.40,.40)).reshape(shape)
        return fn
    def _rock_grade(self,geom,base,bulge):
        def fn(x,z):
            x,z,shape=_vectors(x,z)
            if geom.is_empty:return np.asarray(base(x,z)).reshape(shape)
            d=shapely.distance(shapely.points(x,z),geom.boundary)
            return (np.asarray(base(x,z)).ravel()+bulge*_ease(d/.65)).reshape(shape)
        return fn

    def height(self,x,z,original):
        x,z,shape=_vectors(x,z)
        result=np.broadcast_to(np.asarray(original,float),shape).copy().ravel()
        if self.coverage.is_empty:return result.reshape(shape)
        pts=shapely.points(x,z);inside=shapely.covers(self.coverage.buffer(1e-7),pts)
        for s in self.surfaces:
            hit=inside & shapely.covers(s['geom'].buffer(1e-7),pts)
            if hit.any():result[hit]=np.asarray(s['height_fn'](x[hit],z[hit])).ravel()
        return result.reshape(shape)

    def _structures(self):
        # Low bed edge ONLY at the observed NE gable; no inferred M31 wall.
        for n,(a0,a1) in enumerate(((13.15,14.40),(15.65,16.30))):
            line=LineString([self.xz(a0,7.42),self.xz(a1,7.42)]).difference(self.forbidden.buffer(.16)).intersection(self._work)
            for j,q in enumerate(_parts(line,'LineString')):
                if q.length < .15:continue
                self.walls.append(dict(id=f'm29_low_bed_edge_{n}_{j}',kind='rough_stone_bed_edge',a=list(q.coords[0]),b=list(q.coords[-1]),
                                       top_y=self.front_raw-self.offset,bottom_y=self.front_raw-.55-self.offset,width_m=.28,
                                       nominal_height_m=.55,collision=True,estimated=True))
        for n,ab in enumerate([[(1.8,-8.5),(9.8,-8.8),(11.4,-8.1)],[(12.7,-7.5),(17.5,-7.4),(19.05,-5.9)]]):
            line=LineString([self.xz(a,b) for a,b in ab]).intersection(self._garden.buffer(-.10)).difference(self.forbidden.buffer(.16))
            for j,q in enumerate(_parts(line,'LineString')):
                if q.length < .4:continue
                pts=shapely.get_coordinates(q.segmentize(.7));h=self.height(pts[:,0],pts[:,1],self.raw_height(pts[:,0],pts[:,1]))
                self.fences.append(dict(id=f'm29_vine_fence_{n}_{j}',kind='vine_timber_fence',points=[[float(x),float(y-self.offset),float(z)] for (x,z),y in zip(pts,h)],
                                        height_m=1.20,collision=True,estimated=True))
        ramp=next((s for s in self.surfaces if s['id']=='m29_gate_steps'),None)
        if ramp is not None:
            treads=[]
            for i in range(3):
                b0=8.78-i*.4;b1=b0-.4
                g=self.poly([(14.40,b1),(15.65,b1),(15.65,b0),(14.40,b0)]).intersection(ramp['geom'])
                if not g.is_empty:treads.append(dict(index=i,contours=_contours(g),top_y=self.step_low_raw+(i+1)*self.step_rise_m-self.offset,collision=False))
            self.steps.append(dict(id='m29_three_garden_steps',count=3,width_m=1.25,tread_m=.4,riser_m=self.step_rise_m,
                                   treads=treads,collision_only_ramp='m29_gate_steps',estimated=True))
        hinge=self.xz(14.40,7.42);end=self.xz(15.65,7.42)
        if self._allowed.buffer(.02).covers(LineString([hinge,end])):
            self.fences.append(dict(id='m29_open_timber_gate',kind='open_gate',hinge_xz=hinge.tolist(),latch_xz=end.tolist(),
                                    base_y=self.front_raw-self.offset,height_m=1.05,opening_width_m=1.25,open_angle_deg=90.,
                                    collision=True,estimated=True))

    def planting(self,height,offset):
        if not self._active:return [],[]
        trees,shrubs=[],[]
        # Dense, irregular low garden planting; species and exact positions estimated.
        rng=np.random.default_rng(2931)
        grass=unary_union([s['geom'] for s in self.surfaces if s['kind']=='grass'])
        for a,b,scale,variant in [(7.,-7.35,.60,1),(13.,-6.9,.49,0)]:
            q=self.xz(a,b)
            if grass.buffer(-.3).contains(Point(q)):
                y=float(np.asarray(height([q[0]],[q[1]])).ravel()[0])-offset
                trees.append([float(q[0]),y,float(q[1]),scale,variant,1.2+a])
        for a in np.arange(1.4,19.0,1.05):
            for b in np.arange(-8.7,-4.3,.95):
                q=self.xz(a+rng.uniform(-.18,.18),b+rng.uniform(-.16,.16))
                if not grass.buffer(-.23).contains(Point(q)):continue
                if any(math.hypot(q[0]-t[0],q[1]-t[2])<.85 for t in trees):continue
                y=float(np.asarray(height([q[0]],[q[1]])).ravel()[0])-offset
                shrubs.append([float(q[0]),y,float(q[1]),float(rng.uniform(.19,.28)),float(rng.uniform(.10,.17)),int(rng.integers(0,3)),float(rng.uniform(0,6.28))])
        for a,b in [(12.9,6.6),(14.2,6.6),(16.6,6.6)]:
            q=self.xz(a,b)
            if grass.buffer(-.18).contains(Point(q)):
                y=float(np.asarray(height([q[0]],[q[1]])).ravel()[0])-offset
                shrubs.append([float(q[0]),y,float(q[1]),.20,.13,2,float(a)])
        return trees,shrubs

    def metadata(self):
        if not self._active:return dict(active=False,reason='M29 building missing or no allowed ground in work',surfaces=[],walk_paths=[],ground_checks={})
        checks=[];paths=[];walk_paths=[]
        for s in self.surfaces:
            if s.get('collision_only'):continue
            q=s['geom'].representative_point();y=float(np.asarray(s['height_fn']([q.x],[q.y])).ravel()[0])-self.offset
            checks.append(dict(id=s['id'],position=[q.x,y,q.y],tolerance_m=.15))
        for route in self._routes:
            line=LineString([self.xz(a,b) for a,b in route['ab']]);q=shapely.get_coordinates(line.segmentize(.45))
            h=self.height(q[:,0],q[:,1],self.connection_height(q[:,0],q[:,1]))-self.offset
            xyz=[[float(x),float(y),float(z)] for (x,z),y in zip(q,h)]
            paths.append(dict(id=route['id'],points=xyz,speed_m_s=2.2,tolerance_m=.2))
            walk_paths.append(dict(id=route['id'],points_xz=q.tolist(),expected_y=[float(y) for y in h],height_status='estimated finished surface, local Y'))
        blockers=[]
        a=self.xz(15.025,8.92);b=self.xz(15.025,6.42)
        for ident,p0,p1,blocked in [('m29_open_gate',a,b,False)]:
            q=np.asarray([p0,p1]);h=self.height(q[:,0],q[:,1],self.connection_height(q[:,0],q[:,1]))-self.offset
            blockers.append(dict(id=ident,**{'from':[float(p0[0]),float(h[0]),float(p0[1])],'to':[float(p1[0]),float(h[1]),float(p1[1])]},blocked=blocked))
        candidates=[]
        for fence in self.fences:
            if fence['kind']!='vine_timber_fence':continue
            for p0,p1 in zip(fence['points'],fence['points'][1:]):
                v=np.array([p1[0]-p0[0],p1[2]-p0[2]]);length=np.linalg.norm(v)
                if length<.2:continue
                centre=np.array([(p0[0]+p1[0])/2,(p0[2]+p1[2])/2]);normal=np.array([-v[1],v[0]])/length
                q=np.array([centre-normal*.65,centre+normal*.65])
                if not self._work.covers(LineString(q)) or self.forbidden.intersects(LineString(q)):continue
                h=self.height(q[:,0],q[:,1],self.raw_height(q[:,0],q[:,1]))-self.offset
                fence_y=(p0[1]+p1[1])/2
                score=abs(float(h.mean())-fence_y)+abs(float(h[0]-h[1]))
                candidates.append((score,fence['id'],q,h))
        if candidates:
            _,ident,q,h=min(candidates,key=lambda c:c[0])
            blockers.append(dict(id='m29_vine_fence_block',fence_id=ident,
                                 **{'from':[float(q[0,0]),float(h[0]),float(q[0,1])],'to':[float(q[1,0]),float(h[1]),float(q[1,1])]},blocked=True))
        return dict(active=True,building_id=self.HOUSE,source='reference/roten-m/OBSERVATIONER.md, root visual inspection 2026-10-30',
                    source_status='Observed surface character and garden features; all coordinates, exact extents, species, heights and dimensions estimated.',
                    height_units='Callbacks: finished raw m above sea level, lift=0. Structural *_y and check points: local Y=raw-offset.',
                    frame=dict(origin=self.ORIGIN.tolist(),u=self.U.tolist(),v=self.V.tolist()),offset_m=self.offset,
                    coverage_m2=self.coverage.area,courtyard_raw_m=self.courtyard_raw,
                    grading_note='Small garden cores clamp DTM changes to ±0.40 m and feather .65 m; entrances tie to the actual preserved walking surface within 4 m. No M31 wall.',
                    surfaces=[dict(id=s['id'],kind=s['kind'],contours=_contours(s['geom']),lift_m=0,render=s['render'],collision_only=s['collision_only'],estimated=True) for s in self.surfaces],
                    walls=self.walls,fences=self.fences,steps=self.steps,rocks=self.rocks,walk_paths=walk_paths,
                    ground_checks=dict(points=checks,paths=paths,blockers=blockers))

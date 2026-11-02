"""Estimated M25 entrance, connected to the existing Stalleliden landing.

API: M25Ground(city, stalliden, forbidden, work, raw_height, offset, spec=None).
stalliden is the existing StallidenGround object; its geometry/profiles are read
only. forbidden contains houses/water/bridges and unrelated urban owners, but
NOT the authored garden grass which this small entry is intended to replace.

All surface callbacks return FINISHED RAW height, lift0. coverage/domain do not
overlap the old stair coverage. Cut garden/terrain below coverage, then render
surfaces and COL; supports close technical ground volumes only. They are not
observations of new retaining walls. Door/canopy/floor are built by the house
author, who must use the same Frame and raw floor from the spec.
"""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union


def _parts(g, kind):
    if g.is_empty:
        return []
    if g.geom_type == kind:
        return [g]
    return [p for q in getattr(g, 'geoms', []) for p in _parts(q, kind)]


def _contours(g):
    return [dict(outer=[list(q) for q in p.exterior.coords[:-1]],
                 holes=[[list(q) for q in r.coords[:-1]] for r in p.interiors])
            for p in _parts(g, 'Polygon')]


def _ease(t):
    t = np.clip(t, 0., 1.)
    return t * t * (3. - 2. * t)


class M25Ground:
    HOUSE = 'w92332157'

    def __init__(self, city, stalliden, forbidden, work, raw_height, offset, spec=None):
        self.raw_height, self.offset, self.stalliden = raw_height, float(offset), stalliden
        self.surfaces, self.supports = [], []
        self.coverage = self.domain = Polygon()
        self.active = False
        self.spec = dict(floor_raw_m=33.10, door_ab=[3.7, -1.37],
                         origin_xz=None, axis_xz=None, landing_width_m=1.60,
                         landing_depth_m=1.05, neck_width_m=.68, path_width_m=.85)
        if spec:
            self.spec.update(spec)
        house = next((b for b in city['buildings'] if b['id'] == self.HOUSE), None)
        if house is None or not stalliden.active:
            return
        self.house = house
        self.origin = np.array(self.spec['origin_xz'] or house['centroid_xz'], float)
        self.axis = np.array(self.spec['axis_xz'] or house['major_axis_xz'], float)
        # Exactly modelkit.Frame: no hidden axis normalization/scaling.
        self.cross = np.array([self.axis[1], -self.axis[0]])
        self.out = -self.cross / np.linalg.norm(self.cross)
        self.floor = float(self.spec['floor_raw_m'])
        self.door_xz = self.xz(*self.spec['door_ab'])
        self.door_front_xz = self.door_xz + self.out * .55
        footprint = Polygon(house['footprint_xz']).buffer(0)
        houses = unary_union([Polygon(b['footprint_xz']) if b['id'] == self.HOUSE else
                              Polygon(b['footprint_xz']).union(Polygon(b.get('build_footprint_xz', b['footprint_xz'])))
                              for b in city['buildings']]).buffer(.045)
        self.forbidden = forbidden.union(houses)
        self.allowed = work.difference(self.forbidden).difference(stalliden.coverage)
        flights = stalliden.stairs
        before = next((f for f in flights if f['id'].endswith('_flight_3_0')), None)
        after = next((f for f in flights if f['id'].endswith('_flight_3_1')), None)
        if before is None or after is None:
            return
        a = np.array(before['points'][-1])
        b = np.array(after['points'][0])
        if abs(a[1] - b[1]) > .001:
            raise ValueError('M25 entry requires a shared flat Stalleliden landing')
        self.anchor = ((a + b) / 2)[[0, 2]]
        self.anchor_raw = float(a[1] + self.offset)
        main_u = (b - a)[[0, 2]]
        main_u /= np.linalg.norm(main_u)
        north = np.array([main_u[1], -main_u[0]])
        self.neck_end = self.anchor + north
        self.path_xz = [self.anchor.tolist(), self.neck_end.tolist(), [61., 91.],
                        [61.75, 89.75], self.door_front_xz.tolist()]
        self.path_line = LineString(self.path_xz)
        self.neck = LineString(self.path_xz[:2]).buffer(self.spec['neck_width_m']/2, cap_style=2)
        wide = LineString(self.path_xz[1:]).buffer(self.spec['path_width_m']/2, cap_style=1, join_style=1)
        # The wide cap must not attach beyond the short old flat landing.
        wide = wide.difference(stalliden.coverage.buffer(.04))
        self.path_geom = self.neck.union(wide).buffer(0)
        da, db = self.spec['door_ab']; hw = self.spec['landing_width_m']/2
        depth = self.spec['landing_depth_m']
        self.landing = Polygon([self.xz(da-hw,db), self.xz(da+hw,db),
                                self.xz(da+hw,db-depth), self.xz(da-hw,db-depth)])
        self._primary = [('m25_door_landing', 'paving', self.landing, self._landing_height),
                         ('m25_entrance_walk', 'paving', self.path_geom, self._path_height)]
        # The uphill collar is deliberately small. It lowers only high ground;
        # west/downhill foundation ground is kept. .65 m clears the facade, then
        # .8 m returns smoothly to the old raw DTM rather than inventing a plot.
        ring = footprint.buffer(1.45, join_style=2).union(self.path_geom.buffer(2.4)).union(self.landing.buffer(2.4)).difference(footprint)
        minx, minz, maxx, maxz = ring.bounds
        high_cells = []
        for x in np.arange(math.floor(minx/.35)*.35, maxx, .35):
            for z in np.arange(math.floor(minz/.35)*.35, maxz, .35):
                cell = box(x,z,x+.35,z+.35)
                if cell.intersects(ring) and float(raw_height(x+.175,z+.175)) > self.floor:
                    high_cells.append(cell)
        self.collar = ring.intersection(unary_union(high_cells)).buffer(0)
        self.footprint = footprint
        proposed = self._primary + [('m25_uphill_ground_collar', 'grass', self.collar, self._collar_height)]
        used = Polygon()
        for ident, kind, geom, fn in proposed:
            geom = geom.intersection(self.allowed).difference(used).buffer(0)
            if geom.is_empty or geom.area < 1e-5:
                continue
            self.surfaces.append(dict(id=ident,kind=kind,geom=geom,height_fn=fn,
                                      lift_m=0.,render=True,collision_only=False))
            used = used.union(geom)
        self.coverage = self.domain = used.buffer(0)
        self.active = not self.coverage.is_empty
        self._make_supports()

    def xz(self, a, b):
        return self.origin + self.axis*a + self.cross*b

    def _landing_height(self, x, z):
        return np.full(np.broadcast_arrays(np.atleast_1d(x),np.atleast_1d(z))[0].shape,self.floor)

    def _path_height(self, x, z):
        x,z = np.broadcast_arrays(np.atleast_1d(x),np.atleast_1d(z))
        s = shapely.line_locate_point(self.path_line,shapely.points(x,z))
        t = _ease((s-1.1)/max(.1,self.path_line.length-1.1-1.3))
        return self.anchor_raw + (self.floor-self.anchor_raw)*t

    def _collar_height(self, x, z):
        x,z = np.broadcast_arrays(np.atleast_1d(x),np.atleast_1d(z))
        raw = np.asarray(self.raw_height(x,z),float)
        points = shapely.points(x,z)
        distance = shapely.distance(points,self.footprint)
        weight = 1-_ease((distance-.65)/.8)
        result = raw + (np.minimum(raw,self.floor-.15)-raw)*weight
        # A narrow path cut directly into coarse uphill DTM became a steep
        # grass trench in the native review. Give it a small flat shoulder and
        # 1.85 m smooth return to old terrain; never raise downhill ground.
        for ident,kind,geom,fn in self._primary:
            d = shapely.distance(points,geom)
            near = d < 2.4
            if np.any(near):
                q=shapely.get_point(shapely.shortest_line(points[near],geom),-1)
                target=fn(shapely.get_x(q),shapely.get_y(q))
                w=1-_ease((d[near]-.55)/1.85)
                graded=raw[near]+(np.minimum(raw[near],target)-raw[near])*w
                result[near]=np.minimum(result[near],graded)
        # Meet the entry surfaces exactly, including the short landing neck.
        for ident,kind,geom,fn in self._primary:
            geom = geom.intersection(self.allowed)
            if geom.is_empty:
                continue
            d = shapely.distance(points,geom)
            near = d < .4
            if np.any(near):
                q=shapely.get_point(shapely.shortest_line(points[near],geom),-1)
                target=fn(shapely.get_x(q),shapely.get_y(q))
                w=1-_ease(d[near]/.4)
                result[near] += (target-result[near])*w
        return result

    def height(self, x, z, original):
        x,z=np.broadcast_arrays(np.atleast_1d(np.asarray(x,float)),np.atleast_1d(np.asarray(z,float)))
        result=np.broadcast_to(np.asarray(original,float),x.shape).copy()
        used=np.zeros(x.shape,bool);points=shapely.points(x,z)
        for surface in self.surfaces:
            hit=(~used)&shapely.covers(surface['geom'].buffer(1e-7),points)
            if hit.any():
                result[hit]=surface['height_fn'](x[hit],z[hit]);used[hit]=True
        return result

    def _finished(self, x, z):
        raw=self.raw_height(x,z)
        old=self.stalliden.height(x,z,raw)
        return self.height(x,z,old)

    def _make_supports(self):
        for p in _parts(self.coverage,'Polygon'):
            for ring in [p.exterior]+list(p.interiors):
                q=np.asarray(ring.segmentize(.3).coords)
                raw=np.asarray(self.raw_height(q[:,0],q[:,1]))
                top=self.height(q[:,0],q[:,1],raw)-self.offset
                bottom=np.minimum(raw-self.offset-.25,top-.2)
                for i in range(len(q)-1):
                    self.supports.append(dict(a=q[i].tolist(),b=q[i+1].tolist(),top_a_y=float(top[i]),top_b_y=float(top[i+1]),
                        bottom_a_y=float(bottom[i]),bottom_b_y=float(bottom[i+1]),kind='technical_closed_ground',not_observed_wall=True))

    def metadata(self):
        if not self.active:
            return dict(active=False,ground_checks={})
        q=shapely.get_coordinates(self.path_line.segmentize(.2))
        h=self._finished(q[:,0],q[:,1])-self.offset
        xyz=[[float(x),float(y),float(z)] for (x,z),y in zip(q,h)]
        points=[dict(id='m25_'+name,position=[float(p[0]),float(self._finished([p[0]],[p[1]])[0]-self.offset),float(p[1])],tolerance_m=.12)
                for name,p in [('stair_join',self.anchor),('neck',self.neck_end),('door_front',self.door_front_xz)]]
        door_inside=self.door_xz-self.out*.35
        b=np.array(self.path_xz[2]);v=np.array(self.path_xz[3])-b;v/=np.linalg.norm(v)
        openq=np.array([b-v*.3,b+v*.3]);openh=self._finished(openq[:,0],openq[:,1])-self.offset
        return dict(active=True,source='reference/stalleliden-hus/; M25 observed entrance/ramp motif, exact layout and grading estimated',
            height_units='finished raw m/lift0; structural/check Y is raw-offset',floor_raw_m=self.floor,
            door_xz=self.door_xz.tolist(),door_front_xz=self.door_front_xz.tolist(),outward_xz=self.out.tolist(),
            anchor_xz=self.anchor.tolist(),anchor_raw_m=self.anchor_raw,coverage_m2=self.coverage.area,
            path_xz=self.path_xz,neck_width_m=self.spec['neck_width_m'],path_width_m=self.spec['path_width_m'],
            observed='entrance/canopy and separate smooth approach in reviewed photo; root owns visual interpretation',
            estimated='all metric coordinates, floor, porch depth, route and local uphill grading (0.55 m shoulder + 1.85 m blend); no new surveyed retaining wall',
            surfaces=[dict(id=s['id'],kind=s['kind'],contours=_contours(s['geom']),lift_m=0.) for s in self.surfaces],
            supports=self.supports,
            ground_checks=dict(points=points,paths=[dict(id='m25_to_door',points=xyz,speed_m_s=1.8,tolerance_m=.16),
                                                   dict(id='m25_from_door',points=xyz[::-1],speed_m_s=1.8,tolerance_m=.16)],
                blockers=[dict(id='m25_closed_door',blocked=True,height_m=.8,**{'from':[float(self.door_front_xz[0]),self.floor-self.offset,float(self.door_front_xz[1])],
                             'to':[float(door_inside[0]),self.floor-self.offset,float(door_inside[1])]}),
                          dict(id='m25_entrance_walk_open',blocked=False,height_m=.8,**{'from':[float(openq[0,0]),float(openh[0]),float(openq[0,1])],
                             'to':[float(openq[1,0]),float(openh[1]),float(openq[1,1])]})]))

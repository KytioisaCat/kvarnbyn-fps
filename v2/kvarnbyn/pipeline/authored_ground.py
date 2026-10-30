"""Observed Torget hardscape, with explicitly estimated contours and grading.

The immutable source is city['authored_ground'] from the frozen Torget reference.
Existing asphalt and walking connections have priority. The unified stone
interior uses gentle planes, with four-metre transitions to fixed connections.
"""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union


def polygons(geom):
    if geom.is_empty: return []
    if geom.geom_type == 'Polygon': return [geom]
    return [p for g in getattr(geom, 'geoms', []) for p in polygons(g)]


class AuthoredGround:
    def __init__(self, source, forbidden, original_urban, work, fixed_asphalt):
        self.source = source or {}
        self.original_urban = original_urban
        self.records = []
        # The north-bank contour crosses legacy grades that need a separate site survey.
        # This pass accepts the observed connected forecourt and its three planting islands.
        self.deferred = []
        for spec in self.source.get('pavement_polygons', []):
            if spec['id'] != 'torget_connected_forecourt':
                self.deferred.append(spec['id'])
                continue
            geom = Polygon(spec['polygon_xz']).buffer(0).difference(forbidden).intersection(work)
            if not geom.is_empty:
                self.records.append(dict(spec=spec, geom=geom, plane=None))
        self.coverage = unary_union([r['geom'] for r in self.records])
        # The former narrow pavement bands are part of the unified forecourt,
        # not internal grade constraints. Some contain >0.5 m nearest-profile
        # discontinuities. Preserve asphalt and walking connections outside the
        # observed patch, while grading the whole connected stone interior.
        self.fixed_ground = fixed_asphalt.union(original_urban.difference(self.coverage.buffer(.02)))
        self.planters = []
        for spec in self.source.get('planter_polygons', []):
            geom = Polygon(spec['polygon_xz']).buffer(0).intersection(self.coverage)
            if not geom.is_empty:
                self.planters.append(dict(spec=spec, geom=geom))
        self.soil = unary_union([r['geom'] for r in self.planters])
        self.paving = self.coverage.difference(self.soil)

    def fit(self, base_height, connection_height=None):
        self.base_height = base_height
        self.connection_height = connection_height or base_height
        # Anchor to existing street profiles, not low DTM samples beside the canal.
        for record in self.records:
            q = np.vstack([np.asarray(p.exterior.segmentize(2).coords) for p in polygons(record['geom'])])
            h = base_height(q[:, 0], q[:, 1])
            a, b, c = np.linalg.lstsq(np.column_stack([q, np.ones(len(q))]), h, rcond=None)[0]
            slope = math.hypot(a, b)
            if slope > .06:
                a, b = a * .06 / slope, b * .06 / slope
            c = float(np.median(h - a * q[:, 0] - b * q[:, 1]))
            record['plane'] = np.array([a, b, c])

        # A nearest-boundary rule alone creates a Voronoi crease where two
        # connections have different heights. Fit a local plane from both sides.
        boundary = self.fixed_ground.boundary.intersection(self.coverage.buffer(4.1))
        self.anchors = shapely.get_coordinates(shapely.segmentize(boundary, .5))
        self.anchor_heights = self.connection_height(self.anchors[:,0], self.anchors[:,1]) if len(self.anchors) else np.array([])

    def height(self, x, z, original):
        result = original.copy()
        if self.coverage.is_empty: return result
        pts = shapely.points(x, z)
        # Keep the asphalt and external walking joins at their original heights.
        distance = shapely.distance(pts, self.fixed_ground)
        t = np.clip(distance / 4., 0, 1)
        t = t * t * (3 - 2 * t)
        extension = original.copy()
        near = (distance < 4.) & shapely.covers(self.coverage.buffer(1e-6), pts)
        if near.any():
            # Extend the *actual connection height* from its nearest boundary.
            # Querying the nearest road at the new point can instead select a
            # different uphill footpath and create a hump beside the asphalt.
            q = shapely.get_point(shapely.shortest_line(pts[near], self.fixed_ground), -1)
            extension[near] = self.connection_height(shapely.get_x(q), shapely.get_y(q))
            for index in np.flatnonzero(near):
                if distance[index] < .02 or len(self.anchors) < 3: continue
                dx = self.anchors[:,0] - x[index]
                dz = self.anchors[:,1] - z[index]
                d2 = dx*dx + dz*dz
                take = np.argsort(d2)[:40]
                if d2[take[0]] > 16: continue
                A = np.column_stack((dx[take], dz[take], np.ones(len(take))))
                w = 1 / (d2[take] + .04)
                centre = extension[index]
                fit = np.linalg.solve((A.T*w)@A + np.diag([.2,.2,.0001]), (A.T*w)@(self.anchor_heights[take]-centre))
                blend = min(1., distance[index] / .45)
                blend = blend*blend*(3-2*blend)
                extension[index] += fit[2] * blend
        for record in self.records:
            # Cell/polygon intersections can land a few ULP outside their own
            # boundary. Falling back to a street profile for just that vertex
            # creates steep triangle tips. This tolerance is sub-millimetre;
            # asphalt boundary points remain fixed through distance == 0.
            hit = shapely.covers(record['geom'].buffer(1e-6), pts)
            a, b, c = record['plane']
            plane = a * x[hit] + b * z[hit] + c
            result[hit] = extension[hit] * (1 - t[hit]) + plane * t[hit]
        return result

    def planting(self, height, offset):
        trees, shrubs = [], []
        for n, record in enumerate(self.planters):
            geom, spec = record['geom'], record['spec']
            p = Point(spec['tree_reference_xz'])
            if not geom.buffer(-.45).contains(p): p = geom.representative_point()
            y = float(height([p.x], [p.y])[0]) + .08 - offset
            trees.append([round(p.x, 3), round(y, 3), round(p.y, 3), .52, n % 3, n * 1.7])
            lo_x, lo_z, hi_x, hi_z = geom.bounds
            candidates = []
            for x in np.arange(lo_x + .6, hi_x, 1.35):
                for z in np.arange(lo_z + .6, hi_z, 1.35):
                    q = Point(x, z)
                    if geom.buffer(-.5).contains(q) and q.distance(p) > 1.05:
                        candidates.append((x, z))
            # Shared foliage assets flattened into low, open shrub groups.
            for i, (x, z) in enumerate(candidates[:8]):
                y = float(height([x], [z])[0]) + .08 - offset
                shrubs.append([round(x, 3), round(y, 3), round(z, 3), .18, .085, (i + n) % 3, i * 2.1])
        return trees, shrubs

    def metadata(self):
        def contours(geom):
            return [dict(outer=[list(q) for q in p.exterior.coords[:-1]],
                         holes=[[list(q) for q in r.coords[:-1]] for r in p.interiors]) for p in polygons(geom)]
        return dict(source='city.authored_ground / frozen Torget reference, observed 2026-10-29; Street View May 2026',
                    source_status=self.source.get('status', ''), deferred_pavement_ids=self.deferred,
                    height_status='Estimated unified planes tied to a triangulated reference of existing urban profiles; smooth 4 m ties to unchanged asphalt and external walking connections. Interior former walkway bands are regraded. Not a survey.',
                    planting_status='Three observed young trees; exact contours, tree scale, shrub species/count/positions are design approximations.',
                    coverage_m2=round(self.coverage.area, 3), paving_m2=round(self.paving.area, 3), soil_m2=round(self.soil.area, 3),
                    pavement=[dict(id=r['spec']['id'], contours=contours(r['geom']), plane_raw=r['plane'].tolist(),
                                   confidence=r['spec'].get('confidence')) for r in self.records],
                    planters=[dict(id=r['spec']['id'], contours=contours(r['geom']), confidence=r['spec'].get('confidence')) for r in self.planters])


class SurfaceReference:
    """Barycentric existing-surface height at new connections, with a small local spatial index."""
    def __init__(self, tiles, fallback, offset, lift, bounds):
        self.fallback, self.offset, self.lift = fallback, offset, lift
        self.grid = {}
        if bounds is None: return
        lo_x, lo_z, hi_x, hi_z = bounds
        for bucket in tiles.values():
            for triangle in bucket:
                a, b, c = np.asarray(triangle, float)
                x0, x1 = min(a[0],b[0],c[0]), max(a[0],b[0],c[0])
                z0, z1 = min(a[2],b[2],c[2]), max(a[2],b[2],c[2])
                if x1 < lo_x-.1 or x0 > hi_x+.1 or z1 < lo_z-.1 or z0 > hi_z+.1: continue
                denominator = (b[2]-c[2])*(a[0]-c[0]) + (c[0]-b[0])*(a[2]-c[2])
                if abs(denominator) < 1e-10: continue
                record=(a,b,c,denominator)
                for ix in range(math.floor((x0-.002)/2), math.floor((x1+.002)/2)+1):
                    for iz in range(math.floor((z0-.002)/2), math.floor((z1+.002)/2)+1):
                        self.grid.setdefault((ix,iz),[]).append(record)

    def height(self, x, z):
        x,z=np.asarray(x,float),np.asarray(z,float)
        result=self.fallback(x,z)
        for i,(px,pz) in enumerate(zip(x,z)):
            for a,b,c,d in self.grid.get((math.floor(px/2),math.floor(pz/2)),[]):
                u=((b[2]-c[2])*(px-c[0])+(c[0]-b[0])*(pz-c[2]))/d
                v=((c[2]-a[2])*(px-c[0])+(a[0]-c[0])*(pz-c[2]))/d
                if min(u,v,1-u-v) >= -.002:
                    result[i]=u*a[1]+v*b[1]+(1-u-v)*c[1]+self.offset-self.lift
                    break
        return result

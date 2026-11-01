"""Estimated green verges and a short observed wall/plank motif by Stalleliden.

The 2017 reference supports a rough-stone wall with grey vertical boards on the
northern high plot. Its exact position, length and all planting are estimates.
No wall is invented at M31. Ground is finished raw metres, lift0.
"""
import math
import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union


class StallidenGarden:
    def __init__(self, city, stalliden, forbidden, raw_height, offset):
        self.raw_height=raw_height;self.offset=offset;self.walls=[];self.fences=[];self.surfaces=[]
        self.houses=unary_union([Polygon(b['footprint_xz']).union(Polygon(b.get('build_footprint_xz',b['footprint_xz']))) for b in city['buildings']])
        self.route=stalliden.lines[stalliden.MAIN]
        # x east/z south: negative offset is the physical northern plot here.
        self.wall_line=LineString([[36.91,80.91],[42.71,79.38]])
        a,b=list(self.wall_line.coords);raw=np.asarray(raw_height([a[0],b[0]],[a[1],b[1]]))
        top=raw-offset+1.0
        self.walls=[dict(a=list(a),b=list(b),bottom_a_y=float(raw[0]-offset-.25),bottom_b_y=float(raw[1]-offset-.25),
                         top_a_y=float(top[0]),top_b_y=float(top[1]),status='observed motif; placement and dimensions estimated')]
        self.fences=[dict(a=list(a),b=list(b),base_a_y=float(top[0]),base_b_y=float(top[1]),height_m=1.15,status='estimated grey vertical plank')]
        # The wall is north of the path: keep its grass on the northern side.
        dx,dz=b[0]-a[0],b[1]-a[1];L=math.hypot(dx,dz);n=np.array([dz/L,-dx/L])
        behind=Polygon([a,b,(b[0]+n[0]*2,b[1]+n[1]*2),(a[0]+n[0]*2,a[1]+n[1]*2)])
        self.raised=behind.difference(forbidden.buffer(.04))
        verges=self.route.buffer(3.8,join_style=1).difference(self.route.buffer(1.1,join_style=1)).intersection(box(23,74,88,111))
        self.coverage=verges.union(self.raised).difference(forbidden.buffer(.04)).buffer(0)
        # The raised plot boundary must be an explicit triangle constraint.
        # One union lets triangles bridge the wall's two different floor levels.
        self.surfaces=[dict(id='stalliden_green_verges',kind='grass',geom=self.coverage.difference(self.raised),height_fn=self.raw_height,lift_m=0.,collision_only=False),
                       dict(id='stalliden_raised_plot',kind='grass',geom=self.raised,height_fn=self._height,lift_m=0.,collision_only=False)]
        rng=np.random.default_rng(20261101);minx,minz,maxx,maxz=self.coverage.bounds
        candidates=[]
        for x,z in rng.uniform([minx,minz],[maxx,maxz],(6000,2)):
            p=Point(x,z)
            if self.coverage.buffer(-.15).covers(p):candidates.append((float(x),float(z)))
        self.tree_xz=[];self.shrub_xz=[]
        for q in candidates:
            if Point(q).distance(self.houses)<1.0 or any(math.dist(q,t)<7.0 for t in self.tree_xz):continue
            self.tree_xz.append(q)
            if len(self.tree_xz)==5:break
        for q in candidates:
            if Point(q).distance(self.houses)<.3 or any(math.dist(q,t)<1.0 for t in self.tree_xz) or any(math.dist(q,t)<.85 for t in self.shrub_xz):continue
            self.shrub_xz.append(q)
            if len(self.shrub_xz)==42:break

    def _height(self,x,z):
        x,z=np.broadcast_arrays(np.atleast_1d(np.asarray(x,float)),np.atleast_1d(np.asarray(z,float)))
        old=np.asarray(self.raw_height(x,z),float).copy();p=shapely.points(x,z)
        inside=shapely.covers(self.raised.buffer(1e-7),p)
        if inside.any():
            a,b=np.array(self.wall_line.coords);v=b-a
            t=np.clip(((x-a[0])*v[0]+(z-a[1])*v[1])/np.dot(v,v),0,1)
            aa,bb=self.walls[0]['top_a_y']+self.offset,self.walls[0]['top_b_y']+self.offset
            target=aa+t*(bb-aa);d=shapely.distance(p,self.wall_line)
            weight=np.clip(1-d/2.,0,1);weight=weight*weight*(3-2*weight)
            old=np.where(inside,old+(target-old)*weight,old)
        return old

    def height(self,x,z,original):
        return np.where(shapely.covers(self.coverage.buffer(1e-7),shapely.points(x,z)),self._height(x,z),original)

    def planting(self,height,offset):
        trees=[];shrubs=[]
        for i,(x,z) in enumerate(self.tree_xz):trees.append([x,float(np.asarray(height([x],[z])).ravel()[0])-offset,z,.66+(i%3)*.07,i%3,i*1.37])
        for i,(x,z) in enumerate(self.shrub_xz):shrubs.append([x,float(np.asarray(height([x],[z])).ravel()[0])-offset,z,.21+(i%4)*.025,.19+(i%3)*.03,i%3,i*2.17])
        return trees,shrubs

    def metadata(self):
        supports=[]
        for p in shapely.get_parts(self.raised):
            if p.geom_type!='Polygon':continue
            for ring in [p.exterior]+list(p.interiors):
                q=np.asarray(ring.segmentize(.3).coords);top=self._height(q[:,0],q[:,1])-self.offset
                bottom=np.minimum(self.raw_height(q[:,0],q[:,1])-self.offset-.2,top-.2)
                for i in range(len(q)-1):
                    supports.append(dict(a=q[i].tolist(),b=q[i+1].tolist(),top_a_y=float(top[i]),top_b_y=float(top[i+1]),bottom_a_y=float(bottom[i]),bottom_b_y=float(bottom[i+1]),kind='technical_closed_ground'))
        return dict(source='reference/stalliden/OBSERVATIONER.md',coverage_m2=self.coverage.area,
                    observed=['rough-stone wall and grey vertical plank on north high plot','mature greenery by stairs'],
                    estimated=['wall position/length/heights','all plant positions and species proxies','green contour'],
                    walls=self.walls,fences=self.fences,supports=supports,trees=len(self.tree_xz),shrubs=len(self.shrub_xz))

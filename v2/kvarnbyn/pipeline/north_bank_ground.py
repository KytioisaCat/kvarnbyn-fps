"""Estimated northern-bank hardscape from reviewed May2026 imagery.

OSM34930250 already says asphalt; generic path generation drew dirt. Root owns
source observations and integration. All dimensions/grades are estimates. No
rail is authored: the intake/canal alignment needs a separate reconstruction.
road_height/end_height return FINISHED RAW metres (old lifts included); new
surfaces use lift0. forbidden includes old paving, asphalt, water and authors.
"""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union, substring


def _ease(t):
    t=np.clip(t,0.,1.)
    return t*t*(3.-2.*t)


def _parts(g):
    if g.is_empty:return []
    if g.geom_type=='Polygon':return [g]
    return [p for q in getattr(g,'geoms',[]) for p in _parts(q)]


def _contours(g):
    return [dict(outer=[list(q) for q in p.exterior.coords[:-1]],
                 holes=[[list(q) for q in r.coords[:-1]] for r in p.interiors]) for p in _parts(g)]


class NorthBankGround:
    WAY='w34930250'
    MAIN_ROADS=('w223301747','w268588415')

    def __init__(self,city,forbidden,work,raw_height,offset,road_height,end_height,spec=None,sidewalk_geom=None,sidewalk_height=None):
        self.raw_height=raw_height;self.offset=float(offset)
        self.road_reference=road_height;self.end_reference=end_height
        self.sidewalk_geom=sidewalk_geom
        self.sidewalk_reference=sidewalk_height
        self.spec=dict(bike_width_m=2.8,walk_width_m=1.2,separator_width_m=.9,
                       endpoint_blend_m=6.,old_path_half_width_m=.9,road_drop_m=.05,
                       start_xz=[-16.992,18.691],end_xz=[55.,-17.],
                       apron_road_buffer_m=None,sidewalk_outer_offset_m=5.1,
                       apron_sidewalk_blend_m=1.8)
        if spec:self.spec.update(spec)
        self.surfaces=[];self.supports=[];self.rails=[]
        self.coverage=self.domain=Polygon();self.active=False;self.profile_id=self.WAY
        source=next((r for r in city['roads'] if r['id']==self.WAY),None)
        roads=[LineString(r['line_xz']) for r in city['roads'] if r['id'] in self.MAIN_ROADS]
        if source is None or not roads:return
        self.source_line=LineString(source['line_xz']);self.road_line=unary_union(roads)
        if self.spec.get('route_xz'):
            self.path_line=LineString(self.spec['route_xz'])
        else:
            self.start_s=self.source_line.project(Point(self.spec['start_xz']))
            self.end_s=self.source_line.project(Point(self.spec['end_xz']))
            if self.start_s>=self.end_s:raise ValueError('NorthBank start must precede end on OSM axis')
            self.path_line=substring(self.source_line,self.start_s,self.end_s)
        self.length=self.path_line.length
        if self.length<10:raise ValueError('NorthBank route too short for safe endpoint ties')
        self.blend=min(float(self.spec['endpoint_blend_m']),self.length/3)
        samples=np.linspace(0,self.length,max(2,math.ceil(self.length/.35)+1))
        self.sample_s=samples;self.sample_xz=self._xy(samples);self.sample_n=self._normals(samples)
        self.bike_half=float(self.spec['bike_width_m'])/2
        self.walk_width=float(self.spec['walk_width_m']);self.separator_width=float(self.spec['separator_width_m'])
        side=max(self.bike_half+self.walk_width,self.bike_half+self.separator_width)
        end_scale=min(1.,float(self.spec['old_path_half_width_m'])/side)
        taper=end_scale+(1-end_scale)*_ease(np.minimum(samples,self.length-samples)/self.blend)
        source_spec=next((p for p in city.get('authored_ground',{}).get('pavement_polygons',[])
                          if p['id']=='river_north_bank_hardscape'),None)
        scope=Polygon(source_spec['polygon_xz']).buffer(0) if source_spec else work
        self.allowed=scope.intersection(work).difference(forbidden).buffer(0)
        proposed=[('north_bank_gc_asphalt','asphalt',self._ribbon(-self.bike_half,self.bike_half,taper),self._grade),
                  ('north_bank_river_side_setts','paving',self._ribbon(self.bike_half,self.bike_half+self.walk_width,taper),self._grade),
                  ('north_bank_road_separator','paving',self._ribbon(-self.bike_half-self.separator_width,-self.bike_half,taper),self._grade)]
        used=Polygon()
        for ident,kind,geom,fn in proposed:
            geom=geom.intersection(self.allowed).difference(used).buffer(0)
            if geom.is_empty:continue
            self.surfaces.append(dict(id=ident,kind=kind,geom=geom,height_fn=fn,lift_m=0.,render=True,collision_only=False))
            used=used.union(geom)
        if self.spec.get('apron_road_buffer_m'):
            frame=self.path_line.buffer(30.,cap_style=2,join_style=2)
            apron=scope.intersection(frame).intersection(self.road_line.buffer(float(self.spec['apron_road_buffer_m']),cap_style=2))
            apron=apron.intersection(self.allowed).difference(used).buffer(0)
            if not apron.is_empty:
                self.surfaces.append(dict(id='north_bank_roadside_apron',kind='paving',geom=apron,
                                         height_fn=self._apron_height,lift_m=0.,render=True,collision_only=False))
                used=used.union(apron)
        self.coverage=self.domain=used.buffer(0);self.active=not used.is_empty
        if not self.active:return
        for offset in (0.,self.bike_half+self.walk_width/2):
            pts=self._route_points(offset,step=.3)
            if not bool(np.all(shapely.covers(self.coverage.buffer(.002),shapely.points(pts[:,0],pts[:,1])))):
                raise ValueError('NorthBank corridor clipped by protected owner; shorten/reposition route')
        self._make_supports()
        # A tiny visible/colliding overlap joins separately rounded mesh caps. The cut
        # domain stays unchanged; other old/new faces keep their own owners. The seam sits2mm higher.
        # Native QA found an exact endpoint ray could otherwise hit neither.
        for end in (0.,self.length):
            centre=self._xy([end])[0];normal=self._normals([end])[0]
            cap=LineString([centre-normal*(self.bike_half+self.separator_width)*end_scale,
                            centre+normal*(self.bike_half+self.walk_width)*end_scale]).buffer(.02,cap_style=2)
            cap=cap.intersection(work).difference(forbidden).buffer(0)
            if not cap.is_empty:
                self.surfaces.append(dict(id='north_bank_cap_seam_'+str(int(end)),kind='asphalt',geom=cap,
                                         height_fn=lambda x,z:self._grade(x,z)+.002,lift_m=0.,render=True,collision_only=False))

    def _xy(self,s):
        return shapely.get_coordinates(shapely.line_interpolate_point(self.path_line,np.atleast_1d(s)))

    def _normals(self,s):
        s=np.atleast_1d(s)
        d=self._xy(np.minimum(s+.05,self.length))-self._xy(np.maximum(s-.05,0.))
        d/=np.maximum(1e-9,np.linalg.norm(d,axis=1))[:,None]
        return np.column_stack((-d[:,1],d[:,0]))

    def _ribbon(self,left,right,scale):
        a=self.sample_xz+self.sample_n*(left*np.asarray(scale))[:,None]
        b=self.sample_xz+self.sample_n*(right*np.asarray(scale))[:,None]
        return unary_union([Polygon([a[i],a[i+1],b[i+1],b[i]]).buffer(0) for i in range(len(a)-1)]).buffer(0)

    def _grade(self,x,z):
        x,z=np.broadcast_arrays(np.atleast_1d(x),np.atleast_1d(z))
        pts=shapely.points(x,z);s=shapely.line_locate_point(self.path_line,pts)
        q=shapely.get_point(shapely.shortest_line(pts,self.road_line),-1)
        target=np.asarray(self.road_reference(shapely.get_x(q),shapely.get_y(q)),float)-float(self.spec['road_drop_m'])
        old=np.asarray(self.end_reference(x,z),float)
        weight=_ease(np.minimum(s,self.length-s)/self.blend)
        return old+(target-old)*weight

    def _apron_height(self,x,z):
        x,z=np.broadcast_arrays(np.atleast_1d(x),np.atleast_1d(z));pts=shapely.points(x,z)
        q=shapely.get_point(shapely.shortest_line(pts,self.road_line),-1)
        qx,qz=shapely.get_x(q),shapely.get_y(q)
        dx,dz=x-qx,z-qz;distance=np.maximum(np.hypot(dx,dz),1e-9)
        if self.sidewalk_geom is not None and not self.sidewalk_geom.is_empty and self.sidewalk_reference is not None:
            # Use the actual old owner, rather than a guessed road-normal5.08m
            # point which can fall outside the sidewalk at the SW intersection.
            inside=self.sidewalk_geom.buffer(-.001)
            if inside.is_empty:inside=self.sidewalk_geom
            edge=shapely.get_point(shapely.shortest_line(pts,inside),-1)
            old=self.sidewalk_reference(shapely.get_x(edge),shapely.get_y(edge))
            d=shapely.distance(pts,self.sidewalk_geom)
            weight=1-_ease(d/float(self.spec['apron_sidewalk_blend_m']))
            base=self._grade(x,z)
            return base+(np.asarray(old)-base)*weight
        outer=float(self.spec['sidewalk_outer_offset_m'])
        old=self.end_reference(qx+dx/distance*(outer-.02),qz+dz/distance*(outer-.02))
        weight=1-_ease((distance-outer)/float(self.spec['apron_sidewalk_blend_m']))
        base=self._grade(x,z)
        return base+(np.asarray(old)-base)*weight

    def height(self,x,z,original):
        x,z=np.broadcast_arrays(np.atleast_1d(np.asarray(x,float)),np.atleast_1d(np.asarray(z,float)))
        result=np.broadcast_to(np.asarray(original,float),x.shape).copy();used=np.zeros(x.shape,bool)
        pts=shapely.points(x,z)
        for surface in self.surfaces:
            hit=(~used)&shapely.covers(surface['geom'].buffer(1e-7),pts)
            if np.any(hit):result[hit]=surface['height_fn'](x[hit],z[hit]);used[hit]=True
        return result

    def profile_height(self,x,z,original):
        return self.height(x,z,original)

    def _make_supports(self):
        for p in _parts(self.coverage):
            for ring in [p.exterior]+list(p.interiors):
                q=np.asarray(ring.segmentize(.35).coords);raw=np.asarray(self.raw_height(q[:,0],q[:,1]))
                top=self.height(q[:,0],q[:,1],raw)-self.offset;bottom=np.minimum(raw-self.offset-.25,top-.2)
                for i in range(len(q)-1):
                    self.supports.append(dict(a=q[i].tolist(),b=q[i+1].tolist(),top_a_y=float(top[i]),top_b_y=float(top[i+1]),
                        bottom_a_y=float(bottom[i]),bottom_b_y=float(bottom[i+1]),kind='technical_closed_ground',not_observed_wall=True))

    def _route_points(self,offset,step=.25):
        s=np.linspace(0,self.length,max(2,math.ceil(self.length/step)+1))
        blend=_ease(np.minimum(s,self.length-s)/self.blend)
        return self._xy(s)+self._normals(s)*(offset*blend)[:,None]

    def _xyz(self,q):
        h=self.height(q[:,0],q[:,1],self.end_reference(q[:,0],q[:,1]))-self.offset
        return [[float(x),float(y),float(z)] for (x,z),y in zip(q,h)]

    def metadata(self):
        if not self.active:return dict(active=False,ground_checks={})
        routes=[('bike',self._route_points(0.)),('walk',self._route_points(self.bike_half+self.walk_width/2))]
        paths=[];points=[]
        for kind,q in routes:
            xyz=self._xyz(q)
            paths.extend([dict(id='north_bank_'+kind+'_forward',points=xyz,speed_m_s=2.1,tolerance_m=.16),
                          dict(id='north_bank_'+kind+'_return',points=xyz[::-1],speed_m_s=2.1,tolerance_m=.16)])
            for i in (0,len(q)//2,len(q)-1):points.append(dict(id='north_bank_'+kind+'_'+str(i),position=xyz[i],tolerance_m=.12))
        s=np.array([self.length*.4]);centre=self._xy(s)[0];normal=self._normals(s)[0]
        cross=np.array([centre-normal*.45,centre+normal*(self.bike_half+self.walk_width/2)])
        q=self._route_points(0.);mid=len(q)//2;forward=q[[max(0,mid-2),min(len(q)-1,mid+2)]]
        cross_xyz=self._xyz(cross);forward_xyz=self._xyz(forward)
        blockers=[dict(id='north_bank_cross_lanes_open',blocked=False,height_m=.8,**{'from':cross_xyz[0],'to':cross_xyz[1]}),
                  dict(id='north_bank_cycle_strip_open',blocked=False,height_m=.8,**{'from':forward_xyz[0],'to':forward_xyz[1]})]
        if self.spec.get('apron_road_buffer_m'):
            for fraction in (.3,.7):
                cycle=self._xy(np.array([self.length*fraction]))[0]
                nearest=shapely.get_point(shapely.shortest_line(Point(cycle),self.road_line),-1)
                road=np.array([nearest.x,nearest.y]);v=cycle-road;v/=np.linalg.norm(v)
                crossing=np.array([road+v*5.,cycle]);xyz=self._xyz(crossing)
                blockers.append(dict(id='north_bank_old_sidewalk_to_cycle_'+str(fraction),blocked=False,height_m=.8,
                                     **{'from':xyz[0],'to':xyz[1]}))
        return dict(active=True,source='reference/nordbanken/; Maps May2026 + OSM34930250 asphalt; metrics estimated',
            profile_id=self.profile_id,height_units='finished RAW m/lift0; check/support Y=raw-offset',
            route_xz=[list(q) for q in self.path_line.coords],route_length_m=self.length,coverage_m2=self.coverage.area,
            bike_width_m=self.bike_half*2,walk_width_m=self.walk_width,separator_width_m=self.separator_width,
            endpoint_blend_m=self.blend,road_drop_m=float(self.spec['road_drop_m']),apron_road_buffer_m=self.spec.get('apron_road_buffer_m'),
            observed=['asphalt bike/shared strip','light stone strips beside cycling route'],
            estimated=['route alignment from old OSM','all widths/heights/curves','roadside apron contour','smooth endpoint merges'],
            deferred=['intake basin shape','actual canal/rail alignment','small brick utility volume','furniture/planting'],
            surfaces=[dict(id=s['id'],kind=s['kind'],contours=_contours(s['geom']),lift_m=0.) for s in self.surfaces],
            supports=self.supports,rails=[],cap_seam_collider_width_m=.04,ground_checks=dict(points=points,paths=paths,blockers=blockers))

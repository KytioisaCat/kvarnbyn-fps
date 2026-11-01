"""Connected Stalliden study: FINISHED raw heights, lift=0 everywhere.

API: StallidenGround(city, forbidden, work, raw_height, finished_height, offset).
finished_height must sample ORIGINAL rendered urban triangles, including lift.
forbidden = buildings/water/bridges + unrelated urban, NOT original_domain(city).

Remove replacement_domain from old paving/walkway/trail meshes; skip the two
original stair ways. Keep old urban outside that domain. New surfaces are
disjoint, height_fn is finished raw metres above sea level, lift_m=0. Flights
have invisible collision ramps in surfaces and explicit visible .stairs/treads.
Do not add old +.02 ramp lift or quantise them to an unrelated .16 m grid.
Cut terrain below coverage, including invisible ramps; supports close the edge.

Observed reference: 2017 Stalleliden photo, root inspected 2026-11-01, grey
stone/concrete short flights, walking/landing intervals and one simple rail.
Exact flight count, widths, positions and ALL metric heights are estimates.
No M31 wall and no modification to house footprints are produced here.
"""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union, substring, nearest_points


def _parts(g,kind):
    if g.is_empty:return []
    if g.geom_type==kind:return [g]
    return [p for q in getattr(g,'geoms',[]) for p in _parts(q,kind)]


def _contours(g):
    return [dict(outer=[list(q) for q in p.exterior.coords[:-1]],holes=[[list(q) for q in r.coords[:-1]] for r in p.interiors]) for p in _parts(g,'Polygon')]


def _vectors(x,z):
    x,z=np.broadcast_arrays(np.atleast_1d(np.asarray(x,float)),np.atleast_1d(np.asarray(z,float)))
    return x.ravel(),z.ravel(),x.shape


def _ease(t):
    t=np.clip(t,0.,1.);return t*t*(3.-2.*t)


class StallidenGround:
    MAIN='w461711525';WALK='w461711523';LOWER='w461711524';ROTEN='w330280688'
    WAY_IDS=(MAIN,WALK,LOWER,ROTEN)
    STREET='w63073062';PARALLEL='w1227769459'

    @classmethod
    def original_domain(cls,city):
        """Old bands to subtract from generic urban BEFORE constructing forbidden."""
        result=[];preserve=[]
        for r in city.get('roads',[]):
            if r.get('id') in (cls.PARALLEL,cls.STREET):
                line=LineString(r['line_xz']);w=float(r.get('width_m',2.))/2
                preserve.append(line.buffer(w,cap_style=1 if r['id']==cls.PARALLEL else 2,join_style=1 if r['id']==cls.PARALLEL else 2))
            if r.get('id') not in cls.WAY_IDS:continue
            line=LineString(r['line_xz'])
            if r['id']==cls.ROTEN:line=substring(line,max(0,line.length-4.),line.length)
            result.append(line.buffer(float(r.get('width_m',2.))/2,cap_style=1,join_style=2))
        # The old lower-stair cap overlaps the existing parallel path. Removing
        # that cap wholesale would punch a .175 m sliver in the preserved path
        # on the new direct connector route. Those unrelated floors always win.
        return unary_union(result).difference(unary_union(preserve))

    def __init__(self,city,forbidden,work,raw_height,finished_height,offset):
        self.city,self.raw_height,self.finished_height=city,raw_height,finished_height
        self.offset=float(offset);self.surfaces=[];self.stairs=[];self.rails=[];self.supports=[];self.walls=[]
        self.coverage=Polygon();self.profile_overrides={};self._profiles={};self._routes=[]
        self.roads={r['id']:r for r in city.get('roads',[])}
        self.active=all(w in self.roads for w in self.WAY_IDS+(self.STREET,self.PARALLEL))
        self.replacement_domain=self.original_domain(city).intersection(work)
        if not self.active:return
        houses=unary_union([Polygon(b['footprint_xz']).union(Polygon(b.get('build_footprint_xz',b['footprint_xz']))) for b in city['buildings']]).buffer(.045)
        self.forbidden=forbidden.union(houses)
        self.work=work;self._allowed=work.difference(self.forbidden)
        self.lines={w:LineString(self.roads[w]['line_xz']) for w in self.WAY_IDS}
        self.widths={self.MAIN:1.4,self.WALK:1.6,self.LOWER:1.4,self.ROTEN:2.0}
        # Three shared anchors come from existing finished urban, not raw DTM.
        self._upper=np.array(self.roads[self.MAIN]['line_xz'][-1],float)
        self._j2=np.array(self.roads[self.WALK]['line_xz'][-1],float)
        self._j3=np.array(self.roads[self.WALK]['line_xz'][0],float)
        self._bottom=np.array(self.roads[self.LOWER]['line_xz'][0],float)
        self.anchor_points=[self._upper,self._j2,self._j3,self._bottom]
        self.anchor_heights=[self._sample_finished(q) for q in self.anchor_points]
        upper,j2,j3,bottom=self.anchor_heights
        self._build_stair_profile(self.MAIN,j2,upper)
        self._build_stair_profile(self.LOWER,bottom,j3)
        # The 11 m walking link is a connected graded stone path, not claimed flat.
        line=self.lines[self.WALK];L=line.length
        self._profiles[self.WALK]=dict(line=line,s=np.array([0.,1.,L-1.,L]),h=np.array([j3,j3,j2,j2]),phases=[])
        self._proposals=[]
        for wid in (self.MAIN,self.LOWER):self._flight_surfaces(wid)
        self._add('stalliden_walking_link','paving',self.lines[self.WALK].buffer(self.widths[self.WALK]/2,cap_style=1,join_style=2),self._way_fn(self.WALK),30,way_id=self.WALK)
        # Only the last four metres of Roten M change; the M29 joins remain intact.
        rot=self.lines[self.ROTEN];tail=substring(rot,max(0,rot.length-4.),rot.length)
        self._add('stalliden_roten_landing','paving',tail.buffer(1.,cap_style=1,join_style=2),self._roten_height,20,way_id=self.ROTEN)
        self._make_connector()
        used=Polygon()
        for s in sorted(self._proposals,key=lambda q:-q['priority']):
            s['geom']=s['geom'].intersection(self._allowed).difference(used).buffer(0)
            if s['geom'].is_empty or s['geom'].area<1e-4:continue
            self.surfaces.append(s);used=used.union(s['geom'])
        self.coverage=used.buffer(0)
        if self.coverage.is_empty:self.active=False;return
        for wid in self.WAY_IDS:
            line=self.lines[wid];q=shapely.get_coordinates(line.segmentize(.3))
            h=self._way_fn(wid)(q[:,0],q[:,1])
            self.profile_overrides[wid]=dict(way_id=wid,width_m=self.widths[wid],finished=True,lift_m=0.,
                    points=[[float(x),float(y-self.offset),float(z)] for (x,z),y in zip(q,h)],
                    heights_raw_m=[float(y) for y in h],line_xz=q.tolist(),
                    preserve_before_s_m=max(0,line.length-4.) if wid==self.ROTEN else None)
        self._finalize_treads()
        self._make_supports()
        self._make_rails()
        down=self.roads[self.ROTEN]['line_xz']+list(reversed(self.roads[self.MAIN]['line_xz']))[1:]+list(reversed(self.roads[self.WALK]['line_xz']))[1:]+list(reversed(self.roads[self.LOWER]['line_xz']))[1:]+[self.connector_end.tolist()]
        self._routes=[dict(id='stalliden_down',xz=down),dict(id='stalliden_up',xz=list(reversed(down)))]

    def _sample_finished(self,q):return float(np.asarray(self.finished_height([q[0]],[q[1]])).ravel()[0])

    def _add(self,ident,kind,g,fn,priority,**kwargs):
        s=dict(id=ident,kind=kind,geom=g,height_fn=fn,priority=priority,lift_m=0.,render=True,collision_only=False,estimated=True)
        s.update(kwargs);self._proposals.append(s)

    def _build_stair_profile(self,wid,h0,h1):
        line=self.lines[wid];q=np.asarray(line.coords);ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))]
        heights=np.asarray(self.raw_height(q[:,0],q[:,1]),float);heights[0]=h0;heights[-1]=h1
        # Ground controls are interpreted; monotonic correction prevents DTM noise
        # from inventing reverse steps. End anchors stay exact.
        heights=np.clip(np.maximum.accumulate(heights),h0,h1);heights[0]=h0;heights[-1]=h1
        half=np.full(len(q),.8);half[[0,-1]]=.55
        ss=[0.];hh=[h0];flights=[]
        def knot(s,h):
            if s>ss[-1]+1e-8:ss.append(float(s));hh.append(float(h))
            else:hh[-1]=float(h)
        for j in range(len(q)-1):
            a,b=ds[j]+half[j],ds[j+1]-half[j+1]
            if b<=a:a,b=ds[j],ds[j+1]
            knot(a,heights[j])
            rise=float(heights[j+1]-heights[j]);n=max(1,int(math.ceil(rise/.165)))
            count=max(1,int(math.ceil(n/10)))
            counts=[n//count+(k<n%count) for k in range(count)]
            run=min(n*.34,(b-a)*.82);tread=run/n
            gap=max(0.,(b-a-run)/(count+1));cursor=a;level=float(heights[j])
            for k,num in enumerate(counts):
                cursor+=gap;knot(cursor,level)
                start=cursor;end=cursor+num*tread;top=level+rise*num/n
                knot(end,top)
                flights.append(dict(id=f'{wid}_flight_{j}_{k}',way_id=wid,start_s_m=start,end_s_m=end,
                    low_raw_m=level,high_raw_m=top,count=int(num),riser_m=rise/n,tread_m=tread,width_m=self.widths[wid],estimated=True))
                cursor=end;level=top
            knot(b,heights[j+1]);knot(ds[j+1],heights[j+1])
        self._profiles[wid]=dict(line=line,s=np.asarray(ss),h=np.asarray(hh),phases=flights)

    def _way_fn(self,wid):
        if wid==self.ROTEN:return self._roten_height
        def fn(x,z):
            x,z,shape=_vectors(x,z);p=self._profiles[wid]
            s=shapely.line_locate_point(p['line'],shapely.points(x,z))
            return np.interp(s,p['s'],p['h']).reshape(shape)
        return fn

    def road_height(self,wid,x,z):return self._way_fn(wid)(x,z)

    def _roten_height(self,x,z):
        x,z,shape=_vectors(x,z);line=self.lines[self.ROTEN]
        s=shapely.line_locate_point(line,shapely.points(x,z));t=_ease((s-max(0,line.length-4.))/4.)
        original=np.asarray(self.finished_height(x,z),float)
        return (original*(1-t)+self.anchor_heights[0]*t).reshape(shape)

    def _flight_surfaces(self,wid):
        profile=self._profiles[wid];line=profile['line'];width=self.widths[wid];pieces=[]
        for f in profile['phases']:
            piece=substring(line,f['start_s_m'],f['end_s_m']);g=piece.buffer(width/2,cap_style=2,join_style=2)
            pieces.append(g)
            self._add(f['id'],'paving',g,self._way_fn(wid),60,way_id=wid,render=False,collision_only=True,role='stair_ramp',riser_m=f['riser_m'])
        land=line.buffer(width/2,cap_style=1,join_style=2).difference(unary_union(pieces))
        self._add(wid+'_landings','paving',land,self._way_fn(wid),40,way_id=wid,role='estimated_landing_or_walk')

    def _make_connector(self):
        street=self.roads[self.STREET];street_line=LineString(street['line_xz'])
        _,end=nearest_points(Point(self._bottom),street_line);self.connector_end=np.array([end.x,end.y])
        self._connector=LineString([self._bottom,self.connector_end])
        # Existing parallel footpath and carriageway retain priority; only the gap
        # becomes a new small pedestrian connection. This is a topology estimate.
        self._parallel_band=LineString(self.roads[self.PARALLEL]['line_xz']).buffer(float(self.roads[self.PARALLEL]['width_m'])/2,cap_style=1,join_style=2)
        self._street_band=street_line.buffer(float(street['width_m'])/2,cap_style=2,join_style=2)
        preserve=self._parallel_band.union(self._street_band)
        gap=self._connector.buffer(.7,cap_style=2,join_style=2).difference(preserve)
        if gap.is_empty:return
        intervals=[]
        for piece in _parts(self._connector.intersection(gap),'LineString'):
            intervals.append((self._connector.project(Point(piece.coords[0])),self._connector.project(Point(piece.coords[-1]))))
        if not intervals:return
        s0=min(min(v) for v in intervals);s1=max(max(v) for v in intervals)
        p0=self._connector.interpolate(s0);p1=self._connector.interpolate(s1)
        self.connector_anchor=dict(s0=s0,s1=s1,h0=self._sample_finished((p0.x,p0.y)),h1=self._sample_finished((p1.x,p1.y)))
        self._add('stalliden_norra_pedestrian_link','paving',gap,self._connector_height,50,role='estimated_topological_connection')

    def _connector_height(self,x,z):
        x,z,shape=_vectors(x,z);pts=shapely.points(x,z)
        d0=shapely.distance(pts,self._parallel_band);d1=shapely.distance(pts,self._street_band)
        q0=shapely.get_point(shapely.shortest_line(pts,self._parallel_band),-1)
        q1=shapely.get_point(shapely.shortest_line(pts,self._street_band),-1)
        h0=np.asarray(self.finished_height(shapely.get_x(q0),shapely.get_y(q0)),float)
        h1=np.asarray(self.finished_height(shapely.get_x(q1),shapely.get_y(q1)),float)
        t=_ease(d0/np.maximum(d0+d1,1e-8))
        return (h0*(1-t)+h1*t).reshape(shape)

    def _at(self,x,z,fallback):
        x,z,shape=_vectors(x,z);r=np.asarray(fallback,float).reshape(shape).copy().ravel();pts=shapely.points(x,z)
        used=np.zeros(len(x),bool)
        for s in self.surfaces:
            hit=(~used)&shapely.covers(s['geom'].buffer(1e-7),pts)
            if hit.any():r[hit]=np.asarray(s['height_fn'](x[hit],z[hit])).ravel();used[hit]=True
        return r.reshape(shape)

    def height(self,x,z,original):
        x,z,shape=_vectors(x,z);original=np.broadcast_to(np.asarray(original,float),shape).copy()
        if self.coverage.is_empty:return original
        values=self._at(x,z,original).reshape(shape);mask=shapely.covers(self.coverage,shapely.points(x,z)).reshape(shape)
        return np.where(mask,values,original)

    def _finalize_treads(self):
        for wid in (self.MAIN,self.LOWER):
            line=self.lines[wid]
            for f in self._profiles[wid]['phases']:
                surface=next((s for s in self.surfaces if s['id']==f['id']),None)
                if surface is None:continue
                treads=[]
                for i in range(f['count']):
                    a=f['start_s_m']+i*f['tread_m'];b=a+f['tread_m']
                    g=substring(line,a,b).buffer(f['width_m']/2,cap_style=2).intersection(surface['geom'])
                    if g.is_empty:continue
                    q=shapely.get_coordinates(g);raw=np.asarray(self.raw_height(q[:,0],q[:,1]))
                    top=f['low_raw_m']+(i+1)*f['riser_m']-self.offset
                    treads.append(dict(index=i,contours=_contours(g),top_y=top,bottom_y=min(float(raw.min())-self.offset-.25,top-.22),collision=False))
                p0=line.interpolate(f['start_s_m']);p1=line.interpolate(f['end_s_m'])
                self.stairs.append(dict(**f,points=[[p0.x,f['low_raw_m']-self.offset,p0.y],[p1.x,f['high_raw_m']-self.offset,p1.y]],
                    treads=treads,contours=_contours(surface['geom']),collision_ramp_id=f['id']))

    def _make_supports(self):
        for p in _parts(self.coverage,'Polygon'):
            for ring in [p.exterior]+list(p.interiors):
                q=shapely.get_coordinates(ring.segmentize(.4));raw=np.asarray(self.raw_height(q[:,0],q[:,1]))
                top=self._at(q[:,0],q[:,1],raw).ravel()-self.offset
                bottom=np.minimum(raw-self.offset-.3,top-.2)
                for i in range(len(q)-1):
                    self.supports.append(dict(a=q[i].tolist(),b=q[i+1].tolist(),top_a_y=float(top[i]),top_b_y=float(top[i+1]),
                        bottom_a_y=float(bottom[i]),bottom_b_y=float(bottom[i+1]),kind='technical_closed_ground',not_observed_wall=True))

    def _make_rails(self):
        for wid in (self.MAIN,self.LOWER):
            line=self.lines[wid];width=self.widths[wid]
            # A true offset follows corners. Connecting displaced sample points
            # with long chords can cut .2 m into the centre walking corridor.
            rail=line.offset_curve(width/2-.06,quad_segs=8,join_style=1).difference(self.forbidden.buffer(.025)).intersection(self.work)
            for j,piece in enumerate(_parts(rail,'LineString')):
                if piece.length<.2:continue
                q=shapely.get_coordinates(piece.segmentize(.5));h=self.road_height(wid,q[:,0],q[:,1])-self.offset
                points=[[float(x),float(y),float(z)] for (x,z),y in zip(q,h)]
                self.rails.append(dict(id=f'{wid}_rail_{j}',way_id=wid,points=points,height_m=1.0,radius_m=.028,
                    collider_width_m=.07,collision=True,side_status='estimated one-sided placement, visual reference supports a simple metal rail'))

    def metadata(self):
        if not self.active:return dict(active=False,surfaces=[],ground_checks={})
        points=[]
        for wid in (self.MAIN,self.WALK,self.LOWER):
            line=self.lines[wid]
            for i,q in enumerate(self.roads[wid]['line_xz']):
                h=float(self.road_height(wid,[q[0]],[q[1]])[0])-self.offset
                points.append(dict(id=f'{wid}_node_{i}',position=[q[0],h,q[1]],tolerance_m=.15))
        paths=[];walk=[]
        for route in self._routes:
            line=LineString(route['xz']);q=shapely.get_coordinates(line.segmentize(.2));fallback=self.finished_height(q[:,0],q[:,1])
            h=self.height(q[:,0],q[:,1],fallback).ravel()-self.offset
            xyz=[[float(x),float(y),float(z)] for (x,z),y in zip(q,h)]
            paths.append(dict(id=route['id'],points=xyz,speed_m_s=2.2,tolerance_m=.18))
            walk.append(dict(id=route['id'],points_xz=q.tolist(),expected_y=h.tolist()))
        blockers=[]
        # A rail probe on the fall side must hit the real rail collider before
        # the ground support face. Prefer an outboard floor near ramp height.
        candidates=[]
        for f in self._profiles[self.MAIN]['phases']:
            line=self.lines[self.MAIN];s=(f['start_s_m']+f['end_s_m'])/2
            p=line.interpolate(s);a=line.interpolate(s-.1);b=line.interpolate(s+.1)
            v=np.array([b.x-a.x,b.y-a.y]);v/=max(np.linalg.norm(v),1e-9);n=np.array([-v[1],v[0]])
            q=np.array([[p.x,p.y]+n*.15,[p.x,p.y]+n*1.05])
            if self.forbidden.intersects(LineString(q)):continue
            top=float(self.road_height(self.MAIN,[p.x],[p.y])[0]);outside=float(self.raw_height([q[1,0]],[q[1,1]])[0])
            candidates.append((abs(top-outside),q,top,outside))
        if candidates:
            _,q,h0,h1=min(candidates,key=lambda q:q[0])
            blockers.append(dict(id='stalliden_metal_rail',blocked=True,height_m=.65,
                **{'from':[float(q[0,0]),h0-self.offset,float(q[0,1])],'to':[float(q[1,0]),h1-self.offset,float(q[1,1])]}))
        line=self.lines[self.WALK];q=np.array([line.interpolate(line.length/2-.5).coords[0],line.interpolate(line.length/2+.5).coords[0]])
        h=self.road_height(self.WALK,q[:,0],q[:,1])-self.offset
        blockers.append(dict(id='stalliden_walking_link_open',blocked=False,height_m=.8,
            **{'from':[float(q[0,0]),float(h[0]),float(q[0,1])],'to':[float(q[1,0]),float(h[1]),float(q[1,1])]}))
        return dict(active=True,source='Root inspected Stalleliden photograph, picturelives.wordpress.com, published 2017-06-26; geometry estimated from OSM/DTM 2026-11-01.',
            reference_url='https://picturelives.wordpress.com/wp-content/uploads/2017/06/p1020320.jpg?w=625',
            observed='grey stone/concrete steps in short flights, walking/landing sections, simple metal rail; material observation only',
            estimated='all metric heights, widths, flight counts/positions, rail placement and short topology connector. No M31 wall.',
            height_units='finished raw m above sea level/lift0 for callbacks; structural points and checks local Y=raw-offset',
            widths_m=self.widths,coverage_m2=self.coverage.area,replacement_contours=_contours(self.replacement_domain),
            profiles=self.profile_overrides,
            surfaces=[dict(id=s['id'],way_id=s.get('way_id'),kind=s['kind'],contours=_contours(s['geom']),render=s['render'],collision_only=s['collision_only'],lift_m=0.,role=s.get('role'),riser_m=s.get('riser_m')) for s in self.surfaces],
            flights=self.stairs,rails=self.rails,supports=self.supports,walls=[],walk_paths=walk,
            connector=dict(start_xz=self._bottom.tolist(),end_xz=self.connector_end.tolist(),status='estimated topological pedestrian link, original carriageway/path preserved'),
            ground_checks=dict(points=points,paths=paths,blockers=blockers))

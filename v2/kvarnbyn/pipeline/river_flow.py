#!/usr/bin/env python3
"""Small deterministic downstream field from the world's existing river profiles.

RGB is DATA, not display colour: RG encodes the unit X/Z downstream tangent in
[0,1]; B is an artistic turbulence/foam proxy from an approximately8m height
window. No hydrodynamics, velocity measurement, image pixels or new water mesh.
The renderer samples this only on its existing water geometry.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from PIL import Image
import shapely
from shapely.strtree import STRtree

HERE=Path(__file__).resolve().parents[1]
WINDOW_M=8.0
GRADE_START=.035
GRADE_FULL=.2


def smoothstep(value):
    t=np.clip(value,0.,1.)
    return t*t*(3.-2.*t)


def encode(flow, strength):
    channels=np.column_stack((np.asarray(flow)*.5+.5,np.asarray(strength)))
    return np.floor(np.clip(channels,0.,1.)*255.+.5).astype(np.uint8)


class FlowField:
    """Nearest actual profile segment, with explicit input-order tie breaking."""
    def __init__(self, records):
        self.profiles=[];segments=[];start=[];vector=[];length=[];profile=[];distance=[]
        for source_index,record in enumerate(records):
            points=np.asarray(record.get('points_xyz',[]),float)
            if points.ndim!=2 or points.shape[1]!=3 or len(points)<2 or not np.isfinite(points).all():
                raise ValueError(f'Profile{source_index}: points_xyz needs at least two finite XYZ points')
            if np.any(np.diff(points[:,1])>1e-5):
                raise ValueError(f'Profile{source_index}: heights must already be non-increasing downstream')
            # Keep the downstream height when two consecutive points share X/Z.
            # Never derive direction from a height normal; flat reaches still flow.
            clean=[points[0]]
            for point in points[1:]:
                if np.linalg.norm(point[[0,2]]-clean[-1][[0,2]])<=1e-8:clean[-1]=point
                else:clean.append(point)
            points=np.asarray(clean)
            if len(points)<2:continue
            xz=points[:,[0,2]];d=np.diff(xz,axis=0);ln=np.linalg.norm(d,axis=1)
            s=np.r_[0,np.cumsum(ln)]
            pi=len(self.profiles)
            self.profiles.append(dict(id=str(record.get('id',source_index)),source_index=source_index,
                                      points=points,s=s,length=float(s[-1])))
            for j in range(len(d)):
                segments.append(shapely.LineString([xz[j],xz[j+1]]))
                start.append(xz[j]);vector.append(d[j]);length.append(ln[j]);profile.append(pi);distance.append(s[j])
        if not segments:raise ValueError('river_flow_profiles contains no non-zero X/Z segments')
        self.start=np.asarray(start);self.vector=np.asarray(vector);self.length=np.asarray(length)
        self.profile=np.asarray(profile,dtype=int);self.distance=np.asarray(distance)
        self.tree=STRtree(segments)

    def sample(self, xz):
        q=np.atleast_2d(np.asarray(xz,float))
        pairs,distances=self.tree.query_nearest(shapely.points(q),all_matches=True,return_distance=True)
        # STRtree traversal order is not the tie breaker. Pick lowest source
        # segment index among equal nearest distances, deterministic per input.
        order=np.lexsort((pairs[1],distances,pairs[0]));p=pairs[0,order]
        first=np.r_[True,p[1:]!=p[:-1]];chosen=order[first]
        index=np.empty(len(q),dtype=int);index[pairs[0,chosen]]=pairs[1,chosen]
        v=self.vector[index];length=self.length[index]
        t=np.clip(np.sum((q-self.start[index])*v,axis=1)/(length*length),0.,1.)
        along=self.distance[index]+t*length
        flow=v/length[:,None]
        projected=self.start[index]+v*t[:,None]
        grade=np.zeros(len(q));drop=np.zeros(len(q));window=np.zeros(len(q));height=np.zeros(len(q))
        profile_index=self.profile[index]
        for pi in np.unique(profile_index):
            hit=profile_index==pi;profile=self.profiles[pi]
            a=np.maximum(0.,along[hit]-WINDOW_M/2);b=np.minimum(profile['length'],along[hit]+WINDOW_M/2)
            ha=np.interp(a,profile['s'],profile['points'][:,1]);hb=np.interp(b,profile['s'],profile['points'][:,1])
            delta=np.maximum(0.,ha-hb);span=b-a
            drop[hit]=delta;window[hit]=span
            grade[hit]=delta/np.maximum(span,1e-8)
            height[hit]=np.interp(along[hit],profile['s'],profile['points'][:,1])
        strength=smoothstep((grade-GRADE_START)/(GRADE_FULL-GRADE_START))
        return dict(flow=flow,foam=strength,grade=grade,drop=drop,window=window,height=height,
                    projected=projected,profile=profile_index,segment=index,
                    distance=np.linalg.norm(q-projected,axis=1))


def self_test():
    tests=[]
    def checked(name,condition):
        if not bool(condition):raise AssertionError(name)
        tests.append(name)
    flat=FlowField([dict(id='flat_east',points_xyz=[[0,5,0],[20,5,0]])])
    sample=flat.sample([[5,0],[15,3]])
    checked('flat_profile_retains_downstream_tangent',np.allclose(sample['flow'],[[1,0],[1,0]]) and np.all(sample['foam']==0))
    checked('flat_east_encoding',encode(sample['flow'],sample['foam']).tolist()==[[255,128,0],[255,128,0]])
    steep=FlowField([dict(id='south',points_xyz=[[0,10,0],[0,6,20]])]).sample([[0,10],[0,1]])
    checked('steep_south_tangent_and_8m_grade',np.allclose(steep['flow'],[[0,1],[0,1]]) and np.allclose(steep['grade'],.2))
    checked('full_strength_encoding',encode(steep['flow'],steep['foam']).tolist()==[[128,255,255],[128,255,255]])
    west=FlowField([dict(id='west',points_xyz=[[20,8,0],[0,7,0]])]).sample([[10,0]])
    checked('west_direction_and_soft_strength',np.allclose(west['flow'],[[-1,0]]) and 0<float(west['foam'][0])<1)
    curve=FlowField([dict(id='flat_curve',points_xyz=[[0,2,0],[10,2,0],[10,2,10]])]).sample([[5,0],[10,6]])
    checked('flat_curve_follows_line_not_height_normal',np.allclose(curve['flow'],[[1,0],[0,1]]))
    tie=FlowField([dict(id='first',points_xyz=[[-10,0,0],[10,0,0]]),dict(id='second',points_xyz=[[0,0,-10],[0,0,10]])]).sample([[0,0]])
    checked('exact_distance_tie_uses_input_order',int(tie['profile'][0])==0 and np.allclose(tie['flow'][0],[1,0]))
    rejected=False
    try:FlowField([dict(points_xyz=[[0,1,0],[10,2,0]])])
    except ValueError:rejected=True
    checked('uphill_input_rejected_instead_of_silently_flipped',rejected)
    return tests


def generate(site_path,city_path,output,size=512):
    site_bytes=site_path.read_bytes();city_bytes=city_path.read_bytes()
    site=json.loads(site_bytes);city=json.loads(city_bytes)
    records=site.get('river_flow_profiles',[])
    if not records:raise ValueError('site.json needs river_flow_profiles from site.py; refusing to guess downstream direction')
    bounds=np.asarray(site['meta']['zone'],float)
    if bounds.shape!=(4,) or not np.isfinite(bounds).all() or np.any(bounds[2:]<=bounds[:2]):raise ValueError('Invalid site.meta.zone')
    field=FlowField(records)
    xmin,zmin,xmax,zmax=bounds
    # Image row0 is north/minZ. These are texel CENTRES; shader UV is
    # (worldXZ-bounds.xy)/(bounds.zw-bounds.xy), without a vertical flip.
    xs=xmin+(np.arange(size)+.5)*(xmax-xmin)/size
    zs=zmin+(np.arange(size)+.5)*(zmax-zmin)/size
    x,z=np.meshgrid(xs,zs);points=np.column_stack((x.ravel(),z.ravel()))
    values=field.sample(points);pixels=encode(values['flow'],values['foam']).reshape(size,size,3)
    output.mkdir(parents=True,exist_ok=True)
    png_path=output/'river_flow.png';Image.fromarray(pixels,'RGB').save(png_path,optimize=True)
    decoded_pixels=np.asarray(Image.open(png_path).convert('RGB'))
    assert np.array_equal(decoded_pixels,pixels),'PNG RGB roundtrip changed data'
    decoded=pixels.reshape(-1,3).astype(float)/255
    direction=decoded[:,:2]*2-1
    direction/=np.maximum(1e-10,np.linalg.norm(direction,axis=1))[:,None]
    alignment=np.sum(direction*values['flow'],axis=1)
    assert float(alignment.min())>.9999,'Quantized RG points away from source tangent'
    error=np.abs(decoded[:,2]-values['foam'])
    assert float(error.max())<=.5/255+1e-12,'B error exceeds RGB8 nearest quantization'
    probes=[]
    def probe(label,query):
        q=np.asarray(query,float);v=field.sample([q]);projected=v['projected'][0]
        ix=int(np.clip(np.floor((projected[0]-xmin)/(xmax-xmin)*size),0,size-1))
        iz=int(np.clip(np.floor((projected[1]-zmin)/(zmax-zmin)*size),0,size-1))
        point=np.array([xs[ix],zs[iz]]);expected=field.sample([point]);rgb=decoded_pixels[iz,ix]
        assert np.array_equal(rgb,encode(expected['flow'],expected['foam'])[0]),'Probe texel disagrees with profile query'
        pi=int(v['profile'][0]);profile=field.profiles[pi]
        probes.append(dict(label=label,xz=point.tolist(),downstream=expected['flow'][0].tolist(),
                           grade=float(expected['grade'][0]),foam=float(expected['foam'][0]),
                           pixel_x_y=[ix,iz],pixel_rgb8=rgb.tolist(),
                           query_xz=q.tolist(),nearest_profile_id=profile['id'],
                           nearest_profile_source_index=profile['source_index'],distance_to_profile_m=float(v['distance'][0]),
                           projected_profile_xyz=[float(projected[0]),float(v['height'][0]),float(projected[1])],
                           downstream_xz=v['flow'][0].tolist(),local_drop_m=float(v['drop'][0]),
                           window_span_m=float(v['window'][0]),local_grade=float(v['grade'][0]),foam_proxy=float(v['foam'][0]),
                           texel_xy=[ix,iz],texel_world_xz=point.tolist(),texel_rgb8=rgb.tolist(),
                           texel_expected_downstream_xz=expected['flow'][0].tolist(),texel_encoding_passed=True))
    bridge=next((b for b in site.get('bridges',[]) if b.get('id')=='w44573288' or b.get('name')=='Forsebron'),None)
    if bridge:
        p=bridge['points'][len(bridge['points'])//2];probe('Forsebron nearby profile (bridge midpoint is a locator)',[p[0],p[2]])
    royens=city.get('meta',{}).get('v1_points',{}).get('cap_C',[174.792,-.812])
    probe('Royens trappor nearby river profile (zone is a locator)',royens)
    mids=(field.start+field.vector*.5)
    inside=np.all(mids>bounds[:2]+2,axis=1)&np.all(mids<bounds[2:]-2,axis=1)
    candidates=mids[inside]
    if len(candidates):
        calm=field.sample(candidates)
        # Prefer an 8m window on a flat reach, keeping clear of short endpoints.
        order=np.lexsort((np.arange(len(candidates)),-calm['window'],calm['grade']))
        probe('Quiet profile example (low encoded grade, not measured fluid speed)',candidates[order[0]])
    tests=self_test()
    metadata=dict(schema_version=1,bounds=[float(v) for v in bounds],image=dict(file='river_flow.png',width=size,height=size,mode='RGB8'),
                  encoding=dict(r='downstream unit tangent X * 0.5 + 0.5',g='downstream unit tangent Z * 0.5 + 0.5',
                                b='smoothstep(0.035,0.2,local non-negative height drop / actual window span)',
                                rounding='floor(clamp(channel,0,1)*255+0.5)',window_m=WINDOW_M,
                                pixel_centres=True,row0='north / min Z',shader_uv='(world_xz - bounds.xy) / (bounds.zw - bounds.xy)',
                                sampler='Data texture: omit source_color/sRGB decoding; normalize decoded RG after filtering',
                                mask='No off-channel mask; render/sample only on the existing water mesh'),
                  interpretation='Artistic foam/turbulence proxy from existing estimated water profiles; not hydrodynamics, measured discharge or fluid velocity. B=0 still retains directed stream motion.',
                  nearest_tie_break='lowest source segment index among exact-distance ties',
                  source=dict(generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                              site_sha256=hashlib.sha256(site_bytes).hexdigest(),city_sha256=hashlib.sha256(city_bytes).hexdigest(),
                              profile_count=len(field.profiles),segment_count=len(field.start)),
                  output=dict(png_sha256=hashlib.sha256(png_path.read_bytes()).hexdigest(),png_bytes=png_path.stat().st_size),
                  ranges=dict(flow_x=[float(values['flow'][:,0].min()),float(values['flow'][:,0].max())],
                              flow_z=[float(values['flow'][:,1].min()),float(values['flow'][:,1].max())],
                              local_grade=[float(values['grade'].min()),float(values['grade'].max())],
                              foam_proxy=[float(values['foam'].min()),float(values['foam'].max())],
                              rgb8_min=pixels.reshape(-1,3).min(0).tolist(),rgb8_max=pixels.reshape(-1,3).max(0).tolist()),
                  checks=dict(passed=True,png_roundtrip=True,minimum_decoded_tangent_dot=float(alignment.min()),
                              maximum_foam_quantization_error=float(error.max()),synthetic_assertions=tests),probes=probes)
    (output/'river_flow.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print('KVARNBYN_RIVER_FLOW '+json.dumps(dict(passed=True,size=size,png_bytes=metadata['output']['png_bytes'],
                                               profiles=len(field.profiles),segments=len(field.start),probes=len(probes),
                                               min_tangent_dot=float(alignment.min()))))
    return metadata


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site',type=Path,default=HERE/'data/site.json')
    parser.add_argument('--city',type=Path,default=HERE/'data/city.json')
    parser.add_argument('--output','--stage-dir',dest='output',type=Path,default=HERE/'godot/assets')
    parser.add_argument('--size',type=int,default=512)
    parser.add_argument('--self-test',action='store_true',help='Run deterministic synthetic assertions without reading/writing world data')
    args=parser.parse_args()
    if args.self_test:print('KVARNBYN_RIVER_FLOW_SELF_TEST '+json.dumps(dict(passed=True,checks=self_test())))
    else:
        if not 32<=args.size<=1024:parser.error('--size must be between32 and1024')
        generate(args.site.resolve(),args.city.resolve(),args.output.resolve(),args.size)

"""G18 observed platform/rail; metric geometry and connection steps estimated."""
import math
import numpy as np
from blender_materials import solid_material
from modelkit import color


def build(K,M,city,reference,floor):
    b=next(b for b in city['buildings'] if b['id']==reference['building'])
    foot=b['build_footprint_xz'];a=foot[b['street_edge']];c=foot[(b['street_edge']+1)%len(foot)]
    delta=np.array(c)-a;u=delta/np.linalg.norm(delta);n=np.array([-u[1],u[0]])
    spec=reference['estimates'];s0=spec['from_s_m'];s1=spec['to_s_m'];depth=spec['depth_m']
    top=b['base_y_m']+.45;entry=-spec['entry_length_m']
    p=lambda s,d,y:(a[0]+u[0]*s+n[0]*d,-a[1]-u[1]*s-n[1]*d,y)
    xz=lambda s,d:(a[0]+u[0]*s+n[0]*d,a[1]+u[1]*s+n[1]*d)
    axis=(float(u[0]),float(-u[1]));cross=(float(n[0]),float(-n[1]))
    rail=solid_material('G18_pale_weathered_rail',color(spec['rail_colour']),.85,.12)
    low=min(floor(*xz(s,depth+.1)) for s in [s0,s1])- .3
    def block(name,start,end,height):
        bottom=min(low,height-.2)
        at=p((start+end)/2,(depth+.06)/2,(bottom+height)/2)
        dimensions=(end-start,depth-.06,height-bottom)
        K.box(name,M['concrete'],at,dimensions,axis,cross)
        K.box('COL_'+name,M['collision'],at,dimensions,axis,cross)
    block('Gotafors_platform',s0,s1,top)
    bottom_y=floor(*xz(entry,depth/2))+.025
    count=max(1,math.ceil(abs(top-bottom_y)/.18))
    # Do not invent an impossible narrow/deep stair flight to compensate for DTM.
    if spec['entry_length_m']/count<.24:
        raise ValueError('G18 stair run too short for measured connection height')
    run=min(spec['entry_length_m'],count*.34)
    stair_start=s0-run
    if stair_start-entry>.02:block('Gotafors_approach',entry,stair_start,bottom_y)
    road=next(r for r in city['roads']if r['id']==reference['road'])
    wanted=np.array(xz(entry,depth/2));closest=None;distance=float('inf')
    for A,B in zip(road['line_xz'],road['line_xz'][1:]):
        A=np.array(A);B=np.array(B);delta=B-A
        t=np.clip(np.dot(wanted-A,delta)/max(1e-6,np.dot(delta,delta)),0,1)
        q=A+t*delta;d=np.linalg.norm(q-wanted)
        if d<distance:closest=q;distance=d
    step_points=[[float(closest[0]),float(closest[1]),floor(*closest)]]
    step_points.append([*xz((entry+stair_start)/2,depth/2),bottom_y])
    for i in range(count):
        start=stair_start+run*i/count;end=stair_start+run*(i+1)/count
        h=bottom_y+(top-bottom_y)*(i+1)/count
        block('Gotafors_step_'+str(i),start,end,h)
        step_points.append([*xz((start+end)/2,depth/2),h])
    def tube(name,A,B,radius):
        K.beam(name,rail,A,B,radius,6);K.beam('COL_'+name,M['collision'],A,B,radius,6)
    for s in [s0,(s0+s1)/2,s1]:tube('Gotafors_post',p(s,depth,top),p(s,depth,top+spec['rail_height_m']),.023)
    for h in [.25,spec['rail_height_m']]:
        tube('Gotafors_rail',p(s0,depth,top+h),p(s1,depth,top+h),.023)
        tube('Gotafors_return_rail',p(s1,depth,top+h),p(s1,.08,top+h),.023)
    path=[[float(x),float(y),float(z)] for x,z,y in step_points]
    path += [[float(x),top,float(z)]for x,z in [xz(s0+.3,depth/2),xz(1.85,depth/2),xz(s1-.5,depth/2)]]
    points=[dict(id='g18-platform-'+str(i),position=q,tolerance_m=.16)for i,q in enumerate(path)]
    outer=xz(3,depth+.8);inner=xz(3,depth-.2)
    checks=dict(points=points,paths=[dict(id='g18-to-door',points=path,speed_m_s=1.8,tolerance_m=.22),dict(id='g18-from-door',points=path[::-1],speed_m_s=1.8,tolerance_m=.22)],blockers=[dict(id='g18-rail',**{'from':[outer[0],top,outer[1]],'to':[inner[0],top,inner[1]]},height_m=.9,blocked=True)])
    return dict(source='Observed G18 platform and rail; dimensions and connection treads estimated',top_y_m=top,connection_y_m=bottom_y,step_count_estimated=count,ground_checks=checks)

"""Actual Blender mesh comparison for M29 (run on the staged world.blend).

--site stage/site.json --coverage after/site.json --report report.json --label after --strict
No substitute meshes or height solver are constructed. Intended stair-vs-ramp
height differences are reported separately from normal render/COL discrepancies.
"""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

p=argparse.ArgumentParser();p.add_argument('--site',type=Path,required=True);p.add_argument('--coverage',type=Path,required=True)
p.add_argument('--report',type=Path,required=True);p.add_argument('--label',default='after');p.add_argument('--strict',action='store_true')
args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);site=json.loads(args.site.read_text());after=json.loads(args.coverage.read_text())
meta=after['roten_m29'];surfaces=meta['surfaces']

def in_ring(x,z,ring):
    inside=False
    for (ax,az),(bx,bz) in zip(ring,ring[1:]+ring[:1]):
        if (az>z)!=(bz>z) and x<(bx-ax)*(z-az)/(bz-az)+ax:inside=not inside
    return inside

def contains(x,z,r):
    return any(in_ring(x,z,c['outer']) and not any(in_ring(x,z,h) for h in c.get('holes',[])) for c in r['contours'])

def bvh(prefixes):
    vv,tt,names=[],[],[]
    for ob in bpy.data.objects:
        if ob.type!='MESH' or not ob.name.startswith(prefixes):continue
        ob.data.calc_loop_triangles()
        for tri in ob.data.loop_triangles:
            pts=[ob.matrix_world@ob.data.vertices[i].co for i in tri.vertices]
            if max(v.x for v in pts)<85 or min(v.x for v in pts)>125 or max(-v.y for v in pts)<106 or min(-v.y for v in pts)>140:continue
            start=len(vv);vv.extend(pts);tt.append((start,start+1,start+2));names.append(ob.name)
    return BVHTree.FromPolygons(vv,tt,all_triangles=True),names

def ray(tree,x,z):
    hit,normal,i,d=tree[0].ray_cast(Vector((x,-z,70)),Vector((0,0,-1)),120)
    return (hit.z,tree[1][i]) if hit is not None else None

coll=bvh(('COL_Terrain','COL_asphalt','COL_paving','COL_walkway','COL_trail','COL_Roten_ground','COL_Roten_steps'))
render=bvh(('Terrain','Asphalt','Paving','Walkway','Trail','Roten_ground','Roten_steps'))
new=bvh(('COL_Roten_ground','COL_Roten_steps')) if args.label=='after' else None
holes=[];mismatch=[];missing=[];max_delta=0.;ramp_max=0.;count=0
bounds=[q for r in surfaces for c in r['contours'] for q in c['outer']]
minx,minz=min(q[0] for q in bounds),min(q[1] for q in bounds);maxx,maxz=max(q[0] for q in bounds),max(q[1] for q in bounds)
for ix in range(math.ceil((maxx-minx)/.3)):
    x=minx+(ix+.37)*.3
    for iz in range(math.ceil((maxz-minz)/.3)):
        z=minz+(iz+.41)*.3;records=[r for r in surfaces if contains(x,z,r)]
        if not records:continue
        count+=1;a,b=ray(coll,x,z),ray(render,x,z)
        if a is None or b is None:holes.append([round(x,3),round(z,3)]);continue
        delta=abs(a[0]-b[0]);max_delta=max(max_delta,delta)
        ramp=any(r.get('collision_only',False) or r.get('render',True)==False for r in records)
        if ramp:ramp_max=max(ramp_max,delta)
        if delta>(.205 if ramp else .015):mismatch.append([round(x,3),round(z,3),a,b])
        if new is None or ray(new,x,z) is None:missing.append([round(x,3),round(z,3)])
before=json.loads((args.coverage.parent.parent/'before/site.json').read_text())
fixed={k:site['meshes'][k]==before['meshes'][k] for k in ('asphalt','water')}
fixed['bridge_decks']=site['bridges']==before['bridges']
result=dict(label=args.label,actual_blend=bpy.data.filepath,spacing_m=.3,samples=count,holes=len(holes),
            render_collision_mismatch=len(mismatch),max_render_collision_delta_m=round(max_delta,5),
            stair_ramp_max_delta_m=round(ramp_max,5),samples_without_authored_floor=len(missing),
            unchanged=fixed,first_holes=holes[:10],first_mismatches=mismatch[:10])
result['passed']=count>100 and not holes and not mismatch and not missing and all(fixed.values())
args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2));print('ROTEN_MESH_QA',json.dumps(result),flush=True)
if args.strict and not result['passed']:raise RuntimeError('M29 actual-mesh QA failed: '+str(args.report))

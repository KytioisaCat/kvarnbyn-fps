"""Measure actual saved Blender collision/render meshes, without editing the scene.
Usage: Blender -b blender/torget.blend --python-exit-code 1 --python reference/qa_walk.py -- --label initial
Use --strict to turn failed geometric gates into a nonzero Blender exit.
Game coordinates x/east,y/up,z/south map to Blender(x,-z,y).
"""
import bpy
import json, math, sys, re
from pathlib import Path
from datetime import datetime, timezone
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).resolve().parent
POC=HERE.parent
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
label=args[args.index('--label')+1] if '--label' in args else ''
label=re.sub('[^a-zA-Z0-9_-]','',label)
OUT=HERE/('qa-walk'+('-'+label if label else '')+'.json')
CITY=json.loads((POC/'data/city_spec.json').read_text())
META=json.loads((POC/'godot/assets/world_meta.json').read_text())
FLOORS={'COL_Terrain','COL_asphalt','COL_sidewalk','COL_Forsebron'}
RENDER={'Asphalt','Sidewalk','Forsebron_deck'}
WALK_NAMES={'kvarnbygatan','forsebron','götaforsliden','gamla torget'}
STEP=.5
JUMP_LIMIT=.22
STEP_UP=.65
EPS=1e-4
inventory=[]
col_entries=[]
visual_entries=[]
building_entries=[]
deps=bpy.context.evaluated_depsgraph_get()

def rounded(x,digits=4):
    if x is None:return None
    if isinstance(x,(list,tuple)):return [rounded(v,digits) for v in x]
    return round(float(x),digits)

for obj in bpy.context.scene.objects:
    if obj.type!='MESH':continue
    logical=obj.name.split('__',1)[0]
    kind='floor' if logical in FLOORS else 'render' if logical in RENDER else 'building' if logical.startswith('COL_') else None
    if kind is None:continue
    evaluated=obj.evaluated_get(deps)
    mesh=evaluated.to_mesh()
    mesh.calc_loop_triangles()
    matrix=obj.matrix_world
    verts=[matrix@v.co for v in mesh.vertices]
    triangles=[];down=0;up=0;vertical=0
    for tri in mesh.loop_triangles:
        p,q,r=(verts[i] for i in tri.vertices)
        normal=(q-p).cross(r-p)
        nz=normal.normalized().z if normal.length>1e-12 else 0
        up+=nz>.05;down+=nz<-.05;vertical+=abs(nz)<=.05
        # Only upward top faces are walkable. Building shells keep their walls/caps.
        if kind=='building' or nz>.05:triangles.append(tuple(tri.vertices))
    entry={'name':obj.name,'logical':logical,'kind':kind,'triangles_used':len(triangles),'up_triangles':int(up),'down_triangles':int(down),'vertical_triangles':int(vertical)}
    inventory.append(entry)
    if triangles:
        entry=dict(entry,bvh=BVHTree.FromPolygons(verts,triangles,all_triangles=True,epsilon=1e-6),bounds_min=tuple(min(v[i] for v in verts) for i in range(3)),bounds_max=tuple(max(v[i] for v in verts) for i in range(3)))
        {'floor':col_entries,'render':visual_entries,'building':building_entries}[kind].append(entry)
    evaluated.to_mesh_clear()


def column_hits(entries,x,z):
    """Read layers above AND below refY; keep all upward faces, not only the global top."""
    hits=[]
    for entry in entries:
        top=100.0
        for _ in range(12):
            loc,normal,index,distance=entry['bvh'].ray_cast(Vector((x,-z,top)),Vector((0,0,-1)),300)
            if loc is None:break
            h=float(loc.z)
            if not any(old['object']==entry['logical'] and abs(old['height']-h)<.0005 for old in hits):
                hits.append({'height':h,'object':entry['logical'],'normal_z':float(normal.z)})
            top=h-EPS
    return sorted(hits,key=lambda h:h['height'],reverse=True)


def choose(hits,ref=None):
    if not hits:return None
    if ref is None:return hits[0]
    reachable=[h for h in hits if h['height']<=ref+STEP_UP]
    if reachable:return reachable[0]
    return min(hits,key=lambda h:abs(h['height']-ref))


def clean_hit(hit):
    return None if hit is None else {'height':rounded(hit['height']),'object':hit['object'],'normal_z':rounded(hit['normal_z'])}


def interior_buildings(x,y,z):
    """Horizontal ray parity is valid for these capped polygon shells even without a bottom."""
    found=[]
    direction=Vector((.812367,.583147,0)).normalized()
    for entry in building_entries:
        point=(x,-z,y)
        if any(point[i]<entry['bounds_min'][i]-EPS or point[i]>entry['bounds_max'][i]+EPS for i in range(3)):continue
        cursor=Vector((x,-z,y+.000017));count=0
        for _ in range(50):
            loc,normal,index,distance=entry['bvh'].ray_cast(cursor,direction,500)
            if loc is None:break
            count+=1;cursor=loc+direction*EPS
        if count%2:found.append(entry['logical'])
    return found


def resample(points):
    """Half-metre samples, always including source vertices and the final endpoint."""
    samples=[];distance=0.0
    for a,b in zip(points,points[1:]):
        length=math.dist(a,b)
        if length<1e-7:continue
        count=max(1,math.ceil(length/STEP))
        for k in range(count):
            if samples and k==0 and math.dist(samples[-1]['xz'],a)<1e-7:continue
            t=k/count;samples.append({'xz':[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t],'distance':distance+t*length})
        distance+=length
    if points:samples.append({'xz':list(points[-1]),'distance':distance})
    return samples


def probe_route(road,side_offset=0.0):
    result={'osm_id':road['id'],'name':road['name'],'bridge':road['bridge'],'side_offset_m':side_offset,'sample_spacing_limit_m':STEP,'samples':[],'jumps':[],'holes':[],'missing_rendered_road':[],'buried_rendered_road':[],'building_intrusions':[],'max_height_jump_m':0.0,'max_collision_render_deviation_m':0.0}
    ref=None;last=None
    samples=resample(road['line_xz'])
    for i,sample in enumerate(samples):
        x,z=sample['xz']
        if side_offset:
            a=samples[max(0,i-1)]['xz'];b=samples[min(len(samples)-1,i+1)]['xz']
            dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz)
            if length:x+=-dz/length*side_offset;z+=dx/length*side_offset
        floor_hits=column_hits(col_entries,x,z);paint_hits=column_hits(visual_entries,x,z)
        # Start on the expected painted road when there are multiple height layers.
        if ref is None and paint_hits:ref=paint_hits[0]['height']
        floor=choose(floor_hits,ref)
        shown=paint_hits[0] if paint_hits else None
        record={'xz':rounded([x,z]),'distance_m':rounded(sample['distance']),'floor':clean_hit(floor),'render_top':clean_hit(shown)}
        if len(floor_hits)>1:record['layers']=[clean_hit(h) for h in floor_hits]
        if floor is None:
            result['holes'].append(record)
            last=None;ref=None
        else:
            y=floor['height']
            if last:
                jump=y-last['floor']['height']
                result['max_height_jump_m']=max(result['max_height_jump_m'],abs(jump))
                if abs(jump)>JUMP_LIMIT:
                    result['jumps'].append({'from_xz':last['xz'],'to_xz':record['xz'],'from_height_m':last['floor']['height'],'to_height_m':rounded(y),'delta_m':rounded(jump),'distance_m':rounded(sample['distance']),'from_object':last['floor']['object'],'to_object':floor['object']})
            if shown:
                deviation=y-shown['height']
                result['max_collision_render_deviation_m']=max(result['max_collision_render_deviation_m'],abs(deviation))
                record['collision_minus_render_m']=rounded(deviation)
                if deviation>JUMP_LIMIT:result['buried_rendered_road'].append(record)
            else:result['missing_rendered_road'].append(record)
            buildings=interior_buildings(x,y+1.0,z)
            if buildings:result['building_intrusions'].append({'xz':record['xz'],'height_m':rounded(y+1.0),'buildings':buildings})
            ref=y;last=record
        result['samples'].append(record)
    for key in ['max_height_jump_m','max_collision_render_deviation_m']:result[key]=rounded(result[key])
    result['sample_count']=len(result['samples'])
    return result

selected_roads=[r for r in CITY['roads'] if r.get('name','').casefold() in WALK_NAMES]
routes=[probe_route(r) for r in selected_roads]
# Two side tracks test lane/support edges that a centreline alone can miss.
lateral_routes=[]
for road in selected_roads:
    offset=min(2.5,max(1.0,road.get('width_m',4.5)*.34))
    for side in [-1,1]:lateral_routes.append(probe_route(road,side*offset))
junctions=[]
for i,a in enumerate(routes):
    for b in routes[i+1:]:
        for sa in a['samples'][::max(1,len(a['samples'])-1)]:
            for sb in b['samples'][::max(1,len(b['samples'])-1)]:
                if math.dist(sa['xz'],sb['xz'])<=.05 and sa['floor'] and sb['floor']:
                    delta=sa['floor']['height']-sb['floor']['height']
                    junctions.append({'road_a':a['osm_id'],'road_b':b['osm_id'],'xz':sa['xz'],'delta_m':rounded(delta),'pass':abs(delta)<=JUMP_LIMIT})


def check_position(name,position,source,free_camera=False):
    x,y,z=position;hits=column_hits(col_entries,x,z)
    below=[h for h in hits if h['height']<=y+.05]
    floor=below[0] if below else choose(hits,y-1.7)
    height=y-floor['height'] if floor else None
    inside=interior_buildings(x,y,z)
    inside_feet=interior_buildings(x,y-1.7+.15,z)
    return {'id':name,'source':source,'position':rounded(position),'free_camera':free_camera,'floor':clean_hit(floor),'eye_height_above_floor_m':rounded(height),'inside_building_at_eye':inside,'inside_building_at_feet':inside_feet,'eye_height_pass':True if free_camera else floor is not None and 1.35<=height<=2.15,'pass':not inside and not inside_feet and (free_camera or (floor is not None and 1.35<=height<=2.15))}

# Runtime spawn coordinates represent the CharacterBody feet, whereas named view
# coordinates represent camera eyes. world.gd snaps feet to ground and adds0.05m;
# player.gd then puts the camera1.65m above the feet.
spawn_meta=META['spawn'];spawn_raw=list(spawn_meta['position']);spawn_feet=list(spawn_raw)
if spawn_meta.get('snap_to_ground',False):
    spawn_hits=column_hits(col_entries,spawn_raw[0],spawn_raw[2])
    below_start=[h for h in spawn_hits if h['height']<spawn_raw[1]+35]
    if below_start:spawn_feet[1]=below_start[0]['height']+.05
else:spawn_feet[1]+=.05
spawn_eye=[spawn_feet[0],spawn_feet[1]+1.65,spawn_feet[2]]
positions=[check_position('spawn',spawn_eye,'world_meta feet -> runtime ground snap+0.05m -> camera+1.65m')]
positions[0]['metadata_position_feet']=rounded(spawn_raw)
positions[0]['effective_position_feet']=rounded(spawn_feet)
positions[0]['runtime_snap_to_ground']=spawn_meta.get('snap_to_ground',False)

for view in META['views']:
    cam=bpy.data.objects.get('View_'+view['id'])
    if cam:
        p=cam.matrix_world.translation;pos=[p.x,p.z,-p.y];source='saved Blender camera'
    else:pos=view['position'];source='world_meta fallback (camera absent)'
    positions.append(check_position(view['id'],pos,source,free_camera=view['id']=='oversikt'))

summary={'routes':len(routes),'samples':sum(r['sample_count'] for r in routes),'height_jumps_over_limit':sum(len(r['jumps']) for r in routes),'holes':sum(len(r['holes']) for r in routes),'missing_rendered_road_samples':sum(len(r['missing_rendered_road']) for r in routes),'buried_rendered_road_samples':sum(len(r['buried_rendered_road']) for r in routes),'building_intrusion_samples':sum(len(r['building_intrusions']) for r in routes),'max_height_jump_m':max((r['max_height_jump_m'] for r in routes),default=0),'max_collision_render_deviation_m':max((r['max_collision_render_deviation_m'] for r in routes),default=0),'failed_positions':sum(not p['pass'] for p in positions),'failed_junctions':sum(not p['pass'] for p in junctions)}
summary['pass']=summary['height_jumps_over_limit']==0 and summary['holes']==0 and summary['missing_rendered_road_samples']==0 and summary['building_intrusion_samples']==0 and summary['buried_rendered_road_samples']==0 and summary['failed_positions']==0 and summary['failed_junctions']==0
report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'blend_file':bpy.data.filepath,'blend_modified_utc':datetime.fromtimestamp(Path(bpy.data.filepath).stat().st_mtime,timezone.utc).isoformat(),'world_meta_modified_utc':datetime.fromtimestamp((POC/'godot/assets/world_meta.json').stat().st_mtime,timezone.utc).isoformat(),'method':{'source':'Actual saved evaluated Blender meshes that are exported as COL_ geometry; not heightAt or site-model interpolation.','blender_coordinate_mapping':'game(x,y,z) -> Blender(x,-z,y)','walkable_objects':sorted(FLOORS),'render_reference_objects':sorted(RENDER),'excluded_from_floor':'All building shells, vegetation, rails, river walls and water. Building shells are checked separately for containment.','vertical_raycast':'Top-facing triangles, columns queried from above through all layers. Tracked refY chooses top reachable support <=previous+0.65m, fallback nearest if none.','step_m':STEP,'jump_limit_m':JUMP_LIMIT,'eye_height_gate_m':[1.35,2.15],'limits':['This verifies point support/height, not the full CharacterBody capsule sweep or horizontal rail collision.','Water is not a walkable floor.','OSM street centreline may differ from final lane placement; missing rendered road is recorded separately from a collision hole.','Overview camera is intentionally exempt from walking eye-height test.']},'inventory':inventory,'summary':summary,'positions':positions,'junctions':junctions,'routes':routes,'lateral_routes':lateral_routes,'lateral_summary':{'samples':sum(r['sample_count'] for r in lateral_routes),'height_jumps_over_limit':sum(len(r['jumps']) for r in lateral_routes),'holes':sum(len(r['holes']) for r in lateral_routes),'building_intrusion_samples':sum(len(r['building_intrusions']) for r in lateral_routes),'missing_rendered_road_samples':sum(len(r['missing_rendered_road']) for r in lateral_routes),'max_height_jump_m':max((r['max_height_jump_m'] for r in lateral_routes),default=0),'max_collision_render_deviation_m':max((r['max_collision_render_deviation_m'] for r in lateral_routes),default=0)}}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('QA_WALK_REPORT',OUT)
print('QA_WALK_SUMMARY',json.dumps(summary,ensure_ascii=False))
print('QA_WALK_LATERAL_SUMMARY',json.dumps(report['lateral_summary'],ensure_ascii=False))
for route in routes:
    if route['jumps'] or route['holes'] or route['buried_rendered_road']:
        print('QA_WALK_ROUTE',route['osm_id'],route['name'],'jumps',len(route['jumps']),'holes',len(route['holes']),'buried',len(route['buried_rendered_road']),'max_jump',route['max_height_jump_m'])
        for event in route['jumps'][:5]:print('QA_WALK_JUMP',json.dumps(event,ensure_ascii=False))
for position in positions:
    if not position['pass']:print('QA_WALK_POSITION',json.dumps(position,ensure_ascii=False))
if '--strict' in args and not summary['pass']:raise RuntimeError('Walking geometry gates failed; see '+str(OUT))

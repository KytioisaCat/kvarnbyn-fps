"""Author the Gamla torget proof in Blender, export one glTF world and evidence views.
Usage: Blender -b --python scripts/build_scene.py -- [--render] [--quick]
"""
from pathlib import Path
import json, math, random, sys, time
import bpy, bmesh
from mathutils import Vector

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/'scripts'));sys.path.insert(0,str(HERE/'assets-src'))
from modelkit import Kit,Frame,color,roof,text,window,facade
from blender_materials import pbr_material,solid_material
from blender_vegetation import place_tree,load_library
from blender_finish import apply_finish

random.seed(29)
CITY=json.loads((HERE/'data/city_spec.json').read_text())
SITE=json.loads((HERE/'data/site_meshes.json').read_text())
OFFSET=CITY['meta']['origin']['y_offset_m']
OUT=HERE/'blender';OUT.mkdir(exist_ok=True)
EVIDENCE=HERE/'evidence';EVIDENCE.mkdir(exist_ok=True)
GODOT=HERE/'godot/assets';GODOT.mkdir(parents=True,exist_ok=True)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for d in [bpy.data.materials,bpy.data.meshes,bpy.data.curves]:
    for item in list(d):
        if item.users==0:d.remove(item)
K=Kit()
K.window_batch_name='WindowInteriors'


def pbr(key,name=None,tint=None,strength=.35):
    m=pbr_material(key,name,base_color=color(tint) if tint else None,normal_strength=strength)
    m['tile_size_m']=float(m['tile_size_m'][0]);return m

M={
'panel':pbr('plaster','Painted_clapboard','#eeeae0',.12),
'cream':pbr('plaster','Cream_clapboard','#ded7c3',.12),
'plaster':pbr('plaster','Corpus_plaster','#e8e1cf',.3),
'brick':pbr('brick','Historic_brick',None,.65),
'roof':pbr('roof_tiles','Clay_roof_tiles',None,.6),
'asphalt':pbr('asphalt','Road_asphalt',None,.32),
'paving':pbr('cobblestone','Granite_setts',None,.55),
'grass':pbr('grass','Grass_ground',None,.55),
'stone':pbr('rock','Granite_foundation',None,.55),
'green':solid_material('Krakan_green',color('#225747'),.6),
'rust':solid_material('Musikskolan_oxblood',color('#914d40'),.65),
'white':solid_material('Offwhite_trim',color('#e9e4d9'),.65),
'blue':solid_material('Blue_awning',color('#154b89'),.82),
'metal':solid_material('Standing_seam_roof',color('#343b40'),.58,.18),
'iron':solid_material('Street_iron',color('#313738'),.6,.25),
'wood':pbr('wood_painted','Bench_wood',None,.3),
'glass':solid_material('Window_glass',color('#344b52'),.18,.32),
'black':solid_material('Sign_black',color('#172426'),.8),
'foam':solid_material('Foam',color('#d6e2da'),.6),
'water':solid_material('WaterFlow',color('#31575a'),.34,.03),
'curb':solid_material('Worn_granite_kerb',color('#99998d'),.88),
'soil':solid_material('Planter_soil',color('#4d4c36'),1),
'collision':solid_material('Collision_only',(1,0,1,1),1),
}
apply_finish(M,glass=True)
glass_bsdf=M['glass'].node_tree.nodes.get('Principled BSDF')
glass_bsdf.inputs['Alpha'].default_value=.18
glass_bsdf.inputs['Metallic'].default_value=.03
M['glass'].diffuse_color=tuple(M['glass'].diffuse_color[:3])+(.18,)
M['glass'].surface_render_method='DITHERED'
leaf_collection=load_library()['Broadleaf_A']
M['leaves']=next(o.data.materials[0] for o in leaf_collection.objects if o.type=='MESH' and 'Leaves' in o.name)

T=SITE['terrain'];N=len(T);NX=len(T[0])

def ground(x,z):
    fx=max(0,min(NX-1.001,(x+140)/2));fz=max(0,min(N-1.001,(z+140)/2));ix=int(fx);iz=int(fz);tx=fx-ix;tz=fz-iz
    return (T[iz][ix][1]*(1-tx)+T[iz][ix+1][1]*tx)*(1-tz)+(T[iz+1][ix][1]*(1-tx)+T[iz+1][ix+1][1]*tx)*tz

def walk_height(x,z):
    """The visible authored surface owns camera/furniture heights, not its subgrade."""
    best=ground(x,z)
    for kind in ['asphalt','sidewalk']:
        for tri in SITE['meshes'][kind]:
            (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=tri
            if x<min(x1,x2,x3)-.0001 or x>max(x1,x2,x3)+.0001 or z<min(z1,z2,z3)-.0001 or z>max(z1,z2,z3)+.0001:continue
            den=(z2-z3)*(x1-x3)+(x3-x2)*(z1-z3)
            if abs(den)<1e-9:continue
            a=((z2-z3)*(x-x3)+(x3-x2)*(z-z3))/den;b=((z3-z1)*(x-x3)+(x1-x3)*(z-z3))/den;c=1-a-b
            if min(a,b,c)>=-.00001:best=max(best,a*y1+b*y2+c*y3)
    for bridge in SITE['bridge']:
        a=Vector(bridge['line_xz'][0]);b=Vector(bridge['line_xz'][-1]);p=Vector((x,z));ab=b-a;t=max(0,min(1,(p-a).dot(ab)/ab.length_squared))
        if (p-a-ab*t).length<3.75:best=max(best,17.79-OFFSET)
    return best

def near_bridge(x,z,margin=0):
    p=Vector((x,z))
    for bridge in SITE['bridge']:
        a=Vector(bridge['line_xz'][0]);b=Vector(bridge['line_xz'][-1]);ab=b-a;t=max(0,min(1,(p-a).dot(ab)/ab.length_squared))
        if (p-a-ab*t).length<bridge['width_m']/2+margin:return True
    return False

# Terrain is a fixed, authored background mesh. Street profiles are already conformed offline.
for j in range(N-1):
    for i in range(NX-1):
        points=[T[j][i],T[j][i+1],T[j+1][i+1],T[j+1][i]]
        steep=max(p[1] for p in points)-min(p[1] for p in points)>1.6
        pts=[(x,-z,y) for x,y,z in reversed(points)]
        K.face('Terrain',M['grass'],pts,[(p[0]/3,p[1]/3) for p in pts])
        if -70<=points[0][0]<=70 and -70<=points[0][2]<=70:
            K.face('COL_Terrain',M['collision'],pts)
for name,tris in SITE['meshes'].items():
    mat={'asphalt':M['asphalt'],'sidewalk':M['paving'],'water':M['water'],'soil':M['soil']}[name]
    for tri in tris:
        pts=[Vector((x,-z,y)) for x,y,z in tri]
        if (pts[1]-pts[0]).cross(pts[2]-pts[0]).z<0:pts.reverse()
        tile=mat.get('tile_size_m',3)
        K.face(name.title(),mat,pts,[(p.x/tile,p.y/tile) for p in pts])
        if name!='water':K.face('COL_'+name,M['collision'],pts)
for face in SITE.get('surface_foundations',[]):
    K.face('Paving_foundation',M['curb'],[(x,-z,y) for x,y,z in face])
for a,b in SITE['curbs']:
    x,y,z=a;xx,yy,zz=b;length=math.hypot(xx-x,zz-z)
    if length>14:continue
    u=((xx-x)/length,-(zz-z)/length)
    K.box('Kerbs',M['curb'],((x+xx)/2,-(z+zz)/2,(y+yy)/2-.03),(length,.17,.12),u)

# Authored stone river walls and steel handrails. Break at the actual Forsebron crossing.
water=CITY['waterways'][0]
line=water['line_xz']
for idx,(a,b) in enumerate(zip(line,line[1:])):
    length=math.dist(a,b);u=((b[0]-a[0])/length,-(b[1]-a[1])/length);v=(-u[1],u[0])
    for side in [-1,1]:
        for step in range(max(1,math.ceil(length/3))):
            t0=step/max(1,math.ceil(length/3));t1=(step+1)/max(1,math.ceil(length/3))
            p=Vector((a[0]+(b[0]-a[0])*t0,-a[1]-(b[1]-a[1])*t0,0));q=Vector((a[0]+(b[0]-a[0])*t1,-a[1]-(b[1]-a[1])*t1,0));p.x+=v[0]*side*4.3;p.y+=v[1]*side*4.3;q.x+=v[0]*side*4.3;q.y+=v[1]*side*4.3
            if near_bridge((p.x+q.x)/2,-(p.y+q.y)/2,1.2):continue
            top=(ground(p.x,-p.y)+ground(q.x,-q.y))/2+.12
            bottom=min(top-1.3,-2.25-idx*.15)
            if top-bottom>4:bottom=top-3.4
            K.box('River_wall',M['stone'],((p.x+q.x)/2,(p.y+q.y)/2,(top+bottom)/2),((q-p).length,.38,top-bottom),u)
            K.box('River_cap',M['curb'],((p.x+q.x)/2,(p.y+q.y)/2,top+.04),((q-p).length,.56,.16),u)
            for h in [.52,1.0]:K.beam('River_rail',M['iron'],(p.x,p.y,top+h),(q.x,q.y,top+h),.025)
            K.beam('River_rail',M['iron'],(p.x,p.y,top),(p.x,p.y,top+1.06),.04)
            K.box('COL_Bank_rails',M['collision'],((p.x+q.x)/2,(p.y+q.y)/2,top+.52),((q-p).length,.09,1.04),u)
# Bridge deck follows its two landings, not the DTM pit under the span.
for bridge in SITE['bridge']:
    a=bridge['line_xz'][0];b=bridge['line_xz'][-1];length=math.dist(a,b);u=((b[0]-a[0])/length,-(b[1]-a[1])/length);v=(-u[1],u[0]);center=((a[0]+b[0])/2,-(a[1]+b[1])/2);level=17.76-OFFSET
    K.box('Forsebron_deck',M['asphalt'],(*center,level-.17),(length+1,7.5,.4),u)
    K.box('COL_Forsebron',M['collision'],(*center,level-.17),(length+1,7.5,.4),u)
    for side in [-1,1]:
        K.box('COL_Bridge_rails',M['collision'],(center[0]+v[0]*side*3.65,center[1]+v[1]*side*3.65,level+.52),(length,.09,1.04),u)
        for h in [.45,1.02]:K.beam('Forsebron_rail',M['iron'],(a[0]+v[0]*side*3.65,-a[1]+v[1]*side*3.65,level+h),(b[0]+v[0]*side*3.65,-b[1]+v[1]*side*3.65,level+h),.035)
        for k in range(int(length/.85)+1):
            t=k/max(1,int(length/.85));x=a[0]+(b[0]-a[0])*t+v[0]*side*3.65;y=-a[1]-(b[1]-a[1])*t+v[1]*side*3.65
            K.beam('Forsebron_rail',M['iron'],(x,y,level),(x,y,level+1.06),.03)


def ensure_ccw(poly):
    poly=list(poly);area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1]))
    return list(reversed(poly)) if area>0 else poly


def build_hip_polygon(name,poly,eave,rise,ridge=None):
    c=Vector((sum(p[0] for p in poly)/len(poly),sum(p[1] for p in poly)/len(poly)))
    p=[Vector(a)+(Vector(a)-c).normalized()*.28 for a in poly]
    if ridge is None:
        ridge=[(c.x-.1,c.y),(c.x+.1,c.y)]
    r=[(x,-z,eave+rise) for x,z in ridge]
    points=[(v.x,-v.y,eave) for v in p]
    if len(p)==5:
        faces=[[points[0],points[1],r[0]],[points[1],points[2],r[1],r[0]],[points[2],points[3],r[1]],[points[3],points[4],r[1]],[points[4],points[0],r[0],r[1]]]
    else:
        faces=[[points[i],points[(i+1)%len(points)],r[0]] for i in range(len(points))]
    for f in faces:
        f=list(map(Vector,f))
        if (f[1]-f[0]).cross(f[2]-f[0]).z<0:f.reverse()
        K.face(name,M['metal'],f)
        # Raised standing seams on the long roof slopes.
        if len(f)==4:
            for k in range(1,math.ceil((f[1]-f[0]).length/.65)):
                t=k/max(1,math.ceil((f[1]-f[0]).length/.65));start=f[0].lerp(f[1],t);end=f[3].lerp(f[2],t);start.z+=.018;end.z+=.018
                K.beam(name,M['metal'],start,end,.012,4)
    for a,b in zip(points,points[1:]+points[:1]):
        K.beam(name,M['white'],(a[0],a[1],a[2]-.08),(b[0],b[1],b[2]-.08),.06)


def shell_and_facades(b,poly=None,base=None,height=None,levels=None,mat=None,trim=None):
    poly=ensure_ccw(poly or b['footprint_xz']);base=b['base_y_m'] if base is None else base;height=height or b['wall_height_m'];levels=levels or b['levels'];name=b['id'];wallmat=mat or M['panel'];trim=trim or M['white']
    K.shell('COL_'+name,M['collision'],poly,base-.4,height+.4)
    # Granite plinth is fitted below the surveyed level, not a floating facade.
    for a,bb in zip(poly,poly[1:]+poly[:1]):
        low=min(ground(*a),ground(*bb),base)-.25
        K.face(name+'_Foundation',M['stone'],[(a[0],-a[1],low),(bb[0],-bb[1],low),(bb[0],-bb[1],base+.28),(a[0],-a[1],base+.28)])
        if math.dist(a,bb)>2:
            civic=b['id']=='w92332122'
            facade(K,name,(a[0],-a[1]),(bb[0],-bb[1]),base,height,wallmat,trim,M['glass'],M['white'],levels=4 if civic else levels,bays=8 if civic and math.dist(a,bb)>25 else None,panel=wallmat in [M['panel'],M['cream']],ornate=civic,floor_heights=[1.8,2.6,3.5,2.4] if civic else None)
    return poly

# KRÅKAN: hand-authored three volumes and two differently oriented fronts.
krakan=next(b for b in CITY['buildings'] if b['id']=='w92331981')
for volume in krakan['volumes']:
    poly=ensure_ccw(volume['footprint_xz']);base=volume['base_height_raw_m']-OFFSET;height=volume['wall_height_m'];name=volume['id']
    K.shell('COL_'+name,M['collision'],poly,base-.35,height+.35)
    fronts=[f for f in krakan['street_facades'] if f['volume']==name]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        isfront=next((f for f in fronts if (math.dist(a,f['edge_xz'][1])<.2 and math.dist(b,f['edge_xz'][0])<.2) or (math.dist(a,f['edge_xz'][0])<.2 and math.dist(b,f['edge_xz'][1])<.2)),None)
        if isfront:
            # This loop is CCW in Blender: fronts are reversed from map order.
            bays=len(isfront['lower_bays']);up=isfront.get('upper_bays',bays)
            types=isfront['lower_bays'] if math.dist(a,isfront['edge_xz'][0])<.2 else list(reversed(isfront['lower_bays']))
            facade(K,name,(a[0],-a[1]),(b[0],-b[1]),base,height,M['panel'],M['green'],M['glass'],M['white'],levels=volume['levels'],bays=bays,panel=True,awning=M['blue'] if name=='krakan_west' else None,sign='KRÅKANS KROG' if name=='krakan_west' else None,floor_bays=[bays,up],lower_types=types)
        elif math.dist(a,b)>2:
            facade(K,name,(a[0],-a[1]),(b[0],-b[1]),base,height,M['panel'],M['green'],M['glass'],M['white'],levels=volume['levels'],panel=True)
        low=min(ground(*a),ground(*b),base)-.3
        K.face(name+'_Foundation',M['stone'],[(a[0],-a[1],low),(b[0],-b[1],low),(b[0],-b[1],base+.18),(a[0],-a[1],base+.18)])
    if name=='krakan_west':
        build_hip_polygon(name+'_Roof',volume['footprint_xz'],base+height,volume['roof_rise_m'],[(7,30.3),(16.5,29.1)])
        for x,z in [(9.5,29.8),(16.1,29.4)]:
            K.box(name+'_Chimneys',M['metal'],(x,-z,base+height+1.9),(.65,.65,.9));K.box(name+'_Chimneys',M['metal'],(x,-z,base+height+2.4),(.8,.8,.12))
    else:
        axis=Vector(krakan['major_axis_xz']);c=[sum(v[i] for v in poly)/len(poly) for i in [0,1]];fr=Frame(c,axis);L=10.2 if name=='krakan_link' else 22.3;W=9.6
        roof(K,name+'_Roof',fr,L,W,base+height,volume['roof_rise_m'],M['metal'],M['white'],seams=True)
        for da in ([0] if name=='krakan_link' else[-5,5]):
            dc=fr.p(da,-W/2+.12,base+height-.65)
            K.box(name+'_Dormers',M['panel'],dc,(2.1,.7,1.5),fr.u)
            normal=(-fr.v[0],-fr.v[1]);window(K,name+'_Dormers',(dc[0]+normal[0]*.4,dc[1]+normal[1]*.4,dc[2]-.5),fr.u,normal,.85,1.12,M['green'],M['glass'],M['white'])
            p1=fr.p(da-1.2,-W/2-.5,base+height+.1);p2=fr.p(da+1.2,-W/2-.5,base+height+.1);p3=fr.p(da,-W/2-.5,base+height+1)
            K.face(name+'_Dormers',M['panel'],[p1,p2,p3]);K.face(name+'_Dormers',M['metal'],[p1,p3,fr.p(da,-W/2+1.5,base+height+1),fr.p(da-1.2,-W/2+1.5,base+height+.1)]);K.face(name+'_Dormers',M['metal'],[p3,p2,fr.p(da+1.2,-W/2+1.5,base+height+.1),fr.p(da,-W/2+1.5,base+height+1)])
    # Rainwater pipes sit on observed facade breaks.
    for x,z in volume['footprint_xz'][::2]:
        K.beam(name+'_Downpipes',M['white'],(x,-z,base+.2),(x,-z,base+height-.2),.055)

# Remaining buildings retain surveyed footprints, authored facade kits and explicit estimated heights.
for b in CITY['buildings']:
    if b['id']=='w92331981':continue
    mat=M['brick'] if 'brick' in b['archetype'] else M['cream'] if b['id']=='w92332122' else M['plaster'] if b['id']=='w92332103' else M['panel']
    trim=M['rust'] if b['id']=='w92332122' else M['white']
    poly=shell_and_facades(b,mat=mat,trim=trim)
    rect=b['rectangle_xz'];center=[sum(p[i] for p in rect)/4 for i in [0,1]];fr=Frame(center,b['major_axis_xz']);base=b['base_y_m'];eave=base+b['wall_height_m']
    roofmat=M['metal'] if b['id']=='w92332103' else M['roof']
    if b['id']=='w92332103':
        # The actual footprint is L-shaped. Two authored hip volumes retain the
        # courtyard instead of stretching one rectangular roof across the gap.
        roof(K,b['id']+'_RoofWest',Frame((-16.4,-31.3),(.615,-.788)),20.8,5.6,eave,1.8,roofmat,mat,hipped=True,seams=True)
        roof(K,b['id']+'_RoofSouth',Frame((-10.6,-23.6),(.84,-.543)),14.6,10.1,eave,2.0,roofmat,mat,hipped=True,seams=True)
    else:
        roof(K,b['id']+'_Roof',fr,b['major_length_m'],b['minor_width_m'],eave,b['roof_rise_m'],roofmat,mat)
    K.box(b['id']+'_Chimney',M['brick'],fr.p(b['major_length_m']*.22,0,eave+b['roof_rise_m']+.45),(.7,.8,1.15),fr.u)
    if b['id']=='w92332122':
        # Street-side architectural bands, sign and clock are key identity cues.
        L=b['major_length_m'];W=b['minor_width_m'];normal=(-fr.v[0],-fr.v[1])
        for h in [1.8,4.5,7.7,9.6]:K.box(b['id']+'_Bands',M['rust'],fr.p(0,-W/2-.15,base+h),(L+.12,.18,.2),fr.u)
        edges=[(a,bb) for a,bb in zip(poly,poly[1:]+poly[:1]) if math.dist(a,bb)>25]
        a,bb=max(edges,key=lambda e:Vector((-(e[0][1]+e[1][1])/2,-(e[0][0]+e[1][0])/2)).dot(Vector((-(e[1][1]-e[0][1]),-(e[1][0]-e[0][0]))).normalized()))
        direction=Vector((bb[0]-a[0],-(bb[1]-a[1]))).normalized();front_normal=(direction.y,-direction.x)
        sx=a[0]+(bb[0]-a[0])*.32+front_normal[0]*.35;sy=-a[1]-(bb[1]-a[1])*.32+front_normal[1]*.35
        text('MUSIKSKOLAN',b['id']+'_Sign',(sx,sy,base+1.98),front_normal,.39,M['rust'])
        cp=Vector(fr.p(0,-W/2-.28,base+8.1));K.beam(b['id']+'_Clock',M['white'],cp,cp+Vector((*normal,0))*.025,.42,48)
        for dx,dy in [(.02,.27),(.22,-.08)]:
            end=cp+Vector((fr.u[0]*dx,fr.u[1]*dx,dy));cp2=cp+Vector((*normal,0))*.04;end+=Vector((*normal,0))*.04;K.beam(b['id']+'_ClockHands',M['black'],cp2,end,.018,6)
    if b['id']=='w92332103':
        # Actual Corpus lettering, kept independent from the generic facade generator.
        edge=max(zip(poly,poly[1:]+poly[:1]),key=lambda e:((e[0][1]+e[1][1])/2 if math.dist(*e)>4 else -1000))
        a,bb=edge;d=Vector((bb[0]-a[0],-(bb[1]-a[1])));d.normalize();out=(d.y,-d.x);cx=(a[0]+bb[0])/2;cy=-(a[1]+bb[1])/2
        K.box('Corpus_signboard',M['black'],(cx+out[0]*.24,cy+out[1]*.24,base+3.05),(5.2,.15,.58),(d.x,d.y));text('CORPUS PIZZA','Corpus_letters',(cx+out[0]*.33,cy+out[1]*.33,base+3.05),out,.36,M['white'])

# Authored street furniture. Positions are observed/illustrative, not generated from a random scatter.
factory=json.loads((HERE/'reference/industrial_backdrop.json').read_text())
geo=factory['geography'];facts=factory['authored_volume_estimate'];poly=ensure_ccw(geo['footprint_xz']);base=facts['base_height_raw_m']-OFFSET;hh=facts['wall_height_m'];name='Stora_Gotafors'
K.shell(name+'_Brick',M['brick'],poly,base,hh)
fr=Frame(geo['centroid_xz'],geo['major_axis_xz']);L=geo['major_length_m'];W=geo['minor_width_m']
K.box(name+'_Roof',M['metal'],fr.p(0,0,base+hh+.12),(L+.15,W+.15,.25),fr.u)
for a,b in zip(poly,poly[1:]+poly[:1]):
    d=Vector((b[0]-a[0],-(b[1]-a[1])));length=d.length;u=(d.x/length,d.y/length);out=(u[1],-u[0]);at=lambda s,o,h:(a[0]+u[0]*s+out[0]*o,-a[1]+u[1]*s+out[1]*o,h)
    if length>40:
        for row in range(7):
            for bay in range(17):
                window(K,name,at((bay+.5)*length/17,.10,base+.75+row*3.25),u,out,1.55,1.65,M['white'],M['glass'],M['white'])
    elif (a[0]+b[0])/2<120:
        for bay in range(4):window(K,name,at((bay+.5)*length/4,.11,base+hh-2.55),u,out,3.15,1.95,M['white'],M['glass'],M['white'])
        text('STORA GÖTAFORS',name+'_Letters',at(length/2,.25,base+hh-4.0),out,.76,M['black'])
        K.box(name+'_Band',M['brick'],at(length/2,.12,base+hh-5.2),(length,.18,.2),u)
    for s in [0,length]:
        K.box(name+'_Pilasters',M['brick'],at(s,.14,base+hh/2),(.7,.4,hh+.65),u)
        K.box(name+'_PilasterCaps',M['brick'],at(s,.2,base+hh+.35),(1.0,.7,.2),u)

def bench(x,z,yaw=0):
    h=walk_height(x,z)+.03;u=(math.cos(yaw),math.sin(yaw));v=(-u[1],u[0]);fr=Frame((x,z),(u[0],-u[1]))
    for j in range(5):K.box('Bench_slats',M['wood'],fr.p(0,(j-2)*.085,h+.44),(1.8,.07,.05),u)
    for j in range(3):K.box('Bench_slats',M['wood'],fr.p(0,.22,h+.68+j*.12),(1.8,.045,.095),u)
    for a in [-.65,.65]:
        for b in [-.17,.17]:K.beam('Bench_frame',M['iron'],fr.p(a,b,h),fr.p(a,b,h+.46),.035)
        K.beam('Bench_frame',M['iron'],fr.p(a,.22,h+.3),fr.p(a,.22,h+1),.025)
    K.box('COL_Benches',M['collision'],fr.p(0,0,h+.24),(1.8,.5,.48),u)
for x,z,yaw in [(-27,-5,-.8),(-34,5,-.8),(1,38,.2),(42,33,.25)]:bench(x,z,yaw)

def lamp(x,z,height=4.6):
    h=walk_height(x,z)+.03;K.beam('Streetlamps',M['iron'],(x,-z,h),(x,-z,h+height),.055,10);K.beam('Streetlamps',M['iron'],(x,-z,h+height),(x+.55,-z,h+height-.1),.035);K.box('Streetlamps',M['iron'],(x+.55,-z,h+height-.18),(.48,.35,.12));K.box('Streetlamp_glass',M['white'],(x+.55,-z,h+height-.25),(.35,.25,.035))
    K.box('COL_Lampposts',M['collision'],(x,-z,h+height/2),(.13,.13,height))
for x,z in [(-24,-1),(-33,11),(-8,13),(-2,37),(24,34),(48,27),(18,-25)]:lamp(x,z)
for x,z in [(-26,3),(-29,7),(-21,-4),(-20,-8),(-17,-12)]:
    h=ground(x,z);K.box('Bollards',M['curb'],(x,-z,h+.4),(.32,.32,.68))
for planter in SITE.get('planters',[]):
    poly=planter['polygon_xz']
    for a,b in zip(poly,poly[1:]+poly[:1]):
        length=math.dist(a,b);u=((b[0]-a[0])/length,-(b[1]-a[1])/length)
        h=(ground(*a)+ground(*b))/2+.13
        K.box('Planter_granite',M['curb'],((a[0]+b[0])/2,-(a[1]+b[1])/2,h),(length,.18,.18),u)
    cx=sum(p[0] for p in poly)/len(poly);cz=sum(p[1] for p in poly)/len(poly)
    for i in range(26):
        angle=i*2.39996;radius=.3+1.8*math.sqrt((i+.5)/26);x=cx+math.cos(angle)*radius;z=cz+math.sin(angle)*radius;h=ground(x,z)+.07
        for k in range(3):
            a=angle+k*math.tau/3;dx=math.cos(a)*.16;dy=math.sin(a)*.16;height=random.uniform(.2,.37)
            K.face('Low_planting',M['leaves'],[(x-dx,-z-dy,h),(x+dx,-z+dy,h),(x+dx*.3,-z+dy*.3,h+height),(x-dx*.3,-z-dy*.3,h+height)],[(.515,.395),(.851,.395),(.851,.97),(.515,.97)])
# Pedestrian crossing paint, faded and slightly warm.
fr=Frame((-24,17),(.69,-.724))
for i in range(7):K.box('Crossing_paint',M['white'],fr.p((i-3)*.85,0,walk_height(*fr.xz((i-3)*.85,0))+.008),(.42,2.8,.009),fr.u)

# Subtle ripples/whitewater are geometry; runtime can animate the WaterFlow material.
for i in range(75):
    a=line[min(len(line)-2,i//7)];b=line[min(len(line)-1,i//7+1)];t=random.random();x=a[0]*(1-t)+b[0]*t;z=a[1]*(1-t)+b[1]*t
    # Find exported water surface triangle closest to this point, avoiding unsupported liquid simulation.
    closest=min(SITE['meshes']['water'],key=lambda tri:sum((p[0]-x)**2+(p[2]-z)**2 for p in tri))
    h=sum(p[1] for p in closest)/3+.04
    d=Vector((b[0]-a[0],-(b[1]-a[1]))).normalized();normal=(-d.y,d.x);side=random.uniform(-2.8,2.8)
    x+=normal[0]*side;yy=-z+normal[1]*side
    if i%3==0:K.box('Whitewater',M['foam'],(x,yy,h),(random.uniform(.3,1.2),.045,.01),(d.x,d.y))

objects=K.finish()
for obj in objects:
    if obj.name.startswith('COL_'):obj.hide_render=True;obj.display_type='WIRE'
    elif any(k in obj.name for k in ['Terrain','Water']):
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001);bm.to_mesh(obj.data);bm.free()
        for poly in obj.data.polygons:poly.use_smooth=True

# Young street trees plus woodland behind the houses. Explicit positions are editable scene content.
for idx,(x,z,scale) in enumerate([(-24,-8,.92),(-30,2,1.0),(-37,10,1.02),(-8,-40,.72),(8,-45,.8),(45,-4,.9),(-63,-17,1.4),(-67,-30,1.6),(-56,-43,1.5),(-48,-56,1.3),(-71,15,1.4),(60,48,1.2),(50,55,1.2)]):
    place_tree(['Broadleaf_A','Broadleaf_B','Broadleaf_C'][idx%3],location=(x,-z,ground(x,z)),scale=scale,yaw=idx*1.7)
for idx in range(26):
    x=random.uniform(-115,-73);z=random.uniform(-95,50);place_tree(['Broadleaf_A','Broadleaf_B','Broadleaf_C'][idx%3],location=(x,-z,ground(x,z)),scale=random.uniform(1.3,2.0),yaw=idx*2.3)
for idx in range(16):
    x=random.uniform(-63,-34);z=random.uniform(-80,-34);place_tree(['Broadleaf_A','Broadleaf_B','Broadleaf_C'][idx%3],location=(x,-z,ground(x,z)),scale=random.uniform(1.1,1.7),yaw=idx*1.8)

# Reproducible evidence cameras; eye-height cameras are also the runtime named views.
views=[{'id':'krakan','name':'Kråkans krog','position':[8.0,walk_height(8,48)+1.7,48.0],'target':[11,2.2,30]},
{'id':'torget','name':'Gamla torget','position':[-8.5,walk_height(-8.5,8)+1.7,8],'target':[-40,4.5,-8]},
{'id':'corpus','name':'Corpus','position':[3,walk_height(3,-7)+1.7,-7],'target':[-15,2.6,-25]},
{'id':'forsen','name':'Forsen från Forsebron','position':[-8,walk_height(-8,30)+1.7,30],'target':[45,-2.0,12]},
{'id':'gatan','name':'Längs Götaforsliden','position':[-1,walk_height(-1,43)+1.7,43],'target':[65,6.5,23]},
{'id':'oversikt','name':'Överblick','position':[68,44,90],'target':[-6,2,0],'free_flight':True}]
for view in views:
    lens=28 if view['id']=='krakan' else 32 if view['id']!='oversikt' else 42
    view['fov_degrees']=math.degrees(2*math.atan((36/1.6)/(2*lens)))
meta={'title':'Gamla torget — Kvarnbyn','spawn':{'position':[8.0,walk_height(8,48),48.0],'target':views[0]['target'],'snap_to_ground':True},'views':views,'bounds':{'min':[-64,-12,-64],'max':[64,40,64]},'attribution':['Kartdata © OpenStreetMap-bidragsgivare (ODbL)','Höjddata: Lantmäteriet (CC0)','Material, lövatlas och himmel: Poly Haven (CC0)','Modeller: projektet Försvara Kvarnbyn'],'notes':['Visuellt innehållsprov, ingen färdig spelbana.','Fasader observerade i Google Street View maj 2026 samt Wikimedia-foton.','Höjder uppskattade, ingen laserpunktmolnstolkning ännu.']}
(OUT/'world_meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
for view in views:
    data=bpy.data.cameras.new(view['id']);obj=bpy.data.objects.new('View_'+view['id'],data);bpy.context.collection.objects.link(obj)
    px,py,pz=view['position'];tx,ty,tz=view['target'];obj.location=(px,-pz,py);obj.rotation_euler=(Vector((tx,-tz,ty))-obj.location).to_track_quat('-Z','Y').to_euler();data.lens=28 if view['id']=='krakan' else 32 if view['id']!='oversikt' else 42;data.clip_end=600
bpy.context.scene.camera=bpy.data.objects['View_krakan']

# Physical daylight, shared sun direction and neutral exposure. No photographic background.
world=bpy.data.worlds.new('Swedish_daylight');bpy.context.scene.world=world;world.use_nodes=True
nodes=world.node_tree.nodes;sky=nodes.new('ShaderNodeTexSky');sky.sky_type='NISHITA';sky.sun_elevation=math.radians(36);sky.sun_rotation=math.radians(220);sky.sun_disc=False;sky.air_density=1.1;sky.dust_density=.6;world.node_tree.links.new(sky.outputs['Color'],nodes['Background'].inputs['Color']);nodes['Background'].inputs['Strength'].default_value=.35
# Photographic clouds/reflections; diffuse fill remains the procedural daylight.
# This avoids adding the HDR panorama's photographed sun to the directional sun.
environment=nodes.new('ShaderNodeTexEnvironment');environment.image=bpy.data.images.load(str(HERE/'assets-src/sky/kloofendal_48d_partly_cloudy_puresky_1k.hdr'))
photo=nodes.new('ShaderNodeBackground');photo.inputs['Strength'].default_value=.35;world.node_tree.links.new(environment.outputs['Color'],photo.inputs['Color'])
path=nodes.new('ShaderNodeLightPath');visible=nodes.new('ShaderNodeMath');visible.operation='MAXIMUM';world.node_tree.links.new(path.outputs['Is Camera Ray'],visible.inputs[0]);world.node_tree.links.new(path.outputs['Is Glossy Ray'],visible.inputs[1]);mix=nodes.new('ShaderNodeMixShader');world.node_tree.links.new(visible.outputs[0],mix.inputs[0]);world.node_tree.links.new(nodes['Background'].outputs[0],mix.inputs[1]);world.node_tree.links.new(photo.outputs[0],mix.inputs[2]);world.node_tree.links.new(mix.outputs[0],nodes['World Output'].inputs['Surface'])
sun_data=bpy.data.lights.new('Sun','SUN');sun_data.energy=2.5;sun_data.angle=math.radians(2.5);sun=bpy.data.objects.new('Sun',sun_data);bpy.context.collection.objects.link(sun);sun.rotation_euler=(math.radians(35),math.radians(-25),math.radians(-35))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24 if '--quick' in args else 64;scene.cycles.use_denoising=True;scene.cycles.max_bounces=5;scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=75 if '--quick' in args else 100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='METAL'
    scene.cycles.device='GPU'
except Exception as exc:print('Cycles device:',exc)
# Save source with relative paths; keep linked textures separately to avoid duplication.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'torget.blend'),compress=True)
bpy.ops.file.make_paths_relative()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'torget.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'world_raw.glb'),export_format='GLB',export_cameras=False,export_lights=False,export_apply=True,export_yup=True,export_extras=True,export_image_format='AUTO',export_materials='EXPORT')
report={'objects':len(bpy.data.objects),'meshes':len(bpy.data.meshes),'triangles':sum(sum(len(p.vertices)-2 for p in obj.data.polygons) for obj in bpy.data.objects if obj.type=='MESH' and not obj.name.startswith('COL_')),'raw_glb_bytes':(OUT/'world_raw.glb').stat().st_size,'blender_version':bpy.app.version_string,'cameras':views}
(EVIDENCE/'scene_metrics.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));print('SCENE_METRICS',json.dumps(report))
if '--render' in args:
    for view in views:
        if '--quick' in args and view['id'] not in ['krakan','torget']:continue
        scene.camera=bpy.data.objects['View_'+view['id']];scene.render.filepath=str(EVIDENCE/('blender_'+view['id']+'.png'));bpy.ops.render.render(write_still=True)

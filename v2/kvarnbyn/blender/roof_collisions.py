"""Physics follows the actual authored roof faces, including eaves and hips.

The shared Torget model kit is frozen. Complete collisions in this world's Kit
before finish(), without substituting invisible boxes for sloping roofs.
"""
import math
from mathutils import Vector


def complete(K, material):
    def key(points):
        return tuple(sorted(tuple(round(float(c),5) for c in p) for p in points))
    present={key([batch['verts'][i] for i in face])
             for (name,_),batch in K.batches.items() if name.startswith('COL_')
             for face in batch['faces']}
    added=0;covered=0;candidates=[]
    for (name,_),batch in list(K.batches.items()):
        if name.startswith(('COL_','Far')) or not any(part in name.lower() for part in ('roof','dormer','chimney')):continue
        for face in batch['faces']:
            points=[Vector(batch['verts'][i]) for i in face]
            if len(points)<3:continue
            normal=(points[1]-points[0]).cross(points[2]-points[0])
            if normal.length<1e-9 or normal.normalized().z<=.02:continue
            normal.normalize()
            if key(points) not in present:
                K.face('COL_WalkableRoof_'+name,material,points)
                present.add(key(points));added+=1
            covered+=1
            if normal.z<math.cos(math.radians(54)):continue
            centre=sum(points,Vector())/len(points)
            # Stay well inside a real face when placing the 0.35 m capsule.
            edges=[(a,b) for a,b in zip(points,points[1:]+points[:1])]
            edge=max(edges,key=lambda e:(e[1]-e[0]).length_squared)
            direction=edge[1]-edge[0];direction.z=0
            if direction.length<3:continue
            direction.normalize()
            def inside(q):
                signs=[]
                for a,b in edges:
                    d=b-a;v=q-a;cross=d.x*v.y-d.y*v.x
                    if abs(cross)/max(.001,math.hypot(d.x,d.y))<.65:return False
                    signs.append(cross>0)
                return all(signs) or not any(signs)
            probes=[centre+direction*t for t in (-1.2,0,1.2)]
            if not all(inside(q) for q in probes):continue
            path=[]
            for q in probes:
                q.z=centre.z-(normal.x*(q.x-centre.x)+normal.y*(q.y-centre.y))/normal.z
                path.append([round(q.x,4),round(q.z,4),round(-q.y,4)])
            family='clipped' if name.startswith('Footprint_') or name.startswith('M31') else 'standard' if name.startswith('H') else 'authored'
            candidates.append(dict(id=name,kind=family,points=path,normal=[normal.x,normal.z,-normal.y]))
    checks=[];used=set()
    for family in ('standard','authored','clipped'):
        group=[c for c in candidates if c['kind']==family]
        for i in range(min(5,len(group))):
            candidate=group[int(i*len(group)/min(5,len(group)))]
            if candidate['id'] not in used:
                checks.append(candidate);used.add(candidate['id'])
    return dict(added_faces=added,covered_visible_faces=covered,checks=checks)

"""Render the connected Stalleliden study. All walking collision comes from site ramps.

Metric dimensions are estimated; source and uncertainty live in reference/stalliden.
Technical edge fills must not be described as visually surveyed retaining walls.
"""
import math
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from modelkit import color
from blender_materials import solid_material


def build(K, M, meta, ground):
    railmat = solid_material('Stalleliden_galvanized_rail', color('#8c9391'), .62, .55)
    for flight in meta.get('flights', []):
        for tread in flight['treads']:
            top, bottom = tread['top_y'], tread['bottom_y']
            for contour in tread['contours']:
                if contour['holes']:
                    raise ValueError('Stalleliden treads with holes need constrained triangulation')
                q = contour['outer']; vv = [Vector((x, -z, top)) for x, z in q]
                for tri in tessellate_polygon([vv]):
                    face = [vv[i] for i in tri] if isinstance(tri[0], int) else list(tri)
                    if (face[1]-face[0]).cross(face[2]-face[0]).z < 0: face.reverse()
                    K.face('Stalleliden_steps', M['concrete'], face)
                for (xa, za), (xb, zb) in zip(q, q[1:]+q[:1]):
                    face = [(xa,-za,bottom),(xb,-zb,bottom),(xb,-zb,top),(xa,-za,top)]
                    K.face('Stalleliden_risers', M['concrete'], face)
                    K.face('Stalleliden_risers', M['concrete'], face[::-1])
    for rail in meta.get('rails', []):
        points = rail['points']; h = rail['height_m']; w = rail['collider_width_m']
        for a, b in zip(points, points[1:]):
            pa, pb = (a[0],-a[2],a[1]), (b[0],-b[2],b[1])
            K.beam('Stalleliden_rail', railmat, (pa[0],pa[1],pa[2]+h), (pb[0],pb[1],pb[2]+h), rail['radius_m'], 8)
            # A sloped, closed thin prism follows the rail without staircasing
            # its collision. It stops the actual capsule along the fall side.
            dx,dz=b[0]-a[0],b[2]-a[2];L=math.hypot(dx,dz)
            if L < 1e-6: continue
            ox,oz=-dz/L*w/2,dx/L*w/2
            v=[(a[0]+s*ox,-a[2]-s*oz,a[1]+y) for y in (-.08,h+.04) for s in (-1,1)]
            v += [(b[0]+s*ox,-b[2]-s*oz,b[1]+y) for y in (-.08,h+.04) for s in (-1,1)]
            for ids in ((0,4,6,2),(1,3,7,5),(2,6,7,3),(0,1,5,4),(0,2,3,1),(4,5,7,6)):
                K.face('COL_Stalleliden_rail',M['collision'],[v[i] for i in ids])
        for a in points[::4]+points[-1:]:
            K.beam('Stalleliden_rail',railmat,(a[0],-a[2],a[1]),(a[0],-a[2],a[1]+h+.02),.032,8)
    for edge in meta.get('supports', []):
        a,b=edge['a'],edge['b']
        ba=min(edge['bottom_a_y'],ground(*a)-.2);bb=min(edge['bottom_b_y'],ground(*b)-.2)
        face=[(a[0],-a[1],ba),(b[0],-b[1],bb),(b[0],-b[1],edge['top_b_y']),(a[0],-a[1],edge['top_a_y'])]
        K.face('Stalleliden_ground_edges',M['rock'],face)
        K.face('Stalleliden_ground_edges',M['rock'],face[::-1])
        K.face('COL_Stalleliden_ground_edges',M['collision'],face)


def garden(K,M,meta):
    timber=solid_material('Stalleliden_weathered_grey_plank',color('#777b72'),.9)
    for edge in meta.get('supports',[]):
        a,b=edge['a'],edge['b']
        face=[(a[0],-a[1],edge['bottom_a_y']),(b[0],-b[1],edge['bottom_b_y']),
              (b[0],-b[1],edge['top_b_y']),(a[0],-a[1],edge['top_a_y'])]
        K.face('Stalleliden_plot_ground_edges',M['rock'],face)
        K.face('Stalleliden_plot_ground_edges',M['rock'],face[::-1])
        K.face('COL_Stalleliden_plot_ground_edges',M['collision'],face)
    for wall in meta.get('walls',[]):
        a,b=wall['a'],wall['b'];L=math.dist(a,b);u=((b[0]-a[0])/L,-(b[1]-a[1])/L)
        # Short segments follow the terrain rather than one horizontal box.
        for i in range(math.ceil(L/.4)):
            ta=i/math.ceil(L/.4);tb=(i+1)/math.ceil(L/.4)
            p=[a[j]+ta*(b[j]-a[j]) for j in (0,1)];q=[a[j]+tb*(b[j]-a[j]) for j in (0,1)]
            lo=wall['bottom_a_y']+ta*(wall['bottom_b_y']-wall['bottom_a_y'])
            hi=wall['top_a_y']+tb*(wall['top_b_y']-wall['top_a_y'])
            cen=((p[0]+q[0])/2,-(p[1]+q[1])/2,(lo+hi)/2)
            for name,mat in [('Stalleliden_observed_wall',M['rock']),('COL_Stalleliden_observed_wall',M['collision'])]:
                K.box(name,mat,cen,(math.dist(p,q)+.02,.38,hi-lo),u)
    for fence in meta.get('fences',[]):
        a,b=fence['a'],fence['b'];L=math.dist(a,b);u=((b[0]-a[0])/L,-(b[1]-a[1])/L)
        for i in range(math.ceil(L/.14)):
            t=(i+.5)/math.ceil(L/.14);x=a[0]+t*(b[0]-a[0]);z=a[1]+t*(b[1]-a[1])
            y=fence['base_a_y']+t*(fence['base_b_y']-fence['base_a_y']);h=fence['height_m']
            for name,mat in [('Stalleliden_plank',timber),('COL_Stalleliden_plank',M['collision'])]:
                K.box(name,mat,(x,-z,y+h/2),(.13,.06,h),u)

"""Actual-floor checks for the three reviewed street walks, in both directions."""
import math
import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.ops import nearest_points
from road_layout import width_at


def make_checks(city, height_fn, offset):
    points, paths, blockers = [], [], []
    for road in city['roads']:
        if not road.get('width_profile_m'): continue
        line = LineString(road['line_xz'])
        width = min(p[1] for p in road['width_profile_m'])
        span = [p[0] for p in road['width_profile_m'] if p[1] == width]
        ss = np.linspace(min(span)+1, max(span)-1, math.ceil(max(span)-min(span))+1)
        coords = np.array([line.interpolate(float(s)).coords[0] for s in ss])
        y = height_fn(coords[:,0], coords[:,1])+.03-offset
        walk = [[round(float(x),3),round(float(h),3),round(float(z),3)] for (x,z),h in zip(coords,y)]
        for i in [0,len(walk)//2,len(walk)-1]:
            points.append(dict(id=road['id']+'_'+str(i),position=walk[i],tolerance_m=.16))
        for suffix, route in [('up',walk),('down',walk[::-1])]:
            paths.append(dict(id=road['id']+'_'+suffix,points=route,speed_m_s=3.0,tolerance_m=.2))
        # A horizontal ray must stop on the real street-side wall (not a test box).
        middle = line.interpolate(sum(span)/2)
        building = min(city['buildings'],key=lambda b:Polygon(b.get('build_footprint_xz',b['footprint_xz'])).distance(middle))
        polygon = Polygon(building.get('build_footprint_xz',building['footprint_xz']))
        target = np.array(polygon.representative_point().coords[0])
        h = float(height_fn(np.array([middle.x]),np.array([middle.y]))[0])+.03-offset
        blockers.append(dict(id=road['id']+'_house_wall',**{'from':[middle.x,h,middle.y],'to':[float(target[0]),h,float(target[1])]},blocked=True,height_m=1.25))
    return dict(points=points,paths=paths,blockers=blockers)

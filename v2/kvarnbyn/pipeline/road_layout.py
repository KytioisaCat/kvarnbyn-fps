"""Reviewed local road widths. Keep one corridor for mesh, house safety and map.

Profiles follow the source OSM polyline. Shared junction IDs stay connected.
Width transitions are linear, sampled at <=0.5 m, with exact profile breakpoints.
"""
import math
import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union


def width_at(road, distance):
    profile = road.get('width_profile_m')
    if not profile:
        return np.full_like(np.asarray(distance, dtype=float), float(road['width_m']))
    return np.interp(distance, [p[0] for p in profile], [p[1] for p in profile])


def corridor(road, extra=0.0, source_width=False):
    line = LineString(road.get('source_line_xz',road['line_xz']) if source_width else road['line_xz'])
    if source_width or not road.get('width_profile_m'):
        return line.buffer(road['width_m']/2+extra, cap_style=2, join_style=2)
    c = np.asarray(line.coords, float)
    lengths = np.hypot(*np.diff(c, axis=0).T)
    distance = 0.0
    parts = []
    knots = [float(p[0]) for p in road['width_profile_m']]
    for a, b, length in zip(c, c[1:], lengths):
        if length < 1e-6: continue
        normal = np.array([-(b-a)[1], (b-a)[0]]) / length
        samples = np.unique(np.r_[np.linspace(distance, distance+length, math.ceil(length/.5)+1),
                                  [d for d in knots if distance < d < distance+length]])
        for sa, sb in zip(samples, samples[1:]):
            pa = a+(b-a)*(sa-distance)/length
            pb = a+(b-a)*(sb-distance)/length
            ra, rb = width_at(road, np.array([sa, sb]))/2+extra
            parts.append(Polygon([pa+normal*ra, pa-normal*ra, pb-normal*rb, pb+normal*rb]))
        distance += length
    # Round joins fill only the turn wedges; width never jumps at an OSM node.
    distance = 0.0
    for point, length in zip(c[1:-1], lengths):
        distance += length
        from shapely.geometry import Point
        parts.append(Point(point).buffer(float(width_at(road, distance))/2+extra, quad_segs=8))
    return unary_union(parts).buffer(0)


def apply_reviews(roads, reviews):
    indexed = {r['id']: r for r in roads}
    for review in reviews:
        road = indexed[review['id']]
        line = LineString(road['line_xz'])
        from shapely.geometry import Point
        centre = line.project(Point(review['anchor_xz']))
        start = max(0., centre-review['before_m'])
        end = min(line.length, centre+review['after_m'])
        fade = review['transition_m']
        knots = [(0., road['width_m']), (max(0., start-fade), road['width_m']),
                 (start, review['width_estimate_m']), (end, review['width_estimate_m']),
                 (min(line.length, end+fade), road['width_m']), (line.length, road['width_m'])]
        # At a route endpoint the reviewed width wins; no zero-length transition.
        unique = {}
        for s, w in knots: unique[round(s, 4)] = w
        if start == 0.: unique[0.] = review['width_estimate_m']
        if end == line.length: unique[round(line.length, 4)] = review['width_estimate_m']
        road['width_profile_m'] = sorted([s, w] for s, w in unique.items())
        road['width_source'] = 'street_view_visual_estimate_not_survey'
        road['review_id'] = review['review_id']
        if review.get('surface'): road['reviewed_surface'] = review['surface']
        road['reviewed_edge'] = review.get('edge', 'sett')

    # Move reviewed centre lines locally, tapering to their original endpoints.
    # A shared OSM node moves once for every connected way, including driveways.
    by_id = {entry['id']: entry for entry in reviews}
    offsets = {}
    for road in roads:
        entry = by_id.get(road['id'])
        if not entry or not entry.get('centre_offset_xz'): continue
        points = np.asarray(road['line_xz'], float)
        distances = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        low = min(p[1] for p in road['width_profile_m'])
        plateau = [p[0] for p in road['width_profile_m'] if p[1] == low]
        start, end = plateau[0], plateau[-1]
        def weight(d): return min(1., max(0., (d-start+entry['transition_m'])/entry['transition_m']), max(0., (end+entry['transition_m']-d)/entry['transition_m']))
        for node, distance in zip(road['node_ids'], distances):
            delta = np.asarray(entry['centre_offset_xz'])*weight(distance)
            if np.linalg.norm(delta) > 1e-6: offsets[node] = delta
    for road in roads:
        entry = by_id.get(road['id'])
        direct = entry is not None and bool(entry.get('centre_offset_xz'))
        if not direct and not any(n in offsets for n in road['node_ids']): continue
        original = np.asarray(road['line_xz'], float)
        ids = list(road['node_ids'])
        distances = np.r_[0., np.cumsum(np.linalg.norm(np.diff(original, axis=0), axis=1))]
        if direct:
            profile = road['width_profile_m']
            low = min(p[1] for p in profile)
            plateau = [p[0] for p in profile if p[1] == low]
            start, end = plateau[0], plateau[-1]
            samples = sorted(set(distances.tolist()+[p[0] for p in profile]))
            line = LineString(original)
            positions, node_ids = [], []
            for distance in samples:
                point = np.array(line.interpolate(distance).coords[0])
                weight = min(1., max(0., (distance-start+entry['transition_m'])/entry['transition_m']), max(0., (end+entry['transition_m']-distance)/entry['transition_m']))
                delta = np.asarray(entry['centre_offset_xz'])*weight
                match = np.where(abs(distances-distance)<1e-7)[0]
                node = ids[int(match[0])] if len(match) else None
                if node in offsets: delta = offsets[node]
                positions.append((point+delta).round(3).tolist());node_ids.append(node)
            new_distance = np.r_[0.,np.cumsum(np.linalg.norm(np.diff(positions,axis=0),axis=1))]
            road['width_profile_m'] = [[round(float(np.interp(d,samples,new_distance)),4),w] for d,w in profile]
            road['line_xz'],road['node_ids'] = positions,node_ids
        else:
            road['line_xz'] = [(q+offsets.get(n,np.zeros(2))).round(3).tolist() for q,n in zip(original,ids)]
        road['source_line_xz'] = original.tolist()
        road['source_node_ids'] = ids
        road['layout_source'] = 'street_view_estimated_local_alignment' if direct else 'shared_osm_junction_follows_reviewed_street'

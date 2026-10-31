"""Independent CPU-only invariants for RotenGround; only writes sibling QA artifacts."""
from pathlib import Path
import json
import hashlib
import math
import sys
from datetime import datetime, timezone
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[4]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'v2/kvarnbyn/pipeline'))
from common import ZONE, Y_OFFSET, raw_height

OUT = Path(__file__).resolve().parent
CITY = json.loads((ROOT / 'v2/kvarnbyn/data/city.json').read_text())
SITE = json.loads((ROOT / 'v2/kvarnbyn/data/site.json').read_text())
WORK = box(*ZONE).buffer(30, join_style=2)
REVIEW = box(75, 80, 125, 135)


def context():
    """Reconstruct original site constraints and exact pre-authored height callback."""
    profiles = []
    bridges = []
    for r in CITY['roads']:
        if r['tunnel']:
            continue
        line = LineString(r['line_xz'])
        if not line.intersects(WORK) or line.length < .5:
            continue
        if r['bridge']:
            bridges.append((r, line))
            continue
        n = max(2, int(math.ceil(line.length / 2)) + 1)
        s = np.linspace(0, line.length, n)
        xy = shapely.get_coordinates(shapely.line_interpolate_point(line, s))
        h = raw_height(xy[:, 0], xy[:, 1])
        if n >= 5:
            h = np.convolve(np.pad(h, 2, mode='edge'), np.array([1, 4, 6, 4, 1]) / 16, mode='valid')
        profiles.append((r, line, s, h))
    surfaces = []
    for source in CITY['surfaces']:
        poly = Polygon(source['polygon_xz']).buffer(0)
        if poly.is_empty or not poly.intersects(WORK):
            continue
        q = np.array(poly.exterior.coords)
        ys = raw_height(q[:, 0], q[:, 1])
        a, b, c = np.linalg.lstsq(np.column_stack([q, np.ones(len(q))]), ys, rcond=None)[0]
        limit = .015 if source['kind'] == 'pitch' else .06
        slope = math.hypot(a, b)
        if slope > limit:
            a, b = a * limit / slope, b * limit / slope
            c = float(np.median(ys - a * q[:, 0] - b * q[:, 1]))
        surfaces.append((source, poly, (a, b, c)))
    road_tree = STRtree([p[1] for p in profiles])
    surf_tree = STRtree([p[1] for p in surfaces])

    def base(x, z):
        x, z = np.atleast_1d(np.asarray(x, float)), np.atleast_1d(np.asarray(z, float))
        pts = shapely.points(x, z)
        result = np.full(len(x), np.nan)
        if surfaces:
            point_ids, surface_ids = surf_tree.query(pts, predicate='within')
            for k in np.unique(surface_ids):
                sel = point_ids[surface_ids == k]
                a, b, c = surfaces[k][2]
                result[sel] = a * x[sel] + b * z[sel] + c
        missing = np.isnan(result)
        if missing.any():
            ids = road_tree.nearest(pts[missing])
            original_ids = np.flatnonzero(missing)
            for k in np.unique(ids):
                sel = original_ids[ids == k]
                _, line, s, h = profiles[k]
                result[sel] = np.interp(shapely.line_locate_point(line, pts[sel]), s, h)
        return result

    buildings = unary_union([Polygon(b['footprint_xz']).buffer(0) for b in CITY['buildings']])
    water = unary_union([LineString(w['line_xz']).buffer(w['channel_width_m'] / 2, cap_style=2, join_style=2)
                         for w in CITY['waterways']] + [Polygon(p['polygon_xz']).buffer(0) for p in CITY['water_polygons']]).intersection(WORK)
    bridge_clear = unary_union([line.buffer(r['width_m'] / 2 + .3, cap_style=2) for r, line in bridges])
    cut = buildings.buffer(.05).union(water.buffer(.05)).union(bridge_clear)
    drive = {'primary', 'secondary', 'tertiary', 'residential', 'living_street', 'unclassified', 'service',
             'primary_link', 'secondary_link', 'tertiary_link', 'trunk', 'trunk_link', 'motorway', 'motorway_link'}
    asphalt = unary_union([line.buffer(r['width_m'] / 2, cap_style=2, join_style=2) for r, line, _, _ in profiles if r['kind'] in drive])
    parking = unary_union([p for s, p, _ in surfaces if s['kind'] == 'parking'])
    square = unary_union([p for s, p, _ in surfaces if s['kind'] == 'square'])
    other = unary_union([p for s, p, _ in surfaces if s['kind'] in ('pitch', 'playground')])
    asphalt = asphalt.union(parking).difference(square).difference(other).difference(cut).intersection(WORK)
    foot = unary_union([line.buffer(r['width_m'] / 2, cap_style=1, join_style=1) for r, line, _, _ in profiles if r['kind'] in {'footway', 'pedestrian', 'cycleway', 'path', 'track'}])
    return dict(base=base, forbidden=cut.union(asphalt).union(other),
                streets=asphalt.union(foot).difference(cut).intersection(WORK), buildings=buildings,
                water=water, profiles=profiles)


def local_mesh_triangles():
    triangles = []
    for kind in ('asphalt', 'paving', 'walkway', 'trail', 'soil'):
        for bucket in SITE['meshes'].get(kind, {}).values():
            for tri in bucket:
                q = np.asarray(tri, float)
                if q[:, 0].max() < 70 or q[:, 0].min() > 130 or q[:, 2].max() < 75 or q[:, 2].min() > 140:
                    continue
                m = np.vstack([q[:, 0], q[:, 2], np.ones(3)])
                if abs(np.linalg.det(m)) < 1e-10:
                    continue
                triangles.append((kind, q, np.linalg.inv(m)))
    return triangles


def mesh_at(triangles, x, z):
    result = []
    for kind, q, inverse in triangles:
        if not q[:, 0].min() - 1e-6 <= x <= q[:, 0].max() + 1e-6 or not q[:, 2].min() - 1e-6 <= z <= q[:, 2].max() + 1e-6:
            continue
        barycentric = inverse @ [x, z, 1]
        if barycentric.min() >= -1e-7:
            result.append(dict(kind=kind, raw_m=float(barycentric @ q[:, 1]) + Y_OFFSET))
    return result


def basic_invariants(ground, forbidden, work, ctx):
    """Check externally meaningful invariants without assuming a grading algorithm."""
    problems = []
    stats = {}

    def check(value, message):
        if not value:
            problems.append(message)

    coverage = ground.coverage
    check(coverage.is_valid, 'coverage is invalid')
    check(coverage.difference(work).area < 1e-7, 'coverage escapes work polygon')
    check(coverage.intersection(forbidden).area < 1e-7, 'coverage intersects forbidden geometry')
    surfaces = ground.surfaces
    stats['surface_count'] = len(surfaces)
    stats['coverage_m2'] = coverage.area
    union = unary_union([s['geom'] for s in surfaces])
    check(union.symmetric_difference(coverage).area < 1e-6, 'surface union differs from coverage')
    stats['overlap_m2'] = max(0., sum(s['geom'].area for s in surfaces) - union.area)
    check(stats['overlap_m2'] < 1e-6, 'surface interiors overlap')
    stats['surface_areas_m2'] = {}
    for i, surface in enumerate(surfaces):
        geom = surface['geom']
        check(geom.is_valid and not geom.is_empty and geom.area > 0, f'surface {i} invalid or empty')
        check(callable(surface['height_fn']), f'surface {i} height_fn not callable')
        stats['surface_areas_m2'][surface['kind']] = stats['surface_areas_m2'].get(surface['kind'], 0.) + geom.area
        coords = shapely.get_coordinates(shapely.segmentize(geom.boundary, .25))
        if len(coords):
            values = np.asarray(surface['height_fn'](coords[:, 0], coords[:, 1]))
            check(values.shape == (len(coords),), f'surface {i} height_fn shape mismatch')
            check(np.isfinite(values).all(), f'surface {i} boundary height is not finite')
            check(((values > 25) & (values < 48)).all(), f'surface {i} height is not plausible raw m above sea level')
        point = geom.representative_point()
        expected = float(np.asarray(surface['height_fn']([point.x], [point.y]))[0])
        actual = float(ground.height(np.array([point.x]), np.array([point.y]), np.array([-999.]))[0])
        check(abs(actual - expected) < .002, f'surface {i} differs from public height()')
    gx, gz = np.meshgrid(np.arange(70, 131, .5), np.arange(75, 141, .5))
    x, z = gx.ravel(), gz.ravel()
    original = ctx['base'](x, z)
    untouched = original.copy()
    values = ground.height(x, z, original)
    check(np.array_equal(original, untouched), 'height() mutates caller original height array')
    check(np.asarray(values).shape == original.shape, 'height() changes output array shape')
    check(np.isfinite(values).all(), 'height() produces non-finite grid heights')
    outside = ~shapely.covers(coverage.buffer(1e-5), shapely.points(x, z))
    unchanged_error = float(np.max(np.abs(values[outside] - untouched[outside]))) if outside.any() else 0.
    stats['grid_samples'] = len(x)
    stats['outside_coverage_max_change_m'] = unchanged_error
    check(unchanged_error < 1e-12, 'height() changes values outside coverage')

    def height(x, z):
        x, z = np.atleast_1d(x), np.atleast_1d(z)
        return ground.height(x, z, ctx['base'](x, z))

    trees, shrubs = ground.planting(height, Y_OFFSET)
    stats['tree_count'] = len(trees)
    stats['shrub_count'] = len(shrubs)
    for kind, entries, expected_size in [('tree', trees, 6), ('shrub', shrubs, 7)]:
        for i, item in enumerate(entries):
            check(len(item) == expected_size, f'{kind} {i} list length mismatch')
            check(np.isfinite(np.asarray(item, float)).all(), f'{kind} {i} has non-finite values')
            px, py, pz = item[:3]
            check(coverage.buffer(.002).covers(Point(px, pz)), f'{kind} {i} outside coverage')
            check(not forbidden.buffer(-.001).covers(Point(px, pz)), f'{kind} {i} inside forbidden area')
            check(item[3] > 0 and (kind != 'shrub' or item[4] > 0), f'{kind} {i} non-positive scale')
            expected_y = float(height([px], [pz])[0]) - Y_OFFSET
            check(abs(py - expected_y) < .02, f'{kind} {i} y is not final raw height minus offset')
    try:
        metadata = ground.metadata()
        json.dumps(metadata, allow_nan=False)
    except (TypeError, ValueError) as error:
        problems.append('metadata not finite/JSON serializable: ' + str(error))
        metadata = {}
    stats['metadata'] = metadata
    return dict(passed=not problems, problems=problems, stats=stats)


def main():
    from authored_ground import SurfaceReference
    from roten_ground import RotenGround
    ctx = context()
    tiles = {str((kind, tile)): triangles for kind, buckets in SITE['meshes'].items()
             if kind in ('asphalt', 'paving', 'walkway', 'trail') for tile, triangles in buckets.items()}
    finished = SurfaceReference(tiles, ctx['base'], Y_OFFSET, 0., REVIEW.bounds).height
    args = (CITY, ctx['forbidden'], WORK, raw_height, finished, Y_OFFSET)
    ground = RotenGround(*args)
    report = dict(scope='CPU-only module invariants using real city, raw DTM and finished existing mesh callback',
                  generated_at=datetime.now(timezone.utc).isoformat(),
                  roten_ground_sha256=hashlib.sha256((ROOT / 'v2/kvarnbyn/pipeline/roten_ground.py').read_bytes()).hexdigest(),
                  normal=basic_invariants(ground, ground.forbidden, WORK, ctx))
    ctx['finished'] = finished
    report['normal']['stats']['preserved_road_overlap_m2'] = ground.coverage.intersection(ctx['streets']).area
    report['normal']['stats']['m31_distance_m'] = ground.coverage.distance(Polygon(next(b for b in CITY['buildings'] if b['id'] == 'w92332141')['build_footprint_xz']))
    report['normal']['stats']['structure_counts'] = {name: len(getattr(ground, name)) for name in ('walls', 'fences', 'steps', 'rocks')}
    for name, forbidden, work in [
        ('empty_work', ctx['forbidden'], box(0, 0, 1, 1)),
        ('fully_blocked', WORK, WORK),
        ('clipped_work', ctx['forbidden'], box(100, 115, 109, 125)),
        ('synthetic_cut', ctx['forbidden'].union(box(100, 115, 102, 123)), WORK),
    ]:
        try:
            other = RotenGround(CITY, forbidden, work, raw_height, finished, Y_OFFSET)
            report[name] = basic_invariants(other, other.forbidden, work, ctx)
        except Exception as error:
            report[name] = dict(passed=False, problems=[type(error).__name__ + ': ' + str(error)])
    seams = []
    for i, a in enumerate(ground.surfaces):
        for b in ground.surfaces[i + 1:]:
            shared = a['geom'].boundary.intersection(b['geom'].boundary)
            q = shapely.get_coordinates(shapely.segmentize(shared, .1))
            if len(q) == 0:
                continue
            ha = np.asarray(a['height_fn'](q[:, 0], q[:, 1]))
            hb = np.asarray(b['height_fn'](q[:, 0], q[:, 1]))
            seams.append(dict(a=a['id'], b=b['id'], length_m=shared.length,
                              samples=len(q), maximum_jump_m=float(np.max(np.abs(ha - hb)))))
    report['seams'] = seams
    bad_seams = [s for s in seams if s['maximum_jump_m'] > .02]
    report['seam_continuity'] = dict(passed=not bad_seams, problems=[
        f"{s['a']}/{s['b']}: {s['maximum_jump_m']:.6f} m" for s in bad_seams])
    triangles = local_mesh_triangles()
    existing = unary_union([Polygon(tri[:, [0, 2]]) for _, tri, _ in triangles])
    road_edges = []
    for surface in ground.surfaces:
        p = shapely.get_coordinates(shapely.segmentize(surface['geom'].boundary, .05))
        points = shapely.points(p[:, 0], p[:, 1])
        near = shapely.distance(points, existing) < .002
        if not near.any():
            continue
        p = p[near]
        query = shapely.get_point(shapely.shortest_line(points[near], existing), -1)
        road_y = finished(shapely.get_x(query), shapely.get_y(query))
        new_y = np.asarray(surface['height_fn'](p[:, 0], p[:, 1]))
        error = np.abs(new_y - road_y)
        worst = int(np.argmax(error))
        road_edges.append(dict(id=surface['id'], samples=len(p), maximum_jump_m=float(error[worst]),
                               worst_xz=p[worst].tolist(), new_raw_m=float(new_y[worst]), road_raw_m=float(road_y[worst])))
    report['road_edges_requiring_side_geometry_if_raised'] = road_edges
    path_stats = []
    for path in ground.metadata()['ground_checks']['paths']:
        records = []
        for a, b in zip(path['points'], path['points'][1:]):
            a, b = np.asarray(a), np.asarray(b)
            n = max(2, int(np.ceil(np.linalg.norm((b - a)[[0, 2]]) / .05)) + 1)
            for f in np.linspace(0, 1, n):
                x, y, z = (1 - f) * a + f * b
                inside = ground.coverage.covers(Point(x, z))
                urban = mesh_at(triangles, x, z)
                actual = float(ground.height([x], [z], [np.nan])[0]) if inside else max((t['raw_m'] for t in urban), default=np.nan)
                records.append(dict(x=float(x), z=float(z), expected_raw_m=float(y + Y_OFFSET), actual_raw_m=float(actual),
                                    known_surface=inside or bool(urban)))
        errors = [abs(r['expected_raw_m'] - r['actual_raw_m']) for r in records if r['known_surface']]
        jumps = [abs(a['actual_raw_m'] - b['actual_raw_m']) for a, b in zip(records, records[1:])
                 if a['known_surface'] and b['known_surface']]
        path_stats.append(dict(id=path['id'], samples=len(records), off_new_and_existing=sum(not r['known_surface'] for r in records),
                               maximum_metadata_profile_error_m=max(errors, default=0.), tolerance_m=path.get('tolerance_m', .2),
                               maximum_height_delta_per_5cm_m=max(jumps, default=0.)))
    report['dense_paths'] = path_stats
    bad_paths = [p for p in path_stats if p['off_new_and_existing'] or p['maximum_height_delta_per_5cm_m'] > .23
                 or p['maximum_metadata_profile_error_m'] > p['tolerance_m']]
    report['path_continuity'] = dict(passed=not bad_paths, problems=[
        f"{p['id']}: missing={p['off_new_and_existing']}, max 5cm jump={p['maximum_height_delta_per_5cm_m']:.6f}m, "
        f"metadata error={p['maximum_metadata_profile_error_m']:.6f}m" for p in bad_paths])
    blockers = []
    for spec in ground.metadata()['ground_checks']['blockers']:
        if not spec['blocked']:
            continue
        fence = next(f for f in ground.fences if f['id'] == spec['fence_id'])
        start, end = np.asarray(spec['from']), np.asarray(spec['to'])
        ray = LineString([start[[0, 2]], end[[0, 2]]])
        for p0, p1 in zip(fence['points'], fence['points'][1:]):
            p0, p1 = np.asarray(p0), np.asarray(p1)
            segment = LineString([p0[[0, 2]], p1[[0, 2]]])
            hit = ray.intersection(segment)
            if hit.is_empty:
                continue
            ray_fraction, fence_fraction = ray.project(hit) / ray.length, segment.project(hit) / segment.length
            ray_y = (1 - ray_fraction) * start[1] + ray_fraction * end[1] + spec.get('height_m', 1.)
            fence_base = (1 - fence_fraction) * p0[1] + fence_fraction * p1[1]
            above, below = float(ray_y - fence_base), float(fence_base + fence['height_m'] - ray_y)
            blockers.append(dict(id=spec['id'], fence_id=fence['id'], crossing_xz=[hit.x, hit.y],
                                 ray_above_base_m=above, ray_below_top_m=below, passed=above > 0 and below > 0))
    report['blocker_ray_intersects_fence_height'] = dict(passed=bool(blockers) and all(b['passed'] for b in blockers),
                                                        problems=[] if blockers and all(b['passed'] for b in blockers) else ['No valid fence-height intersection'],
                                                        results=blockers)
    report['passed'] = all(case.get('passed', False) for case in report.values() if isinstance(case, dict) and 'passed' in case)
    (OUT / 'qa-roten-ground-agent.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({name: {k: v for k, v in result.items() if k != 'stats'} for name, result in report.items() if isinstance(result, dict) and 'passed' in result}, ensure_ascii=False, indent=2))
    print('seams', json.dumps(seams, ensure_ascii=False))
    print('normal_stats', json.dumps({k: v for k, v in report['normal']['stats'].items() if k != 'metadata'}, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

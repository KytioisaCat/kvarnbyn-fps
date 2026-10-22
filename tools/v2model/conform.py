"""Terrängkonformering: höjdfältet (1 m) räknas om där det möter vägar. Inne i asfalten läggs
marken strax UNDER vägytan (vägmeshen ritas ovanpå, ingen z-fight), i kantstensbandet exakt på
kantstenens krön, och utanför blendas det mjukt (BLEND m) tillbaka till LiDAR:n. Vägar under
broar är vanliga markvägar — terrängen följer dem, aldrig däcket."""
import numpy as np
import shapely

from .common import EXAG, X0, Z1
from .mesh import KERB_H

UNDER = 0.10     # asfaltens (och kantstensbandets) mark ligger så här långt under vägytan
WALL = 1.5       # större höjdskillnad mellan vägkant och LiDAR utanför vägen = stödmur/terrass: blenda inte
BLEND = 6.0      # m mjuk övergång utanför kantstenen


def conform(model, ground, log=print):
    raw = ground.raw.copy()
    kerb = model.kerb_outer
    minx, minz, maxx, maxz = kerb.bounds
    r0, c0 = ground.cell_of(minx - BLEND - 1, minz - BLEND - 1)
    r1, c1 = ground.cell_of(maxx + BLEND + 1, maxz + BLEND + 1)
    r0, r1 = max(0, int(r0)), min(ground.h - 1, int(r1))
    c0, c1 = max(0, int(c0)), min(ground.w - 1, int(c1))
    rr, cc = np.mgrid[r0:r1 + 1, c0:c1 + 1]
    xs = X0 + cc / ground.sx; zs = Z1 + rr / ground.sz
    X = xs.ravel(); Z = zs.ravel()
    in_road = shapely.contains_xy(model.road_union, X, Z)
    in_kerb = shapely.contains_xy(kerb, X, Z) & ~in_road
    dist = shapely.distance(kerb, shapely.points(X, Z))
    in_blend = (~in_road) & (~in_kerb) & (dist > 0) & (dist <= BLEND)
    touch = in_road | in_kerb | in_blend
    idx = np.nonzero(touch)[0]
    t = model.height_at(X[idx], Z[idx], 'ground')          # spelhöjd på vägytan
    new = raw.ravel().copy() if False else None
    sub = raw[r0:r1 + 1, c0:c1 + 1].ravel().copy()
    old = sub[idx].copy()
    tgt = np.where(in_road[idx], (t - UNDER) / EXAG, np.where(in_kerb[idx], (t - 0.25) / EXAG, (t + KERB_H) / EXAG))
    w = np.where(in_blend[idx], np.clip(dist[idx] / BLEND, 0, 1), 0.0)
    w = w * w * (3 - 2 * w)                                   # smoothstep
    # utanför asfalten: en skillnad > WALL mellan målet och LiDAR:n är en stödmur/terrass —
    # då lämnas terrängen (annars dras den upp till en utsmetad "klippa")
    outside = (~in_road[idx]) & (~in_kerb[idx]) & (dist[idx] > 1.0)   # första metern utanför kantstenen följer den
    wall = outside & (np.abs(tgt - old) * EXAG > WALL)
    w = np.where(wall, 1.0, w)
    sub[idx] = tgt * (1 - w) + old * w
    nwall = int(wall.sum())
    raw[r0:r1 + 1, c0:c1 + 1] = sub.reshape(rr.shape)
    changed = np.abs(sub[idx] - old) * EXAG
    log(f'  konformering: {in_road.sum()} celler asfalt, {in_kerb.sum()} kantsten, {in_blend.sum()} blend; '
        f'ändring p50 {np.percentile(changed, 50):.2f} p90 {np.percentile(changed, 90):.2f} max {changed.max():.2f} m')
    log(f'  {nwall} celler lämnade orörda vid stödmurs-höga skillnader (> {WALL} m)')
    stats = {'wall_cells': nwall, 'cells_road': int(in_road.sum()), 'cells_kerb': int(in_kerb.sum()), 'cells_blend': int(in_blend.sum()),
             'change_p50': float(np.percentile(changed, 50)), 'change_p90': float(np.percentile(changed, 90)),
             'change_max': float(changed.max())}
    return raw, stats

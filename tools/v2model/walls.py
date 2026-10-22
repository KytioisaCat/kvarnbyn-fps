"""Stödmurar: där LiDAR-terrängen 1,6 m utanför kantstenen ligger > MIN_H över kantstenskrönet
(terrasser, gator i skärning) reses en vertikal mur från krönet upp till terrängen. Genereras ur
konformeringens resultat — det är exakt de ställen rapporten tidigare listade som kandidater."""
import numpy as np
import shapely
from shapely.geometry import MultiPolygon

from .mesh import KERB_H

MIN_H = 0.6
OUT = 1.6


def build(model, conformed_ground, mb, log=print):
    ko = model.kerb_outer
    polys = ko.geoms if isinstance(ko, MultiPolygon) else [ko]
    rings = []
    for p in polys:
        rings.append(np.array(p.exterior.coords)); rings += [np.array(r.coords) for r in p.interiors]
    nseg = 0; length = 0.0; hmax = 0.0
    model.wall_mask = []          # (mittpunkt, True) för rapportens undantag
    for ring in rings:
        P0, P1 = ring[:-1], ring[1:]
        d = P1 - P0; L = np.hypot(d[:, 0], d[:, 1]); ok = L > 1e-6
        P0, P1, d, L = P0[ok], P1[ok], d[ok], L[ok]
        n = np.column_stack([d[:, 1], -d[:, 0]]) / L[:, None]
        mid = (P0 + P1) / 2
        # utåt = den sida som inte ligger i kantstenspolygonen
        side = mid + n * OUT
        inside = shapely.contains_xy(ko, side[:, 0], side[:, 1])
        n[inside] *= -1
        out = mid + n * OUT
        kerb_top = model.height_at(mid[:, 0], mid[:, 1], 'ground') + KERB_H
        terr = conformed_ground.at(out[:, 0], out[:, 1])
        h = terr - kerb_top
        for k in np.nonzero(h > MIN_H)[0]:
            t0 = float(model.height_at([P0[k, 0]], [P0[k, 1]], 'ground')[0]) + KERB_H
            t1 = float(model.height_at([P1[k, 0]], [P1[k, 1]], 'ground')[0]) + KERB_H
            top0 = float(conformed_ground.at(P0[k, 0] + n[k, 0] * OUT, P0[k, 1] + n[k, 1] * OUT))
            top1 = float(conformed_ground.at(P1[k, 0] + n[k, 0] * OUT, P1[k, 1] + n[k, 1] * OUT))
            top0 = max(top0, t0 + MIN_H); top1 = max(top1, t1 + MIN_H)
            a = (P0[k, 0], t0, P0[k, 1]); b = (P1[k, 0], t1, P1[k, 1])
            c = (P1[k, 0], top1 + 0.3, P1[k, 1]); dd = (P0[k, 0], top0 + 0.3, P0[k, 1])
            mb.add_quad('wall', a, b, c, dd); mb.add_quad('wall', a, dd, c, b)   # dubbelsidig
            # krön: en 0,4 m bred topp som möter terrängen bakom
            e_ = (P1[k, 0] + n[k, 0] * 0.4, top1 + 0.3, P1[k, 1] + n[k, 1] * 0.4)
            f_ = (P0[k, 0] + n[k, 0] * 0.4, top0 + 0.3, P0[k, 1] + n[k, 1] * 0.4)
            mb.add_quad('wall', dd, c, e_, f_)
            nseg += 1; length += float(L[k]); hmax = max(hmax, float(h[k]))
            model.wall_mask.append((mid[k, 0], mid[k, 1]))
    log(f'  stödmurar: {nseg} segment, {length:.0f} m, högsta {hmax:.1f} m')
    return {'wall_segments': nseg, 'wall_length_m': length, 'wall_max_h': hmax}

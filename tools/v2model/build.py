"""Kör hela offline-modellen för ett område: nät → profil → meshar → konformering → rapport → export.

    cd tools && venv/bin/python -m v2model.build --area torget
"""
import argparse
import os
import sys
import time

import numpy as np

from . import common, network, profile, mesh, conform, export, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--area', default='torget', choices=list(common.AREAS))
    ap.add_argument('--no-export', action='store_true')
    args = ap.parse_args()
    t0 = time.time()
    log = lambda s: print(s, flush=True)
    log(f'[1/6] vägnät ({args.area})')
    net = network.build(common.AREAS[args.area])
    log('  ' + network.stats(net))
    ground = common.Ground()
    log('[2/6] profil-lösare')
    h, g, crossings = profile.solve(net, ground, log=log)
    log('[3/6] meshar')
    model = mesh.RoadModel(net, h, ground)
    mb = model.build(log=log)
    arrays = mb.arrays()
    mesh_stats = {k: len(v[1]) // 3 for k, v in arrays.items()}
    log('[4/6] terrängkonformering')
    raw_new, cstats = conform.conform(model, ground, log=log)
    g2 = common.Ground.__new__(common.Ground)
    g2.raw = raw_new; g2.h, g2.w = raw_new.shape; g2.sx, g2.sz = ground.sx, ground.sz
    log('[5/6] mätgrindar')
    rows, ok = report.evaluate(net, h, g, crossings, model, g2, mesh_stats, cstats, log=log)
    for name, v, lim, okk, unit, det in rows:
        log(f'  {"OK " if okk else "FEL"} {name}: {v:.3f} {unit} (gräns {lim}) {det}')
    png = report.profile_png(net, h, g, 'Mölndals bro', os.path.join(report.OUTDIR, 'profil_molndals_bro.png'), 'Mölndals bro')
    path = report.write(rows, ok, net, h, g, mesh_stats, cstats, args.area,
                        extra_lines=[f'Profilbild: `{os.path.relpath(png, common.TOOLS)}`' if png else '', f'Tid: {time.time() - t0:.0f} s'])
    log(f'  rapport: {path}')
    if not args.no_export:
        log('[6/6] export')
        nbytes = export.write_meshes(arrays)
        export.write_dem(raw_new)
        log(f'  roads.bin {nbytes / 1e6:.1f} MB, lidar_conformed.npy skriven')
    log(f'klart på {time.time() - t0:.0f} s — {"ALLA GRINDAR OK" if ok else "GRIND BRUTEN"}')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()

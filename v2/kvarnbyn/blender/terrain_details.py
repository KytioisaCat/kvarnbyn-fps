"""Terrain appearance attributes and low stone walls on existing OSM lines."""
import math
import numpy as np


def paint(mesh, grid):
    """Linear corner colors: red=exposed rock, green=woodland floor.

    Sample world-coordinate fields so tile/material boundaries stay invisible.
    Colors carry weights, not baked lighting or photo pixels.
    """
    count = len(mesh.vertices)
    xyz = np.empty(count * 3, dtype=np.float32)
    mesh.vertices.foreach_get('co', xyz)
    xyz = xyz.reshape(-1, 3)
    nx, nz = grid['nx'], grid['nz']
    fx = np.clip((xyz[:, 0] - grid['x0']) / grid['step'], 0, nx - 1.0001)
    fz = np.clip((-xyz[:, 1] - grid['z0']) / grid['step'], 0, nz - 1.0001)
    i, k = fx.astype(int), fz.astype(int)
    tx, tz = fx - i, fz - k
    fields = np.column_stack([grid['rock_exposure'], np.asarray(grid['land'])[:, 2]])
    value = (fields[k*nx+i]*(1-tx)[:, None] + fields[k*nx+i+1]*tx[:, None])*(1-tz)[:, None]
    value += (fields[(k+1)*nx+i]*(1-tx)[:, None] + fields[(k+1)*nx+i+1]*tx[:, None])*tz[:, None]
    rgba = np.ones((count, 4), dtype=np.float32)
    rgba[:, :2] = value
    rgba[:, 2] = 0.
    indices = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get('vertex_index', indices)
    attribute = mesh.color_attributes.new(name='TerrainCover', type='FLOAT_COLOR', domain='CORNER')
    attribute.data.foreach_set('color', rgba[indices].ravel())
    mesh.color_attributes.active_color = attribute


def build_walls(kit, materials, ground, city):
    """OSM fixes the plan location. Heights/widths are modest estimates.

    No terrain cutting or tall conjectural terrace walls. Sample both sides,
    bury the foot, follow the lower side, and cap visible rise at 1.45 m.
    """
    profiles = []
    for wall in city['barriers']:
        if wall['id'] not in {'w90143431', 'w92331953'}:
            continue
        for segment, (a, b) in enumerate(zip(wall['line_xz'], wall['line_xz'][1:])):
            dx, dz = b[0]-a[0], b[1]-a[1]
            length = math.hypot(dx, dz)
            ux, uz = dx/length, dz/length
            count = max(1, math.ceil(length / 1.5))
            sections = []
            for n in range(count+1):
                x, z = a[0]+dx*n/count, a[1]+dz*n/count
                sides = [ground(x-uz*.6, z+ux*.6), ground(x+uz*.6, z-ux*.6)]
                low = min(*sides, ground(x, z))
                bottom = low-.3
                top = low + min(1.45, max(.6, max(sides)-low+.12))
                sections.append((x,z,bottom,top))
            name = 'Mapped_stone_wall_' + wall['id']
            for p, q in zip(sections, sections[1:]):
                rings = [[(x-uz*s*.21, -(z+ux*s*.21), y) for s,y in [(-1,lo),(1,lo),(1,hi),(-1,hi)]] for x,z,lo,hi in (p,q)]
                faces = [[rings[0][j], rings[1][j], rings[1][(j+1)%4], rings[0][(j+1)%4]] for j in range(4)]
                faces += [rings[0], list(reversed(rings[1]))]
                for face in faces:
                    kit.face(name, materials['stone'], face)
                    kit.face('COL_' + name, materials['collision'], face)
            profiles.append(dict(id=wall['id'], segment=segment, sections=sections, width=.42))
    return profiles

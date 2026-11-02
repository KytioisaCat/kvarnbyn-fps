#!/usr/bin/env python3
"""Own north-up cartography from the current Kvarnbyn city/site, no map-service pixels.

Run after site.py. The image is a static overview; Godot draws player/zone/allied
markers above it. X grows east/right and Z south/down, exactly as the game world.
"""
from pathlib import Path
import argparse, hashlib, json, math, time
import numpy as np
from PIL import Image, ImageDraw
from common import DATA, HERE, ZONE, land_class, raw_height

PALETTE = {
    'terrain':'#bbc5ac', 'forest':'#81977b', 'rock':'#bcc0b4',
    'urban':'#c2c7b7', 'water':'#5b8d9d', 'asphalt':'#d6d4c8',
    'paving':'#e1decc', 'walkway':'#d8d5c5', 'trail':'#adae94',
    'soil':'#9a9d7f', 'pitch':'#94aa86', 'playground':'#b9ae8f',
    'building':'#575c53', 'building_edge':'#3e4943', 'road_edge':'#7b8478',
}

def rgb(value):
    return np.array([int(value[i:i+2],16) for i in (1,3,5)],float)

def generate(city_path, site_path, output, width=2400):
    t0=time.perf_counter()
    city=json.loads(city_path.read_text());site=json.loads(site_path.read_text())
    xmin,zmin,xmax,zmax=ZONE
    height=round(width*(zmax-zmin)/(xmax-xmin));size=(width,height)
    # Coarse colour/hillshade is derived from licensed source measurements, not
    # an orthophoto. Keep it quiet so streets, buildings and the river read first.
    coarse_w=600;coarse_h=round(coarse_w*(zmax-zmin)/(xmax-xmin))
    xx=np.linspace(xmin,xmax,coarse_w);zz=np.linspace(zmin,zmax,coarse_h)
    x,z=np.meshgrid(xx,zz)
    weights=land_class(x.ravel(),z.ravel()).reshape(coarse_h,coarse_w,4)
    field=np.maximum(0,1-weights.sum(2))
    base=(weights[:,:,0,None]*rgb(PALETTE['urban'])+
          weights[:,:,1,None]*rgb(PALETTE['terrain'])+
          weights[:,:,2,None]*rgb(PALETTE['forest'])+
          weights[:,:,3,None]*rgb(PALETTE['rock'])+
          field[:,:,None]*rgb(PALETTE['terrain']))
    elevations=raw_height(x.ravel(),z.ravel()).reshape(coarse_h,coarse_w)
    dz,dx=np.gradient(elevations,(zmax-zmin)/(coarse_h-1),(xmax-xmin)/(coarse_w-1))
    shade=np.clip(1-.16*dx-.19*dz,.82,1.12)
    base=np.clip(base*shade[:,:,None],0,255).astype(np.uint8)
    image=Image.fromarray(base,'RGB').resize(size,Image.Resampling.BICUBIC)
    draw=ImageDraw.Draw(image)
    scale=width/(xmax-xmin)
    def pixel(q):return ((float(q[0])-xmin)*scale,(float(q[1])-zmin)*scale)
    # A fine dark edge clarifies the street network at minimap scale. Surfaces
    # below paint the actual rendered widths and authoring changes on top.
    for road in city['roads']:
        if road.get('tunnel') or len(road['line_xz'])<2:continue
        xy=[pixel(q) for q in road['line_xz']]
        if road['kind'] not in ('steps','path','track'):
            draw.line(xy,fill=PALETTE['road_edge'],width=max(2,round(road['width_m']*scale)+2),joint='curve')
    kinds={k:k for k in PALETTE}
    for key in ['roten_mesh_kinds','stalliden_mesh_kinds','stalliden_garden_mesh_kinds','m25_mesh_kinds','north_bank_mesh_kinds']:
        kinds.update(site.get(key,{}))
    kinds.update({k:'trail' for k,v in kinds.items() if v=='gravel'})
    rendered_triangles=0
    # Water first, roads later, bridge decks last: this matches world ownership.
    keys=list(site['meshes'])
    keys.sort(key=lambda key:0 if key=='water' else 1)
    for key in keys:
        kind=kinds.get(key,key)
        if kind=='grass':continue
        if kind=='rock':kind='rock'
        if kind not in PALETTE:continue
        for triangles in site['meshes'][key].values():
            for triangle in triangles:
                draw.polygon([pixel((p[0],p[2])) for p in triangle],fill=PALETTE[kind])
                rendered_triangles+=1
    for bridge in site['bridges']:
        points=[pixel((p[0],p[2])) for p in bridge['points']]
        if len(points)<2:continue
        w=max(2,round(bridge['width_m']*scale))
        draw.line(points,fill=PALETTE['building_edge'],width=w+3,joint='curve')
        draw.line(points,fill=PALETTE['paving'] if bridge['kind'] in ('footway','pedestrian','path','cycleway','steps') else PALETTE['asphalt'],width=w,joint='curve')
    buildings=0
    for building in city['buildings']:
        poly=building.get('build_footprint_xz',building['footprint_xz'])
        if len(poly)<3:continue
        if max(q[0] for q in poly)<xmin or min(q[0] for q in poly)>xmax or max(q[1] for q in poly)<zmin or min(q[1] for q in poly)>zmax:continue
        draw.polygon([pixel(q) for q in poly],fill=PALETTE['building'],outline=PALETTE['building_edge'],width=1)
        buildings+=1
    names={b['id']:b for b in city['buildings']}
    landmarks=[]
    for ident,name,offset in [('w48115243','Stadsmuseet',[12,-10]),
                              ('w843661093','Kvarnbytornet',[12,-8])]:
        if ident in names:landmarks.append(dict(id=ident,name=name,position=names[ident]['centroid_xz'],label_offset=offset))
    landmarks.extend([
        dict(id='torget',name='Gamla torget',position=[-8.,0.],label_offset=[-85.,-13.]),
        dict(id='roten',name='Roten M',position=[100.,110.],label_offset=[12.,19.]),
        dict(id='royens',name='Royens trappor',position=[175.,-1.],label_offset=[12.,20.]),
        dict(id='spawn',name='Görjelycksgatan',position=[340.,153.],label_offset=[-135.,-15.]),
    ])
    output.mkdir(parents=True,exist_ok=True)
    image.save(output/'world_map.png',optimize=True)
    metadata=dict(schema_version=1,bounds=[round(v,6) for v in ZONE],
                  image=dict(file='world_map.png',width=width,height=height),
                  landmarks=landmarks,palette=PALETTE,
                  attribution=['Kartdata © OpenStreetMap-bidragsgivare (ODbL)','Höjddata: Lantmäteriet'],
                  source=dict(city_sha256=hashlib.sha256(city_path.read_bytes()).hexdigest(),site_sha256=hashlib.sha256(site_path.read_bytes()).hexdigest(),method='Own cartography; rendered surface triangles and built footprints, land classes and LiDAR hillshade; no external map pixels'),
                  counts=dict(buildings=buildings,roads=len(city['roads']),surface_triangles=rendered_triangles,bridges=len(site['bridges'])))
    (output/'map.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print('KVARNBYN_MAP_IMAGE '+json.dumps(dict(size=size,bytes=(output/'world_map.png').stat().st_size,seconds=round(time.perf_counter()-t0,2),**metadata['counts'])))
    return metadata

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--city',type=Path,default=DATA/'city.json')
    parser.add_argument('--site',type=Path,default=DATA/'site.json')
    parser.add_argument('--output',type=Path,default=HERE/'godot/assets')
    parser.add_argument('--width',type=int,default=2400)
    args=parser.parse_args()
    if not 512<=args.width<=4096:parser.error('--width must be between512 and4096')
    generate(args.city.resolve(),args.site.resolve(),args.output.resolve(),args.width)

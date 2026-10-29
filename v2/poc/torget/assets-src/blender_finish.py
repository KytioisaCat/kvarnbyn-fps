"""Portable, subtle finish variations for the Gamla torget material kit.

Inside Blender, after constructing the material dictionary and before geometry:
    from blender_finish import apply_finish
    apply_finish(M)

Outside Blender, regenerate the baked image variants with tools/venv Python:
    tools/venv/bin/python v2/poc/torget/assets-src/blender_finish.py --prepare

Source photographs are CC0 Poly Haven maps already downloaded in this project.
All renderer inputs are ordinary image textures in Principled BSDF nodes.
"""
from pathlib import Path
import json
import math

ROOT=Path(__file__).resolve().parent
FINISH=ROOT/'finish'
PALETTE={
    'panel':('#eeeae0','paint_offwhite_1k.png'),
    'cream':('#ded7c3','paint_cream_1k.png'),
    'plaster':('#e8e1cf','paint_warm_plaster_1k.png'),
}


def prepare():
    """Derive neutral paint variation and greener grass; never brown façade stains."""
    import numpy as np
    from PIL import Image,ImageFilter
    manifest=json.loads((ROOT/'manifest.json').read_text())
    def source(key,kind='albedo'):
        path=ROOT/manifest['materials'][key]['maps'][kind]['path']
        return Image.open(path).convert('RGB').resize((1024,1024),Image.Resampling.LANCZOS)
    def field(image,blur=7):
        # Remove source pigment. Keep restrained photographed surface variation.
        lum=np.asarray(image.convert('L').filter(ImageFilter.GaussianBlur(blur)),dtype=np.float64)/255
        centered=lum-np.median(lum)
        spread=max(.03,float(np.percentile(np.abs(centered),95)))
        return np.clip(centered/spread,-1,1)
    def linear(rgb):
        rgb=np.asarray(rgb)/255
        return np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    def srgb(value):
        value=np.clip(value,0,1)
        return np.where(value<=.0031308,value*12.92,1.055*value**(1/2.4)-.055)
    def save_rgb(path,array):
        data=np.uint8(np.clip(array,0,1)*255+.5)
        Image.fromarray(data,'RGB').save(path,optimize=True)
        return {'file':path.name,'size_bytes':path.stat().st_size,
            'rgb_min':[int(x) for x in data.min(axis=(0,1))],
            'rgb_mean':[round(float(x),3) for x in data.mean(axis=(0,1))],
            'rgb_max':[int(x) for x in data.max(axis=(0,1))]}
    FINISH.mkdir(exist_ok=True)
    paint_source=source('plaster')
    paint_field=field(paint_source,6)
    paint_fine=field(paint_source,1)
    # 95% of the pattern is broad pigment variation, 5% is fine scanned grain.
    paint_field=np.clip(paint_field*.95+paint_fine*.05,-1,1)
    outputs=[]
    for key,(hex_color,name) in PALETTE.items():
        rgb=[int(hex_color[i:i+2],16) for i in (1,3,5)]
        amplitude=.055 if key!='plaster' else .065
        target=linear(rgb)[None,None,:]*(1+paint_field[:,:,None]*amplitude)
        result=save_rgb(FINISH/name,srgb(target))
        result.update({'purpose':key,'source_asset':'white_plaster_rough_01',
            'source_map':'albedo','target_srgb':hex_color,'linear_brightness_variation':[-amplitude,amplitude]})
        outputs.append(result)
    # Painted sheet-metal pigmentation + roughness variation, not ceramic tile marks.
    asphalt=source('asphalt')
    metal_field=field(asphalt,20)
    column=np.mean(metal_field,axis=0)
    column=np.clip(column/max(.05,float(np.max(np.abs(column)))),-1,1)
    metal_field=np.clip(.78*metal_field+.22*column[None,:],-1,1)
    metal_target=linear([52,59,64])[None,None,:]*(1+.075*metal_field[:,:,None])
    result=save_rgb(FINISH/'painted_metal_albedo_1k.png',srgb(metal_target))
    result.update({'purpose':'painted standing-seam roof','source_asset':'asphalt_02',
        'source_map':'albedo, heavily low-pass filtered and neutralized',
        'target_srgb':'#343b40','linear_brightness_variation':[-.075,.075]})
    outputs.append(result)
    roughness=np.uint8(np.clip(.56+.055*metal_field,0,1)*255+.5)
    Image.fromarray(roughness,'L').save(FINISH/'painted_metal_roughness_1k.png',optimize=True)
    # Preserve the source's fine grass/soil pattern and shade, change pigment modestly.
    grass=np.asarray(source('grass'),dtype=np.float64)/255
    ratio=grass[:,:,1]/np.maximum(grass[:,:,0],.01)
    greener=np.clip((ratio-.80)/.24,0,1)
    mix=.20+.80*greener
    dry=np.array([116,113,74])/255
    green=np.array([78,112,50])/255
    pigment=dry[None,None,:]*(1-mix[:,:,None])+green[None,None,:]*mix[:,:,None]
    luminance=grass@np.array([.2126,.7152,.0722])
    detail=np.clip(luminance/np.median(luminance),.67,1.4)
    grass_variant=np.clip(pigment*detail[:,:,None],0,1)
    result=save_rgb(FINISH/'grass_early_summer_1k.png',grass_variant)
    result.update({'purpose':'moderate early-summer grass proxy','source_asset':'grass_ground',
        'source_map':'albedo','limitation':'Seasonal color interpretation; not measured on-site vegetation or a classified soil map.'})
    outputs.append(result)
    info={
        'license':'CC0-1.0; derived from the attributed CC0 source maps in ../manifest.json',
        'method':'Offline photographic luminance/pigment separation; all delivered maps are ordinary 1k images.',
        'geometry_change':False,
        'source_pages':['https://polyhaven.com/a/white_plaster_rough_01',
            'https://polyhaven.com/a/asphalt_02','https://polyhaven.com/a/grass_ground'],
        'variants':outputs,
    }
    (FINISH/'manifest.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(info,ensure_ascii=False,indent=2))


def _bsdf(material):
    return next(node for node in material.node_tree.nodes if node.type=='BSDF_PRINCIPLED')


def _set_image(material,socket_name,filename,color_space='sRGB'):
    import bpy
    tree=material.node_tree
    socket=_bsdf(material).inputs[socket_name]
    for link in list(socket.links): tree.links.remove(link)
    node=tree.nodes.new('ShaderNodeTexImage')
    node.name='BakedFinish_'+socket_name.replace(' ','')
    node.label='CC0 fotografisk materialvariation'
    node.image=bpy.data.images.load(str(FINISH/filename),check_existing=True)
    node.image.colorspace_settings.name=color_space
    node.interpolation='Linear'
    node.extension='REPEAT'
    tree.links.new(node.outputs['Color'],socket)
    material['finish_source_manifest']='assets-src/finish/manifest.json'
    return material


def apply_painted_finish(material,tone='panel'):
    """Keep existing scanned normal/roughness. Add mild neutral paint albedo."""
    if tone not in PALETTE: raise ValueError(f'Unknown paint tone: {tone}')
    _set_image(material,'Base Color',PALETTE[tone][1])
    material['finish_kind']='paint_'+tone
    return material


def apply_metal_finish(material):
    _set_image(material,'Base Color','painted_metal_albedo_1k.png')
    _set_image(material,'Roughness','painted_metal_roughness_1k.png','Non-Color')
    # The existing raised standing seams remain the geometric roof detail.
    material['finish_kind']='subtle_painted_metal'
    material['tile_size_m']=4.0
    return material


def apply_grass_finish(material):
    _set_image(material,'Base Color','grass_early_summer_1k.png')
    material['finish_kind']='early_summer_grass_proxy'
    return material


def apply_glass_finish(material):
    """Optional opaque glass proxy; no expensive alpha/transmission sorting.

    Real room/curtain planes need per-window UV and geometry in the authoring kit;
    this function only improves response of the shared front glass surface.
    """
    bsdf=_bsdf(material)
    bsdf.inputs['Roughness'].default_value=.105
    bsdf.inputs['Metallic'].default_value=.12
    bsdf.inputs['IOR'].default_value=1.5
    material['finish_kind']='opaque_reflective_window_proxy'
    return material


def apply_finish(materials,glass=False):
    """Apply before generating geometry so the roof's 4m UV scale takes effect."""
    for tone in PALETTE:
        if tone in materials: apply_painted_finish(materials[tone],tone)
    if 'metal' in materials: apply_metal_finish(materials['metal'])
    if 'grass' in materials: apply_grass_finish(materials['grass'])
    if glass and 'glass' in materials: apply_glass_finish(materials['glass'])
    return materials


if __name__=='__main__':
    import sys
    if '--prepare' in sys.argv: prepare()
    else: print(__doc__)

"""Inspect the HDRI and write a display preview. Does not open or save a scene."""
from pathlib import Path
import json
import numpy as np
import bpy
ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'manifest.json').read_text())
image=bpy.data.images.load(str(ROOT/manifest['file']),check_existing=True)
width,height=image.size
pixels=np.empty(width*height*4,dtype=np.float32)
image.pixels.foreach_get(pixels)
pixels=pixels.reshape((height,width,4))
luminance=pixels[:,:,0].astype(np.float64)*.2126+pixels[:,:,1].astype(np.float64)*.7152+pixels[:,:,2].astype(np.float64)*.0722
y,x=np.unravel_index(int(np.argmax(luminance)),luminance.shape)
scene=bpy.context.scene
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGB'
scene.render.image_settings.color_depth='8'
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.view_settings.exposure=-.5
preview=ROOT/'sky_preview_agx.png'
image.save_render(str(preview),scene=scene)
manifest.update({
    'dimensions':[width,height],
    'projection':'equirectangular panorama',
    'source_color_space_in_blender':image.colorspace_settings.name,
    'preview':preview.name,
    'preview_color_management':{'view':'AgX','look':'Medium High Contrast','exposure_stops':-.5},
    'brightest_pixel_uv_bottom_up':[(int(x)+.5)/width,(int(y)+.5)/height],
    'approx_brightest_elevation_deg':round(((int(y)+.5)/height-.5)*180,2),
    'max_linear_channel_value':round(float(pixels[:,:,:3].max()),3),
    'all_source_pixels_finite':bool(np.isfinite(pixels).all()),
})
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:manifest[k] for k in ['dimensions','source_color_space_in_blender','preview','brightest_pixel_uv_bottom_up','approx_brightest_elevation_deg','all_source_pixels_finite']},indent=2))

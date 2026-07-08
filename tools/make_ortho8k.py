"""Bygger 8192px-speltextur ur redan cachade Lantmäteriet-rutor (ingen inloggning behövs)."""
import numpy as np, rasterio, glob
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds
from PIL import Image

LON0, LON1, LAT0, LAT1 = 12.008, 12.044, 57.6495, 57.6625
paths = sorted(glob.glob('cache/o*_mr24.tif'))
assert len(paths) == 4, paths
datasets = [rasterio.open(p) for p in paths]
mosaic, tr = merge(datasets, res=(0.2, 0.2))
crs = datasets[0].crs
for d in datasets: d.close()
print('mosaik', mosaic.shape)
W, H = 8192, 5529
dst = np.zeros((3, H, W), dtype=np.uint8)
reproject(source=mosaic[:3], destination=dst, src_transform=tr, src_crs=crs,
          dst_transform=from_bounds(LON0, LAT0, LON1, LAT1, W, H), dst_crs='EPSG:4326',
          resampling=Resampling.bilinear)
Image.fromarray(np.moveaxis(dst, 0, -1), 'RGB').save('ortho8k.jpg', quality=80)
import os; print('ortho8k.jpg', os.path.getsize('ortho8k.jpg')//1048576, 'MB')

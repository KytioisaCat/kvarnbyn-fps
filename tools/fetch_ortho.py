import math, io, time, urllib.request, json
from PIL import Image
exec(open('fetch_tiles.py').read().split('# --- elevation')[0])

img, crop = stitch('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 18, 'RGB')
img_c = img.crop(tuple(int(round(v)) for v in (crop[0], crop[1], crop[2], crop[3])))
print('cropped', img_c.size)
img_c.save('ortho_full.png')
json.dump({'w':img_c.size[0],'h':img_c.size[1]}, open('ortho_meta.json','w'))
# game texture: cap at 4096 wide for GPU friendliness
scale = 4096 / img_c.size[0]
tex = img_c.resize((4096, int(img_c.size[1]*scale)), Image.LANCZOS)
tex.save('ortho.jpg', quality=82)
print('texture', tex.size)

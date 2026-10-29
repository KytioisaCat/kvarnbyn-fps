"""Comparison of prepared albedos. Scene-render checks are separate after_*.png."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'finish'
font_path='/System/Library/Fonts/Supplemental/Arial.ttf'
try:
    font=ImageFont.truetype(font_path,23)
    small=ImageFont.truetype(font_path,18)
except OSError:
    font=ImageFont.load_default();small=font
canvas=Image.new('RGB',(1260,850),(31,36,38));draw=ImageDraw.Draw(canvas)
size=(380,330)
panels=[
    ('Vitmålad panel',Image.new('RGB',size,(238,234,224)),Image.open(OUT/'paint_offwhite_1k.png')),
    ('Målad plåt',Image.new('RGB',size,(52,59,64)),Image.open(OUT/'painted_metal_albedo_1k.png')),
    ('Tidigsommargräs',Image.open(ROOT/'materials/grass/grass_ground_diff_1k.jpg'),Image.open(OUT/'grass_early_summer_1k.png')),
]
for index,(title,before,after) in enumerate(panels):
    x=30+index*410
    draw.text((x,20),title,font=font,fill=(235,234,226))
    draw.text((x,55),'Före',font=small,fill=(190,195,190))
    canvas.paste(before.resize(size,Image.Resampling.LANCZOS),(x,85))
    draw.text((x,435),'Efter · samma källdetaljer, justerat pigment',font=small,fill=(190,195,190))
    canvas.paste(after.resize(size,Image.Resampling.LANCZOS),(x,465))
draw.text((30,815),'Albedojämförelse. Plåt har även separat roughnessvariation. Ingen geometri ändras.',font=small,fill=(190,195,190))
canvas.save(OUT/'material_comparison.png')

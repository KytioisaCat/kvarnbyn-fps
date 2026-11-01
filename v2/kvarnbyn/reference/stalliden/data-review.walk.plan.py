"""CPU-only plan from frozen reference JSON; writes data-review.walk.jpg only."""
from pathlib import Path
import json, math
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, Polygon, box

OUT=Path(__file__).resolve().parent
data=json.loads((OUT/'data-review.json').read_text())
walk=json.loads((OUT/'data-review.walk.json').read_text())
roads={r['id']:r for r in data['roads']}
W,H=2000,1300
img=Image.new('RGB',(W,H),'#f7f5ed');d=ImageDraw.Draw(img)
FONT='/System/Library/Fonts/Supplemental/Arial.ttf'
f={s:ImageFont.truetype(FONT,s) for s in (17,18,20,22,24,26,30,44)}
ink='#213c42';muted='#596b6d';line='#d7d9d0';red='#b13f39'
left,top,scale=90,180,10
x0,z0,x1,z1=-8,70,126,158
def xy(p):return (left+(p[0]-x0)*scale,top+(p[1]-z0)*scale)
frame=box(x0,z0,x1,z1)
def label(at,text,size=20,fill=ink,bg=True):
    bounds=d.textbbox(at,text,font=f[size])
    if bg:d.rectangle((bounds[0]-4,bounds[1]-2,bounds[2]+4,bounds[3]+2),fill='#f7f5ed')
    d.text(at,text,font=f[size],fill=fill)
def dash(points,fill,width=2,dashlen=8):
    for a,b in zip(points,points[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];L=math.hypot(dx,dy)
        for t in range(0,math.ceil(L),dashlen*2):
            end=min(L,t+dashlen)
            d.line([(a[0]+dx*t/L,a[1]+dy*t/L),(a[0]+dx*end/L,a[1]+dy*end/L)],fill=fill,width=width)
def clipped_lines(coords):
    geom=LineString(coords).intersection(frame)
    return [geom] if geom.geom_type=='LineString' else [g for g in getattr(geom,'geoms',[]) if g.geom_type=='LineString']

d.text((80,42),'STALLIDEN / ROTEN M',font=f[44],fill=ink)
d.text((82,102),'Fryst exportgranskning · ca119f9 · 1 november 2026',font=f[24],fill=muted)
d.text((82,138),'Kartans linjer är källdata och modellkonturer. Inga verkliga vilplan eller murar härleds.',font=f[20],fill=muted)
for x in range(0,127,10):
    xx=xy((x,z0))[0];d.line([(xx,top),(xx,top+(z1-z0)*scale)],fill=line,width=1)
    d.text((xx-10,top-28),str(x),font=f[18],fill=muted)
for z in range(70,159,10):
    yy=xy((x0,z))[1];d.line([(left,yy),(left+(x1-x0)*scale,yy)],fill=line,width=1)
    d.text((left-38,yy-10),str(z),font=f[18],fill=muted)

# The complete OSM road shapes are clipped only for legibility; arrows show the
# shared-node continuation from the stair foot to Norra Forsåkersgatan.
colors={'w63073062':'#aaaead','w330280688':'#679785','w461711525':'#bb6748',
        'w461711523':'#679785','w461711524':'#bb6748','w1227769459':'#376b86','w1227769458':'#82679a'}
for wid in ('w63073062','w1227769459','w1227769458','w330280688','w461711523','w461711525','w461711524'):
    r=roads[wid]
    for ln in clipped_lines(r['line_xz']):
        pts=[xy(p) for p in ln.coords];width=max(5,round(r['width_m']*scale))
        d.line(pts,fill=colors[wid],width=width,joint='curve')
        d.line(pts,fill='#f2efe4',width=2)

for b in data['buildings']:
    original=Polygon(b['footprint_xz']).intersection(frame)
    if original.geom_type=='Polygon':
        pts=[xy(p) for p in original.exterior.coords]
        d.polygon(pts,fill='#e9ddbd',outline='#6b695a',width=2)
    model=Polygon(b['build_footprint_xz']).intersection(frame)
    if model.geom_type=='Polygon':dash([xy(p) for p in model.exterior.coords],red,3,7)
    c=b['centroid_xz'];at=xy(c)
    label((at[0]-18,at[1]-10),b['address'].replace('Roten M ','M'),22)

# Exact exported collision-wall minima, not inferred real obstacles.
for p in walk['actual_export_wall_pinches']:
    a=xy(p['centre_xz']);b=xy(p['actual_COL_wall_slices'][0]['wall_xz'])
    d.line([a,b],fill=red,width=5)
    d.ellipse((a[0]-5,a[1]-5,a[0]+5,a[1]+5),fill=red)
    tag='P24' if p['building_id']=='w92331938' else 'P25'
    label((a[0]+11,a[1]-32),tag,20,red)

nodes=[('J1','3372385219',(87.166,98.474)),('K1','4571796807',(83.45,99.709)),
       ('K2','4571796808',(66.237,105.175)),('K3','4571796809',(62.526,94.355)),
       ('K4','4571796810',(52.699,91.683)),('K5','4571796811',(50.066,83.579)),
       ('K6','4571796812',(45.391,80.54)),('J2','4571796813',(28.66,84.937)),
       ('J3','4571796814',(18.196,88.822)),('K7','11385520693',(14.003,92.796)),
       ('J4','11385520703',(10.751,94.845))]
offsets={'J1':(10,-39),'K1':(9,12),'K2':(-8,12),'K3':(12,-6),'K4':(-32,12),
         'K5':(8,10),'K6':(-4,-34),'J2':(-8,-33),'J3':(-25,-35),'K7':(-39,-14),'J4':(-8,15)}
for tag,node,p in nodes:
    a=xy(p);radius=5
    d.ellipse((a[0]-radius,a[1]-radius,a[0]+radius,a[1]+radius),fill='#f7f5ed',outline=ink,width=2)
    ox,oy=offsets[tag];label((a[0]+ox,a[1]+oy),tag,20)

route=walk['recommended_connected_route_to_Norra_Forsakersgatan']['after_stair_line_xz']
ln=LineString(route)
for station in (13,32,51,66):
    a=ln.interpolate(station-.5);b=ln.interpolate(station+.5)
    pa,pb=xy((a.x,a.y)),xy((b.x,b.y));dx,dy=pb[0]-pa[0],pb[1]-pa[1];L=math.hypot(dx,dy);u,v=dx/L,dy/L
    d.polygon([pb,(pb[0]-u*14-v*6,pb[1]-v*14+u*6),(pb[0]-u*14+v*6,pb[1]-v*14-u*6)],fill='#204d65')

label(xy((94,96)),'Roten M · w330280688',18)
label(xy((59,111)),'Stalliden · w461711525',18,colors['w461711525'])
label(xy((12,80)),'w461711523',18,colors['w461711523'])
label(xy((5,100)),'w461711524',18,colors['w461711524'])
label(xy((20,125)),'Parallell stig · w1227769459',18,colors['w1227769459'])
label(xy((48,149)),'w1227769458',18,colors['w1227769458'])
label(xy((-5,139)),'Norra Forsåkersgatan',18,'#636b69')
label(xy((-5,142)),'w63073062',18,'#636b69')
d.rectangle((left,top,left+(x1-x0)*scale,top+(z1-z0)*scale),outline='#788c89',width=2)

# Side panel is deliberately separate from the map to keep long OSM IDs legible.
sx=1475
d.text((sx,180),'OSM-NODER',font=f[26],fill=ink)
for i,(tag,node,p) in enumerate(nodes):
    yy=224+i*36
    d.text((sx,yy),tag,font=f[20],fill=ink)
    d.text((sx+51,yy),node,font=f[20],fill=muted)
    d.text((sx+51,yy+19),f'{p[0]:.3f} / {p[1]:.3f}',font=f[17],fill='#7c8278')
yy=650
d.text((sx,yy),'MODELLENS PASSAGER',font=f[24],fill=ink)
for i,(head,body) in enumerate([('P24  vägg 0,737 m från mittlinje','0,65 m sidospår: kapseln går in 20 cm.'),
                                ('P25  vägg 0,943 m från mittlinje','0,65 m sidospår: ideal marginal 3 mm.')]):
    y=yy+42+i*73
    d.text((sx,y),head,font=f[20],fill=red)
    d.text((sx,y+27),body,font=f[18],fill=muted)
d.text((sx,866),'KRITISKA FOGAR',font=f[24],fill=ink)
for i,t in enumerate(['J1  gatsten/ramp: 13 cm','J2  ramp/gatsten: 26 cm','J3  gatsten/ramp: 26 cm överlapp','J4  ramp/stig: 15 cm (terräng fyller)']):
    d.text((sx,907+i*29),t,font=f[20],fill=muted)
d.text((sx,1057),'Höjder: faktisk exporterad GLB.',font=f[18],fill=muted)
d.text((sx,1085),'Kapselprov återstår i importerad värld.',font=f[18],fill=red)

d.line([(90,1120),(290,1120)],fill=ink,width=4)
for x in (90,190,290):d.line([(x,1114),(x,1126)],fill=ink,width=2)
d.text((90,1134),'0',font=f[18],fill=muted);d.text((271,1134),'20 m',font=f[18],fill=muted)
d.text((370,1110),'N ↑   x öst / z syd',font=f[22],fill=ink)
d.line([(740,1120),(800,1120)],fill='#6b695a',width=3)
d.text((815,1107),'OSM-fotavtryck',font=f[20],fill=muted)
dash([(1050,1120),(1110,1120)],red,3)
d.text((1125,1107),'Modellkontur',font=f[20],fill=muted)
d.text((90,1195),'Nedre trappfoten J4 landar på gångstigen. OSM-vägen till körbanan följer blå pilar söderut.',font=f[22],fill=ink)
d.text((90,1236),'Källor: OpenStreetMap-bidragsgivare (ODbL), fryst city/site och lokala GLB-filer. Ingen fotoreferens eller DTM-tolkning i bilden.',font=f[18],fill=muted)
img.save(OUT/'data-review.walk.jpg',quality=90,subsampling=0)
print(OUT/'data-review.walk.jpg')

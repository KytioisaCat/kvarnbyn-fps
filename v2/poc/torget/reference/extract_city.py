#!/usr/bin/env python3
"""Reproducible, evidence-labelled interpretation for the first Torget content study.
Only reads committed source data; outputs a city description, not game geometry.
"""
from pathlib import Path
import json, math
import numpy as np
from PIL import Image
from shapely.geometry import Polygon, LineString, box

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'v2/poc/torget/data'
ORIGIN_LON,ORIGIN_LAT=12.02780,57.65690
SX,SZ=59560.0,111320.0
Y_OFFSET=18.0
HALF=60.0
j=json.loads((ROOT/'tools/osm_raw.json').read_text())
nodes={n['id']:n for n in j['elements'] if n['type']=='node'}
ways={w['id']:w for w in j['elements'] if w['type']=='way'}
meta=json.loads((ROOT/'tools/lidar_meta.json').read_text())
heights=np.array(Image.open(ROOT/'tools/lidar_1m.png')).astype(float)/meta['png_scale']-meta['png_offset_m']

def ll(x,z):return ORIGIN_LON+x/SX,ORIGIN_LAT-z/SZ

def height(x,z):
    lon,lat=ll(x,z)
    u=(lon-meta['lon0'])/(meta['lon1']-meta['lon0'])*(meta['w']-1)
    v=(meta['lat1']-lat)/(meta['lat1']-meta['lat0'])*(meta['h']-1)
    i,k=int(math.floor(u)),int(math.floor(v));fx,fz=u-i,v-k
    return float(heights[k,i]*(1-fx)*(1-fz)+heights[k,i+1]*fx*(1-fz)+heights[k+1,i]*(1-fx)*fz+heights[k+1,i+1]*fx*fz)

def pts(w):
    return [((nodes[n]['lon']-ORIGIN_LON)*SX,-(nodes[n]['lat']-ORIGIN_LAT)*SZ) for n in w['nodes']]

def r2(p):return [round(float(x),3) for x in p]

REF_K='https://commons.wikimedia.org/wiki/File:G%C3%B6taforsliden_1_i_M%C3%B6lndal_01.JPG'
REF_T='https://commons.wikimedia.org/wiki/File:Gamla_stadshuset_i_M%C3%B6lndal.JPG'
REF_O='tools/ortho8k.jpg (Lantmäteriet, 2024, CC BY 4.0)'
# Heights are estimates from human observations; they are not point-cloud measurements.
curated={
92331981:dict(name='Kråkans Krog',priority='hero',archetype='white_timber_inn',base_height_raw_m=17.25,levels=2,wall_height_m=5.9,roof_rise_m=1.65,roof_shape='hipped',roof_material='standing_seam_metal',facade_material='horizontal_timber',facade_color='#eeeae0',trim_color='#1c5545',roof_color='#30343a',sign='KRÅKANS KROG',evidence=[dict(source=REF_K,observed='Två våningar i västra huvudvolymen; vit liggande träpanel, gröna foder och dörrar, vita spröjs, blå markiser, mörkt låglutande valmat plåttak.',confidence='high'),dict(source='public/husfakta.js; OSM POI 463940899',observed='Namn och byggnadsmatchning.',confidence='high')],notes='OSM-fotavtrycket omfattar flera sammanbyggda volymer. Huvudvolymen i väster har valmat tak; östra delen har lägre mellandel och sadeltak. Ingen inmätt takhöjd. Gör INTE ett enda likformigt hus av hela polygonen.'),
92332122:dict(name='Gamla stadshuset / Musikskolan',priority='landmark',archetype='historic_timber_civic',base_height_raw_m=18.1,levels=3,wall_height_m=10.3,roof_rise_m=2.2,roof_shape='gabled',roof_material='clay_tile',facade_material='horizontal_timber',facade_color='#e6dfcd',trim_color='#8c4639',roof_color='#8b4938',sign='MUSIKSKOLAN',evidence=[dict(source=REF_T,observed='Gamla stadshuset, Gamla torget43/Kvarnbygatan43: hög ljus träfasad med rödbruna foder, tre huvudvåningar över låg butikssockel; röda takpannor, regelbundet vertikalt fönsterraster och klocka på gatufasaden.',confidence='high')],notes='Byggnadsmatchning genom långsmal form väster om Corpus, anslutande tegelbyggnad i sydväst samt ortofoto. Mått/höjder är visuella uppskattningar. Modellera klocka, höga kopplade fönster och våningsband för igenkänning.'),
92332096:dict(name='Gamla brandstationen / Viktualieföreningens hus',priority='landmark',archetype='historic_brick_civic',base_height_raw_m=18.0,levels=2,wall_height_m=6.0,roof_rise_m=2.0,roof_shape='gabled',roof_material='clay_tile',facade_material='brick',facade_color='#a65e43',trim_color='#bcb5a5',roof_color='#8e4530',sign='',evidence=[dict(source=REF_T,observed='Lägre rött tegelhus i direkt anslutning till Musikskolans sydvästgavel; ljusa tegel-/stenband kring fönster och rött tegeltak.',confidence='medium'),dict(source='https://digitaltmuseum.se/011014739586/gamla-torget-i-molndal-1970-tal-fran-vanster-kvarnbygatan-41-viktualieforeningens',observed='Byggnadsordning och identitet:41 gamla brandstationen,43 Musikskolan,45 öster därom.',confidence='high')],notes='Ligger delvis utanför den exakta120m-rutan men bör behållas helt som västlig kuliss.'),
92332103:dict(name='Corpus Pizzeria',priority='secondary_hero',archetype='historic_timber_shop',base_height_raw_m=18.2,levels=2,wall_height_m=6.1,roof_rise_m=2.2,roof_shape='hipped',roof_material='dark_profiled_metal_estimated',facade_material='stucco',facade_color='#e8e3d5',trim_color='#dedbd0',roof_color='#535559',sign='CORPUS PIZZA',evidence=[dict(source='public/husfakta.js; OSM POI463940910',observed='Huset innehåller Corpus; Gamla torget45B.',confidence='high'),dict(source=REF_O,observed='L-format/knäckt fotavtryck med mörkgrå takytor.',confidence='high')],notes='INTE gamla stadshuset. Google Street View maj2026 visuellt granskat2026-10-29: ljus puts, två våningar, mörkt valmat tak, vita enkla foder, svart skylt med vit text CORPUS PIZZA. Exakta höjder fortfarande uppskattade.'),
92332039:dict(name='Götaforsliden 6',priority='context',archetype='historic_timber_cottage',levels=1,wall_height_m=3.2,roof_rise_m=2.2,roof_shape='gabled',roof_material='clay_tile',facade_material='timber_unconfirmed',facade_color='#eeeae0',trim_color='#ddd8ca',roof_color='#9b4f35',sign='',evidence=[dict(source='tools/osm_raw.json; '+REF_O,observed='Adress och fotavtryck bekräftade; litet hus med rött tak på sydsidan av Götaforsliden.',confidence='medium')],notes='Fasadkulör/höjd uppskattade; ej hjältehus.'),
92332089:dict(name='Götaforsliden 4',priority='context',archetype='historic_timber_cottage',levels=2,wall_height_m=5.4,roof_rise_m=2.1,roof_shape='gabled',roof_material='clay_tile',facade_material='timber_unconfirmed',facade_color='#e8e4dc',trim_color='#d5d1c8',roof_color='#9c5138',sign='',evidence=[dict(source='tools/osm_raw.json; '+REF_O,observed='Adress och fotavtryck bekräftade; rött tak på sydsidan av Götaforsliden.',confidence='medium')],notes='Fasadkulör/höjd uppskattade; ej hjältehus.'),
}
area=box(-HALF,-HALF,HALF,HALF)
buildings=[]
for wid,w in ways.items():
    t=w.get('tags',{})
    if 'building' not in t or t.get('amenity')=='shelter':continue
    p=pts(w)
    if len(p)<4:continue
    poly=Polygon(p)
    if not poly.is_valid:poly=poly.buffer(0)
    if poly.is_empty or not poly.intersects(area):continue
    c=poly.centroid
    rect=list(poly.minimum_rotated_rectangle.exterior.coords)[:-1]
    lens=[math.dist(rect[i],rect[(i+1)%4]) for i in range(4)]
    k=max(range(4),key=lambda i:lens[i]);u=(np.array(rect[(k+1)%4])-np.array(rect[k]))/lens[k]
    if u[0]<0:u=-u
    d=curated.get(wid,dict(name=t.get('name') or 'Bakgrundshus '+str(wid),priority='context',archetype='background_residential',levels=int(float(t.get('building:levels','2'))),wall_height_m=6.0,roof_rise_m=2.0,roof_shape='gabled',roof_material='unconfirmed',facade_material='unconfirmed',facade_color='#e7e2d7',trim_color='#d0c7b6',roof_color='#87584a',sign='',evidence=[dict(source='tools/osm_raw.json',observed='Fotavtryck och läge; övriga husparametrar schabloner.',confidence='low')],notes='Kuliss; ej bekräftad fasad eller takhöjd.'))
    d=dict(d)
    sample=[height(x,z) for x,z in p[:-1]]
    base=d.get('base_height_raw_m',float(np.percentile(sample,65)))
    d.update(id='w'+str(wid),osm_way_id=wid,osm_tags=t,footprint_xz=[r2(p) for p in p[:-1]],centroid_xz=r2((c.x,c.y)),rectangle_xz=[r2(p) for p in rect],major_axis_xz=r2(u),major_length_m=round(max(lens),3),minor_width_m=round(min(lens),3),base_height_raw_m=round(base,3),base_y_m=round(base-Y_OFFSET,3),ground_vertex_heights_raw_m=[round(h,3) for h in sample],height_confidence='estimated_from_reference_not_lidar_roof',closed_ring=True)
    if wid==92331981:
        d['volumes']=[
          dict(id='krakan_west',footprint_xz=[[2.37,32.49],[3.31,29.15],[17.9,25.07],[19.79,34.29],[13.47,35.22]],levels=2,base_height_raw_m=17.25,wall_height_m=5.9,roof_rise_m=1.65,roof_shape='hipped',roof_material='standing_seam_metal',confidence='photo_shape_high_dimensions_estimated',notes='Västra huvudvolymen. Två sneda gatufasader:11.4m med4 nedre och3 övre axlar;6.4m med2 nedre och2 övre axlar.'),
          dict(id='krakan_link',footprint_xz=[[17.9,25.07],[27.99,22.24],[28.17,32.57],[19.79,34.29]],levels=1,base_height_raw_m=17.65,wall_height_m=3.55,roof_rise_m=1.65,roof_shape='gabled_with_front_dormer',roof_material='standing_seam_metal',confidence='photo_shape_high_dimensions_estimated',notes='Lägre mellandel, med frontespis/dörrparti på gatusidan. Höjden ska bryta av tydligt mot huvudhusets takfot.'),
          dict(id='krakan_east',footprint_xz=[[27.99,22.24],[47.22,17.11],[50.21,25.83],[35.0,30.87],[28.17,32.57]],levels=2,base_height_raw_m=18.1,wall_height_m=5.25,roof_rise_m=2.1,roof_shape='gabled_with_front_dormers',roof_material='standing_seam_metal',confidence='photo_shape_high_dimensions_estimated',notes='Östra sadeltaksdelen. Två tydliga små frontespiser mot gatan, gröna foder, vita spröjs; ett fönster högt i östgaveln.')]
        d['street_facades']=[
          dict(volume='krakan_west',edge_xz=[[2.37,32.49],[13.47,35.22]],lower_bays=['green_door','window','glazed_door','window'],upper_bays=3,blue_awnings=3,evidence='Wikimedia photos01+02,2013'),
          dict(volume='krakan_west',edge_xz=[[13.47,35.22],[19.79,34.29]],lower_bays=['window','window'],upper_bays=2,blue_awnings=2,evidence='Wikimedia photos01+02,2013'),
          dict(volume='krakan_link',edge_xz=[[19.79,34.29],[28.17,32.57]],lower_bays=['window','glazed_door','window'],front_dormers=1,evidence='Wikimedia photo02,2013'),
          dict(volume='krakan_east',edge_xz=[[28.17,32.57],[50.21,25.83]],lower_bays=['window','door','window','door'],upper_bays=4,front_dormers=2,evidence='Wikimedia photo02,2013')]
        d['evidence'].append(dict(source='https://commons.wikimedia.org/wiki/File:G%C3%B6taforsliden_1_i_M%C3%B6lndal_02.JPG',observed='Tre takvolymer samt gatufasadens rytm, observerat i foto taget2013.',confidence='high'))
    if wid in [92331981,92332103,92332122,92332096]:
        d['evidence'].append(dict(source='https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=57.65688,12.02745&heading=300&pitch=10&fov=90' if wid!=92331981 else 'https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=57.65652,12.02796&heading=10&pitch=5&fov=85',observed='Manuellt visuellt granskat i Google Maps Street View2026-10-29. Bildinsamling maj2026. Se reference/OBSERVATIONER.md för fasad- och gaturumsnoteringar.',confidence='high_for_appearance_not_metric_dimensions'))
    buildings.append(d)
roads=[];waterways=[];surfaces=[];barriers=[]
widths={'tertiary':7.0,'residential':5.5,'unclassified':4.5,'service':3.2,'footway':2.0,'path':2.5,'steps':1.8,'pedestrian':3.0,'platform':2.3}
for wid,w in ways.items():
    t=w.get('tags',{});p=pts(w)
    if len(p)<2:continue
    line=LineString(p)
    if not line.intersects(area):continue
    if ('amenity' in t and t['amenity']=='parking') or (t.get('area')=='yes' and t.get('highway')=='pedestrian'):
        if len(p)>3 and w['nodes'][0]==w['nodes'][-1]:
            poly=Polygon(p)
            if not poly.is_valid:poly=poly.buffer(0)
            clip=poly.intersection(area)
            for g in (list(clip.geoms) if clip.geom_type=='MultiPolygon' else [clip]):
                if g.is_empty or not isinstance(g,Polygon):continue
                rp=list(g.exterior.coords)[:-1];samples=np.array([[x,z,1] for x,z in rp]);ys=np.array([height(x,z) for x,z in rp]);a,b,c=np.linalg.lstsq(samples,ys,rcond=None)[0];slope=math.hypot(a,b)
                if slope>.08:a*=.08/slope;b*=.08/slope;c=float(np.median(ys-a*np.array([q[0] for q in rp])-b*np.array([q[1] for q in rp])))
                surfaces.append(dict(id='w'+str(wid),name=t.get('name') or 'Parkering',kind='square' if t.get('highway')=='pedestrian' else 'parking',surface=t.get('surface','asphalt'),polygon_xz=[r2(q) for q in rp],ground_plane_raw=[round(float(a),6),round(float(b),6),round(float(c),3)],ground_plane_formula='h_raw=a*x+b*z+c',evidence='OSM polygon; plane fitted to raw DTM boundary; maximum slope8%',osm_tags=t))
    if 'highway' in t and t.get('area')!='yes':
        clip=line.intersection(area);parts=list(clip.geoms) if clip.geom_type=='MultiLineString' else [clip]
        for ix,g in enumerate(parts):
            if g.is_empty or g.geom_type!='LineString':continue
            q=list(g.coords);raw=[height(x,z) for x,z in q]
            roads.append(dict(id='w'+str(wid)+(':'+str(ix) if ix else ''),osm_way_id=wid,name=t.get('name',''),kind=t['highway'],width_m=float(t.get('width',widths.get(t['highway'],3))),width_confidence='OSM' if 'width' in t else 'estimated_from_class_and_ortho',surface=t.get('surface','asphalt'),bridge=t.get('bridge')=='yes',line_xz=[r2(x) for x in q],raw_heights_m=[round(h,3) for h in raw],osm_tags=t))
    if t.get('waterway')=='river':
        clip=line.intersection(area);parts=list(clip.geoms) if clip.geom_type=='MultiLineString' else [clip]
        for g in parts:
            if g.is_empty or g.geom_type!='LineString':continue
            q=list(g.coords)
            waterways.append(dict(id='w'+str(wid),name='Mölndalsån / Götaforsen',line_xz=[r2(x) for x in q],channel_width_m=8.5,width_confidence='estimated_from_2024_orthophoto',raw_heights_m=[round(height(x,z),3) for x,z in q],notes='River centreline only. Build banks and bridge as authored structures. Raw DTM samples may be bed/bank/water and are NOT a measured water surface.'))
    if 'barrier' in t:
        clip=line.intersection(area)
        if clip.geom_type=='LineString':barriers.append(dict(id='w'+str(wid),kind=t['barrier'],line_xz=[r2(x) for x in clip.coords],osm_tags=t))
meta_out=dict(schema_version=1,created='2026-10-29',name='Gamla torget — Kvarnbyn, Mölndal',origin=dict(lat=ORIGIN_LAT,lon=ORIGIN_LON,world_x=round((ORIGIN_LON-12.026)*SX,3),world_z=round(-(ORIGIN_LAT-57.656)*SZ,3),height_raw_m=round(height(0,0),3),y_offset_m=Y_OFFSET),projection=dict(x_m_per_lon_degree=SX,z_m_per_lat_degree=-SZ,world_origin_lon=12.026,world_origin_lat=57.656,local_formula='x=(lon-origin.lon)*59560; z=-(lat-origin.lat)*111320; y=h_raw-y_offset_m',axis='x east, y up, z south',vertical_exaggeration=1.0),bounds=dict(min_x=-HALF,max_x=HALF,min_z=-HALF,max_z=HALF),data_sources=[dict(path='tools/osm_raw.json',license='ODbL',snapshot=j['osm3s']['timestamp_osm_base']),dict(path='tools/lidar_1m.png',license='CC0',meaning='DTM ground, NOT point cloud or roof heights'),dict(path='tools/ortho8k.jpg',license='CC BY 4.0',year=2024)],reference_policy='Wikimedia photographs are observation references only; no source pixels, textures or copied meshes are exported into the game.',limitations=['OSM and orthophoto predate/overlap the2022–2024 street works. The PoC intentionally reconstructs a stable historical-looking square, not2024 roadworks.','Kråkan, Corpus, Musikskolan and the adjoining brick building have visually reviewed facade characteristics. All metric wall/roof heights remain estimates.','No point-cloud-derived roofs or trees in this specification.'])
city=dict(meta=meta_out,buildings=buildings,roads=roads,surfaces=surfaces,waterways=waterways,barriers=barriers,recommended_cameras=[dict(id='krakan',position_xz=[-10,47],look_at_xz=[20,28],eye_height_m=1.7,notes='Från Forsebron/sydväst mot Kråkans gatufasad; undvik att stå i vattenrännan.'),dict(id='torget',position_xz=[-3,10],look_at_xz=[-39,-9],eye_height_m=1.7,notes='Från torg/gata mot Musikskolans höga fasad och tegelhuset.')])
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'city_spec.json').write_text(json.dumps(city,ensure_ascii=False,indent=2)+'\n')
grid=[[round(height(float(x),float(z)),3) for x in range(-60,61)] for z in range(-60,61)]
terrain=dict(schema_version=1,origin=meta_out['origin'],start_x=-60.0,start_z=-60.0,spacing_m=1.0,width=121,height=121,row_order='z increasing (north to south)',vertical_exaggeration=1.0,y_offset_m=Y_OFFSET,encoding='raw_heights_m[row_z][column_x], metres above sea level; y_local=h_raw-y_offset_m',raw_heights_m=grid,min_height_raw_m=min(map(min,grid)),max_height_raw_m=max(map(max,grid)),source='tools/lidar_1m.png + tools/lidar_meta.json',interpolation='bilinear')
(OUT/'terrain.json').write_text(json.dumps(terrain,ensure_ascii=False,separators=(',',':'))+'\n')
print('Wrote',len(buildings),'buildings,',len(roads),'road segments,',len(surfaces),'surfaces,',len(waterways),'waterways')
print('terrain',terrain['min_height_raw_m'],terrain['max_height_raw_m'],'origin',meta_out['origin'])

#!/usr/bin/env python3
"""Resize/re-encode embedded GLB images without modifying geometry or scene data.

Requires Pillow, already present in tools/venv. No network and no external codecs.
Example:
    tools/venv/bin/python v2/poc/torget/assets-src/optimize_glb.py \
        --input world.raw.glb --output world.glb --report mobile-qa.json

All non-image bufferViews are copied byte-for-byte. Accessors, meshes, materials,
textures, samplers, nodes and scenes are checked for exact structural equality.
Normal/ORM JPEGs use 4:4:4 sampling; image PSNR and sampled normal-angle error
are reported against the resized source. Alpha stays PNG.
"""
from __future__ import annotations
from argparse import ArgumentParser
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import hashlib
import json
import math
import os
import struct
import time
from PIL import Image, ImageChops, ImageStat

JSON_CHUNK=0x4E4F534A
BIN_CHUNK=0x004E4942


def read_glb(path):
    raw=Path(path).read_bytes()
    if len(raw)<20:
        raise ValueError('Not a GLB: header too short')
    magic,version,length=struct.unpack_from('<4sII',raw,0)
    if magic!=b'glTF' or version!=2 or length!=len(raw):
        raise ValueError('Expected a complete GLB version 2')
    chunks=[]
    offset=12
    while offset<len(raw):
        length,kind=struct.unpack_from('<II',raw,offset)
        if length%4 or offset+8+length>len(raw):
            raise ValueError('Malformed GLB chunk length')
        chunks.append((kind,raw[offset+8:offset+8+length]))
        offset+=8+length
    if not chunks or chunks[0][0]!=JSON_CHUNK:
        raise ValueError('The first GLB chunk must be JSON')
    document=json.loads(chunks[0][1])
    bins=[data for kind,data in chunks if kind==BIN_CHUNK]
    if len(bins)!=1 or len(document.get('buffers',[]))!=1 or 'uri' in document['buffers'][0]:
        raise ValueError('Only a self-contained GLB with one embedded buffer is supported')
    return raw,document,bins[0],chunks


def slice_view(document,binary,index):
    view=document['bufferViews'][index]
    if view.get('buffer',0)!=0:
        raise ValueError(f'bufferView {index} refers to an external buffer')
    start=view.get('byteOffset',0)
    end=start+view['byteLength']
    if start<0 or end>len(binary):
        raise ValueError(f'bufferView {index} points outside the BIN chunk')
    return binary[start:end]


def texture_image(document,texture_index):
    texture=document['textures'][texture_index]
    if 'source' in texture:
        return texture['source']
    raise ValueError('Compressed texture extensions need a separate conversion step')


def image_roles(document):
    roles={i:set() for i in range(len(document.get('images',[])))}
    alpha_images=set()
    def visit(value,key=''):
        if isinstance(value,dict):
            if key.endswith('Texture') and 'index' in value:
                roles[texture_image(document,value['index'])].add(key)
            for name,child in value.items(): visit(child,name)
        elif isinstance(value,list):
            for child in value: visit(child,key)
    for material in document.get('materials',[]):
        visit(material)
        if material.get('alphaMode','OPAQUE') in ['MASK','BLEND']:
            base=material.get('pbrMetallicRoughness',{}).get('baseColorTexture')
            if base: alpha_images.add(texture_image(document,base['index']))
    return roles,alpha_images


def psnr(reference,encoded):
    decoded=Image.open(BytesIO(encoded)).convert(reference.mode)
    delta=ImageChops.difference(reference,decoded)
    means=ImageStat.Stat(delta).sum2
    mse=sum(means)/(reference.width*reference.height*len(means))
    return float('inf') if mse==0 else 10*math.log10(255*255/mse)


def normal_angle_error(reference,encoded):
    """Angular error on a regular <=128x128 sample grid, after vector normalization."""
    decoded=Image.open(BytesIO(encoded)).convert('RGB')
    reference=reference.convert('RGB')
    source_pixels=reference.load();target_pixels=decoded.load()
    step=max(1,int(math.sqrt(reference.width*reference.height/16384)))
    angles=[]
    for y in range(step//2,reference.height,step):
        for x in range(step//2,reference.width,step):
            a=[v*2/255-1 for v in source_pixels[x,y]]
            b=[v*2/255-1 for v in target_pixels[x,y]]
            denominator=math.sqrt(sum(v*v for v in a)*sum(v*v for v in b))
            if denominator<1e-10: continue
            cosine=max(-1,min(1,sum(u*v for u,v in zip(a,b))/denominator))
            angles.append(math.degrees(math.acos(cosine)))
    angles.sort()
    return {'sample_count':len(angles),'mean':round(sum(angles)/len(angles),3),
        'p95':round(angles[min(len(angles)-1,int(len(angles)*.95))],3),
        'max':round(angles[-1],3)}


def encode_image(raw,name,roles,needs_alpha,max_size,quality):
    source=Image.open(BytesIO(raw))
    source.load()
    original_size=source.size
    has_alpha=('A' in source.getbands()) or ('transparency' in source.info)
    rgba=source.convert('RGBA') if has_alpha else None
    alpha_needed=has_alpha and (needs_alpha or rgba.getchannel('A').getextrema()[0]<255)
    image=rgba if alpha_needed else source.convert('RGB')
    image.thumbnail((max_size,max_size),Image.Resampling.LANCZOS)
    resized=image.size!=original_size
    role_names=sorted(roles)
    is_data=any(role in roles for role in ['normalTexture','metallicRoughnessTexture','occlusionTexture']) or any(s in name.lower() for s in ['normal','nor_gl','rough','_arm','_orm'])
    if alpha_needed:
        mime='image/png'
        chosen_quality=None
        if not resized and source.format=='PNG':
            encoded=raw
        else:
            stream=BytesIO()
            image.save(stream,format='PNG',compress_level=9,optimize=True)
            encoded=stream.getvalue()
        loss=float('inf')
    else:
        mime='image/jpeg'
        # 4:4:4 is essential for vector normals and independent ORM channels.
        subsampling=0 if is_data else 2
        chosen_quality=quality
        stream=BytesIO()
        image.save(stream,format='JPEG',quality=chosen_quality,subsampling=subsampling,optimize=True)
        encoded=stream.getvalue()
        loss=psnr(image,encoded)
        if not resized and source.format=='JPEG' and len(raw)<=len(encoded):
            encoded=raw
            chosen_quality='original'
            loss=float('inf')
    normal_error=None
    if 'normalTexture' in roles or 'nor_gl' in name.lower() or 'normal' in name.lower():
        normal_error=normal_angle_error(image,encoded)
    return encoded,mime,{
        'name':name,'roles':role_names,'original_dimensions':list(original_size),
        'dimensions':list(image.size),'source_bytes':len(raw),'output_bytes':len(encoded),
        'output_mime_type':mime,'alpha_preserved':bool(alpha_needed),
        'jpeg_quality':chosen_quality,'jpeg_chroma_subsampling':'4:4:4' if is_data else '4:2:0',
        'psnr_db_against_resized_source':round(loss,3) if math.isfinite(loss) else 'lossless',
        'normal_angle_degrees':normal_error,
    }


def matrix_multiply(a,b):
    return [[sum(a[row][k]*b[k][column] for k in range(4)) for column in range(4)] for row in range(4)]


def identity(): return [[1.0 if i==j else 0.0 for j in range(4)] for i in range(4)]


def node_matrix(node):
    if 'matrix' in node:
        values=node['matrix']
        return [[values[column*4+row] for column in range(4)] for row in range(4)]
    x,y,z,w=node.get('rotation',[0,0,0,1])
    s=node.get('scale',[1,1,1]); t=node.get('translation',[0,0,0])
    r=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
       [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
       [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
    return [[r[i][j]*s[j] if j<3 else t[i] for j in range(4)] for i in range(3)]+[[0,0,0,1]]


def bounds(document):
    """World AABB from declared POSITION bounds and active scene transforms."""
    low=[float('inf')]*3; high=[float('-inf')]*3
    positions=[]
    for mesh in document.get('meshes',[]):
        for primitive in mesh.get('primitives',[]):
            index=primitive.get('attributes',{}).get('POSITION')
            if index is not None:
                accessor=document['accessors'][index]
                positions.append({'accessor':index,'min':accessor.get('min'),'max':accessor.get('max')})
    def visit(index,parent,ancestors):
        if index in ancestors: raise ValueError('Scene node cycle')
        node=document['nodes'][index]
        world=matrix_multiply(parent,node_matrix(node))
        if 'mesh' in node:
            for primitive in document['meshes'][node['mesh']].get('primitives',[]):
                accessor=document['accessors'][primitive['attributes']['POSITION']]
                if 'min' not in accessor or 'max' not in accessor:
                    raise ValueError('POSITION accessor must declare bounds for verification')
                for mask in range(8):
                    point=[accessor['max' if mask&(1<<i) else 'min'][i] for i in range(3)]+[1]
                    transformed=[sum(world[i][j]*point[j] for j in range(4)) for i in range(3)]
                    for i in range(3):
                        low[i]=min(low[i],transformed[i]);high[i]=max(high[i],transformed[i])
        for child in node.get('children',[]): visit(child,world,ancestors|{index})
    scene=document.get('scenes',[{}])[document.get('scene',0)]
    for index in scene.get('nodes',[]): visit(index,identity(),set())
    return {'position_accessors':positions,'world_aabb_from_accessor_bounds':{'min':low,'max':high}}


def build_glb(document,binary,chunks):
    encoded_json=json.dumps(document,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8')
    encoded_json+=b' '*((-len(encoded_json))%4)
    binary+=b'\0'*((-len(binary))%4)
    out=[]
    for kind,old_data in chunks:
        data=encoded_json if kind==JSON_CHUNK else binary if kind==BIN_CHUNK else old_data
        out.append(struct.pack('<II',len(data),kind)+data)
    payload=b''.join(out)
    return struct.pack('<4sII',b'glTF',2,len(payload)+12)+payload


def optimize(input_path,output_path,max_size=1024,quality=88,report_path=None):
    started=time.monotonic()
    original,source,binary,chunks=read_glb(input_path)
    document=deepcopy(source)
    roles,alpha_images=image_roles(source)
    image_views={}
    reports=[]
    for index,image in enumerate(source.get('images',[])):
        if 'uri' in image or 'bufferView' not in image:
            raise ValueError('Every image must be embedded in a bufferView')
        view_index=image['bufferView']
        raw=slice_view(source,binary,view_index)
        # Multiple image entries may legally share a bufferView. Encode once,
        # conservatively combining alpha/role requirements of all references.
        image_views.setdefault(view_index,[]).append(index)
    encoded_views={}
    for view_index,indices in image_views.items():
        combined_roles=set().union(*(roles[i] for i in indices))
        name=source['images'][indices[0]].get('name',f'image_{indices[0]}')
        encoded,mime,report=encode_image(slice_view(source,binary,view_index),name,combined_roles,
            bool(set(indices)&alpha_images),max_size,quality)
        encoded_views[view_index]=encoded
        report['image_indices']=indices
        reports.append(report)
        for index in indices: document['images'][index]['mimeType']=mime
    # Refuse to re-encode a view also used by an accessor (including sparse data).
    protected=set()
    for accessor in source.get('accessors',[]):
        if 'bufferView' in accessor: protected.add(accessor['bufferView'])
        sparse=accessor.get('sparse',{})
        for key in ['indices','values']:
            if key in sparse: protected.add(sparse[key]['bufferView'])
    if protected & set(image_views):
        raise ValueError('An image bufferView is also referenced by geometry')
    packed=bytearray()
    preserved_hashes=[]
    for index,view in enumerate(source.get('bufferViews',[])):
        packed.extend(b'\0'*((-len(packed))%4))
        offset=len(packed)
        payload=encoded_views.get(index)
        if payload is None:
            payload=slice_view(source,binary,index)
            preserved_hashes.append((index,hashlib.sha256(payload).hexdigest()))
        packed.extend(payload)
        document['bufferViews'][index]['byteOffset']=offset
        document['bufferViews'][index]['byteLength']=len(payload)
    document['buffers'][0]['byteLength']=len(packed)
    output=build_glb(document,bytes(packed),chunks)
    output_path=Path(output_path)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    temporary=output_path.with_name(output_path.name+f'.tmp-{os.getpid()}')
    temporary.write_bytes(output)
    # Validate the actual serialized result before replacing any destination.
    try:
        _,verified,new_binary,_=read_glb(temporary)
        mutable={'images','bufferViews','buffers'}
        for key in set(source)|set(verified):
            if key not in mutable and source.get(key)!=verified.get(key):
                raise AssertionError(f'Scene/geometry field changed: {key}')
        for index,digest in preserved_hashes:
            if hashlib.sha256(slice_view(verified,new_binary,index)).hexdigest()!=digest:
                raise AssertionError(f'Geometry bufferView changed: {index}')
        before_bounds=bounds(source);after_bounds=bounds(verified)
        if before_bounds!=after_bounds: raise AssertionError('World or POSITION bounds changed')
        for old,new in zip(source['images'],verified['images']):
            if {k:v for k,v in old.items() if k!='mimeType'}!={k:v for k,v in new.items() if k!='mimeType'}:
                raise AssertionError('Image identity/reference changed')
        for index,view in enumerate(verified['bufferViews']):
            if view['byteOffset']%4: raise AssertionError('Unaligned bufferView')
        os.replace(temporary,output_path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    report={
        'input':str(Path(input_path).resolve()),'output':str(output_path.resolve()),
        'source_bytes':len(original),'output_bytes':len(output),
        'reduction_percent':round((1-len(output)/len(original))*100,2),
        'image_source_bytes':sum(source['bufferViews'][i]['byteLength'] for i in image_views),
        'image_output_bytes':sum(len(v) for v in encoded_views.values()),
        'image_count':len(source.get('images',[])),'material_count':len(source.get('materials',[])),
        'texture_count':len(source.get('textures',[])),'accessor_count':len(source.get('accessors',[])),
        'preserved_geometry_buffer_views':len(preserved_hashes),
        'verification':'All non-image bufferViews byte-identical; scene, accessor, mesh, material, texture and node dictionaries equal; image references and world bounds unchanged; all views four-byte aligned.',
        'source_world_bounds':before_bounds['world_aabb_from_accessor_bounds'],
        'output_world_bounds':after_bounds['world_aabb_from_accessor_bounds'],
        'max_texture_dimension':max_size,'requested_jpeg_quality':quality,
        'images':reports,'elapsed_seconds':round(time.monotonic()-started,3),
    }
    report_path=Path(report_path) if report_path else output_path.with_suffix(output_path.suffix+'.qa.json')
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    return report


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--max-size',type=int,default=1024)
    parser.add_argument('--quality',type=int,default=88)
    args=parser.parse_args()
    if not 64<=args.max_size<=8192: parser.error('--max-size must be between 64 and 8192')
    if not 50<=args.quality<=95: parser.error('--quality must be between 50 and 95')
    report=optimize(args.input,args.output,args.max_size,args.quality,args.report)
    print(json.dumps({key:value for key,value in report.items() if key!='images'},ensure_ascii=False,indent=2))

if __name__=='__main__': main()

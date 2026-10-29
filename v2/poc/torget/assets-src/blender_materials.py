"""Exportable Principled materials for the Kvarnbyn PoC.
Import this module from Blender. UV coordinates must already be in repeats;
`tile_size_m` in the manifest tells the caller how many meters make one repeat.
"""
from pathlib import Path
import json
import bpy

ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT / 'manifest.json').read_text())


def image_node(nodes, path, color_space):
    image = bpy.data.images.load(str(ROOT / path), check_existing=True)
    image.colorspace_settings.name = color_space
    node = nodes.new('ShaderNodeTexImage')
    node.image = image
    node.interpolation = 'Linear'
    node.extension = 'REPEAT'
    return node


def pbr_material(key, name=None, base_color=None, normal_strength=0.5, roughness=None):
    """Make glTF-compatible nodes.
    base_color overrides albedo rather than using unsupported procedural node trees.
    This is useful for painted wood: keep scanned normal/roughness, set house paint.
    """
    spec = MANIFEST['materials'][key]
    material = bpy.data.materials.new(name or f'PH_{key}')
    material.use_nodes = True
    material.diffuse_color = base_color or (0.6, 0.6, 0.6, 1.0)
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    material.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    bsdf.inputs['Metallic'].default_value = 0.0
    if base_color is None:
        node = image_node(nodes, spec['maps']['albedo']['path'], 'sRGB')
        material.node_tree.links.new(node.outputs['Color'], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = base_color
    if roughness is None:
        node = image_node(nodes, spec['maps']['roughness']['path'], 'Non-Color')
        material.node_tree.links.new(node.outputs['Color'], bsdf.inputs['Roughness'])
    else:
        bsdf.inputs['Roughness'].default_value = roughness
    texture = image_node(nodes, spec['maps']['normal']['path'], 'Non-Color')
    normal = nodes.new('ShaderNodeNormalMap')
    normal.inputs['Strength'].default_value = normal_strength
    material.node_tree.links.new(texture.outputs['Color'], normal.inputs['Color'])
    material.node_tree.links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
    material['source_page'] = spec['source_page']
    material['license'] = spec['license']
    material['tile_size_m'] = spec['tile_size_m']
    return material


def solid_material(name, color, roughness=0.8, metallic=0.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    return material

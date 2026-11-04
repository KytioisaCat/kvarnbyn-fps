extends RefCounted

## Shared material for the existing water mesh. The field encodes directions,
## not colours, and must be sampled without sRGB conversion.
const ShaderSource = preload("res://shaders/water.gdshader")
const FIELD_PATH := "res://assets/river_flow.png"
const META_PATH := "res://assets/river_flow.json"
var field: Texture2D
var metadata: Dictionary = {}
var bounds := Vector4.ZERO
var materials: Array[ShaderMaterial] = []
var surfaces := 0
var loaded := false

func load_field() -> bool:
	if not FileAccess.file_exists(META_PATH) or not ResourceLoader.exists(FIELD_PATH):
		push_warning("Åns flödesfält saknas; kör återbyggnaden.")
		return false
	var value = JSON.parse_string(FileAccess.get_file_as_string(META_PATH))
	if not value is Dictionary or not value.get("bounds",[]) is Array or value.bounds.size()!=4:
		return false
	metadata = value
	bounds = Vector4(float(value.bounds[0]),float(value.bounds[1]),float(value.bounds[2]),float(value.bounds[3]))
	if bounds.z<=bounds.x or bounds.w<=bounds.y:
		return false
	field = load(FIELD_PATH) as Texture2D
	loaded = field!=null and field.get_width()>0 and field.get_height()>0
	return loaded

func material_for(original: Material) -> ShaderMaterial:
	surfaces += 1
	var colour := Color("31575a")
	if original is BaseMaterial3D:
		colour = original.albedo_color
	for existing in materials:
		if existing.get_shader_parameter("water_color") == colour:
			return existing
	var material := ShaderMaterial.new()
	material.shader = ShaderSource
	material.resource_name = "WaterFlow"
	material.set_shader_parameter("water_color",colour)
	material.set_shader_parameter("use_flow_field",loaded)
	if loaded:
		material.set_shader_parameter("flow_field",field)
		material.set_shader_parameter("flow_bounds",bounds)
	materials.append(material)
	return material

func snapshot() -> Dictionary:
	return {"loaded":loaded,"size":[field.get_width(),field.get_height()] if field!=null else [0,0],
		"bounds":[bounds.x,bounds.y,bounds.z,bounds.w],"surfaces":surfaces,"materials":materials.size(),
		"geometry_displacement":false,"new_colliders":0,"source":"existing downstream water profiles"}

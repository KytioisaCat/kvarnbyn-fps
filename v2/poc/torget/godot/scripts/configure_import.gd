extends SceneTree

## Run once after the first --import, then run --import again to generate UV2.
func _initialize() -> void:
	var configuration := ConfigFile.new()
	var path := "res://assets/world.glb.import"
	var error := configuration.load(path)
	if error != OK:
		push_error("Importera assets/world.glb en gång innan configure_import.gd körs.")
		quit(2)
		return
	configuration.set_value("params", "meshes/light_baking", 2)
	configuration.set_value("params", "meshes/lightmap_texel_size", 0.5)
	configuration.set_value("params", "meshes/generate_lods", true)
	configuration.set_value("params", "meshes/create_shadow_meshes", true)
	configuration.set_value("params", "import_script/path", "res://scripts/import_world.gd")
	configuration.set_value("params", "animation/import", false)
	# Avoid generating lightmap UVs for vegetation and invisible collision meshes.
	var glb := FileAccess.open("res://assets/world.glb", FileAccess.READ)
	glb.seek(12)
	var json_size := glb.get_32()
	glb.get_32()
	var document: Dictionary = JSON.parse_string(glb.get_buffer(json_size).get_string_from_utf8())
	var overrides: Dictionary = configuration.get_value("params", "_subresources", {})
	var meshes: Dictionary = overrides.get("meshes", {})
	for mesh in document.get("meshes", []):
		var mesh_name := str(mesh.get("name", ""))
		if "broadleaf" in mesh_name.to_lower() or "_boards" in mesh_name.to_lower() or mesh_name.to_upper().begins_with("COL_"):
			var mesh_options: Dictionary = meshes.get(mesh_name, {})
			mesh_options["generate/lightmap_uv"] = 2
			meshes[mesh_name] = mesh_options
			# glTF naming version 2 prefixes resources with the source file's stem.
			meshes["world_" + mesh_name] = mesh_options.duplicate()
	overrides["meshes"] = meshes
	configuration.set_value("params", "_subresources", overrides)
	error = configuration.save(path)
	print("KVARNBYN_IMPORT_CONFIG ", error)
	quit(error)

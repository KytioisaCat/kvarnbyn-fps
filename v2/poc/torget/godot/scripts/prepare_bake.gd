extends SceneTree

const Lighting = preload("res://scripts/lighting.gd")

func _initialize() -> void:
	call_deferred("prepare")

func prepare() -> void:
	if not ResourceLoader.exists("res://assets/world.glb"):
		push_error("assets/world.glb saknas eller är inte importerad.")
		quit(2)
		return
	var scene_root := Node3D.new()
	scene_root.name = "BakedWorld"
	root.add_child(scene_root)
	var world: Node3D = load("res://assets/world.glb").instantiate()
	world.name = "World"
	scene_root.add_child(world)
	world.owner = scene_root
	var environment := Lighting.make_environment()
	scene_root.add_child(environment)
	environment.owner = scene_root
	var sun := Lighting.make_sun()
	scene_root.add_child(sun)
	sun.owner = scene_root
	var lightmap := LightmapGI.new()
	lightmap.name = "BakatLjus"
	lightmap.quality = LightmapGI.BAKE_QUALITY_MEDIUM
	lightmap.bounces = 2
	lightmap.max_texture_size = 4096
	lightmap.generate_probes_subdiv = LightmapGI.GENERATE_PROBES_SUBDIV_4
	lightmap.directional = false
	lightmap.use_denoiser = true
	lightmap.environment_mode = LightmapGI.ENVIRONMENT_MODE_CUSTOM_COLOR
	lightmap.environment_custom_color = Color("c6d0d7")
	lightmap.environment_custom_energy = 0.35
	# Giving the light data a path avoids an interactive save dialog when baking.
	var light_data := LightmapGIData.new()
	var data_error := ResourceSaver.save(light_data, "res://assets/torget.lmbake", ResourceSaver.FLAG_CHANGE_PATH)
	if data_error != OK:
		push_error("Kunde inte förbereda ljusdata: %s" % data_error)
		quit(data_error)
		return
	light_data.take_over_path("res://assets/torget.lmbake")
	lightmap.light_data = light_data
	scene_root.add_child(lightmap)
	lightmap.owner = scene_root
	var camera := Camera3D.new()
	camera.name = "Förhandskamera"
	var position_value := Vector3(0, 3, 14)
	var target_value := Vector3(0, 2, 0)
	if FileAccess.file_exists("res://assets/world_meta.json"):
		var metadata = JSON.parse_string(FileAccess.get_file_as_string("res://assets/world_meta.json"))
		if metadata is Dictionary and not metadata.get("views", []).is_empty():
			var view: Dictionary = metadata["views"][0]
			var pos: Array = view.get("position", [0, 3, 14])
			var target: Array = view.get("target", [0, 2, 0])
			position_value = Vector3(float(pos[0]), float(pos[1]), float(pos[2]))
			target_value = Vector3(float(target[0]), float(target[1]), float(target[2]))
	scene_root.add_child(camera)
	camera.owner = scene_root
	camera.position = position_value
	camera.look_at(target_value)
	camera.current = false
	var packed := PackedScene.new()
	var pack_error := packed.pack(scene_root)
	if pack_error == OK:
		pack_error = ResourceSaver.save(packed, "res://assets/baked_world.tscn")
	print("KVARNBYN_BAKE_SCENE ", pack_error)
	quit(pack_error)

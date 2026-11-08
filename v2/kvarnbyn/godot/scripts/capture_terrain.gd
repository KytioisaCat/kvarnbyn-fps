extends SceneTree
## Reproducible, silent native views of the real terrain and its street edges.
var world: Node3D

func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	call_deferred("run")

func run() -> void:
	var out := ProjectSettings.globalize_path("res://../evidence/terrain")
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--output="):
			out = argument.trim_prefix("--output=")
	DirAccess.make_dir_recursive_absolute(out)
	world = load("res://main.tscn").instantiate()
	root.add_child(world)
	while not world.world_ready:
		await process_frame
	world.begin_walk()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	world.canvas_layer.hide()
	world.player.set_process(false)
	world.player.set_physics_process(false)
	world.player.weapon.hide()
	var camera := Camera3D.new()
	world.add_child(camera)
	camera.make_current()
	camera.fov = 67.0
	paused = true
	var views := [
		["glasberget-fran-start", Vector3(340, 54.9, 153), Vector3(490, 60, 250)],
		["glasberget-klippfasad", Vector3(388, 56, 180), Vector3(490, 62, 255)],
		["lilla-glasberget", Vector3(145, 35, 190), Vector3(235, 46, 152)],
		["glasberget", Vector3(405, 88, 380), Vector3(635, 66, 565)],
		["hojdskillnader", Vector3(110, 97, 280), Vector3(220, 33, 100)],
		["mur-forsaker", Vector3(6, 7, 142), Vector3(27, 6, 146)],
		["mur-vaster", Vector3(-103, 5, 103), Vector3(-105, 0, 83)],
	]
	for view in views:
		camera.position = view[1]
		camera.look_at(view[2])
		for frame in range(90):
			await process_frame
		await RenderingServer.frame_post_draw
		var path := out.path_join(str(view[0]) + ".png")
		assert(root.get_texture().get_image().save_png(path) == OK)
		print("KVARNBYN_TERRAIN_CAPTURE ", path)
	quit()

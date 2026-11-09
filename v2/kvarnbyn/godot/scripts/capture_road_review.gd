extends SceneTree
func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	call_deferred("run")
func run() -> void:
	root.size = Vector2i(1600, 1000)
	var world = load("res://main.tscn").instantiate()
	root.add_child(world)
	for frame in range(600):
		await physics_frame
		if world.world_ready: break
	world.begin_walk()
	world.player.set_physics_process(false)
	world.player.set_process(false)
	world.player.weapon.hide()
	world.player.weapon.set_process(false)
	world.canvas_layer.hide()
	var phase := "before"
	var views_file := "res://../reference/vag-hus/views.json"
	var image_dir := "res://../evidence/roads"
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--phase="):phase = arg.trim_prefix("--phase=")
		if arg.begins_with("--views="):views_file = arg.trim_prefix("--views=")
		if arg.begins_with("--image-dir="):image_dir = arg.trim_prefix("--image-dir=")
	var cases: Array = JSON.parse_string(FileAccess.get_file_as_string(views_file))
	var out := ProjectSettings.globalize_path(image_dir.path_join(phase))
	DirAccess.make_dir_recursive_absolute(out)
	for study in cases:
		world.player.camera.fov = float(study.get("fov_degrees",67.0))
		var point := Vector3(float(study.camera_xz[0]), 0, float(study.camera_xz[1]))
		point = world.ground_position(point)
		world.player.place_at(point + Vector3.UP * 0.05, 0, 0, false)
		var target := Vector3(float(study.target_xz[0]), 0, float(study.target_xz[1]))
		target = world.ground_position(target) + Vector3.UP * 1.4
		if study.has("target_above_camera_m"):
			target.y = world.player.camera.global_position.y + float(study.target_above_camera_m)
		world.player.look_toward(target)
		for frame in range(10):await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(out.path_join(str(study.id) + ".png"))
		print("ROAD_REVIEW_CAPTURE ", phase, " ", study.id)
	quit()

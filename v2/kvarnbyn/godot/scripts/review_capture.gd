extends SceneTree

## Editor executable only: quiet native captures at fixed x/z, eye above actual COL.
## Release templates disable --script overrides; use world.gd --view/--capture there.
## --script res://scripts/review_capture.gd -- --explore --spec=/absolute/views.json --out=/absolute/folder
func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	call_deferred("run")

func run() -> void:
	var opts := {}
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--"):
			var pair := arg.trim_prefix("--").split("=", true, 1)
			opts[pair[0]] = pair[1] if pair.size() > 1 else "1"
	if not opts.has("explore") or not opts.has("spec") or not opts.has("out"):
		push_error("review_capture needs --explore, --spec and --out")
		quit(2)
		return
	var views = JSON.parse_string(FileAccess.get_file_as_string(opts.spec))
	if not views is Array or DisplayServer.get_name() == "headless":
		push_error("review_capture needs native rendering and an array of camera specifications")
		quit(2)
		return
	var world = load("res://main.tscn").instantiate()
	root.add_child(world)
	while not world.world_ready:
		await physics_frame
	world.canvas_layer.visible = false
	DirAccess.make_dir_recursive_absolute(opts.out)
	var records := []
	for spec in views:
		var x := float(spec.xz[0])
		var z := float(spec.xz[1])
		var ray := PhysicsRayQueryParameters3D.create(Vector3(x, 120, z), Vector3(x, -50, z), 1)
		var hit: Dictionary = world.get_world_3d().direct_space_state.intersect_ray(ray)
		if hit.is_empty():
			push_error("No actual floor at review camera " + str(spec.id))
			quit(3)
			return
		var view := {"id": spec.id, "name": spec.id, "position": [x, hit.position.y + 1.7, z], "target": spec.target}
		world.metadata["views"] = [view]
		world.set_view(0)
		for frame in range(int(opts.get("frames", "150"))):
			await process_frame
		await RenderingServer.frame_post_draw
		var path: String = str(opts.out).path_join(str(spec.id) + ".png")
		var error := root.get_texture().get_image().save_png(path)
		if error != OK:
			push_error("Cannot save review image " + path)
			quit(4)
			return
		var record := {"view": view, "floor_y": hit.position.y, "snapshot": world.snapshot(), "path": path}
		records.append(record)
		print("KVARNBYN_REVIEW_CAPTURE ", JSON.stringify(record))
	var output := FileAccess.open(str(opts.out).path_join("cameras.json"), FileAccess.WRITE)
	output.store_string(JSON.stringify(records, "\t"))
	world.queue_free()
	await process_frame
	quit(0)

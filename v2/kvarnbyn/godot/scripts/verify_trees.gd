extends SceneTree

func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	call_deferred("run")

func run() -> void:
	var world: Node3D = load("res://main.tscn").instantiate()
	root.add_child(world)
	while not world.world_ready:
		await physics_frame
	var groups := 0
	var instances := 0
	var bad := 0
	for group in world.world_instance.find_children("*", "MultiMeshInstance3D", true, false):
		groups += 1
		if not group.has_meta("instance_transforms"):
			bad += 1
			continue
		var transforms: Array = group.get_meta("instance_transforms")
		if group.multimesh == null or transforms.size() != group.multimesh.instance_count:
			bad += 1
		for transform in transforms:
			if absf(transform.basis.determinant()) < 0.000001:
				bad += 1
		instances += transforms.size()
	var passed: bool = groups > 0 and instances > 0 and bad == 0 and world.world_stats.get("vegetation_mesh_instances", 0) == instances
	print("KVARNBYN_TREES_CHECK ", JSON.stringify({"passed": passed, "groups": groups, "mesh_instances": instances, "bad": bad,
		"scope": "serialized CPU placement and runtime restore; visibility also checked in native captures"}))
	world.queue_free()
	await process_frame
	await process_frame
	quit(0 if passed else 2)

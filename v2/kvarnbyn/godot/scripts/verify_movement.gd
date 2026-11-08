extends SceneTree

func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	call_deferred("verify")

func verify() -> void:
	var world = load("res://main.tscn").instantiate()
	root.add_child(world)
	for frame in range(600):
		await physics_frame
		if world.world_ready:
			break
	var checker = load("res://scripts/movement_check.gd").new()
	world.add_child(checker)
	var result: Dictionary = await checker.run(world)
	print("KVARNBYN_MOVEMENT_CHECK ", JSON.stringify(result))
	paused = false
	world.queue_free()
	await process_frame
	quit(0 if result.passed else 3)

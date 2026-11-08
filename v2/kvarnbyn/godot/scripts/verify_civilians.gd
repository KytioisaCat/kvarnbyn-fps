extends SceneTree
func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	call_deferred("run")
func run() -> void:
	var world = load("res://main.tscn").instantiate()
	root.add_child(world)
	for frame in range(600):
		await physics_frame
		if world.world_ready: break
	var report: Dictionary = await preload("res://scripts/civilian_check.gd").new().run(world)
	var file := FileAccess.open("res://../evidence/civilian-check.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t"))
	print("KVARNBYN_CIVILIAN_CHECK ", JSON.stringify(report))
	quit(0 if report.passed else 3)

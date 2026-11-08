extends SceneTree
const TerrainCheck = preload("res://scripts/terrain_check.gd")

func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	call_deferred("run")

func run() -> void:
	var scene: Node3D = load("res://assets/world.glb").instantiate()
	root.add_child(scene)
	await physics_frame
	await physics_frame
	var metadata: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/world_meta.json"))
	var report := TerrainCheck.new().run(scene, metadata)
	print("KVARNBYN_TERRAIN_CHECK ", JSON.stringify(report))
	quit(0 if report.passed else 1)

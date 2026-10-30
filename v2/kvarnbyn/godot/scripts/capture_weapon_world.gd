extends SceneTree

## Native integration captures using the real world, lighting, player and HUD.
## Godot --audio-driver Dummy --path v2/kvarnbyn/godot --script res://scripts/capture_weapon_world.gd
var world: Node3D
var out := ""
var snapshots := {}

func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	call_deferred("run")

func tick(player: Node, weapon: Node, frames: int) -> void:
	player.input_suspended = false
	for frame in range(frames):
		weapon._process(1.0 / 60.0)
		player._process(1.0 / 60.0)
	player.input_suspended = true

func capture(label: String) -> void:
	await create_timer(1.0, true).timeout
	for frame in range(45):
		await process_frame
	await RenderingServer.frame_post_draw
	var path := out.path_join("ak5_world_" + label + ".png")
	var error := root.get_texture().get_image().save_png(path)
	print("WEAPON_WORLD_CAPTURE ", path, " error=", error)
	snapshots[label] = world.player.weapon.visual_snapshot()

func run() -> void:
	out = ProjectSettings.globalize_path("res://").trim_suffix("/").get_base_dir().path_join("evidence/weapon")
	DirAccess.make_dir_recursive_absolute(out)
	world = load("res://main.tscn").instantiate()
	root.add_child(world)
	current_scene = world
	while not world.world_ready:
		await process_frame
	world.begin_walk()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	var player: Node = world.player
	var weapon: Node = player.weapon
	player.bot_input = Vector2.ZERO
	player.input_suspended = true
	# Let the freshly spawned allies land before freezing the integration view.
	for frame in range(60):
		await physics_frame
	paused = true
	player.velocity = Vector3.ZERO
	player.set_process(false)
	player.set_physics_process(false)
	weapon.set_process(false)
	weapon.bot_ads = false
	tick(player, weapon, 90)
	await capture("hip")
	weapon.bot_ads = true
	tick(player, weapon, 90)
	await capture("ads")
	weapon.bot_ads = false
	tick(player, weapon, 90)
	weapon.mag = 18
	weapon.start_reload()
	tick(player, weapon, 40)
	await capture("reload")
	var file := FileAccess.open(out.path_join("weapon_world_qa.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify({"captures": snapshots, "world": world.snapshot()}, "\t"))
	print("KVARNBYN_WEAPON_WORLD ", JSON.stringify(snapshots))
	world.queue_free()
	await process_frame
	quit()

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
	if world.game: world.game.running = false
	world.player.set_physics_process(false)
	world.player.set_process(false)
	world.player.weapon.set_process(false)
	world.player.weapon.hide()
	for actor in world.civilians.people:
		actor.set_physics_process(false)
		actor.global_position = actor.home
	var out := ProjectSettings.globalize_path("res://../evidence/civilians")
	DirAccess.make_dir_recursive_absolute(out)
	for person in world.civilians.people:
		var approach: Vector3 = world.civilians.approach_position(person)
		world.player.place_at(approach, 0, 0, false)
		world.player.look_toward(person.global_position + Vector3.UP * 1.15)
		person.face_point(approach, 1.0)
		person.play_clip("Idle")
		person.animator.advance(0.1)
		for frame in range(10): await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(out.path_join("world-" + str(person.data.id) + ".png"))
		if str(person.data.id) == "lars":
			world.civilians.try_talk()
			for frame in range(4): await process_frame
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(out.path_join("world-conversation.png"))
			world.civilians.card_left = 0.0
		print("CIVILIAN_WORLD_CAPTURE ", person.data.id)
	quit()

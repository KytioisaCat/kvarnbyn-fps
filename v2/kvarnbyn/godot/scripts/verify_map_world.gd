extends SceneTree

## Real world/input/pause integration; always silent. No substitute game/map.
var world
var checks := []
var options := {}

func _initialize() -> void:
	AudioServer.set_bus_mute(0,true)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--"):
			var pair := arg.trim_prefix("--").split("=",true,1)
			options[pair[0]] = pair[1] if pair.size()>1 else "1"
	call_deferred("run")

func check(id: String, passed: bool) -> void:
	checks.append({"test":id,"passed":passed})

func press(key: Key) -> void:
	var event := InputEventKey.new()
	event.keycode = key
	event.physical_keycode = key
	event.pressed = true
	Input.parse_input_event(event)
	await process_frame
	event = InputEventKey.new()
	event.keycode = key
	event.physical_keycode = key
	event.pressed = false
	Input.parse_input_event(event)
	await process_frame

func run() -> void:
	world = load("res://main.tscn").instantiate()
	root.add_child(world)
	for frame in range(600):
		await physics_frame
		if world.world_ready:break
	check("actual_world_ready",world.world_ready)
	check("actual_combat_loaded",world.game != null)
	if not world.world_ready or world.game == null:
		await finish()
		return
	var map = world.tactical_map
	check("real_map_assets_loaded",map != null and map.map_loaded)
	if map == null or not map.map_loaded:
		await finish()
		return
	world.begin_walk()
	world.update_tactical_map()
	await process_frame
	check("minimap_visible_during_play",map.visible and not map.expanded)
	var old_mouse := Input.mouse_mode
	var children: int = map.get_child_count()
	await press(KEY_M)
	check("physical_m_opens_full_map",map.expanded and map.visible)
	check("map_pauses_actual_tree",paused)
	check("map_releases_pointer",Input.mouse_mode == Input.MOUSE_MODE_VISIBLE)
	var position: Vector3 = world.player.global_position
	var elapsed: float = world.game.elapsed
	for frame in range(8):await physics_frame
	check("map_stops_player_and_battle",world.player.global_position.distance_to(position)<.0001 and absf(world.game.elapsed-elapsed)<.0001)
	await press(KEY_ESCAPE)
	check("escape_closes_map_and_resumes",not map.expanded and not paused and not world.overlay.opening)
	check("pointer_mode_restored",Input.mouse_mode == old_mouse)
	for i in range(3):
		await press(KEY_M)
		await press(KEY_M)
	check("repeated_m_toggles_resume_without_extra_controls",not map.expanded and not paused and map.get_child_count()==children)
	await press(KEY_ESCAPE)
	check("normal_escape_pause_menu_works",paused and world.overlay.opening)
	await press(KEY_M)
	check("m_respects_existing_pause_menu",paused and world.overlay.opening and not map.expanded)
	await press(KEY_ESCAPE)
	check("pause_menu_resumes_normally",not paused and not world.overlay.opening)
	await press(KEY_M)
	map.close_button.pressed.emit()
	await process_frame
	check("close_button_resumes_actual_world",not paused and not map.expanded)
	var original_owner: String = world.game.caps[0].owner
	world.game.caps[0].owner = "ally"
	map.last_update_msec = -1000
	world.update_tactical_map()
	check("actual_zone_ownership_reaches_map",map.zone_markers.size()==world.game.caps.size() and map.zone_markers[0].owner=="ally")
	check("no_enemy_position_radar",map.snapshot().enemy_positions==0)
	world.game.caps[0].owner = original_owner
	world.game.over = true
	world._on_game_ended(false)
	world.update_tactical_map()
	check("end_screen_hides_map",not map.visible and not map.expanded)
	await press(KEY_M)
	check("m_does_not_cover_end_screen",not map.expanded)
	await finish()

func finish() -> void:
	var passed := not checks.is_empty()
	for item in checks:passed = passed and bool(item.passed)
	var report := {"passed":passed,"scope":"actual imported world, combat, map, physical M/Esc input and pause","checks":checks}
	if options.has("output"):
		var file := FileAccess.open(str(options.output),FileAccess.WRITE)
		if file != null:file.store_string(JSON.stringify(report,"\t"))
	print("KVARNBYN_MAP_WORLD_CHECK ",JSON.stringify(report))
	paused = false
	if world != null:world.queue_free()
	await process_frame
	quit(0 if passed else 3)

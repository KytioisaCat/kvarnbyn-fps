extends SceneTree

## Integration checks on real Godot collision bodies, not a numerical imitation of movement.
## --fixed-fps 60 makes the simulated seconds run without a wall-clock wait in headless mode.

const Soldier = preload("res://scripts/soldier.gd")
const NavGraph = preload("res://scripts/navgraph.gd")

class Target:
	extends Node3D
	var alive := true
	var crouching := false
	var combat_enabled := true
	var received_damage := 0.0
	func damage(amount: float, _from: Vector3) -> void:
		received_damage += amount

class ArenaGame:
	extends Node
	var running := true
	var nav = NavGraph.new()
	var player: Node3D
	var enemies: Array = []
	var allies: Array = []
	var fx = null
	var goal := Vector3(0, 0, -18)
	func cap_target_for(_soldier: Node) -> Dictionary:
		return {"id": "test", "goal": goal, "pos": goal, "radius": 5.0}
	func nearest_hostile(soldier: Node, distance: float) -> Node3D:
		return player if player.combat_enabled and soldier.global_position.distance_to(player.global_position) < distance else null
	func on_soldier_killed(_soldier: Node, _attacker: Node, _head: bool) -> void:
		pass

var arena: Node3D
var game: ArenaGame
var target: Target
var samples := 0
var penetrations := 0
var bounds_to_check: Array[AABB] = []
var report := {}

func finish(code: int) -> void:
	# Release the live scene before terminating so the verifier does not mask leaks.
	for child in root.get_children():
		child.queue_free()
	await process_frame
	await process_frame
	quit(code)

func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	seed(34781)
	call_deferred("run_world_check" if "--world" in OS.get_cmdline_user_args() else "run_checks")

func solid(label: String, location: Vector3, size: Vector3, check_penetration := true) -> void:
	var body := StaticBody3D.new()
	body.name = label
	body.position = location
	body.collision_layer = 1
	var collider := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	collider.shape = shape
	body.add_child(collider)
	arena.add_child(body)
	if check_penetration:
		bounds_to_check.append(AABB(location - size * 0.5, size))

func reset_arena() -> void:
	if arena != null:
		arena.queue_free()
		await physics_frame
		await physics_frame
	arena = Node3D.new()
	arena.name = "PhysicsArena"
	root.add_child(arena)
	bounds_to_check.clear()
	solid("Ground", Vector3(0, -0.15, 0), Vector3(100, 0.3, 100), false)
	game = ArenaGame.new()
	arena.add_child(game)
	target = Target.new()
	target.position = Vector3(0, 0, -18)
	arena.add_child(target)
	game.player = target
	configure_nav([Vector3(0, 0, 18), Vector3(0, 0, -18)])

func configure_nav(points: Array[Vector3]) -> void:
	game.nav = NavGraph.new()
	for index in range(points.size()):
		game.nav.points.append(points[index])
		game.nav.main_ids.append(index)
		game.nav.astar.add_point(index, points[index])
		game.nav.grid.get_or_add(game.nav._cell(points[index]), []).append(index)
		if index > 0:
			game.nav.astar.connect_points(index - 1, index)

func spawn(location: Vector3):
	var soldier = Soldier.new()
	soldier.setup(game, "enemy", {"speed": [3.2, 3.2], "hp": 1000, "sight_m": 75,
		"engage_m": 70, "fire_interval_s": [0.8, 1.0], "damage": [6, 11]})
	arena.add_child(soldier)
	soldier.global_position = location
	game.enemies.append(soldier)
	if soldier.muzzle == null:
		push_error("Soldatens visuella kontrakt saknar Muzzle. Importera modellen innan provet körs.")
		quit(4)
	return soldier

func simulate(frames: int) -> void:
	for frame in range(frames):
		await physics_frame
		for soldier in game.enemies:
			if not is_instance_valid(soldier):
				continue
			samples += 1
			var center: Vector3 = soldier.global_position + Vector3.UP * 0.8
			for obstacle in bounds_to_check:
				if obstacle.grow(-0.1).has_point(center):
					penetrations += 1

func run_checks() -> void:
	var start := Time.get_ticks_usec()
	await reset_arena()
	solid("SideCover", Vector3(5, 1.5, 0), Vector3(4, 3, 1))
	var starts: Array[Vector3] = []
	for index in range(6):
		var location := Vector3(float(index - 3) * 3.5, 0.15, 12 + (index % 2) * 4)
		starts.append(location)
		spawn(location)
	await simulate(720)
	var moved := 0
	var flanks := 0
	var rays := 0
	var combat := 0.0
	var mobile_combat := 0.0
	var maximum_displacement := 0.0
	for index in range(game.enemies.size()):
		var soldier = game.enemies[index]
		var displacement: float = soldier.global_position.distance_to(starts[index])
		maximum_displacement = maxf(maximum_displacement, displacement)
		if displacement > 3.0:
			moved += 1
		var state: Dictionary = soldier.ai_state()
		flanks += int(state.flanks)
		rays += int(state.rays)
		combat += float(state.combat_s)
		mobile_combat += float(state.moving_combat_s)
	report["flanking"] = {"soldiers": 6, "simulated_s": 12, "displaced_over_3m": moved,
		"flank_choices": flanks, "maximum_displacement_m": maximum_displacement,
		"moving_fraction_when_firing": mobile_combat / maxf(0.01, combat), "rays": rays,
		"passed": moved >= 4 and flanks >= 6 and mobile_combat / maxf(0.01, combat) > 0.45}
	await reset_arena()
	solid("SideCover", Vector3(5, 1.5, 0), Vector3(4, 3, 1))
	var defender = spawn(Vector3(0, 0.15, 6))
	await simulate(45)
	defender.hit(12, false, target.global_position + Vector3.UP * 1.3, target)
	var hidden_frames := 0
	for frame in range(240):
		await simulate(1)
		if not defender.can_see:
			hidden_frames += 1
	var cover_state: Dictionary = defender.ai_state()
	report["cover_after_hit"] = {"cover_choices": cover_state.cover_moves, "hidden_s": hidden_frames / 60.0,
		"position": [defender.position.x, defender.position.y, defender.position.z],
		"passed": int(cover_state.cover_moves) >= 1 and hidden_frames > 20}
	game.running = false
	solid("NewWall", Vector3(0, 1.6, -6), Vector3(30, 3.2, 1))
	await physics_frame
	await physics_frame
	defender.target = target
	defender.can_see = true # cached visibility deliberately predates the new wall.
	var damage_before := target.received_damage
	var blocked_before: int = defender.ai_state().blocked_shots
	defender._shoot(defender.global_position.distance_to(target.global_position), false)
	report["fresh_shot_line"] = {"blocked_shots": int(defender.ai_state().blocked_shots) - blocked_before,
		"damage_through_wall": target.received_damage - damage_before,
		"passed": int(defender.ai_state().blocked_shots) > blocked_before and target.received_damage == damage_before}
	await reset_arena()
	var low_cover_soldier = spawn(Vector3(0, 0.15, 6))
	await simulate(30)
	game.running = false
	# Freeze this real imported pose while constructing the narrow height gap fixture.
	low_cover_soldier.visual.process_mode = Node.PROCESS_MODE_DISABLED
	var barrel: Vector3 = low_cover_soldier.muzzle.global_position
	var eye: Vector3 = low_cover_soldier.global_position + Vector3.UP * 1.55
	var aim: Vector3 = target.global_position + Vector3.UP * 1.3
	var wall_z: float = minf(eye.z, barrel.z) - 2.0
	var muzzle_height := lerpf(barrel.y, aim.y, (wall_z - barrel.z) / (aim.z - barrel.z))
	var eye_height := lerpf(eye.y, aim.y, (wall_z - eye.z) / (aim.z - eye.z))
	var wall_top := (muzzle_height + eye_height) * 0.5
	solid("LowCover", Vector3(0, wall_top * 0.5, wall_z), Vector3(30, wall_top, 0.2))
	await physics_frame
	await physics_frame
	var space := low_cover_soldier.get_world_3d().direct_space_state
	var eye_clear := space.intersect_ray(PhysicsRayQueryParameters3D.create(eye, aim, 1)).is_empty()
	var muzzle_blocked := not space.intersect_ray(PhysicsRayQueryParameters3D.create(barrel, aim, 1)).is_empty()
	low_cover_soldier.target = target
	low_cover_soldier.can_see = true
	damage_before = target.received_damage
	blocked_before = int(low_cover_soldier.ai_state().blocked_shots)
	low_cover_soldier._shoot(low_cover_soldier.global_position.distance_to(target.global_position), false)
	report["low_cover_muzzle_line"] = {"eye_clear": eye_clear, "muzzle_blocked": muzzle_blocked,
		"eye_height_m": eye_height, "muzzle_height_m": muzzle_height,
		"blocked_shots": int(low_cover_soldier.ai_state().blocked_shots) - blocked_before,
		"damage_through_wall": target.received_damage - damage_before,
		"passed": eye_clear and muzzle_blocked and int(low_cover_soldier.ai_state().blocked_shots) > blocked_before and target.received_damage == damage_before}
	await reset_arena()
	solid("House", Vector3(0, 1.5, 0), Vector3(4, 3, 4))
	target.combat_enabled = false
	game.goal = Vector3(8, 0, 0)
	configure_nav([Vector3(-8, 0, 0), Vector3(-4, 0, 0), Vector3(-4, 0, -5),
		Vector3(4, 0, -5), Vector3(4, 0, 0), Vector3(8, 0, 0)])
	var traveller = spawn(Vector3(-8, 0.15, 0))
	await simulate(900)
	report["navigation_around_house"] = {"final_position": [traveller.position.x, traveller.position.y, traveller.position.z],
		"passed": traveller.position.x > 4.0 and traveller.position.distance_to(game.goal) < 4.0}
	await reset_arena()
	solid("UnmappedHouse", Vector3(0, 1.5, 0), Vector3(4, 3, 4))
	target.combat_enabled = false
	game.goal = Vector3(8, 0, 0)
	configure_nav([Vector3(-8, 0, 0), Vector3(8, 0, 0)])
	var blocked = spawn(Vector3(-4, 0.15, 0))
	await simulate(600)
	report["blocked_movement"] = {"escape_attempts": blocked.ai_state().escapes,
		"passed": int(blocked.ai_state().escapes) >= 1}
	var passed := penetrations == 0
	for value in report.values():
		passed = passed and bool(value.passed)
	report["collision_samples"] = samples
	report["wall_penetrations"] = penetrations
	report["wall_clock_s"] = (Time.get_ticks_usec() - start) / 1000000.0
	report["passed"] = passed
	print("KVARNBYN_SOLDIERS_CHECK ", JSON.stringify(report))
	save_report(report)
	await finish(0 if passed else 3)

func save_report(result: Dictionary) -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):
			var file := FileAccess.open(arg.trim_prefix("--output="), FileAccess.WRITE)
			if file != null:
				file.store_string(JSON.stringify(result, "\t") + "\n")

func run_world_check() -> void:
	print("KVARNBYN_SOLDIERS_START ", JSON.stringify({"pid": OS.get_process_id(), "display": DisplayServer.get_name()}))
	root.close_requested.connect(func(): print("KVARNBYN_SOLDIERS_WINDOW_CLOSE"))
	var scene: Node3D = load("res://main.tscn").instantiate()
	root.add_child(scene)
	while not scene.world_ready:
		await physics_frame
	print("KVARNBYN_SOLDIERS_WORLD_READY")
	scene.begin_walk()
	print("KVARNBYN_SOLDIERS_GAME_STARTED")
	var actual_game: Node = scene.game
	var actual_player: CharacterBody3D = scene.player
	for actor in actual_game.enemies + actual_game.allies:
		if actor.muzzle == null:
			var failure := {"passed": false, "valid_measurement": false, "reason": "Soldatmodellen saknar importerad Muzzle; visualintegrationen är inte redo."}
			print("KVARNBYN_SOLDIERS_WORLD ", JSON.stringify(failure))
			save_report(failure)
			quit(4)
			return
	var cap: Dictionary = actual_game.base_cap()
	var location: Vector3 = actual_game.nav.points[actual_game.nav.nearest(cap.pos)]
	# Start on the road's own elevation, avoiding a roof picked by a ray from 100 m up.
	var ground_query := PhysicsRayQueryParameters3D.create(location + Vector3.UP * 3, location + Vector3.DOWN * 4, 1)
	var ground_hit := scene.get_world_3d().direct_space_state.intersect_ray(ground_query)
	if not ground_hit.is_empty():
		location = ground_hit.position
	actual_player.revive(location + Vector3.UP * 0.2, 0.0)
	actual_player.hp = 100000
	actual_player.bot_input = Vector2.ZERO
	var placed := 0
	for point in actual_game.nav.points:
		var distance := Vector2(point.x - location.x, point.z - location.z).length()
		if distance > 14 and distance < 45 and placed < 10:
			var spawned = actual_game.spawn_soldier("enemy", point + Vector3.UP * 0.25)
			spawned.role = "assault"
			if placed == 0:
				actual_player.look_toward(spawned.global_position + Vector3.UP * 1.3)
			placed += 1
	var totals := {"decisions": 0.0, "flanks": 0.0, "cover_moves": 0.0, "search_moves": 0.0,
		"shots": 0.0, "blocked_shots": 0.0, "combat_s": 0.0, "moving_combat_s": 0.0,
		"rays": 0.0, "cpu_usec": 0.0, "travel_m": 0.0, "escapes": 0.0}
	var recorded := {}
	var previous_positions := {}
	var crossings := 0
	var segment_checks := 0
	var physics_times: Array[float] = []
	var process_times: Array[float] = []
	var fps_values: Array[float] = []
	var cpu_render_times: Array[float] = []
	var gpu_render_times: Array[float] = []
	var duration_s := 45.0
	var warmup_s := 0.0
	var screenshot_path := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--seconds="):
			duration_s = maxf(1.0, float(arg.trim_prefix("--seconds=")))
		if arg.begins_with("--warmup="):
			warmup_s = maxf(0.0, float(arg.trim_prefix("--warmup=")))
		if arg.begins_with("--screenshot="):
			screenshot_path = arg.trim_prefix("--screenshot=")
	var warmup_start := Time.get_ticks_usec()
	for frame in range(int(warmup_s * 60.0)):
		await physics_frame
	var warmup_wall_s := (Time.get_ticks_usec() - warmup_start) / 1000000.0
	if warmup_s > 0.0:
		for actor in actual_game.enemies + actual_game.allies:
			if is_instance_valid(actor):
				recorded[actor.get_instance_id()] = actor.ai_state()
	print("KVARNBYN_SOLDIERS_MEASURING ", JSON.stringify({"warmup_s": warmup_s, "warmup_wall_s": warmup_wall_s}))
	var start_usec := Time.get_ticks_usec()
	var frames := int(duration_s * 60.0)
	for frame in range(frames):
		await physics_frame
		if frame > 0 and frame % 900 == 0:
			print("KVARNBYN_SOLDIERS_PROGRESS ", JSON.stringify({"simulated_s": frame / 60.0, "fps": Engine.get_frames_per_second()}))
		if frame == frames / 2 and not screenshot_path.is_empty():
			await RenderingServer.frame_post_draw
			scene.get_viewport().get_texture().get_image().save_png(screenshot_path)
		if frame % 15 != 0:
			continue
		physics_times.append(Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0)
		process_times.append(Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0)
		fps_values.append(Performance.get_monitor(Performance.TIME_FPS))
		cpu_render_times.append(RenderingServer.viewport_get_measured_render_time_cpu(scene.get_viewport().get_viewport_rid()))
		gpu_render_times.append(RenderingServer.viewport_get_measured_render_time_gpu(scene.get_viewport().get_viewport_rid()))
		for actor in actual_game.enemies + actual_game.allies:
			if not is_instance_valid(actor):
				continue
			var id: int = actor.get_instance_id()
			var snapshot: Dictionary = actor.ai_state()
			var old: Dictionary = recorded.get(id, {})
			for key in totals:
				totals[key] += maxf(0.0, float(snapshot.get(key, 0.0)) - float(old.get(key, 0.0)))
			recorded[id] = snapshot
			var position: Vector3 = actor.global_position
			if position.distance_to(actual_player.global_position) < 88.0 and previous_positions.has(id):
				var before: Vector3 = previous_positions[id]
				if position.distance_to(before) > 0.03 and position.distance_to(before) < 2.0:
					segment_checks += 1
					var query := PhysicsRayQueryParameters3D.create(before + Vector3.UP * 1.0, position + Vector3.UP * 1.0, 1)
					if not actor.get_world_3d().direct_space_state.intersect_ray(query).is_empty():
						crossings += 1
			previous_positions[id] = position
	physics_times.sort()
	process_times.sort()
	fps_values.sort()
	cpu_render_times.sort()
	gpu_render_times.sort()
	var result := {"simulated_s": duration_s, "wall_clock_s": (Time.get_ticks_usec() - start_usec) / 1000000.0,
		"scenario": "stationary immortal player on the road near C; ten extra enemies; normal game simulation",
		"warmup_s": warmup_s, "warmup_wall_s": warmup_wall_s,
		"tracked_soldiers": recorded.size(), "extra_enemies_near_player": placed, "near_wall_segment_checks": segment_checks,
		"near_wall_crossings": crossings, "ai_cpu_ms_per_physics_frame": float(totals.cpu_usec) / frames / 1000.0,
		"renderer": RenderingServer.get_current_rendering_method(), "display_server": DisplayServer.get_name(),
		"physics_ms_p50": physics_times[physics_times.size() / 2], "physics_ms_p95": physics_times[int(physics_times.size() * 0.95)],
		"process_ms_p50": process_times[process_times.size() / 2], "process_ms_p95": process_times[int(process_times.size() * 0.95)],
		"fps_p50": fps_values[fps_values.size() / 2], "fps_p05": fps_values[int(fps_values.size() * 0.05)],
		"cpu_render_ms_p50": cpu_render_times[cpu_render_times.size() / 2], "gpu_render_ms_p50": gpu_render_times[gpu_render_times.size() / 2],
		"gpu_render_ms_p95": gpu_render_times[int(gpu_render_times.size() * 0.95)],
		"moving_fraction_when_firing": float(totals.moving_combat_s) / maxf(0.01, float(totals.combat_s)),
		"totals": totals, "game": actual_game.state(), "passed": totals.flanks > 0 and totals.shots > 0 and crossings == 0}
	print("KVARNBYN_SOLDIERS_WORLD ", JSON.stringify(result))
	save_report(result)
	await finish(0 if result.passed else 3)

extends SceneTree

## Checks the imported world and its real player capsule against authored ground metadata.
## No substitute floor/colliders are constructed. Run after export/import, with:
## Godot --audio-driver Dummy --headless --fixed-fps 60 --path godot \
##   --script res://scripts/verify_roten.gd -- --explore --no-pointer-lock --output=/absolute/report.json
## world_meta.m29_ground_checks: points[{id,position,tolerance_m}],
## paths[{id,points,speed_m_s,tolerance_m}], blockers[{id,from,to,blocked,height_m}].
## Other areas: --check-key=stalliden_ground_checks --report-prefix=KVARNBYN_STALLIDEN_CHECK
## All positions use exported Godot/glTF coordinates; y is the walking surface, not eye height.

const PlayerController = preload("res://scripts/player.gd")
const SAMPLE_STEP_M := 0.35
const STATIC_MASK := 1

var scene
var controller
var options := {}
var check_key := "m29_ground_checks"
var report_prefix := "KVARNBYN_ROTEN_CHECK"
var report := {"passed": false, "scope": "actual imported collision geometry and actual player controller",
	"points": [], "paths": [], "blockers": [], "errors": []}

func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--"):
			var pair := arg.trim_prefix("--").split("=", true, 1)
			options[pair[0]] = pair[1] if pair.size() > 1 else "1"
	check_key = str(options.get("check-key", check_key)).strip_edges()
	report_prefix = str(options.get("report-prefix", report_prefix)).strip_edges()
	report["check_key"] = check_key
	call_deferred("run")

func run() -> void:
	if not options.has("explore"):
		report.errors.append("Run with --explore: this geometry check must not start a battle.")
		await finish(2)
		return
	var packed := load("res://main.tscn") as PackedScene
	if packed == null:
		report.errors.append("main.tscn could not be loaded.")
		await finish(2)
		return
	scene = packed.instantiate()
	root.add_child(scene)
	var ready := false
	for frame in range(600):
		await physics_frame
		if scene.world_ready:
			ready = true
			break
	if not ready:
		report.errors.append("The actual world did not become ready.")
		await finish(2)
		return
	if scene.game != null:
		report.errors.append("Combat is active; --explore was not respected.")
		await finish(2)
		return
	var metadata = scene.metadata.get(check_key, {})
	if not metadata is Dictionary:
		report.errors.append("world_meta." + check_key + " must be a dictionary.")
		await finish(2)
		return
	for group in ["points", "paths", "blockers"]:
		if not metadata.get(group, []) is Array or metadata.get(group, []).is_empty():
			report.errors.append(check_key + "." + group + " is missing or empty.")
	if not report.errors.is_empty():
		await finish(2)
		return
	controller = scene.player
	# Keep the verifier independent of desktop focus and keyboard state.
	scene.options["no-pointer-lock"] = "1"
	scene.begin_walk()
	controller.free_flight = false
	controller.combat_enabled = false
	controller.bot_input = Vector2.ZERO
	controller.bot_sprint = false
	controller.weapon.ads = 0.0
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	var geometry_path := "res://assets/baked_world.tscn" if scene.prepared_bake_scene else "res://assets/world.glb"
	report["geometry_source"] = geometry_path
	report["world_asset_mtime_unix"] = FileAccess.get_modified_time(geometry_path)
	report["metadata_mtime_unix"] = FileAccess.get_modified_time("res://assets/world_meta.json")
	report["metadata_source"] = metadata.get("source", "world_meta." + check_key)
	var started := Time.get_ticks_usec()
	for spec in metadata.points:
		report.points.append(check_point(spec))
	for spec in metadata.paths:
		var points := positions(spec.get("points", []))
		if points.size() < 2:
			report.paths.append({"id": spec.get("id", "?"), "passed": false, "reason": "A path needs at least two valid positions."})
			continue
		var tolerance := float(spec.get("tolerance_m", 0.18))
		var sampled := sample_path(points, tolerance)
		var walked: Dictionary = await walk_path(points, float(spec.get("speed_m_s", 2.5)), tolerance)
		report.paths.append({"id": spec.get("id", "?"), "passed": sampled.passed and walked.reached,
			"surface_samples": sampled, "walk": walked})
	for spec in metadata.blockers:
		report.blockers.append(await check_blocker(spec))
	var blocked_count := 0
	var open_count := 0
	for spec in metadata.blockers:
		if bool(spec.get("blocked", false)):
			blocked_count += 1
		else:
			open_count += 1
	report["coverage"] = {"ground_points": metadata.points.size(), "walk_paths": metadata.paths.size(),
		"closed_blocker_probes": blocked_count, "open_passage_probes": open_count}
	var passed := true
	for group in [report.points, report.paths, report.blockers]:
		for result in group:
			passed = passed and bool(result.get("passed", false))
	report["wall_clock_s"] = (Time.get_ticks_usec() - started) / 1000000.0
	report.passed = passed
	await finish(0 if passed else 3)

func position(value) -> Vector3:
	return Vector3(float(value[0]), float(value[1]), float(value[2]))

func valid_position(value) -> bool:
	if not value is Array or value.size() != 3:
		return false
	for number in value:
		if typeof(number) not in [TYPE_INT, TYPE_FLOAT] or not is_finite(float(number)):
			return false
	return true

func positions(values) -> Array[Vector3]:
	var result: Array[Vector3] = []
	if not values is Array:
		return result
	for value in values:
		if not valid_position(value):
			return []
		result.append(position(value))
	return result

func xyz(value: Vector3) -> Array:
	return [value.x, value.y, value.z]

func surface_ray(expected: Vector3) -> Dictionary:
	# A short ray selects the intended road/storey, rather than the highest roof.
	var query := PhysicsRayQueryParameters3D.create(expected + Vector3.UP * 0.8, expected + Vector3.DOWN * 2.0, STATIC_MASK)
	return scene.get_world_3d().direct_space_state.intersect_ray(query)

func collider_name(hit: Dictionary) -> String:
	var body = hit.get("collider")
	return str(body.get_path()) if is_instance_valid(body) else ""

func check_point(spec: Dictionary) -> Dictionary:
	var result := {"id": spec.get("id", "?"), "passed": false}
	if not valid_position(spec.get("position")):
		result["reason"] = "position must contain three finite numbers."
		return result
	var expected := position(spec.position)
	var hit := surface_ray(expected)
	result["expected"] = xyz(expected)
	if hit.is_empty():
		result["reason"] = "No exported collision surface under this point."
		return result
	var delta_y: float = absf(hit.position.y - expected.y)
	result["actual"] = xyz(hit.position)
	result["height_error_m"] = delta_y
	result["normal_y"] = hit.normal.y
	result["collider"] = collider_name(hit)
	result.passed = delta_y <= float(spec.get("tolerance_m", 0.15)) and hit.normal.y >= float(spec.get("min_normal_y", 0.5736))
	return result

func sample_path(points: Array[Vector3], tolerance: float) -> Dictionary:
	var count := 0
	var bad := 0
	var maximum_error := 0.0
	var maximum_step := 0.0
	var previous_hit := {}
	var failures := []
	for segment in range(points.size() - 1):
		var a := points[segment]
		var b := points[segment + 1]
		var steps := maxi(1, ceili(flat_distance(a, b) / SAMPLE_STEP_M))
		for step in range(steps + 1):
			var expected := a.lerp(b, float(step) / steps)
			var hit := surface_ray(expected)
			count += 1
			var error := INF if hit.is_empty() else absf(hit.position.y - expected.y)
			if is_finite(error):
				maximum_error = maxf(maximum_error, error)
			var abrupt_step := false
			if not hit.is_empty() and not previous_hit.is_empty():
				var travel: Vector3 = hit.position - previous_hit.position
				var step_height := absf(travel.y)
				maximum_step = maxf(maximum_step, step_height)
				# Permit an actual sloping triangle; reject an unexpected upright lip.
				var allowed := PlayerController.STEP_HEIGHT + 0.03
				for normal in [hit.normal, previous_hit.normal]:
					allowed = maxf(allowed, absf(normal.x * travel.x + normal.z * travel.z) / maxf(0.01, normal.y) + 0.05)
				abrupt_step = step_height > allowed
			if hit.is_empty() or error > tolerance or hit.normal.y < 0.5736 or abrupt_step:
				bad += 1
				if failures.size() < 20:
					failures.append({"segment": segment, "expected": xyz(expected), "actual": [] if hit.is_empty() else xyz(hit.position),
						"abrupt_step": abrupt_step, "collider": collider_name(hit)})
			previous_hit = hit
	return {"passed": bad == 0, "count": count, "bad": bad, "maximum_height_error_m": maximum_error,
		"maximum_adjacent_height_change_m": maximum_step, "first_failures": failures}

func nearest_path_height(at: Vector3, points: Array[Vector3]) -> Dictionary:
	var best_distance := INF
	var best_y := points[0].y
	for index in range(points.size() - 1):
		var a := Vector2(points[index].x, points[index].z)
		var b := Vector2(points[index + 1].x, points[index + 1].z)
		var horizontal := Vector2(at.x, at.z)
		var fraction := clampf((horizontal - a).dot(b - a) / maxf(0.000001, a.distance_squared_to(b)), 0.0, 1.0)
		var distance := horizontal.distance_to(a.lerp(b, fraction))
		if distance < best_distance:
			best_distance = distance
			best_y = lerpf(points[index].y, points[index + 1].y, fraction)
	return {"height": best_y, "lateral_m": best_distance}

func walk_path(points: Array[Vector3], speed: float, tolerance: float, blocked_collider := "", check_profile := true) -> Dictionary:
	controller.active = true
	controller.input_suspended = false
	controller.free_flight = false
	controller.bot_input = Vector2.ZERO
	controller.bot_sprint = false
	controller.place_at(points[0] + Vector3.UP * 0.12, 0.0, 0.0)
	controller.velocity = Vector3.ZERO
	for frame in range(45):
		await physics_frame
	if not controller.is_on_floor() or absf(controller.position.y - points[0].y) > maxf(0.2, tolerance):
		return {"reached": false, "reason": "start_not_on_expected_ground", "position": xyz(controller.position)}
	var length_m := 0.0
	for index in range(points.size() - 1):
		length_m += flat_distance(points[index], points[index + 1])
	if length_m < 0.5:
		return {"reached": false, "reason": "route_shorter_than_0_5m"}
	speed = clampf(speed, 0.5, PlayerController.WALK_SPEED)
	var budget := maxi(180, ceili((length_m / speed * 3.0 + 3.0) * 60.0))
	var next := 1
	var progress_window: Vector3 = controller.position
	var airborne_frames := 0
	var maximum_error := 0.0
	var maximum_lateral := 0.0
	var side_colliders := {}
	var contact_frames := 0
	var contact_start := Vector3.ZERO
	var reason := "time_limit"
	var used_frames := 0
	for frame in range(mini(budget, 18000)):
		var toward: Vector3 = points[next] - controller.position
		toward.y = 0.0
		if toward.length() <= 0.30:
			if check_profile and blocked_collider.is_empty() and absf(controller.position.y - points[next].y) > maxf(tolerance, 0.25):
				reason = "waypoint_height_mismatch"
				break
			next += 1
			if next == points.size():
				reason = "reached"
				break
			toward = points[next] - controller.position
			toward.y = 0.0
		controller.rotation.y = atan2(-toward.x, -toward.z)
		controller.bot_input = Vector2(0, -speed / PlayerController.WALK_SPEED)
		await physics_frame
		used_frames += 1
		var actual: Vector3 = controller.position
		var expected := nearest_path_height(actual, points)
		var error: float = absf(actual.y - float(expected.height))
		maximum_error = maxf(maximum_error, error)
		maximum_lateral = maxf(maximum_lateral, float(expected.lateral_m))
		var matching_contact := false
		for index in range(controller.get_slide_collision_count()):
			var collision: KinematicCollision3D = controller.get_slide_collision(index)
			if absf(collision.get_normal().y) < 0.45:
				var body = collision.get_collider()
				if is_instance_valid(body):
					var collider_path := str(body.get_path())
					side_colliders[collider_path] = true
					matching_contact = matching_contact or collider_path == blocked_collider
		if matching_contact:
			if contact_frames == 0:
				contact_start = actual
			contact_frames += 1
		else:
			contact_frames = 0
		if contact_frames >= 15 and flat_distance(actual, contact_start) < 0.2:
			reason = "blocked_by_static"
			break
		airborne_frames = 0 if controller.is_on_floor() else airborne_frames + 1
		if (check_profile and blocked_collider.is_empty() and actual.y < float(expected.height) - 0.6) or airborne_frames > 25:
			reason = "floor_gap_or_fall"
			break
		# A retaining wall may separate two levels: interpolating through its solid
		# body is not an expected walking profile. Require contact with that very
		# collider instead; ordinary paths retain all height/route checks.
		if blocked_collider.is_empty() and ((check_profile and error > maxf(tolerance, 0.25)) or float(expected.lateral_m) > 0.8):
			reason = "height_or_route_mismatch"
			break
		if frame > 0 and frame % 90 == 0:
			if flat_distance(actual, progress_window) < 0.10:
				reason = "stuck"
				break
			progress_window = actual
	controller.bot_input = Vector2.ZERO
	controller.velocity = Vector3.ZERO
	if reason == "reached":
		for frame in range(12):
			await physics_frame
		if not controller.is_on_floor() or (blocked_collider.is_empty() and absf(controller.position.y - points[-1].y) > maxf(0.2, tolerance)):
			reason = "final_landing_mismatch"
	return {"reached": reason == "reached", "reason": reason, "frames": used_frames,
		"position": xyz(controller.position), "distance_from_start_m": flat_distance(controller.position, points[0]),
		"height_profile_checked": check_profile and blocked_collider.is_empty(),
		"maximum_height_error_m": maximum_error, "maximum_lateral_error_m": maximum_lateral,
		"side_colliders": side_colliders.keys()}

func check_blocker(spec: Dictionary) -> Dictionary:
	var result := {"id": spec.get("id", "?"), "passed": false}
	if not valid_position(spec.get("from")) or not valid_position(spec.get("to")) or not spec.has("blocked"):
		result["reason"] = "Blockers need from/to foot positions and a blocked boolean."
		return result
	var a := position(spec["from"])
	var b := position(spec["to"])
	var height := float(spec.get("height_m", 1.0))
	var query := PhysicsRayQueryParameters3D.create(a + Vector3.UP * height, b + Vector3.UP * height, STATIC_MASK)
	var hit: Dictionary = scene.get_world_3d().direct_space_state.intersect_ray(query)
	var expected_blocked := bool(spec.blocked)
	var route: Array[Vector3] = [a, b]
	var expected_collider := collider_name(hit) if expected_blocked else ""
	# Two blocker endpoints do not describe the intervening stair/landing profile.
	# Detailed path records above verify that profile; this trial verifies passage/contact.
	var walked: Dictionary = await walk_path(route, float(spec.get("speed_m_s", 2.0)), float(spec.get("tolerance_m", 0.18)), expected_collider, false)
	result["expected_blocked"] = expected_blocked
	result["ray_blocked"] = not hit.is_empty()
	result["ray_collider"] = collider_name(hit)
	result["walk"] = walked
	if expected_blocked:
		result.passed = not hit.is_empty() and not walked.reached and walked.reason in ["stuck", "blocked_by_static"] and expected_collider in walked.get("side_colliders", [])
	else:
		result.passed = hit.is_empty() and walked.reached
	return result

func flat_distance(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length()

func finish(code: int) -> void:
	print(report_prefix, " ", JSON.stringify(report))
	if options.has("output"):
		var file := FileAccess.open(str(options.output), FileAccess.WRITE)
		if file != null:
			file.store_string(JSON.stringify(report, "\t") + "\n")
	if is_instance_valid(scene):
		scene.queue_free()
	await process_frame
	await process_frame
	quit(code)

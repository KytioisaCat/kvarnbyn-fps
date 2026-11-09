extends RefCounted

# Drop, idle and walk the real capsule on roofs from the actual world asset.
var checks: Array = []
func check(id: String, passed: bool, detail = null) -> void:
	checks.append({"test": id, "passed": passed, "detail": detail})
func xyz(value) -> Vector3:
	return Vector3(float(value[0]), float(value[1]), float(value[2]))
func run(world: Node3D) -> Dictionary:
	AudioServer.set_bus_mute(0, true)
	var tree := world.get_tree()
	var p = world.player
	var metadata: Dictionary = world.metadata.get("roof_physics", {})
	var cases: Array = metadata.get("checks", [])
	check("roof_cases_packaged", cases.size() >= 6 and int(metadata.get("added_faces", 0)) > 0)
	world.begin_walk()
	if world.game: world.game.running = false
	p.combat_enabled = false
	p.input_suspended = false
	p.free_flight = false
	p.bot_sprint = false
	p.bot_input = Vector2.ZERO
	p.grapple.release()
	for spec in cases:
		var route: Array = spec.points
		var point := xyz(route[0])
		var hit: Dictionary = p.get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(point + Vector3.UP * .7, point + Vector3.DOWN * .7, 1))
		check(str(spec.id) + "_roof_surface", not hit.is_empty() and absf(hit.position.y - point.y) < .28, {"expected":point,"hit":hit.get("position",Vector3.INF)})
		p.place_at(point + Vector3.UP * 1.5, 0., 0., false)
		p.look_toward(xyz(route[1]))
		var attached: bool = p.grapple.try_attach()
		check(str(spec.id) + "_grapple_attached_to_roof", attached and p.grapple.anchor.distance_to(xyz(route[1])) < .4)
		p.grapple.release()
		p.bot_input = Vector2.ZERO
		for frame in range(90): await tree.physics_frame
		check(str(spec.id) + "_landed", p.is_on_floor() and absf(p.global_position.y - point.y) < .28, {"feet":p.global_position, "roof":point})
		var start: Vector3 = p.global_position
		for frame in range(90): await tree.physics_frame
		check(str(spec.id) + "_stood_still", p.is_on_floor() and p.global_position.distance_to(start) < .025)
		var destination := xyz(route[-1])
		for frame in range(240):
			var toward: Vector3 = destination - p.global_position
			toward.y = 0
			if toward.length() < .2: break
			p.rotation.y = atan2(-toward.x, -toward.z)
			p.bot_input = Vector2(0, -1.8 / p.movement.get_value("walk_speed"))
			await tree.physics_frame
		p.bot_input = Vector2.ZERO
		var distance := Vector2(p.global_position.x - destination.x, p.global_position.z - destination.z).length()
		check(str(spec.id) + "_walked_on_roof", distance < .25 and p.is_on_floor() and absf(p.global_position.y - destination.y) < .3, {"distance_m":distance, "height_error_m":p.global_position.y-destination.y})
	var passed := true
	for result in checks: passed = passed and bool(result.passed)
	return {"passed":passed,"release":not OS.has_feature("editor"),"roofs":cases.size(),"checks":checks}

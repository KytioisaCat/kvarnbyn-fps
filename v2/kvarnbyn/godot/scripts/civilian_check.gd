extends RefCounted

class ImpactSpy extends Node3D:
	var impacts: Array = []
	func impact(_p, _n, kind): impacts.append(kind)
	func tracer(_a, _b): pass
class MarkerSpy extends Control:
	var markers := 0
	func hitmarker(_kind): markers += 1

var checks: Array = []
func check(label: String, passed: bool, detail = null) -> void:
	checks.append({"test": label, "passed": passed, "detail": detail})

func run(world: Node3D) -> Dictionary:
	AudioServer.set_bus_mute(0, true)
	var tree := world.get_tree()
	var system = world.civilians
	var p = world.player
	check("four_unique_people_in_real_world", system.people.size() == 4 and tree.get_nodes_in_group("civilians").size() == 4)
	var identities := []
	var mesh_resources := []
	for person in system.people:
		identities.append(person.data.name)
		var meshes: Array = person.model.find_children("*", "MeshInstance3D", true, false)
		var rigs: Array = person.model.find_children("*", "Skeleton3D", true, false)
		check(str(person.data.id) + "_own_model_rig_five_clips", not meshes.is_empty() and not rigs.is_empty() and rigs[0].get_bone_count() == 16 and person.clips.size() == 5, person.snapshot())
		mesh_resources.append(meshes[0].mesh.get_instance_id() if not meshes.is_empty() else 0)
		check(str(person.data.id) + "_civilian_not_damageable_or_armed", person.collision_layer == 8 and not person.has_method("hit") and not person.has_method("damage") and person.find_children("*", "Camera3D", true, false).is_empty())
	var sample = system.people[3]
	var sample_rig: Skeleton3D = sample.model.find_children("*", "Skeleton3D", true, false)[0]
	sample.play_clip("Talk")
	sample.animator.advance(1.0)
	check("imported_animation_moves_actual_arm_bones", sample_rig.get_bone_pose_rotation(sample_rig.find_bone("UpperArm.R")).angle_to(Quaternion.IDENTITY) > 0.05)
	sample.play_clip("Idle")
	check("identities_and_meshes_distinct", identities.size() == 4 and mesh_resources[0] != mesh_resources[1] and mesh_resources[1] != mesh_resources[2] and mesh_resources[2] != mesh_resources[3], identities)
	check("body_proportions_distinct", system.people[0].data.height > system.people[1].data.height and system.people[0].data.radius < system.people[1].data.radius and system.people[2].data.radius > system.people[1].data.radius and system.people[3].data.height < system.people[1].data.height)
	world.begin_walk()
	if world.game: world.game.running = false
	p.set_physics_process(false)
	p.set_process(false)
	p.weapon.set_process(false)
	p.global_position = Vector3(-8, 1, 14)
	for person in system.people:
		person.wait_left = 0.0
	for frame in range(150): await tree.physics_frame
	for person in system.people:
		var ground: Vector3 = world.ground_position(person.global_position)
		check(str(person.data.id) + "_grounded_walk_in_actual_city", absf(ground.y - person.global_position.y) < 0.15 and person.walked_m > 0.25, {"walked": person.walked_m, "floor_error": person.global_position.y - ground.y})
	# Freeze the simulation through the same tree pause used by Escape.
	var before: Vector3 = system.people[0].global_position
	var time_before: float = system.people[0].time
	tree.paused = true
	for frame in range(4): await tree.process_frame
	check("pause_stops_civilian_movement_and_time", system.people[0].global_position == before and system.people[0].time == time_before)
	tree.paused = false
	var person = system.people[1]
	for actor in system.people: actor.set_physics_process(false)
	person.global_position = person.home
	p.place_at(system.approach_position(person), 0, 0, false)
	p.look_toward(person.global_position + Vector3.UP * 1.25)
	p.input_suspended = false
	await tree.physics_frame
	var event := InputEventKey.new()
	event.keycode = KEY_E
	event.physical_keycode = KEY_E
	event.pressed = true
	Input.parse_input_event(event)
	await tree.process_frame
	event = InputEventKey.new()
	event.keycode = KEY_E
	event.physical_keycode = KEY_E
	event.pressed = false
	Input.parse_input_event(event)
	await tree.process_frame
	check("physical_E_talks_to_aimed_civilian", person.talks == 1 and system.card.visible and system.speaker.text == person.data.name)
	check("talk_cooldown_prevents_repeated_press", not system.try_talk() and person.talks == 1)
	p.look_toward(p.global_position + Vector3.RIGHT * 3)
	system.talk_cooldown = 0.0
	check("cannot_talk_when_looking_away", not system.try_talk())
	tree.paused = true
	for frame in range(2): await tree.process_frame
	check("pause_hides_civilian_UI_and_disables_talk", not system.card.visible and not system.hint.visible and not system.try_talk())
	tree.paused = false
	p.look_toward(person.global_position + Vector3.UP * 1.25)
	var barrier := StaticBody3D.new()
	var barrier_shape := CollisionShape3D.new()
	var barrier_box := BoxShape3D.new()
	barrier_box.size = Vector3(1.0, 2.5, 1.0)
	barrier_shape.shape = barrier_box
	barrier.add_child(barrier_shape)
	world.add_child(barrier)
	barrier.global_position = p.global_position.lerp(person.global_position, 0.5) + Vector3.UP
	await tree.physics_frame
	check("cannot_talk_through_world_obstacle", not system.try_talk())
	barrier.queue_free()
	await tree.physics_frame
	var grapple_hit: Dictionary = p.grapple.cast_target()
	check("grapple_does_not_attach_to_civilian", grapple_hit.is_empty() or not grapple_hit.collider.is_in_group("civilians"))
	if world.game:
		var g = world.game
		var in_pool := false
		for actor in system.people:
			in_pool = in_pool or actor in g.allies or actor in g.enemies
		check("civilians_excluded_from_combat_target_pools", not in_pool)
		var enemy = g.enemies[0] if not g.enemies.is_empty() else null
		if enemy != null:
			enemy.global_position = person.global_position + (person.global_position - p.global_position).normalized() * 2.0
			enemy.set_physics_process(false)
			var hp_before: float = enemy.hp
			var kills_before: int = g.kills
			var headshots_before: int = g.headshots
			var spy := ImpactSpy.new()
			world.add_child(spy)
			var marker := MarkerSpy.new()
			world.canvas_layer.add_child(marker)
			var old_fx: Node3D = p.weapon.fx
			var old_hud: Control = p.weapon.hud
			p.weapon.fx = spy
			p.weapon.hud = marker
			var ammo_before: int = p.weapon.mag
			for height in [0.8, 1.65]:
				p.look_toward(person.global_position + Vector3.UP * height)
				await tree.physics_frame
				p.weapon.bloom = 0
				p.weapon._fire()
			check("real_body_and_head_shots_stop_at_civilian", person.shots_received == 2 and p.weapon.mag == ammo_before - 2 and enemy.hp == hp_before, {"civilian_shots": person.shots_received, "enemy_hp": enemy.hp})
			check("civilian_shots_have_no_blood_hitmarkers_or_score", spy.impacts.is_empty() and marker.markers == 0 and g.kills == kills_before and g.headshots == headshots_before)
			check("accidental_shot_warns_and_startles", person.current_clip == "Startle" and "Civila" in system.line.text)
			# Both sight and muzzle rays in the actual soldier code block on civilians.
			enemy.target = p
			var shots_before: int = enemy.tactics.stats.shots
			var blocked_before: int = enemy.tactics.stats.blocked_shots
			enemy._shoot(5.0, false)
			check("soldiers_hold_fire_when_civilian_blocks_line", enemy.tactics.stats.shots == shots_before and enemy.tactics.stats.blocked_shots > blocked_before)
			p.weapon.fx = old_fx
			p.weapon.hud = old_hud
			spy.queue_free()
			marker.queue_free()
		else:
			check("combat_enemy_available_for_bullet_test", false)
	else:
		check("combat_required_for_bullet_tests", false)
	if world.game:
		world._on_restart()
		world.game.running = false
		check("round_restart_does_not_duplicate_civilians", tree.get_nodes_in_group("civilians").size() == 4)
	var passed := true
	for result in checks: passed = passed and bool(result.passed)
	return {"passed": passed, "release": not OS.has_feature("editor"), "checks": checks, "people": system.snapshot()}

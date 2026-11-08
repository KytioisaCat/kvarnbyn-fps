extends Node3D

## Verklig spelarkapsel + tangenthändelser i kontrollerad fysikfixtur.
## Samma prov kan köras inuti den exporterade appen; inget separat rörelsesubstitut.
const Player = preload("res://scripts/player.gd")
var checks: Array = []
var samples: Dictionary = {}
var p: CharacterBody3D
var origin := Vector3(2000, 0, 2000)

func check(label: String, passed: bool, details: Variant = null) -> void:
	checks.append({"name": label, "passed": passed, "details": details})

func key(code: int, pressed: bool) -> void:
	var event := InputEventKey.new()
	event.physical_keycode = code
	event.pressed = pressed
	Input.parse_input_event(event)

func release_keys() -> void:
	for code in [KEY_W, KEY_A, KEY_D, KEY_S, KEY_SHIFT, KEY_SPACE, KEY_E, KEY_C]:
		key(code, false)

func frames(count: int) -> void:
	for frame in range(count):
		await get_tree().physics_frame

func solid(where: Vector3, dimensions: Vector3) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = origin + where
	body.collision_layer = 1
	body.collision_mask = 2
	var collider := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = dimensions
	collider.shape = shape
	body.add_child(collider)
	add_child(body)
	return body

func reset(where := Vector3(0, 0.05, 5)) -> void:
	release_keys()
	p.active = true
	p.alive = true
	p.free_flight = false
	p.input_suspended = false
	p.place_at(origin + where, 0.0, 0.0)
	await frames(25)
	p.look_toward(origin + Vector3(0, 1, -28))

func launch(diagonal: bool, hz: int, side := KEY_D) -> Dictionary:
	await reset()
	key(KEY_W, true)
	key(KEY_SHIFT, true)
	if diagonal:
		key(side, true)
	await frames(roundi(hz * 0.3))
	key(KEY_E, true)
	await frames(2)
	var attached_at_start: bool = p.grapple.attached
	var start: Vector3 = p.position
	var peak := 0.0
	for frame in range(roundi(hz * 0.8)):
		await frames(1)
		peak = maxf(peak, p.velocity.length())
	var result := {"attached": attached_at_start and p.grapple.attached,
		"speed": p.velocity.length(), "peak": peak,
		"sideways_m": absf(p.position.x - start.x), "distance_m": p.position.distance_to(start)}
	release_keys()
	await frames(2)
	return result

func run(hz := 60) -> Dictionary:
	AudioServer.set_bus_mute(0, true)
	Engine.physics_ticks_per_second = hz
	solid(Vector3(0, -0.5, 0), Vector3(160, 1, 160))
	solid(Vector3(0, 9, -28.5), Vector3(100, 18, 1))
	p = Player.new()
	add_child(p)
	await reset()
	check("normal capsule begins on floor", p.is_on_floor())
	# Miss och räckvidd: det finns en vägg bakom spelaren men ingen i siktriktningen.
	p.look_toward(p.eye_position() + Vector3(0, 30, 30))
	key(KEY_E, true)
	await frames(3)
	check("miss does not attach or grant momentum", not p.grapple.attached and not p.momentum_mode)
	release_keys()
	await frames(2)
	await reset(Vector3(0, 0.05, 25))
	key(KEY_E, true)
	await frames(3)
	check("wall beyond 42m cannot attach", not p.grapple.attached)
	var straight: Dictionary = await launch(false, hz)
	var diagonal: Dictionary = await launch(true, hz)
	var left: Dictionary = await launch(true, hz, KEY_A)
	samples["straight"] = straight
	samples["diagonal"] = diagonal
	samples["left"] = left
	check("E attaches and keeps reeling through real physics", straight.attached and diagonal.attached)
	check("straight pull accelerates beyond sprint", straight.speed > p.RUN_SPEED + 1.0, straight.speed)
	check("diagonal steering builds more speed than straight pull", diagonal.speed > straight.speed * 1.15, [straight.speed, diagonal.speed])
	check("steering creates a swing arc", diagonal.sideways_m > 2.0, diagonal.sideways_m)
	check("left and right swing have equal strength", absf(left.speed - diagonal.speed) < 0.2)
	check("city speed budget holds", maxf(straight.peak, diagonal.peak) <= p.grapple.MAX_SPEED + 0.01)
	# Riktig markstart, hopp under dragning, därefter släpp i luften.
	await reset()
	key(KEY_E, true)
	key(KEY_W, true)
	key(KEY_D, true)
	await frames(roundi(hz * 0.5))
	var grounded_before_jump: bool = p.is_on_floor()
	key(KEY_SPACE, true)
	await frames(5)
	key(KEY_SPACE, false)
	var jumped: bool = not p.is_on_floor() and p.velocity.y > 0.0
	var velocity_before: Vector3 = p.velocity
	p.grapple.release()
	check("release itself never changes velocity", p.velocity.is_equal_approx(velocity_before))
	key(KEY_E, false)
	key(KEY_W, false)
	key(KEY_D, false)
	var horizontal_before := Vector2(p.velocity.x, p.velocity.z).length()
	await frames(roundi(hz * 0.15))
	var horizontal_after := Vector2(p.velocity.x, p.velocity.z).length()
	samples["release"] = {"before_m_s": horizontal_before, "after_m_s": horizontal_after, "airborne": not p.is_on_floor()}
	check("jump during reel lifts actual capsule without rocket", grounded_before_jump and jumped and not p.rocket_used)
	check("key release detaches and preserves airborne momentum", not p.grapple.attached and horizontal_after > horizontal_before * 0.97 and not p.is_on_floor(), samples.release)
	# En andra krok fångar den befintliga rörelsen, utan fartnollställning.
	p.look_toward(origin + Vector3(0, 5, -28))
	key(KEY_E, true)
	await frames(2)
	check("can grapple again while airborne", p.grapple.attached and Vector2(p.velocity.x, p.velocity.z).length() > horizontal_before * 0.8)
	key(KEY_E, false)
	await frames(hz * 2)
	check("landing returns to controllable ground speed", p.is_on_floor() and p.velocity.length() < 8.0, p.velocity.length())
	# Hög fart mot vägg och golv: svept CharacterBody-kollision, ingen teleport.
	await reset(Vector3(0, 1, -23))
	p.velocity = Vector3(0, 0, -30)
	p.momentum_mode = true
	await frames(roundi(hz * 0.4))
	check("fast capsule stops at solid wall", p.position.z > origin.z - 27.75 and p.position.z < origin.z - 26.0, p.position.z - origin.z)
	check("fast capsule does not cross floor", p.position.y >= origin.y - 0.01)
	# Linan måste släppas vid ett nytt hinder mellan spelare och fästpunkt.
	await reset()
	key(KEY_E, true)
	await frames(3)
	var blocker := solid(Vector3(0, 3, -8), Vector3(40, 6, 1))
	await frames(4)
	check("new obstruction breaks cable", not p.grapple.attached)
	blocker.queue_free()
	await frames(2)
	# Livscykel: inga kvarhängande krafter efter död, paus eller placering.
	await reset()
	key(KEY_E, true)
	await frames(3)
	p.combat_enabled = true
	p.damage(1000.0, p.position + Vector3.FORWARD)
	check("death detaches immediately", not p.grapple.attached and not p.alive)
	p.combat_enabled = false
	await reset()
	key(KEY_E, true)
	await frames(3)
	p.active = false
	var before: Vector3 = p.position
	await frames(5)
	check("inactive controller detaches and stops", not p.grapple.attached and p.position.is_equal_approx(before))
	await reset()
	key(KEY_E, true)
	await frames(3)
	p.input_suspended = true
	await frames(2)
	check("suspended input cancels cable", not p.grapple.attached)
	await reset()
	key(KEY_E, true)
	await frames(3)
	var fly_event := InputEventKey.new()
	fly_event.physical_keycode = KEY_F
	fly_event.pressed = true
	p._unhandled_input(fly_event)
	check("free flight cancels cable and momentum", not p.grapple.attached and not p.momentum_mode and p.free_flight)
	await reset()
	key(KEY_E, true)
	await frames(3)
	p.place_at(origin + Vector3(0, 2, 5), 0.0, 0.0)
	check("reset clears cable and momentum", not p.grapple.attached and not p.momentum_mode and p.velocity == Vector3.ZERO)
	release_keys()
	p.active = false
	var passed := true
	for entry in checks:
		passed = passed and bool(entry.passed)
	return {"passed": passed, "checks": checks, "samples": samples,
		"physics_hz": hz, "release": not OS.has_feature("editor"),
		"scope": "actual controller, key input, swept capsule collisions in a synthetic fixture; feel requires Joel"}

func run_city(world: Node3D) -> Dictionary:
	# Stadens ursprungliga kolliderare är enda underlag i denna del.
	var city: CharacterBody3D = world.player
	# Starta striden först: game.start() placerar annars om spelaren efter vyvalet.
	world.begin_walk()
	for index in range(world.metadata.views.size()):
		if world.metadata.views[index].id == "torget":
			world.set_view(index)
			break
	world.begin_walk()
	city.camera.make_current()
	await frames(45)
	var start: Vector3 = city.global_position
	var target := Vector3.ZERO
	var collider_name := ""
	for elevation in [0.15, 0.35, 0.55, 0.0]:
		for index in range(24):
			var angle := float(index) * TAU / 24.0
			city.look_toward(city.eye_position() + Vector3(sin(angle), elevation, -cos(angle)) * 40.0)
			var hit: Dictionary = city.grapple.cast_target()
			if not hit.is_empty():
				var distance: float = city.grapple.harness().distance_to(hit.position)
				var geometry := str(hit.collider.get_parent().name)
				var house := geometry.begins_with("COL_H") or geometry.begins_with("COL_w") or geometry.begins_with("COL_krakan")
				if house and distance > 10.0 and distance < 38.0 and absf(hit.normal.y) < 0.5:
					target = hit.position
					collider_name = geometry
					break
		if collider_name != "":
			break
	key(KEY_E, true)
	await frames(3)
	var latched: bool = city.grapple.attached
	key(KEY_W, true)
	key(KEY_D, true)
	await frames(18)
	var moved: float = city.position.distance_to(start)
	var speed: float = city.velocity.length()
	var still_attached: bool = city.grapple.attached
	var visual: bool = city.grapple.cable.visible and city.grapple.marker.visible
	if world.options.has("grapple-image") and DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		var error := get_viewport().get_texture().get_image().save_png(str(world.options["grapple-image"]))
		check("native city capture saved", error == OK)
	# Verkliga M/Esc-hanterarna måste ta bort linan även när fysiken pausas.
	world.set_map_open(true)
	var map_cancelled: bool = not city.grapple.attached and get_tree().paused
	release_keys()
	world.set_map_open(false)
	await frames(2)
	city.look_toward(target)
	key(KEY_E, true)
	await frames(2)
	var reattached: bool = city.grapple.attached
	world.pause_walk()
	var pause_cancelled: bool = not city.grapple.attached and not city.active
	release_keys()
	get_tree().paused = false
	return {"passed": collider_name != "" and latched and still_attached and moved > 0.5 and speed > city.WALK_SPEED and visual and map_cancelled and reattached and pause_cancelled,
		"start": [start.x, start.y, start.z],
		"collider": collider_name, "attached": latched, "still_attached": still_attached,
		"distance_m": moved, "speed_m_s": speed, "cable_and_anchor_visible": visual,
		"map_cancels": map_cancelled, "reattached": reattached, "pause_cancels": pause_cancelled,
		"scope": "actual imported city at Gamla torget, camera ray, controller movement, map and pause"}

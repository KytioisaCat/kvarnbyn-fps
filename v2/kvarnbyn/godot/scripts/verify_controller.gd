extends SceneTree

## A physics integration check: the actual controller must climb a 20 cm kerb,
## stop at a wall and remain still while paused. It renders no substitute world.

const PlayerController = preload("res://scripts/player.gd")
var controller

func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	call_deferred("verify")

func solid(parent: Node3D, location: Vector3, dimensions: Vector3) -> void:
	var body := StaticBody3D.new()
	body.position = location
	body.collision_layer = 1
	body.collision_mask = 2
	var collider := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = dimensions
	collider.shape = shape
	body.add_child(collider)
	parent.add_child(body)

func key(pressed: bool, code := KEY_W) -> void:
	var event := InputEventKey.new()
	event.physical_keycode = code
	event.pressed = pressed
	Input.parse_input_event(event)

func touch(index: int, point: Vector2, pressed: bool) -> void:
	var event := InputEventScreenTouch.new()
	event.index = index
	event.position = point
	event.pressed = pressed
	# Headless viewports do not route platform touch events. Exercise the real
	# handler, then verify its effect through CharacterBody3D physics below.
	controller._unhandled_input(event)

func drag(index: int, point: Vector2, change: Vector2) -> void:
	var event := InputEventScreenDrag.new()
	event.index = index
	event.position = point
	event.relative = change
	controller._unhandled_input(event)

func verify() -> void:
	var space := Node3D.new()
	root.add_child(space)
	solid(space, Vector3(0, -0.1, 0), Vector3(12, 0.2, 12))
	solid(space, Vector3(0, 0.1, 0), Vector3(3, 0.2, 1.0))
	solid(space, Vector3(0, 1, -2.0), Vector3(3, 2, 0.25))
	var player = PlayerController.new()
	controller = player
	space.add_child(player)
	player.position = Vector3(0, 0.08, 2.5)
	player.active = true
	for frame in range(30):
		await physics_frame
	key(true)
	var maximum_height := 0.0
	var walked_over_kerb := false
	for frame in range(200):
		await physics_frame
		maximum_height = maxf(maximum_height, player.position.y)
		if player.position.z < -0.6:
			walked_over_kerb = true
	key(false)
	var stopped_at_wall: bool = player.position.z > -1.65 and player.position.z < -1.4
	player.active = false
	var paused_position: Vector3 = player.position
	key(true)
	for frame in range(30):
		await physics_frame
	key(false)
	var pause_works: bool = player.position.distance_to(paused_position) < 0.001
	var eye_height_correct: bool = absf(player.camera.position.y - 1.65) < 0.001
	player.place_at(Vector3(4, 0.08, 3), 0.0, 0.0)
	player.active = true
	var viewport_size: Vector2 = root.get_visible_rect().size
	var left := Vector2(viewport_size.x * 0.15, viewport_size.y * 0.7)
	var right := Vector2(viewport_size.x * 0.8, viewport_size.y * 0.6)
	touch(3, left, true)
	touch(7, right, true)
	drag(3, left - Vector2(0, 60), Vector2(0, -60))
	drag(7, right + Vector2(24, -5), Vector2(24, -5))
	for frame in range(35):
		await physics_frame
	var first_touch_position: Vector3 = player.position
	var two_finger_works: bool = first_touch_position.z < 2.2 and absf(player.rotation.y) > 0.05
	touch(7, right + Vector2(24, -5), false)
	for frame in range(35):
		await physics_frame
	var release_look_works: bool = player.position.z < first_touch_position.z - 0.5
	touch(3, left - Vector2(0, 60), false)
	for frame in range(45):
		await physics_frame
	var release_move_position: Vector3 = player.position
	for frame in range(25):
		await physics_frame
	var release_move_works: bool = player.position.distance_to(release_move_position) < 0.01
	# raketdubbelhopp: hopp, släpp, tryck igen i luften och håll → högre och långt framåt
	solid(space, Vector3(40, -0.1, 0), Vector3(40, 0.2, 60))
	player.place_at(Vector3(40, 0.08, 20), 0.0, 0.0)
	for frame in range(20):
		await physics_frame
	var rocket_start: Vector3 = player.position
	var rocket_height := 0.0
	key(true, KEY_SPACE)
	for frame in range(6):
		await physics_frame
	key(false, KEY_SPACE)
	for frame in range(4):
		await physics_frame
	key(true, KEY_SPACE)
	for frame in range(40):
		await physics_frame
		rocket_height = maxf(rocket_height, player.position.y)
	key(false, KEY_SPACE)
	for frame in range(120):
		await physics_frame
		rocket_height = maxf(rocket_height, player.position.y)
	var rocket_works: bool = rocket_height > 2.5 and rocket_start.z - player.position.z > 6.0 and player.is_on_floor()
	var rocket_distance: float = rocket_start.z - player.position.z
	# flygläge: F, W i en halv sekund ska ta en långt
	var fly_event := InputEventKey.new()
	fly_event.physical_keycode = KEY_F
	fly_event.pressed = true
	player._unhandled_input(fly_event)
	var fly_start: Vector3 = player.position
	key(true)
	for frame in range(30):
		await physics_frame
	key(false)
	var fly_works: bool = player.free_flight and fly_start.distance_to(player.position) > 6.0
	player._unhandled_input(fly_event)
	var passed: bool = walked_over_kerb and stopped_at_wall and pause_works and eye_height_correct and two_finger_works and release_look_works and release_move_works and rocket_works and fly_works and not player.free_flight
	var report := {"passed": passed, "walked_over_20cm_kerb": walked_over_kerb,
		"stopped_at_wall": stopped_at_wall, "pause_stops_movement": pause_works,
		"two_finger_move_and_look": two_finger_works, "release_look_keeps_walking": release_look_works,
		"release_move_stops": release_move_works,
		"eye_height_1_65m": eye_height_correct, "rocket_jump": rocket_works,
		"rocket_height": rocket_height, "rocket_distance": rocket_distance, "fly_mode": fly_works, "maximum_height": maximum_height,
		"final_position": [player.position.x, player.position.y, player.position.z]}
	print("KVARNBYN_CONTROLLER_CHECK ", JSON.stringify(report))
	quit(0 if passed else 2)

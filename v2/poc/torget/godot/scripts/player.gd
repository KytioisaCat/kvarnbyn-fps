extends CharacterBody3D

## A small first-person controller for comparing the authored environment on desktop and touch.
## The body's origin is at the feet. Camera eye height is fixed at 1.65 metres.

const WALK_SPEED := 3.5
const RUN_SPEED := 5.5
const JUMP_SPEED := 5.0
const GRAVITY := 16.0
const EYE_HEIGHT := 1.65
const MOUSE_SENSITIVITY := 0.0021
const TOUCH_SENSITIVITY := 0.0032
const STEP_HEIGHT := 0.23

var active := false
var camera: Camera3D
var overlay: Control
var touch_move := Vector2.ZERO
var move_finger := -1
var look_finger := -1
var move_anchor := Vector2.ZERO
var move_position := Vector2.ZERO
var jump_requested := false
var free_flight := false
var input_suspended := false

func _ready() -> void:
	collision_layer = 2
	collision_mask = 1
	floor_snap_length = 0.5
	floor_max_angle = deg_to_rad(55.0)
	floor_stop_on_slope = true
	var collision := CollisionShape3D.new()
	var shape := CapsuleShape3D.new()
	shape.radius = 0.29
	shape.height = 1.76
	collision.shape = shape
	collision.position.y = 0.88
	add_child(collision)
	camera = Camera3D.new()
	camera.name = "SpelarensKamera"
	camera.position.y = EYE_HEIGHT
	camera.fov = 67.0
	camera.near = 0.08
	camera.far = 600.0
	camera.current = true
	add_child(camera)
	set_process_unhandled_input(true)

func _unhandled_input(event: InputEvent) -> void:
	if not active or input_suspended:
		return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		look(event.relative * MOUSE_SENSITIVITY)
	if event is InputEventScreenTouch:
		if event.pressed:
			var width := get_viewport().get_visible_rect().size.x
			if event.position.x < width * 0.44 and move_finger == -1:
				move_finger = event.index
				move_anchor = event.position
				move_position = event.position
			elif look_finger == -1:
				look_finger = event.index
		else:
			if event.index == move_finger:
				move_finger = -1
				touch_move = Vector2.ZERO
			if event.index == look_finger:
				look_finger = -1
	if event is InputEventScreenDrag:
		if event.index == move_finger:
			move_position = event.position
			var radius := joystick_radius()
			var vector: Vector2 = (event.position - move_anchor) / radius
			touch_move = vector.limit_length(1.0)
			if touch_move.length() < 0.12:
				touch_move = Vector2.ZERO
		elif event.index == look_finger:
			look(event.relative * TOUCH_SENSITIVITY)

func joystick_radius() -> float:
	return clampf(get_viewport().get_visible_rect().size.y * 0.11, 48.0, 92.0)

func look(delta: Vector2) -> void:
	rotation.y -= delta.x
	camera.rotation.x = clampf(camera.rotation.x - delta.y, -1.37, 1.37)

func _physics_process(delta: float) -> void:
	if not active or input_suspended:
		velocity = Vector3.ZERO
		return
	var input_vector := touch_move
	if Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP):
		input_vector.y -= 1.0
	if Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN):
		input_vector.y += 1.0
	if Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT):
		input_vector.x -= 1.0
	if Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT):
		input_vector.x += 1.0
	input_vector = input_vector.limit_length(1.0)
	var speed := RUN_SPEED if Input.is_physical_key_pressed(KEY_SHIFT) or touch_move.length() > 0.88 else WALK_SPEED
	var direction := basis * Vector3(input_vector.x, 0.0, input_vector.y)
	var weight := minf(delta * 13.0, 1.0)
	velocity.x = lerpf(velocity.x, direction.x * speed, weight)
	velocity.z = lerpf(velocity.z, direction.z * speed, weight)
	if free_flight:
		velocity.y = 0.0
		if Input.is_physical_key_pressed(KEY_SPACE):
			velocity.y += speed
		if Input.is_physical_key_pressed(KEY_C) or Input.is_physical_key_pressed(KEY_CTRL):
			velocity.y -= speed
		global_position += velocity * delta
	else:
		if not is_on_floor():
			velocity.y -= GRAVITY * delta
		elif jump_requested or Input.is_physical_key_pressed(KEY_SPACE):
			velocity.y = JUMP_SPEED
		else:
			velocity.y = -0.1
		# A small raised test lets the capsule step over an ordinary kerb without jumping.
		if is_on_floor() and direction.length_squared() > 0.01 and velocity.y <= 0.0:
			var travel := Vector3(velocity.x, 0.0, velocity.z) * delta
			if test_move(global_transform, travel):
				var raised := global_transform.translated(Vector3.UP * STEP_HEIGHT)
				if not test_move(raised, travel):
					global_position.y += STEP_HEIGHT
		move_and_slide()
	jump_requested = false

func reset_touches() -> void:
	move_finger = -1
	look_finger = -1
	touch_move = Vector2.ZERO
	jump_requested = false

func place_at(position_value: Vector3, yaw: float, pitch: float, eye_position := false) -> void:
	global_position = position_value - Vector3.UP * EYE_HEIGHT if eye_position else position_value
	rotation.y = yaw
	camera.rotation.x = clampf(pitch, -1.37, 1.37)
	velocity = Vector3.ZERO
	reset_touches()

func look_toward(target: Vector3) -> void:
	var eye := global_position + Vector3.UP * EYE_HEIGHT
	var direction := target - eye
	if direction.length_squared() < 0.0001:
		return
	rotation.y = atan2(-direction.x, -direction.z)
	camera.rotation.x = atan2(direction.y, Vector2(direction.x, direction.z).length())

func snapshot() -> Dictionary:
	return {"position": [global_position.x, global_position.y, global_position.z],
		"eye": [camera.global_position.x, camera.global_position.y, camera.global_position.z],
		"yaw": rotation.y, "pitch": camera.rotation.x,
		"fov_degrees": camera.fov,
		"on_floor": is_on_floor(), "active": active, "free_flight": free_flight}

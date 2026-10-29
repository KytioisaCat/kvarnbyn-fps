extends CharacterBody3D

## Spelaren: förstapersonsrörelse (Codex grund: kantstenssteg, pekskärm) + Fas B: hälsa,
## skada, död, huka, sprint, siktläge, vapen, och känsla — acceleration, huvudgung, FOV vid
## sprint, landningsdipp, rekyl som kameran återhämtar sig från. Origo vid fötterna.

const Weapon = preload("res://scripts/weapon.gd")
const SFX = preload("res://scripts/sfx.gd")

const WALK_SPEED := 4.4
const RUN_SPEED := 6.9
const CROUCH_SPEED := 2.3
const JUMP_SPEED := 5.1
const GRAVITY := 16.0
const EYE_HEIGHT := 1.65
const CROUCH_EYE := 1.05
const MOUSE_SENSITIVITY := 0.0021
const TOUCH_SENSITIVITY := 0.0032
const STEP_HEIGHT := 0.23
const BASE_FOV := 72.0

signal died

var active := false
var camera: Camera3D
var overlay: Control
var weapon: Node3D
var game: Node
var touch_move := Vector2.ZERO
var move_finger := -1
var look_finger := -1
var move_anchor := Vector2.ZERO
var move_position := Vector2.ZERO
var jump_requested := false
var free_flight := false
var input_suspended := false
var combat_enabled := false
# hälsa
var max_hp := 100.0
var hp := 100.0
var alive := true
var last_hurt := -99.0
var regen_delay := 5.0
var regen_rate := 25.0
var hurt_dir := Vector3.ZERO
var hurt_flash := 0.0
# känsla
var crouching := false
var eye_height := EYE_HEIGHT
var bob_t := 0.0
var land_dip := 0.0
var was_on_floor := true
var step_t := 0.0
var recoil := Vector2.ZERO          # (yaw, pitch) som ännu inte återhämtats
var sprinting := false
# bot (automatiskt spelprov)
var bot_input = null               # Vector2 eller null
var bot_sprint := false
var footstep: AudioStreamPlayer
var hurt_voice: AudioStreamPlayer
var shape: CapsuleShape3D
var collision: CollisionShape3D

func _ready() -> void:
	collision_layer = 2
	collision_mask = 1
	floor_snap_length = 0.5
	floor_max_angle = deg_to_rad(55.0)
	floor_stop_on_slope = true
	collision = CollisionShape3D.new()
	shape = CapsuleShape3D.new()
	shape.radius = 0.29
	shape.height = 1.76
	collision.shape = shape
	collision.position.y = 0.88
	add_child(collision)
	camera = Camera3D.new()
	camera.name = "SpelarensKamera"
	camera.position.y = EYE_HEIGHT
	camera.fov = BASE_FOV
	camera.near = 0.05
	camera.far = 900.0
	camera.current = true
	add_child(camera)
	weapon = Weapon.new()
	weapon.player = self
	camera.add_child(weapon)
	footstep = AudioStreamPlayer.new()
	footstep.stream = SFX.get_sound("step")
	footstep.volume_db = -14.0
	add_child(footstep)
	hurt_voice = AudioStreamPlayer.new()
	hurt_voice.stream = SFX.get_sound("hurt")
	hurt_voice.volume_db = -4.0
	add_child(hurt_voice)
	set_process_unhandled_input(true)

func _unhandled_input(event: InputEvent) -> void:
	if not active or input_suspended or not alive:
		return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var sens: float = MOUSE_SENSITIVITY * (1.0 - 0.45 * weapon.ads)
		look(event.relative * sens)
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

## Rekyl: kameran sparkas upp direkt; återhämtningen sker mjukt i _process.
func kick(pitch_rad: float, yaw_rad: float) -> void:
	camera.rotation.x = clampf(camera.rotation.x + pitch_rad, -1.37, 1.37)
	rotation.y += yaw_rad
	recoil += Vector2(yaw_rad, pitch_rad)

func _process(delta: float) -> void:
	# återhämta ~65 % av rekylen
	if recoil.length_squared() > 1e-8:
		var back := recoil * minf(1.0, delta * 7.0) * 0.65
		camera.rotation.x -= back.y
		rotation.y -= back.x
		recoil -= recoil * minf(1.0, delta * 7.0)
	# huvudgung, landningsdipp, hukning, FOV
	var hspeed := Vector2(velocity.x, velocity.z).length()
	var target_eye := CROUCH_EYE if crouching else EYE_HEIGHT
	if not alive:
		target_eye = 0.35
	eye_height = lerpf(eye_height, target_eye, minf(1.0, delta * (4.0 if not alive else 10.0)))
	land_dip = lerpf(land_dip, 0.0, minf(1.0, delta * 8.0))
	if is_on_floor() and hspeed > 0.5 and alive:
		bob_t += delta * hspeed * 1.7
		step_t += delta * hspeed
		if step_t > (2.6 if sprinting else 2.0):
			step_t = 0.0
			footstep.pitch_scale = randf_range(0.85, 1.1)
			footstep.play()
	var bob: float = sin(bob_t) * 0.035 * (1.0 - weapon.ads * 0.8) * clampf(hspeed / WALK_SPEED, 0.0, 1.4)
	camera.position.y = eye_height + bob - land_dip
	camera.position.x = cos(bob_t * 0.5) * 0.018 * clampf(hspeed / WALK_SPEED, 0.0, 1.4) * (1.0 - weapon.ads)
	camera.rotation.z = lerpf(camera.rotation.z, (-0.35 if not alive else 0.0), minf(1.0, delta * 3.0))
	var target_fov := BASE_FOV + (6.0 if sprinting and hspeed > 5.0 else 0.0)
	target_fov = lerpf(target_fov, 48.0, weapon.ads)
	camera.fov = lerpf(camera.fov, target_fov, minf(1.0, delta * 10.0))
	hurt_flash = maxf(0.0, hurt_flash - delta * 1.6)
	# regeneration
	if alive and combat_enabled and hp < max_hp and Time.get_ticks_msec() / 1000.0 - last_hurt > regen_delay:
		hp = minf(max_hp, hp + regen_rate * delta)

func damage(amount: float, from_pos: Vector3) -> void:
	if not alive or not combat_enabled:
		return
	hp -= amount
	last_hurt = Time.get_ticks_msec() / 1000.0
	hurt_dir = (from_pos - global_position).normalized()
	hurt_flash = minf(1.0, hurt_flash + 0.45)
	hurt_voice.pitch_scale = randf_range(0.9, 1.1)
	hurt_voice.play()
	camera.rotation.z += randf_range(-0.02, 0.02)
	if hp <= 0.0:
		hp = 0.0
		alive = false
		weapon.ads = 0.0
		died.emit()

func revive(at: Vector3, yaw: float) -> void:
	hp = max_hp
	alive = true
	crouching = false
	place_at(at, yaw, 0.0)
	camera.rotation.z = 0.0
	eye_height = EYE_HEIGHT
	weapon.refill()

func _physics_process(delta: float) -> void:
	if not active or input_suspended:
		velocity = Vector3.ZERO
		return
	var input_vector := touch_move
	var want_sprint := false
	var want_crouch := false
	if bot_input != null:
		input_vector = bot_input
		want_sprint = bot_sprint
	elif alive:
		if Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP):
			input_vector.y -= 1.0
		if Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN):
			input_vector.y += 1.0
		if Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT):
			input_vector.x -= 1.0
		if Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT):
			input_vector.x += 1.0
		want_sprint = Input.is_physical_key_pressed(KEY_SHIFT) or touch_move.length() > 0.88
		want_crouch = Input.is_physical_key_pressed(KEY_C) or Input.is_physical_key_pressed(KEY_CTRL)
	if not alive:
		input_vector = Vector2.ZERO
	input_vector = input_vector.limit_length(1.0)
	crouching = want_crouch and not free_flight
	sprinting = want_sprint and not crouching and input_vector.y < -0.3 and weapon.ads < 0.3
	shape.height = 1.2 if crouching else 1.76
	collision.position.y = shape.height / 2.0
	var speed := CROUCH_SPEED if crouching else (RUN_SPEED if sprinting else WALK_SPEED)
	speed *= 1.0 - 0.35 * weapon.ads
	var direction := basis * Vector3(input_vector.x, 0.0, input_vector.y)
	var grounded := is_on_floor()
	var accel := 11.0 if grounded else 2.2
	if direction.length_squared() < 0.01 and grounded:
		accel = 14.0
	var weight := minf(delta * accel, 1.0)
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
		if not grounded:
			velocity.y -= GRAVITY * delta
		elif alive and (jump_requested or (bot_input == null and Input.is_physical_key_pressed(KEY_SPACE))) and not crouching:
			velocity.y = JUMP_SPEED
		else:
			velocity.y = -0.1
		if is_on_floor() and direction.length_squared() > 0.01 and velocity.y <= 0.0:
			var travel := Vector3(velocity.x, 0.0, velocity.z) * delta
			if test_move(global_transform, travel):
				var raised := global_transform.translated(Vector3.UP * STEP_HEIGHT)
				if not test_move(raised, travel):
					global_position.y += STEP_HEIGHT
		var falling := velocity.y
		move_and_slide()
		if is_on_floor() and not was_on_floor and falling < -3.0:
			land_dip = clampf(-falling * 0.018, 0.03, 0.14)
			footstep.play()
		was_on_floor = is_on_floor()
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
	recoil = Vector2.ZERO
	reset_touches()

func look_toward(target: Vector3) -> void:
	var eye := global_position + Vector3.UP * EYE_HEIGHT
	var direction := target - eye
	if direction.length_squared() < 0.0001:
		return
	rotation.y = atan2(-direction.x, -direction.z)
	camera.rotation.x = atan2(direction.y, Vector2(direction.x, direction.z).length())

func eye_position() -> Vector3:
	return camera.global_position

func snapshot() -> Dictionary:
	return {"position": [global_position.x, global_position.y, global_position.z],
		"eye": [camera.global_position.x, camera.global_position.y, camera.global_position.z],
		"yaw": rotation.y, "pitch": camera.rotation.x,
		"fov_degrees": camera.fov, "hp": hp, "alive": alive,
		"on_floor": is_on_floor(), "active": active, "free_flight": free_flight}

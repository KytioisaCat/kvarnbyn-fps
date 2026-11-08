extends CharacterBody3D

# Deliberately outside soldier teams, targeting pools, capture counts and damage API.
const MODELS := {
	"lars": preload("res://assets/characters/civilian_lars.glb"),
	"per": preload("res://assets/characters/civilian_per.glb"),
	"ronny": preload("res://assets/characters/civilian_ronny.glb"),
	"linnea": preload("res://assets/characters/civilian_linnea.glb"),
}
signal approached(person)
signal accidental_shot(person)
var data: Dictionary
var system: Node
var model: Node3D
var animator: AnimationPlayer
var clips: Dictionary = {}
var home := Vector3.ZERO
var destination := Vector3.ZERO
var wait_left := 4.0
var gesture_left := 0.0
var gesture := ""
var time := 0.0
var line_index := 0
var shots_received := 0
var talks := 0
var greeted := false
var outbound := true
var current_clip := ""
var walked_m := 0.0

func configure(settings: Dictionary, owner_system: Node) -> void:
	data = settings.duplicate(true)
	system = owner_system
	name = str(data.id)

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_PAUSABLE
	collision_layer = 8
	collision_mask = 1 | 2 | 4 | 8
	floor_snap_length = 0.25
	floor_max_angle = deg_to_rad(44)
	add_to_group("civilians")
	var shape := CapsuleShape3D.new()
	shape.radius = float(data.radius)
	shape.height = float(data.height)
	var collider := CollisionShape3D.new()
	collider.shape = shape
	collider.position.y = shape.height * 0.5
	add_child(collider)
	model = MODELS[str(data.id)].instantiate()
	add_child(model)
	model.rotation.y = PI # Blender front -Y exports to Godot +Z.
	var players := model.find_children("*", "AnimationPlayer", true, false)
	if not players.is_empty():
		animator = players[0]
		for animation_name in animator.get_animation_list():
			var short_name: String = str(animation_name).get_slice("/", str(animation_name).get_slice_count("/") - 1)
			clips[short_name] = animation_name
			animator.get_animation(animation_name).loop_mode = Animation.LOOP_LINEAR if short_name in ["Idle", "Walk"] else Animation.LOOP_NONE
	for mesh in model.find_children("*", "MeshInstance3D", true, false):
		mesh.visibility_range_end = 140.0
	play_clip("Idle")
	wait_left += float(["lars", "per", "ronny", "linnea"].find(str(data.id))) * 1.1

func place(position_on_ground: Vector3) -> void:
	global_position = position_on_ground + Vector3.UP * 0.015
	home = global_position
	destination = home + data.route
	rotation.y = float(data.heading)

func play_clip(clip: String) -> void:
	if animator != null and clips.has(clip) and current_clip != clip:
		animator.play(clips[clip], 0.18)
		current_clip = clip

func face_point(point: Vector3, delta: float) -> void:
	var direction := point - global_position
	direction.y = 0.0
	if direction.length_squared() > 0.01:
		rotation.y = lerp_angle(rotation.y, atan2(-direction.x, -direction.z), minf(1.0, delta * 3.5))

func _physics_process(delta: float) -> void:
	if not system.is_live():
		if animator: animator.pause()
		velocity = Vector3.ZERO
		return
	if animator and not animator.is_playing(): animator.play()
	time += delta
	gesture_left = maxf(0.0, gesture_left - delta)
	var p: CharacterBody3D = system.player
	var nearby := global_position.distance_to(p.global_position) < 3.8
	if nearby:
		face_point(p.global_position, delta)
		if not greeted:
			greeted = true
			gesture = "Wave"
			gesture_left = 2.4
			approached.emit(self)
	elif global_position.distance_to(p.global_position) > 7.0:
		greeted = false
	var moving := false
	if gesture_left > 0.0:
		play_clip(gesture)
	elif nearby:
		play_clip("Idle")
	else:
		wait_left -= delta
		if wait_left <= 0.0:
			var direction := destination - global_position
			direction.y = 0.0
			if direction.length() < 0.18:
				outbound = not outbound
				destination = home + data.route if outbound else home
				wait_left = 4.0 + float(data.speed) * 3.0
			elif safe_step(direction.normalized()):
				velocity.x = direction.normalized().x * float(data.speed)
				velocity.z = direction.normalized().z * float(data.speed)
				face_point(destination, delta)
				moving = true
			else:
				outbound = not outbound
				destination = home + data.route if outbound else home
				wait_left = 3.0
		play_clip("Walk" if moving else "Idle")
	if not moving:
		velocity.x = 0.0
		velocity.z = 0.0
	velocity.y = -1.0 if is_on_floor() else velocity.y - 24.0 * delta
	var before := global_position
	move_and_slide()
	walked_m += Vector2(global_position.x - before.x, global_position.z - before.z).length()

func safe_step(direction: Vector3) -> bool:
	var ahead := global_position + direction * 0.65
	var space := get_world_3d().direct_space_state
	var ground := space.intersect_ray(PhysicsRayQueryParameters3D.create(ahead + Vector3.UP * 0.55, ahead + Vector3.DOWN * 0.65, 1))
	if ground.is_empty() or absf(ground.position.y - global_position.y) > 0.3 or ground.normal.y < 0.72:
		return false
	var obstacle := space.intersect_ray(PhysicsRayQueryParameters3D.create(global_position + Vector3.UP * 0.8, ahead + Vector3.UP * 0.8, 1 | 2 | 4 | 8))
	return obstacle.is_empty()

func talk() -> String:
	gesture = "Talk"
	gesture_left = 3.0
	current_clip = "" # Repeated conversations restart the gesture.
	play_clip("Talk")
	var lines: Array = data.lines
	var line: String = lines[line_index % lines.size()]
	line_index += 1
	talks += 1
	return line

func on_accidental_shot(_source: Node = null) -> void:
	shots_received += 1
	gesture = "Startle"
	gesture_left = 1.6
	current_clip = ""
	play_clip("Startle")
	accidental_shot.emit(self)

func snapshot() -> Dictionary:
	return {"id": data.id, "name": data.name, "position": [global_position.x, global_position.y, global_position.z], "height": data.height, "radius": data.radius, "animation": current_clip, "walked_m": walked_m, "talks": talks, "accidental_shots": shots_received, "clips": clips.keys()}

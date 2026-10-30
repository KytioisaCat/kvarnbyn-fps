extends CharacterBody3D

## Zonroller och skjutbalans från v1; korta flank-/skyddsval i soldier_tactics.gd.
## Vägnätet bär långa rutter, kapseln bär närfysik och alla stridsmål provas mot mark/hinder.
## Träffzoner: "Head" och "Body". Gevärslinjen kontrolleras på nytt vid varje skott.

const GRAVITY := 16.0
const STEP_HEIGHT := 0.25
const Tactics = preload("res://scripts/soldier_tactics.gd")

var game: Node
var team := "enemy"
var hp := 100.0
var alive := true
var speed := 3.0
var role := "assault"
var home_cap = null
var path := PackedVector3Array()
var path_i := 0
var path_key := ""
var los_t := 0.0
var target: Node3D = null
var can_see := false
var fire_t := 1.5
var lateral := 0.0
var wobble := 0.0
var stuck_t := 0.0
var stuck_n := 0
var last_pos := Vector3.ZERO
var escape_t := 0.0
var escape_dir := Vector3.ZERO
var wander_t := 0.0
var wander_goal := Vector3.ZERO
var dead_t := 0.0
var anim_t := 0.0
var flinch := 0.0
var ground_t := 0.0
var ground_y := 0.0
var cfg := {}
var body_root: Node3D
var leg_l: Node3D
var leg_r: Node3D
var arm_pivot: Node3D
var muzzle: Node3D
var tactics: RefCounted
var tactic_state := "advance"
var tactic_goal := Vector3.ZERO

const SoldierVisual = preload("res://scripts/soldier_visual.gd")
var visual: Node3D

func setup(p_game: Node, p_team: String, p_cfg: Dictionary) -> void:
	game = p_game
	team = p_team
	cfg = p_cfg
	var sp: Array = cfg.get("speed", [2.6, 3.5])
	speed = randf_range(float(sp[0]), float(sp[1]))
	hp = float(cfg.get("hp", 100))
	los_t = randf()
	fire_t = 1.0 + randf() * 2.0
	lateral = randf_range(-1.6, 1.6)
	wobble = randf() * 10.0

func _ready() -> void:
	collision_layer = 4
	collision_mask = 1
	floor_snap_length = 0.6
	floor_max_angle = deg_to_rad(52.0)
	var body := CollisionShape3D.new()
	body.name = "Body"
	var cap := CapsuleShape3D.new()
	cap.radius = 0.3
	cap.height = 1.45
	body.shape = cap
	body.position.y = 0.73
	add_child(body)
	var head := CollisionShape3D.new()
	head.name = "Head"
	var sph := SphereShape3D.new()
	sph.radius = 0.15
	head.shape = sph
	head.position.y = 1.62
	add_child(head)
	_build_model()
	tactics = Tactics.new(self)
	last_pos = global_position

# ---------- modell ----------
func _build_model() -> void:
	visual = SoldierVisual.new()
	body_root = visual
	add_child(visual)
	visual.configure(team)
	muzzle = visual.muzzle

# ---------- skada ----------
func hit(dmg: float, head: bool, from_pos: Vector3, attacker: Node) -> bool:
	if not alive:
		return false
	hp -= dmg
	flinch = 1.0
	if tactics != null:
		tactics.on_hit(from_pos, attacker)
	if hp <= 0.0:
		_die(attacker, head)
		return true
	return false

func _die(attacker: Node, head: bool) -> void:
	alive = false
	collision_layer = 0
	velocity = Vector3.ZERO
	dead_t = 0.0
	if game:
		game.on_soldier_killed(self, attacker, head)

# ---------- AI ----------
func _physics_process(delta: float) -> void:
	if not alive:
		dead_t += delta
		visual.update_pose(delta, Vector3.ZERO, false, false, 0.0)
		if dead_t > 8.0:
			queue_free()
		return
	if game == null or not game.running:
		return
	tactics.step(delta)
	var move: Vector3 = tactics.move
	var face: Vector3 = tactics.face
	var engaging: bool = tactics.engaging
	if face == Vector3.ZERO and move.length() > 0.2:
		face = move
	if face.length_squared() > 0.001:
		var yaw := atan2(-face.x, -face.z)
		rotation.y = lerp_angle(rotation.y, yaw, minf(1.0, delta * 8.0))
	velocity.x = move.x
	velocity.z = move.z
	# långt från spelaren: ingen kollisionsfysik — följ vägnätet och en markstråle (billigt)
	var far: bool = game.player != null and global_position.distance_to(game.player.global_position) > 90.0
	if far:
		if tactics.allow_far_step(move, delta):
			global_position += Vector3(move.x, 0, move.z) * delta
		else:
			velocity.x = 0.0
			velocity.z = 0.0
		ground_t -= delta
		if ground_t <= 0.0:
			ground_t = 0.5
			var q := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP * 3.0, global_position + Vector3.DOWN * 30.0, 1)
			var g := get_world_3d().direct_space_state.intersect_ray(q)
			ground_y = g.position.y if not g.is_empty() else global_position.y
		global_position.y = lerpf(global_position.y, ground_y, minf(1.0, delta * 6.0))
		velocity.y = 0.0
		_animate(delta, engaging)
		return
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	else:
		velocity.y = -0.1
	if is_on_floor() and Vector2(move.x, move.z).length() > 0.1:
		var travel := Vector3(move.x, 0, move.z) * delta
		if test_move(global_transform, travel):
			var raised := global_transform.translated(Vector3.UP * STEP_HEIGHT)
			if not test_move(raised, travel):
				global_position.y += STEP_HEIGHT
	move_and_slide()
	_animate(delta, engaging)

func _animate(delta: float, engaging: bool) -> void:
	flinch = maxf(0.0, flinch - delta * 5.0)
	var local_velocity := global_basis.inverse() * velocity
	visual.update_pose(delta, local_velocity, engaging, alive, flinch)
	var head_shape := get_node("Head") as CollisionShape3D
	head_shape.position = to_local(visual.head_global_position()) + Vector3.UP * 0.04

func _target_alive(t: Node) -> bool:
	return bool(t.get("alive"))

func _plan_escape(dir: Vector3) -> void:
	tactics.plan_escape(dir)

func ai_state() -> Dictionary:
	return tactics.snapshot() if tactics != null else {}

func _shoot(dist: float, in_zone: bool) -> void:
	if not is_instance_valid(target) or not _target_alive(target):
		return
	var sight_from := global_position + Vector3.UP * 1.55
	var sight_to: Vector3 = target.global_position + Vector3.UP * (0.9 if target.get("crouching") else 1.3)
	var sight_query := PhysicsRayQueryParameters3D.create(sight_from, sight_to, 1)
	var from: Vector3 = muzzle.global_position
	var muzzle_query := PhysicsRayQueryParameters3D.create(from, sight_to, 1)
	# Seeing over a wall does not let the lower gun barrel fire through it.
	var space := get_world_3d().direct_space_state
	if not space.intersect_ray(sight_query).is_empty() or not space.intersect_ray(muzzle_query).is_empty():
		can_see = false
		los_t = minf(los_t, 0.1)
		if tactics != null:
			tactics.stats.blocked_shots += 1
		return
	if tactics != null:
		tactics.stats.shots += 1
	var aim: Vector3 = sight_to
	var scatter := Vector3(randf_range(-1, 1), randf_range(-1, 1), randf_range(-1, 1)) * clampf(dist * 0.03, 0.3, 2.0)
	if game.fx:
		game.fx.tracer(from, aim + scatter, team == "enemy")
		game.fx.muzzle(from, 2.0)
		var far: bool = game.player != null and from.distance_to(game.player.global_position) > 60.0
		game.fx.sound_at(from, "shot_far" if far else "shot", -2.0 if not far else 2.0, 1.08)
	var moving := not in_zone and dist > 22.0
	var chance := maxf(0.07, (0.42 - dist / 150.0) * (0.65 if moving else 1.0))
	chance *= float(cfg.get("accuracy_scale", cfg.get("enemy_accuracy_scale", 1.08) if team == "enemy" else 1.0))
	if target.get("crouching"):
		chance *= 0.55
	if randf() < chance:
		var dmg_r: Array = cfg.get("damage", [6, 11])
		var dmg := randf_range(float(dmg_r[0]), float(dmg_r[1]))
		if target.has_method("damage"):
			target.damage(dmg, from)
		elif target.has_method("hit"):
			target.hit(dmg * 3.0, false, from, self)

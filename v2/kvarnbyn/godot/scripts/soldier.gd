extends CharacterBody3D

## Soldat (fiende eller allierad). Beteende ur v1 (public/game.js updateEnemy/updateAllies):
## mål = zon enligt roll (garnison håller sin zon, anfallare tar närmaste zon som inte är vår),
## väg längs vägnätet, siktlinje var 0,4–0,7 s inom 75 m, skjuter inom 70 m med v1:s träff-
## sannolikhet, sidsteg på nära håll, flykt när den fastnat. Träffzoner: "Head" och "Body".

const GRAVITY := 16.0
const STEP_HEIGHT := 0.25

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

static var _meshes := {}
static var _mats := {}

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
	last_pos = global_position

# ---------- modell ----------
static func _mesh(key: String) -> Mesh:
	if _meshes.has(key):
		return _meshes[key]
	var m: Mesh
	match key:
		"torso": m = BoxMesh.new(); m.size = Vector3(0.42, 0.56, 0.25)
		"vest": m = BoxMesh.new(); m.size = Vector3(0.44, 0.34, 0.29)
		"hips": m = BoxMesh.new(); m.size = Vector3(0.36, 0.2, 0.23)
		"leg": m = CapsuleMesh.new(); m.radius = 0.085; m.height = 0.86; m.radial_segments = 8; m.rings = 1
		"boot": m = BoxMesh.new(); m.size = Vector3(0.12, 0.09, 0.26)
		"arm": m = CapsuleMesh.new(); m.radius = 0.06; m.height = 0.52; m.radial_segments = 8; m.rings = 1
		"head": m = SphereMesh.new(); m.radius = 0.115; m.height = 0.24; m.radial_segments = 12; m.rings = 6
		"helmet": m = SphereMesh.new(); m.radius = 0.145; m.height = 0.2; m.is_hemisphere = true; m.radial_segments = 12; m.rings = 4
		"rifle": m = BoxMesh.new(); m.size = Vector3(0.05, 0.08, 0.78)
		"pack": m = BoxMesh.new(); m.size = Vector3(0.32, 0.38, 0.14)
	_meshes[key] = m
	return m

static func _mat(key: String, c: Color) -> StandardMaterial3D:
	if not _mats.has(key):
		var m := StandardMaterial3D.new()
		m.albedo_color = c
		m.roughness = 0.85
		_mats[key] = m
	return _mats[key]

func _part(parent: Node3D, mesh_key: String, mat: Material, pos: Vector3, rot := Vector3.ZERO) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = _mesh(mesh_key)
	mi.material_override = mat
	mi.position = pos
	mi.rotation = rot
	mi.visibility_range_end = 280.0
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if mesh_key in ["torso", "leg", "pack"] else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(mi)
	return mi

func _build_model() -> void:
	var enemy := team == "enemy"
	var uniform := _mat("u_" + team, Color("5c2a26") if enemy else Color("34465c"))
	var vest := _mat("v_" + team, Color("3c3a31") if enemy else Color("2a3340"))
	var helmet := _mat("h_" + team, Color("4a4d44") if enemy else Color("263039"))
	var skin := _mat("skin", Color("c99a7a"))
	var dark := _mat("dark", Color("1a1b1c"))
	body_root = Node3D.new()
	add_child(body_root)
	leg_l = Node3D.new(); leg_l.position = Vector3(-0.1, 0.9, 0); body_root.add_child(leg_l)
	leg_r = Node3D.new(); leg_r.position = Vector3(0.1, 0.9, 0); body_root.add_child(leg_r)
	_part(leg_l, "leg", uniform, Vector3(0, -0.43, 0))
	_part(leg_r, "leg", uniform, Vector3(0, -0.43, 0))
	_part(leg_l, "boot", dark, Vector3(0, -0.86, -0.04))
	_part(leg_r, "boot", dark, Vector3(0, -0.86, -0.04))
	_part(body_root, "hips", uniform, Vector3(0, 0.95, 0))
	_part(body_root, "torso", uniform, Vector3(0, 1.3, 0))
	_part(body_root, "vest", vest, Vector3(0, 1.33, 0))
	_part(body_root, "pack", vest, Vector3(0, 1.32, 0.2))
	_part(body_root, "head", skin, Vector3(0, 1.66, 0))
	_part(body_root, "helmet", helmet, Vector3(0, 1.7, 0))
	arm_pivot = Node3D.new(); arm_pivot.position = Vector3(0, 1.48, 0); body_root.add_child(arm_pivot)
	_part(arm_pivot, "arm", uniform, Vector3(-0.24, -0.1, -0.16), Vector3(1.2, 0, 0.25))
	_part(arm_pivot, "arm", uniform, Vector3(0.22, -0.12, -0.08), Vector3(1.0, 0, -0.35))
	_part(arm_pivot, "rifle", dark, Vector3(0.06, -0.16, -0.32))
	muzzle = Node3D.new(); muzzle.position = Vector3(0.06, -0.14, -0.72); arm_pivot.add_child(muzzle)

# ---------- skada ----------
func hit(dmg: float, head: bool, from_pos: Vector3, attacker: Node) -> bool:
	if not alive:
		return false
	hp -= dmg
	flinch = 1.0
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
		body_root.rotation.x = -minf(PI / 2.0, dead_t * 3.5)
		body_root.position.y = -minf(0.25, dead_t * 0.6)
		if dead_t > 8.0:
			queue_free()
		return
	if game == null or not game.running:
		return
	var target_cap: Dictionary = game.cap_target_for(self)
	var goal: Vector3 = target_cap.get("goal", global_position)
	var key := str(target_cap.get("id", ""))
	if key != path_key or path.is_empty():
		path_key = key
		path = game.nav.path(global_position, goal)
		path_i = 0
	# siktlinje
	los_t -= delta
	if los_t <= 0.0:
		los_t = randf_range(0.4, 0.7)
		target = null
		can_see = false
		var cand: Node3D = game.nearest_hostile(self, float(cfg.get("sight_m", 75)))
		if cand != null:
			var from := global_position + Vector3.UP * 1.55
			var to: Vector3 = cand.global_position + Vector3.UP * (0.9 if cand.get("crouching") else 1.45)
			var q := PhysicsRayQueryParameters3D.create(from, to, 1)
			if get_world_3d().direct_space_state.intersect_ray(q).is_empty():
				target = cand
				can_see = true
	var dist_t := INF
	if target != null and is_instance_valid(target) and _target_alive(target):
		dist_t = global_position.distance_to(target.global_position)
	else:
		can_see = false
	var engaging := can_see and dist_t < float(cfg.get("engage_m", 70))
	var in_zone: bool = target_cap.has("pos") and Vector2(global_position.x - target_cap["pos"].x, global_position.z - target_cap["pos"].z).length() < float(target_cap.get("radius", 15.0)) * 0.8
	var move := Vector3.ZERO
	var face := Vector3.ZERO
	if engaging:
		face = target.global_position - global_position
		fire_t -= delta
		if fire_t <= 0.0:
			var fi: Array = cfg.get("fire_interval_s", [0.75, 1.35])
			fire_t = randf_range(float(fi[0]), float(fi[1]))
			_shoot(dist_t, in_zone)
	if escape_t > 0.0:
		escape_t -= delta
		move = escape_dir * speed
		if escape_t <= 0.0:
			path = PackedVector3Array()
			stuck_t = 0.0
			last_pos = global_position
	elif in_zone and not engaging:
		wander_t -= delta
		if wander_t <= 0.0:
			wander_t = randf_range(2.0, 5.0)
			var r: float = float(target_cap.get("radius", 15.0)) * 0.6
			wander_goal = target_cap["pos"] + Vector3(randf_range(-r, r), 0, randf_range(-r, r))
		var to_w := wander_goal - global_position
		to_w.y = 0
		if to_w.length() > 1.2:
			move = to_w.normalized() * speed * 0.45
	else:
		var mul := 1.0
		if engaging:
			mul = 0.0 if dist_t < 22.0 else 0.65
		if mul == 0.0:
			var to_t := (target.global_position - global_position)
			to_t.y = 0
			var side := Vector3(-to_t.z, 0, to_t.x).normalized()
			move = side * sin(Time.get_ticks_msec() / 1000.0 * 1.7 + wobble * 3.0) * 1.6
		elif path_i < path.size():
			var wp: Vector3 = path[path_i]
			var side_off := Vector3(lateral, 0, lateral * 0.5) if path_i < path.size() - 1 else Vector3.ZERO
			var to := wp + side_off - global_position
			to.y = 0
			if to.length() < 2.6 and path_i < path.size() - 1:
				path_i += 1
			move = to.normalized() * speed * mul if to.length() > 0.3 else Vector3.ZERO
		# fastnat?
		if move.length() > 0.5:
			stuck_t += delta
			if stuck_t > 1.6:
				if global_position.distance_to(last_pos) < 1.0:
					stuck_n += 1
					_plan_escape(move.normalized())
				stuck_t = 0.0
				last_pos = global_position
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
		global_position += Vector3(move.x, 0, move.z) * delta
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
	var hs := Vector2(velocity.x, velocity.z).length()
	anim_t += delta * hs * 2.6
	var swing := sin(anim_t) * clampf(hs / 3.0, 0.0, 1.0) * 0.55
	leg_l.rotation.x = swing
	leg_r.rotation.x = -swing
	flinch = maxf(0.0, flinch - delta * 5.0)
	body_root.rotation.x = -flinch * 0.25
	arm_pivot.rotation.x = 0.0 if engaging else -0.35

func _target_alive(t: Node) -> bool:
	return bool(t.get("alive"))

func _plan_escape(dir: Vector3) -> void:
	var base := atan2(dir.z, dir.x)
	var s := 1.0 if randf() < 0.5 else -1.0
	escape_dir = -dir
	for a in [s * PI / 2, -s * PI / 2, s * PI * 0.78, -s * PI * 0.78, PI]:
		var c := Vector3(cos(base + a), 0, sin(base + a))
		if not test_move(global_transform, c * 2.0):
			escape_dir = c
			break
	escape_t = 0.9 + randf() * 0.5 + minf(1.2, stuck_n * 0.3)

func _shoot(dist: float, in_zone: bool) -> void:
	var from: Vector3 = muzzle.global_position
	var aim: Vector3 = target.global_position + Vector3.UP * 1.3
	var scatter := Vector3(randf_range(-1, 1), randf_range(-1, 1), randf_range(-1, 1)) * clampf(dist * 0.03, 0.3, 2.0)
	if game.fx:
		game.fx.tracer(from, aim + scatter, team == "enemy")
		game.fx.muzzle(from, 2.0)
		var far: bool = game.player != null and from.distance_to(game.player.global_position) > 60.0
		game.fx.sound_at(from, "shot_far" if far else "shot", -2.0 if not far else 2.0, 1.08)
	var moving := not in_zone and dist > 22.0
	var chance := maxf(0.07, (0.42 - dist / 150.0) * (0.65 if moving else 1.0))
	if target.get("crouching"):
		chance *= 0.55
	if randf() < chance:
		var dmg_r: Array = cfg.get("damage", [6, 11])
		var dmg := randf_range(float(dmg_r[0]), float(dmg_r[1]))
		if target.has_method("damage"):
			target.damage(dmg, from)
		elif target.has_method("hit"):
			target.hit(dmg * 3.0, false, from, self)

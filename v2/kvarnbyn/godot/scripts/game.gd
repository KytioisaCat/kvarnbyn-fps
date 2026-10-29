extends Node

## Spelregler (Fas B), funktionerna ur v1 (public/game.js): fienden har tagit Kvarnbyn och håller
## zonerna A Gamla torget, B Roten M och C Royens trappor. Spelaren + allierade tar tillbaka dem.
## Zon tas av den sida som ensam står i den (fiende 0,07/s, vi 0,1/s per soldat, högst 3).
## Fienden får förstärkningar så länge den håller någon zon. Förlust: basen (C) faller igen.
## Vinst: alla zoner våra och inga fiender kvar. Siffror i assets/game.json.

const Soldier = preload("res://scripts/soldier.gd")
const NavGraph = preload("res://scripts/navgraph.gd")
const SFX = preload("res://scripts/sfx.gd")

signal ended(victory: bool)

var cfg := {}
var nav := NavGraph.new()
var fx: Node3D
var player: CharacterBody3D
var hud: Control
var world_root: Node3D
var soldiers_root: Node3D
var running := false
var started := false
var over := false
var victory := false
var caps: Array = []
var enemies: Array = []
var allies: Array = []
var kills := 0
var headshots := 0
var deaths := 0
var reinf_left := 0
var reinf_t := 0.0
var ally_reinf_t := 0.0
var respawn_t := 0.0
var elapsed := 0.0
var spawn_point := Vector3.ZERO
var ui_voice: AudioStreamPlayer

func setup(p_world: Node3D, p_player: CharacterBody3D, p_fx: Node3D, p_hud: Control) -> bool:
	world_root = p_world
	player = p_player
	fx = p_fx
	hud = p_hud
	var data = JSON.parse_string(FileAccess.get_file_as_string("res://assets/game.json"))
	if not data is Dictionary or not nav.load_from("res://assets/nav.json"):
		push_error("game.json eller nav.json saknas")
		return false
	cfg = data
	var sp: Array = cfg["player_spawn"]
	spawn_point = Vector3(sp[0], sp[1], sp[2])
	soldiers_root = Node3D.new()
	soldiers_root.name = "Soldater"
	add_child(soldiers_root)
	ui_voice = AudioStreamPlayer.new()
	ui_voice.volume_db = -6.0
	add_child(ui_voice)
	for c in cfg["caps"]:
		var p: Array = c["position"]
		var cap := {"id": c["id"], "name": c["name"], "pos": Vector3(p[0], p[1], p[2]), "radius": float(c["radius"]),
			"owner": "enemy", "progress": 1.0, "contested": false, "last_alarm": -99.0}
		_make_cap_visual(cap)
		caps.append(cap)
	player.died.connect(_on_player_died)
	return true

func base_cap() -> Dictionary:
	for c in caps:
		if c["id"] == cfg.get("base_cap", "C"):
			return c
	return caps[caps.size() - 1]

func _make_cap_visual(cap: Dictionary) -> void:
	var beam := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = cap["radius"] * 0.32
	cyl.bottom_radius = cap["radius"] * 0.32
	cyl.height = 70.0
	cyl.cap_top = false
	cyl.cap_bottom = false
	beam.mesh = cyl
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.no_depth_test = false
	beam.material_override = m
	beam.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	beam.position = cap["pos"] + Vector3.UP * 35.0
	add_child(beam)
	var label := Label3D.new()
	label.text = cap["id"]
	label.font_size = 220
	label.outline_size = 36
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.no_depth_test = true
	label.fixed_size = false
	label.pixel_size = 0.03
	label.position = cap["pos"] + Vector3.UP * 9.0
	add_child(label)
	cap["beam"] = beam
	cap["label"] = label
	_paint_cap(cap)

func _paint_cap(cap: Dictionary) -> void:
	var c := Color(0.95, 0.27, 0.25) if cap["owner"] == "enemy" else Color(0.3, 0.62, 1.0)
	if cap["contested"]:
		c = Color(1.0, 0.68, 0.25)
	var m: StandardMaterial3D = cap["beam"].material_override
	m.albedo_color = Color(c.r, c.g, c.b, 0.14 + (0.1 * sin(elapsed * 8.0) if cap["contested"] else 0.0))
	(cap["label"] as Label3D).modulate = c

# ---------- start/omstart ----------
func start() -> void:
	if started:
		return
	started = true
	over = false
	victory = false
	running = true
	kills = 0; headshots = 0; deaths = 0; elapsed = 0.0
	for cap in caps:
		cap["owner"] = "enemy"; cap["progress"] = 1.0; cap["contested"] = false
		_paint_cap(cap)
	var occ: Dictionary = cfg["occupation"]
	var tries := 0
	var placed := 0
	while placed < int(occ["count"]) and tries < 2000:
		tries += 1
		var p := nav.random_point()
		if Vector2(p.x - spawn_point.x, p.z - spawn_point.z).length() < float(occ["min_distance_from_spawn"]):
			continue
		var s := spawn_soldier("enemy", p + Vector3(randf_range(-4, 4), 0.3, randf_range(-4, 4)))
		_assign_enemy_role(s, float(occ["garrison_share"]))
		placed += 1
	var c_pos: Vector3 = base_cap()["pos"]
	for i in range(int(occ["infiltrators"])):
		var t := 0.3 + 0.25 * (i % 2) + randf_range(-0.05, 0.05)
		var p := c_pos.lerp(spawn_point, t)
		var n: Vector3 = nav.points[nav.nearest(p)]
		var s := spawn_soldier("enemy", n + Vector3(randf_range(-6, 6), 0.3, randf_range(-6, 6)))
		s.role = "assault"
	var al: Dictionary = cfg["allies"]
	for i in range(int(al["count"])):
		var s := spawn_soldier("ally", spawn_point + Vector3(randf_range(-8, 8), 0.5, randf_range(-8, 8)))
		s.role = "guard" if i < int(al["guards"]) else "assault"
	var rf: Dictionary = cfg["reinforcements"]
	reinf_left = int(rf["waves"])
	reinf_t = float(rf["interval_s"])
	ally_reinf_t = float(al["respawn_interval_s"])
	player.combat_enabled = true
	player.revive(spawn_point + Vector3.UP * 0.2, _yaw_toward(spawn_point, c_pos))
	if hud:
		hud.feed("Fienden har tagit Kvarnbyn. Ta tillbaka Royens trappor (C) först!")

func restart() -> void:
	for s in soldiers_root.get_children():
		s.queue_free()
	enemies.clear()
	allies.clear()
	started = false
	start()

func _yaw_toward(from: Vector3, to: Vector3) -> float:
	var d := to - from
	return atan2(-d.x, -d.z)

func spawn_soldier(team: String, at: Vector3) -> Node:
	var s: CharacterBody3D = Soldier.new()
	s.setup(self, team, cfg["soldier"])
	soldiers_root.add_child(s)
	s.global_position = at
	(enemies if team == "enemy" else allies).append(s)
	return s

func _assign_enemy_role(s: Node, garrison_share: float) -> void:
	var held: Array = caps.filter(func(c): return c["owner"] == "enemy")
	if not held.is_empty() and randf() < garrison_share:
		s.role = "garrison"
		s.home_cap = held[randi() % held.size()]
	else:
		s.role = "assault"

# ---------- frågor från soldaterna ----------
func cap_target_for(s: Node) -> Dictionary:
	var cap = null
	if s.team == "enemy":
		if s.role == "garrison" and s.home_cap != null and s.home_cap["owner"] == "enemy":
			cap = s.home_cap
		else:
			var best := INF
			for c in caps:
				if c["owner"] == "enemy":
					continue
				var d: float = s.global_position.distance_to(c["pos"])
				if d < best:
					best = d
					cap = c
			if cap == null:
				cap = base_cap()
	else:
		if s.role == "guard":
			cap = base_cap()
		else:
			for id in ["C", "B", "A"]:
				for c in caps:
					if c["id"] == id and c["owner"] == "enemy" and cap == null:
						cap = c
			if cap == null:
				cap = base_cap()
	var off := Vector3(s.lateral * 2.5, 0, s.lateral * 1.8)
	return {"id": cap["id"], "pos": cap["pos"], "radius": cap["radius"], "goal": cap["pos"] + off}

func nearest_hostile(s: Node, max_d: float) -> Node3D:
	var best: Node3D = null
	var best_d := max_d
	var pool: Array = allies if s.team == "enemy" else enemies
	for o in pool:
		if not o.alive:
			continue
		var d: float = s.global_position.distance_to(o.global_position)
		if d < best_d:
			best_d = d
			best = o
	if s.team == "enemy" and player.alive and player.combat_enabled:
		var d: float = s.global_position.distance_to(player.global_position)
		if d < best_d * 1.15:
			best = player
	return best

# ---------- händelser ----------
func on_soldier_killed(s: Node, attacker: Node, head: bool) -> void:
	if s.team == "enemy":
		enemies.erase(s)
		if attacker == player:
			kills += 1
			if head:
				headshots += 1
	else:
		allies.erase(s)
		s.set_meta("dead_ally", true)
		if hud and attacker != null:
			hud.feed("En kamrat har stupat.")

func _on_player_died() -> void:
	deaths += 1
	respawn_t = float(cfg["player"]["respawn_s"])
	if hud:
		hud.feed("Du stupade! Återuppstår vid Görjelycksgatan om %d s…" % int(respawn_t))

func _play(sound_name: String) -> void:
	ui_voice.stream = SFX.get_sound(sound_name)
	ui_voice.play()

func _physics_process(delta: float) -> void:
	if not running or over:
		for cap in caps:
			if cap.has("beam"):
				_paint_cap(cap)
		return
	elapsed += delta
	_update_caps(delta)
	# spelarens död
	if not player.alive:
		respawn_t -= delta
		if respawn_t <= 0.0:
			player.revive(spawn_point + Vector3.UP * 0.2, _yaw_toward(spawn_point, base_cap()["pos"]))
	# förstärkningar
	var enemy_holds := caps.any(func(c): return c["owner"] == "enemy")
	if enemy_holds and reinf_left > 0:
		reinf_t -= delta
		var rf: Dictionary = cfg["reinforcements"]
		if reinf_t <= 0.0 and enemies.size() < int(rf["max_alive"]):
			reinf_left -= 1
			reinf_t = float(rf["interval_s"])
			for i in range(int(rf["size"])):
				var s := spawn_soldier("enemy", _pick_entry())
				_assign_enemy_role(s, 0.4)
			if hud: hud.feed("Fientliga förstärkningar strömmar in — de håller fortfarande zoner!")
			_play("alarm")
	# allierade förstärkningar
	ally_reinf_t -= delta
	if ally_reinf_t <= 0.0:
		ally_reinf_t = float(cfg["allies"]["respawn_interval_s"])
		var missing: int = int(cfg["allies"]["count"]) - allies.size()
		for i in range(missing):
			var s := spawn_soldier("ally", spawn_point + Vector3(randf_range(-8, 8), 0.5, randf_range(-8, 8)))
			s.role = "assault"
		if missing > 0 and hud:
			hud.feed("Förstärkning ansluter från basen!")
	# vinst
	if not enemy_holds and enemies.is_empty():
		_end(true)

func _pick_entry() -> Vector3:
	var entries: Array = cfg["enemy_entries"]
	var best := Vector3.ZERO
	var best_d := -1.0
	for i in range(8):
		var e: Array = entries[randi() % entries.size()]
		var p := Vector3(e[0], e[1], e[2]) + Vector3(randf_range(-12, 12), 0, randf_range(-12, 12))
		var n: Vector3 = nav.points[nav.nearest(p)]
		var d := n.distance_to(player.global_position)
		if d > best_d:
			best_d = d
			best = n
		if d > 70.0:
			return n + Vector3.UP * 0.4
	return best + Vector3.UP * 0.4

func _update_caps(delta: float) -> void:
	var rates: Dictionary = cfg["capture"]
	for cap in caps:
		var e := 0
		for s in enemies:
			if s.alive and Vector2(s.global_position.x - cap["pos"].x, s.global_position.z - cap["pos"].z).length() < cap["radius"]:
				e += 1
		var f := 0
		if player.alive and Vector2(player.global_position.x - cap["pos"].x, player.global_position.z - cap["pos"].z).length() < cap["radius"]:
			f += 1
		for s in allies:
			if s.alive and Vector2(s.global_position.x - cap["pos"].x, s.global_position.z - cap["pos"].z).length() < cap["radius"]:
				f += 1
		cap["contested"] = false
		cap["enemies_in"] = e
		cap["friends_in"] = f
		if e > 0 and f == 0 and cap["owner"] != "enemy":
			cap["progress"] += delta * float(rates["enemy_rate"]) * mini(e, int(rates["max_count"]))
			cap["contested"] = true
			if cap["progress"] > 0.02 and elapsed - cap["last_alarm"] > 25.0:
				cap["last_alarm"] = elapsed
				if hud: hud.feed("%s är under anfall!" % cap["name"])
				_play("alarm")
			if cap["progress"] >= 1.0:
				cap["owner"] = "enemy"
				cap["progress"] = 1.0
				if hud: hud.feed("Fienden har tagit %s!" % cap["name"])
				_play("bad")
				if cap["id"] == cfg.get("base_cap", "C"):
					_end(false)
					return
		elif f > 0 and e == 0 and (cap["owner"] == "enemy" or cap["progress"] > 0.0):
			cap["progress"] -= delta * float(rates["friendly_rate"]) * mini(f, int(rates["max_count"]))
			cap["contested"] = cap["owner"] == "enemy"
			if cap["progress"] <= 0.0:
				cap["progress"] = 0.0
				if cap["owner"] == "enemy":
					cap["owner"] = "friendly"
					if hud: hud.feed("%s återtaget! Frontlinjen flyttas." % cap["name"])
					_play("good")
		elif e > 0 and f > 0:
			cap["contested"] = true
		_paint_cap(cap)

func _end(won: bool) -> void:
	if over:
		return
	over = true
	victory = won
	running = false
	_play("good" if won else "bad")
	ended.emit(won)

func state() -> Dictionary:
	var cs := []
	for c in caps:
		cs.append({"id": c["id"], "owner": c["owner"], "progress": snappedf(c["progress"], 0.01), "enemies_in": c.get("enemies_in", 0), "friends_in": c.get("friends_in", 0)})
	return {"running": running, "over": over, "victory": victory, "elapsed_s": snappedf(elapsed, 0.1), "kills": kills,
		"headshots": headshots, "deaths": deaths, "enemies": enemies.size(), "allies": allies.size(),
		"reinforcements_left": reinf_left, "caps": cs, "player_hp": snappedf(player.hp, 0.1), "player_alive": player.alive}

extends Node3D

## Spelarens vapen (Ak 5, automatkarbin). Funktioner ur v1: 30 skott, ~600 skott/min, 40 skada
## kropp / 100 huvud, omladdning 1,7 s. Känsla (Fas B, ny): siktläge på höger musknapp, rekyl som
## sparkar kameran och återhämtar sig, spridning som växer med rörelse/eldgivning, vapen som gungar
## och svajar, mynningsflamma med ljus, spårljus, nedslag, träffmarkör och ljud.

const SFX = preload("res://scripts/sfx.gd")

var player: CharacterBody3D
var fx: Node3D
var hud: Control
var mag_size := 30
var mag := 30
var rpm := 600.0
var damage_body := 40.0
var damage_head := 100.0
var reload_time := 1.7
var range_m := 400.0
var reloading := false
var reload_t := 0.0
var reload_total := 1.7
var fire_cd := 0.0
var ads := 0.0
var bloom := 0.0
var kick := 0.0
var shots := 0
var sprint_pose := 0.0
var sway := Vector2.ZERO
var last_cam_rot := Vector2.ZERO
var r_was_down := false
var bot_trigger := false
var bot_ads := false
var bot_reload := false
var model: Node3D
var muzzle_point: Node3D
var flash_light: OmniLight3D
var flash_mesh: MeshInstance3D
var flash_t := 0.0
var shot_voice: AudioStreamPlayer
var mech_voice: AudioStreamPlayer
var hit_voice: AudioStreamPlayer
var reload_events: Array = []

const SCALE := 0.55
const HIP := Vector3(0.12, -0.13, -0.30)
const AIM := Vector3(0.0, -0.088 * SCALE, -0.20)
const SPRINT := Vector3(0.10, -0.17, -0.26)

func _ready() -> void:
	model = Node3D.new()
	model.scale = Vector3.ONE * SCALE
	add_child(model)
	_build_rifle()
	shot_voice = _voice(SFX.get_sound("shot"), -3.0)
	mech_voice = _voice(SFX.get_sound("mag_out"), -6.0)
	hit_voice = _voice(SFX.get_sound("hit"), -6.0)
	position = HIP

func _voice(stream: AudioStream, db: float) -> AudioStreamPlayer:
	var a := AudioStreamPlayer.new()
	a.stream = stream
	a.volume_db = db
	add_child(a)
	return a

func _mat(c: Color, rough: float, metal: float) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = rough
	m.metallic = metal
	return m

func _part(mesh: Mesh, mat: Material, pos: Vector3, rot := Vector3.ZERO) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat
	mi.position = pos
	mi.rotation = rot
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	model.add_child(mi)
	return mi

func _box(size: Vector3) -> BoxMesh:
	var b := BoxMesh.new()
	b.size = size
	return b

func _build_rifle() -> void:
	var steel := _mat(Color(0.2, 0.21, 0.22), 0.38, 0.8)
	var polymer := _mat(Color(0.25, 0.28, 0.22), 0.6, 0.0)
	var glove := _mat(Color(0.42, 0.37, 0.28), 0.85, 0.0)
	# lådan längs −Z, siktlinjen i y = +0.088 så att siktläge ligger mitt i bild
	_part(_box(Vector3(0.055, 0.085, 0.34)), steel, Vector3(0, 0, -0.02))
	var barrel := CylinderMesh.new()
	barrel.top_radius = 0.011
	barrel.bottom_radius = 0.011
	barrel.height = 0.36
	_part(barrel, steel, Vector3(0, 0.012, -0.36), Vector3(PI / 2, 0, 0))
	var brake := CylinderMesh.new()
	brake.top_radius = 0.016
	brake.bottom_radius = 0.016
	brake.height = 0.07
	_part(brake, steel, Vector3(0, 0.012, -0.55), Vector3(PI / 2, 0, 0))
	_part(_box(Vector3(0.062, 0.07, 0.22)), polymer, Vector3(0, 0.0, -0.27))
	_part(_box(Vector3(0.032, 0.17, 0.07)), steel, Vector3(0, -0.11, -0.07), Vector3(0.28, 0, 0))
	_part(_box(Vector3(0.04, 0.11, 0.05)), polymer, Vector3(0, -0.09, 0.08), Vector3(-0.35, 0, 0))
	_part(_box(Vector3(0.045, 0.075, 0.26)), polymer, Vector3(0, -0.02, 0.27))
	_part(_box(Vector3(0.05, 0.11, 0.04)), polymer, Vector3(0, -0.05, 0.39))
	# bärhandtag/sikte och korn
	_part(_box(Vector3(0.022, 0.03, 0.2)), steel, Vector3(0, 0.06, 0.0))
	_part(_box(Vector3(0.026, 0.026, 0.012)), steel, Vector3(0, 0.083, 0.06))
	_part(_box(Vector3(0.006, 0.05, 0.008)), steel, Vector3(0, 0.055, -0.5))
	# händer
	_part(_box(Vector3(0.07, 0.07, 0.11)), glove, Vector3(0.0, -0.06, 0.1))
	_part(_box(Vector3(0.08, 0.06, 0.12)), glove, Vector3(-0.01, -0.035, -0.3))
	muzzle_point = Node3D.new()
	muzzle_point.position = Vector3(0, 0.012, -0.6)
	model.add_child(muzzle_point)
	flash_light = OmniLight3D.new()
	flash_light.light_color = Color(1.0, 0.72, 0.38)
	flash_light.omni_range = 6.0
	flash_light.light_energy = 0.0
	flash_light.light_volumetric_fog_energy = 0.0
	flash_light.visible = false
	muzzle_point.add_child(flash_light)
	flash_mesh = MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(0.16, 0.16)
	flash_mesh.mesh = q
	var fm := StandardMaterial3D.new()
	fm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	fm.albedo_color = Color(1.0, 0.8, 0.45)
	fm.emission_enabled = true
	fm.emission = Color(1.0, 0.7, 0.35)
	fm.emission_energy_multiplier = 8.0
	fm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	fm.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	flash_mesh.material_override = fm
	flash_mesh.visible = false
	flash_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	muzzle_point.add_child(flash_mesh)

func refill() -> void:
	mag = mag_size
	reloading = false
	reload_events.clear()

func current_spread() -> float:
	var hspeed := Vector2(player.velocity.x, player.velocity.z).length()
	var s := lerpf(0.016, 0.0025, ads)
	s += clampf(hspeed / 7.0, 0.0, 1.0) * 0.022 * (1.0 - 0.7 * ads)
	if not player.is_on_floor():
		s += 0.04
	if player.crouching:
		s *= 0.7
	return s + bloom

func _trigger() -> bool:
	if player.bot_input != null:
		return bot_trigger
	return Input.mouse_mode == Input.MOUSE_MODE_CAPTURED and Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT)

func _aim() -> bool:
	if player.bot_input != null:
		return bot_ads
	return Input.mouse_mode == Input.MOUSE_MODE_CAPTURED and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT)

func start_reload() -> void:
	if reloading or mag == mag_size or not player.alive:
		return
	reloading = true
	reload_total = reload_time if mag > 0 else reload_time + 0.5
	reload_t = reload_total
	reload_events = [[reload_total - 0.15, "mag_out"], [reload_total - 1.05, "mag_in"]]
	if mag == 0:
		reload_events.append([0.25, "bolt"])

func _process(delta: float) -> void:
	if player == null:
		return
	var can_act: bool = player.active and not player.input_suspended and player.alive and player.combat_enabled
	visible = player.alive and player.combat_enabled
	fire_cd = maxf(0.0, fire_cd - delta)
	bloom = maxf(0.0, bloom - delta * 0.06)
	kick = lerpf(kick, 0.0, minf(1.0, delta * 14.0))
	flash_t -= delta
	if flash_t <= 0.0:
		flash_light.light_energy = 0.0
		flash_light.visible = false
		flash_mesh.visible = false
	# omladdning
	if reloading:
		reload_t -= delta
		for ev in reload_events.duplicate():
			if reload_t <= ev[0]:
				mech_voice.stream = SFX.get_sound(ev[1])
				mech_voice.play()
				reload_events.erase(ev)
		if reload_t <= 0.0:
			reloading = false
			mag = mag_size
	# inmatning
	var want_ads: bool = can_act and _aim() and not reloading and not player.sprinting
	ads = move_toward(ads, 1.0 if want_ads else 0.0, delta * 6.5)
	var r_down: bool = player.bot_input == null and Input.is_physical_key_pressed(KEY_R)
	if can_act and ((r_down and not r_was_down) or bot_reload):
		bot_reload = false
		start_reload()
	r_was_down = r_down
	sprint_pose = move_toward(sprint_pose, 1.0 if player.sprinting else 0.0, delta * 5.0)
	if can_act and _trigger() and fire_cd <= 0.0 and not reloading and sprint_pose < 0.35:
		if mag > 0:
			_fire()
		else:
			fire_cd = 0.3
			mech_voice.stream = SFX.get_sound("empty")
			mech_voice.play()
			start_reload()
	# vapnets pose: höft/sikte/sprint + gung + svaj + rekyl + omladdning
	var cam_rot := Vector2(player.rotation.y, player.camera.rotation.x)
	var d := cam_rot - last_cam_rot
	last_cam_rot = cam_rot
	sway = sway.lerp(Vector2(clampf(d.x * 0.8, -0.05, 0.05), clampf(d.y * 0.8, -0.05, 0.05)), minf(1.0, delta * 9.0))
	var pose := HIP.lerp(AIM, ads)
	pose = pose.lerp(SPRINT, sprint_pose)
	var hspeed := Vector2(player.velocity.x, player.velocity.z).length()
	var bob: float = player.bob_t
	var bob_amt := clampf(hspeed / 4.4, 0.0, 1.5) * (1.0 - ads * 0.85)
	pose += Vector3(sin(bob * 0.5) * 0.008 * bob_amt, -absf(cos(bob * 0.5)) * 0.01 * bob_amt, 0)
	pose += Vector3(sway.x * 0.6, -sway.y * 0.4, kick * 0.05)
	var reload_k := 0.0
	if reloading:
		var u := 1.0 - reload_t / reload_total
		reload_k = sin(clampf(u, 0.0, 1.0) * PI)
		pose += Vector3(-0.02, -0.11, 0.02) * reload_k
	position = pose
	model.rotation = Vector3(kick * 0.09 - reload_k * 0.5 + sprint_pose * -0.25, -sway.x * 0.6 + sprint_pose * 0.7, reload_k * 0.6 + sprint_pose * 0.25)

func _fire() -> void:
	mag -= 1
	shots += 1
	fire_cd = 60.0 / rpm
	kick = 1.0
	shot_voice.pitch_scale = randf_range(0.95, 1.05)
	shot_voice.play()
	flash_t = 0.045
	flash_light.light_energy = 5.0
	flash_light.visible = true
	flash_mesh.visible = true
	flash_mesh.rotation.z = randf() * TAU
	var spread := current_spread()
	bloom = minf(0.03, bloom + 0.0045 * (1.0 - 0.6 * ads))
	player.kick(randf_range(-0.003, 0.003) * (1.0 - 0.5 * ads), randf_range(0.010, 0.014) * (1.0 - 0.45 * ads))
	var cam: Camera3D = player.camera
	var origin := cam.global_position
	var angle := randf() * TAU
	var r := spread * sqrt(randf())
	var local_dir := Vector3(cos(angle) * r, sin(angle) * r, -1.0).normalized()
	var dir := (cam.global_transform.basis * local_dir).normalized()
	var query := PhysicsRayQueryParameters3D.create(origin, origin + dir * range_m, 1 | 4)
	query.exclude = [player.get_rid()]
	var hit := player.get_world_3d().direct_space_state.intersect_ray(query)
	var end := origin + dir * range_m
	if not hit.is_empty():
		end = hit.position
		var collider = hit.collider
		if collider != null and collider.has_method("hit"):
			var owner_id: int = collider.shape_find_owner(int(hit.shape))
			var shape_node = collider.shape_owner_get_owner(owner_id)
			var head: bool = shape_node != null and str(shape_node.name) == "Head"
			var killed: bool = collider.hit(damage_head if head else damage_body, head, origin, player)
			if fx: fx.impact(hit.position, hit.normal, "blood")
			hit_voice.stream = SFX.get_sound("kill" if killed else ("head" if head else "hit"))
			hit_voice.play()
			if hud: hud.hitmarker("kill" if killed else ("head" if head else "hit"))
		elif fx:
			fx.impact(hit.position, hit.normal, "hard" if absf(hit.normal.y) < 0.6 else "dust")
	if fx and shots % 2 == 0:
		fx.tracer(muzzle_point.global_position, end)

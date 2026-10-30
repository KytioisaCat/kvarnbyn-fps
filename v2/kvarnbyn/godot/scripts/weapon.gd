extends Node3D

## Spelarens vapen (Ak 5, automatkarbin). Funktioner ur v1: 30 skott, ~600 skott/min, 40 skada
## kropp / 100 huvud, omladdning 1,7 s. Känsla (Fas B, ny): siktläge på höger musknapp, rekyl som
## sparkar kameran och återhämtar sig, spridning som växer med rörelse/eldgivning, vapen som gungar
## och svajar, mynningsflamma med ljus, spårljus, nedslag, träffmarkör och ljud.

const SFX = preload("res://scripts/sfx.gd")
const RIFLE_PATH := "res://assets/weapons/ak5_view.glb"

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
var rifle: Node3D
var model_asset_loaded := false
var rear_sight: Node3D
var front_sight: Node3D
var magazine_node: Node3D
var magazine_rest := Transform3D.IDENTITY
var bolt_node: Node3D
var bolt_rest := Transform3D.IDENTITY
var reload_empty := false

const SCALE := 0.55
const HIP := Vector3(0.12, -0.13, -0.30)
# Blender's two iron-sight centers share Y=.117 in Godot meters.
# Align that plane with the camera; the bore/muzzle remains below the sights.
const SIGHT_HEIGHT := 0.117
const AIM := Vector3(0.0, -SIGHT_HEIGHT * SCALE, -0.235)
const SPRINT := Vector3(0.10, -0.17, -0.26)

func _ready() -> void:
	model = Node3D.new()
	model.name = "ViewModel"
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

func _prepare_view_meshes(node: Node) -> void:
	if node is GeometryInstance3D:
		node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		node.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
		# A near-camera mesh must not disappear behind the world's occlusion cells.
		node.ignore_occlusion_culling = true
	for child in node.get_children():
		_prepare_view_meshes(child)

func _build_rifle() -> void:
	if ResourceLoader.exists(RIFLE_PATH):
		var scene := load(RIFLE_PATH) as PackedScene
		if scene != null:
			rifle = scene.instantiate()
			rifle.name = "Ak5"
			model.add_child(rifle)
			_prepare_view_meshes(rifle)
			model_asset_loaded = true
			rear_sight = rifle.find_child("Sight_Rear", true, false) as Node3D
			front_sight = rifle.find_child("Sight_Front", true, false) as Node3D
			magazine_node = rifle.find_child("Magazine", true, false) as Node3D
			bolt_node = rifle.find_child("Charging_Handle", true, false) as Node3D
			if magazine_node != null:
				magazine_rest = magazine_node.transform
			if bolt_node != null:
				bolt_rest = bolt_node.transform
	else:
		push_warning("Ak 5-modellen saknas. Kör blender/build_ak5.py och importera Godot-projektet.")
	# The imported marker is at the actual rendered muzzle, not a guessed old box offset.
	muzzle_point = rifle.find_child("Muzzle", true, false) as Node3D if rifle != null else null
	if muzzle_point == null:
		muzzle_point = Node3D.new()
		muzzle_point.name = "MuzzleFallback"
		muzzle_point.position = Vector3(0, 0.018, -0.623)
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
	reload_empty = false
	_update_component_pose(0.0)

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
	reload_empty = mag == 0
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
		# Keep the detailed model visible while the magazine moves. Same easing/timing.
		pose += Vector3(-0.025, 0.025, -0.05) * reload_k
	position = pose
	model.rotation = Vector3(kick * 0.09 + reload_k * 0.22 + sprint_pose * -0.25, -sway.x * 0.6 + reload_k * 0.05 + sprint_pose * 0.7, -reload_k * 0.45 + sprint_pose * 0.25)
	_update_component_pose(1.0 - reload_t / reload_total if reloading else 0.0)

func _update_component_pose(progress: float) -> void:
	# Cosmetic component motion follows the existing reload/sound timing.
	# It does not change ammo, shooting, recoil, or tactical/empty reload duration.
	if magazine_node != null:
		magazine_node.transform = magazine_rest
		if reloading:
			var pull := smoothstep(0.06, 0.25, progress) * (1.0 - smoothstep(0.43, 0.63, progress))
			magazine_node.position += Vector3(0, -0.13, 0.025) * pull
			magazine_node.rotate_x(-0.13 * pull)
			magazine_node.rotate_z(-0.12 * pull)
	if bolt_node != null:
		bolt_node.transform = bolt_rest
		if reloading and reload_empty:
			var pull := sin(clampf((progress - 0.76) / 0.18, 0.0, 1.0) * PI)
			bolt_node.position.z += 0.035 * pull

func visual_snapshot() -> Dictionary:
	var result := {"model_loaded": model_asset_loaded, "asset": RIFLE_PATH,
		"mag": mag, "reloading": reloading, "ads": ads}
	if player != null and rear_sight != null and front_sight != null:
		var camera: Camera3D = player.camera
		var center := get_viewport().get_visible_rect().size * 0.5
		var rear := camera.unproject_position(rear_sight.global_position)
		var front := camera.unproject_position(front_sight.global_position)
		result["rear_screen"] = [rear.x, rear.y]
		result["front_screen"] = [front.x, front.y]
		result["sight_center_error_px"] = maxf(rear.distance_to(center), front.distance_to(center))
		var muzzle_local := camera.to_local(muzzle_point.global_position)
		result["muzzle_camera_local"] = [muzzle_local.x, muzzle_local.y, muzzle_local.z]
	return result

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

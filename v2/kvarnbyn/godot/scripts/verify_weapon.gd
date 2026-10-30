extends SceneTree

## Isolated gameplay/model verification. Native mode also saves hip/ADS/reload captures.
## Godot --audio-driver Dummy --path v2/kvarnbyn/godot --script res://scripts/verify_weapon.gd -- --screenshots
const Player = preload("res://scripts/player.gd")
const SFX = preload("res://scripts/sfx.gd")
const Lighting = preload("res://scripts/lighting.gd")
var checks: Array = []
var failed := false
var screenshots := false
var out := ""
var player: CharacterBody3D
var weapon: Node3D
var stage: Node3D

func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	call_deferred("run")

func check(label: String, value: bool, details = null) -> void:
	checks.append({"test": label, "pass": value, "details": details})
	print("WEAPON_", "PASS " if value else "FAIL ", label, " ", JSON.stringify(details))
	failed = failed or not value

func tick(frames: int) -> void:
	for frame in range(frames):
		weapon._process(1.0 / 60.0)
		player._process(1.0 / 60.0)

func capture(label: String) -> void:
	if not screenshots:
		return
	for frame in range(12):
		await process_frame
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	var path := out.path_join("ak5_" + label + ".png")
	check("native_capture_" + label, image.save_png(path) == OK, path)

func simple_material(color: Color) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.9
	return material

func run() -> void:
	screenshots = "--screenshots" in OS.get_cmdline_user_args()
	out = ProjectSettings.globalize_path("res://").trim_suffix("/").get_base_dir().path_join("evidence/weapon")
	DirAccess.make_dir_recursive_absolute(out)
	root.size = Vector2i(1600, 900)
	stage = Node3D.new()
	root.add_child(stage)
	stage.add_child(Lighting.make_environment())
	stage.add_child(Lighting.make_sun())
	var floor_body := StaticBody3D.new()
	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(20, 0.2, 40)
	collision.shape = shape
	collision.position.y = -0.1
	floor_body.add_child(collision)
	stage.add_child(floor_body)
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(20, 40)
	ground.mesh = plane
	ground.material_override = simple_material(Color(0.28, 0.30, 0.25))
	stage.add_child(ground)
	# A quiet calibration backdrop shows viewmodel scale and sight alignment.
	for i in range(7):
		var post := MeshInstance3D.new()
		var cube := BoxMesh.new()
		cube.size = Vector3(0.08, 2.0, 0.08)
		post.mesh = cube
		post.position = Vector3((i - 3) * 1.5, 1, -9)
		post.material_override = simple_material(Color(0.23, 0.31, 0.25))
		stage.add_child(post)
	player = Player.new()
	stage.add_child(player)
	player.active = true
	player.combat_enabled = true
	player.bot_input = Vector2.ZERO
	weapon = player.weapon
	await physics_frame
	await physics_frame
	player.set_process(false)
	player.set_physics_process(false)
	weapon.set_process(false)
	check("imported_asset", weapon.model_asset_loaded)
	check("named_anchors", weapon.muzzle_point != null and weapon.rear_sight != null and weapon.front_sight != null)
	check("animated_magazine", weapon.magazine_node != null)
	check("charging_handle", weapon.bolt_node != null)
	weapon.bot_ads = false
	tick(90)
	var hip: Dictionary = weapon.visual_snapshot()
	await capture("hip")
	weapon.bot_ads = true
	tick(90)
	var ads: Dictionary = weapon.visual_snapshot()
	check("ADS_sights_align_with_camera", float(ads.get("sight_center_error_px", 999)) < 0.1, ads)
	check("muzzle_below_sight_axis", float(ads["muzzle_camera_local"][1]) < -0.02, ads["muzzle_camera_local"])
	await capture("ads")
	weapon.bot_ads = false
	tick(90)
	weapon.bot_trigger = true
	tick(60)
	weapon.bot_trigger = false
	check("auto_fire_cadence_and_ammo", weapon.shots >= 9 and weapon.shots <= 11 and weapon.mag == weapon.mag_size - weapon.shots, {"shots_in_one_second": weapon.shots, "mag": weapon.mag})
	weapon.start_reload()
	var expected_tactical: float = weapon.reload_total
	tick(40)
	check("magazine_moves_during_reload", weapon.magazine_node.position.distance_to(weapon.magazine_rest.origin) > 0.07)
	await capture("reload")
	var tactical_frames := 40
	while weapon.reloading and tactical_frames < 160:
		tick(1)
		tactical_frames += 1
	check("tactical_reload_time_and_refill", weapon.mag == 30 and absf(tactical_frames / 60.0 - expected_tactical) < 0.05, {"duration": tactical_frames / 60.0, "expected": expected_tactical})
	check("magazine_restored", weapon.magazine_node.transform.is_equal_approx(weapon.magazine_rest))
	weapon.mag = 0
	weapon.start_reload()
	var expected_empty: float = weapon.reload_total
	var empty_frames := 0
	var saw_bolt := false
	while weapon.reloading and empty_frames < 180:
		tick(1)
		empty_frames += 1
		saw_bolt = saw_bolt or weapon.bolt_node.position.distance_to(weapon.bolt_rest.origin) > 0.02
	check("empty_reload_time_and_refill", weapon.mag == 30 and absf(empty_frames / 60.0 - expected_empty) < 0.05, {"duration": empty_frames / 60.0, "expected": expected_empty})
	check("empty_reload_bolt_motion", saw_bolt)
	check("bolt_restored", weapon.bolt_node.transform.is_equal_approx(weapon.bolt_rest))
	var report := {"passed": not failed, "checks": checks, "hip": hip, "ads": ads, "engine": Engine.get_version_info(), "renderer": RenderingServer.get_current_rendering_method()}
	var file := FileAccess.open(out.path_join("weapon_qa.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t"))
	print("KVARNBYN_WEAPON_QA ", JSON.stringify(report))
	for voice in player.find_children("*", "AudioStreamPlayer", true, false):
		voice.stop()
	stage.queue_free()
	for frame in range(3):
		await process_frame
	SFX._cache.clear()
	quit(1 if failed else 0)

extends Node

const Settings = preload("res://scripts/movement_settings.gd")
const Fixture = preload("res://scripts/grapple_check.gd")
const Player = preload("res://scripts/player.gd")
var checks: Array = []

func check(name: String, passed: bool, details: Variant = null) -> void:
	checks.append({"name": name, "passed": passed, "details": details})

func frames(count: int) -> void:
	for frame in range(count):
		await get_tree().physics_frame

func press(code: Key) -> void:
	var event := InputEventKey.new()
	event.physical_keycode = code
	event.pressed = true
	Input.parse_input_event(event)
	await get_tree().process_frame
	event = InputEventKey.new()
	event.physical_keycode = code
	Input.parse_input_event(event)
	await get_tree().process_frame

func coast(fixture: Node3D, height: float, ticks: int) -> Dictionary:
	await fixture.reset(Vector3(0, 0.05, 30))
	fixture.p.position.y += height
	fixture.p.velocity = Vector3(16, 0, 0)
	fixture.p.momentum_mode = true
	var start: Vector3 = fixture.p.position
	await frames(ticks)
	return {"speed": Vector2(fixture.p.velocity.x, fixture.p.velocity.z).length(),
		"distance": fixture.p.position.distance_to(start), "on_floor": fixture.p.is_on_floor()}

func run(world: Node3D) -> Dictionary:
	process_mode = Node.PROCESS_MODE_ALWAYS
	AudioServer.set_bus_mute(0, true)
	var settings: RefCounted = world.player.movement
	var original_path: String = settings.storage_path
	var original_persistence: bool = settings.persistence_enabled
	var ui_profile_path := OS.get_temp_dir().path_join("kvarnbyn-menu-%s.cfg" % str(Time.get_ticks_usec()))
	settings.storage_path = ui_profile_path
	settings.persistence_enabled = true
	settings.reset_defaults()
	world.begin_walk()
	await frames(3)
	await press(KEY_ESCAPE)
	var panel: PanelContainer = world.overlay.movement_panel
	check("Escape opens movement menu and pauses battle", panel.visible and world.overlay.opening and get_tree().paused and not world.player.active)
	check("all 24 values have sliders and exact number fields", panel.rows.size() == Settings.DEFINITIONS.size() and panel.rows.size() == 24)
	check("slower pull and longer landing glide are defaults", settings.get_value("reel_speed") == 6.0 and settings.get_value("pull_accel") == 20.0 and settings.get_value("ground_drag") == 3.5)
	panel.rows.reel_speed.slider.value = 7.25
	check("slider updates runtime value and number field", settings.get_value("reel_speed") == 7.25 and panel.rows.reel_speed.spin.text.to_float() == 7.25)
	panel.rows.reel_speed.spin.text = "5.5"
	panel.rows.reel_speed.spin.text_submitted.emit("5.5")
	check("exact number field updates slider and runtime", settings.get_value("reel_speed") == 5.5 and panel.rows.reel_speed.slider.value == 5.5)
	panel.rows.reel_speed.spin.grab_focus()
	panel.rows.reel_speed.spin.text = "7.25"
	await press(KEY_ESCAPE)
	var from_menu := Settings.new()
	from_menu.storage_path = ui_profile_path
	from_menu.load_profile()
	check("Escape applies and saves a typed decimal before resuming", world.player.active and settings.get_value("reel_speed") == 7.25 and from_menu.get_value("reel_speed") == 7.25, {"active":world.player.active,"runtime":settings.get_value("reel_speed"),"saved":from_menu.get_value("reel_speed"),"text":panel.rows.reel_speed.spin.text})
	await press(KEY_ESCAPE)
	panel.rows.reel_speed.spin.release_focus()
	var all_bound := true
	for definition in Settings.DEFINITIONS:
		var value: float = definition.min + definition.step
		panel.rows[definition.key].slider.value = value
		all_bound = all_bound and is_equal_approx(settings.get_value(definition.key), value)
		all_bound = all_bound and is_equal_approx(panel.rows[definition.key].spin.text.to_float(), value)
	check("every slider is bound to its actual movement parameter", all_bound)
	panel.reset_button.pressed.emit()
	var reset_correct := true
	for definition in Settings.DEFINITIONS:
		reset_correct = reset_correct and is_equal_approx(settings.get_value(definition.key), definition.default)
	check("reset button restores all new defaults", reset_correct)
	var fitted := true
	for viewport in [Vector2(1600, 900), Vector2(960, 540)]:
		panel.fit(viewport)
		await get_tree().process_frame
		fitted = fitted and panel.size.x <= viewport.x - 20 and panel.size.y <= viewport.y - 20
	check("menu fits desktop and small window", fitted, panel.size)
	panel.fit(world.get_viewport().get_visible_rect().size)
	# Profiltest i en unik temporär fil, aldrig i Joels verkliga rörelseprofil.
	var path := OS.get_temp_dir().path_join("kvarnbyn-movement-%s.cfg" % str(Time.get_ticks_usec()))
	var saved := Settings.new()
	saved.storage_path = path
	saved.set_value("reel_speed", 7.25)
	saved.set_value("ground_drag", 2.25)
	saved.show_speed = false
	var save_error: Error = saved.save_profile()
	var loaded := Settings.new()
	loaded.storage_path = path
	loaded.load_profile()
	check("decimal values and speed display survive profile reload", save_error == OK and loaded.get_value("reel_speed") == 7.25 and loaded.get_value("ground_drag") == 2.25 and not loaded.show_speed)
	loaded.set_value("reel_speed", 999.0)
	loaded.set_value("ground_drag", -99.0)
	check("out of range values are bounded", loaded.get_value("reel_speed") == 18.0 and loaded.get_value("ground_drag") == 0.0)
	loaded.set_value("reel_speed", NAN)
	check("non finite values are ignored", loaded.get_value("reel_speed") == 18.0)
	DirAccess.remove_absolute(path)
	var isolated := Settings.new()
	check("settings are independent per player", isolated.get_value("reel_speed") == 6.0)
	check("share text contains every parameter with units", settings.share_text().split("\n").size() == 25 and "m/s²" in settings.share_text())
	panel.speed_toggle.button_pressed = false
	check("speed meter toggle reaches game state", not settings.show_speed)
	panel.speed_toggle.button_pressed = true
	# Det är samma värdepaket som menyn redigerar som styr den riktiga spelarkapseln.
	var fixture := Fixture.new()
	fixture.process_mode = Node.PROCESS_MODE_ALWAYS
	add_child(fixture)
	fixture.solid(Vector3(0, -0.5, 0), Vector3(160, 1, 160))
	fixture.solid(Vector3(0, 9, -28.5), Vector3(100, 18, 1))
	fixture.p = Player.new()
	fixture.p.movement = settings
	fixture.add_child(fixture.p)
	panel.rows.rope_catchup.spin.text = "0"
	panel.rows.rope_catchup.spin.text_submitted.emit("0")
	panel.rows.reel_speed.slider.value = 3
	panel.rows.pull_accel.slider.value = 10
	var slow: Dictionary = await fixture.launch(false, 60)
	panel.rows.reel_speed.slider.value = 12
	panel.rows.pull_accel.slider.value = 40
	var fast: Dictionary = await fixture.launch(false, 60)
	check("menu changes actual reel speed in capsule simulation", fast.speed > slow.speed + 4.0, {"slow": slow.speed, "fast": fast.speed})
	settings.reset_defaults()
	panel.rows.swing_accel.slider.value = 0
	var no_steer: Dictionary = await fixture.launch(true, 60)
	panel.rows.swing_accel.slider.value = 19
	var steer: Dictionary = await fixture.launch(true, 60)
	check("menu changes actual swing acceleration", steer.speed > no_steer.speed + 5, {"off": no_steer.speed, "on": steer.speed})
	panel.rows.max_speed.spin.text = "12"
	panel.rows.max_speed.spin.text_submitted.emit("12")
	var limited: Dictionary = await fixture.launch(true, 60)
	check("menu speed limit constrains actual capsule", limited.peak <= 12.01, limited.peak)
	settings.reset_defaults()
	panel.rows.ground_drag.slider.value = 2
	var gentle: Dictionary = await coast(fixture, 0, 60)
	panel.rows.ground_drag.slider.value = 10
	var strong: Dictionary = await coast(fixture, 0, 60)
	check("lower landing brake keeps speed and travels farther", gentle.on_floor and strong.on_floor and gentle.speed > strong.speed + 4 and gentle.distance > strong.distance + 2, {"gentle": gentle, "strong": strong})
	panel.rows.air_drag.slider.value = 0
	var free_air: Dictionary = await coast(fixture, 30, 30)
	panel.rows.air_drag.slider.value = 1
	var damped_air: Dictionary = await coast(fixture, 30, 30)
	check("air drag slider affects flight after release", not free_air.on_floor and not damped_air.on_floor and free_air.speed > damped_air.speed + 4, {"free": free_air.speed, "damped": damped_air.speed})
	fixture.release_keys()
	fixture.p.active = false
	settings.reset_defaults()
	panel.sync_all()
	if world.options.has("movement-image") and DisplayServer.get_name() != "headless":
		world.player.camera.make_current()
		panel.tabs.current_tab = 0
		for frame in range(4):
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		check("native tuning menu capture", world.get_viewport().get_texture().get_image().save_png(str(world.options["movement-image"])) == OK)
		panel.tabs.current_tab = 1
		for frame in range(4):
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var second := str(world.options["movement-image"]).get_basename() + "-landing.png"
		check("native landing controls capture", world.get_viewport().get_texture().get_image().save_png(second) == OK)
	panel.tabs.current_tab = 0
	await press(KEY_ESCAPE)
	check("Escape resumes game and hides tuning controls", not get_tree().paused and world.player.active and not panel.visible and not world.overlay.opening)
	await press(KEY_ESCAPE)
	check("reopening menu preserves edited state", panel.visible and settings.get_value("reel_speed") == 6.0)
	panel.closed.emit()
	check("other settings remain accessible", not panel.visible and world.overlay.main_panel.visible)
	world.overlay.movement_button.pressed.emit()
	check("movement button returns to tuning menu", panel.visible)
	panel.resume_button.pressed.emit()
	check("continue button resumes actual game", world.player.active and not get_tree().paused and not panel.visible)
	settings.storage_path = original_path
	settings.persistence_enabled = original_persistence
	DirAccess.remove_absolute(ui_profile_path)
	fixture.queue_free()
	var passed := true
	for item in checks:
		passed = passed and bool(item.passed)
	return {"passed": passed, "checks": checks, "release": not OS.has_feature("editor"),
		"settings": settings.snapshot(), "scope": "actual Escape/menu controls, isolated persistence, and actual capsule physics driven by those controls"}

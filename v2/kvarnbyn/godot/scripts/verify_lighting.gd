extends SceneTree

## The real menu signals, shared lamp materials and moving light pool in the
## imported world. Dummy audio is mandatory; the script also mutes master.
var world
var checks := []

func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	call_deferred("run")

func check(label: String, passed: bool, detail = null) -> void:
	checks.append({"test": label, "passed": passed, "detail": detail})

func choose_lighting(index: int) -> void:
	world.overlay.lighting_selector.select(index)
	world.overlay.lighting_selector.item_selected.emit(index)

func choose_quality(index: int) -> void:
	world.overlay.quality_selector.select(index)
	world.overlay.quality_selector.item_selected.emit(index)

func view(id: String) -> void:
	for index in range(world.metadata.views.size()):
		if world.metadata.views[index].id == id:
			world.set_view(index)
			return

func run() -> void:
	if not "--explore" in OS.get_cmdline_user_args():
		push_error("verify_lighting requires --explore")
		quit(2)
		return
	world = load("res://main.tscn").instantiate()
	root.add_child(world)
	while not world.world_ready:
		await physics_frame
	var geometry = world.world_stats.duplicate(true)
	var rig = world.street_lights
	view("torget")
	choose_lighting(0)
	check("day_unlit_fixtures", rig.snapshot().active_lights == 0 and not rig.evening)
	check("real_fixture_materials_found", rig.fixtures.size() > 0 and rig.positions.size() > 0)
	choose_lighting(1)
	rig.refresh()
	var evening: Dictionary = rig.snapshot()
	check("menu_selects_evening", world.lighting_mode == "evening" and world.overlay.lighting_selector.selected == 1)
	check("evening_has_new_sky", world.scene_environment.environment.sky.sky_material is ProceduralSkyMaterial)
	check("near_lamps_cast_shadows", evening.active_lights > 0 and evening.shadow_lights == evening.active_lights and evening.active_lights <= 8, evening)
	var lit := true
	for fixture in rig.fixtures:
		var mat = fixture.mesh.get_surface_override_material(fixture.surface)
		lit = lit and mat != null and mat.emission_enabled and mat.emission_energy_multiplier > 1.0
	check("glass_glows_in_evening", lit)
	var aligned := true
	for index in range(rig.active_ids.size()):
		aligned = aligned and rig.pool[index].global_position.distance_to(rig.positions[rig.active_ids[index]]) < 0.1
	check("light_centres_at_real_fixture_metadata", aligned)
	var evening_ambient: float = world.scene_environment.environment.ambient_light_energy
	var before: Array = rig.active_ids.duplicate()
	view("royen")
	# The normal update must follow a teleport without a new light allocation.
	for frame in range(20):
		await physics_frame
	check("pool_follows_player", before != rig.active_ids and rig.pool.size() == 8, rig.snapshot())
	choose_quality(1)
	var low: Dictionary = rig.snapshot()
	check("low_quality_keeps_evening", world.lighting_mode == "evening" and low.active_lights <= 4 and low.shadow_lights <= 2)
	check("quality_preserves_evening_ambient", world.scene_environment.environment.ambient_light_energy >= evening_ambient and world.scene_environment.environment.ambient_light_energy <= evening_ambient * 1.3)
	choose_quality(0)
	# Repeat through the actual signals to catch accumulating suns or materials.
	for repeat in range(6):
		choose_lighting(0)
		choose_lighting(1)
	var suns: Array = world.find_children("*", "DirectionalLight3D", true, false)
	check("toggle_does_not_accumulate_lights", suns.size() == 1 and rig.pool.size() == 8 and rig.get_child_count() == 8)
	choose_lighting(0)
	var restored := true
	for fixture in rig.fixtures:
		restored = restored and fixture.mesh.get_surface_override_material(fixture.surface) == fixture.day
	check("day_restores_original_materials", restored and rig.snapshot().active_lights == 0)
	check("day_restores_panorama", world.scene_environment.environment.sky.sky_material is PanoramaSkyMaterial)
	check("lighting_keeps_collision_and_vegetation", world.world_stats == geometry)
	check("pause_keeps_player_stopped", not world.player.active)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--transition-image="):
			if DisplayServer.get_name() == "headless":
				check("native_menu_transition_capture", false, "Native rendering required")
				continue
			# Exercise the actual day -> evening transition with a real renderer,
			# rather than only loading a process directly into evening via CLI.
			view("torget")
			choose_lighting(1)
			for frame in range(240):
				await process_frame
			await RenderingServer.frame_post_draw
			var error := root.get_texture().get_image().save_png(arg.trim_prefix("--transition-image="))
			check("native_menu_transition_capture", error == OK)
	var passed := true
	for result in checks:
		passed = passed and result.passed
	var result := {"passed": passed, "checks": checks, "world": geometry, "fixtures": rig.positions.size()}
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):
			var file := FileAccess.open(arg.trim_prefix("--output="), FileAccess.WRITE)
			file.store_string(JSON.stringify(result, "\t"))
	print("KVARNBYN_LIGHTING_CHECK ", JSON.stringify(result))
	world.queue_free()
	await process_frame
	await process_frame
	quit(0 if passed else 3)

extends SceneTree

## Imported texture bytes, actual world materials and real menu transitions.
## Always pass --audio-driver Dummy. Optional native images use --water-images.
var scene
var checks: Array[Dictionary] = []
var options: Dictionary = {}

func _initialize() -> void:
	AudioServer.set_bus_mute(0,true)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--"):
			var pair := arg.trim_prefix("--").split("=",true,1)
			options[pair[0]] = pair[1] if pair.size()>1 else "1"
	call_deferred("run")

func check(id: String, passed: bool, detail = null) -> void:
	checks.append({"test":id,"passed":passed,"detail":detail})

func run() -> void:
	if not options.has("explore"):
		quit(2)
		return
	scene = load("res://main.tscn").instantiate()
	root.add_child(scene)
	for frame in range(600):
		await physics_frame
		if scene.world_ready:break
	check("actual_world_loaded",scene.world_ready)
	if not scene.world_ready:
		await finish()
		return
	var river = scene.river_water
	check("flow_field_loaded",river!=null and river.loaded,river.snapshot() if river!=null else {})
	if river==null or not river.loaded:
		await finish()
		return
	check("small_512_data_texture",river.field.get_size()==Vector2(512,512))
	var zone: Dictionary = scene.metadata.bounds
	check("field_matches_actual_world_bounds",absf(river.bounds.x-float(zone.min[0]))<.01 and absf(river.bounds.y-float(zone.min[2]))<.01 and absf(river.bounds.z-float(zone.max[0]))<.01 and absf(river.bounds.w-float(zone.max[2]))<.01)
	var found := 0
	var configured := true
	var no_water_collision := true
	for mesh in scene.world_instance.find_children("*","MeshInstance3D",true,false):
		for surface in range(mesh.mesh.get_surface_count()):
			var material: Material = mesh.get_active_material(surface)
			if material==null or str(material.resource_name)!="WaterFlow":continue
			found += 1
			configured = configured and material is ShaderMaterial and material.shader==river.ShaderSource and material.get_shader_parameter("flow_field")==river.field and material.get_shader_parameter("use_flow_field")==true
			for child in mesh.get_children():
				if child is StaticBody3D:no_water_collision=false
	check("actual_water_surfaces_found",found>0 and found==river.surfaces,found)
	check("all_water_surfaces_use_actual_field",configured)
	check("water_remains_visual_without_new_collision",no_water_collision)
	check("shared_material_limits_allocations",river.materials.size()==1,river.materials.size())
	var image: Image = river.field.get_image()
	if image.is_compressed():
		check("data_texture_decompresses",image.decompress()==OK)
	var decoded: Array[Dictionary] = []
	for index in range(river.metadata.probes.size()):
		var probe: Dictionary = river.metadata.probes[index]
		var colour := image.get_pixel(int(probe.pixel_x_y[0]),int(probe.pixel_x_y[1]))
		var actual := [roundi(colour.r*255),roundi(colour.g*255),roundi(colour.b*255)]
		var expected_bytes: Array = probe.pixel_rgb8.map(func(channel):return int(channel))
		var direction := Vector2(colour.r*2-1,colour.g*2-1).normalized()
		var expected := Vector2(float(probe.downstream[0]),float(probe.downstream[1]))
		check("imported_bytes_probe_"+str(index),actual==expected_bytes,{"actual":actual,"expected":expected_bytes})
		check("downstream_direction_probe_"+str(index),direction.dot(expected)>.999,{"dot":direction.dot(expected),"direction":[direction.x,direction.y]})
		check("foam_grade_probe_"+str(index),absf(colour.b-float(probe.foam))<.0021,{"actual":colour.b,"expected":probe.foam})
		decoded.append({"label":probe.label,"grade":probe.grade,"foam":colour.b})
	check("calm_reach_keeps_flow_without_whitewater",decoded.any(func(probe):return float(probe.grade)<.001 and float(probe.foam)<.001))
	check("steeper_reach_gets_more_foam",decoded.any(func(probe):return float(probe.grade)>.1 and float(probe.foam)>.5))
	var geometry: Dictionary = scene.world_stats.duplicate(true)
	var material_ids: Array = river.materials.map(func(material):return material.get_instance_id())
	for quality in [1,0]:
		scene.overlay.quality_selector.select(quality)
		scene.overlay.quality_selector.item_selected.emit(quality)
	for lighting in [1,0]:
		scene.overlay.lighting_selector.select(lighting)
		scene.overlay.lighting_selector.item_selected.emit(lighting)
	check("menu_changes_keep_same_water_materials",material_ids==river.materials.map(func(material):return material.get_instance_id()))
	check("menu_changes_keep_actual_geometry",geometry==scene.world_stats)
	check("native_capture_views_exist",["fors-forsebron","fors-gangbron","fors-ovre"].all(func(id):return scene.metadata.views.any(func(view):return view.id==id)))
	if options.has("water-images"):
		if DisplayServer.get_name()=="headless":
			check("native_render_required_for_images",false)
		else:
			scene.overlay.set_open(false,false)
			scene.started=true
			Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
			for id in ["fors-forsebron","fors-gangbron","fors-ovre"]:
				for index in range(scene.metadata.views.size()):
					if scene.metadata.views[index].id==id:scene.set_view(index);break
				for frame in range(180):await process_frame
				await RenderingServer.frame_post_draw
				var path: String = str(options["water-images"]).path_join(id+".png")
				check("native_image_"+id,root.get_texture().get_image().save_png(path)==OK,path)
	await finish()

func finish() -> void:
	var passed: bool = checks.all(func(item):return bool(item.passed))
	var report := {"passed":passed,"checks":checks,"water":scene.river_water.snapshot() if is_instance_valid(scene) and scene.river_water!=null else {}}
	if options.has("output"):
		var file := FileAccess.open(str(options.output),FileAccess.WRITE)
		if file!=null:file.store_string(JSON.stringify(report,"\t"))
	print("KVARNBYN_WATER_CHECK ",JSON.stringify(report))
	if is_instance_valid(scene):scene.queue_free()
	await process_frame
	quit(0 if passed else 3)

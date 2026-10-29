extends Node3D

const PlayerController = preload("res://scripts/player.gd")
const OverlayController = preload("res://scripts/overlay.gd")
const Lighting = preload("res://scripts/lighting.gd")
const WaterShader = preload("res://shaders/water.gdshader")
const GameManager = preload("res://scripts/game.gd")
const HudController = preload("res://scripts/hud.gd")
const Fx = preload("res://scripts/fx.gd")
const WORLD_PATH := "res://assets/world.glb"
const META_PATH := "res://assets/world_meta.json"
const BAKED_PATH := "res://assets/baked_world.tscn"

var player: CharacterBody3D
var overlay: Control
var canvas_layer: CanvasLayer
var metadata: Dictionary = {}
var world_instance: Node3D
var world_ready := false
var touch_mode := false
var started := false
var view_index := 0
var world_stats := {"meshes": 0, "triangles": 0, "colliders": 0, "explicit_collision_meshes": 0}
var options: Dictionary = {}
var bridge_callback: JavaScriptObject
var bridge_timer := 0.0
var load_msec := 0
var used_baked_world := false
var prepared_bake_scene := false
var spawn_position := Vector3.ZERO
var base_render_scale := 1.0
var game: Node
var hud: Control
var fx: Node3D
var bot_mode := false
var bot_path := PackedVector3Array()
var bot_path_i := 0
var bot_cap := ""
var bot_last := Vector3.ZERO
var bot_stuck := 0.0
var bot_repath := 0.0
var bot_timeout := 900.0

func _ready() -> void:
	var start_msec := Time.get_ticks_msec()
	options = read_options()
	RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
	metadata = load_metadata()
	touch_mode = DisplayServer.is_touchscreen_available() or options.has("touch")
	if OS.has_feature("web"):
		touch_mode = touch_mode or bool(JavaScriptBridge.eval("navigator.maxTouchPoints > 0"))
	if touch_mode:
		# Smaller logical canvas gives phone buttons physical touch-target sizes.
		get_window().content_scale_size = Vector2i(960, 540)
		if OS.has_feature("web"):
			var dpr := float(JavaScriptBridge.eval("window.devicePixelRatio || 1"))
			base_render_scale = minf(1.0, 1.5 / maxf(1.0, dpr))
			get_viewport().scaling_3d_scale = base_render_scale
	player = PlayerController.new()
	player.name = "Spelare"
	add_child(player)
	canvas_layer = CanvasLayer.new()
	canvas_layer.name = "Gränssnitt"
	add_child(canvas_layer)
	overlay = OverlayController.new()
	canvas_layer.add_child(overlay)
	overlay.player = player
	player.overlay = overlay
	overlay.configure(metadata, touch_mode)
	overlay.begin_requested.connect(begin_walk)
	overlay.pause_requested.connect(pause_walk)
	overlay.reset_requested.connect(reset_player)
	overlay.view_requested.connect(set_view)
	overlay.jump_pressed.connect(func(): player.jump_requested = true)
	overlay.fullscreen_requested.connect(toggle_fullscreen)
	overlay.quality_changed.connect(set_quality)
	overlay.set_open(true, true)
	if ResourceLoader.exists(BAKED_PATH):
		world_instance = load(BAKED_PATH).instantiate()
		prepared_bake_scene = true
	elif ResourceLoader.exists(WORLD_PATH):
		world_instance = load(WORLD_PATH).instantiate()
		add_child(Lighting.make_environment())
		add_child(Lighting.make_sun())
	else:
		add_child(Lighting.make_environment())
		add_child(Lighting.make_sun())
		overlay.show_error("Miljön kunde inte laddas. Vänta en stund och ladda sedan om sidan.")
		push_error("world.glb saknas. Exportera Blender-scenen till assets/world.glb.")
		install_bridge()
		return
	world_instance.name = "Varlden"
	add_child(world_instance)
	if prepared_bake_scene:
		# Keep runtime's sky/background settings current without rebaking geometry.
		for environment in world_instance.find_children("*", "WorldEnvironment", true, false):
			if environment.environment != null and environment.environment.sky != null and environment.environment.sky.sky_material is PanoramaSkyMaterial:
				continue
			var updated_environment := Lighting.make_environment()
			environment.environment = updated_environment.environment
			updated_environment.free()
	used_baked_world = has_baked_lighting(world_instance)
	prepare_world()
	player.camera.make_current()
	process_mode = Node.PROCESS_MODE_ALWAYS
	player.process_mode = Node.PROCESS_MODE_PAUSABLE
	if not options.has("explore"):
		setup_combat()
	await get_tree().physics_frame
	await get_tree().physics_frame
	reset_player()
	if options.has("view"):
		var requested := str(options["view"])
		var views: Array = metadata.get("views", [])
		for index in range(views.size()):
			if str(index) == requested or str(views[index].get("id", "")) == requested:
				set_view(index)
				break
	load_msec = Time.get_ticks_msec() - start_msec
	world_ready = true
	install_bridge()
	print("KVARNBYN_READY ", JSON.stringify(snapshot()))
	if options.has("autostart"):
		begin_walk()
	if options.has("hide-ui"):
		canvas_layer.visible = false
	if options.has("free-flight"):
		player.free_flight = true
	if options.has("capture"):
		capture_after_frames(str(options["capture"]), int(options.get("frames", "45")))
	if options.has("probe"):
		run_physics_probe()
	if options.has("walktest"):
		run_walk_test()
	if options.has("quality"):
		set_quality(int(options["quality"]))
	if options.has("bot"):
		start_bot()

func load_metadata() -> Dictionary:
	if not FileAccess.file_exists(META_PATH):
		return {"title": "Kvarnbyn", "spawn": {"position": [0, 0, 14], "snap_to_ground": true},
			"attribution": ["Kartdata © OpenStreetMap-bidragsgivare. Höjddata: Lantmäteriet."]}
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(META_PATH))
	if not parsed is Dictionary:
		return {}
	var credits: Array = parsed.get("attribution", [])
	var sky_credit := "Himmel: Poly Haven, Greg Zaal/Jarod Guest (CC0)"
	if sky_credit not in credits:
		credits.append(sky_credit)
	parsed["attribution"] = credits
	return parsed

func read_options() -> Dictionary:
	var result := {}
	for argument in OS.get_cmdline_user_args():
		if not argument.begins_with("--"):
			continue
		var parts := argument.trim_prefix("--").split("=", true, 1)
		result[parts[0]] = parts[1] if parts.size() > 1 else "1"
	if OS.has_feature("web"):
		var query = JavaScriptBridge.eval("window.location.search.substring(1)")
		if query is String:
			for item in query.split("&", false):
				var parts: PackedStringArray = item.split("=", true, 1)
				result[parts[0].uri_decode()] = parts[1].uri_decode() if parts.size() > 1 else "1"
	return result

func mesh_nodes(parent: Node, result: Array[MeshInstance3D]) -> void:
	if parent is MeshInstance3D and parent.mesh != null:
		result.append(parent)
	for child in parent.get_children():
		mesh_nodes(child, result)

func collision_tagged(mesh_instance: MeshInstance3D) -> bool:
	var node: Node = mesh_instance
	while node != world_instance and node != null:
		if str(node.name).to_upper().begins_with("COL_"):
			return true
		node = node.get_parent()
	return false

func excluded_from_fallback_collision(mesh_instance: MeshInstance3D) -> bool:
	var value := str(mesh_instance.name).to_lower()
	for word in ["leaf", "foliage", "leaves", "grass", "window", "decal", "sign", "sky", "water", "roof_tile", "panel_detail", "lamp_glow"]:
		if word in value:
			return true
	return false

func prepare_world() -> void:
	var meshes: Array[MeshInstance3D] = []
	mesh_nodes(world_instance, meshes)
	var explicit: Array[MeshInstance3D] = []
	for mesh_instance in meshes:
		animate_water_materials(mesh_instance)
		if collision_tagged(mesh_instance):
			explicit.append(mesh_instance)
	world_stats["explicit_collision_meshes"] = explicit.size()
	for mesh_instance in meshes:
		if collision_tagged(mesh_instance):
			mesh_instance.visible = false
		else:
			world_stats["meshes"] += 1
			for surface in range(mesh_instance.mesh.get_surface_count()):
				var arrays: Array = mesh_instance.mesh.surface_get_arrays(surface)
				var indices = arrays[Mesh.ARRAY_INDEX]
				if indices != null and indices.size() > 0:
					world_stats["triangles"] += int(indices.size() / 3)
				else:
					world_stats["triangles"] += int(arrays[Mesh.ARRAY_VERTEX].size() / 3)
		if (not explicit.is_empty() and mesh_instance in explicit) or (explicit.is_empty() and not excluded_from_fallback_collision(mesh_instance)):
			add_static_collision(mesh_instance)

func has_baked_lighting(node: Node) -> bool:
	if node is LightmapGI and node.light_data != null and node.light_data.get_user_count() > 0:
		return true
	for child in node.get_children():
		if has_baked_lighting(child):
			return true
	return false

func animate_water_materials(mesh_instance: MeshInstance3D) -> void:
	for surface in range(mesh_instance.mesh.get_surface_count()):
		var material := mesh_instance.get_active_material(surface)
		if material == null or "waterflow" not in str(material.resource_name).to_lower():
			continue
		var animated := ShaderMaterial.new()
		animated.shader = WaterShader
		animated.resource_name = "WaterFlow"
		if material is BaseMaterial3D:
			animated.set_shader_parameter("water_color", material.albedo_color)
		mesh_instance.set_surface_override_material(surface, animated)
		if mesh_instance.mesh.get_surface_count() == 1:
			mesh_instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

func add_static_collision(mesh_instance: MeshInstance3D) -> void:
	# Geometry is authored offline. Godot's physics owns collision and contact resolution.
	if mesh_instance.get_child_count() > 0:
		for child in mesh_instance.get_children():
			if child is StaticBody3D:
				world_stats["colliders"] += 1
				return
	var shape := mesh_instance.mesh.create_trimesh_shape()
	if shape == null:
		return
	shape.backface_collision = true
	var body := StaticBody3D.new()
	body.name = "Gångyta"
	body.collision_layer = 1
	body.collision_mask = 2
	var collider := CollisionShape3D.new()
	collider.shape = shape
	body.add_child(collider)
	mesh_instance.add_child(body)
	world_stats["colliders"] += 1

func vector(value, default_value := Vector3.ZERO) -> Vector3:
	if value is Array and value.size() >= 3:
		return Vector3(float(value[0]), float(value[1]), float(value[2]))
	return default_value

func reset_player() -> void:
	var spawn: Dictionary = metadata.get("spawn", {})
	var location := vector(spawn.get("position", [0, 0, 14]))
	if bool(spawn.get("snap_to_ground", false)):
		location = ground_position(location)
	spawn_position = location
	player.place_at(location + Vector3.UP * 0.05, deg_to_rad(float(spawn.get("yaw_degrees", 0.0))), deg_to_rad(float(spawn.get("pitch_degrees", 0.0))))
	if spawn.has("target"):
		player.look_toward(vector(spawn["target"]))
	player.free_flight = false
	player.input_suspended = false
	player.camera.fov = 67.0
	if overlay != null:
		overlay.status_label.text = str(metadata.get("title", "Kvarnbyn"))

func ground_position(location: Vector3) -> Vector3:
	var query := PhysicsRayQueryParameters3D.create(location + Vector3.UP * 100, location - Vector3.UP * 150, 1)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if not hit.is_empty():
		return hit.position
	return location

func set_view(index: int) -> void:
	var views: Array = metadata.get("views", [])
	if index < 0 or index >= views.size():
		return
	view_index = index
	var selected: Dictionary = views[index]
	player.camera.fov = float(selected.get("fov_degrees", 67.0))
	player.place_at(vector(selected.get("position", [0, 2, 14])), deg_to_rad(float(selected.get("yaw_degrees", 0))), deg_to_rad(float(selected.get("pitch_degrees", 0))), bool(selected.get("eye_position", true)))
	if selected.has("target"):
		player.look_toward(vector(selected["target"]))
	player.input_suspended = true
	player.free_flight = bool(selected.get("free_flight", false))
	overlay.status_label.text = str(selected.get("name", "Kvarnbyn"))
	overlay.view_selector.select(index)
	if started:
		# A chosen view stays still until the player moves or looks around.
		overlay.status_override = "Gå eller dra för att utforska härifrån"

func setup_combat() -> void:
	fx = Fx.new()
	fx.name = "Effekter"
	fx.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(fx)
	hud = HudController.new()
	canvas_layer.add_child(hud)
	canvas_layer.move_child(hud, 0)
	game = GameManager.new()
	game.name = "Spel"
	game.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(game)
	if not game.setup(self, player, fx, hud):
		game.queue_free()
		game = null
		return
	hud.player = player
	hud.game = game
	player.game = game
	player.weapon.fx = fx
	player.weapon.hud = hud
	game.ended.connect(_on_game_ended)
	hud.restart_requested.connect(_on_restart)

func _on_game_ended(won: bool) -> void:
	hud.show_end(won)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	player.active = false

func _on_restart() -> void:
	hud.hide_end()
	game.restart()
	begin_walk()

func begin_walk() -> void:
	if world_instance == null:
		return
	if game != null and game.over:
		return
	get_tree().paused = false
	if game != null and not game.started:
		game.start()
	started = true
	player.active = true
	player.input_suspended = false
	overlay.status_override = ""
	overlay.set_open(false)
	if not touch_mode and not options.has("no-pointer-lock"):
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func pause_walk() -> void:
	if game != null and game.started:
		get_tree().paused = true
	player.active = false
	player.reset_touches()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	overlay.set_open(true)

func toggle_fullscreen() -> void:
	if DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	else:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)

func set_quality(index: int) -> void:
	# 0 = Normal: realtids-GI, SSIL, volymdimma. 1 = Lägre belastning: utan dem, 85 % upplösning.
	get_viewport().scaling_3d_scale = base_render_scale * (0.85 if index == 1 else 1.0)
	get_viewport().msaa_3d = Viewport.MSAA_DISABLED if index == 1 else Viewport.MSAA_2X
	for we in find_children("*", "WorldEnvironment", true, false):
		var env: Environment = we.environment
		env.sdfgi_enabled = index == 0
		env.ssil_enabled = index == 0
		env.volumetric_fog_enabled = index == 0
		env.ambient_light_energy = 0.6 if index == 0 else 0.9

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.physical_keycode == KEY_ESCAPE:
			if player.active:
				pause_walk()
			else:
				begin_walk()
			get_viewport().set_input_as_handled()
		elif event.physical_keycode == KEY_R and started and game == null:
			reset_player()
		elif event.physical_keycode == KEY_F11:
			toggle_fullscreen()
		elif event.physical_keycode == KEY_H:
			canvas_layer.visible = not canvas_layer.visible
	if player != null and player.input_suspended and player.active:
		if event is InputEventMouseMotion or event is InputEventScreenTouch or event is InputEventScreenDrag or event is InputEventKey:
			player.input_suspended = false
			overlay.status_override = ""

func _process(delta: float) -> void:
	if player == null:
		return
	if player.position.y < spawn_position.y - 80:
		reset_player()
	bridge_timer += delta
	if OS.has_feature("web") and bridge_timer > 0.5:
		bridge_timer = 0.0
		publish_state()

func snapshot() -> Dictionary:
	return {"ready": world_ready, "title": metadata.get("title", "Kvarnbyn"),
		"load_ms": load_msec, "baked_lightmaps": used_baked_world, "prepared_bake_scene": prepared_bake_scene,
		"touch": touch_mode, "world": world_stats, "player": player.snapshot() if player != null else {},
		"fps": Engine.get_frames_per_second(), "view": view_index,
		"draw_calls": Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
		"render_triangles": Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
		"cpu_render_ms": RenderingServer.viewport_get_measured_render_time_cpu(get_viewport().get_viewport_rid()),
		"gpu_render_ms": RenderingServer.viewport_get_measured_render_time_gpu(get_viewport().get_viewport_rid()),
		"process_ms": Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0,
		"physics_ms": Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0,
		"static_memory_bytes": OS.get_static_memory_usage(),
		"game": game.state() if game != null else {}}

func install_bridge() -> void:
	if not OS.has_feature("web"):
		return
	bridge_callback = JavaScriptBridge.create_callback(_bridge_command)
	var window := JavaScriptBridge.get_interface("window")
	window.__kvarnbynCommand = bridge_callback
	JavaScriptBridge.eval("window.__kvarnbyn = {get state(){return JSON.parse(window.__kvarnbynStateJSON || '{}')}, command:window.__kvarnbynCommand};", true)
	publish_state()

func publish_state() -> void:
	var window := JavaScriptBridge.get_interface("window")
	var state_json := JSON.stringify(snapshot())
	window.__kvarnbynStateJSON = state_json
	var document := JavaScriptBridge.get_interface("document")
	var state_node = document.getElementById("kvarnbyn-debug-state")
	if state_node != null:
		state_node.textContent = state_json

func _bridge_command(arguments: Array) -> void:
	if arguments.is_empty():
		return
	var command = JSON.parse_string(str(arguments[0]))
	if not command is Dictionary:
		return
	match str(command.get("action", "")):
		"begin": begin_walk()
		"pause": pause_walk()
		"reset": reset_player()
		"view": set_view(int(command.get("index", 0)))
		"quality": set_quality(int(command.get("index", 0)))
		"ui": canvas_layer.visible = bool(command.get("visible", true))
		"teleport":
			player.place_at(vector(command.get("position", [0, 0, 0])), float(command.get("yaw", 0)), float(command.get("pitch", 0)), bool(command.get("eye_position", false)))
			player.free_flight = bool(command.get("free_flight", false))
			player.input_suspended = bool(command.get("hold", true))
		"look": player.look_toward(vector(command.get("target", [0, 0, 0])))
	publish_state()

func capture_after_frames(path: String, frame_count: int) -> void:
	if not options.has("bot"):
		player.input_suspended = true
	for frame in range(maxi(frame_count, 2)):
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	var error := image.save_png(path)
	print("KVARNBYN_CAPTURE ", path, " result=", error)
	print("KVARNBYN_RENDER ", JSON.stringify(snapshot()))
	get_tree().quit(error)

func run_physics_probe() -> void:
	player.active = true
	player.input_suspended = false
	for frame in range(90):
		await get_tree().physics_frame
	print("KVARNBYN_PROBE ", JSON.stringify(snapshot()))
	if not options.has("capture"):
		get_tree().quit(0 if player.is_on_floor() else 2)


## Gångtest över hela zonen: släpp spelaren 1,5 m ovanför varje provpunkt längs gatorna
## (world_meta.json → probe_points), stega fysiken och kontrollera att hen landar på en yta
## nära den förväntade markhöjden — inte faller igenom, fastnar i något eller svävar.
func run_walk_test() -> void:
	var points: Array = metadata.get("probe_points", [])
	var fails: Array = []
	var landed := 0
	player.active = true
	player.input_suspended = false   # gravitationen gäller bara när inmatningen är på; inga tangenter trycks
	for p in points:
		var target := Vector3(float(p[0]), float(p[1]), float(p[2]))
		player.place_at(target + Vector3(0, 1.5, 0), 0.0, 0.0, false)
		player.velocity = Vector3.ZERO
		for frame in range(50):
			await get_tree().physics_frame
		var y: float = player.global_position.y
		var ok: bool = player.is_on_floor() and absf(y - target.y) < 1.2
		if ok:
			landed += 1
		else:
			fails.append({"at": [snappedf(target.x, 0.1), snappedf(target.y, 0.1), snappedf(target.z, 0.1)], "y": snappedf(y, 0.01), "floor": player.is_on_floor()})
	var result := {"points": points.size(), "landed": landed, "failed": fails.size(), "fails": fails.slice(0, 25)}
	print("KVARNBYN_WALKTEST ", JSON.stringify(result))
	get_tree().quit(0 if fails.is_empty() else 3)


# ---------- bot: spelar en hel omgång automatiskt (spelprov utan människa) ----------
## Tar zonerna i ordningen C → B → A längs vägnätet, siktar på närmaste synliga fiende inom 60 m
## (med lite fel), skjuter, laddar om. Kör med --bot [--speed=3] [--botlimit=900] (sekunder speltid).

func start_bot() -> void:
	bot_mode = true
	bot_timeout = float(options.get("botlimit", "900"))
	Engine.time_scale = float(options.get("speed", "3"))
	begin_walk()
	player.bot_input = Vector2.ZERO
	game.ended.connect(func(won: bool): _bot_finish("seger" if won else "förlust"))

func _bot_finish(result: String) -> void:
	print("KVARNBYN_BOT ", JSON.stringify({"result": result, "state": game.state()}))
	Engine.time_scale = 1.0
	get_tree().quit(0)

func _physics_process(delta: float) -> void:
	if not bot_mode or game == null or game.over:
		return
	if game.elapsed > bot_timeout:
		_bot_finish("tidsgräns")
		return
	var w = player.weapon
	w.bot_trigger = false
	w.bot_ads = false
	if not player.alive:
		player.bot_input = Vector2.ZERO
		bot_path = PackedVector3Array()
		return
	var eye: Vector3 = player.eye_position()
	var target: Node3D = null
	var best := 60.0
	for e in game.enemies:
		if not e.alive:
			continue
		var d: float = eye.distance_to(e.global_position)
		if d < best:
			var q := PhysicsRayQueryParameters3D.create(eye, e.global_position + Vector3.UP * 1.3, 1)
			if get_world_3d().direct_space_state.intersect_ray(q).is_empty():
				best = d
				target = e
	if target != null:
		var aim: Vector3 = target.global_position + Vector3.UP * randf_range(1.1, 1.6) + Vector3(randf_range(-0.25, 0.25), 0, randf_range(-0.25, 0.25))
		var dir := aim - eye
		var want_yaw := atan2(-dir.x, -dir.z)
		var want_pitch := atan2(dir.y, Vector2(dir.x, dir.z).length())
		player.rotation.y = lerp_angle(player.rotation.y, want_yaw, minf(1.0, delta * 9.0))
		player.camera.rotation.x = lerpf(player.camera.rotation.x, want_pitch, minf(1.0, delta * 9.0))
		var off := absf(angle_difference(player.rotation.y, want_yaw))
		w.bot_ads = best > 18.0
		w.bot_trigger = off < 0.06
		player.bot_input = Vector2(sin(game.elapsed * 1.3) * 0.6, 0.0) if best < 25.0 else Vector2.ZERO
		player.bot_sprint = false
		return
	if w.mag < 12 and not w.reloading:
		w.bot_reload = true
	# mål: första zonen i C, B, A som inte är vår, annars C
	var goal_cap: Dictionary = game.base_cap()
	for id in ["C", "B", "A"]:
		for c in game.caps:
			if c["id"] == id and c["owner"] != "friendly" and goal_cap == game.base_cap() and game.base_cap()["owner"] == "friendly":
				goal_cap = c
	if game.base_cap()["owner"] != "friendly" or (game.base_cap()["contested"] and game.base_cap().get("enemies_in", 0) > 0):
		goal_cap = game.base_cap()
	var goal: Vector3 = goal_cap["pos"]
	bot_repath -= delta
	if str(goal_cap["id"]) != bot_cap or bot_path.is_empty() or bot_repath <= 0.0:
		bot_cap = str(goal_cap["id"])
		bot_path = game.nav.path(player.global_position, goal)
		bot_path_i = 0
		bot_repath = 20.0
	var to := Vector3.ZERO
	while bot_path_i < bot_path.size():
		to = bot_path[bot_path_i] - player.global_position
		to.y = 0
		if to.length() < 2.0 and bot_path_i < bot_path.size() - 1:
			bot_path_i += 1
		else:
			break
	if Vector2(player.global_position.x - goal.x, player.global_position.z - goal.z).length() < goal_cap["radius"] * 0.6:
		player.bot_input = Vector2.ZERO
		player.rotation.y += delta * 0.8
		return
	if to.length() > 0.3:
		player.rotation.y = lerp_angle(player.rotation.y, atan2(-to.x, -to.z), minf(1.0, delta * 6.0))
		player.camera.rotation.x = lerpf(player.camera.rotation.x, 0.0, minf(1.0, delta * 4.0))
	player.bot_input = Vector2(0, -1)
	player.bot_sprint = true
	bot_stuck += delta
	if bot_stuck > 2.0:
		if player.global_position.distance_to(bot_last) < 1.0:
			player.jump_requested = true
			player.bot_input = Vector2(1 if randf() < 0.5 else -1, -0.3)
			bot_path = PackedVector3Array()
		bot_stuck = 0.0
		bot_last = player.global_position

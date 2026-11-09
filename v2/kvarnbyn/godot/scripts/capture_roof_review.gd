extends SceneTree
func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	call_deferred("run")
func xyz(value) -> Vector3:
	return Vector3(float(value[0]),float(value[1]),float(value[2]))
func run() -> void:
	root.size = Vector2i(1600,1000)
	var world = load("res://main.tscn").instantiate()
	root.add_child(world)
	for frame in range(600):
		await physics_frame
		if world.world_ready: break
	world.begin_walk()
	var p = world.player
	p.bot_input = Vector2.ZERO
	p.bot_sprint = false
	p.combat_enabled = false
	p.input_suspended = false
	var spec: Dictionary
	for item in world.metadata.roof_physics.checks:
		if item.id == "Footprint_w92331966_Roof": spec = item
	if spec.is_empty(): quit(3); return
	var point := xyz(spec.points[0])
	p.place_at(point+Vector3.UP*1.5,0,0,false)
	for frame in range(120): await physics_frame
	var landed: bool = p.is_on_floor() and absf(p.global_position.y-point.y)<.28
	var direction := (xyz(spec.points[-1])-point).normalized()
	p.look_toward(point+direction*8-Vector3.UP*.8)
	p.set_process(false)
	p.set_physics_process(false)
	p.weapon.set_process(false)
	p.weapon.hide()
	world.canvas_layer.hide()
	for frame in range(10): await process_frame
	await RenderingServer.frame_post_draw
	var out := ProjectSettings.globalize_path("res://../evidence/gorjelyck/roof-standing.png")
	root.get_texture().get_image().save_png(out)
	print("KVARNBYN_ROOF_CAPTURE ",JSON.stringify({"passed":landed,"feet":p.global_position,"expected":point,"roof":spec.id}))
	quit(0 if landed else 3)

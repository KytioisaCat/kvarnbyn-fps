extends SceneTree

## Silent native frame-time probe. Real game, stationary player, rotating camera.
var options := {}
func _initialize() -> void:
	AudioServer.set_bus_mute(0,true)
	seed(20261106)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--"):
			var pair := arg.trim_prefix("--").split("=",true,1)
			options[pair[0]]=pair[1] if pair.size()>1 else "1"
	call_deferred("run")
func stats(values: Array, unit: String = "frame_ms") -> Dictionary:
	if values.is_empty():return {}
	var ordered := values.duplicate()
	ordered.sort()
	var sum := 0.0
	var slow := 0
	for value in values:
		sum+=float(value)
		if float(value)>33.33:slow+=1
	var result := {"samples":values.size(),"unit":unit,"p50":ordered[int(ordered.size()*.5)],"p95":ordered[int(ordered.size()*.95)],
		"p99":ordered[int(ordered.size()*.99)],"max":ordered[-1],"mean":sum/values.size()}
	if unit=="frame_ms":
		result["mean_fps"]=1000.0/(sum/values.size())
		result["over_33ms"]=slow
	return result
func run() -> void:
	var world=load("res://main.tscn").instantiate()
	root.add_child(world)
	while not world.world_ready:await process_frame
	world.options["no-pointer-lock"]="1"
	world.begin_walk()
	world.player.hp=100000
	world.player.bot_input=Vector2.ZERO
	Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
	var yaw: float=world.player.rotation.y
	var frames: Array=[]
	var cold: Array=[]
	var physics: Array=[]
	var calls: Array=[]
	var triangles: Array=[]
	var warmup := float(options.get("warmup","6"))
	var duration := float(options.get("seconds","15"))
	var start := Time.get_ticks_usec()
	var previous := start
	while Time.get_ticks_usec()-start<(warmup+duration)*1000000.0:
		await process_frame
		var now := Time.get_ticks_usec()
		var elapsed := (now-start)/1000000.0
		var dt := (now-previous)/1000.0
		previous=now
		world.player.rotation.y=yaw+TAU*elapsed/15.0
		if elapsed<warmup:cold.append(dt)
		else:
			frames.append(dt)
			physics.append(Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS)*1000)
			calls.append(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
			triangles.append(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME))
	var result := {"scope":"actual native combat world, stationary immortal player, continuously rotating camera; one short probe, not whole-map performance",
		"quality":world.quality_index,"window_size":str(root.size),"viewport_size":str(root.get_texture().get_size()),
		"screen_scale":DisplayServer.screen_get_scale(),"render_scale":root.scaling_3d_scale,"renderer":RenderingServer.get_current_rendering_method(),
		"warmup":stats(cold),"frames":stats(frames),"physics":stats(physics,"ms"),"draw_calls":stats(calls,"count"),"triangles":stats(triangles,"count"),"game":world.game.state()}
	var f:=FileAccess.open(str(options.get("output","/tmp/game-profile.json")),FileAccess.WRITE)
	if f!=null:f.store_string(JSON.stringify(result,"\t"))
	print("KVARNBYN_FRAME_PROFILE ",JSON.stringify(result))
	world.game.running=false
	world.queue_free()
	await process_frame
	await process_frame
	quit()

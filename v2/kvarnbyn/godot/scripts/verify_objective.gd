extends SceneTree

## Tests the real imported world, GameManager caps and HUD. Always quiet.
var scene
var checks: Array[Dictionary] = []
var states: Array[Dictionary] = []
var output_path := ""
var image_path := ""

func _initialize() -> void:
	AudioServer.set_bus_mute(0,true)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):output_path=arg.trim_prefix("--output=")
		if arg.begins_with("--objective-image="):image_path=arg.trim_prefix("--objective-image=")
	call_deferred("run")

func check(id: String, passed: bool, detail = null) -> void:
	checks.append({"test":id,"passed":passed,"detail":detail})

func info(id: String) -> Dictionary:
	scene.hud._process(0.0)
	var value: Dictionary = scene.hud.objective_info()
	var serial := value.duplicate()
	var direction: Vector2 = value.direction
	serial.direction=[direction.x,direction.y]
	states.append({"id":id,"objective":serial,"text":scene.hud.objective_label.text,"label_visible":scene.hud.objective_label.visible})
	return value

func owners(owner: String) -> void:
	for cap in scene.game.caps:
		cap.owner=owner
		cap.contested=false
		cap.enemies_in=0

func cap(id: String) -> Dictionary:
	for item in scene.game.caps:
		if str(item.id)==id:return item
	return {}

func run() -> void:
	scene=load("res://main.tscn").instantiate()
	root.add_child(scene)
	for i in range(600):
		await physics_frame
		if scene.world_ready:break
	if not scene.world_ready or scene.game==null:
		check("actual_combat_world_loaded",false)
		await finish()
		return
	check("actual_combat_world_loaded",true)
	scene.options["no-pointer-lock"]="1"
	scene.begin_walk()
	Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
	# Let the actual spawned capsules settle before freezing the UI fixture.
	for frame in range(60):await physics_frame
	paused=true
	scene.hud.process_mode=Node.PROCESS_MODE_ALWAYS
	var saved_caps: Array = scene.game.caps.duplicate(true)
	var saved_enemies: Array = scene.game.enemies.duplicate()
	var saved_position: Vector3 = scene.player.global_position
	var saved_rotation: Vector3 = scene.player.rotation
	var saved_over: bool = scene.game.over
	owners("enemy")
	var value := info("initial_enemy_zones")
	check("priority_C_before_B_and_A",value.target_id=="C" and value.action=="Återta" and not value.urgent)
	cap("C").owner="friendly"
	value=info("C_reclaimed")
	check("reclaimed_C_switches_to_B",value.target_id=="B")
	cap("B").owner="friendly"
	value=info("B_reclaimed")
	check("reclaimed_B_switches_to_A",value.target_id=="A")
	cap("B").owner="enemy"
	cap("C").contested=true
	cap("C").enemies_in=2
	value=info("base_alarm")
	check("friendly_base_alarm_overrides_B_and_A",value.target_id=="C" and value.action=="Försvara" and value.urgent)
	check("actual_label_shows_defend",scene.hud.objective_label.visible and scene.hud.objective_label.text.begins_with("Försvara C · Royens trappor"))
	cap("C").enemies_in=0
	value=info("contested_without_enemy")
	check("no_false_base_alarm_without_enemies",value.target_id=="B" and not value.urgent)
	owners("enemy")
	var target: Vector3 = cap("C").pos
	for sample in [{"id":"north","offset":Vector3(0,200,20),"expected":Vector2(0,-1)},
		{"id":"east","offset":Vector3(-20,200,0),"expected":Vector2(1,0)},
		{"id":"south","offset":Vector3(0,200,-20),"expected":Vector2(0,1)},
		{"id":"west","offset":Vector3(20,200,0),"expected":Vector2(-1,0)}]:
		scene.player.global_position=target+sample.offset
		scene.player.rotation.y=0
		value=info("bearing_"+str(sample.id))
		check("bearing_"+str(sample.id),Vector2(value.direction).distance_to(sample.expected)<.0001)
		check("planar_distance_ignores_200m_height_"+str(sample.id),value.distance_m==20)
	scene.player.global_position=target+Vector3(0,0,20)
	scene.player.rotation.y=PI/2
	value=info("rotated_player")
	check("bearing_follows_player_yaw",Vector2(value.direction).distance_to(Vector2(1,0))<.0001)
	owners("friendly")
	value=info("cleanup")
	check("all_friendly_requests_cleanup",value.visible and value.action=="Rensa kvarvarande fiender")
	check("cleanup_never_points_to_hidden_enemy",not value.has_target and Vector2(value.direction)==Vector2.ZERO and value.distance_m==0 and str(value.target_id).is_empty())
	scene.game.enemies=[]
	value=info("nothing_remaining")
	check("nothing_remaining_hides_guidance",not value.visible)
	scene.game.enemies=saved_enemies
	owners("enemy")
	scene.player.alive=false
	check("dead_player_hides_guidance",not info("dead").visible)
	scene.player.alive=true
	scene.game.over=true
	check("finished_round_hides_guidance",not info("ended").visible)
	scene.game.over=false
	scene.player.combat_enabled=false
	check("explore_hides_guidance",not info("explore").visible)
	scene.player.combat_enabled=true
	scene.player.active=false
	check("inactive_player_hides_guidance",not info("paused_player").visible)
	scene.player.active=true
	scene.player.global_position=saved_position
	scene.player.rotation=saved_rotation
	scene.game.caps=saved_caps.duplicate(true)
	if not image_path.is_empty():
		if DisplayServer.get_name()=="headless":
			check("native_capture_available",false,"--objective-image needs native rendering")
		else:
			var base: Dictionary=scene.game.base_cap()
			base.owner="friendly";base.contested=true;base.enemies_in=2;base.progress=.35
			scene.game._paint_cap(base)
			info("native_defend_fixture")
			for frame in range(120):await process_frame
			await RenderingServer.frame_post_draw
			var error: Error=root.get_texture().get_image().save_png(image_path)
			check("native_objective_image_saved",error==OK,image_path)
	scene.game.caps=saved_caps
	scene.game.over=saved_over
	scene.game.enemies=saved_enemies
	await finish()

func finish() -> void:
	var passed: bool=checks.all(func(item):return bool(item.passed))
	var report := {"passed":passed,"scope":"actual imported world, actual GameManager caps and live HUD objective","checks":checks,"states":states}
	if not output_path.is_empty():
		var f:=FileAccess.open(output_path,FileAccess.WRITE)
		if f!=null:f.store_string(JSON.stringify(report,"\t"))
	print("KVARNBYN_OBJECTIVE_CHECK ",JSON.stringify(report))
	paused=false
	if is_instance_valid(scene):scene.queue_free()
	await process_frame
	quit(0 if passed else 3)

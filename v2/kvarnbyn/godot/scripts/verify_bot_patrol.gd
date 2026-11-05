extends SceneTree
var world
var checks: Array[Dictionary]=[]
var output := "/tmp/patrol-check.json"
func _initialize() -> void:
	AudioServer.set_bus_mute(0,true)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
	call_deferred("run")
func check(id: String, ok: bool) -> void:
	checks.append({"test":id,"passed":ok})
func run() -> void:
	world=load("res://main.tscn").instantiate()
	root.add_child(world)
	for frame in range(600):
		await physics_frame
		if world.world_ready:break
	check("real_world_and_game_loaded",world.world_ready and world.game!=null)
	if not world.world_ready or world.game==null:
		await finish();return
	paused=true
	check("initial_goal_C",world.bot_navigation_goal(0).id=="C")
	var base: Dictionary=world.game.base_cap()
	base.owner="friendly"
	check("after_C_goal_B",world.bot_navigation_goal(0).id=="B")
	world.game.caps[1].owner="friendly"
	check("after_B_goal_A",world.bot_navigation_goal(0).id=="A")
	for cap in world.game.caps:cap.owner="friendly"
	var goal: Dictionary=world.bot_navigation_goal(0)
	check("all_owned_starts_patrol",str(goal.id).begins_with("patrol-"))
	var patrol=world.bot_patrol
	check("covers_many_district_cells",patrol.nodes.size()>40)
	var connected := true
	for node in patrol.nodes:
		connected=connected and int(node.node) in world.game.nav.main_ids
		connected=connected and not world.game.nav.astar.get_point_path(world.game.nav.main_ids[0],node.node).is_empty()
	check("all_targets_on_real_reachable_main_graph",connected)
	var first: String=goal.id
	world.player.global_position=goal.pos
	goal=world.bot_navigation_goal(0)
	check("arrival_advances_target",goal.id!=first and patrol.visits==1)
	var enemy=world.game.spawn_soldier("enemy",Vector3(500,50,300))
	var stable: String=goal.id
	enemy.global_position=Vector3(-300,-10,-200)
	check("unseen_enemy_move_does_not_change_target",world.bot_navigation_goal(0).id==stable)
	base.contested=true;base.enemies_in=2
	check("base_alarm_interrupts_patrol",world.bot_navigation_goal(0).id=="C")
	base.contested=false;base.enemies_in=0
	check("alarm_end_resumes_patrol",str(world.bot_navigation_goal(0).id).begins_with("patrol-"))
	world.game.caps[0].owner="enemy"
	check("enemy_recapture_restores_capture_goal",world.bot_navigation_goal(0).id=="A")
	# Exercise all representative targets using simulated arrivals, not claimed walking.
	patrol.configure(world.game.nav)
	var seen := {}
	var at := Vector3(10000,0,10000)
	for i in range(patrol.nodes.size()):
		var next: Dictionary=patrol.goal(at,0)
		seen[next.id]=true;at=next.pos
	patrol.goal(at,0)
	check("whole_route_visits_every_cell_before_repeat",seen.size()==patrol.nodes.size() and patrol.cycles==1)
	patrol.configure(world.game.nav)
	at=Vector3(10000,0,10000)
	var stuck: String=patrol.goal(at,0).id
	check("stationary_timer_advances_blocked_goal",patrol.goal(at,14.1).id!=stuck and patrol.skips==1)
	patrol.configure(world.game.nav)
	patrol.goal(at,0)
	patrol.goal(at,8)
	var toward: Vector3=at.move_toward(patrol.nodes[patrol.current].pos,3)
	patrol.goal(toward,8)
	check("real_progress_resets_stall_timer",patrol.skips==0 and patrol.stalled_s==0)
	patrol.configure(world.game.nav)
	check("reset_clears_previous_search",patrol.visits==0 and patrol.skips==0 and patrol.current<0)
	await finish()
func finish() -> void:
	var passed: bool=checks.all(func(c):return bool(c.passed))
	var report := {"passed":passed,"checks":checks,"scope":"real imported world/zone priority and connected nav nodes; simulated arrivals/stalls, not a capsule walk", "patrol":world.bot_patrol.snapshot() if world!=null else {}}
	var f:=FileAccess.open(output,FileAccess.WRITE)
	if f!=null:f.store_string(JSON.stringify(report,"\t"))
	print("KVARNBYN_PATROL_CHECK ",JSON.stringify(report))
	paused=false
	world.queue_free()
	await process_frame
	quit(0 if passed else 3)

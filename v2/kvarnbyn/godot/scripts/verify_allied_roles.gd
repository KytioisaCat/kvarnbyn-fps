extends SceneTree

## Real GameManager, spawned soldiers, hit/death callback and reinforcement timer.
## Frozen simulation, controlled casualties. No damage, speed or enemy balance tuning.
var world
var checks: Array[Dictionary]=[]
var stages: Array[Dictionary]=[]
var output_path := "/tmp/kvarnbyn-allied-roles.json"

func _initialize() -> void:
	AudioServer.set_bus_mute(0,true)
	seed(20261104)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):output_path=arg.trim_prefix("--output=")
	call_deferred("run")

func check(id: String, value: bool, detail=null) -> void:
	checks.append({"test":id,"passed":value,"detail":detail})

func state(id: String) -> Dictionary:
	var guards := 0
	var assault := 0
	for soldier in world.game.allies:
		if soldier.alive:
			if soldier.role=="guard":guards+=1
			if soldier.role=="assault":assault+=1
	var value := {"id":id,"total":world.game.allies.size(),"guards":guards,"assault":assault,
		"timer":world.game.ally_reinf_t,"enemy_budget":world.game.reinf_left}
	stages.append(value)
	return value

func casualties(role: String, count: int) -> int:
	var killed := 0
	for soldier in world.game.allies.duplicate():
		if soldier.alive and soldier.role==role and killed<count:
			soldier.hit(1000,false,world.game.spawn_point,null)
			killed+=1
	return killed

func replenish() -> void:
	world.game.ally_reinf_t=0.0
	world.game._physics_process(1.0/60.0)

func run() -> void:
	world=load("res://main.tscn").instantiate()
	root.add_child(world)
	for frame in range(600):
		await physics_frame
		if world.world_ready:break
	check("real_combat_world_loaded",world.world_ready and world.game!=null)
	if not world.world_ready or world.game==null:
		await finish()
		return
	world.options["no-pointer-lock"]="1"
	world.begin_walk()
	paused=true
	world.game.reinf_t=99999.0
	var initial := state("initial")
	check("starts_with_configured_three_guards",initial.total==9 and initial.guards==3 and initial.assault==6)
	var enemy_budget: int=world.game.reinf_left
	check("three_guards_die_through_real_hit_callback",casualties("guard",3)==3 and world.game.allies.size()==6)
	world.game.ally_reinf_t=10.0
	world.game._physics_process(1.0/60.0)
	check("losses_wait_for_existing_timer",state("waiting").total==6)
	replenish()
	var after_guards := state("guards_replaced")
	check("replacements_restore_guard_quota",after_guards.total==9 and after_guards.guards==3 and after_guards.assault==6)
	check("respawn_interval_preserved",absf(world.game.ally_reinf_t-45.0)<.0001)
	check("attack_soldiers_die_through_real_hit_callback",casualties("assault",2)==2)
	replenish()
	var after_attack := state("attackers_replaced")
	check("attack_losses_do_not_add_extra_guards",after_attack.total==9 and after_attack.guards==3 and after_attack.assault==6)
	casualties("guard",1)
	casualties("assault",2)
	replenish()
	var after_mixed := state("mixed_replaced")
	check("mixed_losses_restore_three_guards_six_assault",after_mixed.total==9 and after_mixed.guards==3 and after_mixed.assault==6)
	var guards_target_C := true
	for soldier in world.game.allies:
		if soldier.role=="guard":guards_target_C=guards_target_C and world.game.cap_target_for(soldier).id=="C"
	check("replacement_guards_target_actual_base",guards_target_C and after_mixed.guards>0)
	var before: int=world.game.soldiers_root.get_child_count()
	replenish()
	check("full_squad_does_not_spawn_extra_soldiers",world.game.soldiers_root.get_child_count()==before and world.game.allies.size()==9)
	check("enemy_reinforcement_budget_unchanged",world.game.reinf_left==enemy_budget)
	for soldier in world.game.allies.duplicate():soldier.hit(1000,false,world.game.spawn_point,null)
	replenish()
	var after_wipe := state("whole_squad_replaced")
	check("whole_squad_replacement_preserves_roles",after_wipe.total==9 and after_wipe.guards==3 and after_wipe.assault==6)
	# The normal restart path must restore roles and remove the former squad.
	world.game.restart()
	var restarted := state("restart")
	check("restart_restores_original_quota",restarted.total==9 and restarted.guards==3 and restarted.assault==6)
	check("debug_state_reports_living_guards",world.game.state().allied_guards==3)
	for spec in [{"count":9,"guards":0},{"count":9,"guards":9},{"count":5,"guards":2},{"count":4,"guards":12}]:
		world.game.cfg.allies.count=spec.count
		world.game.cfg.allies.guards=spec.guards
		world.game.restart()
		await process_frame
		world.game.reinf_t=99999.0
		for soldier in world.game.allies.duplicate():soldier.hit(1000,false,world.game.spawn_point,null)
		replenish()
		var configured := state("config_"+str(spec.count)+"_"+str(spec.guards))
		check("configured_role_quota_"+str(spec.count)+"_"+str(spec.guards),configured.total==int(spec.count) and configured.guards==clampi(int(spec.guards),0,int(spec.count)))

	await finish()

func finish() -> void:
	var passed: bool=not checks.is_empty() and checks.all(func(c):return bool(c.passed))
	var report := {"passed":passed,"scope":"actual GameManager, real spawned soldiers/death callbacks and expired reinforcement timer in paused imported world","checks":checks,"stages":stages}
	var f:=FileAccess.open(output_path,FileAccess.WRITE)
	if f!=null:f.store_string(JSON.stringify(report,"\t"))
	print("KVARNBYN_GUARDS_CHECK ",JSON.stringify(report))
	paused=false
	if is_instance_valid(world):world.queue_free()
	await process_frame
	quit(0 if passed else 3)

extends SceneTree

## Real imported world, actual GameManager/map. Controlled owners, not a battle result.
const Front = preload("res://scripts/map_front.gd")
var world
var checks: Array[Dictionary]=[]
var states: Dictionary={}
var options := {}

func _initialize() -> void:
	AudioServer.set_bus_mute(0,true)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--"):
			var pair := arg.trim_prefix("--").split("=",true,1)
			options[pair[0]]=pair[1] if pair.size()>1 else "1"
	call_deferred("run")

func check(id: String, ok: bool, detail=null) -> void:
	checks.append({"test":id,"passed":ok,"detail":detail})

func refresh(id: String) -> Dictionary:
	world.tactical_map.last_update_msec=-1000
	world.update_tactical_map()
	var state: Dictionary=world.tactical_map.snapshot()
	states[id]=state
	return state

func picture(id: String) -> void:
	if not options.has("front-images"):return
	if DisplayServer.get_name()=="headless":
		check("native_render_required",false)
		return
	for frame in range(90):await process_frame
	await RenderingServer.frame_post_draw
	var path := str(options["front-images"])+"/"+id+".png"
	check("image_"+id,root.get_texture().get_image().save_png(path)==OK,path)

func geometry_checks() -> void:
	var rect := Rect2(-100,-80,200,160)
	var polygon := PackedVector2Array([Vector2(-200,-200),Vector2(200,-200),Vector2(200,200),Vector2(-200,200)])
	var clipped := Front.clip_rect(polygon,rect)
	check("polygon_clips_exactly_to_view",clipped.size()==4 and Array(clipped).all(func(p):return rect.grow(.001).has_point(p)))
	check("empty_view_has_no_front_fill",Front.clip_rect(polygon,Rect2()).is_empty())
	check("tangent_view_has_no_degenerate_polygon",Front.clip_rect(polygon,Rect2(200,-80,50,160)).is_empty())
	var line := Front.clip_segment(Vector2(-200,0),Vector2(200,0),rect)
	check("line_clips_both_sides",line.size()==2 and line[0].distance_to(Vector2(-100,0))<.001 and line[1].distance_to(Vector2(100,0))<.001)
	check("line_outside_is_removed",Front.clip_segment(Vector2(-200,-100),Vector2(200,-100),rect).is_empty())
	check("vertical_line_clips",Front.clip_segment(Vector2(0,-200),Vector2(0,200),rect).size()==2)
	var zones: Array[Dictionary]=[{"id":"L","owner":"enemy","position":Vector2(-50,0),"radius":15},
		{"id":"R","owner":"friendly","position":Vector2(50,0),"radius":15}]
	var model := Front.build(zones,rect)
	check("opposed_zones_have_one_front",model.regions.size()==2 and model.fronts.size()==1)
	check("front_is_equal_distance_bisector",model.fronts.size()==1 and absf(model.fronts[0][0].x)<.005 and absf(model.fronts[0][1].x)<.005)
	var no_overlap := true
	var bounded := true
	for region in model.regions:
		var centre := Vector2(-50,0) if region.id=="L" else Vector2(50,0)
		for point in region.polygon:
			bounded=bounded and rect.grow(.001).has_point(point) and point.distance_to(centre)<=125.01
			no_overlap=no_overlap and (point.x<=.005 if region.id=="L" else point.x>=-.005)
	check("influence_bounded_by_reach_and_world",bounded)
	check("each_colour_stays_on_its_side",no_overlap)
	zones[1].owner="enemy"
	check("same_owner_has_no_front",Front.build(zones,rect).fronts.is_empty())
	zones[1].position=Vector2(-50,0)
	check("coincident_zones_do_not_duplicate_fill",Front.build(zones,rect).regions.size()==1)
	check("empty_explore_model_has_no_regions",Front.build([],rect).regions.is_empty())

func run() -> void:
	geometry_checks()
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
	for frame in range(60):await physics_frame
	paused=true
	var map=world.tactical_map
	for cap in world.game.caps:
		cap.owner="enemy";cap.contested=false;cap.enemies_in=0
	var initial := refresh("initial")
	check("three_actual_hostile_zones_coloured",initial.front.regions==3 and initial.front.boundaries==0)
	check("four_configured_entry_arrows",initial.front.entries==world.game.cfg.enemy_entries.size() and initial.front.incoming==4)
	map.set_expanded(true)
	refresh("initial_full")
	await picture("front-initial")
	var builds: int=map.front_builds
	world.player.global_position+=Vector3(5,0,0)
	refresh("player_moved")
	check("player_movement_does_not_rebuild_regions",map.front_builds==builds)
	var saved_enemy_position: Vector3=world.game.enemies[0].global_position
	world.game.enemies[0].global_position+=Vector3(220,10,190)
	var hidden := refresh("unseen_enemy_moved")
	check("unseen_enemy_has_no_map_effect",hidden.front==states.player_moved.front and hidden.enemy_positions==0)
	world.game.enemies[0].global_position=saved_enemy_position
	var base: Dictionary=world.game.base_cap()
	base.owner="friendly"
	base.contested=true
	base.enemies_in=2
	base.progress=.35
	world.game._paint_cap(base)
	var mixed := refresh("base_under_attack")
	check("reclaiming_C_moves_front",mixed.front.boundaries>0 and map.front_builds==builds+1)
	check("base_attack_matches_real_cap_fields",mixed.front.base_under_attack)
	check("mixed_owner_colours_present",map.front_regions.any(func(r):return str(r.owner)=="friendly") and map.front_regions.any(func(r):return str(r.owner)=="enemy"))
	await picture("front-base-alarm")
	map.set_expanded(false)
	var mini_at: Vector3=base.pos+Vector3(35,0,35)
	var query:=PhysicsRayQueryParameters3D.create(mini_at+Vector3.UP*150,mini_at-Vector3.UP*100,1)
	var ground: Dictionary=world.get_world_3d().direct_space_state.intersect_ray(query)
	check("mini_fixture_uses_actual_floor",not ground.is_empty())
	if not ground.is_empty():
		world.player.global_position=Vector3(ground.position)+Vector3.UP*.1
		world.player.rotation.y=atan2(mini_at.x-base.pos.x,mini_at.z-base.pos.z)
		world.player.camera.rotation.x=-.08
	refresh("mini_base")
	await picture("front-mini")
	base.enemies_in=0
	check("contested_without_enemies_is_not_base_alarm",not refresh("not_an_attack").front.base_under_attack)
	base.enemies_in=2
	base.owner="enemy"
	check("enemy_owned_C_is_not_a_defend_alarm",not refresh("enemy_C").front.base_under_attack)
	base.owner="friendly"
	base.contested=false
	base.enemies_in=0
	world.game.reinf_left=0
	check("exhausted_reinforcements_hide_arrows",refresh("reinforcements_exhausted").front.incoming==0)
	world.game.reinf_left=3
	check("new_reinforcement_budget_restores_arrows",refresh("reinforcements_restored").front.incoming==4)
	for cap in world.game.caps:
		cap.owner="friendly";cap.contested=false;cap.enemies_in=0
		world.game._paint_cap(cap)
	var cleared := refresh("all_reclaimed")
	check("all_reclaimed_no_front_or_incoming",cleared.front.regions==3 and cleared.front.boundaries==0 and cleared.front.incoming==0)
	check("no_red_regions_after_all_reclaimed",not map.front_regions.any(func(r):return str(r.owner)=="enemy"))
	map.set_expanded(true)
	refresh("cleared_full")
	await picture("front-reclaimed")
	map._layout()
	check("expanded_board_fits_viewport",Rect2(Vector2.ZERO,root.get_visible_rect().size).encloses(map._layout()))
	map.set_state(world.player.global_position,0,[],[],false)
	# Force a fresh empty state despite the component's normal75ms throttle.
	map.last_update_msec=-1000
	map.set_state(world.player.global_position,0,[],[],false)
	check("explore_clears_all_front_information",map.front_regions.is_empty() and map.incoming_arrows.is_empty() and not map.base_under_attack)
	await finish()

func finish() -> void:
	var passed: bool=not checks.is_empty() and checks.all(func(c):return bool(c.passed))
	var report := {"passed":passed,"scope":"real world/map/GameManager with controlled owners and algebraic clipping checks; no measured battle front", "checks":checks,"states":states}
	if options.has("output"):
		var f:=FileAccess.open(str(options.output),FileAccess.WRITE)
		if f!=null:f.store_string(JSON.stringify(report,"\t"))
	print("KVARNBYN_FRONT_CHECK ",JSON.stringify(report))
	paused=false
	if is_instance_valid(world):world.queue_free()
	await process_frame
	quit(0 if passed else 3)

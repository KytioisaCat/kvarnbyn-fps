extends SceneTree

## Quiet component checks; root's native world test additionally checks M/Esc/pause.
const TacticalMap = preload("res://scripts/tactical_map.gd")
var checks: Array[Dictionary] = []
var output_path := ""

func _initialize() -> void:
	AudioServer.set_bus_mute(0,true)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):
			output_path = arg.trim_prefix("--output=")
	call_deferred("run")

func check(id: String, passed: bool, detail = null) -> void:
	checks.append({"test":id,"passed":passed,"detail":detail})

func run() -> void:
	var map = TacticalMap.new()
	root.add_child(map)
	await process_frame
	check("actual_generated_map_loads",map.setup())
	check("bounds_cover_900x700m",map.world_bounds.size.is_equal_approx(Vector2(900,700)))
	check("northwest_corner_maps_to_0_0",map.world_to_uv(map.world_bounds.position).is_equal_approx(Vector2.ZERO))
	check("southeast_corner_maps_to_1_1",map.world_to_uv(map.world_bounds.end).is_equal_approx(Vector2.ONE))
	for sample in [[0.0,Vector2(0,-1)],[PI/2,Vector2(-1,0)],[PI,Vector2(0,1)],[-PI/2,Vector2(1,0)]]:
		check("player_heading_"+str(sample[0]),map.heading_vector(sample[0]).distance_to(sample[1])<.0001)
	check("zone_owner_colors_distinct",map.owner_color("ally")!=map.owner_color("enemy"))
	var caps: Array = [{"id":"A","name":"Gamla torget","pos":Vector3(-8,0,0),"owner":"enemy","radius":18.0},
		{"id":"B","name":"Roten M","pos":Vector3(100,24,110),"owner":"ally","radius":15.0},
		{"id":"C","name":"Royens trappor","pos":Vector3(175,21,-1),"owner":"enemy","contested":true,"radius":16.0}]
	var player := Vector3(340,52,153)
	map.set_state(player,PI/2,caps)
	map._layout()
	check("minimap_centres_on_player",map.world_view.get_center().distance_to(Vector2(player.x,player.z))<.001)
	check("minimap_above_health",map.map_rect.end.y<=root.get_visible_rect().size.y-99)
	check("snapshot_contains_3_zones_no_enemy_positions",map.snapshot().zones==3 and map.snapshot().enemy_positions==0)
	check("one_static_map_draw",map.snapshot().static_map_draws==1)
	var before: int = map.get_child_count()
	for i in range(4):
		map.set_expanded(true)
		map._layout()
		check("fullmap_fits_"+str(i),Rect2(Vector2.ZERO,root.get_visible_rect().size).encloses(map.map_rect))
		check("fullmap_preserves_geographic_aspect_"+str(i),absf(map.map_rect.size.x/map.map_rect.size.y-900.0/700)<.0001)
		map.set_expanded(false)
	check("repeated_toggle_does_not_create_controls",map.get_child_count()==before)
	var closed := [false]
	map.close_requested.connect(func(): closed[0]=true)
	map.close_button.pressed.emit()
	check("close_button_requests_host_close",closed[0])
	map.last_update_msec = -1000
	map.set_state(Vector3(map.world_bounds.position.x,0,map.world_bounds.position.y),0,[])
	check("explore_mode_without_zone_or_enemy_markers",map.snapshot().zones==0 and map.snapshot().enemy_positions==0)
	map._layout()
	check("map_edge_keeps_player_centred",map.world_view.get_center().distance_to(map.world_bounds.position)<.001)
	check("invalid_assets_return_false",not map.setup("res://assets/not-a-map.json"))
	check("valid_asset_recovers_after_missing",map.setup())
	var passed := checks.all(func(value):return bool(value.passed))
	var report := {"passed":passed,"scope":"actual generated map texture/metadata and native Control component math/state","checks":checks,"snapshot":map.snapshot()}
	if not output_path.is_empty():
		var f := FileAccess.open(output_path,FileAccess.WRITE)
		if f!=null:f.store_string(JSON.stringify(report,"\t"))
	print("KVARNBYN_MAP_CHECK ",JSON.stringify(report))
	map.queue_free()
	await process_frame
	quit(0 if passed else 3)

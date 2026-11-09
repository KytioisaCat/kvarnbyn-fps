extends RefCounted

# Same real player, city colliders and exported path metadata in editor/release.
var checks: Array = []
var paths: Array = []
func check(id: String, passed: bool, detail = null) -> void:
	checks.append({"test":id,"passed":passed,"detail":detail})
func xyz(value) -> Vector3:
	return Vector3(float(value[0]),float(value[1]),float(value[2]))
func flat(a: Vector3,b: Vector3) -> float:
	return Vector2(a.x-b.x,a.z-b.z).length()
func expected_height(point: Vector3, route: Array) -> float:
	var closest := INF
	var height := 0.0
	for i in range(route.size()-1):
		var a: Vector3=route[i]
		var b: Vector3=route[i+1]
		var delta := Vector2(b.x-a.x,b.z-a.z)
		var t := clampf(Vector2(point.x-a.x,point.z-a.z).dot(delta)/maxf(.00001,delta.length_squared()),0.,1.)
		var on_path := a.lerp(b,t)
		var distance := flat(point,on_path)
		if distance<closest:
			closest=distance
			height=on_path.y
	return height
func run(world: Node3D, metadata_key := "road_ground_checks", minimum_paths := 6, minimum_points := 9) -> Dictionary:
	AudioServer.set_bus_mute(0,true)
	var tree := world.get_tree()
	var p = world.player
	var metadata: Dictionary=world.metadata.get(metadata_key,{})
	check(metadata_key+"_packaged",metadata.get("paths",[]).size()>=minimum_paths and metadata.get("points",[]).size()>=minimum_points)
	if not checks[0].passed:return report()
	world.begin_walk()
	if world.game:world.game.running=false
	p.bot_input=Vector2.ZERO
	p.bot_sprint=false
	p.free_flight=false
	p.grapple.release()
	p.combat_enabled=false
	p.input_suspended=false
	for sample in metadata.points:
		var point := xyz(sample.position)
		var query := PhysicsRayQueryParameters3D.create(point+Vector3.UP*.8,point+Vector3.DOWN*2,1)
		var hit: Dictionary=p.get_world_3d().direct_space_state.intersect_ray(query)
		check(str(sample.id)+"_floor",not hit.is_empty() and absf(hit.position.y-point.y)<.16)
	for spec in metadata.paths:
		var route: Array=[]
		var length := 0.0
		for value in spec.points:
			var next := xyz(value)
			if not route.is_empty():length+=flat(route[-1],next)
			route.append(next)
		p.place_at(route[0]+Vector3.UP*.05,0,0,false)
		p.bot_input=Vector2.ZERO
		for frame in range(25):await tree.physics_frame
		var index := 1
		var maximum_error := 0.0
		var used_frames := 0
		var limit := ceili((length/2.4+6.)*60.)
		for frame in range(limit):
			var toward: Vector3=route[index]-p.global_position
			toward.y=0.
			if toward.length()<.3:
				index+=1
				if index==route.size():break
				toward=route[index]-p.global_position
			p.rotation.y=atan2(-toward.x,-toward.z)
			p.bot_input=Vector2(0,-3./p.movement.get_value("walk_speed"))
			await tree.physics_frame
			used_frames+=1
			maximum_error=maxf(maximum_error,absf(p.global_position.y-expected_height(p.global_position,route)))
		p.bot_input=Vector2.ZERO
		var result := {"id":spec.id,"reached":index==route.size(),"max_height_error_m":maximum_error,"frames":used_frames,"length_m":length}
		paths.append(result)
		check(str(spec.id)+"_actual_capsule",result.reached and maximum_error<.25,result)
	for spec in metadata.blockers:
		var a := xyz(spec["from"])+Vector3.UP*float(spec.get("height_m",1.25))
		var b := xyz(spec["to"])+Vector3.UP*float(spec.get("height_m",1.25))
		var hit: Dictionary=p.get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(a,b,1))
		check(str(spec.id)+"_actual_wall",not hit.is_empty())
	return report()
func report() -> Dictionary:
	var passed := true
	for result in checks:passed=passed and bool(result.passed)
	return {"passed":passed,"release":not OS.has_feature("editor"),"checks":checks,"paths":paths}

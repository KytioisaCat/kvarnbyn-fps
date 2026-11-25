extends SceneTree

func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	call_deferred("run")

func run() -> void:
	var w = load("res://main.tscn").instantiate()
	root.add_child(w)
	for frame in range(900):
		await physics_frame
		if w.world_ready: break
	await physics_frame
	var items = JSON.parse_string(FileAccess.get_file_as_string("res://../reference/gotafors/terraces.json"))
	var ok := true
	for item in items:
		var a := Vector3(float(item.ends_xz[0][0]),0,float(item.ends_xz[0][1]))
		var b := Vector3(float(item.ends_xz[1][0]),0,float(item.ends_xz[1][1]))
		var up := Vector3(-(b-a).z,0,(b-a).x).normalized()*float(item.uphill_side)
		var passed := 0
		var relief := []
		for t in [.2,.5,.8]:
			var p := a.lerp(b,t)
			var top = hit(w,p+up*.16+Vector3.UP*60,p+up*.16-Vector3.UP*10)
			var base = hit(w,p-up*.45+Vector3.UP*60,p-up*.45-Vector3.UP*10)
			if top.is_empty() or base.is_empty():continue
			var diff: float = top.position.y-base.position.y
			relief.append(snappedf(diff,.01))
			var probe := Vector3(p.x,top.position.y-.07,p.z)
			var face = hit(w,probe-up*.4,probe+up*.12)
			if str(top.collider.get_path()).contains("COL_Terrace_"+item.id) and face and str(face.collider.get_path()).contains("COL_Terrace_"+item.id) and diff>.07:passed+=1
		print("TERRACE ",item.id," ",passed,"/3 relief ",relief)
		ok = ok and passed==3
	quit(0 if ok else 1)

func hit(w,p:Vector3,q:Vector3) -> Dictionary:
	return w.get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(p,q,1))

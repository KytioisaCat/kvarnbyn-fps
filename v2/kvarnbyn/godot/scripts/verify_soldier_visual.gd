extends SceneTree

const Visual = preload("res://scripts/soldier_visual.gd")
var actors: Array = []
var failures: Array = []
var reports: Array = []
var capture := ""

func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--capture="):
			capture = arg.trim_prefix("--capture=")
	call_deferred("run")

func check(ok: bool, message: String) -> void:
	if not ok:
		failures.append(message)

func run() -> void:
	var stage := Node3D.new()
	root.add_child(stage)
	var environment := WorldEnvironment.new()
	environment.environment = Environment.new()
	environment.environment.background_mode = Environment.BG_COLOR
	environment.environment.background_color = Color("b2bfca")
	environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.environment.ambient_light_color = Color("c1d2e0")
	environment.environment.ambient_light_energy = 0.65
	stage.add_child(environment)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 1.5
	sun.rotation_degrees = Vector3(-48, -25, 0)
	sun.shadow_enabled = true
	stage.add_child(sun)
	var floor_mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(200, 200)
	floor_mesh.mesh = plane
	var floor_mat := StandardMaterial3D.new()
	floor_mat.albedo_color = Color("6e787a")
	floor_mesh.material_override = floor_mat
	stage.add_child(floor_mesh)
	for i in range(3):
		var v := Visual.new()
		stage.add_child(v)
		v.position = Vector3((i - 1) * 1.65, 0, 0)
		v.rotation.y = PI - 0.2
		v.configure("friendly" if i == 0 else "enemy")
		actors.append(v)
		check(v.animation.has_animation("Run_Left") and v.animation.has_animation("Death"), "Named clips missing")
		check(v.skeleton.get_bone_count() > 40, "Skinned skeleton missing")
	var cam := Camera3D.new()
	stage.add_child(cam)
	cam.position = Vector3(4.3, 2.5, 6)
	cam.look_at(Vector3(0, 1.0, 0))
	cam.fov = 35
	cam.make_current()
	var cases := [
		["Idle_Gun_Pointing", Vector3.ZERO, false],
		["Walk", Vector3(0, 0, -1.2), false],
		["Run_Shoot", Vector3(0, 0, -3), true],
		["Run_Left", Vector3(-3, 0, 0), true],
		["Run_Right", Vector3(3, 0, 0), true],
		["Run_Back", Vector3(0, 0, 2), true]]
	for c in cases:
		var v = actors[0]
		v.update_pose(0.02, c[1], c[2], true, 0.0)
		v.animation.advance(0.24)
		await process_frame
		check(v.state == c[0], "Wrong movement clip: " + v.state)
		var head: Vector3 = v.head_global_position() - v.global_position
		check(head.y > 1.30 and head.y < 1.90, "Head outside standing hit zone")
		var muzzle_local: Vector3 = v.to_local(v.muzzle.global_position)
		check(muzzle_local.y > 1.0 and muzzle_local.y < 1.8 and muzzle_local.z < -0.40, "Muzzle fails forward/height check: " + str(muzzle_local))
		reports.append(v.snapshot())
	actors[0].update_pose(0.02, Vector3.ZERO, false, true, 0.0)
	actors[1].update_pose(0.02, Vector3(0, 0, -3), true, true, 0.0)
	actors[2].update_pose(0.02, Vector3(3, 0, 0), true, true, 0.0)
	for v in actors:
		v.animation.advance(0.16)
	for frame in range(5):
		await process_frame
	var death = actors[0]
	death.update_pose(0.02, Vector3.ZERO, false, false, 0.0)
	check(death.state == "Death", "Death clip not selected")
	check(death.animation.get_animation("Death").loop_mode == Animation.LOOP_NONE, "Death must not loop")
	death.dead = false
	death.update_pose(0.02, Vector3.ZERO, false, true, 0.0)
	var result := {"checks": "six movement directions, skeleton, muzzle, head, death", "fails": failures, "poses": reports}
	print("KVARNBYN_SOLDIER_VISUAL ", JSON.stringify(result))
	if capture != "":
		for frame in range(45):
			await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(capture)
	quit(0 if failures.is_empty() else 2)

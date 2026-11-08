extends SceneTree
const Lighting = preload("res://scripts/lighting.gd")
const Civilian = preload("res://scripts/civilian.gd")
const Roster = preload("res://scripts/civilian_roster.gd")
var stage: Node3D
var camera: Camera3D
var output: String
func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	call_deferred("run")
func capture(label: String) -> void:
	for frame in range(8): await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(output.path_join(label + ".png"))
	print("CAPTURED ", label)
func run() -> void:
	root.size = Vector2i(1600, 1000)
	output = ProjectSettings.globalize_path("res://../evidence/civilians")
	DirAccess.make_dir_recursive_absolute(output)
	stage = Node3D.new()
	root.add_child(stage)
	stage.add_child(Lighting.make_environment())
	stage.add_child(Lighting.make_sun())
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(30, 30)
	ground.mesh = plane
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("68766b")
	material.roughness = 1.0
	ground.material_override = material
	stage.add_child(ground)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-25, 145, 0)
	fill.light_energy = 1.0
	stage.add_child(fill)
	for i in range(4):
		var model: Node3D = Civilian.MODELS[Roster.PEOPLE[i].id].instantiate()
		stage.add_child(model)
		model.position.x = (i - 1.5) * 1.3
		var label := Label3D.new()
		label.text = str(Roster.PEOPLE[i].name)
		label.font_size = 54
		label.pixel_size = 0.0026
		label.outline_size = 8
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.position = Vector3(model.position.x, 2.05, 0)
		stage.add_child(label)
	camera = Camera3D.new()
	stage.add_child(camera)
	camera.position = Vector3(0, 2.2, 7.4)
	camera.fov = 38
	camera.look_at(Vector3(0, 0.95, 0))
	camera.make_current()
	await capture("civilian-lineup")
	var soldier = preload("res://scripts/soldier_visual.gd").new()
	stage.add_child(soldier)
	soldier.configure("ally")
	soldier.rotation.y = PI
	soldier.position.x = 3.65
	camera.position = Vector3(0.7, 2.3, 9.3)
	camera.look_at(Vector3(0.7, 1.0, 0))
	await capture("civilian-soldier-comparison")
	soldier.queue_free()
	for i in range(4):
		var x := (i - 1.5) * 1.3
		camera.position = Vector3(x, 1.60, 1.15)
		camera.fov = 43
		camera.look_at(Vector3(x, 1.45, 0))
		await capture(str(Roster.PEOPLE[i].id) + "-portrait")
	quit()

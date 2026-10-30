extends Node3D

## Shared skinned meshes and authored clips; CharacterBody3D owns world movement.
const MODEL_PATH := "res://assets/characters/soldier.glb"
static var _scene: PackedScene
static var _team_materials := {}
var model: Node3D
var animation: AnimationPlayer
var skeleton: Skeleton3D
var muzzle: Node3D
var head_bone := -1
var state := ""
var dead := false
var phase := 0.0
var updates := 0

func configure(team: String) -> void:
	if _scene == null:
		_scene = load(MODEL_PATH) as PackedScene
	assert(_scene != null, "Soldatmodellen saknas. Kör rebuild.sh.")
	model = _scene.instantiate()
	# The source model faces +Z. Every actor in the game faces -Z.
	model.rotation.y = PI
	add_child(model)
	# Blender bone parenting exports the attached weapon in the chest bone convention.
	# Correct its local forward axis; the muzzle-direction regression probe guards this.
	var rifle := model.find_child("Soldier_Ak5", true, false) as Node3D
	assert(rifle != null)
	rifle.rotation.y += PI
	animation = model.find_children("*", "AnimationPlayer", true, false)[0] as AnimationPlayer
	skeleton = model.find_children("*", "Skeleton3D", true, false)[0] as Skeleton3D
	head_bone = skeleton.find_bone("Head")
	muzzle = model.find_child("Muzzle", true, false) as Node3D
	assert(muzzle != null and head_bone >= 0)
	for clip_name in animation.get_animation_list():
		if clip_name == "RESET":
			continue
		var clip := animation.get_animation(clip_name)
		clip.loop_mode = Animation.LOOP_NONE if "Death" in clip_name or "HitRecieve" in clip_name else Animation.LOOP_LINEAR
	for node in model.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := node as MeshInstance3D
		mesh_instance.visibility_range_end = 200.0
		for surface in range(mesh_instance.mesh.get_surface_count()):
			var source := mesh_instance.get_active_material(surface) as StandardMaterial3D
			if source == null:
				continue
			var mat_name := source.resource_name
			if mat_name not in ["Swat", "Swat_Black", "Grey"]:
				continue
			var key := team + ":" + mat_name
			if not _team_materials.has(key):
				var mat := source.duplicate() as StandardMaterial3D
				if mat_name == "Swat":
					mat.albedo_color = Color("79634d") if team == "enemy" else Color("3e596d")
				elif mat_name == "Swat_Black":
					mat.albedo_color = Color("3c4035") if team == "enemy" else Color("25333d")
				else:
					mat.albedo_color = Color("626951") if team == "enemy" else Color("354c58")
				mat.roughness = 0.86
				_team_materials[key] = mat
			mesh_instance.set_surface_override_material(surface, _team_materials[key])
	play("Idle_Gun_Pointing", 0.0)
	phase = randf()
	animation.seek(phase * animation.current_animation_length, true)

func play(clip: String, blend := 0.16) -> void:
	if state == clip:
		return
	state = clip
	animation.play(clip, blend)

func update_pose(_delta: float, local_velocity: Vector3, engaging: bool, alive: bool, flinch: float) -> void:
	if not alive:
		if not dead:
			dead = true
			play("Death", 0.1)
			animation.speed_scale = 1.0
		return
	updates += 1
	var speed := Vector2(local_velocity.x, local_velocity.z).length()
	var clip := "Idle_Gun_Pointing"
	var natural_speed := 1.0
	if speed > 0.28:
		if speed < 1.85:
			clip = "Walk"
			natural_speed = 1.5
		elif engaging and absf(local_velocity.x) > absf(local_velocity.z) * 0.85:
			clip = "Run_Right" if local_velocity.x > 0.0 else "Run_Left"
			natural_speed = 3.0
		elif engaging and local_velocity.z > 0.4:
			clip = "Run_Back"
			natural_speed = 2.5
		else:
			clip = "Run_Shoot" if engaging else "Run"
			natural_speed = 3.2
	play(clip)
	animation.speed_scale = clampf(speed / natural_speed, 0.55, 1.7) if speed > 0.28 else 1.0
	rotation.x = -flinch * 0.08

func head_global_position() -> Vector3:
	return skeleton.to_global(skeleton.get_bone_global_pose(head_bone).origin)

func snapshot() -> Dictionary:
	return {"clip": state, "dead": dead, "bones": skeleton.get_bone_count(),
		"clips": animation.get_animation_list().size(), "speed": animation.speed_scale,
		"muzzle": [muzzle.global_position.x, muzzle.global_position.y, muzzle.global_position.z],
		"head": [head_global_position().x, head_global_position().y, head_global_position().z]}

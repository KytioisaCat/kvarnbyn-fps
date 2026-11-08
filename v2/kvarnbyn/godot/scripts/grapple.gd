extends Node3D

## En motordriven, mjuk lina: invevning + tangentiell styrning. Ingen teleportering.
## Svingens energi kommer från vinschen och spelaren; släpp ändrar aldrig hastigheten.
const MIN_DISTANCE := 2.0

var player: CharacterBody3D
var attached := false
var anchor := Vector3.ZERO
var rope_length := 0.0
var previous_distance := 0.0
var anchor_body: Node3D
var anchor_local := Vector3.ZERO
var held_last := false
var feedback := ""
var feedback_time := 0.0
var cable: MeshInstance3D
var marker: MeshInstance3D

func _ready() -> void:
	top_level = true
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("dac28b")
	material.roughness = 0.6
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	cable = MeshInstance3D.new()
	var cylinder := CylinderMesh.new()
	cylinder.top_radius = 0.018
	# Tunnare vid handen: en jämntjock cylinder blev en bred kil nära kameran.
	cylinder.bottom_radius = 0.004
	cylinder.height = 1.0
	cylinder.radial_segments = 6
	cable.mesh = cylinder
	cable.material_override = material
	cable.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(cable)
	marker = MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 0.075
	sphere.height = 0.15
	marker.mesh = sphere
	marker.material_override = material
	marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(marker)
	show_cable(false)

func harness() -> Vector3:
	return player.global_position + Vector3.UP

func cast_target() -> Dictionary:
	var origin: Vector3 = player.camera.global_position
	var end: Vector3 = origin - player.camera.global_basis.z * player.movement.get_value("reach")
	var query := PhysicsRayQueryParameters3D.create(origin, end, 1, [player.get_rid()])
	return player.get_world_3d().direct_space_state.intersect_ray(query)

func try_attach() -> bool:
	if not player.active or not player.alive or player.input_suspended or player.free_flight:
		return false
	var hit := cast_target()
	if hit.is_empty() or harness().distance_to(hit.position) < MIN_DISTANCE:
		feedback = "Ingen fästpunkt inom %d m" % roundi(player.movement.get_value("reach"))
		feedback_time = 0.8
		return false
	anchor_body = hit.collider as Node3D
	if anchor_body == null:
		return false
	anchor = hit.position + hit.normal * 0.025
	anchor_local = anchor_body.to_local(anchor)
	rope_length = harness().distance_to(anchor)
	previous_distance = rope_length
	attached = true
	player.momentum_mode = true
	feedback_time = 0.0
	show_cable(true)
	return true

func poll(held: bool) -> void:
	if held and not held_last:
		try_attach()
	elif not held:
		release()
	held_last = held

func release() -> void:
	attached = false
	anchor_body = null
	show_cable(false)

func show_cable(value: bool) -> void:
	if cable != null:
		cable.visible = value
		marker.visible = value

func accelerate(wish: Vector3, delta: float) -> void:
	if not attached:
		return
	if not is_instance_valid(anchor_body):
		release()
		return
	anchor = anchor_body.to_global(anchor_local)
	var offset := anchor - harness()
	var distance := offset.length()
	if distance < 1.3 or distance > player.movement.get_value("reach") * 1.4:
		release()
		return
	var radial := offset / distance
	# Linan går inte genom ett nytt hinder. Närmaste 15 cm vid fästet undantas.
	var query := PhysicsRayQueryParameters3D.create(harness(), anchor - radial * 0.15, 1, [player.get_rid()])
	if not player.get_world_3d().direct_space_state.intersect_ray(query).is_empty():
		feedback = "Linan bröts mot ett hinder"
		feedback_time = 0.8
		release()
		return
	rope_length = maxf(1.3, rope_length - player.movement.get_value("reel_speed") * delta)
	var inward := player.velocity.dot(radial)
	var tangent := player.velocity - radial * inward
	if distance > rope_length - 0.25:
		# Kortare svingradie höjer tangenthastigheten (vinschen utför arbete).
		# Använd faktisk radie, inte nominell linlängd, så ett hinder inte laddar fart.
		var gain := clampf(previous_distance / distance, 1.0, 1.06)
		tangent *= 1.0 + (gain - 1.0) * player.movement.get_value("swing_boost")
		inward = maxf(inward, 0.0)
	var target_pull: float = player.movement.get_value("reel_speed") + clampf((distance - rope_length) * player.movement.get_value("rope_stiffness"), 0.0, player.movement.get_value("rope_catchup"))
	inward += minf(player.movement.get_value("pull_accel") * delta, maxf(0.0, target_pull - inward))
	# Samma analogvektor för W, A/D och diagonal; ingen tangentkombinationsbonus.
	var steering := wish - radial * wish.dot(radial)
	tangent += steering * player.movement.get_value("swing_accel") * delta
	player.velocity = (radial * inward + tangent).limit_length(player.movement.get_value("max_speed"))
	previous_distance = distance

func _process(delta: float) -> void:
	feedback_time = maxf(0.0, feedback_time - delta)
	if not attached:
		return
	var start: Vector3 = player.camera.global_transform * Vector3(-0.24, -0.18, -0.42)
	var offset := anchor - start
	cable.global_position = (start + anchor) * 0.5
	cable.quaternion = Quaternion(Vector3.UP, offset.normalized())
	cable.scale = Vector3(1.0, offset.length(), 1.0)
	marker.global_position = anchor

func snapshot() -> Dictionary:
	return {"attached": attached, "anchor": [anchor.x, anchor.y, anchor.z],
		"rope_length": rope_length, "reach": player.movement.get_value("reach")}

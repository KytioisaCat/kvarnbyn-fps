extends Node3D

## Existing lamp fixtures only. A small reusable pool follows the player; all
## normal-quality lights cast shadows, so pools do not shine through house walls.
const MAX_LIGHTS := 8
const LOW_LIGHTS := 4
const ACTIVE_RADIUS_M := 60.0
const LAMP_COLOR := Color("ffd29b")

var observer: Node3D
var positions: Array[Vector3] = []
var pool: Array[SpotLight3D] = []
var fixtures := []
var active_ids: Array[int] = []
var evening := false
var low_quality := false
var elapsed := 0.0

func configure(world: Node3D, lamps: Array, player: Node3D) -> void:
	observer = player
	for p in lamps:
		positions.append(Vector3(float(p[0]), float(p[1]), float(p[2])))
	var materials := {}
	for mesh in world.find_children("*", "MeshInstance3D", true, false):
		if mesh.mesh == null or not str(mesh.name).begins_with("Streetlamp_glass"):
			continue
		for surface in range(mesh.mesh.get_surface_count()):
			var original = mesh.get_active_material(surface)
			if not original is StandardMaterial3D:
				continue
			var key: int = original.get_instance_id()
			if not materials.has(key):
				var lit: StandardMaterial3D = original.duplicate()
				lit.resource_name = "Gatlyktans varma ljus"
				lit.albedo_color = LAMP_COLOR
				lit.emission_enabled = true
				lit.emission = LAMP_COLOR
				lit.emission_energy_multiplier = 3.5
				materials[key] = lit
			fixtures.append({"mesh": mesh, "surface": surface, "day": original, "evening": materials[key]})
	for index in range(MAX_LIGHTS):
		var light := SpotLight3D.new()
		light.name = "Gatlykta_%d" % index
		light.rotation_degrees.x = -90.0
		light.light_color = LAMP_COLOR
		light.light_energy = 3.8
		light.light_indirect_energy = 0.45
		light.light_volumetric_fog_energy = 0.15
		light.spot_range = 13.5
		light.spot_angle = 58.0
		light.spot_angle_attenuation = 0.7
		light.spot_attenuation = 1.4
		light.shadow_enabled = true
		light.shadow_bias = 0.04
		light.shadow_normal_bias = 0.35
		light.light_bake_mode = Light3D.BAKE_DISABLED
		light.distance_fade_enabled = true
		light.distance_fade_begin = 48.0
		light.distance_fade_shadow = 48.0
		light.distance_fade_length = 12.0
		light.visible = false
		add_child(light)
		pool.append(light)

func set_evening(value: bool) -> void:
	evening = value
	for fixture in fixtures:
		fixture.mesh.set_surface_override_material(fixture.surface, fixture.evening if evening else fixture.day)
	refresh()

func set_low_quality(value: bool) -> void:
	low_quality = value
	refresh()

func refresh() -> void:
	active_ids.clear()
	if evening and is_instance_valid(observer):
		var candidates := []
		for index in range(positions.size()):
			var d := positions[index].distance_squared_to(observer.global_position + Vector3.UP * 4.95)
			if d < ACTIVE_RADIUS_M * ACTIVE_RADIUS_M:
				candidates.append({"id": index, "distance": d})
		candidates.sort_custom(func(a, b): return a.distance < b.distance)
		for index in range(mini(candidates.size(), LOW_LIGHTS if low_quality else MAX_LIGHTS)):
			active_ids.append(int(candidates[index].id))
	for index in range(pool.size()):
		var light := pool[index]
		light.visible = index < active_ids.size()
		if light.visible:
			# Metadata is at the visible glass. Put the source just below it.
			light.position = positions[active_ids[index]] + Vector3.DOWN * 0.08
			light.shadow_enabled = not low_quality or index < 2

func _process(delta: float) -> void:
	elapsed += delta
	if elapsed >= 0.25:
		elapsed = 0.0
		refresh()

func snapshot() -> Dictionary:
	var shadow_count := 0
	for light in pool:
		if light.visible and light.shadow_enabled:
			shadow_count += 1
	return {"fixtures": positions.size(), "emissive_meshes": fixtures.size(), "active_lights": active_ids.size(),
		"shadow_lights": shadow_count, "active_ids": active_ids.duplicate(), "pool_size": pool.size(), "evening": evening}

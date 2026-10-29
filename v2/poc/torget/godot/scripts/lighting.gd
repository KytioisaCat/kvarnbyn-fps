extends RefCounted

## Shared settings keep the runtime and the optional light-bake scene in agreement.

static func make_environment() -> WorldEnvironment:
	var world_environment := WorldEnvironment.new()
	world_environment.name = "Dagsljus"
	var environment := Environment.new()
	environment.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	sky.radiance_size = Sky.RADIANCE_SIZE_256
	var sky_material := PanoramaSkyMaterial.new()
	sky_material.panorama = load("res://assets/sky.hdr")
	sky.sky_material = sky_material
	environment.sky = sky
	environment.background_energy_multiplier = 1.1
	# The panorama contains an HDR sun. It supplies background and reflections,
	# while neutral diffuse ambient plus our single directional light own GI.
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("c6d0d7")
	environment.ambient_light_energy = 0.35
	environment.ambient_light_sky_contribution = 0.0
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment.tonemap_exposure = 1.0
	environment.tonemap_white = 6.0
	environment.adjustment_enabled = true
	environment.adjustment_brightness = 1.0
	environment.adjustment_contrast = 1.045
	environment.adjustment_saturation = 0.97
	environment.fog_enabled = true
	environment.fog_light_color = Color("c2d0d3")
	environment.fog_light_energy = 0.55
	environment.fog_density = 0.0018
	environment.fog_sky_affect = 0.06
	world_environment.environment = environment
	return world_environment

static func make_sun() -> DirectionalLight3D:
	var sun := DirectionalLight3D.new()
	sun.name = "Eftermiddagssol"
	sun.rotation_degrees = Vector3(-37.0, -42.0, 0.0)
	sun.light_color = Color("fff0d8")
	sun.light_energy = 1.35
	sun.light_angular_distance = 0.8
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = 100.0
	sun.directional_shadow_fade_start = 0.85
	sun.shadow_bias = 0.03
	sun.shadow_normal_bias = 1.0
	sun.light_bake_mode = Light3D.BAKE_DYNAMIC
	return sun

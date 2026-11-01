extends RefCounted

## Valbara konstnärliga dags-/kvällsprofiler, inte en astronomisk solmodell.
## Samma värld och realtids-GI; gatlyktor hanteras av street_lights.gd.

static func make_environment(mode := "day") -> WorldEnvironment:
	var world_environment := WorldEnvironment.new()
	world_environment.name = "Dagsljus"
	var environment := Environment.new()
	environment.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	sky.radiance_size = Sky.RADIANCE_SIZE_512
	var sky_material := PanoramaSkyMaterial.new()
	sky_material.panorama = load("res://assets/sky.hdr")
	sky.sky_material = sky_material
	environment.sky = sky
	environment.background_energy_multiplier = 1.0
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	environment.ambient_light_energy = 0.6
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	# Realtids-GI över hela byn
	environment.sdfgi_enabled = true
	environment.sdfgi_use_occlusion = true
	environment.sdfgi_cascades = 6
	environment.sdfgi_min_cell_size = 0.2
	environment.sdfgi_y_scale = Environment.SDFGI_Y_SCALE_75_PERCENT
	environment.sdfgi_energy = 0.9
	environment.sdfgi_bounce_feedback = 0.5
	# Kontaktskuggor och färgad studs
	environment.ssao_enabled = true
	environment.ssao_radius = 1.6
	environment.ssao_intensity = 1.8
	environment.ssao_power = 1.4
	environment.ssil_enabled = true
	environment.ssil_intensity = 0.6
	environment.ssr_enabled = false
	# Glöd runt ljusa ytor, filmisk kurva
	environment.glow_enabled = true
	environment.glow_intensity = 0.55
	environment.glow_bloom = 0.04
	environment.glow_hdr_threshold = 1.1
	environment.tonemap_mode = Environment.TONE_MAPPER_AGX
	environment.tonemap_exposure = 1.0
	environment.adjustment_enabled = true
	environment.adjustment_contrast = 1.1
	environment.adjustment_saturation = 1.04
	# Dis på håll + lätt volymetrisk dimma (synliga solstrålar i åravinen)
	environment.fog_enabled = true
	environment.fog_light_color = Color("b9c8d0")
	environment.fog_density = 0.00045
	environment.fog_sky_affect = 0.15
	environment.fog_aerial_perspective = 0.2
	environment.volumetric_fog_enabled = true
	environment.volumetric_fog_density = 0.0022
	environment.volumetric_fog_albedo = Color("e8eef2")
	environment.volumetric_fog_length = 96.0
	environment.volumetric_fog_anisotropy = 0.45
	if mode == "evening":
		world_environment.name = "Kvällsljus"
		var dusk := ProceduralSkyMaterial.new()
		dusk.sky_top_color = Color("7588ac")
		dusk.sky_horizon_color = Color("e4b79c")
		dusk.ground_bottom_color = Color("28332f")
		dusk.ground_horizon_color = Color("b19c89")
		dusk.sky_curve = 0.18
		dusk.ground_curve = 0.25
		dusk.sky_energy_multiplier = 1.25
		dusk.ground_energy_multiplier = 0.65
		dusk.sun_angle_max = 8.0
		dusk.sun_curve = 0.08
		sky.sky_material = dusk
		environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		environment.ambient_light_color = Color("b8c3d8")
		environment.ambient_light_sky_contribution = 0.15
		# SDFGI takes outdoor fill from the sky radiance, not this ambient knob.
		# Keep the sky bright enough for shaded stairs; COLOR is the low-quality fallback.
		environment.ambient_light_energy = ambient_energy(mode, false)
		environment.ssao_intensity = 1.35
		environment.ssao_power = 1.2
		environment.glow_intensity = 0.42
		environment.glow_bloom = 0.025
		environment.glow_hdr_threshold = 1.35
		environment.adjustment_contrast = 1.06
		environment.adjustment_saturation = 0.98
		environment.fog_light_color = Color("7c879c")
		environment.fog_density = 0.00035
		environment.fog_sky_affect = 0.08
		environment.volumetric_fog_density = 0.0012
		environment.volumetric_fog_albedo = Color("9ca4b4")
		environment.volumetric_fog_anisotropy = 0.25
	world_environment.environment = environment
	return world_environment

static func make_sun(mode := "day") -> DirectionalLight3D:
	var sun := DirectionalLight3D.new()
	sun.name = "Eftermiddagssol"
	sun.rotation_degrees = Vector3(-34.0, -42.0, 0.0)
	sun.light_color = Color("fff0d8")
	sun.light_energy = 1.6
	sun.light_angular_distance = 0.6
	sun.light_volumetric_fog_energy = 1.2
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	sun.directional_shadow_max_distance = 280.0
	sun.directional_shadow_split_1 = 0.06
	sun.directional_shadow_split_2 = 0.16
	sun.directional_shadow_split_3 = 0.42
	sun.directional_shadow_blend_splits = true
	sun.directional_shadow_fade_start = 0.85
	sun.shadow_bias = 0.04
	sun.shadow_normal_bias = 1.2
	sun.light_bake_mode = Light3D.BAKE_DYNAMIC
	if mode == "evening":
		sun.name = "Kvällssol"
		sun.rotation_degrees = Vector3(-12.0, -68.0, 0.0)
		sun.light_color = Color("ffd0a0")
		sun.light_energy = 1.1
		sun.light_volumetric_fog_energy = 0.5
	return sun

static func ambient_energy(mode: String, low: bool) -> float:
	if mode == "evening":
		return 0.7 if low else 0.6
	return 0.9 if low else 0.6

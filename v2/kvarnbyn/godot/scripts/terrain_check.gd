extends RefCounted
## Checks the actual imported world; usable by the editor and exported game.
var checks: Array = []

func check(label: String, passed: bool, detail = {}) -> void:
	checks.append({"label": label, "passed": passed, "detail": detail})

func run(scene: Node3D, metadata: Dictionary) -> Dictionary:
	checks.clear()
	var terrain_count := 0
	var far_count := 0
	var invalid := 0
	var low := 1.0
	var high := 0.0
	var blend_vertices := 0
	var colors_count := 0
	var palette_ok := true
	for node in scene.find_children("*", "MeshInstance3D", true, false):
		var mi := node as MeshInstance3D
		if not (str(mi.name).begins_with("Terrain") or str(mi.name).begins_with("FarTerrain")):
			continue
		terrain_count += 1
		if str(mi.name).begins_with("FarTerrain"):
			far_count += 1
		var material := mi.material_override as ShaderMaterial
		if material == null or material.shader == null:
			invalid += 1
			continue
		for key in ["rock_albedo", "rock_normal", "grass_albedo"]:
			palette_ok = palette_ok and material.get_shader_parameter(key) is Texture2D
		for surface in range(mi.mesh.get_surface_count()):
			var colors: PackedColorArray = mi.mesh.surface_get_arrays(surface)[Mesh.ARRAY_COLOR]
			colors_count += colors.size()
			for color in colors:
				low = minf(low, color.r)
				high = maxf(high, color.r)
				if color.r > 0.15 and color.r < 0.85:
					blend_vertices += 1
	check("both core and backdrop use terrain cover", terrain_count > 100 and far_count > 0 and invalid == 0, {"total": terrain_count, "far": far_count, "invalid": invalid})
	check("real rock/normal/grass textures survived GLB import", palette_ok)
	check("rock and green areas both present", low < 0.01 and high > 0.99, {"min": low, "max": high})
	check("continuous blend data survived GLB import", colors_count > 100000 and blend_vertices > 10000, {"vertices": colors_count, "blended": blend_vertices})
	var profiles: Array = metadata.get("mapped_wall_profiles", [])
	var rays := 0
	var hits := 0
	var bounds_ok := true
	# A retaining wall is intentionally buried on its upper side. Isolate the
	# wall bodies for the two-sided mesh check, then use the whole-world walking
	# and grappling checks for regressions on real routes.
	var other_bodies: Array[RID] = []
	for body in scene.find_children("*", "StaticBody3D", true, false):
		if not "COL_Mapped_stone_wall" in str(body.get_parent().name):
			other_bodies.append(body.get_rid())
	for profile in profiles:
		var sections: Array = profile["sections"]
		for index in range(sections.size() - 1):
			var a: Array = sections[index]
			var b: Array = sections[index + 1]
			bounds_ok = bounds_ok and float(a[3]) - float(a[2]) <= 1.751
			var mid := Vector3((a[0]+b[0])*.5, (a[3]+b[3])*.5-.2, (a[1]+b[1])*.5)
			var across := Vector3(-(b[1]-a[1]), 0, b[0]-a[0]).normalized()
			for sign_value in [-1.0, 1.0]:
				rays += 1
				var query := PhysicsRayQueryParameters3D.create(mid + across * sign_value * 0.8, mid - across * sign_value * 0.8, 1)
				query.exclude = other_bodies
				var hit := scene.get_world_3d().direct_space_state.intersect_ray(query)
				if not hit.is_empty() and "COL_Mapped_stone_wall" in str(hit.collider.get_parent().name):
					hits += 1
	check("two mapped wall lines exist", profiles.size() == 22)
	check("estimated walls remain low", bounds_ok)
	check("all wall sections block rays from both sides", rays > 200 and hits == rays, {"rays": rays, "hits": hits})
	var passed := true
	for result in checks:
		passed = passed and result["passed"]
	var report := {"passed": passed, "checks": checks, "release": not OS.is_debug_build()}
	return report

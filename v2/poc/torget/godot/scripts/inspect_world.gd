extends SceneTree

var report := {"meshes": 0, "static_meshes": 0, "surfaces": 0, "surfaces_uv2": 0,
	"collision_bodies": 0, "visible_collision_meshes": 0, "missing_uv2": [], "mesh_ids": {}}

func _initialize() -> void:
	var world: Node = load("res://assets/world.glb").instantiate()
	root.add_child(world)
	inspect(world)
	print("KVARNBYN_WORLD_INSPECT ", JSON.stringify(report))
	quit()

func inspect(node: Node) -> void:
	if node is MeshInstance3D:
		if "Broadleaf" in str(node.name) or str(node.name).begins_with("COL_"):
			report.mesh_ids[node.mesh.resource_name] = str(node.mesh.get_meta("import_id", ""))
		report.meshes += 1
		if node.gi_mode == GeometryInstance3D.GI_MODE_STATIC:
			report.static_meshes += 1
		if str(node.name).to_upper().begins_with("COL_") and node.visible:
			report.visible_collision_meshes += 1
		for surface in range(node.mesh.get_surface_count()):
			report.surfaces += 1
			if node.mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_TEX_UV2:
				report.surfaces_uv2 += 1
			elif node.gi_mode == GeometryInstance3D.GI_MODE_STATIC:
				report.missing_uv2.append(str(node.name))
	if node is StaticBody3D:
		report.collision_bodies += 1
	for child in node.get_children():
		inspect(child)

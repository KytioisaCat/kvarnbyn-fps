@tool
extends EditorScenePostImport

func _post_import(scene: Node) -> Object:
	prepare_node(scene, false, scene)
	instance_trees(scene)
	return scene

## Träden (länkade kopior i Blender) blir MultiMeshInstance3D per 100 m-ruta och mesh:
## ett ritanrop per ruta i stället för ett per träd, och rutor bortom 320 m ritas inte.
func instance_trees(scene: Node) -> void:
	var groups := {}
	var doomed: Array[Node] = []
	for node in scene.find_children("*", "MeshInstance3D", true, false):
		var mi := node as MeshInstance3D
		if mi.mesh == null or not ("broadleaf" in str(mi.mesh.resource_name).to_lower() or "broadleaf" in str(mi.name).to_lower()):
			continue
		var xf: Transform3D = mi.global_transform if mi.is_inside_tree() else _accumulated(mi, scene)
		var key := "%d_%d|%s" % [int(floor(xf.origin.x / 100.0)), int(floor(xf.origin.z / 100.0)), mi.mesh.resource_name]
		if not groups.has(key):
			groups[key] = {"mesh": mi.mesh, "xf": []}
		groups[key]["xf"].append(xf)
		var root: Node = mi
		while root.get_parent() != scene and root.get_parent() != null:
			root = root.get_parent()
		if root not in doomed:
			doomed.append(root)
	var holder := Node3D.new()
	holder.name = "Trad"
	scene.add_child(holder)
	holder.owner = scene
	for key in groups.keys():
		var g: Dictionary = groups[key]
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = g["mesh"]
		mm.instance_count = g["xf"].size()
		for i in range(mm.instance_count):
			mm.set_instance_transform(i, g["xf"][i])
		var mmi := MultiMeshInstance3D.new()
		mmi.name = "Trad_" + str(key).replace("|", "_")
		mmi.multimesh = mm
		mmi.gi_mode = GeometryInstance3D.GI_MODE_DYNAMIC
		mmi.visibility_range_end = 320.0
		mmi.visibility_range_end_margin = 30.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		holder.add_child(mmi)
		mmi.owner = scene
	for root in doomed:
		root.get_parent().remove_child(root)
		root.queue_free()
	print("KVARNBYN_TREES ", groups.size(), " grupper")

func _accumulated(node: Node3D, scene: Node) -> Transform3D:
	var xf := node.transform
	var p := node.get_parent()
	while p != null and p != scene:
		if p is Node3D:
			xf = (p as Node3D).transform * xf
		p = p.get_parent()
	return xf

func prepare_node(node: Node, collision_parent: bool, scene_root: Node) -> void:
	var is_collision := collision_parent or str(node.name).to_upper().begins_with("COL_")
	if node is MeshInstance3D:
		var mesh_instance := node as MeshInstance3D
		if is_collision:
			node.visible = false
			node.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
			node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			if mesh_instance.mesh != null:
				var shape: ConcavePolygonShape3D = mesh_instance.mesh.create_trimesh_shape()
				if shape != null:
					shape.backface_collision = true
					var body := StaticBody3D.new()
					body.name = "Gångyta"
					body.collision_layer = 1
					body.collision_mask = 2
					var collider := CollisionShape3D.new()
					collider.shape = shape
					node.add_child(body)
					body.owner = scene_root
					body.add_child(collider)
					collider.owner = scene_root
		else:
			var node_name := str(node.name).to_lower()
			if node_name.begins_with("far"):
				node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			if "broadleaf" in node_name or node_name.ends_with("_boards") or "_boards_" in node_name:
				node.gi_mode = GeometryInstance3D.GI_MODE_DYNAMIC
			else:
				node.gi_mode = GeometryInstance3D.GI_MODE_STATIC
				if node_name.begins_with("krakan_") or node_name.begins_with("w92332103") or node_name.begins_with("w92332122"):
					pass  # (ljuskartor används inte i datorversionen)
	if node is Camera3D:
		node.current = false
	if node is Light3D:
		# Runtime and bake use lighting.gd rather than Blender's preview lights.
		node.visible = false
	for child in node.get_children():
		prepare_node(child, is_collision, scene_root)

@tool
extends EditorScenePostImport

func _post_import(scene: Node) -> Object:
	prepare_node(scene, false, scene)
	return scene

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
			if "broadleaf" in node_name:
				node.gi_mode = GeometryInstance3D.GI_MODE_DYNAMIC
			else:
				node.gi_mode = GeometryInstance3D.GI_MODE_STATIC
				if node_name.begins_with("krakan_") or node_name.begins_with("w92332103") or node_name.begins_with("w92332122"):
					node.lightmap_texel_scale = 2.0
	if node is Camera3D:
		node.current = false
	if node is Light3D:
		# Runtime and bake use lighting.gd rather than Blender's preview lights.
		node.visible = false
	for child in node.get_children():
		prepare_node(child, is_collision, scene_root)

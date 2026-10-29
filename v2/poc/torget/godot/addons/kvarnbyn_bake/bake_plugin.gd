@tool
extends EditorPlugin

## LightmapGI.bake is not exposed to GDScript. This opt-in editor helper selects
## the authored LightmapGI and presses the editor's own Bake Lightmaps button.
## No user project is touched unless --bake-kvarnbyn is explicitly supplied.

func _enter_tree() -> void:
	if "--bake-kvarnbyn" in OS.get_cmdline_user_args():
		call_deferred("bake_scene")

func bake_scene() -> void:
	for frame in range(15):
		await get_tree().process_frame
	EditorInterface.open_scene_from_path("res://assets/baked_world.tscn")
	for frame in range(30):
		await get_tree().process_frame
	var scene := EditorInterface.get_edited_scene_root()
	if scene == null:
		finish(false, "Den förberedda scenen kunde inte öppnas.")
		return
	var lightmap := scene.get_node_or_null("BakatLjus") as LightmapGI
	if lightmap == null:
		finish(false, "Scenen saknar BakatLjus.")
		return
	EditorInterface.get_selection().clear()
	EditorInterface.get_selection().add_node(lightmap)
	EditorInterface.edit_node(lightmap)
	for frame in range(30):
		await get_tree().process_frame
	var bake_button: Button
	for button in EditorInterface.get_base_control().find_children("*", "Button", true, false):
		var label := str(button.text).to_lower()
		if "bake lightmap" in label or "baka ljuskart" in label:
			bake_button = button
			break
	if bake_button == null:
		finish(false, "Editorns knapp Bake Lightmaps hittades inte. Välj BakatLjus och baka manuellt.")
		return
	print("KVARNBYN_BAKE_START")
	bake_button.pressed.emit()
	for frame in range(10):
		await get_tree().process_frame
	var users := lightmap.light_data.get_user_count() if lightmap.light_data != null else 0
	if users > 0:
		EditorInterface.save_scene()
		finish(true, "%d modeller har bakat ljus." % users)
	else:
		finish(false, "Bakningen gav ingen användbar ljusdata; se editorns felmeddelande.")

func finish(success: bool, message: String) -> void:
	var report := {"success": success, "message": message, "godot": Engine.get_version_info().string,
		"renderer": RenderingServer.get_current_rendering_method(),
		"time": Time.get_datetime_string_from_system(true)}
	var file := FileAccess.open("res://assets/bake_report.json", FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(report, "\t") + "\n")
	print("KVARNBYN_BAKE_RESULT ", JSON.stringify(report))
	for frame in range(5):
		await get_tree().process_frame
	get_tree().quit(0 if success else 2)

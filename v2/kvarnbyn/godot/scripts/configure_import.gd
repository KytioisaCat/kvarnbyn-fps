extends SceneTree

## Körs efter första --import; därefter --import igen så att importskriptet (träd, kollision) körs.
func _initialize() -> void:
	var configuration := ConfigFile.new()
	var path := "res://assets/world.glb.import"
	var error := configuration.load(path)
	if error != OK:
		push_error("Importera assets/world.glb en gång innan configure_import.gd körs.")
		quit(2)
		return
	configuration.set_value("params", "meshes/light_baking", 1)  # statisk: bidrar till SDFGI, ingen UV2
	configuration.set_value("params", "meshes/generate_lods", true)
	configuration.set_value("params", "meshes/create_shadow_meshes", true)
	configuration.set_value("params", "import_script/path", "res://scripts/import_world.gd")
	configuration.set_value("params", "animation/import", false)
	error = configuration.save(path)
	print("KVARNBYN_IMPORT_CONFIG ", error)
	quit(error)

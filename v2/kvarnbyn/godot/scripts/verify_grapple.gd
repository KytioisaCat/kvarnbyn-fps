extends SceneTree

const Check = preload("res://scripts/grapple_check.gd")

func _initialize() -> void:
	AudioServer.set_bus_mute(0, true)
	call_deferred("verify")

func verify() -> void:
	var check_node := Check.new()
	root.add_child(check_node)
	var hz := 60
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--test-hz="):
			hz = int(argument.get_slice("=", 1))
	var result: Dictionary = await check_node.run(hz)
	print("KVARNBYN_GRAPPLE_CHECK ", JSON.stringify(result))
	check_node.queue_free()
	await process_frame
	quit(0 if result.passed else 3)

extends Node3D

const Person = preload("res://scripts/civilian.gd")
const Roster = preload("res://scripts/civilian_roster.gd")
var world: Node3D
var player: CharacterBody3D
var people: Array = []
var focused: CharacterBody3D
var hint: Label
var card: PanelContainer
var speaker: Label
var line: Label
var card_left := 0.0
var talk_cooldown := 0.0

func setup(owner_world: Node3D) -> void:
	world = owner_world
	player = world.player
	process_mode = Node.PROCESS_MODE_ALWAYS # UI must also hide when the game is paused.
	make_ui()
	for entry in Roster.PEOPLE:
		var person := Person.new()
		person.configure(entry, self)
		add_child(person)
		person.accidental_shot.connect(warn_civilian)
		people.append(person)

func settle() -> void:
	for person in people:
		var location: Vector3 = person.data.home
		var ground := get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(location + Vector3.UP * 100, location + Vector3.DOWN * 150, 1))
		if not ground.is_empty(): location.y = ground.position.y
		person.place(location)
		var view_position := approach_position(person)
		person.face_point(view_position, 1.0)
		world.metadata.views.append({"id": "civilian-" + str(person.data.id), "name": "Gamla torget – " + str(person.data.name), "position": [view_position.x, view_position.y + 1.65, view_position.z], "target": [location.x, location.y + 1.40, location.z], "snap_to_ground": false})
		world.overlay.view_selector.add_item("Gamla torget – " + str(person.data.name))

func approach_position(person: CharacterBody3D) -> Vector3:
	# Check actual collision geometry: tree trunks/planters also matter here.
	for i in range(12):
		var angle := i * TAU / 12.0
		var candidate := person.global_position + Vector3(sin(angle), 0, cos(angle)) * 2.8
		candidate = world.ground_position(candidate)
		if absf(candidate.y - person.global_position.y) > 0.35: continue
		var query := PhysicsRayQueryParameters3D.create(candidate + Vector3.UP * 1.65, person.global_position + Vector3.UP * 1.25, 1)
		if get_world_3d().direct_space_state.intersect_ray(query).is_empty(): return candidate
	return person.global_position + Vector3(0, 0, 2.8)

func is_live() -> bool:
	return world.started and player.active and not player.input_suspended and player.alive and not get_tree().paused

func make_ui() -> void:
	var root := Control.new()
	root.name = "Civila"
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	world.canvas_layer.add_child(root)
	hint = Label.new()
	hint.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	hint.offset_left = -250
	hint.offset_right = 250
	hint.offset_top = 42
	hint.offset_bottom = 100
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_font_size_override("font_size", 20)
	hint.add_theme_color_override("font_color", Color("e0e8d9"))
	hint.add_theme_color_override("font_shadow_color", Color.BLACK)
	hint.add_theme_constant_override("shadow_offset_x", 2)
	hint.add_theme_constant_override("shadow_offset_y", 2)
	root.add_child(hint)
	card = PanelContainer.new()
	card.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	card.offset_left = -330
	card.offset_right = 330
	card.offset_top = -210
	card.offset_bottom = -84
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.055, 0.075, 0.075, 0.96)
	style.border_color = Color("9eae97")
	style.set_border_width_all(1)
	style.set_corner_radius_all(8)
	style.content_margin_left = 22
	style.content_margin_right = 22
	style.content_margin_top = 16
	style.content_margin_bottom = 16
	card.add_theme_stylebox_override("panel", style)
	root.add_child(card)
	var column := VBoxContainer.new()
	card.add_child(column)
	speaker = Label.new()
	speaker.add_theme_font_size_override("font_size", 21)
	speaker.add_theme_color_override("font_color", Color("b9cbb0"))
	column.add_child(speaker)
	line = Label.new()
	line.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	line.custom_minimum_size.x = 610
	line.add_theme_font_size_override("font_size", 20)
	column.add_child(line)
	card.hide()
	hint.hide()

func find_focused() -> CharacterBody3D:
	var camera: Camera3D = player.camera
	var from := camera.global_position
	var query := PhysicsRayQueryParameters3D.create(from, from - camera.global_basis.z * 5.5, 1 | 8)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if not hit.is_empty() and hit.collider.is_in_group("civilians"):
		return hit.collider
	return null

func _process(delta: float) -> void:
	if not is_live():
		hint.hide()
		card.hide()
		card_left = 0.0
		focused = null
		world.overlay.civilian_focus = false
		return
	talk_cooldown = maxf(0.0, talk_cooldown - delta)
	card_left = maxf(0.0, card_left - delta)
	card.visible = card_left > 0.0
	focused = find_focused()
	world.overlay.civilian_focus = focused != null
	hint.visible = focused != null
	if focused:
		hint.text = str(focused.data.name) + " · Civil"
		if player.global_position.distance_to(focused.global_position) < 3.8:
			hint.text += "\n[E] Prata"

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.physical_keycode == KEY_E:
		if try_talk(): get_viewport().set_input_as_handled()

func try_talk() -> bool:
	if not is_live() or talk_cooldown > 0.0: return false
	focused = find_focused()
	if focused == null or player.global_position.distance_to(focused.global_position) >= 3.8: return false
	speaker.text = str(focused.data.name)
	line.text = focused.talk()
	card_left = 5.0
	card.show()
	talk_cooldown = 0.6
	return true

func warn_civilian(person: CharacterBody3D) -> void:
	speaker.text = str(person.data.name) + " · Civil"
	line.text = "Se upp! Civila ska skyddas."
	card_left = 4.0
	card.show()

func snapshot() -> Array:
	var result: Array = []
	for person in people: result.append(person.snapshot())
	return result

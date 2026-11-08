extends PanelContainer

signal closed
signal resume_requested

const Settings = preload("res://scripts/movement_settings.gd")
var settings: RefCounted
var rows: Dictionary = {}
var tabs: TabContainer
var status: Label
var speed_toggle: CheckButton
var save_timer: Timer
var reset_button: Button
var resume_button: Button

func label(text: String, size := 16, colour := Color("f1f0e8")) -> Label:
	var result := Label.new()
	result.text = text
	result.add_theme_font_size_override("font_size", size)
	result.add_theme_color_override("font_color", colour)
	result.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return result

func button(text: String, action: Callable) -> Button:
	var result := Button.new()
	result.text = text
	result.custom_minimum_size.y = 44
	result.pressed.connect(action)
	return result

func configure(value: RefCounted) -> void:
	settings = value
	process_mode = Node.PROCESS_MODE_ALWAYS
	mouse_filter = Control.MOUSE_FILTER_STOP
	var style := StyleBoxFlat.new()
	style.bg_color = Color("122b29")
	style.border_color = Color("53685b")
	style.set_border_width_all(1)
	style.set_corner_radius_all(12)
	style.set_content_margin_all(24)
	add_theme_stylebox_override("panel", style)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 12)
	add_child(column)
	column.add_child(label("Rörelse & gripkrok", 30, Color("dac28b")))
	var introduction := label("Ändra ett värde, tryck Esc och provspela. Dina värden sparas automatiskt på den här datorn.", 16, Color("c1d0c7"))
	introduction.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(introduction)
	tabs = TabContainer.new()
	tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(tabs)
	for group in ["Gripkrok", "Efter släpp", "Gång & hopp", "Raket"]:
		var scroll := ScrollContainer.new()
		scroll.name = group
		scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
		scroll.follow_focus = true
		tabs.add_child(scroll)
		var content := VBoxContainer.new()
		content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		content.add_theme_constant_override("separation", 18)
		scroll.add_child(content)
		for definition in Settings.DEFINITIONS:
			if definition.group == group:
				build_row(content, definition)
	speed_toggle = CheckButton.new()
	speed_toggle.text = "Visa fartmätare under spel"
	speed_toggle.button_pressed = settings.show_speed
	speed_toggle.toggled.connect(func(enabled: bool): settings.show_speed = enabled; schedule_save())
	column.add_child(speed_toggle)
	status = label("Gäller direkt. Rulla i listan för fler reglage.", 14, Color("afc2b8"))
	column.add_child(status)
	var actions := HBoxContainer.new()
	actions.add_theme_constant_override("separation", 10)
	column.add_child(actions)
	reset_button = button("Återställ standard", func(): settings.reset_defaults(); sync_all(); schedule_save())
	actions.add_child(reset_button)
	actions.add_child(button("Kopiera värden", func(): DisplayServer.clipboard_set(settings.share_text()); status.text = "Kopierat. Klistra in värdena i chatten för att dela dem."))
	actions.add_child(button("Övriga inställningar", func(): flush_save(); closed.emit()))
	resume_button = button("Fortsätt spela", func(): flush_save(); resume_requested.emit())
	resume_button.add_theme_color_override("font_color", Color("dac28b"))
	column.add_child(resume_button)
	save_timer = Timer.new()
	save_timer.one_shot = true
	save_timer.wait_time = 0.35
	save_timer.timeout.connect(func(): flush_save(false))
	add_child(save_timer)
	settings.changed.connect(func(key: String, _number: float): sync_row(key); schedule_save())
	visible = false

func build_row(parent: VBoxContainer, definition: Dictionary) -> void:
	var row := VBoxContainer.new()
	row.add_theme_constant_override("separation", 5)
	parent.add_child(row)
	var heading := HBoxContainer.new()
	row.add_child(heading)
	var title := label(definition.label, 18)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	heading.add_child(title)
	var number_row := HBoxContainer.new()
	heading.add_child(number_row)
	var exact := LineEdit.new()
	exact.custom_minimum_size = Vector2(105, 36)
	exact.alignment = HORIZONTAL_ALIGNMENT_RIGHT
	exact.text = str(settings.get_value(definition.key))
	exact.add_theme_font_size_override("font_size", 17)
	number_row.add_child(exact)
	var unit := label(definition.unit, 15, Color("afc2b8"))
	unit.custom_minimum_size.x = 48
	unit.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	number_row.add_child(unit)
	var slider := HSlider.new()
	slider.custom_minimum_size.y = 28
	slider.min_value = definition.min
	slider.max_value = definition.max
	slider.step = definition.step
	slider.value = settings.get_value(definition.key)
	slider.tooltip_text = definition.hint
	row.add_child(slider)
	var hint := label(definition.hint, 14, Color("afc2b8"))
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	row.add_child(hint)
	rows[definition.key] = {"slider": slider, "spin": exact}
	slider.value_changed.connect(func(number: float): settings.set_value(definition.key, number))
	exact.text_submitted.connect(func(_text: String): commit_number(definition.key); schedule_save())
	exact.focus_exited.connect(func(): commit_number(definition.key); schedule_save())

func sync_row(key: String) -> void:
	if rows.has(key):
		rows[key].slider.set_value_no_signal(settings.get_value(key))
		rows[key].spin.text = str(settings.get_value(key))

func commit_number(key: String) -> void:
	var text: String = rows[key].spin.text.strip_edges().replace(",", ".")
	if text.is_valid_float():
		settings.set_value(key, text.to_float())
	sync_row(key)

func sync_all() -> void:
	for key in rows:
		sync_row(key)
	speed_toggle.set_pressed_no_signal(settings.show_speed)

func schedule_save() -> void:
	if save_timer != null:
		save_timer.start()
		status.text = "Gäller direkt. Sparar dina värden…"

func flush_save(commit_fields := true) -> void:
	if save_timer == null or settings == null:
		return
	# Esc tar med pågående text; automatisk sparning stör inte ett aktivt sifferfält.
	if commit_fields:
		for key in rows:
			commit_number(key)
	save_timer.stop()
	var error: Error = settings.save_profile()
	status.text = "Sparat på den här datorn. Esc återgår till spelet." if error == OK else "Värdena gäller nu, men kunde inte sparas till nästa start."

func fit(viewport_size: Vector2) -> void:
	var panel_size := Vector2(minf(820, viewport_size.x - 40), maxf(300, viewport_size.y - 112))
	size = panel_size
	position = (viewport_size - size) * 0.5

func snapshot() -> Dictionary:
	var controls := {}
	for key in rows:
		controls[key] = {"slider": rows[key].slider.value, "number": rows[key].spin.text.to_float()}
	return {"visible": visible, "controls": controls, "values": settings.snapshot(), "tab": tabs.current_tab}

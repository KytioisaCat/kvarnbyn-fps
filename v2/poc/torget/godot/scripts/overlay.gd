extends Control

signal begin_requested
signal pause_requested
signal reset_requested
signal view_requested(index: int)
signal jump_pressed
signal fullscreen_requested
signal quality_changed(index: int)

const INK := Color("183532")
const PAPER := Color("f1f0e8")
const BRASS := Color("b9aa80")

var touch_mode := false
var player: CharacterBody3D
var opening := true
var main_panel: PanelContainer
var title_label: Label
var description_label: Label
var instruction_label: Label
var begin_button: Button
var pause_button: Button
var view_selector: OptionButton
var status_label: Label
var fps_label: Label
var attribution_label: Label
var jump_button: Button
var touch_hint: Label
var top_bar: HBoxContainer
var reticle_visible := false
var has_started := false
var touch_hint_dismissed := false
var settings_row: HBoxContainer
var quality_selector: OptionButton
var available_views: Array = []
var status_override := ""

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var style_theme := Theme.new()
	style_theme.default_font_size = 17
	style_theme.set_color("font_color", "Label", PAPER)
	style_theme.set_color("font_color", "Button", PAPER)
	style_theme.set_color("font_hover_color", "Button", Color.WHITE)
	style_theme.set_color("font_pressed_color", "Button", INK)
	style_theme.set_color("font_focus_color", "Button", Color.WHITE)
	style_theme.set_color("font_color", "OptionButton", PAPER)
	style_theme.set_stylebox("normal", "Button", box(Color(0.08, 0.16, 0.15, 0.9), 8))
	style_theme.set_stylebox("hover", "Button", box(Color(0.15, 0.29, 0.27, 0.98), 8))
	style_theme.set_stylebox("pressed", "Button", box(BRASS, 8))
	style_theme.set_stylebox("focus", "Button", outline_box(BRASS, 8))
	style_theme.set_stylebox("normal", "OptionButton", box(Color(0.08, 0.16, 0.15, 0.9), 8))
	style_theme.set_stylebox("hover", "OptionButton", box(Color(0.15, 0.29, 0.27, 0.98), 8))
	style_theme.set_stylebox("pressed", "OptionButton", box(Color(0.15, 0.29, 0.27, 1.0), 8))
	style_theme.set_stylebox("focus", "OptionButton", outline_box(BRASS, 8))
	theme = style_theme
	build_panel()
	build_chrome()
	resized.connect(layout_controls)
	layout_controls()

func box(color: Color, radius: int) -> StyleBoxFlat:
	var result := StyleBoxFlat.new()
	result.bg_color = color
	result.set_corner_radius_all(radius)
	result.content_margin_left = 18.0
	result.content_margin_right = 18.0
	result.content_margin_top = 12.0
	result.content_margin_bottom = 12.0
	return result

func outline_box(color: Color, radius: int) -> StyleBoxFlat:
	var result := box(Color.TRANSPARENT, radius)
	result.set_border_width_all(2)
	result.border_color = color
	return result

func text_label(value: String, size_value: int, color := PAPER) -> Label:
	var result := Label.new()
	result.text = value
	result.add_theme_font_size_override("font_size", size_value)
	result.add_theme_color_override("font_color", color)
	result.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return result

func make_button(value: String, action: Callable) -> Button:
	var result := Button.new()
	result.text = value
	result.custom_minimum_size.y = 52
	result.mouse_filter = Control.MOUSE_FILTER_STOP
	result.pressed.connect(action)
	return result

func build_panel() -> void:
	main_panel = PanelContainer.new()
	var panel_style := box(Color(0.07, 0.15, 0.14, 0.94), 12)
	panel_style.content_margin_left = 28
	panel_style.content_margin_right = 28
	panel_style.content_margin_top = 26
	panel_style.content_margin_bottom = 24
	main_panel.add_theme_stylebox_override("panel", panel_style)
	main_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(main_panel)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 14)
	main_panel.add_child(column)
	title_label = text_label("Gamla torget", 43)
	column.add_child(title_label)
	description_label = text_label("Ett litet utsnitt av Kvarnbyn.\nGå runt och jämför platsen med ditt minne.", 18, Color("d0dcd5"))
	description_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(description_label)
	begin_button = make_button("Gå runt", func(): begin_requested.emit())
	begin_button.add_theme_stylebox_override("normal", box(BRASS, 8))
	begin_button.add_theme_stylebox_override("hover", box(Color("d4c69e"), 8))
	begin_button.add_theme_color_override("font_color", INK)
	begin_button.add_theme_color_override("font_hover_color", INK)
	begin_button.add_theme_font_size_override("font_size", 19)
	column.add_child(begin_button)
	instruction_label = text_label("WASD / piltangenter: gå\nMus: titta    Mellanslag: hoppa    Esc: paus", 14, Color("afc2b8"))
	column.add_child(instruction_label)
	settings_row = HBoxContainer.new()
	settings_row.add_theme_constant_override("separation", 10)
	column.add_child(settings_row)
	settings_row.add_child(make_button("Börja om", func(): reset_requested.emit()))
	settings_row.add_child(make_button("Helskärm", func(): fullscreen_requested.emit()))
	quality_selector = OptionButton.new()
	quality_selector.custom_minimum_size.y = 52
	quality_selector.add_item("Normal bild")
	quality_selector.add_item("Lägre belastning")
	quality_selector.item_selected.connect(func(index: int): quality_changed.emit(index))
	quality_selector.tooltip_text = "Sänk upplösningen om bilden hackar"
	column.add_child(quality_selector)

func build_chrome() -> void:
	top_bar = HBoxContainer.new()
	top_bar.add_theme_constant_override("separation", 8)
	add_child(top_bar)
	view_selector = OptionButton.new()
	view_selector.custom_minimum_size = Vector2(150, 50)
	view_selector.item_selected.connect(func(index: int): view_requested.emit(index))
	top_bar.add_child(view_selector)
	pause_button = make_button("Paus", func(): pause_requested.emit())
	top_bar.add_child(pause_button)
	status_label = text_label("Gamla torget", 18)
	status_label.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.8))
	status_label.add_theme_constant_override("shadow_offset_x", 1)
	status_label.add_theme_constant_override("shadow_offset_y", 2)
	add_child(status_label)
	fps_label = text_label("", 12, Color(0.95, 0.97, 0.92, 0.78))
	add_child(fps_label)
	attribution_label = text_label("", 11, Color(0.96, 0.97, 0.92, 0.88))
	attribution_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	attribution_label.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.95))
	attribution_label.add_theme_constant_override("shadow_offset_y", 1)
	add_child(attribution_label)
	jump_button = make_button("Hoppa", func(): jump_pressed.emit())
	jump_button.custom_minimum_size = Vector2(104, 68)
	add_child(jump_button)
	touch_hint = text_label("Vänster tumme: gå     Höger tumme: titta", 15, Color(0.95, 0.97, 0.92, 0.9))
	touch_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(touch_hint)

func configure(metadata: Dictionary, is_touch: bool) -> void:
	touch_mode = is_touch
	title_label.text = str(metadata.get("title", "Gamla torget"))
	status_label.text = title_label.text
	available_views = metadata.get("views", [])
	view_selector.clear()
	for view in available_views:
		view_selector.add_item(str(view.get("name", "Vy")))
	view_selector.visible = not available_views.is_empty()
	var credits: Array = metadata.get("attribution", ["Kartdata © OpenStreetMap-bidragsgivare. Höjddata: Lantmäteriet."])
	var lines := PackedStringArray()
	for credit in credits:
		lines.append(str(credit))
	attribution_label.text = "  ".join(lines)
	if touch_mode:
		instruction_label.text = "Vänster tumme: gå    Höger tumme: titta\nTryck Hoppa för att ta dig över en kant."
		title_label.add_theme_font_size_override("font_size", 36)
		attribution_label.add_theme_font_size_override("font_size", 14)
		begin_button.custom_minimum_size.y = 64
		pause_button.custom_minimum_size.y = 64
		view_selector.custom_minimum_size.y = 64
		quality_selector.custom_minimum_size.y = 64
		for button in settings_row.get_children():
			button.custom_minimum_size.y = 64
	jump_button.visible = touch_mode and not opening
	touch_hint.visible = touch_mode and not opening
	layout_controls()

func set_open(value: bool, first_time := false) -> void:
	opening = value
	if not value:
		has_started = true
	main_panel.visible = value
	begin_button.text = "Gå runt" if first_time else "Fortsätt"
	pause_button.visible = not value
	jump_button.visible = touch_mode and not value
	touch_hint.visible = touch_mode and not value and not touch_hint_dismissed
	reticle_visible = not value
	layout_controls()
	queue_redraw()

func show_error(message: String) -> void:
	description_label.text = message
	begin_button.disabled = true
	instruction_label.text = "Ladda om sidan för att försöka igen."

func layout_controls() -> void:
	if main_panel == null:
		return
	var viewport_size := get_viewport_rect().size
	var margin := 24.0
	var panel_width := minf(430.0, viewport_size.x - margin * 2.0)
	description_label.visible = not touch_mode
	instruction_label.visible = not touch_mode or not has_started
	settings_row.visible = not touch_mode or has_started
	quality_selector.visible = not touch_mode or has_started
	main_panel.reset_size()
	main_panel.size.x = panel_width
	main_panel.position = Vector2(margin, maxf(90.0, viewport_size.y - main_panel.get_combined_minimum_size().y - 66.0))
	top_bar.position = Vector2(viewport_size.x - top_bar.get_combined_minimum_size().x - margin, margin)
	status_label.position = Vector2(margin, margin + 11)
	fps_label.position = Vector2(margin, margin + 37)
	attribution_label.position = Vector2(margin, viewport_size.y - 35)
	attribution_label.size.x = viewport_size.x - 2 * margin
	jump_button.position = Vector2(viewport_size.x - 132, viewport_size.y - 132)
	touch_hint.position = Vector2(viewport_size.x * 0.5 - 220, viewport_size.y - 60)
	touch_hint.size = Vector2(440, 24)

func _process(_delta: float) -> void:
	if status_override != "":
		fps_label.text = status_override
	elif OS.is_debug_build():
		fps_label.text = "%d bilder/s" % Engine.get_frames_per_second()
	if player != null and touch_mode:
		if player.move_finger != -1 or player.look_finger != -1:
			touch_hint_dismissed = true
			touch_hint.visible = false
		queue_redraw()

func _draw() -> void:
	if reticle_visible:
		var center := size * 0.5
		draw_circle(center, 2.1, Color(0.96, 0.96, 0.91, 0.72))
	if player != null and player.move_finger != -1 and not opening:
		var radius: float = player.joystick_radius()
		var anchor: Vector2 = player.move_anchor
		var knob: Vector2 = anchor + player.touch_move * radius
		draw_circle(anchor, radius, Color(0.08, 0.18, 0.15, 0.20))
		draw_arc(anchor, radius, 0, TAU, 48, Color(0.95, 0.97, 0.90, 0.4), 2.0, true)
		draw_circle(knob, 22.0, Color(0.95, 0.97, 0.90, 0.45))

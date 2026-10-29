extends Control

## HUD för striden: hårkors som visar spridningen, träffmarkör, ammunition, hälsa, zonerna A/B/C,
## fiender kvar, meddelanden, skadevinjett med riktning, dödsskärm och slutskärm. Svenska.

signal restart_requested
signal menu_requested

var player: CharacterBody3D
var game: Node
var hit_t := 0.0
var hit_kind := "hit"
var feed_lines: Array = []
var ammo_label: Label
var reload_label: Label
var count_label: Label
var feed_box: VBoxContainer
var center_label: Label
var end_panel: PanelContainer
var end_title: Label
var end_stats: Label
var font_big := 30

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	ammo_label = _label(34, HORIZONTAL_ALIGNMENT_RIGHT)
	reload_label = _label(18, HORIZONTAL_ALIGNMENT_RIGHT)
	count_label = _label(17, HORIZONTAL_ALIGNMENT_RIGHT)
	center_label = _label(26, HORIZONTAL_ALIGNMENT_CENTER)
	feed_box = VBoxContainer.new()
	feed_box.add_theme_constant_override("separation", 2)
	feed_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(feed_box)
	end_panel = PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.05, 0.08, 0.08, 0.88)
	sb.set_corner_radius_all(10)
	sb.set_content_margin_all(28)
	end_panel.add_theme_stylebox_override("panel", sb)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 14)
	end_title = Label.new()
	end_title.add_theme_font_size_override("font_size", 46)
	end_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	end_stats = Label.new()
	end_stats.add_theme_font_size_override("font_size", 19)
	end_stats.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	var again := Button.new()
	again.text = "Spela igen"
	again.add_theme_font_size_override("font_size", 22)
	again.pressed.connect(func(): restart_requested.emit())
	v.add_child(end_title)
	v.add_child(end_stats)
	v.add_child(again)
	end_panel.add_child(v)
	end_panel.visible = false
	end_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(end_panel)

func _label(size: int, align: HorizontalAlignment) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", Color(0.96, 0.96, 0.92))
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.8))
	l.add_theme_constant_override("shadow_offset_x", 1)
	l.add_theme_constant_override("shadow_offset_y", 2)
	l.horizontal_alignment = align
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(l)
	return l

func hitmarker(kind: String) -> void:
	hit_t = 0.16 if kind == "hit" else 0.3
	hit_kind = kind

func feed(text: String) -> void:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", 17)
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.85))
	l.add_theme_constant_override("shadow_offset_y", 2)
	feed_box.add_child(l)
	feed_lines.append({"node": l, "t": 7.0})
	while feed_lines.size() > 5:
		feed_lines.pop_front()["node"].queue_free()

func show_end(won: bool) -> void:
	end_title.text = "KVARNBYN ÄR RÄDDAT!" if won else "KVARNBYN HAR FALLIT"
	end_title.add_theme_color_override("font_color", Color("7fd77f") if won else Color("ff5a5a"))
	var mins := int(game.elapsed / 60.0)
	var secs := int(game.elapsed) % 60
	end_stats.text = "%d fiender nedkämpade (%d huvudträffar) · %d gånger stupad · %d:%02d\n%s" % [game.kills, game.headshots, game.deaths, mins, secs,
		"Görjelycksgatan sover tryggt inatt." if won else "Royens trappor föll. Revansch?"]
	end_panel.visible = true

func hide_end() -> void:
	end_panel.visible = false

func _process(delta: float) -> void:
	hit_t = maxf(0.0, hit_t - delta)
	for f in feed_lines.duplicate():
		f["t"] -= delta
		(f["node"] as Label).modulate.a = clampf(f["t"], 0.0, 1.0)
		if f["t"] <= 0.0:
			f["node"].queue_free()
			feed_lines.erase(f)
	var sz := get_viewport_rect().size
	visible = player != null and player.combat_enabled
	if not visible:
		return
	var w: Node = player.weapon
	ammo_label.text = "%d / %d" % [w.mag, w.mag_size]
	ammo_label.add_theme_color_override("font_color", Color(1, 0.45, 0.4) if w.mag <= 5 else Color(0.96, 0.96, 0.92))
	ammo_label.position = Vector2(sz.x - 260, sz.y - 80)
	ammo_label.size = Vector2(220, 40)
	reload_label.text = "Laddar om…" if w.reloading else ("Ladda om [R]" if w.mag <= 5 else "")
	reload_label.position = Vector2(sz.x - 260, sz.y - 110)
	reload_label.size = Vector2(220, 24)
	count_label.text = "Fiender kvar: %d%s\nNedkämpade: %d" % [game.enemies.size(), "  (+förstärkningar)" if game.reinf_left > 0 and game.caps.any(func(c): return c["owner"] == "enemy") else "", game.kills]
	count_label.position = Vector2(sz.x - 380, 74)
	count_label.size = Vector2(360, 50)
	feed_box.position = Vector2(24, 110)
	center_label.position = Vector2(0, sz.y * 0.36)
	center_label.size = Vector2(sz.x, 40)
	center_label.text = ("Du stupade — återuppstår om %d s" % ceili(game.respawn_t)) if not player.alive and not game.over else ""
	end_panel.position = (sz - end_panel.size) / 2.0
	queue_redraw()

func _draw() -> void:
	if player == null or not player.combat_enabled:
		return
	var sz := get_viewport_rect().size
	var c := sz / 2.0
	var w: Node = player.weapon
	# skadevinjett
	var hurt: float = clampf(player.hurt_flash * 0.45 + (1.0 - player.hp / player.max_hp) * 0.3, 0.0, 0.7)
	if not player.alive:
		hurt = 0.55
	if hurt > 0.01:
		for i in range(10):
			var k := float(i) / 10.0
			var m := k * 0.18
			draw_rect(Rect2(sz * m * 0.5, sz * (1.0 - m)), Color(0.55, 0.0, 0.0, hurt * 0.09 * (1.0 - k)), false, sz.y * 0.05)
	if player.hurt_flash > 0.05:
		var rel: Vector3 = player.camera.global_transform.basis.inverse() * player.hurt_dir
		var ang := atan2(rel.x, -rel.z)
		var r := minf(sz.x, sz.y) * 0.22
		draw_arc(c, r, ang - PI / 2 - 0.35, ang - PI / 2 + 0.35, 16, Color(1, 0.15, 0.1, player.hurt_flash * 0.9), 7.0)
	if not player.alive:
		return
	# hårkors
	if w.ads < 0.6 and not w.reloading:
		var gap: float = 6.0 + w.current_spread() * 900.0 * 0.5
		var col := Color(1, 1, 1, 0.9 * (1.0 - w.ads))
		for d in [Vector2(1, 0), Vector2(-1, 0), Vector2(0, 1), Vector2(0, -1)]:
			draw_line(c + d * gap, c + d * (gap + 9.0), Color(0, 0, 0, col.a * 0.5), 4.0)
			draw_line(c + d * gap, c + d * (gap + 9.0), col, 2.0)
	else:
		draw_circle(c, 1.6, Color(1, 1, 1, 0.8))
	# träffmarkör
	if hit_t > 0.0:
		var hc := Color(1, 1, 1, hit_t * 5.0) if hit_kind == "hit" else Color(1, 0.25, 0.2, minf(1.0, hit_t * 4.0))
		var s := 10.0 if hit_kind == "hit" else 14.0
		for d in [Vector2(1, 1), Vector2(-1, 1), Vector2(1, -1), Vector2(-1, -1)]:
			draw_line(c + d * 5.0, c + d * s, hc, 2.5)
	# hälsa
	var hb := Rect2(24, sz.y - 54, 260, 14)
	draw_rect(hb, Color(0, 0, 0, 0.45))
	var frac: float = player.hp / player.max_hp
	draw_rect(Rect2(hb.position, Vector2(hb.size.x * frac, hb.size.y)), Color(0.9, 0.25, 0.2) if frac < 0.35 else Color(0.92, 0.92, 0.88))
	draw_string(get_theme_default_font(), Vector2(24, sz.y - 62), "HÄLSA %d" % int(player.hp), HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color(0.96, 0.96, 0.92))
	# zoner
	var n: int = game.caps.size()
	var pw := 150.0
	var x0 := c.x - (pw * n + 10 * (n - 1)) / 2.0
	for i in range(n):
		var cap: Dictionary = game.caps[i]
		var col := Color(0.93, 0.28, 0.25) if cap["owner"] == "enemy" else Color(0.32, 0.62, 1.0)
		if cap["contested"]:
			col = Color(1.0, 0.68, 0.25)
		var r := Rect2(x0 + i * (pw + 10), 16, pw, 40)
		draw_rect(r, Color(0.04, 0.07, 0.07, 0.72))
		draw_rect(Rect2(r.position, Vector2(6, r.size.y)), col)
		draw_string(get_theme_default_font(), r.position + Vector2(14, 18), "%s  %s" % [cap["id"], cap["name"]], HORIZONTAL_ALIGNMENT_LEFT, pw - 18, 14, Color(0.96, 0.96, 0.92))
		draw_rect(Rect2(r.position + Vector2(14, 27), Vector2(pw - 24, 5)), Color(0, 0, 0, 0.5))
		draw_rect(Rect2(r.position + Vector2(14, 27), Vector2((pw - 24) * float(cap["progress"]), 5)), Color(1.0, 0.35, 0.3) if cap["owner"] == "enemy" else Color(1.0, 0.7, 0.3))

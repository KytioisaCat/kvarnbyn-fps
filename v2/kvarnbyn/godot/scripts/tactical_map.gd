extends Control

## Own north-up cartography; input/pause belongs to world.gd.
## setup() loads the static map once. set_state() shows player, zones and allies;
## enemy positions are intentionally never requested or accepted by this API.
signal close_requested

const MINI_SIZE := Vector2(245,200)
const MINI_WIDTH_M := 190.0
const FRAME := Color("243d45")
const INK := Color("273c39")
const PAPER := Color("eff2e6")
const FRIENDLY := Color("267fa9")
const HOSTILE := Color("b84f43")

var expanded := false
var map_loaded := false
var map_data: Dictionary = {}
var map_texture: Texture2D
var world_bounds := Rect2(-357.208,-299.812,900,700)
var player_position := Vector3.ZERO
var player_yaw := 0.0
var zone_markers: Array[Dictionary] = []
var ally_markers: Array[Vector2] = []
var map_rect := Rect2()
var world_view := Rect2()
var close_button: Button
var last_update_msec := -1000
var shown_frame := 0

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	close_button = Button.new()
	close_button.text = "Stäng [M]"
	close_button.add_theme_font_size_override("font_size",17)
	close_button.mouse_filter = Control.MOUSE_FILTER_STOP
	close_button.pressed.connect(func(): close_requested.emit())
	close_button.visible = expanded
	add_child(close_button)
	resized.connect(queue_redraw)

func setup(metadata_path: String = "res://assets/map.json", texture_path: String = "res://assets/world_map.png") -> bool:
	map_loaded = false
	if not FileAccess.file_exists(metadata_path) or not ResourceLoader.exists(texture_path):
		return false
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(metadata_path))
	if not parsed is Dictionary:
		return false
	var values = parsed.get("bounds",[])
	if not values is Array or values.size() != 4:
		return false
	var candidate := Rect2(float(values[0]),float(values[1]),float(values[2])-float(values[0]),float(values[3])-float(values[1]))
	if candidate.size.x <= 0 or candidate.size.y <= 0:
		return false
	map_texture = load(texture_path) as Texture2D
	if map_texture == null:
		return false
	map_data = parsed
	world_bounds = candidate
	map_loaded = true
	queue_redraw()
	return true

func set_state(position_world: Vector3, yaw: float, caps: Array, allies: Array = []) -> void:
	player_position = position_world
	player_yaw = yaw
	# A small tactical map needs current bearings, not a full 60Hz world copy.
	var now := Time.get_ticks_msec()
	if now-last_update_msec < 75:
		return
	last_update_msec = now
	zone_markers.clear()
	for value in caps:
		if not value is Dictionary:
			continue
		var pos = value.get("pos",Vector3.ZERO)
		if not pos is Vector3:
			continue
		zone_markers.append({"id":str(value.get("id","?")),"name":str(value.get("name","")),
			"position":Vector2(pos.x,pos.z),"owner":str(value.get("owner","enemy")),
			"radius":float(value.get("radius",15.0)),"contested":bool(value.get("contested",false))})
	ally_markers.clear()
	for ally in allies:
		if not is_instance_valid(ally) or not ally is Node3D:
			continue
		if not bool(ally.get("alive")):
			continue
		var pos: Vector3 = ally.global_position
		ally_markers.append(Vector2(pos.x,pos.z))
	queue_redraw()

func set_expanded(value: bool) -> void:
	expanded = value
	mouse_filter = Control.MOUSE_FILTER_STOP if value else Control.MOUSE_FILTER_IGNORE
	if close_button != null:
		close_button.visible = value
	last_update_msec = -1000
	queue_redraw()

func heading_vector(yaw: float) -> Vector2:
	return Vector2(-sin(yaw),-cos(yaw))

func world_to_uv(point: Vector2) -> Vector2:
	return (point-world_bounds.position)/world_bounds.size

func project_world(point: Vector2, view: Rect2, destination: Rect2) -> Vector2:
	return destination.position+(point-view.position)/view.size*destination.size

func owner_color(owner: String) -> Color:
	return FRIENDLY if owner in ["ally","allies","player","friendly"] else HOSTILE if owner == "enemy" else Color("8b9987")

func snapshot() -> Dictionary:
	return {"loaded":map_loaded,"expanded":expanded,"north_up":true,
		"bounds":[world_bounds.position.x,world_bounds.position.y,world_bounds.end.x,world_bounds.end.y],
		"player":[player_position.x,player_position.z],"heading":[heading_vector(player_yaw).x,heading_vector(player_yaw).y],
		"zones":zone_markers.size(),"allies":ally_markers.size(),"enemy_positions":0,"static_map_draws":1 if map_loaded else 0,
		"map_rect":[map_rect.position.x,map_rect.position.y,map_rect.size.x,map_rect.size.y]}

func _layout() -> Rect2:
	var sz := get_viewport_rect().size
	if not expanded:
		var mini := Vector2(minf(MINI_SIZE.x,sz.x*.32),minf(MINI_SIZE.y,sz.y*.33))
		map_rect = Rect2(Vector2(22,maxf(95,sz.y-mini.y-108)),mini)
		var span := Vector2(MINI_WIDTH_M,MINI_WIDTH_M*mini.y/mini.x)
		world_view = Rect2(Vector2(player_position.x,player_position.z)-span/2,span)
		return map_rect.grow_individual(8,31,8,28)
	var maximum := Vector2(minf(1000,sz.x-70),sz.y-160)
	var map_size := Vector2(minf(maximum.x,maximum.y*world_bounds.size.x/world_bounds.size.y),0)
	map_size.y = map_size.x*world_bounds.size.y/world_bounds.size.x
	map_rect = Rect2((sz-map_size)/2+Vector2(0,8),map_size)
	world_view = world_bounds
	var board := map_rect.grow_individual(22,63,22,55)
	if close_button != null:
		close_button.position = Vector2(board.end.x-146,board.position.y+16)
		close_button.size = Vector2(128,32)
	return board

func _draw() -> void:
	if not map_loaded:
		return
	var board := _layout()
	var font := ThemeDB.fallback_font
	if expanded:
		draw_rect(get_viewport_rect(),Color(0.025,0.045,0.05,.78))
	draw_rect(board,Color(FRAME,.96))
	draw_rect(board,Color(.64,.73,.70,.6),false,1)
	if expanded:
		draw_string(font,board.position+Vector2(22,34),"Kvarnbyn",HORIZONTAL_ALIGNMENT_LEFT,-1,25,PAPER)
	else:
		draw_string(font,board.position+Vector2(8,21),"Kvarnbyn",HORIZONTAL_ALIGNMENT_LEFT,-1,16,PAPER)
	draw_rect(map_rect,Color("9ba990"))
	# Clip by geometry rather than stretching edge texels outside the world.
	var clipped := world_view.intersection(world_bounds)
	if clipped.has_area():
		var target := Rect2(project_world(clipped.position,world_view,map_rect),clipped.size/world_view.size*map_rect.size)
		var source := Rect2(world_to_uv(clipped.position)*map_texture.get_size(),clipped.size/world_bounds.size*map_texture.get_size())
		draw_texture_rect_region(map_texture,target,source)
	draw_rect(map_rect,Color(0,0,0,.3),false,1)
	if expanded:
		_draw_landmarks(font)
	_draw_zones(font)
	for point in ally_markers:
		if world_view.has_point(point):
			var p := project_world(point,world_view,map_rect)
			draw_circle(p,3.2,INK)
			draw_circle(p,2.0,Color("6dc1dc"))
	var player_xz := Vector2(player_position.x,player_position.z)
	var player_point := project_world(player_xz,world_view,map_rect)
	player_point = player_point.clamp(map_rect.position+Vector2(12,12),map_rect.end-Vector2(12,12))
	_draw_player(player_point)
	_draw_compass(font)
	if expanded:
		var baseline := board.end.y-22
		_draw_legend(font,Vector2(board.position.x+23,baseline))
		if board.size.x>660:
			draw_string(font,Vector2(board.end.x-248,baseline),"M / Esc stänger kartan",HORIZONTAL_ALIGNMENT_LEFT,-1,15,PAPER)
		draw_string(font,Vector2(board.position.x+23,board.end.y-5),"Kartdata © OpenStreetMap · Höjddata: Lantmäteriet",HORIZONTAL_ALIGNMENT_LEFT,-1,11,Color(.72,.79,.76))
	else:
		draw_string(font,Vector2(board.position.x+8,board.end.y-9),"Öppna karta [M]",HORIZONTAL_ALIGNMENT_LEFT,-1,13,PAPER)
	_draw_scale(font)
	shown_frame += 1

func _draw_player(point: Vector2) -> void:
	var forward := heading_vector(player_yaw)
	var right := Vector2(-forward.y,forward.x)
	var outline := PackedVector2Array([point+forward*12,point-forward*8+right*7,point-forward*4,point-forward*8-right*7])
	draw_colored_polygon(outline,INK)
	var arrow := PackedVector2Array([point+forward*9,point-forward*5+right*4.5,point-forward*2,point-forward*5-right*4.5])
	draw_colored_polygon(arrow,Color("ffffff"))

func _draw_zones(font: Font) -> void:
	for marker in zone_markers:
		var pos: Vector2 = marker.position
		var point := project_world(pos,world_view,map_rect)
		var outside := not world_view.has_point(pos)
		point = point.clamp(map_rect.position+Vector2(14,14),map_rect.end-Vector2(14,14))
		var colour := owner_color(marker.owner)
		if not outside:
			var radius := float(marker.radius)*map_rect.size.x/world_view.size.x
			draw_circle(point,maxf(10,radius),Color(colour,.16))
			draw_arc(point,maxf(10,radius),0,TAU,40,Color(colour,.8),1.5,true)
		draw_circle(point,10.5,INK)
		draw_circle(point,8.8,colour)
		if bool(marker.contested):draw_arc(point,12,0,TAU,32,Color("eecb68"),2,true)
		_draw_centered(font,point+Vector2(0,5),str(marker.id),14,Color.WHITE)
		if expanded:
			var label := str(marker.name)
			var w := font.get_string_size(label,HORIZONTAL_ALIGNMENT_LEFT,-1,15).x
			var x := clampf(point.x+15,map_rect.position.x+6,map_rect.end.x-w-6)
			_draw_map_text(font,Vector2(x,point.y+5),label,15)

func _draw_landmarks(font: Font) -> void:
	for landmark in map_data.get("landmarks",[]):
		var label := str(landmark.get("name",""))
		if zone_markers.any(func(c): return str(c.name).to_lower() == label.to_lower()):
			continue
		var coords = landmark.get("position",[])
		if coords.size()!=2:continue
		var p := project_world(Vector2(float(coords[0]),float(coords[1])),world_view,map_rect)
		var o = landmark.get("label_offset",[10,-10])
		var point := p+Vector2(float(o[0]),float(o[1]))
		var width := font.get_string_size(label,HORIZONTAL_ALIGNMENT_LEFT,-1,14).x
		point.x=clampf(point.x,map_rect.position.x+6,map_rect.end.x-width-6)
		point.y=clampf(point.y,map_rect.position.y+17,map_rect.end.y-6)
		draw_circle(p,2.5,INK)
		_draw_map_text(font,point,label,14)

func _draw_map_text(font: Font, point: Vector2, value: String, font_size: int) -> void:
	draw_string_outline(font,point,value,HORIZONTAL_ALIGNMENT_LEFT,-1,font_size,4,Color("e8eddf"))
	draw_string(font,point,value,HORIZONTAL_ALIGNMENT_LEFT,-1,font_size,INK)

func _draw_centered(font: Font, point: Vector2, value: String, font_size: int, colour: Color) -> void:
	var w := font.get_string_size(value,HORIZONTAL_ALIGNMENT_LEFT,-1,font_size).x
	draw_string(font,point-Vector2(w/2,0),value,HORIZONTAL_ALIGNMENT_LEFT,-1,font_size,colour)

func _draw_compass(font: Font) -> void:
	var p := map_rect.position+Vector2(map_rect.size.x-20,22)
	draw_circle(p,12,Color(FRAME,.85))
	_draw_centered(font,p+Vector2(0,5),"N",14,PAPER)
	draw_line(p+Vector2(0,-14),p+Vector2(0,-21),PAPER,2,true)

func _draw_scale(font: Font) -> void:
	var metres := 100.0 if expanded else 50.0
	var pixels := metres*map_rect.size.x/world_view.size.x
	var p := map_rect.position+Vector2(12,map_rect.size.y-12)
	draw_line(p,p+Vector2(pixels,0),INK,3,true)
	draw_line(p+Vector2(0,-4),p+Vector2(0,4),INK,2,true)
	draw_line(p+Vector2(pixels,-4),p+Vector2(pixels,4),INK,2,true)
	_draw_map_text(font,p+Vector2(0,-8),"%d m" % int(metres),11)

func _draw_legend(font: Font, point: Vector2) -> void:
	draw_circle(point+Vector2(4,-5),4,Color.WHITE)
	draw_string(font,point+Vector2(15,0),"Du",HORIZONTAL_ALIGNMENT_LEFT,-1,14,PAPER)
	draw_circle(point+Vector2(64,-5),4,FRIENDLY)
	draw_string(font,point+Vector2(75,0),"Egen zon",HORIZONTAL_ALIGNMENT_LEFT,-1,14,PAPER)
	draw_circle(point+Vector2(164,-5),4,HOSTILE)
	draw_string(font,point+Vector2(175,0),"Fiendens zon",HORIZONTAL_ALIGNMENT_LEFT,-1,14,PAPER)

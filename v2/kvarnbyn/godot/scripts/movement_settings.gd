extends RefCounted

## Ett separat värdepaket per spelare. Världen laddar Joels profil; prov använder
## egna paket och filer så att sparade speltestvärden aldrig skrivs över av tester.
signal changed(key: String, value: float)

const DEFINITIONS := [
	{"key":"reel_speed", "group":"Gripkrok", "label":"Indragningsfart", "unit":"m/s", "default":6.0, "min":1.0, "max":18.0, "step":0.25, "hint":"Hur snabbt linan vevas in. Lägre ger en lugnare färd mot fästet."},
	{"key":"pull_accel", "group":"Gripkrok", "label":"Acceleration mot fästet", "unit":"m/s²", "default":20.0, "min":2.0, "max":60.0, "step":1.0, "hint":"Hur snabbt draget bygger upp fart. Lägre ger en mjukare start."},
	{"key":"swing_accel", "group":"Gripkrok", "label":"Acceleration i sidled", "unit":"m/s²", "default":19.0, "min":0.0, "max":45.0, "step":0.5, "hint":"Hur mycket din styrning ökar farten runt fästpunkten."},
	{"key":"swing_boost", "group":"Gripkrok", "label":"Fartökning vid kortare lina", "unit":"×", "default":1.0, "min":0.0, "max":2.0, "step":0.05, "hint":"Extra svingfart när radien krymper. 0 stänger av just denna effekt."},
	{"key":"max_speed", "group":"Gripkrok", "label":"Högsta fart med krok", "unit":"m/s", "default":30.0, "min":8.0, "max":50.0, "step":0.5, "hint":"Tak för den sammanlagda hastigheten medan kroken sitter fast."},
	{"key":"reach", "group":"Gripkrok", "label":"Räckvidd", "unit":"m", "default":42.0, "min":10.0, "max":80.0, "step":1.0, "hint":"Längsta avståndet där en ny krok kan fästa."},
	{"key":"rope_stiffness", "group":"Gripkrok", "label":"Linans återhämtning", "unit":"1/s", "default":8.0, "min":0.0, "max":20.0, "step":0.5, "hint":"Hur bestämt draget tar igen slack. Högre kan ge ett ryckigare drag."},
	{"key":"rope_catchup", "group":"Gripkrok", "label":"Extra fart för att ta igen slack", "unit":"m/s", "default":4.0, "min":0.0, "max":12.0, "step":0.25, "hint":"Hur mycket snabbare än vinschen du får dras när linan släpar efter."},
	{"key":"ground_drag", "group":"Efter släpp", "label":"Inbromsning på marken", "unit":"m/s²", "default":3.5, "min":0.0, "max":20.0, "step":0.25, "hint":"Lägre betyder längre glid efter landning. 3,5 tar bort 3,5 m/s per sekund."},
	{"key":"crouch_drag", "group":"Efter släpp", "label":"Inbromsning när du hukar", "unit":"m/s²", "default":1.5, "min":0.0, "max":12.0, "step":0.25, "hint":"Broms under glid med C/Ctrl. Lägre låter dig glida längre."},
	{"key":"air_drag", "group":"Efter släpp", "label":"Luftmotstånd", "unit":"1/s", "default":0.0, "min":0.0, "max":4.0, "step":0.05, "hint":"Hur snabbt sidofarten avtar i luften efter släpp. 0 bevarar den helt."},
	{"key":"air_steer", "group":"Efter släpp", "label":"Styracceleration i luften", "unit":"m/s²", "default":9.0, "min":0.0, "max":30.0, "step":0.5, "hint":"Hur mycket WASD kan ändra din färd efter släpp."},
	{"key":"ground_steer", "group":"Efter släpp", "label":"Styracceleration på marken", "unit":"m/s²", "default":30.0, "min":0.0, "max":70.0, "step":1.0, "hint":"Hur starkt WASD påverkar rörelsen medan landningsfarten finns kvar."},
	{"key":"walk_speed", "group":"Gång & hopp", "label":"Gångfart", "unit":"m/s", "default":4.4, "min":1.0, "max":10.0, "step":0.1, "hint":"Vanlig fart utan Shift."},
	{"key":"run_speed", "group":"Gång & hopp", "label":"Sprintfart", "unit":"m/s", "default":6.9, "min":2.0, "max":15.0, "step":0.1, "hint":"Fart med Shift och framåtrörelse."},
	{"key":"crouch_speed", "group":"Gång & hopp", "label":"Fart när du hukar", "unit":"m/s", "default":2.3, "min":0.5, "max":6.0, "step":0.1, "hint":"Gångfart med C/Ctrl, efter att glidfarten klingat av."},
	{"key":"walk_response", "group":"Gång & hopp", "label":"Respons på marken", "unit":"1/s", "default":11.0, "min":1.0, "max":25.0, "step":0.5, "hint":"Hur snabbt vanlig gång närmar sig önskad fart."},
	{"key":"walk_brake", "group":"Gång & hopp", "label":"Stopp vid vanlig gång", "unit":"1/s", "default":14.0, "min":1.0, "max":30.0, "step":0.5, "hint":"Broms när du släpper WASD utan uppbyggd krokfart."},
	{"key":"air_response", "group":"Gång & hopp", "label":"Respons vid vanligt hopp", "unit":"1/s", "default":2.2, "min":0.1, "max":10.0, "step":0.1, "hint":"Luftstyrning vid ett vanligt hopp, innan någon krok har använts."},
	{"key":"jump_speed", "group":"Gång & hopp", "label":"Hoppets startfart", "unit":"m/s", "default":5.1, "min":2.0, "max":10.0, "step":0.1, "hint":"Fart uppåt när du hoppar från marken."},
	{"key":"gravity", "group":"Gång & hopp", "label":"Tyngdkraft", "unit":"m/s²", "default":16.0, "min":4.0, "max":30.0, "step":0.5, "hint":"Lägre ger längre tid i luften; högre ger tyngre fall."},
	{"key":"rocket_lift", "group":"Raket", "label":"Raketens lyftacceleration", "unit":"m/s²", "default":30.0, "min":0.0, "max":60.0, "step":1.0, "hint":"Lyft medan du håller det andra hoppet."},
	{"key":"rocket_dash", "group":"Raket", "label":"Raketens framåtfart", "unit":"m/s", "default":17.0, "min":0.0, "max":35.0, "step":0.5, "hint":"Framåtfart som raketen försöker ge. Befintlig slungfart finns kvar."},
	{"key":"rocket_fuel", "group":"Raket", "label":"Raketens brinntid", "unit":"s", "default":0.45, "min":0.05, "max":0.9, "step":0.05, "hint":"Längsta brinntid när det andra hoppet hålls inne."},
]

var values: Dictionary = {}
var storage_path := "user://movement.cfg"
var persistence_enabled := true
var show_speed := true

func _init() -> void:
	for definition in DEFINITIONS:
		values[definition.key] = float(definition.default)

func get_value(key: String) -> float:
	return float(values[key])

func set_value(key: String, value: float) -> void:
	if not is_finite(value):
		return
	for definition in DEFINITIONS:
		if definition.key == key:
			var safe := clampf(snappedf(value, float(definition.step)), float(definition.min), float(definition.max))
			if not is_equal_approx(float(values[key]), safe):
				values[key] = safe
				changed.emit(key, safe)
			return

func reset_defaults() -> void:
	for definition in DEFINITIONS:
		set_value(definition.key, float(definition.default))
	show_speed = true

func save_profile() -> Error:
	if not persistence_enabled:
		return OK
	var config := ConfigFile.new()
	for key in values:
		config.set_value("movement", key, values[key])
	config.set_value("display", "show_speed", show_speed)
	return config.save(storage_path)

func load_profile() -> void:
	var config := ConfigFile.new()
	if config.load(storage_path) != OK:
		return
	for definition in DEFINITIONS:
		var value: Variant = config.get_value("movement", definition.key, definition.default)
		if value is float or value is int:
			set_value(definition.key, float(value))
	show_speed = bool(config.get_value("display", "show_speed", true))

func share_text() -> String:
	var lines := PackedStringArray(["Kvarnbyn — rörelsevärden"])
	for definition in DEFINITIONS:
		lines.append("%s: %s %s" % [definition.label, str(get_value(definition.key)), definition.unit])
	return "\n".join(lines)

func snapshot() -> Dictionary:
	return {"values": values.duplicate(), "show_speed": show_speed}

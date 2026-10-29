extends Node3D

## Effekter med återanvända noder: spårljus, nedslag (damm/gnistor), mynningsflammor och
## 3D-ljud för andras skott. Allt kort och billigt; inga partikelsystem att kompilera.

const SFX = preload("res://scripts/sfx.gd")
var tracers: Array = []
var puffs: Array = []
var flashes: Array = []
var voices: Array = []
var _ti := 0
var _pi := 0
var _fi := 0
var _vi := 0
var tracer_mat: StandardMaterial3D
var enemy_tracer_mat: StandardMaterial3D
var dust_mat: StandardMaterial3D
var spark_mat: StandardMaterial3D
var blood_mat: StandardMaterial3D

func _ready() -> void:
	tracer_mat = _glow(Color(1.0, 0.86, 0.55), 3.0)
	enemy_tracer_mat = _glow(Color(1.0, 0.45, 0.3), 3.0)
	dust_mat = StandardMaterial3D.new()
	dust_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	dust_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	dust_mat.albedo_color = Color(0.55, 0.52, 0.47, 0.75)
	dust_mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	spark_mat = _glow(Color(1.0, 0.75, 0.35), 6.0)
	spark_mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	blood_mat = dust_mat.duplicate()
	blood_mat.albedo_color = Color(0.45, 0.05, 0.04, 0.8)
	for i in range(48):
		var t := MeshInstance3D.new()
		var m := BoxMesh.new()
		m.size = Vector3(0.025, 0.025, 1.0)
		t.mesh = m
		t.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		t.visible = false
		add_child(t)
		tracers.append({"node": t, "life": 0.0})
	for i in range(64):
		var p := MeshInstance3D.new()
		var q := QuadMesh.new()
		q.size = Vector2(0.35, 0.35)
		p.mesh = q
		p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		p.visible = false
		add_child(p)
		puffs.append({"node": p, "life": 0.0, "max": 0.5, "grow": 1.0})
	for i in range(24):
		var l := OmniLight3D.new()
		l.light_color = Color(1.0, 0.75, 0.4)
		l.omni_range = 7.0
		l.light_energy = 0.0
		l.shadow_enabled = false
		l.light_volumetric_fog_energy = 0.0
		l.visible = false
		add_child(l)
		flashes.append({"node": l, "life": 0.0})
	for i in range(16):
		var a := AudioStreamPlayer3D.new()
		a.unit_size = 18.0
		a.max_distance = 450.0
		a.attenuation_filter_cutoff_hz = 3500.0
		add_child(a)
		voices.append(a)

func _glow(c: Color, energy: float) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = c
	m.emission_enabled = true
	m.emission = c
	m.emission_energy_multiplier = energy
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	return m

func tracer(from: Vector3, to: Vector3, enemy := false) -> void:
	var length := from.distance_to(to)
	if length < 1.5:
		return
	var t: Dictionary = tracers[_ti]
	_ti = (_ti + 1) % tracers.size()
	var n: MeshInstance3D = t["node"]
	var seg := minf(length * 0.6, 14.0)
	var start := from.lerp(to, 0.15)
	n.material_override = enemy_tracer_mat if enemy else tracer_mat
	n.scale = Vector3(1, 1, seg)
	n.global_position = start + (to - from).normalized() * seg * 0.5
	n.look_at(to, Vector3.UP if absf((to - from).normalized().y) < 0.99 else Vector3.RIGHT)
	n.visible = true
	t["life"] = 0.07
	t["from"] = start
	t["dir"] = (to - from).normalized()
	t["speed"] = 520.0
	t["end"] = length

func impact(at: Vector3, normal: Vector3, kind := "dust") -> void:
	var count := 2 if kind == "blood" else 3
	for k in range(count):
		var p: Dictionary = puffs[_pi]
		_pi = (_pi + 1) % puffs.size()
		var n: MeshInstance3D = p["node"]
		n.material_override = blood_mat if kind == "blood" else (spark_mat if k == 0 and kind == "hard" else dust_mat)
		n.global_position = at + normal * (0.05 + k * 0.08) + Vector3(randf_range(-0.05, 0.05), randf_range(0, 0.08), randf_range(-0.05, 0.05))
		n.scale = Vector3.ONE * (0.25 if k == 0 and kind == "hard" else 0.5)
		n.visible = true
		p["life"] = 0.0
		p["max"] = 0.12 if (k == 0 and kind == "hard") else randf_range(0.45, 0.8)
		p["grow"] = 1.0 if (k == 0 and kind == "hard") else 2.2

func muzzle(at: Vector3, energy := 2.5) -> void:
	var f: Dictionary = flashes[_fi]
	_fi = (_fi + 1) % flashes.size()
	var l: OmniLight3D = f["node"]
	l.global_position = at
	l.light_energy = energy
	l.visible = true
	f["life"] = 0.05

func sound_at(at: Vector3, sound_name: String, volume_db := 0.0, pitch := 1.0) -> void:
	var a: AudioStreamPlayer3D = voices[_vi]
	_vi = (_vi + 1) % voices.size()
	a.stream = SFX.get_sound(sound_name)
	a.global_position = at
	a.volume_db = volume_db
	a.pitch_scale = pitch * randf_range(0.94, 1.06)
	a.play()

func _process(delta: float) -> void:
	for t in tracers:
		if t["life"] > 0.0:
			t["life"] -= delta
			var n: MeshInstance3D = t["node"]
			n.global_position += t["dir"] * t["speed"] * delta
			if t["life"] <= 0.0:
				n.visible = false
	for p in puffs:
		var n: MeshInstance3D = p["node"]
		if n.visible:
			p["life"] += delta
			var k: float = p["life"] / p["max"]
			if k >= 1.0:
				n.visible = false
			else:
				n.scale = Vector3.ONE * (0.25 + k * p["grow"] * 0.6)
				n.transparency = k
	for f in flashes:
		if f["life"] > 0.0:
			f["life"] -= delta
			if f["life"] <= 0.0:
				(f["node"] as OmniLight3D).light_energy = 0.0
				(f["node"] as OmniLight3D).visible = false

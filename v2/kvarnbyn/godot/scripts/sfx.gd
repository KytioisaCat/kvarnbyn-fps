extends RefCounted

## Procedurella ljud (inga nedladdade ljudfiler): syntetiseras som 16-bitars PCM vid start.
## Skott = brusknall med snabb avklingning + lågt dunk + kort eko; avlägsna skott lågpassas.

const RATE := 22050
static var _cache := {}

static func _wav(samples: PackedFloat32Array) -> AudioStreamWAV:
	var bytes := PackedByteArray()
	bytes.resize(samples.size() * 2)
	for i in range(samples.size()):
		bytes.encode_s16(i * 2, int(clampf(samples[i], -1.0, 1.0) * 32000.0))
	var s := AudioStreamWAV.new()
	s.format = AudioStreamWAV.FORMAT_16_BITS
	s.mix_rate = RATE
	s.stereo = false
	s.data = bytes
	return s

static func _lowpass(x: PackedFloat32Array, a: float) -> PackedFloat32Array:
	var y := 0.0
	for i in range(x.size()):
		y += a * (x[i] - y)
		x[i] = y
	return x

static func get_sound(sound_name: String) -> AudioStreamWAV:
	if _cache.has(sound_name):
		return _cache[sound_name]
	var s: AudioStreamWAV
	match sound_name:
		"shot": s = _shot(0.42, 1.0, 0.0)
		"shot_far": s = _shot(0.55, 0.6, 0.12)
		"empty": s = _click(0.035, 1800.0, 0.5)
		"mag_out": s = _clack(0.09, 520.0)
		"mag_in": s = _clack(0.12, 760.0)
		"bolt": s = _clack(0.14, 380.0)
		"hit": s = _tone(0.045, 1900.0, 0.35, 60.0)
		"head": s = _tone(0.11, 2600.0, 0.4, 25.0)
		"kill": s = _tone(0.16, 1400.0, 0.35, 18.0)
		"hurt": s = _thud(0.18)
		"step": s = _step()
		"alarm": s = _alarm()
		"good": s = _chord([523.0, 659.0, 784.0], 0.6)
		"bad": s = _chord([196.0, 233.0, 277.0], 0.9)
	_cache[sound_name] = s
	return s

static func _shot(length: float, gain: float, lowpass: float) -> AudioStreamWAV:
	var n := int(RATE * length)
	var x := PackedFloat32Array()
	x.resize(n)
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for i in range(n):
		var t := float(i) / RATE
		var crack := rng.randf_range(-1, 1) * exp(-t * 55.0)
		var body := sin(TAU * 90.0 * t * (1.0 - t * 1.6)) * exp(-t * 18.0) * 0.9
		var tail := rng.randf_range(-1, 1) * exp(-t * 7.0) * 0.22
		x[i] = (crack + body + tail) * gain
	if lowpass > 0.0:
		x = _lowpass(x, lowpass)
		for i in range(n):
			x[i] *= 3.2
	return _wav(x)

static func _click(length: float, freq: float, gain: float) -> AudioStreamWAV:
	var n := int(RATE * length)
	var x := PackedFloat32Array()
	x.resize(n)
	for i in range(n):
		var t := float(i) / RATE
		x[i] = sin(TAU * freq * t) * exp(-t * 120.0) * gain
	return _wav(x)

static func _clack(length: float, freq: float) -> AudioStreamWAV:
	var n := int(RATE * length)
	var x := PackedFloat32Array()
	x.resize(n)
	var rng := RandomNumberGenerator.new()
	rng.seed = int(freq)
	for i in range(n):
		var t := float(i) / RATE
		x[i] = (rng.randf_range(-1, 1) * 0.6 + sin(TAU * freq * t) * 0.5 + sin(TAU * freq * 2.7 * t) * 0.25) * exp(-t * 60.0) * 0.6
	return _wav(x)

static func _tone(length: float, freq: float, gain: float, decay: float) -> AudioStreamWAV:
	var n := int(RATE * length)
	var x := PackedFloat32Array()
	x.resize(n)
	for i in range(n):
		var t := float(i) / RATE
		x[i] = sin(TAU * freq * t) * exp(-t * decay) * gain
	return _wav(x)

static func _thud(length: float) -> AudioStreamWAV:
	var n := int(RATE * length)
	var x := PackedFloat32Array()
	x.resize(n)
	var rng := RandomNumberGenerator.new()
	rng.seed = 3
	for i in range(n):
		var t := float(i) / RATE
		x[i] = (sin(TAU * 70.0 * t) * 0.8 + rng.randf_range(-1, 1) * 0.3) * exp(-t * 22.0)
	return _wav(_lowpass(x, 0.2))

static func _step() -> AudioStreamWAV:
	var n := int(RATE * 0.09)
	var x := PackedFloat32Array()
	x.resize(n)
	var rng := RandomNumberGenerator.new()
	rng.seed = 11
	for i in range(n):
		var t := float(i) / RATE
		x[i] = rng.randf_range(-1, 1) * exp(-t * 45.0) * 0.35
	return _wav(_lowpass(x, 0.12))

static func _alarm() -> AudioStreamWAV:
	var n := int(RATE * 0.6)
	var x := PackedFloat32Array()
	x.resize(n)
	for i in range(n):
		var t := float(i) / RATE
		var f := 520.0 if t < 0.25 else 392.0
		x[i] = sign(sin(TAU * f * t)) * 0.18 * (1.0 - smoothstep(0.5, 0.6, t))
	return _wav(_lowpass(x, 0.3))

static func _chord(freqs: Array, length: float) -> AudioStreamWAV:
	var n := int(RATE * length)
	var x := PackedFloat32Array()
	x.resize(n)
	for i in range(n):
		var t := float(i) / RATE
		var v := 0.0
		for k in range(freqs.size()):
			v += sin(TAU * float(freqs[k]) * t) * (1.0 if t > k * 0.08 else 0.0)
		x[i] = v / freqs.size() * 0.45 * exp(-t * 2.2)
	return _wav(x)

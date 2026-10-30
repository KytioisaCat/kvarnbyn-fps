extends RefCounted

## Low-frequency decisions on the same collision geometry that carries the player.
## The navigation graph owns long routes; short combat moves must pass floor and capsule tests.

const MEMORY_S := 6.0
const MIN_FLOOR_NORMAL := 0.6157 # cos(52 degrees), same limit as the soldier capsule.

var soldier: CharacterBody3D
var move := Vector3.ZERO
var face := Vector3.ZERO
var engaging := false
var suppression := 0.0
var state := "advance"
var goal := Vector3.ZERO
var goal_active := false
var stats := {"decisions": 0, "flanks": 0, "cover_moves": 0, "search_moves": 0,
	"rejected_positions": 0, "rays": 0, "path_requests": 0, "escapes": 0,
	"blocked_shots": 0, "shots": 0, "moving_combat_s": 0.0, "combat_s": 0.0,
	"travel_m": 0.0, "far_blocked_steps": 0, "cpu_usec": 0}

var _memory_t := 0.0
var _last_seen := Vector3.ZERO
var _decision_t := 0.0
var _hold_t := 0.0
var _escape_t := 0.0
var _escape_dir := Vector3.ZERO
var _stuck_t := 0.0
var _window_position := Vector3.ZERO
var _previous_position := Vector3.ZERO
var _initialized := false
var _far_probe_t := 0.0
var _far_safe := true
var _side := 1.0

func _init(owner: CharacterBody3D) -> void:
	soldier = owner
	_decision_t = randf_range(0.1, 1.1)
	_side = 1.0 if randf() < 0.5 else -1.0

func step(delta: float) -> void:
	var start_usec := Time.get_ticks_usec()
	var s = soldier
	if not _initialized:
		_initialized = true
		_previous_position = s.global_position
		_window_position = s.global_position
	var travelled := Vector2(s.global_position.x - _previous_position.x, s.global_position.z - _previous_position.z).length()
	stats.travel_m += travelled
	_previous_position = s.global_position
	move = Vector3.ZERO
	face = Vector3.ZERO
	_memory_t = maxf(0.0, _memory_t - delta)
	suppression = maxf(0.0, suppression - delta * 0.24)
	_decision_t -= delta
	_hold_t -= delta
	var cap: Dictionary = s.game.cap_target_for(s)
	var cap_goal: Vector3 = cap.get("goal", s.global_position)
	var key := str(cap.get("id", ""))
	if key != s.path_key or s.path.is_empty():
		s.path_key = key
		s.path = s.game.nav.path(s.global_position, cap_goal)
		s.path_i = 0
		stats.path_requests += 1
	s.los_t -= delta
	if s.los_t <= 0.0:
		_scan_threat()
	var distance := INF
	if is_instance_valid(s.target) and s._target_alive(s.target):
		distance = s.global_position.distance_to(s.target.global_position)
	else:
		s.target = null
		s.can_see = false
		_memory_t = 0.0
	engaging = s.can_see and distance < float(s.cfg.get("engage_m", 70))
	var in_zone: bool = cap.has("pos") and flat_distance(s.global_position, cap["pos"]) < float(cap.get("radius", 15.0)) * 0.8
	if engaging:
		face = s.target.global_position - s.global_position
		stats.combat_s += delta
		if travelled > 0.006:
			stats.moving_combat_s += delta
		s.fire_t -= delta
		if s.fire_t <= 0.0:
			var interval: Array = s.cfg.get("fire_interval_s", [0.75, 1.35])
			var scale := float(s.cfg.get("fire_interval_scale", s.cfg.get("enemy_fire_interval_scale", 0.92) if s.team == "enemy" else 1.0))
			s.fire_t = randf_range(float(interval[0]), float(interval[1])) * scale
			s._shoot(distance, in_zone)
	if _escape_t > 0.0:
		_escape_t -= delta
		move = _escape_dir * s.speed
		state = "escape"
		if _escape_t <= 0.0:
			s.path = PackedVector3Array()
			_decision_t = 0.0
	elif engaging or _memory_t > 0.0:
		if _decision_t <= 0.0 and _hold_t <= 0.0:
			_choose_combat_goal(engaging)
		if goal_active:
			var toward: Vector3 = goal - s.global_position
			toward.y = 0.0
			if toward.length() > 0.8:
				var pace := 1.1 if state == "cover" else 0.92
				move = toward.normalized() * s.speed * pace
			else:
				goal_active = false
				_hold_t = randf_range(0.6, 1.3) if state == "cover" else randf_range(0.2, 0.6)
				_decision_t = minf(_decision_t, 0.2)
		elif not engaging and _memory_t > 0.0:
			# Search only the last observed position; do not track an unseen player through walls.
			move = _follow_path(0.85)
		elif distance > 24.0:
			move = _follow_path(0.65)
	else:
		goal_active = false
		if in_zone:
			state = "patrol"
			s.wander_t -= delta
			if s.wander_t <= 0.0:
				s.wander_t = randf_range(2.0, 4.0)
				_choose_patrol_goal(cap)
			var toward: Vector3 = s.wander_goal - s.global_position
			toward.y = 0.0
			if toward.length() > 0.9:
				move = toward.normalized() * s.speed * 0.65
		else:
			state = "advance"
			move = _follow_path(1.0)
	if face.length_squared() < 0.001 and move.length_squared() > 0.01:
		face = move
	_check_progress(delta)
	s.tactic_state = state
	s.tactic_goal = goal if goal_active else s.wander_goal if state == "patrol" else cap_goal
	stats.cpu_usec += Time.get_ticks_usec() - start_usec

func _scan_threat() -> void:
	var s = soldier
	s.los_t = randf_range(0.3, 0.55)
	var previous: Node3D = s.target
	var candidate: Node3D = s.game.nearest_hostile(s, float(s.cfg.get("sight_m", 75)))
	s.can_see = false
	if candidate != null and _visible(candidate):
		s.target = candidate
		s.can_see = true
	elif is_instance_valid(previous) and previous != candidate and s._target_alive(previous) and s.global_position.distance_to(previous.global_position) < float(s.cfg.get("sight_m", 75)) and _visible(previous):
		s.target = previous
		s.can_see = true
	if s.can_see:
		_last_seen = s.target.global_position
		_memory_t = MEMORY_S
	elif _memory_t <= 0.0:
		s.target = null

func _visible(candidate: Node3D) -> bool:
	var height := 0.9 if candidate.get("crouching") else 1.45
	return _ray_clear(soldier.global_position + Vector3.UP * 1.55, candidate.global_position + Vector3.UP * height)

func _ray_clear(from: Vector3, to: Vector3) -> bool:
	stats.rays += 1
	var query := PhysicsRayQueryParameters3D.create(from, to, 1)
	return soldier.get_world_3d().direct_space_state.intersect_ray(query).is_empty()

func _follow_path(scale: float) -> Vector3:
	var s = soldier
	while s.path_i < s.path.size():
		var offset := Vector3(s.lateral, 0.0, s.lateral * 0.5) * (0.35 if s.stuck_n == 0 else 0.1)
		if s.path_i == s.path.size() - 1:
			offset = Vector3.ZERO
		var toward: Vector3 = s.path[s.path_i] + offset - s.global_position
		toward.y = 0.0
		if toward.length() < 1.7 and s.path_i < s.path.size() - 1:
			s.path_i += 1
			continue
		return toward.normalized() * s.speed * scale if toward.length() > 0.45 else Vector3.ZERO
	return Vector3.ZERO

func _choose_combat_goal(visible: bool) -> void:
	var s = soldier
	stats.decisions += 1
	_decision_t = randf_range(2.6, 4.0)
	var threat: Vector3 = s.target.global_position if visible and is_instance_valid(s.target) else _last_seen
	var toward: Vector3 = threat - s.global_position
	toward.y = 0.0
	if toward.length_squared() < 0.01:
		return
	var forward: Vector3 = toward.normalized()
	var side := Vector3(-forward.z, 0.0, forward.x)
	var want_cover: bool = suppression > 0.42 or (s.hp < float(s.cfg.get("hp", 100)) * 0.4 and state != "cover")
	var best_score := -INF
	var best := Vector3.ZERO
	var best_covered := false
	var found := false
	for index in range(8):
		var sign_value := _side if index % 2 == 0 else -_side
		var lateral_m := 4.2 + float(index / 2) * 1.4
		var forward_m := 2.5 if toward.length() > 24.0 else -2.0 if toward.length() < 11.0 else 0.0
		if index >= 4:
			forward_m += 3.0 if not want_cover else -2.0
		var desired: Vector3 = s.global_position + side * sign_value * lateral_m + forward * forward_m
		var checked := walkable_position(desired)
		if checked.is_empty():
			stats.rejected_positions += 1
			continue
		var candidate: Vector3 = checked.position
		var covered := not _ray_clear(candidate + Vector3.UP * 1.35, threat + Vector3.UP * 1.35)
		var distance := flat_distance(candidate, threat)
		var score := -absf(distance - 19.0) * 0.12 + lateral_m * 0.16
		if sign_value == _side:
			score += 0.7
		if want_cover:
			score += 7.0 if covered else -3.0
		else:
			score += 2.5 if not covered else -2.5
		if not visible:
			score += (toward.length() - distance) * 0.35
		for friend in (s.game.enemies if s.team == "enemy" else s.game.allies):
			if friend != s and is_instance_valid(friend) and friend.alive and flat_distance(candidate, friend.global_position) < 2.0:
				score -= 4.0
		if score > best_score:
			best_score = score
			best = candidate
			best_covered = covered
			found = true
	if found:
		goal = best
		goal_active = true
		if want_cover and best_covered:
			state = "cover"
			stats.cover_moves += 1
		elif not visible:
			state = "search"
			stats.search_moves += 1
		else:
			state = "flank"
			stats.flanks += 1
		_side *= -1.0
	else:
		goal_active = false
		state = "advance"

func walkable_position(desired: Vector3) -> Dictionary:
	var start := soldier.global_position
	var previous_y := start.y
	var candidate := desired
	# Short samples reject cliffs and a deck on a different floor before a capsule sweep.
	for fraction in [0.5, 1.0]:
		var sample := start.lerp(desired, fraction)
		stats.rays += 1
		var query := PhysicsRayQueryParameters3D.create(sample + Vector3.UP * 3.0, sample + Vector3.DOWN * 4.0, 1)
		var hit := soldier.get_world_3d().direct_space_state.intersect_ray(query)
		if hit.is_empty() or hit.normal.y < MIN_FLOOR_NORMAL or absf(hit.position.y - previous_y) > 2.1:
			return {}
		previous_y = hit.position.y
		if fraction == 1.0:
			candidate.y = hit.position.y + 0.025
	if not _ray_clear(start + Vector3.UP * 1.05, candidate + Vector3.UP * 1.05):
		return {}
	var raised := soldier.global_transform.translated(Vector3.UP * 0.27)
	if soldier.test_move(raised, candidate - start):
		return {}
	return {"position": candidate}

func _choose_patrol_goal(cap: Dictionary) -> void:
	var s = soldier
	for attempt in range(4):
		var angle := randf() * TAU
		var desired: Vector3 = s.global_position + Vector3(cos(angle), 0, sin(angle)) * randf_range(2.5, 6.0)
		if cap.has("pos") and flat_distance(desired, cap["pos"]) > float(cap.get("radius", 15.0)) * 0.85:
			continue
		var checked := walkable_position(desired)
		if not checked.is_empty():
			s.wander_goal = checked.position
			return
	s.wander_goal = s.global_position

func _check_progress(delta: float) -> void:
	if move.length_squared() < 0.25:
		_stuck_t = 0.0
		_window_position = soldier.global_position
		return
	_stuck_t += delta
	if _stuck_t > 1.3:
		if flat_distance(soldier.global_position, _window_position) < 0.65:
			soldier.stuck_n += 1
			plan_escape(move.normalized())
		_stuck_t = 0.0
		_window_position = soldier.global_position

func plan_escape(direction: Vector3) -> void:
	stats.escapes += 1
	goal_active = false
	var base := atan2(direction.z, direction.x)
	_escape_dir = Vector3.ZERO
	for angle in [_side * PI / 2, -_side * PI / 2, PI * 0.78, -PI * 0.78, PI]:
		var candidate := Vector3(cos(base + angle), 0, sin(base + angle))
		if not walkable_position(soldier.global_position + candidate * 1.8).is_empty():
			_escape_dir = candidate
			break
	_escape_t = randf_range(0.7, 1.15)
	soldier.path = PackedVector3Array()
	_decision_t = 0.0

func on_hit(from: Vector3, attacker: Node) -> void:
	suppression = 1.0
	# A burst should trigger one dash to cover, not eight expensive replans mid-step.
	if state != "cover" or not goal_active:
		_decision_t = minf(_decision_t, 0.1)
		_hold_t = 0.0
	_last_seen = from
	_memory_t = MEMORY_S
	if is_instance_valid(attacker) and attacker is Node3D:
		soldier.target = attacker

func allow_far_step(direction: Vector3, delta: float) -> bool:
	_far_probe_t -= delta
	if _far_probe_t <= 0.0 and direction.length_squared() > 0.01:
		_far_probe_t = 0.4
		_far_safe = _ray_clear(soldier.global_position + Vector3.UP * 0.8, soldier.global_position + Vector3.UP * 0.8 + direction.normalized() * 1.8)
		if not _far_safe:
			stats.far_blocked_steps += 1
			plan_escape(direction.normalized())
	return _far_safe

func snapshot() -> Dictionary:
	var result := stats.duplicate()
	result["state"] = state
	result["goal_active"] = goal_active
	result["suppression"] = suppression
	result["goal"] = [goal.x, goal.y, goal.z]
	return result

static func flat_distance(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length()

extends RefCounted

## Vägnätet (assets/nav.json) som AStar3D. Bara den största sammanhängande delen används, så
## soldater aldrig får en nod de inte kan nå. Närmaste nod hittas via ett 20 m-rutnät.

const CELL := 20.0
var astar := AStar3D.new()
var points := PackedVector3Array()
var main_ids := PackedInt32Array()
var grid := {}

func load_from(path: String) -> bool:
	if not FileAccess.file_exists(path):
		return false
	var data = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not data is Dictionary:
		return false
	for i in range(data["nodes"].size()):
		var p: Array = data["nodes"][i]
		var v := Vector3(float(p[0]), float(p[1]), float(p[2]))
		points.append(v)
		astar.add_point(i, v)
	var adjacency := {}
	for e in data["edges"]:
		var a := int(e[0]); var b := int(e[1])
		astar.connect_points(a, b)
		adjacency.get_or_add(a, []).append(b)
		adjacency.get_or_add(b, []).append(a)
	# största komponenten
	var seen := {}
	var best: Array = []
	for start in range(points.size()):
		if seen.has(start):
			continue
		var comp: Array = [start]
		seen[start] = true
		var stack: Array = [start]
		while not stack.is_empty():
			var u: int = stack.pop_back()
			for v in adjacency.get(u, []):
				if not seen.has(v):
					seen[v] = true
					stack.append(v)
					comp.append(v)
		if comp.size() > best.size():
			best = comp
	var keep := {}
	for i in best:
		keep[i] = true
	for i in range(points.size()):
		if keep.has(i):
			main_ids.append(i)
			var key := _cell(points[i])
			grid.get_or_add(key, []).append(i)
		else:
			astar.set_point_disabled(i, true)
	return true

func _cell(p: Vector3) -> Vector2i:
	return Vector2i(floori(p.x / CELL), floori(p.z / CELL))

func nearest(p: Vector3) -> int:
	var c := _cell(p)
	var best := -1
	var best_d := INF
	for r in range(0, 8):
		for dx in range(-r, r + 1):
			for dz in range(-r, r + 1):
				if maxi(absi(dx), absi(dz)) != r:
					continue
				for i in grid.get(Vector2i(c.x + dx, c.y + dz), []):
					var q: Vector3 = points[i]
					var d := Vector2(q.x - p.x, q.z - p.z).length_squared()
					if d < best_d:
						best_d = d
						best = i
		if best >= 0 and sqrt(best_d) < (r + 0.5) * CELL:
			return best
	if best < 0 and not main_ids.is_empty():
		return main_ids[0]
	return best

func path(from: Vector3, to: Vector3) -> PackedVector3Array:
	var a := nearest(from)
	var b := nearest(to)
	var result := PackedVector3Array()
	if a < 0 or b < 0:
		result.append(to)
		return result
	result = astar.get_point_path(a, b)
	result.append(to)
	return result

func random_point() -> Vector3:
	return points[main_ids[randi() % main_ids.size()]]

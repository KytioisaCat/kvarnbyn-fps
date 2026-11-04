extends RefCounted

## Schematic zone influence, never actual soldier control or pathfinding.
## Convex cells: nearest known zone, bounded to 125m. All geometry is X/Z metres.
const REACH_M := 125.0
const CIRCLE_STEPS := 64

static func friendly(owner: String) -> bool:
	return owner in ["ally", "allies", "player", "friendly"]

static func clip_half_plane(polygon: PackedVector2Array, normal: Vector2, limit: float) -> PackedVector2Array:
	var result := PackedVector2Array()
	if polygon.is_empty(): return result
	var previous := polygon[-1]
	var previous_d := previous.dot(normal)-limit
	for current in polygon:
		var current_d := current.dot(normal)-limit
		if (current_d <= 0.0) != (previous_d <= 0.0):
			result.append(previous.lerp(current,previous_d/(previous_d-current_d)))
		if current_d <= 0.0: result.append(current)
		previous=current
		previous_d=current_d
	return result

static func clip_rect(polygon: PackedVector2Array, rect: Rect2) -> PackedVector2Array:
	if not rect.has_area():return PackedVector2Array()
	var result := polygon
	for plane in [[Vector2(-1,0),-rect.position.x],[Vector2(1,0),rect.end.x],
		[Vector2(0,-1),-rect.position.y],[Vector2(0,1),rect.end.y]]:
		result=clip_half_plane(result,plane[0],plane[1])
	# A view touching a circle/edge can leave repeated or collinear vertices.
	var twice_area := 0.0
	for k in range(result.size()):twice_area+=result[k].cross(result[(k+1)%result.size()])
	return result if absf(twice_area)>0.0001 else PackedVector2Array()

static func clip_segment(a: Vector2, b: Vector2, rect: Rect2) -> PackedVector2Array:
	if not rect.has_area():return PackedVector2Array()
	var low := 0.0
	var high := 1.0
	var delta := b-a
	for plane in [[Vector2(-1,0),-rect.position.x],[Vector2(1,0),rect.end.x],
		[Vector2(0,-1),-rect.position.y],[Vector2(0,1),rect.end.y]]:
		var normal: Vector2=plane[0]
		var remaining: float=float(plane[1])-normal.dot(a)
		var rate := normal.dot(delta)
		if absf(rate)<0.000001:
			if remaining<0.0:return PackedVector2Array()
		elif rate>0.0:high=minf(high,remaining/rate)
		else:low=maxf(low,remaining/rate)
		if low>high:return PackedVector2Array()
	return PackedVector2Array([a+delta*low,a+delta*high])

static func build(zones: Array[Dictionary], bounds: Rect2) -> Dictionary:
	var regions: Array[Dictionary]=[]
	var fronts: Array[PackedVector2Array]=[]
	for i in range(zones.size()):
		var zone: Dictionary=zones[i]
		if str(zone.owner)!="enemy" and not friendly(str(zone.owner)):continue
		var centre: Vector2=zone.position
		var polygon := PackedVector2Array()
		for k in range(CIRCLE_STEPS):
			polygon.append(centre+Vector2.from_angle(TAU*k/CIRCLE_STEPS)*REACH_M)
		for j in range(zones.size()):
			if i==j:continue
			var other: Vector2=zones[j].position
			var normal := other-centre
			# Deterministic first owner if two markers occupy the same location.
			if normal.length_squared()<0.0001:
				if j<i:polygon=PackedVector2Array()
				continue
			polygon=clip_half_plane(polygon,normal,(other.length_squared()-centre.length_squared())/2.0)
		polygon=clip_rect(polygon,bounds)
		if polygon.size()<3:continue
		regions.append({"id":str(zone.id),"owner":str(zone.owner),"polygon":polygon})
		for j in range(i+1,zones.size()):
			var other_zone: Dictionary=zones[j]
			if friendly(str(zone.owner))==friendly(str(other_zone.owner)):continue
			if str(other_zone.owner)!="enemy" and not friendly(str(other_zone.owner)):continue
			var other: Vector2=other_zone.position
			var normal := other-centre
			if normal.length_squared()<0.0001:continue
			var length := normal.length()
			var limit := (other.length_squared()-centre.length_squared())/2.0
			for k in range(polygon.size()):
				var a := polygon[k]
				var b := polygon[(k+1)%polygon.size()]
				if absf(a.dot(normal)-limit)/length<0.005 and absf(b.dot(normal)-limit)/length<0.005 and a.distance_to(b)>0.05:
					# Both cells must be in reach; the polygonal circle can differ at its rim.
					if ((a+b)/2).distance_to(other)<=REACH_M+0.01:fronts.append(PackedVector2Array([a,b]))
	return {"regions":regions,"fronts":fronts}

static func incoming(entries: Array[Vector2], zones: Array[Dictionary], enabled: bool) -> Array[PackedVector2Array]:
	var result: Array[PackedVector2Array]=[]
	if not enabled:return result
	for entry in entries:
		var nearest: Dictionary={}
		var best := INF
		for zone in zones:
			if str(zone.owner)!="enemy":continue
			var distance := entry.distance_squared_to(zone.position)
			if distance<best:
				best=distance
				nearest=zone
		if nearest.is_empty():continue
		var delta: Vector2=Vector2(nearest.position)-entry
		var length := minf(44.0,delta.length()-float(nearest.radius)-7.0)
		if length<6.0:continue
		var direction := delta.normalized()
		result.append(PackedVector2Array([entry+direction*3.0,entry+direction*length]))
	return result

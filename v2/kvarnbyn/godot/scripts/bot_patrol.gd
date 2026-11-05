extends RefCounted

## Test player's cleanup search. Only known navigation nodes and own position enter.
const CELL_M := 65.0
const ARRIVAL_M := 5.0
const STALL_S := 14.0
var nodes: Array[Dictionary]=[]
var visited := {}
var current := -1
var progress_position := Vector3.ZERO
var stalled_s := 0.0
var visits := 0
var skips := 0
var cycles := 0

func configure(nav) -> void:
	nodes.clear()
	visited.clear()
	current=-1
	visits=0;skips=0;cycles=0
	var cells := {}
	for id in nav.main_ids:
		var p: Vector3=nav.points[id]
		var key := Vector2i(floori(p.x/CELL_M),floori(p.z/CELL_M))
		var centre := (Vector2(key)+Vector2(.5,.5))*CELL_M
		var distance := Vector2(p.x,p.z).distance_squared_to(centre)
		if not cells.has(key) or distance<float(cells[key].distance):
			cells[key]={"node":id,"pos":p,"distance":distance}
	var keys: Array=cells.keys()
	keys.sort()
	for key in keys:nodes.append(cells[key])

func goal(position: Vector3, delta: float) -> Dictionary:
	if nodes.is_empty():return {}
	if current>=0:
		var p: Vector3=nodes[current].pos
		var distance := Vector2(position.x-p.x,position.z-p.z).length()
		if distance<ARRIVAL_M:
			visited[current]=true;visits+=1;current=-1
		else:
			# Count time only when this navigator is called, not during combat/pauses.
			if Vector2(position.x-progress_position.x,position.z-progress_position.z).length()>2.0:
				progress_position=position;stalled_s=0.0
			else:stalled_s+=delta
			if stalled_s>=STALL_S:
				visited[current]=true;skips+=1;current=-1
	if current<0:
		if visited.size()>=nodes.size():
			visited.clear();cycles+=1
		var best := INF
		for i in range(nodes.size()):
			if visited.has(i):continue
			var p: Vector3=nodes[i].pos
			var distance := Vector2(position.x-p.x,position.z-p.z).length_squared()
			if distance<best:
				best=distance;current=i
		progress_position=position;stalled_s=0.0
	return {"id":"patrol-"+str(nodes[current].node),"pos":nodes[current].pos,"radius":ARRIVAL_M/0.6}

func snapshot() -> Dictionary:
	return {"candidates":nodes.size(),"visited":visits,"skipped":skips,"cycles":cycles,
		"goal_node":int(nodes[current].node) if current>=0 else -1,"source":"known main navigation component only"}

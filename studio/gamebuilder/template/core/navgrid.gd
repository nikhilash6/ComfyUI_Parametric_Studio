class_name NavGrid
extends RefCounted
## A walkable grid made from real physics queries on the finished world, whatever built it. Enemies use it to go round things; the play-test bot uses it to walk, pressing the same keys a person would.

var astar := AStarGrid2D.new()
var origin := Vector2.ZERO
var cell := 1.0
var size := Vector2i.ZERO
var floor_y := 0.0
var space: PhysicsDirectSpaceState3D

func build(world: World3D, center: Vector2, extent: Vector2, cell_m := 1.0, y0 := 0.0, head := 2.4) -> void:
	space = world.direct_space_state
	cell = cell_m
	floor_y = y0
	origin = center - extent * 0.5
	size = Vector2i(ceili(extent.x / cell), ceili(extent.y / cell))
	astar.region = Rect2i(Vector2i.ZERO, size)
	astar.cell_size = Vector2(cell, cell)
	astar.offset = Vector2(cell, cell) * 0.5
	astar.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES
	astar.update()
	var q := PhysicsShapeQueryParameters3D.new()
	var s := BoxShape3D.new()
	s.size = Vector3(cell * 0.9 + 0.5, 1.2, cell * 0.9 + 0.5)
	q.shape = s
	q.collision_mask = U.LAYER_WORLD
	for x in size.x:
		for z in size.y:
			var w := cell_world(Vector2i(x, z))
			var ray := PhysicsRayQueryParameters3D.create(Vector3(w.x, y0 + head, w.z), Vector3(w.x, y0 - 3.0, w.z), U.LAYER_WORLD)
			var hit := space.intersect_ray(ray)
			var solid: bool = hit.is_empty() or hit.position.y > y0 + 0.9
			if not solid:
				q.transform = Transform3D(Basis.IDENTITY, Vector3(w.x, hit.position.y + 1.05, w.z))
				solid = not space.intersect_shape(q, 1).is_empty()
			astar.set_point_solid(Vector2i(x, z), solid)

func cell_of(p: Vector3) -> Vector2i:
	return Vector2i(clampi(floori((p.x - origin.x) / cell), 0, size.x - 1), clampi(floori((p.z - origin.y) / cell), 0, size.y - 1))

func cell_world(c: Vector2i) -> Vector3:
	return Vector3(origin.x + (c.x + 0.5) * cell, floor_y, origin.y + (c.y + 0.5) * cell)

func nearest_free(p: Vector3, reach_from = null) -> Vector3:
	var c0 := cell_of(p)
	var from_cell = cell_of(reach_from) if reach_from != null else null
	for r in range(0, maxi(size.x, size.y)):
		for dx in range(-r, r + 1):
			for dz in range(-r, r + 1):
				if maxi(absi(dx), absi(dz)) != r:
					continue
				var c := c0 + Vector2i(dx, dz)
				if not astar.is_in_boundsv(c) or astar.is_point_solid(c):
					continue
				if from_cell != null and astar.get_id_path(_free_near(from_cell), c).is_empty():
					continue
				return cell_world(c)
	return p

func _free_near(c0: Vector2i) -> Vector2i:
	if not astar.is_point_solid(c0):
		return c0
	for r in range(1, 12):
		for dx in range(-r, r + 1):
			for dz in range(-r, r + 1):
				var c := c0 + Vector2i(dx, dz)
				if astar.is_in_boundsv(c) and not astar.is_point_solid(c):
					return c
	return c0

func path(a: Vector3, b: Vector3) -> PackedVector3Array:
	var out := PackedVector3Array()
	for c in astar.get_id_path(_free_near(cell_of(a)), _free_near(cell_of(b))):
		out.append(cell_world(c))
	return out

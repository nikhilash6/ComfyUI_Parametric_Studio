class_name Island
## A floating island: a rounded, slightly wobbly top with an overhanging turf lip and a rock underside that tapers away. Walkable exactly where it looks walkable, because the collider is the mesh.

static func _outline(half_x: float, half_z: float, seed: int, n := 30) -> PackedVector2Array:
	var noise := FastNoiseLite.new()
	noise.seed = seed
	noise.frequency = 1.1
	var out := PackedVector2Array()
	for i in n:
		var a := TAU * float(i) / float(n)
		var c := cos(a)
		var s := sin(a)
		var r := pow(pow(absf(c), 3.5) + pow(absf(s), 3.5), -1.0 / 3.5)
		var wob := 0.93 + 0.07 * (noise.get_noise_2d(c * 2.0, s * 2.0) * 0.5 + 0.5)
		out.append(Vector2(c * r * wob * half_x, s * r * wob * half_z))
	return out

static func _ring(st: SurfaceTool, a: PackedVector3Array, b: PackedVector3Array) -> void:
	var n := a.size()
	for i in n:
		var j := (i + 1) % n
		for v in [a[i], a[j], b[i], b[i], a[j], b[j]]:
			st.add_vertex(v)

## The mesh's origin is the middle of the box the level asked for, so the top sits at +size.y / 2.
static func mesh(size: Vector3, seed: int, top: Material, under: Material, depth := -1.0) -> ArrayMesh:
	var out := _outline(size.x * 0.5, size.z * 0.5, seed)
	var y0 := size.y * 0.5
	var deep := depth if depth > 0.0 else clampf(size.x * 0.55, 1.6, 7.0)
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var am := ArrayMesh.new()
	# the walking surface and its lip
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := out.size()
	for i in n:
		var j := (i + 1) % n
		for p in [Vector3(0, y0, 0), Vector3(out[i].x, y0, out[i].y), Vector3(out[j].x, y0, out[j].y)]:
			st.set_smooth_group(0)
			st.add_vertex(p)
	var edge := PackedVector3Array()
	var lip := PackedVector3Array()
	for p in out:
		edge.append(Vector3(p.x, y0, p.y))
		lip.append(Vector3(p.x * 1.04, y0 - 0.32, p.y * 1.04))
	st.set_smooth_group(1)
	_ring(st, edge, lip)
	st.generate_normals()
	st.commit(am)
	am.surface_set_material(0, top)
	# the rock under it
	var rock := SurfaceTool.new()
	rock.begin(Mesh.PRIMITIVE_TRIANGLES)
	rock.set_smooth_group(0)
	var prev := lip
	var rings := 5
	for k in range(1, rings + 1):
		var t := float(k) / float(rings)
		var shrink := pow(1.0 - t, 0.75) * 0.92 + 0.02
		var y := y0 - 0.32 - deep * t
		var ring := PackedVector3Array()
		for p in out:
			var jitter := 1.0 + rng.randf_range(-0.14, 0.14) * (0.3 + t)
			ring.append(Vector3(p.x * shrink * jitter, y + rng.randf_range(-0.2, 0.2) * deep * 0.12, p.y * shrink * jitter))
		_ring(rock, prev, ring)
		prev = ring
	rock.generate_normals()
	rock.commit(am)
	am.surface_set_material(1, under)
	return am

static func solid(parent: Node3D, pos: Vector3, size: Vector3, seed: int, top: Material, under: Material) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = pos
	body.collision_layer = U.LAYER_WORLD | U.LAYER_CAMERA
	var mi := MeshInstance3D.new()
	mi.mesh = mesh(size, seed, top, under)
	body.add_child(mi)
	var cs := CollisionShape3D.new()
	cs.shape = mi.mesh.create_trimesh_shape()
	body.add_child(cs)
	parent.add_child(body)
	return body

## A little life on top: tufts of grass in the setting's colour. One draw call however many.
static func tufts(parent: Node3D, size: Vector3, seed: int, c: Color) -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var count := mini(int(size.x * size.z * 2.5), 260)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for k in 3:
		var a := float(k) / 3.0 * PI
		var d := Vector3(cos(a), 0, sin(a)) * 0.07
		st.set_normal(Vector3.UP)
		st.add_vertex(-d)
		st.set_normal(Vector3.UP)
		st.add_vertex(d)
		st.set_normal(Vector3.UP)
		st.add_vertex(Vector3(0, 0.3, 0))
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = st.commit()
	mm.instance_count = count
	for i in count:
		var a := rng.randf() * TAU
		var r := sqrt(rng.randf()) * 0.82
		var at := Vector3(cos(a) * r * size.x * 0.5, size.y * 0.5, sin(a) * r * size.z * 0.5)
		var b := Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * rng.randf_range(0.6, 1.3))
		mm.set_instance_transform(i, Transform3D(b, at))
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	var mat := U.flat_mat(c.darkened(0.12), 0.9)
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mmi.material_override = mat
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(mmi)

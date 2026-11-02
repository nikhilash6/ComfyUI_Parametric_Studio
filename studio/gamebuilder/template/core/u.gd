class_name U
## Small helpers shared by every kit.

const LAYER_WORLD := 1
const LAYER_PLAYER := 2
const LAYER_ENEMY := 4
## Big solid things the camera stays in front of. A prop isn't one: the camera passing through a lamp post beats jumping in front of it.
const LAYER_CAMERA := 8

static func v3(a) -> Vector3:
	return Vector3(float(a[0]), float(a[1]), float(a[2]))

static func col(hex: String, fallback := Color.WHITE) -> Color:
	return Color.html(hex) if Color.html_is_valid(hex) else fallback

static func box_mesh(parent: Node3D, pos: Vector3, size: Vector3, mat: Material) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var m := BoxMesh.new()
	m.size = size
	mi.mesh = m
	mi.material_override = mat
	mi.position = pos
	parent.add_child(mi)
	return mi

## A solid box: a mesh and a collider in one body.
static func solid_box(parent: Node3D, pos: Vector3, size: Vector3, mat: Material) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = pos
	body.collision_layer = LAYER_WORLD | LAYER_CAMERA
	var shape := CollisionShape3D.new()
	var b := BoxShape3D.new()
	b.size = size
	shape.shape = b
	body.add_child(shape)
	box_mesh(body, Vector3.ZERO, size, mat)
	parent.add_child(body)
	return body

static func flat_mat(c: Color, rough := 0.85, emit := 0.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = rough
	if emit > 0.0:
		m.emission_enabled = true
		m.emission = c
		m.emission_energy_multiplier = emit
	return m

static func sphere(parent: Node3D, pos: Vector3, r: float, mat: Material) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var m := SphereMesh.new()
	m.radius = r
	m.height = r * 2.0
	m.radial_segments = 16
	m.rings = 8
	mi.mesh = m
	mi.material_override = mat
	mi.position = pos
	parent.add_child(mi)
	return mi

static func cylinder(parent: Node3D, pos: Vector3, r: float, h: float, mat: Material, top := -1.0) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var m := CylinderMesh.new()
	m.bottom_radius = r
	m.top_radius = r if top < 0.0 else top
	m.height = h
	m.radial_segments = 16
	mi.mesh = m
	mi.material_override = mat
	mi.position = pos
	parent.add_child(mi)
	return mi

## All mesh nodes under a node.
static func meshes(n: Node, out: Array = []) -> Array:
	if n is MeshInstance3D:
		out.append(n)
	for c in n.get_children():
		meshes(c, out)
	return out

## A node's transform relative to an ancestor, from local transforms alone, so it works before anything is in the tree.
static func rel(n: Node3D, root: Node3D) -> Transform3D:
	var t := Transform3D.IDENTITY
	var at: Node = n
	while at != null and at != root:
		if at is Node3D:
			t = (at as Node3D).transform * t
		at = at.get_parent()
	return t

## The bounds of a node's meshes in that node's parent space (rest pose for skinned meshes).
static func bounds(root: Node3D) -> AABB:
	var first := true
	var box := AABB()
	for mi in meshes(root):
		var a: AABB = (root.transform * rel(mi, root)) * mi.get_aabb()
		box = a if first else box.merge(a)
		first = false
	return box

## Colliders that came with an imported scene (Godot's "-colonly" convention). A pickup or a character has its own.
static func strip_bodies(n: Node) -> void:
	for c in n.get_children():
		if c is CollisionObject3D or c is CollisionShape3D:
			c.get_parent().remove_child(c)
			c.queue_free()
		else:
			strip_bodies(c)

static func burst(parent: Node3D, pos: Vector3, c: Color, amount := 12, speed := 5.0) -> void:
	var p := CPUParticles3D.new()
	p.one_shot = true
	p.emitting = true
	p.amount = amount
	p.lifetime = 0.7
	p.explosiveness = 0.95
	p.direction = Vector3.UP
	p.spread = 80.0
	p.initial_velocity_min = speed * 0.5
	p.initial_velocity_max = speed
	p.gravity = Vector3(0, -12, 0)
	p.scale_amount_min = 0.35
	p.scale_amount_max = 0.8
	var m := SphereMesh.new()
	m.radius = 0.08
	m.height = 0.16
	m.radial_segments = 6
	m.rings = 3
	m.material = flat_mat(c, 0.6, 0.25)
	p.mesh = m
	p.position = pos
	parent.add_child(p)
	p.finished.connect(p.queue_free)

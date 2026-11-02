class_name KitBase
extends Node3D
## What every genre kit is: build the world from level.json, start, keep score, and let the play-test bot drive it through real input.

var ui: GameUI
var hero: Node3D
var cam: Node3D
var controls_text := ""

func build() -> void:
	pass

func begin() -> void:
	pass

func goal_text() -> String:
	return Game.t("goals.text", "Reach the goal.")

func hud_tick(_dt: float) -> void:
	pass

## Where the menu camera looks while the title is up.
func menu_view() -> Transform3D:
	return Transform3D(Basis.IDENTITY, Vector3(0, 8, 14)).looking_at(Vector3.ZERO, Vector3.UP)

func bot_tick(_bot: Node, _dt: float) -> void:
	pass

func prop_scene(i: int) -> String:
	var props: Array = Game.spec.get("props", [])
	return str(props[i % props.size()].get("asset", "")) if props.size() > 0 else ""

## A generated prop standing in the world with its box collider, or a drawn stand-in.
func place_prop(i: int, pos: Vector3, yaw := 0.0, scale_by := 1.0, solid := true, biggest := 1000.0) -> Node3D:
	var props: Array = Game.spec.get("props", [])
	var row: Dictionary = props[i % props.size()] if props.size() > 0 else {}
	var size: float = minf(float(row.get("size_m", 2.0)) * scale_by, biggest)
	var scene := Game.model(str(row.get("asset", "")))
	var holder := Node3D.new()
	holder.position = pos
	holder.rotation.y = yaw
	add_child(holder)
	if scene != null:
		var inst: Node3D = scene.instantiate()
		U.strip_bodies(inst)
		holder.add_child(inst)
		var box := U.bounds(holder)
		var longest: float = maxf(box.size.x, maxf(box.size.y, box.size.z))
		if longest > 0.001:
			inst.scale *= size / longest
		box = U.bounds(holder)
		inst.position -= Vector3(box.get_center().x, box.position.y, box.get_center().z)
		box = U.bounds(holder)
		if solid:
			_collider(holder, box)
	else:
		var c := Game.palette("accent2", Color("#8a7a60"))
		var s := Vector3(size * 0.6, size, size * 0.6)
		if solid:
			var body := U.solid_box(holder, Vector3(0, s.y * 0.5, 0), s, U.flat_mat(c))
			body.rotation.y = 0.0
		else:
			U.box_mesh(holder, Vector3(0, s.y * 0.5, 0), s, U.flat_mat(c))
	return holder

func _collider(holder: Node3D, box: AABB) -> void:
	var body := StaticBody3D.new()
	body.collision_layer = U.LAYER_WORLD
	var shape := CollisionShape3D.new()
	var b := BoxShape3D.new()
	# something tall is its trunk, not its canopy: you walk under a tree and bump into its stem
	var tall: bool = box.size.y > maxf(box.size.x, box.size.z) * 1.4
	var waist := 0.32 if tall else 0.8
	b.size = Vector3(box.size.x * waist, box.size.y, box.size.z * waist)
	shape.shape = b
	shape.position = box.get_center()
	body.add_child(shape)
	holder.add_child(body)

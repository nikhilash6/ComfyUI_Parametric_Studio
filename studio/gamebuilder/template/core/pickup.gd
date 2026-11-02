class_name Pickup
extends Node3D
## Something to collect: a generated model that spins and bobs in a soft glow, or a drawn gem. Collected by being close, so no physics layer can lose it.

signal taken(pickup)

var hero: Node3D
var radius := 1.25
var kind := "star"
var spin := 2.2
var _t := 0.0
var _base_y := 0.0
var visual: Avatar
var active := true
var sound := "coin"
var tint := Color("#f5c518")

func setup(model_name: String, h: float, c: Color, what := "star") -> void:
	kind = what
	tint = c
	visual = Avatar.new()
	add_child(visual)
	var scene := Game.model(model_name)
	if scene != null:
		visual.setup(model_name, h, c)
	else:
		_gem(h, c)
	_base_y = position.y
	_t = randf() * 6.0
	var light := OmniLight3D.new()
	light.light_color = c
	light.light_energy = 0.8
	light.omni_range = maxf(3.0, h * 3.0)
	light.position.y = h * 0.6
	if what != "coin":
		add_child(light)
	var ring := U.cylinder(self, Vector3(0, 0.03, 0), maxf(0.6, h * 0.6), 0.02, _ring_mat(c))
	ring.name = "Ring"
	if what == "coin":
		ring.visible = false
	else:
		var beam := U.cylinder(self, Vector3(0, 7.0, 0), 0.1, 14.0, _beam_mat(c), 0.45)
		beam.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

func _beam_mat(c: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_color = Color(c.r, c.g, c.b, 0.16)
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	return m

func _ring_mat(c: Color) -> StandardMaterial3D:
	var m := U.flat_mat(c, 0.6, 0.35)
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_color = Color(c.r, c.g, c.b, 0.35)
	return m

func _gem(h: float, c: Color) -> void:
	var mat := U.flat_mat(c, 0.3, 0.12)
	mat.metallic = 0.6
	if kind == "coin":
		var coin := U.cylinder(visual, Vector3(0, h * 0.6, 0), h * 0.5, h * 0.12, mat)
		coin.rotation.x = PI / 2.0
		return
	var m := MeshInstance3D.new()
	var p := PrismMesh.new()
	p.size = Vector3(h * 0.6, h * 0.5, h * 0.6)
	m.mesh = p
	m.material_override = mat
	m.position.y = h * 0.7
	visual.add_child(m)
	var m2 := MeshInstance3D.new()
	m2.mesh = p
	m2.material_override = mat
	m2.position.y = h * 0.2
	m2.rotation.x = PI
	visual.add_child(m2)

func _process(dt: float) -> void:
	if not active:
		return
	_t += dt
	visual.rotation.y += spin * dt
	visual.position.y = 0.25 + sin(_t * 2.4) * 0.14
	if hero == null or not is_instance_valid(hero) or Game.state != "playing":
		return
	if hero.global_position.distance_to(global_position) < radius + 0.6 and absf(hero.global_position.y - global_position.y) < 2.4:
		collect()

func collect() -> void:
	if not active:
		return
	active = false
	if kind == "coin":
		Game.sfx(sound, Game.coin_pitch())
	else:
		Game.sfx(sound, randf_range(0.97, 1.08))
		if Game.kit and Game.kit.ui:
			Game.kit.ui.flash(tint, 0.18)
	Game.log_event("pickup", {"kind": kind})
	U.burst(get_parent(), global_position + Vector3.UP * 0.6, tint)
	taken.emit(self)
	queue_free()

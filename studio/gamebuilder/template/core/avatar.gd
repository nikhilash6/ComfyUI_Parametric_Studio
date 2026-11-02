class_name Avatar
extends Node3D
## What a character looks like: a generated model fitted to its height, or a drawn stand-in. Plays named clips from a rig, or moves procedurally when the model has none.

var inst: Node3D
var player: AnimationPlayer
var clips := {}
var current := ""
var rigged := false
var from_model := false
var _time := 0.0
var _speed_norm := 0.0
var _base_scale := Vector3.ONE
var body: Node3D
var flash := 0.0
var height := 1.7

## In-place, looping clips: a generated walk travels and does not meet its own start, so the hips' travel is taken out and the best-matching stretch is kept.
static var _done := {}

func setup(model_name: String, h: float, tint: Color, stand_in := "figure") -> void:
	height = h
	body = Node3D.new()
	add_child(body)
	var scene := Game.model(model_name)
	if scene != null:
		inst = scene.instantiate()
		U.strip_bodies(inst)
		body.add_child(inst)
		from_model = true
		_fit(h)
		var found := inst.find_children("*", "AnimationPlayer", true, false)
		if found.size() > 0:
			player = found[0]
			_prepare_clips()
	if inst == null:
		inst = _stand_in(stand_in, h, tint)
		body.add_child(inst)
	_base_scale = body.scale

func _fit(h: float) -> void:
	var box := U.bounds(body)
	if box.size.y <= 0.001:
		return
	var s := h / box.size.y
	inst.scale *= s
	box = U.bounds(body)
	inst.position -= Vector3(box.get_center().x, box.position.y, box.get_center().z)
	_fit_to_bones(h)

## A skinned mesh draws where its bones say, whatever its node's bounds claim, so a rigged figure is measured by its skeleton.
func _fit_to_bones(h: float) -> void:
	var found := inst.find_children("*", "Skeleton3D", true, false)
	if found.is_empty() or found[0].get_bone_count() < 2:
		return
	var sk: Skeleton3D = found[0]
	var r := _bone_span(sk)
	if r.size.y <= 0.01:
		return
	inst.scale *= h * 0.93 / r.size.y
	r = _bone_span(sk)
	inst.global_position -= Vector3(r.get_center().x - global_position.x, r.position.y - global_position.y - h * 0.03, r.get_center().z - global_position.z)

func _bone_span(sk: Skeleton3D) -> AABB:
	var box := AABB(sk.global_transform * sk.get_bone_global_rest(0).origin, Vector3.ZERO)
	for i in sk.get_bone_count():
		box = box.expand(sk.global_transform * sk.get_bone_global_rest(i).origin)
	return box

func _prepare_clips() -> void:
	for lib_name in player.get_animation_library_list():
		var lib := player.get_animation_library(lib_name)
		for n in lib.get_animation_list():
			var key := str(n).to_lower()
			clips[key] = (str(lib_name) + "/" + str(n)) if str(lib_name) != "" else str(n)
			var a := lib.get_animation(n)
			if not _done.has(a):
				_clean(a, key in ["idle", "walk", "run", "talk", "sprint", "drive", "fly"])
				_done[a] = true
	rigged = clips.size() > 0
	player.playback_default_blend_time = 0.18

func _clean(a: Animation, loop: bool) -> void:
	for t in a.get_track_count():
		if a.track_get_type(t) == Animation.TYPE_POSITION_3D and a.track_get_key_count(t) > 0:
			var first: Vector3 = a.track_get_key_value(t, 0)
			for k in a.track_get_key_count(t):
				var v: Vector3 = a.track_get_key_value(t, k)
				a.track_set_key_value(t, k, Vector3(first.x, v.y, first.z))
	if not loop:
		a.loop_mode = Animation.LOOP_NONE
		return
	a.loop_mode = Animation.LOOP_LINEAR
	var rots := []
	for t in a.get_track_count():
		if a.track_get_type(t) == Animation.TYPE_ROTATION_3D and a.track_get_key_count(t) > 8:
			rots.append(t)
	if rots.is_empty() or a.length < 1.2:
		return
	var step := 1.0 / 15.0
	var best := Vector2(0.0, a.length)
	var best_cost := INF
	var t0 := 0.2
	while t0 < a.length * 0.5:
		var t1 := t0 + 0.7
		while t1 < a.length - 0.05:
			var cost := 0.0
			for t in rots:
				var q0: Quaternion = a.rotation_track_interpolate(t, t0)
				var q1: Quaternion = a.rotation_track_interpolate(t, t1)
				cost += 1.0 - absf(q0.dot(q1))
			cost += 0.0005 / (t1 - t0)
			if cost < best_cost:
				best_cost = cost
				best = Vector2(t0, t1)
			t1 += step
		t0 += step * 2.0
	_trim(a, best.x, best.y)

func _trim(a: Animation, t0: float, t1: float) -> void:
	for t in a.get_track_count():
		var keep := []
		for k in a.track_get_key_count(t):
			var at := a.track_get_key_time(t, k)
			if at >= t0 and at <= t1:
				keep.append([at - t0, a.track_get_key_value(t, k)])
		while a.track_get_key_count(t) > 0:
			a.track_remove_key(t, 0)
		for row in keep:
			a.track_insert_key(t, row[0], row[1])
	a.length = t1 - t0

## A drawn figure so a game with no generated model still has someone to play: visibly a stand-in, never passed off as a model's work.
func _stand_in(kind: String, h: float, tint: Color) -> Node3D:
	var root := Node3D.new()
	var mat := U.flat_mat(tint, 0.6)
	var dark := U.flat_mat(tint.darkened(0.45), 0.7)
	var eye := U.flat_mat(Color.WHITE, 0.3, 0.4)
	var pupil := U.flat_mat(Color("#101014"), 0.3)
	if kind == "blob":
		var b := U.sphere(root, Vector3(0, h * 0.5, 0), h * 0.5, mat)
		b.scale = Vector3(1.05, 0.95, 1.05)
		for sx in [-1.0, 1.0]:
			U.sphere(root, Vector3(sx * h * 0.17, h * 0.62, h * 0.38), h * 0.11, eye)
			U.sphere(root, Vector3(sx * h * 0.17, h * 0.62, h * 0.47), h * 0.05, pupil)
		return root
	var torso := U.cylinder(root, Vector3(0, h * 0.53, 0), h * 0.13, h * 0.36, mat, h * 0.16)
	torso.name = "Torso"
	U.sphere(root, Vector3(0, h * 0.86, 0), h * 0.13, mat)
	for sx in [-1.0, 1.0]:
		U.sphere(root, Vector3(sx * h * 0.05, h * 0.88, h * 0.11), h * 0.03, eye)
		var leg := U.cylinder(root, Vector3(sx * h * 0.07, h * 0.18, 0), h * 0.05, h * 0.36, dark)
		leg.name = "LegL" if sx < 0.0 else "LegR"
		var arm := U.cylinder(root, Vector3(sx * h * 0.2, h * 0.55, 0), h * 0.04, h * 0.32, dark)
		arm.name = "ArmL" if sx < 0.0 else "ArmR"
	return root

## A quick squash that springs back: landing, stomping, being hit. Works on a rigged model too.
func squash(amount := 0.2) -> void:
	if body == null:
		return
	var tw := create_tween()
	tw.tween_property(body, "scale", _base_scale * Vector3(1.0 + amount, 1.0 - amount, 1.0 + amount), 0.05)
	tw.tween_property(body, "scale", _base_scale, 0.16).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

func play(clip: String, speed := 1.0) -> void:
	if not rigged:
		return
	var key := clip if clips.has(clip) else _nearest(clip)
	if key == "":
		return
	if key != current:
		player.play(clips[key], -1, speed)
		current = key
	else:
		player.speed_scale = speed

func _nearest(clip: String) -> String:
	var order := {"run": ["walk", "idle"], "walk": ["run", "idle"], "jump": ["idle"], "fall": ["jump", "idle"], "talk": ["wave", "idle"], "wave": ["idle"]}
	for k in order.get(clip, ["idle"]):
		if clips.has(k):
			return k
	return ""

## Called by the mover every frame. A model with no rig bobs, leans and squashes; a stand-in swings its limbs.
func motion(speed_ratio: float, airborne: bool, dt: float) -> void:
	_time += dt
	_speed_norm = lerpf(_speed_norm, speed_ratio, clampf(dt * 8.0, 0.0, 1.0))
	if flash > 0.0:
		flash -= dt
		visible = fmod(flash, 0.16) > 0.08
	else:
		visible = true
	if rigged:
		return
	var f := _time * (5.0 + _speed_norm * 9.0)
	var bob := absf(sin(f)) * (0.03 + 0.08 * _speed_norm) * height
	body.position.y = bob if not airborne else 0.0
	var lean := -0.16 * _speed_norm
	body.rotation.x = lean
	var sq := 1.0 + sin(f * 2.0) * 0.03 * (0.4 + _speed_norm)
	if airborne:
		sq = 1.07
	body.scale = _base_scale * Vector3(1.0 / sqrt(sq), sq, 1.0 / sqrt(sq))
	if not from_model:
		var swing := sin(f) * 0.7 * _speed_norm
		for nm in [["LegL", swing], ["LegR", -swing], ["ArmL", -swing], ["ArmR", swing]]:
			var n := inst.get_node_or_null(str(nm[0]))
			if n:
				n.rotation.x = nm[1]

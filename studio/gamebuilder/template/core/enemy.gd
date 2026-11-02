class_name Enemy
extends CharacterBody3D
## A cartoon foe. It patrols between two points or chases the hero within a range. It bumps; a stomp or a zap turns it into a puff of confetti. Nothing here hurts anyone in a way a cartoon wouldn't show.

signal poofed(enemy)

var hero: Node3D
var speed := 2.6
var chase_speed := 4.2
var chase_range := 0.0
var points: Array = []
var _leg := 0
var hp := 1
var avatar: Avatar
var size := 1.1
var stompable := true
var gravity := 24.0
var flying := false
var dead := false
var home := Vector3.ZERO
var tint := Color("#d6503c")
var grid = null
var _path: PackedVector3Array = PackedVector3Array()
var _repath := 0.0

func setup(model_name: String, h: float, c: Color) -> void:
	size = h
	tint = c
	collision_layer = U.LAYER_ENEMY
	collision_mask = U.LAYER_WORLD
	var shape := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = minf(h * 0.42, 0.7)
	cap.height = maxf(h, cap.radius * 2.0)
	shape.shape = cap
	shape.position.y = cap.height * 0.5
	add_child(shape)
	avatar = Avatar.new()
	add_child(avatar)
	avatar.setup(model_name, h, c, "blob")
	home = position

func _physics_process(dt: float) -> void:
	if dead or Game.state != "playing":
		if avatar and not dead:
			avatar.motion(0.0, false, dt)
		return
	var want := Vector3.ZERO
	var top := speed
	var to_hero: Vector3 = hero.global_position - global_position if hero else Vector3.ZERO
	var chasing := chase_range > 0.0 and hero != null and to_hero.length() < chase_range
	if chasing:
		want = _chase_dir(to_hero, dt)
		top = chase_speed
	elif points.size() >= 2:
		var p: Vector3 = points[_leg]
		var d := p - global_position
		d.y = 0.0
		if d.length() < 0.4:
			_leg = (_leg + 1) % points.size()
		want = d
	want.y = 0.0
	want = want.normalized() * top if want.length() > 0.01 else Vector3.ZERO
	velocity.x = want.x
	velocity.z = want.z
	velocity.y = 0.0 if flying else velocity.y - gravity * dt
	move_and_slide()
	if want.length() > 0.1:
		avatar.rotation.y = lerp_angle(avatar.rotation.y, atan2(want.x, want.z), clampf(dt * 9.0, 0.0, 1.0))
		avatar.play("run" if chasing else "walk")
	else:
		avatar.play("idle")
	avatar.motion(clampf(want.length() / maxf(speed, 0.1), 0.0, 1.0), false, dt)
	if hero is Player3P:
		_touch(hero)

## Straight at the hero when the way is clear; round whatever is in the way when it isn't, if this world has a grid.
func _chase_dir(to_hero: Vector3, dt: float) -> Vector3:
	if grid == null:
		return to_hero
	_repath -= dt
	var q := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP * 0.8, hero.global_position + Vector3.UP * 0.8, U.LAYER_WORLD)
	if get_world_3d().direct_space_state.intersect_ray(q).is_empty():
		_path = PackedVector3Array()
		return to_hero
	if _repath <= 0.0 or _path.is_empty():
		_repath = 0.6
		_path = grid.path(global_position, hero.global_position)
	while _path.size() > 1 and Vector2(_path[0].x - global_position.x, _path[0].z - global_position.z).length() < 0.9:
		_path.remove_at(0)
	if _path.is_empty():
		return to_hero
	return _path[0] - global_position

func _touch(h: Player3P) -> void:
	var d := h.global_position - global_position
	var flat := Vector2(d.x, d.z).length()
	var reach := 0.45 + size * 0.42
	if flat > reach or d.y > size + 0.5 or d.y < -1.6:
		return
	if stompable and h.velocity.y < -0.5 and d.y > size * 0.4:
		h.bounce(11.0)
		Game.stop_time(0.05)
		if h.cam:
			h.cam.shake(0.35)
		poof()
		return
	h.hurt(global_position)

func zap(amount := 1) -> void:
	hp -= amount
	Game.sfx("zap", randf_range(0.9, 1.2), -8.0)
	if hp <= 0:
		poof()
	elif avatar:
		avatar.flash = 0.25

func poof() -> void:
	if dead:
		return
	dead = true
	collision_layer = 0
	Game.sfx("poof", randf_range(0.9, 1.1))
	Game.log_event("poof")
	for c in [tint, Color("#f5c518"), Color("#6fd0ff"), Color("#ff7ac6")]:
		U.burst(get_parent(), global_position + Vector3.UP * size * 0.5, c, 10, 7.0)
	poofed.emit(self)
	var tw := create_tween()
	tw.tween_property(avatar, "scale", Vector3(1.4, 0.05, 1.4), 0.14)
	tw.tween_callback(queue_free)

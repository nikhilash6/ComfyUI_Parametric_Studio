class_name Player3P
extends CharacterBody3D
## The on-foot hero shared by the platformer, quest, arena and mystery kits. Everything that makes a jump feel fair is here: coyote time, a jump buffer, a cut jump when the button is let go, a heavier fall.

signal hurt_taken(hearts: int)
signal stomped(enemy)

var speed := 7.5
var sprint_mult := 1.45
var accel := 55.0
var air_accel := 26.0
var gravity_up := 24.0
var fall_mult := 1.45
var jump_velocity := 10.0
var can_jump := true
var can_sprint := false
var cam: OrbitCam
var avatar: Avatar
var hearts := 3
var max_hearts := 3
var invuln := 0.0
var coyote := 0.0
var buffer := 0.0
var locked := false
var knock := Vector3.ZERO
var was_floor := true
var move_axes := Vector2.ZERO
var face_override = null
var jumps_made := 0
var air_jumps := 1
var _air_left := 1
var dust_color := Color(0.8, 0.75, 0.65)
var _fall_speed := 0.0
var blob: MeshInstance3D
var step_time := 0.0

func _init() -> void:
	collision_layer = U.LAYER_PLAYER
	collision_mask = U.LAYER_WORLD
	floor_snap_length = 0.3
	floor_max_angle = deg_to_rad(52.0)
	platform_floor_layers = U.LAYER_WORLD
	platform_on_leave = CharacterBody3D.PLATFORM_ON_LEAVE_ADD_VELOCITY

func setup(model_name: String, h: float, tint: Color) -> void:
	var shape := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.38
	cap.height = maxf(h, 1.0)
	shape.shape = cap
	shape.position.y = cap.height * 0.5
	add_child(shape)
	avatar = Avatar.new()
	add_child(avatar)
	avatar.setup(model_name, h, tint)
	blob = MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(1.1, 1.1)
	blob.mesh = pm
	var gr := GradientTexture2D.new()
	gr.fill = GradientTexture2D.FILL_RADIAL
	gr.fill_from = Vector2(0.5, 0.5)
	gr.fill_to = Vector2(1.0, 0.5)
	var g := Gradient.new()
	g.colors = PackedColorArray([Color(0, 0, 0, 0.55), Color(0, 0, 0, 0)])
	g.offsets = PackedFloat32Array([0.0, 1.0])
	gr.gradient = g
	var bm := StandardMaterial3D.new()
	bm.albedo_texture = gr
	bm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	bm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	blob.material_override = bm
	blob.top_level = true
	add_child(blob)

func _physics_process(dt: float) -> void:
	if Game.state != "playing":
		velocity = Vector3.ZERO
		if avatar:
			avatar.motion(0.0, false, dt)
			avatar.play("idle")
		return
	invuln = maxf(0.0, invuln - dt)
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	if locked:
		input = Vector2.ZERO
	move_axes = input
	var wish: Vector3 = (cam.flat_basis() * Vector3(input.x, 0, input.y)) if cam else Vector3(input.x, 0, input.y)
	var sprinting := can_sprint and Input.is_action_pressed("sprint") and input.length() > 0.1
	var top := speed * (sprint_mult if sprinting else 1.0)
	var flat := Vector3(velocity.x, 0, velocity.z) - knock
	var rate := accel if is_on_floor() else air_accel
	flat = flat.move_toward(wish * top, rate * dt)
	knock = knock.move_toward(Vector3.ZERO, 26.0 * dt)
	velocity.x = flat.x + knock.x
	velocity.z = flat.z + knock.z
	if is_on_floor():
		coyote = 0.11
	else:
		coyote -= dt
		var g := gravity_up
		if velocity.y < 0.0:
			g *= fall_mult
		elif not Input.is_action_pressed("jump"):
			g *= 2.1
		velocity.y = maxf(velocity.y - g * dt, -30.0)
	if can_jump and not locked:
		if Input.is_action_just_pressed("jump"):
			buffer = 0.12
		else:
			buffer -= dt
		if buffer > 0.0 and coyote > 0.0:
			velocity.y = jump_velocity
			buffer = 0.0
			coyote = 0.0
			jumps_made += 1
			floor_snap_length = 0.0
			Game.sfx("jump", randf_range(0.95, 1.08))
			U.burst(get_parent(), global_position, dust_color, 8, 2.5)
			if avatar:
				avatar.squash(-0.14)
		elif buffer > 0.0 and _air_left > 0 and not is_on_floor():
			# a second jump in the air: forgiveness for a jump taken too late, and it feels good
			_air_left -= 1
			velocity.y = jump_velocity * 0.85
			buffer = 0.0
			jumps_made += 1
			Game.sfx("jump", 1.4, -2.0)
			U.burst(get_parent(), global_position + Vector3.UP * 0.2, Game.palette("accent", Color.WHITE), 10, 3.0)
			if avatar:
				avatar.squash(-0.18)
	if velocity.y < 0.0:
		_fall_speed = -velocity.y
	move_and_slide()
	if is_on_floor():
		floor_snap_length = 0.3
		_air_left = air_jumps
		if not was_floor:
			var hard := clampf(_fall_speed / 18.0, 0.0, 1.0)
			Game.sfx("land", randf_range(0.9, 1.1), -14.0 + hard * 10.0)
			U.burst(get_parent(), global_position, dust_color, 6 + int(hard * 10.0), 2.0 + hard * 2.0)
			if avatar:
				avatar.squash(0.1 + hard * 0.16)
			if cam and hard > 0.7:
				cam.shake(0.25)
	was_floor = is_on_floor()
	_look(flat, dt)
	var ratio: float = clampf(flat.length() / speed, 0.0, 1.6)
	if avatar:
		avatar.motion(minf(ratio, 1.0), not is_on_floor(), dt)
		if not is_on_floor():
			avatar.play("jump" if velocity.y > 0.0 else "fall")
		elif ratio > 0.08:
			avatar.play("run" if ratio > 0.9 else "walk", clampf(ratio * 1.2, 0.5, 1.8))
		else:
			avatar.play("idle")
	_shadow()
	if is_on_floor() and ratio > 0.2:
		step_time += dt * ratio
		if step_time > 0.32:
			step_time = 0.0
			Game.sfx("step", randf_range(0.85, 1.15), -13.0)
			if ratio > 0.9:
				U.burst(get_parent(), global_position, dust_color, 3, 1.2)

func _look(flat: Vector3, dt: float) -> void:
	var dir: Vector3 = flat
	if face_override != null:
		dir = face_override
	if dir.length() > 0.4 and avatar:
		avatar.rotation.y = lerp_angle(avatar.rotation.y, atan2(dir.x, dir.z), clampf(dt * 13.0, 0.0, 1.0))

func _shadow() -> void:
	var q := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP * 0.3, global_position + Vector3.DOWN * 25.0, U.LAYER_WORLD)
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty():
		blob.visible = false
	else:
		blob.visible = true
		blob.global_position = hit.position + Vector3.UP * 0.03
		var d: float = global_position.y - hit.position.y
		blob.scale = Vector3.ONE * clampf(1.0 - d * 0.06, 0.45, 1.0)

func hurt(from: Vector3, amount := 1) -> void:
	if invuln > 0.0 or Game.state != "playing":
		return
	hearts -= amount
	invuln = 1.3
	Game.sfx("hurt")
	Game.log_event("hurt", {"hearts": hearts})
	var away := global_position - from
	away.y = 0.0
	knock = away.normalized() * 6.0 if away.length() > 0.01 else Vector3.ZERO
	velocity.y = 5.0
	floor_snap_length = 0.0
	if avatar:
		avatar.flash = invuln
		avatar.squash(0.25)
	if cam:
		cam.shake(0.75)
	if Game.kit and Game.kit.ui:
		Game.kit.ui.flash(Color("#ff3030"), 0.4)
	hurt_taken.emit(hearts)

func bounce(v := 9.0) -> void:
	velocity.y = v
	floor_snap_length = 0.0

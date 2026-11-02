class_name OrbitCam
extends Node3D
## A third-person camera on a spring arm. Mouse or arrow keys turn it; when nothing has turned it for a moment it eases back behind the way the target is moving.

var target: Node3D
var yaw := 0.0
var pitch := -0.24
var arm: SpringArm3D
var camera: Camera3D
var height := 1.55
var follow_rate := 12.0
var auto_follow := true
var _idle := 3.0
var trauma := 0.0
var min_pitch := -1.1
var max_pitch := 0.15

func _ready() -> void:
	arm = SpringArm3D.new()
	arm.spring_length = 4.1
	arm.margin = 0.25
	arm.collision_mask = U.LAYER_CAMERA
	var s := SphereShape3D.new()
	s.radius = 0.2
	arm.shape = s
	add_child(arm)
	camera = Camera3D.new()
	camera.fov = 66.0
	camera.far = 600.0
	arm.add_child(camera)
	camera.current = true

func _unhandled_input(event: InputEvent) -> void:
	if Game.state == "playing" and event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		yaw -= event.relative.x * 0.0028
		pitch = clampf(pitch - event.relative.y * 0.0022, min_pitch, max_pitch)
		_idle = 0.0

func _process(dt: float) -> void:
	if target == null or not is_instance_valid(target):
		return
	var lx := Input.get_axis("look_left", "look_right")
	var ly := Input.get_axis("look_up", "look_down")
	if absf(lx) + absf(ly) > 0.01:
		yaw -= lx * 2.4 * dt
		pitch = clampf(pitch - ly * 1.6 * dt, min_pitch, max_pitch)
		_idle = 0.0
	_idle += dt
	if auto_follow and _idle > 1.6 and target is CharacterBody3D:
		var v: Vector3 = target.velocity
		v.y = 0.0
		if v.length() > 1.5:
			var want := atan2(-v.x, -v.z)
			yaw = lerp_angle(yaw, want, clampf(dt * 0.9, 0.0, 1.0))
	global_position = global_position.lerp(target.global_position + Vector3.UP * height, clampf(dt * follow_rate, 0.0, 1.0))
	rotation = Vector3(pitch, yaw, 0.0)
	if Game.state == "won":
		yaw += dt * 0.35
	trauma = maxf(0.0, trauma - dt * 1.8)
	camera.h_offset = randf_range(-1.0, 1.0) * trauma * trauma * 0.35
	camera.v_offset = randf_range(-1.0, 1.0) * trauma * trauma * 0.35
	if target is CharacterBody3D:
		var flat := Vector2(target.velocity.x, target.velocity.z).length()
		camera.fov = lerpf(camera.fov, 66.0 + clampf(flat - 6.0, 0.0, 8.0) * 0.9, clampf(dt * 4.0, 0.0, 1.0))

func shake(amount := 0.6) -> void:
	trauma = minf(1.0, trauma + amount)

## The camera's flat forward and right, for camera-relative movement.
func flat_basis() -> Basis:
	return Basis(Vector3.UP, yaw)

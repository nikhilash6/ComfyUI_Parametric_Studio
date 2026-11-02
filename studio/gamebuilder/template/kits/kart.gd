extends KitBase
## Kart time trial. Three laps against the clock and a ghost. Drift through the corners, hit the boost strips.

var wants_mouse := true
var car: KartBody
var camera: Camera3D
var center: PackedVector3Array = PackedVector3Array()
var cum: PackedFloat32Array = PackedFloat32Array()
var total := 0.0
var width := 12.0
var gates: Array = []
var next_gate := 1
var lap := 1
var laps := 3
var limit := 180.0
var gold := 100.0
var silver := 120.0
var countdown := 3.5
var race_t := 0.0
var lap_t := 0.0
var best_lap := INF
var boosts: Array = []
var ghost: Node3D
var ghost_s := 0.0
var ghost_speed := 20.0
var finished := false
var _offroad_t := 0.0
var _hits := 0
var _last_cd := 4
var engine: AudioStreamPlayer
var _wrong_t := 0.0
var _shake := 0.0
var _dust_t := 0.0

class KartBody extends CharacterBody3D:
	var kit
	var heading := 0.0
	var speed := 0.0
	var max_speed := 27.0
	var accel := 15.0
	var slip := Vector3.ZERO
	var drift := false
	var drift_charge := 0.0
	var boost_t := 0.0
	var visual: Node3D
	var locked := true
	var surface := 1.0
	var flames: CPUParticles3D

	func _physics_process(dt: float) -> void:
		if Game.state != "playing":
			velocity = Vector3.ZERO
			return
		var throttle := Input.get_action_strength("move_forward") - Input.get_action_strength("move_back")
		var turn := Input.get_action_strength("move_left") - Input.get_action_strength("move_right")
		if locked:
			throttle = 0.0
			turn = 0.0
		var top := max_speed * surface
		boost_t = maxf(0.0, boost_t - dt)
		if boost_t > 0.0:
			top = max_speed * 1.38
			speed = move_toward(speed, top, 45.0 * dt)
		elif throttle > 0.0:
			speed = move_toward(speed, top, accel * throttle * dt) if speed < top else move_toward(speed, top, 18.0 * dt)
		elif throttle < 0.0:
			speed = move_toward(speed, -7.0, 34.0 * dt)
		else:
			speed = move_toward(speed, 0.0, 7.0 * dt)
		var want_drift := Input.is_action_pressed("jump") and speed > 11.0 and absf(turn) > 0.25
		if want_drift and not drift:
			Game.sfx("land", 1.2, -8.0)
		if drift and not want_drift and drift_charge > 0.6:
			boost_t = minf(drift_charge * 0.65, 1.3)
			Game.sfx("boost", 1.0, -6.0)
		if not want_drift:
			drift_charge = 0.0
		drift = want_drift
		if drift:
			drift_charge += dt
		var speed_ratio := clampf(absf(speed) / 12.0, 0.0, 1.0)
		var turn_rate := lerpf(1.2, 2.35, speed_ratio) * (1.35 if drift else 1.0)
		heading += turn * turn_rate * dt * signf(speed if absf(speed) > 0.1 else 1.0) * clampf(absf(speed) / 4.0, 0.0, 1.0)
		var forward := Vector3(-sin(heading), 0, -cos(heading))
		var grip := 2.8 if drift else 9.0
		slip = slip.lerp(forward * speed, clampf(grip * dt, 0.0, 1.0))
		velocity = Vector3(slip.x, velocity.y - 30.0 * dt, slip.z)
		move_and_slide()
		if is_on_wall():
			speed *= 0.97
			var n := get_wall_normal()
			if slip.dot(n) < -2.0:
				if absf(speed) > 8.0:
					kit.bump()
				speed *= 0.72
				slip = slip.slide(n) + n * 1.5
		rotation.y = heading
		if visual:
			var lean := -turn * 0.08 * speed_ratio * (2.0 if drift else 1.0)
			visual.rotation.z = lerpf(visual.rotation.z, lean, clampf(dt * 8.0, 0.0, 1.0))
			var slide_angle := (0.42 * turn) if drift else 0.0
			visual.rotation.y = lerp_angle(visual.rotation.y, PI + slide_angle, clampf(dt * 7.0, 0.0, 1.0))
			visual.position.y = absf(sin(Time.get_ticks_msec() * 0.03)) * 0.012 * speed_ratio
		if flames:
			flames.emitting = boost_t > 0.0 or (drift and drift_charge > 0.6)

func build() -> void:
	controls_text = "W accelerate  ·  S brake  ·  A D steer  ·  hold SPACE in a corner to drift, let go for a boost  ·  ESC pause"
	var lv: Dictionary = Game.level
	width = float(lv.get("width", 12.0))
	laps = int(lv.get("laps", 3))
	limit = float(lv.get("limit", 180.0))
	gold = float(lv.get("gold", 100.0))
	silver = float(lv.get("silver", 120.0))
	for p in lv.get("center", []):
		center.append(Vector3(float(p[0]), 0.0, float(p[1])))
	_measure()
	var ground := Game.surface("ground", Game.palette("ground", Color("#55624a")), 12.0)
	var size := float(lv.get("half", 150.0)) * 2.0 + 60.0
	U.solid_box(self, Vector3(0, -0.52, 0), Vector3(size, 1.0, size), ground).visible = false
	_terrain(lv, ground)
	_ribbon()
	_gates(lv)
	for b in lv.get("boosts", []):
		_boost_strip(int(b))
	for d in lv.get("decor", []):
		var at := U.v3(d.pos)
		at.y = hills(at.x, at.z) - 0.1
		place_prop(int(d.get("prop", 0)), at, float(d.get("yaw", 0.0)), float(d.get("scale", 1.0)), false)
	_car()
	_ghost()
	camera = Camera3D.new()
	camera.fov = 72.0
	camera.far = 900.0
	add_child(camera)
	cam = camera

var _grid: Array = []
var _gn := 0
var _gsize := 0.0

func hills(x: float, z: float) -> float:
	if _gn == 0:
		return 0.0
	var fx := clampf((x + _gsize * 0.5) / _gsize, 0.0, 0.999) * float(_gn - 1)
	var fz := clampf((z + _gsize * 0.5) / _gsize, 0.0, 0.999) * float(_gn - 1)
	var ix := int(fx)
	var iz := int(fz)
	var tx := fx - ix
	var tz := fz - iz
	var a: float = _grid[iz * _gn + ix]
	var b: float = _grid[iz * _gn + ix + 1]
	var c: float = _grid[(iz + 1) * _gn + ix]
	var d: float = _grid[(iz + 1) * _gn + ix + 1]
	return lerpf(lerpf(a, b, tx), lerpf(c, d, tx), tz)

## The land the track runs through: flat by the road, rising away from it. Looked at, not driven on; the barriers keep the car on the flat.
func _terrain(lv: Dictionary, ground: StandardMaterial3D) -> void:
	_grid = lv.get("grid", [])
	_gn = int(lv.get("grid_n", 0))
	_gsize = float(lv.get("grid_size", 0.0))
	if _gn == 0:
		return
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var cell := _gsize / float(_gn - 1)
	var rock := Game.palette("accent2", Color("#7b6a58")).lightened(0.25)
	var put := func(ix: int, iz: int) -> void:
		var h: float = _grid[iz * _gn + ix]
		var hx: float = _grid[iz * _gn + mini(ix + 1, _gn - 1)] - _grid[iz * _gn + maxi(ix - 1, 0)]
		var hz: float = _grid[mini(iz + 1, _gn - 1) * _gn + ix] - _grid[maxi(iz - 1, 0) * _gn + ix]
		var normal := Vector3(-hx, 2.0 * cell, -hz).normalized()
		st.set_normal(normal)
		st.set_color(Color.WHITE.lerp(rock, smoothstep(0.92, 0.7, normal.y)))
		st.add_vertex(Vector3(ix * cell - _gsize * 0.5, h, iz * cell - _gsize * 0.5))
	for iz in _gn - 1:
		for ix in _gn - 1:
			put.call(ix, iz)
			put.call(ix + 1, iz)
			put.call(ix, iz + 1)
			put.call(ix + 1, iz)
			put.call(ix + 1, iz + 1)
			put.call(ix, iz + 1)
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	var mat: StandardMaterial3D = ground.duplicate()
	mat.vertex_color_use_as_albedo = true
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mi.material_override = mat
	add_child(mi)

func _measure() -> void:
	cum.resize(center.size() + 1)
	var s := 0.0
	cum[0] = 0.0
	for i in center.size():
		s += center[i].distance_to(center[(i + 1) % center.size()])
		cum[i + 1] = s
	total = s

func at_s(s: float) -> Vector3:
	s = fposmod(s, total)
	var i := cum.bsearch(s) - 1
	i = clampi(i, 0, center.size() - 1)
	var seg: float = maxf(cum[i + 1] - cum[i], 0.001)
	return center[i].lerp(center[(i + 1) % center.size()], (s - cum[i]) / seg)

func nearest_s(p: Vector3) -> float:
	var best := INF
	var best_i := 0
	for i in center.size():
		var d := center[i].distance_squared_to(Vector3(p.x, 0, p.z))
		if d < best:
			best = d
			best_i = i
	return cum[best_i]

func _strip(mat: Material, off0: float, off1: float, y: float) -> void:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := center.size()
	for i in n:
		var a := center[i]
		var b := center[(i + 1) % n]
		var c := center[(i + 2) % n]
		var side0 := Vector3.UP.cross(b - center[(i - 1 + n) % n]).normalized()
		var side1 := Vector3.UP.cross(c - a).normalized()
		var a0 := a + side0 * off0 + Vector3.UP * y
		var a1 := a + side0 * off1 + Vector3.UP * y
		var b0 := b + side1 * off0 + Vector3.UP * y
		var b1 := b + side1 * off1 + Vector3.UP * y
		for v in [a0, b0, a1, a1, b0, b1]:
			st.set_normal(Vector3.UP)
			st.add_vertex(v)
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	mi.material_override = mat
	mi.material_override.cull_mode = BaseMaterial3D.CULL_DISABLED
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)

func _ribbon() -> void:
	var road := Game.surface("road", Color("#3c3c40"), 7.0, 0.95)
	_strip(road, -width * 0.5, width * 0.5, 0.03)
	var curb := U.flat_mat(Game.palette("accent", Color("#f5c518")), 0.7)
	_strip(curb, -width * 0.5 - 0.5, -width * 0.5, 0.05)
	_strip(curb, width * 0.5, width * 0.5 + 0.5, 0.05)
	var dash := U.flat_mat(Color("#e8e8e0"), 0.7)
	dash.cull_mode = BaseMaterial3D.CULL_DISABLED
	var s := 0.0
	while s < total:
		var a := at_s(s)
		var b := at_s(s + 3.0)
		var m := U.box_mesh(self, (a + b) * 0.5 + Vector3.UP * 0.06, Vector3(0.28, 0.02, 3.0), dash)
		m.look_at_from_position(m.position, b + Vector3.UP * 0.06, Vector3.UP)
		s += 9.0
	# Barriers: a low wall on each side, set back past a run-off, so a mistake costs time and never ends the race.
	var wall := Game.surface("rock", Game.palette("accent2", Color("#8d8d88")), 3.0)
	var off := width * 0.5 + 9.0
	var n := center.size()
	for side in [-1.0, 1.0]:
		var i := 0
		while i < n:
			var j := (i + 3) % n
			var a0: Vector3 = center[i]
			var b0: Vector3 = center[j]
			var sa := Vector3.UP.cross(center[(i + 1) % n] - center[(i - 1 + n) % n]).normalized()
			var sb := Vector3.UP.cross(center[(j + 1) % n] - center[(j - 1 + n) % n]).normalized()
			var p0: Vector3 = a0 + sa * off * side
			var p1: Vector3 = b0 + sb * off * side
			if not _crosses_track(p0) and not _crosses_track(p1):
				var mid: Vector3 = (p0 + p1) * 0.5 + Vector3.UP * 0.6
				var body := U.solid_box(self, mid, Vector3(1.0, 1.2, p0.distance_to(p1) + 0.6), wall)
				body.look_at_from_position(mid, p1 + Vector3.UP * 0.6, Vector3.UP)
			i += 3

func _crosses_track(p: Vector3) -> bool:
	var keep := width * 0.5 + 8.0
	for c in center:
		if c.distance_squared_to(p) < keep * keep:
			return true
	return false

func _gates(lv: Dictionary) -> void:
	var pole := U.flat_mat(Game.palette("accent", Color("#f5c518")), 0.5, 0.4)
	for i in lv.get("gates", []):
		var s: float = cum[int(i)]
		var p := at_s(s)
		var side := Vector3.UP.cross(at_s(s + 2.0) - at_s(s - 2.0)).normalized()
		gates.append(p)
		var is_start: bool = gates.size() == 1
		for k in [-1.0, 1.0]:
			U.cylinder(self, p + side * k * (width * 0.5 + 0.8) + Vector3.UP * 3.0, 0.16, 6.0, pole)
		if is_start:
			var arch := U.box_mesh(self, p + Vector3.UP * 6.0, Vector3(0.5, 1.1, 0.5), pole)
			arch.look_at_from_position(arch.position, arch.position + side, Vector3.UP)
			arch.scale.z = (width + 2.2) / 0.5
			var lbl := Label3D.new()
			lbl.text = "START  ·  FINISH"
			lbl.font_size = 128
			lbl.pixel_size = 0.012
			lbl.position = p + Vector3.UP * 6.0
			lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
			lbl.modulate = Color("#111")
			add_child(lbl)
			var white := U.flat_mat(Color.WHITE, 0.8)
			var black := U.flat_mat(Color("#111"), 0.8)
			var along := (at_s(s + 2.0) - at_s(s - 2.0)).normalized()
			for row in 2:
				for k in int(width):
					var cell := p + side * (k - width * 0.5 + 0.5) + along * (float(row) - 0.5) + Vector3.UP * 0.05
					var q := U.box_mesh(self, cell, Vector3(1, 0.02, 1), white if (row + k) % 2 == 0 else black)
					q.look_at_from_position(cell, cell + along, Vector3.UP)

func _boost_strip(i: int) -> void:
	var p := center[i % center.size()]
	var b := center[(i + 1) % center.size()]
	var m := U.flat_mat(Color("#39d0ff"), 0.4, 1.8)
	var mesh := U.box_mesh(self, p + Vector3.UP * 0.07, Vector3(width * 0.45, 0.02, 4.0), m)
	mesh.look_at_from_position(mesh.position, b + Vector3.UP * 0.07, Vector3.UP)
	boosts.append(p)

func _car() -> void:
	car = KartBody.new()
	car.kit = self
	car.collision_layer = U.LAYER_PLAYER
	car.collision_mask = U.LAYER_WORLD
	car.floor_snap_length = 0.4
	var shape := CollisionShape3D.new()
	var b := BoxShape3D.new()
	b.size = Vector3(1.5, 0.8, 2.7)
	shape.shape = b
	shape.position.y = 0.55
	car.add_child(shape)
	var start := at_s(cum[int(Game.level.get("gates", [0])[0])] + 8.0)
	var fwd := (at_s(cum[int(Game.level.get("gates", [0])[0])] + 10.0) - start).normalized()
	car.position = start + Vector3.UP * 0.2
	car.heading = atan2(-fwd.x, -fwd.z)
	car.rotation.y = car.heading
	add_child(car)
	car.visual = _vehicle_visual(str(Game.spec.get("player", {}).get("asset", "")), Game.palette("accent", Color("#f5c518")))
	car.add_child(car.visual)
	car.visual.rotation.y = PI
	var fl := CPUParticles3D.new()
	fl.amount = 24
	fl.lifetime = 0.3
	fl.emitting = false
	fl.direction = Vector3(0, 0.2, 1)
	fl.spread = 18.0
	fl.initial_velocity_min = 4.0
	fl.initial_velocity_max = 8.0
	fl.gravity = Vector3.ZERO
	var sm := SphereMesh.new()
	sm.radius = 0.1
	sm.height = 0.2
	sm.radial_segments = 6
	sm.rings = 3
	sm.material = U.flat_mat(Color("#ff9a2e"), 0.5, 3.0)
	fl.mesh = sm
	fl.position = Vector3(0, 0.4, 1.4)
	car.add_child(fl)
	car.flames = fl
	hero = car

func _vehicle_visual(model_name: String, c: Color) -> Node3D:
	var root := Node3D.new()
	var scene := Game.model(model_name)
	if scene != null:
		var inst: Node3D = scene.instantiate()
		U.strip_bodies(inst)
		root.add_child(inst)
		var box := U.bounds(root)
		var longest: float = maxf(box.size.x, maxf(box.size.y, box.size.z))
		if longest > 0.001:
			inst.scale *= float(Game.spec.get("player", {}).get("size_m", 3.0)) / longest
		box = U.bounds(root)
		inst.position -= Vector3(box.get_center().x, box.position.y, box.get_center().z)
		return root
	var mat := U.flat_mat(c, 0.35)
	var dark := U.flat_mat(Color("#17171a"), 0.8)
	U.box_mesh(root, Vector3(0, 0.42, 0), Vector3(1.3, 0.34, 2.6), mat)
	U.box_mesh(root, Vector3(0, 0.75, 0.25), Vector3(0.9, 0.42, 1.0), dark)
	U.box_mesh(root, Vector3(0, 0.62, 1.2), Vector3(1.5, 0.08, 0.3), mat)
	for sx in [-1.0, 1.0]:
		for sz in [-0.85, 0.85]:
			var w := U.cylinder(root, Vector3(sx * 0.82, 0.32, sz), 0.32, 0.3, dark)
			w.rotation.z = PI / 2.0
	return root

func _ghost() -> void:
	ghost_speed = total * laps / gold if gold > 0.0 else 20.0
	ghost = _vehicle_visual(str(Game.spec.get("player", {}).get("asset", "")), Color("#39d0ff"))
	for mi in U.meshes(ghost):
		var m := StandardMaterial3D.new()
		m.albedo_color = Color(0.3, 0.85, 1.0, 0.35)
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mi.material_override = m
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(ghost)
	ghost_s = cum[int(Game.level.get("gates", [0])[0])] + 8.0
	ghost.position = at_s(ghost_s)

func menu_view() -> Transform3D:
	var p := at_s(Time.get_ticks_msec() * 0.006)
	var q := at_s(Time.get_ticks_msec() * 0.006 + 30.0)
	return Transform3D(Basis.IDENTITY, p + Vector3.UP * 9.0).looking_at(q, Vector3.UP)

func goal_text() -> String:
	return "%d laps. Beat %d:%02d to finish at all. Gold is under %d:%02d." % [laps, int(limit) / 60, int(limit) % 60, int(gold) / 60, int(gold) % 60]

func begin() -> void:
	countdown = 3.5
	car.locked = true
	engine = Game.loop_start("engine", -16.0)

func bump() -> void:
	_hits += 1
	Game.sfx("hit", randf_range(0.9, 1.1), -6.0)
	_shake = 0.5
	ui.flash(Color.WHITE, 0.14)
	U.burst(self, car.global_position + Vector3.UP * 0.5, Color("#ffd27a"), 14, 6.0)
	Game.log_event("barrier")

func _process(dt: float) -> void:
	if camera == null or car == null:
		return
	if Game.state == "playing" or Game.state == "won" or Game.state == "lost":
		var forward := Vector3(-sin(car.heading), 0, -cos(car.heading))
		var want := car.global_position - forward * 5.2 + Vector3.UP * 2.4
		camera.global_position = camera.global_position.lerp(want, clampf(dt * 9.0, 0.0, 1.0))
		camera.look_at(car.global_position + forward * 4.0 + Vector3.UP * 1.0, Vector3.UP)
		_shake = maxf(0.0, _shake - dt * 1.6)
		camera.h_offset = randf_range(-1.0, 1.0) * _shake * _shake * 0.5
		camera.v_offset = randf_range(-1.0, 1.0) * _shake * _shake * 0.5
		_dust_t -= dt
		if _dust_t <= 0.0 and Game.state == "playing" and (car.drift or car.surface < 1.0) and absf(car.speed) > 6.0:
			_dust_t = 0.06
			U.burst(self, car.global_position + forward * -1.2, Game.palette("ground", Color("#bbaa88")).lightened(0.2), 4, 2.0)
		camera.fov = lerpf(camera.fov, 66.0 + absf(car.speed) * 0.55, clampf(dt * 3.0, 0.0, 1.0))
	if engine != null:
		engine.pitch_scale = 0.7 + absf(car.speed) / 22.0

func _physics_process(dt: float) -> void:
	if Game.state != "playing":
		return
	if countdown > 0.0:
		countdown -= dt
		var c := ceili(countdown)
		if c != _last_cd:
			_last_cd = c
			if c >= 1 and c <= 3:
				ui.toast(str(c), 0.9)
				Game.sfx("click", 0.7, -2.0)
		if countdown <= 0.0:
			car.locked = false
			ui.toast("GO", 0.8)
			Game.sfx("star", 1.3, -2.0)
			Game.log_event("go")
		return
	race_t += dt
	lap_t += dt
	ghost_s += ghost_speed * dt
	var gp := at_s(ghost_s)
	var ga := at_s(ghost_s + 2.0)
	ghost.position = gp + Vector3.UP * 0.05
	ghost.look_at(ga + Vector3.UP * 0.05, Vector3.UP)
	ghost.rotate_object_local(Vector3.UP, PI)
	var d := at_s(nearest_s(car.position)).distance_to(Vector3(car.position.x, 0, car.position.z))
	car.surface = 1.0 if d < width * 0.5 + 0.5 else 0.62
	if d >= width * 0.5 + 0.5:
		_offroad_t += dt
	for b in boosts:
		if car.position.distance_to(b) < width * 0.3 and car.boost_t <= 0.0:
			car.boost_t = 1.1
			Game.sfx("boost")
			_shake = 0.3
			ui.flash(Color("#39d0ff"), 0.12)
			Game.log_event("boost")
	_gate_check()
	if race_t > limit:
		Game.lose("out of time")

func _gate_check() -> void:
	var g: Vector3 = gates[next_gate]
	if Vector2(car.position.x - g.x, car.position.z - g.z).length() < width * 0.5 + 6.0:
		if next_gate == 0:
			_lap_done()
		else:
			Game.sfx("coin", 1.2, -12.0)
		next_gate = (next_gate + 1) % gates.size()

func _lap_done() -> void:
	best_lap = minf(best_lap, lap_t)
	Game.log_event("lap", {"lap": lap, "time": snappedf(lap_t, 0.01)})
	if lap >= laps:
		finished = true
		Game.score = int(race_t * 100.0)
		for k in 8:
			U.burst(self, car.global_position + Vector3(randf_range(-6, 6), randf_range(3, 7), randf_range(-6, 6)), Color.from_hsv(randf(), 0.7, 1.0), 20, 8.0)
		Game.win("finished in time")
		return
	lap += 1
	lap_t = 0.0
	ui.toast("LAP %d / %d" % [lap, laps], 1.4)
	Game.sfx("star")

func _fmt(t: float) -> String:
	return "%d:%05.2f" % [int(t) / 60, fmod(t, 60.0)]

func medal() -> String:
	return "GOLD" if race_t <= gold else "SILVER" if race_t <= silver else "BRONZE"

func hud_tick(_dt: float) -> void:
	ui.hud_left.text = "LAP %d / %d\n%d KM/H" % [lap, laps, int(absf(car.speed) * 3.6)]
	ui.hud_center.text = _fmt(race_t)
	ui.hud_right.text = ("BEST " + _fmt(best_lap)) if best_lap < INF else ("GOLD " + _fmt(gold))

func end_stats() -> String:
	if not finished:
		return "The clock ran out at " + _fmt(limit)
	return "%s  ·  %s  ·  best lap %s  ·  %d bumps" % [medal(), _fmt(race_t), _fmt(best_lap), _hits]

func bot_stats() -> Dictionary:
	return {"time": snappedf(race_t, 0.01), "medal": medal() if finished else "", "best_lap": snappedf(best_lap, 0.01) if best_lap < INF else 0.0, "barrier_hits": _hits, "offroad_s": snappedf(_offroad_t, 0.1), "lap": lap}

func bot_tick(bot: Node, _dt: float) -> void:
	var look := clampf(8.0 + absf(car.speed) * 0.55, 8.0, 22.0)
	var s := nearest_s(car.position)
	var target := at_s(s + look)
	var to := target - Vector3(car.position.x, 0, car.position.z)
	var want := atan2(-to.x, -to.z)
	var err := wrapf(want - car.heading, -PI, PI)
	var far := at_s(s + look + 18.0)
	var far_err := absf(wrapf(atan2(-(far - target).x, -(far - target).z) - want, -PI, PI))
	var throttle := 1.0
	if far_err > 0.75 and car.speed > 22.0:
		throttle = -0.6
	elif absf(err) > 0.9:
		throttle = 0.4
	# a drift through a long bend, let go as it straightens: the boost a person learns to want
	if far_err > 0.3 and absf(err) > 0.12 and car.speed > 14.0 and not bot.clumsy:
		bot.press("jump", 0.1)
	bot.drive(throttle, clampf(-err * 2.4, -1.0, 1.0))

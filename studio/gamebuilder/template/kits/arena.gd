extends KitBase
## Top-down arena survival. Move, dash, and hold out through the waves. Bolts of light turn foes into confetti.

const CAM_H := 15.0
const CAM_B := 9.5
var wants_mouse := true
var player: Player3P
var camera: Camera3D
var waves: Array = []
var wave_i := -1
var to_spawn := 0
var spawn_gap := 0.8
var spawn_t := 0.0
var rest := 2.5
var alive: Array = []
var bolts: Array = []
var fire_t := 0.0
var fire_rate := 0.3
var bolt_mat: StandardMaterial3D
var half := 22.0
var pickups: Array = []
var dash_t := 0.0
var dash_cd := 0.0
var aim := Vector3.FORWARD
var _mouse_seen := 0.0
var _shots := 0
var _poofs := 0
var _spawn_points: Array = []
var _bot_dash := 0.0
var nav: NavGrid

func build() -> void:
	controls_text = "WASD move  ·  mouse aims (or it aims at the nearest foe on its own)  ·  bolts fire by themselves  ·  SPACE dash  ·  ESC pause"
	var lv: Dictionary = Game.level
	half = float(lv.get("half", 22.0))
	waves = lv.get("waves", [])
	var floor_mat := Game.surface("ground", Game.palette("ground", Color("#55624a")), 6.0)
	U.solid_box(self, Vector3(0, -0.5, 0), Vector3(half * 2.0 + 8.0, 1.0, half * 2.0 + 8.0), floor_mat)
	var wall := Game.surface("rock", Game.palette("accent2", Color("#555")), 4.0)
	for s in [[0.0, -1.0], [0.0, 1.0], [-1.0, 0.0], [1.0, 0.0]]:
		var horiz: bool = s[0] == 0.0
		var size := Vector3(half * 2.0 + 4.0, 2.4, 1.2) if horiz else Vector3(1.2, 2.4, half * 2.0 + 4.0)
		U.solid_box(self, Vector3(s[0] * (half + 0.6), 1.2, s[1] * (half + 0.6)), size, wall)
	for o in lv.get("obstacles", []):
		if o.has("prop"):
			place_prop(int(o.prop), U.v3(o.pos), float(o.get("yaw", 0.0)), float(o.get("scale", 1.0)), true)
		else:
			U.solid_box(self, U.v3(o.pos) + Vector3.UP * float(o.size[1]) * 0.5, U.v3(o.size), wall)
	for p in lv.get("spawns", []):
		_spawn_points.append(U.v3(p))
	bolt_mat = U.flat_mat(Game.palette("accent", Color("#f5c518")), 0.3, 2.0)
	player = Player3P.new()
	player.position = Vector3(0, 0.1, 0)
	player.can_jump = false
	player.speed = 8.0
	player.accel = 70.0
	player.hearts = int(Game.spec.get("goals", {}).get("hearts", 5))
	player.max_hearts = player.hearts
	add_child(player)
	var row: Dictionary = Game.spec.get("player", {})
	player.setup(str(row.get("asset", "")), float(row.get("height_m", 1.7)), Game.palette("accent", Color("#f5c518")))
	player.hurt_taken.connect(func(n: int) -> void:
		if n <= 0:
			Game.lose("out of hearts"))
	hero = player
	camera = Camera3D.new()
	camera.fov = 52.0
	camera.far = 300.0
	add_child(camera)
	camera.position = Vector3(0, CAM_H, CAM_B)
	camera.look_at(Vector3.ZERO, Vector3.UP)
	cam = camera

func menu_view() -> Transform3D:
	return Transform3D(Basis.IDENTITY, Vector3(0, 21, 21)).looking_at(Vector3.ZERO, Vector3.UP)

func goal_text() -> String:
	return "Hold out through %d waves." % waves.size()

func begin() -> void:
	ui.toast("WAVE 1 COMING", 2.0)
	await get_tree().physics_frame
	await get_tree().physics_frame
	nav = NavGrid.new()
	nav.build(get_world_3d(), Vector2.ZERO, Vector2(half * 2.0, half * 2.0), 1.0)

func _input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		_mouse_seen = 1.5

func _physics_process(dt: float) -> void:
	if Game.state != "playing":
		return
	camera.position = camera.position.lerp(player.position * 0.9 + Vector3(0, CAM_H, CAM_B), clampf(dt * 5.0, 0.0, 1.0))
	_dash(dt)
	_aim(dt)
	_fire(dt)
	_move_bolts(dt)
	_waves(dt)
	alive = alive.filter(func(e): return is_instance_valid(e) and not e.dead)

func _dash(dt: float) -> void:
	dash_cd -= dt
	dash_t -= dt
	if Input.is_action_just_pressed("jump") and dash_cd <= 0.0:
		var v := Vector3(player.velocity.x, 0, player.velocity.z)
		if v.length() > 0.5:
			player.knock = v.normalized() * 16.0
			player.invuln = maxf(player.invuln, 0.3)
			dash_cd = 1.1
			Game.sfx("jump", 1.3, -8.0)

func _aim(dt: float) -> void:
	_mouse_seen -= dt
	var d := Vector3.ZERO
	if _mouse_seen > 0.0 and not Game.bot:
		var m := get_viewport().get_mouse_position()
		var o := camera.project_ray_origin(m)
		var r := camera.project_ray_normal(m)
		if absf(r.y) > 0.01:
			var hit := o + r * ((1.0 - o.y) / r.y)
			d = hit - player.global_position
	else:
		var best := INF
		for e in alive:
			if is_instance_valid(e) and not e.dead:
				var dist: float = e.global_position.distance_to(player.global_position)
				if dist < best:
					best = dist
					d = e.global_position - player.global_position
	d.y = 0.0
	if d.length() > 0.2:
		aim = d.normalized()
	player.face_override = aim

func _fire(dt: float) -> void:
	fire_t -= dt
	if fire_t > 0.0 or alive.is_empty():
		return
	fire_t = fire_rate
	_shots += 1
	var m := U.sphere(self, player.global_position + Vector3.UP * 1.05 + aim * 0.8, 0.18, bolt_mat)
	bolts.append({"node": m, "dir": aim, "life": 0.9})
	Game.sfx("zap", randf_range(1.2, 1.5), -18.0)

func _move_bolts(dt: float) -> void:
	var keep := []
	var space := get_world_3d().direct_space_state
	for b in bolts:
		var n: MeshInstance3D = b.node
		var next: Vector3 = n.position + b.dir * 26.0 * dt
		b.life -= dt
		var gone: bool = b.life <= 0.0
		var ray := PhysicsRayQueryParameters3D.create(n.position, next, U.LAYER_WORLD)
		if not space.intersect_ray(ray).is_empty():
			gone = true
		for e in alive:
			if is_instance_valid(e) and not e.dead and Vector2(e.position.x - next.x, e.position.z - next.z).length() < 0.5 + e.size * 0.4:
				e.zap(1)
				gone = true
				break
		if gone:
			n.queue_free()
		else:
			n.position = next
			keep.append(b)
	bolts = keep

func _waves(dt: float) -> void:
	if nav == null:
		return
	if to_spawn > 0:
		spawn_t -= dt
		if spawn_t <= 0.0 and alive.size() < 16:
			spawn_t = spawn_gap
			to_spawn -= 1
			_spawn()
		return
	if not alive.is_empty():
		return
	if wave_i >= 0 and wave_i == waves.size() - 1:
		Game.win("held out through every wave")
		return
	rest -= dt
	if rest > 0.0:
		return
	rest = 3.0
	if wave_i >= 0:
		_drop_heart()
	wave_i += 1
	var w: Dictionary = waves[wave_i]
	to_spawn = int(w.count)
	spawn_gap = float(w.get("gap", 0.8))
	spawn_t = 0.3
	ui.toast("WAVE %d / %d" % [wave_i + 1, waves.size()], 1.6)
	Game.sfx("star", 0.7, -6.0)
	Game.log_event("wave", {"n": wave_i + 1})

func _spawn() -> void:
	var w: Dictionary = waves[wave_i]
	var foes: Array = Game.spec.get("enemies", [])
	var foe: Dictionary = foes[randi() % foes.size()] if foes.size() > 0 else {}
	var far: Array = _spawn_points.filter(func(p): return p.distance_to(player.global_position) > 10.0)
	var at: Vector3 = (far[randi() % far.size()] if far.size() > 0 else Vector3(half - 2.0, 0.2, half - 2.0))
	var e := Enemy.new()
	e.position = at
	add_child(e)
	e.setup(str(foe.get("asset", "")), float(foe.get("size_m", 1.2)), Game.palette("danger", Color("#d6503c")))
	e.hero = player
	e.stompable = false
	e.grid = nav
	e.chase_range = 1000.0
	e.chase_speed = float(w.get("speed", 3.5)) + randf_range(-0.3, 0.3)
	e.hp = int(w.get("hp", 2))
	e.poofed.connect(func(_x) -> void:
		_poofs += 1
		Game.score += 25)
	alive.append(e)

func _drop_heart() -> void:
	var items: Array = Game.spec.get("items", [])
	var row: Dictionary = items[0] if items.size() > 0 else {}
	var p := Pickup.new()
	p.position = Vector3(randf_range(-8, 8), 0.2, randf_range(-8, 8))
	add_child(p)
	p.setup(str(row.get("asset", "")), float(row.get("size_m", 0.9)), Color("#ff7a7a"), "heart")
	p.hero = player
	p.sound = "star"
	p.taken.connect(func(_x) -> void:
		player.hearts = mini(player.hearts + 1, player.max_hearts)
		fire_rate = maxf(0.14, fire_rate - 0.02)
		ui.toast("+1 HEART, FASTER BOLTS", 1.5))
	pickups.append(p)

func hud_tick(_dt: float) -> void:
	ui.hud_left.text = ui.hearts_text(player.hearts, player.max_hearts)
	ui.hud_center.text = "WAVE %d / %d" % [maxi(wave_i + 1, 1), waves.size()]
	ui.hud_right.text = "%d:%02d   %d" % [int(Game.time_played) / 60, int(Game.time_played) % 60, Game.score]

func end_stats() -> String:
	return "%d foes turned to confetti  ·  wave %d of %d  ·  %d:%02d" % [_poofs, wave_i + 1, waves.size(), int(Game.time_played) / 60, int(Game.time_played) % 60]

func bot_stats() -> Dictionary:
	return {"wave": wave_i + 1, "waves": waves.size(), "poofs": _poofs, "hearts": player.hearts, "shots": _shots}

func bot_tick(bot: Node, dt: float) -> void:
	var push := Vector3.ZERO
	var closest := INF
	for e in alive:
		if is_instance_valid(e) and not e.dead:
			var d: Vector3 = player.global_position - e.global_position
			d.y = 0.0
			var l := d.length()
			closest = minf(closest, l)
			if l < 9.0 and l > 0.01:
				push += d.normalized() * (9.0 - l)
	var home := -player.global_position
	home.y = 0.0
	push += home * 0.22
	for p in pickups:
		if is_instance_valid(p):
			var to: Vector3 = p.global_position - player.global_position
			to.y = 0.0
			push += to.normalized() * 6.0
	_bot_dash -= dt
	if closest < 2.8 and _bot_dash <= 0.0:
		bot.press("jump", 0.05)
		_bot_dash = 1.2
	bot.steer(push if push.length() > 0.5 else Vector3.ZERO, Basis.IDENTITY, 1.0 if push.length() > 0.5 else 0.0)

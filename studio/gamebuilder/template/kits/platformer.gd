extends KitBase
## 3D platformer collectathon. Run, jump, stomp, collect every star, reach the goal.

var player: Player3P
var platforms: Array = []
var moving: Array = []
var stars_total := 0
var stars := 0
var coins := 0
var checkpoint := Vector3.ZERO
var checkpoint_i := 0
var goal_pos := Vector3.ZERO
var goal_mat: StandardMaterial3D
var gate_open := false
var kill_y := -12.0
var _t := 0.0
var _falls := 0
var _bot_i := 0
var _bot_stuck := 0.0
var _bot_last := Vector3.ZERO
var _won_wait := false
var enemies: Array = []
var checkpoints: Array = []

func build() -> void:
	controls_text = "WASD move  ·  mouse or arrow keys look  ·  SPACE jump (hold to go higher)  ·  land on a foe to stomp it  ·  ESC pause"
	var lv: Dictionary = Game.level
	kill_y = float(lv.get("kill_y", -12.0))
	var top := Game.surface("ground", Game.palette("ground", Color("#6da04b")), 7.0)
	var side := Game.surface("rock", Game.palette("accent2", Color("#7b6a58")), 5.0)
	var stone := Game.surface("rock", Game.palette("accent2", Color("#8a8078")), 3.0)
	for i in lv.get("platforms", []).size():
		_platform(lv.platforms[i], top, side, stone, i)
	_clouds(lv)
	for d in lv.get("decor", []):
		place_prop(int(d.get("prop", 0)), U.v3(d.pos), float(d.get("yaw", 0.0)), float(d.get("scale", 1.0)), true, 3.4)
	_goal(U.v3(lv.get("goal", [0, 0, 0])))
	checkpoint = U.v3(lv.get("start", [0, 1, 0]))
	player = Player3P.new()
	player.position = checkpoint
	player.hearts = int(Game.spec.get("goals", {}).get("hearts", 4))
	player.max_hearts = player.hearts
	add_child(player)
	var hero_row: Dictionary = Game.spec.get("player", {})
	player.setup(str(hero_row.get("asset", "")), float(hero_row.get("height_m", 1.7)), Game.palette("accent", Color("#f5c518")))
	hero = player
	player.hurt_taken.connect(_on_hurt)
	var orbit := OrbitCam.new()
	add_child(orbit)
	orbit.target = player
	orbit.global_position = checkpoint + Vector3.UP
	orbit.yaw = float(lv.get("start_yaw", 0.0))
	player.cam = orbit
	cam = orbit
	var items: Array = Game.spec.get("items", [])
	var star_row: Dictionary = items[0] if items.size() > 0 else {}
	var coin_row: Dictionary = items[1] if items.size() > 1 else {}
	for p in lv.get("stars", []):
		var s := Pickup.new()
		s.position = U.v3(p)
		add_child(s)
		s.setup(str(star_row.get("asset", "")), float(star_row.get("size_m", 0.9)), Game.palette("accent", Color("#f5c518")), "star")
		s.hero = player
		s.sound = "star"
		s.taken.connect(_on_star)
		stars_total += 1
	for p in lv.get("coins", []):
		var c := Pickup.new()
		c.position = U.v3(p)
		c.radius = 0.75
		add_child(c)
		c.setup(str(coin_row.get("asset", "")) if coin_row.get("kind", "") == "coin" else "", 0.45, Color("#ffe27a"), "coin")
		c.hero = player
		c.taken.connect(_on_coin)
	var foes: Array = Game.spec.get("enemies", [])
	for i in lv.get("enemies", []).size():
		var row: Dictionary = lv.enemies[i]
		var foe: Dictionary = foes[i % foes.size()] if foes.size() > 0 else {}
		var e := Enemy.new()
		e.position = U.v3(row.pos)
		add_child(e)
		e.setup(str(foe.get("asset", "")), float(foe.get("size_m", 1.1)), Game.palette("danger", Color("#d6503c")))
		e.hero = player
		e.speed = float(foe.get("speed", 2.6))
		var pts := []
		for q in row.patrol:
			pts.append(U.v3(q))
		e.points = pts
		enemies.append(e)
	for c in lv.get("checkpoints", []):
		_flag(U.v3(c))

func _platform(row: Dictionary, top: Material, side: Material, stone: Material, i: int) -> void:
	var pos := U.v3(row.pos)
	var size := U.v3(row.size)
	var body: Node3D
	var kind := str(row.get("kind", "ground"))
	if kind == "moving":
		var a := AnimatableBody3D.new()
		a.sync_to_physics = true
		a.collision_layer = U.LAYER_WORLD
		var cs := CollisionShape3D.new()
		var b := BoxShape3D.new()
		b.size = size
		cs.shape = b
		a.add_child(cs)
		var mi := MeshInstance3D.new()
		var local := stone.duplicate()
		local.uv1_world_triplanar = false
		mi.mesh = Island.mesh(size, int(Game.spec.get("seed", 1)) + i, local, local, 1.4)
		a.add_child(mi)
		b.size = Vector3(size.x * 0.9, size.y, size.z * 0.9)
		a.position = pos
		add_child(a)
		moving.append({"body": a, "base": pos, "move": U.v3(row.move), "period": float(row.period)})
		body = a
		var trim := U.cylinder(a, Vector3(0, size.y * 0.5 + 0.02, 0), size.x * 0.34, 0.04, U.flat_mat(Game.palette("accent", Color("#f5c518")), 0.6, 0.2))
		trim.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	else:
		body = Island.solid(self, pos, size, int(Game.spec.get("seed", 1)) + i, top, side)
		Island.tufts(body, size, int(Game.spec.get("seed", 1)) + i, Game.palette("ground", Color("#6da04b")))
	platforms.append(body)

## Nothing under the islands but sky and soft cloud, so a fall reads as a fall.
func _clouds(lv: Dictionary) -> void:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Game.palette("horizon", Color.WHITE).lightened(0.25)
	var rng := RandomNumberGenerator.new()
	rng.seed = int(Game.spec.get("seed", 1))
	var goal: Vector3 = U.v3(lv.get("goal", [0, 0, -60]))
	for i in 46:
		var t := rng.randf()
		var at: Vector3 = goal * t + Vector3(rng.randf_range(-70, 70), kill_y - rng.randf_range(4, 14), rng.randf_range(-40, 40))
		var c := U.sphere(self, at, rng.randf_range(5, 13), m)
		c.scale = Vector3(1.6, 0.42, 1.2)
		c.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

func _goal(p: Vector3) -> void:
	goal_pos = p
	goal_mat = U.flat_mat(Color("#7c7c78"), 0.5)
	var ring := MeshInstance3D.new()
	var t := TorusMesh.new()
	t.inner_radius = 1.7
	t.outer_radius = 2.15
	ring.mesh = t
	ring.rotation.x = PI / 2.0
	ring.position = p + Vector3.UP * 2.3
	ring.material_override = goal_mat
	add_child(ring)
	var lbl := Label3D.new()
	lbl.text = "GOAL"
	lbl.font_size = 96
	lbl.pixel_size = 0.01
	lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	lbl.position = p + Vector3.UP * 5.0
	lbl.modulate = Color("#f5c518")
	add_child(lbl)

func _flag(p: Vector3) -> void:
	var pole := U.cylinder(self, p + Vector3.UP, 0.05, 2.0, U.flat_mat(Color("#dcdcd4"), 0.4))
	pole.name = "Pole"
	var cloth := U.box_mesh(self, p + Vector3(0.36, 1.72, 0), Vector3(0.7, 0.42, 0.04), U.flat_mat(Color("#8d8d88"), 0.6))
	checkpoints.append({"pos": p, "cloth": cloth, "lit": false})

func menu_view() -> Transform3D:
	_t += 0.004
	var s: Vector3 = U.v3(Game.level.get("start", [0, 1, 0]))
	return Transform3D(Basis.IDENTITY, s + Vector3(sin(_t) * 14.0, 7.0, cos(_t) * 14.0)).looking_at(s + Vector3(0, 1, -8), Vector3.UP)

func goal_text() -> String:
	return "Collect all %d %s, then reach the goal ring." % [stars_total, Game.spec.get("items", [{}])[0].get("plural", "stars")]

func begin() -> void:
	ui.toast(Game.t("setting.name", "").to_upper(), 2.0)

func _physics_process(dt: float) -> void:
	_t += dt
	for m in moving:
		var w := sin(_t * TAU / float(m.period))
		m.body.position = m.base + m.move * w
	if Game.state != "playing":
		return
	if player.position.y < kill_y:
		_falls += 1
		var r_: Array = Game.level.get("route", [])
		Game.log_event("fall", {"route": _bot_i, "platform": int(r_[mini(_bot_i, r_.size() - 1)].p)})
		Game.sfx("fall", 1.0, -6.0)
		player.hurt(player.global_position)
		player.position = checkpoint + Vector3.UP * 0.5
		player.velocity = Vector3.ZERO
		player.knock = Vector3.ZERO
		_bot_i = checkpoint_i
		cam.global_position = checkpoint + Vector3.UP * 2.0
	for c in checkpoints:
		if not c.lit and player.global_position.distance_to(c.pos) < 2.6:
			c.lit = true
			c.cloth.material_override = U.flat_mat(Game.palette("accent", Color("#f5c518")), 0.5, 0.6)
			checkpoint = c.pos + Vector3.UP * 0.2
			checkpoint_i = _route_index(c.pos)
			player.hearts = player.max_hearts
			Game.sfx("star", 0.8, -8.0)
			U.burst(self, c.pos + Vector3.UP * 2.0, Game.palette("accent", Color.WHITE), 20, 5.0)
			ui.toast("CHECKPOINT", 1.2)
			Game.log_event("checkpoint")
	if player.global_position.distance_to(goal_pos + Vector3.UP) < 2.6:
		if stars >= stars_total:
			for k in 6:
				U.burst(self, goal_pos + Vector3(randf_range(-3, 3), randf_range(2, 5), randf_range(-3, 3)), Color.from_hsv(randf(), 0.7, 1.0), 20, 7.0)
			Game.win("reached the goal")
		elif not _won_wait:
			_won_wait = true
			ui.toast("%d MORE TO FIND" % (stars_total - stars), 2.0)
	else:
		_won_wait = false

func _route_index(p: Vector3) -> int:
	var route: Array = Game.level.get("route", [])
	var best := 0
	var best_d := INF
	for i in route.size():
		var d: float = (platforms[int(route[i].p)].global_position + U.v3(route[i].off)).distance_to(p)
		if d < best_d:
			best_d = d
			best = i
	return best

func _on_hurt(n: int) -> void:
	if n <= 0:
		Game.lose("out of hearts")

func _on_star(_p) -> void:
	stars += 1
	Game.score += 100
	ui.toast("%d / %d" % [stars, stars_total], 1.0)
	if stars >= stars_total:
		gate_open = true
		goal_mat.albedo_color = Color("#f5c518")
		goal_mat.emission_enabled = true
		goal_mat.emission = Color("#f5c518")
		goal_mat.emission_energy_multiplier = 1.0
		Game.sfx("win", 1.2, -8.0)
		ui.toast("THE GOAL IS OPEN", 2.5)

func _on_coin(_p) -> void:
	coins += 1
	Game.score += 10

func hud_tick(_dt: float) -> void:
	ui.hud_left.text = ui.hearts_text(player.hearts, player.max_hearts)
	ui.hud_center.text = "%s  %d / %d" % [str(Game.spec.get("items", [{}])[0].get("plural", "stars")).to_upper(), stars, stars_total]
	ui.hud_right.text = "%d:%02d   %d" % [int(Game.time_played) / 60, int(Game.time_played) % 60, Game.score]

func end_stats() -> String:
	return "%d:%02d  ·  %d %s  ·  %d coins  ·  %d falls" % [int(Game.time_played) / 60, int(Game.time_played) % 60, stars, Game.spec.get("items", [{}])[0].get("plural", "stars"), coins, _falls]

func _bone_height() -> float:
	var f := player.avatar.find_children("*", "Skeleton3D", true, false)
	if f.is_empty():
		return 0.0
	var sk: Skeleton3D = f[0]
	var lo := INF
	var hi := -INF
	for i in sk.get_bone_count():
		var y := (sk.global_transform * sk.get_bone_global_rest(i)).origin.y
		lo = minf(lo, y)
		hi = maxf(hi, y)
	return snappedf(hi - lo, 0.01)

func bot_stats() -> Dictionary:
	return {"stars": stars, "stars_total": stars_total, "coins": coins, "falls": _falls, "hearts": player.hearts, "jumps": player.jumps_made, "route_i": _bot_i, "hero_bounds": snappedf(U.bounds(player.avatar).size.y, 0.01), "hero_bones": _bone_height(), "cam": snappedf(cam.camera.global_position.distance_to(player.global_position + Vector3.UP), 0.1), "at": [snappedf(player.position.x, 0.1), snappedf(player.position.y, 0.1), snappedf(player.position.z, 0.1)]}

# ---------- the bot walks the level's route, with the same keys and the same jump
func _floor_ahead(p: Vector3, dir: Vector3, dist: float) -> bool:
	var from := p + dir * dist + Vector3.UP * 0.6
	var q := PhysicsRayQueryParameters3D.create(from, from + Vector3.DOWN * 1.1, U.LAYER_WORLD)
	return not get_world_3d().direct_space_state.intersect_ray(q).is_empty()

func bot_tick(bot: Node, dt: float) -> void:
	var route: Array = Game.level.get("route", [])
	if _bot_i >= route.size():
		var to := goal_pos - player.global_position
		bot.steer(to, cam.flat_basis())
		return
	var node: Dictionary = route[_bot_i]
	var plat: Node3D = platforms[int(node.p)]
	var target: Vector3 = plat.global_position + U.v3(node.off)
	var to := target - player.global_position
	var flat := Vector3(to.x, 0, to.z)
	if player.is_on_floor() and flat.length() < float(node.get("near", 1.0)) and absf(to.y) < 1.2:
		_bot_i += 1
		return
	var half: Vector3 = U.v3(Game.level.platforms[int(node.p)].size) * 0.5
	var edge_gap := maxf(absf(to.x) - half.x, 0.0) + maxf(absf(to.z) - half.z, 0.0)
	var dir := flat.normalized()
	var strength := 1.0
	var is_moving: bool = str(Game.level.platforms[int(node.p)].get("kind", "")) == "moving"
	if player.is_on_floor():
		if Input.is_action_pressed("jump") and player.velocity.y <= 0.0 and float(bot._holds.get("jump", 0.0)) < 0.16:
			bot.release("jump")
			return
		var edge := not _floor_ahead(player.global_position, dir, 1.0)
		if edge and edge_gap > 0.2:
			var reach: float = 3.0 if is_moving else float(Game.level.get("jump_reach", 4.2))
			if edge_gap < reach:
				bot.press("jump", 0.34)
			elif is_moving:
				strength = 0.0        # wait at the edge for it to come round
			else:
				bot.press("jump", 0.34)
		elif to.y > 0.6 and edge_gap < 1.4:
			bot.press("jump", 0.34)
		for e in enemies:
			if is_instance_valid(e) and not e.dead and e.global_position.distance_to(player.global_position) < 2.8 and not Input.is_action_pressed("jump"):
				bot.press("jump", 0.3)
				break
	elif player.velocity.y < -2.0 and player._air_left > 0 and edge_gap > 0.3:
		bot.tap("jump")          # falling short: the second jump, as a person would
	bot.steer(dir, cam.flat_basis(), strength)
	_bot_stuck += dt
	if _bot_stuck > 2.5:
		_bot_stuck = 0.0
		if _bot_last.distance_to(player.global_position) < 0.6 and strength > 0.0:
			bot.press("jump", 0.34)
		_bot_last = player.global_position

extends KitBase
## Third-person exploration quest. Talk to the guide, find the relics out in the wild, bring them home.

var player: Player3P
var noise := FastNoiseLite.new()
var half := 80.0
var grid := 96
var amp := 7.0
var flat_r := 22.0
var guide: Avatar
var guide_pos := Vector3.ZERO
var talked := false
var camps: Array = []
var relics_total := 0
var relics := 0
var enemies: Array = []
var bonk_t := 0.0
var _talking := false
var _bot_stuck := 0.0
var _bot_last := Vector3.ZERO
var _bot_side := 0.0
var _poofs := 0
var _t := 0.0

func height(x: float, z: float) -> float:
	var r := Vector2(x, z).length()
	var mask := smoothstep(flat_r * 0.75, flat_r * 1.6, r)
	var h := noise.get_noise_2d(x, z) * amp * mask
	var edge := smoothstep(half * 0.72, half, r)
	return h + edge * edge * 24.0

func build() -> void:
	controls_text = "WASD move  ·  mouse or arrow keys look  ·  SHIFT sprint  ·  SPACE jump  ·  E talk and bonk  ·  ESC pause"
	var lv: Dictionary = Game.level
	half = float(lv.get("half", 80.0))
	amp = float(lv.get("amp", 7.0))
	noise.seed = int(lv.get("seed", 1))
	noise.frequency = 0.012
	noise.fractal_octaves = 3
	_terrain()
	_sea()
	player = Player3P.new()
	player.can_sprint = true
	player.position = Vector3(0, height(0, 6) + 0.3, 6)
	player.hearts = int(Game.spec.get("goals", {}).get("hearts", 5))
	player.max_hearts = player.hearts
	add_child(player)
	var hero_row: Dictionary = Game.spec.get("player", {})
	player.setup(str(hero_row.get("asset", "")), float(hero_row.get("height_m", 1.7)), Game.palette("accent", Color("#f5c518")))
	player.hurt_taken.connect(func(n: int) -> void:
		if n <= 0:
			Game.lose("out of hearts"))
	hero = player
	var orbit := OrbitCam.new()
	add_child(orbit)
	orbit.target = player
	orbit.global_position = player.position + Vector3.UP
	player.cam = orbit
	cam = orbit
	_guide()
	for d in lv.get("scatter", []):
		var p := Vector3(float(d.x), height(float(d.x), float(d.z)) - 0.05, float(d.z))
		place_prop(int(d.get("prop", 0)), p, float(d.get("yaw", 0.0)), float(d.get("scale", 1.0)), true)
	var foes: Array = Game.spec.get("enemies", [])
	var items: Array = Game.spec.get("items", [])
	var relic_row: Dictionary = items[0] if items.size() > 0 else {}
	for i in lv.get("camps", []).size():
		var c: Dictionary = lv.camps[i]
		var at := Vector3(float(c.x), height(float(c.x), float(c.z)), float(c.z))
		var pk := Pickup.new()
		pk.position = at + Vector3.UP * 0.25
		add_child(pk)
		pk.setup(str(relic_row.get("asset", "")), float(relic_row.get("size_m", 1.0)), Game.palette("accent", Color("#f5c518")), "relic")
		pk.hero = player
		pk.sound = "star"
		pk.taken.connect(_on_relic)
		var beacon := U.cylinder(self, at + Vector3.UP * 30.0, 0.25, 60.0, _beacon_mat())
		beacon.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		camps.append({"pos": at, "pickup": pk, "beacon": beacon, "done": false})
		relics_total += 1
		for k in int(c.get("guards", 2)):
			var e := Enemy.new()
			var ang := float(k) / maxf(1.0, float(c.get("guards", 2))) * TAU
			var ep := at + Vector3(cos(ang), 0, sin(ang)) * 5.5
			ep.y = height(ep.x, ep.z) + 0.4
			e.position = ep
			add_child(e)
			var foe: Dictionary = foes[(i + k) % foes.size()] if foes.size() > 0 else {}
			e.setup(str(foe.get("asset", "")), float(foe.get("size_m", 1.2)), Game.palette("danger", Color("#d6503c")))
			e.hero = player
			e.speed = float(foe.get("speed", 2.4))
			e.chase_speed = float(foe.get("speed", 2.4)) * 1.7
			e.chase_range = 11.0
			e.points = [ep + Vector3(4, 0, 0), ep + Vector3(-4, 0, 0)]
			e.poofed.connect(func(_x) -> void:
				_poofs += 1
				Game.score += 25)
			enemies.append(e)
	var heart_row: Dictionary = items[1] if items.size() > 1 else {}
	for h in lv.get("hearts", []):
		var hp := Pickup.new()
		hp.position = Vector3(float(h.x), height(float(h.x), float(h.z)) + 0.2, float(h.z))
		add_child(hp)
		hp.setup(str(heart_row.get("asset", "")), float(heart_row.get("size_m", 0.7)), Color("#ff7a7a"), "heart")
		hp.hero = player
		hp.taken.connect(func(_x) -> void: player.hearts = mini(player.hearts + 1, player.max_hearts))

func _beacon_mat() -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	var a := Game.palette("accent", Color("#f5c518"))
	m.albedo_color = Color(a.r, a.g, a.b, 0.28)
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return m

func _terrain() -> void:
	var n := grid
	var cell := half * 2.0 / float(n)
	var hmap := PackedFloat32Array()
	hmap.resize((n + 1) * (n + 1))
	for iz in n + 1:
		for ix in n + 1:
			hmap[iz * (n + 1) + ix] = height(ix * cell - half, iz * cell - half)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var cg := Game.palette("ground", Color("#6da04b"))
	var cr := Game.palette("accent2", Color("#7b6a58"))
	var verts := func(ix: int, iz: int) -> void:
		var h: float = hmap[iz * (n + 1) + ix]
		var hx: float = hmap[iz * (n + 1) + mini(ix + 1, n)] - hmap[iz * (n + 1) + maxi(ix - 1, 0)]
		var hz: float = hmap[mini(iz + 1, n) * (n + 1) + ix] - hmap[maxi(iz - 1, 0) * (n + 1) + ix]
		var normal := Vector3(-hx, 2.0 * cell, -hz).normalized()
		var steep := smoothstep(0.86, 0.68, normal.y)
		st.set_normal(normal)
		st.set_color(Color.WHITE.lerp(cr.lightened(0.2), steep))
		st.add_vertex(Vector3(ix * cell - half, h, iz * cell - half))
	for iz in n:
		for ix in n:
			verts.call(ix, iz)
			verts.call(ix + 1, iz)
			verts.call(ix, iz + 1)
			verts.call(ix + 1, iz)
			verts.call(ix + 1, iz + 1)
			verts.call(ix, iz + 1)
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	var mat := Game.surface("ground", cg, 6.0)
	mat.vertex_color_use_as_albedo = true
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mi.material_override = mat
	add_child(mi)
	var body := StaticBody3D.new()
	body.collision_layer = U.LAYER_WORLD | U.LAYER_CAMERA
	var cs := CollisionShape3D.new()
	var hs := HeightMapShape3D.new()
	hs.map_width = n + 1
	hs.map_depth = n + 1
	hs.map_data = hmap
	cs.shape = hs
	cs.scale = Vector3(cell, 1.0, cell)
	body.add_child(cs)
	add_child(body)

func _sea() -> void:
	var w := MeshInstance3D.new()
	var p := PlaneMesh.new()
	p.size = Vector2(half * 2.4, half * 2.4)
	w.mesh = p
	w.position.y = -amp * 0.55
	var m := U.flat_mat(Game.palette("horizon", Color("#7fb0d8")).darkened(0.3), 0.15)
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_color.a = 0.75
	w.material_override = m
	add_child(w)

func _guide() -> void:
	guide_pos = Vector3(0, height(0, -2), -2)
	guide = Avatar.new()
	guide.position = guide_pos
	add_child(guide)
	var npc: Dictionary = (Game.spec.get("story", {}).get("npcs", [{}]) + [{}])[0]
	guide.setup(str(npc.get("asset", "")), float(npc.get("height_m", 1.7)), Color("#6fa8ff"))
	guide.play("idle")
	var lbl := Label3D.new()
	lbl.text = str(npc.get("name", "Guide"))
	lbl.font_size = 48
	lbl.pixel_size = 0.01
	lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	lbl.position = guide_pos + Vector3.UP * 2.2
	add_child(lbl)

func menu_view() -> Transform3D:
	_t += 0.002
	return Transform3D(Basis.IDENTITY, Vector3(sin(_t) * 40.0, 18.0, cos(_t) * 40.0)).looking_at(Vector3(0, 2, 0), Vector3.UP)

func goal_text() -> String:
	return "Find %d %s and bring them back." % [relics_total, Game.spec.get("items", [{}])[0].get("plural", "relics")]

func begin() -> void:
	ui.hint("Walk to %s and press E" % _guide_name())

func _guide_name() -> String:
	return str((Game.spec.get("story", {}).get("npcs", [{}]) + [{}])[0].get("name", "the guide"))

func _on_relic(_p) -> void:
	relics += 1
	Game.score += 200
	for c in camps:
		if c.pickup == _p:
			c.done = true
			c.beacon.visible = false
	if relics >= relics_total:
		ui.toast("ALL FOUND. GO BACK TO %s" % _guide_name().to_upper(), 3.0)
	else:
		ui.toast("%d / %d" % [relics, relics_total], 1.4)

func _physics_process(dt: float) -> void:
	_t += dt
	if Game.state != "playing":
		return
	if player.position.y < -amp - 8.0:
		player.position = Vector3(0, height(0, 6) + 1.0, 6)
		player.velocity = Vector3.ZERO
	bonk_t -= dt
	if Input.is_action_just_pressed("action") and not _talking:
		if player.global_position.distance_to(guide_pos) < 3.4:
			_talk()
		elif bonk_t <= 0.0:
			_bonk()
	var near_guide := player.global_position.distance_to(guide_pos) < 3.4
	if talked:
		ui.hint(("Press E to give %s the %s" % [_guide_name(), Game.spec.get("items", [{}])[0].get("plural", "relics")]) if near_guide and relics >= relics_total else ("Press E to bonk" if _foe_near() else ""))
	guide.motion(0.0, false, dt)

func _foe_near() -> bool:
	for e in enemies:
		if is_instance_valid(e) and not e.dead and e.global_position.distance_to(player.global_position) < 3.2:
			return true
	return false

func _bonk() -> void:
	bonk_t = 0.35
	Game.sfx("zap", 0.8, -10.0)
	U.burst(self, player.global_position + Vector3.UP, Color.WHITE, 8, 3.0)
	for e in enemies:
		if is_instance_valid(e) and not e.dead and e.global_position.distance_to(player.global_position) < 3.0:
			e.zap(1)

func _talk() -> void:
	_talking = true
	player.locked = true
	var npc: Dictionary = (Game.spec.get("story", {}).get("npcs", [{}]) + [{}])[0]
	var lines: Array = npc.get("lines", ["Go on then."])
	if relics >= relics_total and talked:
		ui.say(_guide_name(), Game.t("story.turn_in", "You found them all. Thank you."))
		await ui.dialog_closed
		player.locked = false
		_talking = false
		Game.win("brought them home")
		return
	if not talked:
		for l in lines:
			ui.say(_guide_name(), str(l))
			await ui.dialog_closed
		talked = true
		Game.log_event("talked")
	else:
		ui.say(_guide_name(), "%d of %d so far. Follow the beams of light." % [relics, relics_total])
		await ui.dialog_closed
	player.locked = false
	_talking = false
	if not Game.bot and Game.state == "playing" and kit_wants_capture():
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func kit_wants_capture() -> bool:
	return DisplayServer.get_name() != "headless"

func _nearest_camp() -> Dictionary:
	var best := {}
	var d := INF
	for c in camps:
		if not c.done:
			var l: float = c.pos.distance_to(player.global_position)
			if l < d:
				d = l
				best = c
	return best

func hud_tick(_dt: float) -> void:
	ui.hud_left.text = ui.hearts_text(player.hearts, player.max_hearts)
	ui.hud_center.text = "%s  %d / %d" % [str(Game.spec.get("items", [{}])[0].get("plural", "relics")).to_upper(), relics, relics_total]
	var c := _nearest_camp()
	var tgt: Vector3 = guide_pos if c.is_empty() or not talked else c.pos
	ui.hud_right.text = "%s  %d m" % [_arrow(tgt), int(tgt.distance_to(player.global_position))]

func _arrow(tgt: Vector3) -> String:
	var to := tgt - player.global_position
	var a := wrapf(atan2(-to.x, -to.z) - cam.yaw, -PI, PI)
	if absf(a) < 0.5:
		return "AHEAD"
	if absf(a) > 2.6:
		return "BEHIND"
	return "LEFT" if a > 0.0 else "RIGHT"

func end_stats() -> String:
	return "%d of %d %s  ·  %d foes turned to confetti  ·  %d:%02d" % [relics, relics_total, Game.spec.get("items", [{}])[0].get("plural", "relics"), _poofs, int(Game.time_played) / 60, int(Game.time_played) % 60]

func bot_stats() -> Dictionary:
	return {"relics": relics, "total": relics_total, "poofs": _poofs, "hearts": player.hearts, "jumps": player.jumps_made}

func bot_tick(bot: Node, dt: float) -> void:
	var c := _nearest_camp()
	var tgt: Vector3 = guide_pos if not talked or c.is_empty() else c.pos
	var to := tgt - player.global_position
	to.y = 0.0
	if not talked or c.is_empty():
		if to.length() < 2.6:
			bot.steer(Vector3.ZERO, cam.flat_basis(), 0.0)
			if not _talking:
				bot.tap("action")
			return
	if _foe_near() and bonk_t <= 0.0:
		bot.tap("action")
	var dir := to.normalized()
	if _bot_side != 0.0:
		dir = dir.rotated(Vector3.UP, _bot_side * 1.2)
		_bot_side = move_toward(_bot_side, 0.0, dt * 0.8)
	bot.steer(dir, cam.flat_basis())
	if to.length() > 6.0:
		bot.press("sprint", 0.2)
	_bot_stuck += dt
	if _bot_stuck > 1.0:
		_bot_stuck = 0.0
		if _bot_last.distance_to(player.global_position) < 1.5:
			bot.press("jump", 0.3)
			_bot_side = 1.0 if randf() < 0.5 else -1.0
		_bot_last = player.global_position

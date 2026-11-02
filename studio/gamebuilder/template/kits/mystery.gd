extends KitBase
## A walking mystery. No foes and no clock: question the suspects, find the clues, name the one who did it. Two wrong guesses and the trail goes cold.

var player: Player3P
var nav: NavGrid
var suspects: Array = []
var clues: Array = []
var strikes := 0
var max_strikes := 2
var found := 0
var busy := false
var solved := false
var _ready_world := false
var size := Vector2(44, 34)
var _bot_path: PackedVector3Array = PackedVector3Array()
var _bot_target = null
var _bot_stuck := 0.0
var _bot_last := Vector3.ZERO
var _t := 0.0
var board_pos := Vector3.ZERO
var _asked := 0

func build() -> void:
	controls_text = "WASD walk  ·  mouse or arrow keys look  ·  SHIFT hurry  ·  E talk and look closer  ·  ESC pause"
	var lv: Dictionary = Game.level
	size = Vector2(float(lv.size[0]), float(lv.size[1]))
	var place := Game.model(str(lv.get("place", "")))
	if place != null:
		var inst: Node3D = place.instantiate()
		add_child(inst)
		_fix_place_colliders(inst)
	else:
		_grounds(lv)
	for d in lv.get("decor", []):
		place_prop(int(d.get("prop", 0)), U.v3(d.pos), float(d.get("yaw", 0.0)), float(d.get("scale", 1.0)), true)
	player = Player3P.new()
	player.can_sprint = true
	player.speed = 4.8
	player.sprint_mult = 1.5
	player.jump_velocity = 7.0
	player.position = U.v3(lv.get("start", [0, 0.2, 0]))
	add_child(player)
	var row: Dictionary = Game.spec.get("player", {})
	player.setup(str(row.get("asset", "")), float(row.get("height_m", 1.7)), Game.palette("accent", Color("#f5c518")))
	hero = player
	var orbit := OrbitCam.new()
	add_child(orbit)
	orbit.target = player
	orbit.global_position = player.position + Vector3.UP
	orbit.height = 1.45
	orbit.arm.spring_length = 4.2 if orbit.arm else 4.2
	player.cam = orbit
	cam = orbit
	orbit.pitch = -0.2
	var story: Dictionary = Game.spec.get("story", {})
	for i in story.get("suspects", []).size():
		var s: Dictionary = story.suspects[i]
		var a := Avatar.new()
		add_child(a)
		a.setup(str(s.get("asset", "")), float(s.get("height_m", 1.7)), Color.from_hsv(float(i) * 0.27 + 0.05, 0.55, 0.85))
		a.play("idle")
		var lbl := Label3D.new()
		lbl.text = str(s.get("name", "Someone"))
		lbl.font_size = 44
		lbl.pixel_size = 0.009
		lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		lbl.position = Vector3.UP * (float(s.get("height_m", 1.7)) + 0.35)
		a.add_child(lbl)
		suspects.append({"node": a, "row": s, "asked": false})
	var items: Array = Game.spec.get("items", [])
	for i in story.get("clues", []).size():
		var c: Dictionary = story.clues[i]
		var item: Dictionary = items[i % items.size()] if items.size() > 0 else {}
		var holder := Node3D.new()
		add_child(holder)
		var pk := Avatar.new()
		holder.add_child(pk)
		pk.setup(str(item.get("asset", "")), float(item.get("size_m", 0.7)), Game.palette("accent", Color("#f5c518")), "blob")
		var ring := U.cylinder(holder, Vector3(0, 0.04, 0), 0.8, 0.02, _ring())
		ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		var l := OmniLight3D.new()
		l.light_color = Game.palette("accent", Color("#f5c518"))
		l.light_energy = 0.7
		l.omni_range = 4.0
		l.position.y = 1.0
		holder.add_child(l)
		clues.append({"node": holder, "row": c, "found": false})

func _ring() -> StandardMaterial3D:
	var m := U.flat_mat(Game.palette("accent", Color("#f5c518")), 0.6, 1.2)
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_color.a = 0.45
	return m

## A place arrives with its own sun from Blender, in Blender's units: far too bright here, and the kit lights the world itself.
func _fix_place_colliders(n: Node) -> void:
	if n is Light3D:
		n.visible = false
		n.queue_free()
		return
	if n is CollisionObject3D:
		n.collision_layer = U.LAYER_WORLD | U.LAYER_CAMERA
	for c in n.get_children():
		_fix_place_colliders(c)

func _grounds(lv: Dictionary) -> void:
	var ground := Game.surface("ground", Game.palette("ground", Color("#55624a")), 5.0)
	var wall := Game.surface("rock", Game.palette("accent2", Color("#6d6459")), 4.0)
	U.solid_box(self, Vector3(0, -0.5, 0), Vector3(size.x + 8.0, 1.0, size.y + 8.0), ground)
	var hx := size.x * 0.5
	var hz := size.y * 0.5
	for s in [[Vector3(0, 2, -hz - 0.5), Vector3(size.x + 2, 4, 1)], [Vector3(0, 2, hz + 0.5), Vector3(size.x + 2, 4, 1)], [Vector3(-hx - 0.5, 2, 0), Vector3(1, 4, size.y + 2)], [Vector3(hx + 0.5, 2, 0), Vector3(1, 4, size.y + 2)]]:
		U.solid_box(self, s[0], s[1], wall)
	for b in lv.get("blocks", []):
		var sz := U.v3(b.size)
		U.solid_box(self, U.v3(b.pos) + Vector3.UP * sz.y * 0.5, sz, wall)

func menu_view() -> Transform3D:
	_t += 0.002
	return Transform3D(Basis.IDENTITY, Vector3(sin(_t) * size.x * 0.45, 7.0, cos(_t) * size.y * 0.45)).looking_at(Vector3(0, 1.4, 0), Vector3.UP)

func goal_text() -> String:
	return "Find %d clues, question %d people, and name who did it." % [Game.spec.story.clues.size(), Game.spec.story.suspects.size()]

func begin() -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame
	nav = NavGrid.new()
	nav.build(get_world_3d(), Vector2.ZERO, size, 1.0, float(Game.level.get("floor_y", 0.0)))
	var start := player.global_position
	var free_start := nav.nearest_free(start)
	if free_start.distance_to(Vector3(start.x, nav.floor_y, start.z)) > 0.6:
		player.global_position = free_start + Vector3.UP * 0.2
		start = player.global_position
	for i in suspects.size():
		var p: Vector3 = nav.nearest_free(U.v3(suspects[i].row.spot), start)
		suspects[i].node.position = p
		suspects[i].node.rotation.y = randf() * TAU
		suspects[i]["pos"] = p
	for i in clues.size():
		var p: Vector3 = nav.nearest_free(U.v3(clues[i].row.spot), start)
		clues[i].node.position = p
		clues[i]["pos"] = p
	if GameWorld.dim():
		_lamps()
	_ready_world = true
	ui.toast(Game.t("setting.name", "").to_upper(), 2.2)

## Warm pools of light where the people stand: a dusk mystery is read by its lamps.
func _lamps() -> void:
	for row in suspects:
		var l := OmniLight3D.new()
		l.light_color = Color("#ffc27a")
		l.light_energy = 1.6
		l.omni_range = 7.0
		l.omni_attenuation = 1.4
		l.shadow_enabled = false
		l.position = row.pos + Vector3(0.6, 2.6, 0.4)
		add_child(l)

func _nearest() -> Dictionary:
	var best := {}
	var d := 2.6
	for s in suspects:
		var l: float = s.node.global_position.distance_to(player.global_position)
		if l < d:
			d = l
			best = {"kind": "suspect", "row": s}
	for c in clues:
		if c.found:
			continue
		var l: float = c.node.global_position.distance_to(player.global_position)
		if l < d:
			d = l
			best = {"kind": "clue", "row": c}
	return best

func _physics_process(dt: float) -> void:
	if not _ready_world or Game.state != "playing":
		return
	_t += dt
	for s in suspects:
		s.node.motion(0.0, false, dt)
	for c in clues:
		if not c.found:
			c.node.get_child(0).rotation.y += dt * 1.2
	if busy:
		return
	var what := _nearest()
	if what.is_empty():
		ui.hint("")
	elif what.kind == "suspect":
		ui.hint("E  talk to " + str(what.row.row.name))
	else:
		ui.hint("E  look closer")
	if Input.is_action_just_pressed("action") and not what.is_empty():
		if what.kind == "suspect":
			_ask(what.row)
		else:
			_inspect(what.row)

func _ask(s: Dictionary) -> void:
	busy = true
	player.locked = true
	ui.hint("")
	var a: Avatar = s.node
	var to: Vector3 = player.global_position - a.global_position
	a.rotation.y = atan2(to.x, to.z)
	a.play("talk")
	ui.say(str(s.row.name), str(s.row.get("line", "I saw nothing.")))
	await ui.dialog_closed
	a.play("idle")
	if not s.asked:
		s.asked = true
		_asked += 1
		Game.log_event("asked", {"who": s.row.name})
	_after()

func _inspect(c: Dictionary) -> void:
	busy = true
	player.locked = true
	ui.hint("")
	Game.sfx("star", 1.1, -8.0)
	ui.say(str(c.row.name), str(c.row.text))
	await ui.dialog_closed
	c.found = true
	found += 1
	Game.score += 100
	Game.log_event("clue", {"name": c.row.name})
	for n in c.node.get_children():
		if n is OmniLight3D or n is MeshInstance3D:
			n.visible = false
	_after()

func _after() -> void:
	if found >= clues.size() and _asked >= suspects.size():
		_accuse()
		return
	busy = false
	player.locked = false
	_recapture()

func _recapture() -> void:
	if not Game.bot and DisplayServer.get_name() != "headless":
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _accuse() -> void:
	var names := []
	for s in suspects:
		names.append(str(s.row.name))
	ui.choice("Who did it?", names)
	var pick: int = await ui.chosen
	if pick == int(Game.spec.story.get("culprit", 0)):
		solved = true
		ui.say(names[pick], Game.t("story.confession", "All right. It was me."))
		await ui.dialog_closed
		Game.score += 500
		Game.win("named the culprit")
		return
	strikes += 1
	Game.log_event("wrong_guess", {"who": names[pick]})
	Game.sfx("hurt")
	if strikes >= max_strikes:
		ui.say(names[pick], "You've got it wrong twice now. The trail has gone cold.")
		await ui.dialog_closed
		Game.lose("wrong twice")
		return
	ui.say(names[pick], "It wasn't me. Look again at what you found. One more wrong guess and it's over.")
	await ui.dialog_closed
	_accuse()

func hud_tick(_dt: float) -> void:
	ui.hud_left.text = "CLUES %d / %d" % [found, clues.size()]
	ui.hud_center.text = "ASKED %d / %d" % [_asked, suspects.size()]
	ui.hud_right.text = "GUESSES LEFT %d" % (max_strikes - strikes)

func end_stats() -> String:
	return "%d clues  ·  %d wrong guesses  ·  %d:%02d" % [found, strikes, int(Game.time_played) / 60, int(Game.time_played) % 60]

func bot_stats() -> Dictionary:
	return {"clues": found, "asked": _asked, "strikes": strikes, "solved": solved}

func _bot_next() -> Dictionary:
	var best := {}
	var d := INF
	for c in clues:
		if not c.found and c.has("pos"):
			var l: float = c.pos.distance_to(player.global_position)
			if l < d:
				d = l
				best = c
	for s in suspects:
		if not s.asked and s.has("pos"):
			var l: float = s.pos.distance_to(player.global_position)
			if l < d:
				d = l
				best = s
	return best

func bot_tick(bot: Node, dt: float) -> void:
	if ui.choice_open:
		bot.stop_moving()
		ui.focus_choice(int(Game.spec.story.get("culprit", 0)))
		bot.accept()
		return
	if not _ready_world or busy:
		bot.stop_moving()
		return
	var goal := _bot_next()
	if goal.is_empty():
		bot.stop_moving()
		return
	var at: Vector3 = goal.pos
	if at.distance_to(player.global_position) < 1.9:
		bot.stop_moving()
		bot.tap("action")
		_bot_target = null
		return
	if _bot_target != at or _bot_path.is_empty():
		_bot_target = at
		_bot_path = nav.path(player.global_position, at)
	while _bot_path.size() > 1 and Vector2(_bot_path[0].x - player.global_position.x, _bot_path[0].z - player.global_position.z).length() < 1.1:
		_bot_path.remove_at(0)
	if _bot_path.is_empty():
		return
	var to: Vector3 = _bot_path[0] - player.global_position
	to.y = 0.0
	bot.steer(to.normalized(), cam.flat_basis())
	bot.press("sprint", 0.2)
	_bot_stuck += dt
	if _bot_stuck > 1.2:
		_bot_stuck = 0.0
		if _bot_last.distance_to(player.global_position) < 0.5:
			_bot_path = PackedVector3Array()
			bot.press("jump", 0.2)
		_bot_last = player.global_position

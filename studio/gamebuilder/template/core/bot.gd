extends Node
## The play-test bot. It presses the same actions a player's keys press, and goes through the title and story cards the same way. Only `--bot` on the command line (or ?bot=1 on the web page) turns it on. A kit tells it where to go through bot_tick; it never moves anything itself.

var kit: KitBase
var ui: GameUI
var _holds := {}
var _elapsed := 0.0
var _frames := 0
var _frame_time := 0.0
var _fps_samples: Array = []
var _menu_wait := 2.0
var _end_wait := 3.5
var _timeout := 900.0
var _report_path := ""
var _done := false
var _axis := {"move_left": 0.0, "move_right": 0.0, "move_forward": 0.0, "move_back": 0.0}
var _shots := {}
var _shot_dir := ""
## --bot-clumsy=1 stands in for a person who isn't a machine: late on the button, a wobble in the steering, some jumps never pressed. It isn't a person, but it finds levels only a machine can finish.
var clumsy := false
var _wobble := 0.0
var _wobble_t := 0.0
var _late: Array = []
var rng := RandomNumberGenerator.new()
const REACTION_S := 0.22          # a person sees, then moves: the clumsy bot's hands lag its eyes by this much
var _pending: Array = []

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	process_physics_priority = -100       # before the hero reads the keys, as a key press would be
	_timeout = float(Game.bot_args.get("timeout", "900"))
	_report_path = str(Game.bot_args.get("report", "user://playtest.json"))
	_shot_dir = str(Game.bot_args.get("shots", ""))
	clumsy = Game.bot_args.has("clumsy")
	rng.seed = int(Game.bot_args.get("seed", "1"))

func _physics_process(dt: float) -> void:
	_elapsed += dt
	if _elapsed > _timeout:
		_finish("timeout")
		return
	for a in _holds.keys():
		_holds[a] -= dt
		if _holds[a] <= 0.0:
			Input.action_release(a)
			_holds.erase(a)
	if clumsy:
		while not _pending.is_empty() and _pending[0][0] <= _elapsed:
			var due: Dictionary = _pending.pop_front()[1]
			for a in due:
				_apply_axis(a, due[a])
		_wobble_t -= dt
		if _wobble_t <= 0.0:
			_wobble_t = rng.randf_range(0.25, 0.7)
			_wobble = rng.randf_range(-0.45, 0.45)
		for row in _late.duplicate():
			row[0] -= dt
			if row[0] <= 0.0:
				_late.erase(row)
				Input.action_press(row[1])
				_holds[row[1]] = row[2]
	match Game.state:
		"menu":
			_menu_wait -= dt
			if _menu_wait <= 0.0:
				_menu_wait = 1.2
				_accept()
		"intro":
			_menu_wait -= dt
			if _menu_wait <= 0.0:
				_menu_wait = 1.2
				_accept()
		"playing":
			if ui.dialog_open:
				_menu_wait -= dt
				if _menu_wait <= 0.0:
					_menu_wait = 1.0
					_accept()
			else:
				kit.bot_tick(self, dt)
		"won", "lost":
			stop_moving()
			_end_wait -= dt
			if _end_wait <= 0.0:
				_finish(Game.state)

func _process(dt: float) -> void:
	_frames += 1
	_frame_time += dt
	if _frame_time >= 1.0:
		_fps_samples.append(_frames / _frame_time)
		_frames = 0
		_frame_time = 0.0

func _accept() -> void:
	var e := InputEventAction.new()
	e.action = "ui_accept"
	e.pressed = true
	Input.parse_input_event(e)
	var r := InputEventAction.new()
	r.action = "ui_accept"
	r.pressed = false
	Input.parse_input_event(r)

func accept() -> void:
	_accept()

## Press an action for a while. The same call a key makes.
func press(action: String, seconds := 0.1) -> void:
	if clumsy and action == "jump" and not Input.is_action_pressed(action):
		if _late.is_empty():
			if rng.randf() > 0.04:
				_late.append([rng.randf_range(0.04, 0.16), action, seconds * rng.randf_range(0.6, 1.0)])
		return
	if not Input.is_action_pressed(action):
		Input.action_press(action)
	_holds[action] = maxf(seconds, float(_holds.get(action, 0.0)))

func tap(action: String) -> void:
	if not _holds.has(action):
		Input.action_press(action)
		_holds[action] = 0.05

## Hold the movement keys that head along a world direction, for the kit's camera.
func steer(dir: Vector3, basis: Basis, strength := 1.0) -> void:
	var local := basis.inverse() * dir
	local.y = 0.0
	if clumsy:
		local = local.rotated(Vector3.UP, _wobble)
	if local.length() > 0.001:
		local = local.normalized() * strength
	_set_axis("move_right", maxf(local.x, 0.0))
	_set_axis("move_left", maxf(-local.x, 0.0))
	_set_axis("move_back", maxf(local.z, 0.0))
	_set_axis("move_forward", maxf(-local.z, 0.0))

func drive(throttle: float, steer_amount: float) -> void:
	_set_axis("move_forward", maxf(throttle, 0.0))
	_set_axis("move_back", maxf(-throttle, 0.0))
	if clumsy:
		steer_amount = clampf(steer_amount + _wobble * 0.9, -1.0, 1.0)
		throttle = maxf(throttle, 0.6)          # brakes late, if at all
	_set_axis("move_right", maxf(steer_amount, 0.0))
	_set_axis("move_left", maxf(-steer_amount, 0.0))

func _set_axis(a: String, v: float) -> void:
	if clumsy:
		if _pending.is_empty() or _pending[-1][0] < _elapsed + REACTION_S - 0.001:
			_pending.append([_elapsed + REACTION_S, {}])
		_pending[-1][1][a] = v
		return
	_apply_axis(a, v)

func _apply_axis(a: String, v: float) -> void:
	if v > 0.01:
		Input.action_press(a, clampf(v, 0.0, 1.0))
	else:
		Input.action_release(a)

func release(action: String) -> void:
	_holds.erase(action)
	Input.action_release(action)

func stop_moving() -> void:
	_pending.clear()
	for a in _axis.keys():
		Input.action_release(a)

func _finish(result: String) -> void:
	if _done:
		return
	_done = true
	var avg := 0.0
	var low := 0.0
	if _fps_samples.size() > 0:
		var s: Array = _fps_samples.duplicate()
		s.sort()
		for f in s:
			avg += f
		avg /= s.size()
		low = s[int(s.size() * 0.05)]
	var report := {"clumsy": clumsy, "result": result, "played_s": snappedf(Game.time_played, 0.1), "wall_s": snappedf(_elapsed, 0.1), "fps_avg": snappedf(avg, 0.1), "fps_low5": snappedf(low, 0.1), "kit": Game.spec.get("kit", ""), "title": Game.spec.get("title", ""), "events": Game.events}
	if kit.has_method("bot_stats"):
		report["stats"] = kit.bot_stats()
	var f := FileAccess.open(_report_path, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(report, " "))
		f.close()
	print("PLAYTEST ", JSON.stringify({"result": result, "played_s": report["played_s"], "fps_avg": avg}))
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.__playtest = %s;" % JSON.stringify(report), true)
	else:
		get_tree().quit(0 if result == "won" else 3)

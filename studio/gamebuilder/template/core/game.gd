extends Node
## Loads the validated spec and level, holds the score and state, and plays sound. Autoload "Game".

signal state_changed(state: String)
signal event_logged(name: String, data: Dictionary)

var spec := {}
var level := {}
var credits := []
var state := "menu"             # menu, intro, playing, paused, won, lost
var bot := false
var bot_args := {}
var events: Array = []
var time_played := 0.0
var kit: Node = null
var score := 0

var _music: AudioStreamPlayer
var _sfx: Array = []
var _loops := {}

## Counts engine and script errors as they happen. The same error over and over is a game stuck in a loop: in a play-test it stops the run at once, instead of writing the same line to a log forever.
class ErrorWatch extends Logger:
	var total := 0
	var same := 0
	var last := ""
	func _log_error(function: String, file: String, line: int, code: String, rationale: String, _editor_notify: bool, _error_type: int, _script_backtraces: Array[ScriptBacktrace]) -> void:
		var key := "%s:%d %s" % [file, line, rationale if rationale != "" else code]
		total += 1
		if key == last:
			same += 1
		else:
			same = 1
			last = key
	func _log_message(_message: String, _error: bool) -> void:
		pass

const RUNAWAY_SAME := 60
const RUNAWAY_TOTAL := 600
var watch := ErrorWatch.new()
var _aborted := false

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	OS.add_logger(watch)
	spec = _json("res://game/spec.json", {})
	level = _json("res://game/level.json", {})
	credits = _json("res://game/credits.json", [])
	_input_map()
	_args()
	if bot_args.has("check"):
		_check_scripts()
		return
	_music = AudioStreamPlayer.new()
	_music.volume_db = -9.0
	add_child(_music)
	for i in 8:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_sfx.append(p)

func _process(_dt: float) -> void:
	if _aborted:
		return
	if watch.same >= RUNAWAY_SAME or watch.total >= RUNAWAY_TOTAL:
		var why := "the same error %d times in a row: %s" % [watch.same, watch.last] if watch.same >= RUNAWAY_SAME else "%d errors" % watch.total
		if bot or DisplayServer.get_name() == "headless":
			_stop("error_loop", why)
		else:
			_aborted = true          # a player keeps playing; the count just stops being checked
			push_warning("many errors: " + why)

## A game that can't run says so plainly and, in a play-test, ends with a report instead of spinning.
func fatal(why: String) -> void:
	push_error(why)
	if bot or DisplayServer.get_name() == "headless":
		_stop("broken", why)

func _stop(result: String, why: String) -> void:
	if _aborted:
		return
	_aborted = true
	var report := {"result": result, "error": why.left(400), "errors_seen": watch.total, "played_s": snappedf(time_played, 0.1), "events": events}
	var path := str(bot_args.get("report", "user://playtest.json"))
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(report, " "))
		f.close()
	print("PLAYTEST ", JSON.stringify({"result": result, "error": why.left(200)}))
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.__playtest = %s;" % JSON.stringify(report), true)
		get_tree().paused = true
	else:
		get_tree().quit(5)

func _json(path: String, fallback):
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("missing " + path)
		return fallback
	var got = JSON.parse_string(f.get_as_text())
	return fallback if got == null else got

func _args() -> void:
	var argv := OS.get_cmdline_user_args()
	for a in argv:
		if a == "--bot":
			bot = true
		elif a.begins_with("--bot-"):
			var kv: PackedStringArray = a.trim_prefix("--bot-").split("=", true, 1)
			bot_args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	if OS.has_feature("web"):
		var q = JavaScriptBridge.eval("window.location.search + ''", true)
		if typeof(q) == TYPE_STRING and "bot=1" in q:
			bot = true

## Godot's parser over every script, with this autoload in place. --check-only -s can't do it: a lone script doesn't see autoloads.
func _check_scripts() -> void:
	var bad := 0
	for folder in ["res://core", "res://kits"]:
		for f in DirAccess.get_files_at(folder):
			if f.ends_with(".gd") and not f.begins_with("_"):
				var s: GDScript = load(folder + "/" + f)
				if s == null or not s.can_instantiate():
					print("CHECK FAIL ", folder, "/", f)
					bad += 1
	print("CHECK DONE ", bad)
	get_tree().quit(1 if bad else 0)

func _bind(action: String, keys: Array, pads: Array = [], axes: Array = []) -> void:
	InputMap.add_action(action, 0.2)
	for k in keys:
		var e := InputEventKey.new()
		e.physical_keycode = k
		InputMap.action_add_event(action, e)
	for b in pads:
		var e := InputEventJoypadButton.new()
		e.button_index = b
		InputMap.action_add_event(action, e)
	for a in axes:
		var e := InputEventJoypadMotion.new()
		e.axis = a[0]
		e.axis_value = a[1]
		InputMap.action_add_event(action, e)

func _input_map() -> void:
	_bind("move_left", [KEY_A], [JOY_BUTTON_DPAD_LEFT], [[JOY_AXIS_LEFT_X, -1.0]])
	_bind("move_right", [KEY_D], [JOY_BUTTON_DPAD_RIGHT], [[JOY_AXIS_LEFT_X, 1.0]])
	_bind("move_forward", [KEY_W], [JOY_BUTTON_DPAD_UP], [[JOY_AXIS_LEFT_Y, -1.0]])
	_bind("move_back", [KEY_S], [JOY_BUTTON_DPAD_DOWN], [[JOY_AXIS_LEFT_Y, 1.0]])
	_bind("look_left", [KEY_LEFT], [], [[JOY_AXIS_RIGHT_X, -1.0]])
	_bind("look_right", [KEY_RIGHT], [], [[JOY_AXIS_RIGHT_X, 1.0]])
	_bind("look_up", [KEY_UP], [], [[JOY_AXIS_RIGHT_Y, -1.0]])
	_bind("look_down", [KEY_DOWN], [], [[JOY_AXIS_RIGHT_Y, 1.0]])
	_bind("jump", [KEY_SPACE], [JOY_BUTTON_A])
	_bind("action", [KEY_E, KEY_F], [JOY_BUTTON_X])
	_bind("sprint", [KEY_SHIFT], [JOY_BUTTON_RIGHT_SHOULDER])
	_bind("pause", [KEY_ESCAPE, KEY_P], [JOY_BUTTON_START])
	var click := InputEventMouseButton.new()
	click.button_index = MOUSE_BUTTON_LEFT
	InputMap.action_add_event("action", click)

func set_state(s: String) -> void:
	state = s
	state_changed.emit(s)

func log_event(name: String, data := {}) -> void:
	var row := {"t": snappedf(time_played, 0.01), "e": name}
	row.merge(data)
	events.append(row)
	event_logged.emit(name, data)

func win(reason := "") -> void:
	if state != "playing":
		return
	log_event("win", {"reason": reason})
	loop_stop("engine")
	sfx("win")
	Engine.time_scale = 1.0
	set_state("won")

func lose(reason := "") -> void:
	if state != "playing":
		return
	log_event("lose", {"reason": reason})
	loop_stop("engine")
	Engine.time_scale = 1.0
	sfx("lose")
	set_state("lost")

func t(path: String, fallback := "") -> String:
	var at = spec
	for key in path.split("."):
		if typeof(at) != TYPE_DICTIONARY or not at.has(key):
			return fallback
		at = at[key]
	return str(at)

func palette(name: String, fallback := Color.GRAY) -> Color:
	var p = spec.get("setting", {}).get("palette", {})
	return U.col(str(p.get(name, "")), fallback)

# ---------- assets. A missing file is not an error: every kit has a drawn stand-in.
func model(name: String) -> PackedScene:
	var path := "res://game/models/%s.glb" % name
	if name == "" or not ResourceLoader.exists(path):
		return null
	return load(path) as PackedScene

func tex(name: String) -> Texture2D:
	var path := "res://game/tex/%s.png" % name
	return load(path) as Texture2D if ResourceLoader.exists(path) else null

## A material whose texture repeats at a real-world size on any shape, so a stretched box never stretches its surface.
func surface(name: String, tint: Color, metres := 4.0, rough := 0.9) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.roughness = rough
	var tx := tex(name)
	if tx != null:
		m.albedo_texture = tx
		m.albedo_color = Color(0.82, 0.82, 0.82)
		m.uv1_triplanar = true
		m.uv1_world_triplanar = true
		m.uv1_scale = Vector3.ONE / metres
		m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	else:
		m.albedo_color = tint
	return m

# ---------- sound
func play_music() -> void:
	loop_start("wind", -24.0)
	var path := "res://game/audio/music.ogg"
	if not ResourceLoader.exists(path) or _music.playing:
		return
	var s: AudioStream = load(path)
	if s is AudioStreamOggVorbis:
		s.loop = true
	_music.stream = s
	_music.play()

var _coin_t := 0
var _coin_streak := 0

## Coins taken close together climb in pitch, so a good run sounds like one.
func coin_pitch() -> float:
	var now := Time.get_ticks_msec()
	_coin_streak = _coin_streak + 1 if now - _coin_t < 1100 else 0
	_coin_t = now
	return minf(1.0 + _coin_streak * 0.06, 1.9)

## A tiny freeze on a big hit: the thing that makes a stomp feel heavy.
func stop_time(seconds := 0.05) -> void:
	Engine.time_scale = 0.05
	await get_tree().create_timer(seconds, true, false, true).timeout
	Engine.time_scale = 1.0

func stop_music() -> void:
	_music.stop()

func sfx(name: String, pitch := 1.0, db := -4.0) -> void:
	var path := "res://game/audio/sfx_%s.wav" % name
	if not ResourceLoader.exists(path):
		return
	for p in _sfx:
		if not p.playing:
			p.stream = load(path)
			p.pitch_scale = pitch
			p.volume_db = db
			p.play()
			return

func loop_start(name: String, db := -14.0) -> AudioStreamPlayer:
	if _loops.has(name):
		return _loops[name]
	var path := "res://game/audio/sfx_%s.wav" % name
	if not ResourceLoader.exists(path):
		return null
	var p := AudioStreamPlayer.new()
	var s: AudioStreamWAV = load(path)
	s.loop_mode = AudioStreamWAV.LOOP_FORWARD
	s.loop_begin = 0
	s.loop_end = int(s.get_length() * s.mix_rate)
	p.stream = s
	p.volume_db = db
	add_child(p)
	p.play()
	_loops[name] = p
	return p

func loop_stop(name: String) -> void:
	if _loops.has(name):
		_loops[name].queue_free()
		_loops.erase(name)

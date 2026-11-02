extends Node
## Builds the world, the chosen genre kit and the UI, then runs title -> story -> play -> end.

var world: Node3D
var ui: GameUI
var kit: KitBase
var menu_cam: Camera3D
var bot_node: Node

static var _skip_menu := false

func _ready() -> void:
	if Game.bot_args.has("check"):
		set_process(false)
		set_process_unhandled_input(false)
		return
	Game.set_state("menu")
	Game.events.clear()
	Game.time_played = 0.0
	Game.score = 0
	world = Node3D.new()
	add_child(world)
	GameWorld.build(world)
	ui = GameUI.new()
	add_child(ui)
	var script: GDScript = load("res://kits/kit.gd")
	if script == null or not script.can_instantiate():
		Game.fatal("the game's kit script didn't load, so there is nothing to play")
		return
	kit = script.new()
	kit.ui = ui
	world.add_child(kit)
	Game.kit = kit
	kit.build()
	if ResourceLoader.exists("res://core/flourish.gd"):
		var extra := Node3D.new()
		extra.set_script(load("res://core/flourish.gd"))
		kit.add_child(extra)
	menu_cam = Camera3D.new()
	menu_cam.fov = 60.0
	menu_cam.far = 600.0
	world.add_child(menu_cam)
	menu_cam.global_transform = kit.menu_view()
	menu_cam.current = true
	ui.play_pressed.connect(_on_play)
	ui.intro_done.connect(_on_intro_done)
	ui.retry_pressed.connect(_on_retry)
	Game.state_changed.connect(_on_state)
	Game.play_music()
	if Game.bot:
		bot_node = (load("res://core/bot.gd") as GDScript).new()
		bot_node.kit = kit
		bot_node.ui = ui
		add_child(bot_node)
	if _skip_menu:
		_skip_menu = false
		_on_intro_done()
	else:
		ui.show_menu(kit)

func _on_play() -> void:
	Game.set_state("intro")
	ui.show_intro(kit)

func _on_intro_done() -> void:
	ui.show_hud(kit)
	if kit.cam is Camera3D:
		kit.cam.current = true
	elif kit.cam is OrbitCam:
		kit.cam.camera.current = true
	Game.set_state("playing")
	_capture()
	kit.begin()

func _capture() -> void:
	if kit.get("wants_mouse") == true or Game.bot or DisplayServer.get_name() == "headless":
		return
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _on_retry() -> void:
	_skip_menu = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	get_tree().paused = false
	Game.loop_stop("engine")
	get_tree().reload_current_scene()

func _on_state(s: String) -> void:
	if s == "won" or s == "lost":
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		ui.show_end(s == "won", kit)
	elif s == "playing":
		_capture()

func _process(dt: float) -> void:
	if kit == null or not is_instance_valid(kit):
		return
	GameWorld.follow(world, get_viewport().get_camera_3d())
	if Game.state == "playing":
		Game.time_played += dt
		kit.hud_tick(dt)
	elif Game.state == "menu":
		menu_cam.global_transform = kit.menu_view()

func _unhandled_input(event: InputEvent) -> void:
	if kit == null:
		return
	if event.is_action_pressed("pause"):
		if Game.state == "playing":
			Game.set_state("paused")
			get_tree().paused = true
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
			ui.show_pause(true)
		elif Game.state == "paused":
			_resume()
	elif event is InputEventMouseButton and event.pressed and Game.state == "playing" and Input.mouse_mode == Input.MOUSE_MODE_VISIBLE:
		_capture()

func _resume() -> void:
	ui.show_pause(false)
	get_tree().paused = false
	Game.set_state("playing")

func _enter_tree() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS

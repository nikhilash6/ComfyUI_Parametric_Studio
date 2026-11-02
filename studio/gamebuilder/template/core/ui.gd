class_name GameUI
extends CanvasLayer
## Every word on screen, in a real font. Nothing here comes from an image model.

signal play_pressed
signal intro_done
signal retry_pressed
signal dialog_closed
signal chosen(index: int)

var font: Font
var heavy: FontVariation
var accent := Color("#f5c518")
var ink := Color("#f6f4ee")
var panel_bg := Color(0.03, 0.03, 0.035, 0.92)
var root: Control
var menu: Control
var intro: Control
var hud: Control
var dialog: Control
var picker: Control
var pause_panel: Control
var end_panel: Control
var flash_rect: ColorRect
var hud_left: Label
var hud_right: Label
var hud_center: Label
var toast_label: Label
var hint_label: Label
var _toast_t := 0.0
var _intro_i := 0
var _intro_lines: Array = []
var _intro_label: Label
var _pick_buttons: Array = []
var last_focus: Control
var dialog_open := false
var choice_open := false

func _ready() -> void:
	layer = 10
	process_mode = Node.PROCESS_MODE_ALWAYS
	accent = Game.palette("accent", accent)
	var path := "res://game/fonts/Archivo.woff2"
	if ResourceLoader.exists(path):
		font = load(path)
	else:
		font = ThemeDB.fallback_font
	heavy = FontVariation.new()
	heavy.base_font = font
	heavy.variation_embolden = 0.9
	root = Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var theme := Theme.new()
	theme.default_font = font
	theme.default_font_size = 20
	root.theme = theme
	add_child(root)
	_style_buttons(theme)
	_build_hud()

func _style_buttons(theme: Theme) -> void:
	var n := StyleBoxFlat.new()
	n.bg_color = Color(1, 1, 1, 0.08)
	n.border_color = Color(1, 1, 1, 0.3)
	n.set_border_width_all(1)
	n.set_corner_radius_all(4)
	n.content_margin_left = 22
	n.content_margin_right = 22
	n.content_margin_top = 10
	n.content_margin_bottom = 10
	var f := n.duplicate()
	f.bg_color = accent
	f.border_color = accent
	theme.set_stylebox("normal", "Button", n)
	theme.set_stylebox("hover", "Button", f)
	theme.set_stylebox("focus", "Button", f)
	theme.set_stylebox("pressed", "Button", f)
	theme.set_color("font_color", "Button", ink)
	var dark := Color("#141006")
	theme.set_color("font_hover_color", "Button", dark)
	theme.set_color("font_focus_color", "Button", dark)
	theme.set_color("font_pressed_color", "Button", dark)
	theme.set_font_size("font_size", "Button", 22)

func _label(parent: Node, text: String, size := 20, c := Color.TRANSPARENT, bold := false) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", c if c.a > 0.0 else ink)
	if bold:
		l.add_theme_font_override("font", heavy)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(l)
	return l

func _fill(c: Color, parent: Control = root) -> ColorRect:
	var r := ColorRect.new()
	r.color = c
	r.set_anchors_preset(Control.PRESET_FULL_RECT)
	parent.add_child(r)
	return r

func _button(parent: Node, text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.pressed.connect(func() -> void:
		Game.sfx("click", 1.0, -8.0)
		cb.call())
	parent.add_child(b)
	return b

func _vbox(parent: Control, anchor: int, margin := 48) -> VBoxContainer:
	var m := MarginContainer.new()
	m.set_anchors_preset(anchor)
	if anchor == Control.PRESET_FULL_RECT or anchor == Control.PRESET_BOTTOM_WIDE or anchor == Control.PRESET_LEFT_WIDE:
		for side in ["left", "right", "top", "bottom"]:
			m.add_theme_constant_override("margin_" + side, margin)
	parent.add_child(m)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 12)
	m.add_child(v)
	return v

# ---------- title
func show_menu(kit: KitBase) -> void:
	_clear_panels()
	menu = Control.new()
	menu.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(menu)
	var art_path := "res://game/art/title.png"
	if ResourceLoader.exists(art_path):
		var t := TextureRect.new()
		t.texture = load(art_path)
		t.set_anchors_preset(Control.PRESET_FULL_RECT)
		t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		t.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		menu.add_child(t)
	var shade := _fill(Color(0.02, 0.02, 0.025, 0.46), menu)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var v := _vbox(menu, Control.PRESET_FULL_RECT, 56)
	var title := _label(v, Game.t("title", "Untitled").to_upper(), 84, accent, true)
	title.add_theme_constant_override("line_spacing", -12)
	_label(v, Game.t("tagline"), 26)
	var spacer := Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(spacer)
	var how := _label(v, kit.controls_text, 18, Color("#cfcfc8"))
	how.custom_minimum_size.x = 620
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	v.add_child(row)
	var play := _button(row, "PLAY", func() -> void: play_pressed.emit())
	_button(row, "CREDITS", _show_credits)
	if not OS.has_feature("web"):
		_button(row, "QUIT", func() -> void: get_tree().quit())
	play.grab_focus()
	_show_note_ai(v)

func _show_note_ai(v: Control) -> void:
	_label(v, "Made with Parametric Studio. Art, models and music were generated by AI models or drawn by code: see Credits.", 14, Color("#b6b6ae"))

func _show_credits() -> void:
	var box := Control.new()
	box.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(box)
	_fill(Color(0.02, 0.02, 0.025, 0.97), box)
	var v := _vbox(box, Control.PRESET_FULL_RECT, 48)
	_label(v, "CREDITS", 54, accent, true)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(scroll)
	var inner := VBoxContainer.new()
	inner.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(inner)
	for row in Game.credits:
		_label(inner, "%s: %s. %s" % [row.get("what", ""), row.get("made_by", ""), row.get("licence", "")], 16)
	var back := _button(v, "BACK", func() -> void: box.queue_free())
	back.grab_focus()

func _clear_panels() -> void:
	for p in [menu, intro, end_panel]:
		if p != null and is_instance_valid(p):
			p.queue_free()
	menu = null
	intro = null
	end_panel = null

# ---------- story card
func show_intro(kit: KitBase) -> void:
	_clear_panels()
	intro = Control.new()
	intro.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(intro)
	_fill(Color(0.02, 0.02, 0.025, 0.72), intro)
	var v := _vbox(intro, Control.PRESET_FULL_RECT, 72)
	_label(v, Game.t("title", "").to_upper(), 40, accent, true)
	var sp := Control.new()
	sp.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(sp)
	_intro_lines = Game.spec.get("story", {}).get("intro", [])
	_intro_i = 0
	_intro_label = _label(v, _intro_lines[0] if _intro_lines.size() > 0 else "", 30)
	_label(v, kit.goal_text(), 22, accent)
	var sp2 := Control.new()
	sp2.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(sp2)
	var go := _button(v, "CONTINUE", _next_intro)
	go.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	go.grab_focus()

func _next_intro() -> void:
	_intro_i += 1
	if _intro_i < _intro_lines.size():
		_intro_label.text = str(_intro_lines[_intro_i])
		return
	if intro != null:
		intro.queue_free()
		intro = null
	intro_done.emit()

# ---------- during play
func _build_hud() -> void:
	hud = Control.new()
	hud.set_anchors_preset(Control.PRESET_FULL_RECT)
	hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud.visible = false
	root.add_child(hud)
	var gr := GradientTexture2D.new()
	gr.fill = GradientTexture2D.FILL_RADIAL
	gr.fill_from = Vector2(0.5, 0.5)
	gr.fill_to = Vector2(1.2, 0.5)
	var g := Gradient.new()
	g.colors = PackedColorArray([Color(0, 0, 0, 0), Color(0, 0, 0, 0.22)])
	g.offsets = PackedFloat32Array([0.55, 1.0])
	gr.gradient = g
	var vig := TextureRect.new()
	vig.texture = gr
	vig.set_anchors_preset(Control.PRESET_FULL_RECT)
	vig.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	vig.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud.add_child(vig)
	flash_rect = ColorRect.new()
	flash_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	flash_rect.color = Color(1, 1, 1, 0)
	flash_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud.add_child(flash_rect)
	hud_left = _hud_label(Control.PRESET_TOP_LEFT, 24, HORIZONTAL_ALIGNMENT_LEFT, Vector2(24, 16))
	hud_right = _hud_label(Control.PRESET_TOP_RIGHT, 24, HORIZONTAL_ALIGNMENT_RIGHT, Vector2(-424, 16))
	hud_center = _hud_label(Control.PRESET_CENTER_TOP, 26, HORIZONTAL_ALIGNMENT_CENTER, Vector2(-300, 16))
	toast_label = _hud_label(Control.PRESET_CENTER, 42, HORIZONTAL_ALIGNMENT_CENTER, Vector2(-500, -140))
	toast_label.size = Vector2(1000, 120)
	toast_label.add_theme_color_override("font_color", accent)
	toast_label.add_theme_font_override("font", heavy)
	hint_label = _hud_label(Control.PRESET_CENTER_BOTTOM, 22, HORIZONTAL_ALIGNMENT_CENTER, Vector2(-400, -70))
	hint_label.size = Vector2(800, 50)

func _hud_label(anchor: int, size: int, align: int, offset: Vector2) -> Label:
	var l := Label.new()
	l.set_anchors_preset(anchor)
	l.horizontal_alignment = align
	l.position = offset
	l.size = Vector2(600 if anchor == Control.PRESET_CENTER_TOP else 400, 40)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", ink)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	l.add_theme_constant_override("outline_size", 6)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud.add_child(l)
	return l

func show_hud(_kit: KitBase) -> void:
	_clear_panels()
	hud.visible = true

func toast(text: String, seconds := 2.2) -> void:
	toast_label.text = text
	_toast_t = seconds

## A moment of colour over the whole picture: red when hurt, gold on a big pickup.
func flash(c: Color, strength := 0.35) -> void:
	flash_rect.color = Color(c.r, c.g, c.b, strength)
	var tw := create_tween()
	tw.tween_property(flash_rect, "color:a", 0.0, 0.28)

func hint(text: String) -> void:
	hint_label.text = text

func hearts_text(n: int, of: int) -> String:
	return "HP " + "♥".repeat(maxi(n, 0)) + "♡".repeat(maxi(of - n, 0))

func _process(dt: float) -> void:
	if _toast_t > 0.0:
		_toast_t -= dt
		if _toast_t <= 0.0:
			toast_label.text = ""

# ---------- talking
func say(who: String, text: String) -> void:
	_close_dialog()
	dialog_open = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	dialog = PanelContainer.new()
	var st := StyleBoxFlat.new()
	st.bg_color = panel_bg
	st.border_color = accent
	st.border_width_top = 3
	st.content_margin_left = 28
	st.content_margin_right = 28
	st.content_margin_top = 18
	st.content_margin_bottom = 18
	dialog.add_theme_stylebox_override("panel", st)
	dialog.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	dialog.offset_top = -210
	root.add_child(dialog)
	var v := VBoxContainer.new()
	dialog.add_child(v)
	_label(v, who.to_upper(), 22, accent, true)
	_label(v, text, 24)
	var ok := _button(v, "OK", _dialog_ok)
	ok.size_flags_horizontal = Control.SIZE_SHRINK_END
	ok.grab_focus()
	Game.sfx("talk", 1.0, -10.0)

func _dialog_ok() -> void:
	_close_dialog()
	dialog_closed.emit()

func _close_dialog() -> void:
	if dialog != null and is_instance_valid(dialog):
		dialog.queue_free()
	dialog = null
	dialog_open = false

func choice(title: String, options: Array) -> void:
	choice_open = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	picker = PanelContainer.new()
	var st := StyleBoxFlat.new()
	st.bg_color = panel_bg
	st.border_color = accent
	st.set_border_width_all(2)
	st.content_margin_left = 34
	st.content_margin_right = 34
	st.content_margin_top = 26
	st.content_margin_bottom = 26
	picker.add_theme_stylebox_override("panel", st)
	picker.set_anchors_preset(Control.PRESET_CENTER)
	picker.grow_horizontal = Control.GROW_DIRECTION_BOTH
	picker.grow_vertical = Control.GROW_DIRECTION_BOTH
	root.add_child(picker)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	picker.add_child(v)
	_label(v, title, 30, accent, true)
	_pick_buttons = []
	for i in options.size():
		var idx: int = i
		var b := _button(v, str(options[i]), func() -> void: _picked(idx))
		_pick_buttons.append(b)
	if _pick_buttons.size() > 0:
		_pick_buttons[0].grab_focus()

func _picked(i: int) -> void:
	choice_open = false
	if picker != null:
		picker.queue_free()
		picker = null
	chosen.emit(i)

func focus_choice(i: int) -> void:
	if i < _pick_buttons.size():
		_pick_buttons[i].grab_focus()

# ---------- pause and end
func show_pause(on: bool) -> void:
	if not on:
		if pause_panel != null:
			pause_panel.queue_free()
			pause_panel = null
		return
	pause_panel = Control.new()
	pause_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(pause_panel)
	_fill(Color(0, 0, 0, 0.6), pause_panel)
	var v := _vbox(pause_panel, Control.PRESET_FULL_RECT, 72)
	_label(v, "PAUSED", 64, accent, true)
	var go := _button(v, "RESUME", func() -> void: get_parent()._resume())
	go.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	var again := _button(v, "START OVER", func() -> void: retry_pressed.emit())
	again.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	go.grab_focus()

func show_end(won: bool, kit: KitBase) -> void:
	hud.visible = false
	_close_dialog()
	end_panel = Control.new()
	end_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(end_panel)
	_fill(Color(0.02, 0.02, 0.025, 0.55), end_panel)
	var v := _vbox(end_panel, Control.PRESET_FULL_RECT, 72)
	_label(v, "YOU WIN" if won else "NOT THIS TIME", 92, accent if won else ink, true)
	_label(v, Game.t("story.win" if won else "story.lose"), 28)
	if kit.has_method("end_stats"):
		_label(v, kit.end_stats(), 24, Color("#cfcfc8"))
	var sp := Control.new()
	sp.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(sp)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	v.add_child(row)
	var again := _button(row, "PLAY AGAIN", func() -> void: retry_pressed.emit())
	if not OS.has_feature("web"):
		_button(row, "QUIT", func() -> void: get_tree().quit())
	again.grab_focus()

class_name GameWorld
## Sky, sun, fog and weather from the spec's setting.

const LOOKS := {
	"day": {"exposure": 0.95, "sky": 0.9, "ambient": 0.45, "sun": 1.15, "sun_color": Color("#fff2dc"), "fog_dark": 0.0},
	"golden": {"exposure": 1.05, "sky": 0.7, "ambient": 0.5, "sun": 1.25, "sun_color": Color("#ffb877"), "fog_dark": 0.25},
	"night": {"exposure": 0.85, "sky": 0.35, "ambient": 0.2, "sun": 0.35, "sun_color": Color("#9fb4ff"), "fog_dark": 0.55},
}

## True when the scene is lit low enough that lamps should be on.
static func dim() -> bool:
	var time := str(Game.spec.get("setting", {}).get("time", "day"))
	return time == "night" or (time == "golden" and str(Game.spec.get("kit", "")) == "mystery")

static func build(parent: Node3D) -> void:
	var st: Dictionary = Game.spec.get("setting", {})
	var time := str(st.get("time", "day"))
	var weather := str(st.get("weather", "clear"))
	var sky_top := Game.palette("sky", Color("#4a86c8"))
	var horizon := Game.palette("horizon", sky_top.lerp(Color.WHITE, 0.55))
	var ground := Game.palette("ground", Color("#55624a"))
	var mat: Material
	if ResourceLoader.exists("res://game/art/sky.png"):
		var pano := PanoramaSkyMaterial.new()
		pano.panorama = load("res://game/art/sky.png")
		mat = pano
	else:
		var proc := ProceduralSkyMaterial.new()
		proc.sky_top_color = sky_top
		proc.sky_horizon_color = horizon
		proc.ground_horizon_color = horizon
		proc.ground_bottom_color = horizon.lerp(ground, 0.25)
		mat = proc
	# One table of light for the time of day, measured from play-test frames: a day scene should sit around mid-grey with almost nothing clipped, dusk and night lower.
	var look: Dictionary = LOOKS.get(time, LOOKS["day"]).duplicate()
	var moody := str(Game.spec.get("kit", "")) == "mystery"
	if moody:
		look.sky *= 0.8
		look.ambient *= 0.85
		look.sun *= 0.9
	if mat is PanoramaSkyMaterial:
		mat.energy_multiplier = look.sky
	elif mat is ProceduralSkyMaterial:
		mat.energy_multiplier = look.sky
	var sky := Sky.new()
	sky.sky_material = mat
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = look.ambient
	env.ambient_light_sky_contribution = 0.7
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = look.exposure
	env.tonemap_white = 6.0
	env.adjustment_enabled = true
	env.adjustment_contrast = 1.12 if moody else 1.05
	env.adjustment_saturation = 0.9 if moody else 1.0
	env.fog_enabled = true
	env.fog_light_color = horizon.darkened(look.fog_dark)
	env.fog_light_energy = look.sky
	env.fog_density = {"fog": 0.02, "rain": 0.011, "snow": 0.011, "overcast": 0.007}.get(weather, 0.0045)
	if str(Game.spec.get("kit", "")) in ["kart", "quest"]:
		env.fog_density *= 0.45       # wide open places: see the far side of the valley
	env.fog_sky_affect = 0.0
	if not OS.has_feature("web"):
		env.glow_enabled = true
		env.glow_intensity = 0.45
		env.glow_bloom = 0.0
		env.glow_hdr_threshold = 1.3
	var w := WorldEnvironment.new()
	w.environment = env
	parent.add_child(w)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = {"night": Vector3(-55, 40, 0), "golden": Vector3(-18, -60, 0)}.get(time, Vector3(-55, -35, 0))
	sun.light_color = look.sun_color
	sun.light_energy = look.sun * ({"overcast": 0.7, "rain": 0.65, "fog": 0.65, "snow": 0.6}.get(weather, 1.0))
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	sun.directional_shadow_max_distance = 55.0
	parent.add_child(sun)
	sun.shadow_opacity = 0.9
	if weather in ["rain", "snow"]:
		_weather(parent, weather)
	else:
		_motes(parent, time)

## Warm dust or fireflies in the air: it's what makes empty air read as air. It follows the camera (see follow).
static func _motes(parent: Node3D, time: String) -> void:
	var p := CPUParticles3D.new()
	p.name = "Weather"
	p.amount = 70
	p.lifetime = 6.0
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	p.emission_box_extents = Vector3(16, 6, 16)
	p.direction = Vector3(0.3, 0.2, 0.1)
	p.spread = 180.0
	p.gravity = Vector3.ZERO
	p.initial_velocity_min = 0.1
	p.initial_velocity_max = 0.5
	var m := SphereMesh.new()
	m.radius = 0.03
	m.height = 0.06
	m.radial_segments = 6
	m.rings = 3
	var c := Color("#fff2c0") if time != "night" else Color("#bfe0ff")
	m.material = U.flat_mat(c, 1.0, 0.8)
	p.mesh = m
	parent.add_child(p)

static func follow(parent: Node3D, camera: Camera3D) -> void:
	var w: Node3D = parent.get_node_or_null("Weather")
	if w != null and camera != null:
		w.global_position = camera.global_position + Vector3.UP * (10.0 if w is CPUParticles3D and w.amount >= 300 else 0.0)

static func _weather(parent: Node3D, kind: String) -> void:
	var p := CPUParticles3D.new()
	p.name = "Weather"
	p.amount = 500 if kind == "rain" else 300
	p.lifetime = 1.1 if kind == "rain" else 5.0
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	p.emission_box_extents = Vector3(22, 0.5, 22)
	p.direction = Vector3.DOWN
	p.spread = 3.0
	p.gravity = Vector3.ZERO
	p.initial_velocity_min = 22.0 if kind == "rain" else 1.5
	p.initial_velocity_max = 28.0 if kind == "rain" else 2.5
	var m := BoxMesh.new()
	m.size = Vector3(0.015, 0.45, 0.015) if kind == "rain" else Vector3(0.05, 0.05, 0.05)
	m.material = U.flat_mat(Color(0.8, 0.85, 1.0, 1.0), 1.0, 0.5)
	p.mesh = m
	p.position = Vector3(0, 16, 0)
	parent.add_child(p)

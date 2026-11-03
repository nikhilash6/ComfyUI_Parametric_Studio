# PSN nodes

Original nodes for safe scripting and pipeline control. These core nodes need only the Python 3.12 standard library.
- `PSN_Expression`: maths/conditions/strings with a whitelist evaluator. It never calls eval/exec: no attribute access, bounded size and results.
- `PSN_SandboxScript`: run LLM- or user-written Python in a separate resource-limited process (import allow-list, no network or files, timeout). Defence in depth, not an OS sandbox.
- `PSN_Branch` (lazy if/else), `PSN_QualityGate`, `PSN_AttemptPlanner`: pipeline control; `psn.orchestration.retry` is the same logic for the backend.
- `psn.graph.GraphBuilder`: build API-format graphs in code and validate them against `/object_info` before queueing.
Install: link this repository into `ComfyUI/custom_nodes/` and restart ComfyUI (see [INSTALL.md](../INSTALL.md)). Tests: `python -m pytest tests`.

## Subagents (`PSN_Subagent`, `PSN_SubagentFanOut`)

Role-based model workers whose answers are **checked by code before they count**, and who can **act**, not only read. A role is a job: an output contract (JSON schema), the tools it may call, a budget
(steps, tokens, seconds) and a verifier. The verifier checks the answer against the task context (a quote must exist in the source, a graph must validate, code must pass its tests) and, for
acting roles, against what the tools **really did**: a builder that claims "tests passed" is rejected unless `run_bash` recorded that exact command exiting 0. Problems go back to the model and it retries.

| Role | Job | Tools |
|---|---|---|
| `writer` | Write a document/page from supplied facts only. | - |
| `classifier` | Pick exactly one label from a closed set. | - |
| `coder` | Write Python that parses, passes the supplied tests and avoids banned operations. | run_python |
| `judge` | Score a candidate against a rubric. | - |
| `fact_checker` | Check claims against a source text; every 'supported' needs a verbatim quote. | - |
| `researcher` | Find facts in the local knowledge base and cite file + verbatim quote. | kb_search, read_file |
| `planner` | Split a goal into dependent steps, each assigned to a real role. | - |
| `captioner` | Describe an image: caption plus lowercase tags; SFW wording only. | - |
| `prompt_enhancer` | Expand a short idea into a model-ready prompt without dropping the subject. | - |
| `sfw_guard` | Decide whether text is safe for the SFW contest; a keyword filter can force 'no'. | - |
| `graph_builder` | Build a ComfyUI API-format graph that validates against the live /object_info and uses no partner node. | validate_graph |
| `graph_debugger` | Fix a failing graph and say what changed; the fixed graph must validate. | validate_graph |
| `summarizer` | Condense text without inventing numbers or dropping required facts. | - |
| `extractor` | Pull structured fields out of text; every value must appear in the source. | - |
| `red_team` | Produce distinct adversarial test cases for a prompt, graph or code. | - |
| `license_auditor` | Judge licences from the actual licence text; restrictive wording forces open_ok=false. | - |
| `vram_steward` | Decide run / wait / evict / refuse for a GPU job so the 4 GB floor is never broken. | vram_status |
| `builder` | Implement a change in its own workspace: write files, run tests, report only what the tools recorded. | kb_search, read_file, write_file, edit_file, run_bash, request_approval |
| `operator` | Run a named ComfyUI workflow safely and report the real job and its output files. | list_workflows, vram_status, run_workflow, request_approval |
| `router` | Choose which role should handle a task. | - |

Acting tools: `write_file`/`edit_file` (inside the run's private workspace only), `run_bash` (one command, checked by `guard.py`: no rm/kill/pip/systemctl restart, no credential paths, no writes outside the
workspace), `run_workflow` (a NAMED template on the local ComfyUI; refused if the queue is busy, the VRAM floor would break, or the values are not SFW), `git_commit` (work branches `qwen-*`/`subagent-*` of repos the
task lists; never main, never a push), `fetch_url` (public pages, GET only). There is **no tool that posts, sends, publishes, spends, restarts, deletes or installs**: `request_approval` files a request
(`python3 -m psn.subagents.approvals list|approve ID|deny ID`) and the subagent stops.

Also built in: a subagent cannot start another one; concurrency is capped (`PSN_SUBAGENT_MAX`, default 8); every run is logged to `~/.local/state/parametric_studio/subagents.jsonl` with a private (mode 600)
transcript; the Open edition only talks to loopback model servers (`PSN_EDITION=extended` allows others). Models are chosen per role through named endpoints (`PSN_SUBAGENT_ENDPOINTS`; default is the local
Qwen on :8002). Add a role: one entry in `psn/subagents/roles.py` plus a good/bad case in `tests/test_subagents.py`.

## Maths, logic and geometry when building a graph

Which node to reach for when a graph (yours, Pro mode's, or one `graph_builder` writes) needs a number worked out, a yes or no, or a mesh cleaned. Core and PSN nodes load in every install. The pack rows are Pack Lab results: those packs are not part of the install, and nothing here installs them.

| Need | Use | Where it comes from |
|---|---|---|
| Any formula over a few numbers, typed as text (`a * 2`, `max(a, b)`, `a > b`) | `ComfyMathExpression` (FLOAT, INT and BOOL out; exponents capped) | core |
| A formula that also handles lists and strings | `PSN_Expression` (whitelist evaluator, never calls eval) | PSN |
| If/else, switch, and/or/not | `ComfySwitchNode`, `BranchNode`, `ComfyAndNode`, `ComfyOrNode`, `ComfyNotNode`; `PSN_Branch` for a lazy if/else | core, PSN |
| Width and height from a picked size | `ResolutionSelector`, `ResolutionBucket` | core |
| One operation from a dropdown instead of a typed formula; a comparison that returns BOOLEAN; an op that runs only when a condition is true; Vec2/3/4 maths (dot, distance, cross, normalize); an aspect ratio at a megapixel budget rounded to a multiple | `CM_FloatBinaryOperation`, `CM_IntBinaryOperation`, `CM_FloatBinaryCondition`, `CM_ChooseFloat`, `CM_*OperationConditional`, `CM_Vec3ToScalarBinaryOperation`, `CM_AspectRatioResolution` and 57 more | ComfyMath-NG (`rabanti-github/ComfyMath`, Apache-2.0). **Pack Lab only.** On 2026-11-02 it loaded with 64 nodes and no name clash, and its values set an SD 1.5 render's size, CFG and steps. Its integer `Factorial`, `Pow` and `Shl` have no size cap, so a shared graph can keep a server busy |
| Clean a generated mesh: weld, decimate to a face budget, remesh, fill small holes, smooth normals, unwrap UVs, rotate, merge, measure, render | `WeldVertices`, `DecimateMesh`, `RemeshMesh`, `FillHoles`, `MeshSmoothNormals`, `UnwrapMesh`, `RotateMesh`, `MergeMeshes`, `GetMeshInfo`, `RenderMesh` (load a GLB with `Load3DAdvanced` then `Get3DComponents`) | core. Proof on the 3D page |
| Boolean, alpha wrap, self-intersection repair, skeleton, surface from points | nothing in core | ComfyUI-GeometryPack (GPL-3.0-or-later) has them, but it **was not installed or tested**: it needs `comfy-env` and `comfy-3d-viewers` from pip, and a separate environment it downloads. That needs the owner's OK |

Demo graphs, each with what it proved: `studio/web/pack_lab_demos/`. The vector types (`VEC2`, `VEC3`, `VEC4`) feed no core node; break them out to FLOAT first.

<!-- node reference: generated by scripts/build_node_docs.py, do not edit by hand -->

## Node reference

546 nodes: 7 in the V3 flagship pack and 539 more under 14 areas. By the code audit of 2026-11-01: 158 do real work on images, latents, audio or files, or call a service; 262 are honest utilities (maths, text, config); 102 build a plan or a payload for something else. Those last two groups load no model and render nothing, even when the name sounds bigger. 22 do not work on real ComfyUI inputs yet: PSN_AsTypeConverter, PSN_ArchCompatibilityChecker, PSN_AudioDrivenNoise, PSN_AudioScheduler, PSN_Chunked_Conditioning_Builder, PSN_GoldenSampler, PSN_HDR_Tone_Map, PSN_Latent_Inpaint_Decode, PSN_Latent_Inpaint_Encode, PSN_MasterSongCopy, PSN_Music_Master, PSN_News_Script_Generator, PSN_OCIO_Color_Grade, PSN_Peek_Visualizer, PSN_Quality_Metrics, PSN_Register_Resident_Model, PSN_SpectralScheduler, PSN_StepLifecycleMachine, PSN_StyleGAN_Direction_Apply, PSN_StyleGAN_Direction_Discover, PSN_Video_In_PNG_Decode, PSN_Video_In_PNG_Encode. 3 weak duplicates are hidden from the Add Node menu and keep working in old graphs. Written from the live classes by `scripts/build_node_docs.py`.

## Flagship pack (V3)

Written for `comfy_api.latest`, under `Parametric/Flagship`. A lazy switch is not included because core ships `ComfySwitchNode`.

### Director Prompt (`PSN_DirectorPrompt`)

Writes a one-camera-move video prompt the way the Studio's Director does: idea, shot size, camera move, lens, light and mood. Pick a move and only that move's controls appear.

| Input | Type | What it does |
|---|---|---|
| `idea` | STRING | What happens in the shot, in plain words. |
| `camera` | choice that reveals controls | One camera move per shot: models follow one clear move far better than several. |
| | `locked` | no controls |
| | `dolly_in` | reveals `pace` |
| | `dolly_out` | reveals `pace` |
| | `orbit_left` | reveals `pace`, `arc` |
| | `orbit_right` | reveals `pace`, `arc` |
| | `crane_up` | reveals `pace` |
| | `crane_down` | reveals `pace` |
| | `pan_left` | reveals `pace` |
| | `pan_right` | reveals `pace` |
| | `tilt_up` | reveals `pace` |
| | `tracking` | reveals `speed` |
| | `handheld` | reveals `sway` |
| | `dolly_zoom` | reveals `pace` |
| `shot` | COMBO | Shot size. auto writes nothing. |
| `lens` | COMBO | Lens look. auto writes nothing. |
| `lighting` | COMBO | Light. auto writes nothing. |
| `mood` | COMBO | Mood. auto writes nothing. |

Outputs: `prompt` (STRING).

### Graph Proof (`PSN_GraphProof`)

Writes a JSON file beside your output: a SHA-256 of the exact graph that ran, every node's settings and a hash of the pixels. The same graph always gives the same hash, so anyone can check a result. Values under names like api_key are redacted first. Nothing leaves this machine.

| Input | Type | What it does |
|---|---|---|
| `filename_prefix` | STRING | Where to write it, inside the output folder. |
| `images` (optional) | IMAGE | Optional: the images this graph made, so their pixels are hashed too. |
| `note` (optional) | STRING | Optional note stored in the file. |

Outputs: `graph_sha256` (STRING), `proof_path` (STRING).

### Latent Inspector (`PSN_LatentInspector`)

Shows what a sampler is working on, with no VAE: every channel, the three strongest directions as colour, or a histogram per channel. The stats output gives each channel's numbers and a plain reading: noise, part way or structured. Compare it before and after a sampler.

| Input | Type | What it does |
|---|---|---|
| `latent` | LATENT | Any image or video latent. |
| `view` | choice that reveals controls | What to draw. |
| | `channel_grid` | reveals `columns`, `per_channel`, `scale` |
| | `pca_rgb` | reveals `clip_percent`, `scale` |
| | `histogram` | reveals `bins` |
| `batch_index` | INT | Which item of the batch to inspect. |
| `frame` | INT | Which frame of a video latent to inspect. Ignored for images. |

Outputs: `view` (IMAGE), `stats` (STRING).

### Recast Prompt (`PSN_RecastPrompt`)

Writes a character replacement prompt with the reference tags the Studio's Recast goal uses (<Video N>, <Picture N>). Describe the target to replace, not the scene.

| Input | Type | What it does |
|---|---|---|
| `target` | STRING | Who to replace in the video. Describe the target, not the scene. |
| `direction` | STRING | Optional extra direction, added at the end. |
| `video_ref` | INT | Which reference video the tag points at. |
| `picture_ref` | INT | Which reference picture the tag points at. |

Outputs: `prompt` (STRING), `reference_tags` (STRING).

### Shot Card (`PSN_ShotCard`)

Draws a shot's text on a plain card, on the CPU with no model. Shot List uses it for a free storyboard pass before spending GPU time.

| Input | Type | What it does |
|---|---|---|
| `text` | STRING | The shot text. |
| `number` | INT | The shot number on the card. |
| `width` | INT | Card width in pixels. |
| `height` | INT | Card height in pixels. |

Outputs: `image` (IMAGE).

### Shot List (`PSN_ShotList`)

Connect any number of shot prompts. When it runs, this node turns itself into one render graph per shot and joins the results, so ComfyUI runs and tracks each shot as its own node. Storyboard draws cards on the CPU and needs no model.

| Input | Type | What it does |
|---|---|---|
| `shots` | grows as you connect | Shot prompts, in order. |
| `render` | choice that reveals controls | storyboard draws a card for each shot on the CPU. sampler renders each shot with your model. |
| | `storyboard` | reveals `width`, `height` |
| | `sampler` | reveals `model`, `clip`, `vae`, `negative`, `width`, `height`, `seed`, `steps`, `cfg`, `sampler_name`, `scheduler` |

Outputs: `images` (IMAGE), `shot_count` (INT), `shot_prompts` (STRING).

### VRAM Gate (`PSN_VRAMGate`)

Passes its input through only when free VRAM covers this step's peak plus a safety margin; otherwise everything downstream stops with a plain reason instead of an out-of-memory crash. Works with any type.

| Input | Type | What it does |
|---|---|---|
| `value` | any (output follows input) | Anything: passed through unchanged when the gate is open. |
| `peak_gb` | FLOAT | The most memory the next step will use, in GB. |
| `margin_gb` | FLOAT | Memory to keep free on top of the peak, in GB. |
| `free_idle_models` | BOOLEAN | When short, first unload models this ComfyUI holds idle, then measure again. Never touches other programs. |

Outputs: `value` (any (output follows input)), `free_gb` (FLOAT), `status` (STRING).

## 3D

| Node | What it does | Inputs | Outputs |
|---|---|---|---|
| 3D Camera Projection (Ortho)<br>`PSN_3D_Camera_Projection` | Projects 3D mesh vertices to 2D using orthographic camera math. | `mesh_data`, `camera_angle` | STRING, STRING |
| 3D Mesh Validator & Normalizer<br>`PSN_3D_Mesh_Validator` | Validates and normalizes 3D mesh data provided as JSON. | `mesh_json`, `normalize` | STRING, STRING |
| 3D Mesh to Image<br>`PSN_3D_To_Image` | Render a 3D mesh to a 2D image using simple orthographic projection with flat shading and painter's algorithm. | `mesh`, `camera_angle`, `lighting` | IMAGE |
| PSN Aspect Ratio Enforcer<br>`PSN_AspectRatioEnforcer` | Plan aspect-ratio adjustment (crop/pad/resize) for an image/latent tensor. | `width`, `height`, `target_ratio`, `mode` | INT, INT, STRING |
| Battlemap Generator<br>`PSN_Battlemap_Generate` | Generates a top-down battlemap as a 2D array of RGB colors and a corresponding heightmap for 3D rendering pipelines. | `width`, `height`, `cell_size`, `style`, `seed` | MAP_DATA, HEIGHTMAP_DATA |
| Boolean Mask Operation<br>`PSN_BooleanMaskOperation` | Combine two masks with boolean logic (and / or / xor / difference). | `mask_a`, `mask_b`, `operation` | MASK |
| Cube Preview Render<br>`PSN_Cube_Preview_Render` | Renders a built-in unit cube orthographically (clay or shaded) at a camera angle around the Y axis. | `render_mode`, `camera_angle` | IMAGE, STRING |
| PSN Depth To Point Cloud<br>`PSN_Depth_To_PointCloud` | Back-project an IMAGE + DEPTH_MAP through camera intrinsics into a 3D point cloud. | `IMAGE`, `DEPTH_MAP`, `CAMERA_INTRINSICS` | TENSOR, TENSOR |
| Interpreter Registry Build<br>`PSN_InterpreterRegistryBuild` | Build an :class:`InterpreterRegistry` from a list of family specs. | `root`, `platform`, `families`, `venv_name`, `default_family` | INTERPRETER_REGISTRY |
| Interpreter Resolve<br>`PSN_InterpreterResolve` | Resolve the interpreter path for a given tool family. | `registry`, `family` | STRING, BOOLEAN |
| Interpreter Spec Info<br>`PSN_InterpreterSpecInfo` | Return the full spec dict for a family as a JSON-ish string (for UI display). | `registry`, `family` | STRING |
| Load 3D Mesh<br>`PSN_Load_3D_Mesh` | Loads a mesh from an .obj file path, inline 'obj:' text, or the word 'cube'. | `mesh_path`, `normalize` | MESH |
| MatrixGame Parameter Check (loads nothing)<br>`PSN_MatrixGame_ParamCheck` | Validates the model_path and device strings only and returns them as a dict. | `model_path`, `device` | DICT, STRING |
| Multi-View 2D Shift Preview<br>`PSN_MultiView_Shift_Preview` | Rolls and shifts the input image once per view with 2D geometry. | `image`, `num_views`, `angles` | IMAGE |
| PSN Panorama Stitch (Equirectangular Planner)<br>`PSN_Panorama_Stitch` | Plan an equirectangular 360-degree panorama stitch from overlapping frames. | `num_frames`, `fov`, `overlap`, `projection`, `blend_mode`, `out_width`, `out_height` | STRING, STRING, FLOAT, STRING |
| PSN Point Cloud To Mesh<br>`PSN_PointCloud_To_Mesh` | Builds a triangle mesh from a point cloud by convex hull, open3d ball pivoting, or the raw 3D Delaunay triangulation. | `POINT_CLOUD`, `COLORS`, `METHOD` | TRIMESH |
| ProcGen Optical Illusion<br>`PSN_ProcGen_OpticalIllusion` | Generate an optical-illusion image (moire, spiral, grid_distortion). | `illusion_type`, `width`, `height`, `intensity` | IMAGE |
| ProcGen Patterns<br>`PSN_ProcGen_Patterns` | Generate a procedural pattern image (checker, gradient, halftone, starburst, binary). | `pattern_type`, `width`, `height`, `param_1`, `param_2`, `seed` | IMAGE, STRING |
| Procedural Pattern Generator (Mask)<br>`PSN_ProceduralPatternGenerator` | Generate a deterministic procedural mask (perlin / voronoi / sine / fractal). | `width`, `height`, `pattern_type`, `scale`, `seed` | MASK |
| PSN Schematic Annotation<br>`PSN_Schematic_Annotation` | Validates annotation parameters and emits a JSON payload describing a text label with a leader line. | `text`, `position_x`, `position_y`, `font_size` | STRING |
| PSN Schematic Overlay<br>`PSN_Schematic_Overlay` | Validates schematic overlay parameters and emits a JSON payload describing the overlay to apply (blueprint / wireframe / grid). | `overlay_type`, `line_color`, `opacity` | STRING |
| Stereo 3D Video Converter (Plan)<br>`PSN_Stereo_Converter` | Validate a 2D video + depth-map pair and plan its stereo 3D conversion. | `video_desc`, `depth_desc`, `parallax`, `format`, `depth_min`, `depth_max` | BOOLEAN, STRING, STRING, STRING |
| PSN Tile Plan and Stitch (renders nothing)<br>`PSN_Tile_Plan_Stitch` | Plans a tile grid and stitches tiles you supply; renders nothing, and says so in its status when no tiles are given instead of returning the input as if processed. | `image`, `tile_size`, `overlap`, `blend_mode`, `tile_images` | ANY, STRING, STRING |
| Tripo Image-to-3D Request Builder<br>`PSN_Tripo_Image_Request_Builder` | Builds request JSON for a Tripo image-to-model task, with the first image frame encoded as a base64 PNG. | `image`, `texture` | STRING |
| Tripo Text-to-3D Request Builder<br>`PSN_Tripo_Text_Request_Builder` | Builds request JSON for a Tripo text-to-model task from the prompt. | `prompt`, `texture`, `pbr` | STRING |
| VR180 Projection Conversion<br>`PSN_VR180_Convert` | Convert a rectilinear image to VR180 (cylindrical) projection. | `image`, `fov` | IMAGE |
| VRM Pose Editor (Edit)<br>`PSN_VRMPoseEditor_Edit` | Validate a VRM path, parse a pose, apply one edit, and emit a preview token. | `vrm_model_path`, `pose_data`, `edit_mode`, `joint_name`, `delta_x`, `delta_y`, `delta_z` | STRING, STRING, STRING |

## Agents

| Node | What it does | Inputs | Outputs |
|---|---|---|---|
| Agent Schema Check (runs no agents)<br>`PSN_AgentSchemaCheck` | Validates the starting payload against each agent's declared schema along the handoff chain. | `latent`, `pipeline`, `style` | LATENT, STRING |
| Agent Aggregator<br>`PSN_Agent_Aggregator` | Aggregates results from all agents into a single output structure. | `results` | ANY |
| Agent Loop Init<br>`PSN_Agent_Loop_Init` | Initializes the loop state for batched multi-model agent orchestration. | `model_ids`, `agent_config` | ANY, INT |
| Agent Planner (Validator)<br>`PSN_Agent_Planner` | Validates an LLM-generated JSON graph plan against available node schemas. | `goal`, `available_nodes`, `plan_json`, `llm_connection` | STRING, STRING, BOOLEAN |
| Agent String Transform (calls no model)<br>`PSN_Agent_Transform_Sim` | Applies a configured string transform (identity, prefix, suffix, uppercase, lowercase, reverse) to the fixed text input_for_<model_id> for each model id in turn. | `loop_state`, `current_index`, `model_id` | ANY, INT, BOOLEAN |
| Caption Auditor<br>`PSN_Caption_Auditor` | Validate a caption against banned and allowed term lists. | `caption`, `allowed_terms`, `banned_terms` | BOOLEAN, STRING |
| Image Stats Caption (no VLM)<br>`PSN_Image_Stats_Caption` | Writes a template caption from the image's mean brightness, contrast and dominant RGB tone. | `image`, `caption_style` | STRING |
| LLM Agent Init (ParametricStudio)<br>`PSN_LLM_Agent_Init` | Initialize an LLM agent with a provider, model and system prompt. | `provider`, `model_name`, `system_prompt`, `api_key` | AGENT_INSTANCE |
| Build LLM Chat Request JSON (ParametricStudio)<br>`PSN_LLM_Chat_Request_Build` | Builds an OpenAI-style chat request as JSON text from an agent config and a message. | `agent_instance`, `user_message`, `history` | STRING |
| PSN LLM Context Orchestrator<br>`PSN_LLM_Context_Orchestrator` | Updates the LLM context with new provider settings, preserving history. | `provider_type`, `model_id`, `context` | PSN_LLM_CONTEXT |
| PSN LLM History Manager<br>`PSN_LLM_History_Manager` | Appends a message to conversation history and trims if it exceeds max length. | `context`, `new_message`, `role`, `max_length` | STRING |
| PSN LLM Offloader<br>`PSN_LLM_Offloader` | Builds offload commands and parses responses for LLM VRAM offloading. | `trigger`, `offload_target`, `model_id`, `api_response`, `last_trigger_time` | STRING, FLOAT, STRING |
| LLM Prompt Expander<br>`PSN_LLM_PromptExpander` | Formats a prompt expansion request for a local LLM. | `raw_prompt`, `llm_model_path`, `temperature` | STRING, BOOLEAN, STRING |
| LLM Prompt Refiner<br>`PSN_LLM_Prompt_Refiner` | Formats an LLM request payload for prompt refinement and parses the response. | `raw_prompt`, `llm_endpoint`, `api_key`, `system_prompt`, `api_format`, `llm_response` | STRING, STRING, STRING, STRING |
| LLM Route Decision (local or cloud, calls no LLM)<br>`PSN_LLM_Route_Decision` | Scores prompt complexity (length + keywords) and returns the route 'local' or 'cloud' plus the prompt prefixed with [LOCAL] or [CLOUD]. | `task_prompt`, `complexity_threshold`, `resource_guard_ok` | STRING, STRING |
| Ollama Prompt Enhancer<br>`PSN_Ollama_Prompt_Enhancer` | Expands a short prompt with a local Ollama model via POST /api/generate. | `short_prompt`, `style`, `max_tokens`, `ollama_url`, `model_name` | STRING, STRING, STRING |
| Prompt Style Template (filler words stripped, fixed tokens added, no LLM)<br>`PSN_PromptStyleTemplate` | Strips filler words and appends a style profile's fixed quality tokens and default negative prompt. | `prompt`, `style`, `weight`, `add_negative` | STRING, STRING, INT |
| Role Text Concatenator (no agents, no LLM)<br>`PSN_Role_Text_Concat` | Appends the text you supply for each listed role (from a JSON object) to the brief, in role order. | `brief`, `roles`, `role_text_json` | STRING, STRING |
| PSN Subagent (verified)<br>`PSN_Subagent` | Run one verified subagent. | `role`, `task`, `context_json`, `endpoint`, `max_attempts`, `max_seconds`, `image` | STRING, STRING, BOOLEAN, STRING, STRING |
| PSN Subagent Fan-Out<br>`PSN_SubagentFanOut` | Run the same role on many tasks at once (one task per line, or a JSON list) and join the verified answers: first_ok, vote, all, or merge. | `role`, `tasks`, `join`, `context_json`, `max_parallel`, `endpoint` | STRING, STRING, INT, BOOLEAN |

## Audio

| Node | What it does | Inputs | Outputs |
|---|---|---|---|
| Audio Driven Noise<br>`PSN_AudioDrivenNoise` | Analyzes audio frequency spectrum (simplified) and modulates noise intensity. | `audio`, `latent`, `sensitivity`, `seed` | FLOAT |
| Audio Scheduler<br>`PSN_AudioScheduler` | Generate a sigma schedule tailored for audio diffusion models. | `steps`, `scheduler_type`, `sigma_max`, `sigma_min` | SIGMAS |
| Audio To Mouth Track<br>`PSN_AudioToMouthTrack` | Derive a synchronized mouth-openness track from an audio waveform. | `audio`, `face_image`, `fps`, `sample_rate` | STRING, FLOAT |
| PSN Audio Amplitude Extractor<br>`PSN_Audio_Amplitude_Extractor` | Extract a normalized amplitude curve from a JSON list of audio samples. | `audio`, `window_size`, `hop_size`, `band`, `sample_rate` | STRING, FLOAT |
| Audio JSON Smooth, Half Gain and Normalize<br>`PSN_Audio_Json_Smooth_Gain_Normalize` | Applies a 5-sample moving average, a dB gain to the first half and a dB gain to the second half of the samples (by time position), and peak normalization, on audio given as JSON text. | `audio`, `smooth`, `gain_first_half_db`, `gain_second_half_db`, `normalize` | STRING |
| PSN Audio Loader (Validation)<br>`PSN_Audio_Loader` | Validates audio file parameters and computes metadata for a standardized audio load. | `file_path`, `sample_rate`, `channels`, `byte_count`, `bits_per_sample` | STRING, FLOAT, BOOLEAN, STRING |
| Audio Notification Payload (plays nothing)<br>`PSN_Audio_Notify_Payload` | Validates notification settings (sound_file extension, volume) and formats a JSON payload. | `sound_file`, `volume` | BOOLEAN, STRING, STRING |
| PSN Audio Reactive Driver<br>`PSN_Audio_Reactive_Driver` | Map a [0,1] curve to [min_val, max_val] with optional smoothing. | `curve`, `target_param`, `min_val`, `max_val`, `smoothing`, `frame_index` | FLOAT, STRING |
| Audio Sweep Config<br>`PSN_Audio_Sweep_Config` | Defines and validates the parameter space for an audio sweep. | `x_param`, `x_values`, `y_param`, `y_values` | PSN_AUDIO_SWEEP_CONFIG |
| Audio Sweep Plan<br>`PSN_Audio_Sweep_Plan` | Expands a sweep config into an ordered list of parameter combinations. | `sweep_config` | LIST, LIST |
| Audio Waveform Layout<br>`PSN_Audio_Waveform_Layout` | Computes the grid geometry for a waveform visualization. | `clip_count`, `cols`, `rows`, `canvas_w`, `canvas_h` | INT, INT, INT, LIST |
| MIDI Reactive Visualizer (Music)<br>`PSN_MIDI_Visualizer` | Parse MIDI note events (as JSON or pipe-delimited text) and emit a JSON video payload whose frames react to note activity, velocity energy, and pitch span. | `midi_data`, `visual_style`, `sensitivity`, `fps`, `duration` | STRING, STRING |
| Mask Weight Check (composites nothing)<br>`PSN_Mask_Weight_Check` | Clamps per-frame mask coverage to 0..1 and checks that the base video, mouth track and mask lists have the same frame count. | `base_video`, `mouth_track`, `mask` | FLOAT |
| PSN Music Master<br>`PSN_Music_Master` | Apply a pure-Python mastering chain to a plain audio payload. | `audio`, `target_loudness`, `eq_preset` | AUDIO, FLOAT |
| Music Request Plan (generates no audio)<br>`PSN_Music_Plan` | Validates a music request (prompt, duration, seed, model id) and emits it as a JSON plan. | `prompt`, `duration`, `seed`, `model_id` | STRING, BOOLEAN |
| PSN Audio Cue Selector (plays nothing)<br>`PSN_Notif_Select` | Picks a notification cue name and expected file path from an allow-list and range-checks the volume. | `sound_type`, `volume` | BOOLEAN, STRING, STRING |
| RVC Preprocess (segment + normalize)<br>`PSN_RVC_Preprocess` | Cut audio into fixed-length segments and peak-normalise each one. | `audio`, `sample_rate`, `segment_seconds`, `keep_tail` | AUDIO, INT, INT |
| RVC Train Model (tiny torch autoencoder)<br>`PSN_RVC_Train_Model` | Train a tiny torch autoencoder on preprocessed segments (CPU). | `segments`, `epochs`, `batch_size`, `lr`, `seed` | LATENT, FLOAT, FLOAT |
| PSN Sep Mix (Stem Gain Mixing)<br>`PSN_Sep_Mix` | Mix a list of stems with per-stem gains (pure gain-mixing math). | `stems`, `gains`, `stem_names` | STRING, FLOAT, BOOLEAN, STRING |
| PSN Source Separation Plan (JSON)<br>`PSN_Sep_Plan` | Validates a source-separation request and returns a JSON plan (model, sample count, sample rate, stem names, default gains). | `audio`, `model`, `sample_rate` | STRING, STRING |
| Wave Motion Synthesizer<br>`PSN_Wave_Motion_Synthesizer` | Combine two wave functions to create deterministic, wave-driven motion. | `wave_1`, `wave_2`, `operation`, `num_frames`, `current_frame` | STRING, FLOAT, STRING |

## Character

| Node | What it does | Inputs | Outputs |
|---|---|---|---|
| Band Colour Threshold Mask<br>`PSN_BandColorThresholdMask` | Heuristic brightness/saturation/redness threshold inside a fixed vertical band of the image. | `image`, `rule` | MASK |
| PSN Character Prompt Builder<br>`PSN_Character_Prompt_Builder` | Assemble a structured character prompt from modular text blocks. | `identity`, `hair_style`, `hair_color`, `accessories`, `pose`, `outfit`, `background`, `style_modifiers`, `include_negative`, `character_type`, `max_length` | STRING, STRING |
| Face Preserve Inpaint (Plan)<br>`PSN_Face_Preserve_Inpaint` | Plan and validate face identity preservation for inpainting. | `face_model`, `identity_strength`, `mask` | STRING, BOOLEAN, STRING |

## Data

| Node | What it does | Inputs | Outputs |
|---|---|---|---|
| CSV Batch Prompter<br>`PSN_CSV_Batch_Prompter` | Parse CSV text into batches of prompts, negatives, and reference image paths. | `csv_text`, `positive_col`, `negative_col`, `batch_size`, `ref_image_col` | STRING, STRING, STRING, INT |
| CSV Batch Reader<br>`PSN_CSV_Batch_Reader` | Reads a CSV string and returns the current row's prompt and parameters. | `csv_text`, `row_index` | STRING, DICT, BOOLEAN, INT, STRING |
| CryptIO Decrypt (RSA-OAEP)<br>`PSN_CryptIO_Decrypt` | Decrypt Base64 RSA-OAEP data with a private key (PEM) back to a string. | `encrypted_data`, `private_key` | STRING |
| CryptIO Encrypt (RSA-OAEP)<br>`PSN_CryptIO_Encrypt` | Encrypt a string with RSA-OAEP (public key, PEM) and output Base64. | `data`, `public_key` | STRING |
| PSN Data Getter<br>`PSN_Data_Getter` | Retrieves data from a named global variable. | `name`, `default` | ANY |
| PSN Dataset Loader CSV<br>`PSN_Dataset_Loader_CSV` | Parse CSV text into structured rows and column names. | `file_path`, `csv_text`, `delimiter`, `header_row` | LIST, LIST, STRING |
| Exact Arithmetic (ParametricStudio)<br>`PSN_ExactArithmetic` | Evaluate an arithmetic expression exactly (no LLM guessing). | `expression`, `fallback` | FLOAT, STRING |
| PSN Excel Loadout Reader<br>`PSN_Excel_Loadout_Reader` | Extracts a specific parameter value from a selected loadout row. | `row_data`, `param_name`, `header_row` | STRING, STRING |
| PSN Excel Loadout Selector<br>`PSN_Excel_Loadout_Selector` | Select a loadout row from tabular text by name or index. | `table_text`, `loadout_name`, `delimiter`, `use_index`, `index_value`, `sheet_name`, `excel_path` | LIST, INT, STRING |
| PSN File List Manager<br>`PSN_File_List_Manager` | Filter a list of file names by a glob pattern. | `directory`, `pattern`, `file_names` | STRING, INT, STRING |
| GSheet Cell Selector<br>`PSN_GSheet_Cell_Selector` | Extracts a specific value from the loaded sheet matrix. | `matrix`, `row`, `col` | STRING |
| PSN Int to Float List<br>`PSN_IntToFloatList` | Convert a list of integers to a list of floats. | `int_list` | LIST[FLOAT] |
| PSN JSON Metadata Extractor<br>`PSN_JSON_Metadata_Extractor` | Extract and merge metadata from image metadata JSON and workflow JSON. | `image_metadata`, `workflow`, `include_workflow_nodes`, `max_depth` | STRING, BOOLEAN, STRING |
| PSN Key Retriever<br>`PSN_Key_Retriever` | Retrieve a stored API key or sensitive value by name. | `key_name` | STRING |
| PSN Key Store<br>`PSN_Key_Store` | Store an API key or sensitive value in the in-memory key store. | `key_name`, `key_value` | BOOLEAN |
| PSN List to String<br>`PSN_ListToString` | Join a list of strings into a single string using a delimiter. | `list_input`, `delimiter` | STRING |
| PSN Prompt Document Lookup (pasted JSON, no database)<br>`PSN_Prompt_Document_Lookup` | Looks up an id in a JSON mapping of id to {prompt, params} that you paste in. | `documents_json`, `doc_id` | STRING, STRING, BOOLEAN, STRING |
| Random Asset Selector<br>`PSN_Random_Asset_Selector` | Randomly selects `count` assets from `asset_list` using a fixed `seed` for reproducibility. | `asset_list`, `seed`, `count` | STRING |
| PSN ScRNA Cluster (Leiden Config)<br>`PSN_ScRNA_Cluster` | Validates and prepares configuration for Leiden clustering on normalized single-cell RNA-seq data. | `adata_norm`, `resolution`, `n_neighbors` | STRING, INT, STRING |
| PSN ScRNA Normalize<br>`PSN_ScRNA_Normalize` | Normalize a single-cell expression matrix to a target sum per cell, optionally applying log1p. | `adata`, `target_sum`, `log1p` | OBJECT |
| PSN ScRNA to Latent<br>`PSN_ScRNA_to_Latent` | Converts single-cell clustering results into a latent space representation for diffusion model visualization. | `adata_clustered`, `cluster_id`, `latent_dim`, `seed` | FLOAT, STRING |
| Sheet Parameter Loop<br>`PSN_Sheet_Parameter_Loop` | Iterate through rows in a sheet matrix to generate multiple parameter sets. | `matrix`, `start_row`, `end_row`, `header_row` | LIST, INT |
| PSN Website Builder<br>`PSN_SiteBuilder` | Build a small, offline, SFW static website from a brief (JSON: name, tagline, about, pages, facts{email,phone,address,hours}, brand colour). | `brief_json`, `output_name`, `export_to_dyad` | STRING, BOOLEAN, STRING |
| PSN String to List<br>`PSN_StringToList` | Split a string into a list of strings using a delimiter. | `string_input`, `delimiter` | LIST[STRING] |

## Flow

| Node | What it does | Inputs | Outputs |
|---|---|---|---|
| Accumulate JSON<br>`PSN_Accumulate_Json` | Append a generated image path to the JSON list in the context. | `item`, `ctx` | PSN_CTX, STRING |
| PSN Attempt Planner<br>`PSN_AttemptPlanner` | Seed/cfg/steps for retry attempt N (use with a quality gate and a batch or the studio's retry loop). | `attempt`, `attempts`, `base_seed`, `cfg`, `cfg_step`, `steps`, `steps_step` | INT, FLOAT, INT, STRING |
| PSN Batch Size Optimizer<br>`PSN_Batch_Calculator` | Calculate the optimal image batch size from available VRAM and model size. | `vram_available_gb`, `model_size_gb`, `per_image_vram_gb`, `min_batch`, `max_batch`, `safety_margin_pct` | INT, FLOAT, STRING |
| PSN Batch Conditioning Loop<br>`PSN_Batch_Conditioning_Loop` | Validates a batch of conditioning specs and produces a sampling plan. | `conditioning_list`, `steps`, `cfg`, `seed`, `max_batch_size` | BATCH_PLAN, INT |
| Batch Filter Chain<br>`PSN_Batch_Filter_Chain` | Apply a JSON-defined sequence of filters to a whole image batch. | `image_batch`, `filter_chain`, `parallel` | IMAGE |
| PSN Batch Invariant Sampler<br>`PSN_Batch_Invariant_Sampler` | Pure-logic inference-plan builder for batch-invariant, deterministic sampling. | `model_id`, `positive_id`, `negative_id`, `latent_id`, `seed`, `steps`, `cfg`, `sampler_name`, `scheduler`, `device` | STRING, STRING |
| PSN Batch Iterator<br>`PSN_Batch_Iterator` | Step through a list of prompts, returning the current prompt and whether the batch is complete. | `prompt_list_json`, `auto_advance`, `index` | STRING, INT, BOOLEAN |
| PSN Batch Prompt Loader<br>`PSN_Batch_Prompt_Loader` | Parse a CSV or JSON text payload into a list of prompt strings. | `payload`, `format`, `delimiter` | STRING |
| Batch Prompt Loop<br>`PSN_Batch_Prompt_Loop` | Extract the next prompt from a list and update the loop context. | `prompts`, `loop_ctx` | STRING, PSN_CTX |
| Boolean Logic<br>`PSN_Boolean_Logic` | Performs a boolean operation (AND, OR, NOT, XOR) on inputs a and b. | `a`, `b`, `operation` | BOOLEAN |
| PSN Branch (if/else)<br>`PSN_Branch` | If/else: only the chosen input is evaluated (lazy), so the other branch's nodes never run. | `condition`, `on_true`, `on_false` | * |
| Check Graph (validate API JSON vs object_info)<br>`PSN_CheckGraph` | Validate an API-format ComfyUI graph JSON against /object_info JSON. | `graph_json`, `object_info_json` | STRING, BOOLEAN |
| Dependency Graph Cycle Check<br>`PSN_DependencyGraphCycleCheck` | Validate that a pipeline dependency graph is acyclic. | `edges` | BOOLEAN, STRING, STRING |
| Dict Router<br>`PSN_Dict_Router` | Validates and renames dict entries between input_map and output_map. | `router_id`, `input_map`, `output_map`, `inputs` | DYNAMIC, STRING |
| PSN Dynamic Switch<br>`PSN_Dynamic_Switch` | Routes data from one of multiple inputs to a single output based on a boolean condition or an index. | `input_1`, `input_2`, `condition`, `use_index`, `index`, `input_3`, `input_4` | ANY |
| PSN Error Catcher<br>`PSN_Error_Catcher` | Checks for errors in the output; if error, captures message. | `output`, `error_flag`, `error_message` | *, STRING |
| PSN Expression (safe)<br>`PSN_Expression` | Evaluate a safe expression (maths, comparisons, strings, lists). | `expression`, `a`, `b`, `c`, `d` | *, FLOAT, INT, STRING, BOOLEAN |
| PSN Fixed Seed Generator<br>`PSN_Fixed_Seed_Generator` | Generates a deterministic seed from a base seed and batch index. | `base_seed`, `batch_index`, `mode` | INT |
| Folder Batch Queue (Images)<br>`PSN_Folder_Batch_Queue` | Filters, sorts and limits a manifest of image files and decodes each file's bytes into an IMAGE. | `manifest`, `sort_order`, `file_pattern`, `max_files` | LIST[IMAGE], LIST[STRING], INT |
| PSN Graph Cleaner<br>`PSN_Graph_Cleaner` | Removes orphaned nodes from a graph structure. | `graph` | DICT |
| PSN Graph Standardizer<br>`PSN_Graph_Standardizer` | Rewrite an API graph into the Loader-Controller-Sampler naming pattern. | `graph_json` | STRING, STRING |
| Group Bypass (ParametricStudio)<br>`PSN_Group_Bypass` | Emit a bypass signal for a named workflow group. | `group_id`, `enabled` | BOOLEAN |
| Idempotent Project Structure Setup<br>`PSN_IdempotentProjectStructureSetup` | Check a project file tree for missing boilerplate and inject it. | `project`, `boilerplate`, `inject` | STRING, STRING, INT, INT |
| PSN Iteration Toggle<br>`PSN_Iteration_Toggle` | Alternates between `mode_a` (even iterations) and `mode_b` (odd iterations) based on `current_iteration` parity. | `current_iteration`, `total_iterations`, `mode_a`, `mode_b` | ANY, BOOLEAN |
| PSN List Filter<br>`PSN_List_Filter` | Filters an input list based on a specified condition. | `input_list`, `condition_type`, `custom_func` | LIST |
| PSN List Processor<br>`PSN_List_Processor` | Performs operations on lists: SORT, REVERSE, UNIQUE, or SLICE. | `list`, `operation`, `start`, `end` | LIST |
| Loop Assembler (Seamless)<br>`PSN_LoopAssembler` | Assemble the final seamless loop of exactly ``loop_length`` frames. | `image`, `loop_length` | IMAGE |
| Loop Preparer (Seamless Blend)<br>`PSN_LoopPreparer` | Blend the last N frames with the first N frames for a seamless loop. | `image`, `loop_length`, `blend_frames` | IMAGE |
| PSN Node Inspector (hidden)<br>`PSN_Node_Inspector` | Render a text tree and a Graphviz DOT string of the node graph. Hidden from the menu: use PSN_NodeInspector instead. | `graph_json` | STRING, STRING |
| PSN Param Hub (Set)<br>`PSN_ParamHub` | ComfyUI custom node that stores parameters in a shared dictionary. | `param_name`, `value`, `scope`, `value_int`, `value_str` | PARAM_HUB, BOOLEAN, STRING |
| PSN Param Hub (Read)<br>`PSN_ParamHubRead` | ComfyUI custom node that reads a parameter from the shared hub. | `param_name`, `scope`, `default_value` | FLOAT, BOOLEAN, STRING |
| PSN Param Orchestrator<br>`PSN_ParamOrchestrator` | Centralized parameter orchestration: adapts CFG, steps, sampler and scheduler based on model metadata, pipeline type and quality preset. | `model`, `pipeline_type`, `quality` | DICT, MODEL |
| PSN Pipeline Router<br>`PSN_Pipeline_Router` | Route data to a pipeline based on its type label and a JSON route map. | `data_type`, `data`, `route_map` | ANY, STRING |
| PSN Preset Loader<br>`PSN_PresetLoader` | Loads a predefined workflow preset from a JSON string. | `preset_name`, `preset_dir`, `preset_json` | GRAPH |
| PSN Build Preset JSON Text<br>`PSN_Preset_Json_Build` | Builds preset JSON text from a workflow graph and returns it. | `graph` | STRING |
| Prompt Weight Variation Specs (no conditioning)<br>`PSN_Prompt_Weight_Variation_Specs` | Generates seeded weight/bias variation spec dicts for a prompt string. | `base_conditioning`, `variation_type`, `num_variations`, `magnitude`, `seed`, `base_weight`, `base_bias` | CONDITIONING_LIST |
| PSN Quality Gate<br>`PSN_QualityGate` | Pass the value through when score meets the threshold, otherwise output the fallback. | `score`, `threshold`, `mode`, `value`, `fallback` | BOOLEAN, *, STRING |
| PSN Replay Verifier<br>`PSN_Replay_Verifier` | Compares the hash of the current run's image data with a stored reference hash. | `image_data`, `reference_hash`, `run_id`, `algorithm` | STRING, BOOLEAN, STRING, STRING |
| Request Router (Video/Music/Image)<br>`PSN_Request_Router` | Route a payload to the video / music / image lane by request type. | `request_type`, `payload`, `default_route` | ANY, ANY, ANY, STRING |
| PSN Retry Switch<br>`PSN_Retry_Switch` | If retry_count < max_retries, adjusts parameters and signals retry. | `error_message`, `retry_count`, `max_retries`, `base_steps`, `base_cfg` | BOOLEAN, PSN_BUNDLE |
| Role Catalogue (build)<br>`PSN_RoleCatalogue` | Build a role catalogue from a JSON description of studio entries. | `catalogue_json` | ROLE_CATALOGUE, STRING |
| Role Resolve (pipeline step)<br>`PSN_RoleResolve` | Resolve an abstract role id to a concrete studio entry + settings. | `catalogue`, `role_id`, `overrides_json`, `latent` | STRING, STRING, BOOLEAN |
| PSN Sandboxed Script<br>`PSN_SandboxScript` | Run Python in a separate, resource-limited process (import allow-list, no network, no files, timeout). | `code`, `input_json`, `timeout_s`, `memory_mb` | STRING, BOOLEAN, STRING, STRING |
| PSN Set Operation<br>`PSN_Set_Operation` | Performs set operations on two sets. | `set_a`, `set_b`, `operation` | SET |
| Stage Finish (Auto/Manual)<br>`PSN_StageFinish` | Finish a pipeline stage: auto-approve or queue for manual review based on mode. | `stage_name`, `mode`, `score`, `threshold` | STRING, STRING, FLOAT |
| Stage Finish Batch<br>`PSN_StageFinishBatch` | Finish multiple pipeline stages at once; returns a summary tensor of states. | `stage_names`, `mode`, `scores`, `threshold` | STRING, FLOAT |
| PSN State Container<br>`PSN_State_Container` | Stores a value in a session-scoped state dictionary keyed by `key`. | `key`, `value` | DICT |
| PSN State Retriever<br>`PSN_State_Retriever` | Retrieves a value from a state dictionary, returning `default` if absent. | `state`, `key`, `default` | ANY |
| Step Lifecycle State Machine<br>`PSN_StepLifecycleMachine` | Shared state machine for step lifecycle management. | `machine_id`, `steps`, `deps`, `action`, `target_step` | MASK, STRING |
| Subgraph Port<br>`PSN_SubgraphPort` | Typed entry/exit point for a subgraph. | `port_name`, `data_type`, `value` | DYNAMIC, STRING |
| Type Caster<br>`PSN_Type_Caster` | Converts an input value to a target type (STRING, INT, FLOAT, BOOLEAN). | `value`, `target_type`, `default_value` | ANY |
| PSN Type Inspector<br>`PSN_Type_Inspector` | Inspect a plain Python value and report its type label and shape. | `data` | STRING, LIST |
| VRAM Budget Compare (typed numbers, reads no GPU)<br>`PSN_VRAM_Budget_Compare` | Compares a usage number you type against a budget number you type; reads no GPU. | `budget_gb`, `usage_gb` | BOOLEAN, STRING |
| Workflow Browser<br>`PSN_Workflow_Browser` | Browser node for curated workflows. | `workflow_index_json`, `category`, `search_term`, `selection_index` | STRING, STRING |
| PSN Workflow Configurator<br>`PSN_Workflow_Configurator` | A node that acts as a central registry for workflow parameters. | `config_name`, `scope`, `key`, `mode`, `value`, `inherit` | *, STRING, BOOLEAN |
| PSN Workflow Orchestrator<br>`PSN_Workflow_Orchestrator` | Plan parallel workflow segments and compare the VRAM needed with a typed number. | `workflow_json`, `max_parallel`, `vram_per_instance`, `vram_available_gb` | LIST, STRING |
| Workflow Plugin Descriptor Builder (registers nothing)<br>`PSN_Workflow_Plugin_Descriptor` | Validates a workflow graph and its input/output schemas and wraps them into a plugin descriptor JSON. | `graph_json`, `plugin_name`, `input_schema`, `output_schema` | DICT |
| PSN YAML Batch Definer<br>`PSN_YAML_Batch_Definer` | Parses a YAML batch definition and a base ComfyUI API-format JSON graph, then generates a list of parameterized graph JSON strings for batch execution. | `yaml_content`, `base_graph`, `seed_base` | LIST, DICT |

## Image

| Node | What it does | Inputs | Outputs |
|---|---|---|---|
| ACES Output Setting Check (no image)<br>`PSN_ACES_OutputConfig_Check` | Checks an ACES output-space / tone-mapping / exposure setting against the allowed values and returns config_valid or config_invalid with the reason. | `output_space`, `tone_mapping`, `exposure`, `config_json` | STRING, STRING |
| ASCII Image To ASCII<br>`PSN_ASCII_ImageToASCII` | Convert a 2D luminance grid to an ASCII art string and a preview grid. | `grid`, `width`, `character_set`, `invert` | STRING, STRING |
| Aesthetic Bias Patch<br>`PSN_Aesthetic_Bias_Patch` | Biases the model toward a specific aesthetic by preparing a bias patch payload. | `aesthetic_vector`, `strength`, `vector_list` | BOOLEAN, STRING, STRING |
| Auto Color Adapt (ParametricStudio)<br>`PSN_AutoColorAdapt` | Automatically adjust color grading parameters from image statistics. | `image`, `model_family`, `target_style` | IMAGE, STRING |
| Auto Aspect Ratio Crop (SDXL/Flux)<br>`PSN_Auto_Aspect_Crop` | Crop an image to a target SDXL/Flux aspect ratio (center/face/smart). | `image`, `target_ratio`, `crop_mode`, `custom_w`, `custom_h` | IMAGE, INT, INT |
| Batch Color Correction and Masking (ParametricStudio)<br>`PSN_BatchColorMod` | Apply a color correction to a batch of images, masked per pixel. | `images`, `correction_type`, `params_json`, `masks` | IMAGE |
| Batch Resize & Pad for Datasets<br>`PSN_Batch_Resize_Pad` | Resize each image in a batch to fit a target box (aspect preserved) and pad to uniform size. | `images`, `target_width`, `target_height`, `pad_color` | IMAGE |
| CV BBox Standardizer<br>`PSN_CV_BBoxStandardizer` | Standardize bounding box formats and extract spatial metadata. | `bboxes`, `input_format`, `output_format`, `image_width`, `image_height` | LIST, STRING |
| CV FOV Estimator<br>`PSN_CV_FOVEstimator` | Estimates FOV and tilt from line segments using geometric projection. | `lines_json`, `image_width`, `image_height`, `reference_width` | FLOAT, FLOAT, FLOAT |
| Frequency Domain Artifact Detection<br>`PSN_CV_FrequencyArtifact` | Detect high-frequency artifacts via Radial Average Amplitude Spectrum. | `image`, `artifact_threshold` | IMAGE, FLOAT, BOOLEAN |
| CV Lighting Corrector<br>`PSN_CV_LightingCorrector` | Estimates light direction and adjusts exposure/white balance. | `image`, `correction_strength`, `target_kelvin`, `normal_map` | STRING, STRING, FLOAT |
| CV Line Integrity Check<br>`PSN_CV_LineIntegrity` | Detect straight lines and close gaps in broken contours (technical drawings). | `image`, `gap_threshold`, `min_line_length` | IMAGE, INT, FLOAT |
| CV VRAM Guard<br>`PSN_CV_VRAMGuard` | Decide whether a heavy CV op should run on cuda or cpu based on VRAM usage. | `vram_used_mb`, `threshold_mb`, `device`, `vram_total_mb` | STRING, STRING |
| Civitai-Compatible Image Saver<br>`PSN_Civitai_Compat_Save` | Save an image as PNG with Civitai-compatible metadata. | `image`, `prompt`, `negative_prompt`, `model_name`, `filename_prefix` | STRING |
| Color Space Guard<br>`PSN_ColorSpaceGuard` | Validates and plans color-space conversion for incoming image data. | `vmin`, `vmax`, `vmean`, `expected_space`, `bit_depth`, `auto_fix`, `metadata` | STRING, STRING, STRING, BOOLEAN |
| Composite Grading (Nuke)<br>`PSN_Composite_Grading` | 3-way Lift/Gamma/Gain color correction (Nuke-style grade). | `image`, `lift`, `gamma`, `gain` | IMAGE |
| Composite Mask Generator (Nuke)<br>`PSN_Composite_Mask_Generator` | Generate a soft mask from image luminance (or alpha) with feathering. | `image`, `threshold`, `feather` | MASK |
| Composite Merge (Nuke)<br>`PSN_Composite_Merge` | Merge image_b over image_a using a mask and a blend mode (Nuke-style). | `image_a`, `image_b`, `mask`, `blend_mode` | IMAGE |
| Context-Aware Tile Refinement (Plan)<br>`PSN_Context_Tile_Refine` | Plan context-aware tile refinement for an already-upscaled image. | `width`, `height`, `tile_size`, `overlap`, `blend_mode`, `seam_tolerance`, `left_seam`, `right_seam` | STRING, INT, BOOLEAN, STRING |
| EXR Save Plan (writes nothing)<br>`PSN_EXR_Save_Plan` | Validates an EXR path and compression and estimates the uncompressed size against a free-space number you type. | `height`, `width`, `channels`, `file_path`, `compression`, `free_space` | STRING, STRING |
| Fashion Item Segmenter (ParametricStudio)<br>`PSN_FashionItemSegmenter` | Heuristic fashion-item segmentation (shoes / bags / dresses / all). | `image`, `item_type` | MASK, BBOX |
| Film Grain + Tone LUT (no image input)<br>`PSN_FilmGrainLUT` | Builds a film-stock tone LUT, a seeded uniform grain-noise mask (width*height values) and the highlight threshold where halation would start, all from numbers. | `film_stock`, `iso`, `grain_amount`, `halation`, `width`, `height`, `seed_override` | STRING, STRING, FLOAT, FLOAT |
| PSN Film Stock Preset<br>`PSN_Film_Stock_Preset` | Applies a consistent color grading profile based on a selected film stock name. | `image`, `film_stock`, `intensity`, `custom_lut` | LIST, LIST |
| Gaze Corrector (PSN)<br>`PSN_GazeCorrector` | Compute a bounded correction offset that moves a current gaze vector toward a target gaze vector, scaled by a clamped strength. | `current_gaze`, `target_gaze`, `strength` | FLOAT, FLOAT, BOOLEAN, STRING |
| Gaze Vector Normalize (typed values, no estimation)<br>`PSN_GazeVectorNormalize` | Parses a typed 3D gaze vector and pupil position and returns the unit vector. | `gaze_vector`, `pupil_position` | FLOAT, INT, STRING |
| HDR Colour Config Builder (no pixel conversion)<br>`PSN_HDR_Color_Config` | Validates ICC profile and colour space names and builds a tone-mapping config JSON. | `icc_profile`, `target_colorspace`, `hdr_mode`, `tone_mapping_mode`, `exposure`, `gamma` | BOOLEAN, STRING, STRING |
| HDR Tone Map (ParametricStudio)<br>`PSN_HDR_Tone_Map` | Tone map and color grade HDR images to display range [0, 1]. | `image`, `tone_map_mode`, `exposure`, `saturation` | IMAGE |
| PSN Iterative Morphing Engine<br>`PSN_Iterative_Morphing_Engine` | Generates a Deforum-style iterative morphing schedule. | `wave_function`, `frequency`, `amplitude`, `num_frames`, `motion_strength` | STRING, STRING, INT |
| LAB Space Recolor (ParametricStudio)<br>`PSN_LAB_Recolor` | Recolor an image in CIE-LAB space toward target L/A/B values. | `image`, `target_L`, `target_A`, `target_B`, `strength`, `mask` | IMAGE |
| PSN Latent Forensics<br>`PSN_LatentForensics` | Inspects latent tensor metadata and sampled values for NaNs, Infs, and unexpected shape/dtype changes. | `run_id`, `actual_shape`, `expected_shape`, `actual_dtype`, `expected_dtype`, `sampled_values`, `max_sampled` | STRING, BOOLEAN |
| PSN Latent Inpaint Decode<br>`PSN_Latent_Inpaint_Decode` | Decode an inpaint latent and blend the edited region into the original. | `latent`, `mask_latent`, `vae`, `original_image` | IMAGE |
| PSN Latent Inpaint Encode<br>`PSN_Latent_Inpaint_Encode` | Encode IMAGE + MASK into an inpaint latent and a matching mask latent. | `image`, `mask`, `vae`, `mask_blur` | LATENT, MASK_LATENT |
| Layer Composite (Blend Mode)<br>`PSN_LayerComposite` | Composite a top image over a base image with a blend mode, mask and opacity. | `base_image`, `top_image`, `blend_mode`, `opacity`, `mask` | IMAGE |
| PSN Layout Enforcer<br>`PSN_LayoutEnforcer` | Generate a deterministic layout configuration for a graph. | `graph_id`, `theme`, `grouping_rule`, `nodes` | DICT |
| Log Line Formatter (measures nothing)<br>`PSN_Log_Entry_Formatter` | Formats a JSON log line from node_id, the input_hash you pass in (not computed here) and the current time. | `node_id`, `input_hash` | STRING |
| PSN Luminance / Saturation Mask (Inpainting)<br>`PSN_LuminanceSaturationMask` | Thresholds image luminance or saturation into a binary mask, with optional erode/dilate cleanup. | `image`, `rule_id`, `score_threshold`, `morphology_radius` | MASK, IMAGE |
| PSN Mask Feather<br>`PSN_MaskFeather` | Feathers mask edges with a Gaussian blur for smooth compositing. | `mask`, `feather_radius`, `sigma` | STRING, STRING |
| Master Song Copy<br>`PSN_MasterSongCopy` | Create a mastered copy of a single library song (audio tensor). | `audio`, `name`, `target` | ARTIFACT |
| NAFNet Settings Check (denoises nothing)<br>`PSN_NAFNet_Config_Check` | Validates a NAFNet model name, noise level and image width/height/channels and returns the normalized settings as JSON. | `noise_level`, `model_path`, `image_meta` | BOOLEAN, STRING, STRING |
| Non-Destructive Master Hook (append mastered audio)<br>`PSN_NonDestructiveMasterHook` | Append a loudness-mastered copy of an audio artifact as a NEW artifact. | `artifacts`, `target`, `suffix` | ARTIFACTS, ARTIFACT |
| OCIO Color Grade (ACES)<br>`PSN_OCIO_Color_Grade` | Apply ACES color management to video frames. | `image`, `input_colorspace`, `output_colorspace`, `lut_name`, `ocio_config` | IMAGE |
| PBR Bake Albedo<br>`PSN_PBR_Bake_Albedo` | Convert an image to a clean linear Albedo map (sRGB or Linear input). | `image`, `color_space` | IMAGE |
| PBR Bake Normal<br>`PSN_PBR_Bake_Normal` | Estimate a tangent-space normal map from image luminance (Sobel). | `image`, `strength`, `smoothness` | IMAGE |
| PBR Bake Roughness<br>`PSN_PBR_Bake_Roughness` | Generate a roughness map from local pixel variance. | `image`, `min_roughness`, `max_roughness` | IMAGE |
| PBR Maps from Albedo (heuristic, no delighting)<br>`PSN_PBR_From_Albedo` | Estimates roughness and normal maps from an albedo image with Sobel and local-variance heuristics and can edge-blend them for tiling. | `albedo_image`, `tiled` | IMAGE, IMAGE, IMAGE |
| PSN Param Adjuster<br>`PSN_Param_Adjuster` | Applies suggested parameters from PSN_VLM_Analyzer to the next iteration. | `current_params`, `suggested_params`, `blend_factor` | DICT |
| Patch DCT Shrinkage (list image, not BM3D)<br>`PSN_PatchDCT_Shrink` | Overlapping-patch 2-D DCT soft/hard thresholding on a nested-list grayscale image. | `sigma`, `block_size`, `image`, `threshold_mode`, `vram_budget_bytes` | ANY, FLOAT, STRING, BOOLEAN |
| Point/Box Mask (does not analyse the image)<br>`PSN_PointBoxMask` | Draws a disk around each typed point or a filled box on a blank MASK and multiplies the image by it. | `image`, `point_coords`, `mask_mode` | MASK, IMAGE |
| PSN Prompt Cleaner<br>`PSN_Prompt_Cleaner` | Clean OCR text: strip UI noise, split sections, emit library JSON. | `raw_text`, `remove_ui_elements`, `format_for_library` | STRING, STRING |
| Proportion Adjustment Tool<br>`PSN_ProportionAdjust_Modify` | Adjust pose keypoint proportions toward a target body type. | `pose_keypoint`, `body_type`, `adjustment_strength` | STRING, FLOAT |
| Quality Gate<br>`PSN_Quality_Gate` | Emit needs_upscale=True when quality_score < threshold. | `image`, `quality_score`, `threshold` | BOOLEAN, IMAGE |
| PSN Random Image Selector<br>`PSN_Random_Image_Selector` | Selects random image files from a folder (listed by extension) or from a supplied name list; returns names and paths only, loads no image. | `folder_path`, `num_images`, `seed`, `file_names` | LIST[INT], LIST[STRING], LIST[STRING], STRING |
| PSN Resolution Preset<br>`PSN_Resolution_Preset` | Enforce consistent dimensions and aspect ratios across generation pipelines. | `width`, `height`, `aspect_ratio`, `model_type` | INT, INT, INT |
| PSN Resolution Scaler<br>`PSN_Resolution_Scaler` | Dynamically compute width/height from aspect ratio and megapixel budget. | `aspect_ratio`, `target_megapixels`, `max_width`, `max_height`, `multiple_of` | INT, INT |
| Route Record (creates no connection)<br>`PSN_Route_Record` | Wraps a payload string in a dict recording the source id, target id and a wireless flag. | `source_node_id`, `target_node_id`, `wireless`, `payload` | DICT |
| PSN Steganography Decoder<br>`PSN_Steganography_Decoder` | Extract embedded secret from a watermarked image and check integrity. | `image`, `embedding_key`, `method` | STRING, BOOLEAN |
| PSN Steganography Encoder<br>`PSN_Steganography_Encoder` | Embed invisible metadata/watermark into an image (LSB) and return a key. | `image`, `secret_data`, `method`, `strength` | STRING, STRING |
| TAESD Fast Preview Decode (Plan)<br>`PSN_TAESD_Preview_Decode` | Plan and validate a TAESD fast-preview decode. | `latent_channels`, `latent_width`, `latent_height`, `model_name`, `model_type`, `extra_config` | BOOLEAN, STRING, STRING |
| PSN Split Text Into Line Records<br>`PSN_TextLinesToRegions` | Splits text you supply into one record per non-empty line. | `text` | STRING, STRING |
| Tile Grid Coordinates (PSN)<br>`PSN_TileGrid` | Computes overlapping tile coordinates [x, y, w, h] for an image size. | `width`, `height`, `tile_size`, `overlap` | STRING |
| Tonal Grading Pro<br>`PSN_TonalGradingPro` | Grades an IMAGE (and a sample r,g,b colour) with exposure, brightness, contrast, saturation and per-channel curves from JSON. | `r`, `g`, `b`, `exposure`, `contrast`, `brightness`, `saturation`, `curves_json`, `image` | FLOAT, FLOAT, FLOAT, STRING, IMAGE |
| Trimap Mask Feather<br>`PSN_TrimapMaskFeather` | Builds a trimap by erosion/dilation of a rough mask and diffuses alpha across the unknown band. | `rough_mask`, `fg_radius`, `bg_radius`, `iterations`, `sigma`, `blur_radius` | MASK |
| Typography Artistic Text<br>`PSN_Typography_ArtisticText` | Build a layout description for artistic text rendering. | `text`, `font`, `size`, `effect`, `color` | STRING |
| Upscale Switch<br>`PSN_Upscale_Switch` | Upscale image 2x (bicubic) when flag is True, otherwise pass through unchanged. | `image`, `flag`, `upscaler_model` | IMAGE |
| PSN Workflow Bundle (loader, controller, sampler)<br>`PSN_WorkflowBundle` | Bundles loader output, controller dict and sampler input into one dict; inputs_present only means the controller is a dict and the other two inputs are not None. | `loader_output`, `controller_settings`, `sampler_input`, `log_structure` | DICT, BOOLEAN |
| Workflow Orchestrator (Color Pipeline)<br>`PSN_WorkflowOrchestrator` | Chains multiple color grading ops defined in a JSON workflow into one pass. | `image`, `workflow_json` | IMAGE, STRING |

## Integrations

| Node | What it does | Inputs | Outputs |
|---|---|---|---|
| PSN Deliver To Folder<br>`PSN_DeliverToFolder` | Save images into a watched delivery folder (Eagle, DaVinci Resolve, Nuke, Krita...). | `image`, `name`, `subfolder`, `meta_json` | STRING, BOOLEAN |
| PSN DiscordWebhook<br>`PSN_DiscordWebhook` | Post text and/or an image to a Discord webhook (free). | `content`, `image` | STRING, BOOLEAN |
| PSN FolderRoundtrip<br>`PSN_FolderRoundtrip` | Send an image to an editor via a folder (works with Krita, GIMP, Photoshop...): writes <dir>/out/<name>.png and waits for the edited file in <dir>/in/. | `image`, `directory`, `name`, `wait_s` | IMAGE, BOOLEAN |
| PSN Http Request (restricted)<br>`PSN_HttpRequest` | JSON request to ONE configured API (config section http_api: base_url, optional headers/allowed_hosts). | `method`, `path`, `payload_json` | INT, STRING, BOOLEAN |
| PSN Modal Job Spec (validate only, does not submit)<br>`PSN_Modal_Job_Spec` | Validates a workflow JSON, Modal environment, GPU type and timeout, and builds the job spec as JSON with a content-hash key. | `workflow_json`, `modal_env`, `gpu_type`, `timeout_sec` | STRING, STRING, STRING |
| PSN NtfyNotify<br>`PSN_NtfyNotify` | Free phone push notification via ntfy (ntfy.sh or your own server, e.g. | `message`, `title`, `priority` | STRING, BOOLEAN |
| Nuke Composite (Layers)<br>`PSN_Nuke_Composite` | Nuke-style compositing: blend an overlay over a base with a mask and opacity. | `base_image`, `overlay_image`, `mask`, `blend_mode`, `opacity` | IMAGE |
| NVIDIA VFX Upscale (Plan)<br>`PSN_Nvidia_VFX_Upscale` | Plan an NVIDIA VFX (RTX Video SR) upscale. | `width`, `height`, `scale`, `vfx_model`, `image_json` | BOOLEAN, STRING, INT, INT |
| PSN OSCReceive<br>`PSN_OSCReceive` | Wait for one OSC message on a localhost UDP port (times out). | `port`, `timeout_s` | STRING, STRING, BOOLEAN |
| PSN OSCSend<br>`PSN_OSCSend` | Send an OSC message over UDP (localhost only): TouchDesigner, Resolume, Unreal, Max, VCV... | `host`, `port`, `address`, `args_json` | STRING, BOOLEAN |
| PSN Ray Parallel Sampler<br>`PSN_RayParallelSampler` | Manages multi-GPU sampler setups via Ray (pure-logic planning only). | `num_workers`, `batch_size`, `items_per_task`, `scheduling`, `payload_format` | BOOLEAN, STRING, STRING, INT |
| PSN RemoteQueue<br>`PSN_RemoteQueue` | Queue an API-format graph on a remote ComfyUI (Tailscale/LAN host from the config file) and wait for it. | `prompt_json`, `timeout_s` | BOOLEAN, STRING, STRING, STRING |
| PSN SlackSend<br>`PSN_SlackSend` | Post text to a Slack incoming webhook (free). | `text` | STRING, BOOLEAN |
| TD Control In (Parse)<br>`PSN_TD_Control_Parse` | Parse an incoming OSC-style control message from TouchDesigner into a command string and a float value. | `message` | STRING, FLOAT |
| TD Frame Encode (size only, does not send)<br>`PSN_TD_FrameEncode_Size` | Encodes an IMAGE to the TouchDesigner byte payload and reports its size in bytes. | `image`, `channel` | INT, STRING |
| PSN TelegramPoll<br>`PSN_TelegramPoll` | Check for new commands from allow-listed chats. | `offset`, `commands_json` | INT, STRING, INT, STRING |
| PSN TelegramSend<br>`PSN_TelegramSend` | Send text or an image to an allow-listed Telegram chat (free Bot API; token lives in the config file, not the workflow). | `chat_id`, `text`, `image` | STRING, BOOLEAN |
| Telegram Command Parser (Listener Core)<br>`PSN_Telegram_Command_Parser` | Parse a raw Telegram ``getUpdates`` JSON payload into ComfyUI values. | `updates_json`, `allowed_chat_ids`, `command_prefix`, `timeout_note` | INT, STRING, IMAGE, BOOLEAN |
| Telegram Sender Prep (Upload Core)<br>`PSN_Telegram_Sender_Prep` | Prepare a tensor for upload to Telegram. | `media`, `chat_id`, `caption`, `media_type`, `bot_token` | BOOLEAN, INT, STRING, STRING |
| PSN Telegram Update Parser (does not connect)<br>`PSN_Telegram_Update_Parser` | Parses a pasted Telegram getUpdates JSON string and checks the chat id against an allow-list; does not connect to Telegram. | `allowed_chat_ids`, `updates_payload` | INT, STRING, BOOLEAN, BOOLEAN |

## Models

| Node | What it does | Inputs | Outputs |
|---|---|---|---|
| PSN Architecture Compatibility Checker<br>`PSN_ArchCompatibilityChecker` | Check that a loaded model matches the expected architecture and dtype. | `model`, `expected_arch`, `expected_dtype` | BOOLEAN, STRING |
| PSN Block Offload Manager<br>`PSN_BlockOffloadManager` | ComfyUI-style node that plans block offloading. | `total_blocks`, `offload_blocks`, `mode`, `dry_run` | DICT, STRING, BOOLEAN |
| Checkpoint Best Picker<br>`PSN_CheckpointBestPicker` | Pick the checkpoint with the highest quality score from the registry. | `registry` | STRING, FLOAT, BOOLEAN |
| Checkpoint Quality Tagger<br>`PSN_CheckpointQualityTagger` | Tag a checkpoint with a quality score and tags in the registry. | `checkpoint_name`, `quality_score`, `tags`, `registry` | CHECKPOINT_REGISTRY |
| Checkpoint Registry Lookup<br>`PSN_CheckpointRegistryLookup` | Look up a checkpoint entry; outputs its score, tags and a found flag. | `checkpoint_name`, `registry` | FLOAT, STRING, BOOLEAN |
| Civitai Auth (PSN)<br>`PSN_Civitai_Auth` | Configure and validate a Civitai API token and endpoint. | `api_token`, `endpoint` | CIVITAI_CONFIG |
| PSN Dataset Loader<br>`PSN_Dataset_Loader` | Load a dataset (csv / json / folder) and return records + metadata. | `dataset_path`, `format` | PSN_DATASET, STRING |
| Device Layer Plan (text only)<br>`PSN_Device_Layer_Plan` | Writes a round-robin layer-to-device text plan from a comma-separated device list and a layer count. | `device_map`, `num_layers` | STRING |
| PSN Dynamic Model Selector<br>`PSN_Dynamic_Model_Selector` | Selects a model checkpoint based on a parameter from an external source. | `model_list`, `selector_key`, `selector_value`, `match_mode`, `on_missing`, `default_model` | STRING, STRING, BOOLEAN, STRING |
| Flux NAG (Normalized Attention Guidance)<br>`PSN_FluxNAG` | Applies Normalized Attention Guidance (NAG) configuration for Flux 2 Klein and Anima models. | `model_family`, `nag_scale`, `enable_negative` | STRING, STRING, FLOAT |
| Get Resident Model<br>`PSN_Get_Resident_Model` | Retrieve a model from the residency cache; None + was_cached=False on miss. | `cache_key` | MODEL, BOOLEAN |
| Gradual LoRA Influence<br>`PSN_Gradual_LoRA_Apply` | Schedule LoRA strength over a frame range using a linear or keyframed curve. | `lora_model`, `strength_curve`, `start_frame`, `end_frame` | STRING, STRING |
| HSWQ Model Loader (Validation & VRAM Estimation)<br>`PSN_HSWQ_Model_Loader` | Validates HSWQ model loading configuration and estimates VRAM usage. | `model_path`, `quantization_bit`, `device`, `model_size_gb` | BOOLEAN, FLOAT, STRING |
| PSN Inspect JSON Weights (no checkpoint files)<br>`PSN_Inspect_JSON_Weights` | Lists layer names and counts the numbers in a JSON description of weights. | `model` | STRING, INT, STRING |
| LoRA Grid Assembler<br>`PSN_LoRA_Grid_Assembler` | Given cell descriptors, metadata, and grid dimensions, computes the final grid layout: overall dimensions and per-cell label positions. | `cell_descriptors`, `metadata_list`, `grid_cols`, `grid_rows`, `cell_width`, `cell_height`, `label_font_size` | INT, INT, LIST |
| LoRA Grid Generator<br>`PSN_LoRA_Grid_Generator` | Given a sweep config and grid dimensions, produces a list of cell descriptors. | `sweep_config`, `grid_cols`, `grid_rows` | LIST, LIST |
| PSN LoRA Job Payload (HunYuan, trains nothing)<br>`PSN_LoRA_Job_Payload_HunYuan` | Formats a HunYuan LoRA training job payload as JSON and the expected output path. | `config`, `base_model_path`, `output_dir` | STRING, STRING, STRING |
| PSN LoRA Param Set<br>`PSN_LoRA_Param_Set` | Validates LoRA training hyperparameters and emits a config dict. | `learning_rate`, `batch_size`, `steps`, `rank`, `alpha`, `network_module` | DICT, STRING |
| LoRA Sweep Config<br>`PSN_LoRA_Sweep_Config` | Defines the parameter space for a LoRA strength sweep. | `strength_min`, `strength_max`, `steps`, `seed`, `prompt`, `negative_prompt`, `lora_model`, `checkpoint`, `vae` | PSN_SWEEP_CONFIG |
| PSN LoRA Dataset Loader<br>`PSN_Lora_Dataset_Loader` | Load a list of LoRA files from a JSON manifest into a LORA_LIST. | `manifest_json`, `filter_extension`, `sort_by` | LORA_LIST, STRING |
| PSN Merge JSON Weights (weighted sum, no checkpoint files)<br>`PSN_Merge_JSON_Weights` | Weighted sum of two weight sets written as JSON text (layer name to list of numbers). | `model_a`, `model_b`, `weight_a`, `weight_b` | STRING, STRING |
| Model Pruner (Speed)<br>`PSN_ModelPruner` | Prune keys from a safetensors model file to reduce file size. | `model_path`, `keys_to_prune`, `output_path` | STRING, FLOAT |
| MultiGPU Init (ParametricStudio)<br>`PSN_MultiGPU_Init` | Plan the distribution of model layers across devices. | `model`, `device_map` | MODEL |
| MultiGPU Sync (ParametricStudio)<br>`PSN_MultiGPU_Sync` | Simulate a gradient all-reduce (mean) across devices. | `model` | MODEL |
| PSN Quantization Savings Calculator (measures nothing)<br>`PSN_Quantization_Savings_Calc` | Computes % VRAM saved and a score ratio from numbers you type; measures nothing. | `quantized_vram_mb`, `reference_vram_mb`, `quantized_quality_score`, `reference_quality_score`, `metadata_json` | FLOAT, FLOAT, STRING |
| PSN RGB-D Split<br>`PSN_RGBDSplit` | Split a 4-channel image into colour (first 3 channels) and depth (4th channel, scaled to 0..1 per image; a flat depth map becomes zeros). | `image` | IMAGE, IMAGE, MASK |
| Register Resident Model<br>`PSN_Register_Resident_Model` | Store a model in the global LRU residency cache under cache_key. | `model`, `cache_key`, `ttl_seconds` | HIDDEN |
| Resident Cache Info<br>`PSN_Resident_Cache_Info` | Report cache statistics (size, keys) for debugging. | none | STRING, INT |
| PSN Selective Safetensors Loader<br>`PSN_SelectiveSafetensorsLoader` | Plan a selective safetensors load (pure logic; no I/O). | `path`, `header`, `layers`, `device`, `max_keys` | STRING, STRING, STRING |
| PSN Smart Model Loader<br>`PSN_SmartModelLoader` | Unified Model Loader for PS Backend. | `model_path`, `min_vram_mb`, `quantization_type`, `vram_mb` | STRING |
| Studio Dataset Loader<br>`PSN_StudioDatasetLoader` | Loads and validates the canonical storyboard JSON structure from a JSON text payload. | `path`, `schema_version` | PSN_STORYBOARD_DATA, STRING |
| StyleGAN Direction Apply<br>`PSN_StyleGAN_Direction_Apply` | Project a latent onto a direction vector and scale it. | `latent`, `direction_vector`, `strength` | LATENT |
| StyleGAN Direction Discover<br>`PSN_StyleGAN_Direction_Discover` | Perform PCA on a latent batch to discover principal latent directions. | `latent_batch`, `num_directions`, `seed` | LATENT, FLOAT |
| PSN StyleGAN Generation Spec (makes no image)<br>`PSN_StyleGAN_Generate_Spec` | Builds a generation spec (frame count and latent size) from latent vectors; generates no image. | `path_check_json`, `latents` | STRING |
| PSN StyleGAN Checkpoint Path Check (loads nothing)<br>`PSN_StyleGAN_Path_Check` | Validates a StyleGAN checkpoint path string (extension only); loads nothing and does not check the file exists. | `model_path` | STRING |
| PSN StyleGAN Slerp<br>`PSN_StyleGAN_Slerp` | Performs spherical linear interpolation (slerp) between two latent vectors. | `latent_a`, `latent_b`, `num_frames`, `t_start`, `t_end` | STRING |
| PSN T-LoRA Timestep Mask<br>`PSN_TLora_Timestep_Mask` | Compute the per-step activation strength for a T-LoRA adapter. | `start_step`, `end_step`, `total_steps`, `mask_type`, `custom_mask` | FLOAT, BOOLEAN, STRING |
| Unified Model VAE Loader (Validation)<br>`PSN_Unified_Model_VAE_Loader` | Unified loader for model and VAE with pure-logic validation. | `model_path`, `vae_path`, `dtype`, `allowed_dirs`, `allowed_extensions` | STRING, BOOLEAN, STRING |
| PSN VAE Loader (any colour channels)<br>`PSN_VAELoaderChannels` | Load a KL-VAE whose colour channel count is not 3 (e.g. | `vae_name` | VAE |
| VRAM-Aware Model Selector<br>`PSN_VRAMModelSelector` | Select the best-fitting model from a list given a VRAM budget. | `model_list`, `max_vram_gb`, `prefer_quantized` | STRING, STRING |
| VRAM Check<br>`PSN_VRAM_Check` | Check whether at least *threshold_gb* of VRAM is free. | `threshold_gb`, `force_result` | BOOLEAN |
| VRAM Model Switch<br>`PSN_VRAM_Model_Switch` | Select high_res_model when *vram_check* is True, else low_res_model. | `high_res_model`, `low_res_model`, `vram_check` | MODEL |
| Visual Model Selector (UI Backend)<br>`PSN_VisualModelSelector` | Assemble model cards (name, cover image path, metadata) for a UI. | `model_list`, `limit` | MODEL_CARDS |
| Weight Comparator (L2)<br>`PSN_WeightComparator` | Compute L2 distance between two models, optionally aggregated per block. | `model_a`, `model_b`, `block_level` | FLOAT, CUSTOM |

## Prompts

| Node | What it does | Inputs | Outputs |
|---|---|---|---|
| PSN Chunked Conditioning Builder<br>`PSN_Chunked_Conditioning_Builder` | Encode each prompt chunk with CLIP and combine into one CONDITIONING. | `clip`, `chunks`, `weights` | CONDITIONING |
| Conditioning Subtract<br>`PSN_Conditioning_Subtract` | Subtracts the first tensor of the subtract conditioning, times strength (optionally norm-matched to the base), from every base conditioning tensor. | `base`, `subtract`, `strength`, `auto_scale` | CONDITIONING |
| PSN Document Quality Score (from typed metrics)<br>`PSN_Document_Quality_Score_From_Metrics` | Scores a scan from DPI, sharpness and contrast numbers you supply and applies pass thresholds. | `width_px`, `height_px`, `dpi`, `sharpness`, `contrast`, `min_resolution`, `blur_threshold` | FLOAT, STRING, BOOLEAN |
| ELLA Request Formatter (does not run ELLA)<br>`PSN_ELLA_Request_Formatter` | Validates ELLA parameters and formats a redacted JSON request payload. | `conditioning`, `sigma`, `ella_model`, `strength` | STRING |
| Extract JSON from LLM Output<br>`PSN_ExtractJsonFromLLM` | Extract the first valid JSON object/array from raw LLM text output. | `llm_output` | STRING, STRING |
| PSN Filename Generator<br>`PSN_Filename_Generator` | Generate a unique, sanitized filename from base name, timestamp, seed, and suffix. | `base_name`, `timestamp_format`, `seed`, `suffix` | STRING |
| PSN JSON Config Loader<br>`PSN_JSON_Config_Loader` | Parses a JSON string into a Python dictionary and optionally extracts a nested value via a dot-separated key path. | `json_text`, `key_path` | DICT, BOOLEAN, STRING |
| Keyword Index Builder (no embedding model)<br>`PSN_Keyword_Index_Builder` | Builds a hashed bag-of-words keyword index from the asset descriptors you supply. | `folder_path`, `index_name`, `assets_json` | KEYWORD_INDEX, STRING |
| Keyword Search Query (word overlap, not semantic)<br>`PSN_Keyword_Search_Query` | Ranks indexed assets by hashed bag-of-words cosine overlap with the query text, with a minimum score and top-k. | `query_text`, `keyword_index`, `top_k`, `min_score` | SEARCH_RESULTS, STRING |
| PSN List To Prompt Queue<br>`PSN_ListToPromptQueue` | Normalize input into a standard list of prompt strings for iteration. | `list_input` | LIST[STRING] |
| Lyric Prompt Scheduler (ParametricStudio)<br>`PSN_Lyric_Prompt_Scheduler` | Convert lyrics into a prompt-travel schedule. | `lyrics`, `total_duration`, `frame_rate`, `prompt_template`, `audio`, `whisper_model` | STRING, STRING |
| Multi-Reference Video Scheduler<br>`PSN_MultiRefScheduler` | Split a long prompt into segments and assign reference images by keyword. | `long_prompt`, `reference_images`, `reference_keywords`, `segment_duration` | PSN_STORYBOARD_DATA |
| Number List Clamp (not conditioning)<br>`PSN_Number_List_Clamp` | Clamps a JSON list of numbers to [min, max] with a linear (hard) or tanh (smooth) method. | `min_val`, `max_val`, `method`, `vector` | FLOAT, STRING |
| PSN Param Injector<br>`PSN_Param_Injector` | Injects a value into a specific parameter of a target node within a ComfyUI API graph dictionary. | `graph`, `target_node_id`, `param_name`, `value` | DICT, BOOLEAN, STRING |
| PSN Path Validator<br>`PSN_Path_Validator` | Validate and construct a full file path within allowed roots. | `directory`, `filename`, `create_dirs`, `allowed_roots` | STRING, BOOLEAN, STRING |
| Prompt Beat Plan<br>`PSN_PromptBeatPlan` | Emit the beat timeline (hook/build/payoff/button) for a clip duration, as a string and a tensor of beat boundaries [B=1, n_beats+1] in seconds. | `secs` | STRING, FLOAT |
| Prompt Cleaner<br>`PSN_PromptCleaner` | Clean, normalize, and transform a raw prompt string. | `raw_prompt`, `normalize_case`, `remove_punctuation`, `max_length` | STRING, INT |
| PSN Prompt Enhance (verified + fallback)<br>`PSN_PromptEnhance` | Turn a short idea into a model-ready prompt. | `idea`, `kind`, `seed`, `subject`, `setting`, `camera` | STRING, STRING, STRING |
| Prompt Filler Lint (Purpose-First)<br>`PSN_PromptFillerLint` | Lint a text prompt: quantify filler words per category and emit a purpose-first rewrite instruction with a beat plan for the clip duration. | `prompt`, `secs`, `dialogue`, `word_min`, `word_max` | STRING, STRING, INT, FLOAT |
| PSN Prompt Iterator (hidden)<br>`PSN_PromptIterator` | Return the prompt at the current index, the next index, and is_done. Hidden from the menu: use PSN_Prompt_Iterator instead. | `prompt_list`, `index` | STRING, INT, BOOLEAN |
| Prompt Splitter<br>`PSN_PromptSplitter` | Split a prompt into parts by a delimiter, returning a JSON array of strings. | `prompt`, `delimiter` | STRING |
| PSN Prompt Weighter<br>`PSN_PromptWeighter` | Adds weight syntax to prompt terms based on a JSON weights dictionary. | `prompt`, `weights` | STRING |
| Prompt Attribute Cutoff<br>`PSN_Prompt_Attribute_Cutoff` | Limit the effect of specific prompt attributes by scaling down embedding magnitudes after a cutoff token position. | `tokens`, `magnitudes`, `cutoff_token`, `cutoff_position`, `strength` | STRING, INT, STRING |
| PSN Prompt Chunker<br>`PSN_Prompt_Chunker` | Split a long prompt into CLIP-friendly chunks. | `prompt`, `max_tokens`, `split_strategy`, `overlap_tokens` | STRING, INT |
| PSN Prompt Enhancer (hidden)<br>`PSN_Prompt_Enhancer` | Expand a short prompt into a detailed, model-specific prompt. Hidden from the menu: use PSN_PromptEnhance instead. | `raw_prompt`, `target_model`, `verbosity` | STRING, STRING |
| PSN Prompt Generator<br>`PSN_Prompt_Generator` | Generates multiple prompt variations from a base template. | `template`, `variables`, `num_variations`, `seed` | STRING |
| PSN Prompt Iterator<br>`PSN_Prompt_Iterator` | Yields one prompt at a time from a list of prompts. | `prompts`, `current_index` | STRING, INT, BOOLEAN |
| PSN Prompt Reply Parser (enhances nothing)<br>`PSN_Prompt_Reply_Parser` | Parses a pasted Positive:/Negative: LLM reply into two prompts; calls no LLM and enhances nothing. | `raw_prompt`, `llm_response` | STRING, STRING, STRING |
| Scripted Prompt Rewrite (calls no LLM)<br>`PSN_Prompt_Scripted_Rewrite` | Walks the (score, rewrite) turns you supply, or a length/keyword heuristic that appends a fixed phrase to short prompts, until the score reaches the threshold. | `initial_prompt`, `script`, `max_iterations`, `quality_threshold` | STRING, INT, FLOAT |
| PSN Prompt Structure Enforcer<br>`PSN_Prompt_Structure_Enforcer` | Rewrite a free-form prompt into a fixed structural template. | `prompt`, `template` | STRING |
| PSN Prompt Validator<br>`PSN_Prompt_Validator` | Check a prompt for banned tokens and structural issues. | `prompt`, `ban_list` | STRING, STRING |
| Reference Weight Adjuster<br>`PSN_RefWeightAdjuster` | Scale per-reference weights in a segment plan to prevent over-fitting. | `segment_plan`, `strength` | PSN_STORYBOARD_DATA |
| PSN Rotate (deterministic)<br>`PSN_Rotate` | Pick one option from a list (one per line) by unit and index, deterministically: the same inputs always give the same pick, and nothing repeats within a unit until the list is used up. | `options`, `unit`, `index`, `offset` | STRING |
| PSN String Cleaner<br>`PSN_String_Cleaner` | Cleans and normalizes user input text by applying specified operations: - remove_whitespace: Collapses multiple whitespace characters into a single space and strips leading/trailing whitespace. | `text`, `remove_whitespace`, `lowercase`, `remove_punctuation` | STRING |
| PSN String Normalizer<br>`PSN_String_Normalizer` | Normalizes Unicode text to a specified normalization form: - NFC: Canonical Composition with Canonical Ordering - NFD: Canonical Decomposition with Canonical Ordering - NFKC: Compatibility Composition with Canonical Ordering - NFKD: Compatibility Decomposition with Canonical Ordering | `text`, `normalization_form` | STRING |
| PSN Style Library Switcher<br>`PSN_Style_Library_Switcher` | Selects a specific style block from the loaded prompt structure based on style_key. | `prompt_structure`, `style_key`, `fallback_style`, `delimiter` | STRING |
| PSN TOML Prompt Loader<br>`PSN_TOML_Prompt_Loader` | Loads and parses TOML content defining hierarchical prompt components. | `toml_content`, `context_vars` | DICT |
| PSN Template Controller<br>`PSN_Template_Controller` | Validates a loader payload and reports the resolved sampler configuration. | `payload_json` | DICT, STRING, BOOLEAN |
| PSN Template Loader<br>`PSN_Template_Loader` | Selects a pre-configured template and emits its sampler plan + payload. | `template_name`, `steps`, `cfg`, `denoise`, `notes` | DICT, STRING |
| Text Block Splitter<br>`PSN_Text_Block_Splitter` | Splits the supplied raw_text on blank lines after checking that pdf_path is a safe relative .pdf name. | `pdf_path`, `raw_text` | STRING, STRING |
| Text Blocks to Markdown<br>`PSN_Text_Blocks_To_Markdown` | Formats text blocks into a fixed Markdown template (Concise, Detailed or Tutorial). | `raw_text`, `doc_style` | STRING |

## Quality

| Node | What it does | Inputs | Outputs |
|---|---|---|---|
| Archive JSONL Line Formatter (writes nothing)<br>`PSN_Archive_Line_Format` | Formats a metadata dict as one JSONL archive line and returns it. | `metadata_dict`, `run_id`, `intended_output_path` | STRING |
| Compute Media Hash<br>`PSN_ComputeMediaHash` | Compute the attestation hash for a media tensor (helper node). | `payload` | STRING |
| PSN DataFrame Stats<br>`PSN_DataFrameStats` | Compute describe() and corr() over the selected numeric columns. | `dataframe`, `columns` | DATAFRAME, DATAFRAME |
| Family Workflow Validator<br>`PSN_FamilyWorkflowValidator` | Validate API-format workflow graphs against a model-family object_info dict. | `graph_json`, `object_info_json`, `family_name`, `mode`, `port` | STRING, STRING, BOOLEAN, STRING |
| Fetch Info Introspect (read-only)<br>`PSN_FetchInfoIntrospect` | Read-only introspection of ComfyUI node definitions. | `object_info_json`, `classes`, `graph_json` | STRING, STRING |
| PSN File Path Validator<br>`PSN_FilePathValidator` | Validates file path format and backend port compatibility (pure logic, no I/O). | `file_path`, `backend_port` | BOOLEAN, STRING |
| PSN File Hasher<br>`PSN_File_Hasher` | Compute an MD5 or SHA-256 hash of model-asset data. | `data`, `algorithm` | STRING, INT |
| Graph NSFW Guard (block NSFW LoRAs)<br>`PSN_GraphNSFWGuard` | Raise an error if any NSFW LoRA is detected in the workflow graph. | `graph_json`, `nsfw_markers` | STRING, INT |
| Graph Validation Layer<br>`PSN_GraphValidationLayer` | Validate a ComfyUI graph against forbidden node combinations. | `graph_json`, `rules` | BOOLEAN, STRING |
| PSN Hash Phrase Generator<br>`PSN_Hash_Phrase_Generator` | Convert workflow parameters into deterministic English phrases for debugging. | `input_string`, `word_count` | STRING |
| PSN Hash Verifier<br>`PSN_Hash_Verifier` | Verify that model-asset data matches an expected hash. | `data`, `expected_hash`, `algorithm` | BOOLEAN, STRING |
| PSN Image Dedupe<br>`PSN_ImageDedupe` | Drop near-duplicate images from a batch (perceptual hash; keeps the first of each group). | `images`, `max_distance` | IMAGE, STRING |
| PSN Image Quality (CPU)<br>`PSN_ImageQuality` | Judge each image of a batch on the CPU: sharpness, grain, clipped shadows/highlights, contrast. | `image`, `min_sharpness`, `max_clipped_pct` | IMAGE, STRING, BOOLEAN |
| Image Sharpness and Noise Score<br>`PSN_Image_Sharpness_Noise_Score` | Heuristic whole-image sharpness and noise score with a pass threshold. | `IMAGE`, `THRESHOLD`, `CORRELATION_REFERENCE` | IMAGE, FLOAT, BOOLEAN |
| PSN Image To Latent<br>`PSN_Image_To_Latent` | Encode an IMAGE into LATENT space using a VAE. | `image`, `vae` | LATENT |
| PSN Image To Mask<br>`PSN_Image_To_Mask` | Convert an IMAGE to a MASK by averaging the colour channels. | `image` | MASK |
| PSN Intermediate Inspector<br>`PSN_IntermediateInspector` | Inspect an intermediate latent candidate and optionally branch it. | `latent`, `step`, `action` | LATENT, IMAGE |
| PSN Latent To Image<br>`PSN_Latent_To_Image` | Decode a LATENT into an IMAGE using a VAE. | `latent`, `vae` | IMAGE |
| PSN Latent To Mask<br>`PSN_Latent_To_Mask` | Convert a LATENT back to a MASK (spatial shape of the latent). | `latent` | MASK |
| Manifest HMAC Check (not C2PA)<br>`PSN_Manifest_HMAC_Check` | Recomputes the hash and fixed-key HMAC of the manifest embedded in a media dict. | `media` | BOOLEAN, STRING, STRING |
| Manifest HMAC Embed (not C2PA)<br>`PSN_Manifest_HMAC_Embed` | Adds a JSON provenance manifest with a fixed-key HMAC to a media dict's metadata. | `media`, `author`, `tool`, `add_hmac`, `manifest_override` | MEDIA, STRING |
| PSN Mask To Image<br>`PSN_Mask_To_Image` | Convert a MASK to a single-channel IMAGE. | `mask` | IMAGE |
| PSN Mask To Latent<br>`PSN_Mask_To_Latent` | Convert a MASK into a LATENT representation for inpainting. | `mask`, `vae` | LATENT |
| PSN Meta Extractor<br>`PSN_Meta_Extractor` | Extract generation parameters for the current run into a dict + JSON. | `run_id`, `image`, `prompt`, `seed`, `model`, `steps` | DICT, STRING |
| PSN Metadata Validator<br>`PSN_MetadataValidator` | Check that the required production tags are present on the asset. | `asset` | BOOLEAN, STRING |
| Metadata Decryptor<br>`PSN_Metadata_Decryptor` | Extract metadata from an image payload and Fernet-decrypt the values of selected keys. | `image`, `decrypt_keys`, `studio_key` | DICT |
| Metadata Editor (Encrypt)<br>`PSN_Metadata_Editor` | Merge metadata into an image payload, optionally encrypting the values of selected keys before embedding. | `image`, `metadata`, `encrypt_keys`, `studio_key` | IMAGE |
| Metadata Tag Carrier (in memory, writes no files)<br>`PSN_Metadata_Tag_Carrier` | Attaches a tag dict to a tensor copy in memory so the PSN Metadata Validator can read it. | `asset`, `metadata_dict`, `overwrite` | IMAGE |
| Never-Wire Rule Checker<br>`PSN_NeverWireRuleChecker` | Check a specific connection against never-wire rules. | `source_class`, `target_class`, `extra_rules_json` | BOOLEAN, STRING |
| PSN Node Inspector<br>`PSN_NodeInspector` | Visualizes the node hierarchy and dependencies for debugging. | `graph_json` | STRING, STRING |
| Non-Failing Verify (ParametricStudio)<br>`PSN_NonFailingVerify` | Attempt visual/log checks on a payload without ever failing the pipeline. | `payload`, `label`, `strict` | IMAGE,MASK,LATENT, STRING |
| PSN Peek Grid<br>`PSN_Peek_Grid` | Compute the grid layout for arranging peeked images. | `peek_count`, `max_cols` | INT, INT, STRING |
| PSN Peek Plan<br>`PSN_Peek_Plan` | Plan which sampling steps to peek at. | `steps`, `peek_steps`, `enabled`, `sampler_name`, `scheduler`, `cfg`, `seed` | INT, INT, BOOLEAN, STRING |
| PSN Peek Visualizer<br>`PSN_Peek_Visualizer` | Arrange peeked images [N,H,W,C] into a single grid image. | `peeks` | IMAGE |
| Pre-Submission Graph Validator<br>`PSN_PreSubmissionValidator` | Validate a ComfyUI graph before submission, enforcing never-wire rules. | `graph_json`, `strict_mode`, `extra_rules_json` | STRING, BOOLEAN |
| Prompt Enhancer Interface<br>`PSN_Prompt_Enhancer_Interface` | Selects either the original or enhanced prompt based on the boolean toggle. | `original_prompt`, `enhanced_prompt`, `toggle` | STRING, STRING |
| PSN Quality Gate Router<br>`PSN_QualityGateRouter` | Route an image through a quality gate: pass or fall back. | `IMAGE`, `PASS`, `FALLBACK_IMAGE` | IMAGE |
| Quality Metrics (QA)<br>`PSN_Quality_Metrics` | Compute a full-reference image quality metric (SSIM / PSNR / DISTS-proxy) between `image` and `reference`, returning a scalar score and an optional visual error map. | `image`, `reference`, `metrics`, `return_map` | FLOAT, IMAGE |
| Real-Time A/B Generator<br>`PSN_RealTime_A_B_Generator` | Validates generation parameters and returns a deterministic JSON payload representing the generation request. | `active_prompt`, `prompt_source`, `seed`, `steps`, `cfg` | STRING, STRING |
| Round-Trip Asset Validation (Image)<br>`PSN_RoundTripAssetValidation` | Simulate a lossy export/re-import and validate fidelity frame-by-frame. | `source`, `bits`, `tolerance` | IMAGE, FLOAT |
| Round-Trip Asset Validation (Latent)<br>`PSN_RoundTripLatentValidation` | Same round-trip fidelity check for LATENT tensors [B,C,H,W]. | `latent`, `bits`, `tolerance` | LATENT, FLOAT |
| PSN Stat Plot Generator<br>`PSN_StatPlotGenerator` | Render a bar / line / scatter / histogram plot of a DataFrame to an IMAGE. | `dataframe`, `plot_type`, `x_col`, `y_col`, `sample_size`, `width`, `height` | IMAGE |
| Status: Aggregate Fleet<br>`PSN_StatusAggregateFleet` | Aggregate per-instance snapshots into a fleet health report. | `snapshots`, `threshold` | STRING, FLOAT, IMAGE |
| Status: Score Manual Snapshot (contacts nothing)<br>`PSN_StatusScoreSnapshot` | Scores a manually entered instance snapshot (alive, queue, vram, cpu) from 0 to 1. | `name`, `alive`, `queue`, `vram_used`, `vram_total`, `cpu`, `uptime`, `error` | STRING, FLOAT, IMAGE |
| Tensor Expectation Check (op script, runs no workflow)<br>`PSN_TensorExpectationCheck` | Applies a small op script (identity, scale, add, mean, threshold) to the image and checks min/max/mean expectations on each step. | `script_json`, `image`, `mask` | STRING, STRING, IMAGE |
| PSN Tensor Inspect<br>`PSN_Tensor_Inspect` | Inspect a tensor represented as a nested list. | `tensor_data`, `dtype`, `print_values`, `max_print_elements` | STRING, STRING, FLOAT, FLOAT, FLOAT |
| PSN Tensor Save Plan (writes nothing)<br>`PSN_Tensor_Save_Plan` | Works out where a tensor would be saved; writes nothing. | `path`, `tensor_data` | STRING |
| PSN Token Analyzer (Debugging)<br>`PSN_TokenAnalyzer` | Analyze and report on text conditioning tokens for debugging. | `conditioning`, `vocabulary`, `top_n` | INT, FLOAT, STRING |
| UTCDateTime Batch Normalise<br>`PSN_UTCDateTimeBatch` | Normalise a batch of timestamps (one per line) to tz-aware UTC. | `timestamps`, `source_offset_minutes` | STRING, INT, INT |
| UTCDateTime Round-Trip (TypeDecorator core)<br>`PSN_UTCDateTimeRoundTrip` | Normalise one timestamp to tz-aware UTC (UTCDateTime TypeDecorator core). | `timestamp`, `source_offset_minutes` | STRING, INT |
| Verify Media Integrity<br>`PSN_VerifyMediaIntegrity` | Verify that an uploaded media tensor matches its attested hash. | `payload`, `attested_hash` | BOOLEAN, STRING |

## Sampling

| Node | What it does | Inputs | Outputs |
|---|---|---|---|
| PSN Adaptive Field Filter<br>`PSN_AdaptiveFieldFilter` | Validates an Adaptive Field Filter config and builds its kernel. | `strength`, `threshold`, `kernel_size`, `mode`, `config_json`, `grid_json` | BOOLEAN, STRING, STRING, FLOAT |
| Attention Maps per word<br>`PSN_AttentionMaps` | One heatmap per prompt word: where in the picture that word was attended to, averaged over heads, layers and steps. | `attention`, `clip`, `text`, `image`, `skip_punctuation` | IMAGE, MASK, STRING |
| Attention Record (which word painted what)<br>`PSN_AttentionRecord` | Record cross-attention while sampling, for SD 1.5 and SDXL UNets. | `model` | MODEL, PSN_ATTENTION |
| Attention Style Patch<br>`PSN_Attention_Style_Patch` | Builds a validated attention style patch payload (pure logic, no torch). | `style_vector`, `strength`, `op`, `model_tag` | STRING, BOOLEAN, STRING |
| PSN Auto CFG Rescale<br>`PSN_Auto_CFG_Rescale` | Rescale a CFG value based on the conditional/unconditional noise difference. | `model`, `cfg`, `diff`, `max_cfg`, `rescale_mode` | STRING, FLOAT, STRING |
| PSN Batch Seed Generator<br>`PSN_BatchSeedGenerator` | Generates a list of seeds based on a base seed and an offset. | `count`, `base_seed`, `offset` | INT_LIST |
| PSN CFG Schedule Interpolator (one value)<br>`PSN_CFG_Schedule_Interpolator` | Interpolates a CFG value at a given step percentage from a JSON schedule. | `schedule`, `interpolation`, `step_percent` | FLOAT, STRING, STRING |
| CFG Steering Vector<br>`PSN_CFG_Steering_Vector` | Computes the effective CFG output with a steering vector injected. | `cond`, `uncond`, `strength`, `steering_vector`, `cond_json`, `uncond_json` | STRING, FLOAT |
| PSN Custom Sigma Generator<br>`PSN_CustomSigmaGenerator` | Generate a custom SIGMAS schedule (Linear / Karras / Exponential / Custom). | `scheduler_type`, `steps`, `start_sigma`, `end_sigma`, `custom_sigma_string`, `config` | SIGMAS |
| Fast Attention Patch (Plan)<br>`PSN_Fast_Attention_Patch` | Plans a fast-attention kernel patch (flash/sage/sdpa/auto) for a model. | `backend`, `sm`, `available_packages`, `head_dim`, `batch_size`, `seq_len` | STRING, BOOLEAN, STRING |
| Fast Sampler Plan (Config)<br>`PSN_Fast_Sampler_Plan` | Validate and plan a RES4LYF fast-sampling configuration. | `steps`, `solver`, `scheduler` | BOOLEAN, STRING, STRING, STRING |
| FreeU Patch (Config)<br>`PSN_FreeU_Patch` | Validates FreeU scale parameters and produces a patch descriptor. | `b1`, `b2`, `s1`, `s2` | BOOLEAN, STRING, STRING |
| PSN Generalized Guidance<br>`PSN_GeneralizedGuidance` | Applies Power Law CFG and CFG++ methods for alternative guidance approaches. | `cond`, `uncond`, `method`, `power`, `cfg_scale`, `cond_vector`, `uncond_vector` | BOOLEAN, STRING, STRING |
| PSN Golden Sampler<br>`PSN_GoldenSampler` | Sample a latent using the golden sigma schedule. | `model`, `positive`, `negative`, `latent`, `sigmas`, `sampler`, `config` | LATENT |
| PSN Golden Scheduler<br>`PSN_GoldenScheduler` | Generate an optimized ("golden") sigma schedule + preview image. | `model`, `steps`, `shift`, `config` | SIGMAS, IMAGE |
| PSN HyperTile Patch<br>`PSN_HyperTile_Patch` | Plans and validates a hierarchical hyper-tile attention patch. | `width`, `height`, `tile_size`, `overlap_ratio` | BOOLEAN, STRING, FLOAT, INT |
| KSampler Node Entry Builder (no sampling)<br>`PSN_KSampler_Graph_Builder` | Builds the JSON of one KSampler-style node entry holding a custom sigma list, a sampler name and a seed. | `sigmas`, `sampler`, `seed` | STRING |
| PSN Latent BatchConcat<br>`PSN_LatentBatchConcat` | Join two batches (b is resized to a's spatial size when needed). | `latent_a`, `latent_b` | LATENT |
| PSN Latent BatchRepeat<br>`PSN_LatentBatchRepeat` | Repeat the whole batch n times (frames or variations). | `latent`, `times` | LATENT |
| PSN Latent BatchSlice<br>`PSN_LatentBatchSlice` | Take `count` items starting at `start` (negative start counts from the end). | `latent`, `start`, `count` | LATENT |
| PSN Latent Diff<br>`PSN_LatentDiff` | Compares two latent tensors to quantify divergence (e.g., for A/B testing models). | `latent_a`, `latent_b` | FLOAT, FLOAT, STRING |
| PSN Latent Direction<br>`PSN_LatentDirection` | Move a latent along a direction learned from examples: direction = mean(positive batch) - mean(negative batch); result = target + strength * direction. | `target`, `positive`, `negative`, `strength` | LATENT |
| PSN Latent Interpolator<br>`PSN_LatentInterpolator` | Interpolates between two latent vectors using linear (lerp) or spherical (slerp) methods. | `latent_a`, `latent_b`, `t`, `method`, `latent_a_list`, `latent_b_list` | FLOAT, BOOLEAN, STRING, STRING |
| PSN Latent Math<br>`PSN_LatentMath` | a (op) b with a strength: add, subtract, multiply, lerp, maximum, minimum. | `latent_a`, `latent_b`, `op`, `strength` | LATENT |
| PSN Latent NoiseInject<br>`PSN_LatentNoiseInject` | Add noise to a latent: white (scale 1) or structured blobs (scale > 1, several octaves). | `latent`, `seed`, `strength`, `scale`, `octaves` | LATENT |
| PSN Latent Normalize<br>`PSN_LatentNormalize` | Re-scale a latent: 'standardize' (zero mean, unit std per sample), 'match_reference' (mean/std of a reference latent), or 'set_std' (keep the mean, force a standard deviation). | `latent`, `mode`, `target_std`, `strength`, `reference` | LATENT |
| PSN Latent PatchInject<br>`PSN_LatentPatchInject` | Paste latent_b into latent_a at (x, y) in latent cells with a feathered edge. | `latent_a`, `latent_b`, `x`, `y`, `feather`, `strength` | LATENT |
| PSN Latent Slerp<br>`PSN_LatentSlerp` | Spherical interpolation between two latents (better than a straight blend for transitions between noise-like latents). | `latent_a`, `latent_b`, `t` | LATENT |
| PSN Latent Stats<br>`PSN_LatentStats` | Describe a latent (shape, dtype, mean, std, min, max, NaN/Inf count) as text and JSON; with fail_on_bad=true it stops the workflow when the latent contains NaN/Inf. | `latent`, `fail_on_bad` | LATENT, STRING, STRING |
| PSN Latent TemporalSmooth<br>`PSN_LatentTemporalSmooth` | Calm flicker along time: exponential smoothing over the batch axis (frames) or the T axis of a video latent, then optionally re-anchor mean/std to the first frame so the clip cannot drift. | `latent`, `smoothing`, `anchor_first_frame` | LATENT |
| PSN Latent Tileable<br>`PSN_LatentTileable` | Make a latent tile seamlessly: the left/right (and top/bottom) borders are blended with the content half a tile away, so repeating the image shows no seam. | `latent`, `axis`, `blend` | LATENT |
| PSN Latent Validator<br>`PSN_LatentValidator` | Validate latent tensor metadata (dims, channels, dtype) before processing. | `latent_meta`, `expected_channels`, `strict` | STRING, BOOLEAN, STRING |
| PSN Local Edit Composite<br>`PSN_LocalEditComposite` | Alpha-blend *edited_region* into *original_image* using *region_mask*. | `original_image`, `edited_region`, `region_mask` | IMAGE |
| Model-Aware Sigma Scheduler<br>`PSN_ModelAwareScheduler` | Generate model-aware sigma schedules for Krea2, Flux1, and SD3 models. | `steps`, `model_family`, `config` | LIST, STRING |
| One Click Prompt Generator<br>`PSN_One_Click_Prompt_Generator` | Generate a curated, reproducible SD prompt + negative prompt from theme, complexity, and seed. | `theme`, `complexity`, `seed` | STRING, STRING |
| PSN Prompt Adherence Checker<br>`PSN_Prompt_Adherence_Checker` | Verifies that a generated prompt matches intended style/content constraints before execution. | `prompt`, `constraints`, `llm_handle` | BOOLEAN, STRING |
| RES Fast Sampler (logic)<br>`PSN_RESFastSampler` | Plan a RES fast-sampling run (pure logic; no GPU/torch). | `steps`, `cfg`, `seed` | STRING, STRING, INT, BOOLEAN |
| PSN Region Definition<br>`PSN_RegionDefinition` | Create a binary MASK for a rectangle, ellipse or polygon region. | `image`, `region_type`, `coords` | MASK |
| PSN Regional Mask<br>`PSN_RegionalMask` | Creates a binary mask for a specific region of the image. | `image_width`, `image_height`, `bbox` | STRING, STRING |
| PSN Regional Prompt Plan (JSON)<br>`PSN_RegionalPrompt_Plan` | Validates regions (box + prompt) and emits a JSON plan with the strength split evenly across regions. | `image_width`, `image_height`, `regions`, `attention_strength` | STRING, INT, STRING |
| Regional Noise Perturbation<br>`PSN_Regional_Noise_Perturbation` | Applies localized noise perturbations to conditioning data within masked regions. | `conditioning`, `mask`, `noise_strength`, `noise_type`, `seed` | LIST, STRING |
| SAE Config Validator<br>`PSN_SAE_ConfigValidator` | Validates SAE configuration parameters. | `sae_path`, `layer`, `max_layer`, `allowed_dirs` | BOOLEAN, STRING, STRING |
| SAE Top Feature Analyzer<br>`PSN_SAE_TopFeatureAnalyzer` | Analyzes activation values to identify top features. | `activations`, `top_k`, `threshold` | STRING, INT, FLOAT |
| Seed Hash Vector (not a CLIP embedding)<br>`PSN_SeedHashVector` | Derives deterministic hash-based float vectors from a seed and returns them as JSON text. | `seed`, `strategy`, `size_preset` | STRING, STRING |
| PSN Seed Auditor<br>`PSN_Seed_Auditor` | Audits a seed value: logs it, optionally compares to expected, and hashes seed+model. | `seed`, `run_id`, `model_name`, `expected_seed` | INT, STRING, STRING |
| PSN Seed Generator<br>`PSN_Seed_Generator` | PSN_Seed_Generator: deterministic / pseudo-random / hashed seed generation. | `base_seed`, `param_a`, `param_b`, `mode`, `salt` | INT, STRING |
| PSN Seed Manipulator<br>`PSN_Seed_Manipulator` | Derive a deterministic noise descriptor from a base seed, mode and offset. | `base_seed`, `mode`, `offset`, `shape` | INT, DICT |
| Seed Source (wire to samplers by hand)<br>`PSN_Seed_Source` | Outputs the seed you set and the SHA-256 hash of it. | `seed` | INT, STRING |
| PSN Seed Visualizer<br>`PSN_Seed_Visualizer` | Convert a noise descriptor into a pure-Python pixel grid for visualization. | `noise`, `width`, `height` | LIST |
| PSN Spectral Noise<br>`PSN_SpectralNoise` | Inject spectrally-shaped noise into a latent (CPU-safe, torch.fft). | `latent`, `noise_config`, `noise_scale`, `config` | LATENT |
| PSN Spectral Scheduler<br>`PSN_SpectralScheduler` | Generate a sigma schedule and a spectral noise configuration. | `steps`, `schedule_type`, `start_sigma`, `end_sigma`, `spectral_weight`, `cutoff_frac`, `noise_type`, `seed`, `config` | SIGMAS, PSN_NOISE_CONFIG |
| PSN Sweep Analyzer<br>`PSN_Sweep_Analyzer` | Analyze already-computed sweep scores and pick the best value. | `values`, `scores`, `metric` | STRING, STRING, FLOAT, BOOLEAN |
| PSN Sweep Config<br>`PSN_Sweep_Config` | Plan an XY(Z) parameter sweep. | `param_name`, `values`, `max_values` | STRING, STRING, INT, INT, BOOLEAN |
| PSN Uncond Zero Patch<br>`PSN_Uncond_Zero_Patch` | Configures and validates the Uncond Zero patch for skipping unconditional forward passes. | `enable`, `min_steps`, `max_quality_drop`, `total_steps` | STRING, BOOLEAN, STRING, STRING |
| 2D Vector Decompose (typed numbers, not CFG)<br>`PSN_Vector2D_Decompose` | Computes magnitude, angle, unit direction, scale, projection onto an axis and residual of a 2-D vector typed as JSON. | `vec_json`, `axis_json`, `reference`, `scale_mode` | FLOAT, FLOAT, STRING, FLOAT, FLOAT, STRING, STRING |
| Z-Image Grid Layout Summary (draws nothing)<br>`PSN_ZImage_Grid_Layout` | Computes the rows x columns layout of a Z-Image XY plot from its cell specs and returns it as text. | `cell_specs`, `param_matrix` | STRING |
| Z-Image Grid Cell Specs (no image)<br>`PSN_ZImage_Grid_Spec` | Builds per-cell spec dicts (label, prompt, size) for a Z-Image XY plot. | `plot_config`, `prompt`, `negative_prompt`, `width`, `height` | LIST, LIST |
| Z-Image Plot Config<br>`PSN_ZImage_Plot_Config` | Configures the Z-Image XY plot. | `x_param`, `x_values`, `y_param`, `y_values`, `z_image_specific` | PSN_ZIMAGE_PLOT_CONFIG, LIST, LIST, LIST |

## System

| Node | What it does | Inputs | Outputs |
|---|---|---|---|
| PSN Bottleneck Analyzer<br>`PSN_Bottleneck_Analyzer` | Identifies the slowest nodes in the profile data. | `profile_data`, `top_n` | LIST, STRING |
| Build Probe Plan<br>`PSN_BuildProbePlan` | Build a default read-only HTTP probe plan for local services. | `include_comfyui`, `include_vllm`, `timeout` | STRING |
| Cache Key Compare<br>`PSN_CacheKeyCompare` | Compare two cache keys and report whether they match. | `key_a`, `key_b` | BOOLEAN, STRING |
| Config Parse Guard (names source file)<br>`PSN_ConfigParseGuard` | Parse a key/value configuration and guarantee errors name the file. | `config_text`, `source_name` | INT, STRING |
| PSN Core VRAM Guard<br>`PSN_Core_VRAM_Guard` | Decide whether to offload a model based on a VRAM usage ratio. | `model`, `threshold`, `vram_usage` | ANY, BOOLEAN, STRING |
| PSN Memory Leak Detector<br>`PSN_Memory_Leak_Detector` | Detects VRAM leaks from a numeric usage history. | `history_data`, `min_points`, `min_total_increase`, `max_drop_fraction`, `min_drop_fraction` | BOOLEAN, STRING |
| PSN Memory Recall<br>`PSN_Memory_Recall` | Recall stored memories by keyword substring match. | `store_handle`, `query` | STRING |
| PSN Memory Store<br>`PSN_Memory_Store` | Stores a key-value pair in this process's memory (lost when ComfyUI restarts) and outputs the agent's entries as a JSON list for Memory Recall. | `agent_id`, `key`, `value`, `mode` | MEMORY_HANDLE |
| PSN Model Selector<br>`PSN_Model_Selector` | Select a model based on a boolean hardware flag. | `has_vram`, `model_small`, `model_large` | STRING, STRING |
| PSN Pipeline Selector<br>`PSN_Pipeline_Selector` | Select a pipeline id based on free VRAM vs. | `free_vram_gb`, `threshold_light`, `threshold_heavy`, `pipeline_light_id`, `pipeline_heavy_id` | STRING, STRING |
| Probe Result To Latent<br>`PSN_ProbeResultToLatent` | Convert a probe report IMAGE tensor into a LATENT for downstream use. | `report_image` | LATENT |
| PSN Prompt Document Build (stores nothing)<br>`PSN_Prompt_Document_Build` | Builds a canonical prompt+params document as JSON with a hashed id. | `prompt`, `params`, `timestamp` | STRING, STRING |
| PSN Sticky GPU Residency<br>`PSN_Sticky_GPU_Residency` | ComfyUI node that computes a sticky GPU residency policy for model weight tensors. | `sticky`, `priority`, `weight_map` | STRING, STRING, STRING, STRING |
| VRAM Budget Gate (Shared GPU)<br>`PSN_VRAM_Budget_Gate` | Compares device-wide used VRAM plus an estimate for the next step against a budget. | `model`, `latent`, `max_vram_gb`, `run_id`, `hard_stop`, `probe_gb` | MODEL, LATENT, FLOAT |
| VRAM Bytes Check (typed numbers, reads no GPU)<br>`PSN_VRAM_Bytes_Check` | Arithmetic on allocated, reserved and total bytes you type; reads no GPU. | `required_gb`, `current_batch_size`, `allocated_bytes`, `reserved_bytes`, `total_bytes` | BOOLEAN, STRING |
| PSN VRAM Checker<br>`PSN_VRAM_Checker` | Check whether reported free VRAM meets a threshold. | `free_vram_mb`, `threshold_mb` | BOOLEAN, INT, STRING |
| VRAM Samples Formatter (does not sample the GPU)<br>`PSN_VRAM_Samples_Formatter` | Formats a supplied list of VRAM samples (MB) as JSON with evenly spaced index offsets; does not sample the GPU. | `run_id`, `interval_ms`, `samples` | LIST, STRING |
| VRAM Utilization Calculator<br>`PSN_VRAM_Utilization_Calc` | Computes utilization percent from the free and total GB you type. | `free_vram_gb`, `total_vram_gb` | FLOAT |
| Verifier Probe<br>`PSN_VerifierProbe` | Evaluate read-only HTTP probe results and produce a readiness report. | `plan_json`, `results_json` | IMAGE, STRING, BOOLEAN |
| Versioned Asset Cache Key<br>`PSN_VersionedAssetCacheKey` | Build a versioned cache key from model, prompt, style and optional params. | `model`, `prompt`, `style`, `seed`, `steps`, `cfg` | STRING |
| VRAM Budget Planner (estimate only)<br>`PSN_VramBudgetPlanner` | Estimates VRAM fit from a typed JSON of per-key parameter counts, with regex key filtering and fp32/int8 byte arithmetic. | `state_dict_json`, `prune_keys`, `quantize_mode`, `target_vram_gb` | BOOLEAN, STRING, STRING |
| VRAM Ledger Release (planning only, frees no GPU memory)<br>`PSN_VramLedgerRelease` | Removes a task id from the in-process planning ledger. | `image`, `task_id`, `fail_on_missing` | IMAGE, BOOLEAN |
| VRAM Ledger Reserve (planning only, reserves no GPU memory)<br>`PSN_VramLedgerReserve` | Keeps an in-process planning ledger of typed GB figures (total, system, live used, need). | `image`, `task_id`, `need_gb`, `total_gb`, `system_gb`, `live_used_gb`, `fail_on_denied` | IMAGE, BOOLEAN, FLOAT |
| VRAM Report<br>`PSN_VramReport` | Emit the current ledger snapshot as a FLOAT (free GB) for UI wiring. | `image` | IMAGE, FLOAT, FLOAT, FLOAT |
| Weight Ferry (VRAM Streaming Plan)<br>`PSN_WeightFerry` | Plan VRAM-constrained streaming of model blocks. | `model_json`, `vram_limit`, `overhead_gb` | STRING, INT, INT, BOOLEAN, STRING |

## Video

| Node | What it does | Inputs | Outputs |
|---|---|---|---|
| Asset Type Converter<br>`PSN_AsTypeConverter` | Convert a media asset to a target type (IMAGE / VIDEO / AUDIO). | `input_data`, `target_type`, `frames` | IMAGE,VIDEO,AUDIO |
| Assemble Video From Batch<br>`PSN_AssembleVideoFromBatch` | Pack an IMAGE batch into a VIDEO tensor with metadata. | `image_batch`, `fps`, `format`, `audio_track` | VIDEO |
| CFG Rescale Calculator<br>`PSN_CFG_Rescale_Calculator` | Computes a reduced CFG number from base_cfg, a step window and a typed-in noise magnitude. | `base_cfg`, `rescale_strength`, `start_step`, `end_step`, `step`, `noise_magnitude`, `threshold`, `mode` | FLOAT, BOOLEAN, STRING |
| Camera Timeline Editor<br>`PSN_CameraTimelineEditor` | Interpolate camera keyframes into a smooth timeline curve. | `keyframes`, `duration`, `steps` | STRING |
| Cinematic Camera Angle Controller<br>`PSN_Camera_Angle_Controller` | Look up a predefined cinematic camera angle and build a prompt + JSON params. | `angle_index`, `distance`, `tilt`, `pan` | STRING, STRING |
| PSN Camera Apply<br>`PSN_Camera_Apply` | Evaluates the camera curve at a frame and resamples the image with it: x/y pan in pixels, z as zoom factor (1.0 = none, must be above 0), rot as degrees clockwise. | `camera_curve`, `frame_index`, `base_image` | IMAGE, FLOAT, FLOAT, FLOAT, FLOAT |
| Camera Degradation (Realistic Simulation)<br>`PSN_Camera_Degradation` | Simulate lens defects (bokeh, chromatic aberration, vignette) and sensor noise (Poisson + Gaussian, ISO driven) on an IMAGE tensor. | `image`, `lens_type`, `iso`, `shutter_speed`, `chromatic_aberration` | IMAGE |
| PSN Camera Path Definer<br>`PSN_Camera_Path_Definer` | Parse keyframed camera data and build a deterministic KEYFRAMED_CURVE. | `keyframes`, `interpolation`, `duration_frames` | KEYFRAMED_CURVE, STRING |
| PSN Clip Merger (Plan)<br>`PSN_ClipMerger` | Plan the merge of multiple video clips with optional crossfade transitions. | `clips`, `transition`, `transition_frames`, `clip_frame_counts` | INT, STRING, STRING |
| Contact Sheet Assembler<br>`PSN_Contact_Sheet_Assembler` | Stitch sampled frames into a grid, optionally with a numeric label per cell. | `sampled_frames`, `frame_indices`, `cols`, `rows`, `show_timestamps` | IMAGE |
| Continuity Colour Check<br>`PSN_ContinuityColourCheck` | Checks only colour rules, by the share of pixels near the named RGB colour anywhere in the image. | `generated_asset`, `rule_set` | BOOLEAN, INT, STRING |
| Continuity Rule Definer<br>`PSN_ContinuityRuleDefiner` | Parse natural-language continuity rules into a structured rule set. | `character_profile`, `scene_rules` | PSN_RULE_SET |
| PSN Depth Parallax Generator<br>`PSN_Depth_Parallax_Generator` | Generate per-frame displacement fields for a 2.5D parallax effect. | `depth_map`, `motion_strength`, `frame_count`, `camera_path` | STRING, STRING |
| Energy Curve Mapper<br>`PSN_EnergyCurveMapper` | Modulate camera speed/zoom by audio energy peaks. | `camera_curve`, `audio`, `energy_gain`, `speed_gain` | STRING |
| FBX Pose Extractor (Pure Logic)<br>`PSN_FBX_Pose_Extractor` | Validate an FBX payload (JSON text) and a bone->keypoint mapping, then project 3D bone positions into 2D OpenPose keypoints per frame. | `fbx_payload`, `frame_rate`, `bone_mapping`, `focal`, `z_cam`, `frame_width`, `frame_height` | STRING, STRING, INT |
| FFmpeg Decoder (command)<br>`PSN_FFMpegDecoder` | Build the FFmpeg decode command for a video file (no subprocess here). | `file_path`, `codec`, `fps` | STRING |
| FFmpeg Encoder (command)<br>`PSN_FFMpegEncoder` | Build the FFmpeg encode command for a video batch (no subprocess here). | `image`, `codec`, `crf`, `output_path`, `fps` | STRING, INT |
| FPS Resampler<br>`PSN_FPSResampler` | Resample a frame batch to a target FPS (drop / duplicate / blend). | `image`, `source_fps`, `target_fps`, `mode` | IMAGE |
| PSN Face Repair Trigger<br>`PSN_FaceRepairTrigger` | Build a structured repair plan for frames flagged by the drift mask. | `drift_mask`, `repair_model`, `blend_mode`, `feather_radius`, `strength`, `video` | STRING, INT, STRING |
| Frame Interpolator (High FPS)<br>`PSN_FrameInterpolator` | Increase FPS by synthesising intermediate frames via linear blending. | `image`, `source_fps`, `target_fps`, `model_path` | IMAGE |
| Frame Description Aggregator (no captioning)<br>`PSN_Frame_Description_Aggregator` | Joins per-frame descriptions you type (one line per selected frame) into a narrative and key-moment JSON, using histogram scene boundaries from the frames. | `video_frames`, `frame_interval`, `frame_descriptions`, `boundary_threshold` | STRING, STRING |
| Framerate Converter (Plan)<br>`PSN_FramerateConverter` | Converts video framerate by computing a frame mapping and building a backend payload. | `source_fps`, `target_fps`, `source_frame_count`, `job_id` | STRING, STRING, INT |
| HYMotion to SCAIL Convert<br>`PSN_HYMotionToSCAIL_Convert` | Convert HYMotion data into a SCAIL pose sequence (bone mapping + coordinate transform). | `hymotion_data`, `scail_config` | SCAIL_POSE_SEQUENCE, STRING |
| PSN Identity Drift Detector<br>`PSN_IdentityDriftDetector` | Compare per-frame face-similarity scores against a reference threshold. | `drift_scores`, `drift_threshold`, `video`, `reference_face` | FLOAT, FLOAT, INT, STRING |
| PSN LFO Generator<br>`PSN_LFO_Generator` | Generates a procedural LFO signal for animation parameters. | `wave_type`, `frequency`, `amplitude`, `phase`, `duration`, `sample_rate`, `frame_index` | STRING, FLOAT |
| Latent RGB Stack (no VAE decode)<br>`PSN_Latent_RGB_Stack` | Stacks the first three latent channels of each latent as RGB frames, clamped to 0..1, as an IMAGE batch. | `latents` | IMAGE |
| Live State Init<br>`PSN_Live_State_Init` | Initializes the stateful live workflow loop with an initial state value. | `initial_state` | ANY |
| Live State Loop<br>`PSN_Live_State_Loop` | Simulates a wait/timeout decision in the live loop. | `state`, `wait_ms` | ANY, BOOLEAN, STRING |
| Live State Update<br>`PSN_Live_State_Update` | Processes a new input, updates the state, and emits an output. | `state`, `new_input` | ANY, ANY |
| Media Stage Orchestrator<br>`PSN_MediaStageOrchestrator` | Execute a JSON-defined sequence of processing stages on a media asset. | `stage_config`, `input_asset` | IMAGE,VIDEO,AUDIO, STRING |
| Memory Media Cache Clear<br>`PSN_Memory_Media_Clear` | Clear the shared in-memory media cache. | none | BOOLEAN |
| Memory Media Manager (LRU)<br>`PSN_Memory_Media_Manager` | Cache media tensors in memory (LRU) to avoid repeated disk reads. | `media`, `media_path`, `max_cache_size`, `cache_key` | IMAGE, BOOLEAN |
| Merge Image Batches<br>`PSN_MergeImageBatches` | Combine two image batches into one (concat or interleave). | `batch_a`, `batch_b`, `mode` | IMAGE |
| PSN Merge Upscaled Batches<br>`PSN_MergeUpscaledBatches` | Merge a list of IMAGE sub-batches back into one batch (batch dim concat). | `batch_list`, `extra_1`, `extra_2`, `extra_3` | IMAGE |
| Motion Clean Smooth<br>`PSN_MotionClean_Smooth` | Clean a 1-D motion signal by smoothing and report jitter before/after. | `motion_data`, `smoothing_window`, `method` | STRING, FLOAT, FLOAT |
| Motion Detect<br>`PSN_Motion_Detect` | Detects motion between two frames via per-pixel absolute difference. | `frame`, `previous_frame`, `threshold` | IMAGE, FLOAT |
| PSN Motion Position Curve (offsets only, moves no pixels)<br>`PSN_Motion_Position_Curve` | Computes per-frame x/y offsets and the trajectory from a start point, end point, duration and easing curve. | `start_pos_x`, `start_pos_y`, `end_pos_x`, `end_pos_y`, `duration`, `easing` | STRING, STRING, STRING |
| NDI Video Stream Source<br>`PSN_NDI_Source` | Converts frames to RGB bytes and hands them to the connected NDI_SENDER callable; output is True only if that sender returned truthy. | `image`, `ndi_name`, `fps`, `ndi_sender` | BOOLEAN |
| PSN Nearest-Neighbour Upscale (CPU)<br>`PSN_NearestUpscaleBatch` | Integer nearest-neighbour upscale of an IMAGE batch on CPU. | `image_batch`, `scale` | IMAGE |
| News Script Generator<br>`PSN_News_Script_Generator` | Generate a narration script and scene breakdown from news items (template-based, no LLM). | `news_items`, `script_style` | STRING, STRING |
| News Gradient Thumbnail (no video)<br>`PSN_News_Thumbnail_Placeholder` | Builds a plain black-to-white diagonal gradient IMAGE at the chosen resolution. | `output_resolution` | IMAGE |
| Parallax Filename Builder (writes no video)<br>`PSN_Parallax_Filename_Builder` | Builds a filename string from the frame count and element count of the displacement frames and the codec's extension. | `frames`, `codec` | STRING |
| PSN Path Router<br>`PSN_PathRouter` | Routes a plain value to the node ID for the selected path. | `selected_path`, `path_map`, `value` | STRING, STRING, BOOLEAN, STRING |
| PSN Path Selector<br>`PSN_PathSelector` | Button-based selection of an execution path from an allow-list. | `path_name`, `options` | STRING, BOOLEAN, STRING |
| Pose Video Driver (Pure Logic)<br>`PSN_Pose_Video_Driver` | Validate a pose-frame payload (JSON text of keypoints) and a reference-image payload (JSON text with width/height), and produce a deterministic latent plan (JSON string) describing the video latent a downstream GPU node would build. | `pose_frames`, `reference_image`, `latent_channels`, `latent_scale` | STRING, STRING, BOOLEAN |
| Prompt Gradient Test Images (runs no model)<br>`PSN_PromptPlaceholderImages` | Makes one small hash-coloured gradient IMAGE per prompt for layout testing. | `queue_items`, `height`, `width`, `channels` | LIST[IMAGE] |
| RSS Fetcher (XML)<br>`PSN_RSS_Fetcher` | Parse RSS/Atom XML text into structured news items (no network). | `feed_xml`, `max_items`, `category_filter` | STRING, STRING |
| Random Motion Test Fixture (seeded noise, not real motion)<br>`PSN_Random_Motion_Test_Fixture` | Emits seeded random joint-rotation noise as BVH text and a rotations/translations dict, for wiring tests. | `duration`, `seed` | RANDOM_MOTION_DICT, STRING, INT |
| Realtime Loop (FPS)<br>`PSN_Realtime_Loop` | Emits frames from a batched frame source at a target FPS. | `frame_source`, `fps`, `pacing`, `reset` | IMAGE, BOOLEAN |
| PSN Run Tracker<br>`PSN_RunTracker` | Track grid generation progress and produce a formatted log entry. | `run_id`, `total_items`, `current_item`, `metadata` | FLOAT, STRING |
| PSN Scene Detector<br>`PSN_SceneDetector` | Detect scene changes in a video batch via histogram difference. | `image`, `threshold` | INT_LIST, IMAGE |
| Scene Prompt Compiler (ParametricStudio)<br>`PSN_ScenePromptCompiler` | Compile raw scene description + layout + camera data into a tag prompt. | `raw_description`, `layout_json`, `camera_prompt_fragment`, `negative_prompt`, `quality_tags`, `max_tags` | STRING, STRING |
| PSN Scene Queue Builder<br>`PSN_SceneQueueBuilder` | Combine a base prompt with a JSON list of scene variants. | `base_prompt`, `scene_variants`, `separator` | LIST[STRING] |
| PSN Scene Transition<br>`PSN_SceneTransition` | Compute per-frame blend weights for a transition between two scenes. | `transition_type`, `duration` | STRING, STRING |
| PSN Scene Transition Detector<br>`PSN_Scene_Transition_Detector` | Detect scene changes in a batch of video frames via histogram difference. | `video_frames`, `threshold`, `bins` | INT, STRING |
| PSN Segment Extractor<br>`PSN_SegmentExtractor` | Slice a video batch into segments at scene change indices. | `image`, `scene_indices` | IMAGE_LIST |
| PSN Split Batch For GPU<br>`PSN_SplitBatchForGPU` | Split an IMAGE batch into num_gpus contiguous sub-batches (one per GPU). | `image_batch`, `num_gpus` | IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE, IMAGE |
| State Clear<br>`PSN_State_Clear` | Clears state from the global dictionary to prevent memory leaks. | `key` | BOOLEAN |
| State Retrieve<br>`PSN_State_Retrieve` | Retrieves a value from the global dictionary. | `key`, `default` | ANY |
| State Store<br>`PSN_State_Store` | Stores a value in a global dictionary keyed by `key`. | `key`, `value` | BOOLEAN |
| PSN Stream Init<br>`PSN_Stream_Init` | Initialize a StreamDiffusion-style step-schedule state. | `steps`, `guidance_scale`, `schedule_mode` | DICT |
| PSN Stream Step Counter and Noise Schedule (no denoising)<br>`PSN_Stream_Schedule_Step` | Advances a StreamDiffusion-style step counter and noise-level schedule and emits a JSON status; does not denoise or produce an image. | `stream_state`, `prompt`, `image` | STRING, DICT |
| Test Latent Frame (gradient and noise, no model)<br>`PSN_Synthetic_Latent_Frame` | Makes a deterministic test latent from a gradient and seeded noise, blended with the previous latent when given. | `frame_index`, `total_frames`, `steps`, `cfg`, `seed`, `prev_latent` | LATENT, LATENT |
| Test Latent Loop (gradient and noise, no model)<br>`PSN_Synthetic_Latent_Loop` | Runs the test-latent generator (gradient plus seeded noise, chained from the previous frame) for N frames. | `total_frames`, `steps`, `cfg`, `seed` | LATENT |
| PSN Tail Frame Selector<br>`PSN_Tail_Frame_Selector` | Selects the best tail frame from a set of candidates based on pre-computed similarity scores. | `candidate_scores`, `similarity_metric`, `previous_frame_id` | INT, FLOAT, STRING |
| Temporal Slice Blend<br>`PSN_Temporal_Slice_Blend` | Blend per-slice decoded frame values into a single stitched sequence. | `slice_frames`, `total_frames`, `slice_size`, `overlap` | STRING, STRING |
| Temporal Slice Plan<br>`PSN_Temporal_Slice_Plan` | Compute the temporal slice plan for decoding a long video latent in chunks. | `total_frames`, `slice_size`, `overlap` | STRING, INT, STRING |
| PSN Timeline Director<br>`PSN_TimelineDirector` | Parse a JSON scene list and merge per-scene camera/energy curves into a unified per-frame timeline schedule. | `scenes`, `total_frames` | STRING, INT |
| PSN Timeline Stabilizer (FPS Resample)<br>`PSN_TimelineStabilizer` | Resample a video batch to a constant target frame rate. | `image`, `fps`, `src_fps` | IMAGE |
| Value Animation Mask<br>`PSN_ValueAnimationMask` | Masks of pixels whose brightness or colour changed by at least the threshold since the previous frame; frame 0 has no previous frame so its change is zero. | `video`, `value_type`, `threshold` | LIST |
| PSN Video Dataset Loader (Plan)<br>`PSN_VideoDatasetLoader` | Plan and validate video dataset ingestion without touching the filesystem. | `file_path`, `start_frame`, `end_frame`, `resize_mode`, `target_width`, `target_height`, `fps`, `total_frames`, `codec` | VIDEO_INFO, STRING, STRING |
| PSN Video Frame Difference Metric (PSNR, luminance, weighted L1)<br>`PSN_VideoFrameDiffMetric` | Computes PSNR, a per-pixel luminance-similarity score and a weighted L1 difference between two lists of grayscale frames; not true SSIM or LPIPS. | `frames`, `reference`, `metric` | FLOAT, LIST |
| PSN Video Stabilizer (Motion Correction)<br>`PSN_VideoStabilizer` | Remove camera shake from a video batch using optical flow + inverse warp. | `image`, `strength`, `smoothing` | IMAGE |
| PSN Video A/B Loader<br>`PSN_Video_A_B_Loader` | Validate two video descriptors and package them into a synced pair. | `video_a`, `video_b` | PSN_VIDEO_PAIR, BOOLEAN, STRING |
| Video Frame Extract (ParametricStudio)<br>`PSN_Video_Frame_Extract` | Extract specific frames from a video batch (IMAGE [B,H,W,C]). | `image`, `frame_indices`, `fps` | IMAGE, STRING |
| Video Frame Sampler<br>`PSN_Video_Frame_Sampler` | Sample N frames from a video tensor using a chosen strategy. | `video`, `num_frames`, `sampling_strategy` | IMAGE, LIST[INT] |
| PSN Video In PNG Decode<br>`PSN_Video_In_PNG_Decode` | Extract the embedded video bytes from a combined PNG+video stream. | `combined_png`, `offset` | BYTES |
| PSN Video In PNG Encode<br>`PSN_Video_In_PNG_Encode` | Embed a video clip into a PNG by appending its bytes after IEND. | `png_bytes`, `video_bytes` | BYTES, STRING |
| Video Storyboarder<br>`PSN_Video_Storyboarder` | Fills scene templates with a global style and produces a JSON array of prompts plus metadata about scene indices and transitions. | `scene_count`, `scene_templates`, `global_style`, `transition_type` | STRING, STRING |
| PSN Video Swipe Preview<br>`PSN_Video_Swipe_Preview` | Compute the swipe-composite layout for a synced video pair. | `synced_video_pair`, `split_position`, `frame_index` | DICT, BOOLEAN, STRING |
| Video Temporal SR Workflow (Plan)<br>`PSN_Video_Temporal_SR` | Plan a recurrent (BasicVSR++ style) video super-resolution pass. | `num_frames`, `in_width`, `in_height`, `MODEL_PATH`, `SCALE`, `TEMPORAL_WINDOW` | STRING, STRING, INT, INT, INT, INT |

<!-- end of generated node reference -->

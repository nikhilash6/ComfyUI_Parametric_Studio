# ControlNets and picture guides: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

SDXL xinsir ControlNets: three studio templates run xinsir's SDXL ControlNets on SDXL base, each rendered once on the test machine and looked at. Depth holds the scene's layout while the words change everything else (30.4 s, 9.8 GiB). Scribble turns a rough line drawing into a finished picture that keeps its shapes (35.5 s, 11.3 GiB). Tile redraws a soft or small picture with fine detail and the same layout (25.3 s, 9.8 GiB). [code: studio/family_templates/index.json:3589-3591, studio/family_templates/index.json:3616-3618, studio/family_templates/index.json:3643-3645] [run: studio/family_status.json:9504, studio/family_status.json:9596, studio/family_status.json:9626]

SDXL xinsir results as looked at: a depth map of a rainy street became a snowy evening street with the street, cars and figure where the map put them; a hand-drawn house, tree and sun became a watercolour cottage with every shape in place; a 128 px bear blown up to 1024 came back with fur strands and an eye at tile strength 0.6 and denoise 0.9. A first tile try at 0.8 and 0.65 stayed soft and is not counted. All inputs were drawn or generated in the studio. [claim: commit af5a42cb, 2026-11-02]

SDXL OpenPose control: a template runs xinsir's OpenPose ControlNet (the "twins" variant) on SDXL base; one render, 30.3 s, 9.7 GiB. [run: studio/family_status.json:9489-9496]

IP-Adapter templates: 11 studio templates cover the IP-Adapter files on disk, for SD 1.5 and SDXL (the IPAdapter_plus nodes) and SD 3.5 Large (InstantX nodes), each rendered and viewed. A mug reference steered colour and finish on a prompt that named neither, and the face templates used an invented person. On SDXL at weight 0.8 the reference won over the words: the mug carried over and the asked-for wooden table never appeared. [code: studio/family_templates/index.json:3097-3417] [run: studio/family_status.json:4118, studio/family_status.json:9566] [claim: commit e162c772, 2026-11-02]

IP-Adapter on SD 3.5 Large is weak: the reference's look carried over but the mug's shape did not. The run stays in the model map with its WEAK label but is kept off the Families page, so a later recording does not bring it back. Its template says object references only. [code: scripts/record_family_renders.py:13, studio/family_templates/index.json:3321-3323] [claim: commits e162c772 and 8d3c5141, 2026-11-02]

Virtual Set guide passes: the shot's exact Blender depth or pose pass drives the video. H3 Fun Union 2.0 is the default engine because its weights are present; its source input is the pass itself, which it never sees because the regeneration mask covers every pixel. Wan 2.2 Fun Control is the second engine (81 frames at 16 fps, the first shaded still as its reference picture) and needs its own weights. LTX-2.5 Layout to Render is a third engine, not yet run. A pose pass needs a cast. [code: studio/vset/modes/guide.py:1-3, studio/vset/modes/guide.py:10-11]

Wan Fun Control renders: ComfyUI's Wan 2.2 14B Fun Control template rendered once (232.0 s, 42.9 GiB peak), as did the 5B Fun Control template (90.9 s, 24.3 GiB). The 14B Fun Camera template took 307.7 s at 48.1 GiB. [run: studio/family_status.json:11540, studio/family_status.json:11566, studio/family_status.json:11579]

Z-Image Turbo Fun Union ControlNet: ComfyUI's template rendered once, 30.7 s at 24.2 GiB. [run: studio/family_status.json:12468]

Control LoRAs in family templates: FLUX.1 depth (the template makes the depth map itself) and Qwen-Image union control (the template draws Canny edges itself) are LoRA cards that run in their family's own template; as recorded they have no recipe render yet. [run: studio/lora_recipes.json] [claim: commit de244ef1, 2026-11-02]

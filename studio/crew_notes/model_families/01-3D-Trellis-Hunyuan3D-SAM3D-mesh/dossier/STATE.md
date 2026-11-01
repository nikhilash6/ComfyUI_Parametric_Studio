# Model families: state on 2026-11-01

This specialist's records cover 18 studio families: AniGen, HY-Motion, Hunyuan3D-2.1, HunyuanWorld, InstantMesh, MIDI-3D, Matrix-3D, MoGe, PartCrafter, Pixal3D, SAM-3D-Body, SAM-3D-Objects, Shap-E, Stable-Fast-3D, TRELLIS-2-4B, TripoSR, TripoSplat, UniRig. 8 of them have a recorded render. Older notes in this folder can be out of date; where they disagree, this record of what ran wins. [run: studio/family_status.json]

### AniGen

AniGen is a 3d family, era 2026, licence not recorded: has a recorded render. What it does, from its model card: One picture to a coloured mesh that already has a skeleton and skin weights. No ComfyUI graph: it runs as a tool from the 3D page. [run: studio/family_status.json]

AniGen last recorded render: template tool:anigen, 190.7 s, peak 10.9 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

### HY-Motion

HY-Motion is a 3d family, era 2025, licence not recorded: its server starts; no render on record. [run: studio/family_status.json]

### Hunyuan3D-2.1

Hunyuan3D-2.1 is a 3d family, era 2025, licence Own licence: has a recorded render. What it does, from its ComfyUI template notes: Reconstruct a 3D model from a single photo using Hunyuan3D 2.1, converting one input image into a raw white-mesh geometry without textures or materials. Ideal for rapid 3D concepting, blockout prototyping, and asset preparation before texturing or retopology. [run: studio/family_status.json]

Hunyuan3D-2.1 last recorded render: template 3d_hunyuan3d_image_to_model, 30.3 s, peak 5.8 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Hunyuan3D-2.1 model files with a recorded render on 2026-11-01: hunyuan3d-dit-v2-mv-turbo_fp16.safetensors, hunyuan3d-dit-v2-mv_fp16.safetensors, hunyuan3d-dit-v2_fp16.safetensors. Runs: hunyuan3d-2-1/3d_hunyuan3d_image_to_model (45.8 s); hunyuan3d-2-1/3d_hunyuan3d_multiview_to_model (25.1 s); hunyuan3d-2-1/3d_hunyuan3d_multiview_to_model_turbo (35.2 s). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

### HunyuanWorld

HunyuanWorld is a 3d family, era 2025, licence not recorded: its server starts; no render on record. [run: studio/family_status.json]

### InstantMesh

InstantMesh is a 3d family, era 2024, licence not recorded: its server starts; no render on record. [run: studio/family_status.json]

### MIDI-3D

MIDI-3D is a 3d family, era 2025, licence not recorded: its server starts; no render on record. [run: studio/family_status.json]

### Matrix-3D

Matrix-3D is a 3d family, era 2025, licence not recorded: its server starts; no render on record. [run: studio/family_status.json]

### MoGe

MoGe is a 3d family, era 2026, licence not recorded: has a recorded render. What it does, from its ComfyUI template notes: Geometry from one picture: a depth and normal map, turned into a mesh of what the camera sees (one side only, not a whole object). [run: studio/family_status.json]

MoGe last recorded render: template 3d_moge_perspective_to_mesh, 20.2 s, peak 1.8 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

MoGe model files with a recorded render on 2026-11-01: moge_3_vitg_fp16.safetensors. Runs: moss-image/image_moss_image_color_depth_control (30.5 s). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

### PartCrafter

PartCrafter is a 3d family, era 2025, licence not recorded: its server starts; no render on record. What it does, from its knowledge base: A diffusion-based model for part-aware 3D generation. [run: studio/family_status.json]

### Pixal3D

Pixal3D is a 3d family, era 2026, licence not recorded: its server starts; no render on record. What it does, from its ComfyUI template notes: Upload your own separate view images, or use one mixed multi-view turnaround sheet. The workflow prepares front, back, left and right views, then reconstructs a textured 3D model with Pixal3D Multi-View. [run: studio/family_status.json]

### SAM-3D-Body

SAM-3D-Body is a 3d family, era 2026, licence not recorded: has a recorded render. What it does, from its ComfyUI template notes: Extract a full-body 3D human mesh from a single video frame using SAM 3D Body, guided by a text prompt to refine pose and shape estimation. The workflow loads one video and one text prompt, then outputs a reconstructed video showing the recovered human rig. Ideal for motion capture prototyping, biom [run: studio/family_status.json]

SAM-3D-Body last recorded render: template utility_sam3d_body, 105.6 s, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

SAM-3D-Body model files with a recorded render on 2026-11-01: moge_2_vitl_normal_fp16.safetensors, sam_3d_body_dinov3_bf16.safetensors. Runs: SAM-3D-Body/utility_sam3d_body (families/sam-3d-body_turn.webp). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

### SAM-3D-Objects

SAM-3D-Objects is a 3d family, era 2025, licence not recorded: its server starts; no render on record. What it does, from its tool notes: One picture and a mask to one object mesh. It has no ComfyUI graph here: it runs as World Kit's SAM 3D Objects tool. [run: studio/family_status.json]

### Shap-E

Shap-E is a 3d family, era 2023, licence not recorded: has a recorded render. What it does, from its notes: Words to a small rough mesh with vertex colour. No ComfyUI graph: it runs as a small runner, from the 3D page and World Kit. [run: studio/family_status.json]

Shap-E last recorded render: template runner:shap_e, 41.8 s, peak 4.5 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

### Stable-Fast-3D

Stable-Fast-3D is a 3d family, era 2024, licence not recorded: its server starts; no render on record. What it does, from its knowledge base: A combined tokenizer and estimator architecture for 3D generation. [run: studio/family_status.json]

### TRELLIS-2-4B

TRELLIS-2-4B is a 3d family, era 2025, licence MIT: has a recorded render. What it does, from its ComfyUI template notes: Upload a single image. Generate a high-fidelity 3D model with PBR textures using either Pixal3D or TRELLIS.2, toggled by a single switch. Both pipelines share the same DINOv3 encoder and shape/texture VAEs; Pixal3D adds MoGe camera estimation for pixel-aligned geometry. Includes background removal a [run: studio/family_status.json]

TRELLIS-2-4B last recorded render: template trellis2_image_to_mesh, 253.1 s, peak 18.2 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

TRELLIS-2-4B has 1 studio template: trellis2_image_to_mesh. [code: studio/family_templates/index.json]

TRELLIS-2-4B model files with a recorded render on 2026-11-01: trellis_2_int8_convrot.safetensors. Runs: TRELLIS-2-4B/trellis2_image_to_mesh (families/trellis-2-4b_turn.webp). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

### TripoSR

TripoSR is a 3d family, era 2024, licence MIT: has a recorded render. What it does, from its notes: One picture to a mesh, in seconds. It has no ComfyUI graph here: it runs as a small runner, from the 3D page and World Kit. [run: studio/family_status.json]

TripoSR last recorded render: template runner:triposr, 19.0 s, peak 3.5 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

### TripoSplat

TripoSplat is a 3d family, era 2026, licence not recorded: has a recorded render. What it does, from its ComfyUI template notes: Upload a single 2D image. Generate a high-quality 3D Gaussian splat representation with controllable density and budget for rendering. [run: studio/family_status.json]

TripoSplat last recorded render: template 3d_triposplat_image_to_gaussian_splat, 50.2 s, peak 5.5 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

TripoSplat model files with a recorded render on 2026-11-01: birefnet.safetensors, dino_v3_vit_h.safetensors, triposplat_fp16.safetensors. Runs: TripoSplat/3d_triposplat_image_to_gaussian_splat (families/triposplat_turn.webp). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

### UniRig

UniRig is a 3d family, era 2025, licence not recorded: its server starts; no render on record. What it does, from its knowledge base: A model for generating skeletons and skin weights for 3D meshes. [run: studio/family_status.json]

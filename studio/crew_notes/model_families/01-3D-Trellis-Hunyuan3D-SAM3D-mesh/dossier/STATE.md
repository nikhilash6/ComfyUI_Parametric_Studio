# Model families: state on 2026-11-03

This specialist's records cover 18 studio families: AniGen, HY-Motion, Hunyuan3D-2.1, HunyuanWorld, InstantMesh, MIDI-3D, Matrix-3D, MoGe, PartCrafter, Pixal3D, SAM-3D-Body, SAM-3D-Objects, Shap-E, Stable-Fast-3D, TRELLIS-2-4B, TripoSR, TripoSplat, UniRig. 14 of them have a recorded render. Older notes in this folder can be out of date; where they disagree, this record of what ran wins. [run: studio/family_status.json]

### AniGen

AniGen is a 3d family, era 2026, licence MIT: has a recorded render. What it does, from its model card: One picture to a coloured mesh that already has a skeleton and skin weights. No ComfyUI graph: it runs as a tool from the 3D page. [run: studio/family_status.json]

AniGen last recorded render: template tool:anigen, 190.7 s, peak 10.9 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

AniGen model files with a recorded render on 2026-11-03: decoder_final.pt, denoiser.pt. Runs: tool run anigen (190.7 s, families/anigen_turn.webp); looked at: 33 bones, pose test viewed. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### HY-Motion

HY-Motion is a 3d family, era 2025, licence Tencent Hunyuan Community License: it does not apply in the EU, the UK or South Korea; over 1 million monthly users needs a licence from Tencent: has a recorded render. [run: studio/family_status.json]

HY-Motion last recorded render: template hymotion_t2m_preview, 59.6 s, peak 4.9 GiB, 2026-11-02, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

HY-Motion has 1 studio template: hymotion_t2m_preview. [code: studio/family_templates/index.json]

### Hunyuan3D-2.1

Hunyuan3D-2.1 is a 3d family, era 2025, licence Tencent Hunyuan Community License: it does not apply in the EU, the UK or South Korea; over 1 million monthly users needs a licence from Tencent: has a recorded render. What it does, from its ComfyUI template notes: Reconstruct a 3D model from a single photo using Hunyuan3D 2.1, converting one input image into a raw white-mesh geometry without textures or materials. Ideal for rapid 3D concepting, blockout prototyping, and asset preparation before texturing or retopology. [run: studio/family_status.json]

Hunyuan3D-2.1 last recorded render: template 3d_hunyuan3d_image_to_model, 30.3 s, peak 5.8 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Hunyuan3D-2.1 model files with a recorded render on 2026-11-03: hunyuan3d-dit-v2_fp16.safetensors. Runs: hunyuan3d-2-1/3d_hunyuan3d_image_to_model (45.8 s); looked at: turntable: bear on a white matte. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### HunyuanWorld

HunyuanWorld is a 3d family, era 2025, licence Tencent Hunyuan Community License: it does not apply in the EU, the UK or South Korea; over 1 million monthly users needs a licence from Tencent: has a recorded render. [run: studio/family_status.json]

HunyuanWorld last recorded render: template hunyuanworld_pano_t2i, 40.7 s, peak 35.6 GiB, 2026-11-02, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

HunyuanWorld has 1 studio template: hunyuanworld_pano_t2i. [code: studio/family_templates/index.json]

### InstantMesh

InstantMesh is a 3d family, era 2024, licence Apache-2.0: has a recorded render. [run: studio/family_status.json]

InstantMesh last recorded render: template runner:instantmesh, 67.1 s, peak 22.8 GiB, 2026-11-03, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

### MIDI-3D

MIDI-3D is a 3d family, era 2025, licence Apache-2.0: its server starts; no render on record. [run: studio/family_status.json]

### Matrix-3D

Matrix-3D is a 3d family, era 2025, licence MIT (gated download): its server starts; no render on record. [run: studio/family_status.json]

Matrix-3D model files with a recorded render on 2026-11-03: umt5_xxl_fp8_e4m3fn_scaled.safetensors, wan2.2_vae.safetensors. Runs: matrix-3d/video_wan2_2_5B_ti2v (90.7 s); looked at: thumbnail sheet, two frames differ, on brief. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### MoGe

MoGe is a 3d family, era 2026, licence MIT: has a recorded render. What it does, from its ComfyUI template notes: Geometry from one picture: a depth and normal map, turned into a mesh of what the camera sees (one side only, not a whole object). [run: studio/family_status.json]

MoGe last recorded render: template 3d_moge_perspective_to_mesh, 20.2 s, peak 1.8 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

MoGe model files with a recorded render on 2026-11-03: moge_3_vitg_fp16.safetensors. Runs: moss-image/image_moss_image_color_depth_control (30.5 s); looked at: thumbnail sheet, on brief. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### PartCrafter

PartCrafter is a 3d family, era 2025, licence MIT: its server starts; no render on record. What it does, from its knowledge base: A diffusion-based model for part-aware 3D generation. [run: studio/family_status.json]

### Pixal3D

Pixal3D is a 3d family, era 2026, licence MIT (ComfyUI repackage): has a recorded render. What it does, from its ComfyUI template notes: Upload your own separate view images, or use one mixed multi-view turnaround sheet. The workflow prepares front, back, left and right views, then reconstructs a textured 3D model with Pixal3D Multi-View. [run: studio/family_status.json]

Pixal3D last recorded render: template 3d_pixal3d_trellis2_image_to_model, 286.3 s, peak 17.6 GiB, 2026-11-03, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

### SAM-3D-Body

SAM-3D-Body is a 3d family, era 2026, licence SAM License: commercial use allowed, with use rules: has a recorded render. What it does, from its ComfyUI template notes: Extract a full-body 3D human mesh from a single video frame using SAM 3D Body, guided by a text prompt to refine pose and shape estimation. The workflow loads one video and one text prompt, then outputs a reconstructed video showing the recovered human rig. Ideal for motion capture prototyping, biom [run: studio/family_status.json]

SAM-3D-Body last recorded render: template utility_sam3d_body, 105.6 s, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

SAM-3D-Body has 1 studio template: motion_sam3d_capture. [code: studio/family_templates/index.json]

SAM-3D-Body model files with a recorded render on 2026-11-03: moge_2_vitl_normal_fp16.safetensors, sam_3d_body_dinov3_bf16.safetensors. Runs: sam-3d-body/utility_sam3d_body (255.2 s); looked at: body mesh viewed. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### SAM-3D-Objects

SAM-3D-Objects is a 3d family, era 2025, licence SAM License: commercial use allowed, with use rules: has a recorded render. What it does, from its tool notes: One picture and a mask to one object mesh. It has no ComfyUI graph here: it runs as World Kit's SAM 3D Objects tool. [run: studio/family_status.json]

SAM-3D-Objects last recorded render: template tool:sam3d_objects, 210.0 s, peak 21.7 GiB, 2026-11-03, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

SAM-3D-Objects model files with a recorded render on 2026-11-03: slat_decoder_gs.ckpt, slat_decoder_gs_4.ckpt, slat_decoder_mesh.ckpt, slat_decoder_mesh.pt, slat_generator.ckpt, ss_decoder.ckpt. Runs: tool run sam3d_objects (210.0 s, families/sam3d-objects_turn.webp); looked at: turntable: good shape, colour uneven. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### Shap-E

Shap-E is a 3d family, era 2023, licence MIT: has a recorded render. What it does, from its notes: Words to a small rough mesh with vertex colour. No ComfyUI graph: it runs as a small runner, from the 3D page and World Kit. [run: studio/family_status.json]

Shap-E last recorded render: template runner:shap_e, 41.8 s, peak 4.5 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Shap-E model files with a recorded render on 2026-11-03: diffusion_pytorch_model.bin, diffusion_pytorch_model.fp16.safetensors. Runs: tool run shap_e (41.8 s, families/shap-e_turn.webp); looked at: turntable: simple correct object. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### Stable-Fast-3D

Stable-Fast-3D is a 3d family, era 2024, licence Stability AI Community License (text gated): free commercial use only under US$1,000,000 annual revenue: its server starts; no render on record. What it does, from its knowledge base: A combined tokenizer and estimator architecture for 3D generation. [run: studio/family_status.json]

### TRELLIS-2-4B

TRELLIS-2-4B is a 3d family, era 2025, licence MIT. Its image encoder DINOv3 is under the DINOv3 License (commercial use allowed); BiRefNet is MIT: has a recorded render. What it does, from its ComfyUI template notes: Upload a single image. Generate a high-fidelity 3D model with PBR textures using either Pixal3D or TRELLIS.2, toggled by a single switch. Both pipelines share the same DINOv3 encoder and shape/texture VAEs; Pixal3D adds MoGe camera estimation for pixel-aligned geometry. Includes background removal a [run: studio/family_status.json]

TRELLIS-2-4B last recorded render: template trellis2_image_to_mesh, 253.1 s, peak 18.2 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

TRELLIS-2-4B has 1 studio template: trellis2_image_to_mesh. [code: studio/family_templates/index.json]

TRELLIS-2-4B model files with a recorded render on 2026-11-03: dino_v3_L_naf_fp32.safetensors, trellis_2_int8_convrot.safetensors, trellis_2_shape_vae_bf16.safetensors, trellis_2_texture_vae_bf16.safetensors. Runs: trellis-2-4b/trellis2_image_to_mesh (142.1 s); looked at: turntable: detailed bear, baked texture. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### TripoSR

TripoSR is a 3d family, era 2024, licence MIT: has a recorded render. What it does, from its notes: One picture to a mesh, in seconds. It has no ComfyUI graph here: it runs as a small runner, from the 3D page and World Kit. [run: studio/family_status.json]

TripoSR last recorded render: template runner:triposr, 19.0 s, peak 3.5 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

### TripoSplat

TripoSplat is a 3d family, era 2026, licence MIT: has a recorded render. What it does, from its ComfyUI template notes: Upload a single 2D image. Generate a high-quality 3D Gaussian splat representation with controllable density and budget for rendering. [run: studio/family_status.json]

TripoSplat last recorded render: template 3d_triposplat_image_to_gaussian_splat, 50.2 s, peak 5.5 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

TripoSplat model files with a recorded render on 2026-11-03: birefnet.safetensors, dino_v3_vit_h.safetensors, triposplat_fp16.safetensors, triposplat_vae_decoder_fp16.safetensors. Runs: TripoSplat/3d_triposplat_image_to_gaussian_splat (families/triposplat_turn.webp); looked at: splat turntable: bear. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### UniRig

UniRig is a 3d family, era 2025, licence MIT: has a recorded render. What it does, from its knowledge base: A model for generating skeletons and skin weights for 3D meshes. [run: studio/family_status.json]

UniRig last recorded render: template tool:unirig, 195.9 s, peak 5.9 GiB, 2026-11-02, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

UniRig model files with a recorded render on 2026-11-03: skeleton_model.ckpt, skin_model.ckpt. Runs: tool run unirig (129.2 s, families/unirig_vs_skintokens.webp); looked at: pose test: bends with less tearing, neck stretches. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

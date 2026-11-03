"""The Allegro family render (runner:allegro_t2v): rhymes-ai/Allegro text to video with diffusers' own AllegroPipeline, in the studio venv.
The pipeline folder is the repo's transformer, VAE, tokenizer and scheduler with a T5 v1.1 XXL encoder folder (config.json plus model.safetensors); on this box
that encoder is text_encoders/t5xxl_fp16.safetensors, which holds the same 219 tensors as the repo's fp32 shards.
python scripts/family_allegro_t2v.py <pipeline folder> out.mp4 seed steps "prompt" """
import sys, time, torch
from diffusers import AllegroPipeline
from diffusers.utils import export_to_video
folder, out, seed, steps, prompt = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
POS = "(masterpiece), (best quality), (ultra-detailed), (unwatermarked), {} emotional, harmonious, vignette, 4k epic detailed, shot on kodak, 35mm photo, sharp focus, high budget, cinemascope, moody, epic, gorgeous"
NEG = "nsfw, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry."
t0 = time.time()
pipe = AllegroPipeline.from_pretrained(folder, torch_dtype=torch.bfloat16)
pipe.vae.to(torch.float32)          # the model card keeps the VAE in fp32
pipe.to("cuda"); pipe.vae.enable_tiling()
video = pipe(POS.format(prompt.lower().strip()), negative_prompt=NEG, guidance_scale=7.5, max_sequence_length=512, num_inference_steps=steps, generator=torch.Generator("cuda").manual_seed(seed)).frames[0]
export_to_video(video, out, fps=15)
print("done", round(time.time() - t0, 1), "s,", len(video), "frames, peak", round(torch.cuda.max_memory_allocated() / 2**30, 1), "GiB allocated")

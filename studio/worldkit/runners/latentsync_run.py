"""LatentSync 1.6 (code Apache-2.0, weights OpenRAIL++): a clip and a speech track -> the clip with the mouth redrawn to the speech. Run from its own process with the studio's Python: python latentsync_run.py --code DIR --faces DIR --weights latentsync_unet.pt --vae vae-ft-mse.safetensors --vae-config DIR_WITH_config.json --video a.mp4 --audio b.wav --out c.mp4 --work DIR [--seed N] [--steps 20] [--guidance 1.5]
The face finder inside it is InsightFace buffalo_l (non-commercial weights). --faces is a buffalo_l folder; only its finder and landmark files are used, through links in the work folder. The library reads its configs and face models from paths relative to its own folder, so this changes to that folder; nothing is written there."""
import argparse, os, sys


def run(a):
    a = {**vars(a), "code": os.path.abspath(a.code)}
    for k in ("faces", "weights", "vae", "vae_config", "video", "audio", "out", "work"): a[k] = os.path.abspath(a[k])
    os.makedirs(a["work"], exist_ok=True); os.chdir(a["code"]); sys.path.insert(0, a["code"])
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    root = os.path.join(a["work"], "faces"); pack = os.path.join(root, "models", "buffalo_l"); os.makedirs(pack, exist_ok=True)
    for f in ("det_10g.onnx", "2d106det.onnx"):
        if not os.path.lexists(os.path.join(pack, f)): os.symlink(os.path.join(a["faces"], f), os.path.join(pack, f))
    import insightface.app as IA
    made = IA.FaceAnalysis.__init__
    IA.FaceAnalysis.__init__ = lambda self, **k: made(self, **{**k, "root": root})
    import torch
    from accelerate.utils import set_seed
    from DeepCache import DeepCacheSDHelper
    from diffusers import AutoencoderKL, DDIMScheduler
    from omegaconf import OmegaConf
    from latentsync.models.unet import UNet3DConditionModel
    from latentsync.pipelines.lipsync_pipeline import LipsyncPipeline
    from latentsync.whisper.audio2feature import Audio2Feature
    cfg = OmegaConf.load("configs/unet/stage2_512.yaml"); dtype = torch.float16
    audio = Audio2Feature(model_path="checkpoints/whisper/tiny.pt", device="cuda", num_frames=cfg.data.num_frames, audio_feat_length=cfg.data.audio_feat_length)
    vae = AutoencoderKL.from_single_file(a["vae"], config=a["vae_config"], local_files_only=True, torch_dtype=dtype); vae.config.scaling_factor = 0.18215; vae.config.shift_factor = 0
    unet, _ = UNet3DConditionModel.from_pretrained(OmegaConf.to_container(cfg.model), a["weights"], device="cpu"); unet = unet.to(dtype=dtype)
    pipe = LipsyncPipeline(vae=vae, audio_encoder=audio, unet=unet, scheduler=DDIMScheduler.from_pretrained("configs")).to("cuda")
    helper = DeepCacheSDHelper(pipe=pipe); helper.set_params(cache_interval=3, cache_branch_id=0); helper.enable()
    set_seed(a["seed"])
    pipe(video_path=a["video"], audio_path=a["audio"], video_out_path=a["out"], num_frames=cfg.data.num_frames, num_inference_steps=a["steps"], guidance_scale=a["guidance"], weight_dtype=dtype, width=cfg.data.resolution, height=cfg.data.resolution, mask_image_path=cfg.data.mask_image_path, temp_dir=a["work"])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for k in ("code", "faces", "weights", "vae", "vae-config", "video", "audio", "out", "work"): p.add_argument("--" + k, required=True)
    p.add_argument("--seed", type=int, default=1247); p.add_argument("--steps", type=int, default=20); p.add_argument("--guidance", type=float, default=1.5)
    run(p.parse_args())

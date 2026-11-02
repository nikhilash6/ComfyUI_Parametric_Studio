"""One runner for the speech models: reads a line, writes a WAV, prints one JSON line. Run by the Voices page in its own process, never inside ComfyUI.
usage: voice_speak.py --model ID --text "..." --out out.wav [--voice NAME] [--reference a.wav --reference-text "..." --reference-consent own|permission|synthetic] [--seed N]
A reference is refused without a consent word. Weights are read from the models folder (PSN_MODELS_ROOT or STUDIO_MODELS_ROOT); nothing is downloaded on purpose. Code a model needs and pip doesn't have is looked for in STUDIO_VOICE_CODE."""
import argparse, json, os, sys, time

ROOT = os.environ.get("STUDIO_MODELS_ROOT") or os.environ.get("PSN_MODELS_ROOT") or "models"
CODE = os.environ.get("STUDIO_VOICE_CODE") or ""
ENGINES = {}


def engine(*ids):
    def wrap(f):
        for i in ids: ENGINES[i] = f
        return f
    return wrap


def m(*parts): return os.path.join(ROOT, *parts)
def code(name):
    p = os.path.join(CODE, name)
    if not os.path.isdir(p): raise SystemExit(f"this model needs the code in {name}, which is not in STUDIO_VOICE_CODE")
    sys.path.insert(0, p); return p


def device():
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def seed_all(n):
    import random, numpy as np, torch
    random.seed(n); np.random.seed(n); torch.manual_seed(n)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(n)


def need_ref(a):
    if not a.reference: raise SystemExit("this model only speaks in the voice of a reference clip; pass --reference with --reference-consent")
    return a.reference


@engine("kokoro")
def kokoro(a):
    from kokoro import KModel, KPipeline
    import numpy as np
    d = m("_by_repo", "1038lab__KokoroTTS"); voice = a.voice or "af_heart"
    k = KModel(repo_id="hexgrad/Kokoro-82M", config=os.path.join(d, "config.json"), model=os.path.join(d, "kokoro-v1_0.pth")).to(device()).eval()
    p = KPipeline(lang_code=voice[0], repo_id="hexgrad/Kokoro-82M", model=k)
    parts = [r.audio.cpu().numpy() for r in p(a.text, voice=os.path.join(d, "voices", voice + ".pt"), speed=1.0) if r.audio is not None]
    return np.concatenate(parts), 24000


def _qwen(path, device_map=None):
    import torch
    import transformers.utils.generic as TG
    TG._is_mlx = lambda x: False      # an installed mlx without its library breaks transformers' array checks, and nothing here uses it
    from qwen_tts import Qwen3TTSModel
    from qwen_tts.core.tokenizer_12hz.modeling_qwen3_tts_tokenizer_v2 import Qwen3TTSTokenizerV2Encoder
    from qwen_tts.inference.qwen3_tts_tokenizer import Qwen3TTSTokenizer
    for name in ("upsample", "decoder_transformer", "decoder"): setattr(Qwen3TTSTokenizerV2Encoder, name, None)      # newer transformers made these properties, and the package assigns to them
    from transformers.models.mimi import configuration_mimi as MC
    for cname in ("MimiEncoderConfig", "MimiConfig"):
        if hasattr(MC, cname) and not hasattr(getattr(MC, cname), "rope_theta"): setattr(getattr(MC, cname), "rope_theta", 10000.0)      # the value Mimi always used, which the config no longer spells out
    shared, stock = m("qwen3_tts", "speech_tokenizer"), Qwen3TTSTokenizer.from_pretrained.__func__
    # All the 12 Hz models share one speech tokenizer, and only one folder on disk holds its weights.
    Qwen3TTSTokenizer.from_pretrained = classmethod(lambda cls, p, **kw: stock(cls, p if os.path.isfile(os.path.join(p, "model.safetensors")) else shared, **kw))
    tts = Qwen3TTSModel.from_pretrained(path, device_map=device_map or device(), dtype=torch.bfloat16)
    # Newer transformers moved Mimi's encoder parts under encoder.encoder, and the checkpoint keeps the old names. Without this the clip encoder is random, and a clone is noise.
    from safetensors.torch import load_file
    old = load_file(os.path.join(shared, "model.safetensors"), device="cpu"); moved = {}
    for k, v in old.items():
        for a0, b0 in (("encoder.encoder.layers.", "encoder.encoder.encoder_seanet.layers."), ("encoder.encoder_transformer.", "encoder.encoder.encoder_transformer."), ("encoder.downsample.", "encoder.encoder.downsample.")):
            if k.startswith(a0): moved[b0 + k[len(a0):]] = v
    left = tts.model.speech_tokenizer.model.load_state_dict(moved, strict=False)
    bad = [k for k in left.unexpected_keys]
    if bad: raise SystemExit("speech tokenizer: names didn't line up: " + ", ".join(bad[:4]))
    return tts


@engine("qwen3_custom_17", "qwen3_custom_06")
def qwen_custom(a):
    path = m("qwen3_tts") if a.model.endswith("17") else m("TTS", "qwen3_tts", "Qwen3-TTS-12Hz-0.6B-CustomVoice")
    wavs, sr = _qwen(path).generate_custom_voice(text=a.text, speaker=a.voice or "Ryan", language="English")
    return wavs[0], sr


@engine("qwen3_design_17")
def qwen_design(a):
    wavs, sr = _qwen(m("TTS", "qwen3_tts", "Qwen3-TTS-12Hz-1.7B-VoiceDesign")).generate_voice_design(text=a.text, instruct=a.voice or "A warm, calm adult narrator with a steady pace.", language="English")
    return wavs[0], sr


@engine("qwen3_base_17", "qwen3_base_06")
def qwen_base(a):
    n = "1.7B" if a.model.endswith("17") else "0.6B"
    wavs, sr = _qwen(m("TTS", "qwen3_tts", f"Qwen3-TTS-12Hz-{n}-Base")).generate_voice_clone(text=a.text, language="English", ref_audio=need_ref(a), ref_text=a.reference_text)
    return wavs[0], sr


def _pkg_resources():
    """The watermark package still imports pkg_resources, which newer setuptools no longer ships. Chatterbox stamps its output with that watermark, so it stays on."""
    try: import pkg_resources; return
    except ImportError: pass
    import importlib.resources, types
    mod = types.ModuleType("pkg_resources"); mod.resource_filename = lambda pack, name: str(importlib.resources.files(pack) / name); sys.modules["pkg_resources"] = mod


@engine("chatterbox")
def chatterbox(a):
    import torch
    _pkg_resources()
    from chatterbox.tts import ChatterboxTTS, Conditionals, EnTokenizer, S3Gen, T3, VoiceEncoder
    d = m("TTS", "chatterbox", "English"); dev = device(); load = lambda n: torch.load(os.path.join(d, n), map_location="cpu", weights_only=True)
    ve = VoiceEncoder(); ve.load_state_dict(load("ve.pt")); ve.to(dev).eval()
    t3 = T3(); st = load("t3_cfg.pt"); t3.load_state_dict(st["model"][0] if "model" in st else st); t3.to(dev).eval()
    s3 = S3Gen(); s3.load_state_dict(load("s3gen.pt"), strict=False); s3.to(dev).eval()
    conds = Conditionals.load(os.path.join(d, "conds.pt"), map_location=dev).to(dev)
    tts = ChatterboxTTS(t3, s3, ve, EnTokenizer(os.path.join(d, "tokenizer.json")), dev, conds=conds)
    wav = tts.generate(a.text, audio_prompt_path=a.reference)
    return wav.squeeze().cpu().numpy(), tts.sr


@engine("f5tts")
def f5(a):
    from f5_tts.api import F5TTS
    d = m("TTS", "F5-TTS")
    t = F5TTS(model="F5TTS_v1_Base", ckpt_file=os.path.join(d, "F5TTS_v1_Base", "model_1250000.safetensors"), vocab_file=os.path.join(d, "F5TTS_v1_Base", "vocab.txt"), vocoder_local_path=os.path.join(d, "vocos"), device=device())
    wav, sr, _ = t.infer(ref_file=need_ref(a), ref_text=a.reference_text or "", gen_text=a.text, seed=a.seed, show_info=lambda *x: None)
    return wav, sr


@engine("voxcpm2")
def voxcpm2(a):
    from voxcpm import VoxCPM
    t = VoxCPM(voxcpm_model_path=m("TTS", "voxcpm2"), zipenhancer_model_path=None, enable_denoiser=False, optimize=False)
    say = a.text if a.reference else f"({a.voice or 'A calm adult narrator with a warm, steady voice'}){a.text}"
    wav = t.generate(text=say, reference_wav_path=a.reference)
    return wav, t.tts_model.sample_rate


@engine("vibevoice_large", "vibevoice_15b")
def vibevoice(a):
    import librosa, torch
    code("vibevoice")
    from transformers import AutoConfig, AutoModel
    for auto in (AutoConfig, AutoModel):      # transformers now has its own VibeVoice classes under the same names; these weights need the pack's
        auto.register = (lambda stock: lambda *x, **k: stock(*x, **{**k, "exist_ok": True}))(auto.register)
    from transformers.models.auto import auto_factory as F
    try: import transformers.models.qwen2.tokenization_qwen2_fast
    except ImportError:      # the pack imports the old module name; transformers folded it into tokenization_qwen2
        import types, transformers.models.qwen2.tokenization_qwen2 as QT
        shim = types.ModuleType("transformers.models.qwen2.tokenization_qwen2_fast"); shim.Qwen2TokenizerFast = getattr(QT, "Qwen2TokenizerFast", QT.Qwen2Tokenizer); sys.modules[shim.__name__] = shim
    F._LazyAutoMapping.register = (lambda stock: lambda self, key, value, exist_ok=False: stock(self, key, value, exist_ok=True))(F._LazyAutoMapping.register)
    from vvembed.modular.modeling_vibevoice_inference import VibeVoiceForConditionalGenerationInference as VV
    from vvembed.processor.vibevoice_processor import VibeVoiceProcessor
    d = m("TTS", "VibeVoice", "VibeVoice-Large" if a.model.endswith("large") else "VibeVoice-1.5B")
    # Built by hand: transformers' meta-device loading breaks the scheduler this model makes in its constructor.
    from safetensors.torch import load_file
    from vvembed.modular.configuration_vibevoice import VibeVoiceConfig
    cfg = VibeVoiceConfig.from_pretrained(d); cfg._attn_implementation = "sdpa"; model = VV(cfg); sd = {}
    for f in sorted(os.listdir(d)):
        if f.endswith(".safetensors"): sd.update(load_file(os.path.join(d, f)))
    gone = model.load_state_dict(sd, strict=False).missing_keys; del sd
    if "lm_head.weight" in gone: model.lm_head.weight = model.model.language_model.get_input_embeddings().weight      # the 1.5B checkpoint ties it
    model = model.to(device(), torch.bfloat16).eval(); model.set_ddpm_inference_steps(num_steps=10)
    proc = VibeVoiceProcessor.from_pretrained(d)
    ref, _ = librosa.load(need_ref(a), sr=24000, mono=True)
    inp = proc(["Speaker 1: " + a.text], voice_samples=[[ref]], return_tensors="pt", return_attention_mask=True)
    inp = {k: v.to(device()) if torch.is_tensor(v) else v for k, v in inp.items()}
    out = model.generate(**inp, tokenizer=proc.tokenizer, cfg_scale=1.3, max_new_tokens=None, do_sample=False)
    return out.speech_outputs[0].float().cpu().numpy(), 24000


@engine("bark")
def bark(a):
    import torch
    from transformers import AutoProcessor, BarkModel
    d = m("TTS", "bark"); proc = AutoProcessor.from_pretrained(d); model = BarkModel.from_pretrained(d, dtype=torch.float32).to(device()).eval()
    inp = proc(a.text, voice_preset=a.voice or "v2/en_speaker_6", return_tensors="pt").to(device())
    wav = model.generate(**inp, pad_token_id=10000)
    return wav.squeeze().float().cpu().numpy(), model.generation_config.sample_rate


@engine("firered_instruct", "firered_base")
def firered(a):
    code("FireRedTTS3")
    d = m("tts", "FireRedTTS3")
    if a.model == "firered_instruct":
        from fireredtts3.core import FireRedTTS3Instruct
        wav, sr, _ = FireRedTTS3Instruct(d, use_wetext=False, use_llm_tn=False).generate_voice_design(instruction=a.voice or "A calm adult narrator with a warm, steady voice and an even pace.", text=a.text)
    else:
        import torchaudio
        from fireredtts3.core import FireRedTTS3
        au, sr0 = torchaudio.load(need_ref(a))
        wav, sr = FireRedTTS3(d, use_wetext=False, use_llm_tn=False).generate(language="English", prompt_text=a.reference_text, prompt_audio=au, prompt_audio_sr=sr0, text=a.text, do_tn=False)
    return wav.squeeze().float().cpu().numpy(), sr


@engine("phonon_31m", "phonon_40m")
def phonon(a):
    from safetensors.torch import load_file
    from transformers import AutoProcessor, GradiumPhononTTSForConditionalGeneration as G
    src = m("TTS", "phonon", "phonon-31m-en" if a.model.endswith("31m") else "phonon-40m-multilingual")
    d = view(os.path.basename(src), {f: os.path.join(src, f) for f in os.listdir(src) if f != "processor_config.json" and os.path.isfile(os.path.join(src, f))})
    pc = json.load(open(os.path.join(src, "processor_config.json"))); pc["audio_tokenizer"]["audio_tokenizer_name_or_path"] = m("TTS", "phonon", "phonon-mimi")      # the file names its codec by hub id
    with open(os.path.join(d, "processor_config.json"), "w") as f: json.dump(pc, f)
    proc = AutoProcessor.from_pretrained(d); model = G.from_pretrained(d).to(device()).eval()
    voice = load_file(os.path.join(d, "default-voice.safetensors"))["speaker_wavs"][0].T.float()
    conv = [{"role": "user", "content": [{"type": "audio"}, {"type": "text", "text": a.text}]}]
    inp = proc.apply_chat_template(conv, tokenize=True, return_dict=True, add_generation_prompt=True, processor_kwargs={"audio_prompt_latents": [voice]}).to(device())
    out = model.generate(**inp); wav = proc.decode(out.audio_latents, out.audio_latents_mask)
    wav = wav[0] if isinstance(wav, (list, tuple)) else wav
    return wav.squeeze().float().cpu().numpy(), getattr(proc, "sampling_rate", None) or getattr(model.config, "sampling_rate", 24000)


@engine("supertonic3")
def supertonic3(a):
    from supertonic import TTS
    tts = TTS(model="supertonic-3", model_dir=m("TTS", "supertonic-3", "onnx"), auto_download=False)
    wav, _ = tts.synthesize(a.text, voice_style=tts.get_voice_style(voice_name=a.voice or "F1"), lang="en")
    return wav, tts.sample_rate


@engine("paradee")
def paradee(a):
    code("paradee")
    from paradee import Paradee, SAMPLE_RATE
    d = m("TTS", "paradee-8m-v1.1")
    return Paradee(version="1.1", quantized=False, model_path=os.path.join(d, "onnx", "paradee.onnx"), config_path=os.path.join(d, "config.json"))(a.text), SAMPLE_RATE


@engine("kokoro_onnx")
def kokoro_onnx(a):
    import numpy as np, tempfile, torch
    from kokoro_onnx import Kokoro
    d = m("_by_repo", "1038lab__KokoroTTS", "voices"); name = a.voice or "af_heart"
    with tempfile.TemporaryDirectory() as t:
        path = os.path.join(t, "voices.npz"); np.savez(path, **{name: torch.load(os.path.join(d, name + ".pt"), map_location="cpu", weights_only=True).numpy()})
        wav, sr = Kokoro(m("_by_repo", "speaches-ai__Kokoro-82M-v1.0-ONNX-fp16", "model.onnx"), path).create(a.text, voice=name, speed=1.0, lang="en-us")
    return wav, sr


def view(name, links):
    """A folder that puts weights next to the config files that belong with them, without touching the models folder."""
    d = os.path.join(CODE, "views", name); os.makedirs(d, exist_ok=True); cfg = os.path.join(CODE, "config", name)
    for root, _, files in os.walk(cfg):
        if ".cache" in root: continue
        for f in files:
            to = os.path.join(d, os.path.relpath(os.path.join(root, f), cfg)); os.makedirs(os.path.dirname(to), exist_ok=True)
            if not os.path.lexists(to): os.symlink(os.path.join(root, f), to)
    for rel, src in links.items():
        to = os.path.join(d, rel); os.makedirs(os.path.dirname(to), exist_ok=True)
        if not os.path.lexists(to): os.symlink(src, to)
    return d


@engine("omnivoice")
def omnivoice(a):
    from omnivoice import OmniVoice
    d = view("OmniVoice", {"model.safetensors": m("_by_repo", "k2-fsa__OmniVoice", "model.safetensors"), "audio_tokenizer/model.safetensors": m("_by_repo", "bosonai__higgs-audio-v2-tokenizer", "model.safetensors")})
    t = OmniVoice.from_pretrained(d, device_map=device(), load_asr=False)
    au = t.generate(text=a.text, instruct=a.voice or "male, moderate pitch, american accent")
    return au[0], t.sampling_rate


@engine("luxtts")
def luxtts(a):
    code("LinaCodec"); code("LuxTTS")
    from zipvoice.luxvoice import LuxTTS
    d = view("LuxTTS", {n: m("_by_repo", "YatharthS__LuxTTS", n) for n in ("model.pt", "vocoder/vocos.bin", "text_encoder.onnx", "fm_decoder.onnx", "text_encoder_int8.onnx", "fm_decoder_int8.onnx")})
    t = LuxTTS(d, device=device()); enc = t.encode_prompt(need_ref(a), rms=0.01)
    return t.generate_speech(a.text, enc, num_steps=4).numpy().squeeze(), 48000


def _torchao():
    """torchtune imports this for quantized training only, which a decode never touches."""
    import types
    try: import torchao.dtypes.nf4tensor
    except ImportError:
        for n in ("torchao.dtypes", "torchao.dtypes.nf4tensor"): sys.modules.setdefault(n, types.ModuleType(n))
        mod = sys.modules["torchao.dtypes.nf4tensor"]; mod.NF4Tensor = type("NF4Tensor", (), {}); mod.linear_nf4 = mod.to_nf4 = lambda *x, **k: None


def _w2v():
    from transformers import AutoFeatureExtractor, Wav2Vec2BertModel
    w = _extra("w2v-bert-2.0")
    _local(Wav2Vec2BertModel, "facebook/w2v-bert-2.0", w); _local(AutoFeatureExtractor, "facebook/w2v-bert-2.0", w)


@engine("neucodec")
def neucodec(a):
    import librosa, torch
    from safetensors.torch import load_file
    _torchao(); _w2v()
    from neucodec import NeuCodec
    y, _ = librosa.load(a.audio, sr=16000, mono=True); c = NeuCodec(24_000, 480); st = load_file(m("TTS", "neucodec", "model.safetensors"))
    c.load_state_dict({k: v for k, v in st.items() if "fc_post_s" not in k and "SemanticDecoder" not in k}, strict=False); c = c.eval().to(device())
    with torch.no_grad(): out = c.decode_code(c.encode_code(torch.from_numpy(y)[None, None].to(device())))
    return out.squeeze().cpu().numpy(), 24000


@engine("rubato")
def rubato(a):
    import librosa, torch
    _torchao(); _w2v(); code("RubatoCodec")
    from rubatocodec import RubatoCodec
    c = RubatoCodec.from_checkpoint(m("TTS", "rubato-codec", "model.safetensors"), device=device()); y, sr = librosa.load(a.audio, sr=None, mono=True)
    with torch.no_grad(): return c.decode(c.encode(torch.from_numpy(y), sr=sr)).squeeze().cpu().numpy(), 44100


@engine("voxlock", "voxlock_fp16", "voxlock_fp32")
def voxlock_run(a):
    import voxlock
    vl = voxlock.VoxLock(m("speech_enhancement", "voxlock", "onnx"), precision={"voxlock": "int8", "voxlock_fp16": "fp16", "voxlock_fp32": "fp32"}[a.model])
    return vl.isolate(voxlock.load_audio(a.audio)), 16000


@engine("clear_se48", "clear_se16", "clear_sr48")
def clearvoice_run(a):
    from clearvoice import ClearVoice
    name, task, sr = {"clear_se48": ("MossFormer2_SE_48K", "speech_enhancement", 48000), "clear_se16": ("MossFormerGAN_SE_16K", "speech_enhancement", 16000), "clear_sr48": ("MossFormer2_SR_48K", "speech_super_resolution", 48000)}[a.model]
    os.chdir(m("speech_enhancement", "ClearerVoice-Studio", "clearvoice"))
    return ClearVoice(task=task, model_names=[name])(a.audio, online_write=False), sr


@engine("audiosr_speech", "audiosr_basic")
def audiosr(a):
    import librosa, numpy as np, torch
    sys.path.insert(0, os.environ.get("STUDIO_COMFY_CORE") or ""); code("AudioSR_pack")
    import vasr_node as N
    name = "audiosr_speech_fp32.safetensors" if a.model == "audiosr_speech" else "audiosr_basic_fp32.safetensors"
    model = N.load_vasr_model(m("AudioSR", name), device=device())
    y, _ = librosa.load(a.audio, sr=48000, mono=True); y = y[: int(48000 * 10.24)]
    batch, _ = N.make_batch_for_super_resolution(None, waveform=np.expand_dims(y, 0))
    with torch.no_grad(): out = model.generate_batch(batch, unconditional_guidance_scale=3.5, ddim_steps=50, duration=len(y) / 48000)
    return np.asarray(out).squeeze()[: len(y)], 48000


@engine("step_editx")
def step_editx(a):
    code("Step-Audio-EditX")
    from omegaconf import OmegaConf
    stock = OmegaConf.to_container; OmegaConf.to_container = lambda c, **k: c if isinstance(c, dict) else stock(c, **k)      # its vendored funasr passes a plain dict
    from tokenizer import StepAudioTokenizer
    from tts import StepAudioTTS
    root = m("TTS", "step_audio_editx")
    tok = StepAudioTokenizer(root, model_source="local", funasr_model_id="FunASR-Paraformer")
    t = StepAudioTTS(os.path.join(root, "Step-Audio-EditX"), tok, model_source="local", gpu_memory_utilization=0.15, max_model_len=8192)
    wav, sr = t.clone(prompt_wav_path=need_ref(a), prompt_text=a.reference_text or "", target_text=a.text)
    return wav.squeeze().float().cpu().numpy(), sr


@engine("ming3_tiny")
def ming3(a):
    from pathlib import Path
    sys.path.insert(0, os.environ.get("STUDIO_COMFY_CORE") or ""); code("ming_pack"); sys.path.insert(0, CODE)
    import ming_pack.loader as L, ming_pack.runtime as R
    name = "Ming-3.0-tts-tiny-9b-int8-convrot"; L.resolve_model = lambda c, d: Path(m("TTS", "ming3"))
    if name not in L.MODEL_ASSETS: L.MODEL_ASSETS[name] = "tiny-9b"
    b = L.load_model(name)
    au = R.synthesize(b, a.text, "voice_design", {"style": a.voice or "A calm adult narrator with a warm, steady voice."}, seed=a.seed, flow_steps=10, cfg=2.0)
    return au["waveform"].squeeze().float().cpu().numpy(), au["sample_rate"]


@engine("humaneness_vc")
def humaneness(a):
    import runpy, soundfile as sf
    d = m("_libraries", "audio-models", "Humaneness-Voice-Converter"); _pkg_resources(); rd, wr = sf.read, sf.write
    sf.read = lambda f, *x, **k: rd(str(f), *x, **k); sf.write = lambda f, *x, **k: wr(str(f), *x, **k)      # the script passes Path objects, which this soundfile refuses
    argv, sys.argv = sys.argv, ["infer.py", "--model-dir", d, "--source", a.audio, "--target", need_ref(a), "--output", a.out]
    try: runpy.run_path(os.path.join(d, "infer.py"), run_name="__main__")
    finally: sys.argv = argv; sf.read, sf.write = rd, wr
    return sf.read(a.out, dtype="float32")


def _extra(name):
    """A small companion model kept beside the runner's code, not in the models folder."""
    p = os.path.join(os.environ.get("STUDIO_VOICE_WEIGHTS") or os.path.join(CODE, "weights"), name)
    if not os.path.isdir(p): raise SystemExit(f"this model also needs {name}, which is not in STUDIO_VOICE_WEIGHTS")
    return p


def _local(cls, repo, path):
    """Make one class load a named hub repo from a local folder."""
    stock = cls.from_pretrained.__func__
    cls.from_pretrained = classmethod(lambda c, name=None, *x, **k: stock(c, path if name == repo else name, *x, **k))


@engine("zonos", "zonos_clip")
def zonos(a):
    import espeakng_loader, torch
    from phonemizer.backend.espeak.wrapper import EspeakWrapper
    EspeakWrapper.set_library(espeakng_loader.get_library_path()); EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
    code("Zonos")
    import zonos.autoencoder as AE
    from transformers import DacModel
    _local(DacModel, "descript/dac_44khz", _extra("dac_44khz"))
    from zonos.conditioning import make_cond_dict
    from zonos.model import Zonos
    d = m("TTS", "zonos", "Zonos-v0.1-transformer"); t = Zonos.from_local(os.path.join(d, "config.json"), os.path.join(d, "model.safetensors"), device=device()); spk = None
    if a.reference:
        import torchaudio, zonos.speaker_cloning as SC
        sd = m("TTS", "zonos", "Zonos-v0.1-speaker-embedding"); SC.hf_hub_download = lambda repo_id, filename, **k: os.path.join(sd, filename)
        t.spk_clone_model = SC.SpeakerEmbeddingLDA(device=device()); wav, sr = torchaudio.load(a.reference); spk = t.make_speaker_embedding(wav, sr).to(device())
    codes = t.generate(t.prepare_conditioning(make_cond_dict(text=a.text, speaker=spk, language="en-us", device=device())), disable_torch_compile=True)
    return t.autoencoder.decode(codes)[0].squeeze().float().cpu().numpy(), t.autoencoder.sampling_rate


@engine("maya1")
def maya1(a):
    import numpy as np, torch
    from snac import SNAC
    from transformers import AutoModelForCausalLM, AutoTokenizer
    d = m("maya1-TTS", "maya1"); tok = AutoTokenizer.from_pretrained(d); model = AutoModelForCausalLM.from_pretrained(d, dtype=torch.bfloat16, device_map=device()).eval()
    who = a.voice or "Realistic male voice in the 30s age with american accent. Normal pitch, warm timbre, conversational pacing."
    prompt = tok.apply_chat_template([{"role": "user", "content": f'<description="{who}"> {a.text}'}], tokenize=False, add_generation_prompt=True)
    ids = tok(prompt, return_tensors="pt", add_special_tokens=False).to(device())
    with torch.no_grad(): out = model.generate(**ids, max_new_tokens=2000, min_new_tokens=28, do_sample=True, temperature=0.4, top_p=0.9, repetition_penalty=1.1, eos_token_id=128258)
    new = [t for t in out[0, ids["input_ids"].shape[1]:].tolist() if 128266 <= t <= 156937]; new = new[: len(new) // 7 * 7]
    if not new: raise SystemExit("maya1 wrote no audio tokens")
    l1, l2, l3 = [], [], []
    for i in range(0, len(new), 7):
        f = [(x - 128266) % 4096 for x in new[i:i + 7]]; l1.append(f[0]); l2 += [f[1], f[4]]; l3 += [f[2], f[3], f[5], f[6]]
    sn = SNAC.from_pretrained(_extra("snac_24khz")).eval().to(device())
    with torch.no_grad(): au = sn.decoder(sn.quantizer.from_codes([torch.tensor(x, device=device())[None] for x in (l1, l2, l3)]))
    return au[0, 0].float().cpu().numpy(), 24000


def _load16k(p):
    import librosa
    return librosa.load(p, sr=16000, mono=True)[0]


@engine("whisper_ct2_tiny", "whisper_ct2_large3", "whisper_ct2_distil")
def whisper_ct2(a):
    from faster_whisper import WhisperModel
    d = {"whisper_ct2_tiny": view("faster-whisper-tiny", {"model.bin": m("_by_repo", "Systran__faster-whisper-tiny", "model.bin")}), "whisper_ct2_large3": view("faster-whisper-large-v3", {"model.bin": m("_complete_pipelines", "LongCat-Avatar-15", "audio_encoders", "model.bin")})}.get(a.model) or view("faster-distil-whisper-large-v3", {"model.bin": m("_by_repo", "Systran__faster-distil-whisper-large-v3", "model.bin")})
    seg, _ = WhisperModel(d, device="cpu", compute_type="int8").transcribe(_load16k(a.audio), language="en", beam_size=3, condition_on_previous_text=False)
    return " ".join(x.text.strip() for x in seg)


@engine("whisper_pt_tiny")
def whisper_pt(a):
    import whisper
    return whisper.load_model(m("video_cont", "latentsync", "whisper", "tiny.pt"), device=device()).transcribe(a.audio, language="en")["text"].strip()


@engine("whisper_hf_tiny")
def whisper_hf(a):
    from transformers import WhisperForConditionalGeneration as W, WhisperFeatureExtractor as F, WhisperTokenizer as T
    d = m("musetalk", "whisper-tiny"); fe = F.from_pretrained(d); tok = T.from_pretrained(os.path.join(CODE, "config", "whisper-tiny")); model = W.from_pretrained(d).to(device()).eval()
    ids = model.generate(fe(_load16k(a.audio), sampling_rate=16000, return_tensors="pt").input_features.to(device()), language="en", task="transcribe")
    return tok.batch_decode(ids, skip_special_tokens=True)[0].strip()


@engine("parakeet_v3", "parakeet_ultra", "nemotron")
def parakeet(a):
    import torch
    from transformers import AutoModel, AutoProcessor
    if a.model == "parakeet_ultra": d = m("_libraries", "audio-models", "parakeet-ultra"); pd = view("parakeet-tdt-0.6b-v3", {})
    elif a.model == "parakeet_v3": d = pd = view("parakeet-tdt-0.6b-v3", {"model.safetensors": m("_libraries", "llm-models", "asr", "parakeet-tdt-0.6b-v3", "model.safetensors")})
    else: d = pd = view("nemotron-speech-streaming-en-0.6b", {"model.safetensors": m("_libraries", "llm-models", "asr", "nemotron-speech-streaming-en-0.6b", "model.safetensors")})
    from transformers import GenerationConfig
    proc = AutoProcessor.from_pretrained(pd); model = AutoModel.from_pretrained(d, dtype=torch.bfloat16).to(device()).eval(); model.generation_config = GenerationConfig.from_pretrained(pd)
    inp = proc(_load16k(a.audio), sampling_rate=16000, return_tensors="pt").to(device(), torch.bfloat16)
    with torch.no_grad(): out = model.generate(**inp)
    return proc.batch_decode(out.sequences if hasattr(out, "sequences") else out, skip_special_tokens=True)[0].strip()


@engine("granite_speech")
def granite(a):
    from transformers import AutoModelForCTC, AutoProcessor
    d = m("transformers", "granite-speech-5.0-470m-turboctc"); proc = AutoProcessor.from_pretrained(d); model = AutoModelForCTC.from_pretrained(d).to(device()).eval()
    inp = proc([_load16k(a.audio)], sampling_rate=16000, device=device(), return_tensors="pt").to(device())
    return proc.batch_decode(model(**inp).logits.argmax(-1), skip_special_tokens=True)[0].strip()


@engine("qwen3_asr")
def qwen3_asr(a):
    from transformers import AutoModelForMultimodalLM, AutoProcessor
    d = m("TTS", "qwen3_tts", "asr", "Qwen3-ASR-1.7B-hf"); proc = AutoProcessor.from_pretrained(d); model = AutoModelForMultimodalLM.from_pretrained(d, device_map=device()).eval()
    inp = proc.apply_transcription_request(audio=a.audio).to(model.device, model.dtype); ids = model.generate(**inp, max_new_tokens=256)
    return proc.decode(ids[:, inp["input_ids"].shape[1]:], return_format="parsed")[0]["transcription"]


@engine("paraformer_step", "paraformer_soulx")
def paraformer(a):
    import importlib, setuptools      # funasr still imports distutils, which Python 3.12 dropped and setuptools carries
    for n in ("distutils", "distutils.util", "distutils.version"): sys.modules[n] = importlib.import_module(n.replace("distutils", "setuptools._distutils", 1))
    from funasr import AutoModel
    d = m("TTS", "step_audio_editx", "FunASR-Paraformer") if a.model.endswith("step") else m("soulx_singer", "preprocessors", "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch")
    if a.model.endswith("step"): d = view("paraformer_step", {**{f: os.path.join(d, f) for f in os.listdir(d)}, "model.pt": os.path.join(d, "model.pb")})
    return AutoModel(model=d, disable_update=True, device=device()).generate(input=a.audio)[0]["text"]


@engine("parakeet_nemo")
def parakeet_nemo(a):
    import types
    stub = types.ModuleType("nemo.lightning.one_logger_callback"); stub.OneLoggerNeMoCallback = object; sys.modules[stub.__name__] = stub      # NVIDIA's telemetry hook; its package isn't installed and nothing should phone home
    import lhotse.dataset as LD
    LD.__getattr__ = lambda n: object      # training augmentations only; the installed lhotse is older than this NeMo
    import nemo.collections.asr as A
    t = A.models.ASRModel.restore_from(m("soulx_singer", "preprocessors", "parakeet-tdt-0.6b-v2", "parakeet-tdt-0.6b-v2.nemo"), map_location=device()).eval().transcribe([a.audio])[0]
    return getattr(t, "text", t)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True); p.add_argument("--text", required=True); p.add_argument("--out", required=True)
    p.add_argument("--voice"); p.add_argument("--audio"); p.add_argument("--reference"); p.add_argument("--reference-text"); p.add_argument("--reference-consent", choices=["own", "permission", "synthetic"]); p.add_argument("--seed", type=int, default=7)
    a = p.parse_args()
    if a.model not in ENGINES: raise SystemExit("unknown model " + a.model)
    if a.reference and not a.reference_consent: raise SystemExit("a reference clip needs --reference-consent: own, permission or synthetic")
    import numpy as np, soundfile as sf
    seed_all(a.seed); t = time.time(); got = ENGINES[a.model](a); wav, sr = (got, 0) if isinstance(got, str) else got
    if isinstance(wav, str):
        open(a.out, "w", encoding="utf-8").write(wav); print(json.dumps({"out": a.out, "text": wav, "wall_s": round(time.time() - t, 1), "model": a.model})); return
    wav = np.asarray(wav, dtype="float32").squeeze(); sf.write(a.out, wav, int(sr))
    print(json.dumps({"out": a.out, "sr": int(sr), "seconds": round(len(wav) / sr, 2), "wall_s": round(time.time() - t, 1), "model": a.model, "voice": a.voice}))


if __name__ == "__main__": main()

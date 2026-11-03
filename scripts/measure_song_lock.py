#!/usr/bin/env python3
"""Measures a song-lock render: does the mouth move with the singing, and is the song the song?

Lip-sync: mouth opening per frame (inner-lip gap over the distance between the outer eye corners, mediapipe FaceLandmarker)
against the vocal envelope per frame (RMS of the vocal stem, separated from the song window with the Kim_Vocal_2 MDX-Net
model on the CPU). Reported: Pearson r at lag 0 and the best r within +-4 frames (the measure of the owner's earlier
music-video QA, which called 0.35 good), r per shot, a null baseline (the same mouth track against the vocal envelope shifted
by 2 s or more, which is what an unrelated song would score), mouth opening while singing vs during rests, and, when
Whisper's timed words are given, r between mouth opening and "a word is being sung".
Audio identity: sha256 of the decoded samples of the render's audio and of the song window.
Nothing here listens; these are measurements.
usage: measure_song_lock.py --video V.mp4 --window W.wav --landmarker face_landmarker.task --vocal-model Kim_Vocal_2.onnx [--words words.json] [--shot-frames 124] [--json OUT]"""
import argparse, json, os, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
FPS = 24.0
L_EYE, R_EYE, LIP_TOP, LIP_BOT = 33, 263, 13, 14


def decode(path, sr=44100, ch=2):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-f", "f32le", "-ac", str(ch), "-ar", str(sr), "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, ch).T.copy()


def vocals(mix, model, sr=44100):
    """MDX-Net vocal stem (Kim_Vocal_2 layout: n_fft 7680, hop 1024, 3072 bins x 256 frames), CPU."""
    import onnxruntime as ort, torch
    n_fft, hop, dim_f, dim_t = 7680, 1024, 3072, 256; chunk = hop * (dim_t - 1); trim = n_fft // 2; gen = chunk - 2 * trim; nb = n_fft // 2 + 1
    sess = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"]); win = torch.hann_window(n_fft, periodic=True)
    n = mix.shape[1]; pad = gen - n % gen; x = np.concatenate([np.zeros((2, trim), np.float32), mix, np.zeros((2, pad + trim), np.float32)], 1); out = []
    for i in range(0, x.shape[1] - 2 * trim - 1, gen):
        w = torch.from_numpy(x[:, i:i + chunk])
        s = torch.stft(w, n_fft, hop, window=win, center=True, return_complex=True)          # [2, nb, T]
        s = torch.view_as_real(s).permute(0, 3, 1, 2).reshape(1, 4, nb, -1)[:, :, :dim_f]
        y = torch.from_numpy(sess.run(None, {"input": s.numpy().astype(np.float32)})[0])
        y = torch.cat([y, torch.zeros(1, 4, nb - dim_f, y.shape[-1])], 2).reshape(2, 2, nb, -1).permute(0, 2, 3, 1).contiguous()
        o = torch.istft(torch.view_as_complex(y), n_fft, hop, window=win, center=True, length=chunk)
        out.append(o[:, trim:-trim].numpy())
    return np.concatenate(out, 1)[:, :n] * 1.009


def envelope(x, n, sr=44100):
    m = x.mean(0) if x.ndim == 2 else x; hop = sr / FPS
    return np.array([np.sqrt(np.mean(m[int(i * hop):int((i + 1) * hop)] ** 2)) if int(i * hop) < len(m) else 0.0 for i in range(n)])


def mouth_track(video, task):
    import cv2, mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    lm = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(task)), running_mode=vision.RunningMode.VIDEO, num_faces=2,
                                                                                min_face_detection_confidence=0.4, min_tracking_confidence=0.4))
    cap = cv2.VideoCapture(str(video)); out = []; i = 0
    while True:
        ok, fr = cap.read()
        if not ok: break
        H, W = fr.shape[:2]; res = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)), int(i * 1000 / FPS)); v = np.nan
        if res.face_landmarks:
            pts = [np.array([[q.x * W, q.y * H] for q in f]) for f in res.face_landmarks]; p = max(pts, key=lambda p: np.linalg.norm(p[L_EYE] - p[R_EYE]))
            d = np.linalg.norm(p[L_EYE] - p[R_EYE]); v = float(np.linalg.norm(p[LIP_TOP] - p[LIP_BOT]) / d) if d > 0 else np.nan
        out.append(v); i += 1
    lm.close(); return np.array(out)


def smooth(x, k=3):
    y = x.copy()
    for i in range(len(x)):
        w = x[max(0, i - k // 2):i + k // 2 + 1]; w = w[np.isfinite(w)]; y[i] = w.mean() if len(w) else np.nan
    return y


def corr(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 8 or np.std(a[m]) < 1e-9 or np.std(b[m]) < 1e-9: return float("nan")
    return float(np.corrcoef(a[m], b[m])[0, 1])


def best_lag(m, e, L=4):
    n = len(m); best, lag = -2.0, 0
    for k in range(-L, L + 1):
        c = corr(m[k:], e[:n - k]) if k >= 0 else corr(m[:n + k], e[-k:])
        if np.isfinite(c) and c > best: best, lag = c, k
    return best, lag


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--video", required=True); ap.add_argument("--window", required=True); ap.add_argument("--landmarker", required=True)
    ap.add_argument("--vocal-model", required=True); ap.add_argument("--words"); ap.add_argument("--shot-frames", type=int, default=124); ap.add_argument("--json"); a = ap.parse_args()
    from studio import song_lock as SL
    mouth = mouth_track(a.video, a.landmarker); n = len(mouth)
    voc = vocals(decode(a.window), a.vocal_model); env = envelope(voc, n); mix_env = envelope(decode(a.window), n)
    m, e = smooth(mouth), smooth(env); r0 = corr(m, e); rb, lag = best_lag(m, e)
    shots = []
    for k in range(0, n, a.shot_frames):
        sm, se = m[k:k + a.shot_frames], e[k:k + a.shot_frames]; b, l = best_lag(sm, se)
        shots.append({"from_frame": k, "r0": round(corr(sm, se), 3), "r_best": round(b, 3), "lag": l, "face_rate": round(float(np.isfinite(mouth[k:k + a.shot_frames]).mean()), 3)})
    # per-shot view: each shot has its own framing, so the mouth track is z-scored within its shot before pooling, and the control pairs
    # each shot's mouth with ANOTHER shot's stretch of the song (same singer, same song, wrong words)
    K = list(range(0, n, a.shot_frames)); z = m.copy()
    for k in K:
        seg = z[k:k + a.shot_frames]; mu, sd = np.nanmean(seg), np.nanstd(seg); z[k:k + a.shot_frames] = (seg - mu) / sd if sd > 0 else np.nan
    pooled = best_lag(z, e)[0]; matched = [best_lag(m[k:k + a.shot_frames], e[k:k + a.shot_frames])[0] for k in K]; mism = []
    for i in K:
        for j in K:
            if i == j: continue
            L = min(a.shot_frames, n - i, n - j); mism.append(best_lag(m[i:i + L], e[j:j + L])[0])
    null = []
    for s in range(48, n - 47, 6):
        null.append(best_lag(m, np.roll(e, s))[0])
    null = np.array([x for x in null if np.isfinite(x)])
    sing, rest = e > np.nanpercentile(e, 65), e < np.nanpercentile(e, 35)
    mo, mc = float(np.nanmean(m[sing])), float(np.nanmean(m[rest]))
    rec = {"video": str(a.video), "window": str(a.window), "frames": n, "face_detect_rate": round(float(np.isfinite(mouth).mean()), 3),
           "lip_r0": round(r0, 3), "lip_r_best": round(rb, 3), "lip_lag_frames": lag, "lip_good_threshold": 0.35,
           "null_r_best_mean": round(float(null.mean()), 3) if len(null) else None, "null_r_best_p95": round(float(np.percentile(null, 95)), 3) if len(null) else None, "null_shifts": int(len(null)),
           "mouth_open_singing": round(mo, 4), "mouth_open_rests": round(mc, 4), "mouth_contrast": round(mo / mc, 3) if mc > 0 else None,
           "vocal_vs_mix_env_r": round(corr(env, mix_env), 3), "shots": shots,
           "per_shot": {"matched_r_best_mean": round(float(np.nanmean(matched)), 3), "mismatched_r_best_mean": round(float(np.nanmean(mism)), 3) if mism else None,
                        "mismatched_pairs": len(mism), "pooled_z_r_best": round(pooled, 3)},
           "method": "mouth = inner-lip gap / outer-eye distance (mediapipe FaceLandmarker); vocal envelope = RMS per frame of the Kim_Vocal_2 MDX-Net stem of the song window; r = Pearson, best within +-4 frames; null = same mouth track vs the envelope rolled by >= 2 s; per_shot = mouth z-scored per shot, control = a shot's mouth against another shot's stretch of the song"}
    if a.words and os.path.isfile(a.words):
        t = json.load(open(a.words)); act = np.zeros(n)
        for sg in t.get("segments") or []:
            for w in sg.get("words") or []: act[int(float(w[0]) * FPS):int(np.ceil(float(w[1]) * FPS))] = 1
        rec["words_active_frac"] = round(float(act.mean()), 3); rec["lip_vs_words_r"] = round(corr(m, smooth(act)), 3); rec["vocal_env_vs_words_r"] = round(corr(e, smooth(act)), 3)
    out_id, win_id = SL.identity(a.video), SL.identity(a.window)
    rec["audio"] = {"render_sha256": out_id["sha256"], "window_sha256": win_id["sha256"], "render_codec": out_id["codec"], "samples": [out_id["samples"], win_id["samples"]],
                    "bit_exact": out_id["sha256"] == win_id["sha256"] and out_id["samples"] == win_id["samples"]}
    rec["_series"] = {"mouth": [None if not np.isfinite(x) else round(float(x), 4) for x in m], "vocal": [round(float(x), 5) for x in e]}
    s = json.dumps(rec, indent=1)
    if a.json: Path(a.json).write_text(s)
    print(json.dumps({k: v for k, v in rec.items() if k != "_series"}, indent=1))


if __name__ == "__main__": main()

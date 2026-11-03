"""Measurements for LTX Finish: PSNR and SSIM against a clean original (ffmpeg's own filters), colour against the original in CIELAB (scikit-image), the HDR masters' colour tags (ffprobe)
and the EXR frames' pixel type and linear-light peaks (OpenEXR). Everything here reads files; nothing renders, and nothing here decides whether a picture looks right."""
import glob, json, os, re, shutil, subprocess
from pathlib import Path
import numpy as np

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"; FFPROBE = shutil.which("ffprobe") or "ffprobe"
AP1_LUMA = (0.2722287168, 0.6740817658, 0.0536895174)      # ACEScg (AP1) luminance weights


def _run(args, timeout=1800):
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=timeout)
    return r


def size(path):
    r = _run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=width,height,nb_read_frames", "-of", "json", path], 300)
    s = json.loads(r.stdout or "{}").get("streams", [{}])[0]
    return {"width": s.get("width"), "height": s.get("height"), "frames": int(s["nb_read_frames"]) if str(s.get("nb_read_frames", "")).isdigit() else None}


def psnr_ssim(test, ref, vmaf=True, crop=None):
    """{psnr_db, ssim, vmaf, frames} of test against ref, frame by frame, as ffmpeg's psnr, ssim and libvmaf (model v0.6.1) compute them. test is scaled to ref's size first if they differ;
    crop (w, h) centre-crops both first. Frames are matched by their order, whatever the files' frame rates say."""
    rs = size(ref); ts = size(test); cw, ch = crop or (rs["width"], rs["height"])
    pre = "" if crop or (rs["width"], rs["height"]) == (ts["width"], ts["height"]) else f"scale={rs['width']}:{rs['height']}:flags=lanczos,"
    cut = f"crop={cw}:{ch}," if crop else ""
    out = {}
    tests = [("psnr", "psnr_db", r"average:([0-9.]+|inf)"), ("ssim", "ssim", r"All:([0-9.]+)")] + ([("libvmaf=n_threads=8", "vmaf", r"VMAF score: ([0-9.]+)")] if vmaf else [])
    for f, key, pat in tests:
        r = _run([FFMPEG, "-hide_banner", "-i", test, "-i", ref, "-lavfi", f"[0:v]{pre}{cut}settb=AVTB,setpts=N/(24*TB),format=yuv420p[a];[1:v]{cut}settb=AVTB,setpts=N/(24*TB),format=yuv420p[b];[a][b]{f}", "-f", "null", "-"])
        m = re.findall(pat, r.stderr)
        out[key] = (float("inf") if m[-1] == "inf" else round(float(m[-1]), 4 if key == "ssim" else 2)) if m else None
    out["frames"] = min(x for x in (rs["frames"], ts["frames"]) if x) if rs["frames"] or ts["frames"] else None
    return out


def fidelity_report(damaged, result, clean):
    """Damaged and result, each against the clean original, on three measures. PSNR rewards matching pixels and punishes any re-rendered detail; SSIM looks at structure; VMAF is Netflix's
    perceptual model. better lists the measures on which the result is closer to the original than the damaged input was."""
    b, a = psnr_ssim(damaged, clean), psnr_ssim(result, clean)
    better = [k for k in ("psnr_db", "ssim", "vmaf") if a.get(k) is not None and b.get(k) is not None and a[k] > b[k]]
    return {"before": b, "after": a, "psnr_gain_db": round(a["psnr_db"] - b["psnr_db"], 2), "ssim_gain": round(a["ssim"] - b["ssim"], 4), "vmaf_gain": round(a["vmaf"] - b["vmaf"], 1) if a.get("vmaf") is not None and b.get("vmaf") is not None else None,
            "better_on": better, "improved": len(better) == 3, "result_size": size(result)}


def frames_rgb(path, every=8, width=None, height=None):
    """Every `every`-th frame as uint8 RGB arrays (N, H, W, 3)."""
    s = size(path); w, h = width or s["width"], height or s["height"]
    r = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-vf", f"select='not(mod(n\\,{every}))',scale={w}:{h}:flags=lanczos", "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, timeout=600)
    a = np.frombuffer(r.stdout, np.uint8); n = a.size // (w * h * 3)
    return a[: n * w * h * 3].reshape(n, h, w, 3)


def colour_report(grey, result, clean, every=8):
    """Mean CIELAB chroma of the grey input, the result and the original, and the mean CIEDE2000 colour difference from the original, before and after."""
    from skimage.color import rgb2lab, deltaE_ciede2000
    c = frames_rgb(clean, every); g = frames_rgb(grey, every, c.shape[2], c.shape[1]); r = frames_rgb(result, every, c.shape[2], c.shape[1]); n = min(len(c), len(g), len(r))
    lab = {k: rgb2lab(v[:n].astype(np.float32) / 255.0) for k, v in (("clean", c), ("grey", g), ("result", r))}
    chroma = {k: round(float(np.hypot(v[..., 1], v[..., 2]).mean()), 2) for k, v in lab.items()}
    de = {k: round(float(deltaE_ciede2000(lab["clean"], lab[k]).mean()), 2) for k in ("grey", "result")}
    return {"frames_sampled": n, "mean_chroma": chroma, "delta_e2000_vs_original": {"before": de["grey"], "after": de["result"]}, "chroma_above_grey": chroma["result"] > chroma["grey"], "closer_to_original": de["result"] < de["grey"],
            "psnr_ssim_vs_original": {"before": psnr_ssim(grey, clean, vmaf=False), "after": psnr_ssim(result, clean, vmaf=False)}}


def upscale_report(small, result, clean, lanczos_out, seedvr2=None):
    """The result's size against twice the guide it was given (the input, centre-cropped to a multiple of 32), and how close it, a plain Lanczos x2 and SeedVR2 come to the full-size original, on the same centre crop."""
    s, r = size(small), size(result); crop = (r["width"], r["height"])
    _run([FFMPEG, "-v", "error", "-y", "-i", small, "-vf", f"scale={s['width'] * 2}:{s['height'] * 2}:flags=lanczos", "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p", lanczos_out])
    out = {"input_size": [s["width"], s["height"]], "guide_size": [r["width"] // 2, r["height"] // 2], "output_size": [r["width"], r["height"]], "exactly_2x": r["width"] % 2 == 0 and r["height"] % 2 == 0 and r["width"] // 2 <= s["width"] and r["height"] // 2 <= s["height"],
           "compared_on": f"the centre {r['width']}x{r['height']} of the {2 * s['width']}x{2 * s['height']} original",
           "lanczos_x2_vs_original": psnr_ssim(lanczos_out, clean, crop=crop), "ltx_x2_vs_original": psnr_ssim(result, clean, crop=crop)}
    if seedvr2 and os.path.exists(seedvr2): out |= {"seedvr2_x2_vs_original": psnr_ssim(seedvr2, clean, crop=crop), "seedvr2_size": size(seedvr2)}
    return out


def crop_sheet(files, dest, box, frame=48, zoom=2, size_to=None):
    """The same crop (x, y, w, h) from each clip's frame `frame`, enlarged pixel for pixel and set side by side. size_to (w, h): every clip is centre-cropped to that size first, so clips of 960x544 and 960x512 line up."""
    from PIL import Image
    x, y, w, h = box; tiles = []
    for f in files:
        a = frames_rgb(f, 1); a = a[min(frame, len(a) - 1)]
        if size_to:
            tw, th = size_to; oy, ox = max(0, (a.shape[0] - th) // 2), max(0, (a.shape[1] - tw) // 2); a = a[oy:oy + th, ox:ox + tw]
        tiles.append(Image.fromarray(a[y:y + h, x:x + w]).resize((w * zoom, h * zoom), Image.NEAREST))
    out = Image.new("RGB", (sum(t.width for t in tiles) + 8 * (len(tiles) - 1), h * zoom), (10, 10, 10)); cx = 0
    for t in tiles: out.paste(t, (cx, 0)); cx += t.width + 8
    out.save(dest, quality=92); return str(dest)


def colour_tags(path):
    r = _run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,profile,pix_fmt,color_primaries,color_transfer,color_space,bits_per_raw_sample,width,height", "-of", "json", path], 120)
    s = json.loads(r.stdout or "{}").get("streams", [{}])[0]; pf = s.get("pix_fmt") or ""
    return {k: s.get(k) for k in ("codec_name", "profile", "pix_fmt", "color_primaries", "color_transfer", "color_space", "width", "height")} | {"bits": 12 if "12" in pf else 10 if "10" in pf else 8}


def is_hlg_10bit(tags): return tags.get("color_primaries") == "bt2020" and tags.get("color_transfer") == "arib-std-b67" and tags.get("bits", 0) >= 10


def prores_from_png16(png_dir, dest, fps=24):
    """A ProRes 4444 master from the 16-bit HLG frames the graph saved: BT.2020 matrix, HLG transfer, 10-bit 4:4:4."""
    files = sorted(glob.glob(os.path.join(str(png_dir), "*.png")))
    if not files: raise FileNotFoundError(f"no 16-bit frames in {png_dir}")
    Path(dest).parent.mkdir(parents=True, exist_ok=True); lst = Path(dest).with_suffix(".txt")
    lst.write_text("".join(f"file '{f}'\nduration {1 / fps:.6f}\n" for f in files))
    r = _run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-r", str(fps), "-vf", "scale=out_color_matrix=bt2020:out_range=tv,format=yuv444p10le,setparams=color_primaries=bt2020:color_trc=arib-std-b67:colorspace=bt2020nc:range=tv",
              "-c:v", "prores_ks", "-profile:v", "4444", "-vendor", "apl0", "-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc", "-color_range", "tv", str(dest)])
    lst.unlink(missing_ok=True)
    if r.returncode: raise RuntimeError(r.stderr[-600:])
    return dest


def exr_report(exr_dir):
    """Pixel type of every channel, the frame count, and the linear-light peaks over all frames (ACEScg: 1.0 is SDR reference white)."""
    import OpenEXR
    files = sorted(glob.glob(os.path.join(str(exr_dir), "*.exr")))
    if not files: return {"frames": 0}
    types, peak, lum_peak, over, total, chroma = set(), 0.0, 0.0, 0, 0, None
    for f in files:
        with OpenEXR.File(f) as x:
            ch = x.channels(); hd = x.header()
            if chroma is None: chroma = str(hd.get("chromaticities"))
            for name, c in ch.items(): types.add(str(c.pixels.dtype))
            rgb = ch.get("RGB")
            px = rgb.pixels.astype(np.float32) if rgb is not None else np.stack([ch[k].pixels.astype(np.float32) for k in ("R", "G", "B")], -1)
        y = px[..., 0] * AP1_LUMA[0] + px[..., 1] * AP1_LUMA[1] + px[..., 2] * AP1_LUMA[2]
        peak = max(peak, float(px.max())); lum_peak = max(lum_peak, float(y.max())); over += int((y > 1.0).sum()); total += y.size
    return {"frames": len(files), "pixel_types": sorted(types), "half_float": types == {"float16"}, "chromaticities": chroma, "peak_channel": round(peak, 3), "peak_luminance": round(lum_peak, 3),
            "pixels_above_1_pct": round(100.0 * over / max(1, total), 3), "above_1": lum_peak > 1.0, "size": [int(px.shape[1]), int(px.shape[0])]}


def hdr_report(hlg, exr_dir, prores):
    t, p = colour_tags(hlg), colour_tags(prores)
    return {"hlg_master": t, "hlg_ok": is_hlg_10bit(t), "prores_master": p, "prores_ok": is_hlg_10bit(p) and (p.get("profile") or "").startswith("4444"), "exr": exr_report(exr_dir)}


def side_by_side(files, mp4, jpg, labels=None, height=360):
    """The clips next to each other at one height, the smaller ones enlarged pixel for pixel, plus the middle frame as a JPEG. labels are for the page's caption, not drawn on the picture."""
    n = len(files); ins = []
    for f in files: ins += ["-i", str(f)]
    fl = ";".join(f"[{i}:v]scale=-2:{height}:flags=neighbor,setsar=1,fps=24[v{i}]" for i in range(n)) + ";" + "".join(f"[v{i}]" for i in range(n)) + f"hstack=inputs={n}:shortest=1[o]"
    r = _run([FFMPEG, "-v", "error", "-y", *ins, "-filter_complex", fl, "-map", "[o]", "-an", "-c:v", "libx264", "-crf", "27", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4])
    if r.returncode: raise RuntimeError(r.stderr[-600:])
    _run([FFMPEG, "-v", "error", "-y", "-ss", "2", "-i", mp4, "-frames:v", "1", "-q:v", "3", jpg])
    return {"mp4": str(mp4), "jpg": str(jpg), "labels": labels or []}


def headroom_clip(exr_dir, dest, fps=24):
    """A clip that shows where the HDR result is brighter than SDR white: the frame in grey, and every pixel above 1.0 in linear light painted from yellow (just above) to red (8x and up)."""
    import OpenEXR
    files = sorted(glob.glob(os.path.join(str(exr_dir), "*.exr")))
    if not files: raise FileNotFoundError(f"no EXR frames in {exr_dir}")
    with OpenEXR.File(files[0]) as x: h, w = x.channels()["RGB"].pixels.shape[:2]
    p = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(dest)], stdin=subprocess.PIPE)
    for f in files:
        with OpenEXR.File(f) as x: px = x.channels()["RGB"].pixels.astype(np.float32)
        y = px[..., 0] * AP1_LUMA[0] + px[..., 1] * AP1_LUMA[1] + px[..., 2] * AP1_LUMA[2]
        grey = np.clip(y, 0, 1) ** (1 / 2.4) * 0.55
        t = np.clip(np.log2(np.maximum(y, 1e-6)) / 3.0, 0, 1)                 # 0 at 1.0, 1 at 8.0
        hot = y > 1.0
        rgb = np.stack([grey, grey, grey], -1)
        rgb[hot] = np.stack([np.ones_like(t[hot]), 0.9 * (1 - t[hot]), 0.1 * (1 - t[hot])], -1)
        p.stdin.write((rgb * 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError("ffmpeg could not write the headroom clip")
    return str(dest)

"""A GLB -> a contact sheet of a Blender turntable, CPU only, for looking at a 3D result with your own eyes. python scripts/mesh_turntable.py in.glb out.jpg [--frames 6] [--size 384] [--samples 8]"""
import argparse, json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def sheet(frames, out, cell):
    from PIL import Image
    pngs = sorted(Path(frames).glob("*.png"))
    if not pngs: raise SystemExit(f"Blender wrote no frames into {frames}")
    W = Image.new("RGB", (cell * len(pngs), cell), "white")
    for i, p in enumerate(pngs):
        with Image.open(p) as im: W.paste(im.convert("RGB").resize((cell, cell)), (i * cell, 0))
    W.save(out, quality=88); return len(pngs)


def main(argv=None):
    a = argparse.ArgumentParser(); a.add_argument("model"); a.add_argument("out"); a.add_argument("--frames", type=int, default=6); a.add_argument("--size", type=int, default=384); a.add_argument("--samples", type=int, default=8); a = a.parse_args(argv)
    from studio.worldkit import blender as B, looks
    work = Path(tempfile.mkdtemp(prefix="turn_")); frames = work / "frames"
    with B.cpu_only():
        B.run("wk_turntable.py", {"model": str(Path(a.model).resolve()), "look": looks.resolve("day_clear"), "frames": a.frames, "size": a.size, "out_dir": str(frames), "interior": False, "elevation": 0.35, "kit": "", "samples": a.samples}, work=work, name="turntable", timeout=1800, gpu=False)
    print(sheet(frames, a.out, a.size), "frames ->", a.out)


if __name__ == "__main__": main()

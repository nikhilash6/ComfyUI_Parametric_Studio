"""PSN_PatchDCT_Shrink: overlapping-patch 2-D DCT shrinkage on a nested-list grayscale image.

This is NOT BM3D: it does no block matching and no 3-D grouping. Each overlapping
square patch is transformed with a 2-D DCT, its coefficients are soft- or
hard-thresholded (level = sigma * 0.5), the patch is inverted, and the patches are
averaged back together. Pure Python on a list of rows of floats; it does not accept
ComfyUI IMAGE tensors (anything that is not a non-empty list of equal-length lists
is returned unchanged with a reason). No torch, no GPU, no file or network access.

Helpers in this module: soft/hard thresholds, a 1-D and 2-D DCT-II and inverse,
patch extraction and averaged reassembly, a PSNR metric, input validation, and a
working-set size estimate (bytes) that can be compared with a budget.
"""

import math

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Image"

# ComfyUI uses the string "ANY" as a type marker; we mirror that here.
ANY = "ANY"

# Soft-thresholding modes (mirrors the gate-style "mode" convention).
THRESH_MODES = ("soft", "hard", "none")


def _soft_threshold(x, lam):
    """Soft-threshold a single coefficient: sign(x) * max(|x|-lam, 0)."""
    if lam <= 0.0:
        return x
    ax = abs(x)
    if ax <= lam:
        return 0.0
    return (x - lam) if x > 0 else (x + lam)


def _hard_threshold(x, lam):
    """Hard-threshold: keep x if |x| > lam else 0."""
    if lam <= 0.0:
        return x
    return x if abs(x) > lam else 0.0


def _dct1d(vec):
    """1-D DCT-II (orthonormal-ish, unnormalized) of a list of floats."""
    n = len(vec)
    out = []
    for k in range(n):
        s = 0.0
        for i in range(n):
            s += vec[i] * math.cos(math.pi * (2 * i + 1) * k / (2 * n))
        out.append(s)
    return out


def _idct1d(vec):
    """Inverse of _dct1d (DCT-II inverse), returns the original (scaled)."""
    n = len(vec)
    out = []
    for i in range(n):
        s = vec[0] * 0.5
        for k in range(1, n):
            s += vec[k] * math.cos(math.pi * (2 * i + 1) * k / (2 * n))
        out.append(s * (2.0 / n))
    return out


def _dct2d(block):
    """2-D DCT-II of a square 2-D list (rows x cols)."""
    rows = len(block)
    cols = len(block[0]) if rows else 0
    # transform along columns (each row)
    t = [_dct1d(row) for row in block]
    # transform along rows (each column)
    out = []
    for c in range(cols):
        col = [t[r][c] for r in range(rows)]
        out.append(_dct1d(col))
    # transpose back to row-major
    res = [[out[c][r] for c in range(cols)] for r in range(rows)]
    return res


def _idct2d(block):
    """Inverse 2-D DCT of a square 2-D list."""
    rows = len(block)
    cols = len(block[0]) if rows else 0
    # inverse along columns
    t = []
    for c in range(cols):
        col = [block[r][c] for r in range(rows)]
        t.append(_idct1d(col))
    # t is now col-major; build row-major then inverse along rows
    mid = [[t[c][r] for c in range(cols)] for r in range(rows)]
    res = [_idct1d(row) for row in mid]
    return res


def _extract_patches(image, block_size, stride):
    """Extract overlapping square patches from a 2-D image (list of rows)."""
    h = len(image)
    w = len(image[0]) if h else 0
    patches = []
    for r in range(0, h - block_size + 1, stride):
        for c in range(0, w - block_size + 1, stride):
            patch = []
            for i in range(block_size):
                row = []
                for j in range(block_size):
                    row.append(image[r + i][c + j])
                patch.append(row)
            patches.append((r, c, patch))
    return patches


def _reassemble(patches, block_size, stride, h, w):
    """Average-reassemble patches back into an h x w image."""
    acc = [[0.0] * w for _ in range(h)]
    cnt = [[0] * w for _ in range(h)]
    for (r, c, patch) in patches:
        for i in range(block_size):
            for j in range(block_size):
                acc[r + i][c + j] += patch[i][j]
                cnt[r + i][c + j] += 1
    out = []
    for r in range(h):
        row = []
        for c in range(w):
            row.append(acc[r][c] / cnt[r][c] if cnt[r][c] else 0.0)
        out.append(row)
    return out


def _psnr(clean, noisy, max_val=1.0):
    """Peak signal-to-noise ratio in dB between two 2-D images."""
    h = len(clean)
    w = len(clean[0]) if h else 0
    if h == 0 or w == 0:
        return float("inf")
    mse = 0.0
    for r in range(h):
        for c in range(w):
            d = clean[r][c] - noisy[r][c]
            mse += d * d
    mse /= (h * w)
    if mse <= 0.0:
        return float("inf")
    return 10.0 * math.log10((max_val * max_val) / mse)


def _validate(sigma, block_size, nbd_threshold, h, w):
    """Return (ok, reason). Pure validation, no side effects."""
    if not isinstance(sigma, (int, float)) or isinstance(sigma, bool):
        return False, "sigma must be a number"
    if sigma < 0.0:
        return False, "sigma must be >= 0"
    if not isinstance(block_size, int) or isinstance(block_size, bool):
        return False, "block_size must be an int"
    if block_size < 2:
        return False, "block_size must be >= 2"
    if not isinstance(nbd_threshold, (int, float)) or isinstance(nbd_threshold, bool):
        return False, "nbd_threshold must be a number"
    if nbd_threshold < 0.0:
        return False, "nbd_threshold must be >= 0"
    if h < block_size or w < block_size:
        return False, "image must be at least block_size x block_size"
    return True, "ok"


def _vram_estimate(h, w, block_size, nbd_threshold):
    """Rough working-set estimate in bytes: every overlapping patch stored as
    float32 (num_patches * block_size^2 * 4), doubled for a transform-domain copy.
    It is only compared with the optional byte budget.
    """
    num_patches = max(0, h - block_size + 1) * max(0, w - block_size + 1)
    stack_bytes = num_patches * (block_size * block_size) * 4
    fft_bytes = stack_bytes  # one extra domain copy
    return stack_bytes + fft_bytes


class PSN_PatchDCT_Shrink:
    """Overlapping-patch DCT shrinkage (not BM3D) on a nested-list grayscale image.

    Per patch: 2-D DCT, soft or hard threshold at sigma * 0.5, inverse DCT; patches
    are averaged back. Reports the PSNR of the result against the input (a measure
    of how much changed, not of noise removed) and whether the size estimate fits
    the optional byte budget. IMAGE tensors are not supported.
    """

    DESCRIPTION = ("Overlapping-patch 2-D DCT soft/hard thresholding on a nested-list grayscale image. "
                   "Not BM3D (no block matching, no 3-D grouping) and not for IMAGE tensors. "
                   "psnr_db compares the result with the input, so it measures change, not noise removed.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sigma": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1e9, "step": 0.001}),
                "block_size": ("INT", {"default": 4, "min": 2, "max": 64, "step": 1}),
                "image": (ANY,),
            },
            "optional": {
                "threshold_mode": (list(THRESH_MODES),),
                "vram_budget_bytes": ("INT", {"default": 0, "min": 0, "max": 1 << 62, "step": 1}),
            },
        }

    RETURN_TYPES = (ANY, "FLOAT", "STRING", "BOOLEAN")
    RETURN_NAMES = ("shrunk_image", "psnr_db", "reason", "vram_ok")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, sigma, block_size, image,
            threshold_mode="soft", vram_budget_bytes=0):
        # image must be a 2-D list of floats. Anything else (including an IMAGE
        # tensor) is reported and passed through unchanged.
        if not isinstance(image, (list, tuple)) or len(image) == 0:
            return (image, 0.0, "image must be a non-empty 2-D list", False)
        h = len(image)
        if not all(isinstance(row, (list, tuple)) for row in image):
            return (image, 0.0, "image rows must be lists", False)
        w = len(image[0])
        if any(len(row) != w for row in image):
            return (image, 0.0, "image rows must be equal length", False)

        ok, why = _validate(sigma, block_size, 0.0, h, w)
        if not ok:
            return (image, 0.0, why, False)

        vram = _vram_estimate(h, w, block_size, 0.0)
        vram_ok = (vram_budget_bytes <= 0) or (vram <= vram_budget_bytes)
        if not vram_ok:
            return (image, 0.0, "vram budget exceeded", False)

        # DCT each overlapping patch, threshold the coefficients, invert, average.
        stride = max(1, block_size // 2)
        patches = _extract_patches(image, block_size, stride)
        lam = sigma * 0.5  # shrinkage level derived from sigma
        shrunk_patches = []
        for (r, c, patch) in patches:
            f = _dct2d(patch)
            if threshold_mode == "soft":
                f = [[_soft_threshold(v, lam) for v in row] for row in f]
            elif threshold_mode == "hard":
                f = [[_hard_threshold(v, lam) for v in row] for row in f]
            g = _idct2d(f)
            shrunk_patches.append((r, c, g))
        shrunk = _reassemble(shrunk_patches, block_size, stride, h, w)

        # PSNR of result vs input: how much the image changed (higher = less change).
        psnr = _psnr(image, shrunk, max_val=1.0)
        return (shrunk, psnr, "ok", True)


NODE_CLASS_MAPPINGS = {"PSN_PatchDCT_Shrink": PSN_PatchDCT_Shrink}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_PatchDCT_Shrink": "Patch DCT Shrinkage (list image, not BM3D)"}

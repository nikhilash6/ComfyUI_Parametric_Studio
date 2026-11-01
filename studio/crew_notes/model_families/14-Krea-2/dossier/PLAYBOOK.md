# PLAYBOOK.md: 14-Krea-2

## Prompt structure

## Words and phrasing that work

## Settings that worked

*   **Model File:** krea2/krea2_turbo_bf16.safetensors.
*   **Precision:** Load with weight_dtype fp8_e4m3fn (W8A8). This was allowlisted after A/B testing showed same quality as bf16 but lower VRAM.
*   **Text Encoder:** qwen3vl_4b (type krea2).
*   **VAE:** qwen_image_vae.
*   **Steps:** 8.
*   **CFG:** 1.
*   **Sampler:** euler.
*   **Scheduler:** simple.
*   **Negative Prompt:** None (empty).
*   **Default Seed:** 710001.
*   **Resolution:** Approximately 1 MP on a 32 grid. Examples: 1:1 (1024x1024), 3:4 (896x1184), 9:16 (768x1344), 16:9 (1344x768).
*   **VRAM Usage:** ~22.0-22.7 GB peak at fp8.
*   **Speed:** ~2.3-2.4 seconds per image warm.
*   **Not in notes:** Specific settings for "high" vs "fast" thinking modes (these are mentioned for Krea 3, not Krea 2).

## Processes built on it

## What to avoid

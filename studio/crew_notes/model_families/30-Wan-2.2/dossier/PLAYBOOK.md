# PLAYBOOK.md for 30-Wan-2.2

## Prompt structure

*   **T2V (Text-to-Video):** Use the formula **Entity (description) + Scene (description) + Motion (description) + Aesthetic control + Stylization**.
*   **I2V (Image-to-Video):** Use the formula **Motion + Camera movement only**. The input image defines the entity, scene, and style, so do not describe them in the prompt.
*   **Length:** The official guide provides no word limit, but the encoder holds 512 tokens. The studio uses **40-90 words for I2V** and **70-120 words for T2V** (standard mode).
*   **Prompt Extension:** Prompt extension is optional but recommended to enrich details. It is typically an LLM rewrite step; in this setup, the studio's writer plays that role.
*   **Negative Prompt:** Keep the negative prompt **empty**. The official default is a Chinese string, but it only matters at CFG > 1. Since the standard 4-step graphs run at CFG 1, the negative prompt has no effect.

## Words and phrasing that work

*   **Camera Vocabulary:** Use official terms such as **push in, pull out, pan left/right, tilt up, handheld, following, orbit, fixed camera**. Third-party terms like **dolly in/back, crane, whip pan, orbital arc** are also documented.
*   **Camera Intent:** Each move carries a specific intent: **push-in** for intimacy, **pull-out** for scale, **orbit** for importance, and **fixed camera** for stillness.
*   **Intensity Adverbs:** Use adverbs to control motion speed and intensity, such as **"quickly," "slowly,"** or **"swaying violently."**
*   **Not in notes:** Specific aesthetic or stylization keywords from the "prompt dictionary" table were not fully captured in the provided text (the table sat past the fetch window), though the structure requires them.

## Settings that worked

## Processes built on it

## What to avoid

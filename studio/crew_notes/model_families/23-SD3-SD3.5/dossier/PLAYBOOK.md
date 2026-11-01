# PLAYBOOK.md for 23-SD3-SD3.5

## Prompt structure
Not in notes: The provided documents do not contain specific instructions on prompt structure, syntax, or formatting for the SD3/SD3.5 model family.

## Words and phrasing that work
Not in notes: The provided documents do not list specific keywords, phrases, or stylistic modifiers that have been tested or confirmed to work well for the SD3/SD3.5 model family.

## What to avoid
*   **Using Quantized Weights for Merging:** If performing any model merging operations involving SD3/SD3.5 weights, avoid feeding scaled-FP8/NVFP4 weights to stock merge nodes; merges must use unquantized bf16/fp16 weights only.
*   **Blind Git Pulls:** Check for local patches before updating ComfyUI core, because a plain `git pull` can drop them.

# Qwen-Image and Qwen-Image-Edit: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## Try-on and try-off

Qwen Image 2.1 try-on (template qwen21_tryon) dresses a person in a garment with the Outfit Swap Consistency LoRA at strength 1, 25 steps, CFG 1, as the LoRA's notes say. One family run: 53.7 s, peak 35.1 GiB, seed 1131149263. [code: studio/family_templates/index.json:1995-1997] [run: studio/family_status.json:7725-7739]

Qwen try-on on the studio's test kept the coat's full length and buttons, and the jeans and face stayed the same; the page quotes 80 s and 28 GB. It sits third in the try-on list, after the two Klein LoRA methods. Its page note still says "best on our test", written before Klein 4B with its LoRA became the default on 2026-11-01. [code: studio/tryon.py:14, studio/tryon.py:10-13] [claim: studio commit 3617e621, 2026-11-01]

Qwen Image 2.1 is under the Qwen Research License, for research or evaluation only, and the Outfit Swap LoRA is rent-only on its source. The page marks both try-on and try-off as non-commercial. [code: studio/tryon.py:14, studio/tryon.py:17]

Qwen Image 2.1 try-off (template qwen21_tryoff) asks the base edit model, with no LoRA, for a product shot of what the person wears. One run: 40.7 s, peak 32.5 GiB. On the test it gave a clean white t-shirt with a small label it made up: it invents what it cannot see. [code: studio/family_templates/index.json:2032-2034, studio/tryon.py:17] [run: studio/family_status.json:7740-7754]

## Edit runs recorded on 2026-11-02

Qwen edit templates from ComfyUI each have one recorded run: Qwen Image 2.1 background removal 30.2 s at 25.5 GiB, Qwen Image 2.1 image edit 30.2 s at 27.9 GiB, Qwen Image Edit 2509 (int8) 30.3 s at 28.8 GiB, and 2509 relight 25.2 s at 26.0 GiB. Each was looked at. [run: studio/family_status.json:7755-7814] [claim: studio commit 0abfba0e, 2026-11-02]

Qwen Image 2.1 Turbo with the nvfp4 text encoder (template qwen21_turbo_nvfp4te_t2i) swaps qwen3vl_8b_turbo_nvfp4 in for the bf16 encoder. One run: 25.2 s, peak 17.0 GiB, seed 1647410878. [code: studio/family_templates/index.json:2800] [run: studio/family_status.json:7815-7875] [claim: studio commit 2792c70f, 2026-11-02]

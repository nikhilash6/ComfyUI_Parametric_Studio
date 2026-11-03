# Qwen-Image 2.1: how to write a prompt (checked 2026-11-03)

How Qwen-Image 2.1 wants its prompts, rewritten in plain words from Qwen's own prompt-enhancer models and README. Qwen publishes the enhancers' system prompts under its research licence, so this file summarises them and links to them rather than copying. Where this file and older notes disagree, this file wins. The same rules are the writer's notes in the studio's prompt kits. [claim: Qwen-Image 2.1 README, github.com/QwenLM/Qwen-Image-2.1] [code: studio/prompt_kits.json]

## Text to image

Describe the finished picture as someone looking at it, in one long English paragraph. The first sentence, about twenty words, names the medium (photograph, poster, illustration, infographic, logo), the style, the subject and the background with its colours; never leave out the medium word. [claim: Qwen PE-T2I system prompt, huggingface.co/Qwen/Qwen-Image-2.1-PE-T2I]

Keep everything the request fixed, character for character for any text, and decide everything it left open, so a three-word request still becomes a full description. Place eight to fourteen things with position phrases that reach the corners, edges and centre, and list every legible piece of text in reading order, quoted exactly. [claim: Qwen PE-T2I system prompt]

Never write a ratio, a resolution or a pixel count into the description: the shape is chosen separately, 3:2 for horizontal and 2:3 for vertical unless the subject calls for something else. An instruction about the job, such as "make the text sharp", is obeyed, not described. [claim: Qwen PE-T2I system prompt]

## Editing

Lead with the operation, and edit only what is named, at full strength: under-editing counts as failing. Name what stays in one blanket clause by type or role; describing the kept things in detail makes them drift. For a person or a product from a reference, point at the picture ("the person in <image1>") and never describe the face or the product in words. Pictures are <image1>, <image2> and so on, and image1 is the canvas. [claim: Qwen PE-I2I system prompt, huggingface.co/Qwen/Qwen-Image-2.1-PE-I2I]

On the earlier studio, re-describing a person drifted the face in 1 of 2 seeds, while "the person in this photo" kept it in 2 of 2. Descriptive, text-to-image-style wording barely edited; instructions did. [claim: earlier studio tests]

For a transparent picture, say it is an RGBA image with a transparent background. For a local edit, paint a circle on the picture and name its colour ("the jacket in the red area"). [claim: Qwen-Image 2.1 README]

## Settings and quirks

Official defaults: 40 steps, CFG 1, euler, native 2K sizes (2048x2048 square, 2752x1536 at 16:9). CFG 1 ignores the negative prompt; community users report CFG 2 tightens text but oversharpens, and 5 or more degrades. On the earlier studio, a 2K edit from a 1 MP source reframed the picture, so about 1 MP and 40 steps was the default for edits. [claim: Qwen-Image 2.1 README] [claim: community reports] [claim: earlier studio tests]

Qwen's enhancer models answer in JSON with rewritten_prompt, wh_ratio and ratio_follow, and the key sometimes comes back misspelt as rewrited_prompt, so read both. Give them room: 16,256 new tokens for text to image and 24,000 for edits; with 4,096 the thinking used the whole budget and the answer came back empty. [claim: Qwen-Image 2.1 prompt_rewrite code] [claim: earlier studio notes]

Reusing one seed across a text-to-image step and an edit at the same size replays the same noise, so the edit comes back nearly unchanged. Change the seed between steps. [claim: maintainer comment reported in community notes]

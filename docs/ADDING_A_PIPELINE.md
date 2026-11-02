# Adding a pipeline

A pipeline is several model families making one result. It takes one JSON file and needs no new code.

1. **Write `studio/pipelines/<id>.json`.** It uses the recipe format (`studio/recipes.py`), plus:
   - `order`, the place on the page, and `kicker`, a few words above the title.
   - `models`: every model with its `licence` and `licence_class` (`open`, `community` or `noncommercial`). Every stage names one of them in `model`, so the page always shows its licence. Read the licence on the model's own card.
   - `does` on each stage: one plain sentence.
2. **Pick each stage's type.**
   - `goal`: a studio goal from `studio/goals.py`.
   - `template`: a ComfyUI template, a graph in `studio/family_templates`, or your own in `studio/pipelines/graphs`. Give `peak_gib`, and `seed_node` and `seed` so the seed is recorded.
   - `cpu`: an ffmpeg step, such as `mux`, `join`, `beat_cut`, `compare` or `frame`.
   - `worldkit`: builds a World Kit asset. `vset`: renders a Virtual Set shot. `worldkit_pack`: zips assets for a game engine.
   - `"@step"` passes an earlier stage's output on. `{field}` fills in a value from `fields`.
3. **Check it.** `python -m pytest tests/test_pipelines.py` tells you in a sentence what is wrong.
4. **Run it.** Open the page and press Run, or `POST /api/recipes/<id>/run`. It uses the same queue as every recipe.
5. **Look at every output.** Check hands, faces and any text in the picture, and listen to the audio. If one is bad, change the seed or the prompt and run it again.
6. **Publish what you saw.** Write a review file and run:

   ```
   python scripts/record_pipeline.py <run id> --id <id> --review review.json
   ```

   The review holds your verdict, the status of any stage that was flawed or failed, and what you threw out and why:

   ```json
   {"status": "partial", "verdict": "What you saw.",
    "stages": {"shot2": {"status": "flawed", "note": "The left hand blurs at 3 s."}},
    "rejected": [{"what": "First take", "why": "Six fingers on the right hand."}]}
   ```

A pipeline with no run stays on the page as "Not run yet". A failed run stays on the page as failed.

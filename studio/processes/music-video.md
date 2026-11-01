# Music video maker

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## What is here
Open the **Music Video Maker** recipe (Recipes, or Processes → "Music video" → Open). It writes one song on the Music goal and cuts seven directed H3 shots to it. To pick the song's sound, use the **Style library** under the prompt box of the Music goal.

Everything from "How the earlier maker worked" down to "Batch phases" describes the earlier studio's larger maker. Its screen, review stage, reroll, ArcFace and lip checks, realism finish and batch mode are **not in this studio**. They are kept as the reasoning behind the recipe and as a plan. Nothing below that describes them has been tested here.

## The style library
- **What you can do.** On the Music goal, search or pick a family, open a style, and pick a card. The card shows its BPM, key, singer and mood. Picking it puts the style's name, voice, key and typical BPM in the prompt box, in front of your own tags. Pick another card and the first card's tags are swapped out, while tags you typed or edited stay. Your own BPM or key wins over the card's. **Remove card tags** takes them out again. A full three-block caption in the box is left alone.
- **What is in it.** 19 families, 675 styles, 1,056 cards. 18 families, 634 styles and 988 cards are from MiniMax's official caption-rewriter library (MiniMax-Music3 Community License). 41 styles and 68 cards are studio-authored: the 15 dubstep styles below and 26 novelty and global styles. This edition is safe for work, so anything whose name or card text hit the content scan was left out at build time, which includes the earlier studio's Kids & Family genre. Scene lines and full captions were not carried over either.
- **Where it lives.** Data: `studio/music3_styles.json`. API: `studio/music_styles.py`. Picker: `studio/web/music_styles.js`, `studio/web/music_styles_logic.js`. It is generated, not hand-edited, by a build script that is not in the public repo; that script needs the earlier checkout and stays out of the public release. Tests: `tests/test_music_styles.py`, `tests/studio_lanes/test_music_styles.mjs`.
- **What is proven.** The filter, the API and the prompt filling are tested. **No song has been rendered from a card**, official or studio-authored, in this studio. The prompt reaches Music 3 as one line of tags at AR 1.7, the path the earlier studio measured as weak on genre: [music-engines.md](music-engines.md).

## How the earlier maker worked (its screen is not in this studio)
1. Open **🎵 Music video** in the left rail (or Processes → Video → "Music video" → Open).
2. **Song.** *Make one with Music 3*: pick the **genre** (18 families of the official caption-rewriter library, in its
   router order) and the **subgenre** (type to filter), then the **variation** when a style has several
   templates (each shows its BPM, key and singer). Vocals or instrumental, the singer (as the card / female / male /
   duet), the language (auto = the style's own idiom: Mandopop / C-Pop / Guofeng / Chinese → Mandarin, Cantopop →
   Cantonese, J-Pop / J-Rock / City Pop → Japanese, else English), what the song and video are about, and the lyrics:
   type them with `[verse]` / `[chorus]` tags, press **✍ Write lyrics** (the local content LLM, laid onto the
   skeleton), or leave them empty and the run writes them. *Or use a song you have*: a library song, an uploaded file
   or a studio audio result.
3. **Length** (0:30 … 4:00), **character** (one saved sheet; two for a duet: singing shots alternate), **look**
   (music video, cinematic, 35mm, VHS, noir, dramatic, dark, live / documentary, phone, action cam), **mix**
   (performance / balanced / story = 70 / 50 / 30 % singing shots), **pace** (slow / medium / fast ≈ 6.5 / 4.5 / 3 s
   shots before the section factor), **aspect** (16:9 = the B1 1344x768, 9:16, 4:5, 1:1), **quality** (draft = turbo
   v4 4 steps; final = the full 20-step recipe, ~3x), **best of** (1-3 takes per singing shot), the performance set
   (where they sing; empty = the treatment picks), microphone at the chest, and **pause for my OK** (on by default).
4. **Show the plan** gives the shot count, GPU hours and wall time; **🎵 Make the music video** starts (over 1 GPU hour
   asks first).
5. At **review** the song plays, the analysis shows (BPM, sections, words heard) and the storyboard lists every shot:
   time, section, kind, lens, the lyric words of the singing shots and the prompt (editable). **Approve** renders the
   shots; **New song** makes the song again with a new seed; **Re-plan** cuts the storyboard again (pace / mix / look /
   set / seed) on the same song.
6. The run panel follows each shot (tries, identity, problems). Cancel / Resume are there; when it is done, **↻ Reroll**
   renders one shot again with a new seed and re-joins. The video and its storyboard sheet play in the panel; both
   are normal results (Download etc.), with a `.LICENSE.txt` next to the video.

## The rules the earlier maker followed (and where each comes from)
| Step | Rule | Source |
|---|---|---|
| Song caption | The style's **official template** verbatim (the trained 3-block Global Metadata / Vocal Details / Arrangement format, the genre label in Basic Attributes); the lyrics language appended to the Vocal Style line; the singer line rewritten only when you pick a different singer; your theme as the scenario line | the author's Music 3 notes (official caption + AR 3.0 = 94 % top-1 on the CLAP check) |
| Instrumental | Rule 3: "No vocals. Purely instrumental." in the caption + the instrumental tag layout (never a lone `[Instrumental]`) | the author's Music 3 notes |
| Lyrics | The batch skeleton: ~6 s per sung line (26 lines for 3 min, 22 slow, 30 rap), every tag alone on its line, no numbered tags, no lines under intro / instrumental / outro, identical choruses; ≤ 2000 characters | the author's Music 3 notes |
| Song length | The seconds chip = the next Music 3 ceiling ≥ target × 1.1 (a ceiling, not a target) | rule 2 |
| Song QC | SHORT (< 60 % of the target), SILENCE (an internal gap ≥ 4 s at −45 dB), NO_VOCALS (< 10 words heard) → one new seed, then kept with its flags | the genre batch's QC |
| Cuts | On downbeats; faster on chorus / drop, slower on intro / outro / bridge; a section change preferred as the cut; 2.0–7.8 s per shot | song analysis; H3 lens limits |
| Story shots | H3 image → video (Ref2VA) with the look chip; their own sound replaced by the song (guided-style B-roll, lead 0) | same |
| No chaining | Every shot renders from the same character sheet; never from the last frame of the one before | the earlier long-video test: identity fell ~0.06-0.1 per chained segment, under 0.45 after ~25 s |
| Checks | Output guard; ArcFace to the headshot (bar 0.45, no face = not judged); black / blown frames; **no hard cut inside a shot**; a story shot must not open on its reference picture; reroll, keep the best and flag | long-video checks; the Wren gate's "no internal cut" |
| Join | Frame-exact at 24 fps, one size, hard cuts on the planned beats, the song window under it, fades, two-pass loudnorm to −14 LUFS | the earlier song mix and long-video join |
| Plan / estimate / confirm | GPU = lens × measured rate (H3 4-step ≈ 11 s per s; full ×3) × takes + 15 % rerolls + a cold load; + ~110 s job path per shot; confirm over 1 GPU h | the earlier long-video estimate and smoke test |
| Robustness | JSON state after every step; a restart marks a live run interrupted (Resume carries on); Cancel stops the job in flight | the long-video / Recreate run pattern |

## Gaps the earlier maker had
- **Lip-sync r is not scored** (the Wren gate's ≥ 0.35 needs a lip scorer the studio does not have): check singing
  shots by eye and reroll; best of 2-3 raises the odds (lip-sync follows the seed).
- **Lyric timing** comes from Whisper on the full mix (pp's post transcribe step). Without it (service down) singing
  shots have no line words: the lock still follows the audio.
- **No location reference picture** on singing shots: the B1 recipe's 3 refs (location first) need a scene picture the
  single-character lock path does not send; the performance set is described in words in every prompt.
- **Duets** alternate the two characters per singing shot on the full mix (no stem separation: one audio, one mouth).
- Music 3 needs a visible **"MiniMax-Music3"** attribution for commercial use (rule 7); every video gets a LICENSE note.

## Dubstep and its variants (studio-authored styles)
The official library has no plain dubstep (only `melodic-dubstep-electronic-pop` and `melodic-dubstep-future-bass`, plus `electronic-rock-dubstep` and `electronic-pop-melodic-dubstep` in other families), so the earlier studio wrote its own, **without touching the official styles**.

- **Where they are.** Family *Club, EDM, House & Trance*, or search "dubstep" in the style library. 15 styles, 42 cards, every label starting "Dubstep / ": Classic UK Dubstep (3), Deep Dubstep (2), Brostep (3), Riddim (3), Briddim (3), Liquid Riddim (3), Tearout (3), Deathstep (3), Drumstep (2), Chillstep (3), Hybrid Trap (3; "trapstep" finds it), Colour Bass / Melodic Riddim (3), Post-Dubstep / UK Bass (2), Future Garage (3), Moombahcore (3). Melodic dubstep and future bass stay official and are not duplicated.
- **Instrumental and vocal options.** Each style mixes *instrumental-led* cards (no lead singer: only processed vocal fragments, chops, shouts or a chant) with sung or rapped ones. An instrumental-led card adds the tag "instrumental". Empty lyrics are still your choice to make: see [music-engines.md](music-engines.md).
- **Tempo as written versus felt.** BPMs run from 128 (chillstep piano) to 174 (drumstep), written the conventional dubstep way (140 felt as 70). A card reads "172 BPM (felt 86)", the style shows its tempo line, and a half-time card adds the tag "half-time feel". The official melodic dubstep cards say 171 for the same kind of music. Nobody has compared them by ear.
- **Search all families.** A typed phrase matches a style's label, id or alias in every family, so "dubstep" also finds the official Electronic Rock / Dubstep and Electronic Pop / Melodic Dubstep.
- **Marked everywhere.** The list and each card read "studio-authored, untested", and a note says "Studio-authored recipe, not an official Music 3 template, untested (nothing has been rendered from it yet)". Style and card data carry `source: "studio"` and `proof: "recipe"`. Proof level of every one: **recipe**, written from sources, not verified, not even load-tested. The earlier studio's novelty and global styles carry the same marks.
- **What was left behind.** Each dubstep card had a full three-block caption in the earlier studio, built with a checker that refused artist, label and plugin names. Those captions and that builder are not in this studio: a card fills tags only.
- **Honest limit: nothing has been rendered with Music 3 from these styles.** Whether it follows a half-time feel, a wobble or a clean sub from text is unmeasured. Judge by ear and report back.

## Batch phases (earlier maker; built there, nothing timed on the GPU)
The recipe here does not have this. Request field `batch_phases`: `"auto"` (default, nothing stored) | `"on"` | `"off"`; a **Batch phases** select sits beside the prompt-length select. Auto is on from 3 shots, so almost every music video is batched. On: the writer LLM writes **all** the shot prompts first (new stage `prepare`, status "Writing the shot prompts", before the review), the review shows the written prompts ("Prepared H3 prompt" under each shot), and after your OK the shots render back to back, each carrying its prompt (`pre_enhanced`, the writer is skipped, the prompt guard still reads the final prompt). The writer is dropped before the first render through the existing room logic. A shot whose prompt could not be written falls back to writing its own at render time (a note says so). Edit a shot at review and only that shot's prompt is written again; a reroll writes a fresh prompt for that shot only; re-plan discards the written prompts. The plan and the run header say the mode and the expected saving, labelled **estimate** (about 35 to 78 min for 48 shots). Off = the old run, request for request. Details, limits and the measurement protocol: [batch-phases.md](batch-phases.md).

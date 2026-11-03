# Song hooks and the first seconds: what the research says (checked 2026-11-03)

This is research on what makes a song or a loop catch, rewritten in plain words. It came from a graded literature review done for the studio this one grew from, plus measurements of that studio's own renders. Nothing here was re-run for this studio unless a run label says so. NOW.md describes what the Music page really rendered; where the two disagree on a fact about this studio, NOW.md wins. [inference]

Labels: a paper named in a claim label was read at least as an abstract by the earlier review, not by us. "Earlier studio" means a measurement on that studio's renders. [inference]

## Nothing predicts a hit

The best audio-only hit prediction found was about 0.74 accuracy over more than 500,000 songs, rising to 0.85 only when the artist's recent chart presence was added. Models trained on one year get worse on the next, and none was tested on short-video sound popularity. A song checker can say whether a track is well formed. It must never give a chance of success. [claim: Interiano et al. 2018, Royal Society Open Science] [claim: earlier studio literature review, 2026-10-17]

## The first seconds

Listeners decide early. In streaming data a quarter of songs were skipped within 5 s and about half were played to the end, and skips bunched about 3.5 s after a section change. [claim: Montecchio, Roy and Pachet 2020, PLOS ONE]

Pop has moved its start forward. Across 303 top-10 singles the intro before the first vocal fell from over 20 s in the mid-1980s to about 5 s by 2015, and a later study found the trend mostly continued to 2020. But songs by the same artist showed no stream difference by intro length, so a short intro is a fashion, not a proven cause. [claim: Léveillé Gauvin 2018, via Ohio State University news] [claim: Klimmt et al. 2023, Convergence]

For a hook: put it in the first seconds, start at full level, and end on a point that loops. A clip to be reused works best at 5 to 10 s, the length memory favours. [claim: earlier studio literature review, 2026-10-17] [inference]

## What a catchy tune has

Tunes people name as earworms were faster (mean about 124 BPM), followed common arch-shaped contours, and used smaller steps and longer notes. A three-feature model told them apart 62.5% of the time against a chance of 50%, so these lean the odds, nothing more. [claim: Jakubowski et al. 2017, Psychology of Aesthetics, Creativity, and the Arts]

Groove peaks at medium syncopation: too little is dull, too much stops people wanting to move. Liking follows a balance of the expected and the surprising, a familiar frame with one controlled surprise. [claim: Witek et al. 2014, PLOS ONE] [claim: Gold et al. 2019, Journal of Neuroscience]

More repetitive lyrics were processed more easily and reached number one more often in Billboard charts from 1958 to 2012. In a Music 3 brief that means identical choruses, which the studio's prompting notes already ask for. [claim: Nunes, Ordanini and Valsesia 2015, Journal of Consumer Psychology] [docs: docs/MODEL_COOKBOOK.md]

## Loudness for delivery

The one official figure found: a music streaming service normalises to -14 LUFS integrated and leaves 1 dB of headroom for lossy encoding. No short-video app publishes a target, and vendor blogs disagree. [claim: Spotify loudness normalization help page]

On the earlier studio, 24 Music 3 songs measured a median of -13.8 LUFS with a true peak of +0.1 dBTP, three quarters of them above -0.1 dBTP, with clipped samples in most files. Their first second sat about 8 dB under the file's median level, a slow fade-in, and they started near -33 dB and ended near -48 dB, so a plain loop has an audible re-entry. [claim: earlier studio measurement of its own renders, 2026-10-17]

This studio's Music page shows the same hot output: the Music 3 render measured -12.5 LUFS with a true peak of 0.5 dB, and every model on the page peaked above 0 dB except Stable Audio Open and DiffSynth-Music. A limiter at -1 dBTP before delivery fixes it, and the studio's mastering step targets -14 LUFS and -1 dBTP. [run: studio/music_proof.json] [code: studio/audio_master.py:1-7]

## A hook cutter, if one is built

The earlier review proposed cutting a 5 to 10 s hook from a full song: start on a strong onset at full level, end on a loop point with matching level and slope over the last and first 5 to 20 ms, and master the cut to -14 LUFS and -1 dBTP while keeping the raw take. It was never built or tested. [claim: earlier studio literature review, 2026-10-17] [inference]

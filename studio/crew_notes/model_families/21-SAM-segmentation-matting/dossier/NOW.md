# SAM, segmentation and matting: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## SAM 3 itself: no new run

SAM 3 rendered on 2026-11-03 on its own family server: template utility_image_segment_sam3 on a Kolors picture, 6.2 s, 2.4 GiB peak. The mask was looked at over the picture. One run on the test machine. The earlier SAM 3.1 video segment run (45.6 s) is in the 2026-11-01 evidence table. [run: studio/family_status.json:8840, studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

SAM 3 is under the SAM License: commercial use is allowed, with use rules. [code: studio/licences.py:90]

## Masks and cut-outs made by other families

Qwen Image 2.1 background removal has a recorded run on 2026-11-02: 30.2 s, peak 25.5 GiB. It is an edit model asked to remove the background, not a segmenter. [run: studio/family_status.json:7755-7769] [claim: studio commit 0abfba0e, 2026-11-02]

SAM 3D Objects, in the 3D notes, takes a cut-out and its mask; its run on 2026-11-01 used a bear cut-out and mask. [run: studio/model3d_proof.json:102-111]

## SeC-4B is planned, not on disk

SeC-4B, a video object segmenter, is in the studio's download plan as part of the Wan Animate character set. The only single-file source is a community repack of the official model (Apache-2.0). It was never downloaded before, and it was not on disk when these notes were written. [claim: studio download records 2026-11-03]

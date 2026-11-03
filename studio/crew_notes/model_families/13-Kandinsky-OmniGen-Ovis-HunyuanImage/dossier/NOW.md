# Kandinsky, OmniGen, Ovis and HunyuanImage: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## No new runs since 2026-11-01

None of this folder's four families gained a render in the final session; the records are as STATE.md describes them. [run: studio/family_status.json:3569-3648, studio/family_status.json:4250-4418, studio/family_status.json:6966-7091, studio/family_status.json:7113-7195] [docs: studio/crew_notes/model_families/13-Kandinsky-OmniGen-Ovis-HunyuanImage/dossier/STATE.md]

HunyuanDiT-1.2's family holds four runs: two generic test renders at 16.1 s, HunyuanImage 2.1 at 30.2 s, and the core HunyuanDiT 1.2 template at 20.2 s, seed 1908372649. [run: studio/family_status.json:3594-3646]

Kandinsky 5.0 Lite has two picture runs at 20.3 s and one image-to-video run (video_kandinsky5_i2v, 5 s model) at 354.6 s, peak 28.7 GiB, seed 593325116. Its text-to-video template is kept off the Families page. [run: studio/family_status.json:4275-4315] [code: scripts/record_family_renders.py:13]

OmniGen2 has two text-to-image test runs at 16.0 s and one image edit at 30.6 s, seed 1611872186, on omnigen2_fp16. [run: studio/family_status.json:7012-7051]

Ovis-Image has two test runs at 18.0 s. Its text-to-image template is kept off the Families page, because its fine runs show the template's own sample people and the studio does not show faces it cannot vouch for. [run: studio/family_status.json:7138-7164] [code: scripts/record_family_renders.py:11-13]

The large peaks in the early test rows (31.4 to 67.4 GiB) were measured for the whole card on the shared main ComfyUI. They are not what these models need on their own. [run: studio/family_status.json:3594, studio/family_status.json:4275, studio/family_status.json:7012, studio/family_status.json:7138] [inference]

## Licences

HunyuanDiT is under the Tencent Hunyuan Community License, and HunyuanImage 2.1 does not apply in the EU, the UK or South Korea. Kandinsky 5.0 Lite is MIT; OmniGen2 and Ovis-Image are Apache-2.0. [code: studio/licences.py:53, studio/licences.py:63, studio/licences.py:80-81]

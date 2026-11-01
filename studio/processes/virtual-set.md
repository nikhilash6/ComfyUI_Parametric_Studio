# Virtual Set

Block a shot in a real-scale 3D place, move an exact camera through it, and steer a video model with what Blender renders: depth, pose and shaded passes, plus first and last stills. Open it from the **Virtual Set** button in the left rail.

Status: modes A (H3 depth and LTX-2.5 with raw keyframes), B, C (raw keyframes) and D have each rendered once here on one street shot, and QC passed. Wan, a pose pass, and the Qwen keyframe steps have not run on these passes yet.

## What you need

- Blender, and an approved place from World Kit. That is enough for the passes. No model, no GPU and no ComfyUI.
- For the video, the model files of the mode you pick. The page asks the server, which reads the disk on every call: a 0-byte placeholder, a hash sidecar or a config file is not a model. If something is missing the page says so in plain words, for example "Wan 2.2 Fun Control (high noise): model still downloading or missing", and Render video stays off.

## Modes

| Mode | What goes in | Model | Length and size |
|---|---|---|---|
| A guide passes | the exact depth pass, or the pose pass when the shot has a cast | MiniMax H3 Fun Union 2.0 on the FL2VA base. Or Wan 2.2 Fun Control, with the first still as its reference picture | H3: 5 s, 124 frames at 24 fps, 16:9, 9:16 or 1:1. Wan: 81 frames at 16 fps, 832 x 480 or 480 x 832 |
| B restyle | the shaded render and the exact depth pass | MiniMax H3 Fun Union 2.0 | 5 s, 124 frames at 24 fps |
| C keyframes | the first and last stills | Qwen-Image 2.1 makes each one photoreal, then MiniMax H3 first and last frame. Set keyframes to "use the Blender stills" and only H3 is needed | 5, 8 or 10 s |
| D motion copy | the shaded render as a reference clip, the first still as the reference picture | MiniMax H3 reference to video | 5, 8 or 10 s |

H3 sizes are 1344 x 768, 768 x 1344 and 1024 x 1024. H3 takes 17k+5 frames, so 5 s is 124, 8 s is 192 and 10 s is 243, and the passes are rendered at exactly that count.

Modes A (depth) and B send H3 the same control. In both the regeneration mask is solid white, so H3 sees the source clip masked out: the shaded render's colours do not reach it in mode B. The depth pass and your words decide the picture. To carry the look of the render itself, use C or D.

Mode A's third engine is LTX-2.5 Layout to Render: 121 frames at 24 fps, 1920 x 1088 or 1088 x 1920 out, driven by a grey clay pass and the first still. With raw keyframes the video keeps the Blender look, because the first still sets the art direction.

## Using it

1. **Pick an approved place**, add props with a position and a turn, and give the marks the camera follows, in metres (`0,0; 0,-3`). With no cast these are an empty point moving through the set.
2. **Write the action**, pick a camera move (slow push-in, orbit, tracking alongside, point of view, handheld, static, or a custom path from a start to an end), the format, the look and the mode.
3. **Preview camera** draws the move on a plan of the set, with a frame slider. Nothing renders.
4. **Render passes** runs Blender on the CPU and needs nothing else. On this machine a 5 s shot at 1344 x 768 took about 19 minutes on 16 threads, with other jobs running.
5. **Render video** keeps finished passes and sends them to the model. It stays off until the mode's files are there.
6. **Cancel** stops a render, killing Blender through its own process group. **Retry** resumes from the step that did not finish. Saving a changed shot clears its render.

## Passes

Kept with the shot, under `shots/<id>/passes/`: `shaded.mp4`, `depth.mp4`, `pose.mp4`, `edges.mp4`, `first.png`, `last.png`, `camera.json` and the frames. Each video is counted after encoding, and a pass with the wrong number of frames fails the step.

- **Depth**: 8-bit grey. Near is white, far and open sky are black, linear in metres from 0.3 m to the farthest corner of the place seen from any camera position, capped at 80 m. One sample, no denoiser, no dither, no colour management.
- **Ids**: one flat colour per object, used to draw the edges. Not encoded as a video.
- **Pose**: OpenPose skeletons drawn from the rig with the same camera maths as the render. With no cast these are black frames, so mode A refuses a pose pass for such a shot.
- **Edges**: drawn from depth and id borders.

## QC

After a video, on the CPU. Flicker is judged and can fail a shot. Layout (edge overlap with the Blender edge pass) is a number for you to read and never fails one. A failed video or a failed flicker check gets one automatic reroll with a new seed and keeps the passes, then the shot waits for review. The seed that made the final video is saved in the shot. The flicker limit of 6.0 is a starting guess.

**The face match does not run here.** It needs a saved character in the shot and a face classifier, and this studio ships no face classifier. The result says so.

## Shot lists

One shot per line in the last saved shot's set, look, mode and format, up to 12. Words in a line pick the camera (orbit, tracking, point of view, static), otherwise moves rotate. Seeds step on. After rendering, a set-consistency score compares each shot's colours with the first. Its limit of 0.6 is a starting guess.

## Characters

Off by default, as in World Kit. A shot works with a place and props alone. With `STUDIO_WORLDKIT_CHARACTERS=1`, a shot takes up to two approved, rigged characters, each with a clip and marks. H3's depth control has no identity input, and in mode D the reference picture is the first still, so nothing here locks a face.

## What the safety check covers

The shot's name, action and settings, a list's name and script, and the final prompt with the words it takes from assets go through the studio's safe-for-work word check, plus World Kit's rule that refuses a word for a young person together with words for undress or a body on show.

**What it does not cover:** it reads words only. This studio has no image classifier, so a Blender frame, a generated keyframe and a finished video are not checked by what they show. Nothing can tell whether a character looks like a real person, which is why characters are off by default.

## HTTP API (`studio/vset/api.py`)

- `GET /api/vset/meta`, `GET /api/vset/capabilities`, `POST /api/vset/camera` `{shot}`
- `GET|POST /api/vset/shots` (`{shot, render?: true | "passes"}`), `GET /api/vset/shots/<id>`, `GET /api/vset/shots/<id>/file/<depth|pose|edges|shaded|first|last|key_first|key_last|video>`
- `POST /api/vset/shots/<id>/<render|passes|retry|cancel>`
- `GET|POST /api/vset/lists`, `GET /api/vset/lists/<id>`, `POST /api/vset/lists/<id>/<order|render>`

## Settings

Environment variables, or the machine's settings file. World Kit's `STUDIO_BLENDER`, `STUDIO_WORLDKIT_THREADS`, `STUDIO_WORLDKIT_GPU` and `STUDIO_WORLDKIT_CHARACTERS` apply here too.

| Setting | Meaning | Default |
|---|---|---|
| `STUDIO_VSET_ROOT` | where shots and lists live | a `parametric-studio/vset` folder under the home folder's `.local/share` |

## Troubleshooting

- **The shaded frames are black at the start**: the camera began inside a building. Open the plan view, then change the marks or the distance.
- **"has no asset.glb" or "not approved"**: the asset changed in World Kit after the shot was saved. Approve it again, or pick another.
- **Render video is off**: read the "Not ready on this machine" box. Mode C with the Blender stills as they are needs only H3.

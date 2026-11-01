# CU-360 - Image to mesh with core nodes

**Objective.** Read an image-to-mesh graph, know which part generates and which part only converts, and pick the mesh option that doesn't give you cubes. Taught by Professor Latent.

## The idea

3D generation in ComfyUI is less exotic than it sounds. Hunyuan3D 2 samples a latent with an ordinary `KSampler`, guided by an image in place of a prompt. What's new sits at each end: the shape of the latent, and a last step that turns a field of numbers into triangles.

We have not run these graphs. They pass ComfyUI's validation, but the weights aren't on our test machine, so nothing below comes from a render of ours.

{{graph:hunyuan3d_mesh}}

![A sample for Hunyuan3D 2.1 from ComfyUI's template library. MIT licensed, and not rendered by us.](families/lib_hunyuan3d-2-1.webp)

## Walk the graph

**`ImageOnlyCheckpointLoader`.** The loader returns a model, a vision encoder and a VAE, with no text encoder at all.

**`LoadImage` and `CLIPVisionEncode`.** The picture goes through the vision encoder with `crop` set to `center`, so anything outside the centre square is lost. Square your image first.

**`Hunyuan3Dv2Conditioning`.** The positive is the image's `last_hidden_state`. The negative is zeros of the same shape. So CFG here pushes away from "no image".

**`EmptyLatentHunyuan3Dv2`.** Here's the strange part. It makes `[batch, 64, 3072]`, which has no height, width or depth. It's a list of 3072 tokens, each with 64 numbers. `resolution` is how many tokens, not a size in space.

**`KSampler`.** Ordinary: 30 steps, cfg 5.5, euler. Hunyuan's paper describes the shape model as a flow-based diffusion transformer.

**`VAEDecodeHunyuan3D`.** The tokens hold a shape implicitly. The decoder asks a question at each point of a grid: what value is here? With `octree_resolution` 256 that's 257 points per side, nearly 17 million. `num_chunks` is how many points it asks about at a time, so it trades memory for speed. This node's output is the `VOXEL` type.

**The mesh node, then `SaveGLB`.** Finally a threshold decides what counts as inside.

## Cubes or a surface

There are two ways to turn that grid into triangles, and the first graph uses the older one.

**`VoxelToMeshBasic`**, which the node marks as deprecated, or `VoxelToMesh` set to `basic`, draws a square on every exposed face of every solid cell. It gives you stairs. It also makes separate vertices per face, so the shape isn't welded.

**`VoxelToMesh` set to `surface net`** puts one vertex in each cell the surface crosses, at the mean of where the surface crosses the cell's edges, using the values between grid points. This one's smooth.

{{graph:e_hunyuan3d_surfnet}}

Here it is in 2D. The same effect is why blocks can't converge on the right area:

{{play:isosurface}}

## What goes wrong

- **A staircase shape.** You used basic. Switch to `VoxelToMesh` with `surface net`.
- **The object is too fat or too thin, or missing parts.** The threshold moves the surface. In the lab a threshold of 0.6 on a sphere of radius 0.7 leaves only 108 triangles. Try a lower one. If the surface is empty, lower it further.
- **Out of memory at decode, after sampling finished.** Lower `octree_resolution`, or lower `num_chunks`. 256 is 2,122 batches at 8000 points each.
- **Long decode times.** The cost grows with the cube of `octree_resolution`: 512 takes 8 times the queries of 256.
- **Cropped results.** `crop: center` cut your object. Pad to square first.
- **A background shows up in the shape.** The vision encoder sees everything you give it. Our reading is that cutting out the object first helps, but we haven't tested it. Note that this graph has no step for it.
- **Far too many triangles.** Normal. Clean up with the tools in CU-362.

## Lab

The lab builds a field for a sphere of radius 0.7, where value = 0.7 minus distance, on the same kind of grid the decoder uses. Then it meshes it with a port of each method. The grid sizes go up, and the error goes down, except for the area of the blocks:

```text
a sphere of radius 0.7, true area 6.158. Field value = 0.7 - distance, so threshold t makes radius 0.7 - t
grid   basic triangles   basic area / true   surface net triangles   surface net area / true   vertex distance error
16     1,164             1.507               1,164                   0.980                     0.0077
32     4,620             1.495               4,620                   0.995                     0.0020
64     18,588            1.504               18,588                  0.999                     0.0005
the blocky area stays near 3/2 however fine the grid is; the surface net converges to the truth
```

The blocky area stays at about 3/2 of the truth at every grid size. Finer grids make smaller stairs and the same total. Our surface net is a simple version, checked by running the real function too. At 32 the real one gave 4,728 triangles, and this one gives 4,620. Then the threshold:

```text
threshold moves the surface: on the same 32 grid
threshold 0.0 :  4,620 triangles, expected radius 0.7
threshold 0.1 :  3,516 triangles, expected radius 0.6
threshold 0.3 :  1,548 triangles, expected radius 0.4
threshold 0.6 :    108 triangles, expected radius 0.1
```

And the cost of the decode, followed by the latent:

```text
octree_resolution   grid points     decoder batches at num_chunks 8000
64                  274,625         35
128                 2,146,689       269
256                 16,974,593      2,122
512                 135,005,697     16,876

EmptyLatentHunyuan3Dv2 at resolution 3072: latent [1, 64, 3072], a list of 3072 tokens with no grid in it
```

## Sources

- [Hunyuan3D 2.0: Scaling Diffusion Models for High Resolution Textured 3D Assets Generation](https://arxiv.org/abs/2501.12202)
- [ComfyUI v0.43.0, comfy_extras/nodes_hunyuan3d.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_hunyuan3d.py)
- [ComfyUI v0.43.0, comfy/ldm/hunyuan3d/vae.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/hunyuan3d/vae.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_save_3d.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_save_3d.py)

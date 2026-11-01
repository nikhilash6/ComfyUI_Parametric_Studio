# CU-513 - History 13: Seeing in 3D: NeRF, Gaussian splats and structured latents

**Objective.** Explain how NeRF and Gaussian splatting draw a picture, why the second is so much faster, and where structured latents fit. Taught by Professor Latent.

## The idea

For decades, 3D meant triangles. Then, around 2020, researchers asked a different question. Forget surfaces. If you want a picture from a new angle, what's the least you need to know? Only how much light each point along each ray gives and blocks.

## NeRF: a network that answers questions

**NeRF (2020)** trains a network on photos of one scene. Its input is a 5D coordinate: a position (x, y, z) and a viewing direction. Its output is a volume density and a colour for that view. There's no stored shape. The scene lives in the network's weights.

To draw one pixel, walk along its ray, ask the network at many points, and add up. The usual sum looks like this:

```
alpha_i = 1 - exp(-density_i x step_i)
T_i     = product over earlier samples of (1 - alpha_j)
colour  = sum of T_i x alpha_i x colour_i
```

T is what light gets through so far. That's what makes near things hide far things. The cost is the catch. At 192 samples per ray, an 800 x 800 image is about 123 million network queries.

## Gaussian splatting: just draw the blobs

**3D Gaussian Splatting (2023)** keeps the idea of soft, see-through material, and drops the network at drawing time. It fits a cloud of 3D Gaussians to the photos, then rasterizes them. Its paper reports real-time rendering at 1080p.

{{play:splat}}

Each blob has a place, a size in three directions, a rotation, an opacity and a colour. Order matters: blending the same blobs in a different order gives a different picture, so renderers sort them. Core's `RenderSplat` composites front to back through depth slabs.

## Then: generating 3D

Both of those fit one scene from photos. They don't invent anything. To generate, you need a latent space for 3D, and a sampler.

**Structured latents (2024)**, or SLAT, the idea behind TRELLIS, keeps a sparse 3D grid with features attached, then decodes to radiance fields, Gaussians or meshes. In ComfyUI, `SLatFlowModel` is the flow model, and `VaeDecodeShapeTrellis` is one of its decoders.

**TripoSplat** in core uses `LatentSeqMMFlowModel`, then `VAEDecodeTripoSplat` makes a `SPLAT`. `render_splat` draws previews during sampling. **Hunyuan3D 2** uses a list of tokens and queries points, which you can read through in CU-360.

{{graph:hunyuan3d_mesh}}

![A sample for Hunyuan3D 2.1 from ComfyUI's template library. MIT licensed, and not rendered by us.](families/lib_hunyuan3d-2-1.webp)

## A name that misleads

`comfy/ldm/chroma_radiance` has `NerfEmbedder` and `nerf_blocks`. An earlier draft of this lesson claimed that it lets the model "think in 3D". It doesn't. The docstring says `NerfEmbedder` adds a 2D positional encoding to image patches. Chroma Radiance is an image model that borrows the coordinate-network idea for pixels. Read the code, not the name.

## What goes wrong

- **Treating NeRF as a generator.** The original fits one scene from photos. It can't dream up a new one.
- **Too few samples on a thin surface.** A wall thinner than the sample spacing can be missed entirely. In the lab, 16 and 64 samples see nothing.
- **Blobs in the wrong order.** Wrong blending looks like the near object is see-through. Use the renderer's sort.
- **Calling Chroma Radiance 3D.** See above.
- **Asking for a mesh from a splat without loss.** A surface has to be invented. See CU-361.
- **Assuming "real time" applies to your job.** That claim is about drawing a finished splat. Generating one is another matter.

## Lab

The sum on three slices of opacity 0.5, red, green and blue. Each one takes half of what's left:

```text
three slices, alpha 0.5: colour [0.5, 0.25, 0.125]  transmittance [1.0, 0.5, 0.25]  background keeps 0.125
```

A soft ball of fog is easy. With few samples the answer is rough, and it soon settles:

```text
ray through fog, exact opacity 0.864665
samples per ray   opacity
5                 0.909282
7                 0.819908
16                0.864665
64                0.864665
192               0.864664
```

A thin wall is hard. Evenly spaced samples miss it, then hit it by luck:

```text
a thin wall, 0.04 thick, density 200, seen through evenly spaced samples:
  16 samples: opacity 0.0000
  64 samples: opacity 0.0000
 128 samples: opacity 1.0000
 256 samples: opacity 0.9981
 512 samples: opacity 0.9999
```

That is why NeRF-style methods put effort into where to sample. Then the cost:

```text
NeRF at 800 x 800, 192 samples a ray: 122,880,000 network queries per image. Splats: no network at render time, one projection per Gaussian
```

And order. The same three blobs, sorted against unsorted:

```text
three Gaussians at depths 2, 1, 3, sorted before blending: [0.25, 0.5, 0.125] (the nearest colour wins most)
unsorted, in stored order: [0.5, 0.25, 0.125]
```

## Sources

- [NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis](https://arxiv.org/abs/2003.08934)
- [3D Gaussian Splatting for Real-Time Radiance Field Rendering](https://arxiv.org/abs/2308.04079)
- [Structured 3D Latents for Scalable and Versatile 3D Generation](https://arxiv.org/abs/2412.01506)
- [ComfyUI v0.43.0, comfy_extras/nodes_gaussian_splat.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_gaussian_splat.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_trellis2.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_trellis2.py)
- [ComfyUI v0.43.0, comfy/ldm/trellis2/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/trellis2/model.py)
- [ComfyUI v0.43.0, comfy/ldm/triposplat/preview.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/triposplat/preview.py)
- [ComfyUI v0.43.0, comfy/ldm/triposplat/gaussian.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/triposplat/gaussian.py)
- [ComfyUI v0.43.0, comfy/ldm/chroma_radiance/layers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/chroma_radiance/layers.py)

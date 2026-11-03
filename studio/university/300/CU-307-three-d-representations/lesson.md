# CU-307 - 3D generation: meshes, SDFs, voxels and Gaussian splats

**Objective.** Say what each 3D representation stores, how its cost grows, and how they convert into one another. Taught by Professor Latent.

## The idea

An image is a grid and nobody argues about it. In 3D there's no single natural form, and that choice shapes everything. Think of a sphere. You can store which cubes are full, the distance to the surface everywhere, a skin of triangles, or a cloud of soft blobs. Each is good at something.

| kind | stores | good at | bad at |
|---|---|---|---|
| Voxels | a value per cell of a 3D grid | easy for networks | cost grows with the cube |
| SDF | signed distance per point: minus inside, plus outside | smooth surfaces, simple sums | still a field, needs converting to show |
| Mesh | vertices and triangles | games, printing, physics | hard for networks to generate directly |
| Gaussian splat | soft oriented blobs | looks real, draws fast | no surface |

## How the sizes grow

A grid's cost grows with the cube of its resolution. A 1024 grid has over a billion cells. But the surface of a shape grows only with the square. Most cells are empty air or solid inside. So real systems keep only cells near the surface, called a narrow band or a sparse grid. `SparseTensor` in Trellis 2 stores only the occupied coordinates, and `_build_narrow_band_voxels` does this for remeshing. Meshes and splats also follow the surface.

## Stairs

Here's a fact that surprises people. Draw a sphere in cubes, and measure the area of the exposed faces. It comes to 1.5 times the true area, and a finer grid doesn't help.

Why? Each axis sees the sphere's shadow from both sides, and stairs add up to those shadows: 3 axes x 2 sides x πr² = 6πr², against the true 4πr². Smaller stairs have the same total. Smoothness has to come from values between grid points, which occupancy doesn't have and an SDF does. Try it in 2D, where the ratio is 4/π:

{{play:isosurface}}

## In ComfyUI

Core passes three geometry types on wires: `VOXEL`, `MESH` and `SPLAT`.

- **Hunyuan3D 2** generates a latent, decodes it to a grid of values, and makes a mesh. CU-360 walks through it.
- **Trellis 2** works on sparse voxels with a flow model, `SLatFlowModel`, and `ShapeVae` to decode.
- **TripoSplat** generates a latent sequence, and `VAEDecodeTripoSplat` turns it into a `SPLAT`.
- **Conversions:** `VoxelToMesh`, `SplatToMesh`, and for cleaning, `RemeshMesh` and `DecimateMesh`. CU-361 and CU-362 cover these.

{{graph:hunyuan3d_mesh}}

![A sample for Trellis 2 and Pixal3D from ComfyUI's template library. MIT licensed, and not rendered by us.](families/lib_trellis-2-4b.webp)

![Our own Trellis 2 run: ComfyUI's core Trellis.2 nodes with a baked PBR texture, from one cut-out picture of a bear, turned in Blender on the CPU. Lit from the side, the fur reads pale. Recorded: 253.1 s, peak 18.2 GiB. One seed.](families/trellis-2-4b_turn.webp)

{{video:pipelines/drawing_to_figure/figure.mp4|A pipeline built on it, Drawing to Figure: Anima drew a round robot postman, Trellis 2 built a textured mesh from that one picture, and Blender set it at 18 cm with its pivot at the base and turned it. From the front it matches the drawing; the back, which the drawing never showed, is covered in grey smudges. 72 frames at 512 x 512.|pipelines/drawing_to_figure/figure.webp}}

## What goes wrong

- **Calling an SDF a mesh.** An SDF is a value at every point. You have to extract a surface from it.
- **Raising voxel resolution until memory runs out.** The cost is cubic. Use a sparse method, or use the surface extraction to get more from the grid you have.
- **Expecting a splat to behave like a solid.** It has no inside. Physics and printing need a mesh.
- **Measuring blocky meshes for area.** On a sphere the area is 50% too high at any resolution. The factor depends on the shape: a cube lined up with the grid has none. Volume is fine: the lab's 325,184 inside voxels at grid 128 are within 0.1% of the sphere's volume.
- **Keeping millions of triangles.** Use `DecimateMesh`.
- **Assuming any mesh is watertight.** It might not be. `RemeshMesh` in `solid` mode aims for a watertight solid from messy input.

## Lab

Cubes around a unit sphere, at three grids:

```text
grid    voxels stored   inside voxels   near-surface voxels   blocky area / true
32      32,768          5,040           2,864                 1.511
64      262,144         40,800          11,624                1.507
128     2,097,152       325,184         46,184                1.500
```

The area doesn't improve. The exact limit, and what the first version of this lab did wrong:

```text
the area of the blocks stays near 3/2 of the truth. A finer grid gives smaller stairs, not less stair
exact limit: 6 pi r^2 / 4 pi r^2 = 1.500
counting both walls of a thin shell, as the first version of this lab did: ratio 3.04
```

Finding the surface along a ray. Occupancy can only say which sample passed the surface. An SDF lets you interpolate, and this one lands exactly since the distance is linear along the ray:

```text
surface radius recovered along a ray by linear interpolation between SDF samples, against the staircase answer
  8 samples: SDF crossing 1.0000   occupancy only 1.1250
 16 samples: SDF crossing 1.0000   occupancy only 1.0312
 32 samples: SDF crossing 1.0000   occupancy only 1.0312
```

How each kind grows, roughly. Only the full grid grows with the cube:

```text
resolution   full grid, 1 float   thin band, coords + 1 float   triangle mesh, about   Gaussians at band count, 14 floats
64           1.0                  0.2                           0.4                    0.6  MiB
256          64.0                 2.8                           6.3                    9.8  MiB
1024         4096.0               44.7                          100.5                  156.4  MiB
```

And a Gaussian, soft all the way out:

```text
one Gaussian of scale 0.1, value at a distance: [1.0, 0.607, 0.135, 0.011]
```

## Sources

- [3D Gaussian Splatting for Real-Time Radiance Field Rendering](https://arxiv.org/abs/2308.04079)
- [Structured 3D Latents for Scalable and Versatile 3D Generation](https://arxiv.org/abs/2412.01506)
- [ComfyUI v0.43.0, comfy_api/latest/_util/geometry_types.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api/latest/_util/geometry_types.py)
- [ComfyUI v0.43.0, comfy/ldm/trellis2/vae.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/trellis2/vae.py)
- [ComfyUI v0.43.0, comfy/ldm/trellis2/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/trellis2/model.py)
- [ComfyUI v0.43.0, comfy/ldm/triposplat/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/triposplat/model.py)
- [ComfyUI v0.43.0, comfy/ldm/triposplat/vae.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/triposplat/vae.py)
- [ComfyUI v0.43.0, comfy_extras/mesh3d/postprocess/remesh.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/mesh3d/postprocess/remesh.py)
- [ComfyUI v0.43.0, comfy_extras/mesh3d/postprocess/qem_decimate.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/mesh3d/postprocess/qem_decimate.py)

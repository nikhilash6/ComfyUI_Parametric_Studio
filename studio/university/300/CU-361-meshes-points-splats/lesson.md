# CU-361 - Meshes, points and Gaussian splats

**Objective.** Say what a mesh, a point cloud and a Gaussian splat each store, what each is good at, and what core's `SplatToMesh` does to convert one. Taught by Professor Latent.

## The idea

All three describe the same object, and what they keep is very different.

- A **mesh** has vertices and triangles. It has a real surface, and it knows inside from outside when it's closed. Games, printers and physics want this.
- A **point cloud** has positions, perhaps with colour. It has no size and no surface. Between two points, there's nothing.
- A **Gaussian splat** is a cloud of soft, coloured, stretched blobs. It looks real from many angles, it's quick to draw, and it has no surface at all.

## What ComfyUI stores

The types are small classes in `comfy_api/latest/_util/geometry_types.py`:

```
MESH   vertices (B, N, 3), faces (B, M, 3), then optional uvs, vertex_colors, texture...
SPLAT  positions (B, N, 3), scales (B, N, 3), rotations (B, N, 4)
       opacities (B, N, 1), sh (B, N, K, 3), K = (sh_degree + 1) squared
VOXEL  data, optional voxel_colors and resolution
```

Each splat's rotation and three scales make it a flat disc, a needle or a ball. `sh` is colour that can change with the viewing angle. At degree 0, it's one colour from every side.

Core has no plain "points" wire type in common use. A comment in `_io.py` says the `POINT` type has no references in core code. Depth nodes hold point data in their own types and turn it directly into a mesh: `MoGePointMapToMesh`, `DA3GeometryToMesh`.

## Drawing a splat

Project each blob to the screen, and blend from front to back. `_render_gaussian` sorts into depth slabs and composites them, with no network involved. Try the idea here:

{{play:splat}}

A soft thing can look solid when many blobs overlap. Orbit it. The picture stays convincing, but the blobs give you nothing to attach a surface to.

## From splat to mesh

`SplatToMesh`, shown as "Extract Mesh from Splat", has to invent a surface. Here's what `_gaussian_to_mesh` does:

1. Drops blobs fainter than `min_opacity`.
2. Paints each blob into a density grid, out to 3 sigma, capped at `kernel` voxels, with a matching colour grid. `resolution` sets the grid along the longest side.
3. Picks a density level to call the surface, using Otsu's method, which splits the values into two groups. `level` scales that choice, so 1.0 means automatic. The default is 0.4, making the surface fatter.
4. Runs Surface Nets on the grid.
5. Removes small pieces under `min_component`, including the inner wall of a double shell.
6. Smooths with Taubin smoothing if `smooth` is above 0.
7. Reads colours from the colour grid. `color_sharpen` above 1 favours the strongest blob.

The output is marked `unlit`, so it's saved to show flat colours and not get lit twice.

Mesh going the other way isn't in that node. Rendered views, or a model, are how splats get made.

Compare with a mesh made directly:

{{graph:hunyuan3d_mesh}}

## Which to use

- Need a printable or game-ready object: a mesh.
- Need something to look real on a turntable, fast: splats.
- Need depth for a picture: a point map, and often a mesh made from it.

We're describing what the data structures can do. We haven't compared results on the same object.

## What goes wrong

- **Holes in a splat-to-mesh result.** Sparse blobs don't reach each other. Raise `kernel`, or lower `level`. The lab's first row shows this.
- **A thick, puffy mesh.** `level` is low, or blobs are large. Raise `level`.
- **Lumps floating near the object.** Raise `min_component` or `min_opacity`.
- **The colours look washed out or muddy.** Raise `color_sharpen`, which affects colour only. Check that the lighting isn't being applied on top of baked colour.
- **Out of memory on `SplatToMesh`.** The tooltip says cost grows with `resolution` cubed, and the node's comments put Surface Nets at about 3 to 3.5 times the grid. Lower `resolution` from 384.
- **A file is huge.** 1,000,000 Gaussians at degree 3 is 236.5 MiB as `.ply`. Core also writes `ksplat` and `spz`, through `SplatToFile3D`.
- **Expecting a splat to work in a game engine as a mesh.** It has no triangles. Convert it, and accept the loss.

## Lab

What each element costs:

```text
per element, in 32-bit floats:
  point with colour: 6
  Gaussian, SH degree 0: 14 (centre 3, scale 3, rotation 4, opacity 1, colour 3)
  Gaussian, SH degree 1: 23 (centre 3, scale 3, rotation 4, opacity 1, colour 12)
  Gaussian, SH degree 3: 59 (centre 3, scale 3, rotation 4, opacity 1, colour 48)
  mesh vertex with colour: 6, plus 3 integers per triangle, about 2 triangles per vertex on a closed mesh
  100,000 Gaussians, degree 0, in a .ply: 6.5 MiB
1,000,000 Gaussians, degree 3, in a .ply: 236.5 MiB
```

Now points on a sphere, painted into a density grid as blobs of three sizes, with an Otsu level like the node's. A line test fires 200 rays through the shell, counting those that find nothing:

```text
blob size   occupied voxels   Otsu level   surface voxels   holes on a line test (rays that miss the surface, of 200)
0.01        6,113             0.335        729              165
0.03        24,816            1.081        5,964            56
0.08        43,724            5.881        14,627           0
small blobs on sparse points leave holes; bigger blobs close them and thicken the wall
```

Small blobs leave most rays passing through, and larger blobs close the holes with a thicker wall. The real node's `kernel` and `level` are about this trade. Then the front-to-back sum, where the first blob takes half and the background keeps what's left:

```text
three blobs on one ray, opacity 0.5 each: weights [0.5, 0.25, 0.125] background gets 0.125
```

And why rotation matters. A flat disc turns to nearly nothing edge-on, which is how splats can represent thin surfaces seen from the right side:

```text
a flat disc tilted  0 degrees: footprint on screen 1.000
a flat disc tilted 45 degrees: footprint on screen 0.708
a flat disc tilted 90 degrees: footprint on screen 0.050
```

## Sources

- [3D Gaussian Splatting for Real-Time Radiance Field Rendering](https://arxiv.org/abs/2308.04079)
- [ComfyUI v0.43.0, comfy_api/latest/_util/geometry_types.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api/latest/_util/geometry_types.py)
- [ComfyUI v0.43.0, comfy_api/latest/_io.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api/latest/_io.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_gaussian_splat.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_gaussian_splat.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_triposplat.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_triposplat.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_moge.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_moge.py)

# CU-362 - Mesh tools in core: decimate, remesh, unwrap

**Objective.** Say what remesh, decimate and unwrap each do, run them in the right order, and choose the settings that matter. Taught by Professor Latent.

## The idea

A generated mesh comes out far too dense, with uneven triangles and sometimes inner walls. It has no UV map, so it can't hold a texture. Three core nodes deal with this, in `3d/mesh` and `3d/texturing`:

1. **`RemeshMesh`** builds a new, even surface around the old one.
2. **`DecimateMesh`** removes triangles to hit a budget.
3. **`UnwrapMesh`** flattens the surface into a UV atlas.

The order matters, and the source says so. Remesh's description says to run it before decimating to hit an exact face count. Unwrap's says to run it after remesh and decimate, and before baking. Remesh or decimate after unwrapping, and your UVs are gone or wrong.

{{graph:e_mesh_cleanup}}

## Remesh

`remesh_narrow_band_dc` ignores the old triangles' layout. It measures distance to the old surface, but only in a thin band of voxels near it, then extracts a new surface with Dual Contouring. So bad topology, self-intersections and stray triangles don't carry through. The new mesh is even, because the grid is.

The settings to know:

- `resolution` sets density. The node's tooltip says 256 gives about 100k faces and 512 about 1M.
- `sign_mode`: `udf` copes with messy input. `sdf` gives clean, sharper results but needs consistent winding. `solid` uses a graph cut to get one watertight solid from messy input, and it's slower.
- `smooth_iters` 2 or 3 cleans stair-like artefacts, according to its tooltip.
- `drop_small_components` removes specks.

Memory is the catch: the node asks for at least resolution cubed x 64 bytes. At 1024 that's 64 GiB. It's built to run on your GPU, and it'll be much slower elsewhere.

## Decimate

Quadric Error Metrics give each vertex a measure of how far it could move while staying near its original planes. Collapse the edge that costs least, and repeat. `qem_simplify` does this in parallel rounds, with checks against flipped normals and skinny triangles. `placement_mode` chooses where the new vertex goes. `midpoint` is the recommended default and keeps thin features, by the node's description. `qem` computes the best position.

Flat areas lose triangles first, which is the point. A 2D version:

{{play:decimate}}

## Unwrap

A UV map says which texel each triangle uses. You can't flatten a curved surface without cutting it, so `UnwrapMesh` splits it into charts, flattens each one, and packs them into a square. Vertices on a cut become two vertices: same place, different UV. So the vertex count goes up. Our sphere went from 2562 to 2960.

Parameterization is an orthographic PCA projection, falling back to ABF or LSCM. `segmenter` chooses `pec`, fast on a GPU, or `adaptive`, on a CPU. `padding` leaves a gap so colours don't bleed across charts when the map is filtered.

## What goes wrong

- **Thousands of tiny charts, one per triangle.** The input isn't welded. The tooltip says to raise `weld_distance` to about 0.001. `VoxelToMesh` in `basic` mode gives unwelded output like this.
- **Decimate does nothing.** It's already under `target_face_count`. Or the target is 0, which disables it.
- **The texture is scrambled after a cleanup.** You remeshed or decimated after unwrapping. Unwrap last, then bake.
- **Remesh gives a double shell.** `udf` on a closed input also gives an inner shell, by the docstring. Use the options to drop enclosed components, or use `sdf` or `solid`.
- **Sharp edges go soft.** Remesh rebuilt them at the grid's resolution. Raise `resolution`, or try `sdf`, which turns on sharp-feature recovery.
- **Out of memory on remesh.** Lower `resolution`. Doubling it costs eight times the memory floor.
- **Thin hair or fins vanish on decimate.** Stay with `midpoint`, or raise the target. Check the worst case and not only the mean.
- **The graph fails validation on `sign_mode`.** Its sub-options count as required inputs. Our file gives them as `sign_mode.qef` and so on.

## Lab

A small QEM written from scratch, collapsing to midpoints on an icosphere. It's the idea, without the real node's parallel rounds or checks. We ran the real `qem_simplify` too: its numbers are in the list of checks on this page, and they're the same size.

```text
icosphere: 642 vertices, 1280 faces. True sphere radius 1.
target faces   faces left   vertices   mean distance from the sphere   worst
640            640          322        0.00245                         0.00500
320            320          162        0.00599                         0.00926
160            160          82         0.01307                         0.02047
80             80           42         0.02604                         0.04135
```

Memory floor for remesh:

```text
RemeshMesh memory_required floor
resolution  128:   0.12 GiB
resolution  256:   1.00 GiB
resolution  512:   8.00 GiB
resolution 1024:  64.00 GiB
```

What cuts cost. The vertex list grows, and the same geometry stays:

```text
A cube has 8 corners. Cut into 6 separate squares its vertex list becomes 24 ; laid out as one cross, 14 ; the geometry is the same
```

And padding. More small charts waste more of your texture:

```text
    6 charts in a 1024 atlas with padding 1: at most 99.0% of the texels hold colour
   96 charts in a 1024 atlas with padding 1: at most 95.3% of the texels hold colour
 1536 charts in a 1024 atlas with padding 1: at most 84.4% of the texels hold colour
```

## Sources

- [ComfyUI v0.43.0, comfy_extras/nodes_mesh_postprocess.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_mesh_postprocess.py)
- [ComfyUI v0.43.0, comfy_extras/mesh3d/postprocess/qem_decimate.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/mesh3d/postprocess/qem_decimate.py)
- [ComfyUI v0.43.0, comfy_extras/mesh3d/postprocess/remesh.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/mesh3d/postprocess/remesh.py)
- [ComfyUI v0.43.0, comfy_extras/mesh3d/uv_unwrap/segment.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/mesh3d/uv_unwrap/segment.py)
- [ComfyUI v0.43.0, comfy_extras/mesh3d/uv_unwrap/parameterize.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/mesh3d/uv_unwrap/parameterize.py)
- [ComfyUI v0.43.0, comfy_extras/mesh3d/uv_unwrap/pack.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/mesh3d/uv_unwrap/pack.py)

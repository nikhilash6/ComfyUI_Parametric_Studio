"""blender -b --factory-startup --python wk_place.py -- PAYLOAD.json
payload {"recipe": makers/place.py plan(), "textures": {material: png}, "look": looks.resolve(), "out": glb,
         "views": dir, "size": px, "samples": int, "engine": "eevee"|"cycles", "detail_textures": {material: png} (optional, built in, never from a model)}
A place from its kit (street / interior / beach), seeded (the same recipe builds the same place). Every solid gets a
"<name>-colonly" box collider (Godot's import convention), hidden from renders. Small parts (window frames, sills, planks, furniture detail) are merged per material into one mesh with no collider. Materials use the
tileable textures when given, flat colours otherwise; a wet look lowers ground roughness; a night look lights windows and lamps. Scenery whose name starts backdrop or sea runs out past the horizon and is not the asset's size. Exports
the glb, renders four overview stills (view_0..3.png; inside a room, from its corners), reports inspect facts."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import _wk  # noqa: E402

FLAT = {"ground": (0.16, 0.16, 0.17), "sidewalk": (0.55, 0.55, 0.53), "wall": (0.50, 0.27, 0.20),
        "wall2": (0.80, 0.76, 0.68), "floor": (0.45, 0.30, 0.18), "counter": (0.22, 0.14, 0.09),
        "deck": (0.50, 0.40, 0.30), "sea": (0.03, 0.20, 0.28), "glass": (0.05, 0.07, 0.09),
        "metal": (0.30, 0.30, 0.32), "fabric": (0.75, 0.25, 0.20), "trim": (0.72, 0.70, 0.64), "roof": (0.13, 0.13, 0.14),
        "tile": (0.34, 0.15, 0.10), "dark": (0.05, 0.05, 0.06), "paint": (0.85, 0.85, 0.82), "curb": (0.42, 0.42, 0.41),
        "leaf": (0.09, 0.22, 0.06), "palm": (0.13, 0.27, 0.07), "bark": (0.20, 0.13, 0.08), "foam": (0.86, 0.90, 0.90),
        "white": (0.82, 0.82, 0.78), "blue": (0.10, 0.28, 0.48), "green": (0.10, 0.32, 0.20), "yellow": (0.80, 0.58, 0.14),
        "red": (0.60, 0.12, 0.09), "far": (0.42, 0.44, 0.47), "hill": (0.26, 0.31, 0.27), "rug": (0.35, 0.10, 0.09),
        "rock": (0.30, 0.28, 0.25), "bottle": (0.10, 0.25, 0.14), "shade": (0.85, 0.72, 0.50)}
TILE_M = 2.0
WET = ("ground", "sidewalk", "deck")
BIG = 3000.0                                       # scenery runs out to here: no edge of it shows on the horizon


def box_v(size, loc, yaw=0.0):
    """The eight corners and six faces of a box, turned about its own centre."""
    sx, sy, sz = (v / 2 for v in size)
    c, s = math.cos(yaw), math.sin(yaw)
    vs = [(loc[0] + x * c - y * s, loc[1] + x * s + y * c, loc[2] + z) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
    return vs, [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]


def ring_v(r1, r2, h, loc, n=10, lean=(0.0, 0.0), squash=1.0):
    """A cylinder or cone standing on loc; lean moves its top."""
    vs = [(loc[0] + r * math.cos(2 * math.pi * i / n) * squash + dx, loc[1] + r * math.sin(2 * math.pi * i / n), loc[2] + z)
          for r, z, dx, dy in ((r1, 0.0, 0.0, 0.0), (r2, h, lean[0], lean[1])) for i in range(n)]
    vs = [(v[0], v[1] + (lean[1] if j >= n else 0.0), v[2]) for j, v in enumerate(vs)]
    fs = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)] + [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    return vs, fs


def blob_v(radius, loc, rnd, squash=0.85):
    """A lumpy ball, for a tree's crown or a rock."""
    bands, n, vs, fs = 5, 9, [], []
    for b in range(bands + 1):
        t = math.pi * b / bands
        for i in range(n):
            a = 2 * math.pi * i / n
            r = radius * rnd.uniform(0.86, 1.14)
            vs.append((loc[0] + r * math.sin(t) * math.cos(a), loc[1] + r * math.sin(t) * math.sin(a), loc[2] + r * squash * math.cos(t)))
    for b in range(bands):
        for i in range(n):
            j = (i + 1) % n
            fs.append((b * n + i, (b + 1) * n + i, (b + 1) * n + j, b * n + j))
    return vs, fs


class Kit:
    def __init__(self, p):
        self.p, self.r = p, p["recipe"]
        self.rnd = random.Random(int(self.r.get("seed", 0)))
        self.wet = float(p["look"].get("wet", 0.0))
        self.night = bool(p["look"].get("night"))
        self.mats, self.names = {}, {}
        self.lumps = {}                            # detail merged by material: thousands of small parts stay one fast mesh each
        self.tex = {**p.get("detail_textures", {}), **p["textures"]}

    def uname(self, base):
        self.names[base] = self.names.get(base, 0) + 1
        return base if self.names[base] == 1 else f"{base}_{self.names[base]}"

    def mat(self, name, rough=0.8, emit=None):
        key = (name, emit)
        if key in self.mats:
            return self.mats[key]
        m = bpy.data.materials.new(name if emit is None else f"{name}_lit")
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Roughness"].default_value = rough * (1.0 - 0.8 * self.wet) if name in WET else rough
        tex = self.tex.get(name)
        if tex:
            node = m.node_tree.nodes.new("ShaderNodeTexImage")
            node.image = bpy.data.images.load(tex)
            m.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
        else:
            bsdf.inputs["Base Color"].default_value = (*FLAT.get(name, (0.5, 0.5, 0.5)), 1.0)
        if emit is not None:
            bsdf.inputs["Emission Color"].default_value = (*emit, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 3.0
        self.mats[key] = m
        return m

    def finish(self, o, name, mat, collider):
        o.name = self.uname(name)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        o.data.materials.append(mat)
        self.box_uv(o)
        if collider:
            c = o.copy()
            c.data = o.data.copy()
            c.data.materials.clear()
            c.name = f"{o.name}-colonly"
            c.hide_render = True
            bpy.context.scene.collection.objects.link(c)
        return o

    def box_uv(self, o):
        """UVs in metres, projected along each face's main axis: a brick is the same size on a tall wall and a short one."""
        uv = o.data.uv_layers.active
        if uv is None:
            return
        verts, loops = o.data.vertices, o.data.loops
        for poly in o.data.polygons:
            n = poly.normal
            axis = max(range(3), key=lambda i: abs(n[i]))
            a, b = {0: (1, 2), 1: (0, 2), 2: (0, 1)}[axis]
            for li in poly.loop_indices:
                co = verts[loops[li].vertex_index].co
                uv.data[li].uv = ((co[a] + o.location[a]) / TILE_M, (co[b] + o.location[b]) / TILE_M)

    def box(self, name, size, loc, mat, collider=True):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
        o = bpy.context.active_object
        o.scale = size
        return self.finish(o, name, mat, collider)

    def collider(self, name, size, loc):
        """A collider with no solid of its own, for a thing made of merged small parts."""
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
        o = bpy.context.active_object
        o.scale = size
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        o.name, o.hide_render = f"{self.uname(name)}-colonly", True
        return o

    def cyl(self, name, radius, depth, loc, mat, collider=True):
        bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc, vertices=16)
        return self.finish(bpy.context.active_object, name, mat, collider)

    def light(self, loc, energy, colour=(1.0, 0.8, 0.55), kind="POINT"):
        name = self.uname("lamp")
        lamp = bpy.data.objects.new(name, bpy.data.lights.new(name, kind))
        bpy.context.scene.collection.objects.link(lamp)
        lamp.location, lamp.data.energy, lamp.data.color = loc, energy, colour

    # small parts, merged per material when the kit is done
    def add(self, mat, part, group="detail"):
        vs, fs = part
        lump = self.lumps.setdefault((group, mat.name), ([], [], mat))
        base = len(lump[0])
        lump[0].extend(vs)
        lump[1].extend(tuple(i + base for i in f) for f in fs)

    def b(self, mat, size, loc, yaw=0.0, group="detail"):
        self.add(mat, box_v(size, loc, yaw), group)

    def flush(self):
        for (group, name), (vs, fs, mat) in self.lumps.items():
            me = bpy.data.meshes.new(f"{group}_{name}")
            me.from_pydata(vs, [], fs)
            me.update()
            me.uv_layers.new(name="UVMap")
            o = bpy.data.objects.new(self.uname(f"{group}_{name}"), me)
            bpy.context.scene.collection.objects.link(o)
            me.materials.append(mat)
            self.box_uv(o)
        self.lumps = {}

    def grid(self, name, xs, ys, height, mat):
        """A ground mesh on the given lines, z = height(x, y)."""
        vs = [(x, y, height(x, y)) for y in ys for x in xs]
        n = len(xs)
        fs = [(j * n + i, j * n + i + 1, (j + 1) * n + i + 1, (j + 1) * n + i) for j in range(len(ys) - 1) for i in range(n - 1)]
        me = bpy.data.meshes.new(name)
        me.from_pydata(vs, [], fs)
        me.update()
        me.uv_layers.new(name="UVMap")
        o = bpy.data.objects.new(self.uname(name), me)
        bpy.context.scene.collection.objects.link(o)
        me.materials.append(mat)
        self.box_uv(o)
        return o

    def backdrop(self, size, z, mat):
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, z))
        o = bpy.context.active_object
        o.scale = (size, size, 1)
        self.finish(o, "backdrop", mat, False)

    # street furniture
    def lamp_post(self, x, y, side):
        metal = self.mat("metal", 0.4)
        self.cyl("lamp_post", 0.08, 4.8, (x, y, 2.4), metal)
        self.b(metal, (0.07, 1.2, 0.07), (x, y - side * 0.55, 4.78))
        head = self.mat("glass", 0.2, emit=(1.0, 0.82, 0.55)) if self.night else self.mat("white", 0.3)
        self.b(head, (0.22, 0.5, 0.08), (x, y - side * 1.05, 4.72))
        if self.night:
            self.light((x, y - side * 1.05, 4.5), 400.0)

    def bench(self, x, y, yaw=0.0):
        wood, metal = self.mat("deck", 0.7), self.mat("metal", 0.4)
        c, s = math.cos(yaw), math.sin(yaw)
        for i in range(3):
            self.b(wood, (1.7, 0.1, 0.04), (x - s * (i - 1) * -0.14, y + c * (i - 1) * 0.14, 0.45), yaw)
        for off in (-0.7, 0.7):
            self.b(metal, (0.06, 0.45, 0.43), (x + c * off, y + s * off, 0.22), yaw)
            self.b(metal, (0.05, 0.05, 0.45), (x + c * off - s * -0.22, y + s * off + c * 0.22, 0.65), yaw)
        self.b(wood, (1.7, 0.04, 0.12), (x - s * -0.22, y + c * 0.22, 0.72), yaw)
        self.collider("bench", (1.8, 0.5, 0.5), (x, y, 0.25))

    def tree(self, x, y, h=None, base=0.15):
        h = h or self.rnd.uniform(4.5, 6.5)
        self.cyl("tree_trunk", 0.13, h * 0.6, (x, y, base + h * 0.3), self.mat("bark", 0.9))
        leaf = self.mat("leaf", 0.9)
        for _ in range(4):
            self.add(leaf, blob_v(self.rnd.uniform(0.9, 1.5), (x + self.rnd.uniform(-0.7, 0.7), y + self.rnd.uniform(-0.7, 0.7), base + h * self.rnd.uniform(0.68, 0.92)), self.rnd))

    def car(self, x, y, yaw_x=True):
        body = self.mat(self.rnd.choice(["red", "blue", "white", "dark", "green", "yellow"]), 0.25)
        glass, tyre = self.mat("glass", 0.1), self.mat("dark", 0.9)
        L_, W = 4.3, 1.8
        size = (L_, W, 0.65) if yaw_x else (W, L_, 0.65)
        self.box("car", size, (x, y, 0.62), body)
        top = (2.2, W - 0.16, 0.5) if yaw_x else (W - 0.16, 2.2, 0.5)
        self.b(glass, top, (x, y, 1.18), group="car")
        roof = (2.0, W - 0.3, 0.05) if yaw_x else (W - 0.3, 2.0, 0.05)
        self.b(body, roof, (x, y, 1.45), group="car")
        for a in (-1.3, 1.3):
            for b in (-0.8, 0.8):
                px, py = (x + a, y + b) if yaw_x else (x + b, y + a)
                self.add(tyre, ring_v(0.32, 0.32, 0.22, (px, py, 0.0), 10), "car")

    def facade(self, cx, y, out, bw, bh, style, shop):
        """Everything stuck on one street wall. y is the wall's plane, out (+1/-1) the way it faces."""
        trim, glass = self.mat(style["trim"], 0.6), self.mat("glass", 0.08)
        lit = self.mat("glass", 0.1, emit=(1.0, 0.78, 0.5)) if self.night else None
        lo = 4.2 if shop else 1.0
        cols = max(1, int(bw // style["spacing"]))
        rows = max(1, int((bh - lo - 0.6) // style["floor"]))
        win_w, win_h = style["win_w"], style["win_h"]
        for j in range(rows):
            z = lo + (j + 0.5) * style["floor"]
            for i in range(cols):
                x = cx - bw / 2 + (i + 0.5) * bw / cols
                pane = lit if (lit is not None and self.rnd.random() < 0.55) else glass
                self.b(trim, (win_w + 0.18, 0.08, win_h + 0.18), (x, y + out * 0.03, z))
                self.b(pane, (win_w, 0.08, win_h), (x, y + out * 0.06, z))
                self.b(trim, (0.05, 0.1, win_h), (x, y + out * 0.08, z))
                self.b(trim, (win_w + 0.35, 0.2, 0.09), (x, y + out * 0.1, z - win_h / 2 - 0.1))
                if style["lintel"]:
                    self.b(trim, (win_w + 0.3, 0.14, 0.14), (x, y + out * 0.07, z + win_h / 2 + 0.14))
                if style["shutters"]:
                    colour = self.mat(style["accent"], 0.7)
                    for side in (-1, 1):
                        self.b(colour, (0.42, 0.05, win_h), (x + side * (win_w / 2 + 0.28), y + out * 0.05, z))
                if style["balconies"] and j % 2 == 0 and i % 2 == 0:
                    metal = self.mat("dark", 0.5)
                    self.b(trim, (win_w + 0.7, 0.8, 0.1), (x, y + out * 0.42, z - win_h / 2 - 0.2))
                    self.b(metal, (win_w + 0.7, 0.03, 0.75), (x, y + out * 0.8, z - win_h / 2 + 0.2))
                    for sx in (-1, 1):
                        self.b(metal, (0.03, 0.8, 0.75), (x + sx * (win_w / 2 + 0.35), y + out * 0.42, z - win_h / 2 + 0.2))
            if style["bands"] and j:
                self.b(trim, (bw, 0.1, 0.1), (cx, y + out * 0.05, lo + j * style["floor"]))
        self.b(trim, (bw + 0.1, 0.4, 0.4), (cx, y + out * 0.18, bh - 0.2))    # cornice
        if not shop:
            self.b(self.mat("curb"), (bw, 0.06, 0.8), (cx, y + out * 0.03, 0.4))
            return
        accent = self.mat(style["accent"], 0.6)
        self.b(trim, (bw, 0.2, 0.5), (cx, y + out * 0.08, 3.9))                # the fascia the shop's name goes on
        self.b(accent, (bw * 0.7, 0.06, 0.32), (cx, y + out * 0.2, 3.9))
        self.b(self.mat("dark", 0.5), (bw, 0.1, 0.5), (cx, y + out * 0.05, 0.25))
        door = cx + self.rnd.uniform(-0.25, 0.25) * bw
        for x0, x1 in ((cx - bw / 2 + 0.3, door - 0.7), (door + 0.7, cx + bw / 2 - 0.3)):
            if x1 - x0 > 0.5:
                pane = lit if lit is not None else glass
                self.b(pane, (x1 - x0, 0.08, 2.8), ((x0 + x1) / 2, y + out * 0.05, 1.95))
                self.b(trim, (x1 - x0 + 0.1, 0.1, 0.08), ((x0 + x1) / 2, y + out * 0.07, 3.38))
        self.b(self.mat("dark", 0.5), (1.1, 0.08, 2.5), (door, y + out * 0.04, 1.25))
        self.b(glass, (0.8, 0.09, 1.5), (door, y + out * 0.06, 1.55))
        if style["awning"]:
            n = max(2, int(bw // 0.9))
            for i in range(n):
                colour = accent if i % 2 == 0 else self.mat("white", 0.7)
                x = cx - bw / 2 + (i + 0.5) * bw / n
                x0, x1 = x - bw / n / 2, x + bw / n / 2
                y0, y1 = y + out * 0.05, y + out * 1.3
                self.add(colour, ([(x0, y0, 3.55), (x1, y0, 3.55), (x1, y1, 3.0), (x0, y1, 3.0), (x0, y1, 2.85), (x1, y1, 2.85)], [(0, 1, 2, 3), (3, 2, 5, 4)]))

    def roof(self, cx, cy, bw, bd, bh, kind):
        """On top of a building: a pitched roof, or a flat one with a parapet and its plant."""
        if kind == "pitched":
            tile = self.mat("tile", 0.8)
            hw, hd, rise = bw / 2 + 0.25, bd / 2 + 0.25, min(bd * 0.32, 2.4)
            v = [(cx - hw, cy - hd, bh), (cx + hw, cy - hd, bh), (cx + hw, cy + hd, bh), (cx - hw, cy + hd, bh), (cx - hw, cy, bh + rise), (cx + hw, cy, bh + rise)]
            self.add(tile, (v, [(0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5)]))
            return
        slab, wall = self.mat("roof", 0.9), self.mat("trim", 0.7)
        self.b(slab, (bw, bd, 0.08), (cx, cy, bh + 0.02))
        for sx, sy, w, d in ((0, -1, bw, 0.2), (0, 1, bw, 0.2), (-1, 0, 0.2, bd - 0.4), (1, 0, 0.2, bd - 0.4)):       # parts must not overlap face to face: Cycles renders that black
            self.b(wall, (w, d, 0.55), (cx + sx * (bw / 2 - 0.1), cy + sy * (bd / 2 - 0.1), bh + 0.28))
        metal = self.mat("metal", 0.5)
        if kind == "plant":
            for _ in range(self.rnd.randint(2, 4)):
                self.b(metal, (self.rnd.uniform(0.8, 1.4), self.rnd.uniform(0.8, 1.2), 0.8), (cx + self.rnd.uniform(-0.3, 0.3) * bw, cy + self.rnd.uniform(-0.25, 0.25) * bd, bh + 0.45))
        elif kind == "tank":
            x, y = cx + self.rnd.uniform(-0.2, 0.2) * bw, cy + self.rnd.uniform(-0.15, 0.15) * bd
            for ox, oy in ((-0.6, -0.6), (0.6, -0.6), (0.6, 0.6), (-0.6, 0.6)):
                self.b(self.mat("dark", 0.5), (0.1, 0.1, 1.4), (x + ox, y + oy, bh + 0.7))
            self.add(self.mat("bark", 0.8), ring_v(0.95, 0.95, 1.6, (x, y, bh + 1.4), 12))
            self.add(self.mat("dark", 0.8), ring_v(1.0, 0.1, 0.5, (x, y, bh + 3.0), 12))
        elif kind == "hut":
            self.b(wall, (2.6, 2.2, 2.3), (cx - bw * 0.2, cy, bh + 1.15))
            self.b(slab, (2.8, 2.4, 0.1), (cx - bw * 0.2, cy, bh + 2.35))
            self.b(metal, (0.12, 0.12, 1.1), (cx + bw * 0.25, cy + 0.3, bh + 0.55))

    def street(self):
        w, d = self.r["size_m"]
        self.backdrop(BIG, -0.2, self.mat("sidewalk"))
        asphalt, kerb, paint = self.mat("ground"), self.mat("curb", 0.8), self.mat("paint", 0.6)
        self.box("road", (w, 8.0, 0.1), (0, 0, -0.05), asphalt)
        self.b(asphalt, (BIG, 8.0, 0.1), (0, 0, -0.07), group="backdrop_road")           # the road carries on past both ends
        for x in range(int(-w / 2) + 1, int(w / 2) - 1, 5):
            self.b(paint, (2.5, 0.14, 0.012), (x + 1.25, 0, 0.004))
        for side in (-1, 1):
            self.b(paint, (w, 0.12, 0.012), (0, side * 3.65, 0.004))
            self.b(kerb, (w, 0.2, 0.28), (0, side * 4.05, 0.05))
        for i in range(8):
            self.b(paint, (3.0, 0.45, 0.012), (w * 0.34, -3.15 + i * 0.9, 0.004))          # a zebra crossing
        for x in (-w * 0.2, w * 0.1):
            self.add(self.mat("dark", 0.7), ring_v(0.35, 0.35, 0.015, (x, 1.5, 0.0), 12))
        for side in (-1, 1):
            self.box("sidewalk", (w, 3.0, 0.25), (0, side * 5.5, 0.075), self.mat("sidewalk"))
            x = -w / 2
            while x < w / 2 - 3.0:
                bw = min(self.rnd.uniform(6.0, 10.0), w / 2 - x)
                bh, bd = self.rnd.uniform(7.0, 20.0), max(4.0, d / 2 - 7.0)
                cx, cy = x + bw / 2, side * (7.0 + bd / 2)
                self.box("building", (bw - 0.3, bd, bh), (cx, cy, bh / 2), self.mat(self.rnd.choice(["wall", "wall2"])))
                style = {"spacing": self.rnd.uniform(2.1, 3.1), "floor": self.rnd.uniform(3.0, 3.4), "win_w": self.rnd.uniform(1.0, 1.5), "win_h": self.rnd.uniform(1.4, 2.0),
                         "trim": self.rnd.choice(["trim", "trim", "white", "curb"]), "accent": self.rnd.choice(["blue", "green", "red", "yellow"]),
                         "lintel": self.rnd.random() < 0.6, "shutters": self.rnd.random() < 0.25, "balconies": self.rnd.random() < 0.3, "bands": self.rnd.random() < 0.5,
                         "awning": self.rnd.random() < 0.65}
                self.facade(cx, side * 7.0, -side, bw - 0.3, bh, style, shop=self.rnd.random() < 0.75)
                self.facade(cx, side * (7.0 + bd), side, bw - 0.3, bh, {**style, "balconies": False, "shutters": False}, shop=False)
                self.roof(cx, cy, bw - 0.3, bd, bh, self.rnd.choice(["pitched", "plant", "plant", "tank", "hut"]))
                x += bw
            for lx in range(int(-w / 2) + 6, int(w / 2), 12):
                self.lamp_post(lx, side * 4.5, side)
            for tx in range(int(-w / 2) + 12, int(w / 2) - 2, 12):
                self.tree(tx, side * 5.2, base=0.2)
                self.add(self.mat("dark", 0.8), ring_v(0.7, 0.7, 0.05, (tx, side * 5.2, 0.2), 12))
            self.bench(-w / 2 + 9.0 + (side + 1) * 3.0, side * 6.3, 0.0 if side < 0 else math.pi)
            for bx in (-w * 0.3 * side, w * 0.15 * side):
                self.cyl("bin", 0.27, 0.9, (bx, side * 4.7, 0.65), self.mat("green", 0.5))
            self.b(self.mat("metal", 0.4), (0.06, 0.06, 2.6), (w * 0.28 * side, side * 4.4, 1.5))   # a street sign
            self.b(self.mat("blue", 0.3), (0.7, 0.04, 0.7), (w * 0.28 * side, side * 4.4, 2.6))
            for cx in [x for x in (-w * 0.3, -w * 0.05, w * 0.2) if self.rnd.random() < 0.8]:
                self.car(cx + self.rnd.uniform(-1, 1), side * 2.8)
        # the rest of town, low and in the haze: it fills the horizon where there was an empty plane
        far = self.mat("far", 0.9)
        for _ in range(140):
            a, dist = self.rnd.uniform(0, 2 * math.pi), self.rnd.uniform(max(w, d) * 1.35, max(w, d) * 7)
            x, y = math.cos(a) * dist, math.sin(a) * dist
            if abs(y) < 8.0:
                continue
            h = self.rnd.uniform(6, 16 + dist * 0.05)
            self.b(far, (self.rnd.uniform(8, 20), self.rnd.uniform(8, 20), h), (x, y, h / 2 - 0.2), group="backdrop_town")

    def interior(self):
        w, d = self.r["size_m"]
        h, t, gap, door = 3.2, 0.15, min(3.0, w / 3), 1.0
        self.box("floor", (w, d, 0.1), (0, 0, -0.05), self.mat("floor", 0.6))
        self.box("ceiling", (w, d, 0.1), (0, 0, h + 0.05), self.mat("wall2"))
        self.box("wall_left", (t, d, h), (-w / 2, 0, h / 2), self.mat("wall"))
        self.box("wall_right", (t, d, h), (w / 2, 0, h / 2), self.mat("wall"))
        for sx in (-(w + gap) / 4, (w + gap) / 4):
            self.box("wall_back", ((w - gap) / 2, t, h), (sx, d / 2, h / 2), self.mat("wall"))
        self.box("wall_back_low", (gap, t, 0.9), (0, d / 2, 0.45), self.mat("wall"))
        self.box("wall_back_high", (gap, t, 0.6), (0, d / 2, h - 0.3), self.mat("wall"))
        self.box("window", (gap, 0.04, h - 1.5), (0, d / 2, 0.9 + (h - 1.5) / 2), self.mat("glass", 0.05),
                 collider=False)
        self.box("wall_front", (w - door - 0.5, t, h), ((door + 0.5) / 2, -d / 2, h / 2), self.mat("wall"))
        self.box("wall_front_end", (0.5, t, h), (-w / 2 + 0.25, -d / 2, h / 2), self.mat("wall"))
        trim, wood, metal = self.mat("trim", 0.5), self.mat("counter", 0.45), self.mat("metal", 0.4)
        # skirting, dado rail and wall panels; window bars; door frame
        for x, y, sx, sy in ((-w / 2 + t, 0, 0.04, d), (w / 2 - t, 0, 0.04, d), (0, d / 2 - t, w, 0.04), (0, -d / 2 + t, w, 0.04)):
            self.b(trim, (sx, sy, 0.14), (x, y, 0.07))
            self.b(trim, (sx, sy, 0.06), (x, y, 1.0))
            self.b(trim, (sx, sy, 0.08), (x, y, h - 0.04))
        for i in range(1, 3):
            self.b(self.mat("dark", 0.5), (0.05, 0.08, h - 1.5), (-gap / 2 + i * gap / 3, d / 2, 0.9 + (h - 1.5) / 2))
        self.b(self.mat("dark", 0.5), (gap, 0.08, 0.05), (0, d / 2, 2.0))
        self.b(trim, (gap + 0.2, 0.25, 0.08), (0, d / 2 - 0.12, 0.94))
        for off in (0.5, 0.5 + door):                                 # the doorway is between the two front walls
            self.b(trim, (0.1, 0.22, 2.2), (-w / 2 + off, -d / 2, 1.1))
        # the counter: top, front panels, stools; behind it shelves of bottles
        cw, cx, cy = min(4.0, w * 0.5), max(0.0, w / 4 - 0.8), d / 2 - 1.2
        self.box("counter", (cw, 0.7, 1.05), (cx, cy, 0.525), self.mat("counter", 0.5))
        self.b(self.mat("trim", 0.3), (cw + 0.15, 0.85, 0.05), (cx, cy, 1.07))
        for i in range(int(cw // 0.7)):
            sx = cx - cw / 2 + 0.35 + i * 0.7
            self.b(wood, (0.5, 0.02, 0.8), (sx, cy - 0.36, 0.5))
            self.add(metal, ring_v(0.03, 0.03, 0.75, (sx, cy - 0.75, 0.0), 8))
            self.add(wood, ring_v(0.18, 0.18, 0.05, (sx, cy - 0.75, 0.75), 12))
        for z in (1.35, 1.8, 2.25):
            self.b(wood, (cw, 0.25, 0.04), (cx, d / 2 - 0.22, z))
            for i in range(int(cw // 0.22)):
                if self.rnd.random() < 0.75:
                    bh = self.rnd.uniform(0.22, 0.32)
                    self.add(self.mat(self.rnd.choice(["bottle", "yellow", "glass", "red"]), 0.2), ring_v(0.04, 0.025, bh, (cx - cw / 2 + 0.11 + i * 0.22, d / 2 - 0.22, z + 0.02), 8))
        # tables, chairs, hanging lamps
        for i in range(3):
            tx, ty = -w / 3 + i * (w / 3), -d / 6
            self.box("table_top", (0.8, 0.8, 0.05), (tx, ty, 0.75), self.mat("counter", 0.4))
            self.cyl("table_leg", 0.05, 0.72, (tx, ty, 0.36), self.mat("metal", 0.4))
            self.add(metal, ring_v(0.28, 0.28, 0.02, (tx, ty, 0.0), 12))
            for off in (-0.65, 0.65):
                self.box("chair", (0.42, 0.42, 0.05), (tx + off, ty, 0.46), self.mat("fabric", 0.9))
                self.b(self.mat("fabric", 0.9), (0.04, 0.42, 0.42), (tx + off * 1.32, ty, 0.72))
                for lx in (-0.18, 0.18):
                    for ly in (-0.18, 0.18):
                        self.b(metal, (0.03, 0.03, 0.44), (tx + off + lx, ty + ly, 0.22))
            shade = self.mat("shade", 0.5, emit=(1.0, 0.8, 0.55)) if self.night else self.mat("shade", 0.5)
            self.add(self.mat("dark", 0.5), ring_v(0.012, 0.012, 0.9, (tx, ty, h - 0.9), 6))
            self.add(shade, ring_v(0.26, 0.09, 0.24, (tx, ty, h - 1.1), 14))
            self.light((tx, ty, h - 1.2), 60.0 if self.night else 20.0)
        self.b(self.mat("rug", 0.95), (w * 0.72, d * 0.3, 0.012), (0, -d / 6, 0.006))
        for x, width in ((-w * 0.32, 0.8), (-w * 0.1, 0.6)):                               # pictures on the side wall
            y = x / w * d
            self.b(self.mat("dark", 0.5), (0.03, width + 0.1, 0.6), (-w / 2 + t, y, 1.8))
            self.b(self.mat(self.rnd.choice(["blue", "yellow", "green"]), 0.6), (0.04, width, 0.5), (-w / 2 + t, y, 1.8))
        px, py = -w / 2 + 0.6, d * 0.28                                                   # a plant by the side wall, clear of the corners the views stand in
        self.add(self.mat("bark", 0.8), ring_v(0.22, 0.28, 0.5, (px, py, 0.0), 12))
        for _ in range(4):
            self.add(self.mat("leaf", 0.8), blob_v(self.rnd.uniform(0.25, 0.4), (px + self.rnd.uniform(-0.2, 0.2), py + self.rnd.uniform(-0.2, 0.2), self.rnd.uniform(0.8, 1.4)), self.rnd))
        if not self.night:
            self.light((0, d / 2 - 1.2, 2.2), 150.0, (1.0, 0.97, 0.92))     # a point light: a glb carries no area lights

    def beach(self):
        w, d = self.r["size_m"]
        ph = [self.rnd.uniform(0, 6.28) for _ in range(3)]
        shore_y = d / 2 + 8.0

        def shore(x):
            return shore_y + 3.5 * math.sin(x / 19.0 + ph[0]) + 1.6 * math.sin(x / 7.5 + ph[1]) + 0.5 * math.sin(x / 2.7 + ph[2])

        def bump(x, y):
            return 0.09 * math.sin(x / 4.3 + ph[1]) * math.cos(y / 5.1 + ph[2]) + 0.05 * math.sin(x / 1.7 + y / 2.3 + ph[0])

        def sand(x, y):
            """Dunes on the beach, then a slope running under the water line."""
            fall = max(0.0, y - (d / 2 - 2.0)) * 0.03 + max(0.0, y - shore(x) + 3.0) * 0.05
            return 0.12 + bump(x, y) * min(1.0, max(0.0, (shore(x) - y) / 6.0)) - fall

        def lines(a, b, step):
            return [a + i * step for i in range(int((b - a) / step) + 1)]

        side = max(w, d) * 3
        near_x = lines(-side, side, 1.0)
        xs = [-BIG, -side * 4, *near_x, side * 4, BIG]
        ys = [-BIG, -d * 4, *lines(-d * 2, shore_y + 22.0, 1.0), BIG]
        ground = self.mat("ground", 0.95)
        self.grid("backdrop_beach", xs, ys, lambda x, y: sand(x, y) - 0.015, ground)
        # the part that is the asset: same surface, a touch above the scenery around it, with a collider that walks can use
        sx, sy = lines(-w / 2, w / 2, 1.0), lines(-d / 2, d / 2, 1.0)
        self.grid("sand", sx, sy, sand, ground)
        self.collider("sand", (w, d, 0.2), (0, 0, 0.02))
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, shore_y + BIG / 2 - 6.0, -0.06))
        sea = bpy.context.active_object
        sea.scale = (BIG * 2, BIG + 12.0, 1)
        self.finish(sea, "sea", self.mat("sea", 0.16), False)
        # the edge of the waves, following the shore: a broken band of white on the wet sand
        foam, n = self.mat("foam", 0.5), len(near_x)
        for off, thick in ((-0.4, 0.7), (1.6, 0.25), (4.5, 0.15)):
            lump = []
            for x in near_x:
                wob = 0.6 * math.sin(x / 3.1 + off) + 0.3 * math.sin(x / 1.3 + ph[2])
                y0 = shore(x) + off + wob
                lump.append((x, y0, -0.045))
                lump.append((x, y0 + thick * (0.3 + 0.7 * abs(math.sin(x / (2.0 + off * 0.3)))), -0.045))
            faces = [(2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) for i in range(n - 1)]
            self.add(foam, (lump, faces), "sea_foam")
        hill = self.mat("hill", 0.9)                                                       # a headland past the water, far off
        for i in range(9):
            x = -1500 + i * 150 + self.rnd.uniform(-40, 40)
            self.add(hill, blob_v(self.rnd.uniform(120, 240), (x, 1900, -20.0), self.rnd, squash=0.32), "backdrop_hills")
        far = self.mat("far", 0.9)                                                         # the seaside town behind the boardwalk, and hills behind that
        for _ in range(70):
            x, y = self.rnd.uniform(-side * 2.5, side * 2.5), -self.rnd.uniform(d * 1.6, d * 8)
            h = self.rnd.uniform(5, 18)
            self.b(far, (self.rnd.uniform(7, 16), self.rnd.uniform(7, 14), h), (x, y, h / 2 - 0.2), group="backdrop_town")
        for i in range(12):
            self.add(hill, blob_v(self.rnd.uniform(140, 300), (-1800 + i * 320, -1500 - self.rnd.uniform(0, 300), -20.0), self.rnd, squash=0.30), "backdrop_hills")
        # the boardwalk: planks across it, posts under it, a rail on the land side, benches
        deck_y, deck = -d / 2 + 2.0, self.mat("deck", 0.7)
        self.box("boardwalk", (w, 3.0, 0.3), (0, deck_y, 0.33), deck)
        wood, metal = self.mat("bark", 0.85), self.mat("metal", 0.4)
        for x in lines(-w / 2 + 0.5, w / 2 - 0.5, 0.5):
            self.b(self.mat("dark", 0.8), (0.03, 3.0, 0.015), (x, deck_y, 0.485))
        for x in lines(-w / 2 + 1.0, w / 2 - 1.0, 3.0):
            for y in (deck_y - 1.4, deck_y + 1.4):
                self.b(wood, (0.2, 0.2, 0.6), (x, y, 0.15))
            self.b(wood, (0.1, 0.1, 0.95), (x, deck_y - 1.45, 0.95))
        for z in (1.08, 1.4):
            self.b(wood, (w - 1.0, 0.08, 0.08), (0, deck_y - 1.45, z))
        for x in (-w * 0.32, w * 0.08, w * 0.3):
            self.bench(x, deck_y - 0.9, 0.0)
        for x in lines(-w / 2 + 4.0, w / 2 - 2.0, 12.0):
            self.lamp_post(x, deck_y + 1.3, -1)
        # the kiosk: a real front with a hatch and a counter, a striped awning and a sign on the roof
        kx, ky = -w / 4, -d / 2 + 6.5
        self.box("kiosk", (4.0, 3.0, 2.6), (kx, ky, 1.42), self.mat("wall", 0.7))
        self.b(deck, (5.0, 4.0, 0.2), (kx, ky, 2.82))
        self.b(self.mat("dark", 0.8), (2.6, 0.06, 1.0), (kx, ky + 1.52, 1.75))
        self.b(self.mat("trim", 0.4), (2.9, 0.5, 0.08), (kx, ky + 1.7, 1.2))
        for i in range(7):
            col = self.mat("blue", 0.7) if i % 2 == 0 else self.mat("white", 0.7)
            x0 = kx - 1.75 + i * 0.5
            self.add(col, ([(x0, ky + 1.5, 2.6), (x0 + 0.5, ky + 1.5, 2.6), (x0 + 0.5, ky + 2.6, 2.1), (x0, ky + 2.6, 2.1)], [(0, 1, 2, 3)]))
        self.b(self.mat("yellow", 0.5), (2.6, 0.12, 0.7), (kx, ky + 1.3, 3.3))
        for ox in (-1.0, 1.0):
            self.b(wood, (0.08, 0.08, 0.6), (kx + ox, ky + 1.3, 3.05))
        # a row of painted beach huts behind the sand
        for i in range(4):
            hx, hy = w * 0.12 + i * 3.1, -d / 2 + 6.0
            colour = ["blue", "red", "yellow", "green"][i % 4]
            self.box("hut", (2.6, 2.4, 2.3), (hx, hy, 1.3), self.mat(colour, 0.7))
            self.b(self.mat("white", 0.6), (1.0, 0.06, 1.9), (hx, hy + 1.22, 1.1))
            self.add(self.mat("white", 0.7), ([(hx - 1.5, hy - 1.4, 2.4), (hx + 1.5, hy - 1.4, 2.4), (hx + 1.5, hy + 1.5, 2.4), (hx - 1.5, hy + 1.5, 2.4), (hx - 1.5, hy, 3.3), (hx + 1.5, hy, 3.3)], [(0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5)]))
        # a lifeguard's tower
        tx, ty = w * 0.38, d / 2 - 7.0
        for ox in (-0.8, 0.8):
            for oy in (-0.8, 0.8):
                self.b(self.mat("white", 0.6), (0.12, 0.12, 2.2), (tx + ox, ty + oy, 1.2))
        self.box("lifeguard_tower", (2.4, 2.4, 1.6), (tx, ty, 3.1), self.mat("white", 0.6))
        self.b(self.mat("red", 0.6), (2.8, 2.8, 0.15), (tx, ty, 4.0))
        self.b(self.mat("dark", 0.5), (1.5, 0.05, 0.6), (tx, ty + 1.22, 3.3))
        for i in range(6):
            self.b(self.mat("white", 0.6), (0.9, 0.2, 0.05), (tx, ty - 1.3 - i * 0.28, 2.0 - i * 0.33))
        # umbrellas with striped canopies, slatted loungers, towels; palms and rocks at the back
        n_um = 4 + int(w // 16)
        for i in range(n_um):
            ux, uy = -w * 0.42 + i * w * 0.84 / max(1, n_um - 1) + self.rnd.uniform(-1, 1), self.rnd.uniform(-1.0, d * 0.36)
            self.cyl("umbrella_pole", 0.04, 2.2, (ux, uy, 1.2), self.mat("metal", 0.4))
            a, b = self.mat(self.rnd.choice(["red", "blue", "green", "yellow"]), 0.8), self.mat("white", 0.8)
            for k in range(8):
                t0, t1 = 2 * math.pi * k / 8, 2 * math.pi * (k + 1) / 8
                self.add(a if k % 2 else b, ([(ux + 1.25 * math.cos(t0), uy + 1.25 * math.sin(t0), 2.05), (ux + 1.25 * math.cos(t1), uy + 1.25 * math.sin(t1), 2.05), (ux, uy, 2.55)], [(0, 1, 2)]))
            lx = ux + 1.2
            self.collider("lounger", (0.7, 1.9, 0.4), (lx, uy, 0.3))
            for k in range(9):
                self.b(deck, (0.65, 0.16, 0.03), (lx, uy - 0.8 + k * 0.2, 0.42 + (0.12 * max(0, k - 5))))
            for ox in (-0.28, 0.28):
                for oy in (-0.8, 0.7):
                    self.b(metal, (0.04, 0.04, 0.3), (lx + ox, uy + oy, 0.25))
            self.b(self.mat(self.rnd.choice(["red", "yellow", "blue"]), 0.9), (0.9, 1.7, 0.01), (ux - 1.2, uy + 0.3, 0.2))
            if self.night:
                self.light((ux, uy, 2.0), 80.0)
        for i in range(max(3, int(w // 8))):
            px, py = -w / 2 + 4.5 + i * (w - 9.0) / max(1, max(3, int(w // 8)) - 1), -d / 2 + self.rnd.uniform(5.0, 9.0)
            if abs(px - kx) < 3.5 or abs(px - (w * 0.12 + 4.6)) < 6.5:
                continue
            self.palm(px, py)
        for _ in range(6):
            self.add(self.mat("rock", 0.9), blob_v(self.rnd.uniform(0.35, 0.9), (self.rnd.uniform(-w / 2 + 1.2, w / 2 - 1.2), d / 2 - self.rnd.uniform(1.2, 3.5), 0.1), self.rnd, squash=0.6))

    def palm(self, x, y):
        h = self.rnd.uniform(5.5, 8.0)
        dx, dy = self.rnd.uniform(-0.8, 0.8), self.rnd.uniform(-0.8, 0.8)
        self.cyl("palm_trunk_base", 0.2, 0.6, (x, y, 0.3), self.mat("bark", 0.9))
        self.add(self.mat("bark", 0.9), ring_v(0.17, 0.11, h, (x, y, 0.1), 10, lean=(dx, dy)))
        tx, ty, tz, leaf = x + dx, y + dy, h + 0.1, self.mat("palm", 0.8)
        for k in range(9):
            a = 2 * math.pi * k / 9 + self.rnd.uniform(-0.2, 0.2)
            length = self.rnd.uniform(2.4, 3.3)
            ca, sa = math.cos(a), math.sin(a)
            pts = []
            for s in range(6):
                t = s / 5
                r = length * t
                z = tz + 0.6 * math.sin(t * 2.2) - 1.6 * t * t
                half = 0.42 * math.sin(math.pi * min(1.0, t + 0.08))
                pts.append((tx + ca * r - sa * half, ty + sa * r + ca * half, z))
                pts.append((tx + ca * r + sa * half, ty + sa * r - ca * half, z))
            self.add(leaf, (pts, [(2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) for i in range(5)]))


def views(p, kit):
    sc = bpy.context.scene
    _wk.set_engine(sc, p.get("engine", "cycles"), int(p.get("samples", 16)))
    sc.render.resolution_x = sc.render.resolution_y = int(p.get("size", 512))
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    lo, hi = _wk.world_bounds(_wk.solids(list(sc.objects)))
    c = Vector([(lo[i] + hi[i]) / 2 for i in range(3)])
    cam = bpy.data.objects.new("views_cam", bpy.data.cameras.new("views_cam"))
    sc.collection.objects.link(cam)
    sc.camera, cam.rotation_mode, cam.data.lens, cam.data.clip_end = cam, "QUATERNION", 20.0, BIG * 2
    if kit == "interior":
        w, d = hi[0] - lo[0], hi[1] - lo[1]
        shots = [(Vector((c.x + sx * (w / 2 - 0.6), c.y + sy * (d / 2 - 0.6), 1.7)),
                  Vector((c.x - sx * w / 2, c.y - sy * d / 2, 1.0))) for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
    elif kit == "street":
        # A street is seen from inside it: along the road from each end, and from above each end looking down its length.
        half, r = (hi[0] - lo[0]) / 2, max(hi[0] - lo[0], hi[1] - lo[1])
        far = Vector((c.x, c.y, 1.5))
        shots = [(Vector((c.x + half - 1.0, c.y - 1.0, 1.7)), far), (Vector((c.x - half + 1.0, c.y + 1.0, 1.7)), far),
                 (Vector((c.x + half + 6.0, c.y, r * 0.45)), far), (Vector((c.x - half - 6.0, c.y, r * 0.45)), far)]
    else:
        r = max(hi[0] - lo[0], hi[1] - lo[1])
        shots = [(Vector((c.x + math.cos(a) * r * 0.55, c.y + math.sin(a) * r * 0.55, r * 0.22)), Vector((c.x, c.y, 1.0)))
                 for a in (math.radians(x) for x in (65, 135, 225, 295))]
    os.makedirs(p["views"], exist_ok=True)
    for i, (pos, look) in enumerate(shots):
        cam.location = pos
        cam.rotation_quaternion = (look - pos).to_track_quat("-Z", "Y")
        sc.render.filepath = os.path.join(p["views"], f"view_{i}.png")
        bpy.ops.render.render(write_still=True)


def run(p):
    _wk.reset()
    kit = p["recipe"]["kit"]
    k = Kit(p)
    getattr(k, kit)()
    k.flush()
    _wk.apply_look(p["look"])
    _wk.export_glb(p["out"], lights=True)
    views(p, kit)
    _wk.reset()
    _wk.done(inspect=_wk.inspect(_wk.import_model(p["out"])))


_wk.main(run)

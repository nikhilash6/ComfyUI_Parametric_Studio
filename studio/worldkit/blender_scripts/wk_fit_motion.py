"""blender -b --factory-startup --python wk_fit_motion.py -- PAYLOAD.json
payload {"motion": a Kimodo SOMA BVH, "rig": a rigged character glb, "out": an FBX of the rig with the clip}
A Kimodo BVH's zero pose is not a person standing: every bone lies along its own local X, so nothing can be compared with a rig's rest pose by rotation (that gives a wrong facing and limbs twisted to ribbons). What it does hold is where each joint is. So this fits the rig from joint positions, frame by frame: the hips and the chest from their left-right and up axes, each limb bone by the smallest turn that points it where the motion's bone points, with no twist of its own, and a foot stays flat and only turns. Fingers and anything else follow their parent. The rig keeps the motion's world facing: Kimodo's people face -Y once imported, as a rig does. CPU, no render."""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
from mathutils import Matrix, Quaternion, Vector  # noqa: E402

import _wk  # noqa: E402

_spec = importlib.util.spec_from_file_location("rigmap", os.path.join(os.path.dirname(HERE), "rigmap.py"))
rigmap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rigmap)

#: rig slot -> the motion's joint where the bone starts and the joint it points at
LIMBS = {"neck": ("Neck1", "Head"),     # the head turns with the neck: a rig's head bone is a leaf, and a leaf's tail is the importer's guess
         "l_upperarm": ("LeftArm", "LeftForeArm"), "l_forearm": ("LeftForeArm", "LeftHand"), "l_hand": ("LeftHand", "LeftHandMiddle2"),
         "r_upperarm": ("RightArm", "RightForeArm"), "r_forearm": ("RightForeArm", "RightHand"), "r_hand": ("RightHand", "RightHandMiddle2"),
         "l_thigh": ("LeftLeg", "LeftShin"), "l_shin": ("LeftShin", "LeftFoot"), "l_foot": ("LeftFoot", "LeftToeBase"),
         "r_thigh": ("RightLeg", "RightShin"), "r_shin": ("RightShin", "RightFoot"), "r_foot": ("RightFoot", "RightToeBase")}
CLAVICLES = {"l_upperarm": ("LeftShoulder", "LeftArm"), "r_upperarm": ("RightShoulder", "RightArm")}


def frame_of(left, right, base, top) -> Matrix:
    """A rotation from a left-right axis and an up axis."""
    x = (left - right).normalized()
    up = top - base
    z = (up - x * up.dot(x)).normalized()
    return Matrix((x, z.cross(x), z)).transposed()


def flat_turn(rest, want) -> Quaternion:
    """The turn about the vertical that takes one direction to another, seen from above."""
    r, w = Vector((rest.x, rest.y, 0)), Vector((want.x, want.y, 0))
    return r.rotation_difference(w) if r.length > 1e-6 and w.length > 1e-6 else Quaternion()


def run(p):
    _wk.reset()
    tgt_objs = _wk.import_model(p["rig"])
    tgt = next(o for o in tgt_objs if o.type == "ARMATURE")
    slots = rigmap.slots(_wk.bones(tgt_objs))
    if tgt.animation_data:
        for t in list(tgt.animation_data.nla_tracks):
            tgt.animation_data.nla_tracks.remove(t)
        tgt.animation_data.action = None
    src = next(o for o in _wk.import_model(p["motion"]) if o.type == "ARMATURE")
    f0, f1 = (int(x) for x in src.animation_data.action.frame_range)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = f0, f1
    with open(p["motion"], errors="replace") as fh:         # the clip plays at the motion's own speed, not the scene's default
        step = next((float(ln.split(":")[1]) for ln in fh if ln.strip().startswith("Frame Time:")), 0.0)
    if step > 0:
        sc.render.fps, sc.render.fps_base = round(1 / step), 1.0

    bones = sorted(tgt.data.bones, key=lambda b: len(b.parent_recursive))
    by = {b.name: b for b in bones}
    head = {b.name: b.head_local.copy() for b in bones}
    rest_rot = {b.name: b.matrix_local.to_quaternion() for b in bones}
    kids = {b.name: [c.name for c in b.children] for b in bones}

    def aim_point(name: str) -> Vector:
        """Where a rig bone points: its next joint. A hand or a foot: the middle of its children."""
        c = kids[name]
        if not c:
            return by[name].tail_local.copy()
        return sum((head[n] for n in c), Vector()) / len(c)

    # what each rig bone does: its slot's aim, in the order parents come first
    aim = {}
    for slot, joints in LIMBS.items():
        name = slots[slot]
        target = head[name]
        next_slot = {"neck": "head", "l_upperarm": "l_forearm", "l_forearm": "l_hand", "r_upperarm": "r_forearm", "r_forearm": "r_hand", "l_thigh": "l_shin", "l_shin": "l_foot", "r_thigh": "r_shin", "r_shin": "r_foot"}.get(slot)
        aim[name] = (joints, (head[slots[next_slot]] if next_slot else aim_point(name)) - target)
    for slot, joints in CLAVICLES.items():
        arm = by[slots[slot]]
        if arm.parent is not None and arm.parent.name != slots["chest"]:
            aim[arm.parent.name] = (joints, head[arm.name] - head[arm.parent.name])

    feet = {slots["l_foot"], slots["r_foot"]}
    hips, chest = slots["hips"], slots["chest"]
    chain = [by[chest]]                                     # the spine, hips to chest: turned part of the way
    while chain[-1].parent is not None and chain[-1].parent.name != hips:
        chain.append(chain[-1].parent)
    if chain[-1].parent is None:
        raise ValueError("the rig's chest does not hang from its hips")
    spine = {b.name: (i + 1) / len(chain) for i, b in enumerate(reversed(chain))}

    lthigh, rthigh = head[slots["l_thigh"]], head[slots["r_thigh"]]
    tgt_hips = frame_of(lthigh, rthigh, head[hips], head[slots["chest"]]).to_quaternion()
    larm, rarm = head[slots["l_upperarm"]], head[slots["r_upperarm"]]
    tgt_chest = frame_of(larm, rarm, head[chest], head[slots["neck"]]).to_quaternion()
    rest_rel = {b.name: (b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else b.matrix_local.copy() for b in bones}
    obj_ground = min(v.z for v in head.values())

    def joints_at(f):
        sc.frame_set(f)
        return {pb.name: src.matrix_world @ pb.head for pb in src.pose.bones}

    first = joints_at(f0)
    s_ground = min(first[n].z for n in ("LeftToeBase", "RightToeBase"))
    ratio = (head[hips].z - obj_ground) / max(first["Hips"].z - s_ground, 1e-6)

    ad = tgt.animation_data_create()
    act = bpy.data.actions.new("clip")
    ad.action = act
    _wk.use_slot(ad, act)
    for pb in tgt.pose.bones:
        pb.rotation_mode = "QUATERNION"
    for f in range(f0, f1 + 1):
        j = joints_at(f)
        turned = {}                                         # bone -> how far it has turned from rest, in the armature's space
        pose = {}
        d_hips = frame_of(j["LeftLeg"], j["RightLeg"], j["Hips"], j["Chest"]).to_quaternion() @ tgt_hips.inverted()
        d_chest = frame_of(j["LeftArm"], j["RightArm"], j["Chest"], j["Neck1"]).to_quaternion() @ tgt_chest.inverted()
        for b in bones:
            n = b.name
            parent = b.parent.name if b.parent else ""
            if n == hips:
                d = d_hips
            elif n in spine:
                d = d_hips.slerp(d_chest, spine[n])
            elif n in aim:
                (a, c), rest_dir = aim[n]
                base = turned.get(parent, Quaternion())
                want = j[c] - j[a]
                now = base @ rest_dir
                if n in feet:                             # a foot only turns about the vertical and stays flat: a rig's foot bone and the motion's do not lie the same way, and aiming one at the other tips the boot onto its side
                    d = flat_turn(rest_dir, want)
                else:
                    d = (now.rotation_difference(want) @ base) if want.length > 1e-6 and now.length > 1e-6 else base
            else:
                d = turned.get(parent, Quaternion())
            turned[n] = d
            q = d @ rest_rot[n]
            if n == hips:
                loc = Vector((head[n].x + (j["Hips"].x - first["Hips"].x) * ratio, head[n].y + (j["Hips"].y - first["Hips"].y) * ratio, obj_ground + (j["Hips"].z - s_ground) * ratio))
            elif parent:
                loc = (pose[parent] @ rest_rel[n]).translation
            else:
                loc = head[n]
            pose[n] = Matrix.LocRotScale(loc, q, None)
            m0 = (pose[parent] @ rest_rel[n]) if parent else rest_rel[n]
            basis = m0.inverted() @ pose[n]
            pb = tgt.pose.bones[n]
            pb.rotation_quaternion = basis.to_quaternion()
            pb.keyframe_insert("rotation_quaternion", frame=f)
            if not parent:
                pb.location = basis.translation
                pb.keyframe_insert("location", frame=f)

    bpy.data.objects.remove(src, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in [tgt, *_wk.meshes(tgt_objs)]:                  # with its skinned mesh: FBX stores the rest pose as the mesh's bind pose, and without one the importer takes a posed frame for rest
        o.select_set(True)
    bpy.context.view_layer.objects.active = tgt
    bpy.ops.export_scene.fbx(filepath=p["out"], use_selection=True, object_types={"ARMATURE", "MESH"}, use_mesh_modifiers=False, add_leaf_bones=False, bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                             bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0, armature_nodetype="NULL")
    _wk.done(frames=f1 - f0 + 1, ratio=round(ratio, 5))


_wk.main(run)

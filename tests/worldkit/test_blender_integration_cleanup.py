from studio import glb
from studio.worldkit import library as L
from studio.worldkit.makers import prop as P
from tests.worldkit.conftest import needs_blender
from tests.worldkit.helpers import ctx_for

pytestmark = needs_blender


def test_cleanup_scales_centres_grounds_and_adds_a_collider(wk_fixtures, tmp_path):
    lib = L.Library()
    meta = lib.create(L.new_meta("prop", "box", source={"kind": "text", "prompt": "box"}, recipe={"size_m": 1.0}))
    main = P.cleanup(ctx_for(lib, meta, tmp_path, {"mesh": {"main": {"path": str(wk_fixtures / "prop.glb")}}}))["main"]
    ins = main["inspect"]
    assert abs(max(ins["dims_m"]) - 1.0) < 0.01 and abs(ins["lo"][2]) < 0.001
    assert abs(ins["lo"][0] + ins["hi"][0]) < 0.01 and abs(ins["lo"][1] + ins["hi"][1]) < 0.01
    assert ins["colliders"] == 1 and glb.facts(main["path"])["colliders"] == 1

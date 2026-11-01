import torch
import n_10_fbx_loading_and_rendering_test as mod

CLS = mod.PSN_Cube_Preview_Render


def test_node_class_exists():
    assert list(mod.NODE_CLASS_MAPPINGS) == ["PSN_Cube_Preview_Render"]
    assert mod.NODE_DISPLAY_NAME_MAPPINGS["PSN_Cube_Preview_Render"] == "Cube Preview Render"
    # the old FBX-loading node is gone
    assert not hasattr(mod, "PSN_FBXLoad_Render")
    assert not hasattr(mod, "_load_fbx_mesh")
    assert "does not read fbx" in CLS.DESCRIPTION.lower()


def test_input_types():
    req = CLS.INPUT_TYPES()["required"]
    assert set(req) == {"render_mode", "camera_angle"}  # fbx_path dropped
    assert req["render_mode"][0] == ("clay", "shaded")


def test_return_types():
    assert CLS.RETURN_TYPES == ("IMAGE", "STRING")
    assert CLS.RETURN_NAMES == ("rendered_image", "mesh_description")
    assert CLS.FUNCTION == "run"
    assert CLS.CATEGORY.startswith("ParametricStudio/")


def test_run_basic_values():
    img, desc = CLS().run(render_mode="clay", camera_angle=0.0)
    assert tuple(img.shape) == (1, 256, 256, 3)
    assert img.min() >= 0.0 and img.max() <= 1.0
    # clay background is 0.15 grey in the corner, cube face is 0.85 * brightness at the centre
    assert torch.allclose(img[0, 0, 0], torch.full((3,), 0.15))
    centre = img[0, 128, 128]
    assert centre[0] > 0.4 and torch.allclose(centre, centre[0].expand(3))
    assert desc == "built-in unit cube (8 vertices, 6 faces)"
    assert "fbx" not in desc.lower()


def test_shaded_mode_differs_and_is_blue():
    clay, _ = CLS().run(render_mode="clay", camera_angle=0.0)
    shaded, _ = CLS().run(render_mode="shaded", camera_angle=0.0)
    assert torch.allclose(shaded[0, 0, 0], torch.tensor([0.05, 0.05, 0.10]))
    c = shaded[0, 128, 128]
    assert c[2] > c[0]
    assert not torch.allclose(clay, shaded)


def test_bad_render_mode_falls_back_to_clay():
    bad, _ = CLS().run(render_mode="invalid_mode", camera_angle=0.0)
    clay, _ = CLS().run(render_mode="clay", camera_angle=0.0)
    assert torch.equal(bad, clay)


def test_different_camera_angles_change_cube_footprint():
    img0, _ = CLS().run(render_mode="clay", camera_angle=0.0)
    img1, _ = CLS().run(render_mode="clay", camera_angle=0.7854)
    cube0 = (img0[0, :, :, 0] > 0.2).sum().item()
    cube1 = (img1[0, :, :, 0] > 0.2).sum().item()
    assert cube0 > 0 and cube1 > 0
    assert cube0 != cube1


def test_no_in_place_modification():
    img1, _ = CLS().run(render_mode="clay", camera_angle=0.0)
    img2, _ = CLS().run(render_mode="clay", camera_angle=0.0)
    img1[0, 0, 0, 0] = 0.999
    assert img2[0, 0, 0, 0].item() < 0.999


if __name__ == "__main__":
    test_node_class_exists()
    test_input_types()
    test_return_types()
    test_run_basic_values()
    test_shaded_mode_differs_and_is_blue()
    test_bad_render_mode_falls_back_to_clay()
    test_different_camera_angles_change_cube_footprint()
    test_no_in_place_modification()
    print("ok")

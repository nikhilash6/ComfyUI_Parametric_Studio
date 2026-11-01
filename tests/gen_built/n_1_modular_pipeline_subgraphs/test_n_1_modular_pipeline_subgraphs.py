import torch

import n_1_modular_pipeline_subgraphs as mod
from n_1_modular_pipeline_subgraphs import (
    PSN_SubgraphPort,
    PSN_Dict_Router,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_module_mappings():
    assert set(NODE_CLASS_MAPPINGS) == {"PSN_SubgraphPort", "PSN_Dict_Router"}
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Dict_Router"] == "Dict Router"
    # the stage-running wrapper claim is gone: no stage registry, no old name
    assert not hasattr(mod, "PSN_SubgraphWrapper")
    assert not hasattr(PSN_Dict_Router, "register_stage")
    assert not hasattr(PSN_Dict_Router, "_stages")
    assert PSN_Dict_Router.RETURN_NAMES == ("routed_dict", "status")
    assert "Runs no stages" in PSN_Dict_Router.DESCRIPTION
    for cls in NODE_CLASS_MAPPINGS.values():
        assert cls.FUNCTION == "run"
        assert cls.CATEGORY.startswith("ParametricStudio/")
        it = cls.INPUT_TYPES()
        assert "required" in it


def test_port_ok_and_type_safety():
    port = PSN_SubgraphPort()
    img = torch.rand(1, 4, 4, 3)
    val, status = port.run("in_0", "IMAGE", img)
    assert status == "ok"
    assert torch.equal(val, img)
    # input must not be mutated by the port
    val[0, 0, 0, 0] = 0.5
    assert not torch.equal(val, img)

    # bad type: 3-d tensor is not an IMAGE
    bad, status = port.run("in_0", "IMAGE", torch.rand(1, 4, 4))
    assert status.startswith("error")

    # out-of-range image values rejected
    bad, status = port.run("in_0", "IMAGE", torch.rand(1, 4, 4, 3) * 2.0)
    assert status.startswith("error")

    # empty port name rejected
    _, status = port.run("  ", "IMAGE", img)
    assert status.startswith("error")


def test_router_renames_and_validates():
    w = PSN_Dict_Router()

    img = torch.rand(2, 8, 8, 3)
    mask = torch.rand(2, 8, 8)
    handle, status = w.run(
        "sg_test",
        {"in_img": ("img", "IMAGE"), "in_mask": ("mask", "MASK")},
        {"out_img": ("img", "IMAGE"), "out_mask": ("mask", "MASK")},
        {"in_img": img, "in_mask": mask},
    )
    assert status == "routed 2 entries"
    assert set(handle) == {"out_img", "out_mask"}
    # values are copied unchanged: no stage ran, nothing was scaled
    assert torch.equal(handle["out_img"], img)
    assert torch.equal(handle["out_mask"], mask)
    # no in-place mutation of the inputs
    handle["out_img"].fill_(1.0)
    assert not torch.equal(handle["out_img"], img)


def test_router_only_returns_outputs_named_in_output_map():
    w = PSN_Dict_Router()
    handle, status = w.run(
        "sg_sub",
        {"a": "INT", "b": "STRING"},
        {"only_b": ("b", "STRING")},
        {"a": 3, "b": "hi"},
    )
    assert handle == {"only_b": "hi"}
    assert status == "routed 1 entries"


def test_router_registered_stage_is_not_run():
    """Stage functions are no longer a thing: nothing user-registered can run."""
    ran = []
    PSN_Dict_Router._stages = {"sg_s": lambda i: ran.append(1) or {"x": 1}}
    handle, status = PSN_Dict_Router().run(
        "sg_s", {"a": "INT"}, {"x": ("a", "INT")}, {"a": 7}
    )
    assert ran == []
    assert handle == {"x": 7}


def test_router_bad_inputs():
    w = PSN_Dict_Router()

    # missing input
    _, status = w.run("sg_x", {"a": "IMAGE"}, {}, {})
    assert status.startswith("error")

    # wrong type for declared input
    _, status = w.run("sg_x", {"a": "IMAGE"}, {}, {"a": torch.rand(2, 2)})
    assert status.startswith("error")

    # malformed input map
    _, status = w.run("sg_x", {"a": 123}, {}, {})
    assert status.startswith("error")

    # bad router id
    _, status = w.run("", {}, {}, {})
    assert status.startswith("error")

    # output names an internal entry that no input produced
    handle, status = w.run("sg_x", {"a": "INT"}, {"o": ("nope", "INT")}, {"a": 1})
    assert handle == {} and "no routed entry" in status

    # output type does not match the routed value
    handle, status = w.run("sg_x", {"a": "INT"}, {"o": ("a", "IMAGE")}, {"a": 1})
    assert handle == {} and status.startswith("error")


def test_router_latent_passthrough():
    w = PSN_Dict_Router()
    latent = {"samples": torch.rand(1, 4, 16, 16)}
    handle, status = w.run(
        "sg_latent",
        {"lat": "LATENT"},
        {"lat_out": ("lat", "LATENT")},
        {"lat": latent},
    )
    assert status == "routed 1 entries"
    assert isinstance(handle["lat_out"], dict)
    assert torch.equal(handle["lat_out"]["samples"], latent["samples"])
    # clone check: mutating the handle must not touch the original
    handle["lat_out"]["samples"].fill_(0.0)
    assert not torch.equal(handle["lat_out"]["samples"], latent["samples"])


def main():
    test_module_mappings()
    test_port_ok_and_type_safety()
    test_router_renames_and_validates()
    test_router_only_returns_outputs_named_in_output_map()
    test_router_registered_stage_is_not_run()
    test_router_bad_inputs()
    test_router_latent_passthrough()
    print("ok")


if __name__ == "__main__":
    main()

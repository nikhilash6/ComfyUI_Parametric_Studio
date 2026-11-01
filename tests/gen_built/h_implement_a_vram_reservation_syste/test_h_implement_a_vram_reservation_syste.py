import torch

import h_implement_a_vram_reservation_syste as mod


def _img():
    return torch.rand(1, 4, 4, 3)


def _fresh_ledger():
    led = mod._Ledger()
    return led


def _reset_global():
    mod.LEDGER = mod._Ledger()


def test_reserve_grants_and_reduces_free():
    led = _fresh_ledger()
    led.configure(16.0, 1.0)
    led.set_live_used(2.0)
    granted, free_after = led.reserve("a", 3.0)
    assert granted is True
    assert abs(free_after - (16.0 - 1.0 - 2.0 - 3.0)) < 1e-9
    assert led.snapshot()["reservations"] == {"a": 3.0}


def test_reserve_denied_when_not_enough():
    led = _fresh_ledger()
    led.configure(8.0, 1.0)
    led.set_live_used(0.0)
    granted, free = led.reserve("big", 100.0)
    assert granted is False
    assert abs(free - 7.0) < 1e-9
    # ledger must be untouched on denial
    assert led.snapshot()["reservations"] == {}


def test_release_and_duplicate():
    led = _fresh_ledger()
    led.configure(8.0, 0.0)
    led.reserve("x", 1.0)
    led.release("x")
    assert led.snapshot()["reservations"] == {}
    try:
        led.release("x")
        raise AssertionError("expected KeyError")
    except KeyError:
        pass
    try:
        led.reserve("x", 1.0)
        led.reserve("x", 1.0)
        raise AssertionError("expected ValueError on duplicate")
    except ValueError:
        pass


def test_bad_inputs_raise():
    led = _fresh_ledger()
    for bad in [(0.0, 1.0), (8.0, 8.0), (8.0, -1.0)]:
        try:
            led.configure(*bad)
            raise AssertionError("expected ValueError for %r" % (bad,))
        except ValueError:
            pass
    try:
        led.set_live_used(-0.5)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        led.reserve("", 1.0)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        led.reserve("ok", -1.0)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_node_reserve_gate_passes_image_unchanged():
    _reset_global()
    node = mod.PSN_VramLedgerReserve()
    img = _img()
    out_img, granted, free = node.run(img, "t1", 1.0, 16.0, 1.0, 0.0, True)
    assert granted is True
    assert out_img is not img
    assert torch.equal(out_img, img)
    # input must not be mutated
    assert img.shape == (1, 4, 4, 3)


def test_node_reserve_denied_raises_and_no_mutation():
    _reset_global()
    node = mod.PSN_VramLedgerReserve()
    img = _img()
    try:
        node.run(img, "t2", 1000.0, 8.0, 1.0, 0.0, True)
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass
    # with fail_on_denied=False it returns granted=False
    out_img, granted, free = node.run(img, "t2", 1000.0, 8.0, 1.0, 0.0, False)
    assert granted is False
    assert torch.equal(out_img, img)


def test_node_release_and_report():
    _reset_global()
    node = mod.PSN_VramLedgerReserve()
    rel = mod.PSN_VramLedgerRelease()
    rep = mod.PSN_VramReport()
    img = _img()
    node.run(img, "t3", 2.0, 16.0, 1.0, 0.0, True)
    out_img, released = rel.run(img, "t3", True)
    assert released is True
    assert torch.equal(out_img, img)
    # releasing again with fail_on_missing=False -> released False
    _, released2 = rel.run(img, "t3", False)
    assert released2 is False
    # releasing again with fail_on_missing=True -> KeyError
    try:
        rel.run(img, "t3", True)
        raise AssertionError("expected KeyError")
    except KeyError:
        pass
    out_img, free, reserved, live = rep.run(img)
    assert reserved == 0.0
    assert live == 0.0
    assert abs(free - 15.0) < 1e-9
    assert torch.equal(out_img, img)


def test_bad_image_type_and_shape():
    _reset_global()
    node = mod.PSN_VramLedgerReserve()
    try:
        node.run("not a tensor", "t", 1.0, 16.0, 1.0, 0.0, True)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass
    try:
        node.run(torch.rand(4, 4, 3), "t4", 1.0, 16.0, 1.0, 0.0, True)
        raise AssertionError("expected TypeError for 3-d image")
    except TypeError:
        pass


def test_ledger_names_and_no_gpu_claim():
    R, L = mod.PSN_VramLedgerReserve, mod.PSN_VramLedgerRelease
    assert R.RETURN_NAMES == ("image", "ledger_granted", "ledger_free_gb")
    assert L.RETURN_NAMES == ("image", "ledger_entry_removed")
    assert "Reserves no GPU memory" in R.DESCRIPTION
    assert "Frees no GPU memory" in L.DESCRIPTION
    assert "PSN_VramReserve" not in mod.NODE_CLASS_MAPPINGS
    assert "PSN_VramRelease" not in mod.NODE_CLASS_MAPPINGS
    # figures come from the typed inputs: 10 total - 2 system - 1 live - 3 need = 4
    _reset_global()
    _, granted, free = R().run(_img(), "n1", 3.0, 10.0, 2.0, 1.0, True)
    assert granted is True and abs(free - 4.0) < 1e-9


def test_module_mappings():
    assert "PSN_VramLedgerReserve" in mod.NODE_CLASS_MAPPINGS
    assert "PSN_VramLedgerRelease" in mod.NODE_CLASS_MAPPINGS
    assert "PSN_VramReport" in mod.NODE_CLASS_MAPPINGS
    for name, cls in mod.NODE_CLASS_MAPPINGS.items():
        assert cls.FUNCTION == "run"
        assert cls.CATEGORY == "ParametricStudio/VRAM"
        assert name in mod.NODE_DISPLAY_NAME_MAPPINGS
        it = cls.INPUT_TYPES()
        assert "required" in it


if __name__ == "__main__":
    test_reserve_grants_and_reduces_free()
    test_reserve_denied_when_not_enough()
    test_release_and_duplicate()
    test_bad_inputs_raise()
    test_node_reserve_gate_passes_image_unchanged()
    test_node_reserve_denied_raises_and_no_mutation()
    test_node_release_and_report()
    test_bad_image_type_and_shape()
    test_ledger_names_and_no_gpu_claim()
    test_module_mappings()
    print("ok")

"""New-arrival scan on a temp folder. No live ports."""
import importlib.util, os, time
from pathlib import Path
s = importlib.util.spec_from_file_location("scan_new", Path(__file__).resolve().parent.parent / "scripts" / "scan_new_models.py"); M = importlib.util.module_from_spec(s); s.loader.exec_module(M)


def _put(p, n=10, age=1000):
    p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b"x" * n); t = time.time() - age; os.utime(p, (t, t)); return p


def test_partials_and_temp_folders_are_skipped(tmp_path):
    _put(tmp_path / "a.safetensors"); _put(tmp_path / "b.safetensors.incomplete"); _put(tmp_path / "c.part"); _put(tmp_path / "dl_small" / "d.safetensors"); _put(tmp_path / "x.tmp" / "e.ckpt"); _put(tmp_path / "f.txt")
    new, _ = M.scan([str(tmp_path)], {})
    assert [Path(p).name for p, _ in new] == ["a.safetensors"]


def test_a_growing_file_waits_and_a_done_file_is_reported_once(tmp_path):
    f = _put(tmp_path / "g.safetensors", age=200)
    new, st = M.scan([str(tmp_path)], {str(f): 5})
    assert not new and st[str(f)] == 10                   # the size changed since the last scan
    new, st = M.scan([str(tmp_path)], st)
    assert [p for p, _ in new] == [str(f)]
    assert M.scan([str(tmp_path)], st)[0] == []


def test_a_fresh_file_is_not_trusted_yet(tmp_path):
    f = _put(tmp_path / "h.ckpt", age=5)
    assert M.scan([str(tmp_path)], {})[0] == []

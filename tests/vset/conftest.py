"""Virtual Set tests share World Kit's isolation (a tmp library, tmp work folders, ComfyUI pointed at a dead port) and its Blender fixtures, and keep shots under tmp_path."""
import pytest

from tests.worldkit.conftest import _worldkit_isolation, wk_fixtures  # noqa: F401  (fixtures)


@pytest.fixture(autouse=True)
def _vset_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_VSET_ROOT", str(tmp_path / "vset"))
    yield

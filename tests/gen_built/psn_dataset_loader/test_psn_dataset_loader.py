import json

from psn_dataset_loader import (
    PSN_Dataset_Loader,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    DATASET,
)

node = PSN_Dataset_Loader()

# 1. CSV happy path
out, meta = node.run("name,age\nAlice,30\nBob,25", "csv")
assert out["num_records"] == 2
assert out["records"][0] == {"name": "Alice", "age": "30"}
assert out["keys"] == ["name", "age"]
m = json.loads(meta)
assert m["num_records"] == 2 and m["format"] == "csv"

# 2. JSON happy path (list of objects)
out, meta = node.run('[{"a": 1}, {"a": 2, "b": 3}]', "json")
assert out["num_records"] == 2
assert out["keys"] == ["a", "b"]
assert json.loads(meta)["num_records"] == 2

# 3. JSON single object -> wrapped in list
out, _ = node.run('{"x": 5}', "json")
assert out["num_records"] == 1
assert out["records"] == [{"x": 5}]

# 4. Folder format: newline-separated paths
out, meta = node.run("/data/a.png\n/data/b.png", "folder")
assert out["num_records"] == 2
assert out["records"][1] == {"path": "/data/b.png"}

# 5. Edge: empty CSV (only header) -> zero records
out, meta = node.run("name,age", "csv")
assert out["num_records"] == 0
assert out["records"] == []
assert json.loads(meta)["num_records"] == 0

# 6. Bad input: unsupported format raises
try:
    node.run("x", "yaml")
    raise AssertionError("expected ValueError for bad format")
except ValueError:
    pass

# 7. Bad input: empty path raises
try:
    node.run("   ", "csv")
    raise AssertionError("expected ValueError for empty path")
except ValueError:
    pass

# 8. Bad input: non-string path raises TypeError
try:
    node.run(123, "csv")
    raise AssertionError("expected TypeError for non-string path")
except TypeError:
    pass

# 9. Bad input: invalid JSON raises
try:
    node.run("{not json", "json")
    raise AssertionError("expected error for invalid JSON")
except Exception:
    pass

# 10. Module-level mappings exist and are consistent
assert "PSN_Dataset_Loader" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_Dataset_Loader"] is PSN_Dataset_Loader
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Dataset_Loader"] == "PSN Dataset Loader"

# 11. Node contract: INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY
it = PSN_Dataset_Loader.INPUT_TYPES()
assert "dataset_path" in it["required"]
assert "format" in it["required"]
assert PSN_Dataset_Loader.RETURN_TYPES == (DATASET, "STRING")
assert PSN_Dataset_Loader.FUNCTION == "run"
assert PSN_Dataset_Loader.CATEGORY.startswith("ParametricStudio/")

# 12. CSV with ragged rows: missing cells become empty strings
out, _ = node.run("a,b,c\n1,2", "csv")
assert out["records"][0] == {"a": "1", "b": "2", "c": ""}

# 13. A real file path is read, not parsed as text
import os, tempfile
with tempfile.TemporaryDirectory() as d:
    csv_path = os.path.join(d, "data.csv")
    with open(csv_path, "w", encoding="utf-8") as fh:
        fh.write("name,age\nAlice,30\nBob,25\nCy,41\n")
    out, meta = node.run(csv_path, "csv")
    assert out["num_records"] == 3, out
    assert out["records"][2] == {"name": "Cy", "age": "41"}
    assert json.loads(meta)["source_kind"] == "file"

    json_path = os.path.join(d, "data.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        fh.write('[{"a": 1}, {"a": 2}]')
    out, _ = node.run(json_path, "json")
    assert out["records"] == [{"a": 1}, {"a": 2}]

    # 14. A directory with format folder lists sorted file names (subdirs skipped)
    folder = os.path.join(d, "imgs")
    os.mkdir(folder)
    os.mkdir(os.path.join(folder, "sub"))
    for n in ("b.png", "a.png", "c.txt"):
        open(os.path.join(folder, n), "w").close()
    out, meta = node.run(folder, "folder")
    assert [r["path"] for r in out["records"]] == [os.path.join(folder, n) for n in ("a.png", "b.png", "c.txt")]
    assert json.loads(meta)["source_kind"] == "directory"

    # 15. A directory with a text format raises instead of parsing the path as text
    try:
        node.run(folder, "csv")
        raise AssertionError("expected ValueError for directory with csv")
    except ValueError:
        pass

    # 16. A file path in folder format holds one path per line
    lst = os.path.join(d, "list.txt")
    with open(lst, "w", encoding="utf-8") as fh:
        fh.write("/x/1.png\n/x/2.png\n")
    out, _ = node.run(lst, "folder")
    assert [r["path"] for r in out["records"]] == ["/x/1.png", "/x/2.png"]

# 17. Inline text still works and is labelled as such
out, meta = node.run("k\nv", "csv")
assert json.loads(meta)["source_kind"] == "inline_text" and out["records"] == [{"k": "v"}]

print("ok")

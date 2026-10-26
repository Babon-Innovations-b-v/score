"""The copy of a seed a layer is written over takes a save, though the store's seed is read-only and copies keep its
modes (layer_base.py `writable`).

Break that turns it red (applied once and seen red, then reverted):
- `writable`: its chmod left out (the function body made `return`)  -> a PermissionError on the save.
"""
from score.stages import layer_base


def test_a_built_layer_copy_of_a_read_only_seed_is_writable(tmp_path):
    folder = tmp_path / "seed"
    (folder / "layers").mkdir(parents=True)
    (folder / "layers" / "base.usda").write_text("#usda 1.0\n")
    for path in (folder / "layers" / "base.usda", folder / "layers", folder):
        path.chmod(0o555 if path.is_dir() else 0o444)
    layer_base.writable(folder)
    (folder / "layers" / "base.usda").write_text("#usda 1.0\n")
    (folder / "layers" / "new.usda").write_text("#usda 1.0\n")

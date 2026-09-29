"""Checks the glTF writer, with the system python and nothing installed.

Run by the gate (`tools/test/run.sh`), which has no numpy and no tool chain built, so nothing
here may import either.
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import glb  # noqa: E402

BARE = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}]}


def check(what, got, wanted):
    if got != wanted:
        raise AssertionError(f"{what}: got {got!r}, wanted {wanted!r}")


def refused(document):
    """Whether the writer turned this document away, and what it said."""
    try:
        glb.refuse_a_tangled_graph(document)
    except ValueError as complaint:
        return str(complaint)
    return ""


def a_node_cannot_be_its_own_child():
    """The fault that cost fifteen minutes of Godot at full tilt on #36."""
    check("its own child", refused({"nodes": [{"children": [0]}]}) != "", True)


def a_node_cannot_have_two_parents():
    check("two parents", refused({"nodes": [{"children": [2]}, {"children": [2]}, {}]}) != "", True)


def a_ring_of_nodes_is_refused():
    ring = {"nodes": [{"children": [1]}, {"children": [2]}, {"children": [0]}]}
    check("a ring", refused(ring) != "", True)


def a_plain_tree_is_let_through():
    check("a tree", refused({"nodes": [{"children": [1, 2]}, {"children": [3]}, {}, {}]}), "")


def the_numbers_come_back_out_as_they_went_in():
    contents = glb.Contents()
    where = contents.reading([0.0, 0.0, 0.0, 1.0, 2.0, 3.0], "VEC3", glb.FLOAT,
                             glb.ARRAY_BUFFER, with_bounds=True)
    contents.reading([0, 1, 2], "SCALAR", glb.UNSIGNED_SHORT, glb.ELEMENT_ARRAY_BUFFER)
    out = pathlib.Path(tempfile.mkdtemp()) / "one.glb"
    glb.write(out, dict(BARE, nodes=[{"name": "one"}]), contents)
    read = glb.read_document(out)
    check("two ways of reading", len(read["accessors"]), 2)
    check("how many vectors", read["accessors"][where]["count"], 2)
    check("smallest", read["accessors"][where]["min"], [0.0, 0.0, 0.0])
    check("largest", read["accessors"][where]["max"], [1.0, 2.0, 3.0])
    check("the node kept its name", read["nodes"][0]["name"], "one")


def a_picture_is_kept_byte_for_byte_and_named_as_an_image():
    contents = glb.Contents()
    contents.reading([0.0, 0.0, 0.0], "VEC3", glb.FLOAT)
    encoded = b"\x89PNG not really, but five bytes past the header"
    image = contents.picture(encoded)
    out = pathlib.Path(tempfile.mkdtemp()) / "pictured.glb"
    glb.write(out, dict(BARE, nodes=[{"name": "one"}]), contents)
    read = glb.read_document(out)
    view = read["bufferViews"][read["images"][image]["bufferView"]]
    check("the picture's type", read["images"][image]["mimeType"], "image/png")
    check("the picture's length", view["byteLength"], len(encoded))
    check("the picture starts on a four-byte boundary", view["byteOffset"] % 4, 0)


def a_run_of_numbers_that_does_not_divide_is_refused():
    try:
        glb.Contents().reading([1.0, 2.0], "VEC3", glb.FLOAT)
    except ValueError:
        return
    raise AssertionError("two numbers were accepted as a run of three-number vectors")


def main():
    for name, run_this in sorted(globals().items()):
        if name.startswith(("a_", "the_")) and callable(run_this):
            run_this()
    print("glb: green")


main()

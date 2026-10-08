"""Runs inside Blender: puts ProcFunc, infinigen2's shaders and the library on the path, and lets ProcFunc (written
for Blender 4.2) find the sockets Blender 5 renamed.

    import runtime; runtime.ready()

ProcFunc pins bpy 4.2; the Blender here is 5.0.1, where a few node outputs were renamed (the noise texture's and the
colour ramp's `Fac` is now `Factor`). Rather than edit the vendored copy, which stays as released, its socket lookup
is wrapped: a name it cannot find is tried once more under its Blender 5 name. pandas, which ProcFunc imports, is not
in Blender's own Python: ../../cloud/library_setup.sh installs it beside Blender, in PROPS_HOME's blender-mcp/pf-site.
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[3]
PROPS_HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
SITE = PROPS_HOME / "blender-mcp" / "pf-site"
PATHS = [SITE, REPO / "vendor/procfunc/src", REPO / "vendor/infinigen2/src", HERE.parent, HERE]
# Blender 4.2 socket names ProcFunc uses -> their Blender 5 names.
RENAMED = {"fac": "factor"}


def ready():
    """Make `import procfunc`, `import infinigen2.shaders` and `import recipes` work in this Blender."""
    for path in reversed(PATHS):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    import procfunc.nodes.execute.util as lookup

    if getattr(lookup.get_nth_socket, "blender5", False):
        return
    original = lookup.get_nth_socket

    def nth_socket(sockets, socket_name, index, debug_node_name=""):
        try:
            return original(sockets, socket_name, index, debug_node_name)
        except ValueError:
            if socket_name.lower() not in RENAMED:
                raise
            return original(sockets, RENAMED[socket_name.lower()], index, debug_node_name)

    nth_socket.blender5 = True
    for module in list(sys.modules.values()):
        if getattr(module, "get_nth_socket", None) is original:
            module.get_nth_socket = nth_socket

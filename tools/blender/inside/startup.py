"""Runs inside Blender at launch (session.py): installs and enables the MCP add-on, which then
starts listening on FARM_BLENDER_PORT from its own interface timer.

The add-on goes into this Blender's own user folder (BLENDER_USER_RESOURCES, set by session.py),
so nothing touches another Blender's settings. Its telemetry consent stays off, the default, and
DISABLE_TELEMETRY is set as well.
"""
import os

import bpy

ADDON = os.environ["FARM_BLENDER_ADDON"]
PORT = int(os.environ["FARM_BLENDER_PORT"])


def enable_addon():
    bpy.ops.preferences.addon_install(filepath=ADDON, overwrite=True)
    bpy.ops.preferences.addon_enable(module="addon")
    bpy.context.preferences.addons["addon"].preferences.telemetry_consent = False


def listen_on_port():
    """The add-on reads its port from the scene when its start timer fires, half a second on."""
    bpy.context.scene.blendermcp_port = PORT
    bpy.context.scene.blendermcp_auto_start_server = True


enable_addon()
listen_on_port()
print(f"farm-factory: Blender {bpy.app.version_string}, MCP add-on on port {PORT}", flush=True)

"""The world files of the turntable and SegviGen rows: their scripts and the place's takes' raw files. A module of its
own, so these paid rows' code version is their own modules and this one: neither this folder's __init__.py (which
imports the whole line, place_line.py's paint, bake and check) nor a module the free rows import (segvigen_row.py
is in the inputs', maps' and names' code version, so editing it would re-draw every map).
"""
import surface_data
import segvigen_row
import turntable_row


def turntable_files(place):
    return {**turntable_row.FILES, **surface_data.take_files(place)}


def segvigen_files(place):
    return {**segvigen_row.FILES, **surface_data.take_files(place)}

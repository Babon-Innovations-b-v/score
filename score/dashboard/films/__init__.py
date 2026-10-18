"""The film script (CONTEXT.md): a demo film written as data in the creator cockpit, played there for free on the
places' 3D web copies and existing films, and compiled to render items priced before anything is bought.

One JSON file a film. The repository's copy, `data/films/<film>.json`, is the starter; the cockpit saves the creator's
edits to `$SCORE_DASHBOARD_HOME/films/<film>.json`, which is read first. No stage reads either file today, so neither
moves a key.

    {"format": "score-film-script", "version": 1, "film": "k9", "title": "World 1: 2099", "world": "world1",
     "target_seconds": 180, "size": [1280, 720], "rate": 24, "why": "...",
     "defaults": {<cut>: seconds},                 # the creator's own default lengths, over script.CUTS'
     "segments": [{
        "cut": "walk-through",                     # one of script.CUTS
        "shows": {"place": "hub"},                 # {"world"} | {"place"} and, by cut, "layer", "part", "step", "film"
        "seconds": 3.5,                            # absent: the default of its cut
        "transition": "cross-fade",                # into this segment: cut, cross-fade, fade-through-black, push
        "sound": "place",                          # place (its film's own track), bed (the nearest film's sound
                                                   # carried under), silence
        "camera": "wide-north",                    # optional: a camera of the place's scene record
        "text": "The hub", "line": "The Moon base" # optional: the words on it
     }]}

The render hook (for tools/review/showcase.py and the demo-film rows, which read the file as plain JSON and never
import this package): each segment in order, its length `seconds` (else `defaults`, else CUTS), joined with
TRANSITION_SECONDS of overlap where the transition is a cross-fade or a push. render.py says which segment reuses what
already exists (an accepted demo-film's shot from FILM_SHOT_FROM, the step's pictures) and which needs new frames.
"""

"""A screen take's script (CONTEXT.md "screen take"): the page it opens (`shows.page`, a cockpit path) and its steps on
the segment's own clock, played the same way every time by films/preview/recorder.mjs.

    "take": [{"at": 0.4, "do": "move", "on": "#pick", "over": 0.8},     # the cursor glides to an element
             {"at": 1.4, "do": "click", "on": ".draws img:nth-child(3)"},# a click: never one that spends (below)
             {"at": 2.0, "do": "drag", "on": "#picture", "from": [0.3, 0.3], "to": [0.6, 0.55], "over": 0.8},
             {"at": 3.0, "do": "type", "on": "#note", "text": "taller dome", "over": 1.2},
             {"at": 4.0, "do": "box", "on": "#draw", "for": 1.5, "words": "Redraw with notes"},  # a highlight
             {"at": 5.0, "do": "scroll", "on": ".plan", "over": 0.8},    # the element brought to the middle
             {"at": 6.0, "do": "goto", "page": "/plan/hub/"}]            # another page, as a link would

`on` is a CSS selector, `from`/`to` shares of that element's box. A take never spends: the recorder refuses the whole
take when a click lands on a button that posts a form, names a price (EUR) or carries a spend word (SPEND_WORDS), and
it aborts every request that is not a GET, so a take cannot change anything either. Typing never presses Enter.
"""
import re

DOES = ("move", "click", "drag", "type", "box", "scroll", "goto", "hover")
# The words on the cockpit's buttons that spend or decide (concept review, plans, buy, environment concept); read by
# the recorder against the clicked element's own text and title.
SPEND_WORDS = ("draw", "redraw", "pick", "unlock", "lock", "buy", "send", "save", "keep", "take", "write",
               "make plan", "correct", "queue", "launch", "checkout", "accept", "read back", "approve")
SPEND = re.compile(r"\b(" + "|".join(re.escape(word) for word in SPEND_WORDS) + r")\b|EUR|€", re.IGNORECASE)


def step_faults(number, index, step):
    """What is wrong with one step of a take, in words."""
    where = f"segment {number} step {index}"
    if not isinstance(step, dict) or step.get("do") not in DOES:
        return [f"{where}: no step {step.get('do') if isinstance(step, dict) else step!r}"]
    found = []
    if not isinstance(step.get("at"), (int, float)) or step["at"] < 0:
        found.append(f"{where}: its time `at` is a number of seconds")
    if step["do"] == "goto" and not str(step.get("page", "")).startswith("/"):
        found.append(f"{where}: goto names a cockpit page (a path from /)")
    if step["do"] not in ("goto", "scroll") and not step.get("on"):
        found.append(f"{where}: {step['do']} names the element it is `on`")
    if step["do"] == "type" and "\n" in str(step.get("text", "")):
        found.append(f"{where}: typing never presses Enter (it could send a form)")
    if step["do"] == "click" and SPEND.search(str(step.get("words", ""))):
        found.append(f"{where}: refused, it clicks {step['words']!r}: a take never clicks a button that spends")
    return found


def faults(number, segment):
    """What is wrong with a screen take's segment: its page and every step."""
    page = (segment.get("shows") or {}).get("page", "")
    found = [] if str(page).startswith("/") else [f"segment {number}: a screen take opens a cockpit page (a path)"]
    steps = segment.get("take", [])
    if not isinstance(steps, list):
        return found + [f"segment {number}: its take is a list of steps"]
    return found + [fault for index, step in enumerate(steps, 1) for fault in step_faults(number, index, step)]

"""The Library's folders: each kind, then the categories inside it, built from the entries themselves.

    folders(entries)  # {"tree": [kind node, ...], "members": {node id: [entry, ...]}}

A node is {id, label, count, children}; its id is the path of keys from the kind down ("model/piece/wall"). Inside a
kind the entries are split first by the tags that name what they are (a model's type, a surface's family then its
recipe, a sound's category, ...), skipping a level that would make one folder; a folder still larger than LEAF_MAX is
split by the words of the entries' names (wall, wall upper, ...), and one whose names are all the same by the place
each came from. Groups smaller than GROUP_MIN go together in "Other". The Places shelf is a folder a place, its
root and its own layers in it.
"""
import re

from score.dashboard.state.library import KINDS, kind_label
from score.dashboard.state.names import everyday

TAG_LEVELS = {"model": ["model"], "surface": ["family", "recipe"], "sound": ["category"], "effect": ["effect"],
              "character": ["character"]}
PLURAL_TAGS = {"model"}  # a model's type reads as a folder of many: Pieces, Props
LEAF_MAX = 36
SPLIT_MORE = 12  # a folder made by a tag is split by the next tag only when it holds more than this
GROUP_MIN = 3
MAX_WORDS = 4
OTHER = "other"
UNTAGGED = "untagged"
NUMBERED = re.compile(r"(_\d+)+$")


def name_words(entry):
    """The words of an entry's name without its place and number: `ac_unit_1.square` -> ["ac", "unit"]."""
    return NUMBERED.sub("", entry.entry_id.split(".")[0]).split("_")


def words_key(entry, count):
    return "_".join(name_words(entry)[:count])


def tag_key(entry, tag):
    values = entry.tags.get(tag) or []
    return str(values[0]) if values else UNTAGGED


def label_of(key):
    return "Other" if key == OTHER else everyday(key.replace("_", " ").capitalize())


def tag_label(tag, key):
    said = label_of(key)
    return said + "s" if tag in PLURAL_TAGS and key != UNTAGGED else said


def grouped(entries, key_of):
    """{key: [entry, ...]} in the entries' order."""
    groups = {}
    for entry in entries:
        groups.setdefault(key_of(entry), []).append(entry)
    return groups


def in_order(groups):
    """Folders by name, Other and untagged last."""
    return sorted(groups.items(), key=lambda item: (item[0] in (OTHER, UNTAGGED), item[0]))


def small_ones_together(groups):
    """Groups smaller than GROUP_MIN merged into Other; {} when nothing would be left but Other."""
    kept = {key: members for key, members in groups.items() if len(members) >= GROUP_MIN}
    rest = [entry for key, members in groups.items() if len(members) < GROUP_MIN for entry in members]
    if not kept:
        return {}
    return {**kept, OTHER: rest} if rest else kept


def word_groups(entries, used):
    """(groups, words used) by the fewest further name words that split these entries; ({}, used) when none does."""
    for count in range(used + 1, MAX_WORDS + 1):
        groups = grouped(entries, lambda entry, count=count: words_key(entry, count))
        if len(groups) > 1:
            return groups, count
    return {}, used


class Builder:
    """Builds the tree, keeping every node's entries by id."""

    def __init__(self):
        self.members = {}

    def node(self, node_id, label, entries, children):
        self.members[node_id] = entries
        return {"id": node_id, "label": label, "count": len(entries), "children": children}

    def by_tags(self, parent, entries, tags):
        """Folders by the first tag level that splits, then by name; the leaves' list when none does."""
        for depth, tag in enumerate(tags):
            groups = grouped(entries, lambda entry, tag=tag: tag_key(entry, tag))
            if len(groups) > 1:
                return [self.node(f"{parent}/{key}", tag_label(tag, key), members, self.inside_tag(
                    f"{parent}/{key}", members, tags[depth + 1:])) for key, members in in_order(groups)]
        return self.by_name(parent, entries, 0)

    def inside_tag(self, node_id, entries, tags):
        """A tag's folder: split by the next tags when it is large enough to need it, else by name."""
        return self.by_tags(node_id, entries, tags if len(entries) > SPLIT_MORE else [])

    def by_name(self, parent, entries, used):
        """Folders by name words, then by place; none for a folder small enough to list."""
        if len(entries) <= LEAF_MAX:
            return []
        groups, used = word_groups(entries, used)
        if not groups:
            return self.by_place(parent, entries)
        return [self.node(f"{parent}/{key}", label_of(key), members,
                          [] if key == OTHER else self.by_name(f"{parent}/{key}", members, used))
                for key, members in in_order(small_ones_together(groups))]

    def by_own_place(self, parent, entries):
        """The Places shelf: a folder a place, holding its root and its own layers (`<layer>.<place>`)."""
        groups = grouped(entries, lambda entry: entry.entry_id.split(".")[-1])
        return [self.node(f"{parent}/{key}", label_of(key), members, []) for key, members in sorted(groups.items())]

    def by_place(self, parent, entries):
        groups = small_ones_together(grouped(entries, lambda entry: entry.place or OTHER))
        return [self.node(f"{parent}/@{key}", f"from {label_of(key).lower()}" if key != OTHER else "Other places",
                          members, []) for key, members in in_order(groups)]


def folders(entries):
    """The Library's tree of kinds and categories, and each node's entries."""
    builder = Builder()
    tree = []
    for kind, _ in KINDS:
        of_kind = [entry for entry in entries if (entry.shelf or entry.kind) == kind]
        if of_kind:
            children = builder.by_own_place(kind, of_kind) if kind == "place" else \
                builder.by_tags(kind, of_kind, TAG_LEVELS.get(kind, []))
            tree.append(builder.node(kind, kind_label(kind), of_kind, children))
    return {"tree": tree, "members": builder.members}

"""The Library screen's JSON under /api/library: a branch's children a page at a time, and the owner's choices (lock or
withdraw, and refine items into the basket). What each answer holds is made in pages/library.py."""
from django.db import IntegrityError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from score.dashboard.api.deps import owner_only, signed_in
from score.dashboard.pages import actions, library_actions
from score.dashboard.pages import library as pages
from score.dashboard.pages.models import RefineItem, is_owner
from score.dashboard.state import library as lib

library_api = APIRouter()


class ChoiceIn(BaseModel):
    action: str
    addresses: list[str] = []
    address: str = ""  # one entry, from its page's form

    def chosen(self):
        return [*self.addresses, self.address] if self.address else self.addresses


class RefineIn(ChoiceIn):
    action: str = "refine"
    option: str = ""


def shown():
    found = lib.library()
    if found is None:
        raise HTTPException(404, "no library here")
    return found


@library_api.get("/children")
def branch(node: str, page: int = 0, user=Depends(signed_in)):
    """One page of a folder's children as tree nodes (templates/pages/c/tree.html), loaded when its branch opens."""
    found = pages.children(shown(), node, max(page, 0))
    if found is None:
        raise HTTPException(404, f"no folder {node}")
    return found


@library_api.post("/ask")
def ask(body: ChoiceIn, user=Depends(owner_only)):
    """The owner's lock or withdraw of the chosen entries (pages/library_actions.py)."""
    return {"said": library_actions.ask(user.username, body.action, body.chosen(), actions.hosted())}


def refine_refusal(library, addresses, option):
    """Why these entries cannot go into the basket as refine items with this option, or None."""
    if not addresses:
        return "nothing chosen"
    for address in addresses:
        found = library.entry(address)
        if found is None:
            return f"{address} is not in the library"
        if option and option not in {choice["id"] for choice in found.refine_options}:
            return f"{found.title} has no refine option {option!r}"
    return None


def added_refine(address, option, user):
    """True when the refine item is new in the basket."""
    try:
        _, made = RefineItem.objects.get_or_create(address=address, option=option, defaults={"added_by": user})
    except IntegrityError:
        return False
    return made


@library_api.post("/refine")
def refine(body: RefineIn, user=Depends(owner_only)):
    """The chosen entries into the basket as refine items (owner only)."""
    addresses = sorted(set(body.chosen()))
    why = refine_refusal(shown(), addresses, body.option)
    if why:
        raise HTTPException(400, why)
    added = sum(added_refine(address, body.option, user.username) for address in addresses)
    return {"said": f"{added} refine item{'' if added == 1 else 's'} added to the basket", "added": added,
            "in_basket": RefineItem.objects.count()}

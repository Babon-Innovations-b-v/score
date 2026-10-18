"""The basket and checkout API under /api/checkout (one sign-in with the pages, CSRF on every write: api/deps.py).

    GET    /api/checkout/offers               every fix branch on offer, priced                     signed in
    POST   /api/checkout/offers/{branch}/price  start pricing the branch's commit now               owner
    GET    /api/checkout/basket               the basket's items and totals                         owner
    POST   /api/checkout/basket               {branch, preview_hash}: add it as seen                 owner
    DELETE /api/checkout/basket/{branch}      take it out                                            owner
    POST   /api/checkout                      {key, confirmed}: the one checkout (same key: same one) owner
    GET    /api/checkout/{checkout_id}        the checkout's state                                   signed in
    GET    /api/checkout/{checkout_id}/results  per item: real cost against forecast, gates, outputs signed in
"""
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from score.dashboard.api.deps import owner_only, signed_in
from score.dashboard.checkout import flow, pricing, results
from score.dashboard.pages.models import Checkout

checkout = APIRouter()
BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


class Said(BaseModel):
    said: str


class AddIn(BaseModel):
    branch: str
    preview_hash: str


class CheckoutIn(BaseModel):
    key: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    confirmed: bool = False


class CheckoutOut(BaseModel):
    id: int
    by: str
    at: str
    state: str
    detail: str
    items: list
    totals: dict
    landed: list
    main_before: str
    main_after: str
    stop_line: dict
    launch: int | None


class Started(BaseModel):
    said: str
    checkout: CheckoutOut | None


def checkout_out(record):
    return CheckoutOut(id=record.pk, by=record.by, at=record.at.isoformat(), state=record.state, detail=record.detail,
                       items=record.items, totals=record.totals, landed=record.landed, main_before=record.main_before,
                       main_after=record.main_after, stop_line=record.stop_line, launch=record.launch_id)


def checked_branch(branch):
    """The branch name, 404 when it is not a plain branch name or no such branch is on offer."""
    if not BRANCH.match(branch) or ".." in branch:
        raise HTTPException(404, "no such branch")
    try:
        return flow.offer(branch)["branch"]
    except RuntimeError:
        raise HTTPException(404, "no such branch")


def found_checkout(checkout_id):
    record = Checkout.objects.filter(pk=checkout_id).first()
    if record is None:
        raise HTTPException(404, "no such checkout")
    return record


@checkout.get("/offers")
def offer_list(user=Depends(signed_in)) -> list[dict]:
    return flow.offers()


@checkout.post("/offers/{branch}/price", response_model=Said)
def offer_price(branch: str, user=Depends(owner_only)):
    record = pricing.start(checked_branch(branch))
    return Said(said=f"{branch}: {record.state}")


@checkout.get("/basket")
def basket_read(user=Depends(owner_only)) -> dict:
    return flow.basket()


@checkout.post("/basket", response_model=Said)
def basket_add(body: AddIn, user=Depends(owner_only)):
    return Said(said=flow.add(user.username, checked_branch(body.branch), body.preview_hash))


@checkout.delete("/basket/{branch}", response_model=Said)
def basket_remove(branch: str, user=Depends(owner_only)):
    return Said(said=flow.remove(branch))


@checkout.post("", response_model=Started)
def checkout_start(body: CheckoutIn, user=Depends(owner_only)):
    record, said = flow.start(user, body.key, body.confirmed)
    return Started(said=said, checkout=checkout_out(record) if record else None)


@checkout.get("/{checkout_id}", response_model=CheckoutOut)
def checkout_read(checkout_id: int, user=Depends(signed_in)):
    return checkout_out(found_checkout(checkout_id))


@checkout.get("/{checkout_id}/results")
def checkout_results(checkout_id: int, user=Depends(signed_in)) -> dict:
    return results.results(found_checkout(checkout_id))

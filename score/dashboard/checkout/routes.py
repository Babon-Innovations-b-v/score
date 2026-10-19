"""The checkout API under /api/checkout (one sign-in with the pages, CSRF on every write: api/deps.py).

    POST   /api/checkout                      {key, confirmed}: the one checkout of the items he chose   owner
    GET    /api/checkout/{checkout_id}        the checkout's state                                       signed in
    GET    /api/checkout/{checkout_id}/results  per item: real cost against forecast, gates, outputs     signed in
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from score.dashboard.api.deps import owner_only, signed_in
from score.dashboard.checkout import flow, results
from score.dashboard.pages.models import BasketChoice, Checkout

checkout = APIRouter()


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
    stop_line: dict
    launch: int | None


class Started(BaseModel):
    said: str
    checkout: CheckoutOut | None


def checkout_out(record):
    return CheckoutOut(id=record.pk, by=record.by, at=record.at.isoformat(), state=record.state, detail=record.detail,
                       items=record.items, totals=record.totals, stop_line=record.stop_line,
                       launch=record.launch_id)


def found_checkout(checkout_id):
    record = Checkout.objects.filter(pk=checkout_id).first()
    if record is None:
        raise HTTPException(404, "no such checkout")
    return record


@checkout.post("", response_model=Started)
def checkout_start(body: CheckoutIn, user=Depends(owner_only)):
    seen = [{"id": choice.item, "version": choice.version} for choice in BasketChoice.objects.filter(choice="buy")]
    record, said = flow.start(user, body.key, body.confirmed, seen)
    return Started(said=said, checkout=checkout_out(record) if record else None)


@checkout.get("/{checkout_id}", response_model=CheckoutOut)
def checkout_read(checkout_id: int, user=Depends(signed_in)):
    return checkout_out(found_checkout(checkout_id))


@checkout.get("/{checkout_id}/results")
def checkout_results(checkout_id: int, user=Depends(signed_in)) -> dict:
    return results.results(found_checkout(checkout_id))

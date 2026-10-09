"""The cloud layer's one interface: the runners rent machines by capability class through it and never name a
provider, a machine type, a zone or a price themselves.

The backend is chosen by SCORE_CLOUD (default `scaleway`, the backend the framework runs on today) and lives in
`backends/<name>.py`. A backend is a module that gives:

    NAME                                   its name, as in SCORE_CLOUD
    CLASSES                                {capability class: (its machine types, tried in this order)}
    QUOTAS                                 {capability class: machines the account may hold at once}, where known
    account()                              the account it rents in, checked to be the configured one
    offers(classes)                        every Offer for those classes, in every region it rents from
    price(machine_type, zone)              (euros a minute, the minutes it is billed by)
    month_spend(account)                   what the provider has billed the account this month, in euros
    allow_key(account, name, public_key)   let the runner's ssh key into new machines
    create(account, offer, name, tags, disk_gb)  rent and start one: (its id, None) or (None, the refusal)
    start_if_stopped(machine_id, zone)     start a machine left stopped; the refusal, or None
    address(machine_id, zone)              its public address, or None while it has none
    delete(machine_id, zone)               delete it with its disk and address; True if it was there
    ours(account)                          every machine the runner rented: (id, zone, name, tags), each checked
                                           to belong to the account by its own record
    leftover_addresses(account), leftover_disks(account), delete_address(id, zone), delete_disk(id, zone)
    secret(name)                           a secret's value from the provider's secret store, never printed
    registry()                             the private image registry the job images are pushed to and pulled from:
                                           {"endpoint": "<host>/<namespace>", "username": ..., "password": ...},
                                           made once if missing, credentials read at run time (tools/cloud/images/)
    object_store()                         the S3 bucket for the weights cache, code bundles and job inputs and
                                           outputs: {"endpoint", "region", "bucket", "access_key", "secret_key"},
                                           made once if missing, credentials read at run time (tools/cloud/runtime/)

The machine itself runs `self_delete.py`, which needs the backend's own way to ask who it is and to delete itself
(its BACKENDS table). Running a command and copying files go over ssh and rsync (batch.remote, batch.copy), the same
on every provider. The section "Add a cloud backend" of the README says how to add one.

A capability class names what a job needs, not a product: `gpu-<GB>gb` is one card with that much memory,
`gpu-<GB>gb-x<N>` a machine with N of them, `cpu-<cores>c-<GB>gb` a processor machine with no card.
"""
import collections
import importlib
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "backends"))

# Where a machine of a class can be rented: euros a card a minute, the stock rank (0 best), the backend's machine
# type, its zone, euros a minute, the capability class, its place in the class's list of types, and the stock word.
Offer = collections.namedtuple("Offer", "per_card stock type zone price machine_class order stock_word")

GPU = re.compile(r"gpu-(\d+)gb(?:-x(\d+))?$")
CPU = re.compile(r"cpu-(\d+)c-(\d+)gb$")


def cards(machine_class):
    """How many cards a machine of the class has; 0 for a processor machine."""
    found = GPU.match(machine_class)
    if found:
        return int(found.group(2) or 1)
    if CPU.match(machine_class):
        return 0
    raise SystemExit(f"'{machine_class}' is not a capability class (gpu-<GB>gb[-x<N>] or cpu-<cores>c-<GB>gb)")


def card_gb(machine_class):
    """The memory of one card of the class in GB; 0 for a processor machine."""
    found = GPU.match(machine_class)
    return int(found.group(1)) if found else 0


def load(name=None):
    """The backend module named `name`, else SCORE_CLOUD's, else Scaleway."""
    return importlib.import_module(name or os.environ.get("SCORE_CLOUD", "scaleway"))


cloud = load()

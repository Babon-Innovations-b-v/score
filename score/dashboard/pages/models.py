"""The dashboard's own records, in its SQLite only: never a mirror of the store's state."""
from django.conf import settings
from django.db import models


class ChangeRequest(models.Model):
    """What a signed-in user said should change about a step's output, recorded for an agent or the owner."""

    user = models.CharField(max_length=150)
    place = models.CharField(max_length=100, blank=True)
    stage = models.CharField(max_length=100)
    node = models.CharField(max_length=200)
    output_seen = models.CharField(max_length=64, blank=True)
    words = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=30, default="recorded")
    detail = models.TextField(blank=True)

    class Meta:
        ordering = ["-created"]


class BasketItem(models.Model):
    """One step queued for a launch: a place's stage, or an environment stage (place empty)."""

    place = models.CharField(max_length=100, blank=True)
    stage = models.CharField(max_length=100)
    added_by = models.CharField(max_length=150)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["place", "stage"]
        constraints = [models.UniqueConstraint(fields=["place", "stage"], name="one_basket_item_a_step")]


class RefineItem(models.Model):
    """One library entry the owner chose to have made better: its address and the refine option (empty: as its
    scoring suggests). Not priced or launched yet: no refine step exists to buy."""

    address = models.CharField(max_length=200)
    option = models.CharField(max_length=100, blank=True)
    added_by = models.CharField(max_length=150)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["address", "option"]
        constraints = [models.UniqueConstraint(fields=["address", "option"], name="one_refine_item_an_option")]


class Plan(models.Model):
    """A worked-out plan of the basket: the runner's plan per group, the money and time against the stop."""

    basket_hash = models.CharField(max_length=64)
    made_by = models.CharField(max_length=150)
    started = models.DateTimeField(auto_now_add=True)
    finished = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=20, default="working")  # working, ready, failed
    body = models.JSONField(default=dict)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-started"]


class Launch(models.Model):
    """One launch of a plan's groups through the compute backend."""

    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="launches")
    by = models.CharField(max_length=150)
    at = models.DateTimeField(auto_now_add=True)
    jobs = models.PositiveIntegerField(default=8)
    rebuy_reason = models.TextField(blank=True)
    state = models.CharField(max_length=30, default="starting")  # starting, running, done, failed, stopped, refused
    handles = models.JSONField(default=list)  # [{command, pid, log, state, output}]
    result = models.TextField(blank=True)

    class Meta:
        ordering = ["-at"]


class SyncRequest(models.Model):
    """A hosted request for the store's machine: a change request, a decision or a launch basket."""

    kind = models.CharField(max_length=20)  # change, decision, launch
    payload = models.JSONField(default=dict)
    user = models.CharField(max_length=150)
    created = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=20, default="waiting")  # waiting, picked_up, running, done, refused
    detail = models.TextField(blank=True)
    log_tail = models.TextField(blank=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]


class Seen(models.Model):
    """The owner looked at one output of a step (opening its page while it was the shown output), and, when
    `advanced`, pressed advance: the paid steps after it may then be launched. Only his signed-in session writes it."""

    node = models.CharField(max_length=200)
    output = models.CharField(max_length=64)
    user = models.CharField(max_length=150)
    at = models.DateTimeField(auto_now_add=True)
    advanced = models.BooleanField(default=False)

    class Meta:
        ordering = ["-at"]
        indexes = [models.Index(fields=["node", "output"])]


class Checkout(models.Model):
    """The owner's one checkout of the basket: his money yes for the items he bought, the stop line, the batch."""

    key = models.CharField(max_length=64, unique=True)  # the page's own key: a second press is the same checkout
    by = models.CharField(max_length=150)
    at = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=20, default="launching")  # launching, launched, done, refused, failed
    items = models.JSONField(default=list)  # [{id, version, place, layers, nodes: {node: price}, totals}]
    totals = models.JSONField(default=dict)
    stop_line = models.JSONField(default=dict)
    before = models.JSONField(default=dict)  # {node: accepted output at checkout}
    launch = models.ForeignKey(Launch, null=True, blank=True, on_delete=models.PROTECT, related_name="checkouts")
    detail = models.TextField(blank=True)
    pid = models.IntegerField(null=True, blank=True)  # the process running it while launching: gone, it failed
    design_at = models.CharField(max_length=32, blank=True)  # when the design last changed as it was made: a new batch

    class Meta:
        ordering = ["-at"]


class BasketChoice(models.Model):
    """The owner's answer to one basket item: buy it, or not now, as he saw it (its version). His checkout buys the
    items he chose to buy."""

    item = models.CharField(max_length=100, unique=True)
    version = models.CharField(max_length=64)
    choice = models.CharField(max_length=10)  # buy, later
    by = models.CharField(max_length=150)
    at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["item"]


class BasketAnswer(models.Model):
    """The owner's answer to one question of a basket item (its number among the item's questions, and the question
    as he read it). Agents read the answers from the basket's answers.json on the store's machine."""

    item = models.CharField(max_length=100)
    number = models.PositiveIntegerField()
    question = models.TextField()
    answer = models.TextField()
    by = models.CharField(max_length=150)
    at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["item", "number"]
        constraints = [models.UniqueConstraint(fields=["item", "number"], name="one_answer_a_question")]


def is_owner(user):
    """True for the signed-in owner (SCORE_OWNER)."""
    return bool(user and user.is_authenticated and settings.SCORE_OWNER and user.username == settings.SCORE_OWNER)

"""The dashboard's Django app: its pages, its own records (change requests, basket, plans, launches, sync requests)."""
from django.apps import AppConfig


class PagesConfig(AppConfig):
    name = "score.dashboard.pages"
    label = "dashboard"
    verbose_name = "SCORE dashboard"
    default_auto_field = "django.db.models.BigAutoField"

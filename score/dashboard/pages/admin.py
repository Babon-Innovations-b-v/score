"""The admin for the dashboard's own records (owner only: the admin's own staff check, the owner is its superuser)."""
from django.contrib import admin

from score.dashboard.pages.models import BasketItem, ChangeRequest, Launch, Plan, Seen, SyncRequest

for model in (ChangeRequest, BasketItem, Plan, Launch, SyncRequest, Seen):
    admin.site.register(model)

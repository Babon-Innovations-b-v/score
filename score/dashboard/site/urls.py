"""The dashboard's page URLs (Django). /api, /files, /thumbs, /web, /static and /healthz are the ASGI app's
(site/asgi.py)."""
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from score.dashboard.pages import films, library, views

STEP_ROUTES = [("", views.step_page), ("request/", views.step_request), ("decide/", views.step_decide),
               ("queue/", views.step_queue), ("advance/", views.step_advance)]

urlpatterns = [
    path("", views.board),
    path("place/<slug:place>/", views.place_page),
    *[path(f"place/<slug:place>/step/<slug:stage>/{suffix}", view) for suffix, view in STEP_ROUTES],
    *[path(f"world/step/<slug:stage>/{suffix}", view) for suffix, view in STEP_ROUTES],
    path("basket/", views.basket),
    path("basket/change/", views.basket_change),
    path("basket/confirm/<int:plan_id>/", views.confirm),
    path("runs/", views.runs),
    path("runs/<int:run_id>/", views.run_page),
    path("requests/", views.requests_page),
    path("library/", library.library_page),
    path("library/<slug:kind>/<str:entry_id>/<int:version>/3d/", library.entry_viewer),
    path("film/", films.film_list),
    path("film/new/", films.film_new),
    path("film/pictures/<slug:place>/", films.film_pictures),
    path("film/<slug:film>/", films.film_page),
    path("film/<slug:film>/compile/", films.film_compile),
    path("film/<slug:film>/save/", films.film_save),
    path("film/<slug:film>/basket/", films.film_basket),
    path("view/<slug:place>", views.viewer),
    path("picks/<slug:place>", views.picks),
    path("refresh/", views.refresh),
    path("freshness/", views.freshness),
    path("admin/", admin.site.urls),
]
if settings.SCORE_PROXY_MODE:
    urlpatterns.append(path("login/", views.login_closed))
else:
    urlpatterns += [path("login/", auth_views.LoginView.as_view(template_name="pages/login.html")),
                    path("logout/", auth_views.LogoutView.as_view())]

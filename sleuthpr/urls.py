from django.urls import path

from . import views
from .services import github

urlpatterns = [
    path("", views.index, name="index"),
    path("event", github.on_event, name="event"),
    path("welcome", views.welcome, name="welcome"),
    path("api", views.api, name="api"),
]

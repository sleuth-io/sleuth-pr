from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('install', views.install, name='install'),
    path('event', views.event, name='event'),
    path('welcome', views.welcome, name='welcome'),
]

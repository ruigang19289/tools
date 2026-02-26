"""
WebSocket URL routing for FIO test
"""
from django.urls import re_path
from . import views

websocket_urlpatterns = [
    re_path(r'api/v1/perf/fio/ws$', views.FIOTestConsumer.as_asgi()),
]

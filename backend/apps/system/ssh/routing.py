"""
WebSocket URL routing for SSH terminal
"""
from django.urls import re_path
from . import views

websocket_urlpatterns = [
    re_path(r'api/ssh/ws$', views.SSHTerminalConsumer.as_asgi()),
]

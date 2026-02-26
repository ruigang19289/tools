"""
WebSocket URL routing for Network Bandwidth Test
"""
from django.urls import re_path
from . import views_ws

websocket_urlpatterns = [
    re_path(r'api/v1/network/iperf3/ws$', views_ws.BandwidthTestConsumer.as_asgi()),
]

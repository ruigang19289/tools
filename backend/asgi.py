"""
ASGI config for tools project.
Supports HTTP and WebSocket protocols.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.tools.settings')

# Get Django ASGI application
django_asgi_app = get_asgi_application()

# Import WebSocket consumers after Django is setup
from backend.apps.performance.FIOTest.routing import websocket_urlpatterns as fio_websocket_patterns
from backend.apps.network.NetworkReliabilityTest.routing import websocket_urlpatterns as bandwidth_websocket_patterns

# Combine all WebSocket URL patterns
websocket_urlpatterns = fio_websocket_patterns + bandwidth_websocket_patterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})

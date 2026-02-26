"""
URL configuration for tools project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from backend.utils import views as utils_views


urlpatterns = [
    path('admin/', admin.site.urls),
    # Health check
    path('api/health/', utils_views.health),
    path('api/info/', utils_views.info),
    # API v1 - Performance tools
    path('api/v1/perf/', include('backend.apps.performance.urls')),
    # API v1 - Network tools
    path('api/v1/network/', include('backend.apps.network.urls')),
    # API v1 - System tools
    path('api/v1/system/', include('backend.apps.system.urls')),
    # Vue SPA catch-all - 放在最后
    re_path(r'^(?!api/).*$', TemplateView.as_view(template_name='index.html'), name='spa'),
]

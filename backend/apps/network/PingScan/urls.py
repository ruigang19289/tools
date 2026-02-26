from django.urls import path
from . import views

urlpatterns = [
    path('ping-scan', views.start_ping_scan, name='ping_scan'),
    path('ping-results/<str:scan_id>', views.get_ping_results, name='ping_results'),
    path('ping-cancel/<str:scan_id>', views.cancel_scan, name='ping_cancel'),
]

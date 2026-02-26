from django.urls import path
from . import views

urlpatterns = [
    path('connect', views.connect, name='monitor_connect'),
    path('disconnect', views.disconnect, name='monitor_disconnect'),
    path('system-info', views.system_info, name='monitor_system_info'),
    path('server-info', views.server_info, name='monitor_server_info'),
]

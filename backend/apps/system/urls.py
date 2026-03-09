from django.urls import path, include

urlpatterns = [
    path('ssh/', include('backend.apps.system.ssh.urls')),
    path('system-init/', include('backend.apps.system.system_init.urls')),
]

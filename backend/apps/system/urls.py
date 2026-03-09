from django.urls import path, include

urlpatterns = [
    path('ansible/', include('backend.apps.system.ansible.urls')),
    path('ssh/', include('backend.apps.system.ssh.urls')),
    path('system-init/', include('backend.apps.system.system_init.urls')),
]

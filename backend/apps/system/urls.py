from django.urls import path, include

urlpatterns = [
    path('ssh/', include('backend.apps.system.ssh.urls')),
    path('system-init/', include('backend.apps.system.system_init.urls')),
    path('database/', include('backend.apps.system.DatabaseTool.urls')),
    path('postgresql/', include('backend.apps.system.DatabaseTool.urls')),  # PostgreSQL 别名
    path('mysql/', include('backend.apps.system.DatabaseTool.urls')),  # MySQL 别名
]

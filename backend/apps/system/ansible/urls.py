from django.urls import path
from . import views

urlpatterns = [
    path('validate-hosts', views.validate_hosts, name='ansible_validate'),
    path('execute', views.execute_command, name='ansible_execute'),
    path('file-transfer', views.file_transfer, name='ansible_file'),
    path('playbook', views.run_playbook, name='ansible_playbook'),
]

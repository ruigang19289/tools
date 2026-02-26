from django.urls import path
from . import views

urlpatterns = [
    path('connect', views.ssh_connect, name='ssh_connect'),
    path('disconnect', views.ssh_disconnect, name='ssh_disconnect'),
    path('validate-hosts', views.validate_hosts, name='ssh_validate_hosts'),
    path('parse-addresses', views.parse_addresses, name='ssh_parse_addresses'),
    path('server-info', views.server_info, name='ssh_server_info'),
    # File Manager APIs
    path('file/connect', views.file_connect, name='file_connect'),
    path('file/list', views.file_list, name='file_list'),
    path('file/download', views.file_download, name='file_download'),
    path('file/upload', views.file_upload, name='file_upload'),
    path('file/disconnect', views.file_disconnect, name='file_disconnect'),
]

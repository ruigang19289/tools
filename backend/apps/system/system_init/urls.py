import re
from django.urls import path
from . import views

urlpatterns = [
    path('validate-hosts', views.validate_hosts, name='system_init_validate'),
    path('full-init', views.full_init, name='system_init_full'),
    path('modify-hostnames', views.modify_hostnames, name='system_init_hostnames'),
    path('configure-ntp', views.configure_ntp, name='system_init_ntp'),
    path('configure-ssh', views.configure_ssh, name='system_init_ssh'),
    path('configure-firewall', views.configure_firewall, name='system_init_firewall'),
    path('disable-selinux', views.disable_selinux, name='system_init_selinux'),
    path('security-hardening', views.security_hardening, name='system_init_hardening'),
]

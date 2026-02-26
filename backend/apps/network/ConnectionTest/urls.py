from django.urls import path
from . import views

urlpatterns = [
    path('ping-start', views.start_ping_test, name='pingtest_ping'),
    path('ssh-start', views.start_ssh_test, name='pingtest_ssh'),
    path('output', views.get_test_output, name='pingtest_output'),
    path('stop', views.stop_test, name='pingtest_stop'),
]

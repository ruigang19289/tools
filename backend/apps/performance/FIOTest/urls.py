from django.urls import path
from . import views

urlpatterns = [
    path('validate-hosts', views.validate_hosts, name='fio-validate-hosts'),
    path('start-test', views.start_test, name='fio-start-test'),
    path('stop-test', views.stop_test, name='fio-stop-test'),
    path('get-output', views.get_output, name='fio-get-output'),
    path('get-results', views.get_results, name='fio-get-results'),
]

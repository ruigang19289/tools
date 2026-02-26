from django.urls import path
from . import views_new

urlpatterns = [
    path('start', views_new.start_bandwidth_test, name='bandwidth_start'),
    path('results/<str:task_id>', views_new.get_test_results, name='bandwidth_results'),
    path('cancel/<str:task_id>', views_new.cancel_test, name='bandwidth_cancel'),
    path('validate', views_new.validate_hosts, name='bandwidth_validate'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('generate-config', views.generate_config, name='cosbench-generate-config'),
]

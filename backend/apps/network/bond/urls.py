from django.urls import path
from . import views

urlpatterns = [
    path('get-nics', views.get_nics, name='bond_get_nics'),
    path('check-service', views.check_service, name='bond_check_service'),
    path('apply-bond', views.apply_bond, name='bond_apply'),
    path('clear-bonds', views.clear_bonds, name='bond_clear'),
]
